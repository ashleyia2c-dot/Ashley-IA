"""Regression tests para v0.19.41 — fix del bug donde play_music abría
2 tabs del mismo video porque el dedupe usaba TITLE matching en vez de URL.

User reportó (segunda vez): 'puso dos veces la cancion de daft Punk de
nuevo, tu fix de antes no se que mierda hizo pero no parece haber
funcionado y por cierto se demora lo suyo en poner la cancion'.

Causa raíz REAL identificada (después de v0.19.38, v0.19.39 fallidos):

`find_tabs_matching("youtube")` filtra por TITLE de la tab. Pero Opera
(y otros browsers Chromium) muestran el title de YouTube como solo el
nombre del video — "Daft Punk - Harder, Better..." SIN la palabra
"YouTube". Eso significa:

  1. DEDUPE FALLA al inicio: tab anterior de Daft Punk no matchea
     "youtube" en title → dedupe no la encuentra → abre OTRA tab
  2. POLLING ES LENTO: nueva tab no aparece como "youtube" en title
     hasta que page load completa (~3-5s) → el código polea
     innecesariamente todo ese tiempo

Fix v0.19.41: cambiar TODOS los lookups de YouTube tabs a URL-based
(siempre contiene "youtube.com" Y se setea inmediatamente al crear la
tab, antes de que el title se pueble).
"""
from unittest.mock import patch, MagicMock
import sys

import pytest


def _vid_url(vid: str = "abc12345678") -> str:
    return f"https://www.youtube.com/watch?v={vid}"


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


@pytest.fixture
def stub_legacy_deps():
    with patch("reflex_companion.actions._capture_browser_hwnd",
               return_value=None), \
         patch("reflex_companion.actions._get_browser_tabs_via_uia",
               return_value=["tab1", "tab2"]), \
         patch("reflex_companion.actions._get_all_browser_hwnds",
               return_value=[]), \
         patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
        yield mock_wbo


# ════════════════════════════════════════════════════════════════════════
#  EL BUG ESPECÍFICO — title sin "youtube" pero URL sí
# ════════════════════════════════════════════════════════════════════════


class TestDedupeWorksWhenTitleHasNoYouTube:
    """v0.19.41 — REGRESIÓN del bug exacto reportado:
    el dedupe debe encontrar tabs existentes aunque su title sea solo
    el nombre del video (sin la palabra 'YouTube'). El title de Opera
    suele ser 'Daft Punk - Harder, Better, Faster, Stronger' SIN
    'YouTube' — el dedupe basado en title fallaba aquí.
    """

    def test_dedupe_finds_existing_tab_when_title_only_has_song_name(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Tab anterior con title='Daft Punk - Harder' (sin 'youtube')
        DEBE detectarse como duplicado y NO abrirse otra vez."""
        from reflex_companion import actions

        target_url = _vid_url("dft1234567X")  # 11 chars

        # Tab existente con title sin "youtube" pero URL sí
        existing_tabs = [{
            "id": "tab1",
            "title": "Daft Punk - Harder, Better, Faster, Stronger",  # sin "YouTube"
            "url": target_url,
        }]
        mock_cdp_module.list_tabs.return_value = existing_tabs

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Daft Punk")):
            actions.play_music("daft punk", prefer_cdp=True, lang="en")

        # CRÍTICO: NO debe haber llamado a new_tab (dedupe debió catch)
        assert not mock_cdp_module.new_tab.called, (
            "BUG REGRESIÓN v0.19.41: tab existente con title sin 'youtube' "
            "DEBE detectarse vía URL match. Si new_tab se llama, abrimos "
            "una segunda tab del mismo video (el bug exacto reportado)."
        )

    def test_dedupe_misses_when_videoid_different(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Si la tab existente tiene OTRO videoId, NO debe deduplicarse —
        es una canción distinta."""
        from reflex_companion import actions

        existing_url = _vid_url("aaaaaaaaaaa")
        new_url = _vid_url("bbbbbbbbbbb")

        existing_tabs = [{
            "id": "tab1", "title": "Old Song",
            "url": existing_url,
        }]
        mock_cdp_module.list_tabs.return_value = existing_tabs
        mock_cdp_module.new_tab.return_value = {"id": "new1", "url": new_url}

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(new_url, "New Song")):
            actions.play_music("new song", prefer_cdp=True, lang="en")

        # Diferente videoId → NO deduplicar, sí abrir tab nueva
        assert mock_cdp_module.new_tab.called

    def test_close_old_yt_finds_tab_via_url_not_title(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """v0.19.41 — el close-old-yt loop debe encontrar tabs viejas
        de YouTube via URL (siempre contiene 'youtube.com'), no via
        title (puede no contener 'youtube')."""
        from reflex_companion import actions

        old_url = _vid_url("oldsong1234")
        new_url = _vid_url("newsong5678")

        # v0.19.45 (cambio de comportamiento): ahora SOLO cerramos la
        # tab que ASHLEY abrió antes (track via _last_ashley_music_tab_id),
        # NO todas las tabs youtube.com. Antes cerrábamos el video de
        # Warcraft del user al pedir música — bug reportado.
        #
        # Para que este test funcione con el nuevo comportamiento,
        # seteamos _last_ashley_music_tab_id="old_tab" antes (simulando
        # que Ashley había abierto esa tab antes).
        from reflex_companion import actions as _actions_mod
        _actions_mod._last_ashley_music_tab_id = "old_tab"

        existing_tabs = [{
            "id": "old_tab",
            "title": "Some old song name",  # sin "youtube"
            "url": old_url,
        }]
        mock_cdp_module.list_tabs.return_value = existing_tabs
        mock_cdp_module.new_tab.return_value = {"id": "new1", "url": new_url}

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(new_url, "New Song")):
            actions.play_music("new", prefer_cdp=True, lang="en")

        # v0.19.45 — close_tab debe haberse llamado para old_tab porque
        # estaba trackeada como Ashley's previous music tab.
        close_calls = mock_cdp_module.close_tab.call_args_list
        close_ids = [c.args[0] if c.args else c.kwargs.get("tab_id")
                     for c in close_calls]
        assert "old_tab" in close_ids, (
            "v0.19.45: close-old-yt debe cerrar la tab anterior de música "
            "que Ashley abrió (trackeada via _last_ashley_music_tab_id)."
        )


