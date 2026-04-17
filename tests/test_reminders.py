"""
Tests for reflex_companion.reminders — reminder/important persistence and parsing.
"""

from datetime import datetime, timedelta

import pytest

from reflex_companion import reminders


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """Redirect REMINDERS_FILE and IMPORTANT_FILE to tmp_path for every test.

    reminders.py uses ``from .config import REMINDERS_FILE`` so the name is
    bound locally inside the reminders module — we must patch *there*.
    """
    monkeypatch.setattr(reminders, "REMINDERS_FILE", str(tmp_path / "recordatorios.json"))
    monkeypatch.setattr(reminders, "IMPORTANT_FILE", str(tmp_path / "importantes.json"))


# ── parse_remind_params ──────────────────────────────────────────────────────


def test_parse_remind_params_with_seconds():
    """Full ISO datetime with seconds + text."""
    result = reminders.parse_remind_params("2026-04-15T15:00:00:Meeting tomorrow")
    assert result == ["2026-04-15T15:00:00", "Meeting tomorrow"]


def test_parse_remind_params_without_seconds():
    """ISO datetime without seconds + text."""
    result = reminders.parse_remind_params("2026-04-15T15:00:Meeting tomorrow")
    assert result == ["2026-04-15T15:00", "Meeting tomorrow"]


def test_parse_remind_params_empty_string():
    """Empty string returns empty list."""
    result = reminders.parse_remind_params("")
    assert result == []


def test_parse_remind_params_no_datetime():
    """Plain text with no datetime prefix returns [rest]."""
    result = reminders.parse_remind_params("just text no datetime")
    assert result == ["just text no datetime"]


# ── add_reminder ─────────────────────────────────────────────────────────────


def test_add_reminder_creates_valid_entry():
    """add_reminder creates an entry with id, text, datetime, fired."""
    result_msg = reminders.add_reminder("Call doctor", "2026-05-01T10:00:00")
    assert "Call doctor" in result_msg

    loaded = reminders.load_reminders()
    assert len(loaded) == 1

    entry = loaded[0]
    assert "id" in entry
    assert entry["text"] == "Call doctor"
    assert entry["datetime"] == "2026-05-01T10:00:00"
    assert entry["fired"] is False
    assert "created_at" in entry


# ── get_due_reminders ────────────────────────────────────────────────────────


def test_get_due_reminders_returns_past_reminders():
    """Reminders whose datetime is in the past should be returned."""
    past = (datetime.now() - timedelta(hours=1)).isoformat()
    reminders.add_reminder("Past event", past)

    due = reminders.get_due_reminders()
    assert len(due) == 1
    assert due[0]["text"] == "Past event"


def test_get_due_reminders_does_not_return_future():
    """Reminders in the future should NOT be returned."""
    future = (datetime.now() + timedelta(hours=24)).isoformat()
    reminders.add_reminder("Future event", future)

    due = reminders.get_due_reminders()
    assert len(due) == 0


def test_get_due_reminders_does_not_return_fired():
    """Already-fired reminders should NOT be returned even if past."""
    past = (datetime.now() - timedelta(hours=1)).isoformat()
    reminders.add_reminder("Fired event", past)

    entry = reminders.load_reminders()[0]
    reminders.mark_reminder_fired(entry["id"])

    due = reminders.get_due_reminders()
    assert len(due) == 0


# ── mark_reminder_fired ─────────────────────────────────────────────────────


def test_mark_reminder_fired_sets_flag():
    """mark_reminder_fired sets fired=True on the correct reminder."""
    reminders.add_reminder("Test reminder", "2026-01-01T00:00:00")
    entry = reminders.load_reminders()[0]

    reminders.mark_reminder_fired(entry["id"])

    reloaded = reminders.load_reminders()
    assert reloaded[0]["fired"] is True


# ── format_reminders_for_prompt ──────────────────────────────────────────────


def test_format_reminders_for_prompt_empty():
    """Empty list returns empty string."""
    assert reminders.format_reminders_for_prompt([]) == ""


def test_format_reminders_for_prompt_formatting():
    """Pending reminders are formatted with id, text, and date."""
    items = [
        {"id": "abc1", "text": "Call doctor", "datetime": "2026-05-01T10:00:00", "fired": False},
        {"id": "abc2", "text": "Buy milk", "datetime": "2026-05-02T08:00:00", "fired": False},
    ]
    result = reminders.format_reminders_for_prompt(items)
    assert "abc1" in result
    assert "Call doctor" in result
    assert "abc2" in result
    assert "Buy milk" in result
    assert result.count("\n") == 1  # two lines, one newline


def test_format_reminders_for_prompt_skips_fired():
    """Fired reminders are excluded from prompt formatting."""
    items = [
        {"id": "abc1", "text": "Done thing", "datetime": "2026-05-01T10:00:00", "fired": True},
        {"id": "abc2", "text": "Pending thing", "datetime": "2026-05-02T08:00:00", "fired": False},
    ]
    result = reminders.format_reminders_for_prompt(items)
    assert "Done thing" not in result
    assert "Pending thing" in result


# ── Importantes ──────────────────────────────────────────────────────────────


def test_add_important_creates_entry():
    """add_important creates an entry with id, text, done=False."""
    result_msg = reminders.add_important("Buy groceries")
    assert "Buy groceries" in result_msg

    loaded = reminders.load_important()
    assert len(loaded) == 1
    entry = loaded[0]
    assert "id" in entry
    assert entry["text"] == "Buy groceries"
    assert entry["done"] is False


def test_mark_important_done_by_id():
    """mark_important_done marks the correct item by id."""
    reminders.add_important("Task A")
    entry = reminders.load_important()[0]

    result_msg = reminders.mark_important_done(entry["id"])
    assert "hecho" in result_msg.lower() or "Task A" in result_msg

    reloaded = reminders.load_important()
    assert reloaded[0]["done"] is True


def test_mark_important_done_by_partial_text():
    """mark_important_done matches by partial text (case-insensitive)."""
    reminders.add_important("Call the doctor before Friday")

    result_msg = reminders.mark_important_done("doctor")
    assert "doctor" in result_msg.lower() or "hecho" in result_msg.lower()

    reloaded = reminders.load_important()
    assert reloaded[0]["done"] is True


def test_mark_important_done_not_found():
    """mark_important_done with unknown text returns not-found message."""
    reminders.add_important("Real task")
    result_msg = reminders.mark_important_done("nonexistent")
    assert "no encontr" in result_msg.lower() or "nonexistent" in result_msg.lower()


def test_format_important_for_prompt_empty():
    """Empty list returns empty string."""
    assert reminders.format_important_for_prompt([]) == ""


def test_format_important_for_prompt_excludes_done():
    """Done items are excluded from the prompt formatting."""
    items = [
        {"id": "x1", "text": "Done task", "done": True},
        {"id": "x2", "text": "Pending task", "done": False},
    ]
    result = reminders.format_important_for_prompt(items)
    assert "Done task" not in result
    assert "Pending task" in result
    assert "x2" in result
