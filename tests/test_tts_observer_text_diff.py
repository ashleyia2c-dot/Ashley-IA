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


class TestObserverDetectsByMsgId:
    """v0.19.26 — cambio de tracking por texto a tracking por data-msg-id.

    Razón: el tracking por texto rompía dos casos:
      1) Delete del último ashley-msg → penúltimo se vuelve "último",
         tiene texto distinto al baseline → observer cree que es nuevo
         y lo lee (re-leía el mensaje borrado anterior).
      2) Startup tardío (Reflex hidrata >3s) → bootstrap toma baseline
         con msgs.length=0 y texto=''. Al hidratar después, cualquier
         mensaje se ve como nuevo y se lee.

    Fix: Set<msgId> de mensajes ya vistos. Cada msg lleva data-msg-id
    estable (v0.19.23). Bootstrap añade los existentes al set sin leer.
    Delete: el id queda en el set pero no en DOM (no problema).
    """

    def test_uses_spoken_ids_set(self, voice_js):
        """El observer debe trackear `_spokenIds` Set de IDs ya leídos."""
        assert "_spokenIds" in voice_js, (
            "v0.19.26: ashley_voice.js debe usar _spokenIds (Set) para "
            "trackear mensajes ya leídos por ID, no por texto"
        )
        assert "new Set()" in voice_js, (
            "_spokenIds debe inicializarse como new Set()"
        )

    def test_observer_reads_data_msg_id(self, voice_js):
        """En _tickObserver, debe leer data-msg-id del wrapper."""
        assert "getAttribute('data-msg-id')" in voice_js, (
            "El observer debe leer data-msg-id de cada .ashley-msg para "
            "trackear quién ha sido leído"
        )


class TestBootstrapAddsExistingIdsToSet:
    def test_bootstrap_adds_existing_ids_to_set(self, voice_js):
        """Tras el deadline, el bootstrap debe añadir todos los msg-id
        existentes al set _spokenIds sin leerlos."""
        import re
        # Patrón: bootstrap añade ids al spokenIds antes de marcar bootstrapped
        match = re.search(
            r"_spokenIds\.add[\s\S]{0,300}?_bootstrapped\s*=\s*true",
            voice_js,
        )
        assert match, (
            "v0.19.26: el bootstrap debe llamar _spokenIds.add(id) sobre "
            "todos los mensajes existentes antes de marcar bootstrapped "
            "como true. Sin esto, al hidratar Reflex el último msg se "
            "leería como si fuera nuevo."
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
