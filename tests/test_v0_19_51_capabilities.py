"""Regression tests para v0.19.51 — capabilities por modelo + UI banner.

User pidió: "explica bien al user los límites de cada LLM, así si quiere
usar Claude porque le parece más listo que Grok pues sabe que pierde
ciertas funciones".

Implementación:
  • llm_provider._MODEL_CAPABILITIES: tabla por model_id con vision /
    web_search / actions / quality
  • get_model_capabilities(model_id) con heuristics para modelos Ollama
    no listados (vision por keywords "llava/vl/vision", actions por
    sufijo de tamaño)
  • State.active_model_supports_vision, .active_model_actions_level,
    .active_model_quality_label — computed vars reactivos
  • _caps_banner(warning_text) — helper UI que muestra en cada
    sub-panel (xAI/OpenRouter/Ollama) qué pierde/gana el user con el
    modelo activo
  • i18n × 7 idiomas: caps_banner_title, caps_vision_yes/no, caps_actions_*,
    caps_websearch_yes/no, caps_quality_label, caps_warning_xai/or/oll
"""
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  _MODEL_CAPABILITIES + get_model_capabilities
# ════════════════════════════════════════════════════════════════════════


class TestModelCapabilitiesTable:
    def test_xai_models_all_have_vision_and_websearch(self):
        """xAI siempre tiene vision + web_search nativo via SDK."""
        from reflex_companion.llm_provider import (
            get_model_capabilities, XAI_MODELS,
        )
        for model_id, _label, _notes in XAI_MODELS:
            caps = get_model_capabilities(model_id)
            assert caps["vision"], f"xAI {model_id} debería tener vision"
            assert caps["web_search"], f"xAI {model_id} debería tener web_search"
            assert caps["actions"] == "high", (
                f"xAI {model_id} debería tener actions=high (modelo grande)"
            )

    def test_openrouter_no_websearch_for_any_model(self):
        """OpenRouter NO tiene web_search nativo — el path OpenAI-compat
        no expone tools de búsqueda. Aplica a TODOS los modelos OR."""
        from reflex_companion.llm_provider import (
            get_model_capabilities, OPENROUTER_MODELS,
        )
        for model_id, _label, _notes in OPENROUTER_MODELS:
            caps = get_model_capabilities(model_id)
            assert not caps["web_search"], (
                f"OpenRouter {model_id} no debería tener web_search"
            )

    def test_known_no_vision_models_marked(self):
        """DeepSeek y MiniMax M2 NO soportan vision. Critical para gating
        del toggle 👁."""
        from reflex_companion.llm_provider import get_model_capabilities
        assert not get_model_capabilities("deepseek/deepseek-chat")["vision"]
        assert not get_model_capabilities("minimax/minimax-m2")["vision"]

    def test_claude_supports_vision(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("anthropic/claude-sonnet-4.6")["vision"]
        assert get_model_capabilities("anthropic/claude-haiku-4.5")["vision"]

    def test_gemini_gpt_grok_via_or_have_vision(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("google/gemini-2.5-flash")["vision"]
        assert get_model_capabilities("openai/gpt-5")["vision"]
        assert get_model_capabilities("x-ai/grok-4.1-fast")["vision"]

    def test_ollama_small_models_marked_low_actions(self):
        """Llama3.2 3B y Mistral 7B small son notoriamente flaky con
        action tags. Marcados como low explicitamente."""
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("llama3.2")["actions"] == "low"
        assert get_model_capabilities("mistral")["actions"] == "low"

    def test_ollama_8b_models_marked_ok_actions(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("llama3.1:8b")["actions"] == "ok"
        assert get_model_capabilities("qwen2.5:7b")["actions"] == "ok"


class TestUnknownModelHeuristics:
    """Para modelos Ollama que el user bajó pero no son los sugeridos,
    inferimos capabilities por nombre."""

    def test_vision_keyword_in_name_marks_as_vision(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("custom-llava-7b")["vision"]
        assert get_model_capabilities("qwen2-vl:13b")["vision"]
        assert get_model_capabilities("foo-vision-model")["vision"]

    def test_size_indicator_70b_marks_high_actions(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("custom-model:70b")["actions"] == "high"
        assert get_model_capabilities("foo-13b")["actions"] == "high"

    def test_size_indicator_7b_marks_ok_actions(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("custom:7b")["actions"] == "ok"
        assert get_model_capabilities("model-8b")["actions"] == "ok"

    def test_unknown_no_size_marks_low(self):
        from reflex_companion.llm_provider import get_model_capabilities
        assert get_model_capabilities("totally-random-model")["actions"] == "low"

    def test_unknown_never_has_websearch(self):
        from reflex_companion.llm_provider import get_model_capabilities
        # web_search es solo xAI; cualquier otro = False (incluso unknowns)
        for unknown in ["random", "foo:13b", "vision-model"]:
            assert not get_model_capabilities(unknown)["web_search"]


# ════════════════════════════════════════════════════════════════════════
#  i18n strings × 7 idiomas
# ════════════════════════════════════════════════════════════════════════


class TestCapsI18n:
    @pytest.mark.parametrize("lang", ["en", "es", "fr", "ja", "de", "ru", "ko"])
    @pytest.mark.parametrize("key", [
        "caps_banner_title",
        "caps_vision_yes", "caps_vision_no",
        "caps_actions_high", "caps_actions_ok", "caps_actions_low",
        "caps_websearch_yes", "caps_websearch_no",
        "caps_quality_label",
        "caps_warning_xai", "caps_warning_or", "caps_warning_oll",
    ])
    def test_caps_string_in_all_languages(self, lang, key):
        """Cada string del banner debe estar traducido en los 7 idiomas."""
        from reflex_companion.i18n import UI
        assert lang in UI
        assert key in UI[lang], f"v0.19.51: falta {key!r} en idioma {lang!r}"
        assert UI[lang][key], f"v0.19.51: {key} vacío en {lang!r}"


# ════════════════════════════════════════════════════════════════════════
#  Helper UI _caps_banner
# ════════════════════════════════════════════════════════════════════════


class TestCapsBannerHelper:
    def test_helper_exists_in_module(self):
        """v0.19.51 — _caps_banner es función module-level usada por
        Settings dialog en cada sub-panel (xAI/OR/Ollama)."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        assert "def _caps_banner(" in src

    def test_helper_invoked_in_three_subpanels(self):
        """Debe invocarse 3 veces (uno por cada sub-panel de provider)
        con el warning text correspondiente."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        assert "_caps_banner(State.t[\"caps_warning_xai\"])" in src
        assert "_caps_banner(State.t[\"caps_warning_or\"])" in src
        assert "_caps_banner(State.t[\"caps_warning_oll\"])" in src
