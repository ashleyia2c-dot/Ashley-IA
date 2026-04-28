"""
04_train.py — Entrena el modelo de wake word "Ashley" usando OpenWakeWord.

NOTA IMPORTANTE sobre la arquitectura del pipeline:

OpenWakeWord ya provee un pipeline completo de training (`openwakeword.train`
como CLI module). Ese pipeline:
  1. Genera audio sintético positivo con piper-sample-generator (5000+ samples
     de voces y prosodias distintas)
  2. Genera audio adversarial negativo (palabras parecidas: "Asher", "Ashling",
     "ashtray"...) — esto es crítico para tener bajo False Accept Rate
  3. Hace augmentation (background noise mix, reverb, pitch shift) usando los
     RIR + background paths del config
  4. Computa features con AudioFeatures
  5. Entrena el modelo (DNN o RNN) con auto_train()
  6. Exporta a ONNX y luego TFlite

Por tanto, este script NO necesita los outputs de scripts/01-03 — ésos eran
del plan original donde íbamos a hacer todo nosotros. La nueva implementación
es un wrapper que:
  - Verifica que tenemos piper-sample-generator clonado (lo necesita para TTS)
  - Verifica que tenemos los background features de openwakeword
  - Verifica que tenemos RIR + background audio para augmentation
  - Genera ashley.yaml config
  - Lanza `python -m openwakeword.train --training_config ashley.yaml
                                        --generate_clips --augment_clips
                                        --train_model`

Tiempo total: ~3-4 horas en RTX 5060 (gen 30 min + augment+features 1h + train 1-2h).
Disco: ~10-15 GB durante training (limpiable después).
"""

from pathlib import Path
import sys
import subprocess
import urllib.request
import shutil

# Forzar UTF-8 en stdout/stderr para que los caracteres no-ASCII (→, ✓, ↓...
# usados en los mensajes de progreso) no exploten cuando el script se
# redirige a un archivo en Windows (cp1252 por default no los soporta).
# `errors="replace"` evita crashes si algún byte raro sigue colándose.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    # Python < 3.7 o stream wrapped que no soporta reconfigure; ignoramos.
    pass

# Aplicar el patch de torchaudio.load → soundfile ANTES de cualquier import
# que cargue openwakeword o torchaudio. PyTorch nightly movió el backend a
# torchcodec, que en Windows requiere FFmpeg DLLs externas. Sin este patch,
# la fase de feature computation explota con ImportError de torchcodec.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _torchaudio_patch  # noqa: F401 — side-effect import

import torch

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
MODELS_DIR = ROOT / "models"

# Repositorio externo necesario para la generación TTS sintética
PIPER_GEN_DIR = ROOT / "piper-sample-generator"
PIPER_GEN_URL = "https://github.com/rhasspy/piper-sample-generator.git"

# Datos de fondo para augmentation (RIR + background noise)
RIR_DIR = DATA_DIR / "rir"
BG_DIR = DATA_DIR / "background"

# Background features (validación de False Positives durante training).
# Es un .npy con embeddings (N, 96) de speech humano que NO contiene la
# wake word — openwakeword los compara contra las predicciones del modelo
# durante training para calibrar el target_false_positives_per_hour.
#
# El dataset original que openwakeword referencia
# (davidscripka/openwakeword-features en HuggingFace) se hizo privado en
# 2026 y devuelve 401 Unauthorized. Como fallback, generamos nuestro
# propio validation set procesando LibriSpeech dev-clean (~340 MB de
# speech inglés humano público, OpenSLR-12) con AudioFeatures de
# openwakeword. Resultado equivalente al original — la wake word es
# "Ashley" (palabra inglesa) y LibriSpeech es speech inglés clean,
# que es exactamente el caso a validar.
FP_VALIDATION_FILE = DATA_DIR / "validation_set_features.npy"
LIBRISPEECH_URL = "https://www.openslr.org/resources/12/dev-clean.tar.gz"
LIBRISPEECH_TAR = DATA_DIR / "librispeech-dev-clean.tar.gz"
LIBRISPEECH_DIR = DATA_DIR / "LibriSpeech"

WAKE_WORD = "ashley"
CONFIG_FILE = ROOT / f"{WAKE_WORD}.yaml"
TARGET_MODEL = OUTPUT_DIR / f"{WAKE_WORD}.tflite"


