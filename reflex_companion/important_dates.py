"""
important_dates.py — Cumpleaños, aniversarios y fechas importantes (v0.18.0 Fase 2).

Sistema separado de "important items" (one-time todos) porque las fechas
importantes son ANUALES recurrentes — el cumpleaños del jefe se repite cada
año, no es un item que se marca como done.

Schema (fechas_importantes_ashley.json):
[
  {
    "id": "abc12345",
    "type": "birthday|anniversary|event",
    "who": "user" | "<nombre persona>",
    "date": "1995-03-15" | "03-15"   ← YYYY-MM-DD si se conoce el año, MM-DD si no
    "label": "Mathieu's birthday" | "Bodas con María",
    "created_at": "ISO timestamp"
  }
]

Uso típico desde Ashley:
  - User: "mi cumple es el 15 de marzo"
  - Ashley emite: [action:save_date:birthday:03-15:user]
  - Cada vez que el prompt se construye:
    - Si HOY es 15 de marzo → línea celebratoria al prompt
    - Si en próximos 7 días → línea preparatoria al prompt

Diseño anti-frágil:
  - MM-DD permite recurrencia anual sin reasignar año.
  - YYYY-MM-DD permite calcular edad si tipo es "birthday" del user.
  - Atomic save vía memory.save_json (mismo patrón que tastes/reminders).
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from .config import IMPORTANT_DATES_FILE
from .memory import load_json, now_iso, save_json

_log = logging.getLogger("ashley.important_dates")


# Tipos válidos. Si Ashley emite uno fuera de esta lista, normalizamos a "event".
VALID_TYPES = {"birthday", "anniversary", "event"}


# ─────────────────────────────────────────────
#  Helpers internos
# ─────────────────────────────────────────────


def _parse_date_to_md(date_str: str) -> Optional[str]:
    """Normaliza un date string a 'MM-DD' (solo el mes y día, sin año).

    Acepta:
      - 'YYYY-MM-DD' → devuelve 'MM-DD'
      - 'MM-DD'      → devuelve 'MM-DD' (ya está)
      - cualquier otro formato → None

    El MM-DD es la clave para matching anual recurrente.
    """
    if not date_str:
        return None
    s = date_str.strip()
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return f"{m.group(2)}-{m.group(3)}"
    # MM-DD
    m = re.match(r"^(\d{2})-(\d{2})$", s)
    if m:
        return s
    return None


def _extract_year(date_str: str) -> Optional[int]:
    """Devuelve el año si el date_str tiene formato YYYY-MM-DD, sino None."""
    if not date_str:
        return None
    m = re.match(r"^(\d{4})-\d{2}-\d{2}$", date_str.strip())
    return int(m.group(1)) if m else None


def _validate_md(md: str) -> bool:
    """Verifica que MM-DD es una fecha válida del calendario."""
    try:
        m, d = md.split("-")
        # Año bisiesto para permitir 02-29
        date(2000, int(m), int(d))
        return True
    except (ValueError, AttributeError):
        return False


# ─────────────────────────────────────────────
#  CRUD básico
# ─────────────────────────────────────────────


def load_dates() -> list[dict]:
    """Devuelve la lista de fechas importantes. Vacía si no hay archivo."""
    return load_json(IMPORTANT_DATES_FILE, [])


def save_dates(items: list[dict]) -> None:
    """Persist atómico vía save_json (con .bak fallback)."""
    save_json(IMPORTANT_DATES_FILE, items)


def add_date(
    type_: str,
    date_str: str,
    label: str,
    who: str = "user",
) -> Optional[dict]:
    """Añade una fecha importante. Devuelve el dict guardado o None si inválido.

    type_ se normaliza a uno de VALID_TYPES (default "event").
    date_str se valida y normaliza a MM-DD para matching anual.
    label es free-form.
    who es "user" para fechas del propio user, o nombre de persona para terceros.

    Si ya existe una fecha con MISMO type + MISMO who + MISMO MM-DD → no duplica,
    solo actualiza el label y devuelve la existente. Esto evita que Ashley acumule
    duplicados si el user vuelve a mencionar su cumpleaños.
    """
    md = _parse_date_to_md(date_str)
    if md is None or not _validate_md(md):
        _log.warning("add_date: invalid date_str=%r", date_str)
        return None

    norm_type = type_.lower().strip() if type_ else "event"
    if norm_type not in VALID_TYPES:
        norm_type = "event"

    norm_who = (who or "user").strip().lower() if (who or "").strip() else "user"
    label = (label or "").strip()
    if not label:
        # Sin label, no tiene sentido — Ashley necesita saber qué evento es
        _log.warning("add_date: empty label, rejecting")
        return None

    items = load_dates()

    # Anti-duplicado: mismo type + who + MM-DD → update label
    for it in items:
        existing_md = _parse_date_to_md(it.get("date", ""))
        if (
            it.get("type") == norm_type
            and (it.get("who") or "user").lower() == norm_who
            and existing_md == md
        ):
            it["label"] = label
            # Si el nuevo aporta año (YYYY-MM-DD) y el viejo no, actualizamos
            new_year = _extract_year(date_str)
            if new_year and not _extract_year(it.get("date", "")):
                it["date"] = date_str.strip()
            save_dates(items)
            return it

    entry = {
        "id": str(uuid.uuid4())[:8],
        "type": norm_type,
        "who": norm_who,
        "date": date_str.strip(),  # guardamos el original (preserva año si lo tenía)
        "label": label,
        "created_at": now_iso(),
    }
    items.append(entry)
    save_dates(items)
    return entry


def remove_date(date_id: str) -> bool:
    """Borra por id. Devuelve True si encontró y borró, False si no existe."""
    items = load_dates()
    new_items = [it for it in items if it.get("id") != date_id]
    if len(new_items) == len(items):
        return False
    save_dates(new_items)
    return True


# ─────────────────────────────────────────────
#  Matching de fechas — hoy, próximas
# ─────────────────────────────────────────────


def get_today_dates(today: Optional[date] = None) -> list[dict]:
    """Fechas que CAEN hoy (matching por MM-DD anual recurrente).

    today: opcional, default = local date now. Útil para tests.
    """
    if today is None:
        today = date.today()
    today_md = today.strftime("%m-%d")
    out = []
    for it in load_dates():
        md = _parse_date_to_md(it.get("date", ""))
        if md == today_md:
            out.append(it)
    return out


def get_upcoming_dates(
    days_ahead: int = 7,
    today: Optional[date] = None,
) -> list[dict]:
    """Fechas que caen en los próximos `days_ahead` días (excluyendo HOY).

    Usa MM-DD para matching anual recurrente. Maneja correctamente el wrap
    de año (ej: hoy 28 dic, 7 días ahead incluye 03 ene del año siguiente).

    Devuelve cada item enriquecido con `days_until: int` (1 = mañana, 7 = en
    una semana). Ordenado de más cercano a más lejano.
    """
    if today is None:
        today = date.today()
    if days_ahead < 1:
        return []

    upcoming_mds = {}
    for offset in range(1, days_ahead + 1):
        day = today + timedelta(days=offset)
        md = day.strftime("%m-%d")
        # Si dos offsets diferentes dan el mismo MM-DD (imposible salvo edge
        # case), nos quedamos con el offset menor.
        if md not in upcoming_mds:
            upcoming_mds[md] = offset

    out = []
    for it in load_dates():
        md = _parse_date_to_md(it.get("date", ""))
        if md in upcoming_mds:
            enriched = dict(it)
            enriched["days_until"] = upcoming_mds[md]
            out.append(enriched)
    out.sort(key=lambda x: x["days_until"])
    return out


# ─────────────────────────────────────────────
#  Formato para el system prompt de Ashley
# ─────────────────────────────────────────────


def _label_with_who(item: dict) -> str:
    """Formato 'label' o 'label (who)' si who != user.

    'Cumpleaños del jefe' suele tener who='user' y label='cumpleaños del jefe'
    → mostramos solo label.
    'Cumpleaños de mamá' tiene who='mamá' → mostramos label tal cual.
    """
    return item.get("label", "")


def format_dates_for_prompt(
    today: Optional[date] = None,
    upcoming_days: int = 7,
    lang: str = "en",
) -> str:
    """Formatea fechas hoy + próximas para inyectar al system prompt.

    Devuelve string vacío si no hay nada relevante (ni hoy ni próximas) →
    el prompt no añade sección, no rompe cache.

    Estructura del output (cuando hay contenido):
      ⭐ HOY: <label> (es <type>)
      📅 PRÓXIMAS:
        - en X días: <label> (<type>)
        - en Y días: <label> (<type>)
    """
    today_items = get_today_dates(today)
    upcoming_items = get_upcoming_dates(days_ahead=upcoming_days, today=today)

    if not today_items and not upcoming_items:
        return ""

    # i18n inline (no añadimos a TIME_CTX porque esto es contexto distinto)
    L = (lang or "en").strip().lower()[:2]
    if L == "es":
        head_today = "⭐ HOY:"
        head_upcoming = "📅 PRÓXIMOS DÍAS:"
        in_x_days = "en {n} día"
        in_x_days_pl = "en {n} días"
        type_labels = {"birthday": "cumpleaños", "anniversary": "aniversario", "event": "evento"}
    elif L == "fr":
        head_today = "⭐ AUJOURD'HUI :"
        head_upcoming = "📅 PROCHAINS JOURS :"
        in_x_days = "dans {n} jour"
        in_x_days_pl = "dans {n} jours"
        type_labels = {"birthday": "anniversaire", "anniversary": "anniversaire", "event": "événement"}
    else:
        head_today = "⭐ TODAY:"
        head_upcoming = "📅 UPCOMING:"
        in_x_days = "in {n} day"
        in_x_days_pl = "in {n} days"
        type_labels = {"birthday": "birthday", "anniversary": "anniversary", "event": "event"}

    lines = []
    if today_items:
        lines.append(head_today)
        for it in today_items:
            t = type_labels.get(it.get("type", "event"), "event")
            lines.append(f"  - {_label_with_who(it)} ({t})")

    if upcoming_items:
        if today_items:
            lines.append("")  # separador visual
        lines.append(head_upcoming)
        for it in upcoming_items:
            n = it["days_until"]
            tmpl = in_x_days if n == 1 else in_x_days_pl
            t = type_labels.get(it.get("type", "event"), "event")
            lines.append(f"  - {tmpl.format(n=n)}: {_label_with_who(it)} ({t})")

    return "\n".join(lines)
