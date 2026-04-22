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
    "Access-Control-Allow-Headers": "Content-Type, X-Requested-With",
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
        from .whisper_stt import transcribe_bytes, is_loaded, is_loading, warmup
        # Si el modelo no está listo, informar al frontend y seguir descargando
        if not is_loaded():
            if not is_loading():
                warmup()  # iniciar descarga en background
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
    from .whisper_stt import is_loaded, is_loading, load_error
    return _with_cors(_StarletteJSON({
        "loaded": is_loaded(),
        "loading": is_loading(),
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
    """Call ElevenLabs TTS API and return (audio_bytes, 'audio/mpeg')."""
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
    url = f"{base}/v1/audio/speech"
    payload = _json.dumps({
        "model": "kokoro",
        "voice": voice,
        "input": text,
        "response_format": "mp3",
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


def register_routes(app):
    """Insert API routes at the BEGINNING of the Starlette router.
    Include OPTIONS methods for CORS preflight."""
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/transcribe", _transcribe_endpoint, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/whisper/status", _whisper_status_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/tts", _tts_endpoint, methods=["POST", "OPTIONS"]))