# -----------------------------------------------------------------------------
# Setup helpers
# -----------------------------------------------------------------------------

def _download(url: str, dest: Path):
    """urllib con barra de progreso simple."""
    print(f"  ↓ {url}")
    print(f"    → {dest}")

    def hook(block, block_size, total):
        if total <= 0:
            return
        pct = min(100.0, block * block_size * 100.0 / total)
        mb = block * block_size / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        print(f"    {pct:5.1f}%  [{mb:.1f}/{total_mb:.1f} MB]",
              end="\r", flush=True)

    urllib.request.urlretrieve(url, dest, hook)
    print()


def ensure_piper_sample_generator():
    """Setup de piper-sample-generator. openwakeword.train lo usa para
    generar audio TTS de "ashley" en miles de voces sintéticas.

    El repo upstream (rhasspy/piper-sample-generator) cambió de layout en
    v3 — antes había `generate_samples.py` en root, ahora está bajo
    `piper_sample_generator/__main__.py`. Esta función:

      1. Clona el repo si no está (idempotente — si ya existe pero
         incompleto, NO re-clona, asume que un run previo lo dejó OK)
      2. Asegura el voice model .pt en models/
      3. Asegura nuestro shim `generate_samples.py` en root del clone
         que re-exporta con la signature que openwakeword.train espera
    """
    voice_dir = PIPER_GEN_DIR / "models"
    voice_file = voice_dir / "en_US-libritts_r-medium.pt"
    shim_file = PIPER_GEN_DIR / "generate_samples.py"
    package_init = PIPER_GEN_DIR / "piper_sample_generator" / "__init__.py"

    # Paso 1: clonar si NO existe nada del repo
    if not package_init.exists():
        if PIPER_GEN_DIR.exists():
            # Hay un directorio pero está parcial / vacío. Lo limpiamos.
            print(f"Removiendo clone parcial: {PIPER_GEN_DIR}")
            shutil.rmtree(PIPER_GEN_DIR, ignore_errors=True)
        print(f"Cloning piper-sample-generator → {PIPER_GEN_DIR}")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", PIPER_GEN_URL, str(PIPER_GEN_DIR)],
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ERROR clonando: {e}")
            print(f"Manual fix: git clone {PIPER_GEN_URL} {PIPER_GEN_DIR}")
            sys.exit(1)
    else:
        print(f"OK clone presente: {PIPER_GEN_DIR}")

    # Paso 2: voice model
    voice_dir.mkdir(exist_ok=True)
    if not voice_file.exists() or voice_file.stat().st_size < 100_000_000:
        print("Descargando voice model de Piper (~190 MB)...")
        _download(
            "https://github.com/rhasspy/piper-sample-generator/releases/download/"
            "v2.0.0/en_US-libritts_r-medium.pt",
            voice_file,
        )
    else:
        print(f"OK voice model presente: {voice_file.name} "
              f"({voice_file.stat().st_size / 1024 / 1024:.0f} MB)")

    # Paso 3: shim de compatibilidad. openwakeword.train espera un archivo
    # `generate_samples.py` en root del repo (layout viejo de v1.x). El
    # repo nuevo (>=v3) movió la función a piper_sample_generator/__main__.py.
    # Generamos el shim aquí para que `from generate_samples import
    # generate_samples` funcione.
    _SHIM_CONTENT = '''"""Auto-generado por scripts/04_train.py.

Shim de compatibilidad para openwakeword.train, que hace
`from generate_samples import generate_samples` esperando que esto
exista en root del repo de piper-sample-generator (layout v1.x).

El repo actual (>=v3.0) movió la función al sub-package y añadió un
arg `model` requerido. Este shim defaultea `model` al voice .pt
bundled y absorbe kwargs viejos como `auto_reduce_batch_size`.
"""
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
_DEFAULT_MODEL = _HERE / "models" / "en_US-libritts_r-medium.pt"

sys.path.insert(0, str(_HERE))
from piper_sample_generator.__main__ import generate_samples as _real


def generate_samples(text, output_dir, model=None, **kwargs):
    if model is None:
        model = str(_DEFAULT_MODEL)
    _DROPPED = {"auto_reduce_batch_size"}
    safe_kwargs = {k: v for k, v in kwargs.items() if k not in _DROPPED}
    return _real(text=text, output_dir=output_dir, model=model, **safe_kwargs)
'''
    if not shim_file.exists():
        print(f"Generando shim de compatibilidad: {shim_file.name}")
        shim_file.write_text(_SHIM_CONTENT, encoding="utf-8")
    else:
        print(f"OK shim ya existe: {shim_file.name}")


