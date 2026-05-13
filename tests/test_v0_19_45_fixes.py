"""Regression tests para v0.19.45 — sinónimos multilingües en
click_by_text.

User reportó: 'parece que ashley no esta usando la version advanced de
Modern browser mode' (luego se confirmó que CDP sí estaba activo). El
problema real: Ashley emitía [action:click:like] pero su YouTube estaba
en español ("Indica que te gusta este vídeo" / "Me gusta") — la palabra
"like" no aparecía en aria-labels → click_by_text fallaba con "No
clickable element matched: like".

Fix v0.19.45: diccionario _BUTTON_SYNONYMS con variantes multilingües
para los botones más comunes (like/dislike/subscribe/share/save/play/
pause). click_by_text expande automáticamente cuando reconoce uno de
los términos canonical.
"""
import re
import sys
from unittest.mock import patch, MagicMock

import pytest


# ════════════════════════════════════════════════════════════════════════
#  _BUTTON_SYNONYMS dict
# ════════════════════════════════════════════════════════════════════════


class TestButtonSynonymsDict:
    """v0.19.45 — diccionario de sinónimos multilingües."""

    def test_dict_exists(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        assert isinstance(_BUTTON_SYNONYMS, dict)
        assert len(_BUTTON_SYNONYMS) >= 6

    def test_like_has_spanish(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        like_variants = [v.lower() for v in _BUTTON_SYNONYMS["like"]]
        assert "me gusta" in like_variants, (
            "Falta 'Me gusta' en sinónimos de like — caso del bug del user "
            "(YouTube en español usa 'Me gusta' / 'Indica que te gusta')"
        )
        assert any("indica que te gusta" in v for v in like_variants), (
            "Falta el aria-label completo de YouTube ES"
        )

    def test_like_has_french_japanese_german_russian_korean(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        variants = [v.lower() for v in _BUTTON_SYNONYMS["like"]]
        assert any("j'aime" in v or "j’aime" in v for v in variants), (
            "Falta variante FR (j'aime)"
        )
        assert "いいね" in _BUTTON_SYNONYMS["like"], "Falta JA (いいね)"
        assert "gefällt mir" in [v.lower() for v in _BUTTON_SYNONYMS["like"]], (
            "Falta DE (gefällt mir)"
        )
        assert "нравится" in [v.lower() for v in _BUTTON_SYNONYMS["like"]], (
            "Falta RU (нравится)"
        )
        assert "좋아요" in _BUTTON_SYNONYMS["like"], "Falta KO (좋아요)"

    def test_essential_buttons_present(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        for canonical in ["like", "dislike", "subscribe", "share", "save",
                          "play", "pause"]:
            assert canonical in _BUTTON_SYNONYMS, (
                f"Falta '{canonical}' en _BUTTON_SYNONYMS"
            )


# ════════════════════════════════════════════════════════════════════════
#  _expand_synonyms helper
# ════════════════════════════════════════════════════════════════════════


class TestExpandSynonyms:
    def test_known_canonical_returns_all_variants(self):
        from reflex_companion.browser_cdp import _expand_synonyms
        result = _expand_synonyms("like")
        assert "like" in result
        assert "me gusta" in result
        assert any("j'aime" in v or "j’aime" in v for v in result)
        assert len(result) >= 7

    def test_case_insensitive(self):
        from reflex_companion.browser_cdp import _expand_synonyms
        a = _expand_synonyms("like")
        b = _expand_synonyms("LIKE")
        c = _expand_synonyms("Like")
        assert a == b == c

    def test_variant_input_also_expands(self):
        """Si el user pasa 'me gusta' directamente, también debe expandir
        a TODAS las variantes (no solo devolver 'me gusta')."""
        from reflex_companion.browser_cdp import _expand_synonyms
        result = _expand_synonyms("me gusta")
        assert len(result) >= 7
        assert "like" in result

    def test_unknown_returns_input_unchanged(self):
        """Si no es un canonical conocido, devuelve [text] sin expandir."""
        from reflex_companion.browser_cdp import _expand_synonyms
        result = _expand_synonyms("Some random button label")
        assert result == ["Some random button label"]

    def test_empty_returns_list_with_empty(self):
        from reflex_companion.browser_cdp import _expand_synonyms
        # No crashea con string vacío
        result = _expand_synonyms("")
        assert isinstance(result, list)


# ════════════════════════════════════════════════════════════════════════
#  click_by_text con sinónimos
# ════════════════════════════════════════════════════════════════════════


class TestClickByTextWithSynonyms:
    """v0.19.45 — click_by_text genera JS con TODOS los sinónimos del
    término. Verifica que el JS contiene cada variante."""

    def test_click_by_text_generates_multilingual_js(self):
        """Cuando text='like', el JS generado debe incluir las variantes
        en español/francés/etc."""
        from reflex_companion import browser_cdp

        captured_js = {"value": None}

        def fake_evaluate_js(target, js, port=9222):
            captured_js["value"] = js
            # v0.19.46 — para toggle canonicals (like), success requiere
            # verified=True (aria-pressed cambió o vino vía site-selector).
            return {"result": {"value": {"found": True, "label": "Me gusta",
                                          "method": "aria", "matched": "me gusta",
                                          "verified": True,
                                          "before": "false", "after": "true"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_evaluate_js):
            ok, msg = browser_cdp.click_by_text({"id": "x", "webSocketDebuggerUrl": "ws://x"}, "like")

        assert ok is True
        # El JS debe contener variantes en español
        assert "me gusta" in captured_js["value"].lower(), (
            "v0.19.45: JS generado debe incluir 'me gusta' (sinónimo ES de 'like')"
        )

    def test_click_by_text_unknown_term_uses_only_input(self):
        """Si el text no es un canonical conocido, el JS solo usa ese texto."""
        from reflex_companion import browser_cdp

        captured_js = {"value": None}

        def fake_evaluate_js(target, js, port=9222):
            captured_js["value"] = js
            return {"result": {"value": {"found": True, "label": "x", "method": "text"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_evaluate_js):
            browser_cdp.click_by_text({"id": "x"}, "myCustomButton")

        # NO debe contener "me gusta" ni otros sinónimos random
        js = captured_js["value"].lower()
        assert "me gusta" not in js
        # Debe contener nuestro texto custom
        assert "mycustombutton" in js


# ════════════════════════════════════════════════════════════════════════
#  No regresión — comportamiento previo intacto
# ════════════════════════════════════════════════════════════════════════


class TestNoRegression:
    def test_click_by_text_still_returns_tuple(self):
        from reflex_companion import browser_cdp
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {"found": False, "error": "x"}}}):
            result = browser_cdp.click_by_text({"id": "x"}, "test")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_click_by_text_handles_no_response(self):
        from reflex_companion import browser_cdp
        with patch("reflex_companion.browser_cdp.evaluate_js", return_value=None):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "like")
        assert ok is False

    def test_click_by_selector_unchanged(self):
        """click_by_selector NO debe haberse alterado."""
        from reflex_companion import browser_cdp
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {"found": True, "label": "x"}}}):
            ok, msg = browser_cdp.click_by_selector({"id": "x"}, "#my-button")
        assert ok is True
