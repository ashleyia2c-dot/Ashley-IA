"""Tests for mental_state module.

Cubre las partes deterministas (mood drift, event classification,
initiative counter, gap reconciliation, formatting). NO cubre la
regeneración de preoccupation porque eso hace una llamada real a Grok.
"""

import datetime as dt
import pytest

from reflex_companion import mental_state as ms


# ──────────────────────────────────────────────────
#  Default state
# ──────────────────────────────────────────────────

def test_default_state_has_expected_keys():
    s = ms._default_state()
    assert "mood" in s
    assert set(s["mood"].keys()) == {"energy", "valence", "openness"}
    # All axes start at neutral
    for axis in ("energy", "valence", "openness"):
        assert s["mood"][axis] == pytest.approx(0.5)
    assert s["turns_since_initiative"] == 0
    assert s["preoccupation"] == ""


# ──────────────────────────────────────────────────
#  Event classification
# ──────────────────────────────────────────────────

def test_classify_affection_phrases_across_langs():
    for msg in ("te quiero", "me gustas mucho", "I love you", "tu me plais"):
        events = ms.classify_user_event(msg, None)
        assert "affection" in events, f"missed affection in: {msg!r}"


def test_classify_priority_phrases():
    events = ms.classify_user_event("estoy hablando contigo ahora", None)
    assert "priority" in events


def test_classify_checkin():
    events = ms.classify_user_event("hola como estas", None)
    assert "checkin" in events


def test_classify_short_reply():
    events = ms.classify_user_event("si", None)
    assert "short_reply" in events


def test_classify_long_return():
    # 300 min = 5 h → long_return
    events = ms.classify_user_event("hola", 300.0)
    assert "long_return" in events


def test_classify_short_return():
    # 90 min between short_return (>60) and long_return (>240)
    events = ms.classify_user_event("hola", 90.0)
    assert "short_return" in events
    assert "long_return" not in events


def test_classify_dismissive():
    events = ms.classify_user_event("callate ashley", None)
    assert "dismissive" in events


def test_classify_empty_returns_empty():
    assert ms.classify_user_event("", None) == []


# ──────────────────────────────────────────────────
#  Mood deltas
# ──────────────────────────────────────────────────

def test_affection_raises_valence_and_openness():
    s = ms._default_state()
    ms.apply_events_to_mood(s, ["affection"])
    assert s["mood"]["valence"] > 0.5
    assert s["mood"]["openness"] > 0.5


def test_dismissive_lowers_valence():
    s = ms._default_state()
    ms.apply_events_to_mood(s, ["dismissive"])
    assert s["mood"]["valence"] < 0.5


def test_mood_clamped_to_range():
    s = ms._default_state()
    # Apply many positive events
    for _ in range(30):
        ms.apply_events_to_mood(s, ["affection", "priority"])
    for axis in ("energy", "valence", "openness"):
        assert 0.0 <= s["mood"][axis] <= 1.0


def test_mood_drifts_toward_neutral():
    """Sin eventos, aplicar apply_events_to_mood([]) acerca todo a 0.5."""
    s = ms._default_state()
    s["mood"]["valence"] = 0.9
    s["mood"]["openness"] = 0.1
    for _ in range(50):
        ms.apply_events_to_mood(s, [])  # no events, pure drift
    # Both should have converged toward 0.5 from opposite extremes
    assert 0.4 < s["mood"]["valence"] < 0.8
    assert 0.2 < s["mood"]["openness"] < 0.6


# ──────────────────────────────────────────────────
#  Mood description (abstract, no numbers)
# ──────────────────────────────────────────────────

def test_describe_mood_produces_prose_not_numbers():
    s = ms._default_state()
    for lang in ("es", "en", "fr"):
        desc = ms.describe_mood(s, lang)
        assert isinstance(desc, str)
        assert len(desc) > 0
        # Must not leak internal number values or technical field names.
        # "energy" as a natural English word in a description is fine
        # ("normal energy"), but debug-like outputs like "=0.5" or
        # field names as standalone tokens should not appear.
        assert "0.5" not in desc
        assert "valence" not in desc.lower()  # internal-only field name
        assert "openness" not in desc.lower()  # internal-only field name


def test_describe_mood_changes_with_values():
    s_low = ms._default_state()
    s_low["mood"]["energy"] = 0.1
    s_high = ms._default_state()
    s_high["mood"]["energy"] = 0.9
    assert ms.describe_mood(s_low, "es") != ms.describe_mood(s_high, "es")


