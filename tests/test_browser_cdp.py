"""Tests para reflex_companion/browser_cdp.py — control directo del
navegador vía Chrome DevTools Protocol HTTP REST.

Cobertura:
  • is_cdp_available — verifica que sea Chromium real (H5)
  • get_browser_info — dict válido o None
  • list_tabs — filtra a type='page'
  • close_tab / new_tab / activate_tab — happy + fail paths
  • find_tabs_matching / close_tabs_matching — substring match
"""
from unittest.mock import patch, MagicMock
import json

import pytest

from reflex_companion import browser_cdp as bc
from reflex_companion.browser_cdp import (
    DEFAULT_CDP_PORT,
    is_cdp_available,
    get_browser_info,
    list_tabs,
    close_tab,
    new_tab,
    activate_tab,
    find_tabs_matching,
    close_tabs_matching,
)


def _mock_get_json(return_value):
    """Helper: mockea _get_json para devolver un valor fijo."""
    return patch("reflex_companion.browser_cdp._get_json",
                 return_value=return_value)


# ════════════════════════════════════════════════════════════════════════
#  Constants
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_default_port_is_9222(self):
        assert DEFAULT_CDP_PORT == 9222

    def test_chromium_browser_markers_includes_main_browsers(self):
        """v0.19.34 (H5) — marcadores de Browser que reconocemos como
        Chromium reales."""
        markers = bc._CHROMIUM_BROWSER_MARKERS
        for expected in ("Chrome", "Chromium", "Edge", "Brave", "Opera", "Vivaldi"):
            assert expected in markers, f"Falta marker {expected!r}"


# ════════════════════════════════════════════════════════════════════════
#  is_cdp_available — H5 fix
# ════════════════════════════════════════════════════════════════════════


class TestIsCDPAvailable:
    def test_returns_false_when_no_response(self):
        with _mock_get_json(None):
            assert is_cdp_available() is False

    def test_returns_true_when_chrome_responds(self):
        with _mock_get_json({
            "Browser": "Chrome/120.0.0.0",
            "Protocol-Version": "1.3",
        }):
            assert is_cdp_available() is True

    def test_returns_true_when_edge_responds(self):
        with _mock_get_json({"Browser": "Edge/120.0.0.0"}):
            assert is_cdp_available() is True

    def test_returns_true_when_brave_responds(self):
        with _mock_get_json({"Browser": "Brave/1.60.0"}):
            assert is_cdp_available() is True

    def test_returns_true_when_opera_responds(self):
        with _mock_get_json({"Browser": "Opera/106.0.0"}):
            assert is_cdp_available() is True

    def test_returns_true_when_vivaldi_responds(self):
        with _mock_get_json({"Browser": "Vivaldi/6.5.3206"}):
            assert is_cdp_available() is True

    def test_returns_true_when_chromium_responds(self):
        with _mock_get_json({"Browser": "Chromium/120.0"}):
            assert is_cdp_available() is True

    def test_returns_FALSE_when_random_app_squats_port(self):
        """v0.19.34 (H5) — REGRESIÓN: si otra app está usando :9222
        (Docker, otro IDE), is_cdp_available debe devolver False, NO True."""
        with _mock_get_json({
            "Browser": "RandomService/1.0",
            "Version": "...",
        }):
            assert is_cdp_available() is False, (
                "App random respondiendo en :9222 NO debe contar como CDP "
                "available. Bug H5: antes devolvíamos True optimistamente."
            )

    def test_returns_FALSE_when_browser_field_missing(self):
        """JSON válido pero sin Browser field → no es Chromium real."""
        with _mock_get_json({"Version": "1.0", "Other": "data"}):
            assert is_cdp_available() is False

    def test_returns_FALSE_when_browser_field_empty(self):
        with _mock_get_json({"Browser": ""}):
            assert is_cdp_available() is False

    def test_returns_FALSE_when_browser_field_none(self):
        with _mock_get_json({"Browser": None}):
            assert is_cdp_available() is False

    def test_uses_correct_endpoint_url(self):
        """Verifica que se llama /json/version, no otro endpoint."""
        with patch("reflex_companion.browser_cdp._get_json") as mock:
            mock.return_value = None
            is_cdp_available(port=12345)
            called_url = mock.call_args[0][0]
            assert "12345" in called_url
            assert "/json/version" in called_url


