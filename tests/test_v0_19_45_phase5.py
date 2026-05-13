"""Regression tests para v0.19.45 FASE 5 — fixes post-prueba del user.

Bugs reportados al probar v0.19.45 FASE 1-4 en electron.bat:
  1. "ella borro el otro video de warcraft": close-old-yt cerraba TODAS
     las tabs youtube.com, incluido el video que el user estaba viendo.
  2. play_music + search_web emitidos juntos para la misma canción
     (speculative=2 confirmado en logs) → 2 tabs.

Fixes:
  1. Track `_last_ashley_music_tab_id` global. Solo cerramos esa tab,
     no todas las youtube.com. Captura id tanto en happy path
     (new_tab returns dict) como en poll path (encuentra tab por URL).
  2. Prompt rule explícita en ES/EN/FR: "NUNCA emitir play_music +
     search_web para la misma canción".
"""
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _vid_url(vid: str) -> str:
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
    mock.list_tabs.return_value = []
    mock.find_tabs_matching.return_value = []
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


@pytest.fixture
def stub_legacy_deps():
    with patch("reflex_companion.actions._capture_browser_hwnd",
               return_value=None), \
         patch("reflex_companion.actions._get_browser_tabs_via_uia",
               return_value=[]), \
         patch("reflex_companion.actions._get_all_browser_hwnds",
               return_value=[]), \
         patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
        yield mock_wbo


@pytest.fixture(autouse=True)
def reset_ashley_music_tab():
    """Reset el global _last_ashley_music_tab_id antes/después de cada test."""
    from reflex_companion import actions as _act
    _act._last_ashley_music_tab_id = ""
    yield
    _act._last_ashley_music_tab_id = ""


# ════════════════════════════════════════════════════════════════════════
#  Track Ashley's music tab — no toca tabs del user
# ════════════════════════════════════════════════════════════════════════


class TestOnlyCloseAshleysOwnTab:
    """v0.19.45 — close-old-yt SOLO cierra la tab que Ashley abrió antes,
    NO todas las tabs youtube.com (que pueden incluir tabs del user)."""

    def test_does_not_close_user_tabs_when_no_previous_ashley_tab(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Si Ashley nunca abrió música antes (`_last_ashley_music_tab_id=""`),
        NO debe cerrar ninguna tab — aunque haya tabs youtube.com del user."""
        from reflex_companion import actions

        # User tiene 2 tabs youtube.com (videos suyos)
        user_tabs = [
            {"id": "user_warcraft", "title": "Warcraft stream",
             "url": "https://www.youtube.com/watch?v=warcraft111"},
            {"id": "user_tutorial", "title": "Python tutorial",
             "url": "https://www.youtube.com/watch?v=tutorial222"},
        ]
        mock_cdp_module.list_tabs.return_value = user_tabs
        new_url = _vid_url("newmusic333")
        mock_cdp_module.new_tab.return_value = {"id": "new_music", "url": new_url}

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(new_url, "New Music")):
            actions.play_music("new music", prefer_cdp=True, lang="en")

        # close_tab NO debe haberse llamado (Ashley no tenía tab previa)
        close_calls = mock_cdp_module.close_tab.call_args_list
        close_ids = [c.args[0] if c.args else c.kwargs.get("tab_id")
                     for c in close_calls]
        assert "user_warcraft" not in close_ids, (
            "v0.19.45: NO cerrar el video de Warcraft del user"
        )
        assert "user_tutorial" not in close_ids

    def test_only_closes_previously_tracked_tab(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Si Ashley abrió tab antes (id='ashley_song1'), al pedir nueva
        música cierra SOLO ashley_song1 — preserva las del user."""
        from reflex_companion import actions
        # Setup: Ashley abrió tab antes
        actions._last_ashley_music_tab_id = "ashley_song1"

        all_tabs = [
            {"id": "user_warcraft", "title": "Warcraft",
             "url": "https://www.youtube.com/watch?v=warcraft111"},
            {"id": "ashley_song1", "title": "Old song",
             "url": "https://www.youtube.com/watch?v=oldsong222"},
        ]
        mock_cdp_module.list_tabs.return_value = all_tabs
        new_url = _vid_url("newsong333")
        mock_cdp_module.new_tab.return_value = {"id": "ashley_song2", "url": new_url}

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(new_url, "New Song")):
            actions.play_music("new song", prefer_cdp=True, lang="en")

        close_calls = mock_cdp_module.close_tab.call_args_list
        close_ids = [c.args[0] if c.args else c.kwargs.get("tab_id")
                     for c in close_calls]
        # SOLO ashley_song1 debe haberse cerrado
        assert "ashley_song1" in close_ids
        assert "user_warcraft" not in close_ids

    def test_updates_last_tab_id_on_successful_open(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Cuando new_tab retorna id, debe actualizarse
        `_last_ashley_music_tab_id` para tracking futuro."""
        from reflex_companion import actions
        new_url = _vid_url("track1234567")
        mock_cdp_module.new_tab.return_value = {"id": "tracked_id", "url": new_url}

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(new_url, "Music")):
            actions.play_music("song", prefer_cdp=True, lang="en")

        assert actions._last_ashley_music_tab_id == "tracked_id"

    def test_handles_stale_tracked_id(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Si Ashley trackea id="X" pero esa tab ya no existe (user la cerró),
        no crashea — solo loguea y continúa."""
        from reflex_companion import actions
        actions._last_ashley_music_tab_id = "stale_id_user_closed"

        # list_tabs no incluye stale_id
        mock_cdp_module.list_tabs.return_value = [
            {"id": "other_tab", "title": "Other",
             "url": "https://www.youtube.com/watch?v=other"},
        ]
        new_url = _vid_url("new9999999X")
        mock_cdp_module.new_tab.return_value = {"id": "new_id", "url": new_url}

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(new_url, "Music")):
            # No debe crashear
            actions.play_music("song", prefer_cdp=True, lang="en")

        # close_tab NO debe llamarse para stale_id (verificamos primero
        # que la tab existe)
        close_calls = mock_cdp_module.close_tab.call_args_list
        close_ids = [c.args[0] if c.args else c.kwargs.get("tab_id")
                     for c in close_calls]
        assert "stale_id_user_closed" not in close_ids


