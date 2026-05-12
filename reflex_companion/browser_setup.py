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

v0.19.6 — Backups antes vivían junto al .lnk original (ej. en el ESCRITORIO
del user, ensuciando), ahora viven en %APPDATA%\\Ashley\\data\\browser_lnk_backups\\
con un nombre que codifica el path original via hash. Migration automática
mueve cualquier .bak suelto del escritorio a la carpeta nueva al primer uso.

NO modifica el .exe del browser, solo los .lnk. Si el user abre el
browser por otro camino (ej: doble click directo en chrome.exe, otra
extensión, "abrir con..." de Windows), CDP no estará activo en esa
sesión — pero la app cae al modo legacy automáticamente. Defensa en
profundidad.

Usa PowerShell + WScript.Shell COM para leer/escribir .lnk. NO requiere
dependencias extra (PowerShell viene con Windows).

v0.19.34 — Audit cleanup:
  • C2: PowerShell injection — escape lnk_path con doubled-single-quote
        (antes folder names con apóstrofe rompían el script entero).
  • C3: status codes estables ("modified"/"already_had_flag"/"no_flag"/"failed")
        en vez de string match en mensajes ES (que se rompía si traduciéramos).
  • H1: tempfile.mkstemp en _is_writable_dir (antes la pareja create+unlink
        podía dejar archivos huérfanos por race con antivirus).
  • H2/M6: logging.warning en cada subprocess timeout/exit-non-zero/exception.
  • M1: re-read del .lnk para verificar la escritura cuando stderr non-empty.
  • M2: CDP_FLAG construido desde DEFAULT_CDP_PORT (single source of truth).
  • M5: _shortcut_locations skipea cleanly cuando una env var no existe.
