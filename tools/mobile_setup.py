"""
mobile_setup.py — Helper para configurar la app móvil de Ashley.

Uso:
    python tools/mobile_setup.py            # abre la página de pairing en tu browser
    python tools/mobile_setup.py --info     # solo imprime URL e info, sin abrir browser
    python tools/mobile_setup.py --regen    # regenera el pairing token (desconecta móviles)

Lo que hace:
  1. Detecta el puerto del Ashley desktop corriendo (frontend port)
  2. Abre tu browser a la página de "Conectar móvil" donde verás el QR
  3. Escanea el QR desde la app móvil de Ashley en tu Android

REQUIERE: Ashley desktop debe estar corriendo. Si no lo está, primero
abre Ashley.exe y luego ejecuta este script.

Nota: desde v0.18.2, Ashley acepta conexiones LAN POR DEFAULT (no hay
flag para activar — viene listo). El acceso está protegido por el
pairing token, igual que WhatsApp Web.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import sys
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path


def _data_dir() -> Path:
    env_dir = os.environ.get("ASHLEY_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    here = Path(__file__).resolve().parent.parent
    if (here / "rxconfig.py").exists():
        return here
    return Path.cwd()


def _pairing_file() -> Path:
    return _data_dir() / "mobile_pairing.json"


def _read_config() -> dict:
    p = _pairing_file()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_config(data: dict) -> None:
    p = _pairing_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_or_create_token() -> str:
    cfg = _read_config()
    tok = (cfg.get("token") or "").strip()
    if tok:
        return tok
    cfg["token"] = secrets.token_urlsafe(24)
    _write_config(cfg)
    return cfg["token"]


def get_lan_ip() -> str | None:
    """Devuelve la IP local del PC (para que el móvil llegue a ella)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return None


def detect_frontend_port() -> int:
    """Intenta detectar el puerto del frontend de Ashley.

    Strategy:
      1. Intenta hacer GET a /api/whisper/status en cada puerto típico
         desde 17300 hasta 17320 (rango Electron busca puertos libres).
      2. El backend (Starlette) responde a este endpoint, así que un 200
         indica que es el puerto correcto.
      3. Si no encuentra ninguno, devuelve 17300 (default).
    """
    for port in range(17300, 17321):
        url = f"http://127.0.0.1:{port}/api/whisper/status"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=0.5) as resp:
                if resp.status == 200:
                    return port
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            continue
    return 17300


def open_connect_page():
    """Abre la página de pairing en el browser del PC."""
    port = detect_frontend_port()
    url = f"http://127.0.0.1:{port}/mobile/connect.html"
    print(f"\nAbriendo {url} en tu browser...\n")
    try:
        webbrowser.open(url)
        print("Si no se abrió automáticamente, copia esa URL en tu browser.\n")
    except Exception as e:
        print(f"No se pudo abrir browser automáticamente: {e}")
        print(f"Abre manualmente: {url}\n")


def print_info(token: str):
    lan_ip = get_lan_ip() or "127.0.0.1"
    port = detect_frontend_port()
    print()
    print("═" * 64)
    print(" Ashley — Mobile Setup")
    print("═" * 64)
    print()
    print(f"  Token de emparejamiento: {token}")
    print(f"  Tu IP en LAN:            {lan_ip}")
    print(f"  Puerto frontend:          {port}")
    print()
    print("  Para emparejar:")
    print(f"    1. Abre en este PC:  http://127.0.0.1:{port}/mobile/connect.html")
    print("       (o ejecuta este script sin --info para que se abra solo)")
    print()
    print("    2. En tu Android, abre la app Ashley (PWA) y escanea el QR.")
    print()
    print("    3. Para instalar la PWA:")
    print(f"         Chrome (Android) → http://{lan_ip}:{port}/mobile/")
    print("         menú ⋮ → 'Añadir a pantalla de inicio'")
    print()
    print("═" * 64)
    print()


def main():
    ap = argparse.ArgumentParser(description="Ashley mobile setup helper")
    ap.add_argument("--info", action="store_true",
                    help="Solo imprime info, no abre browser.")
    ap.add_argument("--regen", action="store_true",
                    help="Regenera token (desconecta móviles existentes).")
    args = ap.parse_args()

    if args.regen:
        cfg = _read_config()
        cfg["token"] = secrets.token_urlsafe(24)
        _write_config(cfg)
        print("Token regenerado. Los móviles antiguos perdieron acceso.\n")

    token = get_or_create_token()

    if args.info:
        print_info(token)
    else:
        open_connect_page()
        print_info(token)


if __name__ == "__main__":
    main()
