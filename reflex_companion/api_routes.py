"""
api_routes.py — Starlette API endpoints for the Ashley companion app.

Contains the Whisper STT transcription endpoint, whisper status endpoint,
and the TTS proxy endpoint.

TTS PROXY (v0.12 — multi-backend)
─────────────────────────────────
POST /api/tts receives {"text": "..."} and returns audio bytes.  The
backend is chosen based on voice.json → voice_provider:

  • "elevenlabs" → elevenlabs.io REST API (requires key)
  • "kokoro"     → Kokoro-FastAPI local server (OpenAI-compatible)
  • "voicevox"   → VoiceVox Engine local (audio_query → synthesis)
  • "webspeech"  → this endpoint returns 204; JS handles it in-browser

This lets the JS side keep a single fetch to /api/tts and not worry about
routing.  Provider selection lives on the Python side where we already
read voice.json.

These endpoints live on the BACKEND (Starlette on backend_port), NOT on the
frontend (Next.js on frontend_port).  The browser loads the app from the
frontend port, so calling /api/* from the same origin would give 405
(Next.js doesn't have these routes).  The JS fetches directly to
127.0.0.1:<backend> and that requires CORS headers (different origins =
frontend vs backend).
"""

import json as _json
import urllib.error as _urlerr
import urllib.request as _urlreq

from starlette.responses import JSONResponse as _StarletteJSON, Response as _StarletteResponse
from starlette.routing import Route as _StarletteRoute


_CORS_HEADERS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    # v0.18.2 — CRÍTICO: incluir X-Ashley-Token. Sin esto, el browser hace
    # CORS preflight OPTIONS y el server NO lo declara como header permitido
    # → browser rechaza el request real → fetch() lanza TypeError "Failed
    # to fetch". Síntoma reportado: "TypeError sin red" en el móvil al
    # escanear QR. Causa raíz #1 del pareo roto cross-origin (Capacitor
    # WebView → Cloudflare tunnel).
    "Access-Control-Allow-Headers": "Content-Type, X-Requested-With, X-Ashley-Token",
    "Access-Control-Max-Age":       "86400",
}


def _with_cors(response):
    for k, v in _CORS_HEADERS.items():
        response.headers[k] = v
    return response


def _cors_preflight():
    return _StarletteResponse(status_code=204, headers=_CORS_HEADERS)


# ═══════════════════════════════════════════════════════════════════════
#  Whisper STT (unchanged)
# ═══════════════════════════════════════════════════════════════════════

async def _transcribe_endpoint(request):
    """POST /api/transcribe — recibe audio binario, devuelve {text}.
    Si el modelo aún no está descargado, devuelve {"status":"downloading"}
    para que el frontend muestre un banner de progreso y reintente."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    body = await request.body()
    if not body:
        return _with_cors(_StarletteJSON({"error": "empty body"}, status_code=400))
    lang = request.query_params.get("lang", None)
    try:
        from .whisper_stt import (
            transcribe_bytes, is_loaded, is_loading, warmup, load_error,
            is_cached_on_disk,
        )
        # Si el modelo no está listo, informar al frontend y seguir descargando.
        # PERO: si una carga previa falló (load_error está set), reportamos el
        # error en vez de re-disparar warmup en loop. Sin esto, cada call al
        # endpoint reintenta la carga, vuelve a fallar y muestra el banner
        # "downloading" eternamente al user.
        if not is_loaded():
            err = load_error()
            if err:
                return _with_cors(_StarletteJSON({
                    "status": "error",
                    "error": err,
                    "message": f"Whisper failed to load: {err}",
                    "message_es": f"Whisper no pudo cargarse: {err}",
                }, status_code=503))
            if not is_loading():
                warmup()  # iniciar carga en background
            # v0.16.13 — distinguir "primera descarga real" vs "cargando del
            # disco a RAM". Antes siempre mostrabamos 'Descargando 245 MB'
            # aunque el modelo ya estuviera en disco — el user lo veía cada
            # primera vez por sesión y se frustraba.
            if is_cached_on_disk():
                return _with_cors(_StarletteJSON({
                    "status": "loading",
                    "message": "Loading speech model from disk... ~10s, only once per session.",
                    "message_es": "Cargando modelo de voz desde disco... ~10s, solo la primera vez por sesión.",
                }))
            return _with_cors(_StarletteJSON({
                "status": "downloading",
                "message": "Downloading speech model (~245 MB)... This only happens once.",
                "message_es": "Descargando modelo de voz (~245 MB)... Solo la primera vez.",
            }))
        text = transcribe_bytes(body, language=lang)
        return _with_cors(_StarletteJSON({"text": text}))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _with_cors(_StarletteJSON({"error": str(e)}, status_code=500))


async def _whisper_status_endpoint(request):
    """GET /api/whisper/status — indica si el modelo está cargado."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    from .whisper_stt import is_loaded, is_loading, load_error, is_cached_on_disk
    return _with_cors(_StarletteJSON({
        "loaded": is_loaded(),
        "loading": is_loading(),
        "cached_on_disk": is_cached_on_disk(),  # v0.16.13
        "error": load_error(),
    }))


# ═══════════════════════════════════════════════════════════════════════
#  TTS Backends
# ═══════════════════════════════════════════════════════════════════════
#
# Each backend is a function: (text, cfg) → (audio_bytes, media_type) or
# raises with a (status_code, detail) tuple we turn into an error JSON.
#
# `cfg` is the dict returned by i18n.load_voice_config().
#
# The dispatcher in _tts_endpoint reads cfg["voice_provider"] and picks
# the right function.  Each function only cares about its own config
# fields; they're independent.


class _TTSError(Exception):
    """Raised by backends to short-circuit to a JSON error response.

    status_code: HTTP status to return to the client.
    error: machine-readable error code (e.g. "no_key", "unreachable").
    detail: human-readable explanation for the JS log.
    """
    def __init__(self, status_code: int, error: str, detail: str):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        super().__init__(f"{error}: {detail}")