"""

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .browser_cdp import DEFAULT_CDP_PORT


_log = logging.getLogger("ashley.browser_setup")


# v0.19.34 — Single source of truth para el puerto CDP. Antes había dos:
# este módulo y browser_cdp.py — cambiar uno sin el otro era un bug latente.
CDP_FLAG = f"--remote-debugging-port={DEFAULT_CDP_PORT}"


# v0.19.34 (C3) — Status codes estables que devuelve add_cdp_flag /
# remove_cdp_flag. configure_all_shortcuts agrupa por status sin tener
# que parsear los mensajes humanos (que están en español y podrían
# traducirse en el futuro, rompiendo el control flow).
STATUS_MODIFIED = "modified"          # se cambió el .lnk
STATUS_ALREADY_HAD_FLAG = "already"   # add: ya tenía el flag
STATUS_NO_FLAG_TO_REMOVE = "no_flag"  # remove: no tenía flag, nada que quitar
STATUS_FAILED = "failed"              # error de IO, COM, PowerShell, etc.


# Procesos de browsers Chromium-based que soportan CDP. Firefox no
# está aquí porque usa un protocolo distinto (Marionette) — el wizard
# no lo modifica.
_CHROMIUM_EXES = frozenset({
    "chrome.exe", "msedge.exe", "brave.exe",
    "opera.exe", "operagx.exe", "vivaldi.exe",
})


# v0.19.6 — Carpeta donde guardamos los .bak (limpios, en el data dir de Ashley
# en lugar de tirados al lado de cada .lnk original).
def _backup_dir() -> Path:
    from .config import _data_path
    d = Path(_data_path("browser_lnk_backups"))
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception as _e:
        _log.warning("No pude crear backup dir %s: %s", d, _e)
    return d


def _backup_path_for(lnk_path: str) -> Path:
    """Path donde guardamos el .bak del .lnk original.

    Formato: {basename}.{shorthash}.lnk.bak
    El shorthash codifica el path completo para evitar colisiones cuando
    hay 2 shortcuts del mismo browser en sitios distintos (ej: Desktop +
    Start Menu).
    """
    p = Path(lnk_path)
    h = hashlib.sha256(str(p.resolve()).encode("utf-8")).hexdigest()[:8]
    safe_name = p.stem  # "Google Chrome.lnk" → "Google Chrome"
    return _backup_dir() / f"{safe_name}.{h}.lnk.bak"


def _migrate_legacy_backup(lnk_path: str) -> None:
    """v0.19.6 — Si existe un .bak antiguo junto al .lnk (versiones previas),
    lo movemos a la carpeta nueva. Idempotente."""
    legacy = lnk_path + ".bak"
    if not os.path.exists(legacy):
        return
    new_path = _backup_path_for(lnk_path)
    if new_path.exists():
        # Ya migrado en una run anterior: borramos el legacy duplicado
        try:
            os.remove(legacy)
        except Exception as _e:
            _log.warning("No pude borrar legacy backup %s: %s", legacy, _e)
        return
    try:
        shutil.move(legacy, str(new_path))
    except Exception as _e:
        # Si falla el move (permisos), intentar copy + delete
        _log.warning("Move legacy backup %s falló (%s), intentando copy+del", legacy, _e)
        try:
            shutil.copy2(legacy, str(new_path))
            os.remove(legacy)
        except Exception as _e2:
            _log.warning("Copy+del legacy backup %s también falló: %s", legacy, _e2)


def _ps_escape_single_quoted(s: str) -> str:
    """v0.19.34 (C2) — Escape para insertar `s` dentro de un string
    PowerShell single-quoted ('...').

    PowerShell single-quoted: el único carácter especial es `'` (apóstrofe),
    que se escapa duplicándolo (`''`). Backticks, `$`, etc. NO se interpretan.

    Bug previo: paths con apóstrofe (ej. `C:\\Users\\O'Brien\\...`) rompían el
    script de PowerShell entero porque `lnk_path` se interpolaba sin escape.
    """
    return s.replace("'", "''")


def _is_writable_dir(path: Path) -> bool:
    """v0.19.19 — True si el proceso actual puede ESCRIBIR en path.

    Test = intento crear un archivo temporal con tempfile.mkstemp.

    v0.19.34 (H1): antes usábamos `path / f".ashley-write-test-{getpid()}"`
    + `unlink()` manual. Si un antivirus tomaba el archivo entre create
    y unlink, quedaba archivo huérfano + PID podía ser reusado. tempfile
    es atomic y resiste ese race.

    Razón: queremos saltarnos shortcuts en `C:\\ProgramData\\` cuando
    Ashley corre como user (sin admin). Modificar esos `.lnk` requiere
    elevation que no tenemos en perUser install. Sin este filter,
    `find_browser_shortcuts()` los devuelve, `add_cdp_flag()` falla con
    PermissionError, y el user ve "(1 fallaron)" sin entender por qué.
    """
    if not path.exists():
        return False
    try:
        # mkstemp crea + abre + devuelve fd. Es atomic. Cerramos fd y
        # borramos el archivo. Si el unlink falla por antivirus, lo
        # logueamos pero la función igual devuelve True (probamos que
        # podemos escribir, que es lo que queríamos saber).
        fd, tmppath = tempfile.mkstemp(prefix=".ashley-write-test-", dir=str(path))
        os.close(fd)
        try:
            os.unlink(tmppath)
        except OSError as _e:
            _log.warning("No pude limpiar tempfile %s tras write-test: %s", tmppath, _e)
        return True
    except (PermissionError, OSError):
        return False


def _shortcut_locations() -> list[Path]:
    """Carpetas donde Windows guarda shortcuts de aplicaciones.

    v0.19.19 — Filtramos las que no son escribibles por el user actual
    (típicamente C:\\ProgramData\\ sin admin). Estos shortcuts son
    casi siempre duplicados del Start Menu del user, así que filtrarlos
    no pierde funcionalidad y evita el "(N fallaron)" feo en la UI.

    v0.19.34 (M5): si una env var (USERPROFILE/APPDATA/PUBLIC/PROGRAMDATA)
    está vacía o no existe, skipeamos esa location en vez de construir
    `Path("") / "Desktop"` que daba un Path RELATIVO al CWD. Sin esto,
    en entornos raros (servicios Windows, contenedores) escaneábamos el
    CWD random — no peligroso pero ineficiente y confuso.
    """
    home = os.environ.get("USERPROFILE")
    appdata = os.environ.get("APPDATA")
    public = os.environ.get("PUBLIC")
    progdata = os.environ.get("PROGRAMDATA")

    candidates: list[Path] = []
    if home:
        candidates.append(Path(home) / "Desktop")
    if public:
        candidates.append(Path(public) / "Desktop")
    if appdata:
        candidates.append(Path(appdata) / "Microsoft/Windows/Start Menu/Programs")
        # Pinned to taskbar — Windows guarda las shortcuts pinneadas aquí
        # (legacy Quick Launch path; algunos pins de Win10/11 NO están
        # aquí, pero los más antiguos sí — ver M4 en audit notes).
        candidates.append(Path(appdata) / "Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar")
    if progdata:
        candidates.append(Path(progdata) / "Microsoft/Windows/Start Menu/Programs")

    return [p for p in candidates if _is_writable_dir(p)]


def _read_lnks_batch(lnk_paths: list[str]) -> dict[str, dict]:
    """v0.19.35 (M3) — Lee MUCHOS .lnk en UNA sola invocación de PowerShell.

    Antes: `find_browser_shortcuts()` llamaba a `_read_lnk_via_ps` por
    cada .lnk → 1 subprocess Python por .lnk → ~100ms × N. En PCs
    pobladas (300+ shortcuts en Start Menu) eso eran 30-60s con la UI
    bloqueada en el spinner del wizard CDP.

    Ahora: 1 PowerShell process que recibe TODOS los paths via stdin
    (evita los 32KB del límite de command-line de Windows) y los procesa
    con un loop interno. Latencia: ~3-5s para 200 .lnk vs ~30s antes.

    Cada .lnk individual se envuelve en try/catch dentro del script —
    un .lnk corrupto NO rompe el batch entero, solo se omite.

    Returns dict {path: {target, arguments, working_directory}}. Solo
    incluye paths que se leyeron exitosamente (los corruptos/permission
    errors quedan fuera del dict).
    """
    if not lnk_paths:
        return {}

    # PowerShell script: lee paths de stdin, escribe metadata por cada uno.
    # Separador "---" entre entries para parsing seguro.
    ps_script = (
        '$shell = New-Object -ComObject WScript.Shell\n'
        'while ($p = [Console]::In.ReadLine()) {\n'
        '    Write-Output ("PATH=" + $p)\n'
        '    try {\n'
        '        $sc = $shell.CreateShortcut($p)\n'
        '        Write-Output ("TARGET=" + $sc.TargetPath)\n'
        '        Write-Output ("ARGS=" + $sc.Arguments)\n'
        '        Write-Output ("WD=" + $sc.WorkingDirectory)\n'
        '    } catch {\n'
        '        Write-Output ("ERROR=" + $_.Exception.Message)\n'
        '    }\n'
        '    Write-Output "---"\n'
        '}\n'
    )

    # Pasamos paths via stdin separados por newlines. Una entrada por línea.
    # Esto evita el límite de ~32KB del command-line argument de Windows.
    stdin_input = "\n".join(lnk_paths) + "\n"

    # Timeout escala con el batch size: base 8s + 50ms por path.
    # 200 .lnk = 18s timeout cap.
    timeout_seconds = 8.0 + len(lnk_paths) * 0.05

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            input=stdin_input,
            capture_output=True, text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        _log.warning(
            "Batch lnk read timeout (paths=%d, timeout=%.1fs)",
            len(lnk_paths), timeout_seconds,
        )
        return {}
    except Exception as _e:
        _log.warning("Batch lnk read exception (paths=%d): %s", len(lnk_paths), _e)
        return {}

    if result.returncode != 0:
        _log.warning(
            "Batch lnk read failed: rc=%d, stderr=%r",
            result.returncode, (result.stderr or "").strip()[:200],
        )
        return {}

    return _parse_batch_lnk_output(result.stdout)


def _parse_batch_lnk_output(stdout: str) -> dict[str, dict]:
    """Parsea el output del batch reader. Devuelve dict {path: info}.

    Estructura esperada por entry:
        PATH=<path>
        TARGET=<target>      (o ERROR=<msg> si falló)
        ARGS=<args>
        WD=<working_dir>
        ---

    Skipea entries con ERROR= (corruptos) o sin TARGET= (parse rota).
    """
    result: dict[str, dict] = {}
    current_path: Optional[str] = None
    current: dict = {}
    had_error = False

    for raw_line in stdout.split("\n"):
        line = raw_line.rstrip("\r")
        if line.startswith("PATH="):
            # Reset para nueva entrada
            current_path = line[5:]
            current = {}
            had_error = False
        elif line.startswith("TARGET=") and current_path is not None:
            current["target"] = line[7:]
        elif line.startswith("ARGS=") and current_path is not None:
            current["arguments"] = line[5:]
        elif line.startswith("WD=") and current_path is not None:
            current["working_directory"] = line[3:]
        elif line.startswith("ERROR=") and current_path is not None:
            had_error = True
            _log.warning("Batch read error for %s: %s", current_path, line[6:])
        elif line == "---" and current_path is not None:
            # Cierre de entry — solo añadir si no hubo error y leímos target
            if not had_error and current.get("target") is not None:
                result[current_path] = current
            current_path = None
            current = {}
            had_error = False

    return result


def _read_lnk_via_ps(lnk_path: str) -> Optional[dict]:
    """Lee un .lnk usando WScript.Shell COM via PowerShell.

    Devuelve dict con {target, arguments, working_directory} o None si falla.
    Es la forma estándar de Windows de inspeccionar shortcuts sin librerías
    de terceros.

    v0.19.34 (C2/H2): lnk_path ahora se escapa antes de interpolarlo en el
    script de PowerShell (apóstrofes, etc.) y los timeouts/errores se
    loguean en vez de morir silenciosos.
    """
    safe_path = _ps_escape_single_quoted(lnk_path)
    ps_lines = [
        "$shell = New-Object -ComObject WScript.Shell",
        f"$sc = $shell.CreateShortcut('{safe_path}')",
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
    except subprocess.TimeoutExpired:
        _log.warning("PowerShell timeout leyendo .lnk %s (>5s)", lnk_path)
        return None
    except Exception as _e:
        _log.warning("PowerShell exception leyendo .lnk %s: %s", lnk_path, _e)
        return None

    if result.returncode != 0:
        _log.warning(
            "PowerShell falló leyendo .lnk %s: rc=%d, stderr=%r",
            lnk_path, result.returncode, (result.stderr or "").strip()[:200],
        )
        return None

    out: dict[str, str] = {}
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("TARGET="):
            out["target"] = line[7:]
        elif line.startswith("ARGS="):
            out["arguments"] = line[5:]
        elif line.startswith("WD="):
            out["working_directory"] = line[3:]
    return out


def _write_lnk_args_via_ps(lnk_path: str, new_args: str) -> bool:
    """Escribe los nuevos arguments al .lnk vía WScript.Shell COM.
    Returns True si la operación fue exitosa.

    v0.19.34 (C2/H2/M1): lnk_path ahora se escapa con doubled-single-quote
    igual que safe_args; timeouts/errores se loguean; y si stderr de
    PowerShell trae cualquier output (señal de COM warning aunque
    rc=0), re-leemos el .lnk para verificar que la escritura persistió.
    """
    safe_path = _ps_escape_single_quoted(lnk_path)
    safe_args = _ps_escape_single_quoted(new_args)
    ps_lines = [
        "$shell = New-Object -ComObject WScript.Shell",
        f"$sc = $shell.CreateShortcut('{safe_path}')",
        f"$sc.Arguments = '{safe_args}'",
        "$sc.Save()",
    ]
    ps_script = "; ".join(ps_lines)
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True, text=True, timeout=5,
        )
    except subprocess.TimeoutExpired:
        _log.warning("PowerShell timeout escribiendo .lnk %s (>5s)", lnk_path)
        return False
    except Exception as _e:
        _log.warning("PowerShell exception escribiendo .lnk %s: %s", lnk_path, _e)
        return False

    if result.returncode != 0:
        _log.warning(
            "PowerShell falló escribiendo .lnk %s: rc=%d, stderr=%r",
            lnk_path, result.returncode, (result.stderr or "").strip()[:200],
        )
        return False

    # M1 — Si stderr trae output (warning COM, archivo bloqueado, etc.)
    # aunque rc=0, verificamos releyendo. Sin esto, "rc=0 + stderr no
    # vacío" nos hacía retornar True optimistamente y luego el flag
    # nunca aparecía en el .lnk → user ve "modificado" pero CDP no
    # funciona al reabrir browser.
    stderr_clean = (result.stderr or "").strip()
    if stderr_clean:
        _log.warning(
            "PowerShell rc=0 pero stderr non-empty al escribir %s: %r",
            lnk_path, stderr_clean[:200],
        )
        verify = _read_lnk_via_ps(lnk_path)
        if verify is None:
            _log.warning("Verify post-write: no pude releer %s", lnk_path)
            return False
        # Normalizar whitespace para comparación (PowerShell puede meter
        # espacios extra al guardar).
        wrote_norm = " ".join(new_args.split())
        read_norm = " ".join((verify.get("arguments") or "").split())
        if wrote_norm != read_norm:
            _log.warning(
                "Verify post-write: escribimos %r pero leemos %r en %s",
                wrote_norm, read_norm, lnk_path,
            )
            return False

    return True


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

    v0.19.35 (M3): rediseño en 2 fases. Antes 1 subprocess PowerShell por
    .lnk encontrado (~100ms × N) → 30-60s en PCs pobladas. Ahora:
      • Fase 1 — recolectar TODOS los paths .lnk (Python file system,
        millisegundos)
      • Fase 2 — leer metadata de todos en UN SOLO batch PowerShell
        (~3-5s para 200 .lnk)
      • Fase 3 — filtrar a Chromium browsers en Python (instantáneo)

    Resultado típico: ~3-5s en PCs pobladas (antes 30s+).
    """
    # ── Fase 1: recolectar paths .lnk únicos
    all_lnk_paths: list[str] = []
    seen_paths: set[str] = set()
    for loc in _shortcut_locations():
        if not loc.exists():
            continue
        try:
            for lnk in loc.rglob("*.lnk"):
                lnk_str = str(lnk)
                if lnk_str not in seen_paths:
                    seen_paths.add(lnk_str)
                    all_lnk_paths.append(lnk_str)
        except Exception as _e:
            _log.warning("rglob falló en %s: %s", loc, _e)
            continue

    if not all_lnk_paths:
        return []

    # ── Fase 2: batch read (1 subprocess para TODOS los paths)
    info_by_path = _read_lnks_batch(all_lnk_paths)

    # ── Fase 3: filtrar a browsers Chromium y construir resultado
    found: list[dict] = []
    for lnk_str in all_lnk_paths:
        info = info_by_path.get(lnk_str)
        if not info:
            continue  # batch read falló para este .lnk (corrupto/permisos)
        try:
            target = (info.get("target") or "").strip()
            if not target:
                continue
            exe_name = Path(target).name.lower()
            if exe_name not in _CHROMIUM_EXES:
                continue
            args = info.get("arguments") or ""
            # v0.19.6 — limpieza opportunistic de .bak legacy junto al .lnk.
            _migrate_legacy_backup(lnk_str)
            found.append({
                "path": lnk_str,
                "browser": _browser_friendly_name(exe_name),
                "target_exe": exe_name,
                "has_cdp_flag": CDP_FLAG in args,
                "arguments": args,
            })
        except Exception as _e:
            _log.warning("Error procesando .lnk %s: %s", lnk_str, _e)
            continue
    return found


