"""Guards para el botón + dialog de "Conectar móvil" (v0.18.2).

El botón vive en _top_nav_bar() de components.py y abre un rx.dialog.root
que muestra QR + datos manuales para que el user paree su móvil con
Ashley Mobile (Android).

Tests cubren:
  • i18n keys exist en es/en/fr
  • State vars + métodos están definidos
  • _top_nav_bar incluye el link "smartphone"
  • mobile_pair_dialog() es importable
  • Métodos llaman a los endpoints correctos (qr_payload + regen_token)

También: settings panel de Modo offline en assets/mobile/index.html y app.js.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_PY = ROOT / "reflex_companion" / "components.py"
MAIN_PY = ROOT / "reflex_companion" / "reflex_companion.py"
I18N_PY = ROOT / "reflex_companion" / "i18n.py"
MOBILE_HTML = ROOT / "assets" / "mobile" / "index.html"
MOBILE_JS = ROOT / "assets" / "mobile" / "app.js"
MOBILE_CSS = ROOT / "assets" / "mobile" / "app.css"


# ─────────────────────────────────────────────
#  i18n keys (es/en/fr)
# ─────────────────────────────────────────────

REQUIRED_I18N_KEYS = [
    "pill_mobile_pair",
    "mobile_pair_title",
    "mobile_pair_subtitle",
    "mobile_pair_manual",
    "mobile_pair_server",
    "mobile_pair_token",
    "mobile_pair_regen",
    "mobile_pair_close",
]


@pytest.mark.parametrize("key", REQUIRED_I18N_KEYS)
def test_i18n_keys_in_all_languages(key):
    """Cada key debe estar en es, en, fr — sino el botón cambia de idioma roto."""
    src = I18N_PY.read_text(encoding="utf-8")
    # Cada idioma tiene su propio dict; buscamos al menos 3 ocurrencias
    occurrences = src.count(f'"{key}":')
    assert occurrences >= 3, (
        f"i18n key {key!r} solo aparece {occurrences}/3 veces (es+en+fr requeridas)"
    )


# ─────────────────────────────────────────────
#  State vars + métodos
# ─────────────────────────────────────────────

REQUIRED_STATE_VARS = [
    "show_mobile_pair",
    "mobile_pair_server",
    "mobile_pair_token",
    "mobile_pair_lan_ip",
    "mobile_pair_qr_url",
    "mobile_pair_loading",
    "mobile_pair_error",
]


@pytest.mark.parametrize("var", REQUIRED_STATE_VARS)
def test_state_var_defined(var):
    src = MAIN_PY.read_text(encoding="utf-8")
    pattern = re.compile(rf"^\s+{var}\s*:\s*\w+\s*=", re.MULTILINE)
    assert pattern.search(src), f"State no define {var!r} (con type annotation + default)"


def test_toggle_mobile_pair_method():
    src = MAIN_PY.read_text(encoding="utf-8")
    # v0.18.2 bug fix — debe ser async + yield para que el spinner aparezca
    # ANTES de cargar el payload (sin yield, la UI nunca renderea loading=True
    # porque toggle síncrono se ejecuta entero antes del próximo render).
    assert "async def toggle_mobile_pair(self)" in src, (
        "toggle_mobile_pair debe ser async — sino el spinner nunca se muestra"
    )
    section = re.search(
        r"async def toggle_mobile_pair[\s\S]+?(?=\n    def |\n    async def |\Z)",
        src,
    )
    assert section
    body = section.group(0)
    assert "yield" in body, (
        "toggle_mobile_pair debe hacer yield tras setear loading=True para "
        "flush UI antes de cargar"
    )
    assert "mobile_pair_loading = True" in body, (
        "toggle_mobile_pair debe setear loading=True al abrir"
    )


def test_set_show_mobile_pair_method():
    """Setter explícito necesario para rx.dialog.root(on_open_change=...)."""
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "def set_show_mobile_pair(self" in src, (
        "Falta setter explícito set_show_mobile_pair (Reflex 0.8.9+ deprecó "
        "auto-setters)"
    )


def test_refresh_method_uses_BACKEND_port_not_frontend():
    """v0.18.2 bug fix CRÍTICO #2 — el dialog QR del desktop construye el
    server URL inline (no via HTTP al endpoint), y AÚN llamaba a
    _detect_frontend_port. El móvil intentaba conectar al puerto del
    frontend Next.js que devuelve 404 para /api/mobile/*.

    Bug raíz "page not found" / "TypeError sin red" reportado v0.18.2:
    no era el endpoint qr_payload (que ya estaba arreglado), era ESTE
    método del State del desktop que tiene su propia copia de la lógica.
    """
    src = MAIN_PY.read_text(encoding="utf-8")
    section = re.search(
        r"def _refresh_mobile_pair_data_local[\s\S]+?(?=\n    def |\n    async def |\Z)",
        src,
    )
    assert section, "_refresh_mobile_pair_data_local no encontrado"
    body = section.group(0)
    assert "_detect_backend_port" in body, (
        "_refresh_mobile_pair_data_local DEBE llamar _detect_backend_port. "
        "Si llama _detect_frontend_port, el QR apunta a Next.js que NO tiene "
        "los endpoints /api/mobile/* → móvil ve 404."
    )
    # Y NO debe seguir importando _detect_frontend_port para el dialog
    assert "_detect_frontend_port" not in body, (
        "_refresh_mobile_pair_data_local NO debe usar _detect_frontend_port — "
        "el dialog del desktop debe usar backend port igual que el endpoint."
    )


def test_refresh_method_uses_local_helpers():
    """v0.18.2 bug fix — el refresh NO debe usar urllib.request.urlopen
    contra el propio backend. Eso bloquea el event loop (mismo proceso) y
    causa timeout. Debe llamar directamente a las funciones helper de
    api_routes (síncronas, locales, sin red)."""
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "def _refresh_mobile_pair_data_local" in src, (
        "Falta _refresh_mobile_pair_data_local — método sin HTTP loopback"
    )
    section = re.search(
        r"def _refresh_mobile_pair_data_local[\s\S]+?(?=\n    def |\n    async def |\Z)",
        src,
    )
    assert section
    body = section.group(0)
    # Debe llamar a las funciones helper directamente
    assert "_read_pairing_token" in body, (
        "_refresh_mobile_pair_data_local debe llamar _read_pairing_token directamente"
    )
    assert "_detect_lan_ip" in body, (
        "_refresh_mobile_pair_data_local debe llamar _detect_lan_ip directamente"
    )
    # backend port (no frontend) — ver test específico de bug fix arriba
    assert "_detect_backend_port" in body, (
        "_refresh_mobile_pair_data_local debe llamar _detect_backend_port directamente"
    )


def test_regenerate_uses_local_token_generation():
    """v0.18.2 bug fix — regenerate NO debe usar urllib.request.urlopen
    contra /api/mobile/regen_token (loopback bloquea event loop). Genera
    el nuevo token directamente con secrets.token_urlsafe."""
    src = MAIN_PY.read_text(encoding="utf-8")
    section = re.search(
        r"async def regenerate_mobile_token[\s\S]+?(?=\n    def |\n    async def |\Z)",
        src,
    )
    assert section
    body = section.group(0)
    assert "secrets.token_urlsafe" in body, (
        "regenerate_mobile_token debe usar secrets.token_urlsafe (no HTTP loopback)"
    )
    # No debe haber urlopen contra propio backend
    assert "urlopen" not in body, (
        "regenerate_mobile_token NO debe usar urlopen — causa deadlock al ser "
        "loopback en el mismo proceso"
    )


def test_no_http_loopback_in_mobile_pair_handlers():
    """REGRESIÓN GUARD CRÍTICO — ningún handler del dialog debe hacer
    urllib.request.urlopen('http://127.0.0.1:...'). Eso es el bug que
    causaba el timeout: HTTP loopback bloquea el event loop del propio
    proceso que tiene que responder."""
    src = MAIN_PY.read_text(encoding="utf-8")
    # Buscar la sección de Mobile pair
    pair_section = re.search(
        r"# ── Mobile pair dialog[\s\S]+?(?=\n    # ── |\n    def toggle_tts)",
        src,
    )
    assert pair_section, "Sección Mobile pair dialog no encontrada"
    body = pair_section.group(0)
    # No debe haber llamadas urlopen contra 127.0.0.1
    bad_pattern = re.compile(
        r"urlopen\([^)]*http://127\.0\.0\.1",
        re.DOTALL,
    )
    assert not bad_pattern.search(body), (
        "Mobile pair handlers NO pueden hacer HTTP loopback a 127.0.0.1 — "
        "deadlockea el event loop del proceso que sirve el endpoint."
    )


# ─────────────────────────────────────────────
#  Componente UI
# ─────────────────────────────────────────────

def test_mobile_pair_dialog_function_exists():
    src = COMPONENTS_PY.read_text(encoding="utf-8")
    assert "def mobile_pair_dialog()" in src


def test_mobile_pair_dialog_uses_state_vars():
    src = COMPONENTS_PY.read_text(encoding="utf-8")
    section = re.search(
        r"def mobile_pair_dialog\(\)[\s\S]+?(?=\ndef |\Z)", src
    )
    assert section
    body = section.group(0)
    for var in ("State.show_mobile_pair", "State.mobile_pair_qr_url",
                "State.mobile_pair_server", "State.mobile_pair_token"):
        assert var in body, f"mobile_pair_dialog no usa {var}"


def test_close_mobile_pair_method_exists():
    """Método explícito para cerrar — necesario porque rx.dialog.close NO
    actualiza el state cuando open=Var es controlado."""
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "def close_mobile_pair(self)" in src, (
        "Falta close_mobile_pair — sin este método el botón Cerrar no cierra"
    )


def test_mobile_pair_dialog_close_uses_direct_handler():
    """v0.18.2 bug fix — el botón Cerrar debe usar on_click=close_mobile_pair,
    NO rx.dialog.close. Con open=Var controlado, rx.dialog.close emite el
    evento UI pero el state sigue True → render reabre el dialog."""
    src = COMPONENTS_PY.read_text(encoding="utf-8")
    section = re.search(
        r"def mobile_pair_dialog\(\)[\s\S]+?(?=\ndef |\Z)", src
    )
    assert section
    body = section.group(0)
    # Debe haber on_click=State.close_mobile_pair en algún botón
    assert "State.close_mobile_pair" in body, (
        "El botón Cerrar debe wirear on_click=State.close_mobile_pair "
        "(no rx.dialog.close)"
    )
    # Y NO debe seguir usando rx.dialog.close(...) — esa era la causa
    # del bug. Buscamos la llamada con paréntesis para no matchear
    # comentarios o docstrings que la mencionan.
    bad_call = re.compile(r"rx\.dialog\.close\s*\(")
    # Quitamos los comentarios línea-a-línea para no matchear texto explicativo
    code_only = "\n".join(
        line for line in body.splitlines()
        if not line.strip().startswith("#")
    )
    assert not bad_call.search(code_only), (
        "rx.dialog.close(...) NO funciona con open=Var controlado — usar "
        "on_click=State.close_mobile_pair en su lugar"
    )


def test_top_nav_bar_includes_mobile_pair_link():
    src = COMPONENTS_PY.read_text(encoding="utf-8")
    section = re.search(
        r"def _top_nav_bar\(\)[\s\S]+?(?=\ndef |\Z)", src
    )
    assert section
    body = section.group(0)
    assert "smartphone" in body, (
        "_top_nav_bar debe incluir un link con icon 'smartphone'"
    )
    assert "toggle_mobile_pair" in body, (
        "_top_nav_bar debe wirear State.toggle_mobile_pair"
    )


def test_mobile_pair_dialog_imported_in_index():
    """El index.py debe importar mobile_pair_dialog para renderizarlo."""
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "mobile_pair_dialog" in src
    # Y montarlo
    assert "mobile_pair_dialog()" in src


def test_components_module_imports_cleanly():
    """RUNTIME guard — el módulo components.py debe importar sin NameError.

    Tests que solo verifican strings (mis otros guards) NO atrapan errores
    de constantes no importadas como `COLOR_BG_CHAT` en mobile_pair_dialog.
    Este test forza el import real → cualquier NameError/ImportError sale aquí
    en lugar de en runtime cuando el user abre la app.
    """
    import sys
    # Limpiar import cache para forzar re-evaluación de top-level
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("reflex_companion."):
            del sys.modules[mod_name]
    sys.path.insert(0, str(ROOT))
    # Solo importar el módulo — no instanciar el componente (eso requiere
    # State + rx.App context). El import es suficiente para atrapar
    # NameError en las defaults de funciones.
    from reflex_companion import components  # noqa: F401
    # Verificar que mobile_pair_dialog es callable (no rompe al referirlo)
    assert callable(components.mobile_pair_dialog), (
        "mobile_pair_dialog no es callable tras import"
    )


def test_mobile_pair_dialog_constants_are_imported():
    """Verifica que las constantes que usa mobile_pair_dialog están en
    el import top-level de components.py. Atrapa el patrón que rompió en
    runtime: usar una constante (COLOR_BG_CHAT) sin importarla."""
    src = COMPONENTS_PY.read_text(encoding="utf-8")
    # Extraer la sección de imports al top
    import_section = re.search(
        r"from \.config import\s*\(([\s\S]+?)\)",
        src,
    )
    assert import_section, "Bloque 'from .config import (...)' no encontrado"
    imported_names = import_section.group(1)

    # Extraer constantes COLOR_* usadas en mobile_pair_dialog
    dialog_section = re.search(
        r"def mobile_pair_dialog\(\)[\s\S]+?(?=\ndef |\Z)", src
    )
    assert dialog_section
    dialog_body = dialog_section.group(0)
    used_constants = set(re.findall(r"\bCOLOR_[A-Z_]+\b", dialog_body))

    for const in used_constants:
        assert const in imported_names, (
            f"mobile_pair_dialog usa {const} pero no está en "
            f"`from .config import (...)`. Bug que rompe en runtime."
        )


# ─────────────────────────────────────────────
#  Mobile HTML — Modo offline settings
# ─────────────────────────────────────────────

def test_mobile_html_has_offline_provider_select():
    html = MOBILE_HTML.read_text(encoding="utf-8")
    assert 'id="settings-offline-provider"' in html, (
        "index.html debe tener select 'settings-offline-provider'"
    )
    # Debe ofrecer al menos xAI y OpenRouter
    assert 'value="xai"' in html and 'value="openrouter"' in html, (
        "Provider select debe ofrecer xai + openrouter"
    )


def test_mobile_html_has_offline_key_input():
    html = MOBILE_HTML.read_text(encoding="utf-8")
    assert 'id="settings-offline-key"' in html
    # Debe ser type=password para no mostrar la key
    pattern = re.compile(
        r'<input[^>]+type="password"[^>]+id="settings-offline-key"|'
        r'<input[^>]+id="settings-offline-key"[^>]+type="password"',
    )
    assert pattern.search(html), (
        "API key input debe ser type='password' (no mostrar la key plain)"
    )


def test_mobile_html_has_test_and_save_buttons():
    html = MOBILE_HTML.read_text(encoding="utf-8")
    assert 'id="settings-offline-test-btn"' in html
    assert 'id="settings-offline-save-btn"' in html


def test_mobile_html_has_offline_status_element():
    html = MOBILE_HTML.read_text(encoding="utf-8")
    assert 'id="settings-offline-status"' in html


# ─────────────────────────────────────────────
#  Mobile JS — handlers + offline fallback
# ─────────────────────────────────────────────

def test_mobile_js_has_offline_config_storage():
    js = MOBILE_JS.read_text(encoding="utf-8")
    assert "STORE_OFFLINE_CFG" in js or "offline_config" in js, (
        "app.js debe persistir el config offline en localStorage"
    )
    assert "loadOfflineConfig" in js
    assert "saveOfflineConfig" in js


def test_mobile_js_has_test_connection_handler():
    js = MOBILE_JS.read_text(encoding="utf-8")
    assert "settingsOfflineTestBtn" in js
    # Debe hacer fetch al endpoint del provider
    assert "/chat/completions" in js, (
        "Test connection debe hacer una llamada mínima a /chat/completions"
    )


def test_mobile_js_supports_xai_and_openrouter():
    js = MOBILE_JS.read_text(encoding="utf-8")
    assert "https://api.x.ai/v1" in js
    assert "https://openrouter.ai/api/v1" in js


def test_mobile_js_uses_bearer_auth_for_offline():
    js = MOBILE_JS.read_text(encoding="utf-8")
    assert "Bearer " in js, "Offline LLM call debe usar Bearer auth"


def test_mobile_js_falls_back_to_offline_when_pc_unreachable():
    """sendMessage debe intentar /api/mobile/send primero, fallback a offline."""
    js = MOBILE_JS.read_text(encoding="utf-8")
    # La función sendMessage debe tener TANTO el path online como el offline
    section = re.search(
        r"async function sendMessage[\s\S]+?(?=\n  async function |\n  function |\Z)",
        js,
    )
    assert section, "sendMessage no encontrado"
    body = section.group(0)
    assert "/api/mobile/send" in body, "sendMessage debe intentar /api/mobile/send"
    assert "loadOfflineConfig" in body, (
        "sendMessage debe consultar offline config como fallback"
    )


def test_mobile_js_offline_uses_recent_msgs_as_context():
    """El offline LLM call debe enviar últimos mensajes como context — sino
    Ashley pierde memoria de la conversación al ir offline."""
    js = MOBILE_JS.read_text(encoding="utf-8")
    section = re.search(
        r"async function sendMessage[\s\S]+?(?=\n  async function |\Z)", js
    )
    body = section.group(0)
    # Debe leer el chat DOM o IDB para construir context
    assert "chatEl" in body or "recentMsgs" in body, (
        "Offline path debe construir messages array con context reciente"
    )


def test_mobile_js_strips_tags_in_offline_mode():
    """Después del LLM call offline, debe limpiar [mood:X] etc. del display."""
    js = MOBILE_JS.read_text(encoding="utf-8")
    section = re.search(
        r"async function sendMessage[\s\S]+?(?=\n  async function |\Z)", js
    )
    body = section.group(0)
    assert "mood" in body and "[mood" in body or "mood:" in body, (
        "Offline path debe extraer/strippear tag [mood:X]"
    )


# ─────────────────────────────────────────────
#  CSS — clases nuevas
# ─────────────────────────────────────────────

def test_mobile_css_has_settings_section_title_class():
    css = MOBILE_CSS.read_text(encoding="utf-8")
    assert ".settings-section-title" in css


def test_mobile_css_has_secondary_btn_class():
    css = MOBILE_CSS.read_text(encoding="utf-8")
    assert ".secondary-btn" in css


def test_mobile_css_has_settings_status_states():
    css = MOBILE_CSS.read_text(encoding="utf-8")
    assert ".settings-status" in css
    # Estados visuales para feedback claro
    assert ".settings-status.ok" in css
    assert ".settings-status.error" in css
