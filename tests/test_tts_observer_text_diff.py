"""Tests para Bug B (v0.16.14) — TTS no se disparaba cuando MAX_HISTORY_MESSAGES
truncaba mensajes viejos.

Caso reportado por user: tras enviar mensaje, Ashley respondía
correctamente (Python: msgs=51 → 52, post-append role=assistant) pero el
observer JS reportaba `ashleyMsgCount=27, prevCount=27` y no detectaba
ningún cambio.

Causa raíz: el observer comparaba count de `.ashley-msg`. Con
MAX_HISTORY_MESSAGES=50, después del append (52 items) Reflex truncaba
a 50. Si los 2 mensajes más viejos que se borraban incluían 1 ashley
+ 1 user, el COUNT total de ashley-msg quedaba igual (27 antes, 27
después). El observer veía `count <= prevCount` y skipeaba speech.

Fix: cambiar la lógica de detección de "msgs.length cambió" a "el
contenido textual del último ashley-msg cambió". El nuevo mensaje SIEMPRE
está al final del array, así que su textContent será diferente al
previo (excepto si Ashley repite literalmente la respuesta anterior —
edge case aceptable).
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASHLEY_VOICE = REPO_ROOT / "assets" / "ashley_voice.js"


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  Detección por contenido (no por count)
# ════════════════════════════════════════════════════════════════════════


class TestObserverDetectsByText:
    def test_uses_last_ashley_text_state(self, voice_js):
        """El observer debe trackear `_lastAshleyText` para comparar
        contenido, no count."""
        assert "_lastAshleyText" in voice_js, (
            "ashley_voice.js no usa _lastAshleyText. Sin esto, cuando "
            "MAX_HISTORY_MESSAGES trima mensajes viejos, el count de "
            "ashley-msg puede quedar igual aunque haya respuesta nueva, "
            "y el observer skipea speech."
        )

    def test_compares_text_not_count(self, voice_js):
        """En _tickObserver, la condición de 'mensaje nuevo' debe ser
        text-based, no count-based."""
        # Buscar la condición text === _lastAshleyText (skip)
        # o text !== _lastAshleyText (act)
        assert "this._lastAshleyText" in voice_js
        # Verificar que NO se sigue usando solo count comparison
        # (puede haber count para diagnóstico, pero la decisión debe ser
        # por text)
        # Buscar la línea de decisión: if (text === this._lastAshleyText) return;
        assert "text === this._lastAshleyText" in voice_js, (
            "El observer no compara `text === this._lastAshleyText`. "
            "Necesario para detectar mensajes nuevos cuando el count "
            "está estable por trim."
        )


class TestBootstrapTakesTextBaseline:
    def test_bootstrap_stores_last_text(self, voice_js):
        """Tras los 3s de deadline, el bootstrap debe leer y guardar el
        textContent del último ashley-msg como baseline."""
        # Buscar que en el bootstrap se asigne _lastAshleyText
        # tras el deadline
        # Patrón: if (now < this._bootstrapDeadline) { return; }
        # ... seguido de this._lastAshleyText = ...
        import re
        match = re.search(
            r"_bootstrapped[\s\S]{0,800}?_lastAshleyText\s*=",
            voice_js,
        )
        assert match, (
            "El bootstrap no asigna _lastAshleyText con el contenido del "
            "último ashley-msg. Sin esto, el primer mensaje real podría "
            "leerse o saltarse incorrectamente."
        )

    def test_bootstrap_does_not_speak(self, voice_js):
        """Durante el bootstrap (!_bootstrapped), no debe haber llamada
        a this.speak() — eso reintroduciría Bug 4 (lee historial)."""
        import re
        match = re.search(
            r"_tickObserver\s*\(\)\s*\{([\s\S]*?)\n    \},",
            voice_js,
        )
        assert match
        body = match.group(1)
        bootstrap_block = re.search(
            r"if\s*\(\s*!this\._bootstrapped\s*\)\s*\{([\s\S]*?)return;",
            body,
        )
        assert bootstrap_block
        block_text = bootstrap_block.group(1)
        assert "this.speak(" not in block_text, (
            "BUG 4 REGRESIÓN: bootstrap llama a speak() — eso lee el "
            "último mensaje del historial al abrir."
        )


class TestNoCountBasedDecision:
    """Validamos que la decisión NO depende solo de count cambiando."""

    def test_no_msgs_length_gt_prev_count_decision(self, voice_js):
        """No debe haber decisión basada en `msgs.length <= prevMessageCount`
        que skipea sin comparar texto."""
        # El antiguo código tenía: if (msgs.length <= this._prevMessageCount) return;
        # Eso es el bug. Verificamos que no esté.
        import re
        # Buscar condición del tipo "if (msgs.length <= ... prevMessage" return"
        bad = re.search(
            r"if\s*\([^)]*msgs\.length\s*<=\s*this\._prevMessageCount[^)]*\)\s*return",
            voice_js,
        )
        assert not bad, (
            "Detectado decision basada en msgs.length <= _prevMessageCount. "
            "Eso es el bug B (v0.16.14): cuando MAX_HISTORY_MESSAGES trima, "
            "count se queda igual aunque haya mensaje nuevo → no se "
            "dispara TTS."
        )
