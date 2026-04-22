"""Tests for llm_provider.py — multi-provider routing (xAI, OpenRouter, Ollama).

No hace llamadas reales a ningún endpoint. Mockeamos load_voice_config()
para controlar qué provider reporta activo, y urllib.request para simular
Ollama corriendo/no corriendo.
"""

from unittest import mock

import pytest

from reflex_companion import llm_provider as lp


# ══════════════════════════════════════════════════════════════════════
#  get_active_config — resolución de config según provider
# ══════════════════════════════════════════════════════════════════════

def _mock_config(**overrides):
    """Helper: mockea load_voice_config() con un dict base + overrides."""
    base = {
        "llm_provider": "xai",
        "openrouter_key": "",
        "llm_model": "",
    }
    base.update(overrides)
    return mock.patch("reflex_companion.i18n.load_voice_config", return_value=base)


def test_active_config_defaults_to_xai():
    with _mock_config():
        cfg = lp.get_active_config()
    assert cfg["provider"] == "xai"
    # xAI usa SDK nativo → base_url vacío
    assert cfg["base_url"] == ""
    # Modelo por defecto = GROK_MODEL o el primer XAI_MODELS
    assert cfg["model"]  # non-empty


def test_active_config_openrouter_resolves_key_and_baseurl():
    with _mock_config(llm_provider="openrouter", openrouter_key="sk-or-abc"):
        cfg = lp.get_active_config()
    assert cfg["provider"] == "openrouter"
    assert cfg["api_key"] == "sk-or-abc"
    assert cfg["base_url"] == "https://openrouter.ai/api/v1"
    # Default model: primer OPENROUTER_MODELS
    assert cfg["model"] == lp.OPENROUTER_MODELS[0][0]


def test_active_config_openrouter_respects_user_model():
    with _mock_config(llm_provider="openrouter", openrouter_key="sk-or-abc",
                      llm_model="anthropic/claude-haiku-4.5"):
        cfg = lp.get_active_config()
    assert cfg["model"] == "anthropic/claude-haiku-4.5"


def test_active_config_ollama_uses_localhost():
    with _mock_config(llm_provider="ollama"):
        cfg = lp.get_active_config()
    assert cfg["provider"] == "ollama"
    # Ollama no requiere key real — pasamos "ollama" dummy al OpenAI SDK
    assert cfg["api_key"] == "ollama"
    assert cfg["base_url"] == "http://localhost:11434/v1"
    # Default model
    assert cfg["model"] == lp.OLLAMA_DEFAULT_MODEL


def test_active_config_ollama_respects_user_model():
    with _mock_config(llm_provider="ollama", llm_model="qwen2.5:7b"):
        cfg = lp.get_active_config()
    assert cfg["model"] == "qwen2.5:7b"


# ══════════════════════════════════════════════════════════════════════
#  is_* flags
# ══════════════════════════════════════════════════════════════════════

def test_is_xai_flag():
    with _mock_config():
        assert lp.is_xai() is True
        assert lp.is_openrouter() is False
        assert lp.is_ollama() is False


def test_is_openrouter_flag():
    with _mock_config(llm_provider="openrouter"):
        assert lp.is_xai() is False
        assert lp.is_openrouter() is True
        assert lp.is_ollama() is False


def test_is_ollama_flag():
    with _mock_config(llm_provider="ollama"):
        assert lp.is_xai() is False
        assert lp.is_openrouter() is False
        assert lp.is_ollama() is True


def test_is_openai_compat_covers_openrouter_and_ollama():
    """is_openai_compat() agrupa los dos providers que comparten el path
    OpenAI-compat. El dispatcher usa este flag para decidir qué stream
    inicializar."""
    with _mock_config(llm_provider="xai"):
        assert lp.is_openai_compat() is False
    with _mock_config(llm_provider="openrouter"):
        assert lp.is_openai_compat() is True
    with _mock_config(llm_provider="ollama"):
        assert lp.is_openai_compat() is True


def test_supports_web_search_only_for_xai():
    """web_search sólo existe en el SDK nativo de xAI."""
    with _mock_config(llm_provider="xai"):
        assert lp.supports_web_search() is True
    with _mock_config(llm_provider="openrouter"):
        assert lp.supports_web_search() is False
    with _mock_config(llm_provider="ollama"):
        assert lp.supports_web_search() is False


