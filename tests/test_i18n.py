"""
test_i18n.py — Tests for the i18n module (reflex_companion/i18n.py).

Covers: normalize_lang, ui, act_desc, key_labels, time_ctx,
        save_language / load_language roundtrip,
        save_voice_config / load_voice_config roundtrip,
        and default voice config values.
"""

import json
import os
import pytest

from reflex_companion import i18n
from reflex_companion.i18n import (
    normalize_lang,
    ui,
    act_desc,
    key_labels,
    time_ctx,
    save_language,
    load_language,
    save_voice_config,
    load_voice_config,
    DEFAULT_LANG,
    DEFAULT_VOICE_ID,
    SUPPORTED,
    UI,
    ACT_DESC,
    KEY_LABELS,
    TIME_CTX,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  normalize_lang
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalizeLang:

    def test_en_lowercase(self):
        assert normalize_lang("en") == "en"

    def test_es_lowercase(self):
        assert normalize_lang("es") == "es"

    def test_uppercase_ES(self):
        assert normalize_lang("ES") == "es"

    def test_uppercase_EN(self):
        assert normalize_lang("EN") == "en"

    def test_mixed_case(self):
        assert normalize_lang("Es") == "es"

    def test_fr_lowercase(self):
        assert normalize_lang("fr") == "fr"

    def test_uppercase_FR(self):
        assert normalize_lang("FR") == "fr"

    def test_unsupported_language_returns_default(self):
        assert normalize_lang("de") == "en"

    def test_none_returns_default(self):
        assert normalize_lang(None) == "en"

    def test_empty_string_returns_default(self):
        assert normalize_lang("") == "en"

    def test_whitespace_only_returns_default(self):
        assert normalize_lang("   ") == "en"

    def test_long_string_truncated_to_two_chars(self):
        assert normalize_lang("english") == "en"

    def test_long_unsupported(self):
        assert normalize_lang("german") == "en"

    def test_whitespace_around_valid(self):
        assert normalize_lang("  es  ") == "es"

    def test_french_word_resolves_to_fr(self):
        # "french" → "fr" truncation → supported → fr
        assert normalize_lang("french") == "fr"


# ═══════════════════════════════════════════════════════════════════════════════
#  UI dict accessor
# ═══════════════════════════════════════════════════════════════════════════════

class TestUi:

    def test_en_returns_dict(self):
        result = ui("en")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_es_returns_dict(self):
        result = ui("es")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_fr_returns_dict(self):
        result = ui("fr")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_supported_languages_have_same_keys(self):
        """Todos los idiomas soportados deben tener exactamente las mismas
        keys — si falta alguna, un user de esa lengua vería texto en blanco."""
        en_keys = set(ui("en").keys())
        for lang in SUPPORTED:
            lang_keys = set(ui(lang).keys())
            assert lang_keys == en_keys, (
                f"UI key mismatch in '{lang}' — only in EN: {en_keys - lang_keys}, "
                f"only in {lang}: {lang_keys - en_keys}"
            )

    def test_unsupported_falls_back_to_en(self):
        result = ui("de")
        assert result == ui("en")

    def test_contains_expected_keys(self):
        en = ui("en")
        expected = [
            "brand_subtitle", "status_thinking", "status_online",
            "input_placeholder", "btn_send", "pill_memories",
            "mem_title", "act_title", "lang_label",
        ]
        for key in expected:
            assert key in en, f"Missing expected key: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
#  ACT_DESC dict accessor
# ═══════════════════════════════════════════════════════════════════════════════

class TestActDesc:

    def test_en_returns_dict(self):
        result = act_desc("en")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_es_returns_dict(self):
        result = act_desc("es")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_supported_languages_have_same_keys(self):
        en_keys = set(act_desc("en").keys())
        for lang in SUPPORTED:
            lang_keys = set(act_desc(lang).keys())
            assert lang_keys == en_keys, (
                f"ACT_DESC key mismatch in '{lang}' — only in EN: {en_keys - lang_keys}, "
                f"only in {lang}: {lang_keys - en_keys}"
            )

    def test_fr_returns_dict(self):
        result = act_desc("fr")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_unsupported_falls_back_to_en(self):
        assert act_desc("de") == act_desc("en")

    def test_contains_action_types(self):
        en = act_desc("en")
        expected = [
            "screenshot", "open_app", "play_music", "search_web",
            "open_url", "vol_up", "vol_down", "vol_mute", "vol_set",
            "type_text", "type_in", "write_to_app", "focus_window",
            "hotkey", "press_key", "close_window", "close_tab",
            "remind", "add_important", "done_important", "save_taste",
            "generic",
        ]
        for key in expected:
            assert key in en, f"Missing action description: {key}"


# ═══════════════════════════════════════════════════════════════════════════════
#  KEY_LABELS dict accessor
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeyLabels:

    def test_en_returns_dict(self):
        result = key_labels("en")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_es_returns_dict(self):
        result = key_labels("es")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_supported_languages_have_same_keys(self):
        en_keys = set(key_labels("en").keys())
        for lang in SUPPORTED:
            lang_keys = set(key_labels(lang).keys())
            assert lang_keys == en_keys

    def test_fr_returns_dict(self):
        assert isinstance(key_labels("fr"), dict)
        assert len(key_labels("fr")) > 0

    def test_unsupported_falls_back_to_en(self):
        assert key_labels("zh") == key_labels("en")

    def test_contains_expected_keys(self):
        en = key_labels("en")
        for key in ("space", "backspace", "delete", "home", "end"):
            assert key in en


# ═══════════════════════════════════════════════════════════════════════════════
#  TIME_CTX dict accessor
# ═══════════════════════════════════════════════════════════════════════════════

class TestTimeCtx:

    def test_en_returns_dict(self):
        result = time_ctx("en")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_es_returns_dict(self):
        result = time_ctx("es")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_supported_languages_have_same_keys(self):
        en_keys = set(time_ctx("en").keys())
        for lang in SUPPORTED:
            lang_keys = set(time_ctx(lang).keys())
            assert lang_keys == en_keys, (
                f"TIME_CTX key mismatch in '{lang}' — only in EN: {en_keys - lang_keys}, "
                f"only in {lang}: {lang_keys - en_keys}"
            )

    def test_fr_returns_dict(self):
        assert isinstance(time_ctx("fr"), dict)
        assert len(time_ctx("fr")) > 0

    def test_unsupported_falls_back_to_en(self):
        assert time_ctx("ja") == time_ctx("en")

    def test_contains_time_of_day_parts(self):
        en = time_ctx("en")
        for key in ("part_dawn", "part_morning", "part_afternoon",
                     "part_evening", "part_night"):
            assert key in en

    def test_contains_datetime_line(self):
        en = time_ctx("en")
        assert "datetime_line" in en

    def test_contains_days_and_months(self):
        en = time_ctx("en")
        assert "days" in en
        assert "months" in en
        assert isinstance(en["days"], dict)
        assert isinstance(en["months"], dict)
        assert len(en["days"]) == 7
        assert len(en["months"]) == 12


# ═══════════════════════════════════════════════════════════════════════════════
#  save_language / load_language roundtrip
# ═══════════════════════════════════════════════════════════════════════════════

class TestLanguagePersistence:

    def test_save_and_load_en(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        save_language("en")
        assert load_language() == "en"

    def test_save_and_load_es(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        save_language("es")
        assert load_language() == "es"

    def test_save_normalizes(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        save_language("ES")
        assert load_language() == "es"

    def test_save_and_load_fr(self, tmp_path, monkeypatch):
        """El francés debe persistir igual que EN/ES."""
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        save_language("fr")
        assert load_language() == "fr"

    def test_save_unsupported_defaults_to_en(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        save_language("de")  # alemán no soportado
        assert load_language() == "en"

    def test_load_missing_file_returns_default(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "nonexistent.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        assert load_language() == DEFAULT_LANG

    def test_load_corrupt_file_returns_default(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        with open(lang_file, "w") as f:
            f.write("not valid json {{{")
        assert load_language() == DEFAULT_LANG

    def test_file_contents_are_valid_json(self, tmp_path, monkeypatch):
        lang_file = str(tmp_path / "language.json")
        monkeypatch.setattr(i18n, "LANG_FILE", lang_file)
        save_language("es")
        with open(lang_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {"language": "es"}


# ═══════════════════════════════════════════════════════════════════════════════
#  save_voice_config / load_voice_config roundtrip
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoiceConfigPersistence:

    def test_default_values_no_file(self, tmp_path, monkeypatch):
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        cfg = load_voice_config()
        assert cfg["tts_enabled"] is False
        assert cfg["elevenlabs_key"] == ""
        assert cfg["openai_key"] == ""
        assert cfg["voice_id"] == DEFAULT_VOICE_ID
        assert cfg["voice_mode"] is False

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        save_voice_config(
            tts_enabled=True,
            elevenlabs_key="sk_test_123",
            voice_id="custom_voice_id",
            openai_key="oai_key",
            voice_mode=True,
        )
        cfg = load_voice_config()
        assert cfg["tts_enabled"] is True
        assert cfg["elevenlabs_key"] == "sk_test_123"
        assert cfg["openai_key"] == "oai_key"
        assert cfg["voice_id"] == "custom_voice_id"
        assert cfg["voice_mode"] is True

    def test_save_minimal_params(self, tmp_path, monkeypatch):
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        save_voice_config(
            tts_enabled=False,
            elevenlabs_key="",
            voice_id="",
        )
        cfg = load_voice_config()
        assert cfg["tts_enabled"] is False
        assert cfg["elevenlabs_key"] == ""
        # Empty voice_id should fall back to DEFAULT_VOICE_ID
        assert cfg["voice_id"] == DEFAULT_VOICE_ID

    def test_corrupt_file_returns_default(self, tmp_path, monkeypatch):
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        with open(voice_file, "w") as f:
            f.write("{corrupt")
        cfg = load_voice_config()
        assert cfg["tts_enabled"] is False
        assert cfg["voice_id"] == DEFAULT_VOICE_ID

    def test_file_contents_are_valid_json(self, tmp_path, monkeypatch):
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        save_voice_config(
            tts_enabled=True,
            elevenlabs_key="key",
            voice_id="vid",
            openai_key="okey",
            voice_mode=True,
        )
        with open(voice_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["tts_enabled"] is True
        assert data["elevenlabs_key"] == "key"
        assert data["openai_key"] == "okey"
        assert data["voice_id"] == "vid"
        assert data["voice_mode"] is True

    def test_voice_mode_defaults_false(self, tmp_path, monkeypatch):
        """save_voice_config without voice_mode kwarg defaults to False."""
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        save_voice_config(tts_enabled=True, elevenlabs_key="k", voice_id="v")
        cfg = load_voice_config()
        assert cfg["voice_mode"] is False

    def test_openai_key_defaults_empty(self, tmp_path, monkeypatch):
        """save_voice_config without openai_key kwarg defaults to ''."""
        voice_file = str(tmp_path / "voice.json")
        monkeypatch.setattr(i18n, "VOICE_FILE", voice_file)
        save_voice_config(tts_enabled=True, elevenlabs_key="k", voice_id="v")
        cfg = load_voice_config()
        assert cfg["openai_key"] == ""
