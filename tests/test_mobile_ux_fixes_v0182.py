"""Guards de los 4 bugs UX del móvil (v0.18.2 final final).

1. Mensajes duplicados (3-4 veces) — appendMessage debe dedupe por data-id
2. Avatar de Ashley NO se ve — fix: usar ./ashley_pfp.jpg local, no serverUrl
3. Último mensaje queda OCULTO bajo el teclado — auto-scroll en focus +
   visualViewport.resize
4. Icono de la app es default Android — workflow genera desde ashley_pfp.jpg
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_JS = ROOT / "assets" / "mobile" / "app.js"
WORKFLOW = ROOT / ".github" / "workflows" / "build-android-apk.yml"


# ─────────────────────────────────────────────
#  Bug 1 — Dedupe en appendMessage
# ─────────────────────────────────────────────

def test_append_message_dedupes_by_data_id():
    """Sin dedupe, polling + optimistic + handleSend response añadían
    el mismo mensaje 3-4 veces. appendMessage debe chequear si data-id
    ya existe en el DOM antes de añadir."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function appendMessage\(msg\)[\s\S]+?(?=\n  function |\n  async function )",
        src,
    )
    assert section, "appendMessage no encontrado"
    body = section.group(0)
    # Debe buscar elemento existente con el mismo data-id
    assert "data-id" in body and "querySelector" in body, (
        "appendMessage debe usar querySelector con [data-id=...] para dedupe"
    )
    # Estructura típica: const existing = chatEl.querySelector('[data-id="..."]'); if (existing) { ... return; }
    assert "if (existing)" in body or "if(existing)" in body, (
        "Tras encontrar elemento existente, debe haber un if (existing) {...}"
    )
    # Y dentro debe haber return para skip añadir duplicado
    if_existing_block = body.split("if (existing)" if "if (existing)" in body else "if(existing)")[1]
    # En los próximos 30 lines debe haber return
    next_lines = "\n".join(if_existing_block.split("\n")[:15])
    assert "return" in next_lines, (
        "if (existing) debe contener return para skip añadir duplicado"
    )


def test_append_message_uses_css_escape_for_data_id():
    """data-id puede contener caracteres especiales (timestamps con :).
    Debe usar CSS.escape para construir el selector."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function appendMessage\(msg\)[\s\S]+?(?=\n  function )",
        src,
    )
    body = section.group(0)
    assert "CSS.escape" in body, (
        "appendMessage debe usar CSS.escape(msgId) para escapar selector "
        "(IDs como 'mobile-u-2026-05-07T00:00:00' tienen ':' que romperían "
        "el querySelector)"
    )


# ─────────────────────────────────────────────
#  Bug 2 — Avatar local
# ─────────────────────────────────────────────

def test_avatar_uses_local_path_not_server():
    """v0.18.2 — el avatar debe cargarse del bundle local (./ashley_pfp.jpg),
    NO de serverUrl + '/ashley_pfp.jpg'. Con Cloudflare tunnel, serverUrl
    apunta al backend que NO sirve estáticos del frontend → avatar 404."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function appendMessage\(msg\)[\s\S]+?(?=\n  function )",
        src,
    )
    body = section.group(0)
    # Strip line-comments para no matchear texto explicativo
    code_only = "\n".join(
        line for line in body.splitlines()
        if not line.strip().startswith("//")
    )
    # NO debe usar serverUrl para el avatar
    assert "serverUrl + '/ashley_pfp" not in code_only and "serverUrl + \"/ashley_pfp" not in code_only, (
        "Avatar NO debe construir URL desde serverUrl (no funciona con Cloudflare tunnel)"
    )
    # SÍ debe usar path local
    assert "'./ashley_pfp.jpg'" in code_only or '"./ashley_pfp.jpg"' in code_only, (
        "Avatar debe usar './ashley_pfp.jpg' (path relativo del bundle Capacitor)"
    )


# ─────────────────────────────────────────────
#  Bug 3 — Auto-scroll con teclado
# ─────────────────────────────────────────────

