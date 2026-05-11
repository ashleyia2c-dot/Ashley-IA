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
_SAFE_ACTIONS = {
    "save_taste", "remind", "add_important", "done_important", "save_date",
    "save_goal", "check_in_goal", "complete_goal",
}

# v0.19.31 — Acciones TERMINALES (auto-completas). Una vez ejecutadas, NO
# tiene sentido disparar la "agentic continuation" porque no hay plan que
# continuar.
#
# Bug observado v0.19.30 (screenshot en producción): Ashley emitió
# play_music, sonó la canción, el agentic-continuation disparó un follow-up
# y Ashley re-emitió play_music con la MISMA canción → 2 tabs idénticas en
# Opera. La heurística previa "executed_count == 1 = plan incompleto" es
# demasiado optimista para acciones que ya cubren la petición entera del
# user (típicamente verbos atómicos tipo "pon X", "screenshot", "lista
# ventanas"). El trigger del continuation pide al LLM "si está completo,
# no emitas tag" — pero la presión textual hace que re-emita igual.
#
# Mantenemos la lista MÍNIMA para no romper flujos multi-step legítimos
# como "abre YT y busca X" (donde después de open_url SÍ esperamos search).
# Si aparecen más bugs reportados con otras acciones, ampliar la lista.
_TERMINAL_ACTIONS = {
    "play_music",       # canción ya sonando, no hay siguiente paso
    "screenshot",       # captura ya tomada
    "list_windows",     # info ya devuelta a Ashley
    "read_page",        # página ya leída a Ashley
}

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
    # ── v0.18.2 — Bug "[system:proactive_message]" alucinado ──────────────
    # Ashley a veces inventa tags estilo [system:X] aunque no estén en el
    # protocolo. Pasa más en proactivos donde el LLM pierde contexto del
    # formato esperado y se inventa un "marker" interno. Strippear cualquier
    # [system:X] / [System:X] / [SYSTEM:X] (con o sin contenido).
    text = re.sub(r'\[\s*system\s*:[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[\s*system\s*:[^\]]*$', '', text, flags=re.IGNORECASE)  # parcial al final
    # También bare "[system]" sin colon (raro pero posible)
    text = re.sub(r'\[\s*system\s*\]', '', text, flags=re.IGNORECASE)
    # ── Bug C (v0.16.14) — tags BARE sin prefijo "action:" ──────────────
    # Caso real reportado: Ashley emitió "[save_taste:proyectos:mejorando
    # voz de Ashley]" SIN el prefijo "action:". El regex anterior solo
    # pillaba "[action:save_taste:...]" así que el tag bare quedaba
    # visible en el bubble. Listamos los action types conocidos y los
    # eliminamos también en formato bare. Lista sincronizada con
    # actions.py::execute_action.
    _BARE_ACTION_TYPES = (
        # Sistema
        "screenshot", "open_app", "play_music", "search_web", "open_url",
        "volume", "type_text", "type_in", "write_to_app", "focus_window",
        "hotkey", "press_key", "close_window", "close_tab",
        # Browser CDP
        "click", "type_browser", "read_page", "scroll_page",
        # Safe (no requieren toggle de acciones)
        "remind", "add_important", "done_important", "save_taste",
    )
    _bare_action_re = (
        r'\[\s*(?:' + '|'.join(_BARE_ACTION_TYPES) + r')\s*:[^\]]*\]'
    )
    text = re.sub(_bare_action_re, '', text, flags=re.IGNORECASE)
    # Variante parcial al final (durante streaming): "[save_taste:proye"
    _bare_action_partial = (
        r'\[\s*(?:' + '|'.join(_BARE_ACTION_TYPES) + r')\s*:[^\]]*$'
    )
    text = re.sub(_bare_action_partial, '', text, flags=re.IGNORECASE)
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
    # ── Meta-narrativa sobre la propia respuesta (red de seguridad) ──
    # A veces el LLM verbaliza juicios sobre su propia respuesta — sobre
    # si emitió acciones, sobre el estilo de la conversación, etc. —
    # típicamente al final, como un "cierre" tipo evaluación. El prompt
    # ya tiene la instrucción de no hacerlo, pero como red de seguridad
    # filtramos post-stream también.
    #
    # v0.17.4 — ampliado: antes solo cubríamos acciones explícitas tipo
    # "no actions needed". Ahora cubrimos también:
    #   • "No actions." sin "needed"
    #   • "Conversación fluida." y variantes (LLM alucinaba esto sin estar
    #     en el prompt — patrón de auto-evaluación inventado)
    #   • Catch-all genérico: fragmento final tras coma/punto que contiene
    #     keyword de meta-evaluación y no tiene estructura conversacional
    _META_ACTION_PATTERNS = [
        # Acciones — explícito (existentes)
        r'\bno\s+actions?\s+(?:needed|required|necessary|to\s+take|to\s+execute|taken|executed|performed)\.?\s*',
        r'\bnothing\s+to\s+do\s+here\.?\s*',
        r'\bno\s+action\s+is\s+(?:needed|required)\.?\s*',
        r'\bno\s+(?:se\s+)?necesita(?:n)?\s+acci[oó]n(?:es)?\.?\s*',
        r'\bno\s+(?:hay|requiere)\s+acci[oó]n(?:es)?\.?\s*',
        r'\bsin\s+acci[oó]n(?:es)?\s+que\s+(?:ejecutar|tomar)\.?\s*',
        r'\bpas\s+d[\'’]action\s+(?:n[eé]cessaire|requise)\.?\s*',
        r'\baucune\s+action\s+(?:requise|n[eé]cessaire)\.?\s*',
        # Bare "No actions." al final (sin "needed/required") — v0.17.4
        r'(?:^|[\.\n])\s*no\s+actions?\.?\s*$',
        r'(?:^|[\.\n])\s*sin\s+acci[oó]n(?:es)?\.?\s*$',
        r'(?:^|[\.\n])\s*pas\s+d[\'’]actions?\.?\s*$',
        r'(?:^|[\.\n])\s*aucune\s+action\.?\s*$',
        # Meta sobre conversación / estilo (NUEVO v0.17.4) — el LLM
        # alucina "conversación fluida" como cierre evaluativo
        r',?\s*conversaci[oó]n\s+(?:fluida|natural|fluida\s+y\s+natural)\.?\s*$',
        r',?\s*conversation\s+(?:flowing|fluid|natural|flowing\s+naturally)\.?\s*$',
        r',?\s*conversation\s+(?:fluide|naturelle)\.?\s*$',
        r',?\s*flujo\s+(?:natural|fluido|de\s+conversaci[oó]n)\.?\s*$',
        r',?\s*natural\s+(?:flow|conversation\s+flow)\.?\s*$',
        r',?\s*r[eé]ponse\s+(?:naturelle|fluide)\.?\s*$',
    ]
    for _pat in _META_ACTION_PATTERNS:
        text = re.sub(_pat, '', text, flags=re.IGNORECASE | re.MULTILINE)
    # ── Catch-all genérico v0.17.4 ──
    # Detecta fragmentos finales tipo ", <frase corta con keyword meta>."
    # que se le escapan al LLM y no están en los patrones específicos.
    # Estructura: tras coma/punto al final, frase de 1-4 palabras que
    # contiene UN keyword meta-evaluativo (no es diálogo natural).
    # Riesgo controlado: solo aplica al final del texto Y la frase debe ser
    # corta + contener keyword reconocido. False positives muy poco probables.
    _META_KEYWORDS_RE = (
        r'(?:fluid[ae]?|fluide|flowing|naturalmente|naturellement|narrativ[oa]?|'
        r'narrative|grindeand[oa]?|conversaci[oó]n|conversation|response|'
        r'r[eé]ponse|respuesta|conclusi[oó]n|conclusion|ending|cierre)'
    )
    _CATCH_ALL_TRAILING = re.compile(
        r'(?:[,.!?]\s+|\s*\n\s*)'  # separador (coma, punto, nueva línea)
        r'(?:\([^)]{0,40}\)|\b\w+(?:\s+\w+){0,3}\s+)'  # paren breve o 1-4 palabras
        r'\b' + _META_KEYWORDS_RE + r'\b'
        r'[\s.!?]*$',  # cierre opcional + EOT
        re.IGNORECASE,
    )
    text = _CATCH_ALL_TRAILING.sub('', text)
    # ── Empty bracket residues (v0.17.5) ──────────────────────────────
    # El LLM a veces emite "[ ]" o "[]" o "[mood:]" al final pensando que
    # representan "tag vacío / no action". Los regex de stripping previos
    # solo cubren tags CON contenido — tags vacíos se cuelan literal.
    # Bug observado en v0.17.4: tras el cambio de prompt (regla más
    # abstracta sobre tags), Ashley empezó a alucinar "[ ]" como cierre.
    text = re.sub(r'\[\s*\]', '', text)              # [] [ ] [    ]
    text = re.sub(r'\[\s*\w+\s*:\s*\]', '', text)    # [mood:] [action:] [affection:] etc
    text = re.sub(r'\[\s*\w+\s*:\s*\w+\s*:\s*\]', '', text)  # [action:type:] sin params
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

    v0.19.30 — DEDUPE de acciones idempotentes. Bug observado en producción:
    Ashley emitió [action:play_music:URL_1][action:play_music:URL_2] en la
    MISMA respuesta donde URL_1 y URL_2 apuntaban al MISMO video pero con
    query params distintos (ej: ?v=X vs ?v=X&t=10s) → 2 tabs idénticas en
    Opera. El "dedupe accidental" previo via text.replace en extract_action
    solo colapsaba byte-idénticos — variaciones de URL no.

    Fix:
    • play_music: dedupe por videoId extraído (regex YouTube /watch?v=XXX
      o youtu.be/XXX). Si no es URL de YouTube, fallback a key exacta.
    • open_url / search_web / open_app / focus_window / screenshot:
      dedupe por (type, params) — defensa explícita aunque text.replace ya
      colapse byte-idénticos.

    Para type_text / hotkey / press_key / volume NO deduplicamos en esta
    capa (aunque el text.replace accidental colapse byte-idénticos —
    comportamiento histórico, fuera de scope de este fix).
    """
    actions: list[dict] = []
    remaining_text = text
    while True:
        stripped, action = extract_action(remaining_text)
        if action is None:
            break
        actions.append(action)
        remaining_text = stripped

    # ── v0.19.30 — dedupe idempotent actions ──────────────────────────
    _IDEMPOTENT_FOR_DEDUPE = {
        "play_music", "open_url", "search_web", "open_app",
        "focus_window", "screenshot",
    }
    # Regex para extraer videoId de URLs YouTube (ambos formatos)
    _YT_ID_RE = re.compile(
        r'(?:youtube\.com/watch\?[^"\s]*?[?&]?v=|youtu\.be/)'
        r'([a-zA-Z0-9_-]{11})',
        re.IGNORECASE,
    )

    def _dedupe_key(act: dict) -> tuple | None:
        atype = act["type"]
        params = act.get("params") or []
        # Caso especial: play_music con URL de YouTube → dedupe por videoId
        if atype == "play_music" and params:
            url = params[0] or ""
            m = _YT_ID_RE.search(url)
            if m:
                return ("play_music_yt", m.group(1))
        return (atype, tuple(params))

    seen_keys: set[tuple] = set()
    deduped: list[dict] = []
    for a in actions:
        if a["type"] in _IDEMPOTENT_FOR_DEDUPE:
            key = _dedupe_key(a)
            if key in seen_keys:
                continue
            seen_keys.add(key)
        deduped.append(a)
    return remaining_text, deduped


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
    elif a_type == "add_important":
        # Soporta dos formatos:
        #   [action:add_important:texto]                          (legacy)
        #   [action:add_important:YYYY-MM-DDTHH:MM:texto]          (con fecha)
        # Si el inicio parsea como ISO datetime, split en (fecha, texto).
        # Si no, todo es texto sin fecha — comportamiento original.
        params = parse_remind_params(rest) if rest else []
        # parse_remind_params devuelve [date, text] si match, o [rest] si no.
        # Para legacy "Llamar al médico antes del viernes" sin fecha, devolverá
        # [rest] que es exactamente lo que add_important espera como texto.
    elif a_type == "done_important":
        params = [rest] if rest else []
    elif a_type == "save_taste":
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    elif a_type == "save_date":
        # save_date:TYPE:DATE:LABEL — TYPE = birthday|anniversary|event
        # DATE = YYYY-MM-DD o MM-DD (sin colons internos)
        # LABEL = freeform (puede tener colons en teoría, le damos todo el resto)
        # v0.18.0 Fase 2.
        parts = rest.split(":", 2)  # max 3 partes: [type, date, rest_label]
        params = parts
    elif a_type == "save_goal":
        # save_goal:CATEGORY:GOAL_TEXT — v0.18.0 Fase 3
        # GOAL_TEXT puede contener colons (improbable pero defensivo).
        inner = rest.find(":")
        if inner == -1:
            params = [rest] if rest else []
        else:
            params = [rest[:inner], rest[inner + 1:]]
    elif a_type in ("check_in_goal", "complete_goal"):
        # check_in_goal:ID_O_TEXTO  /  complete_goal:ID_O_TEXTO
        # v0.18.0 Fase 3 — un único parámetro (puede contener colons).
        params = [rest] if rest else []
    else:
        # v0.19.20 — FALLBACK CRÍTICO. El docstring decía "resto: split normal
        # por ':'" pero el branch nunca se implementó → UnboundLocalError al
        # return cuando a_type era algo no listado arriba (volume, open_app,
        # close_window, hotkey, press_key, focus_window, screenshot, etc).
        # Síntoma para el user: "Something went wrong with Grok (send_message):
        # cannot access local variable 'params' where it is not associated
        # with a value" tras pedir "increase volume" / "abre notepad" / etc.
        # Fix: split por ":" normal — cubre TODOS los action types restantes
        # que tienen 0+ params separados por colons (volume:up, volume:set:75,
        # open_app:NOMBRE, hotkey:ctrl:c, etc).
        params = rest.split(":") if rest else []

    clean = text.replace(full_tag, "").strip()
    return clean, {"type": a_type, "params": params}
