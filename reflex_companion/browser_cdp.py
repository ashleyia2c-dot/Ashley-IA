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


def click_by_text(target: str | dict, text: str,
                   port: int = DEFAULT_CDP_PORT) -> tuple[bool, str]:
    """Hace click en el primer elemento clickeable cuyo texto/aria-label
    contenga el `text` dado (case-insensitive).

    Estrategia más universal que CSS selector — funciona en muchos sitios
    sin selectores hardcoded. Busca en este orden:
      1. button/[role=button] con aria-label que contenga el texto
      2. button con innerText que contenga el texto
      3. <a> con innerText que contenga el texto
    """
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'")
    js = f"""
(() => {{
    const target = '{safe_text}'.toLowerCase();
    const isClickable = (el) => {{
        if (!el) return false;
        const tag = el.tagName.toLowerCase();
        if (tag === 'button' || tag === 'a') return true;
        if (el.getAttribute('role') === 'button') return true;
        if (el.onclick) return true;
        return false;
    }};
    // 1. aria-label
    const ariaCandidates = document.querySelectorAll('[aria-label]');
    for (const el of ariaCandidates) {{
        const lbl = (el.getAttribute('aria-label') || '').toLowerCase();
        if (lbl.includes(target) && isClickable(el)) {{
            el.click();
            return {{found: true, label: el.getAttribute('aria-label'), method: 'aria'}};
        }}
    }}
    // 2. innerText match
    const all = document.querySelectorAll('button, a, [role="button"]');
    for (const el of all) {{
        const txt = (el.innerText || '').toLowerCase().trim();
        if (txt && txt.includes(target)) {{
            el.click();
            return {{found: true, label: el.innerText.slice(0, 60), method: 'text'}};
        }}
    }}
    return {{found: false, error: 'No clickable element matched: ' + target}};
}})()
"""
    res = evaluate_js(target, js, port)
    if not res or not res.get("result"):
        return False, "CDP no respondió"
    val = res["result"].get("value") or {}
    if val.get("found"):
        return True, f"Click en '{val.get('label', '?')}' (vía {val.get('method', '?')})"
    return False, val.get("error", "No se encontró elemento clickeable")


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