def test_input_focus_triggers_scroll():
    """Cuando el user toca el textarea (foco) → teclado abre → debe
    auto-scroll para que el último mensaje quede visible arriba del teclado."""
    src = APP_JS.read_text(encoding="utf-8")
    pattern = re.compile(
        r"inputEl\.addEventListener\('focus'[\s\S]+?\}\);",
    )
    m = pattern.search(src)
    assert m, "Falta listener inputEl 'focus' para scroll al abrir teclado"
    body = m.group(0)
    assert "scrollToBottom" in body, (
        "El listener focus debe llamar scrollToBottom"
    )


def test_visual_viewport_resize_triggers_scroll():
    """visualViewport.resize dispara cuando teclado abre/cierra (Android).
    Si el viewport se hace MÁS PEQUEÑO (teclado abrió), scroll al fondo
    para que el último mensaje no quede tapado."""
    src = APP_JS.read_text(encoding="utf-8")
    assert "visualViewport" in src, (
        "Falta listener visualViewport.resize para detectar apertura del teclado"
    )
    section = re.search(
        r"visualViewport\.addEventListener\('resize'[\s\S]+?\}\);",
        src,
    )
    assert section
    body = section.group(0)
    assert "scrollToBottom" in body, (
        "Listener visualViewport.resize debe scrollear al fondo cuando "
        "el teclado abre"
    )