def add_cdp_flag(lnk_path: str) -> tuple[bool, str, str]:
    """Añade --remote-debugging-port=9222 al Arguments del .lnk.

    Si el flag ya está, no hace nada (idempotente).
    Hace backup automático en `%APPDATA%\\Ashley\\data\\browser_lnk_backups\\`
    la primera vez (no sobrescribe backups existentes — preserva el
    "estado original original").

    v0.19.6 — Antes los .bak se quedaban tirados en el escritorio del user
    junto a sus .lnk originales. Ahora van todos a la carpeta de Ashley.

    Returns (ok, mensaje legible, status_code).
    status_code es uno de:
      • STATUS_MODIFIED        — flag añadido OK
      • STATUS_ALREADY_HAD_FLAG — ya tenía el flag, no se tocó
      • STATUS_FAILED          — error de IO/COM/permisos

    v0.19.34 (C3): se añade status_code para que configure_all_shortcuts
    no tenga que matchear strings ES (que pueden traducirse a futuro y
    romper el control flow del contador "skipped").
    """
    # Migrar .bak legacy del escritorio si existe
    _migrate_legacy_backup(lnk_path)

    info = _read_lnk_via_ps(lnk_path)
    if not info:
        return False, f"No pude leer el shortcut: {Path(lnk_path).name}", STATUS_FAILED

    args = (info.get("arguments") or "").strip()
    if CDP_FLAG in args:
        return (
            True,
            f"{Path(lnk_path).name}: ya tenía el flag, sin cambios",
            STATUS_ALREADY_HAD_FLAG,
        )

    # Backup (solo la primera vez — preserve el "antes de Ashley")
    bak_path = _backup_path_for(lnk_path)
    try:
        if not bak_path.exists():
            shutil.copy2(lnk_path, str(bak_path))
    except Exception as e:
        _log.warning("No pude hacer backup de %s: %s", lnk_path, e)
        return False, f"No pude hacer backup: {e}", STATUS_FAILED

    new_args = (args + " " + CDP_FLAG).strip() if args else CDP_FLAG
    if not _write_lnk_args_via_ps(lnk_path, new_args):
        return (
            False,
            f"No pude escribir el shortcut: {Path(lnk_path).name}",
            STATUS_FAILED,
        )

    return True, f"{Path(lnk_path).name}: flag añadido", STATUS_MODIFIED


