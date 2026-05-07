"""Guards para la app móvil de Ashley (v0.18.2).

Cubren:
  1. Existencia de archivos críticos (HTML, CSS, JS, manifest, SW)
  2. API endpoints registrados en api_routes.py
  3. PWA manifest correctamente formateado
  4. Service worker funcional
  5. Embedded server con LAN binding opcional + proxy /api/*
  6. Helper script tools/mobile_setup.py

Estos tests son guards de regresión sobre el código fuente — no smoke
tests del runtime (no podemos arrancar la app móvil real desde pytest).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ASSETS_MOBILE = ROOT / "assets" / "mobile"
API_ROUTES = ROOT / "reflex_companion" / "api_routes.py"
MAIN_JS = ROOT / "electron" / "main.js"
SETUP_SCRIPT = ROOT / "tools" / "mobile_setup.py"


# ─────────────────────────────────────────────
#  Existencia de archivos
# ─────────────────────────────────────────────


def test_mobile_index_html_exists():
    assert (ASSETS_MOBILE / "index.html").exists()


def test_mobile_app_css_exists():
    assert (ASSETS_MOBILE / "app.css").exists()


def test_mobile_app_js_exists():
    assert (ASSETS_MOBILE / "app.js").exists()


def test_pwa_manifest_exists():
    assert (ASSETS_MOBILE / "manifest.json").exists()


def test_service_worker_exists():
    assert (ASSETS_MOBILE / "sw.js").exists()


def test_setup_script_exists():
    assert SETUP_SCRIPT.exists()


# ─────────────────────────────────────────────
#  PWA manifest válido
# ─────────────────────────────────────────────


def test_manifest_is_valid_json():
    raw = (ASSETS_MOBILE / "manifest.json").read_text(encoding="utf-8")
    json.loads(raw)  # raises if invalid


def test_manifest_has_required_fields():
    data = json.loads((ASSETS_MOBILE / "manifest.json").read_text(encoding="utf-8"))
    required = ["name", "short_name", "start_url", "display", "icons"]
    for field in required:
        assert field in data, f"manifest.json falta campo {field!r}"


def test_manifest_display_standalone():
    """Para apariencia de app nativa, display debe ser 'standalone' o 'fullscreen'."""
    data = json.loads((ASSETS_MOBILE / "manifest.json").read_text(encoding="utf-8"))
    assert data["display"] in ("standalone", "fullscreen", "minimal-ui"), (
        f"manifest.display={data['display']!r} — debe ser standalone/fullscreen para PWA"
    )


def test_manifest_has_icons():
    data = json.loads((ASSETS_MOBILE / "manifest.json").read_text(encoding="utf-8"))
    assert len(data["icons"]) >= 1
    for icon in data["icons"]:
        assert "src" in icon and "sizes" in icon


def test_manifest_scope_matches_start_url():
    """El scope del PWA debe contener al start_url."""
    data = json.loads((ASSETS_MOBILE / "manifest.json").read_text(encoding="utf-8"))
    scope = data.get("scope", "/")
    start = data["start_url"]
    assert start.startswith(scope), (
        f"start_url {start!r} no está en scope {scope!r}"
    )


# ─────────────────────────────────────────────
#  Service worker
# ─────────────────────────────────────────────


def test_sw_has_install_handler():
    src = (ASSETS_MOBILE / "sw.js").read_text(encoding="utf-8")
    assert "addEventListener('install'" in src or 'addEventListener("install"' in src


def test_sw_has_fetch_handler():
    src = (ASSETS_MOBILE / "sw.js").read_text(encoding="utf-8")
    assert "addEventListener('fetch'" in src or 'addEventListener("fetch"' in src


def test_sw_does_not_cache_api_calls():
    """Las llamadas /api/* NO deben cachearse — son data dinámica."""
    src = (ASSETS_MOBILE / "sw.js").read_text(encoding="utf-8")
    # El SW debe early-return en /api/*
    assert "/api/" in src and "return" in src, (
        "Service worker debe excluir /api/* del cacheo."
    )


# ─────────────────────────────────────────────
#  HTML móvil
# ─────────────────────────────────────────────


def test_html_has_viewport_meta():
    html = (ASSETS_MOBILE / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "initial-scale=1" in html


def test_html_links_manifest():
    html = (ASSETS_MOBILE / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest"' in html
    assert "/mobile/manifest.json" in html


def test_html_registers_service_worker():
    html = (ASSETS_MOBILE / "index.html").read_text(encoding="utf-8")
    assert "navigator.serviceWorker" in html
    assert "register" in html


def test_html_has_chat_setup_and_settings_screens():
    """Deben existir los 3 screens principales."""
    html = (ASSETS_MOBILE / "index.html").read_text(encoding="utf-8")
    assert 'id="setup-screen"' in html
    assert 'id="app-screen"' in html
    assert 'id="memories-panel"' in html
    assert 'id="settings-panel"' in html


# ─────────────────────────────────────────────
#  JS — endpoints + flujo
# ─────────────────────────────────────────────


def test_js_uses_correct_api_paths():
    """El JS debe llamar a /api/mobile/* paths."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    assert "/api/mobile/status" in src
    assert "/api/mobile/chat" in src
    assert "/api/mobile/facts" in src
    assert "/api/mobile/send" in src


def test_js_sends_auth_header():
    """El JS debe mandar X-Ashley-Token en headers de las peticiones."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    assert "X-Ashley-Token" in src or "x-ashley-token" in src.lower()


def test_js_persists_config_in_localstorage():
    """El JS debe guardar serverUrl + token en localStorage para persistencia."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    assert "localStorage" in src
    assert "setItem" in src


def test_js_polls_for_new_messages():
    """Debe haber un setInterval o equivalente para polling."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    assert "setInterval" in src or "setTimeout" in src


# ─────────────────────────────────────────────
#  API endpoints registrados
# ─────────────────────────────────────────────


def test_api_routes_registered():
    src = API_ROUTES.read_text(encoding="utf-8")
    required = [
        "/api/mobile/status",
        "/api/mobile/chat",
        "/api/mobile/facts",
        "/api/mobile/send",
        "/api/mobile/pairing_token",
    ]
    for route in required:
        assert route in src, f"Ruta {route!r} no está registrada en api_routes.py"


def test_api_endpoints_check_auth():
    """Los endpoints (excepto /status y /pairing_token) deben verificar auth."""
    src = API_ROUTES.read_text(encoding="utf-8")
    # Buscamos que cada endpoint ÚSE _check_mobile_auth
    chat_section = re.search(
        r"_mobile_chat_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert chat_section, "_mobile_chat_endpoint no encontrado"
    assert "_check_mobile_auth" in chat_section.group(0), (
        "/api/mobile/chat no verifica auth — vulnerabilidad."
    )

    facts_section = re.search(
        r"_mobile_facts_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert facts_section
    assert "_check_mobile_auth" in facts_section.group(0)

    send_section = re.search(
        r"_mobile_send_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert send_section
    assert "_check_mobile_auth" in send_section.group(0)


def test_pairing_token_localhost_only():
    """El endpoint que devuelve el token solo debe responder a localhost
    (defensa: si por error LAN está activo, el token NO se filtra)."""
    src = API_ROUTES.read_text(encoding="utf-8")
    pairing_section = re.search(
        r"_mobile_pairing_token_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert pairing_section
    body = pairing_section.group(0)
    assert "localhost" in body.lower() or "127.0.0.1" in body, (
        "/api/mobile/pairing_token debe estar restringido a localhost."
    )
    assert "403" in body or "localhost_only" in body.lower(), (
        "/api/mobile/pairing_token debe rechazar (403) requests no-localhost."
    )


def test_token_uses_secrets_module():
    """El token debe generarse con secrets.token_urlsafe (criptográficamente seguro),
    NOT con random.* (predecible)."""
    src = API_ROUTES.read_text(encoding="utf-8")
    assert "secrets.token_urlsafe" in src or "from secrets import token_urlsafe" in src, (
        "Token debe usar el módulo `secrets` (CSPRNG), no random."
    )


# ─────────────────────────────────────────────
#  Embedded server — LAN binding + proxy
# ─────────────────────────────────────────────


def test_embedded_server_default_lan_with_paranoid_optout():
    """v0.18.2 — Embedded server bind a 0.0.0.0 por DEFAULT (igual que Reflex).
    Solo se desactiva si el user pone lan_disabled=true (opt-out paranoid)."""
    src = MAIN_JS.read_text(encoding="utf-8")
    assert "_readMobileLanDisabled" in src, (
        "Falta función _readMobileLanDisabled — checkea opt-out paranoid."
    )
    assert "0.0.0.0" in src and "127.0.0.1" in src, (
        "Embedded server debe contemplar ambos hosts."
    )
    # El opt-out debe verificar lan_disabled === true explícito
    pattern = re.compile(
        r"_readMobileLanDisabled[\s\S]+?lan_disabled\s*===?\s*true",
    )
    assert pattern.search(src), (
        "_readMobileLanDisabled debe verificar `lan_disabled === true` "
        "explícitamente — evita que cualquier valor truthy active el modo paranoid."
    )


def test_api_proxy_function_exists():
    """El embedded server debe tener un proxy function para /api/*."""
    src = MAIN_JS.read_text(encoding="utf-8")
    assert "_proxyToBackend" in src, (
        "Falta función _proxyToBackend para reenviar /api/* del frontend port "
        "al backend port. Sin esto el móvil tendría que conocer ambos puertos."
    )


def test_proxy_used_for_api_paths():
    """El handler del embedded server debe llamar al proxy para /api/*."""
    src = MAIN_JS.read_text(encoding="utf-8")
    # Buscar la DEFINICIÓN de la función (con `function`), no el call site
    server_section = re.search(
        r"function _startEmbeddedFrontendServer[\s\S]+?(?=\nfunction |\Z)",
        src,
    )
    assert server_section, "No encontré la definición de _startEmbeddedFrontendServer"
    body = server_section.group(0)
    assert "/api/" in body and "_proxyToBackend" in body, (
        "El embedded server no proxy /api/* requests al backend."
    )


def test_freshness_check_includes_html_and_json():
    """El freshness check debe vigilar .html y .json para detectar cambios
    en assets/mobile/{index.html, manifest.json}."""
    src = MAIN_JS.read_text(encoding="utf-8")
    pattern = re.compile(
        r"watchDirs\s*=\s*\[[\s\S]+?'assets'[\s\S]+?exts:\s*\[([^\]]+)\]"
    )
    m = pattern.search(src)
    assert m, "No encontré watchDirs en main.js"
    exts_str = m.group(1)
    assert "'.html'" in exts_str or '".html"' in exts_str, (
        "freshness check no vigila .html"
    )
    assert "'.json'" in exts_str or '".json"' in exts_str, (
        "freshness check no vigila .json"
    )


def test_freshness_check_is_recursive():
    """El freshness check debe ser recursivo para detectar archivos en subcarpetas."""
    src = MAIN_JS.read_text(encoding="utf-8")
    assert "_findStaleFile" in src, (
        "freshness check debe usar función recursiva _findStaleFile."
    )
    pattern = re.compile(
        r"function _findStaleFile[\s\S]+?(?=\nfunction |\nconst |$)"
    )
    m = pattern.search(src)
    assert m
    body = m.group(0)
    assert "_findStaleFile" in body[10:], (
        "_findStaleFile debe llamarse a sí mismo (recursión)."
    )


# ─────────────────────────────────────────────
#  Setup script
# ─────────────────────────────────────────────


def test_setup_script_imports_correctly():
    """El script debe importar sin errores."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("mobile_setup", SETUP_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # v0.18.2 — script simplificado, abre browser a connect.html
    assert hasattr(mod, "get_or_create_token")
    assert hasattr(mod, "get_lan_ip")
    assert hasattr(mod, "open_connect_page")
    assert hasattr(mod, "detect_frontend_port")


def test_setup_script_token_generation_uses_secrets():
    """El script debe usar secrets.token_urlsafe (no random.*)."""
    src = SETUP_SCRIPT.read_text(encoding="utf-8")
    assert "secrets.token_urlsafe" in src or "import secrets" in src


# ─────────────────────────────────────────────
#  QR pairing UX (v0.18.2)
# ─────────────────────────────────────────────


def test_connect_html_exists():
    """La página connect.html para mostrar QR en PC."""
    assert (ASSETS_MOBILE / "connect.html").exists()


def test_connect_html_loads_qr_payload():
    """connect.html debe llamar a /api/mobile/qr_payload para obtener server+token."""
    html = (ASSETS_MOBILE / "connect.html").read_text(encoding="utf-8")
    assert "/api/mobile/qr_payload" in html


def test_connect_html_has_regen_button():
    """Debe haber un botón para regenerar el token desde la página."""
    html = (ASSETS_MOBILE / "connect.html").read_text(encoding="utf-8")
    assert "/api/mobile/regen_token" in html, (
        "connect.html debe permitir regenerar token (botón 'Regenerar')."
    )


def test_qr_payload_endpoint_localhost_only():
    """qr_payload tiene token sensible — solo localhost."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_qr_payload_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert section
    body = section.group(0)
    assert "localhost" in body.lower() or "127.0.0.1" in body
    assert "403" in body


def test_regen_token_endpoint_localhost_only():
    """regen_token también localhost-only (no exponer a LAN)."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_regen_token_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert section
    body = section.group(0)
    assert "localhost" in body.lower() or "127.0.0.1" in body
    assert "403" in body


def test_qr_payload_returns_server_url_and_token():
    """qr_payload debe devolver `server`, `token`, `lan_ip`, `port`."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_qr_payload_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    body = section.group(0)
    for key in ('"server"', '"token"', '"lan_ip"', '"port"'):
        assert key in body, f"qr_payload no devuelve {key}"


def test_lan_ip_detection_function_exists():
    """_detect_lan_ip detecta la IP local del PC vía socket."""
    src = API_ROUTES.read_text(encoding="utf-8")
    assert "_detect_lan_ip" in src
    assert "8.8.8.8" in src, (
        "_detect_lan_ip debe usar el truco socket UDP a IP remota para "
        "detectar la interfaz local correcta."
    )


def test_qr_payload_uses_backend_port_not_frontend():
    """v0.18.2 bug fix CRÍTICO — el server URL del QR debe apuntar al
    BACKEND port (donde Starlette tiene los endpoints /api/mobile/*),
    NO al frontend port (donde Reflex Next.js está y NO conoce esas rutas).

    Bug raíz que rompía el pareo del móvil: cuando Reflex está en slow-path
    (modo normal sin embedded server JS), el frontend port :17300 sirve
    Next.js que devuelve 404 para /api/mobile/*. El móvil recibía
    "page not found" y no podía pairing.

    Fix: el QR tiene server=http://<ip>:<backend_port> — siempre tiene los
    endpoints disponibles, sin depender del proxy del embedded server.
    """
    src = API_ROUTES.read_text(encoding="utf-8")
    # Helper backend port debe existir
    assert "_detect_backend_port" in src, (
        "Falta _detect_backend_port — el QR no puede apuntar al backend"
    )
    # qr_payload debe usar backend port
    section = re.search(
        r"_mobile_qr_payload_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert section, "qr_payload endpoint no encontrado"
    body = section.group(0)
    assert "_detect_backend_port" in body, (
        "qr_payload debe usar _detect_backend_port (no _detect_frontend_port). "
        "Sino el móvil intenta llamar al puerto del frontend Next.js que "
        "devuelve 404 para /api/mobile/*."
    )


def test_rxconfig_backend_host_is_lan_accessible():
    """rxconfig.py debe declarar backend_host='0.0.0.0' explícitamente
    para que el móvil pueda llegar via LAN. Es el default de Reflex pero
    lo hacemos explícito para que un upgrade futuro de Reflex que cambie
    el default no rompa el pareo móvil silenciosamente."""
    rxconfig = ROOT / "rxconfig.py"
    src = rxconfig.read_text(encoding="utf-8")
    assert 'backend_host="0.0.0.0"' in src or "backend_host='0.0.0.0'" in src, (
        "rxconfig.py debe declarar backend_host='0.0.0.0' para LAN access móvil"
    )


def test_mobile_app_has_scan_qr_button():
    """index.html debe tener botón 'Escanear QR' como acción primaria."""
    html = (ASSETS_MOBILE / "index.html").read_text(encoding="utf-8")
    assert 'id="scan-qr-btn"' in html
    assert 'id="scanner-overlay"' in html
    assert 'id="scanner-video"' in html


def test_mobile_app_uses_barcode_detector_or_fallback():
    """app.js debe usar BarcodeDetector (Chrome Android) para escanear QR."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    assert "BarcodeDetector" in src
    assert "facingMode" in src and "environment" in src, (
        "Scanner debe pedir cámara trasera (environment) en móvil."
    )


def test_mobile_app_parses_qr_json_payload():
    """Tras scan, el QR contiene JSON {s,t} — el cliente parsea."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    assert "JSON.parse" in src
    # Debe extraer fields s/server y t/token
    assert "parsed.s" in src or "parsed.server" in src
    assert "parsed.t" in src or "parsed.token" in src


def test_mobile_app_releases_camera_on_close():
    """Al cerrar el scanner, debe liberar el stream de cámara (privacidad)."""
    src = (ASSETS_MOBILE / "app.js").read_text(encoding="utf-8")
    pattern = re.compile(r"closeScanner[\s\S]+?getTracks[\s\S]+?stop\(\)")
    assert pattern.search(src), (
        "closeScanner debe llamar getTracks().forEach(t => t.stop()) "
        "para liberar la cámara cuando el user cierra el scanner."
    )