def test_scroll_to_bottom_uses_double_raf():
    """El scroll debe esperar al menos 2 frames de animación antes de
    aplicar scrollTop, sino el scroll ocurre antes del paint del teclado
    y queda mal posicionado en Android."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function scrollToBottom\(\)\s*\{[\s\S]+?\n  \}",
        src,
    )
    assert section
    body = section.group(0)
    raf_count = body.count("requestAnimationFrame")
    assert raf_count >= 2, (
        f"scrollToBottom debe usar doble requestAnimationFrame (encontrados: {raf_count}) "
        "para garantizar que ocurre tras el paint del teclado"
    )


# ─────────────────────────────────────────────
#  Bug 4 — Icono APK desde ashley_pfp.jpg
# ─────────────────────────────────────────────

def test_workflow_replaces_app_icon():
    """El workflow debe tener un step que regenera ic_launcher.png en todos
    los mipmap-* desde assets/ashley_pfp.jpg."""
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "Replace default app icon" in src, (
        "Workflow debe tener step 'Replace default app icon'"
    )
    assert "ashley_pfp.jpg" in src, (
        "Workflow debe usar ashley_pfp.jpg como source"
    )


def test_workflow_uses_pregenerated_icons():
    """v0.18.2 — los iconos están PRE-GENERADOS en android-overrides/icons/
    (commiteados al repo) y el workflow solo hace cp. Antes intentaba
    usar ImageMagick que NO está pre-instalado en runners ubuntu-latest
    de GitHub Actions (verificado en build #25518234900) — fallaba con
    "ImageMagick no disponible, skipping" silencioso."""
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "android-overrides/icons" in src, (
        "Workflow debe copiar iconos pre-generados de android-overrides/icons/"
    )
    assert "ICONS_SRC" in src or "cp \"" in src, (
        "Workflow debe usar cp en lugar de generar iconos en CI"
    )

    # Verificar que los iconos pre-generados existen en el repo
    icons_dir = ROOT / "mobile-app" / "android-overrides" / "icons"
    assert icons_dir.is_dir(), (
        "Falta dir mobile-app/android-overrides/icons/ con iconos pre-generados"
    )
    densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
    for d in densities:
        icon = icons_dir / f"mipmap-{d}" / "ic_launcher.png"
        assert icon.is_file(), f"Falta icono pre-generado: {icon}"


def test_workflow_generates_all_mipmap_sizes():
    """Android necesita 5 tamaños: mdpi (48), hdpi (72), xhdpi (96),
    xxhdpi (144), xxxhdpi (192). Sin todos, algunos devices muestran
    icono pixelado o default."""
    src = WORKFLOW.read_text(encoding="utf-8")
    # Buscar la sección del step de iconos
    section = re.search(
        r"Replace default app icon[\s\S]+?(?=\n      - name:|\Z)",
        src,
    )
    assert section
    body = section.group(0)
    expected_densities = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
    for d in expected_densities:
        assert d in body, (
            f"Workflow no genera icono para density '{d}' — Android lo "
            f"renderiza pixelado en devices de esa densidad"
        )


def test_workflow_generates_round_icon_variant():
    """Android 7.1+ usa ic_launcher_round.png para launchers que muestran
    iconos circulares (samsung One UI, Pixel launcher)."""
    src = WORKFLOW.read_text(encoding="utf-8")
    assert "ic_launcher_round" in src, (
        "Workflow debe generar ic_launcher_round.png también"
    )


# ─────────────────────────────────────────────
#  Bug 5 — Teclado parpadea al enviar
# ─────────────────────────────────────────────
#
# Síntoma reportado por el user:
#   "cuando envias un mensaje el teclado en pantalla desaparece y luego
#    reaparece"
#
# Causa: el sendBtn roba el foco al input al hacer click → IME (teclado
# Android) se cierra → handleSend completa → re-focus al input → IME
# reabre. Visible al user como un "parpadeo" del teclado.
#
# Fix: mousedown.preventDefault() en el sendBtn bloquea el cambio de
# foco SIN bloquear el click. + remover el inputEl.focus() del finally.

def test_send_button_prevents_focus_steal():
    """sendBtn debe tener listener mousedown que llama preventDefault para
    que no robe el foco al input → teclado NO parpadea al enviar."""
    src = APP_JS.read_text(encoding="utf-8")
    # mousedown SIN cambio de focus (single line, ".*" ok)
    pattern_mouse = re.compile(
        r"sendBtn\.addEventListener\('mousedown'.*preventDefault",
    )
    assert pattern_mouse.search(src), (
        "Falta sendBtn.addEventListener('mousedown', e => e.preventDefault()) — "
        "sin esto el botón roba foco al input → teclado parpadea al enviar"
    )
    # pointerdown como cobertura para touch + mouse modernos
    pattern_pointer = re.compile(
        r"sendBtn\.addEventListener\('pointerdown'.*preventDefault",
    )
    assert pattern_pointer.search(src), (
        "Falta sendBtn.addEventListener('pointerdown', e => e.preventDefault()) — "
        "cubre touch+mouse en WebViews modernos"
    )


def test_handle_send_does_not_refocus_input():
    """v0.18.2 — el finally de handleSend NO debe llamar inputEl.focus().
    El input nunca pierde el foco gracias al mousedown.preventDefault del
    sendBtn → re-focus causaba el parpadeo del teclado (Android oculta
    e re-muestra el IME al focusear lo que ya estaba focused)."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"async function handleSend\(\)[\s\S]+?\n  \}",
        src,
    )
    assert section, "handleSend no encontrado"
    body = section.group(0)
    # Buscar el bloque finally específicamente
    finally_match = re.search(r"\}\s*finally\s*\{([\s\S]+?)\}\s*\}", body)
    assert finally_match, "Falta bloque finally en handleSend"
    finally_body = finally_match.group(1)
    # Strip comentarios para no matchear texto explicativo
    code_only = "\n".join(
        line for line in finally_body.splitlines()
        if not line.strip().startswith("//")
    )
    assert "inputEl.focus()" not in code_only, (
        "handleSend.finally NO debe llamar inputEl.focus() — causa parpadeo "
        "del teclado en Android cuando el input ya estaba focused"
    )


