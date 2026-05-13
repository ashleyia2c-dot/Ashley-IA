"""Regression tests para v0.19.45 FASE 1 — open_app safety + search_web/
open_url success propagation.

Bug del user "abre et" (Lady Gaga) → open_app interpretó "et" como nombre
de app → fuzzy substring match encontró "Ashley-S**et**up-0.19.44.exe" en
Desktop → LANZÓ EL INSTALLER.

Causas raíz:
  1. score_shortcut_name aceptaba substring match (60 pts) para hints
     muy cortos. "et" matcheaba cualquier .exe con "et" dentro.
  2. _SHORTCUT_REJECT_TOKENS no incluía "setup"/"installer", así que
     installers pasaban el filtro de descarte.
  3. search_web siempre reportaba éxito aunque el browser no abriera —
     Ashley nunca disculpaba.

Fixes:
  - score_shortcut_name: hints <3 chars siempre return 0; hints 3-4 chars
    requieren exact (100) o prefix (80), NO substring (60).
  - _SHORTCUT_REJECT_TOKENS añade "setup", "installer".
  - search_web/open_url retornan (msg, success) en vez de solo msg.
"""
import pytest


# ════════════════════════════════════════════════════════════════════════
#  score_shortcut_name — short hint safety
# ════════════════════════════════════════════════════════════════════════


class TestScoreShortcutNameShortHintSafety:
    """v0.19.45 — hints muy cortos no deben fuzzy-matchear."""

    def test_two_char_hint_returns_zero(self):
        """'et' contra cualquier name → 0 (demasiado ambiguo)."""
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("Ashley-Setup-0.19.44", "et") == 0
        assert score_shortcut_name("Notepad", "et") == 0
        # Incluso match exacto de 2 chars: rechazado
        assert score_shortcut_name("et", "et") == 0

    def test_one_char_hint_returns_zero(self):
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("Notepad", "n") == 0

    def test_three_char_hint_substring_rejected(self):
        """Hint de 3 chars NO debe matchear por substring."""
        from reflex_companion.actions import score_shortcut_name
        # 'vsc' no es prefix de "MyVscEditor" pero está dentro como substring
        # → con _MIN_HINT_LEN_FOR_SUBSTRING=5, 3 chars rechaza substring.
        assert score_shortcut_name("MyVscEditor", "vsc") == 0
        # Otro: 'aim' está dentro de "ChainedAim" como substring (no prefix)
        assert score_shortcut_name("ChainedAim", "aim") == 0

    def test_three_char_hint_prefix_works(self):
        """'vsc' SÍ debe matchear "vscode" por prefix (80 pts)."""
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("VSCode", "vsc") == 80

    def test_three_char_hint_exact_works(self):
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("VSC", "vsc") == 100

    def test_four_char_hint_substring_still_rejected(self):
        """4 chars sigue siendo demasiado corto para substring match."""
        from reflex_companion.actions import score_shortcut_name
        # 'word' is in "MyWordEditor" but 4 < _MIN_HINT_LEN_FOR_SUBSTRING (5)
        assert score_shortcut_name("MyWordEditor", "word") == 0

    def test_five_char_hint_substring_works(self):
        """5+ chars permite substring match (60 pts)."""
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("MyWordsEditor", "words") == 60


# ════════════════════════════════════════════════════════════════════════
#  _SHORTCUT_REJECT_TOKENS — installer markers
# ════════════════════════════════════════════════════════════════════════


class TestRejectTokensIncludeInstaller:
    """v0.19.45 — los installers NO deben matchear como apps lanzables."""

    def test_setup_token_rejected(self):
        from reflex_companion.actions import score_shortcut_name
        # Hint largo (legítimo) que substring-matchea un installer:
        # incluso así debe rechazarse por el token "setup".
        assert score_shortcut_name("Ashley-Setup-0.19.44", "ashley") == 0

    def test_installer_token_rejected(self):
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("MyApp Installer", "myapp") == 0

    def test_real_app_with_setup_in_name_unfortunately_rejected(self):
        """Falso positivo aceptable: un app legítimo con 'setup' en su
        nombre (raro) será rechazado. Trade-off para evitar lanzar
        installers reales."""
        from reflex_companion.actions import score_shortcut_name
        # 'QuickSetup.exe' (hipotético) → rechazado
        assert score_shortcut_name("QuickSetup", "quicksetup") == 0

    def test_legitimate_app_unaffected(self):
        """Apps normales sin install markers funcionan igual."""
        from reflex_companion.actions import score_shortcut_name
        assert score_shortcut_name("Visual Studio Code", "visual studio") == 80
        assert score_shortcut_name("Steam", "steam") == 100
        assert score_shortcut_name("Discord", "discord") == 100


# ════════════════════════════════════════════════════════════════════════
#  Bug específico del user — "abre et" no debe lanzar installer
# ════════════════════════════════════════════════════════════════════════