# ══════════════════════════════════════════════════════════════════════
#  Ollama detection + model listing
# ══════════════════════════════════════════════════════════════════════

def test_is_ollama_available_true_when_ping_ok():
    """Simula Ollama respondiendo 200 a /api/version."""
    fake_resp = mock.MagicMock()
    fake_resp.status = 200
    fake_resp.__enter__ = mock.MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = mock.MagicMock(return_value=False)

    with mock.patch("urllib.request.urlopen", return_value=fake_resp):
        assert lp.is_ollama_available(timeout=0.1) is True


def test_is_ollama_available_false_on_connection_refused():
    with mock.patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
        assert lp.is_ollama_available(timeout=0.1) is False


def test_is_ollama_available_false_on_timeout():
    import socket
    with mock.patch("urllib.request.urlopen", side_effect=socket.timeout()):
        assert lp.is_ollama_available(timeout=0.1) is False


def test_list_ollama_models_parses_tags_response():
    """Ollama /api/tags responde {"models": [{"name": "llama3.2:latest"}, ...]}"""
    import json as _json
    fake_body = _json.dumps({
        "models": [
            {"name": "llama3.2:latest", "size": 123},
            {"name": "qwen2.5:7b", "size": 456},
            {"name": "mistral:latest", "size": 789},
        ]
    }).encode("utf-8")

    fake_resp = mock.MagicMock()
    fake_resp.read = mock.MagicMock(return_value=fake_body)
    fake_resp.__enter__ = mock.MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = mock.MagicMock(return_value=False)

    with mock.patch("urllib.request.urlopen", return_value=fake_resp):
        models = lp.list_ollama_models()

    assert models == ["llama3.2:latest", "qwen2.5:7b", "mistral:latest"]


def test_list_ollama_models_empty_when_ollama_down():
    with mock.patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
        assert lp.list_ollama_models() == []


def test_list_ollama_models_handles_malformed_json():
    fake_resp = mock.MagicMock()
    fake_resp.read = mock.MagicMock(return_value=b"not json")
    fake_resp.__enter__ = mock.MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = mock.MagicMock(return_value=False)

    with mock.patch("urllib.request.urlopen", return_value=fake_resp):
        assert lp.list_ollama_models() == []


# ══════════════════════════════════════════════════════════════════════
#  Penalty support detection (OpenAI-compat path)
# ══════════════════════════════════════════════════════════════════════

def test_openai_compat_penalty_helper_rejects_grok_reasoning():
    """Grok reasoning rechaza penalties aun pasando por OpenRouter."""
    assert lp._openai_compat_supports_penalties("x-ai/grok-4-reasoning") is False
    assert lp._openai_compat_supports_penalties("x-ai/grok-4.1-fast") is False


def test_openai_compat_penalty_helper_accepts_normal_models():
    assert lp._openai_compat_supports_penalties("anthropic/claude-sonnet-4.6") is True
    assert lp._openai_compat_supports_penalties("deepseek/deepseek-chat") is True
    assert lp._openai_compat_supports_penalties("llama3.2") is True  # Ollama-style
    assert lp._openai_compat_supports_penalties("") is True
    assert lp._openai_compat_supports_penalties(None) is True


def test_build_sampling_kwargs_creative_true():
    kw = lp._build_sampling_kwargs("llama3.2", creative=True)
    assert kw == {"frequency_penalty": 0.5, "presence_penalty": 0.3}


def test_build_sampling_kwargs_creative_false():
    kw = lp._build_sampling_kwargs("llama3.2", creative=False)
    assert kw == {}


def test_build_sampling_kwargs_skips_penalties_for_grok_reasoning():
    # Aun creative=True, si el modelo no soporta penalties → dict vacío
    kw = lp._build_sampling_kwargs("x-ai/grok-4.1-fast", creative=True)
    assert kw == {}


# ══════════════════════════════════════════════════════════════════════
#  Backward-compat aliases
# ══════════════════════════════════════════════════════════════════════

def test_openrouter_aliases_point_to_new_functions():
    """El código histórico llama a las funciones como openrouter_*. Los
    alias deben seguir funcionando sin cambios."""
    assert lp.openrouter_stream is lp.openai_compat_stream
    assert lp.openrouter_complete is lp.openai_compat_complete
    assert lp.openrouter_simple is lp.openai_compat_simple