def _tts_elevenlabs(text: str, cfg: dict) -> tuple[bytes, str]:
    """Call ElevenLabs TTS API and return (audio_bytes, 'audio/mpeg').

    v0.16.14 — REVERTIDO al modelo eleven_multilingual_v2 que el user
    venía usando y funcionaba bien. El experimento con eleven_turbo_v2_5
    se hizo para soportar `speed` server-side, pero rompía la
    reproducción para algunos voice_ids del user (audio se recibía pero
    no sonaba). La velocidad ahora se aplica cliente-side via
    audio.playbackRate (universal, funciona con cualquier modelo).
    """
    from . import i18n as _i18n
    key = (cfg.get("elevenlabs_key") or "").strip()
    voice_id = (cfg.get("voice_id") or _i18n.DEFAULT_VOICE_ID).strip() or _i18n.DEFAULT_VOICE_ID

    if not key or len(key) < 10:
        raise _TTSError(400, "no_key",
            "No ElevenLabs API key configured in Settings.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = _json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.8,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")
    req = _urlreq.Request(url, data=payload, method="POST", headers={
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    try:
        resp = _urlreq.urlopen(req, timeout=30)
        return resp.read(), "audio/mpeg"
    except _urlerr.HTTPError as e:
        err_body = ""
        try: err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception: pass
        raise _TTSError(502, f"HTTP {e.code}", err_body or str(e))
    except Exception as e:
        raise _TTSError(502, "network", str(e))


def _tts_kokoro(text: str, cfg: dict) -> tuple[bytes, str]:
    """Call Kokoro-FastAPI via its OpenAI-compatible /v1/audio/speech endpoint.

    Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) exposes an endpoint
    shaped like OpenAI's TTS API.  We send {model, voice, input} and get
    audio/mpeg back.

    User installs Kokoro-FastAPI separately (Docker or pip).  Default URL
    is http://localhost:8880.  If Kokoro isn't running, we return a
    friendly error so the frontend can fall back to Web Speech.
    """
    base = (cfg.get("kokoro_url") or "http://localhost:8880").rstrip("/")
    voice = (cfg.get("kokoro_voice") or "af_bella").strip() or "af_bella"
    # Speed (v0.16.14): Kokoro acepta range 0.25-4.0. Clamp pragmático.
    speed = max(0.5, min(2.0, float(cfg.get("voice_speed", 1.0) or 1.0)))
    url = f"{base}/v1/audio/speech"
    payload = _json.dumps({
        "model": "kokoro",
        "voice": voice,
        "input": text,
        "response_format": "mp3",
        "speed": speed,
    }).encode("utf-8")
    req = _urlreq.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    try:
        resp = _urlreq.urlopen(req, timeout=60)
        return resp.read(), "audio/mpeg"
    except _urlerr.HTTPError as e:
        err_body = ""
        try: err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception: pass
        raise _TTSError(502, f"HTTP {e.code}",
            f"Kokoro error at {base}: {err_body or str(e)}")
    except Exception as e:
        raise _TTSError(502, "unreachable",
            f"Kokoro server not reachable at {base}. Install from "
            f"github.com/remsky/Kokoro-FastAPI and run it. ({e})")


def _tts_voicevox(text: str, cfg: dict) -> tuple[bytes, str]:
    """Call VoiceVox Engine's two-step API and return WAV audio.

    VoiceVox flow:
      1. POST /audio_query?text=...&speaker=N  → returns audio_query JSON
      2. POST /synthesis?speaker=N            → body=audio_query JSON → WAV bytes

    User installs VoiceVox from voicevox.hiroshiba.jp and runs the Engine.
    Default URL is http://localhost:50021.
    """
    import urllib.parse as _urlparse
    base = (cfg.get("voicevox_url") or "http://localhost:50021").rstrip("/")
    speaker = (cfg.get("voicevox_speaker") or "1").strip() or "1"

    # Step 1: audio_query
    query_url = f"{base}/audio_query?text={_urlparse.quote(text)}&speaker={_urlparse.quote(speaker)}"
    try:
        req = _urlreq.Request(query_url, method="POST",
            headers={"Content-Type": "application/json"})
        resp = _urlreq.urlopen(req, timeout=30)
        audio_query = resp.read()
    except _urlerr.HTTPError as e:
        err_body = ""
        try: err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception: pass
        raise _TTSError(502, f"HTTP {e.code}",
            f"VoiceVox audio_query error at {base}: {err_body or str(e)}")
    except Exception as e:
        raise _TTSError(502, "unreachable",
            f"VoiceVox engine not reachable at {base}. Install from "
            f"voicevox.hiroshiba.jp and run the engine. ({e})")

    # Inyectar speedScale en el audio_query (v0.16.14). VoiceVox acepta
    # range 0.5-2.0. Clamp aquí para evitar 422.
    try:
        speed = max(0.5, min(2.0, float(cfg.get("voice_speed", 1.0) or 1.0)))
        if abs(speed - 1.0) > 1e-3:
            _q = _json.loads(audio_query.decode("utf-8"))
            _q["speedScale"] = speed
            audio_query = _json.dumps(_q).encode("utf-8")
    except Exception:
        pass

    # Step 2: synthesis — produces WAV
    synth_url = f"{base}/synthesis?speaker={_urlparse.quote(speaker)}"
    try:
        req = _urlreq.Request(synth_url, data=audio_query, method="POST", headers={
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        })
        resp = _urlreq.urlopen(req, timeout=60)
        return resp.read(), "audio/wav"
    except _urlerr.HTTPError as e:
        err_body = ""
        try: err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception: pass
        raise _TTSError(502, f"HTTP {e.code}",
            f"VoiceVox synthesis error at {base}: {err_body or str(e)}")
    except Exception as e:
        raise _TTSError(502, "network", f"VoiceVox synthesis failed: {e}")


_TTS_BACKENDS = {
    "elevenlabs": _tts_elevenlabs,
    "kokoro":     _tts_kokoro,
    "voicevox":   _tts_voicevox,
}


async def _tts_endpoint(request):
    """POST /api/tts — dispatch to the configured TTS backend.

    Returns audio bytes on success.  If voice_provider is 'webspeech' we
    return 204 (no content) so the JS falls back to browser SpeechSynthesis.
    If the backend errors, we return a JSON error so the JS can log it and
    fall back to Web Speech gracefully.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    from . import i18n as _i18n

    try:
        body = await request.json()
    except Exception:
        return _with_cors(_StarletteJSON({"error": "invalid json"}, status_code=400))
    text = ((body or {}).get("text") or "").strip()
    if not text:
        return _with_cors(_StarletteJSON({"error": "empty text"}, status_code=400))

    cfg = _i18n.load_voice_config()
    # Override explícito del body: si el JS pasa "provider", gana sobre
    # voice.json (útil para probar desde Settings sin tocar el global).
    provider = ((body or {}).get("provider") or cfg.get("voice_provider") or "webspeech").lower()

    if provider == "webspeech":
        # El frontend debería haber usado SpeechSynthesis directamente.
        # Devolver 204 le dice que no hay audio del backend.
        return _with_cors(_StarletteResponse(status_code=204))

    backend = _TTS_BACKENDS.get(provider)
    if backend is None:
        return _with_cors(_StarletteJSON(
            {"error": "unknown_provider", "detail": f"Unknown voice_provider: {provider}"},
            status_code=400))

    try:
        audio_bytes, media_type = backend(text, cfg)
        return _with_cors(_StarletteResponse(audio_bytes, media_type=media_type))
    except _TTSError as e:
        return _with_cors(_StarletteJSON(
            {"error": e.error, "detail": e.detail, "provider": provider},
            status_code=e.status_code))
    except Exception as e:
        return _with_cors(_StarletteJSON(
            {"error": "internal", "detail": str(e), "provider": provider},
            status_code=500))


async def _wake_word_pause(request):
    """POST /api/wake_word/pause — pausa el detector mientras el JS hace
    grabación manual. Idempotente — si no está corriendo, no-op."""
    from .wake_word_lifecycle import pause_detector
    try:
        pause_detector()
        return _with_cors(_StarletteJSON({"ok": True}))
    except Exception as e:
        return _with_cors(_StarletteJSON({"ok": False, "error": str(e)},
                                          status_code=500))


async def _wake_word_resume(request):
    """POST /api/wake_word/resume — reanuda el detector después de que
    la grabación manual termine."""
    from .wake_word_lifecycle import resume_detector
    try:
        resume_detector()
        return _with_cors(_StarletteJSON({"ok": True}))
    except Exception as e:
        return _with_cors(_StarletteJSON({"ok": False, "error": str(e)},
                                          status_code=500))


async def _wake_word_debug(request):
    """GET /api/wake_word/debug — devuelve estado completo del detector.

    Útil para diagnosticar:
      - ¿está corriendo? (is_running)
      - ¿está paused por grabación manual? (is_paused)
      - ¿cuántas detecciones hubo desde el arranque? (detection_count)
      - ¿el modelo .onnx existe y carga? (model_path, model_present)
    """
    from .wake_word_lifecycle import is_running, is_paused
    from .wake_word_bridge import detection_count
    from . import wake_word as _ww
    from pathlib import Path

    try:
        deps_ok, deps_reason = _ww.is_available()
        model_path = Path(__file__).resolve().parent / "wake_word" / "ashley.onnx"
        return _with_cors(_StarletteJSON({
            "is_running": is_running(),
            "is_paused": is_paused(),
            "detection_count": detection_count(),
            "model_path": str(model_path),
            "model_present": model_path.exists(),
            "deps_ok": deps_ok,
            "deps_reason": deps_reason or None,
        }))
    except Exception as e:
        return _with_cors(_StarletteJSON({"error": str(e)}, status_code=500))


async def _wake_word_test_trigger(request):
    """POST /api/wake_word/test_trigger — dispara una "detección" sintética.

    Diagnóstico: si esto arranca grabación en el frontend, el flujo
    bridge → State bg listener → JS funciona — el problema (si lo hay)
    está en el detector ↔ mic. Si no arranca, hay un bug en el wiring.
    """
    from .wake_word_bridge import signal_detection
    try:
        signal_detection(0.99)  # score sintético alto
        return _with_cors(_StarletteJSON({
            "ok": True,
            "message": "Synthetic detection signaled. The bg listener "
                       "should pick this up within 200ms and trigger "
                       "the recording in the frontend.",
        }))
    except Exception as e:
        return _with_cors(_StarletteJSON({"ok": False, "error": str(e)},
                                          status_code=500))


async def _shutdown_endpoint(request):
    """POST /api/shutdown — graceful shutdown del backend.

    Llamado por Electron antes de matar Reflex con SIGKILL. Da chance al
    Python de:
      • parar el wake_word detector → libera el handle del mic (sin esto
        el icono "alguna app está usando tu mic" queda hasta reboot).
      • cerrar streams de audio activos.
      • flushear logs y persistencia pendiente.

    Si Electron no llamó este endpoint (cierre súbito del SO, etc.),
    seguirá funcionando con el SIGKILL fallback — solo que el mic puede
    quedar pegado.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()

    # 1. Parar el detector wake word (libera el mic).
    try:
        from .wake_word_lifecycle import stop_detector
        stop_detector(timeout=1.0)
    except Exception:
        pass

    # 2. Programar exit en el siguiente tick para responder al HTTP
    # request primero — sin esto, el cliente Electron puede recibir un
    # connection-reset en lugar del 200 OK.
    import asyncio
    import os as _os

    def _exit_now():
        try:
            _os._exit(0)
        except Exception:
            pass

    try:
        asyncio.get_event_loop().call_later(0.1, _exit_now)
    except Exception:
        # Fallback síncrono si el loop está caído.
        _exit_now()

    return _with_cors(_StarletteJSON({"ok": True, "shutdown": "pending"}))


# ═══════════════════════════════════════════════════════════════════════
#  Mobile API (v0.18.2 — companion app móvil para Play Store)
# ═══════════════════════════════════════════════════════════════════════
#
# Estos endpoints permiten que una app móvil (PWA / TWA) se conecte al
# Ashley desktop del user y vea/interactúe con su chat + memorias.
#
# Arquitectura: PC = source of truth, móvil = cliente remoto.
# Mismo Ashley, accesible desde dos sitios.
#
# Auth: por simple shared token. Generamos un pairing code en el PC,
# el user lo introduce en el móvil. Cada llamada lleva el header
# `X-Ashley-Token: <token>`. Sin token correcto → 401.
#
# Sync: el móvil hace polling cada 2-3s al endpoint /chat para detectar
# nuevos mensajes. NO real-time WebSocket por simplicidad — basta para
# UX de "abro app, veo conversación".
#
# CORS: permitimos cualquier origin para que el TWA/PWA funcione desde
# subdominios distintos al PC (ej. tunnel.cloudflare.com → PC LAN).


def _data_dir():
    """Devuelve el directorio donde viven los JSONs de Ashley."""
    import os
    env_dir = os.getenv("ASHLEY_DATA_DIR")
    if env_dir:
        return env_dir
    # Fallback: project root
    return ".."


def _read_json_safe(filename: str, default):
    """Lee un JSON del data dir. Devuelve default si falta o es inválido."""
    import os
    path = os.path.join(_data_dir(), filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return default


# v0.18.2 — Auto-rotation: el token se regenera automáticamente cada N días
# para limitar el blast radius si alguien lo filtra. El user re-empareja el
# móvil (regenera localStorage en el APK) escaneando el QR nuevo.
_TOKEN_ROTATION_DAYS = 30


def _generate_new_token_record() -> dict:
    """Genera un token nuevo + timestamp. Usado por _read_pairing_token
    al primer arranque y por la auto-rotation."""
    import secrets
    from datetime import datetime, timezone
    return {
        "token": secrets.token_urlsafe(24),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _persist_pairing_record(record: dict) -> None:
    """Escribe el record (token + created_at) a mobile_pairing.json
    preservando otros campos (lan_disabled, etc.) si existen."""
    import os
    path = os.path.join(_data_dir(), "mobile_pairing.json")
    existing = {}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = _json.load(f) or {}
    except Exception:
        pass
    # Merge — preserva lan_disabled u otros campos opcionales del user
    existing.update(record)
    try:
        os.makedirs(_data_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(existing, f)
    except Exception:
        pass


def _read_pairing_token() -> str:
    """Lee el pairing token. Si no existe, lo genera. Si tiene >N días,
    lo auto-rota (el móvil tendrá que re-escanear).
    """
    import os
    from datetime import datetime, timezone
    path = os.path.join(_data_dir(), "mobile_pairing.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            tok = (data.get("token") or "").strip()
            created_at = (data.get("created_at") or "").strip()
            if tok:
                # v0.18.2 — chequear edad del token
                if created_at:
                    try:
                        created = datetime.fromisoformat(created_at)
                        if created.tzinfo is None:
                            created = created.replace(tzinfo=timezone.utc)
                        age_days = (datetime.now(timezone.utc) - created).days
                        if age_days >= _TOKEN_ROTATION_DAYS:
                            # Auto-rotación: regenerar y persistir
                            new_record = _generate_new_token_record()
                            _persist_pairing_record(new_record)
                            return new_record["token"]
                    except Exception:
                        pass
                else:
                    # Token sin created_at (legacy) — añadir timestamp pero
                    # mantener el token actual (no romper móviles ya pareados).
                    _persist_pairing_record({
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                return tok
        except Exception:
            pass
    # Primera vez — generar nuevo
    record = _generate_new_token_record()
    _persist_pairing_record(record)
    return record["token"]


# ─────────────────────────────────────────────
# Rate limiting (v0.18.2)
# ─────────────────────────────────────────────
#
# Defensa contra: si alguien filtra el QR, el atacante con el token podría
# spammear /api/mobile/send para drenar la API key del LLM del user.
# Sliding window: 60 requests/min por token. Un user normal nunca llega
# a 10/min — el límite solo afecta abuso real.

import time as _time
import threading as _threading

_RATE_LIMIT_MAX_PER_MIN = 60
_RATE_LIMIT_WINDOW_SEC = 60.0
_rate_limit_log: dict[str, list[float]] = {}
_rate_limit_lock = _threading.Lock()


def _is_rate_limited(token: str) -> bool:
    """True si el token excedió el límite en la ventana actual.
    Side effect: registra el timestamp del request actual.
    Thread-safe."""
    if not token:
        return False
    now = _time.time()
    with _rate_limit_lock:
        bucket = _rate_limit_log.setdefault(token, [])
        # Purgar timestamps fuera de ventana
        cutoff = now - _RATE_LIMIT_WINDOW_SEC
        bucket[:] = [t for t in bucket if t >= cutoff]
        if len(bucket) >= _RATE_LIMIT_MAX_PER_MIN:
            return True
        bucket.append(now)
        return False


def _check_mobile_auth(request) -> bool:
    """True si el request lleva el token correcto en X-Ashley-Token Y
    no está rate-limited. Mismo error 401 ambos casos para no leakear
    a un atacante si su problema es token mal vs rate limit."""
    expected = _read_pairing_token()
    given = request.headers.get("x-ashley-token", "").strip()
    if not (expected and given == expected):
        return False
    # Token correcto — chequear rate limit
    if _is_rate_limited(given):
        import logging
        logging.getLogger("ashley.mobile").warning(
            "rate-limit hit (token suffix=...%s)", given[-6:]
        )
        return False
    return True


def _unauthorized():
    return _with_cors(_StarletteJSON({"error": "invalid_token"}, status_code=401))


async def _mobile_status_endpoint(request):
    """GET /api/mobile/status — info básica + verificación de auth.

    Sin token: devuelve {ok: True, paired: False} para que el móvil sepa
    que el endpoint existe pero no está pareado.
    Con token correcto: devuelve {ok: True, paired: True, version: "..."}.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    paired = _check_mobile_auth(request)
    payload = {"ok": True, "paired": paired}
    if paired:
        try:
            from .config import GROK_MODEL
            payload["model"] = GROK_MODEL
        except Exception:
            pass
        payload["version"] = "0.19.1"
    return _with_cors(_StarletteJSON(payload))


async def _mobile_pairing_token_endpoint(request):
    """GET /api/mobile/pairing_token — devuelve el token actual.

    SOLO accesible desde localhost — el desktop UI lo muestra al user
    (con QR code o texto) para que lo introduzca en su móvil. Móvil
    NO debería llamar este endpoint nunca.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    # Solo localhost — defensa básica
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "localhost", "::1"):
        return _with_cors(_StarletteJSON({"error": "localhost_only"}, status_code=403))
    return _with_cors(_StarletteJSON({"token": _read_pairing_token()}))


def _detect_lan_ip() -> str:
    """Detecta la IP local del PC en la LAN. Devuelve '127.0.0.1' si falla."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return "127.0.0.1"


def _detect_frontend_port() -> int:
    """Detecta el puerto del frontend (donde sirve el embedded server).

    En runtime via Electron: el puerto se asigna dinámicamente y se pasa
    via env ASHLEY_FRONTEND_PORT. Sino usamos el default 17300.
    """
    import os
    try:
        return int(os.getenv("ASHLEY_FRONTEND_PORT") or "17300")
    except Exception:
        return 17300


def _detect_backend_port() -> int:
    """Detecta el puerto del BACKEND (donde corre Starlette y los endpoints
    /api/mobile/*). Es el que el móvil debe usar — siempre tiene los
    endpoints, sin depender de proxy del frontend.

    Reflex lo asigna dinámicamente y Electron lo pasa via env
    ASHLEY_BACKEND_PORT. Sino default 17800.
    """
    import os
    try:
        return int(os.getenv("ASHLEY_BACKEND_PORT") or "17800")
    except Exception:
        return 17800


def _read_tunnel_url() -> str:
    """v0.18.2 — Lee la URL del Cloudflare Quick Tunnel si está activo.

    Electron escribe la URL pública del túnel a un archivo en el data dir
    cuando arranca el túnel. Si el archivo existe Y la URL es válida (https://),
    el QR del móvil debe usar esa URL en lugar de la LAN IP — porque permite
    al móvil conectar desde CUALQUIER red (LAN, 4G, viaje), no solo cuando
    está en la misma subnet del PC.

    Devuelve "" si no hay túnel activo (fallback a LAN).
    """
    import os
    try:
        url_file = os.path.join(_data_dir(), "tunnel_url.txt")
        if not os.path.isfile(url_file):
            return ""
        with open(url_file, "r", encoding="utf-8") as f:
            url = f.read().strip()
        # Validación básica: solo aceptamos HTTPS de Cloudflare
        if url.startswith("https://") and ".trycloudflare.com" in url:
            return url
        return ""
    except Exception:
        return ""


async def _mobile_qr_payload_endpoint(request):
    """GET /api/mobile/qr_payload — devuelve datos para generar QR de pairing.

    SOLO accesible desde localhost. Devuelve JSON con server URL + token
    + IP detectada. La página /mobile/connect.html lo usa para generar el
    QR que el user escanea desde su móvil.

    v0.18.2 — el server URL apunta al BACKEND port (no frontend), porque:
      • El backend Starlette siempre tiene los endpoints /api/mobile/*
      • El frontend Next.js NO conoce esas rutas (slow-path) y devuelve 404
      • El embedded HTTP proxy de Electron (fast-path) sí proxea, pero no
        siempre está activo. El backend es la fuente confiable.
      • El móvil APK Capacitor sirve la PWA desde su bundle local — no
        necesita el frontend del PC.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "localhost", "::1"):
        return _with_cors(_StarletteJSON({"error": "localhost_only"}, status_code=403))

    lan_ip = _detect_lan_ip()
    port = _detect_backend_port()
    token = _read_pairing_token()

    # v0.18.2 — preferir Cloudflare Tunnel URL si está activo. Esto permite
    # al móvil conectar desde CUALQUIER red (LAN, 4G, viaje) sin importar
    # boosters/mesh/AP isolation. Fallback a LAN si el túnel no arrancó.
    tunnel_url = _read_tunnel_url()
    if tunnel_url:
        server_url = tunnel_url
        connection_mode = "tunnel"
    else:
        server_url = f"http://{lan_ip}:{port}"
        connection_mode = "lan"

    return _with_cors(_StarletteJSON({
        "server": server_url,
        "token": token,
        "lan_ip": lan_ip,
        "port": port,
        "tunnel_url": tunnel_url,        # vacío si no hay túnel
        "connection_mode": connection_mode,  # "tunnel" | "lan"
    }))


async def _mobile_regen_token_endpoint(request):
    """POST /api/mobile/regen_token — regenera el token (invalida móviles existentes).

    SOLO accesible desde localhost. Útil si el user piensa que el token
    se filtró o quiere desconectar todos los móviles pareados.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "localhost", "::1"):
        return _with_cors(_StarletteJSON({"error": "localhost_only"}, status_code=403))

    import os
    import secrets as _secrets
    path = os.path.join(_data_dir(), "mobile_pairing.json")
    cfg = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = _json.load(f) or {}
        except Exception:
            cfg = {}
    cfg["token"] = _secrets.token_urlsafe(24)
    try:
        os.makedirs(_data_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(cfg, f)
    except Exception as e:
        return _with_cors(_StarletteJSON({"error": str(e)}, status_code=500))
    return _with_cors(_StarletteJSON({"ok": True, "token": cfg["token"]}))


async def _mobile_tunnel_url_endpoint(request):
    """GET /api/mobile/tunnel_url — devuelve la URL actual del Cloudflare
    Tunnel + LAN IP + port.

    Usado por el móvil para AUTO-RECOVERY cuando la URL cached del túnel
    deja de responder (Cloudflare regenera URL en cada arranque del PC).

    Si el móvil tiene la lan_ip cached del último pareo, llama a este
    endpoint vía LAN para obtener la URL nueva del túnel — sin que el
    user tenga que re-escanear el QR. Funciona si móvil y PC están en
    la misma subnet LAN.

    Si el móvil NO está en la misma LAN (boosters/mesh), este endpoint
    también está expuesto vía Cloudflare, pero por definición el móvil
    NO podría llegar (la URL Cloudflare cambió). En ese caso la UI
    muestra "Re-escanear QR".

    Auth: requiere pairing token. NO localhost-only para que el móvil
    en LAN pueda llamar.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    lan_ip = _detect_lan_ip()
    port = _detect_backend_port()
    tunnel_url = _read_tunnel_url()

    return _with_cors(_StarletteJSON({
        "tunnel_url": tunnel_url,        # vacío si túnel caído
        "lan_ip": lan_ip,
        "port": port,
        "connection_mode": "tunnel" if tunnel_url else "lan",
    }))


async def _mobile_chat_endpoint(request):
    """GET /api/mobile/chat[?since=ISO_TIMESTAMP]

    Devuelve mensajes del historial. Si `since` se pasa, devuelve solo
    mensajes con timestamp > since (para polling incremental).

    Cada mensaje incluye: role, content, timestamp, id.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    history = _read_json_safe("historial_ashley.json", [])
    if not isinstance(history, list):
        history = []

    since = (request.query_params.get("since") or "").strip()
    if since:
        history = [m for m in history if (m.get("timestamp") or "") > since]

    # Filtrar campos que el móvil necesita
    out = []
    for m in history:
        if m.get("role") == "system_result":
            # Mensajes de sistema (resultado de actions) — los incluimos
            # como tipo distinto para que móvil pueda renderizar diferente.
            # v0.19.23 — PRIVACY: si hay ui_content, lo enviamos en vez del
            # content completo (read_page leak fix también aplica al móvil).
            ui_short = m.get("ui_content") or ""
            mobile_content = ui_short if ui_short else m.get("content", "")
            out.append({
                "role": "system",
                "content": mobile_content,
                "timestamp": m.get("timestamp", ""),
                "id": m.get("id", ""),
            })
        else:
            out.append({
                "role": m.get("role", "assistant"),
                "content": m.get("content", ""),
                "timestamp": m.get("timestamp", ""),
                "id": m.get("id", ""),
                "image": m.get("image", ""),
            })

    return _with_cors(_StarletteJSON({"messages": out, "count": len(out)}))


async def _mobile_facts_endpoint(request):
    """GET /api/mobile/facts — devuelve los facts (memorias del user)."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    facts = _read_json_safe("hechos_ashley.json", [])
    if not isinstance(facts, list):
        facts = []

    return _with_cors(_StarletteJSON({"facts": facts, "count": len(facts)}))


async def _mobile_send_endpoint(request):
    """POST /api/mobile/send — recibe {message: "..."}, dispara respuesta de Ashley.

    Append user message a historial, genera respuesta de Ashley vía Grok
    (sync, no streaming — móvil hace polling para verla), append respuesta
    a historial. Devuelve confirmación.

    Limitación conocida: el desktop Ashley (si está abierto en Reflex) NO
    se entera del mensaje hasta que se refresque. Sync real-time entre
    desktop y móvil queda para v2.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    try:
        body = await request.json()
    except Exception:
        return _with_cors(_StarletteJSON({"error": "invalid_json"}, status_code=400))

    text = (body.get("message") or "").strip()
    if not text:
        return _with_cors(_StarletteJSON({"error": "empty_message"}, status_code=400))

    import os
    from datetime import datetime, timezone

    # Append user message a historial
    history = _read_json_safe("historial_ashley.json", [])
    if not isinstance(history, list):
        history = []

    now_iso_str = datetime.now(timezone.utc).isoformat()
    user_msg = {
        "role": "user",
        "content": text,
        "timestamp": now_iso_str,
        "id": f"mobile-u-{now_iso_str}",
        "image": "",
    }
    history.append(user_msg)

    # Generar respuesta de Ashley vía Grok (sync)
    try:
        from .grok_client import stream_response
        from .prompts import build_system_prompt, build_device_section
        from .parsing import (
            extract_mood as _ext_mood,
            extract_action as _ext_act,
            extract_affection as _ext_aff,
            clean_display as _clean_display,
        )
        from .i18n import load_language

        facts = _read_json_safe("hechos_ashley.json", [])
        diary = _read_json_safe("diario_ashley.json", [])
        lang = load_language() or "es"

        # v0.18.2 — el endpoint /api/mobile/send siempre viene del móvil,
        # así que device_section informa a Ashley que está en el móvil
        # del jefe (no en su PC) y le restringe los tags de actions.
        sys_prompt = build_system_prompt(
            facts=facts if isinstance(facts, list) else [],
            diary=diary if isinstance(diary, list) else [],
            voice_mode=False, lang=lang,
            device_section=build_device_section("mobile", lang),
        )

        recent = history[-14:]
        # stream_response es generador — concatenamos chunks
        raw = "".join(t for t in stream_response(
            recent, sys_prompt, use_web_search=False, trigger=None,
        ))
    except Exception as _e:
        import logging
        logging.getLogger("ashley.mobile").warning("send grok call failed: %s", _e)
        # Save user message anyway, return error
        try:
            path = os.path.join(_data_dir(), "historial_ashley.json")
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return _with_cors(_StarletteJSON({
            "error": "ashley_error",
            "detail": str(_e),
            "user_message_saved": True,
        }, status_code=500))

    # Parsear respuesta
    clean, mood = _ext_mood(raw)
    clean, _ = _ext_aff(clean)
    clean, _ = _ext_act(clean)
    clean = _clean_display(clean)

    if not clean or len(clean) < 1:
        clean = "..."

    ashley_msg = {
        "role": "assistant",
        "content": clean,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "id": f"mobile-a-{now_iso_str}",
        "image": "",
        "mood": mood,
    }
    history.append(ashley_msg)

    # Persistir
    try:
        path = os.path.join(_data_dir(), "historial_ashley.json")
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as _e:
        import logging
        logging.getLogger("ashley.mobile").warning("save history failed: %s", _e)

    return _with_cors(_StarletteJSON({
        "ok": True,
        "user_message": user_msg,
        "ashley_message": ashley_msg,
    }))


async def _mobile_sync_prompts_endpoint(request):
    """GET /api/mobile/sync_prompts — devuelve los system prompts pre-construidos
    para los 3 idiomas (es/en/fr) en versión "mobile-ready".

    Cada prompt:
      • Incluye toda la personalidad estable (~9.5K tokens) + rules + reglas.
      • Tiene `device_section=mobile` ya inyectado (limita actions del PC).
      • Las secciones dinámicas (facts/diary/time/mood/etc.) van como
        placeholders que el brain JS sustituye en runtime con su propia data.

    Usado por el brain JS del móvil al primer pareo (y en cada update de la
    versión del desktop). Cacheado en IndexedDB del móvil.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    try:
        from .prompts import build_system_prompt, build_device_section
    except Exception as _e:
        return _with_cors(_StarletteJSON(
            {"error": "import_failed", "detail": str(_e)}, status_code=500
        ))

    languages = {}
    for lang in ("es", "en", "fr"):
        try:
            # Construimos prompt "mobile-ready" sin facts/diary/dynamics.
            # El brain JS añade lo dinámico al final del prompt antes de
            # llamar al LLM.
            prompt = build_system_prompt(
                facts=[],
                diary=[],
                voice_mode=False,
                lang=lang,
                device_section=build_device_section("mobile", lang),
            )
            languages[lang] = {
                "system_prompt": prompt,
                "device_section_mobile": build_device_section("mobile", lang),
            }
        except Exception as _e:
            languages[lang] = {"error": str(_e)}

    payload = {
        "version": "0.19.20",
        "languages": languages,
    }
    return _with_cors(_StarletteJSON(payload))


async def _mobile_sync_state_endpoint(request):
    """GET /api/mobile/sync_state — devuelve TODOS los datos persistentes
    de Ashley para que el móvil pueda funcionar offline.

    Devuelve:
      • chat_history (últimos 50 mensajes)
      • facts
      • diary (últimas 5 entradas)
      • tastes
      • reminders
      • important
      • important_dates
      • goals
      • stats
      • mental_state (mood + preoccupation)
      • affection (del último mensaje en mental state)
      • language preference

    Auth: requiere pairing token.
    Llamado por el brain JS al pulsar "Sincronizar" o automáticamente al
    detectar conexión con el PC.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    payload: dict = {"version": "0.19.20"}

    # Chat history (últimos 50)
    try:
        history = _read_json_safe("historial_ashley.json", [])
        if isinstance(history, list):
            payload["chat_history"] = history[-50:]
        else:
            payload["chat_history"] = []
    except Exception as _e:
        payload["chat_history"] = []
        payload["chat_history_error"] = str(_e)

    # Facts
    try:
        facts = _read_json_safe("hechos_ashley.json", [])
        payload["facts"] = facts if isinstance(facts, list) else []
    except Exception:
        payload["facts"] = []

    # Diary (últimas 5)
    try:
        diary = _read_json_safe("diario_ashley.json", [])
        if isinstance(diary, list):
            payload["diary"] = diary[-5:]
        else:
            payload["diary"] = []
    except Exception:
        payload["diary"] = []

    # Tastes
    try:
        payload["tastes"] = _read_json_safe("gustos_ashley.json", [])
    except Exception:
        payload["tastes"] = []

    # Reminders + important
    try:
        payload["reminders"] = _read_json_safe("recordatorios_ashley.json", [])
    except Exception:
        payload["reminders"] = []
    try:
        payload["important"] = _read_json_safe("importantes_ashley.json", [])
    except Exception:
        payload["important"] = []

    # Important dates (v0.18.0 fase 2)
    try:
        from .important_dates import load_dates
        payload["important_dates"] = load_dates()
    except Exception:
        payload["important_dates"] = []

    # Goals (v0.18.0 fase 3)
    try:
        from .goals import load_goals
        payload["goals"] = load_goals()
    except Exception:
        payload["goals"] = []

    # Stats (v0.18.0 fase 1)
    try:
        from .stats import load_stats
        payload["stats"] = load_stats()
    except Exception:
        payload["stats"] = {}

    # Mental state (mood + preoccupation)
    try:
        from .mental_state import load_state as _load_mental_state
        payload["mental_state"] = _load_mental_state()
    except Exception:
        payload["mental_state"] = {}

    # Affection — extraído del mental_state si existe, sino default 50
    try:
        affection = payload.get("mental_state", {}).get("affection", 50)
        payload["affection"] = int(affection)
    except Exception:
        payload["affection"] = 50

    # Language
    try:
        from .i18n import load_language
        payload["language"] = load_language() or "es"
    except Exception:
        payload["language"] = "es"

    return _with_cors(_StarletteJSON(payload))


async def _mobile_sync_push_endpoint(request):
    """POST /api/mobile/sync_push — recibe del móvil mensajes nuevos creados
    offline y los mergea al historial del PC.

    Body: {messages: [...], mental_state: {...} (opcional), tastes_added: [...] (opcional)}

    El móvil hace push al volver a estar conectado con el PC. El PC mergea
    cronológicamente por timestamp. NO es destructivo — los mensajes del
    móvil se APPEND al historial existente (no reemplaza).

    Auth: requiere pairing token.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    if not _check_mobile_auth(request):
        return _unauthorized()

    try:
        body = await request.json()
    except Exception:
        return _with_cors(_StarletteJSON({"error": "invalid_json"}, status_code=400))

    new_messages = body.get("messages") or []
    if not isinstance(new_messages, list):
        return _with_cors(_StarletteJSON(
            {"error": "messages_must_be_list"}, status_code=400
        ))

    # Merge cronológico al historial del PC
    import os
    from datetime import datetime, timezone

    history = _read_json_safe("historial_ashley.json", [])
    if not isinstance(history, list):
        history = []

    # Set de IDs existentes para evitar duplicados (idempotencia)
    existing_ids = {m.get("id") for m in history if m.get("id")}

    merged = list(history)
    added = 0
    for m in new_messages:
        if not isinstance(m, dict):
            continue
        mid = m.get("id")
        if mid and mid in existing_ids:
            continue  # ya estaba — skip duplicate
        # Normalizar timestamp (tolerante)
        if not m.get("timestamp"):
            m["timestamp"] = datetime.now(timezone.utc).isoformat()
        merged.append(m)
        if mid:
            existing_ids.add(mid)
        added += 1

    # Re-orden por timestamp (mantener mensajes sin timestamp al final)
    def _ts_key(msg):
        try:
            return datetime.fromisoformat(msg.get("timestamp", ""))
        except Exception:
            return datetime.max.replace(tzinfo=timezone.utc)

    merged.sort(key=_ts_key)

    # Truncar a últimos 200 (config: HISTORY_MAX) — el PC mantiene 50 default
    # pero permitimos crecer durante merge para que el móvil offline no
    # pierda mensajes en el push.
    merged = merged[-200:]

    # Persistir
    try:
        path = os.path.join(_data_dir(), "historial_ashley.json")
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(merged, f, ensure_ascii=False, indent=2)
    except Exception as _e:
        return _with_cors(_StarletteJSON(
            {"error": "save_failed", "detail": str(_e)}, status_code=500
        ))

    return _with_cors(_StarletteJSON({
        "ok": True,
        "added": added,
        "total": len(merged),
        "duplicates_skipped": len(new_messages) - added,
    }))


async def _export_data_endpoint(request):
    """GET /api/export/data — descarga ZIP con todos los datos del user.

    v0.19.7 — feature de "Export all my data" en Settings. Builds in-memory
    a partir de %APPDATA%\\Ashley\\data\\ (todos los JSON files que Ashley
    persiste). Excluye key.bin (cifrado DPAPI inútil de exportar) y
    license.json (atado a una activación específica).

    Devuelve:
      Content-Type: application/zip
      Content-Disposition: attachment; filename="ashley-backup-YYYY-MM-DD_HHMM.zip"
    """
    if request.method == "OPTIONS":
        return _cors_preflight()
    try:
        from .export import build_data_zip
        zip_bytes, filename = build_data_zip()
        return _with_cors(_StarletteResponse(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(zip_bytes)),
                # Cache control — el zip cambia cada llamada (timestamp diferente)
                "Cache-Control": "no-store, no-cache, must-revalidate",
            },
        ))
    except Exception as e:
        import logging
        logging.getLogger("ashley.export").exception("export failed: %s", e)
        return _with_cors(_StarletteJSON(
            {"error": f"Export failed: {e}"},
            status_code=500,
        ))


def register_routes(app):
    """Insert API routes at the BEGINNING of the Starlette router.
    Include OPTIONS methods for CORS preflight."""
    # ── Data export (v0.19.7) ──
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/export/data", _export_data_endpoint, methods=["GET", "OPTIONS"]))
    # ── Mobile API (v0.18.2) ──
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/status", _mobile_status_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/pairing_token", _mobile_pairing_token_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/qr_payload", _mobile_qr_payload_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/regen_token", _mobile_regen_token_endpoint, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/chat", _mobile_chat_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/facts", _mobile_facts_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/send", _mobile_send_endpoint, methods=["POST", "OPTIONS"]))
    # ── tunnel_url para auto-recovery (v0.18.2) ──
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/tunnel_url", _mobile_tunnel_url_endpoint, methods=["GET", "OPTIONS"]))
    # ── Sync endpoints (v0.18.2 — para brain JS offline) ──
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/sync_prompts", _mobile_sync_prompts_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/sync_state", _mobile_sync_state_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/mobile/sync_push", _mobile_sync_push_endpoint, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/transcribe", _transcribe_endpoint, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/whisper/status", _whisper_status_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/tts", _tts_endpoint, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/wake_word/pause", _wake_word_pause, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/wake_word/resume", _wake_word_resume, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/wake_word/debug", _wake_word_debug, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/wake_word/test_trigger", _wake_word_test_trigger,
        methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/shutdown", _shutdown_endpoint, methods=["POST", "OPTIONS"]))