def ensure_background_features():
    """Genera/descarga validation_set_features.npy — usado por openwakeword
    para medir False Positives durante training.

    Estrategia: descargamos LibriSpeech dev-clean (~340 MB, audio público
    de OpenSLR), extraemos los .flac, y generamos features con
    AudioFeatures de openwakeword. El .npy resultante (~50-200 MB según
    cuánto audio procesamos) sustituye al dataset original de HuggingFace
    que se hizo privado.

    Idempotente — si el .npy ya existe (>10 MB), no hace nada. Si solo
    el .tar.gz está descargado pero no extraído, salta el download.
    """
    if FP_VALIDATION_FILE.exists() and FP_VALIDATION_FILE.stat().st_size > 10_000_000:
        size_mb = FP_VALIDATION_FILE.stat().st_size / 1024 / 1024
        print(f"OK validation features presente: {FP_VALIDATION_FILE.name} "
              f"({size_mb:.0f} MB)")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Paso 1: descargar LibriSpeech dev-clean si no está
    if not LIBRISPEECH_TAR.exists() or LIBRISPEECH_TAR.stat().st_size < 100_000_000:
        print("Descargando LibriSpeech dev-clean (~340 MB)...")
        print("(Audio público de OpenSLR — usado para validar False Positive rate.)")
        try:
            _download(LIBRISPEECH_URL, LIBRISPEECH_TAR)
        except Exception as e:
            print(f"ERROR descargando LibriSpeech: {e}")
            print(f"Manual: curl -L {LIBRISPEECH_URL} -o {LIBRISPEECH_TAR}")
            sys.exit(1)
    else:
        print(f"OK LibriSpeech ya descargado ({LIBRISPEECH_TAR.stat().st_size / 1024 / 1024:.0f} MB)")

    # Paso 2: extraer si no está extraído
    if not LIBRISPEECH_DIR.exists() or not any(LIBRISPEECH_DIR.rglob("*.flac")):
        print("Extrayendo LibriSpeech...")
        import tarfile
        with tarfile.open(LIBRISPEECH_TAR, "r:gz") as tar:
            tar.extractall(DATA_DIR)
        print(f"OK extraído a {LIBRISPEECH_DIR}")
    else:
        print(f"OK LibriSpeech ya extraído")

    # Paso 3: generar features con AudioFeatures
    _generate_validation_features_from_librispeech()


