"""
test_whisper.py — Tests para whisper_stt.py.
NO carga el modelo real (sería 245MB). Testa la lógica de control.
"""
import pytest


def test_cache_dir_with_env(monkeypatch, tmp_path):
    """_cache_dir usa ASHLEY_DATA_DIR si está en el env."""
    monkeypatch.setenv("ASHLEY_DATA_DIR", str(tmp_path))
    from reflex_companion.whisper_stt import _cache_dir
    d = _cache_dir()
    assert str(tmp_path) in d
    assert d.endswith("whisper")
    assert os.path.isdir(d)


def test_cache_dir_without_env(monkeypatch):
    """_cache_dir usa ruta relativa si no hay ASHLEY_DATA_DIR."""
    monkeypatch.delenv("ASHLEY_DATA_DIR", raising=False)
    from reflex_companion.whisper_stt import _cache_dir
    d = _cache_dir()
    assert "whisper" in d


def test_is_loaded_initial():
    """El modelo no está cargado al inicio (sin warmup)."""
    from reflex_companion.whisper_stt import is_loaded, is_loading
    # No podemos garantizar el estado global, pero sí que las funciones existen
    assert isinstance(is_loaded(), bool)
    assert isinstance(is_loading(), bool)


def test_load_error_initial():
    """load_error devuelve None o string."""
    from reflex_companion.whisper_stt import load_error
    result = load_error()
    assert result is None or isinstance(result, str)


def test_transcribe_bytes_empty():
    """Audio vacío o muy corto devuelve string vacío (sin cargar modelo)."""
    from reflex_companion.whisper_stt import transcribe_bytes, is_loaded
    if is_loaded():
        # Si el modelo ya está cargado, probar transcripción real con bytes vacíos
        result = transcribe_bytes(b"", language="en")
        assert result == ""
        result = transcribe_bytes(b"x" * 100, language="en")
        assert result == ""
    else:
        # Sin modelo, bytes cortos deben dar vacío (check len < 500)
        result = transcribe_bytes(b"", language="en")
        assert result == ""


import os
