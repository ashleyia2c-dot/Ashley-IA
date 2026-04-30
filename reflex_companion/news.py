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

import re
import uuid
from datetime import datetime
from typing import Optional

from .config import NEWS_FILE
from .memory import load_json, save_json


MAX_NEWS_ITEMS = 50

# Cuántos items recientes mirar para dedup. 8 cubre los últimos ~1-2 días
# de actividad de Ashley (descubre cada hora cuando está en sesión).
DEDUP_LOOKBACK = 8

# Mínimo de palabras "específicas" compartidas para considerar dos items
# duplicados. "Específico" = numérico (versión, año, episodio) o ≥6 chars
# (nombre propio, marca, término técnico). Stopwords filtradas previamente.
#
# Calibrado contra casos reales:
#   • "Parche League 26.8 PsyOps Vladimir" vs "patch 26.8 skins PsyOps"
#     → comparten {league, psyops} → 2 ✓ DEDUP
#   • "Single de Bad Bunny" vs "Álbum de Rosalía" → comparten {single}
#     → 1 ✗ no dedup ✓
DEDUP_MIN_SHARED_SPECIFIC = 2

# Mínimo de palabras significativas TOTAL (no solo específicas) para
# considerar dedup. Cubre el caso donde dos items comparten muchas
# palabras comunes (4+) sin necesariamente compartir nombres propios.
DEDUP_MIN_SHARED_TOTAL = 4

