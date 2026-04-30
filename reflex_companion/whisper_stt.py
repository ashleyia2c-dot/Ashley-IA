"""
whisper_stt.py — Speech-to-Text local con faster-whisper.

Transcribe audio a texto usando un modelo multilingüe local. El modelo
se descarga la primera vez y se cachea en %APPDATA%\\ashley\\models\\
whisper\\ (o equivalente en otros sistemas).

Puntos clave:
  • Lazy loading: el modelo no se carga hasta la primera transcripción
  • Thread-safe: hay un Lock para evitar cargas paralelas
  • Audio gain normalization PRE-Whisper: susurros (-30dB) se promocionan
    a -20dB target, lo que ayuda a que Whisper los procese como speech
    normal en lugar de filtrarlos como ruido
  • VAD filter activo con threshold bajo (0.3) para no cortar susurros
  • Modelo y device configurables via env vars (ASHLEY_WHISPER_MODEL,
    ASHLEY_WHISPER_DEVICE) — para que power users puedan subir a medium
    o usar GPU sin tocar código.
"""

import os
import tempfile
import threading
from typing import Optional


# Configuración por defecto. Override via env vars:
#   ASHLEY_WHISPER_MODEL=tiny|base|small|medium|large-v3|large-v3-turbo
#   ASHLEY_WHISPER_DEVICE=cpu|cuda  (cuda requiere CUDA + cuDNN instalados)
#   ASHLEY_WHISPER_COMPUTE=int8|int8_float16|float16|float32
_MODEL_SIZE = os.getenv("ASHLEY_WHISPER_MODEL", "small")
_DEVICE = os.getenv("ASHLEY_WHISPER_DEVICE", "cpu")
_COMPUTE_TYPE = os.getenv(
    "ASHLEY_WHISPER_COMPUTE",
    "int8" if _DEVICE == "cpu" else "float16",
)

_model = None
_model_lock = threading.Lock()
_model_loading = False
_model_error: Optional[str] = None


def _cache_dir() -> str:
    """Devuelve la carpeta de cache del modelo."""
    env_dir = os.getenv("ASHLEY_DATA_DIR")
    if env_dir:
        base = env_dir
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path = os.path.join(base, "models", "whisper")
    os.makedirs(path, exist_ok=True)
    return path


def is_loading() -> bool:
    return _model_loading


def is_loaded() -> bool:
    return _model is not None


def load_error() -> Optional[str]:
    return _model_error


def is_cached_on_disk() -> bool:
    """v0.16.13 — True si el modelo ya está descargado físicamente en disco.

    Permite distinguir entre "primera descarga real" (~245 MB, ~1-5 min)
    vs "cargando del disco a RAM" (~5-15s). Antes el frontend mostraba
    'Descargando 245 MB' aunque el modelo ya estuviera cacheado, porque
    el código solo verificaba is_loaded() (en memoria), no en disco.

    Verificamos los archivos esperados con tamaño >0. Si el modelo está
    completo, devuelve True; si falta algo o no existe, False.
    """
    try:
        cache_dir = _cache_dir()
        local_dir = os.path.join(
            cache_dir,
            f"models--Systran--faster-whisper-{_MODEL_SIZE}-direct",
        )
        expected = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")
        return all(
            os.path.exists(os.path.join(local_dir, f)) and
            os.path.getsize(os.path.join(local_dir, f)) > 0
            for f in expected
        )
    except Exception:
        return False


def _ensure_model_local(model_size: str, cache_dir: str) -> str:
    """Asegura que el modelo está físicamente descargado en disk con
    archivos REALES (no symlinks). Devuelve el path local listo para
    pasarse a WhisperModel(...).

    Necesario porque huggingface_hub usa symlinks entre `snapshots/` y
    `blobs/` por default. En Windows los symlinks requieren modo
    Developer o admin — sin esos privilegios, los archivos en
    `snapshots/` quedan vacíos (0 bytes) y faster-whisper no puede
    cargar el modelo aunque YA esté descargado en `blobs/`.
    Resultado: re-descarga en cada arranque de la app.

    Forzamos `local_dir_use_symlinks=False` → copies reales que
    funcionan sin privilegios. Idempotente: si los archivos ya están
    completos, snapshot_download es no-op (~100ms para verificar).
    """
    import os as _os

    # faster-whisper usa el repo "Systran/faster-whisper-{size}"
    repo_id = f"Systran/faster-whisper-{model_size}"
    local_dir = _os.path.join(cache_dir, f"models--{repo_id.replace('/', '--')}-direct")

    # Si la carpeta ya tiene los archivos esperados con tamaño >0,
    # asumimos que está bien y skipeamos el download check.
    expected = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")
    have_all = all(
        _os.path.exists(_os.path.join(local_dir, f)) and
        _os.path.getsize(_os.path.join(local_dir, f)) > 0
        for f in expected
    )
    if have_all:
        return local_dir

    # Descargar (o completar) sin symlinks
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,  # ← key fix para Windows
    )
    return local_dir