def _generate_validation_features_from_librispeech():
    """Procesa los .flac de LibriSpeech dev-clean con AudioFeatures de
    openwakeword y guarda el embedding tensor como validation_set_features.npy.

    El train.py hace un sliding window sobre el .npy y espera shape
    (M, embedding_dim) donde M es el número total de frames de
    embeddings y embedding_dim típicamente 96. Generamos exactamente
    ese formato.

    AudioFeatures.embed_clips() exige clips de longitud uniforme — los
    .flac variables se trocean en chunks de 2s (32000 samples a 16 kHz).
    Limitamos a ~30 min de audio total para que el .npy quede manejable
    (~50-100 MB) en línea con el tamaño del original.
    """
    import numpy as np
    import soundfile as sf

    # Lazy import porque openwakeword tarda 2-3s en importar (carga TF)
    from openwakeword.utils import AudioFeatures

    flac_files = sorted(LIBRISPEECH_DIR.rglob("*.flac"))
    if not flac_files:
        print(f"ERROR: no se encontraron .flac en {LIBRISPEECH_DIR}")
        sys.exit(1)

    # Limitar a ~30 min (LibriSpeech dev-clean tiene ~5h, demasiado).
    MAX_SECONDS = 30 * 60
    CHUNK_SAMPLES = 32000  # 2s a 16 kHz — múltiplo cómodo para el sliding window
    print(f"Encontrados {len(flac_files)} .flac. "
          f"Procesando hasta {MAX_SECONDS//60} min en chunks de 2s...")

    # Cargar SAMPLES de ESC-50 para mezclar como background. El validation
    # set adversarial = speech limpio + speech con TV/música/conversación
    # de fondo. Eso da FPH medido cercano al real-world (vs LibriSpeech
    # solo, que es speech limpio = "fácil").
    bg_paths = list(BG_DIR.glob("*.wav"))
    bg_audios = []
    if bg_paths:
        print(f"Cargando {min(200, len(bg_paths))} backgrounds para mix adversarial...")
        import random
        random.seed(42)
        for bg_path in random.sample(bg_paths, min(200, len(bg_paths))):
            try:
                bg, bg_sr = sf.read(str(bg_path))
                if bg.ndim > 1:
                    bg = bg.mean(axis=1)
                if bg_sr != 16000:
                    from librosa import resample
                    bg = resample(bg, orig_sr=bg_sr, target_sr=16000)
                if len(bg) >= CHUNK_SAMPLES:
                    bg_audios.append(bg[:CHUNK_SAMPLES * 3])  # max 6s por bg
            except Exception:
                continue
        print(f"OK {len(bg_audios)} backgrounds en RAM")

    # Paso 1: cargar audio y trocear en chunks uniformes — con mix opcional
    chunks = []
    total_seconds = 0.0
    n_clean = 0
    n_mixed = 0

    from tqdm import tqdm
    import random
    rng = random.Random(42)
    for flac_path in tqdm(flac_files, desc="Loading FLACs"):
        if total_seconds >= MAX_SECONDS:
            break
        try:
            audio, sr = sf.read(str(flac_path))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != 16000:
                from librosa import resample
                audio = resample(audio, orig_sr=sr, target_sr=16000)
            duration = len(audio) / 16000

            for start in range(0, len(audio) - CHUNK_SAMPLES + 1, CHUNK_SAMPLES):
                speech_chunk = audio[start:start + CHUNK_SAMPLES].astype(np.float32)

                # Con 50% probabilidad, mezclar con background a SNR ~10dB
                # (background audible pero speech sigue dominando)
                if bg_audios and rng.random() < 0.5:
                    bg = rng.choice(bg_audios)
                    bg_start = rng.randint(0, max(0, len(bg) - CHUNK_SAMPLES))
                    bg_chunk = bg[bg_start:bg_start + CHUNK_SAMPLES].astype(np.float32)
                    if len(bg_chunk) < CHUNK_SAMPLES:
                        bg_chunk = np.pad(bg_chunk, (0, CHUNK_SAMPLES - len(bg_chunk)))
                    # SNR ~10dB: scale bg para que su RMS sea ~1/3 del speech RMS
                    speech_rms = np.sqrt(np.mean(speech_chunk ** 2)) + 1e-8
                    bg_rms = np.sqrt(np.mean(bg_chunk ** 2)) + 1e-8
                    bg_chunk = bg_chunk * (speech_rms / bg_rms) * 0.32
                    mixed = speech_chunk + bg_chunk
                    # Clip para evitar overflow
                    mixed = np.clip(mixed, -1.0, 1.0)
                    chunks.append((mixed * 32767).astype(np.int16))
                    n_mixed += 1
                else:
                    chunks.append((speech_chunk * 32767).astype(np.int16))
                    n_clean += 1

            total_seconds += duration
        except Exception as e:
            tqdm.write(f"  warn: {flac_path.name}: {e}")
            continue

    if not chunks:
        print("ERROR: no se pudo trocear ningún .flac en chunks de 2s.")
        sys.exit(1)

    print(f"Total chunks: {len(chunks)} "
          f"(speech limpio: {n_clean}, mezclado adversarial: {n_mixed})")

    # Paso 2: embeddings en batch. verify_environment ya descargó los
    # feature models (melspectrogram + embedding) al inicio, así que
    # AudioFeatures puede instanciarse directamente.
    print("Computando embeddings con AudioFeatures...")
    F = AudioFeatures(device="gpu" if torch.cuda.is_available() else "cpu")
    batch = np.stack(chunks)  # (N, 32000)

    # embed_clips devuelve (N, frames, embedding_dim)
    embeddings = F.embed_clips(batch, batch_size=128)
    print(f"Embeddings shape: {embeddings.shape}")

    # Paso 3: aplanar a (M, embedding_dim) — concatenar todos los frames
    flat = embeddings.reshape(-1, embeddings.shape[-1])
    print(f"Flat shape: {flat.shape}")

    # Paso 4: guardar
    np.save(FP_VALIDATION_FILE, flat)
    size_mb = FP_VALIDATION_FILE.stat().st_size / 1024 / 1024
    print(f"OK guardado: {FP_VALIDATION_FILE} ({size_mb:.1f} MB)")


