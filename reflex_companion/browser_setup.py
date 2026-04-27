"""
browser_setup.py — Wizard para activar el modo CDP automáticamente
modificando los accesos directos (.lnk) de los navegadores instalados.

Sin esto, el user tendría que:
  1. Cerrar todas las ventanas del browser
  2. Editar manualmente el shortcut → Properties → añadir flag al Target
  3. Reabrir el browser

Con esto: un click en Settings → la app encuentra los shortcuts de
Chrome/Edge/Brave/Opera/Opera GX/Vivaldi en Desktop, Start Menu y Taskbar,
y les añade `--remote-debugging-port=9222` al campo Arguments del .lnk.
Hace backup en `<shortcut>.lnk.bak` antes de modificar — el user puede
revertir desactivando el toggle.

NO modifica el .exe del browser, solo los .lnk. Si el user abre el
browser por otro camino (ej: doble click directo en chrome.exe, otra
extensión, "abrir con..." de Windows), CDP no estará activo en esa
sesión — pero la app cae al modo legacy automáticamente. Defensa en
profundidad.

Usa PowerShell + WScript.Shell COM para leer/escribir .lnk. NO requiere
dependencias extra (PowerShell viene con Windows).
"""

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional


CDP_FLAG = "--remote-debugging-port=9222"

# Procesos de browsers Chromium-based que soportan CDP. Firefox no
# está aquí porque usa un protocolo distinto (Marionette) — el wizard
# no lo modifica.
_CHROMIUM_EXES = frozenset({
    "chrome.exe", "msedge.exe", "brave.exe",
    "opera.exe", "operagx.exe", "vivaldi.exe",
})


def _shortcut_locations() -> list[Path]:
    """Carpetas donde Windows guarda shortcuts de aplicaciones."""
    home = Path(os.environ.get("USERPROFILE", ""))
    appdata = Path(os.environ.get("APPDATA", ""))
    public = Path(os.environ.get("PUBLIC", ""))
    progdata = Path(os.environ.get("PROGRAMDATA", ""))
    return [
        home / "Desktop",
        public / "Desktop",
        appdata / "Microsoft/Windows/Start Menu/Programs",
        progdata / "Microsoft/Windows/Start Menu/Programs",
        # Pinned to taskbar — Windows guarda las shortcuts pinneadas aquí
        appdata / "Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar",
    ]


def _read_lnk_via_ps(lnk_path: str) -> Optional[dict]:
    """Lee un .lnk usando WScript.Shell COM via PowerShell.

    Devuelve dict con {target, arguments, working_directory} o None si falla.
    Es la forma estándar de Windows de inspeccionar shortcuts sin librerías
    de terceros.
    """
    # Escapar el path para PowerShell (las rutas pueden tener espacios).
    # Usamos here-string single-quoted para evitar interpolación.
    ps_lines = [
        "$shell = New-Object -ComObject WScript.Shell",
        f"$sc = $shell.CreateShortcut('{lnk_path}')",
        'Write-Output ("TARGET=" + $sc.TargetPath)',
        'Write-Output ("ARGS=" + $sc.Arguments)',
        'Write-Output ("WD=" + $sc.WorkingDirectory)',
    ]
    ps_script = "; ".join(ps_lines)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        out = {}
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("TARGET="):
                out["target"] = line[7:]
            elif line.startswith("ARGS="):
                out["arguments"] = line[5:]
            elif line.startswith("WD="):
                out["working_directory"] = line[3:]
        return out
    except Exception:
        return None


def _write_lnk_args_via_ps(lnk_path: str, new_args: str) -> bool:
    """Escribe los nuevos arguments al .lnk vía WScript.Shell COM.
    Returns True si la operación fue exitosa.
    """
    # Escape de comillas: $args puede contener double quotes (ej:
    # `--profile-directory="Default"`). Escapamos a `'` (single quote)
    # en PowerShell duplicando.
    safe_args = new_args.replace("'", "''")
    ps_lines = [
        "$shell = New-Object -ComObject WScript.Shell",
        f"$sc = $shell.CreateShortcut('{lnk_path}')",
        f"$sc.Arguments = '{safe_args}'",
        "$sc.Save()",
    ]
    ps_script = "; ".join(ps_lines)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _browser_friendly_name(exe: str) -> str:
    return {
        "chrome.exe": "Chrome",
        "msedge.exe": "Edge",
        "brave.exe": "Brave",
        "opera.exe": "Opera",
        "operagx.exe": "Opera GX",
        "vivaldi.exe": "Vivaldi",
    }.get(exe.lower(), exe)