# ════════════════════════════════════════════════════════════════════════
#  get_browser_info
# ════════════════════════════════════════════════════════════════════════


class TestGetBrowserInfo:
    def test_returns_dict_when_available(self):
        info = {"Browser": "Chrome/120", "User-Agent": "Mozilla/..."}
        with _mock_get_json(info):
            assert get_browser_info() == info

    def test_returns_none_when_unavailable(self):
        with _mock_get_json(None):
            assert get_browser_info() is None


# ════════════════════════════════════════════════════════════════════════
#  list_tabs
# ════════════════════════════════════════════════════════════════════════


class TestListTabs:
    def test_returns_empty_when_unavailable(self):
        with _mock_get_json(None):
            assert list_tabs() == []

    def test_filters_to_type_page(self):
        with _mock_get_json([
            {"id": "1", "title": "Page", "type": "page", "url": "..."},
            {"id": "2", "title": "Worker", "type": "service_worker", "url": "..."},
            {"id": "3", "title": "Bg", "type": "background_page", "url": "..."},
            {"id": "4", "title": "Page2", "type": "page", "url": "..."},
        ]):
            tabs = list_tabs()
        assert len(tabs) == 2
        assert all(t["type"] == "page" for t in tabs)
        assert {t["id"] for t in tabs} == {"1", "4"}

    def test_returns_empty_for_non_list_response(self):
        """Si _get_json devuelve algo no-list (ej. dict de error), no crashea."""
        with _mock_get_json({"error": "boom"}):
            assert list_tabs() == []

    def test_falls_back_to_json_endpoint_if_list_empty(self):
        """Algunos Chromium responden a /json en lugar de /json/list."""
        responses = iter([
            None,  # /json/list devuelve None
            [{"id": "1", "title": "T", "type": "page", "url": "u"}],  # /json works
        ])
        with patch("reflex_companion.browser_cdp._get_json",
                   side_effect=lambda *a, **kw: next(responses)):
            tabs = list_tabs()
        assert len(tabs) == 1


# ════════════════════════════════════════════════════════════════════════
#  close_tab / new_tab / activate_tab
# ════════════════════════════════════════════════════════════════════════


class TestCloseTab:
    def test_returns_true_on_200(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   return_value=mock_resp):
            assert close_tab("tab123") is True

    def test_returns_false_on_exception(self):
        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   side_effect=Exception("boom")):
            assert close_tab("tab123") is False


class TestNewTab:
    """v0.19.46 — `new_tab` migró de _get_json (GET) a urlopen con
    method='PUT' porque Chromium 130+ rechaza GET con HTTP 405. Los
    tests ahora interceptan urlopen directamente y verifican el method."""

    def _make_mock_resp(self, body=None):
        mock_resp = MagicMock()
        if body is None:
            body = b'{"id":"new1","title":"","url":"about:blank"}'
        mock_resp.read = MagicMock(return_value=body)
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_uses_put_method(self):
        """v0.19.46 — DEBE usar PUT (no GET). Chromium 130+ devuelve 405
        en GET. Bug confirmado experimentalmente con curl PUT vs GET."""
        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   return_value=self._make_mock_resp()) as mock_open:
            new_tab("https://example.com")
            req = mock_open.call_args[0][0]
            assert req.get_method() == "PUT", (
                f"new_tab debe usar PUT, está usando {req.get_method()}. "
                "Chromium 130+ rechaza GET con HTTP 405."
            )

    def test_url_is_url_encoded(self):
        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   return_value=self._make_mock_resp()) as mock_open:
            new_tab("https://youtube.com/watch?v=abc&t=10")
            req = mock_open.call_args[0][0]
            called_url = req.full_url
            # & debe estar encoded para no romper la query string
            assert "%26" in called_url or "v%3D" in called_url

    def test_empty_url_uses_blank_endpoint(self):
        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   return_value=self._make_mock_resp(
                       body=b'{"id":"x","url":"about:blank"}'
                   )) as mock_open:
            new_tab("")
            req = mock_open.call_args[0][0]
            called_url = req.full_url
            # Sin query string
            assert "?" not in called_url

    def test_returns_none_on_exception(self):
        import urllib.error
        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("network down")):
            assert new_tab("https://example.com") is None


