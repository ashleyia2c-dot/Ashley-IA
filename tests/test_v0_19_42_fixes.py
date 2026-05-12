"""Regression tests para v0.19.42 — añadir CDP path con dedupe a
open_url y search_web, usando el mismo patrón defensivo de play_music
v0.19.41.

User pidió: 'haz la mejora y espero funcione correctamente'.

Contexto: open_url y search_web usaban solo webbrowser.open (lento, foco
visible, sin dedupe). El user había confirmado que NO tenían bug, pero
para mejorar UX:
  • CDP cuando esté disponible (rápido, sin foco visible)
  • Dedupe en open_url: si la URL ya está abierta, activa esa tab
  • Misma lógica defensiva v0.19.41 (poll URL-based, no fallback double-open)

search_web NO tiene dedupe (cada búsqueda Google puede querer resultados
frescos).
"""
import sys
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def fast_sleep():
    with patch("reflex_companion.actions.time.sleep"):
        yield


@pytest.fixture
def mock_cdp_module():
    import reflex_companion
    mock = MagicMock()
    mock.is_cdp_available.return_value = True
    mock.find_tabs_matching.return_value = []
    mock.list_tabs.return_value = []
    mock.close_tab.return_value = True
    mock.activate_tab.return_value = True
    mock.new_tab.return_value = None

    saved_sys = sys.modules.get("reflex_companion.browser_cdp")
    saved_attr = getattr(reflex_companion, "browser_cdp", None)

    sys.modules["reflex_companion.browser_cdp"] = mock
    reflex_companion.browser_cdp = mock

    try:
        yield mock
    finally:
        if saved_sys is not None:
            sys.modules["reflex_companion.browser_cdp"] = saved_sys
        else:
            sys.modules.pop("reflex_companion.browser_cdp", None)
        if saved_attr is not None:
            reflex_companion.browser_cdp = saved_attr
        elif hasattr(reflex_companion, "browser_cdp"):
            delattr(reflex_companion, "browser_cdp")


# ════════════════════════════════════════════════════════════════════════
#  _normalize_url_for_match
# ════════════════════════════════════════════════════════════════════════


class TestNormalizeUrl:
    def test_strips_trailing_slash(self):
        from reflex_companion.actions import _normalize_url_for_match
        assert _normalize_url_for_match("https://github.com/") == "https://github.com"

    def test_strips_fragment(self):
        from reflex_companion.actions import _normalize_url_for_match
        assert _normalize_url_for_match(
            "https://github.com#readme"
        ) == "https://github.com"

    def test_strips_both(self):
        from reflex_companion.actions import _normalize_url_for_match
        assert _normalize_url_for_match(
            "https://github.com/path/#section"
        ) == "https://github.com/path"

    def test_preserves_query_string(self):
        """Query string IS case-sensitive y debe preservarse."""
        from reflex_companion.actions import _normalize_url_for_match
        url = "https://example.com?ID=ABC123"
        assert _normalize_url_for_match(url) == url

    def test_empty_returns_empty(self):
        from reflex_companion.actions import _normalize_url_for_match
        assert _normalize_url_for_match("") == ""
        assert _normalize_url_for_match(None) == ""


# ════════════════════════════════════════════════════════════════════════
#  open_url + dedupe
# ════════════════════════════════════════════════════════════════════════


