"""
test_parsing.py — Tests for the action/mood tag parsing logic
used by State._extract_mood and State._extract_action in reflex_companion.py,
plus parse_remind_params from reminders.py.

Since State is an rx.State subclass and hard to instantiate in a test,
we replicate the regex-based parsing logic in standalone functions and
test those directly.  The patterns are copied verbatim from the source.
"""

import re
import pytest

from reflex_companion.reminders import parse_remind_params


# ═══════════════════════════════════════════════════════════════════════════════
#  Standalone replicas of State._extract_mood / State._extract_action
# ═══════════════════════════════════════════════════════════════════════════════

def extract_mood(text: str) -> tuple[str, str]:
    """Replica of State._extract_mood (regex from reflex_companion.py)."""
    match = re.search(r'\[mood:(\w+)\]', text)
    if match:
        detected = match.group(1)
        clean = text.replace(match.group(0), "").strip()
        return clean, detected
    return text, "default"


def extract_action(text: str) -> tuple[str, dict | None]:
    """
    Replica of State._extract_action (regex + per-type parsing
    from reflex_companion.py), minus the describe_action call.
    """
    match = re.search(r'\[action:([^\]]+)\]', text)
    if not match:
        return text, None

    full_tag = match.group(0)
    content  = match.group(1)

    colon = content.find(":")
    if colon == -1:
        a_type, rest = content, ""
    else:
        a_type = content[:colon]
        rest   = content[colon + 1:]

    TEXT_ACTIONS = ("type_text", "search_web", "open_url", "play_music")
    if a_type in TEXT_ACTIONS:
        params = [rest] if rest else []
    elif a_type == "type_in":
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    elif a_type == "write_to_app":
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    elif a_type == "remind":
        params = parse_remind_params(rest)
    elif a_type in ("add_important", "done_important"):
        params = [rest] if rest else []
    elif a_type == "save_taste":
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    else:
        params = rest.split(":") if rest else []

    clean = text.replace(full_tag, "").strip()
    return clean, {"type": a_type, "params": params}


