"""Guards para sistema de goals / objetivos a largo plazo (v0.18.0 Fase 3).

Sistema separado de important items (one-time todos) y important dates
(eventos recurrentes) porque los goals son OBJETIVOS DE LARGO PLAZO con
progreso continuo: aprender un idioma, correr 5k, lanzar un producto.

Tests cubren:
  1. CRUD básico (add, complete, check_in)
  2. Anti-duplicado de goals activos
  3. Idempotencia (mismo pattern que done_important)
  4. Detección de goals "due for check-in"
  5. format_goals_for_prompt en 3 idiomas
  6. Parser de actions (save_goal/check_in_goal/complete_goal)
  7. Action handlers end-to-end
  8. Cache prefix preservado tras añadir sección
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from reflex_companion import goals as goals_mod
from reflex_companion.actions import execute_action
from reflex_companion.parsing import _SAFE_ACTIONS, extract_action


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(
        goals_mod, "GOALS_FILE",
        str(tmp_path / "objetivos.json"),
    )


# ─────────────────────────────────────────────
#  CRUD básico
# ─────────────────────────────────────────────


def test_load_empty_returns_empty_list():
    assert goals_mod.load_goals() == []


def test_add_goal_basic():
    g = goals_mod.add_goal("Aprender francés", category="aprendizaje")
    assert g is not None
    assert g["goal"] == "Aprender francés"
    assert g["category"] == "aprendizaje"
    assert g["completed"] is False
    assert g["completed_at"] is None
    assert g["last_check_in"] is None
    assert "id" in g
    assert "created_at" in g


def test_add_goal_default_category():
    g = goals_mod.add_goal("test")
    assert g["category"] == "personal"


def test_add_goal_empty_text_rejected():
    assert goals_mod.add_goal("") is None
    assert goals_mod.add_goal("   ") is None
    assert goals_mod.add_goal(None) is None


def test_add_goal_anti_duplicate_active():
    """Mismo texto activo → no crea duplicado, devuelve el existente."""
    g1 = goals_mod.add_goal("Aprender francés")
    g2 = goals_mod.add_goal("Aprender francés")
    assert g1["id"] == g2["id"]
    assert len(goals_mod.load_goals()) == 1


def test_add_goal_anti_duplicate_case_insensitive():
    g1 = goals_mod.add_goal("Aprender Francés")
    g2 = goals_mod.add_goal("aprender francés")
    assert g1["id"] == g2["id"]


def test_add_goal_duplicate_after_complete_allowed():
    """Si un goal está completado, permitir crear nuevo con mismo texto (renew)."""
    g1 = goals_mod.add_goal("Correr 5K")
    goals_mod.complete_goal(g1["id"])
    g2 = goals_mod.add_goal("Correr 5K")
    assert g1["id"] != g2["id"]
    assert len(goals_mod.load_goals()) == 2  # uno completado, uno nuevo


# ─────────────────────────────────────────────
#  complete_goal
# ─────────────────────────────────────────────


def test_complete_goal_by_id():
    g = goals_mod.add_goal("Test goal")
    msg = goals_mod.complete_goal(g["id"])
    assert "completado" in msg.lower() or "Test goal" in msg
    items = goals_mod.load_goals()
    assert items[0]["completed"] is True
    assert items[0]["completed_at"] is not None


def test_complete_goal_by_text_substring():
    goals_mod.add_goal("Aprender francés intermedio")
    msg = goals_mod.complete_goal("francés")
    assert msg != ""
    assert goals_mod.load_goals()[0]["completed"] is True


def test_complete_goal_already_done_returns_empty_noop():
    """Idempotente: completar un goal ya completado → "" (noop signal)."""
    g = goals_mod.add_goal("Test")
    goals_mod.complete_goal(g["id"])
    msg2 = goals_mod.complete_goal(g["id"])
    assert msg2 == "", f"Expected noop signal, got: {msg2!r}"


def test_complete_goal_not_found_returns_message():
    goals_mod.add_goal("Real goal")
    msg = goals_mod.complete_goal("nonexistent")
    assert msg != ""
    assert "no encontr" in msg.lower()


# ─────────────────────────────────────────────
#  mark_check_in
# ─────────────────────────────────────────────


def test_check_in_updates_last_check_in():
    g = goals_mod.add_goal("Test")
    assert g["last_check_in"] is None
    msg = goals_mod.mark_check_in(g["id"])
    assert "registrado" in msg.lower() or "Test" in msg
    items = goals_mod.load_goals()
    assert items[0]["last_check_in"] is not None


def test_check_in_idempotent_within_6h():
    """Si Ashley hace check-in 2 veces en mismo turn, segunda vez = noop."""
    g = goals_mod.add_goal("Test")
    goals_mod.mark_check_in(g["id"])
    msg2 = goals_mod.mark_check_in(g["id"])
    assert msg2 == "", "Segundo check-in dentro 6h debe ser noop"


def test_check_in_not_found_returns_message():
    goals_mod.add_goal("Real")
    msg = goals_mod.mark_check_in("nonexistent")
    assert msg != ""
    assert "no encontr" in msg.lower()


# ─────────────────────────────────────────────
#  Queries
# ─────────────────────────────────────────────


def test_get_active_goals_excludes_completed():
    g1 = goals_mod.add_goal("Active one")
    g2 = goals_mod.add_goal("Completed one")
    goals_mod.complete_goal(g2["id"])
    actives = goals_mod.get_active_goals()
    assert len(actives) == 1
    assert actives[0]["goal"] == "Active one"


def test_get_recent_completed_goals():
    g1 = goals_mod.add_goal("First completed")
    g2 = goals_mod.add_goal("Second completed")
    goals_mod.complete_goal(g1["id"])
    goals_mod.complete_goal(g2["id"])
    recent = goals_mod.get_recent_completed_goals(limit=5)
    assert len(recent) == 2


def test_days_since_check_in_none_when_never():
    g = goals_mod.add_goal("Test")
    assert goals_mod.days_since_check_in(g) is None


def test_days_since_check_in_recent():
    g = goals_mod.add_goal("Test")
    goals_mod.mark_check_in(g["id"])
    items = goals_mod.load_goals()
    days = goals_mod.days_since_check_in(items[0])
    assert days == 0


def test_is_due_for_check_in_old_creation_no_check_in():
    """Goal creado hace >10 días sin nunca check-in → due."""
    g = goals_mod.add_goal("Old goal")
    items = goals_mod.load_goals()
    # Forzar created_at hace 15 días
    items[0]["created_at"] = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    goals_mod.save_goals(items)
    assert goals_mod.is_due_for_check_in(items[0]) is True


def test_is_due_for_check_in_recent_creation_not_due():
    """Goal recién creado (hace <10 días) sin check-in → NO due (grace period)."""
    g = goals_mod.add_goal("Fresh goal")
    items = goals_mod.load_goals()
    assert goals_mod.is_due_for_check_in(items[0]) is False


def test_is_due_for_check_in_recent_check_in_not_due():
    """Goal con check-in reciente → NO due."""
    g = goals_mod.add_goal("Test")
    goals_mod.mark_check_in(g["id"])
    items = goals_mod.load_goals()
    assert goals_mod.is_due_for_check_in(items[0]) is False


def test_is_due_for_check_in_old_check_in_due():
    """Goal con check-in hace >10 días → due."""
    g = goals_mod.add_goal("Test")
    items = goals_mod.load_goals()
    items[0]["last_check_in"] = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    goals_mod.save_goals(items)
    assert goals_mod.is_due_for_check_in(items[0]) is True


# ─────────────────────────────────────────────
#  Format for prompt
# ─────────────────────────────────────────────


def test_format_for_prompt_empty_when_no_goals():
    """Sin goals activos → string vacío (preserva cache)."""
    assert goals_mod.format_goals_for_prompt(lang="es") == ""


def test_format_for_prompt_includes_active_goals():
    goals_mod.add_goal("Aprender francés", category="aprendizaje")
    out = goals_mod.format_goals_for_prompt(lang="es")
    assert "OBJETIVOS" in out
    assert "Aprender francés" in out
    assert "aprendizaje" in out


def test_format_for_prompt_excludes_completed():
    g = goals_mod.add_goal("Completed one")
    goals_mod.complete_goal(g["id"])
    out = goals_mod.format_goals_for_prompt(lang="es")
    assert out == ""


def test_format_for_prompt_marks_due_with_clock():
    """Goals due for check-in deben tener el marcador ⏰."""
    g = goals_mod.add_goal("Old goal")
    items = goals_mod.load_goals()
    items[0]["created_at"] = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    goals_mod.save_goals(items)
    out = goals_mod.format_goals_for_prompt(lang="es")
    assert "⏰" in out


def test_format_for_prompt_no_clock_for_recent_goals():
    goals_mod.add_goal("Fresh goal")
    out = goals_mod.format_goals_for_prompt(lang="es")
    # El marcador en la lista de goals (no contar el del hint footer)
    # El footer del hint también tiene ⏰ explicativo, pero solo 1.
    assert out.count("⏰") <= 1  # solo en el hint, no en goals individuales


def test_format_for_prompt_lang_fallback():
    goals_mod.add_goal("Test")
    out = goals_mod.format_goals_for_prompt(lang="zh")
    assert "GOALS" in out  # fallback EN


def test_format_for_prompt_three_languages():
    """Las 3 langs deben dar output funcional."""
    goals_mod.add_goal("Test goal")
    for lang in ("en", "es", "fr"):
        out = goals_mod.format_goals_for_prompt(lang=lang)
        assert out != ""
        assert "Test goal" in out


# ─────────────────────────────────────────────
#  Parser de acciones
# ─────────────────────────────────────────────


def test_parser_save_goal_basic():
    text, action = extract_action(
        "[action:save_goal:aprendizaje:Aprender francés]"
    )
    assert action["type"] == "save_goal"
    assert action["params"] == ["aprendizaje", "Aprender francés"]


def test_parser_save_goal_text_with_colons():
    """Goal text con colons internos → todo va al segundo param."""
    text, action = extract_action(
        "[action:save_goal:profesional:Lanzar Ashley v1.0: producción]"
    )
    assert action["params"][0] == "profesional"
    assert action["params"][1] == "Lanzar Ashley v1.0: producción"


def test_parser_check_in_goal():
    text, action = extract_action("[action:check_in_goal:abc12345]")
    assert action["type"] == "check_in_goal"
    assert action["params"] == ["abc12345"]


def test_parser_complete_goal():
    text, action = extract_action("[action:complete_goal:Aprender francés]")
    assert action["type"] == "complete_goal"
    assert action["params"] == ["Aprender francés"]


# ─────────────────────────────────────────────
#  Safe actions registry
# ─────────────────────────────────────────────


def test_save_goal_in_safe_actions():
    assert "save_goal" in _SAFE_ACTIONS


def test_check_in_goal_in_safe_actions():
    assert "check_in_goal" in _SAFE_ACTIONS


def test_complete_goal_in_safe_actions():
    assert "complete_goal" in _SAFE_ACTIONS


# ─────────────────────────────────────────────
#  execute_action end-to-end
# ─────────────────────────────────────────────


def test_execute_save_goal():
    result = execute_action("save_goal", ["aprendizaje", "Aprender francés"])
    assert result["success"] is True
    assert "guardado" in result["result"].lower()
    assert len(goals_mod.load_goals()) == 1


def test_execute_save_goal_empty_returns_failure():
    result = execute_action("save_goal", ["aprendizaje", ""])
    assert result["success"] is False


def test_execute_check_in_goal():
    g = goals_mod.add_goal("Test")
    result = execute_action("check_in_goal", [g["id"]])
    assert result["success"] is True
    assert result.get("noop") is not True
    assert "registrado" in result["result"].lower() or "Test" in result["result"]


def test_execute_check_in_goal_idempotent_noop():
    """Segundo check-in en <6h → noop=True."""
    g = goals_mod.add_goal("Test")
    execute_action("check_in_goal", [g["id"]])
    result = execute_action("check_in_goal", [g["id"]])
    assert result.get("noop") is True
    assert result["result"] == ""


def test_execute_complete_goal():
    g = goals_mod.add_goal("Test")
    result = execute_action("complete_goal", [g["id"]])
    assert result["success"] is True
    assert result.get("noop") is not True
    items = goals_mod.load_goals()
    assert items[0]["completed"] is True


def test_execute_complete_goal_already_done_noop():
    g = goals_mod.add_goal("Test")
    execute_action("complete_goal", [g["id"]])
    result = execute_action("complete_goal", [g["id"]])
    assert result.get("noop") is True


# ─────────────────────────────────────────────
#  Cache prefix preservation
# ─────────────────────────────────────────────


def test_cache_prefix_preserved_with_goals_section():
    """El prompt con goals section debe seguir teniendo cache prefix >=95%."""
    import os
    os.environ.setdefault("XAI_API_KEY", "dummy")
    from reflex_companion.prompts_es import build_system_prompt

    facts = [{"hecho": "Vive en Barcelona", "categoria": "x",
              "relevancia": "permanente", "importancia": "8"}]

    p1 = build_system_prompt(
        facts=facts, diary=[],
        time_context="14:23 del 6 mayo",
        goals="OBJETIVOS DEL JEFE (largo plazo):\n  - [aprendizaje] [abc12345] Aprender francés (creado hace 5 días, aún no has preguntado)",
    )
    p2 = build_system_prompt(
        facts=facts, diary=[],
        time_context="14:24 del 6 mayo",
        goals="OBJETIVOS DEL JEFE (largo plazo):\n  - [aprendizaje] [abc12345] Aprender francés (creado hace 5 días, aún no has preguntado)",
    )

    common = 0
    for i, (a, b) in enumerate(zip(p1, p2)):
        if a != b:
            common = i
            break
    else:
        common = min(len(p1), len(p2))

    ratio = common / len(p1)
    assert ratio >= 0.95, (
        f"Cache prefix solo {ratio*100:.1f}% tras añadir goals_section. Debe >=95%."
    )


def test_goals_section_appears_after_principles():
    """La sección de goals debe estar DESPUÉS de los principios."""
    import os
    os.environ.setdefault("XAI_API_KEY", "dummy")
    from reflex_companion.prompts_es import build_system_prompt

    prompt = build_system_prompt(
        facts=[], diary=[],
        goals="OBJETIVOS DEL JEFE (largo plazo):\n  - [test] [abc] Test goal",
    )
    principles_idx = prompt.find("PRINCIPIOS DE CONEXIÓN")
    goals_idx = prompt.find("OBJETIVOS DEL JEFE")
    assert goals_idx > 0
    assert goals_idx > principles_idx, (
        "OBJETIVOS DEL JEFE debe ir DESPUÉS de PRINCIPIOS para preservar cache"
    )


def test_no_goals_no_section_in_prompt():
    """Sin goals → la sección no aparece en el prompt (cero impacto)."""
    import os
    os.environ.setdefault("XAI_API_KEY", "dummy")
    from reflex_companion.prompts_es import build_system_prompt

    prompt = build_system_prompt(facts=[], diary=[], goals=None)
    assert "OBJETIVOS DEL JEFE" not in prompt
