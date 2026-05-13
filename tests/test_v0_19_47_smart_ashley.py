"""Regression tests para v0.19.47 — "Smart Ashley".

3 features añadidos en sesión 2026-05-12:

1. **Lista de apps instaladas en system_state** — Ashley ve qué apps
   tiene el user para no inventar nombres. Filtro MÍNIMO language-
   agnostic; el LLM filtra semánticamente uninstaller/about/help en
   cualquier idioma. Cacheado 5 min.

2. **Disambiguation en close_browser_tab y close_window** — si >1
   matches, devuelve la lista y NO cierra. Antes el código cerraba
   TODAS las tabs/windows que matcheaban → bug del user que pidió
   "cierra youtube" con 3 tabs y se cerraron las 3 incluyendo el
   video del Warcraft que estaba viendo.

3. **Sugerencias en open_app failure** — cuando open_app no encuentra,
   collect_app_suggestions hace fuzzy match (score_shortcut_name +
   FZF subsequence con densidad) y sugiere top 3 apps similares para
   que Ashley reintente con nombre correcto.
"""
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  Feature 1: app discovery
# ════════════════════════════════════════════════════════════════════════


class TestDiscoverInstalledApps:
    def test_returns_list_of_strings(self):
        from reflex_companion import actions
        # Reset cache para test fresh
        actions._INSTALLED_APPS_CACHE["ts"] = 0
        actions._INSTALLED_APPS_CACHE["apps"] = []
        apps = actions.discover_installed_apps(max_total=20)
        assert isinstance(apps, list)
        for a in apps:
            assert isinstance(a, str)

    def test_respects_max_total(self):
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["ts"] = 0
        actions._INSTALLED_APPS_CACHE["apps"] = []
        small = actions.discover_installed_apps(max_total=5)
        assert len(small) <= 5

    def test_uses_cache_within_ttl(self):
        """Cache hits son O(1) — la lista se reutiliza dentro del TTL."""
        from reflex_companion import actions
        # Forzar cache poblada
        actions._INSTALLED_APPS_CACHE["apps"] = ["FakeApp1", "FakeApp2"]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        apps = actions.discover_installed_apps(max_total=10)
        # Debe devolver lo cacheado, no escanear
        assert apps == ["FakeApp1", "FakeApp2"]


class TestPowerShellPrimaryFallbackToLnk:
    """v0.19.47 — Get-StartApps es el método primario (universal). Si
    falla por timeout/error, caemos al .lnk parsing."""

    def test_powershell_method_called_first(self):
        """discover_installed_apps debe intentar PowerShell antes de .lnk."""
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["ts"] = 0
        actions._INSTALLED_APPS_CACHE["apps"] = []
        with patch.object(actions, "_discover_via_powershell",
                          return_value=["PS_App1", "PS_App2"]) as mock_ps, \
             patch.object(actions, "_discover_via_lnk_walk") as mock_lnk:
            apps = actions.discover_installed_apps(max_total=10)
        assert mock_ps.called
        assert not mock_lnk.called  # PS funcionó, no necesita fallback
        assert apps == ["PS_App1", "PS_App2"]

    def test_falls_back_to_lnk_when_powershell_returns_empty(self):
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["ts"] = 0
        actions._INSTALLED_APPS_CACHE["apps"] = []
        with patch.object(actions, "_discover_via_powershell",
                          return_value=[]) as mock_ps, \
             patch.object(actions, "_discover_via_lnk_walk",
                          return_value=["LnkApp1"]) as mock_lnk:
            apps = actions.discover_installed_apps(max_total=10)
        assert mock_ps.called
        assert mock_lnk.called  # PS dio [], usamos fallback
        assert apps == ["LnkApp1"]

    def test_powershell_priorizes_known_apps(self):
        """Las apps que matchean APP_MAP deben ir primero en el resultado.
        Esto garantiza que Word/Excel/Discord/Steam siempre salen aunque
        el cap sea bajo y el user tenga 200+ apps."""
        from reflex_companion import actions
        # Mock subprocess.run para simular Get-StartApps con apps mixed
        fake_json = (
            '['
            '{"Name":"Zzzz Custom App"},'
            '{"Name":"Discord"},'
            '{"Name":"Acerca de Java"},'
            '{"Name":"Word"},'
            '{"Name":"Random Tool"}'
            ']'
        )
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = fake_json
        with patch("reflex_companion.actions.subprocess.run",
                   return_value=fake_result):
            apps = actions._discover_via_powershell()
        # Discord y Word (en APP_MAP) deben venir antes que Random Tool
        # y Zzzz Custom App (no conocidos)
        idx_discord = apps.index("Discord")
        idx_word = apps.index("Word")
        idx_zzzz = apps.index("Zzzz Custom App")
        idx_random = apps.index("Random Tool")
        assert idx_discord < idx_zzzz, (
            "Discord (APP_MAP) debe ir antes de apps desconocidas"
        )
        assert idx_word < idx_random, (
            "Word (APP_MAP) debe ir antes de apps desconocidas"
        )


