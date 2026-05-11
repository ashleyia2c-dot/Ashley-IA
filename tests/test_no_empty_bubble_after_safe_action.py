"""Tests para v0.18.5 — Burbuja vacía después de acciones safe/conversacionales.

Bug histórico (v0.18.5): después de que Ashley emitía
`[action:check_in_goal:...]` aparecía una burbuja vacía después del
system message del check-in.

Causa raíz: la "agentic continuation" (v0.14.4) disparaba un follow-up
turn para CUALQUIER ejecución single-action, incluso conversacionales
(check_in_goal, save_taste, save_goal). El LLM, al ser preguntado "¿algo
más?", respondía "no, ya está" → texto vacío → bubble vacía.

NOTA v0.19.32: la agentic continuation se desactivó por completo (ver
test_v0_19_31_fixes.py::TestAgenticContinuationDisabled). El bug original
de bubble vacía YA NO PUEDE OCURRIR porque la continuation jamás se
dispara — los tests del root cause se eliminaron por obsoletos.

Lo que SÍ permanece útil: las defensas en profundidad que verifican que
los 3 paths que appendean assistant message tras strippear tags
(continuation, blocked-followup, apology) no appendeen contenido vacío.
Aunque la continuation no se dispare, el código sigue ahí (por si se
re-habilita) y los otros 2 paths (blocked-followup, apology) se siguen
ejecutando — sus guardas siguen valiendo.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


@pytest.fixture(scope="module")
def rc_source() -> str:
    return RC_FILE.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  DEFENSA EN PROFUNDIDAD: Skipear append si content vacío
# ════════════════════════════════════════════════════════════════════════


class TestNoEmptyMessageAppend:
    """Los 3 paths que appendean assistant message tras strippear tags
    deben verificar que el contenido no esté vacío antes de appendear."""

    def test_continuation_path_guards_empty(self, rc_source):
        """_stream_action_continuation: el append está envuelto en
        `if display_content and display_content.strip()`."""
        # Buscar el bloque que asigna display_content y luego appendea
        pattern = re.compile(
            r"display_content\s*=\s*_clean_display_fn\(ct_clean\).*?"
            r"if\s+display_content\s+and\s+display_content\.strip\(\)",
            re.DOTALL,
        )
        assert pattern.search(rc_source), (
            "_stream_action_continuation debe verificar que display_content "
            "no esté vacío antes de hacer self.messages.append. Sin esta "
            "guarda, si el LLM responde con solo whitespace o solo un tag, "
            "se appendea bubble vacía."
        )

    def test_blocked_followup_path_guards_empty(self, rc_source):
        """Path de action blocked followup: `ft_display` se chequea antes
        del append."""
        pattern = re.compile(
            r"ft_display\s*=\s*_clean_display_fn\(ft_clean\).*?"
            r"if\s+ft_display\s+and\s+ft_display\.strip\(\)",
            re.DOTALL,
        )
        assert pattern.search(rc_source), (
            "El path de action_blocked_followup debe verificar `ft_display` "
            "antes del append, mismo patrón que el continuation path."
        )

    def test_apology_path_guards_empty(self, rc_source):
        """Path de apology tras failure: `ap_display` se chequea antes
        del append."""
        pattern = re.compile(
            r"ap_display\s*=\s*_clean_display_fn\(ap_clean\).*?"
            r"if\s+ap_display\s+and\s+ap_display\.strip\(\)",
            re.DOTALL,
        )
        assert pattern.search(rc_source), (
            "El path de apology tras failure debe verificar `ap_display` "
            "antes del append, mismo patrón que continuation y blocked."
        )


