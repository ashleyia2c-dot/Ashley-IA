"""Tests para v0.18.5 — Burbuja vacía después de acciones safe/conversacionales.

Bug reportado por user (con screenshot): después de que Ashley dijo
"¿Qué tal si hoy me cuentas cómo va ese goal de mejorar mi voz? Me intriga
de verdad. 💕" y emitió `[action:check_in_goal:mejorar voz Ashley]`, el
sistema mostraba:

  [Ashley message con texto + corazoncito]
  [✿ Check-in registrado: 'mejorar voz Ashley'.]
  [BURBUJA VACÍA de Ashley]  ← BUG

Causa raíz: la "agentic continuation" (v0.14.4) se diseñó para planes
multi-step donde Ashley ejecuta una system action (open_app, etc.) y
luego necesita ver el [system_result] para emitir el siguiente paso. Esa
heurística (`executed_count == 1 and not any_failed`) disparaba la
continuación incluso para acciones safe/conversacionales como
`check_in_goal`, `save_taste`, `save_goal`, etc., donde Ashley YA dijo
todo lo que tenía que decir en su mensaje principal. El LLM, al ser
preguntado "¿algo más?", correctamente respondía "no, ya está" → texto
vacío → bubble vacía en UI.

Doble fix:
1. Skipear `_stream_action_continuation` si TODAS las acciones ejecutadas
   fueron safe/conversacionales (root cause).
2. Defensa en profundidad: en los 3 paths que appendean assistant message
   tras strippear tags (continuation, blocked-followup, apology),
   verificar que el contenido limpio no esté vacío antes de appendear.
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
#  ROOT CAUSE: Continuation skippeada para safe actions
# ════════════════════════════════════════════════════════════════════════


class TestContinuationSkipsSafeActions:
    def test_should_continue_checks_safe_actions(self, rc_source):
        """should_continue debe excluir el caso donde todas las acciones
        ejecutadas son SAFE (conversacionales)."""
        assert "all_safe_conversational" in rc_source, (
            "Falta el chequeo `all_safe_conversational` en should_continue. "
            "Sin esto, la agentic continuation se dispara para acciones "
            "puramente conversacionales (check_in_goal, save_taste, etc.) "
            "y produce burbujas vacías cuando el LLM correctamente decide "
            "no añadir nada."
        )

    def test_uses_safe_actions_set(self, rc_source):
        """El chequeo debe consultar `_SAFE_ACTIONS` (no una lista hardcoded
        local que se desincroniza)."""
        # Buscamos el patrón exacto del chequeo
        assert "_SAFE_ACTIONS" in rc_source, (
            "El chequeo de all_safe_conversational debe usar el set "
            "_SAFE_ACTIONS importado de parsing.py."
        )

    def test_check_excludes_continuation(self, rc_source):
        """should_continue debe tener la condición `not all_safe_conversational`
        — si está pero no se usa, no protege."""
        assert "not all_safe_conversational" in rc_source, (
            "should_continue debe tener `not all_safe_conversational` como "
            "una de sus condiciones AND. Sin esto, el chequeo se calcula "
            "pero no impide la continuación → bubble vacío sigue."
        )


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


# ════════════════════════════════════════════════════════════════════════
#  Smoke test: la lógica all_safe_conversational opera sobre lista correcta
# ════════════════════════════════════════════════════════════════════════


class TestSafeConversationalLogic:
    """Verifica que la implementación use el campo correcto del dict
    executed_results (cada entry es {"action": {...}, "result": {...}})."""

    def test_extracts_action_type_correctly(self, rc_source):
        """El chequeo debe extraer `r.get("action", {}).get("type")` —
        coincide con el shape definido en el código que appendea a
        executed_results."""
        # Patrón flexible — permite diferentes estilos pero debe acceder
        # a action.type de cada result.
        assert re.search(
            r'r\.get\("action".*?\)\.get\("type"\)',
            rc_source,
        ) or re.search(
            r"r\['action'\]\['type'\]",
            rc_source,
        ), (
            "El chequeo de all_safe_conversational debe extraer el "
            "action type de cada entry. El shape de executed_results es "
            "[{\"action\": {\"type\": ...}, \"result\": ...}, ...]."
        )