# ═══════════════════════════════════════════════════════════════════════════════
#  MOOD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractMood:
    """Tests for extract_mood — the [mood:X] tag parser."""

    # ── All 7 moods ──────────────────────────────────────────────────────────

    @pytest.mark.parametrize("mood", [
        "excited", "embarrassed", "tsundere", "soft",
        "surprised", "proud", "default",
    ])
    def test_all_valid_moods(self, mood: str):
        text = f"hello [mood:{mood}] world"
        clean, detected = extract_mood(text)
        assert detected == mood
        assert f"[mood:{mood}]" not in clean

    # ── Position variants ────────────────────────────────────────────────────

    def test_mood_at_end(self):
        clean, mood = extract_mood("hello [mood:excited]")
        assert mood == "excited"
        assert clean == "hello"

    def test_mood_at_start(self):
        clean, mood = extract_mood("[mood:tsundere] hey")
        assert mood == "tsundere"
        assert clean == "hey"

    def test_mood_in_middle(self):
        clean, mood = extract_mood("before [mood:soft] after")
        assert mood == "soft"
        assert clean == "before  after"  # double space from str.replace

    # ── Default / missing ────────────────────────────────────────────────────

    def test_no_mood_tag(self):
        clean, mood = extract_mood("no mood here")
        assert mood == "default"
        assert clean == "no mood here"

    def test_empty_text(self):
        clean, mood = extract_mood("")
        assert mood == "default"
        assert clean == ""

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_multiple_mood_tags_first_wins(self):
        """str.replace removes ALL occurrences, re.search picks the first."""
        text = "a [mood:excited] b [mood:proud] c"
        clean, mood = extract_mood(text)
        assert mood == "excited"
        # Both tags are removed because str.replace removes the first match
        # and the second [mood:proud] stays (replace only removes exact match)
        assert "[mood:excited]" not in clean
        # The second tag is NOT removed because replace only targets the
        # matched group(0), which is [mood:excited]
        assert "[mood:proud]" in clean

    def test_mood_only_text(self):
        clean, mood = extract_mood("[mood:surprised]")
        assert mood == "surprised"
        assert clean == ""

    def test_mood_with_surrounding_whitespace(self):
        clean, mood = extract_mood("  [mood:embarrassed]  ")
        assert mood == "embarrassed"
        assert clean == ""  # strip() in the function

    def test_mood_tag_case_sensitive(self):
        r"""Mood tags are lowercase only (\\w+ matches but State checks exact)."""
        clean, mood = extract_mood("text [mood:EXCITED]")
        assert mood == "EXCITED"  # regex \w+ matches uppercase too
        assert clean == "text"

    def test_malformed_tag_missing_bracket(self):
        clean, mood = extract_mood("text [mood:excited")
        assert mood == "default"
        assert clean == "text [mood:excited"

    def test_mood_with_newlines(self):
        clean, mood = extract_mood("line1\n[mood:soft]\nline2")
        assert mood == "soft"
        assert "line1" in clean
        assert "line2" in clean


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractAction:
    """Tests for extract_action — the [action:type:params] tag parser."""

    # ── No action ────────────────────────────────────────────────────────────

    def test_no_action_tag(self):
        clean, action = extract_action("just some text")
        assert action is None
        assert clean == "just some text"

    def test_empty_text_no_action(self):
        clean, action = extract_action("")
        assert action is None
        assert clean == ""

    # ── Screenshot (no params) ───────────────────────────────────────────────

    def test_screenshot(self):
        clean, action = extract_action("text [action:screenshot]")
        assert action is not None
        assert action["type"] == "screenshot"
        assert action["params"] == []
        assert clean == "text"

    # ── open_app (standard split) ────────────────────────────────────────────

    def test_open_app(self):
        clean, action = extract_action("text [action:open_app:notepad]")
        assert action["type"] == "open_app"
        assert action["params"] == ["notepad"]

    def test_open_app_with_spaces_in_name(self):
        clean, action = extract_action("text [action:open_app:Visual Studio Code]")
        assert action["type"] == "open_app"
        assert action["params"] == ["Visual Studio Code"]

    # ── volume (standard split, multiple params) ─────────────────────────────

    def test_volume_set(self):
        clean, action = extract_action("text [action:volume:set:50]")
        assert action["type"] == "volume"
        assert action["params"] == ["set", "50"]

    def test_volume_up(self):
        clean, action = extract_action("text [action:volume:up]")
        assert action["type"] == "volume"
        assert action["params"] == ["up"]

    def test_volume_down(self):
        clean, action = extract_action("[action:volume:down] adjusting")
        assert action["type"] == "volume"
        assert action["params"] == ["down"]

    def test_volume_mute(self):
        clean, action = extract_action("text [action:volume:mute]")
        assert action["type"] == "volume"
        assert action["params"] == ["mute"]

    # ── TEXT_ACTIONS (single param, may contain colons) ──────────────────────

    def test_type_text(self):
        clean, action = extract_action("text [action:type_text:Hello world!]")
        assert action["type"] == "type_text"
        assert action["params"] == ["Hello world!"]

    def test_search_web(self):
        clean, action = extract_action("text [action:search_web:python regex tutorial]")
        assert action["type"] == "search_web"
        assert action["params"] == ["python regex tutorial"]

    def test_open_url_with_colons(self):
        """URLs contain colons — the whole URL must be a single param."""
        clean, action = extract_action("text [action:open_url:https://example.com:8080/path]")
        assert action["type"] == "open_url"
        assert action["params"] == ["https://example.com:8080/path"]

    def test_play_music(self):
        clean, action = extract_action("text [action:play_music:lofi hip hop radio]")
        assert action["type"] == "play_music"
        assert action["params"] == ["lofi hip hop radio"]

    # ── type_in (window title + text body) ───────────────────────────────────

    def test_type_in(self):
        clean, action = extract_action("text [action:type_in:Notepad:hello world]")
        assert action["type"] == "type_in"
        assert action["params"] == ["Notepad", "hello world"]

    def test_type_in_text_with_colons(self):
        """The text portion of type_in may contain colons."""
        clean, action = extract_action("text [action:type_in:Notepad:time is 12:30:00]")
        assert action["type"] == "type_in"
        assert action["params"] == ["Notepad", "time is 12:30:00"]

    def test_type_in_no_text(self):
        clean, action = extract_action("text [action:type_in:Notepad]")
        assert action["type"] == "type_in"
        assert action["params"] == ["Notepad"]

    # ── write_to_app (app name + content body) ───────────────────────────────

    def test_write_to_app(self):
        clean, action = extract_action(r"text [action:write_to_app:notepad:Hello\nWorld]")
        assert action["type"] == "write_to_app"
        assert action["params"][0] == "notepad"
        assert action["params"][1] == r"Hello\nWorld"

    def test_write_to_app_content_with_colons(self):
        clean, action = extract_action("text [action:write_to_app:notepad:key: value: extra]")
        assert action["type"] == "write_to_app"
        assert action["params"] == ["notepad", "key: value: extra"]

    # ── remind (datetime parsing) ────────────────────────────────────────────

    def test_remind_with_seconds(self):
        clean, action = extract_action(
            "text [action:remind:2026-04-15T15:00:00:Meeting with team]"
        )
        assert action["type"] == "remind"
        assert action["params"] == ["2026-04-15T15:00:00", "Meeting with team"]

    def test_remind_without_seconds(self):
        clean, action = extract_action(
            "text [action:remind:2026-04-15T15:00:Check email]"
        )
        assert action["type"] == "remind"
        assert action["params"] == ["2026-04-15T15:00", "Check email"]

    # ── save_taste (category + value) ────────────────────────────────────────

    def test_save_taste(self):
        clean, action = extract_action("text [action:save_taste:musica:reggaeton]")
        assert action["type"] == "save_taste"
        assert action["params"] == ["musica", "reggaeton"]

    def test_save_taste_single_param(self):
        clean, action = extract_action("text [action:save_taste:comida]")
        assert action["type"] == "save_taste"
        assert action["params"] == ["comida"]

    # ── add_important / done_important (single text param) ───────────────────

    def test_add_important(self):
        clean, action = extract_action("text [action:add_important:Buy groceries]")
        assert action["type"] == "add_important"
        assert action["params"] == ["Buy groceries"]

    def test_done_important(self):
        clean, action = extract_action("text [action:done_important:Buy groceries]")
        assert action["type"] == "done_important"
        assert action["params"] == ["Buy groceries"]

    # ── hotkey / press_key (standard split) ──────────────────────────────────

    def test_hotkey(self):
        clean, action = extract_action("text [action:hotkey:ctrl:c]")
        assert action["type"] == "hotkey"
        assert action["params"] == ["ctrl", "c"]

    def test_press_key(self):
        clean, action = extract_action("text [action:press_key:enter]")
        assert action["type"] == "press_key"
        assert action["params"] == ["enter"]

    # ── focus_window / close_window / close_tab ──────────────────────────────

    def test_focus_window(self):
        clean, action = extract_action("text [action:focus_window:Chrome]")
        assert action["type"] == "focus_window"
        assert action["params"] == ["Chrome"]

    def test_close_window(self):
        clean, action = extract_action("text [action:close_window:Notepad]")
        assert action["type"] == "close_window"
        assert action["params"] == ["Notepad"]

    def test_close_tab(self):
        clean, action = extract_action("text [action:close_tab:YouTube]")
        assert action["type"] == "close_tab"
        assert action["params"] == ["YouTube"]

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_multiple_action_tags_first_wins(self):
        """re.search picks the first match."""
        text = "a [action:screenshot] b [action:open_app:notepad] c"
        clean, action = extract_action(text)
        assert action["type"] == "screenshot"
        # Only the first tag is removed
        assert "[action:open_app:notepad]" in clean

    def test_action_tag_cleaned_from_text(self):
        clean, action = extract_action("before [action:screenshot] after")
        assert clean == "before  after"
        assert action["type"] == "screenshot"

    def test_action_only_text(self):
        clean, action = extract_action("[action:screenshot]")
        assert clean == ""
        assert action["type"] == "screenshot"

    def test_action_with_empty_params(self):
        """An action type with trailing colon but no value: rest is empty str."""
        clean, action = extract_action("text [action:open_app:]")
        assert action["type"] == "open_app"
        # rest is "" which is falsy, so `rest.split(":") if rest else []` -> []
        assert action["params"] == []


