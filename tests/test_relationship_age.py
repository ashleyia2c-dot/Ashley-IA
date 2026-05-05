"""Guards para sistema de "relationship age" (v0.18.0 — Fase 1 Tier 1).

Reutiliza first_message_at (que ya existía en stats.py para anti-tamper)
para exponer "X días juntos" a Ashley + activar achievements temporales
en hitos exactos (7/30/100/365 días).

Tests cubren:
  1. get_relationship_age_days — cálculo correcto en local date
  2. get_relationship_milestone_today — solo el día EXACTO del hito
  3. Achievements temporales se desbloquean al alcanzar threshold
  4. i18n strings presentes en EN/ES/FR
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from reflex_companion import achievements, stats


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: aislar archivos JSON
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """Redirect STATS_FILE y ACHIEVEMENTS_FILE a tmp_path por test."""
    monkeypatch.setattr(stats, "STATS_FILE", str(tmp_path / "stats.json"))
    monkeypatch.setattr(achievements, "ACHIEVEMENTS_FILE", str(tmp_path / "achievements.json"))
    # Disable registry mirror in tests to keep them deterministic
    monkeypatch.setattr(stats, "_registry_available", lambda: False)


# ─────────────────────────────────────────────────────────────────────────────
# get_relationship_age_days
# ─────────────────────────────────────────────────────────────────────────────


def _make_stats(first_at_offset_days: int | None = None) -> dict:
    """Helper para construir un stats dict con first_message_at en pasado.

    IMPORTANTE: el offset es en DÍAS LOCALES (no UTC) — get_relationship_age_days
    cuenta calendar days en LOCAL time del user. Si construimos el target
    como "now_utc - N days", podemos cruzar boundaries de fecha local y
    obtener N+1 o N-1 días según la hora UTC actual.

    Por eso anclamos el target a NOON LOCAL del día N atrás — eso garantiza
    que la fecha LOCAL del target es exactamente lo que esperamos.
    """
    if first_at_offset_days is None:
        return {"total_user_messages": 0, "first_message_at": None, "_tampered": False}
    today_local = datetime.now().astimezone()
    target_local_date = today_local.date() - timedelta(days=first_at_offset_days)
    # Combinar la fecha con noon local time (12:00) para evitar boundary crossings
    target_local = datetime.combine(
        target_local_date,
        datetime.min.time().replace(hour=12),
    ).astimezone()  # naive → aware (local tz)
    target_utc = target_local.astimezone(timezone.utc)
    return {
        "total_user_messages": 5,
        "first_message_at": target_utc.isoformat(),
        "_tampered": False,
    }


def test_age_none_when_no_first_message():
    """Si nunca habló (first_message_at None) → age es None."""
    age = stats.get_relationship_age_days(_make_stats(first_at_offset_days=None))
    assert age is None


def test_age_zero_on_first_day():
    """Mismo día → 0 días."""
    age = stats.get_relationship_age_days(_make_stats(first_at_offset_days=0))
    assert age == 0


def test_age_seven_days():
    """Hace 7 días → 7."""
    age = stats.get_relationship_age_days(_make_stats(first_at_offset_days=7))
    assert age == 7


def test_age_thirty_days():
    age = stats.get_relationship_age_days(_make_stats(first_at_offset_days=30))
    assert age == 30


def test_age_one_year():
    age = stats.get_relationship_age_days(_make_stats(first_at_offset_days=365))
    assert age == 365


def test_age_clamps_negative():
    """Si reloj viajó al pasado (raro) → clamp a 0, no negativo."""
    future = datetime.now(timezone.utc) + timedelta(days=5)
    s = {"total_user_messages": 5, "first_message_at": future.isoformat(), "_tampered": False}
    age = stats.get_relationship_age_days(s)
    assert age == 0  # nunca negativo


def test_age_handles_invalid_timestamp():
    """first_message_at corrupto → None, no raise."""
    s = {"total_user_messages": 5, "first_message_at": "not-a-date", "_tampered": False}
    age = stats.get_relationship_age_days(s)
    assert age is None


def test_age_loads_from_disk_when_no_arg():
    """Sin pasar arg, llama load_stats() — debe funcionar sin crashear."""
    # No first_message_at en disco → None
    age = stats.get_relationship_age_days()
    assert age is None


# ─────────────────────────────────────────────────────────────────────────────
# get_relationship_milestone_today
# ─────────────────────────────────────────────────────────────────────────────


def test_milestone_none_when_no_first_message():
    m = stats.get_relationship_milestone_today(_make_stats(None))
    assert m is None


def test_milestone_none_on_random_days():
    """Días que NO son hito → None."""
    for days in [1, 5, 8, 15, 29, 31, 50, 99, 101, 200, 364, 366]:
        m = stats.get_relationship_milestone_today(_make_stats(days))
        assert m is None, f"day {days} should NOT be a milestone, got {m}"


def test_milestone_first_week_at_day_7():
    m = stats.get_relationship_milestone_today(_make_stats(7))
    assert m == "first_week"


def test_milestone_month_at_day_30():
    m = stats.get_relationship_milestone_today(_make_stats(30))
    assert m == "month_together"


def test_milestone_hundred_at_day_100():
    m = stats.get_relationship_milestone_today(_make_stats(100))
    assert m == "hundred_days"


def test_milestone_year_at_day_365():
    m = stats.get_relationship_milestone_today(_make_stats(365))
    assert m == "year_together"


def test_milestone_only_on_exact_day_not_after():
    """Hitos solo el día exacto — al siguiente ya no aparece (evita
    que Ashley diga 'celebremos los 30 días' durante toda la semana siguiente)."""
    assert stats.get_relationship_milestone_today(_make_stats(31)) is None
    assert stats.get_relationship_milestone_today(_make_stats(101)) is None
    assert stats.get_relationship_milestone_today(_make_stats(366)) is None


# ─────────────────────────────────────────────────────────────────────────────
# Achievements temporales
# ─────────────────────────────────────────────────────────────────────────────


def test_achievement_first_week_unlocks_at_day_7():
    newly = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=7,
    )
    ids = [a["id"] for a in newly]
    assert "first_week" in ids


def test_achievement_first_week_does_not_unlock_at_day_6():
    newly = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=6,
    )
    ids = [a["id"] for a in newly]
    assert "first_week" not in ids


def test_achievement_month_together_unlocks_at_day_30():
    newly = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=30,
    )
    ids = [a["id"] for a in newly]
    assert "month_together" in ids


def test_achievement_hundred_days_unlocks_at_day_100():
    newly = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=100,
    )
    ids = [a["id"] for a in newly]
    assert "hundred_days" in ids


def test_achievement_year_together_unlocks_at_day_365():
    newly = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=365,
    )
    ids = [a["id"] for a in newly]
    assert "year_together" in ids


def test_achievement_unlocks_all_under_threshold_at_high_age():
    """Al día 400, deben desbloquearse TODOS los hitos temporales <= 400."""
    newly = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=400,
    )
    ids = [a["id"] for a in newly]
    assert "first_week" in ids
    assert "month_together" in ids
    assert "hundred_days" in ids
    assert "year_together" in ids


def test_achievement_idempotent_second_call():
    """Segundo call sobre los mismos hitos NO los re-desbloquea."""
    achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=7,
    )
    newly2 = achievements.check_achievements(
        affection=0, message_count=1, facts_count=0,
        vision_enabled=False, used_mic=False, executed_action=False,
        relationship_age_days=7,
    )
    ids = [a["id"] for a in newly2]
    assert "first_week" not in ids


def test_achievement_no_age_no_time_milestones():
    """Si relationship_age_days es None, NO se desbloquean los temporales."""
    newly = achievements.check_achievements(
        affection=100, message_count=1000, facts_count=10,
        vision_enabled=True, used_mic=True, executed_action=True,
        relationship_age_days=None,
    )
    ids = [a["id"] for a in newly]
    # Otros achievements sí (afecto, mensajes, etc.) pero NO los temporales
    assert "first_week" not in ids
    assert "month_together" not in ids
    assert "hundred_days" not in ids
    assert "year_together" not in ids


# ─────────────────────────────────────────────────────────────────────────────
# Achievements ACHIEVEMENTS list (definiciones)
# ─────────────────────────────────────────────────────────────────────────────


def test_time_achievements_defined_in_list():
    """Los 4 achievements de tiempo deben estar en la constante ACHIEVEMENTS."""
    ids = [a["id"] for a in achievements.ACHIEVEMENTS]
    for required in ("first_week", "month_together", "hundred_days", "year_together"):
        assert required in ids, f"Achievement {required!r} no está definido"


def test_time_achievements_have_tier():
    """Los achievements temporales deben tener tier='time' para distinguirlos."""
    for tid in ("first_week", "month_together", "hundred_days", "year_together"):
        a = achievements.get_achievement_def(tid)
        assert a is not None
        assert a["tier"] == "time", (
            f"Achievement {tid} debe tener tier='time' (es: {a.get('tier')!r})"
        )


def test_time_achievements_have_bilingual_text():
    """Achievements temporales deben tener nombre y desc en EN y ES."""
    for tid in ("first_week", "month_together", "hundred_days", "year_together"):
        a = achievements.get_achievement_def(tid)
        for key in ("name_en", "name_es", "desc_en", "desc_es"):
            assert key in a and a[key], f"{tid} falta {key}"


# ─────────────────────────────────────────────────────────────────────────────
# i18n strings
# ─────────────────────────────────────────────────────────────────────────────


def test_i18n_relationship_strings_present_all_languages():
    """rel_first_day, rel_days_together, rel_milestone_* deben existir en EN/ES/FR."""
    from reflex_companion import i18n

    required_keys = [
        "rel_first_day",
        "rel_days_together",
        "rel_milestone_first_week",
        "rel_milestone_month_together",
        "rel_milestone_hundred_days",
        "rel_milestone_year_together",
    ]

    for lang in ("en", "es", "fr"):
        ctx = i18n.time_ctx(lang)
        for key in required_keys:
            assert key in ctx, f"Falta i18n key {key!r} en TIME_CTX[{lang!r}]"
            assert ctx[key], f"i18n key {key!r} en {lang} está vacío"


def test_i18n_rel_days_together_has_format_placeholder():
    """rel_days_together debe tener {days} como placeholder formateable."""
    from reflex_companion import i18n
    for lang in ("en", "es", "fr"):
        ctx = i18n.time_ctx(lang)
        assert "{days}" in ctx["rel_days_together"], (
            f"rel_days_together en {lang} debe contener {{days}}"
        )
        # Test que se puede formatear sin error
        formatted = ctx["rel_days_together"].format(days=42)
        assert "42" in formatted


# ─────────────────────────────────────────────────────────────────────────────
# Constantes RELATIONSHIP_MILESTONES
# ─────────────────────────────────────────────────────────────────────────────


def test_relationship_milestones_constant_matches_achievements():
    """Los thresholds en stats.RELATIONSHIP_MILESTONES deben coincidir con
    los achievement IDs en achievements.ACHIEVEMENTS."""
    milestone_ids = {mid for _, mid in stats.RELATIONSHIP_MILESTONES}
    achievement_time_ids = {
        a["id"] for a in achievements.ACHIEVEMENTS if a["tier"] == "time"
    }
    assert milestone_ids == achievement_time_ids, (
        f"Mismatch entre stats.RELATIONSHIP_MILESTONES ({milestone_ids}) "
        f"y achievements de tier='time' ({achievement_time_ids})"
    )
