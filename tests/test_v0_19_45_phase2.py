"""Regression tests para v0.19.45 FASE 2 — multilingual click_by_text +
site-specific selectors (YouTube/Twitter/X).

Bug del user: pidió "darle like al video de Warcraft" → Ashley emitió
[action:click:like] → click_by_text buscó "like" como substring en
aria-labels. PERO YouTube en español muestra "Indica que te gusta este
vídeo" / "Me gusta" — no contiene "like" en ningún sitio. → Fallo.

Fix v0.19.45 (FASE 2):
  1. Sinónimos multilingües: 'like' expande a ['like', 'me gusta',
     'j'aime', 'いいね', 'gefällt mir', 'нравится', '좋아요', ...]
  2. Site-specific selectors: para youtube.com/x.com, usa selectors
     CSS estables del DOM (`like-button-view-model button`, etc.) que
     no dependen del idioma.
  3. Cascada: site-selector → aria-label → innerText.
"""
from unittest.mock import patch
import pytest


# ════════════════════════════════════════════════════════════════════════
#  _BUTTON_SYNONYMS — completitud
# ════════════════════════════════════════════════════════════════════════


class TestButtonSynonyms:
    def test_like_includes_main_languages(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        v = [s.lower() for s in _BUTTON_SYNONYMS["like"]]
        assert "like" in v
        assert "me gusta" in v
        assert "indica que te gusta" in v
        assert any("j'aime" in s or "j’aime" in s for s in v)
        assert "いいね" in _BUTTON_SYNONYMS["like"]
        assert "좋아요" in _BUTTON_SYNONYMS["like"]

    def test_essential_canonicals(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        for c in ["like", "dislike", "subscribe", "share", "save",
                  "play", "pause"]:
            assert c in _BUTTON_SYNONYMS


# ════════════════════════════════════════════════════════════════════════
#  _expand_synonyms helper
# ════════════════════════════════════════════════════════════════════════


class TestExpandSynonyms:
    def test_canonical_expands(self):
        from reflex_companion.browser_cdp import _expand_synonyms
        result = _expand_synonyms("like")
        assert "me gusta" in result
        assert len(result) >= 7

    def test_variant_also_expands(self):
        """User pasa 'me gusta' directamente, expande a TODAS las variantes."""
        from reflex_companion.browser_cdp import _expand_synonyms
        result = _expand_synonyms("me gusta")
        assert len(result) >= 7

    def test_unknown_returns_input(self):
        from reflex_companion.browser_cdp import _expand_synonyms
        assert _expand_synonyms("MyCustomButton") == ["MyCustomButton"]


# ════════════════════════════════════════════════════════════════════════
#  Site-specific selectors
# ════════════════════════════════════════════════════════════════════════


class TestSiteSpecificSelectors:
    """v0.19.45 — selectores CSS estables para sitios populares."""

    def test_youtube_like_has_selectors(self):
        from reflex_companion.browser_cdp import _SITE_SPECIFIC_SELECTORS
        yt = _SITE_SPECIFIC_SELECTORS["youtube.com"]
        assert "like" in yt
        # Selector estable conocido de YouTube
        assert any("like-button-view-model" in s for s in yt["like"])

    def test_youtube_dislike_subscribe_share(self):
        from reflex_companion.browser_cdp import _SITE_SPECIFIC_SELECTORS
        yt = _SITE_SPECIFIC_SELECTORS["youtube.com"]
        for action in ["dislike", "subscribe", "share"]:
            assert action in yt
            assert len(yt[action]) > 0

    def test_twitter_x_have_selectors(self):
        from reflex_companion.browser_cdp import _SITE_SPECIFIC_SELECTORS
        for host in ["twitter.com", "x.com"]:
            assert host in _SITE_SPECIFIC_SELECTORS

    def test_get_site_selectors_returns_youtube_for_like(self):
        from reflex_companion.browser_cdp import _get_site_selectors_for
        result = _get_site_selectors_for("like")
        assert "youtube.com" in result
        assert "x.com" in result or "twitter.com" in result

    def test_get_site_selectors_works_with_synonym(self):
        """User pasa 'me gusta' (variante ES) → debe expandir y devolver
        los selectores de YouTube para like."""
        from reflex_companion.browser_cdp import _get_site_selectors_for
        result = _get_site_selectors_for("me gusta")
        assert "youtube.com" in result

    def test_get_site_selectors_returns_empty_for_unknown(self):
        from reflex_companion.browser_cdp import _get_site_selectors_for
        assert _get_site_selectors_for("MyCustomButton") == {}


# ════════════════════════════════════════════════════════════════════════
#  click_by_text — JS generado incluye site-selectors + sinónimos
# ════════════════════════════════════════════════════════════════════════


class TestClickByTextJSIntegration:
    def test_click_like_js_includes_site_selectors(self):
        """Cuando text='like', el JS generado debe incluir el dict
        siteSelectors con youtube.com como key."""
        from reflex_companion import browser_cdp
        captured = {"js": None}

        def fake_eval(target, js, port=9222):
            captured["js"] = js
            return {"result": {"value": {"found": True, "label": "Like", "method": "site-selector"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_eval):
            browser_cdp.click_by_text({"id": "x"}, "like")

        js = captured["js"]
        assert "siteSelectors" in js
        assert "youtube.com" in js
        assert "like-button-view-model" in js

    def test_click_unknown_text_no_site_selectors(self):
        """Texto random → siteSelectors es dict vacío en el JS."""
        from reflex_companion import browser_cdp
        captured = {"js": None}

        def fake_eval(target, js, port=9222):
            captured["js"] = js
            return {"result": {"value": {"found": False, "error": "x"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_eval):
            browser_cdp.click_by_text({"id": "x"}, "myCustomLabel")

        js = captured["js"]
        # Sin site-selector, dict vacío
        assert "youtube.com" not in js  # No deberíamos tener selectores YT

    def test_click_like_includes_multilingual_synonyms(self):
        """Con text='like', el targets array debe incluir 'me gusta'."""
        from reflex_companion import browser_cdp
        captured = {"js": None}

        def fake_eval(target, js, port=9222):
            captured["js"] = js
            return {"result": {"value": {"found": True, "label": "x", "method": "aria"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_eval):
            browser_cdp.click_by_text({"id": "x"}, "like")

        assert "me gusta" in captured["js"].lower()

    def test_clicked_returns_success_when_method_site_selector(self):
        from reflex_companion import browser_cdp
        # v0.19.46 — site-selector con verified=True (aria-pressed cambió
        # o el botón no expone aria-pressed pero vino vía selector estable).
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {
                       "found": True, "label": "Like button",
                       "method": "site-selector", "matched": "like-button-view-model button",
                       "verified": True,
                       "before": "false", "after": "true",
                   }}}):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "like")
        assert ok is True
        assert "site-selector" in msg


# ════════════════════════════════════════════════════════════════════════
#  No regresión — comportamiento sin sinónimos
# ════════════════════════════════════════════════════════════════════════


class TestNoRegressionExistingBehavior:
    def test_unknown_text_still_uses_aria_text_fallback(self):
        """Para textos no canonical (ej. 'Submit'), debe seguir buscando
        en aria-label e innerText. v0.19.46 — non-toggle canonicals
        siempre tienen verified=True (no requieren aria-pressed change)."""
        from reflex_companion import browser_cdp
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {
                       "found": True, "label": "Submit",
                       "method": "aria", "matched": "submit",
                       "verified": True,
                       "before": None, "after": None,
                   }}}):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "Submit")
        assert ok is True

    def test_returns_failure_when_nothing_matched(self):
        from reflex_companion import browser_cdp
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {
                       "found": False, "error": "No clickable",
                   }}}):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "foo")
        assert ok is False

    def test_handles_no_evaluate_response(self):
        from reflex_companion import browser_cdp
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value=None):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "like")
        assert ok is False
