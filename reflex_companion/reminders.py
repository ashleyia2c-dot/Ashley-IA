"""
reminders.py — Persistencia de recordatorios programados y lista de importants.

Recordatorios: el jefe le dice a Ashley "recuérdame X el martes a las 18:00".
  Ashley genera un [action:remind:YYYY-MM-DDTHH:MM:SS:texto] que lo guarda aquí.
  En _build_time_context() se comprueba si alguno venció y se inyecta en el prompt.

Importantes: el jefe (o Ashley) añade cosas a una lista persistente con
  [action:add_important:texto]. Siempre visibles en el system prompt.
  Se marcan como hechas con [action:done_important:texto_o_id].
"""

import json
import os
import uuid
import re
from datetime import datetime

from .config import REMINDERS_FILE, IMPORTANT_FILE


# ── Helpers internos ─────────────────────────────────────────────────────────

def _load(path: str) -> list:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(path: str, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parse_dt(dt_str: str) -> datetime:
    """Parsea ISO datetime; devuelve datetime.max si no se puede (nunca vence)."""
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return datetime.max


def _fmt_dt(dt_str: str) -> str:
    """Devuelve fecha/hora en formato legible español."""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d/%m/%Y a las %H:%M")
    except Exception:
        return dt_str


# ── Recordatorios ─────────────────────────────────────────────────────────────

def load_reminders() -> list[dict]:
    return _load(REMINDERS_FILE)


def add_reminder(text: str, dt_iso: str) -> str:
    """Añade un recordatorio. Devuelve mensaje de confirmación."""
    reminders = load_reminders()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "datetime": dt_iso,
        "created_at": datetime.now().isoformat(),
        "fired": False,
    }
    reminders.append(entry)
    _save(REMINDERS_FILE, reminders)
    return f"Recordatorio guardado: '{text}' para el {_fmt_dt(dt_iso)}."


def get_due_reminders() -> list[dict]:
    """Recordatorios cuya hora ya llegó/pasó y no han sido disparados."""
    now = datetime.now()
    return [r for r in load_reminders() if not r.get("fired") and _parse_dt(r.get("datetime", "")) <= now]


def mark_reminder_fired(reminder_id: str) -> None:
    reminders = load_reminders()
    for r in reminders:
        if r["id"] == reminder_id:
            r["fired"] = True
    _save(REMINDERS_FILE, reminders)


def delete_reminder(text_or_id: str) -> str:
    """Elimina un recordatorio por id o por texto parcial."""
    reminders = load_reminders()
    before = len(reminders)
    reminders = [
        r for r in reminders
        if r["id"] != text_or_id and text_or_id.lower() not in r["text"].lower()
    ]
    if len(reminders) < before:
        _save(REMINDERS_FILE, reminders)
        return f"Recordatorio '{text_or_id}' eliminado."
    return f"No encontré recordatorio '{text_or_id}'."


def format_reminders_for_prompt(reminders: list[dict]) -> str:
    """Formatea recordatorios pendientes para el system prompt de Ashley."""
    pending = [r for r in reminders if not r.get("fired")]
    if not pending:
        return ""
    lines = []
    for r in pending:
        lines.append(f"- [{r['id']}] {r['text']} → {_fmt_dt(r['datetime'])}")
    return "\n".join(lines)


# ── Importantes ───────────────────────────────────────────────────────────────

def load_important() -> list[dict]:
    return _load(IMPORTANT_FILE)


def add_important(text: str) -> str:
    """Añade un elemento a la lista de importantes."""
    items = load_important()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "created_at": datetime.now().isoformat(),
        "done": False,
    }
    items.append(entry)
    _save(IMPORTANT_FILE, items)
    return f"Añadido a importantes: '{text}'."


def mark_important_done(text_or_id: str) -> str:
    """Marca un importante como hecho por id o texto parcial."""
    items = load_important()
    for item in items:
        if item["id"] == text_or_id or text_or_id.lower() in item["text"].lower():
            item["done"] = True
            _save(IMPORTANT_FILE, items)
            return f"Marcado como hecho: '{item['text']}'."
    return f"No encontré '{text_or_id}' en la lista de importantes."


def format_important_for_prompt(items: list[dict]) -> str:
    """Formatea la lista de importantes activos para el system prompt de Ashley."""
    pending = [i for i in items if not i.get("done")]
    if not pending:
        return ""
    lines = [f"- [{i['id']}] {i['text']}" for i in pending]
    return "\n".join(lines)


# ── Parser de datetime desde tag de acción ────────────────────────────────────

def parse_remind_params(rest: str) -> list[str]:
    """
    Parsea el contenido de [action:remind:...] en [dt_iso, texto].
    El formato esperado es: YYYY-MM-DDTHH:MM:SS:texto (o HH:MM sin segundos).
    Usa regex para no confundir los : del tiempo con el : separador.
    """
    m = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?):(.+)', rest)
    if m:
        return [m.group(1), m.group(2)]
    # Fallback: solo datetime sin texto
    return [rest] if rest else []