# ─────────────────────────────────────────────
#  Bug 6 — Re-emparejado cada arranque (localStorage limpiado por OS)
# ─────────────────────────────────────────────
#
# Síntoma reportado por el user:
#   "lo normal es no tener que poner el qr cada vez que entres en la app"
#
# Causa: Android WebView CAN limpiar localStorage en low-memory, después
# de updates del APK con android:fullBackupContent, o si el user hizo
# "clear cache" manual. La data crítica (server URL, token) se perdía.
#
# Fix: usar @capacitor/preferences (SharedPreferences nativo) además de
# localStorage. localStorage queda como cache sync para reads en hot
# paths; Preferences es la fuente de verdad persistente.

def test_capacitor_preferences_dependency_present():
    """mobile-app/package.json debe tener @capacitor/preferences."""
    pkg = ROOT / "mobile-app" / "package.json"
    src = pkg.read_text(encoding="utf-8")
    assert "@capacitor/preferences" in src, (
        "Falta dep @capacitor/preferences en mobile-app/package.json — "
        "necesaria para persistir token + server URL entre arranques"
    )


def test_persisted_set_helper_exists():
    """app.js debe tener helper _persistedSet que escribe a Preferences
    Y localStorage. Sin esto, el OS puede borrar localStorage entre
    arranques y el user tendría que re-escanear el QR."""
    src = APP_JS.read_text(encoding="utf-8")
    assert "function _persistedSet" in src, (
        "Falta helper _persistedSet(key, value) en app.js"
    )
    assert "function _persistedRemove" in src, (
        "Falta helper _persistedRemove(key) en app.js"
    )
    assert "Capacitor.Plugins.Preferences" in src or "C.Plugins.Preferences" in src, (
        "Helper _persistedSet debe usar @capacitor/preferences (no solo localStorage)"
    )


def test_critical_keys_use_persisted_set():
    """Las 4 keys críticas (server URL, token, LAN IP, backend port) NO
    deben escribirse SOLO con localStorage.setItem — eso es lo que se
    pierde entre arranques. Deben pasar por _persistedSet."""
    src = APP_JS.read_text(encoding="utf-8")
    critical_keys = [
        "STORE_SERVER_URL",
        "STORE_TOKEN",
        "STORE_LAN_IP",
        "STORE_BACKEND_PORT",
    ]
    # Buscar setItem(STORE_SERVER_URL...) directo — debería ser CERO
    for key in critical_keys:
        bad = re.findall(
            rf"localStorage\.setItem\(\s*{key}\s*[,)]",
            src,
        )
        assert not bad, (
            f"Encontrado localStorage.setItem({key}, ...) directo en app.js — "
            f"debe usar _persistedSet({key}, ...) para que SharedPreferences "
            f"también lo guarde y persista entre arranques de la app"
        )
        bad_remove = re.findall(
            rf"localStorage\.removeItem\(\s*{key}\s*\)",
            src,
        )
        assert not bad_remove, (
            f"Encontrado localStorage.removeItem({key}) directo — debe usar "
            f"_persistedRemove({key}) para limpiar también de Preferences"
        )


def test_msg_input_autocomplete_is_on_for_ime_suggestions():
    """v0.18.2-r2 — el msg-input debe tener autocomplete="on" (NO "off").
    El user confirmó que en Chrome standalone SÍ aparecen sugerencias de
    Gboard, pero en el WebView de Capacitor no — causa: WebView Android
    traduce autocomplete="off" como IME_FLAG_NO_PERSONALIZED_LEARNING que
    suprime sugerencias predictivas (no solo el autofill bar como en
    Chrome standalone). Cambiar a "on" hace que el IME muestre la barra
    de palabras predictivas normalmente."""
    html_path = ROOT / "assets" / "mobile" / "index.html"
    src = html_path.read_text(encoding="utf-8")
    # Buscar la zona del input msg-input
    section = re.search(
        r'<input[^>]*id="msg-input"[^>]*/?>',
        src,
        re.DOTALL,
    )
    assert section, "No se encuentra input#msg-input en index.html"
    body = section.group(0)
    assert 'autocomplete="off"' not in body, (
        'msg-input NO debe tener autocomplete="off" — en WebView Capacitor '
        'eso suprime las sugerencias predictivas del IME. Usar "on" para '
        'que Gboard muestre la barra de palabras como en Chrome standalone.'
    )
    assert 'autocomplete="on"' in body, (
        'msg-input debe tener autocomplete="on" para que el WebView Android '
        'permita al IME mostrar sugerencias predictivas (palabras, autocorrect).'
    )