class TestPollFindsTabFastViaURL:
    """v0.19.41 — el polling debe encontrar la tab nueva INMEDIATAMENTE
    porque la URL se setea al crear la tab. Antes esperaba a que el
    title cargara con 'youtube' (varios segundos)."""

    def test_poll_finds_tab_via_url_even_with_empty_title(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Tab apareció con URL correcta pero title aún vacío (loading).
        El poll debe encontrarla INMEDIATAMENTE (Phase 1) sin esperar."""
        from reflex_companion import actions

        target_url = _vid_url("loading1234")

        polled_state = {"calls": 0}

        def fake_list_tabs(*_args, **_kwargs):
            polled_state["calls"] += 1
            # Call 1: dedupe init → []
            # Call 2: close-old-yt loop → []
            # Call 3+: poll attempts → la tab está ahí con URL pero title vacío
            if polled_state["calls"] <= 2:
                return []
            return [{
                "id": "loading_tab",
                "title": "",  # ← TITLE VACÍO (loading)
                "url": target_url,  # ← pero URL ya está
            }]

        mock_cdp_module.list_tabs.side_effect = fake_list_tabs
        mock_cdp_module.new_tab.return_value = None  # forzar polling

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Loading")):
            actions.play_music("loading", prefer_cdp=True, lang="en")

        # NO fallback a webbrowser.open
        assert not stub_legacy_deps.called, (
            "v0.19.41: poll debe encontrar tab via URL inmediatamente "
            "(no esperar a que title cargue con 'youtube'). Sin esto, "
            "polea hasta 10s innecesariamente y al final asume éxito."
        )


# ════════════════════════════════════════════════════════════════════════
#  Sanity: el código ya no usa find_tabs_matching para YT lookups
# ════════════════════════════════════════════════════════════════════════


class TestSourceUsesURLBasedLookup:
    """Verifica que el código fuente ya no use find_tabs_matching("youtube")
    en play_music — debe usar list_tabs + URL filter para evitar el bug."""

    def test_play_music_does_not_use_find_tabs_matching_youtube(self):
        from pathlib import Path
        actions_py = (
            Path(__file__).resolve().parent.parent
            / "reflex_companion" / "actions.py"
        )
        src = actions_py.read_text(encoding="utf-8")

        # Localizar la función play_music
        start = src.find("def play_music(")
        assert start != -1
        end = src.find("\ndef ", start + 1)
        assert end != -1
        play_music_body = src[start:end]

        # Filtrar líneas de comentarios (que pueden referenciar el bug
        # como histórico). Solo nos interesa código executable.
        code_lines = []
        for line in play_music_body.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            code_lines.append(line)
        code_only = "\n".join(code_lines)

        # NO debe llamar a find_tabs_matching("youtube") en código
        # (el title-based lookup que causaba el bug)
        assert 'find_tabs_matching("youtube")' not in code_only, (
            "v0.19.41: play_music NO debe usar find_tabs_matching('youtube') "
            "(filtra por title que puede no contener 'youtube' en Opera/etc.). "
            "Debe usar list_tabs() + URL filter."
        )

    def test_play_music_filters_yt_tabs_by_url(self):
        """play_music debe filtrar tabs YT por 'youtube.com' en URL."""
        from pathlib import Path
        actions_py = (
            Path(__file__).resolve().parent.parent
            / "reflex_companion" / "actions.py"
        )
        src = actions_py.read_text(encoding="utf-8")
        start = src.find("def play_music(")
        end = src.find("\ndef ", start + 1)
        body = src[start:end]

        # Debe usar list_tabs (la API URL-aware)
        assert "_cdp.list_tabs()" in body, (
            "play_music debe usar _cdp.list_tabs() (URL-aware) en vez de "
            "find_tabs_matching (title-only)"
        )
        # Y debe filtrar por youtube.com en URL
        assert '"youtube.com"' in body, (
            "play_music debe filtrar tabs por 'youtube.com' en URL"
        )
