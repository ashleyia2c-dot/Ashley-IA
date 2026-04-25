"""Tests for the news feed module (v0.13.3).

El news feed reemplaza el comportamiento anterior de discovery (que
insertaba descubrimientos directo al chat). Ahora los items van aquí,
el user los ve cuando pulsa 📰 del header.
"""

import json
from unittest import mock

import pytest

from reflex_companion import news


# ══════════════════════════════════════════════════════════════════════
#  CRUD básico
# ══════════════════════════════════════════════════════════════════════

def test_load_empty_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    assert news.load_news() == []


def test_add_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    item = news.add_news_item("Title X", "Body here", "song")
    assert item["id"].startswith("n-")
    assert item["title"] == "Title X"
    assert item["body"] == "Body here"
    assert item["category"] == "song"
    assert item["read"] is False

    loaded = news.load_news()
    assert len(loaded) == 1
    assert loaded[0]["title"] == "Title X"


def test_add_requires_title_or_body(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    with pytest.raises(ValueError):
        news.add_news_item("", "", "other")


def test_add_derives_title_from_body_if_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    item = news.add_news_item("", "Nuevo álbum de Artista. Segunda frase.", "song")
    assert "Nuevo álbum" in item["title"]


def test_most_recent_first(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    news.add_news_item("Oldest", "body1", "song")
    news.add_news_item("Newest", "body2", "article")
    loaded = news.load_news()
    assert loaded[0]["title"] == "Newest"
    assert loaded[1]["title"] == "Oldest"


def test_cap_at_max_items(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    # Reducir el cap para test más rápido
    monkeypatch.setattr(news, "MAX_NEWS_ITEMS", 3)
    for i in range(5):
        news.add_news_item(f"Item {i}", f"body {i}", "other")
    loaded = news.load_news()
    assert len(loaded) == 3
    # Los más nuevos se quedan
    assert loaded[0]["title"] == "Item 4"
    assert loaded[1]["title"] == "Item 3"
    assert loaded[2]["title"] == "Item 2"


def test_mark_all_read(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    news.add_news_item("X", "b", "song")
    news.add_news_item("Y", "b", "song")
    assert news.unread_count() == 2
    news.mark_all_read()
    assert news.unread_count() == 0
    for i in news.load_news():
        assert i["read"] is True


def test_delete_item(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    news.add_news_item("Keep", "b", "song")
    target = news.add_news_item("Delete", "b", "song")
    assert news.delete_item(target["id"]) is True
    assert len(news.load_news()) == 1
    assert news.load_news()[0]["title"] == "Keep"


def test_delete_item_nonexistent_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    news.add_news_item("X", "b", "song")
    assert news.delete_item("n-nonexistent") is False


def test_clear_all(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "NEWS_FILE", str(tmp_path / "news.json"))
    news.add_news_item("X", "b", "song")
    news.add_news_item("Y", "b", "song")
    news.clear_all()
    assert news.load_news() == []


def test_corrupted_file_returns_empty(tmp_path, monkeypatch):
    """Si news.json no es JSON válido, devolver [] no crashear."""
    f = tmp_path / "news.json"
    f.write_text("{this is not valid json")
    monkeypatch.setattr(news, "NEWS_FILE", str(f))
    assert news.load_news() == []


def test_non_list_json_returns_empty(tmp_path, monkeypatch):
    """Si alguien cambia el fichero manualmente a un dict, no confiamos."""
    f = tmp_path / "news.json"
    f.write_text(json.dumps({"not": "a list"}))
    monkeypatch.setattr(news, "NEWS_FILE", str(f))
    assert news.load_news() == []


# ══════════════════════════════════════════════════════════════════════
#  parse_ashley_discovery
# ══════════════════════════════════════════════════════════════════════

def test_parse_empty_returns_none():
    assert news.parse_ashley_discovery("") is None
    assert news.parse_ashley_discovery(None) is None


def test_parse_too_short_returns_none():
    assert news.parse_ashley_discovery("hola") is None


def test_parse_splits_title_from_first_sentence():
    raw = "Nuevo álbum de Fulano. Tiene 10 tracks y la crítica lo adora."
    parsed = news.parse_ashley_discovery(raw)
    assert parsed is not None
    assert "Nuevo álbum de Fulano" in parsed["title"]
    assert "10 tracks" in parsed["body"]


def test_parse_detects_song_category():
    parsed = news.parse_ashley_discovery("Salió una canción brutal hoy.")
    assert parsed["category"] == "song"


def test_parse_detects_trailer_category():
    parsed = news.parse_ashley_discovery("Llegó el tráiler de la peli esta.")
    assert parsed["category"] == "trailer"


def test_parse_detects_game_category():
    parsed = news.parse_ashley_discovery("Nueva update de RimWorld que arregla X.")
    assert parsed["category"] == "game"


def test_parse_detects_tech_category():
    parsed = news.parse_ashley_discovery("Nuevo framework de Python llamado X.")
    assert parsed["category"] == "tech"


def test_parse_defaults_to_other():
    parsed = news.parse_ashley_discovery("Algo genérico sin categoría clara aquí.")
    assert parsed["category"] == "other"


def test_parse_title_capped_at_200():
    huge = "x" * 500 + "."
    parsed = news.parse_ashley_discovery(huge)
    assert len(parsed["title"]) <= 200
