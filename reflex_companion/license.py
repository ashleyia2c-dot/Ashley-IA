"""
license.py — Lemon Squeezy license validation.

Contiene toda la lógica de validación de licencias vía la API pública de LS.
Los endpoints /v1/licenses/activate|validate|deactivate NO requieren API key
del vendedor — solo la license key del cliente, que actúa como su propio
credencial.

Flujo:
  1. Usuario pega su license key en el gate de Ashley.
  2. activate(key, instance_name) → LS devuelve instance_id.
  3. Guardamos {key, instance_id, activated_at, last_validated_at} en disco.
  4. En cada arranque: validate(key, instance_id) para confirmar vigencia.
  5. Si LS no responde: permitimos arrancar si last_validated_at < 7 días
     (grace period offline), para que un corte de internet no deje al user
     sin app.

La encriptación del archivo license.json con DPAPI se maneja desde Electron
en un pass separado (mismo patrón que key.bin). Aquí usamos save_json plano.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib import error as url_error
from urllib import parse as url_parse
from urllib import request as url_request

from .config import LICENSE_FILE
from .memory import load_json, now_iso, save_json

_log = logging.getLogger("ashley.license")


# ─────────────────────────────────────────────
#  Endpoints + configuración
# ─────────────────────────────────────────────

LS_API_BASE = "https://api.lemonsqueezy.com/v1"
REQUEST_TIMEOUT = 10.0
OFFLINE_GRACE_DAYS = 7

# Errores de red que justifican retry (todo el resto, incluido 400/401/403,
# se propaga sin reintento porque son problemas de la key, no transitorios).
_RETRYABLE_STATUSES = {500, 502, 503, 504}


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def generate_instance_name() -> str:
    """Nombre descriptivo para este PC, visible en el dashboard de LS.

    Formato: "<hostname> (<platform>) - <uuid-corto>"
    El UUID corto evita colisiones si el user reactiva tras deactivate.
    """
    try:
        hostname = socket.gethostname()[:40] or "unknown-host"
    except Exception:
        hostname = "unknown-host"
    system = platform.system() or "unknown"
    short_uuid = uuid.uuid4().hex[:8]
    return f"{hostname} ({system}) - {short_uuid}"


def _post_form(path: str, fields: dict[str, str]) -> tuple[int, dict]:
    """POST application/x-www-form-urlencoded y devuelve (status, json).

    Los endpoints públicos de LS aceptan form-encoded (no JSON). Devuelve
    el status HTTP y el body parseado como dict (vacío si no es JSON).
    """
    url = f"{LS_API_BASE}{path}"
    data = url_parse.urlencode(fields).encode("utf-8")
    req = url_request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with url_request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except url_error.HTTPError as e:
        # LS devuelve JSON con 'valid: false' o 'error' incluso en 4xx/5xx,
        # así que intentamos parsear el body igualmente.
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        status = e.code
    except url_error.URLError as e:
        # Error de red (timeout, DNS, offline). Lo traducimos a excepción
        # explícita para que el caller pueda distinguir "LS dice no" de
        # "LS no contesta".
        raise ConnectionError(f"LS unreachable: {e.reason}") from e

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        _log.warning("LS %s returned non-JSON body (status=%s): %s", path, status, body[:200])
        payload = {}

    return status, payload


def _post_with_retry(path: str, fields: dict[str, str], max_attempts: int = 3) -> tuple[int, dict]:
    """Como _post_form pero con retry en errores de red y 5xx."""
    last_err: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            status, payload = _post_form(path, fields)
        except ConnectionError as e:
            last_err = e
            if attempt == max_attempts:
                raise
            delay = 1.0 * (2 ** (attempt - 1))
            _log.warning(
                "LS %s network error (attempt %d/%d), retry in %.1fs: %s",
                path, attempt, max_attempts, delay, e,
            )
            time.sleep(delay)
            continue

        # 5xx → retry. 4xx → devolver tal cual (problema de la key).
        if status in _RETRYABLE_STATUSES and attempt < max_attempts:
            delay = 1.0 * (2 ** (attempt - 1))
            _log.warning(
                "LS %s 5xx (attempt %d/%d, status=%d), retry in %.1fs",
                path, attempt, max_attempts, status, delay,
            )
            time.sleep(delay)
            continue

        return status, payload

    # No debería llegar aquí, pero por si acaso.
    if last_err:
        raise last_err
    return 0, {}


# ─────────────────────────────────────────────
#  Endpoints públicos
# ─────────────────────────────────────────────

def activate(license_key: str, instance_name: str) -> tuple[bool, dict]:
    """Activa la license key en este PC.

    Devuelve (ok, payload). Si ok=True, payload['instance']['id'] es el
    identificador que hay que guardar y usar en validate/deactivate futuros.

    Errores típicos (ok=False):
      - Key inválida o inexistente
      - Key deshabilitada manualmente
      - Activation limit excedido (todas las slots usadas)
    """
    if not license_key or not license_key.strip():
        return False, {"error": "empty_key"}

    status, payload = _post_with_retry("/licenses/activate", {
        "license_key": license_key.strip(),
        "instance_name": instance_name,
    })

    activated = bool(payload.get("activated")) and status == 200
    if activated:
        _log.info("license activated (status=%d, instance=%s)", status, payload.get("instance", {}).get("id"))
    else:
        _log.warning("license activation failed (status=%d, error=%s)", status, payload.get("error"))
    return activated, payload


def validate(license_key: str, instance_id: Optional[str] = None) -> tuple[bool, dict]:
    """Valida la key (y opcionalmente la instancia).

    Si se pasa instance_id, LS verifica además que esa instancia siga
    activa. Si se omite, solo verifica que la key en sí sea válida.
    """
    if not license_key or not license_key.strip():
        return False, {"error": "empty_key"}

    fields = {"license_key": license_key.strip()}
    if instance_id:
        fields["instance_id"] = instance_id

    status, payload = _post_with_retry("/licenses/validate", fields)

    valid = bool(payload.get("valid")) and status == 200
    if not valid:
        _log.warning("license validation failed (status=%d, error=%s)", status, payload.get("error"))
    return valid, payload


def deactivate(license_key: str, instance_id: str) -> tuple[bool, dict]:
    """Libera la slot de activación de este PC en LS.

    Usar cuando el usuario quiere migrar a otra máquina y ya está en el
    límite (3). No se borra la key de LS — solo esta instancia.
    """
    if not license_key or not instance_id:
        return False, {"error": "missing_params"}

    status, payload = _post_with_retry("/licenses/deactivate", {
        "license_key": license_key.strip(),
        "instance_id": instance_id,
    })

    deactivated = bool(payload.get("deactivated")) and status == 200
    if deactivated:
        _log.info("license deactivated (instance=%s)", instance_id)
    else:
        _log.warning("license deactivation failed (status=%d, error=%s)", status, payload.get("error"))
    return deactivated, payload


# ─────────────────────────────────────────────
#  Storage local
# ─────────────────────────────────────────────

def load_stored() -> Optional[dict]:
    """Carga la licencia almacenada. None si no hay archivo o está vacío.

    Formato esperado:
      {
        "key": "XXXX-XXXX-...",
        "instance_id": "uuid",
        "activated_at": "2026-04-18T14:18:58+00:00",
        "last_validated_at": "2026-04-18T14:19:00+00:00",
        "customer_email": "...",
        "test_mode": true|false
      }
    """
    data = load_json(LICENSE_FILE, default=None)
    if not data or not isinstance(data, dict):
        return None
    if not data.get("key") or not data.get("instance_id"):
        _log.warning("license file exists but is missing key/instance_id")
        return None
    return data


def store(data: dict) -> None:
    """Persiste la licencia (atómico con .bak via save_json)."""
    save_json(LICENSE_FILE, data)


def clear_stored() -> None:
    """Borra la licencia local (tras deactivate o cuando el user la revoca)."""
    for suffix in ("", ".bak", ".tmp"):
        path = LICENSE_FILE + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            _log.warning("could not remove %s: %s", path, e)


# ─────────────────────────────────────────────
#  Grace period offline
# ─────────────────────────────────────────────

def is_within_grace_period(last_validated_at: Optional[str], days: int = OFFLINE_GRACE_DAYS) -> bool:
    """True si la licencia fue validada contra LS hace menos de `days`.

    Si LS está caído o el user no tiene internet, permitimos arrancar
    durante este período. Pasado el umbral, exigimos validación online.
    """
    if not last_validated_at:
        return False
    try:
        last = datetime.fromisoformat(last_validated_at.replace("Z", "+00:00"))
    except ValueError:
        _log.warning("invalid last_validated_at timestamp: %s", last_validated_at)
        return False
    # Ambos deben ser tz-aware para comparar.
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return now - last < timedelta(days=days)


# ─────────────────────────────────────────────
#  Flujo de alto nivel (para el State)
# ─────────────────────────────────────────────

def activate_and_store(license_key: str) -> tuple[bool, str]:
    """Activa la key y persiste todo. Devuelve (ok, mensaje-user-friendly).

    El mensaje está pensado para mostrar directamente al usuario — ya
    traducido a algo comprensible (no el string raw de LS).
    """
    instance_name = generate_instance_name()
    ok, payload = activate(license_key, instance_name)
    if not ok:
        return False, _friendly_error(payload)

    instance = payload.get("instance") or {}
    meta = payload.get("meta") or {}
    license_info = payload.get("license_key") or {}

    data = {
        "key": license_key.strip(),
        "instance_id": str(instance.get("id", "")),
        "instance_name": instance_name,
        "activated_at": now_iso(),
        "last_validated_at": now_iso(),
        "customer_email": meta.get("customer_email", ""),
        "product_id": meta.get("product_id"),
        "test_mode": bool(license_info.get("test_mode")),
    }
    try:
        store(data)
    except Exception as e:
        _log.error("failed to persist license after successful activation: %s", e)
        # La activación ya fue consumida en LS → el user se queda sin slot
        # si no persistimos. Devolvemos error para que reintente.
        return False, "No pude guardar la licencia en disco. Vuelve a intentarlo."

    return True, ""


def ensure_valid_on_startup() -> tuple[bool, str]:
    """Chequea la licencia almacenada al arrancar.

    Returns (valid, reason). `reason` es "" si todo OK, o un string
    explicando por qué falló (para mostrar en el gate / logs).

    Política:
      1. Si no hay licencia almacenada → invalid ("no_license").
      2. Valida contra LS. Si OK → actualiza last_validated_at, return OK.
      3. Si LS dice "invalid" (no red, sino respuesta concreta) → invalid.
      4. Si LS no responde (red) → consulta grace period:
           - Dentro → valid (modo offline).
           - Fuera → invalid ("offline_grace_expired").
    """
    data = load_stored()
    if not data:
        return False, "no_license"

    try:
        ok, payload = validate(data["key"], data.get("instance_id"))
    except ConnectionError:
        # LS no contesta. Caemos a grace period.
        if is_within_grace_period(data.get("last_validated_at")):
            _log.info("LS unreachable, within grace period — allowing startup offline")
            return True, "offline_grace"
        _log.warning("LS unreachable and grace period expired")
        return False, "offline_grace_expired"

    if ok:
        # Actualizamos timestamp (best-effort; si falla write no bloquea).
        data["last_validated_at"] = now_iso()
        try:
            store(data)
        except Exception as e:
            _log.warning("could not update last_validated_at: %s", e)
        return True, ""

    # LS respondió y dijo que NO. Puede ser que el vendedor deshabilitó la
    # key, que la instance fue deactivada desde otro PC, o que el user hizo
    # chargeback. En cualquier caso, toca re-entrar la key.
    error = (payload.get("error") or "").lower()
    if "instance" in error:
        # Caso común: la key sigue viva pero esta instance fue removida
        # (user deactivó desde otro PC). Borramos solo la instance_id
        # local para que pueda reactivar sin volver a pagar.
        _log.info("license instance no longer valid — clearing for reactivation")
        return False, "instance_invalid"
    return False, "license_invalid"


def _friendly_error(payload: dict) -> str:
    """Traduce el error de LS a algo legible para el user."""
    err = (payload.get("error") or "").lower()
    if not err:
        return "La licencia no se pudo activar. Verifica que pegaste la key completa."
    if "not found" in err or "invalid" in err:
        return "Esa license key no existe o no es válida."
    if "disabled" in err:
        return "Esta licencia fue deshabilitada. Contacta con soporte."
    if "limit" in err or "maximum" in err:
        return (
            "Ya activaste esta licencia en el número máximo de PCs. "
            "Desactiva uno desde otro PC antes de continuar."
        )
    if "expired" in err:
        return "Esta licencia ha expirado."
    return f"No pudimos activar la licencia: {payload.get('error')}"
