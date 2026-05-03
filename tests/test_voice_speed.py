"""Tests para voice_speed (v0.16.14) — slider de velocidad de voz.

v0.16.14 (post-fix) — el cambio a eleven_turbo_v2_5 rompía la
reproducción para algunos voice_ids del user (audio recibido pero no
sonaba). Revertimos a eleven_multilingual_v2 y aplicamos speed
cliente-side via audio.playbackRate (universal con cualquier modelo).

Persistencia: voice.json con clamp 0.5-2.0.

Estos tests bloquean regresión: si alguien rompe el patrón coherente
(modelo + speed), los tests fallan.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROUTES_PY = REPO_ROOT / "reflex_companion" / "api_routes.py"
ASHLEY_VOICE_JS = REPO_ROOT / "assets" / "ashley_voice.js"


# ══════════════════════════════════════════════════════════════════════
#  Persistencia: voice.json carga/guarda voice_speed
# ══════════════════════════════════════════════════════════════════════


class TestVoiceSpeedPersistence:

    def test_default_is_one(self):
        from reflex_companion import i18n, memory
        from unittest.mock import patch
        with patch.object(memory, "load_json", return_value=None):
            cfg = i18n.load_voice_config()
        assert cfg["voice_speed"] == 1.0

    def test_loads_persisted_value(self):
        from reflex_companion import i18n, memory
        from unittest.mock import patch
        fake_data = {"voice_speed": 1.3}
        with patch.object(memory, "load_json", return_value=fake_data):
            cfg = i18n.load_voice_config()
        assert cfg["voice_speed"] == 1.3

    def test_clamps_excessive_values_on_load(self):
        from reflex_companion import i18n, memory
        from unittest.mock import patch
        with patch.object(memory, "load_json", return_value={"voice_speed": 10.0}):
            cfg = i18n.load_voice_config()
        assert cfg["voice_speed"] == 2.0
        with patch.object(memory, "load_json", return_value={"voice_speed": -1.0}):
            cfg = i18n.load_voice_config()
        assert cfg["voice_speed"] == 0.5

    def test_save_clamps_too(self):
        from reflex_companion import i18n, memory
        from unittest.mock import patch
        captured = {}
        def _capture(_path, data):
            captured.update(data)
        with patch.object(memory, "save_json", side_effect=_capture):
            i18n.save_voice_config(
                tts_enabled=True, elevenlabs_key="", voice_id="x",
                voice_speed=10.0,
            )
        assert captured["voice_speed"] == 2.0


# ══════════════════════════════════════════════════════════════════════
#  Backend: providers usan voice_speed
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def api_routes_src() -> str:
    return API_ROUTES_PY.read_text(encoding="utf-8")


class TestElevenLabsPayloadCoherence:
    """v0.16.14 — REVERTIDO el cambio a eleven_turbo_v2_5 porque rompía
    la reproducción para algunos voice_ids del user (audio recibido pero
    no sonaba). Volvimos a eleven_multilingual_v2 (el que el user usaba
    antes y funcionaba). El slider de velocidad ahora se aplica
    cliente-side via audio.playbackRate, que funciona con cualquier
    modelo.

    Este test valida que el payload a ElevenLabs es COHERENTE: si usa
    multilingual_v2, NO envía `speed` (no soportado, ElevenLabs lo
    rechazaría); si en el futuro alguien vuelve a turbo_v2_5, debe
    enviar `speed`.
    """

    def test_uses_multilingual_v2_or_turbo(self, api_routes_src):
        """El modelo debe ser uno reconocido."""
        valid = ["eleven_multilingual_v2", "eleven_turbo_v2_5", "eleven_v3"]
        assert any(
            f'"model_id": "{m}"' in api_routes_src for m in valid
        ), (
            f"Modelo de ElevenLabs no es uno de los conocidos: {valid}"
        )

    def test_speed_only_when_supported(self, api_routes_src):
        """Si el modelo es multilingual_v2 (no soporta speed), el payload
        NO debe incluir 'speed' en voice_settings — ElevenLabs rechazaría
        o ignoraría con warning."""
        if '"model_id": "eleven_multilingual_v2"' in api_routes_src:
            # Buscar dentro del bloque de _tts_elevenlabs si hay speed
            # en voice_settings
            elevenlabs_block = re.search(
                r"def _tts_elevenlabs[\s\S]*?(?=\ndef |\Z)",
                api_routes_src,
            )
            assert elevenlabs_block, "No se localizó _tts_elevenlabs"
            block = elevenlabs_block.group(0)
            assert '"speed":' not in block, (
                "El modelo es multilingual_v2 (NO soporta speed) PERO el "
                "payload incluye 'speed' en voice_settings. ElevenLabs "
                "puede rechazar el request. Quita el speed del payload, "
                "o cambia el modelo a turbo_v2_5/v3 que sí lo soportan."
            )


class TestKokoroPassesSpeed:
    def test_kokoro_payload_includes_speed(self, api_routes_src):
        assert '"speed": speed' in api_routes_src, (
            "_tts_kokoro no pasa speed al endpoint Kokoro — el slider sería "
            "ignorado para usuarios de Kokoro."
        )


class TestVoiceVoxPassesSpeed:
    def test_voicevox_modifies_speedscale(self, api_routes_src):
        assert "speedScale" in api_routes_src, (
            "_tts_voicevox no inyecta speedScale en audio_query — VoiceVox "
            "ignoraría la velocidad y devolvería audio a 1.0x."
        )


# ══════════════════════════════════════════════════════════════════════
#  Frontend: utterance.rate respeta voice_speed
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE_JS.read_text(encoding="utf-8")


class TestFrontendRespectsSpeed:
    def test_voice_speed_in_state(self, voice_js):
        assert "voiceSpeed" in voice_js, (
            "voiceSpeed no está en el state del JS — slider no se aplica."
        )

    def test_web_speech_uses_voice_speed(self, voice_js):
        assert "voiceSpeed" in voice_js
        assert "u.rate = 1.0" not in voice_js, (
            "Detectado u.rate = 1.0 (hardcoded). El slider voice_speed "
            "se ignoraría para Web Speech. Debe ser u.rate = voiceSpeed."
        )

    def test_dom_marker_includes_voice_speed(self, voice_js):
        assert "data-voice-speed" in voice_js, (
            "El JS no lee data-voice-speed del DOM — desincronización con "
            "Settings."
        )

    def test_backend_audio_uses_playbackrate(self, voice_js):
        """v0.16.14 — para backend providers (ElevenLabs/Kokoro/VoiceVox),
        el speed se aplica cliente-side via audio.playbackRate (porque
        ElevenLabs multilingual_v2 NO soporta speed server-side). Sin
        esto el slider no tendría efecto en el TTS principal."""
        # Buscar dentro de _speakBackendTTS
        match = re.search(
            r"_speakBackendTTS[\s\S]{0,4000}?audio\.playbackRate\s*=",
            voice_js,
        )
        assert match, (
            "_speakBackendTTS no asigna audio.playbackRate. El slider de "
            "velocidad NO tendría efecto para ElevenLabs/Kokoro/VoiceVox."
        )

    def test_playbackrate_uses_voice_speed_not_hardcoded(self, voice_js):
        """playbackRate NO debe estar hardcoded a 1.0 — debe leer voiceSpeed."""
        # Patrón malo: playbackRate = 1.0 (hardcoded, ignora slider)
        assert "audio.playbackRate = 1.0" not in voice_js, (
            "Detectado audio.playbackRate = 1.0 hardcoded. El slider "
            "voice_speed sería ignorado. Debe ser audio.playbackRate = speed "
            "(donde speed se calcula de voiceSpeed)."
        )


class TestDomMarkerHasVoiceSpeed:
    def test_marker_includes_voice_speed_attr(self):
        src = (
            REPO_ROOT / "reflex_companion" / "reflex_companion.py"
        ).read_text(encoding="utf-8")
        assert '"data-voice-speed"' in src, (
            "El marker DOM no expone data-voice-speed — JS no se sincroniza "
            "con el Settings del user."
        )


# ══════════════════════════════════════════════════════════════════════
#  i18n: strings del slider en los 3 idiomas
# ══════════════════════════════════════════════════════════════════════


class TestI18nVoiceSpeedStrings:
    def test_all_languages_have_label(self):
        from reflex_companion import i18n
        for lang in ("en", "es", "fr"):
            assert "settings_voice_speed_label" in i18n.UI[lang], (
                f"Falta settings_voice_speed_label en idioma {lang}"
            )
            assert "settings_voice_speed_hint" in i18n.UI[lang], (
                f"Falta settings_voice_speed_hint en idioma {lang}"
            )
