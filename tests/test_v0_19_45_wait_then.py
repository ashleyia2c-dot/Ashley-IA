"""Regression tests para v0.19.45 — [action:wait_then:N:NESTED] action.

Caso del user: "pon Espresso y luego dale like" — antes Ashley
prometía pero nunca ejecutaba el like (la página de YouTube no había
cargado el botón cuando click se intentaba). Ahora puede emitir:

  [action:play_music:Espresso Sabrina][action:wait_then:5:click:like]

Que ejecuta:
  1. play_music abre la tab
  2. wait_then duerme 5s (deja que la página cargue)
  3. click:like ejecuta sobre la página ya cargada

Seguridad:
  - delay capeado entre 1-20s (sino timeout 30s del speculative
    dispatch causaría doble ejecución por fallback).
  - wait_then NO se puede anidar dentro de wait_then (recursion bomb).
  - wait_then en _LONG_RUNNING_ACTIONS para que finalize tenga
    timeout 30s en thread.join.
"""
from unittest.mock import patch
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  Parser: extract_action handles wait_then correctly
# ════════════════════════════════════════════════════════════════════════


class TestWaitThenParsing:
    def test_simple_wait_then_click(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:wait_then:5:click:like]")
        assert action is not None
        assert action["type"] == "wait_then"
        assert action["params"] == ["5", "click", "like"]

    def test_wait_then_with_text_action(self):
        """Para wait_then anidando una acción text-based (click con texto
        que tiene espacios), el split por : aún funciona porque "Me gusta"
        no tiene colon."""
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:wait_then:7:click:Me gusta]")
        assert action["params"] == ["7", "click", "Me gusta"]

    def test_wait_then_strips_from_text(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action(
            "voy a esperar [action:wait_then:5:click:like] y listo"
        )
        assert action["type"] == "wait_then"
        assert "voy a esperar" in clean
        assert "listo" in clean
        assert "wait_then" not in clean


# ════════════════════════════════════════════════════════════════════════
#  Execute: time.sleep + dispatch nested
# ════════════════════════════════════════════════════════════════════════


class TestWaitThenExecution:
    def test_sleeps_then_dispatches_nested(self):
        from reflex_companion import actions
        sleep_calls = []

        def fake_sleep(s):
            sleep_calls.append(s)

        with patch("reflex_companion.actions.time.sleep",
                   side_effect=fake_sleep), \
             patch("reflex_companion.actions.execute_action",
                   wraps=actions.execute_action) as wrapped_exec:
            # Reset wrapped: la primera call es la nuestra, la segunda
            # debería ser la recursiva por wait_then.
            result = actions.execute_action(
                "wait_then", ["3", "screenshot"],
                browser_opened=False, lang="en",
            )
        # Sleep llamado con 3
        assert 3 in sleep_calls
        # execute_action recursivo a screenshot
        recursive_calls = [c for c in wrapped_exec.call_args_list
                           if c.args and c.args[0] == "screenshot"]
        assert len(recursive_calls) >= 1, (
            "wait_then debe dispatchar la nested action via execute_action"
        )

    def test_caps_delay_at_20s(self):
        """Aunque Ashley emita wait_then:99:..., el delay se capea a 20s
        para no exceder el timeout 30s del speculative dispatch."""
        from reflex_companion import actions
        sleep_calls = []

        def fake_sleep(s):
            sleep_calls.append(s)

        with patch("reflex_companion.actions.time.sleep",
                   side_effect=fake_sleep), \
             patch("reflex_companion.actions.execute_action",
                   wraps=actions.execute_action):
            actions.execute_action(
                "wait_then", ["99", "screenshot"],
                browser_opened=False, lang="en",
            )
        # 99 debe ser capeado a 20
        assert 20 in sleep_calls
        assert 99 not in sleep_calls

    def test_caps_delay_at_minimum_1s(self):
        """delay 0 o negativo se capea a 1s mínimo."""
        from reflex_companion import actions
        sleep_calls = []

        with patch("reflex_companion.actions.time.sleep",
                   side_effect=sleep_calls.append), \
             patch("reflex_companion.actions.execute_action",
                   wraps=actions.execute_action):
            actions.execute_action(
                "wait_then", ["0", "screenshot"],
                browser_opened=False, lang="en",
            )
        assert 1 in sleep_calls

    def test_invalid_delay_returns_failure(self):
        """delay no numérico devuelve success=False, no crashea."""
        from reflex_companion import actions
        with patch("reflex_companion.actions.time.sleep"):
            result = actions.execute_action(
                "wait_then", ["abc", "screenshot"],
                browser_opened=False, lang="en",
            )
        assert result["success"] is False
        assert "no es número" in result["result"] or "no es n" in result["result"]

    def test_missing_nested_action_returns_failure(self):
        """Sin nested_type, returns failure no crashea."""
        from reflex_companion import actions
        result = actions.execute_action(
            "wait_then", ["5"],
            browser_opened=False, lang="en",
        )
        assert result["success"] is False

    def test_nested_wait_then_rejected(self):
        """No se puede anidar wait_then dentro de wait_then (recursion bomb)."""
        from reflex_companion import actions
        with patch("reflex_companion.actions.time.sleep"):
            result = actions.execute_action(
                "wait_then", ["5", "wait_then", "5", "screenshot"],
                browser_opened=False, lang="en",
            )
        assert result["success"] is False
        assert "wait_then" in result["result"]


# ════════════════════════════════════════════════════════════════════════
#  Text-based nested actions: params se rejoinan con ":"
# ════════════════════════════════════════════════════════════════════════


class TestNestedTextActionsRejoinParams:
    """Si el nested es type_text/play_music/click/etc. y el texto tiene
    ":", los params se rejoinan correctamente."""

    def test_nested_play_music_with_simple_query(self):
        from reflex_companion import actions
        with patch("reflex_companion.actions.time.sleep"), \
             patch("reflex_companion.actions.play_music",
                   return_value=("ok", True, True)) as mock_pm:
            actions.execute_action(
                "wait_then", ["3", "play_music", "Espresso Sabrina"],
                browser_opened=False, lang="en",
            )
        # play_music recibe "Espresso Sabrina" como query
        assert mock_pm.called
        args = mock_pm.call_args
        assert "Espresso Sabrina" in args.args[0]

    def test_nested_click_simple_label(self):
        """click:like → click recibe params=["like"]."""
        from reflex_companion import actions
        # Skip CDP path en click — devuelve sin browser
        with patch("reflex_companion.actions.time.sleep"), \
             patch("reflex_companion.browser_cdp.is_cdp_available",
                   return_value=False):
            result = actions.execute_action(
                "wait_then", ["3", "click", "like"],
                browser_opened=False, lang="en", prefer_cdp=False,
            )
        # Sin CDP, click devuelve error pero no crashea
        assert "result" in result


# ════════════════════════════════════════════════════════════════════════
#  Long running action: wait_then en _LONG_RUNNING_ACTIONS
# ════════════════════════════════════════════════════════════════════════


class TestWaitThenLongRunning:
    def test_in_long_running_actions_set(self):
        """wait_then debe estar en _LONG_RUNNING_ACTIONS para que
        finalize use timeout 30s y no fallback re-ejecute."""
        from reflex_companion.parsing import _LONG_RUNNING_ACTIONS
        assert "wait_then" in _LONG_RUNNING_ACTIONS


# ════════════════════════════════════════════════════════════════════════
#  Prompts: documentado en los 7 idiomas
# ════════════════════════════════════════════════════════════════════════


class TestWaitThenInPrompts:
    @pytest.mark.parametrize("lang_file", [
        "prompts_es.py", "prompts_en.py", "prompts_fr.py",
        "prompts_ja.py", "prompts_de.py", "prompts_ru.py", "prompts_ko.py",
    ])
    def test_wait_then_documented_in_all_languages(self, lang_file):
        src = (REPO_ROOT / "reflex_companion" / lang_file).read_text(
            encoding="utf-8",
        )
        assert "[action:wait_then:" in src, (
            f"{lang_file} debe documentar [action:wait_then:...]"
        )
        # Debe tener el ejemplo de chain play_music + click:like
        assert "click:like" in src or "click:Me gusta" in src or "wait_then:5" in src