def ensure_rir_and_background():
    """RIR (Room Impulse Response) + background audio para augmentation.

    Descarga automática si los dirs están vacíos:
      - RIR: OpenSLR-26 sim_rir_16k.zip (~170 MB → ~248 RIR de 16 kHz)
      - Background: ESC-50 (~600 MB → 2000 audios de 5s, 50 categorías
        ambient: TV, música, calle, conversación, etc.)

    Total descarga: ~770 MB. Es lo que diferencia un modelo wake-word
    aceptable (FAR<1/h con TV de fondo) de uno frágil (FAR>5/h).
    """
    RIR_DIR.mkdir(parents=True, exist_ok=True)
    BG_DIR.mkdir(parents=True, exist_ok=True)

    rir_count = len(list(RIR_DIR.rglob("*.wav")))
    bg_count = len(list(BG_DIR.rglob("*.wav")))

    if rir_count >= 50 and bg_count >= 50:
        print(f"OK RIR ({rir_count}) y background ({bg_count}) presentes")
        return

    print(f"RIR/background insuficientes ({rir_count} rir, {bg_count} bg). "
          f"Descargando datasets...")

    # ── RIR: OpenSLR-26 sim_rir_16k ─────────────────────────────────────
    if rir_count < 50:
        rir_zip = DATA_DIR / "sim_rir_16k.zip"
        if not rir_zip.exists() or rir_zip.stat().st_size < 100_000_000:
            print("\nDescargando sim_rir_16k.zip (~170 MB)...")
            try:
                _download(
                    "https://openslr.elda.org/resources/26/sim_rir_16k.zip",
                    rir_zip,
                )
            except Exception as e:
                print(f"WARNING: RIR download failed: {e}")
                print("Continuando sin RIR — modelo final será más frágil.")
                rir_zip = None

        if rir_zip and rir_zip.exists():
            print("Extrayendo RIRs (flatten subdirs to top level)...")
            import zipfile
            # sim_rir_16k.zip tiene estructura subdirs (largeroom/Room001/*.wav).
            # openwakeword usa os.scandir(top_dir) que da subdirs como "files"
            # y luego soundfile crashea al intentar abrir un dir como audio.
            # Solución: extraer directo al top con nombres únicos derivados
            # del path.
            with zipfile.ZipFile(rir_zip) as z:
                for member in z.namelist():
                    if not member.endswith(".wav"):
                        continue
                    # Generar nombre único uniendo segmentos del path
                    flat_name = "_".join(Path(member).parts).replace(" ", "_")
                    target = RIR_DIR / flat_name
                    if not target.exists():
                        with z.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            rir_count = len(list(RIR_DIR.glob("*.wav")))
            print(f"OK extraídos {rir_count} RIR a {RIR_DIR}")

    # ── Background: ESC-50 ──────────────────────────────────────────────
    if bg_count < 50:
        esc50_zip = DATA_DIR / "ESC-50.zip"
        if not esc50_zip.exists() or esc50_zip.stat().st_size < 500_000_000:
            print("\nDescargando ESC-50 (~600 MB)...")
            try:
                _download(
                    "https://github.com/karolpiczak/ESC-50/archive/refs/heads/master.zip",
                    esc50_zip,
                )
            except Exception as e:
                print(f"WARNING: ESC-50 download failed: {e}")
                print("Continuando sin background — modelo final será más frágil.")
                esc50_zip = None

        if esc50_zip and esc50_zip.exists():
            print("Extrayendo ESC-50...")
            import zipfile
            with zipfile.ZipFile(esc50_zip) as z:
                # ESC-50 zip tiene los .wav en ESC-50-master/audio/
                for member in z.namelist():
                    if member.endswith(".wav") and "/audio/" in member:
                        # Flatten al directorio BG_DIR
                        target = BG_DIR / Path(member).name
                        if not target.exists():
                            with z.open(member) as src, open(target, "wb") as dst:
                                shutil.copyfileobj(src, dst)
            bg_count = len(list(BG_DIR.glob("*.wav")))
            print(f"OK extraídos {bg_count} clips de background a {BG_DIR}")

    final_rir = len(list(RIR_DIR.rglob("*.wav")))
    final_bg = len(list(BG_DIR.rglob("*.wav")))
    print(f"\nTotal: {final_rir} RIR + {final_bg} background")
    if final_rir < 50 or final_bg < 50:
        print("WARNING: Aún pocos archivos. Modelo final puede tener FAR alto.")


