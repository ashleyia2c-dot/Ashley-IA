"""
api_routes.py — Starlette API endpoints for the Ashley companion app.

Extracted from reflex_companion.py.  Contains the Whisper STT transcription
endpoint, whisper status endpoint, and TTS proxy endpoint, plus CORS helpers.

These endpoints live on the BACKEND (Starlette on backend_port), NOT on the
frontend (Next.js on frontend_port).  The browser loads the app from the
frontend port, so calling /api/* from the same origin would give 405
(Next.js doesn't have these routes).  The JS fetches directly to
127.0.0.1:<backend> and that requires CORS headers (different origins =
frontend vs backend).
"""

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


async def _tts_endpoint(request):
    """POST /api/tts — proxy a ElevenLabs. Lee la key/voice_id del voice.json
    guardado en disco. Evita problemas de CORS del browser a elevenlabs.io."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    import json as _json
    import urllib.request as _urlreq
    import urllib.error as _urlerr
    from . import i18n as _i18n

    try:
        body = await request.json()
    except Exception:
        return _with_cors(_StarletteJSON({"error": "invalid json"}, status_code=400))
    text = ((body or {}).get("text") or "").strip()
    if not text:
        return _with_cors(_StarletteJSON({"error": "empty text"}, status_code=400))

    cfg = _i18n.load_voice_config()
    key = (cfg.get("elevenlabs_key") or "").strip()
    voice_id = (cfg.get("voice_id") or _i18n.DEFAULT_VOICE_ID).strip() or _i18n.DEFAULT_VOICE_ID

    if not key or len(key) < 10:
        return _with_cors(_StarletteJSON({"error": "no_key",
            "detail": "No ElevenLabs API key configured in Settings."}, status_code=400))

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
        audio_bytes = resp.read()
        return _with_cors(_StarletteResponse(
            audio_bytes, media_type="audio/mpeg"
        ))
    except _urlerr.HTTPError as e:
        err_body = ""
        try: err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception: pass
        return _with_cors(_StarletteJSON({
            "error": f"HTTP {e.code}",
            "detail": err_body or str(e),
        }, status_code=502))
    except Exception as e:
        return _with_cors(_StarletteJSON({
            "error": "network",
            "detail": str(e),
        }, status_code=502))


def register_routes(app):
    """Insert API routes at the BEGINNING of the Starlette router.
    Include OPTIONS methods for CORS preflight."""
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/transcribe", _transcribe_endpoint, methods=["POST", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/whisper/status", _whisper_status_endpoint, methods=["GET", "OPTIONS"]))
    app._api.router.routes.insert(0, _StarletteRoute(
        "/api/tts", _tts_endpoint, methods=["POST", "OPTIONS"]))
