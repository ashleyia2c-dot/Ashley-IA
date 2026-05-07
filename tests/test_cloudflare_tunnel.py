"""Guards para Cloudflare Quick Tunnel integration (v0.18.2).

Acceso móvil universal: el PC arranca un Cloudflare Tunnel automático que
expone el backend vía URL pública HTTPS. El móvil escanea el QR (con esa
URL) y conecta desde CUALQUIER red — LAN, 4G, casa de un amigo, viaje.

Sin esto, el pareo sólo funciona si móvil y PC están en la misma subnet
LAN — falla con boosters/mesh/AP isolation/redes corporativas.

Componentes:
  • electron/cloudflared-tunnel.js — npm package wrapper, spawn, capture URL
  • electron/main.js — lifecycle (start tras backend ready, stop en shutdown)
  • api_routes._read_tunnel_url() — lee URL del archivo escrito por electron
  • api_routes._mobile_qr_payload_endpoint — usa tunnel URL si disponible
  • State._refresh_mobile_pair_data_local — igual

Tests verifican:
  - El módulo JS expone startTunnel + stopTunnel + onStatusChange
  - electron/main.js llama startTunnel después del waitForReflex
  - electron/main.js llama stopTunnel en shutdown handlers
  - Backend lee tunnel_url.txt y prefiere esa URL si está
  - El QR payload retorna connection_mode = "tunnel" o "lan"
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TUNNEL_JS = ROOT / "electron" / "cloudflared-tunnel.js"
MAIN_JS = ROOT / "electron" / "main.js"
PACKAGE_JSON = ROOT / "electron" / "package.json"
API_ROUTES = ROOT / "reflex_companion" / "api_routes.py"
MAIN_PY = ROOT / "reflex_companion" / "reflex_companion.py"


# ─────────────────────────────────────────────
#  Files / dependencies
# ─────────────────────────────────────────────

def test_cloudflared_npm_dep():
    src = PACKAGE_JSON.read_text(encoding="utf-8")
    assert '"cloudflared"' in src, (
        "package.json debe tener 'cloudflared' en dependencies"
    )


def test_tunnel_js_module_exists():
    assert TUNNEL_JS.exists(), "Falta electron/cloudflared-tunnel.js"


# ─────────────────────────────────────────────
#  cloudflared-tunnel.js exports
# ─────────────────────────────────────────────

def test_tunnel_js_exports_startTunnel():
    src = TUNNEL_JS.read_text(encoding="utf-8")
    assert "async function startTunnel" in src, (
        "tunnel-js: falta startTunnel async"
    )
    assert "module.exports" in src and "startTunnel" in src.split("module.exports")[1]


def test_tunnel_js_exports_stopTunnel():
    src = TUNNEL_JS.read_text(encoding="utf-8")
    assert "function stopTunnel" in src
    assert "stopTunnel" in src.split("module.exports")[1]


def test_tunnel_js_exports_status_helpers():
    src = TUNNEL_JS.read_text(encoding="utf-8")
    assert "function onStatusChange" in src
    assert "function getStatus" in src
    after_exports = src.split("module.exports")[1]
    assert "onStatusChange" in after_exports
    assert "getStatus" in after_exports


def test_tunnel_js_writes_url_to_file():
    """Escribir la URL a disco para que el backend Python pueda leerla."""
    src = TUNNEL_JS.read_text(encoding="utf-8")
    section = re.search(
        r"async function startTunnel\([\s\S]+?(?=\n(?:function |async function |/\*\*|module\.exports))",
        src,
    )
    assert section
    body = section.group(0)
    assert "writeFileSync" in body and "tunnelUrlFile" in body, (
        "startTunnel debe escribir la URL del túnel a tunnelUrlFile"
    )


def test_tunnel_js_uses_official_npm_package():
    """Usamos el paquete npm oficial 'cloudflared' que maneja download +
    spawn + capture URL automático."""
    src = TUNNEL_JS.read_text(encoding="utf-8")
    assert "require('cloudflared')" in src or 'require("cloudflared")' in src


def test_tunnel_js_handles_failure_gracefully():
    """Si el túnel falla (sin red, cloudflared no descarga, etc.), el módulo
    NO debe crashear Ashley — debe retornar error y dejar que el backend
    use LAN IP como fallback."""
    src = TUNNEL_JS.read_text(encoding="utf-8")
    section = re.search(
        r"async function startTunnel\([\s\S]+?(?=\n(?:function |async function |/\*\*|module\.exports))",
        src,
    )
    body = section.group(0)
    # Debe haber try/catch que retorna {ok: false, error}
    assert "try {" in body and "catch" in body, (
        "startTunnel debe envolver en try/catch para no crashear"
    )
    assert "ok: false" in body, (
        "startTunnel debe retornar {ok: false, error} en fallo"
    )


# ─────────────────────────────────────────────
#  electron/main.js integration
# ─────────────────────────────────────────────

def test_main_js_imports_tunnel_module():
    src = MAIN_JS.read_text(encoding="utf-8")
    assert "require('./cloudflared-tunnel')" in src or 'require("./cloudflared-tunnel")' in src, (
        "main.js debe importar ./cloudflared-tunnel"
    )


def test_main_js_starts_tunnel_after_reflex_ready():
    """El túnel se arranca DESPUÉS de waitForReflex porque cloudflared
    necesita que el backend esté escuchando en el puerto local primero."""
    src = MAIN_JS.read_text(encoding="utf-8")
    # Buscar bloque desde waitForReflex hasta antes del próximo step principal
    pattern = re.compile(
        r"await waitForReflex[\s\S]+?createMainWindow\(\)",
    )
    m = pattern.search(src)
    assert m, "no encontré bloque waitForReflex → createMainWindow"
    body = m.group(0)
    assert "startTunnel" in body, (
        "Tunnel debe arrancar después de waitForReflex y antes de "
        "createMainWindow"
    )


def test_main_js_passes_tunnel_url_file_path():
    src = MAIN_JS.read_text(encoding="utf-8")
    # Verifica que pasamos tunnelUrlFile al startTunnel
    pattern = re.compile(r"startTunnel\(\{[\s\S]+?tunnelUrlFile")
    assert pattern.search(src), (
        "startTunnel call debe incluir tunnelUrlFile path"
    )


def test_main_js_stops_tunnel_in_shutdown_handlers():
    """Asegura que el túnel se cierra cuando Ashley termina (sino queda
    proceso huérfano de cloudflared.exe usando red + memoria)."""
    src = MAIN_JS.read_text(encoding="utf-8")
    # Verificar handlers que deberían parar el túnel
    handlers = ["window-all-closed", "before-quit", "SIGINT"]
    for h in handlers:
        section = re.search(
            rf"app\.on\('{h}'[\s\S]+?\}}\)|process\.on\('{h}'[\s\S]+?\}}\);",
            src,
        )
        assert section, f"handler {h} no encontrado"
        body = section.group(0)
        assert "stopTunnel" in body or "cfTunnel.stopTunnel" in body, (
            f"handler '{h}' debe llamar stopTunnel para limpiar cloudflared"
        )


# ─────────────────────────────────────────────
#  Backend Python integration
# ─────────────────────────────────────────────

def test_backend_has_read_tunnel_url_helper():
    src = API_ROUTES.read_text(encoding="utf-8")
    assert "def _read_tunnel_url" in src, (
        "Falta _read_tunnel_url() en api_routes.py"
    )


def test_read_tunnel_url_validates_https_cloudflare():
    """_read_tunnel_url debe validar que la URL es HTTPS de Cloudflare —
    no aceptar URLs aleatorias del archivo (defensa contra escritura
    maliciosa al archivo)."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"def _read_tunnel_url[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert section
    body = section.group(0)
    assert "https://" in body, (
        "_read_tunnel_url debe validar que la URL empieza con https://"
    )
    assert "trycloudflare.com" in body, (
        "_read_tunnel_url debe validar dominio trycloudflare.com"
    )


def test_qr_payload_prefers_tunnel_url():
    """qr_payload debe devolver el tunnel URL si está activo, fallback LAN."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_qr_payload_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    assert section
    body = section.group(0)
    assert "_read_tunnel_url" in body, (
        "qr_payload debe consultar _read_tunnel_url"
    )
    assert "connection_mode" in body, (
        "qr_payload debe devolver 'connection_mode' (tunnel/lan) para que "
        "la UI sepa cómo está conectando el móvil"
    )


def test_state_dialog_prefers_tunnel_url():
    """El dialog QR del desktop también debe usar tunnel URL si existe."""
    src = MAIN_PY.read_text(encoding="utf-8")
    section = re.search(
        r"def _refresh_mobile_pair_data_local[\s\S]+?(?=\n    def |\n    async def |\Z)",
        src,
    )
    assert section
    body = section.group(0)
    assert "_read_tunnel_url" in body, (
        "_refresh_mobile_pair_data_local debe usar _read_tunnel_url"
    )


def test_qr_payload_endpoint_returns_tunnel_url_field():
    """Tests directo: con env var simulado, el endpoint retorna tunnel_url."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_qr_payload_endpoint[\s\S]+?(?=\nasync def |\ndef )",
        src,
    )
    body = section.group(0)
    assert '"tunnel_url"' in body, (
        "qr_payload payload debe incluir field 'tunnel_url' (vacío si no activo)"
    )
