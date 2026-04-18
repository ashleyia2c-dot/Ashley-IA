"""
Tests for reflex_companion.stats — HMAC signing + tamper detection.

El registry mirror solo se testea en Windows (otros OS lo saltan). En dev
usamos monkeypatch para aislar el registry access.
"""

from __future__ import annotations

import json

import pytest

from reflex_companion import stats as s


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """Redirect STATS_FILE + disable registry mirror por default."""
    monkeypatch.setattr(s, "STATS_FILE", str(tmp_path / "stats.json"))
    # Default: desactivamos registry mirror para que los tests sean puros
    # y no dependan del entorno. Los tests que quieran probarlo lo reactivan.
    monkeypatch.setattr(s, "_load_from_registry", lambda: None)
    monkeypatch.setattr(s, "_save_to_registry", lambda data: None)


# ── Load/save básico ─────────────────────────────────────────────────────────


def test_load_stats_returns_default_when_empty():
    stats = s.load_stats()
    assert stats["total_user_messages"] == 0
    assert stats["first_message_at"] is None
    assert stats["_tampered"] is False


def test_save_and_load_roundtrip():
    s.save_stats({"total_user_messages": 7, "first_message_at": "2026-04-18T12:00:00+00:00"})
    loaded = s.load_stats()
    assert loaded["total_user_messages"] == 7
    assert loaded["first_message_at"] == "2026-04-18T12:00:00+00:00"
    assert loaded["_tampered"] is False


# ── HMAC tampering detection ─────────────────────────────────────────────────


