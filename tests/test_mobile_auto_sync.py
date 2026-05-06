"""Guards para auto-sync del móvil (v0.18.2).

Auto-sync resyncs automáticos del móvil con el PC. Sin esto, el user
tendría que pulsar "Sync" manualmente cada vez que cambia algo.

Triggers que se verifican:
  • tryConnect → autoSyncState({force: true}) tras conectar OK
  • visibilitychange (foreground) → autoSyncState({force: true}) + flush pending
  • Heartbeat cada 5 min mientras visible + online
  • online event → autoSyncState({force: true})
  • Tras mensaje offline → appendPending() para push posterior
  • Reconexión (offline → online detectada en autoSyncState) → flushPending()

Throttle: mínimo 30s entre syncs (constante SYNC_THROTTLE_MS).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP_JS = ROOT / "assets" / "mobile" / "app.js"


def _read_js() -> str:
    return APP_JS.read_text(encoding="utf-8")


# ─────────────────────────────────────────────
#  Funciones expuestas
# ─────────────────────────────────────────────

def test_autosync_function_defined():
    src = _read_js()
    assert "async function autoSyncState" in src, (
        "Falta autoSyncState — auto-sync no implementado"
    )


def test_flush_pending_function_defined():
    src = _read_js()
    assert "async function flushPending" in src, (
        "Falta flushPending — push de mensajes offline no implementado"
    )


def test_sync_heartbeat_start_stop():
    src = _read_js()
    assert "function startSyncHeartbeat" in src
    assert "function stopSyncHeartbeat" in src


def test_pending_storage_helpers():
    src = _read_js()
    for fn in ("loadPending", "savePending", "appendPending"):
        assert f"function {fn}" in src, f"Falta helper {fn}"


# ─────────────────────────────────────────────
#  Constantes y throttle
# ─────────────────────────────────────────────

def test_throttle_constant_defined():
    """SYNC_THROTTLE_MS debe estar definido — sin throttle, los triggers
    múltiples (foreground + heartbeat + online) crearían spam."""
    src = _read_js()
    assert "SYNC_THROTTLE_MS" in src
    # Debe ser >= 10s para tener efecto real
    m = re.search(r"SYNC_THROTTLE_MS\s*=\s*(\d+)\s*\*\s*1000", src)
    assert m, "SYNC_THROTTLE_MS no definido como N * 1000"
    seconds = int(m.group(1))
    assert seconds >= 10, f"throttle de {seconds}s es demasiado bajo"


def test_heartbeat_interval_reasonable():
    """SYNC_HEARTBEAT_MS debería ser entre 1 min y 15 min — más bajo
    spamea network, más alto desincroniza demasiado."""
    src = _read_js()
    m = re.search(r"SYNC_HEARTBEAT_MS\s*=\s*(\d+)\s*\*\s*60\s*\*\s*1000", src)
    assert m, "SYNC_HEARTBEAT_MS no definido como N * 60 * 1000"
    minutes = int(m.group(1))
    assert 1 <= minutes <= 15, f"heartbeat de {minutes} min fuera de rango"


def test_pending_storage_key_namespaced():
    """STORE_PENDING debe estar bajo namespace 'ashley.mobile.' para no
    colisionar con otros sites."""
    src = _read_js()
    m = re.search(r"STORE_PENDING\s*=\s*'(ashley\.mobile\.[^']+)'", src)
    assert m, "STORE_PENDING debe estar namespaced bajo 'ashley.mobile.'"


# ─────────────────────────────────────────────
#  autoSyncState behavior
# ─────────────────────────────────────────────

def test_autosync_calls_sync_state_endpoint():
    src = _read_js()
    section = re.search(
        r"async function autoSyncState[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    assert section, "autoSyncState no encontrado o malformado"
    body = section.group(0)
    assert "/api/mobile/sync_state" in body, (
        "autoSyncState debe llamar /api/mobile/sync_state"
    )


def test_autosync_respects_throttle_unless_force():
    src = _read_js()
    section = re.search(
        r"async function autoSyncState[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    body = section.group(0)
    # Throttle check: si !force AND time < throttle → skip
    assert "force" in body and "SYNC_THROTTLE_MS" in body, (
        "autoSyncState debe consultar `force` y SYNC_THROTTLE_MS"
    )
    assert "throttled" in body, (
        "autoSyncState debe devolver reason='throttled' al saltar por throttle"
    )


def test_autosync_caches_payload_in_localstorage():
    """El sync debe persistir en localStorage para que features offline
    (memorias panel, modo offline) tengan los datos sin tener que reconectar."""
    src = _read_js()
    section = re.search(
        r"async function autoSyncState[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    body = section.group(0)
    # Verifica que cachea facts + diary (lo más crítico) y el resto en bundle
    assert "STORE_CACHED_FACTS" in body or "cached_facts" in body
    assert "cached_state" in body or "cached_diary" in body, (
        "autoSyncState debe cachear el payload"
    )


def test_autosync_detects_reconnection_and_flushes():
    """Cuando detectamos transición offline → online, autoSyncState debe
    llamar flushPending automáticamente — sin esto, los mensajes offline
    quedan colgados hasta que el user pulse algo."""
    src = _read_js()
    section = re.search(
        r"async function autoSyncState[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    body = section.group(0)
    assert "_wasOnline" in body and "flushPending" in body, (
        "autoSyncState debe detectar reconexión y llamar flushPending"
    )


# ─────────────────────────────────────────────
#  flushPending behavior
# ─────────────────────────────────────────────

def test_flush_pending_calls_sync_push():
    src = _read_js()
    section = re.search(
        r"async function flushPending[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    assert section
    body = section.group(0)
    assert "/api/mobile/sync_push" in body
    assert "messages" in body  # body del POST


def test_flush_pending_keeps_messages_on_failure():
    """Si el push falla, los mensajes pending NO se borran — sino se
    perderían sin haber llegado al PC. Solo se borra en res.ok."""
    src = _read_js()
    section = re.search(
        r"async function flushPending[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    body = section.group(0)
    # savePending([]) solo bajo el path res.ok
    # Estructura: if (res.ok) { savePending([]); ... } else { return ... }
    assert "savePending([])" in body, (
        "flushPending debe llamar savePending([]) en caso de éxito"
    )
    # El savePending([]) debe estar dentro de un if (res.ok) — no después
    ok_check_pos = body.find("res.ok")
    save_clear_pos = body.find("savePending([])")
    assert ok_check_pos != -1 and save_clear_pos != -1
    assert save_clear_pos > ok_check_pos, (
        "savePending([]) debe estar después del check res.ok (dentro del if)"
    )


# ─────────────────────────────────────────────
#  Triggers — startup, visibility, online
# ─────────────────────────────────────────────

def test_tryconnect_triggers_initial_autosync():
    src = _read_js()
    section = re.search(
        r"async function tryConnect[\s\S]+?(?=\n  async function |\n  function |\n})",
        src,
    )
    assert section
    body = section.group(0)
    assert "autoSyncState" in body, (
        "tryConnect debe disparar autoSyncState al primer connect exitoso"
    )
    assert "startSyncHeartbeat" in body


def test_visibilitychange_triggers_sync():
    """Al volver a foreground, sync inmediato (force=true). Sin esto el
    user que vuelve tras min/horas en background ve datos viejos."""
    src = _read_js()
    section = re.search(
        r"document\.addEventListener\('visibilitychange'[\s\S]+?\}\);", src,
    )
    assert section
    body = section.group(0)
    assert "autoSyncState" in body
    assert "force" in body, "Foreground sync debe ser force=true (saltar throttle)"


def test_visibilitychange_stops_heartbeat_when_hidden():
    src = _read_js()
    section = re.search(
        r"document\.addEventListener\('visibilitychange'[\s\S]+?\}\);", src,
    )
    body = section.group(0)
    assert "stopSyncHeartbeat" in body, (
        "Cuando hidden, heartbeat debe pararse (battery + network)"
    )


def test_online_event_triggers_sync():
    """Cuando el browser detecta que volvió la red, fuerza sync — sin
    esperar al heartbeat de 5 min."""
    src = _read_js()
    assert "addEventListener('online'" in src, (
        "Falta listener 'online' para detectar reconexión rápida"
    )
    section = re.search(
        r"addEventListener\('online'[\s\S]+?\}\);", src,
    )
    assert section
    body = section.group(0)
    assert "autoSyncState" in body
    assert "force" in body


# ─────────────────────────────────────────────
#  Offline send → pending
# ─────────────────────────────────────────────

def test_offline_send_marks_pending():
    """Tras un send offline exitoso, los 2 mensajes (user + ashley) deben
    quedar en pending_sync para push automático cuando vuelva online."""
    src = _read_js()
    # Buscar el path offline de sendMessage
    section = re.search(
        r"async function sendMessage[\s\S]+?(?=\n  async function |\n  function )",
        src,
    )
    assert section
    body = section.group(0)
    assert "appendPending" in body, (
        "Path offline de sendMessage debe llamar appendPending para auto-push"
    )


def test_offline_send_marks_was_online_false():
    """Tras send offline exitoso, _wasOnline debe quedar False — sino el
    siguiente autoSyncState exitoso no detectaría la transición y no
    flushearía pending."""
    src = _read_js()
    section = re.search(
        r"async function sendMessage[\s\S]+?(?=\n  async function |\n  function )",
        src,
    )
    body = section.group(0)
    assert "_wasOnline = false" in body, (
        "Path offline debe marcar _wasOnline=false para que reconexión "
        "trigger flushPending automático"
    )


# ─────────────────────────────────────────────
#  Sanity — no rompe el polling existente
# ─────────────────────────────────────────────

def test_polling_still_works():
    src = _read_js()
    # El polling existente para chat (cada 2.5s) debe seguir funcionando.
    # Lo validamos verificando que las funciones siguen ahí.
    assert "function startPolling" in src
    assert "function stopPolling" in src
    assert "setInterval(pollOnce" in src