def write_config():
    """Escribe ashley.yaml con la config para openwakeword.train."""
    n_samples = 16000  # 4x del run inicial — más voces sintéticas, mejor recall
    n_samples_val = 2000
    steps = 50000  # auto_train hace seq 1 (steps) + seq 2 (steps/10) + seq 3 (steps/100)

    config = f"""# OpenWakeWord training config para "Ashley"
# Generado por scripts/04_train.py — no editar a mano

# === Target ===
target_phrase: ["ashley"]
custom_negative_phrases:
  # English variants/homophones
  - "actually"
  - "ashes"
  - "ashen"
  - "ashling"
  - "asher"
  - "ashtray"
  - "ash tree"
  - "ashlee"
  - "ashleigh"
  - "ash"
  - "ashed"
  - "ashy"
  - "absolutely"
  - "actually then"
  - "actuary"
  - "ashtin"
  - "ash three"
  # Other languages with Ashley-like sounds
  - "asia"           # /eɪʒə/ similar to "ashley" /æʃli/ end
  - "ascia"          # italian "axe" /ˈaʃʃa/
  - "achille"        # french /aʃil/
  - "ashanti"
  - "ashfield"
  - "ashgabat"
  # Common confusables in conversational speech
  - "actually I"
  - "ash and"
  - "nashville"
  - "trash"
  - "smashed"
  - "lash"

# === Output ===
model_name: "{WAKE_WORD}"
model_type: "dnn"
layer_size: 64  # 2x — más capacidad para discriminar phonemes parecidos
output_dir: "{OUTPUT_DIR.as_posix()}"

# === Sample generation (Piper TTS) ===
piper_sample_generator_path: "{PIPER_GEN_DIR.as_posix()}"
n_samples: {n_samples}
n_samples_val: {n_samples_val}
tts_batch_size: 50

# === Augmentation ===
# 2 rounds = cada clip se augmenta 2x con distintas combinaciones de RIR
# y background. Crítico para que el modelo sea robusto a TV/música/eco.
augmentation_rounds: 2
augmentation_batch_size: 16
rir_paths:
  - "{RIR_DIR.as_posix()}"
background_paths:
  - "{BG_DIR.as_posix()}"
background_paths_duplication_rate:
  - 1

# === Training ===
steps: {steps}
# batch_n_per_class debe ser un dict mapeando label → cantidad por batch.
# Las labels son las keys de feature_data_files (que train.py rellena con
# 'positive' y 'adversarial_negative'). Los valores controlan el balance:
# 128/128 = 1:1 ratio positivos vs negativos en cada batch.
batch_n_per_class:
  positive: 128
  adversarial_negative: 128
# Penalización para falsos positivos durante backprop. 5000 (vs default 1000)
# fuerza al modelo a optimizar fuertemente para low FP, a costo potencial de
# 2-3% de recall. Trade-off worth it para wake words consumer.
max_negative_weight: 5000
target_false_positives_per_hour: 0.5

# Background features (precomputadas, sirven como validation false-positive set)
false_positive_validation_data_path: "{FP_VALIDATION_FILE.as_posix()}"

# Datasets adicionales de features (vacío para empezar)
feature_data_files: {{}}

# total_length lo calcula el script según la duración mediana de los clips
total_length: 32000
"""
    CONFIG_FILE.write_text(config, encoding="utf-8")
    print(f"OK Config escrita: {CONFIG_FILE.name}")


