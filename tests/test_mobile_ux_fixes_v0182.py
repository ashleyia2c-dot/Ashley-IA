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
