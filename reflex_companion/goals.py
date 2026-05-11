"""
goals.py — Tracking de objetivos personales del jefe (v0.18.0 Fase 3).

Sistema separado de "important items" (one-time todos) y "important dates"
(eventos recurrentes anuales) porque los goals son OBJETIVOS de largo plazo
con progreso continuo:

  - "Aprender francés"        — meses de práctica
  - "Correr 5K sin parar"      — semanas de entrenamiento
  - "Lanzar Ashley"            — proyecto multi-mes
  - "Leer 12 libros este año"  — meta anual

Schema (objetivos_ashley.json):
[
  {
    "id": "abc12345",
    "goal": "Aprender francés",
    "category": "personal|profesional|salud|aprendizaje|otros",
    "created_at": "ISO timestamp",
    "completed": false,
    "completed_at": null | "ISO timestamp",
    "last_check_in": null | "ISO timestamp"   ← cuándo Ashley preguntó por última vez
  }
]

Uso típico:
  - User menciona aprender algo → Ashley emite [action:save_goal:CAT:GOAL]
  - Cada N días Ashley ve el goal en el prompt marcado como "due for check-in"
  - Si encaja en conversación natural, pregunta cómo va → emite check_in_goal:ID
  - User confirma terminado → Ashley emite complete_goal:ID

Diseño anti-coach-pesada:
  - Check-in cadence default: 10 días (no 1, evita preguntas constantes)
  - Goals completed se archivan (no se borran), para que Ashley pueda
    referenciarlos como historia ("¿te acuerdas cuando aprendías francés?")
  - El prompt instruye a Ashley a NO insistir si el user da respuesta corta
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import GOALS_FILE
from .memory import load_json, now_iso, save_json

_log = logging.getLogger("ashley.goals")


# Categorías sugeridas (no obligatorias — Ashley puede usar cualquiera).
SUGGESTED_CATEGORIES = (
    "personal", "profesional", "salud", "aprendizaje", "otros",
)

# Días sin check-in tras los cuales el goal se marca como "due" (para que
# Ashley considere preguntar). 10 días es suave — no acosa, pero tampoco
# olvida los goals durante meses.
DEFAULT_CHECK_IN_DAYS = 10


# ─────────────────────────────────────────────
#  CRUD básico
# ─────────────────────────────────────────────


def load_goals() -> list[dict]:
    """Devuelve la lista completa de goals (activos + completados).

    El caller filtra por completed según necesite.
    """
    return load_json(GOALS_FILE, [])


def save_goals(items: list[dict]) -> None:
    """Persist atómico vía save_json (con .bak fallback)."""
    save_json(GOALS_FILE, items)


def add_goal(goal: str, category: str = "personal") -> Optional[dict]:
    """Añade un goal nuevo. Devuelve el dict guardado o None si inválido.

    Anti-duplicado: si ya hay un goal ACTIVO con el mismo texto (case-insensitive),
    no duplica — devuelve el existente. Goals completados con mismo texto SÍ
    permiten crear uno nuevo (puede ser un "renew" — empezar a aprender otro idioma).
    """
    goal_text = (goal or "").strip()
    if not goal_text:
        _log.warning("add_goal: empty goal text, rejecting")
        return None

    cat = (category or "personal").strip().lower() or "personal"

    items = load_goals()

    # Anti-duplicado: solo contra goals ACTIVOS
    for it in items:
        if it.get("completed"):
            continue
        if (it.get("goal") or "").strip().lower() == goal_text.lower():
            return it  # ya existe activo

    entry = {
        "id": str(uuid.uuid4())[:8],
        "goal": goal_text,
        "category": cat,
        "created_at": now_iso(),
        "completed": False,
        "completed_at": None,
        "last_check_in": None,
    }
    items.append(entry)
    save_goals(items)
    return entry


def _find_goal(text_or_id: str, items: list[dict]) -> Optional[dict]:
    """Busca un goal por id exacto o por substring del texto (case-insensitive).

    Solo match contra goals ACTIVOS. Si hay varios matches por substring,
    devuelve el primero (Ashley puede ser más específica si pasa).
    """
    if not text_or_id:
        return None
    needle = text_or_id.strip().lower()
    for it in items:
        if it.get("completed"):
            continue
        if it.get("id") == text_or_id:
            return it
        if needle in (it.get("goal") or "").lower():
            return it
    return None


def mark_check_in(text_or_id: str, lang: str = "en") -> str:
    """Ashley confirma que acaba de preguntar al jefe por progreso de un goal.

    Actualiza last_check_in al timestamp actual. Esto evita que el goal
    aparezca como "due" en próximos N días.

    Returns:
      - "Check-in registrado: '<goal>'." si encontró el goal
      - "" (string vacío) si ya estaba checked-in HOY (idempotente, evita
        burbuja duplicada en chat — mismo pattern que done_important).
      - "No encontré ..." si no hubo match.
    """
    from .actions import _amsg
    items = load_goals()
    item = _find_goal(text_or_id, items)
    if item is None:
        return _amsg(lang, "goal_not_found", goal=text_or_id)

    # Idempotente: si ya hay check-in hoy, no spam
    if item.get("last_check_in"):
        try:
            last = datetime.fromisoformat(item["last_check_in"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if (now - last).total_seconds() < 3600 * 6:
                return ""  # noop signal
        except (ValueError, TypeError) as _e:
            # v0.19.24 — antes era except Exception:pass silente. Si el
            # timestamp last_check_in está corrupto, ahora logueamos.
            import logging
            logging.getLogger("ashley.goals").warning(
                "mark_check_in: last_check_in corrupto %r: %s",
                item.get("last_check_in"), _e,
            )

    item["last_check_in"] = now_iso()
    save_goals(items)
    return _amsg(lang, "goal_check_in", goal=item["goal"])


def complete_goal(text_or_id: str, lang: str = "en") -> str:
    """Marca un goal como completado.

    Returns:
      - "🎉 Objetivo completado: '<goal>'." si encontró el goal pendiente
      - "" si ya estaba completado (noop signal)
      - "No encontré ..." si no hubo match
    """
    from .actions import _amsg
    items = load_goals()
    item = _find_goal(text_or_id, items)
    if item is None:
        for it in items:
            if it.get("completed") and (
                it.get("id") == text_or_id
                or text_or_id.strip().lower() in (it.get("goal") or "").lower()
            ):
                return ""  # noop
        return _amsg(lang, "goal_not_found", goal=text_or_id)

    item["completed"] = True
    item["completed_at"] = now_iso()
    save_goals(items)
    return _amsg(lang, "goal_completed", goal=item["goal"])


# ─────────────────────────────────────────────
#  Queries para inyección al prompt
# ─────────────────────────────────────────────


def get_active_goals() -> list[dict]:
    """Devuelve solo goals NO completados, ordenados por created_at descendente
    (más recientes primero, suelen ser más relevantes)."""
    items = [it for it in load_goals() if not it.get("completed")]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_recent_completed_goals(limit: int = 3) -> list[dict]:
    """Goals completados recientemente (ordenados por completed_at descendente).

    Útil para que Ashley pueda referenciarlos: "te acuerdas cuando aprendiste X".
    """
    items = [it for it in load_goals() if it.get("completed")]
    items.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    return items[:limit]


def days_since_check_in(goal: dict, now: Optional[datetime] = None) -> Optional[int]:
    """Días desde el último check-in (None si nunca tuvo check-in)."""
    last = goal.get("last_check_in")
    if not last:
        return None
    try:
        dt = datetime.fromisoformat(last)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if now is None:
            now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return None


def days_since_creation(goal: dict, now: Optional[datetime] = None) -> Optional[int]:
    """Días desde que se creó el goal."""
    created = goal.get("created_at")
    if not created:
        return None
    try:
        dt = datetime.fromisoformat(created)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if now is None:
            now = datetime.now(timezone.utc)
        return (now - dt).days
    except Exception:
        return None


def is_due_for_check_in(
    goal: dict,
    threshold_days: int = DEFAULT_CHECK_IN_DAYS,
    now: Optional[datetime] = None,
) -> bool:
    """True si el goal lleva >= threshold_days sin check-in.

    Para goals que NUNCA tuvieron check-in: usar created_at + threshold extra
    (no marcar como due en los primeros días tras crearlo — molesto).
    """
    days_check = days_since_check_in(goal, now=now)
    if days_check is not None:
        return days_check >= threshold_days
    # Nunca check-in → mirar created_at, dar extra grace period
    days_create = days_since_creation(goal, now=now)
    if days_create is None:
        return False
    return days_create >= threshold_days


# ─────────────────────────────────────────────
#  Format for prompt
# ─────────────────────────────────────────────


def format_goals_for_prompt(lang: str = "en") -> str:
    """Formatea los goals activos del jefe para inyectar al system prompt.

    Devuelve string vacío si no hay goals activos → no se añade sección
    al prompt → cero impacto en cache.

    Marca con ⏰ los goals "due for check-in" para que Ashley los priorice
    si la conversación da pie.
    """
    actives = get_active_goals()
    if not actives:
        return ""

    L = (lang or "en").strip().lower()[:2]
    if L == "es":
        head = "OBJETIVOS DEL JEFE (largo plazo):"
        days_ago_one = "creado hace {n} día"
        days_ago_pl = "creado hace {n} días"
        no_check_in = "aún no has preguntado"
        check_in_one = "última vez que preguntaste hace {n} día"
        check_in_pl = "última vez que preguntaste hace {n} días"
        recent_check = "recién hablaste de esto"
        due_marker = "⏰"
        hint = (
            "⏰ marca goals que llevan tiempo sin que les hayas preguntado. "
            "Si encaja en la conversación natural, pregunta UNO con curiosidad — "
            "no listes todos. Si el jefe da respuesta corta ('voy bien' / "
            "'no he avanzado'), regístralo y déjalo, no insistas. "
            "Si el jefe dice que YA terminó algo, emite [action:complete_goal:ID_O_TEXTO]. "
            "Cuando preguntes por progreso, emite [action:check_in_goal:ID_O_TEXTO] "
            "(silencioso, no genera burbuja extra)."
        )
    elif L == "fr":
        head = "OBJECTIFS DU PATRON (long terme) :"
        days_ago_one = "créé il y a {n} jour"
        days_ago_pl = "créé il y a {n} jours"
        no_check_in = "tu n'as pas encore demandé"
        check_in_one = "dernière fois que tu as demandé il y a {n} jour"
        check_in_pl = "dernière fois que tu as demandé il y a {n} jours"
        recent_check = "tu en as parlé récemment"
        due_marker = "⏰"
        hint = (
            "⏰ marque les objectifs sans nouvelles depuis longtemps. "
            "Si la conversation s'y prête, demande UN seul avec curiosité — "
            "ne liste pas tous. Si le patron répond court ('ça avance' / "
            "'pas vraiment'), enregistre et laisse, n'insiste pas. "
            "S'il dit qu'il a TERMINÉ quelque chose, émets [action:complete_goal:ID_OU_TEXTE]. "
            "Quand tu demandes pour le progrès, émets [action:check_in_goal:ID_OU_TEXTE] "
            "(silencieux, pas de bulle supplémentaire)."
        )
    else:
        head = "BOSS'S GOALS (long-term):"
        days_ago_one = "created {n} day ago"
        days_ago_pl = "created {n} days ago"
        no_check_in = "you haven't asked yet"
        check_in_one = "last asked {n} day ago"
        check_in_pl = "last asked {n} days ago"
        recent_check = "you talked about it recently"
        due_marker = "⏰"
        hint = (
            "⏰ marks goals you haven't asked about in a while. "
            "If the conversation fits, ask ONE with curiosity — don't list "
            "them all. If the boss gives a short answer ('going well' / "
            "'haven't progressed'), record it and let it go, don't insist. "
            "If the boss says he FINISHED something, emit [action:complete_goal:ID_OR_TEXT]. "
            "When you ask about progress, emit [action:check_in_goal:ID_OR_TEXT] "
            "(silent, doesn't generate extra bubble)."
        )

    lines = [head]
    now = datetime.now(timezone.utc)
    for g in actives:
        days_create = days_since_creation(g, now=now) or 0
        days_check = days_since_check_in(g, now=now)
        cat = g.get("category", "otros")
        gtext = g.get("goal", "")
        gid = g.get("id", "?")

        # Construir descripción temporal
        if days_create == 0:
            time_part = "creado hoy" if L == "es" else (
                "créé aujourd'hui" if L == "fr" else "created today"
            )
        else:
            tmpl = days_ago_one if days_create == 1 else days_ago_pl
            time_part = tmpl.format(n=days_create)

        if days_check is None:
            check_part = no_check_in
        elif days_check == 0:
            check_part = recent_check
        else:
            tmpl = check_in_one if days_check == 1 else check_in_pl
            check_part = tmpl.format(n=days_check)

        marker = (
            f" {due_marker}"
            if is_due_for_check_in(g, now=now)
            else ""
        )
        lines.append(
            f"  - [{cat}] [{gid}] {gtext} ({time_part}, {check_part}){marker}"
        )

    lines.append("")
    lines.append(hint)
    return "\n".join(lines)
