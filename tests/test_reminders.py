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


# ── Idempotencia (v0.17.3) ───────────────────────────────────────────────────
# Bug observado en v0.17.2: Ashley re-emitía [action:done_important:X] varias
# veces sobre el mismo item. mark_important_done devolvía "Marcado como hecho"
# cada vez → el user veía 3-4 notificaciones duplicadas. Ahora el segundo+
# call sobre un item ya done devuelve "" (señal de no-op) que el caller
# usa para suprimir la notificación.


def test_mark_important_done_returns_empty_on_already_done():
    """Segundo call sobre item ya hecho devuelve string vacío (señal noop)."""
    reminders.add_important("Task X")
    entry = reminders.load_important()[0]

    # Primer call: marca y devuelve mensaje
    msg1 = reminders.mark_important_done(entry["id"])
    assert msg1 != "", "Primer call debería devolver mensaje no-vacío"
    assert "hecho" in msg1.lower()

    # Segundo call sobre el mismo item: noop, devuelve ""
    msg2 = reminders.mark_important_done(entry["id"])
    assert msg2 == "", (
        f"Segundo call sobre item ya done debe devolver '' (noop signal). "
        f"Got: {msg2!r}"
    )

    # Estado no debería cambiar al segundo call (defensive check)
    reloaded = reminders.load_important()
    assert reloaded[0]["done"] is True


def test_mark_important_done_partial_text_idempotent():
    """Idempotencia también funciona con match parcial por texto."""
    reminders.add_important("Buy groceries on Monday")

    # Marcar primera vez
    msg1 = reminders.mark_important_done("groceries")
    assert "hecho" in msg1.lower()

    # Re-emit: debe ser noop
    msg2 = reminders.mark_important_done("groceries")
    assert msg2 == ""

    # Y otra forma de match (más texto): también noop
    msg3 = reminders.mark_important_done("Buy groceries on Monday")
    assert msg3 == ""


def test_mark_important_done_picks_pending_over_done():
    """Si hay items done Y pending matching, marca el pending (no devuelve noop).

    Caso edge: usuario tiene "Buy milk" (done de la semana pasada) y
    crea "Buy milk" otra vez (nuevo). Ashley emite done_important:milk.
    Esperado: marca el segundo (pendiente), no el primero (done) ni
    devuelve noop pensando que ya estaba hecho.
    """
    reminders.add_important("Buy milk")
    first = reminders.load_important()[0]
    reminders.mark_important_done(first["id"])  # mark first as done

    reminders.add_important("Buy milk")  # second one, pending
    items_after = reminders.load_important()
    assert len(items_after) == 2
    assert items_after[0]["done"] is True
    assert items_after[1]["done"] is False

    # Now Ashley re-emits done_important:milk → should mark the PENDING one
    msg = reminders.mark_important_done("milk")
    assert msg != "", "Debería marcar el pendiente, no devolver noop"
    assert "hecho" in msg.lower()

    # Verificar que se marcó el segundo (el pendiente), no el primero
    final = reminders.load_important()
    assert final[0]["done"] is True  # already was done
    assert final[1]["done"] is True  # now also done


def test_mark_important_done_not_found_still_returns_not_found():
    """No-match (nada con ese texto) NO debe devolver noop — debe devolver
    el mensaje 'No encontré' para que Ashley sepa que algo va mal."""
    reminders.add_important("Real task")
    msg = reminders.mark_important_done("totally_unrelated")
    assert msg != "", "No-match no es noop, debería devolver mensaje 'no encontré'"
    assert "no encontr" in msg.lower()


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


# ══════════════════════════════════════════════════════════════════════
#  add_important con fecha (v0.14.2)
# ══════════════════════════════════════════════════════════════════════

def test_add_important_with_due_date():
    """add_important guarda due_date cuando se le pasa."""
    msg = reminders.add_important("Llamar al médico", due_date="2026-05-10T15:00:00")
    item = reminders.load_important()[0]
    assert item["text"] == "Llamar al médico"
    assert item["due_date"] == "2026-05-10T15:00:00"
    # El mensaje incluye la fecha formateada
    assert "10/05/2026" in msg


