"""Tests para reflex_companion/memory.py.

Cubre I/O atómico, helpers de format y validation. NO cubre las funciones
LLM-driven (extract_facts, generate_diary_entry) — esas requieren mock
del Grok client; un smoke test aparte iría en tests/test_grok_*.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from reflex_companion import memory
from reflex_companion.memory import (
    DIARY_KEYWORDS,
    ensure_facts,
    ensure_ids,
    format_diary,
    format_facts,
    is_diary_query,
    load_json,
    now_iso,
    save_json,
)


# ══════════════════════════════════════════════════════════════════════
#  load_json / save_json — atomicidad y recuperación
# ══════════════════════════════════════════════════════════════════════

def test_load_missing_file_returns_default(tmp_path):
    path = str(tmp_path / "nope.json")
    assert load_json(path, []) == []
    assert load_json(path, {"x": 1}) == {"x": 1}


def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "data.json")
    data = {"hello": "world", "list": [1, 2, 3]}
    save_json(path, data)
    assert load_json(path, None) == data


def test_save_creates_parent_directory(tmp_path):
    """Si el path tiene un dir padre que no existe, lo crea."""
    path = str(tmp_path / "subdir" / "data.json")
    save_json(path, [1, 2, 3])
    assert os.path.exists(path)


def test_save_writes_bak_after_first_save(tmp_path):
    """Tras 2 saves, el .bak existe con la versión anterior."""
    path = str(tmp_path / "data.json")
    save_json(path, {"version": 1})
    save_json(path, {"version": 2})
    assert os.path.exists(path + ".bak")
    # .bak tiene la versión anterior
    with open(path + ".bak", "r", encoding="utf-8") as f:
        bak_data = json.load(f)
    assert bak_data == {"version": 1}


def test_save_invalid_data_does_not_corrupt_file(tmp_path):
    """Si data no es JSON-serializable, el archivo original no se toca."""
    path = str(tmp_path / "data.json")
    save_json(path, {"valid": 1})
    # Intentar guardar algo no-serializable
    with pytest.raises(TypeError):
        save_json(path, {"bad": object()})
    # Original intacto
    assert load_json(path, None) == {"valid": 1}


def test_load_recovers_from_bak_when_main_corrupt(tmp_path):
    """Si el archivo principal está corrupto (no JSON), load lo recupera del .bak."""
    path = str(tmp_path / "data.json")
    save_json(path, {"good": True})
    save_json(path, {"good": True, "v": 2})  # crea .bak con {"good": True}

    # Corromper el principal
    with open(path, "w") as f:
        f.write("{ this is not valid json")

    # load_json debe usar el .bak
    loaded = load_json(path, None)
    assert loaded == {"good": True}


def test_load_returns_default_when_both_corrupt(tmp_path):
    """Si principal y .bak están corruptos, devuelve default y no crashea."""
    path = str(tmp_path / "data.json")
    with open(path, "w") as f:
        f.write("garbage")
    with open(path + ".bak", "w") as f:
        f.write("also garbage")

    assert load_json(path, "fallback") == "fallback"


# ══════════════════════════════════════════════════════════════════════
#  Helpers de tiempo y validación
# ══════════════════════════════════════════════════════════════════════

def test_now_iso_returns_parseable_iso():
    iso = now_iso()
    parsed = datetime.fromisoformat(iso)
    # debe ser timezone-aware (UTC)
    assert parsed.tzinfo is not None


def test_now_iso_is_utc():
    iso = now_iso()
    parsed = datetime.fromisoformat(iso)
    assert parsed.tzinfo == timezone.utc


def test_ensure_ids_adds_id_to_legacy_messages():
    msgs = [{"role": "user", "content": "hi", "timestamp": "2026-01-01T00:00:00"}]
    ensure_ids(msgs)
    assert "id" in msgs[0]
    assert msgs[0]["id"].startswith("legacy-")


def test_ensure_ids_preserves_existing_id():
    msgs = [{"id": "abc-123", "role": "user", "content": "hi"}]
    ensure_ids(msgs)
    assert msgs[0]["id"] == "abc-123"


def test_ensure_ids_adds_image_field():
    msgs = [{"role": "user", "content": "hi"}]
    ensure_ids(msgs)
    assert msgs[0]["image"] == ""


def test_ensure_facts_adds_default_importancia():
    facts = [{"hecho": "Mathieu coding", "categoria": "work"}]
    ensure_facts(facts)
    assert facts[0]["importancia"] == "5"


def test_ensure_facts_preserves_existing_importancia():
    facts = [{"hecho": "x", "categoria": "y", "importancia": "9"}]
    ensure_facts(facts)
    assert facts[0]["importancia"] == "9"


# ══════════════════════════════════════════════════════════════════════
#  Format helpers
# ══════════════════════════════════════════════════════════════════════

def test_format_facts_empty():
    assert "Ningún" in format_facts([])


def test_format_facts_groups_by_category():
    facts = [
        {"hecho": "le gusta el cine", "categoria": "gustos", "importancia": "5"},
        {"hecho": "tiene un gato", "categoria": "vida", "importancia": "5"},
        {"hecho": "ve sci-fi", "categoria": "gustos", "importancia": "7"},
    ]
    out = format_facts(facts)
    assert "[GUSTOS]" in out
    assert "[VIDA]" in out
    # gustos juntos
    assert out.index("le gusta") < out.index("tiene un gato") or \
           out.index("ve sci-fi") < out.index("tiene un gato")


def test_format_facts_sorts_by_importance():
    """Dentro de una categoría, los más importantes van primero."""
    facts = [
        {"hecho": "fact A", "categoria": "x", "importancia": "3"},
        {"hecho": "fact B", "categoria": "x", "importancia": "9"},
    ]
    out = format_facts(facts)
    # B (importancia 9) debe ir antes que A (importancia 3)
    assert out.index("fact B") < out.index("fact A")


def test_format_diary_empty():
    assert "Sin entradas" in format_diary([])


def test_format_diary_returns_last_n():
    entries = [
        {"fecha": "2026-04-25", "resumen": "lunes"},
        {"fecha": "2026-04-26", "resumen": "martes"},
        {"fecha": "2026-04-27", "resumen": "miércoles"},
        {"fecha": "2026-04-28", "resumen": "jueves"},
    ]
    out = format_diary(entries, limit=2)
    # Solo los últimos 2
    assert "miércoles" in out
    assert "jueves" in out
    assert "lunes" not in out


# ══════════════════════════════════════════════════════════════════════
#  is_diary_query — heurística de detección de queries sobre el diario
# ══════════════════════════════════════════════════════════════════════

def test_is_diary_query_detects_keywords():
    assert is_diary_query("¿qué hablamos ayer?")
    assert is_diary_query("recuerdas cuando hicimos X")
    assert is_diary_query("la semana pasada me dijiste...")


def test_is_diary_query_false_for_unrelated():
    assert not is_diary_query("hola, ¿cómo estás?")
    assert not is_diary_query("ponme música")


def test_is_diary_query_case_insensitive():
    assert is_diary_query("¿QUÉ HABLAMOS AYER?")


def test_diary_keywords_well_defined():
    """Smoke check del set de keywords. Si añadimos uno nuevo, este test
    se puede actualizar para asegurar que la lista no quedó muy corta."""
    assert len(DIARY_KEYWORDS) >= 10
    # Incluye los más comunes
    assert "ayer" in DIARY_KEYWORDS
    assert any("semana" in k for k in DIARY_KEYWORDS)