class TestOpenUrlDedupe:
    """v0.19.42 — open_url con CDP debe dedupear y activar tab existente."""

    def test_dedupe_finds_existing_tab_and_activates(
            self, fast_sleep, mock_cdp_module):
        from reflex_companion import actions

        target = "https://github.com/anthropics"
        mock_cdp_module.list_tabs.return_value = [
            {"id": "t1", "title": "Anthropic · GitHub", "url": target},
        ]

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            msg = actions.open_url(target, prefer_cdp=True, lang="en")

        # NO debe haber llamado a new_tab (dedupe disparó)
        assert not mock_cdp_module.new_tab.called
        # NO debe haber llamado a webbrowser.open
        assert not mock_wbo.called
        # SÍ debe activar la tab existente
        mock_cdp_module.activate_tab.assert_called_once_with("t1")
        # Mensaje de "ya abierta" en lugar de "abierta"
        assert "existing" in msg.lower() or "switched" in msg.lower()

    def test_dedupe_handles_trailing_slash_difference(
            self, fast_sleep, mock_cdp_module):
        """github.com/ y github.com deben matchear como mismo URL."""
        from reflex_companion import actions

        # Tab existente sin slash, request con slash
        mock_cdp_module.list_tabs.return_value = [
            {"id": "t1", "title": "GH", "url": "https://github.com"},
        ]

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.open_url("https://github.com/", prefer_cdp=True, lang="en")

        assert not mock_cdp_module.new_tab.called
        assert not mock_wbo.called
        assert mock_cdp_module.activate_tab.called

    def test_no_dedupe_when_url_different(self, fast_sleep, mock_cdp_module):
        """URL distintas → abre nueva tab, no dedupea."""
        from reflex_companion import actions

        mock_cdp_module.list_tabs.return_value = [
            {"id": "t1", "title": "GH",
             "url": "https://github.com/anthropics"},
        ]
        mock_cdp_module.new_tab.return_value = {
            "id": "t2", "url": "https://github.com/openai",
        }

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.open_url("https://github.com/openai",
                             prefer_cdp=True, lang="en")

        # Distinto path → debe abrir nueva
        assert mock_cdp_module.new_tab.called
        assert not mock_cdp_module.activate_tab.called
        assert not mock_wbo.called  # CDP triunfó, no fallback


# ════════════════════════════════════════════════════════════════════════
#  open_url + CDP path defensivo (poll, no fallback double-open)
# ════════════════════════════════════════════════════════════════════════


class TestOpenUrlCDPDefensive:
    """v0.19.42 — open_url usa el mismo patrón defensivo que play_music
    v0.19.41: poll después de new_tab=None, NO fallback a webbrowser
    para evitar duplicados en PCs lentos."""

    def test_polls_when_new_tab_returns_none(
            self, fast_sleep, mock_cdp_module):
        from reflex_companion import actions

        target = "https://example.com"
        polls = {"calls": 0}

        def fake_list_tabs(*_args, **_kwargs):
            polls["calls"] += 1
            # Call 1: dedupe init → []
            # Call 2+: poll attempts → la tab apareció (slow CDP response)
            if polls["calls"] == 1:
                return []
            return [{"id": "t1", "title": "Example", "url": target}]

        mock_cdp_module.list_tabs.side_effect = fake_list_tabs
        mock_cdp_module.new_tab.return_value = None  # CDP timeout

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.open_url(target, prefer_cdp=True, lang="en")

        # NO fallback a webbrowser.open (evita duplicar)
        assert not mock_wbo.called, (
            "v0.19.42: cuando new_tab=None pero la tab apareció en poll, "
            "NO debe haber fallback a webbrowser.open (evita 2 tabs)."
        )

    def test_no_fallback_when_poll_exhausts(
            self, fast_sleep, mock_cdp_module):
        """Poll de 10s sin tab → asumir éxito optimista, no fallback."""
        from reflex_companion import actions

        mock_cdp_module.list_tabs.return_value = []
        mock_cdp_module.new_tab.return_value = None

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.open_url("https://example.com",
                             prefer_cdp=True, lang="en")

        # Aunque el poll falle, NO fallback (consistent con play_music)
        assert not mock_wbo.called

    def test_falls_back_only_on_exception(
            self, fast_sleep, mock_cdp_module):
        """Si CDP path THROWS, sí fallback a webbrowser."""
        from reflex_companion import actions

        mock_cdp_module.new_tab.side_effect = RuntimeError("CDP crashed")

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.open_url("https://example.com",
                             prefer_cdp=True, lang="en")

        assert mock_wbo.called, (
            "Si CDP REALMENTE crashea (excepción), sí fallback"
        )