def remove_cdp_flag(lnk_path: str) -> tuple[bool, str, str]:
    """Quita --remote-debugging-port=9222 del Arguments del .lnk.

    Si el .bak existe, lo restauramos (más seguro que un replace
    parcial). Si no, hacemos string replacement.

    v0.19.6 — busca el .bak en la carpeta nueva (data dir) primero, luego
    en la legacy location (al lado del .lnk original) por compatibilidad
    con instalaciones de versiones anteriores.

    Returns (ok, mensaje, status_code).
    status_code es uno de:
      • STATUS_MODIFIED          — flag quitado OK
      • STATUS_NO_FLAG_TO_REMOVE — no tenía flag, nada que hacer
      • STATUS_FAILED            — error de IO/COM/permisos
    """
    # Migrar .bak legacy del escritorio si existe (también en este path)
    _migrate_legacy_backup(lnk_path)

    bak_path = _backup_path_for(lnk_path)
    if bak_path.exists():
        try:
            shutil.copy2(str(bak_path), lnk_path)
            return (
                True,
                f"{Path(lnk_path).name}: restaurado desde backup",
                STATUS_MODIFIED,
            )
        except Exception as e:
            _log.warning("No pude restaurar backup de %s: %s", lnk_path, e)
            return False, f"No pude restaurar backup: {e}", STATUS_FAILED

    # Sin backup: string replace defensivo
    info = _read_lnk_via_ps(lnk_path)
    if not info:
        return False, f"No pude leer el shortcut: {Path(lnk_path).name}", STATUS_FAILED

    args = (info.get("arguments") or "")
    if CDP_FLAG not in args:
        return (
            True,
            f"{Path(lnk_path).name}: no tenía el flag, sin cambios",
            STATUS_NO_FLAG_TO_REMOVE,
        )

    new_args = args.replace(CDP_FLAG, "")
    new_args = " ".join(new_args.split())  # dedup spaces

    if not _write_lnk_args_via_ps(lnk_path, new_args):
        return (
            False,
            f"No pude escribir el shortcut: {Path(lnk_path).name}",
            STATUS_FAILED,
        )

    return True, f"{Path(lnk_path).name}: flag quitado", STATUS_MODIFIED