def test_signature_mismatch_detected_as_tampering(tmp_path):
    """Si editamos el contador a mano sin regenerar la firma → tampered."""
    s.save_stats({"total_user_messages": 47, "first_message_at": "2026-04-18T12:00:00+00:00"})

    # User edita el archivo manualmente
    with open(s.STATS_FILE, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["total_user_messages"] = 5  # engañando al contador
        # dejamos el _sig viejo
        f.seek(0)
        f.truncate()
        json.dump(data, f)

    loaded = s.load_stats()
    assert loaded["_tampered"] is True
    assert loaded["total_user_messages"] == s._POISONED_COUNT


def test_missing_signature_detected_as_tampering():
    """Archivo sin _sig → creado a mano o de versión anterior → tampered."""
    from reflex_companion.memory import save_json
    save_json(s.STATS_FILE, {"total_user_messages": 3, "first_message_at": None})

    loaded = s.load_stats()
    assert loaded["_tampered"] is True


def test_user_cannot_guess_valid_signature_for_lower_count():
    """Sanity: si el user intenta firmar con su propio HMAC (sin saber el secret)
    la verificación falla."""
    import hashlib, hmac as hmac_mod
    fake_secret = b"hunter2"
    forged = {"total_user_messages": 1, "first_message_at": None}
    fake_sig = hmac_mod.new(fake_secret, json.dumps(forged, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    forged["_sig"] = fake_sig

    from reflex_companion.memory import save_json
    save_json(s.STATS_FILE, forged)

    loaded = s.load_stats()
    assert loaded["_tampered"] is True


# ── Increment ────────────────────────────────────────────────────────────────


def test_increment_starts_at_one():
    result = s.increment_message_counter()
    assert result["total_user_messages"] == 1
    assert result["first_message_at"] is not None


def test_increment_persists_first_message_timestamp():
    first = s.increment_message_counter()
    second = s.increment_message_counter()
    assert first["first_message_at"] == second["first_message_at"]
    assert second["total_user_messages"] == 2


def test_increment_on_tampered_is_noop(monkeypatch):
    """Cuando el contador está envenenado, increment NO debe bajar el valor."""
    s.save_stats({"total_user_messages": 50, "first_message_at": "2026-04-18T12:00:00+00:00"})

    # Simular tampering editando el archivo
    with open(s.STATS_FILE, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["total_user_messages"] = 1
        f.seek(0); f.truncate()
        json.dump(data, f)

    result = s.increment_message_counter()
    assert result["_tampered"] is True
    assert result["total_user_messages"] == s._POISONED_COUNT


# ── is_refund_eligible ───────────────────────────────────────────────────────


def test_refund_eligible_under_threshold():
    s.save_stats({"total_user_messages": 30, "first_message_at": "2026-04-18T12:00:00+00:00"})
    assert s.is_refund_eligible() is True


def test_refund_not_eligible_at_threshold():
    s.save_stats({"total_user_messages": 40, "first_message_at": "2026-04-18T12:00:00+00:00"})
    assert s.is_refund_eligible() is False


def test_refund_not_eligible_over_threshold():
    s.save_stats({"total_user_messages": 41, "first_message_at": "2026-04-18T12:00:00+00:00"})
    assert s.is_refund_eligible() is False


def test_tampered_is_never_refund_eligible():
    """Aun si el contador envenenado supera 40, el flag tampered es suficiente
    para denegar por política."""
    stats = {"total_user_messages": 0, "first_message_at": None, "_tampered": True}
    assert s.is_refund_eligible(stats) is False


def test_custom_threshold_respected():
    s.save_stats({"total_user_messages": 15, "first_message_at": "2026-04-18T12:00:00+00:00"})
    assert s.is_refund_eligible(threshold=20) is True
    assert s.is_refund_eligible(threshold=10) is False


# ── Registry mirror (mockeado) ───────────────────────────────────────────────


def test_load_takes_max_of_file_and_registry(monkeypatch):
    """Si JSON dice 5 pero registry dice 47 → tomamos 47 (y marcamos tampered
    por divergencia)."""
    s.save_stats({"total_user_messages": 5, "first_message_at": "2026-04-18T12:00:00+00:00"})

    def fake_registry():
        return {
            "total_user_messages": 47,
            "first_message_at": "2026-04-18T12:00:00+00:00",
            "_tampered": False,
        }
    monkeypatch.setattr(s, "_load_from_registry", fake_registry)

    loaded = s.load_stats()
    assert loaded["total_user_messages"] == 47
    # Divergencia fuerte → flag tampered
    assert loaded["_tampered"] is True


def test_load_no_divergence_when_small_drift(monkeypatch):
    """File=10, Registry=11 → drift de 1, no marcamos tampered."""
    s.save_stats({"total_user_messages": 10, "first_message_at": "2026-04-18T12:00:00+00:00"})
    monkeypatch.setattr(s, "_load_from_registry", lambda: {
        "total_user_messages": 11,
        "first_message_at": "2026-04-18T12:00:00+00:00",
        "_tampered": False,
    })
    loaded = s.load_stats()
    assert loaded["total_user_messages"] == 11
    assert loaded["_tampered"] is False


def test_tampered_registry_propagates_flag(monkeypatch):
    """Aun si el file está sano, si el registry está tampered → flag tampered."""
    s.save_stats({"total_user_messages": 20, "first_message_at": "2026-04-18T12:00:00+00:00"})
    monkeypatch.setattr(s, "_load_from_registry", lambda: {
        "total_user_messages": 20,
        "first_message_at": "2026-04-18T12:00:00+00:00",
        "_tampered": True,
    })
    loaded = s.load_stats()
    assert loaded["_tampered"] is True


def test_fallback_to_registry_when_file_missing(monkeypatch):
    """Si el user borra el JSON, el registry mantiene el valor."""
    # No guardamos nada en file
    monkeypatch.setattr(s, "_load_from_registry", lambda: {
        "total_user_messages": 33,
        "first_message_at": "2026-04-18T12:00:00+00:00",
        "_tampered": False,
    })
    loaded = s.load_stats()
    assert loaded["total_user_messages"] == 33


# ── is_tampered_vs_history ───────────────────────────────────────────────────


def test_history_full_with_low_counter_detected():
    """Historial a tope + contador bajo → obvio que hay tampering."""
    assert s.is_tampered_vs_history(total_messages=5, history_length=50) is True


def test_history_partial_does_not_trigger():
    """Historial medio lleno + contador razonable → OK."""
    assert s.is_tampered_vs_history(total_messages=20, history_length=30) is False


def test_history_full_with_matching_counter_ok():
    """Historial a tope + contador alto → normal, usuario activo."""
    assert s.is_tampered_vs_history(total_messages=500, history_length=50) is False
