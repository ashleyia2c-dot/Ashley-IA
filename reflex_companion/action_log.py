"""
action_log.py — Logging estructurado de las acciones que ejecuta Ashley.

Cada vez que Ashley dispara una acción del sistema (volume, open_app,
hotkey, etc.) guardamos una entry con:

  - timestamp ISO
  - user_intent: el último mensaje del user (lo que pidió)
  - action_type / action_params: lo que Ashley emitió
  - action_description: la descripción human-readable que vio el user
  - result: lo que devolvió execute_action
  - state_before / state_after: snapshots del estado del sistema antes
    y después de la acción (volumen, ventana, etc.)
  - mismatch: True si el state_after NO coincide con lo esperado dado
    el action_type/params (e.g. action='volume:set:100' pero
    state_after.volume_pct=0)

El log sirve para:

  1. **Debugging**: cuando el user reporta "Ashley se equivocó", podemos
     ver QUÉ pasó exactamente — qué pidió, qué se ejecutó, qué resultó.

  2. **Auto-mejora**: con tiempo, vemos qué casos fallan más (ej: "al
     máximo" mapea mal a `volume:set:0` el 30% de las veces). Esos
     casos guían qué partes del prompt o del action layer hay que
     mejorar.

Cap a 500 entries — más que suficiente para inspeccionar patrones de
las últimas 1-2 semanas de uso. Los más viejos se descartan.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from .config import ACTION_LOG_FILE
from .memory import load_json, save_json


MAX_ACTION_LOG_ENTRIES = 500

_log = logging.getLogger("ashley.action_log")


def _check_volume_mismatch(action_type: str, params: list,
                            state_before: dict, state_after: dict) -> Optional[str]:
    """Para acciones de volumen, comparar lo esperado vs lo real.
    Devuelve None si OK, string descriptivo si hay mismatch."""
    if action_type != "volume":
        return None
    if not params:
        return None

    sub = params[0]
    val = params[1] if len(params) > 1 else None

    vol_after = state_after.get("volume_pct")
    vol_before = state_before.get("volume_pct")
    muted_after = state_after.get("volume_muted")
    muted_before = state_before.get("volume_muted")

    if vol_after is None or vol_before is None:
        # Sin datos de pycaw — no podemos verificar
        return None

    if sub == "set" and val is not None:
        try:
            target = int(val)
            # Tolerancia ±2% para evitar falsos positivos por redondeo
            if abs(vol_after - target) > 2:
                return f"set:{target} requested but volume is {vol_after}%"
        except (ValueError, TypeError):
            return f"set requested with non-numeric value '{val}'"
    elif sub == "up":
        if vol_after <= vol_before and vol_after < 100:
            return f"up requested but volume went {vol_before}% → {vol_after}%"
    elif sub == "down":
        if vol_after >= vol_before and vol_after > 0:
            return f"down requested but volume went {vol_before}% → {vol_after}%"
    elif sub == "mute":
        if muted_after == muted_before:
            return f"mute toggle requested but mute state unchanged ({muted_after})"
    return None


def log_action_result(user_intent: str,
                       action_type: str,
                       action_params: list,
                       action_description: str,
                       result: Any,
                       state_before: Optional[dict] = None,
                       state_after: Optional[dict] = None) -> None:
    """Guarda una entry en el log de acciones. Idempotente, fail-safe.

    Si cualquier cosa falla (disco lleno, JSON inválido), loguea
    warning y sigue — NUNCA debe romper el flow de la app.
    """
    try:
        state_before = state_before or {}
        state_after = state_after or {}

        mismatch = _check_volume_mismatch(
            action_type, action_params or [], state_before, state_after,
        )

        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_intent": (user_intent or "")[:500],
            "action_type": action_type,
            "action_params": list(action_params or []),
            "action_description": (action_description or "")[:200],
            "result": str(result)[:500] if result is not None else "",
            "state_before": state_before,
            "state_after": state_after,
            "mismatch": mismatch,
        }

        existing = load_json(ACTION_LOG_FILE, [])
        if not isinstance(existing, list):
            existing = []
        existing.insert(0, entry)
        if len(existing) > MAX_ACTION_LOG_ENTRIES:
            existing = existing[:MAX_ACTION_LOG_ENTRIES]
        save_json(ACTION_LOG_FILE, existing)

        if mismatch:
            _log.warning("action mismatch: %s — %s", action_type, mismatch)
    except Exception as e:
        _log.warning("failed to log action: %s", e)


def load_recent_actions(n: int = 50) -> list[dict]:
    """Carga las N últimas entries del log. Para inspección manual o
    eventual UI de 'historial de acciones'."""
    data = load_json(ACTION_LOG_FILE, [])
    if not isinstance(data, list):
        return []
    return data[:n]


def count_mismatches(n: int = 100) -> int:
    """Cuenta cuántas de las N últimas acciones tuvieron mismatch.
    Útil para health metrics: 'el 12% de las acciones falla'."""
    return sum(1 for e in load_recent_actions(n) if e.get("mismatch"))
