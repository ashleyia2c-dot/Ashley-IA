"""
parsing.py — Tag parsing helpers for the Ashley companion app.

Extracted from reflex_companion.py.  Contains standalone functions for
extracting [mood:X] and [action:X:Y] tags from Ashley's responses, plus
the display cleaner that strips those tags before showing text to the user.

Also defines the constant tuples/sets used by the fallback action detection
logic in ``State._finalize_response``.
"""

import re

from .reminders import parse_remind_params


# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

# Acciones "seguras" que se ejecutan SIEMPRE, sin necesidad del toggle Acciones.
# Son operaciones de datos, no de control del sistema. No requieren confirmación.
_SAFE_ACTIONS = {"save_taste", "remind", "add_important", "done_important"}

# Verbos del usuario que indican un pedido de acción (para fallback)
_USER_ACTION_VERBS = (
    # Spanish
    "abre ", "abre el ", "abre la ", "abre los ", "abre las ",
    "cierra ", "cierra el ", "cierra la ", "cierra los ", "cierra las ",
    "pon ", "pon música", "ponme ", "reproduce ", "reproducir ",
    "busca ", "buscar ", "googlea ",
    "sube el volumen", "baja el volumen", "silencia", "volumen",
    "toma una captura", "screenshot", "captura de pantalla",
    "escribe ", "escríbeme ",
    "abre paint", "abre steam", "abre chrome", "abre discord",
    # English
    "open ", "open the ", "close ", "close the ",
    "play ", "play music", "search ", "google ",
    "raise volume", "lower volume", "mute", "volume up", "volume down",
    "take a screenshot", "capture screen",
    "type ", "write ",
    "launch ", "start ",
)

# Pistas de que Ashley describe la acción en texto (sin tag)
_ASHLEY_FAKE_HINTS = (
    "reproduciendo", "abriendo", "buscando", "cerrando",
    "voy a poner", "pongo ahora", "abriré", "iniciando",
    "cierro", "cerrado", "abro", "lanzando", "ejecutando",
    "borrado", "borrada", "eliminado",
)


# ─────────────────────────────────────────────
#  Standalone parsing functions
# ─────────────────────────────────────────────

def clean_display(text: str) -> str:
    """Elimina tags [mood:...], [action:...] y [affection:...] del texto para mostrarlo al usuario."""
    # Elimina tags completos en cualquier posición (case insensitive por seguridad)
    text = re.sub(r'\[(?:mood|action|affection):[^\]]*\]', '', text, flags=re.IGNORECASE)
    # Elimina tag parcial al final (durante streaming)
    text = re.sub(r'\[(?:mood|action|affection)[^\]]*$', '', text, flags=re.IGNORECASE)
    # Captura variantes extra: a veces el LLM añade espacios o mayúsculas
    text = re.sub(r'\[\s*affection\s*:\s*[^\]]*\]', '', text, flags=re.IGNORECASE)
    # Elimina "undefined" suelto (renderizado roto de Reflex)
    text = re.sub(r'\bundefined\b', '', text)
    # Elimina líneas vacías consecutivas que quedan tras limpiar tags
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_mood(text: str) -> tuple[str, str]:
    """
    Busca [mood:xxx] en el texto.
    Devuelve (texto_limpio, mood_detectado).
    Si no hay tag devuelve (texto_original, "default").

    Regex tolerante: acepta espacios, case insensitive, y elimina TODAS las
    ocurrencias (no sólo la primera) para no dejar tags duplicados en el texto.
    """
    matches = re.findall(r'\[\s*mood\s*:\s*(\w+)\s*\]', text, flags=re.IGNORECASE)
    detected = matches[0].lower() if matches else "default"
    clean = re.sub(r'\[\s*mood\s*:[^\]]*\]', '', text, flags=re.IGNORECASE).strip()
    return clean, detected


def extract_affection(text: str) -> tuple[str, int]:
    """
    Busca [affection:+N] o [affection:-N] en el texto.
    Devuelve (texto_limpio, delta). Delta se limita a [-3, +3].
    Si no hay tag devuelve (texto_original, 0).

    Regex tolerante: acepta espacios, case insensitive, y elimina TODAS las
    ocurrencias (no sólo la primera). Sin esto, si Ashley escribe el tag dos
    veces o con espacios raros, se quedaba visible en el bubble final.
    """
    matches = re.findall(r'\[\s*affection\s*:\s*([+-]?\d+)\s*\]', text, flags=re.IGNORECASE)
    delta = max(-3, min(3, int(matches[0]))) if matches else 0
    clean = re.sub(r'\[\s*affection\s*:[^\]]*\]', '', text, flags=re.IGNORECASE).strip()
    return clean, delta


def extract_action(text: str) -> tuple[str, dict | None]:
    """
    Busca [action:tipo:...] en el texto.
    Devuelve (texto_limpio, {type, params} | None).

    Parsing inteligente por tipo de acción:
    - type_text / search_web / open_url / play_music:
        todo lo que sigue al primer ":" es un único parámetro (puede contener ":")
    - type_in:
        segundo campo = título de ventana, resto = texto completo
    - resto (open_app, volume, hotkey, press_key, focus_window...):
        split normal por ":"

    NOTE: This standalone version does NOT include a "description" key.
    The State method adds that after calling this function.
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

    # Parseo de params según tipo
    TEXT_ACTIONS = ("type_text", "search_web", "open_url", "play_music")
    if a_type in TEXT_ACTIONS:
        # El texto completo es un único param (puede tener ":" dentro)
        params = [rest] if rest else []
    elif a_type == "type_in":
        # type_in:titulo_ventana:texto a escribir (texto puede tener ":")
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    elif a_type == "write_to_app":
        # write_to_app:nombre_app:contenido (contenido puede tener ":")
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    elif a_type == "remind":
        # remind:YYYY-MM-DDTHH:MM:SS:texto — datetime tiene ":" propios
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
        # Split estándar: volume:set:50, hotkey:ctrl:c, etc.
        params = rest.split(":") if rest else []

    clean = text.replace(full_tag, "").strip()
    return clean, {"type": a_type, "params": params}