def _load_model():
    """Carga (y descarga si hace falta) el modelo Whisper.

    En Windows: forzamos download a una carpeta plana sin symlinks
    para que el modelo persista entre reinicios de la app. Sin esto,
    huggingface_hub crea symlinks que Windows rellena con 0 bytes y
    faster-whisper re-descarga cada vez (bug visible al user como
    "siempre sale el banner de descargando").
    """
    global _model, _model_loading, _model_error
    with _model_lock:
        if _model is not None:
            return _model
        _model_loading = True
        _model_error = None
    try:
        from faster_whisper import WhisperModel

        cache_dir = _cache_dir()
        # Pre-download con copies (no symlinks). Devuelve path local plano.
        try:
            local_path = _ensure_model_local(_MODEL_SIZE, cache_dir)
            mdl = WhisperModel(
                local_path,  # path local directo, no model_size
                device=_DEVICE,
                compute_type=_COMPUTE_TYPE,
            )
        except Exception:
            # Fallback al path original (download_root con symlinks).
            # Si el user tiene Developer Mode o admin, esto funciona.
            # Si no, primer arranque OK pero re-download cada vez.
            mdl = WhisperModel(
                _MODEL_SIZE,
                device=_DEVICE,
                compute_type=_COMPUTE_TYPE,
                download_root=cache_dir,
            )

        with _model_lock:
            _model = mdl
            _model_loading = False
        return _model
    except Exception as e:
        with _model_lock:
            _model_error = str(e)
            _model_loading = False
        raise


# Gain normalization target. -20 dBFS RMS es típico de speech humano normal.
# Susurros tienen RMS ~-30 a -40 dBFS. Si normalizamos a -20, Whisper procesa
# el susurro con la misma "energía" que voz normal y la transcribe mejor.
_TARGET_RMS_DBFS = -20.0
# Cap de gain — no amplificamos más de 25 dB (eso es ya 18x el volumen).
# Más allá empieza a meter ruido del propio mic. 25 dB es buen techo.
_MAX_GAIN_DB = 25.0


def _decode_audio_to_numpy(audio_path: str):
    """Decodifica un archivo de audio (cualquier formato que ffmpeg lea —
    webm/opus, mp3, wav, ogg, m4a) a un numpy array float32 mono.

    Returns (audio_np, sample_rate) o (None, None) si falla. Usa PyAV
    que viene bundled como wheel (sin requerir ffmpeg en el sistema)
    y es el mismo decoder que faster-whisper usa internamente.
    """
    try:
        import av
        import numpy as np
    except ImportError:
        return None, None

    try:
        container = av.open(audio_path)
        try:
            audio_stream = next(
                s for s in container.streams if s.type == "audio"
            )
        except StopIteration:
            container.close()
            return None, None

        sr = audio_stream.codec_context.sample_rate or audio_stream.rate
        # Decodificar todos los frames y concatenar a un solo array
        chunks = []
        for frame in container.decode(audio_stream):
            arr = frame.to_ndarray()
            # PyAV puede devolver shape (channels, samples) o (1, samples)
            if arr.ndim > 1:
                arr = arr.mean(axis=0)  # mono
            chunks.append(arr.astype(np.float32, copy=False))
        container.close()

        if not chunks:
            return None, None
        audio = np.concatenate(chunks)
        # PyAV típicamente da int16 — normalizamos a [-1, 1] float
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if audio.max() > 1.5 or audio.min() < -1.5:
            # Probablemente int range — normalize
            audio = audio / 32768.0
        return audio, sr
    except Exception:
        return None, None


def _normalize_audio_gain(audio_path: str) -> str:
    """Lee el audio, calcula su RMS, y lo amplifica al target si está bajo.

    Devuelve el path al archivo normalizado (un .wav nuevo si normalizamos,
    o el path original si no era necesario o no pudimos decodificar).
    Funciona con webm/opus (formato típico de MediaRecorder en Chrome/
    Electron) gracias a PyAV.
    """
    try:
        import math
        import numpy as np
        import soundfile as sf
    except ImportError:
        return audio_path

    audio, sr = _decode_audio_to_numpy(audio_path)
    if audio is None or len(audio) == 0:
        return audio_path

    # RMS y su dBFS (full-scale = 0 dBFS = clip)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-6:
        # Audio silencioso — no normalizamos (sería amplificar puro ruido)
        return audio_path
    rms_dbfs = 20.0 * math.log10(rms)

    # ¿Hace falta amplificar?
    gain_db = _TARGET_RMS_DBFS - rms_dbfs
    if gain_db <= 0:
        # El audio ya está al target (o más alto) — no tocar
        return audio_path
    gain_db = min(gain_db, _MAX_GAIN_DB)
    gain_linear = 10.0 ** (gain_db / 20.0)

    amplified = audio * gain_linear
    # Soft-clip con tanh: smooth, preserva señal mejor que hard clip a [-1,1]
    amplified = np.tanh(amplified)

    # Guardar como .wav (subtype PCM_16 es universal). soundfile escribe
    # WAV sin necesitar ffmpeg.
    out_path = audio_path + ".normalized.wav"
    try:
        sf.write(out_path, amplified, sr, subtype="PCM_16")
        return out_path
    except Exception:
        return audio_path


