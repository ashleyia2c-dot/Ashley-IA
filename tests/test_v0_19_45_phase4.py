"""Regression tests para v0.19.45 FASE 4 — prompts anti-ambigüedad +
inyección de tabs+URLs en system state vía CDP.

User pidió:
  • "que si no sabe que abrir que pida al usuario que especifique no
    que actue tontamente abriendo algo sin sentido"
  • "opera envia datos de todo lo que esta abierto en ese momento asi
    que ella deberia saber todo eso"

Fixes:
  1. Regla anti-ambigüedad en prompts ES/EN/FR: si nombre corto/ambiguo,
     PREGUNTA en vez de adivinar (especial mención del bug "abre et").
  2. `get_system_state(prefer_cdp=True)` enriquece con tabs+URLs vía
     CDP cuando está disponible. Permite a Ashley targetear acciones
     con precisión ("el video de warcraft está en la tab youtube.com/
     watch?v=XYZ" en vez de adivinar).
  3. Cache por turno separa el bucket CDP del UIA (toggle CDP a mitad
     de sesión se refleja correctamente).
"""
import re
from pathlib import Path
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  Anti-ambigüedad en prompts (3 idiomas + el alias para los 4 que
#  hacen fallback a EN)
# ════════════════════════════════════════════════════════════════════════


class TestPromptsAntiAmbiguity:
    def test_es_has_anti_ambiguity_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_es.py").read_text(
            encoding="utf-8",
        )
        assert "REGLA ANTI-AMBIGÜEDAD" in src or "ANTI-AMBIGÜEDAD" in src
        # Caso específico del bug del user
        assert '"et"' in src or "abre et" in src.lower()

    def test_en_has_anti_ambiguity_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_en.py").read_text(
            encoding="utf-8",
        )
        assert "ANTI-AMBIGUITY" in src.upper()
        assert "open et" in src.lower() or '"et"' in src

    def test_fr_has_anti_ambiguity_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_fr.py").read_text(
            encoding="utf-8",
        )
        assert "ANTI-AMBIGUÏTÉ" in src.upper() or "ANTI AMBIGUITE" in src.upper()

    def test_anti_ambiguity_mentions_short_names(self):
        """La regla debe mencionar explícitamente nombres CORTOS como
        problemáticos (ej. 'et', 'vs', 1-3 letras)."""
        src = (REPO_ROOT / "reflex_companion" / "prompts_es.py").read_text(
            encoding="utf-8",
        )
        assert "1-3" in src or "corto" in src.lower() or "letras" in src.lower()

    def test_anti_ambiguity_says_to_ask(self):
        """Debe decir explícitamente PREGUNTAR, no adivinar."""
        src = (REPO_ROOT / "reflex_companion" / "prompts_es.py").read_text(
            encoding="utf-8",
        )
        # En ES "preguntar" / "PREGUNTA"
        idx = src.find("ANTI-AMBIGÜEDAD")
        if idx == -1:
            pytest.fail("ANTI-AMBIGÜEDAD no encontrada")
        section = src[idx:idx + 1500]
        assert "PREGUNTA" in section or "pregunta" in section.lower()


# ════════════════════════════════════════════════════════════════════════
#  get_system_state(prefer_cdp=True) — tabs con URL vía CDP
# ════════════════════════════════════════════════════════════════════════


class TestGetSystemStateWithCDP:
    def test_get_system_state_accepts_prefer_cdp_param(self):
        """v0.19.45 — get_system_state ahora acepta `prefer_cdp` kwarg."""
        from reflex_companion.actions import get_system_state
        import inspect
        sig = inspect.signature(get_system_state)
        assert "prefer_cdp" in sig.parameters

    def test_browser_tabs_via_cdp_helper_exists(self):
        """Existe `_get_browser_tabs_via_cdp` que devuelve [{title,url}, ...]."""
        from reflex_companion.actions import _get_browser_tabs_via_cdp
        # Sin CDP disponible debe devolver [] (no crashear)
        with patch("reflex_companion.browser_cdp.is_cdp_available",
                   return_value=False):
            assert _get_browser_tabs_via_cdp() == []

    def test_browser_tabs_via_cdp_returns_title_url_dicts(self):
        from reflex_companion.actions import _get_browser_tabs_via_cdp
        fake_tabs = [
            {"id": "1", "title": "YouTube", "url": "https://youtube.com",
             "type": "page"},
            {"id": "2", "title": "Worker", "url": "...", "type": "service_worker"},
            {"id": "3", "title": "Twitter", "url": "https://twitter.com",
             "type": "page"},
        ]
        with patch("reflex_companion.browser_cdp.is_cdp_available",
                   return_value=True), \
             patch("reflex_companion.browser_cdp.list_tabs",
                   return_value=fake_tabs):
            result = _get_browser_tabs_via_cdp()
        # Solo type='page' deben aparecer
        assert len(result) == 2
        assert all("title" in t and "url" in t for t in result)

    def test_get_system_state_includes_url_when_cdp_available(self):
        """Cuando hay CDP, el output del estado debe incluir URLs."""
        from reflex_companion.actions import get_system_state
        fake_cdp_tabs = [{
            "id": "1", "type": "page",
            "title": "Warcraft 3 stream", "url": "https://youtube.com/watch?v=abc12345678",
        }]
        with patch("reflex_companion.browser_cdp.is_cdp_available",
                   return_value=True), \
             patch("reflex_companion.browser_cdp.list_tabs",
                   return_value=fake_cdp_tabs):
            output = get_system_state(prefer_cdp=True)
        assert "youtube.com/watch?v=abc12345678" in output, (
            "Output debe incluir la URL completa para que Ashley pueda "
            "targetear acciones con precisión"
        )
        assert "vía CDP" in output

    def test_get_system_state_falls_back_to_uia_without_cdp(self):
        """Sin CDP, debe usar UIA fallback (comportamiento original)."""
        from reflex_companion.actions import get_system_state
        with patch("reflex_companion.browser_cdp.is_cdp_available",
                   return_value=False), \
             patch("reflex_companion.actions._get_browser_tabs_via_uia",
                   return_value=["Some tab"]):
            output = get_system_state(prefer_cdp=False)
        assert "Some tab" in output
        # NO debe decir "vía CDP" porque no se usó
        assert "vía CDP" not in output

    def test_get_system_state_default_no_cdp(self):
        """Default `prefer_cdp=False` mantiene compatibilidad backward."""
        from reflex_companion.actions import get_system_state
        import inspect
        sig = inspect.signature(get_system_state)
        assert sig.parameters["prefer_cdp"].default is False


# ════════════════════════════════════════════════════════════════════════
#  Cache separado por bucket (CDP vs UIA)
# ════════════════════════════════════════════════════════════════════════


class TestCacheBucketsSeparate:
    """v0.19.45 — el cache del state debe tener buckets separados para
    CDP y UIA. Si el user toggle CDP, el siguiente turn debe re-fetch."""

    def test_cached_system_state_uses_separate_keys(self):
        """Smoke test: el método _cached_system_state debe usar keys
        distintas para CDP vs UIA."""
        rc_src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        # Buscar las dos cache keys
        assert '"system_state_cdp"' in rc_src
        assert '"system_state_uia"' in rc_src