# ════════════════════════════════════════════════════════════════════════
#  search_web — usa CDP pero SIN dedupe
# ════════════════════════════════════════════════════════════════════════


class TestSearchWebCDP:
    """v0.19.42 — search_web usa CDP pero NO dedupe (cada búsqueda Google
    puede querer resultados frescos)."""

    def test_uses_cdp_when_available(self, fast_sleep, mock_cdp_module):
        from reflex_companion import actions

        mock_cdp_module.new_tab.return_value = {
            "id": "t1", "url": "https://www.google.com/search?q=python",
        }

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.search_web("python", prefer_cdp=True, lang="en")

        assert mock_cdp_module.new_tab.called
        assert not mock_wbo.called  # CDP triunfó

    def test_no_dedupe_for_search_web(self, fast_sleep, mock_cdp_module):
        """Si buscas 'python tutorials' y ya hay tab con esa búsqueda,
        debe abrir OTRA tab (no dedupear). Cada búsqueda puede querer
        resultados frescos."""
        from reflex_companion import actions

        existing_url = "https://www.google.com/search?q=python%20tutorials"
        mock_cdp_module.list_tabs.return_value = [
            {"id": "t1", "title": "python tutorials - Google", "url": existing_url},
        ]
        mock_cdp_module.new_tab.return_value = {
            "id": "t2", "url": existing_url,
        }

        actions.search_web("python tutorials", prefer_cdp=True, lang="en")

        # NO debe activar tab existente (no dedupe)
        assert not mock_cdp_module.activate_tab.called
        # SÍ debe abrir nueva
        assert mock_cdp_module.new_tab.called

    def test_falls_back_when_no_cdp(self, fast_sleep, mock_cdp_module):
        from reflex_companion import actions

        mock_cdp_module.is_cdp_available.return_value = False

        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.search_web("test", prefer_cdp=True, lang="en")

        assert mock_wbo.called


# ════════════════════════════════════════════════════════════════════════
#  Regresión guard — i18n keys en 7 idiomas
# ════════════════════════════════════════════════════════════════════════


class TestI18nKeys:
    """v0.19.42 — la nueva key url_already_open debe existir en los 7
    idiomas del _ACTION_MSGS dict."""

    def test_url_already_open_present_in_all_7_langs(self):
        from reflex_companion.actions import _ACTION_MSGS
        assert "url_already_open" in _ACTION_MSGS
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            assert lang in _ACTION_MSGS["url_already_open"], (
                f"Falta '{lang}' en url_already_open"
            )
            value = _ACTION_MSGS["url_already_open"][lang]
            assert "{url}" in value, (
                f"'{lang}'.url_already_open debe contener {{url}} placeholder"
            )

    def test_translations_actually_translated(self):
        """No debe ser todo igual al EN (verificar que se tradujeron)."""
        from reflex_companion.actions import _ACTION_MSGS
        en_val = _ACTION_MSGS["url_already_open"]["en"]
        for lang in ["es", "fr", "ja", "de", "ru", "ko"]:
            local_val = _ACTION_MSGS["url_already_open"][lang]
            assert local_val != en_val, (
                f"{lang} no se tradujo (igual a EN)"
            )


# ════════════════════════════════════════════════════════════════════════
#  Sanity — no regresión cuando prefer_cdp=False (path original)
# ════════════════════════════════════════════════════════════════════════


class TestNoRegressionWithoutCDP:
    """Cuando el user no tiene CDP activo (prefer_cdp=False), behaviour
    debe ser igual que antes: webbrowser.open directo, sin dedupe."""

    def test_open_url_without_cdp_uses_webbrowser(self, fast_sleep):
        from reflex_companion import actions
        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.open_url("https://example.com",
                             prefer_cdp=False, lang="en")
        assert mock_wbo.called

    def test_search_web_without_cdp_uses_webbrowser(self, fast_sleep):
        from reflex_companion import actions
        with patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
            actions.search_web("test", prefer_cdp=False, lang="en")
        assert mock_wbo.called
