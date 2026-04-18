"""
stats.py — Contador persistente de mensajes del usuario, con protección
anti-manipulación en 3 capas.

Motivación:
La política de reembolso es "14 días con max 40 mensajes enviados". Cuando
alguien pide refund, necesitamos poder verificar que está bajo el umbral.
El user ve su contador en Settings → lo captura y nos lo manda por email.

Capas de protección (ordenadas por esfuerzo para vulnerarlas):

  1. HMAC signature sobre el JSON — el usuario no puede editar el
     contador a mano sin romper la firma. Al arrancar detectamos el
     tampering y ponemos el contador en modo "envenenado".

  2. Mirror en Windows Registry (HKCU\\Software\\Ashley\\Stats) — aun si
     el user borra o edita el JSON, el valor del registro sigue vivo.
     Al cargar tomamos el MÁXIMO de ambas fuentes.

  3. Cross-check con historial_ashley.json — si el archivo de historial
     tiene 50 entradas (el máximo) pero el contador dice "5", es mentira
     obvia. Esto se usa como sanity check adicional en
     `is_tampered_vs_history()`.

Importante: esto NO es protección criptográfica de nivel militar. Un
reverse engineer con tiempo lo romperá. El objetivo es desincentivar al
95% de los usuarios (los que googlearían "editar stats Ashley") sin
añadir complejidad innecesaria.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Optional

from .config import STATS_FILE
from .memory import load_json, now_iso, save_json

_log = logging.getLogger("ashley.stats")


# ─────────────────────────────────────────────
#  Configuración
# ─────────────────────────────────────────────

# Clave para HMAC. Obfuscada en trozos para que un simple `grep "secret"` no
# la encuentre. NO es un secreto criptográfico — un reverse-engineer lo
# encontrará. Sirve contra tampering casual.
_SECRET_PARTS = (
    b"ashley-stats-v1",
    b"-7e8b3c4d",
    b"-5f6a1b2c",
    b"-hmac-key",
)
_SECRET = b"".join(_SECRET_PARTS)

# Umbral de tampering. Cuando detectamos manipulación, ponemos el contador
# en este valor — suficientemente alto para que ningún threshold razonable
# se pueda cumplir, pero no MAX_INT (por si algún cálculo se pasa de largo).
_POISONED_COUNT = 9999

# Registry path. Solo se usa en Windows. En otros OS (tests, CI) lo saltamos.
_REG_PATH = r"Software\Ashley\Stats"


# ─────────────────────────────────────────────
#  HMAC signing
# ─────────────────────────────────────────────

def _canonical_payload(data: dict) -> bytes:
    """Serialización determinista para firmar."""
    # sort_keys=True garantiza que {"a":1,"b":2} y {"b":2,"a":1} den la
    # misma firma. separators evita espacios que podrían diferir entre
    # plataformas al re-serializar.
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign(data: dict) -> str:
    return hmac.new(_SECRET, _canonical_payload(data), hashlib.sha256).hexdigest()


def _verify(data: dict, expected_sig: str) -> bool:
    # hmac.compare_digest evita timing attacks (minúscula pero incluida por higiene)
    return hmac.compare_digest(_sign(data), expected_sig)


# ─────────────────────────────────────────────
#  Registry mirror (Windows only)
# ─────────────────────────────────────────────

def _registry_available() -> bool:
    """True si podemos acceder al registro (solo Windows)."""
    try:
        import winreg  # noqa: F401
        return True
    except ImportError:
        return False


def _load_from_registry() -> Optional[dict]:
    """Lee el mirror del registro. None si no existe o está corrupto."""
    if not _registry_available():
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            count, _ = winreg.QueryValueEx(key, "total_messages")
            first_at, _ = winreg.QueryValueEx(key, "first_message_at")
            sig, _ = winreg.QueryValueEx(key, "sig")
        # Verificar firma — si alguien tocó el registro, lo detectamos igual.
        # IMPORTANTE: usamos la misma convención que _save_to_registry — cadena
        # vacía (no None) cuando first_message_at no está seteado. Si hacemos
        # `first_at or None` aquí pero el save firmó con "", las firmas no
        # cuadran y damos falsos positivos de tampering.
        first_at_str = first_at or ""
        payload = {"total_messages": int(count), "first_message_at": first_at_str}
        if not _verify(payload, sig):
            _log.warning("registry mirror signature mismatch — treating as tampered")
            return {
                "total_user_messages": _POISONED_COUNT,
                "first_message_at": first_at_str or None,
                "_tampered": True,
            }
        return {
            "total_user_messages": int(count),
            "first_message_at": first_at_str or None,  # convertimos "" -> None para el caller
            "_tampered": False,
        }
    except FileNotFoundError:
        # El key no existe — primera ejecución, sin mirror previo.
        return None
    except Exception as e:
        _log.warning("could not read registry mirror: %s", e)
        return None


def _save_to_registry(data: dict) -> None:
    """Escribe el mirror al registro. Best-effort — si falla, no rompemos."""
    if not _registry_available():
        return
    try:
        import winreg
        payload = {
            "total_messages": int(data.get("total_user_messages", 0)),
            "first_message_at": data.get("first_message_at") or "",
        }
        sig = _sign(payload)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
            winreg.SetValueEx(key, "total_messages", 0, winreg.REG_DWORD, payload["total_messages"])
            winreg.SetValueEx(key, "first_message_at", 0, winreg.REG_SZ, payload["first_message_at"])
            winreg.SetValueEx(key, "sig", 0, winreg.REG_SZ, sig)
    except Exception as e:
        _log.warning("could not write registry mirror: %s", e)


# ─────────────────────────────────────────────
#  Load / save
# ─────────────────────────────────────────────

def _default_stats() -> dict:
    return {
        "total_user_messages": 0,
        "first_message_at": None,
        "_tampered": False,
    }


def _load_from_file() -> Optional[dict]:
    """Lee el JSON, verifica HMAC, devuelve dict o None si no existe."""
    raw = load_json(STATS_FILE, default=None)
    if not raw or not isinstance(raw, dict):
        return None

    sig = raw.pop("_sig", None)
    if not sig:
        # JSON sin firma → alguien lo creó a mano o es de versión muy vieja.
        _log.warning("stats file has no signature — treating as tampered")
        return {"total_user_messages": _POISONED_COUNT, "first_message_at": raw.get("first_message_at"), "_tampered": True}

    if not _verify(raw, sig):
        _log.warning("stats file signature mismatch — treating as tampered")
        return {"total_user_messages": _POISONED_COUNT, "first_message_at": raw.get("first_message_at"), "_tampered": True}

    return {
        "total_user_messages": int(raw.get("total_user_messages", 0)),
        "first_message_at": raw.get("first_message_at"),
        "_tampered": False,
    }


def load_stats() -> dict:
    """Carga el contador, combinando JSON + registro con cross-check.

    Devuelve un dict con:
      - total_user_messages: int
      - first_message_at: str | None
      - _tampered: bool (True si detectamos manipulación en cualquier fuente)
    """
    from_file = _load_from_file()
    from_reg = _load_from_registry()

    # Ambas fuentes vacías → primera ejecución limpia.
    if from_file is None and from_reg is None:
        return _default_stats()

    # Una fuente falta, usar la otra.
    if from_file is None:
        return from_reg
    if from_reg is None:
        return from_file

    # Ambas existen — tomamos el MÁXIMO de ambos counters, y si alguna
    # estaba tampered, marcamos el resultado como tampered también.
    # Aun si el user editó el JSON a 5, el registro sigue diciendo 47 → gana 47.
    # Si manipuló ambos (muy pocos intentarán esto), la firma rota en cualquiera
    # marca tampered y la política de refund se deniega por default.
    tampered = from_file.get("_tampered", False) or from_reg.get("_tampered", False)
    max_count = max(from_file["total_user_messages"], from_reg["total_user_messages"])
    # first_message_at: el más antiguo entre los dos (no-nulo)
    ts_candidates = [f for f in (from_file.get("first_message_at"), from_reg.get("first_message_at")) if f]
    first_at = min(ts_candidates) if ts_candidates else None

    # Además: si los counters divergen MUCHO (ej. file=5, reg=47), es señal
    # fuerte de manipulación. Marcamos tampered aunque ambas firmas fueran OK
    # (significa que alguien editó una de las dos antes de lograr firmar bien).
    if abs(from_file["total_user_messages"] - from_reg["total_user_messages"]) > 5:
        _log.warning(
            "stats divergence: file=%d registry=%d — treating as tampered",
            from_file["total_user_messages"], from_reg["total_user_messages"],
        )
        tampered = True

    return {
        "total_user_messages": max_count,
        "first_message_at": first_at,
        "_tampered": tampered,
    }


def save_stats(data: dict) -> None:
    """Persiste el contador a JSON (firmado) + registro (firmado)."""
    clean = {
        "total_user_messages": int(data.get("total_user_messages", 0)),
        "first_message_at": data.get("first_message_at"),
    }
    clean["_sig"] = _sign(clean)
    save_json(STATS_FILE, clean)

    # Mirror al registro (best-effort, no bloqueamos si falla)
    _save_to_registry(clean)


def increment_message_counter() -> dict:
    """Incrementa el contador de mensajes enviados por el user en +1.

    Se llama desde send_message() justo cuando el user da a 'Send'.
    Si el contador está envenenado por tampering, NO lo incrementamos
    (ya no tiene sentido — está en 9999+).

    Devuelve el dict actualizado para uso opcional del caller.
    """
    stats = load_stats()

    # Si ya está envenenado, no hacemos nada — el daño ya fue hecho.
    if stats.get("_tampered"):
        return stats

    stats["total_user_messages"] = stats.get("total_user_messages", 0) + 1
    if not stats.get("first_message_at"):
        stats["first_message_at"] = now_iso()

    save_stats(stats)
    return stats


def is_refund_eligible(stats: Optional[dict] = None, threshold: int = 40) -> bool:
    """True si el usuario está dentro del límite de reembolso.

    Si el contador fue manipulado → retorna False (denegado por default).
    """
    if stats is None:
        stats = load_stats()
    if stats.get("_tampered"):
        return False
    return stats.get("total_user_messages", 0) < threshold


def is_tampered_vs_history(
    total_messages: int,
    history_length: int,
    max_history: int = 50,
    counter_started_at: Optional[str] = None,
    oldest_history_ts: Optional[str] = None,
) -> bool:
    """Sanity check adicional: si el historial está lleno (capado al max) pero
    el contador dice menos que eso → alguien borró el historial y reseteó
    mal el contador. Señal de tampering aunque las firmas cuadren.

    EXCEPCIÓN (grandfather-in): si el mensaje más viejo del historial es
    ANTERIOR al primer mensaje registrado por el contador, la discrepancia
    es legítima — significa que el user tenía historia antes de que la
    feature de stats existiera. No podemos inventar un contador retroactivo.

    Parámetros:
      total_messages: contador persistente de mensajes del user.
      history_length: número de entradas en historial_ashley.json.
      max_history: límite máximo del historial (50 por default).
      counter_started_at: ISO ts del primer incremento del contador.
      oldest_history_ts: ISO ts del mensaje más antiguo del historial.
    """
    if history_length < max_history:
        return False
    if total_messages >= history_length:
        return False

    # Regla de grandfather: el historial tiene entradas de antes de que el
    # contador existiera → no es tampering, es feature nueva sobre datos viejos.
    if counter_started_at and oldest_history_ts:
        try:
            if oldest_history_ts < counter_started_at:
                return False
        except TypeError:
            # timestamps con tipos raros — ignorar el check, ser conservador.
            pass

    return True