# ═══════════════════════════════════════════════════════════════════════════════
#  PARSE_REMIND_PARAMS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseRemindParams:
    """Tests for parse_remind_params from reminders.py."""

    def test_full_datetime_with_seconds(self):
        result = parse_remind_params("2026-04-15T15:00:00:Meeting with team")
        assert result == ["2026-04-15T15:00:00", "Meeting with team"]

    def test_datetime_without_seconds(self):
        result = parse_remind_params("2026-04-15T15:00:Check email")
        assert result == ["2026-04-15T15:00", "Check email"]

    def test_text_with_colons(self):
        result = parse_remind_params("2026-04-15T10:30:00:Time is 12:30 ok")
        assert result == ["2026-04-15T10:30:00", "Time is 12:30 ok"]

    def test_no_text_only_datetime(self):
        r"""
        Input: "2026-04-15T15:00:00" (no trailing :text).
        The regex (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?):(.+) matches
        with the optional seconds group NOT consumed, so:
          group(1) = "2026-04-15T15:00", group(2) = "00"
        This is a known quirk: a bare datetime with seconds is ambiguous.
        """
        result = parse_remind_params("2026-04-15T15:00:00")
        assert result == ["2026-04-15T15:00", "00"]

    def test_empty_string(self):
        result = parse_remind_params("")
        assert result == []

    def test_garbage_input(self):
        result = parse_remind_params("just random text")
        assert result == ["just random text"]

    def test_datetime_with_seconds_and_complex_text(self):
        result = parse_remind_params(
            "2026-12-25T09:00:00:Christmas morning: open presents!"
        )
        assert result == [
            "2026-12-25T09:00:00",
            "Christmas morning: open presents!",
        ]


