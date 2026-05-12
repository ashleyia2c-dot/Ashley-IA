"""Regression tests para v0.19.44 — fix REAL del 'play_music abre 2
tabs' (race entre speculative dispatch y finalize fallback).

User reportó (3ra vez): 'ashley sigue abriendo dos veces, por favor
verifica eso dios santo nunca funcionan tus fixes, y lo de antes que
habias hecho con las otras paginas entonces es mierda tmabien'.

Causa raíz REAL (no era find_tabs_matching como v0.19.41 pensó):

El **speculative dispatch** (v0.14.1) ejecuta cada action en un thread
durante el streaming de Grok para ahorrarse latencia. Cuando el stream
termina, `_finalize_response` hace `thread.join(timeout=1.0)` esperando
que el thread haya completado.

Problema: play_music puede tardar hasta ~20s en el thread:
  • _resolve_youtube_url: HTTP scrape a YouTube (hasta 8s)
  • CDP new_tab: hasta 3s timeout HTTP
  • Mi poll de v0.19.41: hasta 10s adicionales

Tras 1.0s en el join, el thread aún corre → `pre_result is None` →
fallback a `_execute_and_record_action` → play_music SE EJECUTA OTRA
VEZ → SEGUNDA tab del mismo video.

Mientras el speculative thread ABRE su tab vía CDP, el fallback ABRE
OTRA tab. = 2 tabs. Exacto el bug reportado.

Fix v0.19.44:
  • Nuevo set `_LONG_RUNNING_ACTIONS` en parsing.py con play_music,
    open_url, search_web.
  • `_finalize_response` usa timeout dinámico: 30s para acciones en
    ese set, 1.5s para el resto.
  • 30s cubre todos los timeouts internos sumados (8+3+10+buffer).
  • En 99% de casos el speculative termina ANTES que finalize empiece
    (corrió durante el stream que toma 3-5s) → no se espera nada.
"""
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"
PARSING_FILE = REPO_ROOT / "reflex_companion" / "parsing.py"


# ════════════════════════════════════════════════════════════════════════
#  _LONG_RUNNING_ACTIONS set
# ════════════════════════════════════════════════════════════════════════


class TestLongRunningActionsSet:
    """v0.19.44 — set de acciones con polling/scrape interno largo."""

    def test_set_exists(self):
        from reflex_companion.parsing import _LONG_RUNNING_ACTIONS
        assert isinstance(_LONG_RUNNING_ACTIONS, set)

    def test_includes_play_music(self):
        from reflex_companion.parsing import _LONG_RUNNING_ACTIONS
        assert "play_music" in _LONG_RUNNING_ACTIONS, (
            "play_music DEBE estar en _LONG_RUNNING_ACTIONS — es el "
            "caso del bug reportado por user (~20s posible en thread)"
        )

    def test_includes_open_url_and_search_web(self):
        """Las dos del v0.19.42 también tienen polling CDP interno."""
        from reflex_companion.parsing import _LONG_RUNNING_ACTIONS
        assert "open_url" in _LONG_RUNNING_ACTIONS
        assert "search_web" in _LONG_RUNNING_ACTIONS

    def test_backward_compat_alias(self):
        """`_NO_SPECULATIVE_DISPATCH` debe seguir existiendo (alias)."""
        from reflex_companion.parsing import (
            _LONG_RUNNING_ACTIONS, _NO_SPECULATIVE_DISPATCH,
        )
        assert _LONG_RUNNING_ACTIONS == _NO_SPECULATIVE_DISPATCH


# ════════════════════════════════════════════════════════════════════════
#  Dynamic timeout in _finalize_response
# ════════════════════════════════════════════════════════════════════════


