"""
Tests for the shortcut ranking logic used by open_app to avoid launching
installers/uninstallers/helpers when the user asks for the actual app.

The bug that motivated this: asking Ashley to open "rimworld" opened
"Uninstall RimWorld.lnk" because glob returned it first.
"""

from reflex_companion.actions import score_shortcut_name


# ── Rejections ───────────────────────────────────────────────────────────────


def test_uninstall_rejected():
    """The exact bug — do not match uninstaller shortcuts."""
    assert score_shortcut_name("Uninstall RimWorld", "rimworld") == 0
    assert score_shortcut_name("Desinstalar Steam", "steam") == 0
    assert score_shortcut_name("Désinstaller Chrome", "chrome") == 0


def test_inno_setup_uninstaller_naming_rejected():
    assert score_shortcut_name("unins000", "rimworld") == 0
    assert score_shortcut_name("unins001", "chrome") == 0


def test_docs_and_helpers_rejected():
    assert score_shortcut_name("RimWorld Readme", "rimworld") == 0
    assert score_shortcut_name("Chrome Manual", "chrome") == 0
    assert score_shortcut_name("Crash Reporter", "reporter") == 0
    assert score_shortcut_name("Steam Config", "steam") == 0
    assert score_shortcut_name("VC++ Redistributable x64", "redistributable") == 0


# ── Exact / starts / contains / reverse ──────────────────────────────────────


def test_exact_match_is_highest():
    assert score_shortcut_name("RimWorld", "rimworld") == 100
    assert score_shortcut_name("Steam", "steam") == 100


def test_starts_with_is_higher_than_contains():
    starts = score_shortcut_name("RimWorld Classic", "rimworld")
    contains = score_shortcut_name("Play RimWorld Now", "rimworld")
    assert starts == 80
    assert contains == 60
    assert starts > contains


def test_contains_match():
    assert score_shortcut_name("Play RimWorld Now", "rimworld") == 60


def test_reverse_substring_is_weakest():
    # name='rim' ⊂ hint='rimworld' — weak match, could be a different app
    assert score_shortcut_name("rim", "rimworld") == 30


def test_no_relation_is_zero():
    assert score_shortcut_name("Discord", "rimworld") == 0
    assert score_shortcut_name("Steam", "chrome") == 0


# ── Case insensitivity ───────────────────────────────────────────────────────


def test_case_insensitive_exact():
    assert score_shortcut_name("RIMWORLD", "rimworld") == 100
    assert score_shortcut_name("rimworld", "RIMWORLD") == 100
    assert score_shortcut_name("RimWorld", "rimworld") == 100


def test_case_insensitive_rejection():
    assert score_shortcut_name("UNINSTALL RIMWORLD", "rimworld") == 0


# ── Empty / edge cases ───────────────────────────────────────────────────────


def test_empty_inputs_return_zero():
    assert score_shortcut_name("", "rimworld") == 0
    assert score_shortcut_name("RimWorld", "") == 0
    assert score_shortcut_name("", "") == 0


# ── End-to-end ranking simulation ────────────────────────────────────────────


def test_ranking_picks_game_over_uninstaller():
    """The core bug case: simulate two candidates in the Start Menu folder.
    The uninstaller is rejected entirely; only the real game gets a score."""
    hint = "rimworld"
    candidates = [
        ("Uninstall RimWorld", score_shortcut_name("Uninstall RimWorld", hint)),
        ("RimWorld", score_shortcut_name("RimWorld", hint)),
    ]
    best = max(candidates, key=lambda t: t[1])
    assert best[0] == "RimWorld"
    assert best[1] == 100


def test_ranking_prefers_shorter_exact_over_longer_variant():
    """When both match exactly on content but one has extra framing
    ('Play X'), the shorter one wins with higher score (starts_with=80 vs
    contains=60). This is the Steam-vs-Play-Steam case."""
    hint = "steam"
    assert score_shortcut_name("Steam", hint) > score_shortcut_name("Play Steam Beta", hint)