# ─────────────────────────────────────────────────────────────────
# v0.19.20 — guard contra UnboundLocalError "params"
# Bug original: extract_action no tenía rama else para action types
# que no eran type_text/type_in/write_to_app/remind/add_important/
# done_important/save_taste/save_date/save_goal/check_in_goal/complete_goal.
# Para volume/open_app/close_window/screenshot/hotkey/etc, params nunca
# se asignaba y al return crashaba con UnboundLocalError visible al
# user como "Something went wrong with Grok (send_message): cannot
# access local variable 'params' where it is not associated with a value".
# ─────────────────────────────────────────────────────────────────


class TestExtractActionFallthroughBranch:
    """Ensures extract_action handles ALL action types without crashing,
    not just the ones explicitly listed in if/elif branches."""

    def test_volume_up(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:volume:up]")
        assert action == {"type": "volume", "params": ["up"]}

    def test_volume_set_with_value(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:volume:set:75]")
        assert action == {"type": "volume", "params": ["set", "75"]}

    def test_open_app(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:open_app:notepad]")
        assert action == {"type": "open_app", "params": ["notepad"]}

    def test_close_window(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:close_window:Discord]")
        assert action == {"type": "close_window", "params": ["Discord"]}

    def test_close_tab(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:close_tab:YouTube]")
        assert action == {"type": "close_tab", "params": ["YouTube"]}

    def test_screenshot_no_params(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:screenshot]")
        assert action == {"type": "screenshot", "params": []}

    def test_hotkey_multiple_keys(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:hotkey:ctrl:c]")
        assert action == {"type": "hotkey", "params": ["ctrl", "c"]}

    def test_press_key(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:press_key:enter]")
        assert action == {"type": "press_key", "params": ["enter"]}

    def test_focus_window(self):
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:focus_window:Chrome]")
        assert action == {"type": "focus_window", "params": ["Chrome"]}

    def test_unknown_action_type_doesnt_crash(self):
        """Even for completely new/unknown action types, must not raise
        UnboundLocalError. The fallback branch handles it gracefully."""
        from reflex_companion.parsing import extract_action
        clean, action = extract_action("[action:future_action:foo:bar:baz]")
        assert action is not None
        assert action["type"] == "future_action"
        assert action["params"] == ["foo", "bar", "baz"]


# ─────────────────────────────────────────────────────────────────
# v0.19.30 — extract_all_actions DEBE deduplicar acciones idempotentes,
# especialmente play_music donde dos URLs distintas pueden apuntar al
# mismo videoId (?v=X vs ?v=X&t=10s). Bug producción: Ashley emitió
# play_music dos veces en la misma respuesta → 2 tabs idénticas en Opera.
#
# Notar: `extract_action` ya colapsa byte-idénticos vía text.replace()
# (comportamiento histórico, no parte de este fix). Los tests aquí se
# enfocan en lo que el dedupe NUEVO añade: variaciones de URL para el
# mismo videoId, y defensa explícita para los demás idempotentes.
# ─────────────────────────────────────────────────────────────────