def verify_environment():
    """Sanity check antes de lanzar el training."""
    print("=== Environment check ===")
    print(f"PyTorch: {torch.__version__}")
    if not torch.cuda.is_available():
        print("WARNING: CUDA NO DISPONIBLE. Training en CPU será MUY lento.")
        ans = input("Continuar en CPU? [y/N]: ").strip().lower()
        if ans != "y":
            sys.exit(1)
    else:
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU: {gpu} ({vram:.1f} GB)")

    try:
        import openwakeword  # noqa: F401
        print("OK openwakeword instalado")
    except ImportError:
        print("ERROR: openwakeword no instalado. Run setup.bat primero.")
        sys.exit(1)

    # Descargar feature extraction models (melspectrogram + embedding +
    # VAD) una sola vez. openwakeword los necesita para compute_features
    # y para AudioFeatures, pero NO los incluye en el package install.
    # Idempotente — skipea si ya están en resources/models/.
    print("Asegurando feature extraction models (one-time download ~5 MB)...")
    try:
        from openwakeword.utils import download_models
        download_models([])
        print("OK feature models presentes")
    except Exception as e:
        print(f"WARNING: download_models falló: {e}")
        print("  El training podría fallar más adelante si los modelos no están.")

    print()


def run_training():
    """Ejecuta openwakeword.train EN EL MISMO PROCESO (no subprocess).

    Razón: el patch de torchaudio.load → soundfile se aplica al import
    de _torchaudio_patch al inicio de este script. Si lanzáramos un
    subprocess de python, ese subprocess no tendría el patch aplicado y
    la fase de feature computation explotaría con torchcodec ImportError.

    Implementación: seteamos sys.argv como si openwakeword.train fuera
    invocado vía CLI, y usamos runpy para ejecutar el módulo con
    `__name__ == '__main__'` para que su bloque CLI se active.
    """
    import runpy

    print(f"=== Lanzando openwakeword.train (in-process) ===")
    print(f"Config: {CONFIG_FILE}")
    print(f"Esto va a tomar varias horas. Ctrl+C para parar — checkpoints")
    print(f"intermedios se guardan en {OUTPUT_DIR}\n")

    # ¿Hay features parciales de un run anterior? El --augment_clips de
    # openwakeword skipea si encuentra positive_features_train.npy, pero
    # NO chequea los otros 3 .npy — si una corrida previa abortó a mitad
    # del feature computation, dejaste positive_features_train.npy pero
    # faltan negative_features_train.npy y los _test.npy. En ese caso hay
    # que pasar --overwrite para regenerar todos.
    feature_dir = OUTPUT_DIR / WAKE_WORD
    expected_features = [
        "positive_features_train.npy",
        "negative_features_train.npy",
        "positive_features_test.npy",
        "negative_features_test.npy",
    ]
    missing = [f for f in expected_features if not (feature_dir / f).exists()]
    has_some = any((feature_dir / f).exists() for f in expected_features)
    needs_overwrite = has_some and bool(missing)
    if needs_overwrite:
        print(f"Features parciales detectadas. Regenerando todas (faltan: {missing})")

    # NOTA: el fix del Windows file-lock en trim_mmap está aplicado
    # DIRECTAMENTE en venv/.../openwakeword/data.py.

    # Inyectar fake `k2` module para evitar que speechbrain.integrations.k2_fsa
    # explote durante imports. La cadena del bug es:
    #   runpy carga openwakeword.train
    #   → openwakeword.data
    #   → torch_audiomentations
    #   → torchmetrics.functional.image.arniqa
    #   → torchvision (carga inicial)
    #   → torch.library.register_fake("torchvision::nms")
    #   → inspect.getframeinfo()
    #   → inspect.getmodule()
    #   → hasattr(speechbrain.LazyModule, '__file__')  ← activa el lazy
    #   → speechbrain intenta `import k2`
    #   → ModuleNotFoundError 'k2'
    # Como nuestro flow NO usa k2, le damos un módulo vacío que pasa el
    # import. speechbrain.integrations.k2_fsa quedará "imported but useless",
    # que es exactamente lo que queremos.
    if "k2" not in sys.modules:
        import types
        sys.modules["k2"] = types.ModuleType("k2")

    # Preservar argv original para poder restaurarlo después (defensive)
    original_argv = sys.argv[:]
    try:
        sys.argv = [
            "openwakeword.train",
            "--training_config", str(CONFIG_FILE),
            "--generate_clips",
            "--augment_clips",
            "--train_model",
        ]
        if needs_overwrite:
            sys.argv.append("--overwrite")
        print("Args:", " ".join(sys.argv[1:]), "\n")
        runpy.run_module("openwakeword.train", run_name="__main__")
    except SystemExit as e:
        # train.py llama sys.exit() en algunos paths; lo capturamos para no
        # cerrar nuestro propio proceso antes de imprimir el resumen final.
        if e.code not in (None, 0):
            print(f"\nERROR: training salió con código {e.code}")
            sys.exit(e.code)
    except KeyboardInterrupt:
        print("\n[INTERRUMPIDO]")
        sys.exit(130)
    finally:
        sys.argv = original_argv


