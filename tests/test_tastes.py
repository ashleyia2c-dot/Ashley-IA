"""
Tests for reflex_companion.tastes — taste persistence and discovery timing.
"""

import json
import time

import pytest

from reflex_companion import tastes


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_paths(tmp_path, monkeypatch):
    """Redirect TASTES_FILE and DISCOVERY_FILE to tmp_path for every test.

    tastes.py uses ``from .config import TASTES_FILE`` so the name is bound
    locally inside the tastes module — we must patch *there*.
    """
    monkeypatch.setattr(tastes, "TASTES_FILE", str(tmp_path / "gustos.json"))
    monkeypatch.setattr(tastes, "DISCOVERY_FILE", str(tmp_path / "discovery.json"))


# ── load_tastes ──────────────────────────────────────────────────────────────


def test_load_tastes_empty_file_returns_empty_list(tmp_path):
    """When the file does not exist, load_tastes returns []."""
    assert tastes.load_tastes() == []


def test_load_tastes_nonexistent_file_returns_empty_list():
    """Explicit check: no file at all -> []."""
    assert tastes.load_tastes() == []


# ── add_taste ────────────────────────────────────────────────────────────────


def test_add_taste_creates_valid_entry():
    """add_taste should create an entry with id, categoria, valor, created_at."""
    result = tastes.add_taste("musica", "rock")
    assert "rock" in result  # confirmation message

    loaded = tastes.load_tastes()
    assert len(loaded) == 1

    entry = loaded[0]
    assert "id" in entry
    assert entry["categoria"] == "musica"
    assert entry["valor"] == "rock"
    assert "created_at" in entry


def test_add_taste_strips_and_lowercases_categoria():
    """categoria is lowered and stripped; valor is stripped."""
    tastes.add_taste("  MuSiCa  ", "  jazz  ")
    entry = tastes.load_tastes()[0]
    assert entry["categoria"] == "musica"
    assert entry["valor"] == "jazz"


# ── roundtrip ────────────────────────────────────────────────────────────────


def test_add_and_load_roundtrip():
    """Add several tastes, then load and verify them all."""
    tastes.add_taste("musica", "rock")
    tastes.add_taste("entretenimiento", "anime")
    tastes.add_taste("musica", "jazz")

    loaded = tastes.load_tastes()
    assert len(loaded) == 3
    cats = [t["categoria"] for t in loaded]
    assert cats.count("musica") == 2
    assert cats.count("entretenimiento") == 1


# ── delete_taste ─────────────────────────────────────────────────────────────


def test_delete_taste_removes_correct_entry():
    """delete_taste with a valid id removes that entry and returns True."""
    tastes.add_taste("musica", "rock")
    tastes.add_taste("musica", "jazz")

    entries = tastes.load_tastes()
    target_id = entries[0]["id"]

    assert tastes.delete_taste(target_id) is True
    remaining = tastes.load_tastes()
    assert len(remaining) == 1
    assert remaining[0]["valor"] == "jazz"


def test_delete_taste_nonexistent_returns_false():
    """delete_taste with an id that doesn't exist returns False."""
    tastes.add_taste("musica", "rock")
    assert tastes.delete_taste("nonexistent") is False
    assert len(tastes.load_tastes()) == 1  # nothing removed


# ── format_tastes_for_prompt ─────────────────────────────────────────────────


def test_format_tastes_empty_list_returns_empty_string():
    """format_tastes_for_prompt([]) -> ''."""
    assert tastes.format_tastes_for_prompt([]) == ""


def test_format_tastes_groups_by_category():
    """Multiple categories are grouped and formatted correctly."""
    items = [
        {"categoria": "musica", "valor": "rock"},
        {"categoria": "musica", "valor": "jazz"},
        {"categoria": "entretenimiento", "valor": "anime"},
    ]
    result = tastes.format_tastes_for_prompt(items)

    # Should contain both categories
    assert "musica" in result
    assert "entretenimiento" in result

    # musica values should be comma-separated on one line
    for line in result.splitlines():
        if line.strip().startswith("musica"):
            assert "rock" in line
            assert "jazz" in line

    # entretenimiento should have anime
    for line in result.splitlines():
        if line.strip().startswith("entretenimiento"):
            assert "anime" in line


# ── should_run_discovery / update_discovery_time ─────────────────────────────


def test_should_run_discovery_true_on_first_run():
    """With no discovery file, should_run_discovery returns True."""
    assert tastes.should_run_discovery() is True


def test_should_run_discovery_false_within_4_hours():
    """Right after update_discovery_time, should_run_discovery returns False."""
    tastes.update_discovery_time()
    assert tastes.should_run_discovery() is False


def test_should_run_discovery_true_after_tiny_delay():
    """With min_hours very small, should_run_discovery returns True quickly."""
    tastes.update_discovery_time()
    # min_hours=0.001 == 3.6 seconds; sleep long enough to exceed it
    time.sleep(0.005)
    # Use an even smaller threshold so 5 ms of elapsed time is enough
    assert tastes.should_run_discovery(min_hours=0.0000001) is True
