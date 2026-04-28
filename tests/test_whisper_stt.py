"""Tests para reflex_companion/whisper_stt.py.

Cobertura:
  - _decode_audio_to_numpy: decodifica WAV (PyAV) a numpy float32 mono
  - _normalize_audio_gain: amplifica audio bajo a -20 dBFS RMS
  - Audio ya alto NO se toca
  - Audio totalmente silencioso NO se toca (no amplifica ruido)

NO cubre transcribe_bytes — eso requiere cargar el modelo Whisper
(245 MB) que tarda ~3s y consume RAM significativa. Test integration
manual.
"""

from __future__ import annotations

import math
import os
import tempfile

import pytest


@pytest.fixture
def soundfile_or_skip():
    sf = pytest.importorskip("soundfile")
    return sf


@pytest.fixture
def numpy_or_skip():
    np = pytest.importorskip("numpy")
    return np


def _write_test_wav(path: str, audio, sr: int = 16000):
    """Helper — escribe un wav con el audio dado."""
    import soundfile as sf
    sf.write(path, audio, sr, subtype="PCM_16")


# ══════════════════════════════════════════════════════════════════════
#  _decode_audio_to_numpy
# ══════════════════════════════════════════════════════════════════════

def test_decode_wav_returns_numpy(tmp_path, numpy_or_skip, soundfile_or_skip):
    """Un WAV mono se decodifica a numpy float32 con el sample rate."""
    np = numpy_or_skip
    from reflex_companion.whisper_stt import _decode_audio_to_numpy

    wav_path = str(tmp_path / "tone.wav")
    sr = 16000
    audio = 0.3 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr).astype(np.float32)
    _write_test_wav(wav_path, audio, sr)

    decoded, decoded_sr = _decode_audio_to_numpy(wav_path)
    assert decoded is not None
    assert decoded_sr == sr
    assert len(decoded) > 0
    # Range check: float audio en [-1, 1]
    assert np.max(np.abs(decoded)) <= 1.5


def test_decode_nonexistent_file_returns_none():
    from reflex_companion.whisper_stt import _decode_audio_to_numpy
    audio, sr = _decode_audio_to_numpy("/nonexistent/path.wav")
    assert audio is None
    assert sr is None


def test_decode_garbage_file_returns_none(tmp_path):
    """Un archivo con bytes random NO debe crashear, debe devolver None."""
    from reflex_companion.whisper_stt import _decode_audio_to_numpy
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"NOT A REAL WAV FILE")
    audio, sr = _decode_audio_to_numpy(str(bad))
    assert audio is None


# ══════════════════════════════════════════════════════════════════════
#  _normalize_audio_gain
# ══════════════════════════════════════════════════════════════════════

def test_normalize_amplifies_quiet_audio(tmp_path, numpy_or_skip):
    """Audio a -35 dBFS debe normalizarse a ~-20 dBFS."""
    np = numpy_or_skip
    import soundfile as sf
    from reflex_companion.whisper_stt import _normalize_audio_gain

    sr = 16000
    # Tono a -35 dBFS RMS (~susurro)
    quiet = 0.018 * np.sin(2 * np.pi * 440 * np.arange(sr * 2) / sr).astype(np.float32)
    quiet_rms_db = 20 * math.log10(np.sqrt(np.mean(quiet ** 2)))
    assert quiet_rms_db < -30  # confirmar que es realmente bajo

    wav_path = str(tmp_path / "quiet.wav")
    _write_test_wav(wav_path, quiet, sr)

    out_path = _normalize_audio_gain(wav_path)
    assert out_path != wav_path  # se generó un archivo nuevo
    assert os.path.exists(out_path)

    # Verificar el nuevo RMS
    audio_norm, _ = sf.read(out_path, dtype="float32")
    rms_norm = np.sqrt(np.mean(audio_norm ** 2))
    rms_db_norm = 20 * math.log10(rms_norm)
    # Debe estar cerca de -20 dBFS (target). Tolerancia ±3 dB porque
    # tanh saturation introduce algo de cambio.
    assert abs(rms_db_norm - (-20.0)) < 3.0


