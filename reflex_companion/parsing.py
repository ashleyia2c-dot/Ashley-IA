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
    """Elimina tags [mood:...], [action:...] y [affection:...] del texto para mostrarlo al usuario.

    Defensivo contra None, ints, objetos — si algún path llama con valor
    no-string, no crasheamos (silently coerce). None → "".
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return ""
    # Elimina tags completos en cualquier posición (case insensitive por seguridad)
    text = re.sub(r'\[(?:mood|action|affection):[^\]]*\]', '', text, flags=re.IGNORECASE)
    # Elimina tag parcial al final (durante streaming)
    text = re.sub(r'\[(?:mood|action|affection)[^\]]*$', '', text, flags=re.IGNORECASE)
    # Captura variantes extra: a veces el LLM añade espacios o mayúsculas
    text = re.sub(r'\[\s*affection\s*:\s*[^\]]*\]', '', text, flags=re.IGNORECASE)
    # Elimina "undefined" suelto (renderizado roto de Reflex) — cubre casos
    # con variaciones de capitalización y también cuando aparece pegado a
    # puntuación sin whitespace (ej. "frase.undefined").
    text = re.sub(r'(?:\s|^)undefined(?:\s|$|[\.\!\?\,\;])', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bundefined\b', '', text, flags=re.IGNORECASE)
    # Caso adicional: el LLM (o algún data-binding roto) genera un code
    # block markdown que contiene "undefined". Se renderiza como
    # rectángulo gris feo en el chat. Regla agresiva: CUALQUIER code
    # block (fenced o inline) que contenga la palabra "undefined" en
    # cualquier parte, se elimina entero. Mejor perder texto inocente
    # tipo "undefined behavior in C" que dejar el rectángulo feo.
    text = re.sub(r'```[^`]*?undefined[^`]*?```', '', text,
                  flags=re.IGNORECASE | re.DOTALL)
    # Code block sin cerrar (truncado al final o al doble salto)
    text = re.sub(r'```[^`]*?undefined[^`]*?(?:\n\n|$)', '\n\n', text,
                  flags=re.IGNORECASE | re.DOTALL)
    # Inline backtick que contenga undefined
    text = re.sub(r'`[^`]*?undefined[^`]*?`', '', text,
                  flags=re.IGNORECASE)
    # Code blocks vacíos (sin contenido o solo whitespace) — pueden
    # quedar tras eliminar undefined o por otros artefactos del LLM.
    text = re.sub(r'```[a-zA-Z]*[ \t]*\n?\s*\n?[ \t]*```', '', text,
                  flags=re.DOTALL)
    # ── Backticks SIN CERRAR al final del string ────────────────────
    # Patrón real visto en producción: el LLM emitía "```undefined```"
    # y la limpieza dejaba solo "```" suelto al final. Markdown lo
    # interpreta como code block abierto y renderiza "undefined" como
    # contenido fallback. Eliminamos cualquier ``` (con o sin
    # language hint) que quede colgando al final del texto sin pareja.
    # IMPORTANTE: este pase va ANTES de la regla de inline backticks
    # vacíos, porque si no esa regla rompe el grupo de 3 en pares y
    # deja un backtick suelto colgando.
    text = re.sub(r'\n*```[a-zA-Z]*[ \t]*\n*\s*$', '', text)
    # También al inicio si quedó solo (raro pero posible)
    text = re.sub(r'^\s*```[a-zA-Z]*[ \t]*\n*', '', text)
    # Inline backticks vacíos — pero SOLO si NO son parte de un fenced
    # code block (```). Lookbehind/lookahead lo limita a backticks
    # individuales rodeados por no-backtick, así no rompe ```js code```.
    text = re.sub(r'(?<!`)`\s*`(?!`)', '', text)
    # Backtick único suelto al final (residuo de cleanup previo).
    # Igual: solo si el carácter anterior no es otro backtick.
    text = re.sub(r'\n*[ \t]*(?<!`)`\s*$', '', text)
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


def extract_all_actions(text: str) -> tuple[str, list[dict]]:
    """Extrae TODAS las acciones del texto en orden de aparición.

    Cuando el user pide dos cosas en un mensaje ("pon X y cierra Y"),
    Ashley suele emitir dos tags consecutivos. Antes el sistema solo
    procesaba el primero — la segunda acción se quedaba sin ejecutar
    pero la descripción verbal daba a entender que sí. Ahora las
    recogemos todas.
    """
    actions: list[dict] = []
    remaining_text = text
    while True:
        stripped, action = extract_action(remaining_text)
        if action is None:
            break
        actions.append(action)
        remaining_text = stripped
    return remaining_text, actions


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
