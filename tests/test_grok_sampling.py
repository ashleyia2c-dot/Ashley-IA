"""Verifica que los sampling penalties se pasan correctamente a la API
de xAI en las rutas conversacionales, y NO en detect_intended_action
(que queremos determinista)."""

from unittest import mock


def test_chat_create_wrapper_sets_penalty_defaults_on_standard_model():
    from reflex_companion.grok_client import _chat_create, CHAT_FREQUENCY_PENALTY, CHAT_PRESENCE_PENALTY

    fake_client = mock.MagicMock()
    fake_client.chat.create = mock.MagicMock()

    # grok-3-fast soporta penalties
    _chat_create(fake_client, model="grok-3-fast")

    args, kwargs = fake_client.chat.create.call_args
    assert kwargs["frequency_penalty"] == CHAT_FREQUENCY_PENALTY
    assert kwargs["presence_penalty"] == CHAT_PRESENCE_PENALTY
    assert kwargs["model"] == "grok-3-fast"


def test_chat_create_skips_penalties_for_fast_family():
    """La familia grok-4-1-fast NO soporta penalties.
    El wrapper debe omitir esos params para ellos, no crashear con 400."""
    from reflex_companion.grok_client import _chat_create

    for model in ["grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning", "grok-4-1-fast"]:
        fake_client = mock.MagicMock()
        fake_client.chat.create = mock.MagicMock()
        _chat_create(fake_client, model=model)
        _, kwargs = fake_client.chat.create.call_args
        assert "frequency_penalty" not in kwargs, f"leaked on {model}"
        assert "presence_penalty" not in kwargs, f"leaked on {model}"
        assert kwargs["model"] == model


def test_model_supports_penalties_helper():
    from reflex_companion.grok_client import _model_supports_penalties
    # Standard models → supports
    assert _model_supports_penalties("grok-3") is True
    assert _model_supports_penalties("grok-3-fast") is True
    assert _model_supports_penalties("grok-3-mini") is True
    assert _model_supports_penalties("grok-4") is True
    # grok-4.20 non-reasoning → supports
    assert _model_supports_penalties("grok-4.20-0309-non-reasoning") is True
    # Reasoning models → doesn't support
    assert _model_supports_penalties("grok-4.20-0309-reasoning") is False
    # Familia grok-4-1-fast ENTERA → no soporta (ni la non-reasoning)
    assert _model_supports_penalties("grok-4-1-fast-reasoning") is False
    assert _model_supports_penalties("grok-4-1-fast-non-reasoning") is False
    assert _model_supports_penalties("grok-4-1-fast") is False
    # Case-insensitive
    assert _model_supports_penalties("Grok-4-1-Fast-Non-Reasoning") is False
    assert _model_supports_penalties("Grok-4.20-0309-Reasoning") is False
    # Empty/None defensive — defaulteamos a True (los modelos clásicos
    # sin nombre específico son los de GPT-style estándar)
    assert _model_supports_penalties("") is True
    assert _model_supports_penalties(None) is True


def test_chat_create_wrapper_respects_override():
    """Si el caller especifica los valores explícitamente, se respetan."""
    from reflex_companion.grok_client import _chat_create

    fake_client = mock.MagicMock()
    fake_client.chat.create = mock.MagicMock()

    _chat_create(
        fake_client,
        model="test",
        frequency_penalty=0.9,
        presence_penalty=0.7,
    )

    _, kwargs = fake_client.chat.create.call_args
    assert kwargs["frequency_penalty"] == 0.9
    assert kwargs["presence_penalty"] == 0.7


def test_penalty_values_in_expected_range():
    """Valores estándar OpenAI están en [0, 2]. Nuestros defaults deben
    estar en zona conservadora."""
    from reflex_companion.grok_client import CHAT_FREQUENCY_PENALTY, CHAT_PRESENCE_PENALTY
    assert 0.2 <= CHAT_FREQUENCY_PENALTY <= 1.0
    assert 0.0 <= CHAT_PRESENCE_PENALTY <= 1.0