# ──────────────────────────────────────────────────
#  Preoccupation regeneration trigger
# ──────────────────────────────────────────────────

def test_should_regenerate_when_empty():
    s = ms._default_state()
    assert ms.should_regenerate_preoccupation(s) is True


def test_should_regenerate_when_stale():
    s = ms._default_state()
    s["preoccupation"] = "Some text"
    # 2 hours ago
    s["preoccupation_generated_at"] = (
        dt.datetime.now() - dt.timedelta(hours=2)
    ).isoformat()
    assert ms.should_regenerate_preoccupation(s) is True


def test_should_not_regenerate_when_fresh():
    s = ms._default_state()
    s["preoccupation"] = "Some text"
    s["preoccupation_generated_at"] = dt.datetime.now().isoformat()
    assert ms.should_regenerate_preoccupation(s) is False


# ──────────────────────────────────────────────────
#  Gap reconciliation
# ──────────────────────────────────────────────────

def test_gap_context_none_for_small_gap():
    assert ms.compute_gap_context(30.0, "es") is None
    assert ms.compute_gap_context(None, "es") is None


def test_gap_context_long_gap_returns_text():
    ctx = ms.compute_gap_context(300.0, "es")  # 5 h
    assert ctx is not None
    assert "hour" in ctx.lower() or "day" in ctx.lower()


def test_drift_mood_on_gap_brings_extremes_to_neutral():
    s = ms._default_state()
    s["mood"]["valence"] = 0.9
    s["mood"]["energy"] = 0.1
    ms.drift_mood_on_gap(s, 600.0)  # 10 h → factor ~1.0
    # Both should be ~0.5
    assert abs(s["mood"]["valence"] - 0.5) < 0.1
    assert abs(s["mood"]["energy"] - 0.5) < 0.1


def test_drift_mood_ignores_small_gap():
    s = ms._default_state()
    s["mood"]["valence"] = 0.9
    ms.drift_mood_on_gap(s, 10.0)  # 10 min — ignored
    assert s["mood"]["valence"] == 0.9


# ──────────────────────────────────────────────────
#  Initiative counter
# ──────────────────────────────────────────────────

def test_initiative_counter_deprecated_always_returns_false():
    """El contador de iniciativa FORZADA fue eliminado porque hacía
    que Ashley saltase de tema aunque el user estuviera en medio de
    algo. Ahora la función sigue existiendo (no rompe callers) pero
    siempre devuelve False."""
    s = ms._default_state()
    s["turns_since_initiative"] = 99
    for _ in range(20):
        fired = ms.tick_initiative_counter(s)
        assert fired is False, "initiative should never fire anymore"
    assert s["turns_since_initiative"] == 0  # se resetea


# ──────────────────────────────────────────────────
#  Format block
# ──────────────────────────────────────────────────

def test_format_block_contains_mood_description():
    s = ms._default_state()
    block = ms.format_mental_state_block(s, "es", initiative_due=False)
    assert "ESTADO INTERIOR" in block
    assert "PRIVADO" in block


def test_format_block_no_longer_forces_initiative():
    """Incluso si pasamos initiative_due=True (legacy), el bloque ya no
    contiene la directiva de 'abre un tema' — se eliminó porque forzaba
    a Ashley a ignorar el hilo del user."""
    s = ms._default_state()
    block_yes = ms.format_mental_state_block(s, "es", initiative_due=True)
    # El bloque NO debe contener el forcing anterior
    assert "ABRAS" not in block_yes
    assert "CAMBIO DE TEMA" not in block_yes
    assert "OPEN A TOPIC" not in block_yes.upper()


def test_format_block_all_three_langs():
    s = ms._default_state()
    s["preoccupation"] = "Ashley ha estado pensando en algo."
    for lang, marker in [("es", "INTERIOR"), ("en", "INTERIOR"), ("fr", "INTÉRIEUR")]:
        block = ms.format_mental_state_block(s, lang, False)
        assert marker in block, f"missing marker in {lang}"


def test_format_block_does_not_include_preoccupation_when_empty():
    s = ms._default_state()
    s["preoccupation"] = ""
    block = ms.format_mental_state_block(s, "es", False)
    # Should not include a "rumiando" section if nothing there
    assert "rumiando" not in block.lower()
