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
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional


# Puerto default del flag --remote-debugging-port. El user (o un setup
# wizard futuro) puede cambiarlo a uno random para reducir el surface
# de detección por escaneo de puertos.
DEFAULT_CDP_PORT = 9222

# Timeout para todas las llamadas. CDP responde en sub-100ms cuando todo
# va bien — 1.5s de cap es safety neta, no afecta UX en happy path.
_DEFAULT_TIMEOUT = 1.5


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
    """¿Hay un browser corriendo con CDP en este puerto?

    Llama al endpoint /json/version que devuelve metadata del browser.
    Si responde 200 con JSON válido → CDP activo. Si timeout o connection
    refused → CDP no activo (probablemente el browser arrancó sin el flag
    o no hay browser corriendo).
    """
    info = _get_json(f"http://127.0.0.1:{port}/json/version")
    return info is not None


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
    """
    if url:
        encoded = urllib.parse.quote(url, safe='')
        endpoint = f"http://127.0.0.1:{port}/json/new?{encoded}"
    else:
        endpoint = f"http://127.0.0.1:{port}/json/new"
    return _get_json(endpoint, timeout=3.0)  # algo más de timeout — abre + carga


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