def _preflight_summary() -> None:
    """Muestra un resumen de qué se va a hacer antes de descargar nada,
    para que el user pueda cancelar antes de comprometer disco/tiempo.

    Modo no-interactivo: si stdin no es un tty (ej: lanzado desde un
    subprocess en background), skipea el confirm automáticamente. Eso
    permite ejecutarlo desde herramientas externas sin colgarse esperando
    input. El user puede forzar interactivo con `WAKE_TRAIN_CONFIRM=1`
    si quiere el confirm aunque tenga stdin redirigido.
    """
    piper_present = (PIPER_GEN_DIR / "generate_samples.py").exists()
    fp_present = (FP_VALIDATION_FILE.exists()
                  and FP_VALIDATION_FILE.stat().st_size > 100_000_000)

    print("--- Preflight ---")
    print(f"piper-sample-generator: "
          f"{'OK ya está' if piper_present else 'se clonará (~80 MB)'}")
    print(f"validation features:    "
          f"{'OK ya está' if fp_present else 'se descargará (~250 MB)'}")
    print(f"output dir:             {OUTPUT_DIR}")
    print(f"GPU training estimado:  ~3-4 horas en RTX 5060")
    print(f"Disco usado durante:    ~10-15 GB (limpiable después)")
    print()

    if piper_present and fp_present:
        return  # nada que descargar, no hace falta confirm

    import os
    is_interactive = sys.stdin.isatty() or os.environ.get("WAKE_TRAIN_CONFIRM") == "1"
    if not is_interactive:
        print("Modo no-interactivo (stdin no es tty). Continuando automáticamente.")
        print("Para forzar confirm: set WAKE_TRAIN_CONFIRM=1")
        return

    ans = input("¿Continuar y descargar lo que falta? [Y/n]: ").strip().lower()
    if ans == "n":
        print("Cancelado por el user.")
        sys.exit(0)


def main():
    print("=== Wake word training pipeline ===\n")
    verify_environment()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    _preflight_summary()

    print("--- 1/4 piper-sample-generator ---")
    ensure_piper_sample_generator()

    print("\n--- 2/4 background validation features ---")
    ensure_background_features()

    print("\n--- 3/4 RIR + background audio ---")
    ensure_rir_and_background()

    print("\n--- 4/4 config YAML ---")
    write_config()

    print()
    run_training()

    # Verificar output. openwakeword exporta DOS archivos:
    #   - ashley.onnx  (formato preferido para integrar en Ashley app —
    #                   onnxruntime ya está en el venv principal)
    #   - ashley.tflite (formato alternativo, requiere tflite_runtime
    #                   — y `onnx_tf` para la conversión, que en 2026
    #                   tiene incompatibilidades con tensorflow 2.21)
    # Nota: openwakeword guarda en OUTPUT_DIR (no OUTPUT_DIR/WAKE_WORD).
    onnx_path = OUTPUT_DIR / f"{WAKE_WORD}.onnx"
    tflite_path = OUTPUT_DIR / f"{WAKE_WORD}.tflite"

    print()
    print("=== Output ===")
    if onnx_path.exists():
        mb = onnx_path.stat().st_size / 1024 / 1024
        print(f"OK ONNX:   {onnx_path} ({mb:.1f} MB)  ← preferido para Ashley")
    if tflite_path.exists():
        mb = tflite_path.stat().st_size / 1024 / 1024
        print(f"OK TFLite: {tflite_path} ({mb:.1f} MB)")
    if not onnx_path.exists() and not tflite_path.exists():
        print(f"WARNING: no se encontraron ni .onnx ni .tflite en "
              f"{OUTPUT_DIR / WAKE_WORD}")
        print(f"Buscar manualmente en {OUTPUT_DIR}")
        return

    print()
    print("=== Next ===")
    print(f"  1. Test con tu mic: python scripts/05_test.py")
    print(f"  2. Si los números (FRR<5%, FAR<1/h) son OK, copia el .onnx a:")
    print(f"     reflex_companion/wake_word/{WAKE_WORD}.onnx")


if __name__ == "__main__":
    main()
