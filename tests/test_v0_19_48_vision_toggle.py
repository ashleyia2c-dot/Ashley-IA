"""Regression tests para v0.19.48 — Vision toggle desacoplado.

Bug raíz: el bg_task corría screen awareness cada 10min con screenshot
adjunto cuando auto_actions estaba ON. El user activaba ⚡ Actions para
poder hacer play_music + click, sin saber que también acoplaba ~50% de
calls invisibles a Grok ($0.05-0.15/día extra). Confirmado con dashboard
real del user: 10 mensajes 'v-' (vision) + 6 'fu-' (followup) en 11 msgs
user reales = 52% de calls invisibles.

Fix: separar vision_enabled de auto_actions. Default OFF. Toggle propio
en el portrait overlay (botón eye, reemplaza el duplicado de focus mode
que ya estaba en el header).
"""
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  Vision flag desacoplado de auto_actions
# ════════════════════════════════════════════════════════════════════════


class TestVisionDecoupled:
    def test_vision_enabled_state_var_exists(self):
        """v0.19.48 — State debe declarar vision_enabled como bool default False."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        assert "vision_enabled: bool = False" in src, (
            "v0.19.48: State debe declarar 'vision_enabled: bool = False' "
            "para opt-in explícito de Screen Awareness"
        )

    def test_bg_task_uses_vision_enabled_not_auto_actions(self):
        """El bg_task debe leer self.vision_enabled (no self.auto_actions)
        para decidir si dispara screen awareness."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        # Buscar el bloque del bg_task que decide vision
        # Debe estar usando vision_enabled, NO auto_actions
        assert "_vision  = self.vision_enabled" in src or \
               "_vision = self.vision_enabled" in src, (
            "v0.19.48: bg_task debe usar self.vision_enabled (no auto_actions) "
            "para gate de screen awareness — antes acoplado, ahora opt-in."
        )

    def test_per_turn_screenshot_uses_vision_enabled(self):
        """v0.19.50 — el screenshot adjunto a cada mensaje user (path 1)
        ahora debe estar gated por self.vision_enabled (no self.auto_actions).

        Antes acoplado a auto_actions: si user activaba ⚡ Actions para
        play_music + click, Ashley empezaba a adjuntar screenshot cada msg
        SIN que el user lo supiera. Y si user activaba solo 👁 Vision, "mira
        mi pantalla" NO funcionaba porque el screenshot no se adjuntaba."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        # El bloque del per-turn screenshot debe usar vision_enabled
        # No es trivial buscar el contexto exacto, así que verificamos que
        # exista el patrón "self.vision_enabled and messages_for_llm"
        assert "self.vision_enabled and messages_for_llm" in src, (
            "v0.19.50: el bloque per-turn screenshot debe usar "
            "vision_enabled (no auto_actions) para gating."
        )

    def test_toggle_vision_enabled_method_exists(self):
        """Hay un toggle dedicado para Vision."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        assert "def toggle_vision_enabled" in src

    def test_default_value_is_false(self):
        """Vision DEBE empezar OFF — antes default ON via auto_actions
        coupling cuando user activaba Actions. Default OFF protege al user
        del coste invisible (~$0.05/día) hasta que opt-in explícito."""
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8",
        )
        assert "vision_enabled: bool = False" in src, (
            "v0.19.48: vision_enabled debe ser False por default."
        )


# ════════════════════════════════════════════════════════════════════════
#  Persistencia en voice.json
# ════════════════════════════════════════════════════════════════════════


class TestVisionPersistence:
    def test_save_voice_config_accepts_vision_enabled_kwarg(self):
        """save_voice_config debe aceptar vision_enabled como parámetro."""
        from reflex_companion import i18n
        import inspect
        sig = inspect.signature(i18n.save_voice_config)
        assert "vision_enabled" in sig.parameters

    def test_load_voice_config_returns_vision_enabled(self):
        """load_voice_config debe devolver vision_enabled (default False)."""
        from reflex_companion import i18n
        with patch("reflex_companion.memory.load_json", return_value={}):
            cfg = i18n.load_voice_config()
            assert "vision_enabled" in cfg
            assert cfg["vision_enabled"] is False  # default

    def test_load_voice_config_respects_persisted_value(self):
        """Si voice.json tiene vision_enabled=true, lo respeta."""
        from reflex_companion import i18n
        # Necesita stub de todos los keys que load_voice_config usa
        fake_data = {
            "tts_enabled": False, "elevenlabs_key": "", "voice_id": "x",
            "voice_mode": False, "vision_enabled": True,
        }
        with patch("reflex_companion.memory.load_json", return_value=fake_data):
            cfg = i18n.load_voice_config()
            assert cfg["vision_enabled"] is True


# ════════════════════════════════════════════════════════════════════════
#  Botón vision en portrait overlay
# ════════════════════════════════════════════════════════════════════════