# ════════════════════════════════════════════════════════════════════════
#  Prompt rule: NEVER play_music + search_web for same song
# ════════════════════════════════════════════════════════════════════════


class TestPromptNoRedundantSearchWeb:
    """v0.19.45 — prompts deben tener regla explícita contra emitir
    play_music + search_web para la misma canción (causa 2 tabs)."""

    def test_es_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_es.py").read_text(
            encoding="utf-8",
        )
        # Buscar el bloque de regla
        assert "play_music + search_web" in src or (
            "NUNCA emitas play_music" in src and "search_web" in src
        ), (
            "prompts_es.py debe tener regla anti-redundante "
            "play_music + search_web"
        )

    def test_en_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_en.py").read_text(
            encoding="utf-8",
        )
        assert "play_music + search_web" in src or (
            "NEVER emit play_music" in src and "search_web" in src
        )

    def test_fr_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_fr.py").read_text(
            encoding="utf-8",
        )
        assert "play_music + search_web" in src or (
            "JAMAIS" in src and "search_web" in src
        )

    def test_ja_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_ja.py").read_text(
            encoding="utf-8",
        )
        assert "play_music + search_web" in src

    def test_de_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_de.py").read_text(
            encoding="utf-8",
        )
        assert "play_music + search_web" in src

    def test_ru_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_ru.py").read_text(
            encoding="utf-8",
        )
        assert "play_music + search_web" in src

    def test_ko_has_no_redundant_rule(self):
        src = (REPO_ROOT / "reflex_companion" / "prompts_ko.py").read_text(
            encoding="utf-8",
        )
        assert "play_music + search_web" in src

    def test_rule_includes_concrete_example(self):
        """La regla debe tener un ejemplo concreto para que el LLM
        lo interiorice mejor (anti-pattern + correct pattern)."""
        src = (REPO_ROOT / "reflex_companion" / "prompts_es.py").read_text(
            encoding="utf-8",
        )
        idx = src.find("play_music + search_web")
        if idx == -1:
            pytest.skip("Rule not found by exact string")
        block = src[idx:idx + 600]
        # Debe incluir tanto el WRONG como el RIGHT pattern
        assert "❌" in block or "MAL" in block.upper() or "WRONG" in block.upper()
        assert "✓" in block or "BIEN" in block.upper() or "RIGHT" in block.upper()