# ─────────────────────────────────────────────
#  Bug 7 — Teclado desaparece cuando Ashley responde
# ─────────────────────────────────────────────
#
# Síntoma reportado por el user:
#   "el teclado desaparece cuando ashley responde"
#
# Causa: cuando Ashley responde por polling, appendMessage añade nodos
# al chatEl y scrollToBottom modifica chatEl.scrollTop. En Android
# WebView esto puede hacer que el input pierda el foco → IME se cierra.
# Justo cuando el user estaba escribiendo a la mid-frase.
#
# Fix: capturar document.activeElement === inputEl ANTES de cada mutación
# del DOM o scroll. Si el input lo perdió, restaurar con
# focus({preventScroll: true}) — sin causar parpadeo.

def test_restore_focus_helper_exists():
    """Debe existir el helper _restoreFocusIfWas para restaurar el foco
    del input tras mutaciones del DOM/scroll que el WebView pueda haber
    interrumpido."""
    src = APP_JS.read_text(encoding="utf-8")
    assert "function _restoreFocusIfWas" in src, (
        "Falta helper _restoreFocusIfWas(wasFocused) en app.js"
    )
    # Debe usar preventScroll para evitar loop visual con scrollToBottom
    section = re.search(
        r"function _restoreFocusIfWas[\s\S]+?\n  \}",
        src,
    )
    assert section, "Helper _restoreFocusIfWas no encontrado"
    body = section.group(0)
    assert "preventScroll" in body, (
        "_restoreFocusIfWas debe usar focus({preventScroll: true}) — sino "
        "causa scroll/parpadeo extra cuando se llama después de scrollToBottom"
    )


def test_append_message_preserves_input_focus():
    """appendMessage debe capturar el foco antes de mutar el DOM y
    restaurarlo después si lo perdió. Sin esto, el teclado se cierra
    cuando llega la respuesta de Ashley mientras el user escribe."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function appendMessage\(msg\)[\s\S]+?\n  \}\n",
        src,
    )
    assert section, "appendMessage no encontrado"
    body = section.group(0)
    assert "document.activeElement === inputEl" in body, (
        "appendMessage debe capturar activeElement === inputEl ANTES de "
        "mutar el DOM"
    )
    assert "_restoreFocusIfWas" in body, (
        "appendMessage debe llamar _restoreFocusIfWas al final para "
        "restaurar el foco si el WebView lo perdió"
    )


def test_scroll_to_bottom_preserves_input_focus():
    """scrollToBottom modifica chatEl.scrollTop, lo que en Android WebView
    puede hacer que el input pierda el foco. Debe restaurarlo."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function scrollToBottom\(\)\s*\{[\s\S]+?\n  \}",
        src,
    )
    assert section
    body = section.group(0)
    assert "_restoreFocusIfWas" in body, (
        "scrollToBottom debe llamar _restoreFocusIfWas tras modificar "
        "scrollTop — sino el teclado se cierra al recibir respuesta"
    )


# ─────────────────────────────────────────────
#  Bug 8 — Hitboxes pequeños (no apto para móvil)
# ─────────────────────────────────────────────
#
# Síntoma reportado por el user:
#   "los botones deberian ser mas grande la hitbox osea es un celular"
#
# Estándar Material Design: 48dp mínimo. Apple HIG: 44pt. W3C WCAG 2.5.5
# (Target Size): 44 CSS pixels mínimo para tap targets.

