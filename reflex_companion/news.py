"""
news.py — Feed de noticias/descubrimientos de Ashley (v0.13.3).

Hasta v0.13.2 Ashley metía sus discoveries (canciones, tráilers, noticias
basadas en los gustos del user) directo en el chat. Problema: rompe la
conversación en marcha — el user dice "me voy a dormir" y al volver ve
un tráiler de random antes de su propia charla.

Desde v0.13.3 hay un feed separado: Ashley sigue descubriendo cosas en
background, pero las guarda aquí en news_ashley.json. El user accede
cuando quiere via el pill 📰 del header. El chat queda limpio.

Formato de un item:
    {
        "id": "n-abc123",           # uuid corto
        "title": "...",             # título/resumen corto (1 frase)
        "body": "...",              # texto de Ashley explicando
        "category": "song"|"article"|"trailer"|"game"|"tech"|"other",
        "source_url": "...",        # opcional, enlace si Ashley lo dio
        "created_at": "ISO timestamp",
        "read": False,              # marca de leído
    }

Cap: máximo 50 items. Al pasar, descartamos los más viejos primero.
"""

import uuid
from datetime import datetime
from typing import Optional

from .config import NEWS_FILE
from .memory import load_json, save_json


MAX_NEWS_ITEMS = 50


def load_news() -> list[dict]:
    """Devuelve la lista de items, ordenada del MÁS NUEVO al más viejo."""
    data = load_json(NEWS_FILE, [])
    if not isinstance(data, list):
        return []
    # Normalizar + orden por created_at descendente
    out: list[dict] = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        out.append({
            "id": str(raw.get("id", "")) or f"n-{uuid.uuid4().hex[:8]}",
            "title": str(raw.get("title", "")),
            "body": str(raw.get("body", "")),
            "category": str(raw.get("category", "other")),
            "source_url": str(raw.get("source_url", "")),
            "created_at": str(raw.get("created_at", "")),
            "read": bool(raw.get("read", False)),
        })
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return out


def add_news_item(
    title: str,
    body: str,
    category: str = "other",
    source_url: str = "",
) -> dict:
    """Añade un nuevo descubrimiento al feed. Devuelve el item creado.

    El body puede traer `[mood:...]` o `[action:...]` dentro — NO los
    parseamos aquí, es responsabilidad del caller limpiarlos antes.
    """
    title = (title or "").strip()[:200]
    body = (body or "").strip()[:2000]
    if not title and not body:
        raise ValueError("news item needs title or body")
    if not title:
        # Fallback: primera frase del body como título
        title = body.split(".")[0][:80] if body else "Untitled"

    item = {
        "id": f"n-{uuid.uuid4().hex[:8]}",
        "title": title,
        "body": body,
        "category": (category or "other").lower().strip(),
        "source_url": (source_url or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "read": False,
    }

    items = load_news()
    items.insert(0, item)  # prepend (ya vienen ordenados descending)
    # Cap al máximo — descarta los más viejos
    if len(items) > MAX_NEWS_ITEMS:
        items = items[:MAX_NEWS_ITEMS]
    save_json(NEWS_FILE, items)
    return item


def mark_all_read() -> None:
    """Marca todos los items como leídos. Se dispara al abrir el panel."""
    items = load_news()
    changed = False
    for it in items:
        if not it.get("read"):
            it["read"] = True
            changed = True
    if changed:
        save_json(NEWS_FILE, items)


def delete_item(item_id: str) -> bool:
    """Elimina un item. Devuelve True si algo cambió."""
    items = load_news()
    new_items = [i for i in items if i.get("id") != item_id]
    if len(new_items) == len(items):
        return False
    save_json(NEWS_FILE, new_items)
    return True


def clear_all() -> None:
    """Vacía el feed completo (acción del user)."""
    save_json(NEWS_FILE, [])


def unread_count() -> int:
    return sum(1 for i in load_news() if not i.get("read", False))


# ─────────────────────────────────────────────
#  Parser — extrae title+body+category de la respuesta raw de Ashley
# ─────────────────────────────────────────────

def parse_ashley_discovery(raw_text: str) -> Optional[dict]:
    """Dado el texto crudo que Ashley produjo en un discovery, intenta
    extraer (title, body, category). Heurística simple:

      • La primera oración = title (corta a 200 chars).
      • El resto = body.
      • Si el body contiene 'canción'/'song' → category='song', etc.

    Devuelve None si el texto es demasiado corto para ser útil
    (probablemente Ashley dijo '[mood:default]' sin nada).
    """
    if not raw_text:
        return None
    text = raw_text.strip()
    if len(text) < 15:
        return None

    # Split por primera oración (. ! ?)
    import re
    first_sentence_end = None
    for m in re.finditer(r"[\.!?]\s", text + " "):
        first_sentence_end = m.end()
        break

    if first_sentence_end and first_sentence_end < len(text):
        title = text[:first_sentence_end].strip(" .!?")[:200]
        body = text[first_sentence_end:].strip()
    else:
        # Texto corto sin puntuación clara → usarlo entero como title
        title = text[:200]
        body = ""

    # Heurística de categoría (ES/EN/FR)
    low = text.lower()
    category = "other"
    if any(k in low for k in ("canción", "canciones", "song", "track", "álbum", "chanson")):
        category = "song"
    elif any(k in low for k in ("tráiler", "trailer", "bande-annonce", "película", "movie", "film")):
        category = "trailer"
    elif any(k in low for k in ("artículo", "article", "blog", "post", "noticia", "news", "actu")):
        category = "article"
    elif any(k in low for k in ("juego", "game", "jeu", "rimworld", "steam", "update", "patch")):
        category = "game"
    elif any(k in low for k in ("librería", "library", "framework", "python", "javascript",
                                "typescript", "react", "api", "repo", "github")):
        category = "tech"

    return {"title": title, "body": body, "category": category}