class TestExtractAllActionsDedupe:
    """Garantiza que el LLM emitiendo dos veces play_music para el mismo
    video (con URLs ligeramente distintas) no genera doble tab."""

    def test_dedupes_play_music_same_videoid_diff_url_params(self):
        """BUG B v0.19.29 → fix v0.19.30: dos play_music con MISMO videoId
        pero query params distintos (?t=10) ya NO abre 2 tabs."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:play_music:https://www.youtube.com/watch?v=dQw4w9WgXcQ]"
            "[action:play_music:https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 1, (
            f"Dos play_music para el mismo videoId con URLs distintas deben "
            f"deduplicarse. Got {len(actions)} actions."
        )
        assert actions[0]["type"] == "play_music"

    def test_dedupes_play_music_youtu_be_vs_youtube_com_same_video(self):
        """youtu.be/X y youtube.com/watch?v=X son el mismo video."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:play_music:https://youtu.be/dQw4w9WgXcQ]"
            "[action:play_music:https://www.youtube.com/watch?v=dQw4w9WgXcQ]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 1

    def test_does_NOT_dedupe_different_videoids(self):
        """Si los videoIds son distintos, ambas deben ejecutarse."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:play_music:https://youtube.com/watch?v=AAAAAAAAAAA]"
            "[action:play_music:https://youtube.com/watch?v=BBBBBBBBBBB]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 2

    def test_dedupes_open_url(self):
        """defensa explícita aunque text.replace ya colapse byte-idénticos."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:open_url:https://github.com]"
            "[action:open_url:https://github.com]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 1

    def test_dedupes_search_web(self):
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:search_web:python tutorials]"
            "[action:search_web:python tutorials]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 1

    def test_dedupes_open_app(self):
        from reflex_companion.parsing import extract_all_actions
        text = "[action:open_app:notepad][action:open_app:notepad]"
        _, actions = extract_all_actions(text)
        assert len(actions) == 1

    def test_dedupes_focus_window(self):
        from reflex_companion.parsing import extract_all_actions
        text = "[action:focus_window:Chrome][action:focus_window:Chrome]"
        _, actions = extract_all_actions(text)
        assert len(actions) == 1

    def test_does_NOT_dedupe_different_open_apps(self):
        """User pide 'abre notepad y abre paint' → 2 acciones."""
        from reflex_companion.parsing import extract_all_actions
        text = "[action:open_app:notepad][action:open_app:mspaint]"
        _, actions = extract_all_actions(text)
        assert len(actions) == 2

    def test_does_NOT_dedupe_different_search_terms(self):
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:search_web:python tutorials]"
            "[action:search_web:rust tutorials]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 2

    def test_dedupe_preserves_order_for_mixed_actions(self):
        """Si hay [play_music:A][type_text:X][play_music:A_t=10], el segundo
        play_music se elimina (mismo videoId) pero type_text se mantiene."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:play_music:https://youtube.com/watch?v=dQw4w9WgXcQ]"
            "[action:type_text:hello]"
            "[action:play_music:https://youtube.com/watch?v=dQw4w9WgXcQ&t=5]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 2
        assert actions[0]["type"] == "play_music"
        assert actions[1]["type"] == "type_text"

    def test_three_identical_play_music_collapse_to_one(self):
        """Si Ashley emite el mismo videoId 3+ veces (con URLs distintas
        cada una para evitar el dedupe accidental de text.replace), sigue
        siendo solo 1."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:play_music:https://youtube.com/watch?v=dQw4w9WgXcQ]"
            "[action:play_music:https://youtube.com/watch?v=dQw4w9WgXcQ&t=5]"
            "[action:play_music:https://youtu.be/dQw4w9WgXcQ]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 1

    def test_play_music_non_youtube_url_falls_back_to_exact_key(self):
        """Si la URL no es YouTube, el videoId regex no matchea y caemos
        al dedupe por exact (type, params). Spotify/SoundCloud quedan
        protegidos por el accidental text.replace."""
        from reflex_companion.parsing import extract_all_actions
        text = (
            "[action:play_music:spotify:track:abc123]"
            "[action:play_music:spotify:track:xyz789]"
        )
        _, actions = extract_all_actions(text)
        assert len(actions) == 2  # tracks distintos → ambos pasan
