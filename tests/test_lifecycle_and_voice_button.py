"""Tests para:

  1. Botón TTS en la UI — `toggle_tts` debe estar cableado a un botón
     visible. Antes (v0.16) vivía en un sidebar que se borró en la
     limpieza de dead code, dejando la voz sin trigger en la nueva UI.

  2. Graceful shutdown — Electron debe llamar `/api/shutdown` antes de
     SIGKILL. Sin esto, el wake_word detector no libera el handle del
     mic (PortAudio) y el icono "Apps están usando tu micrófono" queda
     en la barra de Windows hasta reboot. Además algunos python.exe
     pueden quedar zombies.

Estos tests bloquean regresión: si alguien refactoriza la UI o el
shutdown logic, los tests fallan y queda claro qué se rompió.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_PY = REPO_ROOT / "reflex_companion" / "components.py"
API_ROUTES_PY = REPO_ROOT / "reflex_companion" / "api_routes.py"
MAIN_JS = REPO_ROOT / "electron" / "main.js"


# ══════════════════════════════════════════════════════════════════════
#  Botón TTS visible en la UI
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def components_source() -> str:
    return COMPONENTS_PY.read_text(encoding="utf-8")


class TestTTSToggleButton:
    """`toggle_tts` debe estar cableado a un botón en la UI activa."""

    def test_toggle_tts_referenced_in_components(self, components_source):
        # Buscar referencia explícita a State.toggle_tts en components.py
        # (puede ser en el chat_header_bar o el portrait_overlay).
        assert "State.toggle_tts" in components_source, (
            "No se encuentra State.toggle_tts en components.py. El método "
            "existe en Python (toggle_tts) pero falta el botón que lo "
            "dispare → la voz de Ashley no puede activarse desde la UI."
        )

    def test_tts_button_has_volume_icons(self, components_source):
        # El botón debe usar iconos volume-2 / volume-x (Lucide) según
        # el estado de tts_enabled.
        # Buscamos el bloque cerca de toggle_tts.
        match = re.search(
            r"State\.toggle_tts[\s\S]{0,2000}",
            components_source,
        )
        # Verificamos que en el componente hay iconos de volumen y la
        # condición tts_enabled cerca.
        # El test es flexible: aceptamos volume-2/volume-x O similar
        # (mute, volume-1, etc.) — solo exige que NO sea un botón sin icono.
        block = match.group(0) if match else ""
        # Buscar hacia atrás también
        idx = components_source.find("State.toggle_tts")
        surrounding = components_source[max(0, idx - 800): idx + 800]
        assert (
            "volume-2" in surrounding or "volume-x" in surrounding
            or "volume_2" in surrounding or "volume_x" in surrounding
        ), (
            "El botón TTS no parece tener iconos de volumen (volume-2/x). "
            "Sin un icono claro, el user no sabe qué hace el botón."
        )


# ══════════════════════════════════════════════════════════════════════
#  Endpoint /api/shutdown registrado
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def api_routes_source() -> str:
    return API_ROUTES_PY.read_text(encoding="utf-8")


class TestShutdownEndpoint:
    """El endpoint /api/shutdown debe existir y parar el wake_word."""

    def test_shutdown_endpoint_function_exists(self, api_routes_source):
        assert "_shutdown_endpoint" in api_routes_source, (
            "Falta la función _shutdown_endpoint. Sin este endpoint el "
            "Python no puede hacer cleanup graceful → mic queda colgado "
            "tras cerrar la app."
        )

    def test_shutdown_calls_stop_detector(self, api_routes_source):
        # El handler debe llamar stop_detector para liberar el mic.
        match = re.search(
            r"async def _shutdown_endpoint[\s\S]*?(?=\n(?:async )?def |\nclass |\Z)",
            api_routes_source,
        )
        assert match, "No se localizó la función _shutdown_endpoint"
        body = match.group(0)
        assert "stop_detector" in body, (
            "/api/shutdown no llama stop_detector — sin esto el handle "
            "PortAudio del mic no se libera y el icono 'apps usando tu mic' "
            "queda hasta reboot."
        )

    def test_shutdown_calls_os_exit(self, api_routes_source):
        # Tras cleanup, debe forzar exit del proceso.
        match = re.search(
            r"async def _shutdown_endpoint[\s\S]*?(?=\n(?:async )?def |\nclass |\Z)",
            api_routes_source,
        )
        body = match.group(0) if match else ""
        assert "os._exit" in body or "_os._exit" in body, (
            "/api/shutdown no fuerza exit del proceso. Sin esto el python "
            "queda corriendo tras el cleanup → bug 'python no se cierra'."
        )

    def test_shutdown_route_registered(self, api_routes_source):
        assert '"/api/shutdown"' in api_routes_source, (
            "La ruta /api/shutdown no está registrada en register_routes. "
            "Sin esto Electron no puede llamarla."
        )


# ══════════════════════════════════════════════════════════════════════
#  Electron: gracefulShutdownBackend wired in lifecycle hooks
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def main_js_source() -> str:
    return MAIN_JS.read_text(encoding="utf-8")


class TestElectronGracefulShutdown:
    """Los 3 hooks de salida (window-all-closed, before-quit, SIGTERM/INT)
    deben llamar gracefulShutdownBackend antes de killReflex."""

    def test_graceful_shutdown_function_exists(self, main_js_source):
        assert "function gracefulShutdownBackend" in main_js_source, (
            "Falta la función gracefulShutdownBackend en main.js. Sin "
            "esta función Electron solo hace SIGKILL → Python no cleanup → "
            "mic colgado."
        )

    def test_graceful_shutdown_posts_to_endpoint(self, main_js_source):
        match = re.search(
            r"function gracefulShutdownBackend[\s\S]*?(?=\n\n)",
            main_js_source,
        )
        assert match, "No se localizó gracefulShutdownBackend"
        body = match.group(0)
        assert "/api/shutdown" in body, (
            "gracefulShutdownBackend no hace POST a /api/shutdown."
        )

    def test_window_all_closed_calls_graceful(self, main_js_source):
        # Buscar el handler de 'window-all-closed' y verificar que llama
        # gracefulShutdownBackend.
        match = re.search(
            r"app\.on\('window-all-closed'[\s\S]*?\}\);",
            main_js_source,
        )
        assert match, "No se localizó el handler window-all-closed"
        body = match.group(0)
        assert "gracefulShutdownBackend" in body, (
            "El handler window-all-closed no llama gracefulShutdownBackend "
            "— el cierre por X de la ventana deja el mic colgado."
        )

    def test_before_quit_calls_graceful(self, main_js_source):
        match = re.search(
            r"app\.on\('before-quit'[\s\S]*?\}\);",
            main_js_source,
        )
        assert match, "No se localizó el handler before-quit"
        body = match.group(0)
        assert "gracefulShutdownBackend" in body, (
            "El handler before-quit no llama gracefulShutdownBackend."
        )

    def test_sigterm_sigint_call_graceful(self, main_js_source):
        # Ambos handlers de signal deben llamar graceful antes de killReflex.
        for sig in ["SIGINT", "SIGTERM"]:
            match = re.search(
                rf"process\.on\('{sig}'[\s\S]*?\}}\);",
                main_js_source,
            )
            assert match, f"No se localizó el handler {sig}"
            body = match.group(0)
            assert "gracefulShutdownBackend" in body, (
                f"El handler {sig} no llama gracefulShutdownBackend — "
                f"un kill -{sig} deja el mic colgado."
            )

    def test_main_js_passes_node_syntax_check(self, main_js_source):
        node = shutil.which("node")
        if not node:
            pytest.skip("node no disponible — saltando JS syntax check")
        result = subprocess.run(
            [node, "--check", str(MAIN_JS)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, (
            f"electron/main.js tiene errores de sintaxis tras el cambio:\n"
            f"{result.stderr}"
        )
