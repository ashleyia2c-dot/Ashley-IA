"""
browser_cdp.py — Control directo del navegador vía Chrome DevTools Protocol.

Cuando el browser está arrancado con --remote-debugging-port=PORT, expone una
API REST en localhost que permite listar/cerrar/abrir tabs sin SendInput,
sin foco visible, y sin dependencias del browser específico (Chrome, Edge,
Brave, Vivaldi, Opera GX — todos los Chromium soportan).

Por qué es mejor que el approach SendInput:
  - No requiere foco de la ventana del browser (funciona minimizado)
  - No hay teclas ciclando visiblemente (preserva inmersión)
  - Acceso directo a tabs por ID, no por title-matching frágil
  - Sub-100ms vs 1-3s del cycling con keybd_event
  - No depende del browser-specific shortcut (Ctrl+Tab vs Ctrl+PageDown vs setting
    "ciclar entre tabs recientes" que cambia behavior)
  - Robust contra anti-input shields (Opera GX bloquea SendInput pero acepta CDP)

Por qué es opt-in:
  - El user tiene que arrancar el browser con --remote-debugging-port
  - Si el browser ya está corriendo, hay que cerrarlo y reabrirlo (Windows reusa
    la instancia y ignora flags nuevos)
  - El puerto abierto en localhost permite a cualquier app local controlar el
    browser. En la práctica el risk es bajo (otras apps legítimas no escanean
    puertos ajenos), pero hay que comunicarlo honesto

Uso típico (modo híbrido con fallback):

    from .browser_cdp import is_cdp_available, list_tabs, close_tab

    if is_cdp_available():
        # Path moderno: directo, robusto
        tabs = list_tabs()
        for t in tabs:
            if "youtube" in t["title"].lower():
                close_tab(t["id"])
    else:
        # Fallback: SendInput cycling como hasta ahora
        ...

API REST de CDP que usamos (sin WebSockets — más simple, menos deps):
  - GET /json/version   → info del browser (User-Agent, version)
  - GET /json o /json/list → lista de tabs como array de objects
  - GET /json/close/{targetId} → cierra una tab por ID
  - PUT /json/new?{url} → abre nueva tab con URL
  - PUT /json/activate/{targetId} → activa una tab (la trae al frente)

Cada tab object tiene los campos:
  { "id", "title", "url", "type", "webSocketDebuggerUrl", "devtoolsFrontendUrl" }

type='page' son las tabs normales — filtramos a esas. Otras (background_page,
service_worker, browser) son internals que no nos interesan.
"""

import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


_log = logging.getLogger("ashley.browser_cdp")


# Puerto default del flag --remote-debugging-port. El user (o un setup
# wizard futuro) puede cambiarlo a uno random para reducir el surface
# de detección por escaneo de puertos.
DEFAULT_CDP_PORT = 9222

# Timeout para todas las llamadas. CDP responde en sub-100ms cuando todo
# va bien — 1.5s de cap es safety neta, no afecta UX en happy path.
_DEFAULT_TIMEOUT = 1.5


# v0.19.34 (H5) — Lista de marcas de browser que esperamos en el campo
# "Browser" del endpoint /json/version. Si responde algo que NO matchea
# ninguna de estas, asumimos que NO es un Chromium real (alguna otra app
# está squatteando el puerto 9222) y devolvemos is_cdp_available=False.
# Sin esto, cualquier servicio random en :9222 hacía que las llamadas
# CDP siguientes fallaran con errores raros que confundían al user.
_CHROMIUM_BROWSER_MARKERS = (
    "Chrome", "Chromium", "Edge", "Brave", "Opera", "Vivaldi",
    "HeadlessChrome",
)


