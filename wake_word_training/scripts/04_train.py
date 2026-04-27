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
# Es un .npy ~250 MB que openwakeword publica en HuggingFace.
FP_VALIDATION_FILE = DATA_DIR / "validation_set_features.npy"
FP_VALIDATION_URL = (
    "https://huggingface.co/datasets/davidscripka/"
    "openwakeword-features/resolve/main/validation_set_features.npy"
)

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
    """Clona rhasspy/piper-sample-generator. openwakeword.train lo usa para
    generar audio TTS de "ashley" en miles de voces sintéticas."""
    if (PIPER_GEN_DIR / "generate_samples.py").exists():
        print(f"OK piper-sample-generator presente: {PIPER_GEN_DIR}")
        return
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

    # Modelo de Piper que el generator necesita (~60 MB)
    voice_dir = PIPER_GEN_DIR / "models"
    voice_dir.mkdir(exist_ok=True)
    voice_file = voice_dir / "en_US-libritts_r-medium.pt"
    if not voice_file.exists():
        print("Descargando voice model de Piper (~60 MB)...")
        _download(
            "https://github.com/rhasspy/piper-sample-generator/releases/download/"
            "v2.0.0/en_US-libritts_r-medium.pt",
            voice_file,
        )


def ensure_background_features():
    """Descarga validation_set_features.npy — usado por openwakeword para medir
    False Positives durante training. ~250 MB."""
    if FP_VALIDATION_FILE.exists() and FP_VALIDATION_FILE.stat().st_size > 100_000_000:
        print(f"OK validation features presente: {FP_VALIDATION_FILE.name}")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Descargando validation features (~250 MB)...")
    try:
        _download(FP_VALIDATION_URL, FP_VALIDATION_FILE)
    except Exception as e:
        print(f"ERROR descargando validation features: {e}")
        print(f"Manual: curl -L {FP_VALIDATION_URL} -o {FP_VALIDATION_FILE}")
        sys.exit(1)


def ensure_rir_and_background():
    """RIR (Room Impulse Response) + background audio para augmentation.

    openwakeword recomienda:
      - RIR: MIT IR Survey o BUT_ReverbDB
      - Background: FMA (Free Music Archive) o AudioSet

    Como esos datasets pesan mucho (>5GB), usamos un subset razonable:
    descargamos sólo unos 50 RIR + 200 clips de background. Suficiente para una
    primera iteración. Si los números de FAR salen mal, descargar datasets
    completos manualmente y meterlos en data/rir/ y data/background/.
    """
    RIR_DIR.mkdir(parents=True, exist_ok=True)
    BG_DIR.mkdir(parents=True, exist_ok=True)

    rir_count = len(list(RIR_DIR.glob("*.wav")))
    bg_count = len(list(BG_DIR.glob("*.wav")))

    if rir_count >= 10 and bg_count >= 10:
        print(f"OK RIR ({rir_count}) y background ({bg_count}) presentes")
        return

    if rir_count < 10 or bg_count < 10:
        print()
        print(f"WARNING: pocos RIR/background ({rir_count} rir, {bg_count} bg)")
        print("Para un training de calidad necesitas ~50+ de cada uno.")
        print("Recomendación:")
        print("  RIR:  https://www.openslr.org/26/  (Aachen IR Database)")
        print("  BG:   https://github.com/karolpiczak/ESC-50  (ambient sounds)")
        print(f"  Mete los .wav en {RIR_DIR} y {BG_DIR}")
        print()
        # Dejamos seguir — openwakeword se las apaña con poco background, sólo
        # bajará la calidad del augmentation.


def write_config():
    """Escribe ashley.yaml con la config para openwakeword.train."""
    n_samples = 4000  # cuántos clips positivos generar (más = mejor pero más tiempo)
    n_samples_val = 500
    steps = 50000  # pasos de entrenamiento

    config = f"""# OpenWakeWord training config para "Ashley"
# Generado por scripts/04_train.py — no editar a mano

# === Target ===
target_phrase: ["ashley"]
custom_negative_phrases:
  - "actually"
  - "ashes"
  - "ashen"
  - "ashling"
  - "asher"
  - "asia"
  - "ashtray"
  - "ash tree"
  - "ashlee"
  - "ashleigh"

# === Output ===
model_name: "{WAKE_WORD}"
model_type: "dnn"
layer_size: 32
output_dir: "{OUTPUT_DIR.as_posix()}"

# === Sample generation (Piper TTS) ===
piper_sample_generator_path: "{PIPER_GEN_DIR.as_posix()}"
n_samples: {n_samples}
n_samples_val: {n_samples_val}
tts_batch_size: 50

# === Augmentation ===
augmentation_rounds: 1
augmentation_batch_size: 16
rir_paths:
  - "{RIR_DIR.as_posix()}"
background_paths:
  - "{BG_DIR.as_posix()}"
background_paths_duplication_rate:
  - 1

# === Training ===
steps: {steps}
batch_n_per_class: 256
max_negative_weight: 1500
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

    print()


def run_training():
    """Lanza openwakeword.train como subprocess y stream el stdout."""
    print(f"=== Lanzando openwakeword.train ===")
    print(f"Config: {CONFIG_FILE}")
    print(f"Esto va a tomar ~3-4 horas en RTX 5060.")
    print(f"Ctrl+C para parar — checkpoints intermedios se guardan en {OUTPUT_DIR}\n")

    cmd = [
        sys.executable, "-m", "openwakeword.train",
        "--training_config", str(CONFIG_FILE),
        "--generate_clips",
        "--augment_clips",
        "--train_model",
    ]
    print("Command:", " ".join(cmd), "\n")

    # subprocess con stdout pipe — para ver progreso en tiempo real
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    try:
        for line in proc.stdout:
            print(line, end="", flush=True)
        rc = proc.wait()
    except KeyboardInterrupt:
        print("\n[INTERRUMPIDO]")
        proc.terminate()
        proc.wait()
        sys.exit(130)

    if rc != 0:
        print(f"\nERROR: training falló (exit {rc})")
        sys.exit(rc)


def _preflight_summary() -> None:
    """Muestra un resumen de qué se va a hacer antes de descargar nada,
    para que el user pueda cancelar antes de comprometer disco/tiempo."""
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
    if not piper_present or not fp_present:
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
    #   - ashley.tflite (formato alternativo, requiere tflite_runtime)
    onnx_path = OUTPUT_DIR / WAKE_WORD / f"{WAKE_WORD}.onnx"
    tflite_path = OUTPUT_DIR / WAKE_WORD / f"{WAKE_WORD}.tflite"

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
