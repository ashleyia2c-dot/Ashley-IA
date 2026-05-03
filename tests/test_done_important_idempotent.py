"""Guards de idempotencia end-to-end para `done_important` (v0.17.3).

Bug observado: Ashley re-emite [action:done_important:X] varias veces sobre
el mismo item entre turns, y el user veía 3-4 burbujas "Marcado como hecho"
duplicadas. Causa: mark_important_done devolvía el mismo mensaje cada vez.

Fix:
  1. mark_important_done devuelve "" si el item ya estaba done (señal noop)
  2. actions.py propaga noop=True en el dict de resultado
  3. _execute_and_record_action en reflex_companion.py salta el append al
     chat + el log_action_result si result["noop"] is True

Estos tests bloquean regresión de cualquiera de las tres capas.
"""

import os
from pathlib import Path

import pytest

from reflex_companion import reminders
from reflex_companion.actions import execute_action

ROOT = Path(__file__).resolve().parent.parent
REFLEX_PY = ROOT / "reflex_companion" / "reflex_companion.py"
ACTIONS_PY = ROOT / "reflex_companion" / "actions.py"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: reminders.mark_important_done devuelve "" en noop
# (cubierto en test_reminders.py — aquí solo guardamos lectura del símbolo)
# ─────────────────────────────────────────────────────────────────────────────


def test_reminders_module_has_idempotent_marker():
    """El docstring de mark_important_done documenta el contrato noop."""
    src = (ROOT / "reflex_companion" / "reminders.py").read_text(encoding="utf-8")
    assert "mark_important_done" in src
    # Buscar el comportamiento documentado
    assert 'return ""' in src or "return ''" in src, (
        "mark_important_done debe devolver string vacío para señalar noop "
        "cuando el item ya estaba marcado como hecho."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: actions.py propaga noop=True
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """Aislar archivos JSON a tmp_path por test."""
    monkeypatch.setattr(reminders, "REMINDERS_FILE", str(tmp_path / "rec.json"))
    monkeypatch.setattr(reminders, "IMPORTANT_FILE", str(tmp_path / "imp.json"))


def test_execute_action_done_important_noop_flag_first_call_false():
    """Primer call sobre item pendiente: noop=False, mensaje no vacío."""
    reminders.add_important("Task A")

    result = execute_action("done_important", ["Task A"])
    assert result["success"] is True
    assert result["result"] != ""
    assert result.get("noop") is False, (
        f"Primer call (item pendiente) NO es noop. Got: {result!r}"
    )


def test_execute_action_done_important_noop_flag_second_call_true():
    """Segundo call sobre el mismo item: noop=True, mensaje vacío."""
    reminders.add_important("Task A")

    # Mark first time
    execute_action("done_important", ["Task A"])

    # Re-emit on same item
    result = execute_action("done_important", ["Task A"])
    assert result["success"] is True, (
        "noop sigue siendo success=True (la operación 'tuvo éxito' "
        "en el sentido de que la lista refleja lo que Ashley quería)"
    )
    assert result["result"] == "", (
        f"Segundo call sobre item ya done debe tener result vacío. Got: {result!r}"
    )
    assert result.get("noop") is True, (
        f"Segundo call debe marcar noop=True. Got: {result!r}"
    )


def test_execute_action_done_important_unknown_item_not_noop():
    """Item desconocido: NO es noop — muestra 'No encontré' al user."""
    reminders.add_important("Real task")

    result = execute_action("done_important", ["totally_unrelated"])
    assert result["success"] is True
    assert result["result"] != ""
    assert "no encontr" in result["result"].lower()
    assert result.get("noop") is False, (
        "Item no encontrado NO es noop — Ashley debe ver el mensaje "
        "'no encontré' para no insistir."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: _execute_and_record_action salta chat append en noop
# ─────────────────────────────────────────────────────────────────────────────


def test_execute_and_record_action_skips_noop_append_to_chat():
    """El método _execute_and_record_action debe saltar el append al chat
    cuando result.get('noop') is True. Esto se verifica leyendo el código
    fuente — no podemos instanciar el State de Reflex en un test unitario
    sin tirar de toda la app."""
    src = REFLEX_PY.read_text(encoding="utf-8")

    # Buscar la sección del método
    assert "_execute_and_record_action" in src

    # Buscar el early return basado en noop
    # Patrón esperado: dentro del método, antes del messages.append, hay un
    # check `if result.get("noop"): return result`
    import re
    method_match = re.search(
        r"def _execute_and_record_action\(self[\s\S]+?(?=\n    def \w|\nclass )",
        src,
    )
    assert method_match, "No encontré el método _execute_and_record_action"
    method_body = method_match.group(0)

    # El check de noop debe aparecer ANTES del append al chat
    noop_check_idx = method_body.find('result.get("noop")')
    assert noop_check_idx != -1, (
        "Falta check `result.get('noop')` en _execute_and_record_action. "
        "Sin esto las acciones no-op (ej: done_important sobre item ya hecho) "
        "siguen generando burbujas duplicadas en el chat."
    )

    append_idx = method_body.find("self.messages.append")
    assert append_idx != -1, "No encontré messages.append en el método"
    assert noop_check_idx < append_idx, (
        "El check de noop debe ir ANTES del append al chat. "
        f"noop check at {noop_check_idx}, append at {append_idx}."
    )

    # Y debe haber un return tras el check de noop
    # Buscamos en una ventana cerrada a noop_check_idx
    window = method_body[noop_check_idx:noop_check_idx + 200]
    assert "return result" in window, (
        "El check de noop debe ir seguido de `return result` (early exit) "
        "para evitar el append + log."
    )


def test_actions_py_done_important_propagates_noop():
    """actions.py debe propagar noop=True basado en el retorno de mark_important_done."""
    src = ACTIONS_PY.read_text(encoding="utf-8")
    # Buscar el handler de done_important
    import re
    handler_match = re.search(
        r'elif action_type == "done_important":[\s\S]+?(?=elif action_type|$)',
        src,
    )
    assert handler_match, "No encontré el handler de done_important en actions.py"
    handler = handler_match.group(0)

    # Debe propagar noop
    assert '"noop"' in handler or "'noop'" in handler, (
        "El handler de done_important debe propagar el flag 'noop' al dict "
        "de resultado. Sin esto _execute_and_record_action no sabe que "
        "saltar el append."
    )