class TestUserBugAbreET:
    """v0.19.45 — REGRESION GUARD del bug exacto reportado por el user."""

    def test_et_does_not_match_ashley_setup(self):
        """'et' (Lady Gaga E.T.) NO debe matchear 'Ashley-Setup-0.19.44'."""
        from reflex_companion.actions import score_shortcut_name
        # Triple defensa:
        # 1. "et" tiene <3 chars → 0
        # 2. "Ashley-Setup-0.19.44" contiene "setup" → 0
        # 3. Aunque pasara, "et" en "ashley-setup-0.19.44" sería substring
        #    pero "et" tiene < _MIN_HINT_LEN_FOR_SUBSTRING (5) → 0
        assert score_shortcut_name("Ashley-Setup-0.19.44", "et") == 0

    def test_et_does_not_match_any_installer(self):
        """Cualquier installer del Desktop con 'et' como substring NO
        debe matchear."""
        from reflex_companion.actions import score_shortcut_name
        installers = [
            "Steam Setup",
            "Discord Setup",
            "MyApp-Installer-1.0",
            "Some Random Setup.exe",
        ]
        for inst in installers:
            assert score_shortcut_name(inst, "et") == 0, (
                f"'et' NO debe matchear installer {inst!r}"
            )

    def test_legitimate_short_hints_still_work(self):
        """Pero queries cortas LEGÍTIMAS de 3+ chars con prefix sí funcionan."""
        from reflex_companion.actions import score_shortcut_name
        # 'vlc' debe matchear "VLC media player" por prefix
        assert score_shortcut_name("VLC media player", "vlc") == 80
        # 'gimp' (4 chars) match exacto si app se llama así
        assert score_shortcut_name("GIMP", "gimp") == 100


# ════════════════════════════════════════════════════════════════════════
#  search_web / open_url — success propagation
# ════════════════════════════════════════════════════════════════════════


class TestSearchWebReturnsSuccessTuple:
    """v0.19.45 — search_web retorna (msg, success) — antes solo msg."""

    def test_search_web_returns_tuple(self):
        """search_web devuelve (msg: str, success: bool)."""
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions._open_url_cdp_safe",
                   return_value=(False, True)):
            result = actions.search_web("test query", lang="en")
        assert isinstance(result, tuple)
        assert len(result) == 2
        msg, ok = result
        assert isinstance(msg, str)
        assert ok is True

    def test_search_web_propagates_failure(self):
        """Si _open_url_cdp_safe devuelve opened_ok=False, search_web
        propaga success=False."""
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions._open_url_cdp_safe",
                   return_value=(False, False)):
            msg, ok = actions.search_web("test", lang="en")
        assert ok is False, (
            "v0.19.45: search_web debe propagar failure (antes siempre True)"
        )


class TestOpenUrlReturnsSuccessTuple:
    def test_open_url_returns_tuple(self):
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions._open_url_cdp_safe",
                   return_value=(False, True)):
            result = actions.open_url("https://example.com", lang="en")
        assert isinstance(result, tuple) and len(result) == 2

    def test_open_url_propagates_already_open_as_success(self):
        """Si la tab ya estaba abierta, success=True (no es un fallo)."""
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions._open_url_cdp_safe",
                   return_value=(True, True)):  # already_open=True
            msg, ok = actions.open_url("https://github.com", lang="en")
        assert ok is True

    def test_open_url_propagates_failure(self):
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions._open_url_cdp_safe",
                   return_value=(False, False)):
            msg, ok = actions.open_url("https://example.com", lang="en")
        assert ok is False


# ════════════════════════════════════════════════════════════════════════
#  execute_action propaga el success de search_web/open_url
# ════════════════════════════════════════════════════════════════════════


class TestExecuteActionPropagatesSuccess:
    """v0.19.45 — execute_action debe usar el success real (no hardcoded
    True) en search_web y open_url para que Ashley se disculpe en
    personaje cuando la búsqueda no se abrió."""

    def test_execute_action_search_web_uses_real_success(self):
        """Si search_web devuelve ok=False, execute_action debe devolver
        success=False."""
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions.search_web",
                   return_value=("msg", False)) as mock_sw:
            result = actions.execute_action(
                "search_web", ["test"], browser_opened=False, lang="en",
            )
        assert mock_sw.called
        assert result["success"] is False, (
            "execute_action debe propagar success=False de search_web"
        )

    def test_execute_action_open_url_uses_real_success(self):
        from unittest.mock import patch
        from reflex_companion import actions
        with patch("reflex_companion.actions.open_url",
                   return_value=("msg", False)) as mock_ou:
            result = actions.execute_action(
                "open_url", ["https://example.com"],
                browser_opened=False, lang="en",
            )
        assert mock_ou.called
        assert result["success"] is False