def test_icon_btn_hitbox_at_least_48px():
    """v0.18.2-r3 — .icon-btn (cerrar overlay, settings, memorias) debe
    ser al menos 48x48px. Antes era 38x38 → muchos missclicks."""
    css_path = ROOT / "assets" / "mobile" / "app.css"
    src = css_path.read_text(encoding="utf-8")
    section = re.search(
        r"\.icon-btn\s*\{[^}]+\}",
        src,
    )
    assert section
    body = section.group(0)
    # Buscar width: Npx height: Npx
    m_w = re.search(r"width:\s*(\d+)px", body)
    m_h = re.search(r"height:\s*(\d+)px", body)
    assert m_w and m_h, ".icon-btn debe tener width y height en px"
    w = int(m_w.group(1))
    h = int(m_h.group(1))
    assert w >= 48 and h >= 48, (
        f".icon-btn es {w}x{h}px — debe ser al menos 48x48 (Material Design "
        f"recomienda 48dp para tap targets en móvil)"
    )


def test_send_btn_hitbox_at_least_48px():
    """v0.18.2-r3 — .send-btn (botón enviar mensaje) debe ser ≥48x48px."""
    css_path = ROOT / "assets" / "mobile" / "app.css"
    src = css_path.read_text(encoding="utf-8")
    section = re.search(
        r"\.send-btn\s*\{[^}]+\}",
        src,
    )
    assert section
    body = section.group(0)
    m_w = re.search(r"width:\s*(\d+)px", body)
    m_h = re.search(r"height:\s*(\d+)px", body)
    assert m_w and m_h
    w = int(m_w.group(1))
    h = int(m_h.group(1))
    assert w >= 48 and h >= 48, (
        f".send-btn es {w}x{h}px — debe ser al menos 48x48"
    )


def test_msg_input_height_at_least_48px():
    """v0.18.2-r3 — el input del chat debe tener height ≥48px para
    que sea cómodo de tap y consistente con .send-btn."""
    css_path = ROOT / "assets" / "mobile" / "app.css"
    src = css_path.read_text(encoding="utf-8")
    section = re.search(
        r"#msg-input\s*\{[^}]+\}",
        src,
    )
    assert section
    body = section.group(0)
    m_h = re.search(r"height:\s*(\d+)px", body)
    assert m_h, "#msg-input debe tener height en px"
    h = int(m_h.group(1))
    assert h >= 48, (
        f"#msg-input es {h}px alto — debe ser al menos 48px"
    )


def test_msg_input_font_size_prevents_ios_zoom():
    """En iOS Safari, inputs con font-size <16px disparan auto-zoom al
    focusear → UX horrible. font-size: 16px o más previene esto."""
    css_path = ROOT / "assets" / "mobile" / "app.css"
    src = css_path.read_text(encoding="utf-8")
    section = re.search(
        r"#msg-input\s*\{[^}]+\}",
        src,
    )
    assert section
    body = section.group(0)
    m_fs = re.search(r"font-size:\s*(\d+)px", body)
    assert m_fs
    fs = int(m_fs.group(1))
    assert fs >= 16, (
        f"#msg-input font-size es {fs}px — debe ser ≥16px para evitar "
        f"auto-zoom de iOS al focusear el input"
    )


def test_boot_restores_from_preferences():
    """En el init (al cargar la app), debe await _restoreFromPreferences()
    ANTES de tryConnect() para rehidratar el localStorage si el OS lo
    limpió entre arranques."""
    src = APP_JS.read_text(encoding="utf-8")
    # Buscar el bloque init final
    init_section = re.search(
        r"// ─── Init ─+[\s\S]+?\}\)\(\);\s*\}\)\(\);",
        src,
    )
    assert init_section, "No se encuentra el bloque ─── Init ───"
    body = init_section.group(0)
    assert "_restoreFromPreferences" in body, (
        "El init debe llamar await _restoreFromPreferences() para rehidratar "
        "config crítica desde SharedPreferences si localStorage está vacío"
    )
    assert "tryConnect" in body, (
        "El init debe llamar tryConnect() después de la rehidratación"
    )
