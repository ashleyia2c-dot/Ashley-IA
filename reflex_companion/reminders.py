"""
reminders.py — Persistencia de recordatorios programados y lista de importants.

Recordatorios: el jefe le dice a Ashley "recuérdame X el martes a las 18:00".
  Ashley genera un [action:remind:YYYY-MM-DDTHH:MM:SS:texto] que lo guarda aquí.
  En _build_time_context() se comprueba si alguno venció y se inyecta en el prompt.

Importantes: el jefe (o Ashley) añade cosas a una lista persistente con
  [action:add_important:texto] (sin fecha) o
  [action:add_important:YYYY-MM-DDTHH:MM:texto] (con fecha de evento).
  Siempre visibles en el system prompt mientras estén pendientes.
  Se marcan como hechas con [action:done_important:texto_o_id].

  Items con fecha y que vencieron hace >2 días son detectados por
  get_stale_important_items() — Ashley puede preguntar al user si los
  limpia (vía [action:done_important]). Approach proactivo, no
  destructivo.

Housekeeping: reminders con fired=True hace más de 7 días se borran
  automáticamente al hacer load_reminders() — sin notificar al user.
  Es solo cleanup de archivo (evita acumular cientos de reminders
  vencidos). El comportamiento visible para el user no cambia.
"""

import uuid
import re
from datetime import datetime, timedelta

from .config import REMINDERS_FILE, IMPORTANT_FILE
from .memory import load_json, save_json

# Cuántos días después de la fecha del item importante avisamos al user.
# 2 días es la solicitud original — pasado un fin de semana, casi siempre
# significa que el evento ya ocurrió.
_STALE_IMPORTANT_DAYS = 2

# Cuántos días después de "fired" un reminder se borra del archivo.
# El user nunca ve esto — es housekeeping interno.
_REMINDER_GC_DAYS = 7


# ── Helpers internos ─────────────────────────────────────────────────────────
# Usan load_json/save_json centralizados de memory.py — tienen escritura
# atómica + fallback automático a .bak si el archivo principal se corrompe.

def _load(path: str) -> list:
    return load_json(path, [])


def _save(path: str, data: list) -> None:
    save_json(path, data)


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
    """Carga los reminders + housekeeping silencioso de fired antiguos.

    Reminders con fired=True hace más de _REMINDER_GC_DAYS se eliminan
    del archivo. Esto evita que el archivo crezca indefinidamente con
    eventos viejos. El user nunca interactúa con reminders fired (no
    aparecen en el prompt), así que el GC es invisible.
    """
    items = _load(REMINDERS_FILE)
    if not items:
        return items

    cutoff = datetime.now() - timedelta(days=_REMINDER_GC_DAYS)
    kept: list[dict] = []
    purged = False
    for r in items:
        if not r.get("fired"):
            kept.append(r)
            continue
        # Reminder fired — comparar fired_at (cuándo se marcó disparado).
        # Para reminders legacy sin fired_at, fallback a datetime (la
        # fecha del evento) — si el evento es viejo, probablemente
        # también el fired lo es.
        ref_iso = r.get("fired_at") or r.get("datetime", "")
        try:
            ref_dt = datetime.fromisoformat(ref_iso)
            if ref_dt < cutoff:
                purged = True
                continue  # skip — too old, GC
        except Exception:
            pass  # datetime inválido → mantener por seguridad
        kept.append(r)

    if purged:
        try:
            _save(REMINDERS_FILE, kept)
        except Exception:
            return items  # no romper el flow si el save falla
    return kept


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
    """Marca un reminder como disparado. Guarda `fired_at` con timestamp
    actual — usado por el GC interno (load_reminders) para borrar
    reminders fired hace más de _REMINDER_GC_DAYS.

    Hasta v0.14.2 no se guardaba fired_at — esos reminders legacy se
    GCean usando `datetime` (la fecha del evento) como fallback.
    """
    reminders = load_reminders()
    for r in reminders:
        if r["id"] == reminder_id:
            r["fired"] = True
            r["fired_at"] = datetime.now().isoformat()
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


