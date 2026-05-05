"""Guards para sistema de cumpleaños / fechas importantes (v0.18.0 Fase 2).

Sistema separado de "important items" (one-time todos) porque las fechas
importantes son ANUALES recurrentes — el cumpleaños del jefe se repite cada
año, no es un item que se marca como done.

Tests cubren:
  1. CRUD básico de important_dates
  2. Matching today / upcoming (con wrap de año)
  3. Validación de fechas (formatos, Feb 29, etc.)
  4. Anti-duplicado (mismo type + who + MM-DD)
  5. Action handler (save_date) extremo a extremo
  6. Parser de [action:save_date:...]
  7. i18n strings
  8. Cache prefix preservado tras añadir la sección
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from reflex_companion import important_dates as ids_mod
from reflex_companion.actions import execute_action
from reflex_companion.parsing import _SAFE_ACTIONS, extract_action


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """Aislar IMPORTANT_DATES_FILE a tmp_path por test."""
    monkeypatch.setattr(
        ids_mod, "IMPORTANT_DATES_FILE",
        str(tmp_path / "fechas_importantes.json"),
    )


# ─────────────────────────────────────────────
#  CRUD básico
# ─────────────────────────────────────────────


def test_load_empty_returns_empty_list():
    """Sin archivo previo → lista vacía."""
    assert ids_mod.load_dates() == []


def test_add_birthday_user_basic():
    entry = ids_mod.add_date(
        type_="birthday", date_str="1995-03-15", label="user", who="user",
    )
    assert entry is not None
    assert entry["type"] == "birthday"
    assert entry["date"] == "1995-03-15"
    assert entry["label"] == "user"
    assert "id" in entry
    assert "created_at" in entry


def test_add_anniversary_with_md_only():
    """Permitir MM-DD sin año (recurrencia anual sin necesidad de año específico)."""
    entry = ids_mod.add_date(
        type_="anniversary", date_str="08-30", label="bodas con María",
    )
    assert entry is not None
    assert entry["date"] == "08-30"


def test_add_invalid_date_returns_none():
    """Date mal formateada → None, no rompe."""
    assert ids_mod.add_date("birthday", "not-a-date", "user") is None
    assert ids_mod.add_date("birthday", "2025-13-99", "user") is None


def test_add_empty_label_rejected():
    """Sin label, no se guarda — Ashley necesita saber QUÉ es."""
    assert ids_mod.add_date("birthday", "03-15", "") is None
    assert ids_mod.add_date("birthday", "03-15", None) is None


def test_invalid_type_normalized_to_event():
    """Type fuera de VALID_TYPES → 'event' (no rechaza, normaliza)."""
    entry = ids_mod.add_date("randomthing", "03-15", "test")
    assert entry["type"] == "event"


def test_add_date_anti_duplicate_updates_label():
    """Mismo type + who + MM-DD → no duplica, actualiza label."""
    e1 = ids_mod.add_date("birthday", "1995-03-15", "Mathieu", who="user")
    e2 = ids_mod.add_date("birthday", "03-15", "El Jefe", who="user")
    assert e1["id"] == e2["id"]  # mismo id, no se creó nuevo
    assert e2["label"] == "El Jefe"  # label actualizado
    assert len(ids_mod.load_dates()) == 1


def test_add_date_year_upgrade_when_provided():
    """Si primero se guarda MM-DD y luego YYYY-MM-DD del mismo evento,
    upgrade el date al formato con año (no pierde info)."""
    ids_mod.add_date("birthday", "03-15", "user")
    ids_mod.add_date("birthday", "1995-03-15", "user")
    items = ids_mod.load_dates()
    assert len(items) == 1
    assert items[0]["date"] == "1995-03-15"


def test_remove_date_by_id():
    e = ids_mod.add_date("birthday", "03-15", "user")
    assert ids_mod.remove_date(e["id"]) is True
    assert ids_mod.load_dates() == []


def test_remove_unknown_id_returns_false():
    assert ids_mod.remove_date("nonexistent") is False


# ─────────────────────────────────────────────
#  Matching today / upcoming
# ─────────────────────────────────────────────


def test_get_today_dates_match_md():
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-04", "user")
    ids_mod.add_date("birthday", "06-15", "mom")
    found = ids_mod.get_today_dates(today=today)
    assert len(found) == 1
    assert found[0]["label"] == "user"


def test_get_today_dates_works_with_yyyy_mm_dd():
    """Matching anual debe funcionar aun cuando date guardado tiene año."""
    today = date(2026, 3, 15)
    ids_mod.add_date("birthday", "1995-03-15", "user")  # del año 1995
    found = ids_mod.get_today_dates(today=today)
    assert len(found) == 1


def test_get_today_dates_empty_when_no_match():
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "01-01", "user")
    assert ids_mod.get_today_dates(today=today) == []


def test_get_upcoming_dates_within_7_days():
    today = date(2026, 5, 4)
    # Mañana + en 7 días
    ids_mod.add_date("birthday", "05-05", "tomorrow_birthday")
    ids_mod.add_date("birthday", "05-11", "in_seven_days")
    # 8 días → fuera del rango
    ids_mod.add_date("birthday", "05-12", "in_eight_days")
    upcoming = ids_mod.get_upcoming_dates(days_ahead=7, today=today)
    labels = [u["label"] for u in upcoming]
    assert "tomorrow_birthday" in labels
    assert "in_seven_days" in labels
    assert "in_eight_days" not in labels


def test_get_upcoming_includes_days_until():
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-05", "tomorrow")
    ids_mod.add_date("birthday", "05-08", "in_4_days")
    upcoming = ids_mod.get_upcoming_dates(days_ahead=7, today=today)
    by_label = {u["label"]: u["days_until"] for u in upcoming}
    assert by_label["tomorrow"] == 1
    assert by_label["in_4_days"] == 4


def test_get_upcoming_sorted_by_days_until():
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-09", "in_5_days")
    ids_mod.add_date("birthday", "05-05", "in_1_day")
    ids_mod.add_date("birthday", "05-07", "in_3_days")
    upcoming = ids_mod.get_upcoming_dates(days_ahead=7, today=today)
    assert [u["days_until"] for u in upcoming] == [1, 3, 5]


def test_get_upcoming_handles_year_wrap():
    """Si hoy es 28 dic, en 7 días incluye 03 ene del año siguiente."""
    today = date(2026, 12, 28)
    ids_mod.add_date("birthday", "01-03", "new_year_baby")
    upcoming = ids_mod.get_upcoming_dates(days_ahead=7, today=today)
    assert any(u["label"] == "new_year_baby" for u in upcoming)


def test_get_upcoming_excludes_today():
    """Las dates de HOY van en today_dates, NO en upcoming."""
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-04", "today_one")
    upcoming = ids_mod.get_upcoming_dates(days_ahead=7, today=today)
    assert all(u["label"] != "today_one" for u in upcoming)


# ─────────────────────────────────────────────
#  Format for prompt
# ─────────────────────────────────────────────


def test_format_for_prompt_empty_when_no_data():
    """Sin datos relevantes → string vacío (importante para cache)."""
    today = date(2026, 5, 4)
    assert ids_mod.format_dates_for_prompt(today=today) == ""


def test_format_for_prompt_today_only():
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-04", "user")
    out = ids_mod.format_dates_for_prompt(today=today, lang="es")
    assert "HOY" in out
    assert "user" in out
    assert "cumpleaños" in out


def test_format_for_prompt_includes_upcoming():
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-08", "test_in_4_days")
    out = ids_mod.format_dates_for_prompt(today=today, lang="es")
    assert "PRÓXIMOS" in out
    assert "test_in_4_days" in out
    assert "4" in out  # número de días


def test_format_for_prompt_lang_fallback():
    """Lang desconocido → cae a EN sin crashear."""
    today = date(2026, 5, 4)
    ids_mod.add_date("birthday", "05-04", "user")
    out = ids_mod.format_dates_for_prompt(today=today, lang="zh")
    assert "TODAY" in out  # fallback EN


# ─────────────────────────────────────────────
#  Parser de [action:save_date:...]
# ─────────────────────────────────────────────


def test_parser_extracts_save_date_three_params():
    text, action = extract_action(
        "Vale jefe, lo guardo. [action:save_date:birthday:1995-03-15:user]"
    )
    assert action is not None
    assert action["type"] == "save_date"
    assert action["params"] == ["birthday", "1995-03-15", "user"]


def test_parser_save_date_with_label_containing_spaces():
    text, action = extract_action(
        "[action:save_date:anniversary:08-30:bodas con María]"
    )
    assert action["params"] == ["anniversary", "08-30", "bodas con María"]


def test_parser_save_date_md_only():
    text, action = extract_action("[action:save_date:birthday:06-12:mamá]")
    assert action["params"] == ["birthday", "06-12", "mamá"]


# ─────────────────────────────────────────────
#  Safe action listing
# ─────────────────────────────────────────────


def test_save_date_is_safe_action():
    """save_date debe estar en _SAFE_ACTIONS — es solo guardar datos,
    no requiere toggle Acciones."""
    assert "save_date" in _SAFE_ACTIONS


# ─────────────────────────────────────────────
#  Action handler (execute_action) end-to-end
# ─────────────────────────────────────────────


def test_execute_save_date_birthday_user():
    result = execute_action(
        "save_date", ["birthday", "1995-03-15", "user"]
    )
    assert result["success"] is True
    assert "Fecha guardada" in result["result"]
    # Verificar que se guardó
    items = ids_mod.load_dates()
    assert len(items) == 1
    assert items[0]["type"] == "birthday"


def test_execute_save_date_invalid_returns_failure():
    """Date mal formateada → success=False con mensaje de error."""
    result = execute_action("save_date", ["birthday", "garbage", "user"])
    assert result["success"] is False
    assert "invalid" in result["result"].lower()


def test_execute_save_date_infers_user_from_label():
    """Si label es 'user'/'jefe'/'boss' → who se infiere como 'user'."""
    execute_action("save_date", ["birthday", "03-15", "user"])
    items = ids_mod.load_dates()
    assert items[0]["who"] == "user"


def test_execute_save_date_third_party_uses_label_as_who():
    """Si label NO es marcador de user → who = label en lowercase."""
    execute_action("save_date", ["birthday", "06-12", "mamá"])
    items = ids_mod.load_dates()
    assert items[0]["who"] == "mamá"


# ─────────────────────────────────────────────
#  Cache prefix sigue intacto tras añadir sección
# ─────────────────────────────────────────────


def test_cache_prefix_preserved_with_dates_section():
    """El prompt con important_dates section debe seguir teniendo cache prefix
    >=95% entre dos llamadas que solo difieren en hora."""
    import os
    os.environ.setdefault("XAI_API_KEY", "dummy")
    from reflex_companion.prompts_es import build_system_prompt

    facts = [{"hecho": "Vive en Barcelona", "categoria": "x",
              "relevancia": "permanente", "importancia": "8"}]

    p1 = build_system_prompt(
        facts=facts, diary=[],
        time_context="14:23 del 4 mayo",
        important_dates="⭐ HOY:\n  - cumpleaños del jefe (cumpleaños)",
    )
    p2 = build_system_prompt(
        facts=facts, diary=[],
        time_context="14:24 del 4 mayo",
        important_dates="⭐ HOY:\n  - cumpleaños del jefe (cumpleaños)",
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
        f"Cache prefix solo {ratio*100:.1f}% tras añadir important_dates_section. "
        f"Debe seguir >=95%."
    )


def test_dates_section_appears_in_dynamic_bottom_es():
    """La sección de dates debe estar DESPUÉS de los principios."""
    import os
    os.environ.setdefault("XAI_API_KEY", "dummy")
    from reflex_companion.prompts_es import build_system_prompt

    prompt = build_system_prompt(
        facts=[], diary=[],
        important_dates="⭐ HOY:\n  - test_event (event)",
    )
    principles_idx = prompt.find("PRINCIPIOS DE CONEXIÓN")
    dates_idx = prompt.find("FECHAS IMPORTANTES")
    assert dates_idx > 0
    assert dates_idx > principles_idx, (
        "FECHAS IMPORTANTES debe ir DESPUÉS de PRINCIPIOS para preservar cache"
    )


# ─────────────────────────────────────────────
#  Validación date format internal
# ─────────────────────────────────────────────


def test_parse_date_to_md_yyyy_mm_dd():
    assert ids_mod._parse_date_to_md("1995-03-15") == "03-15"


def test_parse_date_to_md_md_only():
    assert ids_mod._parse_date_to_md("03-15") == "03-15"


def test_parse_date_to_md_invalid():
    assert ids_mod._parse_date_to_md("garbage") is None
    assert ids_mod._parse_date_to_md("") is None
    assert ids_mod._parse_date_to_md(None) is None


def test_validate_md_accepts_feb_29():
    """Feb 29 es válido (años bisiestos). El matching anual lo respeta."""
    assert ids_mod._validate_md("02-29") is True


def test_validate_md_rejects_invalid_dates():
    assert ids_mod._validate_md("13-01") is False  # mes 13
    assert ids_mod._validate_md("02-30") is False  # 30 feb
    assert ids_mod._validate_md("garbage") is False


def test_extract_year_yyyy_mm_dd():
    assert ids_mod._extract_year("1995-03-15") == 1995
    assert ids_mod._extract_year("03-15") is None