class TestSystemStateIncludesApps:
    def test_get_system_state_includes_app_list_section(self):
        """get_system_state() debe incluir sección 'Apps instaladas'."""
        from reflex_companion import actions
        # Cache fake apps para asegurar la sección aparece
        actions._INSTALLED_APPS_CACHE["apps"] = ["FakeApp1", "FakeApp2"]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        state = actions.get_system_state(prefer_cdp=False)
        assert "Apps instaladas" in state
        assert "FakeApp1" in state
        assert "FakeApp2" in state

    def test_app_section_includes_filter_instruction(self):
        """La sección debe instruir a Ashley a filtrar uninstaller/about
        semánticamente, ya que NO los filtramos por regex."""
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["apps"] = ["RealApp", "Uninstall RealApp"]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        state = actions.get_system_state(prefer_cdp=False)
        # Texto que enseña a Ashley a ignorar uninstallers
        assert "uninstaller" in state.lower() or "ignora" in state.lower()


# ════════════════════════════════════════════════════════════════════════
#  Feature 1.5: filtro language-agnostic
# ════════════════════════════════════════════════════════════════════════


class TestLnkTargetFilter:
    def test_skips_doc_targets(self):
        """_is_real_app_target debe rechazar .pdf/.txt/.html/.url."""
        from reflex_companion.actions import _is_real_app_target
        assert _is_real_app_target("C:\\path\\readme.pdf") is False
        assert _is_real_app_target("C:\\help\\manual.txt") is False
        assert _is_real_app_target("C:\\app\\index.html") is False
        assert _is_real_app_target("C:\\link.url") is False

    def test_skips_system32_admin_tools(self):
        """Skip .lnk que apuntan a Windows\\System32 (admin tools).
        Excepción: cmd.exe/powershell.exe/calc.exe (legítimos)."""
        from reflex_companion.actions import _is_real_app_target
        # Admin tools
        assert _is_real_app_target("C:\\Windows\\System32\\dfrgui.exe") is False
        assert _is_real_app_target("C:\\Windows\\System32\\eventvwr.msc") is False
        # Allowed
        assert _is_real_app_target("C:\\Windows\\System32\\cmd.exe") is True
        assert _is_real_app_target("C:\\Windows\\System32\\notepad.exe") is True

    def test_allows_program_files_apps(self):
        """Apps en Program Files NO son skipeadas."""
        from reflex_companion.actions import _is_real_app_target
        assert _is_real_app_target("C:\\Program Files\\Discord\\Discord.exe") is True

    def test_returns_true_when_target_unparseable(self):
        """Si no podemos leer el target (None), asumir OK (no skipear)."""
        from reflex_companion.actions import _is_real_app_target
        assert _is_real_app_target(None) is True


# ════════════════════════════════════════════════════════════════════════
#  Feature 3: collect_app_suggestions (fuzzy + score)
# ════════════════════════════════════════════════════════════════════════


class TestAppSuggestions:
    def test_short_hint_returns_empty(self):
        """Hints <3 chars rechazadas (anti-falso-match)."""
        from reflex_companion import actions
        assert actions.collect_app_suggestions("ab") == []
        assert actions.collect_app_suggestions("") == []

    def test_exact_match_returns_first(self):
        """Si hint matchea exactly el nombre, debe ir primero."""
        from reflex_companion import actions
        # Inyectar lista controlada
        actions._INSTALLED_APPS_CACHE["apps"] = [
            "Discord", "Discord Canary", "DiscordSetup",
        ]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        sugg = actions.collect_app_suggestions("discord")
        assert sugg
        assert sugg[0] == "Discord"

    def test_fuzzy_typo_match(self):
        """Typo simple debe encontrar la app."""
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["apps"] = ["Telegram", "Steam", "Visual Studio Code"]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        # 'telegrm' → Telegram (substring match)
        sugg = actions.collect_app_suggestions("telegrm")
        assert "Telegram" in sugg

    def test_fzf_acronym_match(self):
        """'vscode' debe matchear 'Visual Studio Code' vía fuzzy."""
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["apps"] = [
            "Visual Studio Code", "Steam", "Spotify",
        ]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        sugg = actions.collect_app_suggestions("vscode")
        assert "Visual Studio Code" in sugg, (
            "FZF subsequence + word-start bonus debe matchear vscode → "
            f"Visual Studio Code. Got: {sugg}"
        )

    def test_skips_uninstallers_in_fuzzy(self):
        """Aunque la subsequence matchee, _SHORTCUT_REJECT_TOKENS los descarta."""
        from reflex_companion import actions
        actions._INSTALLED_APPS_CACHE["apps"] = [
            "Uninstall Discord", "Discord",
        ]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()
        # 'disc' → Discord (no Uninstall Discord)
        sugg = actions.collect_app_suggestions("disc")
        assert "Discord" in sugg
        assert "Uninstall Discord" not in sugg


