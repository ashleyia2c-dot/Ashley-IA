"""
Tests for reflex_companion.license — Lemon Squeezy activation/validation.

La API de LS se mockea mediante monkeypatch de `license._post_form`, así que
los tests no tocan la red. Eso nos permite cubrir timing y branches sin
depender de LS estar vivo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from reflex_companion import license as lic


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_license_file(tmp_path, monkeypatch):
    """Redirect LICENSE_FILE to a temp dir for every test."""
    monkeypatch.setattr(lic, "LICENSE_FILE", str(tmp_path / "license.json"))


@pytest.fixture
def mock_ls(monkeypatch):
    """Mock _post_form. Returns a list that tests append (status, payload) to."""
    responses: list = []
    calls: list = []

    def fake_post(path, fields):
        calls.append((path, dict(fields)))
        if not responses:
            raise AssertionError(f"unexpected LS call to {path}")
        return responses.pop(0)

    monkeypatch.setattr(lic, "_post_form", fake_post)
    # También pinchamos la versión con retry para que use el mismo mock
    # directamente (saltando el sleep).
    monkeypatch.setattr(lic, "_post_with_retry", fake_post)
    return {"responses": responses, "calls": calls}


# ── generate_instance_name ───────────────────────────────────────────────────


def test_generate_instance_name_has_all_parts():
    name = lic.generate_instance_name()
    assert "(" in name and ")" in name  # tiene la plataforma en paréntesis
    assert " - " in name                # separador del uuid
    # El uuid corto son 8 hex al final.
    assert len(name.split(" - ")[-1]) == 8


def test_generate_instance_name_is_unique():
    a = lic.generate_instance_name()
    b = lic.generate_instance_name()
    assert a != b  # el uuid garantiza unicidad


# ── activate ─────────────────────────────────────────────────────────────────


def test_activate_success(mock_ls):
    mock_ls["responses"].append((200, {
        "activated": True,
        "instance": {"id": "inst-123", "name": "test"},
        "license_key": {"test_mode": True},
        "meta": {"customer_email": "a@b.com", "product_id": 984701},
    }))
    ok, payload = lic.activate("VALID-KEY", "my-pc")
    assert ok is True
    assert payload["instance"]["id"] == "inst-123"

    path, fields = mock_ls["calls"][0]
    assert path == "/licenses/activate"
    assert fields == {"license_key": "VALID-KEY", "instance_name": "my-pc"}


def test_activate_rejects_empty_key(mock_ls):
    ok, payload = lic.activate("", "my-pc")
    assert ok is False
    assert payload["error"] == "empty_key"
    # No tiene que haber llamado a LS.
    assert mock_ls["calls"] == []


def test_activate_returns_false_on_api_error(mock_ls):
    mock_ls["responses"].append((400, {
        "activated": False,
        "error": "license_keys not found",
    }))
    ok, payload = lic.activate("BAD-KEY", "my-pc")
    assert ok is False
    assert "not found" in payload["error"]


def test_activate_strips_whitespace(mock_ls):
    mock_ls["responses"].append((200, {"activated": True, "instance": {"id": "x"}}))
    lic.activate("  KEY-WITH-SPACES  ", "my-pc")
    _, fields = mock_ls["calls"][0]
    assert fields["license_key"] == "KEY-WITH-SPACES"


# ── validate ─────────────────────────────────────────────────────────────────


def test_validate_success_with_instance(mock_ls):
    mock_ls["responses"].append((200, {"valid": True, "license_key": {"status": "active"}}))
    ok, _payload = lic.validate("KEY", instance_id="inst-xyz")
    assert ok is True
    _, fields = mock_ls["calls"][0]
    assert fields == {"license_key": "KEY", "instance_id": "inst-xyz"}


def test_validate_success_without_instance(mock_ls):
    mock_ls["responses"].append((200, {"valid": True}))
    ok, _ = lic.validate("KEY")
    assert ok is True
    _, fields = mock_ls["calls"][0]
    assert "instance_id" not in fields


def test_validate_rejects_empty_key():
    ok, payload = lic.validate("")
    assert ok is False
    assert payload["error"] == "empty_key"


def test_validate_returns_false_when_ls_says_invalid(mock_ls):
    mock_ls["responses"].append((400, {"valid": False, "error": "license_keys not found"}))
    ok, _ = lic.validate("BAD-KEY")
    assert ok is False


# ── deactivate ───────────────────────────────────────────────────────────────


def test_deactivate_success(mock_ls):
    mock_ls["responses"].append((200, {"deactivated": True}))
    ok, _ = lic.deactivate("KEY", "inst-1")
    assert ok is True


def test_deactivate_rejects_missing_params(mock_ls):
    ok, _ = lic.deactivate("", "inst-1")
    assert ok is False
    ok, _ = lic.deactivate("KEY", "")
    assert ok is False


# ── Storage local ────────────────────────────────────────────────────────────


def test_load_stored_returns_none_when_missing():
    assert lic.load_stored() is None


def test_store_and_load_roundtrip():
    data = {
        "key": "KEY-123",
        "instance_id": "inst-abc",
        "activated_at": "2026-04-18T14:00:00+00:00",
        "last_validated_at": "2026-04-18T14:00:00+00:00",
    }
    lic.store(data)
    loaded = lic.load_stored()
    assert loaded == data


def test_load_stored_rejects_incomplete_data():
    # Guardamos manualmente un archivo sin instance_id
    lic.store({"key": "KEY-123"})
    assert lic.load_stored() is None


def test_clear_stored_removes_file_and_bak():
    lic.store({"key": "K", "instance_id": "I"})
    # Simular .bak
    import os, shutil
    shutil.copy(lic.LICENSE_FILE, lic.LICENSE_FILE + ".bak")
    assert os.path.exists(lic.LICENSE_FILE)
    assert os.path.exists(lic.LICENSE_FILE + ".bak")

    lic.clear_stored()
    assert not os.path.exists(lic.LICENSE_FILE)
    assert not os.path.exists(lic.LICENSE_FILE + ".bak")


# ── Grace period ─────────────────────────────────────────────────────────────


def test_grace_period_returns_true_within_window():
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    assert lic.is_within_grace_period(recent) is True


def test_grace_period_returns_false_beyond_window():
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    assert lic.is_within_grace_period(old) is False


def test_grace_period_returns_false_for_none():
    assert lic.is_within_grace_period(None) is False


def test_grace_period_handles_invalid_timestamp():
    assert lic.is_within_grace_period("not a date") is False


def test_grace_period_handles_naive_timestamp():
    """Timestamps sin tz deben asumirse UTC — no tirar excepción."""
    naive = (datetime.utcnow() - timedelta(days=2)).isoformat()
    assert lic.is_within_grace_period(naive) is True


def test_grace_period_respects_custom_days():
    mid = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    assert lic.is_within_grace_period(mid, days=7) is True
    assert lic.is_within_grace_period(mid, days=3) is False


# ── activate_and_store (flujo alto nivel) ────────────────────────────────────


def test_activate_and_store_success_persists_data(mock_ls):
    mock_ls["responses"].append((200, {
        "activated": True,
        "instance": {"id": "new-inst"},
        "license_key": {"test_mode": True},
        "meta": {"customer_email": "mathieu@test.com", "product_id": 984701},
    }))
    ok, msg = lic.activate_and_store("FRESH-KEY")
    assert ok is True
    assert msg == ""

    stored = lic.load_stored()
    assert stored["key"] == "FRESH-KEY"
    assert stored["instance_id"] == "new-inst"
    assert stored["customer_email"] == "mathieu@test.com"
    assert stored["test_mode"] is True
    assert "activated_at" in stored
    assert "last_validated_at" in stored


def test_activate_and_store_failure_does_not_persist(mock_ls):
    mock_ls["responses"].append((400, {"activated": False, "error": "license_keys not found"}))
    ok, msg = lic.activate_and_store("WRONG")
    assert ok is False
    assert msg  # un mensaje friendly, no vacío
    assert lic.load_stored() is None


# ── ensure_valid_on_startup ──────────────────────────────────────────────────


def test_ensure_valid_on_startup_no_license():
    ok, reason = lic.ensure_valid_on_startup()
    assert ok is False
    assert reason == "no_license"


def test_ensure_valid_on_startup_valid_updates_timestamp(mock_ls):
    old_ts = "2026-01-01T00:00:00+00:00"
    lic.store({
        "key": "K", "instance_id": "I",
        "activated_at": old_ts, "last_validated_at": old_ts,
    })
    mock_ls["responses"].append((200, {"valid": True}))

    ok, reason = lic.ensure_valid_on_startup()
    assert ok is True
    assert reason == ""

    # timestamp debió actualizarse
    stored = lic.load_stored()
    assert stored["last_validated_at"] != old_ts


def test_ensure_valid_on_startup_invalid_license(mock_ls):
    lic.store({
        "key": "K", "instance_id": "I",
        "activated_at": "2026-01-01T00:00:00+00:00",
        "last_validated_at": "2026-01-01T00:00:00+00:00",
    })
    mock_ls["responses"].append((400, {"valid": False, "error": "license_keys not found"}))

    ok, reason = lic.ensure_valid_on_startup()
    assert ok is False
    assert reason == "license_invalid"


def test_ensure_valid_on_startup_invalid_instance(mock_ls):
    lic.store({
        "key": "K", "instance_id": "I",
        "activated_at": "2026-01-01T00:00:00+00:00",
        "last_validated_at": "2026-01-01T00:00:00+00:00",
    })
    mock_ls["responses"].append((400, {"valid": False, "error": "instance not found"}))

    ok, reason = lic.ensure_valid_on_startup()
    assert ok is False
    assert reason == "instance_invalid"


def test_ensure_valid_on_startup_offline_grace_allows(monkeypatch):
    """LS down + último validate hace 3 días → permite arranque."""
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    lic.store({
        "key": "K", "instance_id": "I",
        "activated_at": recent, "last_validated_at": recent,
    })

    def boom(*a, **kw):
        raise ConnectionError("LS unreachable: test")
    monkeypatch.setattr(lic, "_post_with_retry", boom)

    ok, reason = lic.ensure_valid_on_startup()
    assert ok is True
    assert reason == "offline_grace"


def test_ensure_valid_on_startup_offline_grace_expired(monkeypatch):
    """LS down + último validate hace 10 días → bloquea."""
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    lic.store({
        "key": "K", "instance_id": "I",
        "activated_at": old, "last_validated_at": old,
    })

    def boom(*a, **kw):
        raise ConnectionError("LS unreachable: test")
    monkeypatch.setattr(lic, "_post_with_retry", boom)

    ok, reason = lic.ensure_valid_on_startup()
    assert ok is False
    assert reason == "offline_grace_expired"


# ── _friendly_error ──────────────────────────────────────────────────────────


def test_friendly_error_unknown_key():
    msg = lic._friendly_error({"error": "license_keys not found"})
    assert "no existe" in msg.lower() or "válida" in msg.lower()


def test_friendly_error_disabled():
    msg = lic._friendly_error({"error": "license key has been disabled"})
    assert "deshabilitada" in msg.lower() or "soporte" in msg.lower()


def test_friendly_error_limit_exceeded():
    msg = lic._friendly_error({"error": "activation limit reached"})
    assert "desactiva" in msg.lower() or "pcs" in msg.lower() or "máximo" in msg.lower()


def test_friendly_error_empty_payload_has_fallback():
    msg = lic._friendly_error({})
    assert msg  # no vacío