# ════════════════════════════════════════════════════════════════════════
#  find_tabs_matching / close_tabs_matching
# ════════════════════════════════════════════════════════════════════════


class TestFindTabsMatching:
    def test_substring_case_insensitive(self):
        with _mock_get_json([
            {"id": "1", "title": "YouTube - Home", "type": "page"},
            {"id": "2", "title": "Twitter Feed", "type": "page"},
            {"id": "3", "title": "Manchild - YouTube", "type": "page"},
        ]):
            matches = find_tabs_matching("youtube")
        assert {t["id"] for t in matches} == {"1", "3"}

    def test_no_match_returns_empty(self):
        with _mock_get_json([
            {"id": "1", "title": "Twitter", "type": "page"},
        ]):
            assert find_tabs_matching("youtube") == []

    def test_handles_missing_title(self):
        """Algunos targets no tienen title — no debe crashear."""
        with _mock_get_json([
            {"id": "1", "type": "page"},  # sin title
            {"id": "2", "title": "YouTube", "type": "page"},
        ]):
            matches = find_tabs_matching("youtube")
        assert len(matches) == 1


class TestCloseTabsMatching:
    def test_closes_all_matching(self):
        with _mock_get_json([
            {"id": "1", "title": "YT 1", "type": "page"},
            {"id": "2", "title": "YT 2", "type": "page"},
            {"id": "3", "title": "Other", "type": "page"},
        ]), patch("reflex_companion.browser_cdp.close_tab") as mock_close:
            mock_close.return_value = True
            count, titles = close_tabs_matching("YT")
        assert count == 2
        assert mock_close.call_count == 2

    def test_exclude_filter(self):
        with _mock_get_json([
            {"id": "1", "title": "YouTube - Manchild", "type": "page"},
            {"id": "2", "title": "YouTube - Espresso", "type": "page"},
        ]), patch("reflex_companion.browser_cdp.close_tab") as mock_close:
            mock_close.return_value = True
            count, titles = close_tabs_matching("youtube", exclude="manchild")
        # Solo Espresso, Manchild excluído
        assert count == 1
        assert "Espresso" in titles[0]

    def test_close_failures_not_counted(self):
        with _mock_get_json([
            {"id": "1", "title": "YT", "type": "page"},
            {"id": "2", "title": "YT 2", "type": "page"},
        ]), patch("reflex_companion.browser_cdp.close_tab") as mock_close:
            # Primer close OK, segundo falla
            mock_close.side_effect = [True, False]
            count, titles = close_tabs_matching("YT")
        assert count == 1


# ════════════════════════════════════════════════════════════════════════
#  Logging coverage
# ════════════════════════════════════════════════════════════════════════


class TestLoggingPresent:
    def test_module_has_logger(self):
        assert hasattr(bc, "_log")
        assert bc._log.name == "ashley.browser_cdp"

    def test_non_chromium_response_logs_warning(self, caplog):
        """v0.19.34 (H5) — cuando is_cdp_available detecta que el responder
        no es Chromium, debe loguear (para debug)."""
        with _mock_get_json({"Browser": "WeirdService/1.0"}):
            with caplog.at_level("WARNING", logger="ashley.browser_cdp"):
                is_cdp_available()
            messages = [r.message for r in caplog.records]
            assert any("Chromium" in m or "WeirdService" in m for m in messages), (
                f"Esperaba log warning sobre non-Chromium response. Got: {messages}"
            )