def configure_all_shortcuts(enable: bool) -> dict:
    """Activa/desactiva el flag CDP en TODOS los shortcuts de browsers
    Chromium encontrados.

    Returns dict con resumen:
      {
        "shortcuts": [{"name", "browser", "ok", "message", "status"}, ...],
        "modified": int,    # cuántos cambiaron de estado
        "skipped": int,     # cuántos ya estaban como queríamos
        "failed": int,      # cuántos fallaron
        "total": int,       # cuántos shortcuts en total
      }

    v0.19.34 (C3): el conteo de "skipped" usa el status_code que devuelven
    add_cdp_flag/remove_cdp_flag, no string match en mensajes ES.
    """
    shortcuts = find_browser_shortcuts()
    out: dict = {
        "shortcuts": [],
        "modified": 0,
        "skipped": 0,
        "failed": 0,
        "total": len(shortcuts),
    }

    for s in shortcuts:
        if enable:
            ok, msg, status = add_cdp_flag(s["path"])
        else:
            ok, msg, status = remove_cdp_flag(s["path"])

        out["shortcuts"].append({
            "name": Path(s["path"]).name,
            "browser": s["browser"],
            "path": s["path"],
            "ok": ok,
            "message": msg,
            "status": status,
        })

        if status == STATUS_FAILED:
            out["failed"] += 1
        elif status in (STATUS_ALREADY_HAD_FLAG, STATUS_NO_FLAG_TO_REMOVE):
            out["skipped"] += 1
        else:  # STATUS_MODIFIED
            out["modified"] += 1

    return out