# Umbrales de confianza para descartar transcripciones probablemente
# espurias (audio de fondo cuando el wake word disparó al detectar un
# video reproduciendo, ruido del mic, etc).
#
# Whisper devuelve en cada segment:
#   no_speech_prob: probabilidad de que el segment sea silencio/ruido
#                   (no voz humana). 0=segura voz, 1=segura no-voz.
#   avg_logprob: logprob promedio de los tokens. Más cerca de 0 = más
#                seguro de la transcripción. Bajo (e.g. -1.5) = el
#                modelo no "creía" lo que estaba diciendo.
#
# Si TODOS los segments fallan ambos thresholds, asumimos ruido y
# devolvemos vacío. Ningún listado de palabras concretas — la propia
# señal de Whisper decide.
_NO_SPEECH_THRESHOLD = 0.6
_LOGPROB_THRESHOLD = -1.0


def transcribe_bytes(audio_bytes: bytes, language: Optional[str] = None) -> str:
    """
    Transcribe audio (webm / wav / mp3 / ogg) a texto.

    Args:
        audio_bytes: contenido del archivo de audio
        language: código ISO 639-1 ('en', 'es'). None = auto-detectar.

    Returns:
        Texto transcrito (string). Vacío si no se detectó habla.
    """
    if not audio_bytes or len(audio_bytes) < 500:
        return ""

    model = _load_model()

    # faster-whisper acepta path de archivo; guardamos en temp
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        temp_path = f.name

    # Pre-procesado: amplificar audio bajo (susurros) al rango de speech
    # normal antes de pasar a Whisper. Si el audio ya está alto, no toca
    # nada — devuelve el path original.
    normalized_path = _normalize_audio_gain(temp_path)

    try:
        try:
            segments, info = model.transcribe(
                normalized_path,
                language=language if language in ("en", "es") else None,
                beam_size=5,              # 5 = precisión alta (1 era rápido pero impreciso)
                vad_filter=True,          # salta silencios
                vad_parameters={
                    # Threshold bajo (0.3) para no cortar susurros — el VAD
                    # default de Silero es 0.5 y a esa exigencia los
                    # susurros normalizados pueden seguir siendo "silencio".
                    "threshold": 0.3,
                    "min_silence_duration_ms": 500,   # antes 300 — cortaba palabras
                    "speech_pad_ms": 300,             # +100ms pad antes/después
                                                      # — protege bordes en
                                                      # frases cortas tipo "sí"
                },
                initial_prompt="Ashley, jefe, boss.",  # ayuda a reconocer palabras clave
            )
        except Exception as decode_err:
            # Errores típicos:
            #   - AVERROR_INVALIDDATA (errno 1094995529): el webm/opus
            #     que mandó MediaRecorder está corrupto o truncado —
            #     suele pasar con grabaciones MUY cortas (<200ms) o
            #     cuando el wake word disparó pero el user no llegó
            #     a hablar.
            #   - OSError de I/O temporal.
            # En cualquier caso, mejor devolver "" (frontend skipea texts
            # vacíos en silencio) que dejar burbujear una alert al user
            # con un errno hexadecimal sin contexto.
            import logging
            logging.getLogger("ashley.whisper").warning(
                "transcribe failed on %s: %s — returning empty",
                normalized_path, decode_err,
            )
            return ""
        parts = []
        any_confident = False  # ¿algún segment cumplió ambos thresholds?
        for s in segments:
            t = (s.text or "").strip()
            if not t:
                continue
            parts.append(t)
            # ¿Este segment es confiable? Si al menos uno lo es, la
            # transcripción tiene contenido real — la devolvemos entera.
            no_speech = getattr(s, "no_speech_prob", 0.0)
            logp = getattr(s, "avg_logprob", 0.0)
            if no_speech < _NO_SPEECH_THRESHOLD and logp > _LOGPROB_THRESHOLD:
                any_confident = True
        if not any_confident:
            # Todos los segments tenían baja confianza — probable ruido
            # (video de fondo, mic con TV, etc). Mejor devolver vacío
            # que meter contenido fantasma al chat.
            return ""
        return " ".join(parts).strip()
    finally:
        for p in {temp_path, normalized_path}:
            try:
                os.unlink(p)
            except Exception:
                pass


def warmup():
    """Carga el modelo en background sin bloquear (opcional, para acelerar primera petición)."""
    def _bg():
        try:
            _load_model()
        except Exception as e:
            print(f"[whisper_stt] warmup failed: {e}")
    t = threading.Thread(target=_bg, daemon=True)
    t.start()
