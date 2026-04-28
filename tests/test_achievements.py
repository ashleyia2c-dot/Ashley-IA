"""Tests para reflex_companion/achievements.py.

Cubre:
  - Definiciones (12 logros, todos con campos completos)
  - load/save round-trip con tmp_path
  - unlock_achievement: idempotencia + timestamp
  - is_unlocked / get_achievement_def lookups
  - check_achievements: cada condición real (affection, mensajes, facts,
    vision, mic, actions) dispara el logro correcto
"""

from __future__ import annotations

from datetime import datetime

import pytest

from reflex_companion import achievements
from reflex_companion.achievements import (
    ACHIEVEMENTS,
    check_achievements,
    get_achievement_def,
    is_unlocked,
    load_achievements,
    save_achievements,
    unlock_achievement,
)


# ══════════════════════════════════════════════════════════════════════
#  Definiciones
# ══════════════════════════════════════════════════════════════════════

def test_all_achievements_have_required_fields():
    """Cada logro debe tener id, icon, tier, name_en, name_es, desc_en, desc_es."""
    required = {"id", "icon", "tier", "name_en", "name_es", "desc_en", "desc_es"}
    for ach in ACHIEVEMENTS:
        missing = required - set(ach.keys())
        assert not missing, f"Achievement {ach.get('id', '?')} missing fields: {missing}"


def test_achievement_ids_are_unique():
    """Los ids no se pueden repetir — son la key del dict."""
    ids = [a["id"] for a in ACHIEVEMENTS]
    assert len(ids) == len(set(ids)), "Duplicate achievement ids found"


def test_total_achievements_count():
    """Hay 12 logros documentados (4 affection + 4 mensajes + 4 features).
    Si añadimos más, este test recordatorio fuerza updatear el manual."""
    assert len(ACHIEVEMENTS) == 12, (
        f"Achievements count changed: {len(ACHIEVEMENTS)}. "
        "Update the user manual (manual_content.py) to mention the new ones."
    )


def test_known_tiers():
    """Los tiers usados son affection / messages / features. Si cambia,
    la UI que agrupa por tier puede romper."""
    valid = {"affection", "messages", "features"}
    for ach in ACHIEVEMENTS:
        assert ach["tier"] in valid, f"Unknown tier: {ach['tier']}"


# ══════════════════════════════════════════════════════════════════════
#  Persistence
# ══════════════════════════════════════════════════════════════════════

def test_load_empty_returns_empty_dict(tmp_path, monkeypatch):
    """Si el archivo no existe, load_achievements devuelve {}."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "achievements.json"))
    assert load_achievements() == {}


def test_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    data = {"hello_world": {"unlocked": True, "unlocked_at": "2026-04-28T01:00:00"}}
    save_achievements(data)
    loaded = load_achievements()
    assert loaded == data


# ══════════════════════════════════════════════════════════════════════
#  unlock_achievement
# ══════════════════════════════════════════════════════════════════════

def test_unlock_first_time_returns_true(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    assert unlock_achievement("hello_world") is True
    assert is_unlocked("hello_world")


def test_unlock_second_time_returns_false(tmp_path, monkeypatch):
    """Idempotente: re-unlock devuelve False (ya estaba)."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlock_achievement("hello_world")
    assert unlock_achievement("hello_world") is False


def test_unlock_records_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlock_achievement("chatty")
    data = load_achievements()
    ts = data["chatty"]["unlocked_at"]
    # Parseable como ISO datetime — protege contra format drift
    parsed = datetime.fromisoformat(ts)
    # Y muy reciente
    assert (datetime.now() - parsed).total_seconds() < 5


def test_get_achievement_def_returns_full_dict():
    ach = get_achievement_def("hello_world")
    assert ach is not None
    assert ach["id"] == "hello_world"
    assert ach["tier"] == "messages"


def test_get_achievement_def_unknown_returns_none():
    assert get_achievement_def("nonexistent") is None


# ══════════════════════════════════════════════════════════════════════
#  check_achievements — condiciones reales
# ══════════════════════════════════════════════════════════════════════

def test_check_no_conditions_unlocks_nothing(tmp_path, monkeypatch):
    """Con stats a 0, ningún logro disparable."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=0, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    assert unlocked == []


def test_check_first_message_unlocks_hello_world(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    ids = [a["id"] for a in unlocked]
    assert "hello_world" in ids


def test_check_50_messages_unlocks_chatty_and_hello(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=50, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    ids = {a["id"] for a in unlocked}
    assert {"hello_world", "chatty"}.issubset(ids)


def test_check_500_messages_unlocks_all_message_tiers(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=500, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    ids = {a["id"] for a in unlocked}
    assert {"hello_world", "chatty", "best_friends", "inseparable"}.issubset(ids)


def test_check_affection_thresholds(tmp_path, monkeypatch):
    """Affection 20/40/60/80 = ice_breaker / getting_closer / heartstrings / devoted."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=80, message_count=0, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    ids = {a["id"] for a in unlocked}
    assert {"ice_breaker", "getting_closer", "heartstrings", "devoted"}.issubset(ids)


def test_check_affection_partial_threshold(tmp_path, monkeypatch):
    """Affection 35 → ice_breaker pero no getting_closer (40)."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=35, message_count=0, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    ids = {a["id"] for a in unlocked}
    assert "ice_breaker" in ids
    assert "getting_closer" not in ids


def test_check_facts_5_unlocks_she_remembers(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=0, facts_count=5,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    assert any(a["id"] == "she_remembers" for a in unlocked)


def test_check_facts_4_does_not_unlock_she_remembers(tmp_path, monkeypatch):
    """5 es el threshold — 4 no debería disparar."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=0, facts_count=4,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    assert not any(a["id"] == "she_remembers" for a in unlocked)


def test_check_vision_enabled_unlocks_she_sees(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=0, facts_count=0,
        vision_enabled=True, used_mic=False, executed_action=False,
    )
    assert any(a["id"] == "she_sees" for a in unlocked)


def test_check_mic_unlocks_voice_unlocked(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=0, facts_count=0,
        vision_enabled=False, used_mic=True, executed_action=False,
    )
    assert any(a["id"] == "voice_unlocked" for a in unlocked)


def test_check_action_unlocks_she_acts(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=0, message_count=0, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=True,
    )
    assert any(a["id"] == "she_acts" for a in unlocked)


def test_check_idempotent_does_not_re_unlock(tmp_path, monkeypatch):
    """Llamar check_achievements 2 veces con la misma condición sólo
    devuelve el logro la 1ª vez (la 2ª ya está unlocked)."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    first = check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    second = check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
    )
    assert first  # primera vez disparó
    assert not second  # segunda vez no


def test_check_all_conditions_at_once(tmp_path, monkeypatch):
    """Si entra todo a la vez, deberían unlockearse los 12 logros."""
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE",
                        str(tmp_path / "ach.json"))
    unlocked = check_achievements(
        affection=100, message_count=1000, facts_count=10,
        vision_enabled=True, used_mic=True, executed_action=True,
    )
    assert len(unlocked) == 12
