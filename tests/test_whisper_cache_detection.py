"""Tests para la detección del cache del modelo Whisper en disco.

Antes el backend solo verificaba is_loaded() (modelo en RAM). Si el
modelo estaba descargado en disco pero NO en RAM (caso típico al primer
uso por sesión), devolvía 'downloading' al frontend → user veía
'Descargando 245 MB' aunque el modelo ya estuviera ahí desde hace
sesiones. Confuso y frustrante.

v0.16.13 introduce is_cached_on_disk() que detecta si los archivos del
modelo existen, y separa 'downloading' (primera descarga) vs 'loading'
(en disco, cargando a RAM).
"""

import os
import tempfile

import pytest


# ══════════════════════════════════════════════════════════════════════
#  is_cached_on_disk() detecta correctamente
# ══════════════════════════════════════════════════════════════════════


class TestIsCachedOnDisk:

    def test_returns_false_when_no_files(self, tmp_path, monkeypatch):
        """Si la carpeta del modelo está vacía, devolver False."""
        monkeypatch.setenv("ASHLEY_DATA_DIR", str(tmp_path))
        # Recargar módulo para que pille la nueva env var
        import importlib
        from reflex_companion import whisper_stt
        importlib.reload(whisper_stt)
        assert whisper_stt.is_cached_on_disk() is False

    def test_returns_false_when_partial_files(self, tmp_path, monkeypatch):
        """Si solo hay algunos archivos (ej. download interrumpido), False."""
        monkeypatch.setenv("ASHLEY_DATA_DIR", str(tmp_path))
        import importlib
        from reflex_companion import whisper_stt
        importlib.reload(whisper_stt)

        # Crear solo model.bin pero NO los otros
        cache_dir = whisper_stt._cache_dir()
        local_dir = os.path.join(
            cache_dir,
            f"models--Systran--faster-whisper-{whisper_stt._MODEL_SIZE}-direct",
        )
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, "model.bin"), "wb") as f:
            f.write(b"x" * 1000)
        # No creamos config.json, tokenizer.json ni vocabulary.txt
        assert whisper_stt.is_cached_on_disk() is False

    def test_returns_false_when_files_empty(self, tmp_path, monkeypatch):
        """Si los archivos existen pero están vacíos (0 bytes — symlink
        roto en Windows sin Developer Mode), devolver False."""
        monkeypatch.setenv("ASHLEY_DATA_DIR", str(tmp_path))
        import importlib
        from reflex_companion import whisper_stt
        importlib.reload(whisper_stt)

        cache_dir = whisper_stt._cache_dir()
        local_dir = os.path.join(
            cache_dir,
            f"models--Systran--faster-whisper-{whisper_stt._MODEL_SIZE}-direct",
        )
        os.makedirs(local_dir, exist_ok=True)
        for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
            open(os.path.join(local_dir, name), "wb").close()  # 0 bytes
        assert whisper_stt.is_cached_on_disk() is False

    def test_returns_true_when_all_files_present_with_content(self, tmp_path, monkeypatch):
        """Si todos los archivos esperados existen con contenido, True."""
        monkeypatch.setenv("ASHLEY_DATA_DIR", str(tmp_path))
        import importlib
        from reflex_companion import whisper_stt
        importlib.reload(whisper_stt)

        cache_dir = whisper_stt._cache_dir()
        local_dir = os.path.join(
            cache_dir,
            f"models--Systran--faster-whisper-{whisper_stt._MODEL_SIZE}-direct",
        )
        os.makedirs(local_dir, exist_ok=True)
        for name in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
            with open(os.path.join(local_dir, name), "wb") as f:
                f.write(b"placeholder content")
        assert whisper_stt.is_cached_on_disk() is True


# ══════════════════════════════════════════════════════════════════════
#  api_routes distingue 'downloading' vs 'loading'
# ══════════════════════════════════════════════════════════════════════


class TestApiRoutesDistinguishesStates:
    """El endpoint /api/transcribe debe mandar 'loading' (no 'downloading')
    cuando el modelo está en disco pero no en RAM."""

    def test_api_routes_imports_is_cached_on_disk(self):
        """El módulo api_routes debe importar is_cached_on_disk del
        módulo whisper_stt — sin esto, no puede distinguir los 2 estados."""
        from pathlib import Path
        api_src = (
            Path(__file__).resolve().parent.parent
            / "reflex_companion" / "api_routes.py"
        ).read_text(encoding="utf-8")
        assert "is_cached_on_disk" in api_src, (
            "api_routes.py no usa is_cached_on_disk — sigue mostrando "
            "'descargando 245 MB' aunque el modelo ya esté en disco."
        )

    def test_api_routes_returns_loading_status(self):
        """El endpoint debe devolver 'loading' (no 'downloading') cuando
        is_cached_on_disk() es True."""
        from pathlib import Path
        api_src = (
            Path(__file__).resolve().parent.parent
            / "reflex_companion" / "api_routes.py"
        ).read_text(encoding="utf-8")
        assert '"status": "loading"' in api_src, (
            "El endpoint /api/transcribe no devuelve status='loading' "
            "cuando el modelo está en disco. Sin esto el user ve "
            "'Descargando 245 MB' en cada primera vez por sesión."
        )


class TestPrewarmIncludesWhisper:
    """_prewarm_session_state debe lanzar el load del modelo Whisper en
    background para que la primera transcripción sea instantánea."""

    def test_prewarm_loads_whisper(self):
        from pathlib import Path
        src = (
            Path(__file__).resolve().parent.parent
            / "reflex_companion" / "reflex_companion.py"
        ).read_text(encoding="utf-8")
        # Buscar referencia al pre-warm de whisper en _prewarm_session_state
        assert "_do_whisper_warmup" in src or "whisper_stt" in src, (
            "_prewarm_session_state no carga el modelo Whisper en background. "
            "Sin esto el user ve 'Cargando modelo...' la primera vez que "
            "active voz por sesión (~5-15s)."
        )
