"""
whisper_stt.py — Speech-to-Text local con faster-whisper.

Transcribe audio a texto usando el modelo 'base' multilingüe.
El modelo se descarga la primera vez (~75 MB) y se cachea en
%APPDATA%\\ashley\\models\\whisper\\ (o equivalente en otros sistemas).

Puntos clave:
  • Lazy loading: el modelo no se carga hasta la primera transcripción
  • Thread-safe: hay un Lock para evitar cargas paralelas
  • int8 compute type: máxima velocidad con mínima pérdida de precisión
  • VAD filter activo: ignora silencios al principio/final
"""

import os
import tempfile
import threading
from typing import Optional


# Modelo y configuración
_MODEL_SIZE = "small"          # ~245 MB multilingüe, alta precisión (~96%)
_COMPUTE_TYPE = "int8"         # CPU optimizado
_DEVICE = "cpu"                # CPU por defecto (GPU requiere setup extra)

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


def _load_model():
    """Carga (y descarga si hace falta) el modelo Whisper."""
    global _model, _model_loading, _model_error
    with _model_lock:
        if _model is not None:
            return _model
        _model_loading = True
        _model_error = None
    try:
        from faster_whisper import WhisperModel
        mdl = WhisperModel(
            _MODEL_SIZE,
            device=_DEVICE,
            compute_type=_COMPUTE_TYPE,
            download_root=_cache_dir(),
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

    try:
        segments, info = model.transcribe(
            temp_path,
            language=language if language in ("en", "es") else None,
            beam_size=5,              # 5 = precisión alta (1 era rápido pero impreciso)
            vad_filter=True,          # salta silencios
            vad_parameters={
                "min_silence_duration_ms": 500,   # antes 300 — cortaba palabras
                "speech_pad_ms": 200,             # pad alrededor del habla detectada
            },
            initial_prompt="Ashley, jefe, boss.",  # ayuda a reconocer palabras clave
        )
        parts = []
        for s in segments:
            t = (s.text or "").strip()
            if t:
                parts.append(t)
        return " ".join(parts).strip()
    finally:
        try:
            os.unlink(temp_path)
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