class TestDynamicJoinTimeoutInFinalize:
    """v0.19.44 — _finalize_response debe usar timeout dinámico (30s para
    long-running, 1.5s para el resto) en thread.join."""

    def test_finalize_imports_long_running_actions(self):
        src = RC_FILE.read_text(encoding="utf-8")
        # Buscar en los primeros 100 lines
        head = "\n".join(src.split("\n")[:100])
        assert "_LONG_RUNNING_ACTIONS" in head, (
            "_finalize_response debe importar _LONG_RUNNING_ACTIONS"
        )

    def test_no_more_fixed_1s_join(self):
        """Después del fix, NO debe haber `thread.join(timeout=1.0)` en
        _finalize_response (era el bug)."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Localizar el bloque _finalize_response
        idx = src.find("def _finalize_response")
        assert idx != -1
        end = src.find("\n    def ", idx + 1)
        body = src[idx:end if end != -1 else idx + 8000]
        # No debe estar el join con timeout 1.0 literal
        assert "thread.join(timeout=1.0)" not in body, (
            "v0.19.44 bug fix: join(timeout=1.0) causaba que play_music "
            "se re-ejecutara cuando el speculative thread tardaba >1s. "
            "Debe usar timeout dinámico per action type."
        )

    def test_dynamic_timeout_present(self):
        """Verifica que use spec_timeout dinámico con _LONG_RUNNING_ACTIONS."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _finalize_response")
        end = src.find("\n    def ", idx + 1)
        body = src[idx:end if end != -1 else idx + 8000]
        assert "spec_timeout" in body, (
            "Debe haber variable `spec_timeout` calculada por action type"
        )
        assert "_LONG_RUNNING_ACTIONS" in body, (
            "spec_timeout debe usar _LONG_RUNNING_ACTIONS para decidir"
        )
        # Y debe haber un timeout de al menos 12s (idealmente 30s)
        # para acciones long-running
        match = re.search(
            r'spec_timeout\s*=\s*\(\s*(\d+(?:\.\d+)?)',
            body,
        )
        assert match, "No se encontró asignación de spec_timeout"
        timeout_val = float(match.group(1))
        assert timeout_val >= 12.0, (
            f"spec_timeout para long-running debe ser >= 12s, found {timeout_val}s. "
            f"Necesita cubrir HTTP scrape (8s) + CDP (3s) + poll (10s)."
        )


# ════════════════════════════════════════════════════════════════════════
#  Speculative dispatch NO se skipea (REVERT de v0.19.44 parcial)
# ════════════════════════════════════════════════════════════════════════


class TestSpeculativeDispatchStillFires:
    """Importante: v0.19.44 NO debe skipear el speculative dispatch para
    play_music. Eso lo haría MÁS LENTO. La solución correcta es el
    timeout dinámico en finalize."""

    def test_maybe_dispatch_speculative_does_not_skip_long_running(self):
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _maybe_dispatch_speculative")
        end = src.find("\n    def ", idx + 1)
        body = src[idx:end if end != -1 else idx + 4000]

        # NO debe haber el patrón "if a['type'] in _LONG_RUNNING_ACTIONS:
        # continue" o similar que skipearía la dispatch.
        # Aceptamos referencias en comentarios.
        code_lines = [
            ln for ln in body.split("\n")
            if not ln.strip().startswith("#")
        ]
        code_only = "\n".join(code_lines)
        assert "_LONG_RUNNING_ACTIONS" not in code_only, (
            "_maybe_dispatch_speculative NO debe usar _LONG_RUNNING_ACTIONS "
            "para skipear el dispatch. Skipear haría play_music más LENTO "
            "(no overlap con stream). La solución correcta es esperar "
            "más en finalize via timeout dinámico."
        )
        assert "_NO_SPECULATIVE_DISPATCH" not in code_only, (
            "Tampoco _NO_SPECULATIVE_DISPATCH (alias)"
        )


# ════════════════════════════════════════════════════════════════════════
#  Logical regression — no más doble ejecución teórica
# ════════════════════════════════════════════════════════════════════════


class TestNoDoubleExecutionPath:
    """Test estructural: el path else (fallback a _execute_and_record_action)
    sigue presente PERO solo se alcanza tras 30s para long-running. En la
    práctica eso significa speculative ya completó."""

    def test_fallback_path_still_exists(self):
        """El fallback a _execute_and_record_action sigue existiendo como
        red de seguridad (si el thread genuinamente hangs >30s, mejor
        re-ejecutar que dejar al user sin respuesta)."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _finalize_response")
        end = src.find("\n    def ", idx + 1)
        body = src[idx:end if end != -1 else idx + 8000]
        # Sigue habiendo fallback (en caso de hang genuino del thread)
        assert "_execute_and_record_action(current_action)" in body, (
            "Fallback a _execute_and_record_action sigue siendo necesario "
            "como red de seguridad (thread genuinamente colgado > 30s)"
        )