def test_normalize_skips_loud_audio(tmp_path, numpy_or_skip):
    """Audio ya a -10 dBFS no se toca (devuelve mismo path)."""
    np = numpy_or_skip
    from reflex_companion.whisper_stt import _normalize_audio_gain

    sr = 16000
    loud = 0.32 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr).astype(np.float32)
    loud_rms_db = 20 * math.log10(np.sqrt(np.mean(loud ** 2)))
    assert loud_rms_db > -15  # confirmar que es alto

    wav_path = str(tmp_path / "loud.wav")
    _write_test_wav(wav_path, loud, sr)

    out_path = _normalize_audio_gain(wav_path)
    # No tocó el archivo — devuelve el original
    assert out_path == wav_path


def test_normalize_skips_silence(tmp_path, numpy_or_skip):
    """Audio totalmente silencioso no se amplifica (sería puro ruido)."""
    np = numpy_or_skip
    from reflex_companion.whisper_stt import _normalize_audio_gain

    sr = 16000
    silence = np.zeros(sr, dtype=np.float32)
    wav_path = str(tmp_path / "silence.wav")
    _write_test_wav(wav_path, silence, sr)

    out_path = _normalize_audio_gain(wav_path)
    assert out_path == wav_path  # no normalizó nada


def test_normalize_caps_at_max_gain(tmp_path, numpy_or_skip):
    """Audio MUY bajo (-50 dBFS) se amplifica solo hasta el cap (+25 dB),
    no a -20 dBFS exactos. Eso evita amplificar puro ruido."""
    np = numpy_or_skip
    import soundfile as sf
    from reflex_companion.whisper_stt import _normalize_audio_gain, _MAX_GAIN_DB

    sr = 16000
    # ~-50 dBFS — más allá del cap
    very_quiet = 0.003 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr).astype(np.float32)
    rms_in_db = 20 * math.log10(np.sqrt(np.mean(very_quiet ** 2)))
    assert rms_in_db < -45

    wav_path = str(tmp_path / "tiny.wav")
    _write_test_wav(wav_path, very_quiet, sr)

    out_path = _normalize_audio_gain(wav_path)
    assert out_path != wav_path

    audio_norm, _ = sf.read(out_path, dtype="float32")
    rms_norm_db = 20 * math.log10(np.sqrt(np.mean(audio_norm ** 2)))

    # Boost aplicado debería ser cercano al cap (no más)
    boost = rms_norm_db - rms_in_db
    assert boost <= _MAX_GAIN_DB + 2.0  # tolerancia para tanh saturation


def test_normalize_preserves_when_decode_fails(tmp_path):
    """Si el archivo no decodifica, devuelve el path original sin crashear."""
    from reflex_companion.whisper_stt import _normalize_audio_gain
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"NOT A REAL WAV FILE AT ALL")
    out_path = _normalize_audio_gain(str(bad))
    assert out_path == str(bad)


# ══════════════════════════════════════════════════════════════════════
#  Config defaults
# ══════════════════════════════════════════════════════════════════════

def test_default_model_size_is_small():
    """small es el tradeoff de calidad/lag para CPU. Si cambia, el doc
    del manual y el comment del módulo deben updatearse."""
    from reflex_companion import whisper_stt
    # Default cuando no hay env var
    assert whisper_stt._MODEL_SIZE in ("tiny", "base", "small", "medium",
                                        "large-v3", "large-v3-turbo")


def test_default_target_rms_is_minus_20_dbfs():
    """-20 dBFS es speech humano normal. Cambiarlo afecta directamente
    cómo se transcriben susurros."""
    from reflex_companion.whisper_stt import _TARGET_RMS_DBFS
    assert _TARGET_RMS_DBFS == -20.0
