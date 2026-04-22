"""Tests for api_routes TTS backend dispatcher.

No hace llamadas reales a ElevenLabs/Kokoro/VoiceVox. Mockeamos
urllib.request para simular las respuestas de cada servicio.

Probamos las funciones _tts_* directamente (unidad), no a través de
Starlette, porque eso requeriría levantar el app entero.
"""

import io
from unittest import mock

import pytest

from reflex_companion import api_routes as api


# ══════════════════════════════════════════════════════════════════════
#  _tts_elevenlabs
# ══════════════════════════════════════════════════════════════════════

def test_elevenlabs_raises_when_no_key():
    cfg = {"elevenlabs_key": "", "voice_id": "xxx"}
    with pytest.raises(api._TTSError) as exc_info:
        api._tts_elevenlabs("hello", cfg)
    assert exc_info.value.error == "no_key"
    assert exc_info.value.status_code == 400


def test_elevenlabs_raises_when_key_too_short():
    cfg = {"elevenlabs_key": "abc", "voice_id": "xxx"}
    with pytest.raises(api._TTSError) as exc_info:
        api._tts_elevenlabs("hello", cfg)
    assert exc_info.value.error == "no_key"


def test_elevenlabs_success_path_returns_mp3():
    """Simula respuesta exitosa de ElevenLabs."""
    fake_audio = b"MP3FAKEDATA" * 100
    fake_resp = mock.MagicMock()
    fake_resp.read = mock.MagicMock(return_value=fake_audio)

    cfg = {"elevenlabs_key": "sk-eleven-longenough-key", "voice_id": "xxx"}
    with mock.patch("urllib.request.urlopen", return_value=fake_resp):
        audio, media_type = api._tts_elevenlabs("hello", cfg)

    assert audio == fake_audio
    assert media_type == "audio/mpeg"


# ══════════════════════════════════════════════════════════════════════
#  _tts_kokoro
# ══════════════════════════════════════════════════════════════════════

def test_kokoro_success_returns_mp3():
    fake_audio = b"KOKOROAUDIO" * 50
    fake_resp = mock.MagicMock()
    fake_resp.read = mock.MagicMock(return_value=fake_audio)

    cfg = {"kokoro_url": "http://localhost:8880", "kokoro_voice": "af_bella"}
    with mock.patch("urllib.request.urlopen", return_value=fake_resp):
        audio, media_type = api._tts_kokoro("hello", cfg)

    assert audio == fake_audio
    assert media_type == "audio/mpeg"


def test_kokoro_unreachable_raises_friendly_error():
    """Si Kokoro no está corriendo, el error debe mencionar dónde instalar."""
    cfg = {"kokoro_url": "http://localhost:8880", "kokoro_voice": "af_bella"}
    with mock.patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
        with pytest.raises(api._TTSError) as exc_info:
            api._tts_kokoro("hello", cfg)
    assert exc_info.value.error == "unreachable"
    assert "Kokoro-FastAPI" in exc_info.value.detail


def test_kokoro_sends_correct_payload():
    """Verificamos que se arma el JSON correcto para el endpoint OpenAI-compat."""
    captured = {}

    def _fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["data"] = req.data
        captured["method"] = req.get_method()
        captured["headers"] = dict(req.headers)
        fake_resp = mock.MagicMock()
        fake_resp.read = mock.MagicMock(return_value=b"audio")
        return fake_resp

    cfg = {"kokoro_url": "http://localhost:8880", "kokoro_voice": "af_bella"}
    with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
        api._tts_kokoro("hello world", cfg)

    assert captured["url"] == "http://localhost:8880/v1/audio/speech"
    assert captured["method"] == "POST"
    import json
    payload = json.loads(captured["data"])
    assert payload["model"] == "kokoro"
    assert payload["voice"] == "af_bella"
    assert payload["input"] == "hello world"


# ══════════════════════════════════════════════════════════════════════
#  _tts_voicevox
# ══════════════════════════════════════════════════════════════════════

def test_voicevox_two_step_flow_returns_wav():
    """VoiceVox requiere 2 calls: audio_query → synthesis. Ambas deben
    mockearse para que el test pase. Devolvemos WAV al final."""
    responses = [
        # Primera llamada: audio_query → devuelve el JSON de query
        b'{"speedScale": 1.0, "accent_phrases": []}',
        # Segunda llamada: synthesis → devuelve audio WAV
        b"RIFFWAVFAKEDATA" + b"\x00" * 100,
    ]
    call_count = [0]

    def _fake_urlopen(req, timeout=None):
        fake_resp = mock.MagicMock()
        fake_resp.read = mock.MagicMock(return_value=responses[call_count[0]])
        call_count[0] += 1
        return fake_resp

    cfg = {"voicevox_url": "http://localhost:50021", "voicevox_speaker": "1"}
    with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
        audio, media_type = api._tts_voicevox("こんにちは", cfg)

    assert audio.startswith(b"RIFFWAV")
    assert media_type == "audio/wav"
    assert call_count[0] == 2, "Both audio_query and synthesis must be called"


def test_voicevox_unreachable_raises_friendly_error():
    cfg = {"voicevox_url": "http://localhost:50021", "voicevox_speaker": "1"}
    with mock.patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
        with pytest.raises(api._TTSError) as exc_info:
            api._tts_voicevox("hello", cfg)
    assert exc_info.value.error == "unreachable"
    assert "voicevox.hiroshiba.jp" in exc_info.value.detail


# ══════════════════════════════════════════════════════════════════════
#  Backend registry integrity
# ══════════════════════════════════════════════════════════════════════

def test_backend_registry_has_all_expected_providers():
    """El dict _TTS_BACKENDS debe mapear todos los providers no-webspeech."""
    assert set(api._TTS_BACKENDS.keys()) == {"elevenlabs", "kokoro", "voicevox"}


def test_tts_error_preserves_status_code():
    err = api._TTSError(502, "network", "timeout")
    assert err.status_code == 502
    assert err.error == "network"
    assert err.detail == "timeout"