def add_important(text: str, due_date: str | None = None) -> str:
    """Añade un elemento a la lista de importantes.

    Args:
        text: descripción del item (lo que el user quiere recordar).
        due_date: ISO datetime opcional de cuándo vence el evento. Si se
            provee, se usa para detectar items "stale" tras la fecha y
            preguntar al user si los limpia.

    Cuando Ashley emite el tag con fecha
    `[action:add_important:YYYY-MM-DDTHH:MM:texto]`, la action layer
    parsea la fecha y la pasa aquí. Sin fecha
    (`[action:add_important:texto]`) sigue funcionando — backward compat.
    """
    items = load_important()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "text": text,
        "created_at": datetime.now().isoformat(),
        "done": False,
    }
    if due_date:
        entry["due_date"] = due_date
    items.append(entry)
    _save(IMPORTANT_FILE, items)
    if due_date:
        return f"Añadido a importantes: '{text}' para {_fmt_dt(due_date)}."
    return f"Añadido a importantes: '{text}'."


def mark_important_done(text_or_id: str) -> str:
    """Marca un importante como hecho por id o texto parcial.

    Returns:
        - "Marcado como hecho: '<texto>'." si encontró un item PENDIENTE y lo marcó.
        - "" (string vacío) si el match fue contra un item que YA estaba hecho.
          Es el "señal de no-op" — el caller debe suprimir notificación.
        - "No encontré ..." si no hubo ningún match (ni done ni pendiente).

    El string vacío como señal de no-op evita el bug v0.17.2 donde Ashley
    re-emitía [action:done_important:X] varias veces sobre el mismo item y
    el user veía 3-4 notificaciones "Marcado como hecho" idénticas.

    Si hay múltiples items que matchean el mismo texto y algunos están
    done y otros no, marcamos el primer pendiente. Solo devolvemos noop
    si TODOS los matches estaban ya done.
    """
    items = load_important()
    saw_done_match = False
    for item in items:
        text_match = text_or_id.lower() in item["text"].lower()
        id_match = item["id"] == text_or_id
        if not (text_match or id_match):
            continue
        if item.get("done"):
            saw_done_match = True
            continue  # skip done, busca match pendiente
        # Primer match pendiente: marca y devuelve
        item["done"] = True
        _save(IMPORTANT_FILE, items)
        return f"Marcado como hecho: '{item['text']}'."
    # No hubo match pendiente
    if saw_done_match:
        return ""  # noop signal — caller suprime notificación
    return f"No encontré '{text_or_id}' en la lista de importantes."


def format_important_for_prompt(items: list[dict]) -> str:
    """Formatea la lista de importantes activos para el system prompt de Ashley."""
    pending = [i for i in items if not i.get("done")]
    if not pending:
        return ""
    lines = []
    for i in pending:
        due = i.get("due_date")
        if due:
            lines.append(f"- [{i['id']}] {i['text']} (fecha: {_fmt_dt(due)})")
        else:
            lines.append(f"- [{i['id']}] {i['text']}")
    return "\n".join(lines)


def get_stale_important_items(items: list[dict] | None = None,
                               days: int = _STALE_IMPORTANT_DAYS) -> list[dict]:
    """Devuelve items pendientes con `due_date` anterior a hace `days` días.

    Estos son los candidatos para que Ashley pregunte al user si los limpia
    ("ya pasó el evento, ¿lo borro?"). Items sin due_date NUNCA aparecen
    aquí — no podemos inferir su vencimiento sin parsear el texto y eso
    es heurístico/frágil.

    Items ya marcados done tampoco aparecen.
    """
    if items is None:
        items = load_important()
    cutoff = datetime.now() - timedelta(days=days)
    stale: list[dict] = []
    for i in items:
        if i.get("done"):
            continue
        due = i.get("due_date")
        if not due:
            continue
        try:
            due_dt = datetime.fromisoformat(due)
        except Exception:
            continue
        if due_dt < cutoff:
            stale.append(i)
    return stale


def format_stale_for_prompt(stale_items: list[dict]) -> str:
    """Formato del bloque que se inyecta al system prompt avisando a
    Ashley de items vencidos. Diseñado como una OBSERVACIÓN, no como
    instrucción imperativa: "estos vencieron — si encaja en la
    conversación, pregunta al user si los limpiamos".

    Ashley decide cuándo (no en cada turno — sería molesto). El user
    confirma con un "sí limpia X" → Ashley emite [action:done_important:X].
    """
    if not stale_items:
        return ""
    lines = []
    for i in stale_items:
        due = i.get("due_date", "?")
        lines.append(f"  - [{i['id']}] {i['text']} (venció {_fmt_dt(due)})")
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