class TestVisionButtonInUI:
    def test_portrait_overlay_has_vision_button(self):
        """El portrait overlay debe tener el botón eye (vision)."""
        src = (REPO_ROOT / "reflex_companion" / "components.py").read_text(
            encoding="utf-8",
        )
        # El botón vision usa icono "eye" + on_click=toggle_vision_enabled
        assert "toggle_vision_enabled" in src, (
            "v0.19.48: portrait overlay debe tener botón que llama "
            "toggle_vision_enabled"
        )
        assert '"eye"' in src, (
            "v0.19.48: el botón vision usa icono 'eye'"
        )

    def test_focus_mode_no_longer_duplicated_in_portrait(self):
        """El portrait overlay ya NO tiene el botón focus duplicado.
        El focus mode sigue en el header."""
        src = (REPO_ROOT / "reflex_companion" / "components.py").read_text(
            encoding="utf-8",
        )
        # Buscar específicamente en el bloque _portrait_overlay
        # El portrait NO debe tener "focus" como icono.
        # (Sigue habiendo "focus_mode" en otros sitios — el del header)
        portrait_section_start = src.find("def _portrait_overlay")
        portrait_section_end = src.find("def _portrait_view_toggle")
        if portrait_section_start == -1 or portrait_section_end == -1:
            pytest.skip("no se localizaron las funciones — refactor?")
        portrait_block = src[portrait_section_start:portrait_section_end]
        assert '"focus"' not in portrait_block, (
            "v0.19.48: el botón 'focus' del portrait overlay debe estar "
            "reemplazado por 'eye' (vision). El focus sigue en el header."
        )


# ════════════════════════════════════════════════════════════════════════
#  i18n parity para vision_tooltip
# ════════════════════════════════════════════════════════════════════════


class TestVisionTooltipI18n:
    @pytest.mark.parametrize("lang", ["en", "es", "fr", "ja", "de", "ru", "ko"])
    def test_vision_tooltip_in_all_7_languages(self, lang):
        """v0.19.48 — vision_tooltip debe estar en los 7 idiomas."""
        from reflex_companion.i18n import UI
        assert lang in UI
        assert "vision_tooltip" in UI[lang], (
            f"v0.19.48: falta vision_tooltip en idioma {lang!r}"
        )
        assert UI[lang]["vision_tooltip"], (
            f"v0.19.48: vision_tooltip vacío en {lang!r}"
        )

    def test_vision_tooltip_mentions_cost(self):
        """El tooltip debe avisar del coste extra para que el user sepa
        que activarlo cuesta dinero. Transparencia."""
        from reflex_companion.i18n import UI
        for lang in ("en", "es", "fr", "de"):
            text = UI[lang]["vision_tooltip"].lower()
            # Mención al coste — varias formas de decirlo
            has_cost = ("$" in text or "0.05" in text or "api" in text
                        or "coste" in text or "cost" in text or "coût" in text
                        or "kostet" in text)
            assert has_cost, (
                f"v0.19.48 ({lang}): el tooltip debe mencionar coste para "
                f"transparencia. Got: {UI[lang]['vision_tooltip']!r}"
            )


# ════════════════════════════════════════════════════════════════════════
#  Manual de usuario — sección vision en 7 idiomas
# ════════════════════════════════════════════════════════════════════════


class TestVisionInUserManual:
    @pytest.mark.parametrize("lang", ["en", "es", "fr", "ja", "de", "ru", "ko"])
    def test_manual_has_vision_section(self, lang):
        """v0.19.48 — manual_content debe tener sección 'vision' en cada
        idioma con título descriptivo y mención del coste."""
        from reflex_companion import manual_content
        manual = manual_content.get_manual(lang)
        sections = manual.get("sections", [])
        assert sections, f"manual sin sections en idioma {lang!r}"

        vision_sec = next((s for s in sections if s.get("id") == "vision"), None)
        assert vision_sec is not None, (
            f"v0.19.48 ({lang}): falta sección vision en el manual de usuario"
        )
        # Debe tener icono, título, contenido
        assert vision_sec.get("icon"), f"vision sin icono en {lang}"
        assert vision_sec.get("title"), f"vision sin título en {lang}"
        assert vision_sec.get("content_md"), f"vision sin contenido en {lang}"
        # Contenido razonablemente largo (~500+ chars de explicación)
        assert len(vision_sec["content_md"]) > 400, (
            f"vision content too short in {lang}: {len(vision_sec['content_md'])} chars"
        )

    @pytest.mark.parametrize("lang", ["en", "es", "fr", "de"])
    def test_manual_vision_section_mentions_cost(self, lang):
        """La sección manual debe transparentar el coste API."""
        from reflex_companion import manual_content
        manual = manual_content.get_manual(lang)
        sections = manual.get("sections", [])
        vision_sec = next((s for s in sections if s.get("id") == "vision"), {})
        content = vision_sec.get("content_md", "").lower()
        # Mención al coste — $, 0.05, API o sinónimos
        has_cost_mention = (
            "$0.05" in content or "0.05" in content or "$" in content
            or "api" in content
        )
        assert has_cost_mention, (
            f"v0.19.48 ({lang}): manual debe mencionar coste extra"
        )