class TestFuzzyScoreLogic:
    """v0.19.47 — _fuzzy_score con densidad + word-start bonus.
    Evita matches "Godot_v4" para 'vscode' aunque tenga v,s,c en orden."""

    def test_score_zero_for_non_subsequence(self):
        from reflex_companion.actions import _fuzzy_score
        assert _fuzzy_score("xyz", "abcd") == 0

    def test_score_high_for_acronym(self):
        from reflex_companion.actions import _fuzzy_score
        # 'vsc' iniciales perfectas de Visual Studio Code
        s = _fuzzy_score("vsc", "Visual Studio Code")
        assert s > 100

    def test_score_low_for_disperse_match(self):
        from reflex_companion.actions import _fuzzy_score
        # 'vsc' chars en posiciones lejanas, no word-starts → score bajo o 0
        s = _fuzzy_score("vsc", "abvabbabbcabb")  # densidad < 30%
        assert s == 0

    def test_score_zero_for_empty(self):
        from reflex_companion.actions import _fuzzy_score
        assert _fuzzy_score("", "anything") == 0


# ════════════════════════════════════════════════════════════════════════
#  Feature 2: disambiguation en close_browser_tab
# ════════════════════════════════════════════════════════════════════════


class TestCloseBrowserTabDisambiguation:
    def test_ambiguous_match_returns_list_without_closing(self):
        """Si find_tabs_matching devuelve >1, NO cerramos ninguna."""
        from reflex_companion import actions, browser_cdp

        fake_matches = [
            {"id": "tab1", "title": "Espresso - Sabrina", "url": "https://www.youtube.com/watch?v=eVli"},
            {"id": "tab2", "title": "Warcraft 3", "url": "https://www.youtube.com/watch?v=oT3rt"},
            {"id": "tab3", "title": "Random YouTube", "url": "https://www.youtube.com/watch?v=xxxxx"},
        ]

        with patch.object(browser_cdp, "is_cdp_available", return_value=True), \
             patch.object(browser_cdp, "find_tabs_matching",
                          return_value=fake_matches), \
             patch.object(browser_cdp, "close_tab") as mock_close:
            msg = actions.close_browser_tab("youtube",
                                              prefer_cdp=True, lang="es")

        # NO se llamó a close_tab para ninguno
        assert not mock_close.called, (
            "v0.19.47: close_browser_tab NO debe cerrar tabs cuando hay "
            "ambigüedad — debe devolver la lista para que Ashley elija"
        )
        # Mensaje debe contener los títulos
        assert "3" in msg  # cuenta
        assert "Espresso" in msg or "Warcraft" in msg

    def test_single_match_closes_it(self):
        """1 match → cerrar."""
        from reflex_companion import actions, browser_cdp
        with patch.object(browser_cdp, "is_cdp_available", return_value=True), \
             patch.object(browser_cdp, "find_tabs_matching",
                          return_value=[{"id": "x", "title": "Specific Tab", "url": "https://x.com"}]), \
             patch.object(browser_cdp, "close_tab", return_value=True) as mock_close:
            msg = actions.close_browser_tab("specific",
                                              prefer_cdp=True, lang="en")
        assert mock_close.called
        assert mock_close.call_args[0][0] == "x"

    def test_zero_matches_returns_not_found(self):
        from reflex_companion import actions, browser_cdp
        with patch.object(browser_cdp, "is_cdp_available", return_value=True), \
             patch.object(browser_cdp, "find_tabs_matching", return_value=[]), \
             patch.object(browser_cdp, "close_tab") as mock_close:
            msg = actions.close_browser_tab("nope",
                                              prefer_cdp=True, lang="en")
        assert not mock_close.called
        assert "no" in msg.lower() or "not" in msg.lower()


# ════════════════════════════════════════════════════════════════════════
#  Feature 2: disambiguation en close_window
# ════════════════════════════════════════════════════════════════════════


