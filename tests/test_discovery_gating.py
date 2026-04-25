"""Tests for the discovery gating logic (v0.13).

Focuses on two pieces:
  • `topic_share.last_user_was_emotional` — helper that scans recent
    user messages and decides whether Ashley should skip discovery.
  • The conditions wiring in reflex_companion (state fields + persist)
    — covered by a lightweight integration-ish test that doesn't boot
    Reflex but verifies save_voice_config round-trips the new field.

We DO NOT test the actual on_load dispatch here — that runs through
Reflex event generators and real Grok calls. The gating logic is
isolated in pure helpers so we can test deterministically.
"""

import pytest

from reflex_companion.topic_share import last_user_was_emotional


# ══════════════════════════════════════════════════════════════════════
#  last_user_was_emotional — el helper clave del gating
# ══════════════════════════════════════════════════════════════════════

def test_last_user_was_emotional_empty_messages_returns_false():
    assert last_user_was_emotional([]) is False


def test_last_user_was_emotional_detects_recent_sadness():
    messages = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola!"},
        {"role": "user", "content": "estoy triste hoy"},
    ]
    assert last_user_was_emotional(messages) is True


def test_last_user_was_emotional_ignores_casual_recent():
    """Si el mensaje emocional está FUERA del lookback, no cuenta.
    Simulamos que el user ya se recompuso hace rato (4 turnos casuales
    recientes > lookback=3)."""
    messages = [
        {"role": "user", "content": "estoy triste hoy"},   # viejo (fuera de lookback)
        {"role": "assistant", "content": "lo siento jefe..."},
        {"role": "user", "content": "oye mira esto"},      # casual
        {"role": "assistant", "content": "qué?"},
        {"role": "user", "content": "este juego está guapo"},  # casual
        {"role": "assistant", "content": "a ver"},
        {"role": "user", "content": "bastante bueno sí"},  # casual
    ]
    # Lookback=3 → mira solo los 3 casuales más recientes, el triste queda fuera
    assert last_user_was_emotional(messages, lookback=3) is False


def test_last_user_was_emotional_respects_lookback_limit():
    """Con lookback=1 solo mira el último mensaje del user."""
    messages = [
        {"role": "user", "content": "estoy triste"},      # emocional antiguo
        {"role": "user", "content": "como va todo"},      # casual reciente
    ]
    assert last_user_was_emotional(messages, lookback=1) is False
    # Pero con lookback=2 sí lo detecta
    assert last_user_was_emotional(messages, lookback=2) is True


def test_last_user_was_emotional_detects_within_multiple_langs():
    for msg in [
        "estoy jodido",
        "i'm exhausted",
        "je suis épuisé",
        "necesito ayuda",
        "i feel alone",
    ]:
        messages = [{"role": "user", "content": msg}]
        assert last_user_was_emotional(messages) is True, f"failed: {msg!r}"


def test_last_user_was_emotional_ignores_assistant_messages():
    """Si Ashley dice 'estoy triste' (improbable pero posible), NO cuenta
    — solo miramos los mensajes del USER."""
    messages = [
        {"role": "assistant", "content": "estoy triste por ti"},
        {"role": "user", "content": "qué tal el día"},
    ]
    assert last_user_was_emotional(messages) is False


def test_last_user_was_emotional_handles_missing_content():
    """Defensive: si algún mensaje no tiene content, no crashea."""
    messages = [
        {"role": "user"},  # no content
        {"role": "user", "content": None},  # None content
        {"role": "user", "content": "todo bien"},
    ]
    # No debería crashear, solo devolver False
    assert last_user_was_emotional(messages) is False


def test_last_user_was_emotional_returns_true_if_any_within_lookback():
    """Si CUALQUIERA de los últimos N mensajes del user fue emocional,
    devuelve True — basta con uno para activar la gating."""
    messages = [
        {"role": "user", "content": "qué tal"},
        {"role": "assistant", "content": "bien"},
        {"role": "user", "content": "estoy fatal"},  # emotional
        {"role": "assistant", "content": "lo siento"},
        {"role": "user", "content": "nada, se me pasará"},  # casual
    ]
    # Default lookback=3 → mira "nada se me pasará", "estoy fatal", "qué tal"
    # "estoy fatal" matches → True
    assert last_user_was_emotional(messages, lookback=3) is True


# ══════════════════════════════════════════════════════════════════════
#  Persistence round-trip: discovery_enabled en voice.json
# ══════════════════════════════════════════════════════════════════════

def test_voice_config_default_discovery_is_off(tmp_path, monkeypatch):
    """El nuevo default para discovery_enabled debe ser False."""
    from reflex_companion import i18n
    monkeypatch.setattr(i18n, "VOICE_FILE", str(tmp_path / "voice.json"))
    cfg = i18n.load_voice_config()
    assert cfg["discovery_enabled"] is False


def test_voice_config_persists_discovery_true(tmp_path, monkeypatch):
    from reflex_companion import i18n
    monkeypatch.setattr(i18n, "VOICE_FILE", str(tmp_path / "voice.json"))
    # Guardar con discovery=True
    i18n.save_voice_config(
        tts_enabled=True,
        elevenlabs_key="sk-x",
        voice_id="v1",
        discovery_enabled=True,
    )
    # Cargar y verificar
    cfg = i18n.load_voice_config()
    assert cfg["discovery_enabled"] is True


def test_voice_config_persists_discovery_false(tmp_path, monkeypatch):
    from reflex_companion import i18n
    monkeypatch.setattr(i18n, "VOICE_FILE", str(tmp_path / "voice.json"))
    i18n.save_voice_config(
        tts_enabled=False,
        elevenlabs_key="",
        voice_id="v1",
        discovery_enabled=False,
    )
    cfg = i18n.load_voice_config()
    assert cfg["discovery_enabled"] is False


def test_voice_config_legacy_file_without_discovery_defaults_off(tmp_path, monkeypatch):
    """Back-compat: un voice.json existente SIN discovery_enabled debe
    leerse como False (nuevo default), no crashear."""
    import json
    from reflex_companion import i18n
    voice_file = tmp_path / "voice.json"
    voice_file.write_text(json.dumps({
        "tts_enabled": True,
        "elevenlabs_key": "sk-x",
        "voice_id": "v1",
        # Ningún campo discovery_enabled — archivo legacy
    }))
    monkeypatch.setattr(i18n, "VOICE_FILE", str(voice_file))
    cfg = i18n.load_voice_config()
    assert cfg["discovery_enabled"] is False