def find_browser_shortcuts() -> list[dict]:
    """Escanea las locations comunes y devuelve todos los .lnk que apuntan
    a browsers Chromium.

    Returns:
        Lista de dicts con campos:
          - path: ruta absoluta al .lnk
          - browser: nombre legible (Chrome, Edge, Opera GX, ...)
          - target_exe: nombre del .exe (chrome.exe, etc)
          - has_cdp_flag: bool — ya está modificado o no
          - arguments: string con los args actuales
    """
    found = []
    seen_paths: set[str] = set()

    for loc in _shortcut_locations():
        if not loc.exists():
            continue
        for lnk in loc.rglob("*.lnk"):
            lnk_str = str(lnk)
            if lnk_str in seen_paths:
                continue
            seen_paths.add(lnk_str)
            try:
                info = _read_lnk_via_ps(lnk_str)
                if not info:
                    continue
                target = (info.get("target") or "").strip()
                if not target:
                    continue
                exe_name = Path(target).name.lower()
                if exe_name not in _CHROMIUM_EXES:
                    continue
                args = info.get("arguments") or ""
                found.append({
                    "path": lnk_str,
                    "browser": _browser_friendly_name(exe_name),
                    "target_exe": exe_name,
                    "has_cdp_flag": CDP_FLAG in args,
                    "arguments": args,
                })
            except Exception:
                continue
    return found


def add_cdp_flag(lnk_path: str) -> tuple[bool, str]:
    """Añade --remote-debugging-port=9222 al Arguments del .lnk.

    Si el flag ya está, no hace nada (idempotente).
    Hace backup automático en `<lnk>.bak` la primera vez (no sobrescribe
    backups existentes — preservar el "estado original original").

    Returns (ok, mensaje legible).
    """
    info = _read_lnk_via_ps(lnk_path)
    if not info:
        return False, f"No pude leer el shortcut: {Path(lnk_path).name}"

    args = (info.get("arguments") or "").strip()
    if CDP_FLAG in args:
        return True, f"{Path(lnk_path).name}: ya tenía el flag, sin cambios"

    # Backup (solo la primera vez — preserve el "antes de Ashley")
    bak_path = lnk_path + ".bak"
    try:
        if not os.path.exists(bak_path):
            shutil.copy2(lnk_path, bak_path)
    except Exception as e:
        return False, f"No pude hacer backup: {e}"

    new_args = (args + " " + CDP_FLAG).strip() if args else CDP_FLAG
    if not _write_lnk_args_via_ps(lnk_path, new_args):
        return False, f"No pude escribir el shortcut: {Path(lnk_path).name}"

    return True, f"{Path(lnk_path).name}: flag añadido"


def remove_cdp_flag(lnk_path: str) -> tuple[bool, str]:
    """Quita --remote-debugging-port=9222 del Arguments del .lnk.

    Si el .lnk.bak existe, lo restauramos (más seguro que un replace
    parcial). Si no, hacemos string replacement.
    """
    bak_path = lnk_path + ".bak"
    if os.path.exists(bak_path):
        try:
            shutil.copy2(bak_path, lnk_path)
            return True, f"{Path(lnk_path).name}: restaurado desde backup"
        except Exception as e:
            return False, f"No pude restaurar backup: {e}"

    # Sin backup: string replace defensivo
    info = _read_lnk_via_ps(lnk_path)
    if not info:
        return False, f"No pude leer el shortcut: {Path(lnk_path).name}"

    args = (info.get("arguments") or "")
    if CDP_FLAG not in args:
        return True, f"{Path(lnk_path).name}: no tenía el flag, sin cambios"

    new_args = args.replace(CDP_FLAG, "")
    new_args = " ".join(new_args.split())  # dedup spaces

    if not _write_lnk_args_via_ps(lnk_path, new_args):
        return False, f"No pude escribir el shortcut: {Path(lnk_path).name}"

    return True, f"{Path(lnk_path).name}: flag quitado"


def configure_all_shortcuts(enable: bool) -> dict:
    """Activa/desactiva el flag CDP en TODOS los shortcuts de browsers
    Chromium encontrados.

    Returns dict con resumen:
      {
        "shortcuts": [{"name", "browser", "ok", "message"}, ...],
        "modified": int,    # cuántos cambiaron de estado
        "skipped": int,     # cuántos ya estaban como queríamos
        "failed": int,      # cuántos fallaron
        "total": int,       # cuántos shortcuts en total
      }
    """
    shortcuts = find_browser_shortcuts()
    out = {
        "shortcuts": [],
        "modified": 0,
        "skipped": 0,
        "failed": 0,
        "total": len(shortcuts),
    }

    for s in shortcuts:
        if enable:
            ok, msg = add_cdp_flag(s["path"])
        else:
            ok, msg = remove_cdp_flag(s["path"])

        out["shortcuts"].append({
            "name": Path(s["path"]).name,
            "browser": s["browser"],
            "path": s["path"],
            "ok": ok,
            "message": msg,
        })
        if not ok:
            out["failed"] += 1
        elif "ya tenía" in msg or "no tenía" in msg or "sin cambios" in msg:
            out["skipped"] += 1
        else:
            out["modified"] += 1

    return out