class TestCloseWindowDisambiguation:
    """Tests directos de la lógica de ambiguity. Mockeamos ctypes."""

    def test_ambiguous_messages_template_present(self):
        """Existe el template windows_ambiguous en _ACTION_MSGS."""
        from reflex_companion.actions import _ACTION_MSGS
        assert "windows_ambiguous" in _ACTION_MSGS
        for lang in ("en", "es", "fr", "ja", "de", "ru", "ko"):
            assert lang in _ACTION_MSGS["windows_ambiguous"], (
                f"Falta traducción de windows_ambiguous en {lang}"
            )

    def test_known_app_in_app_map_is_not_ambiguous(self):
        """Si hint es 'notepad' (en APP_MAP), close_window NO debe activar
        disambiguation aunque haya múltiples instancias — el user
        explícitamente pidió esa app por nombre canonical."""
        # Verificación del FLAG en código:
        src = (REPO_ROOT / "reflex_companion" / "actions.py").read_text(
            encoding="utf-8",
        )
        # El check is_explicit_proc usa APP_MAP — verifica que está
        assert "is_explicit_proc" in src, (
            "Debe haber check is_explicit_proc para no disambiguar "
            "cuando el hint matchea APP_MAP"
        )


# ════════════════════════════════════════════════════════════════════════
#  Feature 3: open_app failure path con suggestions
# ════════════════════════════════════════════════════════════════════════


class TestOpenAppSuggestionsOnFailure:
    def test_failure_includes_suggestions_when_available(self):
        """open_app que falla en las 7 estrategias debe consultar
        collect_app_suggestions y incluir resultados en el mensaje."""
        from reflex_companion import actions

        # Inyectar apps cacheadas
        actions._INSTALLED_APPS_CACHE["apps"] = ["Telegram", "Discord"]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()

        # Bypass los 7 paths que abren cosas — fácil: simular que todo
        # falla. Mockeamos os.startfile, subprocess, etc. para que
        # nunca encuentre nada.
        with patch("reflex_companion.actions.os.startfile",
                   side_effect=OSError("fake")), \
             patch("reflex_companion.actions.subprocess.run",
                   return_value=MagicMock(returncode=1)), \
             patch("reflex_companion.actions._search_desktop", return_value=None), \
             patch("reflex_companion.actions._search_start_menu", return_value=None), \
             patch("reflex_companion.actions.os.path.isdir", return_value=False):
            msg = actions.open_app("telegrm", lang="en")  # typo
        # Debe contener Telegram como sugerencia
        assert "Telegram" in msg, (
            f"v0.19.47: failure path debe incluir suggestions. Got: {msg!r}"
        )

    def test_failure_without_similar_apps_uses_old_message(self):
        """Si collect_app_suggestions devuelve [], usar mensaje original."""
        from reflex_companion import actions

        actions._INSTALLED_APPS_CACHE["apps"] = ["NoMatch1", "NoMatch2"]
        import time as _t
        actions._INSTALLED_APPS_CACHE["ts"] = _t.time()

        with patch("reflex_companion.actions.os.startfile",
                   side_effect=OSError("fake")), \
             patch("reflex_companion.actions.subprocess.run",
                   return_value=MagicMock(returncode=1)), \
             patch("reflex_companion.actions._search_desktop", return_value=None), \
             patch("reflex_companion.actions._search_start_menu", return_value=None), \
             patch("reflex_companion.actions.os.path.isdir", return_value=False):
            msg = actions.open_app("xyzabc123", lang="en")  # totally random
        # No debe tener suggestions ni nombres random
        assert "NoMatch" not in msg


# ════════════════════════════════════════════════════════════════════════
#  i18n parity: nuevos templates están en los 7 idiomas
# ════════════════════════════════════════════════════════════════════════


class TestI18nParity:
    @pytest.mark.parametrize("key", [
        "open_not_found_suggestions",
        "tabs_ambiguous",
        "windows_ambiguous",
    ])
    def test_template_in_all_7_languages(self, key):
        from reflex_companion.actions import _ACTION_MSGS
        assert key in _ACTION_MSGS, f"{key} no existe en _ACTION_MSGS"
        for lang in ("en", "es", "fr", "ja", "de", "ru", "ko"):
            assert lang in _ACTION_MSGS[key], (
                f"v0.19.47: falta traducción de {key} en {lang}"
            )
            # No debe ser string vacío
            assert _ACTION_MSGS[key][lang], (
                f"v0.19.47: traducción de {key}[{lang}] está vacía"
            )