# Stopwords que NO sirven para comparar similitud entre items. Son
# palabras frecuentes en cualquier texto sobre cualquier tema. Sin
# filtrarlas, dos items completamente distintos darían "similitud alta"
# solo por compartir "para", "como", "este", etc.
_STOPWORDS = frozenset({
    # Español
    "para", "como", "esto", "esta", "este", "pero", "mientras", "cuando",
    "donde", "porque", "tanto", "sobre", "entre", "hasta", "desde", "hace",
    "haya", "tienen", "tiene", "pueden", "puede", "están", "sigue", "siguen",
    "muy", "poco", "mucho", "todo", "toda", "todos", "todas", "otro", "otra",
    "ahora", "antes", "después", "luego", "ayer", "hoy", "tarde", "noche",
    "boss", "jefe", "capullo", "ashley",  # roles/nombres recurrentes
    # Inglés
    "this", "that", "with", "from", "have", "been", "were", "they", "them",
    "their", "would", "could", "should", "about", "into", "over", "what",
    "where", "when", "while", "still", "just", "very", "more", "most", "some",
    # Acción markers que Ashley pone al inicio
    "asoma", "acurruca", "levanta", "rozando", "sonriendo", "curiosa",
    "monitor", "hombro", "vista", "brazo", "mira", "oye", "pillé", "busqué",
})


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
) -> Optional[dict]:
    """Añade un nuevo descubrimiento al feed. Devuelve el item creado,
    o None si fue rechazado por duplicado.

    v0.13.11: añadidos dos safeguards adicionales:
      • Strip de tags residuales (`[mood:...]`, `[affection:...]`, etc.)
        que pudieran haberse colado al title/body. La función `clean()`
        de parsing.py los quita upstream, pero defense-in-depth.
      • Dedup contra los últimos N items: si el nuevo item es muy
        similar a uno reciente (Jaccard ≥0.55 sobre palabras
        significativas) lo rechazamos. Antes Ashley repetía noticias
        del mismo evento (ej: 'patch League 26.8') varias veces.
    """
    # Limpiar primero — los tags pueden corromper el title/body antes
    # incluso de aplicar el cap (un [affection:+1] puede ocupar 16
    # chars del title y luego mostrarse al user).
    title_clean = _strip_residual_tags((title or "").strip())
    body_clean  = _strip_residual_tags((body or "").strip())

    # v0.14.5 — fix de "mensajes cortados". Antes: title[:200] hacía
    # un slice raw que cortaba mid-palabra mid-frase ("...sale hoy
    # mismo para"). Ahora usamos _smart_truncate que respeta la
    # boundary de palabras y mueve el overflow al body, así nada
    # se pierde. Plus subimos el cap de 200 → 320 para acomodar
    # primeras frases largas (parse_ashley_discovery ya genera títulos
    # hasta 280, antes el [:200] cortaba lo que ya estaba OK).
    title, title_overflow = _smart_truncate(title_clean, 320)
    if title_overflow:
        body_clean = (title_overflow + " " + body_clean).strip()
    body = body_clean[:2000]
    if not title and not body:
        raise ValueError("news item needs title or body")
    if not title:
        # Fallback: primera frase del body como título
        title = body.split(".")[0][:80] if body else "Untitled"

    items = load_news()

    # Dedup: si esto es una repetición de algo reciente, NO añadir.
    # Devolvemos None — el caller ya tiene try/except y simplemente
    # no se actualiza el feed visible. Mejor un feed corto que un
    # feed con 4 items hablando del mismo patch de League.
    if _is_duplicate_of_recent(title, body, items):
        return None

    item = {
        "id": f"n-{uuid.uuid4().hex[:8]}",
        "title": title,
        "body": body,
        "category": (category or "other").lower().strip(),
        "source_url": (source_url or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "read": False,
    }

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

def _smart_truncate(text: str, max_len: int) -> tuple[str, str]:
    """Trunca `text` a `max_len` SIN cortar a media palabra.
    Devuelve (truncated, leftover). Si el texto cabe entero,
    leftover es ''.

    v0.13.7: antes cortaba a media palabra ('...y e').
    v0.13.10: además, si la última palabra es muy corta (≤3 chars),
    también la mueve al leftover. Sin esto el corte se ve raro
    aunque técnicamente sea en boundary de palabra: '...PsyOps
    Vladimir y e' → la 'e' es probablemente el inicio de algo
    como 'extras' que el truncate cortó. Mejor terminar limpio
    en 'PsyOps Vladimir' aunque perdamos una conjunción.
    """
    if len(text) <= max_len:
        return text, ""
    truncated = text[:max_len]
    leftover = text[max_len:]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.5:
        leftover = text[last_space:].lstrip()
        truncated = truncated[:last_space]

    # Protección anti-"hueso colgando": si la última palabra del
    # truncated tiene ≤3 chars, también la movemos al leftover.
    # Excepción: números (años, versiones) sí valen aunque sean cortos.
    truncated_stripped = truncated.rstrip()
    last_space2 = truncated_stripped.rfind(' ')
    if last_space2 > max_len * 0.4:
        last_word = truncated_stripped[last_space2 + 1:]
        if len(last_word) <= 3 and not last_word.isdigit():
            leftover = (last_word + " " + leftover).strip()
            truncated = truncated_stripped[:last_space2]

    return truncated.rstrip(' .!?,;:—–-,'), leftover


def _strip_residual_tags(text: str) -> str:
    """Quita cualquier `[mood:..]`, `[action:..]`, `[affection:..]` que
    se haya colado al body/title. La función `clean()` de parsing.py
    los quita upstream, pero por defensa en profundidad limpiamos otra
    vez aquí — si por algún edge case (versión vieja, parser fallido,
    streaming truncado) un tag llega a este punto, no lo guardamos al
    feed. Mejor perder un tag que dejarlo visible al user."""
    if not text:
        return text
    text = re.sub(r'\[\s*(?:mood|action|affection)\s*:[^\]]*\]', '',
                  text, flags=re.IGNORECASE)
    # Tags partidos por streaming (ej. '[affection:' al final sin cerrar)
    text = re.sub(r'\[\s*(?:mood|action|affection)\s*:[^\]]*$', '',
                  text, flags=re.IGNORECASE)
    return text.strip()


def _significant_words(text: str) -> set[str]:
    """Devuelve el set de palabras 'significativas' del texto:
    minúsculas, sin acciones `*...*`, ≥4 chars, no stopwords.

    Usado para detectar duplicados entre items de news. La idea: dos
    items que hablan del mismo tema comparten muchas palabras
    significativas (e.g. 'league', 'patch', 'skins'); items distintos
    aunque del mismo género (e.g. dos canciones distintas) no.
    """
    if not text:
        return set()
    # Quita acciones embebidas tipo *se asoma curiosa*
    cleaned = re.sub(r'\*[^*]+\*', ' ', text)
    # Lowercase + extrae palabras alfanuméricas de 4+ chars
    cleaned = cleaned.lower()
    words = re.findall(r'[a-záéíóúüñ0-9]{4,}', cleaned)
    return {w for w in words if w not in _STOPWORDS}


def _specific_words(words: set[str]) -> set[str]:
    """Filtro adicional sobre `_significant_words`: nos quedamos solo con
    palabras 'específicas' (numéricas o ≥6 chars). Esas son las que
    delatan que dos items hablan del mismo evento concreto: nombres
    propios (League, PsyOps, Vladimir), versiones (26.8, 14), términos
    técnicos largos. Palabras genéricas de 4-5 chars como 'skins',
    'songs', 'pelis' no cuentan — pueden coincidir entre items distintos
    del mismo género."""
    return {w for w in words
            if any(c.isdigit() for c in w) or len(w) >= 6}


def _is_duplicate_of_recent(title: str, body: str,
                             recent_items: list[dict]) -> bool:
    """¿El nuevo item es muy similar a alguno de los últimos N? Si sí,
    es probablemente repetición y no merece su propia entrada en el feed.

    Estrategia (después de varios intentos con Jaccard puro que
    fallaba en casos reales): considerar duplicado si comparte CON UN
    ITEM RECIENTE:
      • ≥4 palabras significativas TOTAL, O
      • ≥2 palabras 'específicas' (numéricas o ≥6 chars).

    El segundo criterio captura casos donde Ashley re-descubre el
    mismo evento usando vocabulario distinto: 'Parche League 26.8'
    vs 'patch 26.8 skins' comparten {league, psyops} pero solo 3
    palabras totales (Jaccard bajo). El criterio de "específicas"
    cuenta esos nombres propios.
    """
    new_words = _significant_words(f"{title} {body}")
    if len(new_words) < 3:
        # Texto demasiado corto para comparar fiable — dejarlo pasar
        return False

    new_specific = _specific_words(new_words)

    for item in recent_items[:DEDUP_LOOKBACK]:
        old_text = f"{item.get('title', '')} {item.get('body', '')}"
        old_words = _significant_words(old_text)
        if len(old_words) < 3:
            continue
        old_specific = _specific_words(old_words)

        shared_total = len(new_words & old_words)
        shared_specific = len(new_specific & old_specific)

        if (shared_total >= DEDUP_MIN_SHARED_TOTAL or
                shared_specific >= DEDUP_MIN_SHARED_SPECIFIC):
            return True

    return False


def parse_ashley_discovery(raw_text: str) -> Optional[dict]:
    """Dado el texto crudo que Ashley produjo en un discovery, intenta
    extraer (title, body, category). Heurística simple:

      • La primera oración = title (corte sin partir palabras, ~280 chars).
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

    import re
    first_sentence_end = None
    for m in re.finditer(r"[\.!?]\s", text + " "):
        first_sentence_end = m.end()
        break

    if first_sentence_end and first_sentence_end < len(text) and first_sentence_end < 320:
        # Primera oración razonable → title=oración, body=resto
        raw_title = text[:first_sentence_end].strip(" .!?")
        title, spillover = _smart_truncate(raw_title, 280)
        rest = text[first_sentence_end:].strip()
        body = (spillover + " " + rest).strip() if spillover else rest
    else:
        # Sin puntuación o primera oración demasiado larga → cortar
        # por palabra completa al rededor de 200 chars; resto al body.
        title, body = _smart_truncate(text, 200)

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
