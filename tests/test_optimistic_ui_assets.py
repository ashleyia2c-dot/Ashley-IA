"""Tests para los activos (CSS + JS) que implementan el optimistic UI.

El optimistic UI hace que el bubble del user aparezca AL INSTANTE al
pulsar enter. Es 100% temporal — vive solo hasta que React monte el
real (~100-200ms), entonces el observer lo borra y el real toma su
lugar.

Piezas críticas:

  1. CSS regla `.user-msg.msg-enter { animation: none }` evita que el
     real ejecute slide-up tras el swap fake→real. Sin esto el bubble
     parece "moverse" cuando el real reemplaza al fake.

  2. CSS reset margin para `<p>/<h*>/<li>` dentro de `.bubble-*` iguala
     dimensiones del real (markdown) con el fake (`<p style="margin:0">`).
     Sin esto el real es ~32px más alto y el bubble crece al swap.

  3. JS `_showOptimisticUserBubble` añade el fake + dispara `playSend()`.
     Solo el fake suena — el observer NO suena para user-msgs (evita
     doble sonido).

  4. JS `_purgeOptimistic` borra los fakes cuando el observer detecta
     un nuevo real.

  5. CSS oculta el `<input type=file>` nativo del rx.upload (el
     "Ningún archivo seleccionado" del browser).

Estos tests bloquean regresión: si alguien refactoriza y rompe alguna
de estas reglas, los tests fallan ruidosamente.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
STYLES_PY = REPO_ROOT / "reflex_companion" / "styles.py"
ASHLEY_FX_JS = REPO_ROOT / "assets" / "ashley_fx.js"


# ══════════════════════════════════════════════════════════════════════
#  CSS — reglas críticas del optimistic UI presentes en styles.py
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def styles_source() -> str:
    return STYLES_PY.read_text(encoding="utf-8")


class TestUserMsgNoAnimation:
    """El user-msg real NO anima slide-up.

    Sin esta regla, tras el swap fake→real el real ejecuta `fadeSlideIn`
    (translateY 12px → 0) durante 250ms — el user ve su bubble "moverse".
    Con animation:none, el real toma exactamente la posición del fake.
    """

    def test_user_msg_msg_enter_animation_none(self, styles_source):
        # La regla debe existir y forzar animation: none con !important
        pattern = (
            r"\.user-msg\.msg-enter\s*\{\{?\s*animation:\s*none\s*!important"
        )
        assert re.search(pattern, styles_source), (
            "Falta `.user-msg.msg-enter { animation: none !important }`. "
            "Sin esto el bubble real anima slide-up tras el swap fake→real "
            "y el user ve su mensaje 'moverse'."
        )


class TestBubbleHeightEquality:
    """El <p> dentro de .bubble-user (real) y el <p> del fake deben tener
    EXACTAMENTE la misma altura. El real usa rx.markdown que mete el
    <p> con marginTop/marginBottom 1em (~16px arriba y abajo). El fake
    usa <p style="margin:0">. Sin reset, el real es 32px más alto y el
    bubble crece al swap fake→real → "se mueve".
    """

    def test_p_margin_reset(self, styles_source):
        # Reglas que aplican margin:0 a <p> (y otros bloques) dentro de
        # .bubble-ashley/.bubble-user.
        assert ".bubble-user p" in styles_source, (
            "Falta selector `.bubble-user p` para resetear margin. "
            "Sin esto, el bubble real es más alto que el fake → swap visible."
        )
        # El bloque de margin reset debe usar margin-top: 0 + !important
        block_pattern = re.compile(
            r"\.bubble-ashley p, \.bubble-user p[\s\S]{0,400}?"
            r"margin-top:\s*0\s*!important[\s\S]{0,200}?"
            r"margin-bottom:\s*0\s*!important",
        )
        assert block_pattern.search(styles_source), (
            "El reset de margin para `<p>` dentro de bubbles no usa "
            "margin-top:0 !important + margin-bottom:0 !important."
        )


class TestUploadInputHidden:
    """El <input type=file> del rx.upload se oculta off-screen para que
    no aparezca el texto nativo del browser ('Ningún archivo seleccionado')
    en la UI."""

    def test_input_file_hidden_off_screen(self, styles_source):
        pattern = (
            r"\.ashley-upload-clean\s+input\[type=\"file\"\]\s*\{\{?[^}]*"
            r"(?:left:\s*-9999px|opacity:\s*0)"
        )
        assert re.search(pattern, styles_source, re.DOTALL), (
            "Falta la regla CSS que oculta el input[type=file] nativo del "
            "rx.upload. Sin esto, el browser pinta 'Ningún archivo seleccionado'."
        )


# ══════════════════════════════════════════════════════════════════════
#  JS — sintaxis válida + funciones críticas presentes
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def js_source() -> str:
    return ASHLEY_FX_JS.read_text(encoding="utf-8")


class TestJsSyntax:
    """Si ashley_fx.js tiene un syntax error, NADA del frontend
    interactivo funciona. Estos tests requieren node disponible — si
    no está, se skip-ean."""

    def test_js_parses_with_node(self):
        node = shutil.which("node")
        if not node:
            pytest.skip("node no disponible — saltando JS syntax check")
        result = subprocess.run(
            [node, "--check", str(ASHLEY_FX_JS)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, (
            f"ashley_fx.js tiene errores de sintaxis:\n{result.stderr}"
        )


class TestOptimisticJsAPI:
    """Funciones clave del optimistic UI deben existir en el JS."""

    def test_show_optimistic_function_exists(self, js_source):
        assert "function _showOptimisticUserBubble" in js_source

    def test_purge_optimistic_function_exists(self, js_source):
        # _purgeOptimistic borra los fakes cuando el real llega
        assert "function _purgeOptimistic" in js_source, (
            "Falta _purgeOptimistic — sin esto los fakes no se limpian "
            "cuando React monta el real → quedan dos bubbles del mismo mensaje."
        )

    def test_init_optimistic_function_exists(self, js_source):
        assert "function initOptimisticUI" in js_source

    def test_optimistic_calls_play_send(self, js_source):
        # El sonido playSend debe dispararse al insertar el optimistic.
        match = re.search(
            r"function _showOptimisticUserBubble[\s\S]*?\n\s{2}\}",
            js_source,
        )
        assert match, "No se pudo localizar _showOptimisticUserBubble"
        body = match.group(0)
        assert "playSend" in body, (
            "_showOptimisticUserBubble debe disparar playSend() al insertar "
            "el bubble — feedback sonoro instantáneo."
        )

    def _msg_observer_body(self, js_source):
        """Localiza el MutationObserver del chat (no el del starfield).
        El de mensajes se identifica por usar REAL_SEL y prevMsgCount."""
        # Hay varios MutationObservers en el archivo. Buscamos uno que
        # contenga referencias a 'prevMsgCount' o 'REAL_SEL' (variables
        # del observer del chat).
        for match in re.finditer(
            r"new MutationObserver\(function\s*\([^)]*\)\s*\{[\s\S]*?\n\s{6,8}\}\s*\)",
            js_source,
        ):
            body = match.group(0)
            if "prevMsgCount" in body or "REAL_SEL" in body:
                return body
        return None

    def test_observer_purges_optimistic_on_new_real(self, js_source):
        # El observer debe llamar _purgeOptimistic cuando llega delta>=1
        # de mensajes reales.
        obs_body = self._msg_observer_body(js_source)
        assert obs_body, "no se localizó el MutationObserver del chat"
        assert "_purgeOptimistic" in obs_body, (
            "El observer del chat debe llamar _purgeOptimistic cuando "
            "llega un user-msg real para limpiar los fakes."
        )

    def test_observer_does_not_play_send_for_user_msg(self, js_source):
        # El observer NO debe llamar playSend para user-msgs (eso lo hace
        # _showOptimisticUserBubble).
        obs_body = self._msg_observer_body(js_source)
        assert obs_body, "no se localizó el MutationObserver del chat"
        bad_pattern = re.compile(
            r"contains\(['\"]user-msg['\"]\)[\s\S]{0,80}playSend",
        )
        assert not bad_pattern.search(obs_body), (
            "El observer dispara playSend para user-msgs — eso causa el "
            "sonido doble (optimistic + real). Solo _showOptimisticUserBubble "
            "debe sonar."
        )

    def test_no_complex_legacy_logic_remains(self, js_source):
        """Las funciones complejas previas (_enforceOptimistic, _markExisting...)
        causaban bugs raros al borrar mensajes y al recibir respuestas.
        Si alguien las re-introduce, este test falla."""
        forbidden = [
            "_enforceOptimistic",
            "_markExistingUserMsgsAsShown",
            "user-msg-shown",
            "user-msg-hidden",
        ]
        for term in forbidden:
            assert term not in js_source, (
                f"Encontrado '{term}' en ashley_fx.js. Esa lógica fue "
                f"eliminada porque causaba bugs (mensajes que se desplazan "
                f"al borrar, respuesta de Ashley arriba del envío, etc.). "
                f"Mantener la lógica simple: optimistic temporal + purge."
            )


class TestOptimisticBubbleStructure:
    """El optimistic bubble debe tener clases correctas para distinguirse
    del real."""

    def test_optimistic_class_applied(self, js_source):
        assert "'user-msg ashley-optimistic'" in js_source, (
            "El wrapper del optimistic debe tener className "
            "'user-msg ashley-optimistic'."
        )

    def test_optimistic_uses_inline_animation_none(self, js_source):
        match = re.search(
            r"function _buildFakeBubble[\s\S]*?\n\s{2}\}",
            js_source,
        )
        assert match, "No se localizó _buildFakeBubble"
        body = match.group(0)
        assert "animation:none" in body, (
            "_buildFakeBubble debe declarar animation:none en el style "
            "inline del wrapper."
        )


class TestNoLegacyCssRules:
    """Reglas CSS de iteraciones previas que causaban bugs deben estar
    eliminadas. Si alguien las re-introduce, los tests fallan."""

    def test_no_user_msg_shown_rule(self, styles_source):
        # `.user-msg-shown` era parte de una solución compleja que
        # rompía la lógica de eliminar mensajes.
        assert "user-msg-shown" not in styles_source, (
            "Encontrada regla con .user-msg-shown — esa estrategia "
            "causaba bugs al borrar mensajes. Eliminar."
        )

    def test_no_user_msg_hidden_rule(self, styles_source):
        # `.user-msg-hidden` ocultaba el real con display:none, lo que
        # rompía la eliminación de mensajes.
        assert "user-msg-hidden" not in styles_source, (
            "Encontrada regla con .user-msg-hidden — display:none "
            "rompía la eliminación de mensajes. Eliminar."
        )