def test_add_important_without_due_date_legacy():
    """Sin due_date sigue funcionando (backward compat)."""
    msg = reminders.add_important("Tarea sin fecha")
    item = reminders.load_important()[0]
    assert item["text"] == "Tarea sin fecha"
    assert "due_date" not in item


def test_format_important_shows_date_when_present():
    """Items con due_date muestran la fecha formateada al inyectar al prompt."""
    items = [
        {"id": "a", "text": "Reunión", "done": False,
         "due_date": "2026-05-10T15:00:00"},
        {"id": "b", "text": "Sin fecha", "done": False},
    ]
    out = reminders.format_important_for_prompt(items)
    assert "Reunión" in out and "10/05/2026" in out
    assert "Sin fecha" in out


# ══════════════════════════════════════════════════════════════════════
#  Stale important items
# ══════════════════════════════════════════════════════════════════════

def test_stale_items_detected_after_due_date():
    """Item con due_date hace 5 días aparece en stale."""
    five_days_ago = (datetime.now() - timedelta(days=5)).isoformat()
    items = [{"id": "x", "text": "Evento pasado", "done": False,
              "due_date": five_days_ago}]
    stale = reminders.get_stale_important_items(items, days=2)
    assert len(stale) == 1
    assert stale[0]["id"] == "x"


def test_stale_items_excludes_recent():
    """Items con due_date hoy NO son stale."""
    today = datetime.now().isoformat()
    items = [{"id": "x", "text": "Hoy", "done": False, "due_date": today}]
    assert reminders.get_stale_important_items(items, days=2) == []


def test_stale_items_excludes_done():
    """Items ya marcados done NO aparecen en stale aunque su fecha haya pasado."""
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    items = [{"id": "x", "text": "Done", "done": True, "due_date": week_ago}]
    assert reminders.get_stale_important_items(items, days=2) == []


def test_stale_items_excludes_no_due_date():
    """Items sin due_date NUNCA son stale (no podemos inferir vencimiento)."""
    items = [{"id": "x", "text": "Sin fecha", "done": False}]
    assert reminders.get_stale_important_items(items, days=2) == []


def test_format_stale_for_prompt():
    """format_stale_for_prompt produce un listing legible."""
    week_ago = (datetime.now() - timedelta(days=5)).isoformat()
    stale = [{"id": "abc123", "text": "Evento ya pasó",
              "due_date": week_ago, "done": False}]
    out = reminders.format_stale_for_prompt(stale)
    assert "abc123" in out
    assert "Evento ya pasó" in out
    assert "venció" in out.lower()


# ══════════════════════════════════════════════════════════════════════
#  Reminder GC (housekeeping)
# ══════════════════════════════════════════════════════════════════════

def test_reminder_gc_keeps_pending():
    """Reminders no-fired NO se borran (GC solo afecta a fired)."""
    reminders.add_reminder("Future event", "2030-01-01T00:00:00")
    items = reminders.load_reminders()
    assert len(items) == 1


def test_reminder_gc_keeps_recently_fired():
    """Reminder fired hace 1 día NO se purga (cutoff es 7 días)."""
    reminders.add_reminder("Recent", "2026-04-26T10:00:00")
    rid = reminders.load_reminders()[0]["id"]
    reminders.mark_reminder_fired(rid)  # fired_at = now
    items = reminders.load_reminders()
    assert len(items) == 1
    assert items[0]["fired"] is True


def test_reminder_gc_purges_old_fired(tmp_path, monkeypatch):
    """Reminder fired hace >7 días se elimina al hacer load."""
    # Inyectamos manualmente un fired reminder con fired_at viejo
    from reflex_companion.memory import save_json
    old_fired_at = (datetime.now() - timedelta(days=10)).isoformat()
    save_json(reminders.REMINDERS_FILE, [{
        "id": "old", "text": "Viejo", "datetime": "2025-01-01T00:00:00",
        "created_at": "2025-01-01T00:00:00", "fired": True,
        "fired_at": old_fired_at,
    }])
    items = reminders.load_reminders()
    assert items == []  # GC borró el viejo