def _get_json(url: str, timeout: float = _DEFAULT_TIMEOUT):
    """GET una URL y devuelve JSON parseado, o None si falla.

    Fail-safe — cualquier excepción (browser cerrado, puerto distinto, JSON
    inválido) devuelve None. El caller debe asumir que CDP no está
    disponible si recibe None y caer a fallback.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionRefusedError,
            TimeoutError, json.JSONDecodeError, OSError):
        return None


def is_cdp_available(port: int = DEFAULT_CDP_PORT) -> bool:
    """¿Hay un browser CHROMIUM corriendo con CDP en este puerto?

    Llama al endpoint /json/version que devuelve metadata del browser.
    Si responde 200 con JSON válido Y el campo "Browser" matchea uno de
    los marcadores Chromium conocidos → CDP activo. Si timeout, connection
    refused, o el responder NO es Chromium → False.

    v0.19.34 (H5): antes solo verificábamos que ALGO respondiera en el
    puerto. Si otra app (Docker, otro IDE) estaba squatteando :9222,
    devolvíamos True optimistamente y luego las llamadas CDP fallaban
    con errores raros. Ahora exigimos que la respuesta venga de un
    browser Chromium real.
    """
    info = _get_json(f"http://127.0.0.1:{port}/json/version")
    if info is None:
        return False
    browser = str(info.get("Browser") or "")
    if not any(marker in browser for marker in _CHROMIUM_BROWSER_MARKERS):
        _log.warning(
            "Puerto %d responde pero NO es Chromium (Browser=%r). "
            "Otra app está usando este puerto; CDP no está disponible.",
            port, browser,
        )
        return False
    return True


def get_browser_info(port: int = DEFAULT_CDP_PORT) -> Optional[dict]:
    """Devuelve dict con info del browser (Browser, User-Agent, V8-Version,
    Protocol-Version, webSocketDebuggerUrl) o None si no responde.

    Útil para debug — logueamos qué browser/version está conectado.
    """
    return _get_json(f"http://127.0.0.1:{port}/json/version")


def list_tabs(port: int = DEFAULT_CDP_PORT) -> list[dict]:
    """Lista todas las tabs (filtradas a type='page', que son las normales).

    Cada tab dict tiene 'id' (string único usable con close_tab y otros
    endpoints), 'title' (lo que ve el user en la pestaña), y 'url'.

    Si CDP no responde, devuelve [] — el caller no puede distinguir entre
    'no hay browser' y 'browser sin tabs', pero en ambos casos no hay
    nada que hacer vía CDP.
    """
    raw = _get_json(f"http://127.0.0.1:{port}/json/list")
    if not raw or not isinstance(raw, list):
        # Algunos versions de Chromium responden a /json en lugar de /json/list
        raw = _get_json(f"http://127.0.0.1:{port}/json")
    if not raw or not isinstance(raw, list):
        return []
    return [t for t in raw if t.get("type") == "page"]


def close_tab(tab_id: str, port: int = DEFAULT_CDP_PORT) -> bool:
    """Cierra una tab por su ID.

    Returns True si la request fue 200 (browser confirmó el close). Returns
    False si el ID era inválido, el browser no respondió, o cualquier otro
    error. Idempotente — cerrar una tab ya cerrada simplemente devuelve
    False sin efectos secundarios.
    """
    try:
        url = f"http://127.0.0.1:{port}/json/close/{tab_id}"
        with urllib.request.urlopen(url, timeout=_DEFAULT_TIMEOUT) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def new_tab(url: str = "", port: int = DEFAULT_CDP_PORT) -> Optional[dict]:
    """Abre una nueva tab. Si url está vacío, abre about:blank.

    Returns el tab object recién creado (con id, title='', url) o None si
    el browser no respondió. Útil para play_music: abrir directamente la
    URL de YouTube sin pasar por webbrowser.open ni SendInput.

    v0.19.46 — CRÍTICO: Chromium 130+ (que incluye Opera GX 130, Edge,
    Brave reciente) cambió `/json/new` de aceptar GET a EXIGIR PUT por
    razones de seguridad CSRF. El error literal del browser es:
        "Using unsafe HTTP verb GET to invoke /json/new.
         This action supports only PUT verb." (HTTP 405)
    Con GET el endpoint devolvía None → caíamos al poll de 10s → al final
    al fallback optimista mentiroso → wait_then clickeaba la tab vieja.
    Verificado experimentalmente con curl PUT (200 OK + tab abierta en
    50ms) vs GET (405 instantáneo).
    """
    if url:
        encoded = urllib.parse.quote(url, safe='')
        endpoint = f"http://127.0.0.1:{port}/json/new?{encoded}"
    else:
        endpoint = f"http://127.0.0.1:{port}/json/new"
    try:
        # PUT (no GET) — Chromium 130+ rechaza GET con 405.
        req = urllib.request.Request(endpoint, method="PUT")
        with urllib.request.urlopen(req, timeout=3.0) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionRefusedError,
            TimeoutError, json.JSONDecodeError, OSError):
        return None


def activate_tab(tab_id: str, port: int = DEFAULT_CDP_PORT) -> bool:
    """Trae una tab al frente (activa) sin cambiar foco de la ventana.

    Returns True si fue OK. Útil para 'enfoca la pestaña de YouTube' sin
    cerrar otras.
    """
    try:
        url = f"http://127.0.0.1:{port}/json/activate/{tab_id}"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as r:
            return 200 <= r.status < 300
    except Exception:
        # Algunos Chromium aceptan solo GET
        try:
            with urllib.request.urlopen(url, timeout=_DEFAULT_TIMEOUT) as r:
                return 200 <= r.status < 300
        except Exception:
            return False


# ─────────────────────────────────────────────
#  Helpers de alto nivel — operaciones agregadas
# ─────────────────────────────────────────────

def find_tabs_matching(hint: str, port: int = DEFAULT_CDP_PORT) -> list[dict]:
    """Encuentra tabs cuyo title contenga el hint (case-insensitive).

    El hint se trata como substring — más permisivo que match exacto. Útil
    para 'cierra YouTube' que matchea cualquier tab con 'youtube' en el
    título incluyendo subtítulos como 'X video - YouTube'.
    """
    hint_lower = hint.lower()
    return [
        t for t in list_tabs(port)
        if hint_lower in t.get("title", "").lower()
    ]


def close_tabs_matching(hint: str, exclude: Optional[str] = None,
                         port: int = DEFAULT_CDP_PORT) -> tuple[int, list[str]]:
    """Cierra todas las tabs que contengan hint, excepto las que contengan
    exclude (también case-insensitive substring match).

    Returns (cuántas se cerraron, lista de títulos cerrados). El caller
    puede usar el count para reportar éxito y los títulos para mostrar al
    user qué se cerró.

    Use case principal: 'cierra todas las de YouTube excepto Running Up
    That Hill' → close_tabs_matching('youtube', exclude='running up that
    hill').
    """
    matches = find_tabs_matching(hint, port)
    if exclude:
        exclude_lower = exclude.lower()
        matches = [
            t for t in matches
            if exclude_lower not in t.get("title", "").lower()
        ]

    closed_titles = []
    for t in matches:
        if close_tab(t["id"], port):
            closed_titles.append(t.get("title", ""))

    return len(closed_titles), closed_titles


# ─────────────────────────────────────────────
#  Funciones avanzadas vía WebSocket — Runtime.evaluate, Input
# ─────────────────────────────────────────────
#
# Para click, fill input, scroll, read DOM, screenshot necesitamos hablar
# WebSocket con el Page target específico (tab). HTTP REST no soporta
# Runtime.evaluate ni los métodos de Input/Page. La conexión va al
# webSocketDebuggerUrl que viene en el tab object de list_tabs().
#
# Estas funciones son async (websockets es asyncio-based). Los callers
# síncronos deben envolverlas con asyncio.run() o usar executor.

import asyncio
import base64


def _resolve_tab(target_or_id: str | dict, port: int = DEFAULT_CDP_PORT) -> Optional[dict]:
    """Acepta un tab dict, un tab id string, o keywords como 'active'/'first'.
    Devuelve el tab dict completo (con webSocketDebuggerUrl) o None si no
    se encuentra."""
    if isinstance(target_or_id, dict):
        return target_or_id
    target_str = str(target_or_id or "").strip().lower()
    tabs = list_tabs(port)
    if not tabs:
        return None
    if not target_str or target_str in ("active", "current", "first"):
        return tabs[0]
    # Buscar por id exacto, o por substring del title
    for t in tabs:
        if t.get("id") == target_or_id:
            return t
    for t in tabs:
        if target_str in t.get("title", "").lower():
            return t
    return None


async def _ws_send(ws_url: str, method: str, params: Optional[dict] = None,
                   timeout: float = 10.0) -> Optional[dict]:
    """Abre una conexión WebSocket al target, envía un comando CDP, espera
    la respuesta correspondiente, cierra. Devuelve el campo 'result' de la
    respuesta CDP o None si falló.

    CDP usa request/response asincrono — cada mensaje lleva un 'id' y la
    respuesta lo correlaciona. Como aquí mandamos un comando único por
    conexión, usamos id=1 fijo y leemos hasta encontrar id=1 en la
    respuesta (puede haber events intermedios que ignoramos).
    """
    try:
        import websockets
    except ImportError:
        return None

    payload = {"id": 1, "method": method}
    if params is not None:
        payload["params"] = params

    try:
        async with websockets.connect(ws_url, max_size=10_000_000) as ws:
            import json as _json
            await asyncio.wait_for(ws.send(_json.dumps(payload)), timeout=timeout)

            # Leer mensajes hasta encontrar la respuesta con id=1
            # (CDP puede enviar events asincronos en el medio).
            deadline = asyncio.get_event_loop().time() + timeout
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    return None
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                msg = _json.loads(raw)
                if msg.get("id") == 1:
                    return msg.get("result")
                # Si es un error de CDP en respuesta a nuestro id
                if "error" in msg and msg.get("id") == 1:
                    return None
    except Exception:
        return None


def _run_async(coro):
    """Ejecuta una coroutine desde código síncrono. Si ya hay un event loop
    corriendo, usa run_in_executor con un loop nuevo en otro thread; si
    no, usa asyncio.run normal."""
    try:
        asyncio.get_running_loop()
        # Hay loop corriendo — necesitamos ejecutar en otro thread con su
        # propio loop para no interferir.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        # No hay loop — podemos usar asyncio.run directamente
        return asyncio.run(coro)


def evaluate_js(target: str | dict, expression: str,
                 port: int = DEFAULT_CDP_PORT) -> Optional[dict]:
    """Ejecuta un fragmento de JavaScript en el contexto de la tab.

    Returns dict CDP con 'result' (el valor de retorno del JS) o None si
    falla. El JS corre en el window global de la página — tiene acceso
    completo al DOM como si fuera la consola DevTools del user.
    """
    tab = _resolve_tab(target, port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    return _run_async(_ws_send(
        tab["webSocketDebuggerUrl"],
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
    ))


def click_by_selector(target: str | dict, css_selector: str,
                      port: int = DEFAULT_CDP_PORT) -> tuple[bool, str]:
    """Hace click en el primer elemento que matchee el CSS selector.

    Returns (ok, mensaje). Si no encuentra el elemento, ok=False con
    msg explicativo. Si hace click, ok=True con el title del botón
    (si lo había) o el selector matched.
    """
    # Escape de comillas en el selector
    safe_sel = css_selector.replace("\\", "\\\\").replace("'", "\\'")
    js = f"""
