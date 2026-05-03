"""Tests para el fix definitivo del Bug 2 (v0.16.14) — root cause:
UnicodeEncodeError en Windows cmd cp1252.

Caso real diagnosticado: Ashley generaba una respuesta normal con caracteres
ASCII puros, pero MIS PROPIOS DIAGNÓSTICOS de logging incluían `→` (→)
en el format string. Cuando Python intentaba escribir a stdout/stderr,
Windows cmd con codepage 1252 (charmap) NO PUEDE encodear ese carácter →
UnicodeEncodeError. La excepción se atrapaba silenciosamente en
`_send_message_impl`'s try/except, disparando `_handle_grok_error` que
añadía un mensaje de error al chat ("Algo falló: 'charmap' codec...").

El user veía la "respuesta" (que era el mensaje de error en realidad)
pero el observer SÍ detectaba el cambio (27→28). Por eso TTS leía el
mensaje de error en lugar de la respuesta real de Ashley.

Fix: PYTHONIOENCODING=utf-8 en el env del spawn de Reflex desde
electron/main.js. Esto fuerza a Python a usar UTF-8 para stdin/stdout/
stderr regardless of the terminal codepage. Cubre TODOS los prints/logs
sin necesidad de sanitizar cada string.

Sin este fix, cualquier emoji o carácter no-ASCII (que el LLM puede generar
en cualquier momento) en un print/log podría romper la app.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ELECTRON_MAIN = REPO_ROOT / "electron" / "main.js"
RC_PY = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


@pytest.fixture(scope="module")
def main_js() -> str:
    return ELECTRON_MAIN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rc_src() -> str:
    return RC_PY.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  PYTHONIOENCODING en el spawn de Reflex
# ════════════════════════════════════════════════════════════════════════


class TestPythonIOEncoding:
    """electron/main.js DEBE pasar PYTHONIOENCODING=utf-8 al spawn de
    Reflex en TODAS las rutas (split y single)."""

    def test_split_process_sets_utf8(self, main_js):
        """_startSplitProcesses spawn de Reflex debe tener
        PYTHONIOENCODING: 'utf-8'."""
        # Buscar el bloque del spawn de reflex en split path
        # No buscamos el frontend (sirv) porque es node, no python
        # El reflex spawn es el primer spawn con XAI_API_KEY en split
        spawn_blocks = re.findall(
            r"spawn\([^)]+\)[\s\S]*?env:\s*\{[\s\S]*?\}",
            main_js,
        )
        # Al menos uno debe contener XAI_API_KEY (es python/reflex)
        py_blocks = [b for b in spawn_blocks if "XAI_API_KEY" in b]
        assert py_blocks, "No se localizó ningún spawn con XAI_API_KEY"
        for block in py_blocks:
            assert "PYTHONIOENCODING" in block, (
                "Un spawn de Python (con XAI_API_KEY) NO tiene "
                "PYTHONIOENCODING en su env. Sin esto, Python en Windows "
                "cmd cp1252 lanza UnicodeEncodeError al imprimir/loguear "
                "caracteres no-ASCII (→, emojis, é, etc.) y la excepción "
                "rompe _finalize_response."
            )
            assert "utf-8" in block.lower(), (
                "PYTHONIOENCODING está pero su valor no es 'utf-8'."
            )


# ════════════════════════════════════════════════════════════════════════
#  Sanity: el código del backend NO tiene prints con non-ASCII (defensa)
# ════════════════════════════════════════════════════════════════════════


class TestBackendDoesNotPrintNonASCII:
    """Defensa en profundidad: aunque PYTHONIOENCODING fix esto, evitamos
    introducir prints/logs con non-ASCII en reflex_companion.py para que
    si el fix se rompe (alguien quita el env var), no volvemos al bug."""

    def test_no_arrow_in_print_statements(self, rc_src):
        """No debe haber `→` (\\u2192) dentro de print() en el código.
        Es el carácter exacto que rompió la app en el bug original."""
        # Buscar print( con → adentro
        # Regex: print\([^)]*→[^)]*\)
        bad = re.findall(r"print\([^)]*→[^)]*\)", rc_src)
        assert not bad, (
            f"Se detectaron print() con '→' (\\u2192). Esto rompe Windows "
            f"cmd cp1252. Aunque PYTHONIOENCODING=utf-8 lo arregla, mantén "
            f"los prints en ASCII puro como defensa. Casos: {bad[:3]}"
        )

    def test_no_arrow_in_logging_calls(self, rc_src):
        """Igual para logger calls (logging.info, logger.warning, etc.)."""
        bad = re.findall(
            r"(?:logger|logging|_log|_dbg)\.\w+\([^)]*→[^)]*\)",
            rc_src,
        )
        assert not bad, (
            f"Se detectaron logger calls con '→'. Mantén formats en ASCII. "
            f"Casos: {bad[:3]}"
        )


# ════════════════════════════════════════════════════════════════════════
#  Doc: el comentario explica el motivo del env var
# ════════════════════════════════════════════════════════════════════════


class TestDocumentedReason:
    """Si alguien intenta quitar PYTHONIOENCODING en el futuro porque parece
    superfluo, el comentario debe explicar el motivo bug-real."""

    def test_main_js_explains_pythonioencoding(self, main_js):
        """electron/main.js debe documentar POR QUÉ se setea
        PYTHONIOENCODING."""
        # Buscar el comentario referenciando charmap o cp1252
        has_comment = (
            "charmap" in main_js.lower() or
            "cp1252" in main_js.lower() or
            "UnicodeEncodeError" in main_js
        )
        assert has_comment, (
            "PYTHONIOENCODING está sin un comentario que explique POR QUÉ. "
            "Sin contexto, alguien puede quitar el env var y volver el bug."
        )
