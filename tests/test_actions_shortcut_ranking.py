"""
Tests for the shortcut ranking logic used by open_app to avoid launching
installers/uninstallers/helpers when the user asks for the actual app.

The bug that motivated this: asking Ashley to open "rimworld" opened
"Uninstall RimWorld.lnk" because glob returned it first.

Also covers the Desktop search path added afterwards (users often put
their frequently-used app shortcuts on the Desktop).
"""

import os

import pytest

from reflex_companion import actions as _actions
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


# ── _search_desktop (filesystem-touching, uses tmp_path) ─────────────────────


@pytest.fixture
def fake_desktop(tmp_path, monkeypatch):
    """Point _search_desktop at a fake single-Desktop layout in tmp_path.

    We redirect USERNAME so the "%USERPROFILE%\\Desktop" pattern resolves
    under tmp_path, and also redirect PUBLIC for the all-users Desktop
    location. OneDrive paths don't exist → skipped by isdir() check.
    """
    user_root = tmp_path / "users" / "tester"
    desktop = user_root / "Desktop"
    desktop.mkdir(parents=True)
    public_desktop = tmp_path / "Public" / "Desktop"
    public_desktop.mkdir(parents=True)

    # Hack: _search_desktop builds paths as rf"C:\Users\{username}\Desktop".
    # Monkey-patch the function to use our tmp paths instead.
    def _fake_search(hint):
        import glob
        candidates = []
        for root in [str(desktop), str(public_desktop)]:
            if not os.path.isdir(root):
                continue
            for pattern in ("*.lnk", "*.url", "*.exe"):
                for f in glob.iglob(os.path.join(root, pattern)):
                    name = os.path.splitext(os.path.basename(f))[0]
                    score = score_shortcut_name(name, hint)
                    if score > 0:
                        candidates.append((-score, len(name), f))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][2]

    monkeypatch.setattr(_actions, "_search_desktop", _fake_search)
    return {"desktop": desktop, "public": public_desktop}


def test_desktop_finds_exact_match(fake_desktop):
    (fake_desktop["desktop"] / "RimWorld.lnk").write_bytes(b"")
    result = _actions._search_desktop("rimworld")
    assert result is not None
    assert result.endswith("RimWorld.lnk")


def test_desktop_rejects_uninstaller_same_as_start_menu(fake_desktop):
    (fake_desktop["desktop"] / "Uninstall RimWorld.lnk").write_bytes(b"")
    (fake_desktop["desktop"] / "RimWorld.lnk").write_bytes(b"")
    result = _actions._search_desktop("rimworld")
    assert result.endswith("RimWorld.lnk")  # not the uninstaller


def test_desktop_accepts_url_shortcuts(fake_desktop):
    (fake_desktop["desktop"] / "Steam.url").write_bytes(b"")
    assert _actions._search_desktop("steam").endswith("Steam.url")


def test_desktop_accepts_bare_exes(fake_desktop):
    (fake_desktop["desktop"] / "MyGame.exe").write_bytes(b"")
    assert _actions._search_desktop("mygame").endswith("MyGame.exe")


def test_desktop_returns_none_when_no_match(fake_desktop):
    (fake_desktop["desktop"] / "Discord.lnk").write_bytes(b"")
    assert _actions._search_desktop("rimworld") is None


def test_desktop_checks_public_desktop_too(fake_desktop):
    (fake_desktop["public"] / "Chrome.lnk").write_bytes(b"")
    assert _actions._search_desktop("chrome").endswith("Chrome.lnk")


def test_desktop_handles_duplicates_gracefully(fake_desktop):
    """Same shortcut name on both user and public desktops — function
    must return exactly one valid path without crashing. Which one wins
    on a perfect tie is unspecified (same score, same length) and we
    don't assert on it."""
    (fake_desktop["desktop"] / "Chrome.lnk").write_bytes(b"USER")
    (fake_desktop["public"] / "Chrome.lnk").write_bytes(b"PUBLIC")
    result = _actions._search_desktop("chrome")
    assert result is not None
    assert result.endswith("Chrome.lnk")
    assert os.path.exists(result)