(() => {{
    const el = document.querySelector('{safe_sel}');
    if (!el) return {{found: false, error: 'No element matches selector'}};
    const desc = (el.getAttribute('aria-label') || el.innerText || el.tagName).slice(0, 60);
    el.click();
    return {{found: true, label: desc}};
}})()
"""
    res = evaluate_js(target, js, port)
    if not res or not res.get("result"):
        return False, "CDP no respondió"
    val = res["result"].get("value") or {}
    if val.get("found"):
        return True, f"Click en: {val.get('label', '?')}"
    return False, val.get("error", "Elemento no encontrado")


# v0.19.45 — Sinónimos multilingües para botones comunes. Cuando Ashley
# dice "like" pero el browser está en otro idioma (Opera/Chrome usan el
# locale del SO), los aria-labels NO contienen "like" — contienen "Me
# gusta" / "J'aime" / "いいね" / etc. Sin esto, click_by_text fallaba para
# usuarios con YouTube no-inglés (caso del user reportado).
#
# Cada entrada mapea un término "canonical" (lo que Ashley puede emitir)
# a una lista de variantes que CUALQUIERA podría aparecer como aria-label
# o texto del botón. La búsqueda intenta TODAS las variantes hasta encontrar
# match.
# v0.19.46 — ORDEN IMPORTA. La búsqueda en aria-label/innerText itera
# variantes en orden y se queda con la primera que matchee. Las más
# largas/específicas van PRIMERO porque son menos propensas a falsos
# positivos. Ej: "indica que te gusta" antes que "me gusta" antes que
# "like" — sino "like" matchea cualquier canal random como
# "@studylikenat" (bug real reportado por user en YouTube/Opera ES).
_BUTTON_SYNONYMS = {
    "like": [
        # ES — más específico primero
        "indica que te gusta", "me gusta",
        # FR
        "j'aime", "j’aime",
        # JA — frase + carácter
        "高く評価", "いいね",
        # DE
        "gefällt mir", "mag ich",
        # RU — más específico primero
        "мне нравится", "нравится",
        # KO
        "좋아요",
        # EN — más específico primero, "like" al final (genérico)
        "i like this", "like",
    ],
    "dislike": [
        "indica que no te gusta", "no me gusta",
        "je n'aime pas", "je n’aime pas",
        "低く評価", "よくないね",
        "gefällt mir nicht", "mag ich nicht",
        "не нравится",
        "싫어요",
        "i dislike this", "dislike",
    ],
    "subscribe": [
        "suscribirse", "suscríbete", "suscrito",
        "s'abonner", "s’abonner", "abonné",
        "チャンネル登録", "登録",
        "abonnieren", "abonniert",
        "подписаться", "вы подписаны",
        "구독중", "구독",
        "subscribed", "subscribe",
    ],
    "share": [
        "compartir", "partager", "共有", "teilen", "поделиться", "공유", "share",
    ],
    "save": [
        "guardar", "enregistrer", "保存", "speichern", "сохранить", "저장", "save",
    ],
    "play": [
        "reproducir", "lire", "再生", "abspielen", "воспроизвести", "재생", "play",
    ],
    "pause": [
        "pausar", "mettre en pause", "一時停止", "pausieren", "пауза", "일시중지", "pause",
    ],
}

# v0.19.46 — Canonicals cuyo botón es TOGGLEABLE (aria-pressed cambia
# tras click). Para estos, verificamos post-click leyendo aria-pressed
# antes/después → success real (no solo "el JS encontró algo").
# Cubre el bug del user: click_by_text reportaba True habiendo clickeado
# `@studylikenat` (un canal aleatorio) en vez del botón Like real.
_TOGGLE_CANONICALS = frozenset({"like", "dislike", "subscribe", "play", "pause"})


def _expand_synonyms(text: str) -> list[str]:
    """v0.19.45 — Si `text` es una palabra-clave conocida (like/dislike/etc.),
    devuelve todas las variantes multilingües. Si no, devuelve [text]."""
    norm = text.lower().strip()
    for canonical, variants in _BUTTON_SYNONYMS.items():
        if norm == canonical or norm in [v.lower() for v in variants]:
            return variants
    return [text]


# v0.19.45 — Selectores estables CSS-only para botones conocidos en
# sitios populares. Cuando aria-label / innerText fallan (DOM custom,
# button sin texto, locale exótico), estos selectores apuntan a la
# estructura DOM estable del sitio. Solo se prueban si el target es
# uno de los canonical conocidos (like/dislike/subscribe/etc.) y la
# tab matchea el dominio correspondiente.
# v0.19.46 — YouTube 2025 cambió el wrapping: ahora usa
# segmented-like-dislike-button-view-model para encapsular like + dislike.
# Hay 3 instancias de like-button-view-model en el DOM (mobile/responsive
# variants); solo 1 es visible. Por eso el JS abajo usa querySelectorAll
# y filtra por offsetParent !== null en vez de querySelector (que da el
# primero, que suele ser el oculto). Verificado experimentalmente con
# probe_youtube_dom.py: 3 like-button-view-model, sample[1] es el visible.
_SITE_SPECIFIC_SELECTORS = {
    "youtube.com": {
        "like": [
            # Selector 2025 — wrapping nuevo, MÁS específico, primero
            "segmented-like-dislike-button-view-model like-button-view-model button",
            # Fallback genérico — el JS de click_by_text elige el primer VISIBLE
            "like-button-view-model button",
            # Selectores legacy (pueden funcionar en versiones viejas)
            "ytd-segmented-like-dislike-button-renderer like-button-view-model button",
            "#segmented-like-button button",
            "ytd-toggle-button-renderer like-button-view-model button",
        ],
        "dislike": [
            "segmented-like-dislike-button-view-model dislike-button-view-model button",
            "dislike-button-view-model button",
            "ytd-segmented-like-dislike-button-renderer dislike-button-view-model button",
            "#segmented-dislike-button button",
        ],
        "subscribe": [
            "ytd-subscribe-button-renderer button",
            "#subscribe-button button",
            "#subscribe-button-shape button",
            "yt-subscribe-button-view-model button",
        ],
        "share": [
            'yt-button-view-model button[aria-label*="ompartir" i]',
            'yt-button-view-model button[aria-label*="hare" i]',
            'ytd-button-renderer[id="share"] button',
        ],
    },
    "twitter.com": {
        "like": ['button[data-testid="like"]'],
        "share": ['button[data-testid="retweet"]'],
    },
    "x.com": {
        "like": ['button[data-testid="like"]'],
        "share": ['button[data-testid="retweet"]'],
    },
}


def _get_site_selectors_for(text: str) -> dict[str, list[str]]:
    """Devuelve {hostname_substring: [selectors]} si `text` es un canonical
    conocido. Sino devuelve {}."""
    norm = text.lower().strip()
    # Normalizar a canonical si el user dio una variante
    canonical = None
    for cn, variants in _BUTTON_SYNONYMS.items():
        if norm == cn or norm in [v.lower() for v in variants]:
            canonical = cn
            break
    if not canonical:
        return {}
    out: dict[str, list[str]] = {}
    for host, mapping in _SITE_SPECIFIC_SELECTORS.items():
        if canonical in mapping:
            out[host] = mapping[canonical]
    return out


def _is_toggle_canonical(text: str) -> bool:
    """v0.19.46 — True si `text` (o uno de sus sinónimos) corresponde a un
    canonical toggleable (like/dislike/subscribe/play/pause). Usado para
    decidir si verificamos post-click vía aria-pressed."""
    norm = text.lower().strip()
    for canonical, variants in _BUTTON_SYNONYMS.items():
        if canonical not in _TOGGLE_CANONICALS:
            continue
        if norm == canonical or norm in [v.lower() for v in variants]:
            return True
    return False


def click_by_text(target: str | dict, text: str,
                   port: int = DEFAULT_CDP_PORT) -> tuple[bool, str]:
    """Hace click en el primer elemento clickeable cuyo texto/aria-label
    matche el `text` dado, con varias estrategias defensivas.

    Estrategia en cascada (más fiable → más permisiva):
      1. **Site-specific selectors** (v0.19.46): para sitios conocidos
         (youtube.com, x.com, etc.) y canonicals conocidos (like/share/...),
         prueba selectores DOM estables. Usa `querySelectorAll` y elige el
         PRIMER VISIBLE (no el primer match) — YouTube tiene varias
         instancias del mismo selector pero solo una es visible.
      2. **aria-label match con sinónimos multilingües, prioridad por
         especificidad** (v0.19.46): los sinónimos están ordenados de
         más específico (frase larga) a más genérico (palabra corta).
         Para sinónimos cortos (≤4 chars) requiere whole-word match
         (regex `\\b`) — sino "like" matchea cualquier "@studylikenat".
      3. **innerText match** con misma lógica de prioridad.

    Para canonicals TOGGLEABLES (like/dislike/subscribe/play/pause),
    además: lee aria-pressed antes/después del click y verifica que
    cambió. Si no cambió → success=False (el click técnicamente ocurrió
    pero no surtió efecto, posiblemente clickeó elemento equivocado).

    Cubre 3 bugs reales reportados:
      • YouTube ES: "like" no estaba en aria-labels (eran "Indica que
        te gusta..."), pero la primera instancia del selector estaba
        oculta — `querySelector` daba la oculta, no clickeable.
      • Aria substring "like" matcheaba `@studylikenat` (canal random)
        antes de las variantes en español de la lista.
      • Reportaba success=True habiendo clickeado el elemento equivocado
        — sin verificación post-click no había forma de saber.
    """
    # v0.19.45 — Expandir a sinónimos multilingües si aplica
    candidates = _expand_synonyms(text)
    safe_candidates = [c.replace("\\", "\\\\").replace("'", "\\'") for c in candidates]
    candidates_js = "[" + ",".join(f"'{c}'" for c in safe_candidates) + "]"

    # v0.19.45 — Site-specific selectors (más fiables que aria/text)
    site_selectors = _get_site_selectors_for(text)
    site_selectors_js_parts = []
    for host, sels in site_selectors.items():
        safe_host = host.replace("'", "\\'")
        safe_sels = [s.replace("\\", "\\\\").replace("'", "\\'") for s in sels]
        sels_arr = "[" + ",".join(f"'{s}'" for s in safe_sels) + "]"
        site_selectors_js_parts.append(f"'{safe_host}':{sels_arr}")
    site_selectors_js = "{" + ",".join(site_selectors_js_parts) + "}"

    is_toggle = _is_toggle_canonical(text)
    is_toggle_js = "true" if is_toggle else "false"

    js = f"""
(async () => {{
    const targets = {candidates_js}.map(t => t.toLowerCase());
    const siteSelectors = {site_selectors_js};
    const isToggle = {is_toggle_js};

    const isClickable = (el) => {{
        if (!el) return false;
        if (el.disabled) return false;
        if (el.offsetParent === null && el.tagName !== 'BODY') {{
            return false;  // hidden via display:none/detached
        }}
        const tag = el.tagName.toLowerCase();
        if (tag === 'button' || tag === 'a') return true;
        if (el.getAttribute('role') === 'button') return true;
        if (el.onclick) return true;
        return false;
    }};

    // v0.19.46 — Match con prioridad por especificidad. Sinónimos cortos
    // (≤4 chars) requieren WHOLE-WORD match (sino "like" → "@studylikenat").
    // Sinónimos largos pueden matchear como substring.
    const matchesTarget = (text_lower, target) => {{
        if (!text_lower) return false;
        if (target.length <= 4) {{
            // Whole-word con \\b regex (escape para regex literal del target)
            const escaped = target.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
            const re = new RegExp("\\\\b" + escaped + "\\\\b", "i");
            return re.test(text_lower);
        }}
        return text_lower.includes(target);
    }};

    // v0.19.46 — Helper: realizar click + verificación opcional aria-pressed.
    // Para toggleables, lee aria-pressed antes, click, espera 250ms, lee
    // después. Devuelve verified=true si cambió o si el botón no tenía
    // aria-pressed (no toggle real, asumimos OK porque encontramos el
    // selector específico).
    const doClick = async (el, method, matched_str) => {{
        const beforePressed = el.getAttribute('aria-pressed');
        const beforeLabel = (el.getAttribute('aria-label') || el.innerText || '').slice(0, 80);
        el.click();
        if (!isToggle) {{
            return {{found: true, label: beforeLabel, method: method, matched: matched_str,
                     verified: true, before: null, after: null}};
        }}
        // Toggle: esperar y leer aria-pressed tras click
        await new Promise(r => setTimeout(r, 250));
        const afterPressed = el.getAttribute('aria-pressed');
        let verified = false;
        if (beforePressed === null && afterPressed === null) {{
            // Botón no expone aria-pressed (no es un toggle real). Asumimos
            // OK SOLO si vino vía site-selector (más fiable que aria/text).
            verified = (method === 'site-selector');
        }} else {{
            verified = (beforePressed !== afterPressed);
        }}
        return {{found: true, label: beforeLabel, method: method, matched: matched_str,
                 verified: verified, before: beforePressed, after: afterPressed}};
    }};

    // ── 0. Site-specific selectors ───────────────────────────────────────
    // v0.19.46 — querySelectorAll + filter visible. Antes usábamos
    // querySelector que da SOLO el primero — en YouTube hay 3 instancias
    // de like-button-view-model y la primera suele estar oculta.
    const host = (location.hostname || '').toLowerCase();
    for (const [siteHost, sels] of Object.entries(siteSelectors)) {{
        if (!host.includes(siteHost)) continue;
        for (const sel of sels) {{
            try {{
                const all = document.querySelectorAll(sel);
                for (const el of all) {{
                    if (isClickable(el)) {{
                        return await doClick(el, 'site-selector', sel);
                    }}
                }}
            }} catch (e) {{
                // selector inválido — siguiente
            }}
        }}
    }}

    // ── 1. aria-label match con prioridad por especificidad ──────────────
    const ariaCandidates = document.querySelectorAll('[aria-label]');
    for (const target of targets) {{
        for (const el of ariaCandidates) {{
            const lbl = (el.getAttribute('aria-label') || '').toLowerCase();
            if (matchesTarget(lbl, target) && isClickable(el)) {{
                return await doClick(el, 'aria', target);
            }}
        }}
    }}

    // ── 2. innerText match con misma lógica ──────────────────────────────
    const allClickable = document.querySelectorAll('button, a, [role="button"]');
    for (const target of targets) {{
        for (const el of allClickable) {{
            const txt = (el.innerText || '').toLowerCase().trim();
            if (matchesTarget(txt, target) && isClickable(el)) {{
                return await doClick(el, 'text', target);
            }}
        }}
    }}
    return {{found: false, verified: false,
             error: 'No clickable element matched: ' + targets.join(' | ')}};
}})()
"""
    res = evaluate_js(target, js, port)
    if not res or not res.get("result"):
        return False, "CDP no respondió"
    val = res["result"].get("value") or {}
    if not val.get("found"):
        return False, val.get("error", "No se encontró elemento clickeable")
    # v0.19.46 — éxito real solo si verified (toggle cambió o site-selector)
    method = val.get("method", "?")
    label = val.get("label", "?")
    if val.get("verified"):
        return True, f"Click en '{label}' (vía {method})"
    # Click ocurrió pero el aria-pressed NO cambió (botón equivocado).
    # Reportar honestamente para que Ashley se disculpe en personaje.
    before = val.get("before")
    after = val.get("after")
    return False, (
        f"Click ejecutado en '{label}' pero no surtió efecto "
        f"(aria-pressed: {before!r} → {after!r}, vía {method}). "
        f"Probablemente clickeó el elemento equivocado."
    )


def fill_input(target: str | dict, css_selector: str, value: str,
                port: int = DEFAULT_CDP_PORT) -> tuple[bool, str]:
    """Escribe `value` en el campo input/textarea matched por CSS selector.

    Dispara eventos input + change para que React/Vue/Angular detecten el
    cambio (sin esto algunos sitios ignoran el valor cuando se asigna
    directamente via JS).
    """
    safe_sel = css_selector.replace("\\", "\\\\").replace("'", "\\'")
    safe_val = value.replace("\\", "\\\\").replace("'", "\\'")
    js = f"""
(() => {{
    const el = document.querySelector('{safe_sel}');
    if (!el) return {{found: false, error: 'No input matches selector'}};
    el.focus();
    const setter = Object.getOwnPropertyDescriptor(
        el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype,
        'value'
    ).set;
    setter.call(el, '{safe_val}');
    el.dispatchEvent(new Event('input', {{bubbles: true}}));
    el.dispatchEvent(new Event('change', {{bubbles: true}}));
    return {{found: true}};
}})()
"""
    res = evaluate_js(target, js, port)
    if not res or not res.get("result"):
        return False, "CDP no respondió"
    val = res["result"].get("value") or {}
    if val.get("found"):
        return True, "Texto escrito en el campo"
    return False, val.get("error", "Campo no encontrado")


def scroll_page(target: str | dict, direction: str = "down",
                 amount: int = 800,
                 port: int = DEFAULT_CDP_PORT) -> tuple[bool, str]:
    """Scroll programático. direction: 'up'|'down'|'top'|'bottom'."""
    direction = direction.lower().strip()
    if direction == "top":
        js = "window.scrollTo(0, 0); 'top'"
    elif direction == "bottom":
        js = "window.scrollTo(0, document.body.scrollHeight); 'bottom'"
    elif direction == "up":
        js = f"window.scrollBy(0, -{amount}); 'up {amount}'"
    else:  # down (default)
        js = f"window.scrollBy(0, {amount}); 'down {amount}'"
    res = evaluate_js(target, js, port)
    if not res or not res.get("result"):
        return False, "CDP no respondió"
    return True, f"Scroll {direction}"


def get_page_text(target: str | dict, max_chars: int = 5000,
                   port: int = DEFAULT_CDP_PORT) -> Optional[str]:
    """Devuelve el texto visible de la página actual (innerText del body).

    Truncado a max_chars para no llenar el contexto del LLM. Útil para
    'léeme ese artículo' o 'qué dice esa página'.
    """
    js = f"""
(() => {{
    const t = document.body ? document.body.innerText : '';
    return t.slice(0, {max_chars});
}})()
"""
    res = evaluate_js(target, js, port)
    if not res or not res.get("result"):
        return None
    return res["result"].get("value") or ""


def screenshot_tab(target: str | dict,
                    port: int = DEFAULT_CDP_PORT) -> Optional[str]:
    """Captura screenshot de la tab (incluso si está en background).

    Returns base64 PNG data URL, o None si falla. NO requiere que la tab
    esté visible — CDP captura el DOM renderizado off-screen. Eso es
    superior a las screenshots de pantalla completa.
    """
    tab = _resolve_tab(target, port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    res = _run_async(_ws_send(
        tab["webSocketDebuggerUrl"],
        "Page.captureScreenshot",
        {"format": "png"},
    ))
    if not res or "data" not in res:
        return None
    return f"data:image/png;base64,{res['data']}"
