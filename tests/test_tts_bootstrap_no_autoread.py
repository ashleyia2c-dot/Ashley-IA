"""Tests para Bug 4 (v0.16.14) — Ashley leía el último mensaje histórico
al abrir la app.

Bug reportado por user: "lo de la voz cuando abro la app ashley habla el
ultimo mensaje automaticamente, luego cuando envio otro ya no habla
nunca mas".

Causa identificada: el observer de TTS hacía baseline en el primer tick
con `prevMessageCount = msgs.length`. PERO si Reflex aún no había
hidratado el historial, msgs.length=0. En el siguiente tick (500ms),
ya hidratado, msgs.length=N > 0 = prevMessageCount → "nuevo mensaje
detectado" → lee el último del historial.

Fix: timestamp-based bootstrap. Esperar 3 segundos absolutos desde init()
ANTES de tomar el baseline. En 3s Reflex ya hidrató en cualquier máquina
razonable. Trade-off aceptado: si llega un mensaje genuinamente nuevo en
los primeros 3s tras abrir la app (caso muy raro), no se lee — vale el
silencio.

Intento previo "2 ticks estables" falló: si Reflex tarda >2 ticks en
hidratar, sigues bootstrapping con count=0 (estable porque sigue 0).
Timestamp absoluto es robusto: independiente de cuántos ticks pasen.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASHLEY_VOICE = REPO_ROOT / "assets" / "ashley_voice.js"


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE.read_text(encoding="utf-8")


class TestBootstrapDeadlineExists:
    """El observer debe usar un deadline absoluto, no contar ticks."""

    def test_uses_bootstrap_deadline(self, voice_js):
        """Debe haber una variable _bootstrapDeadline o similar con
        timestamp absoluto."""
        assert "_bootstrapDeadline" in voice_js, (
            "El observer no usa _bootstrapDeadline (timestamp absoluto). "
            "Sin esto, el bootstrap depende del nº de ticks lo cual falla "
            "si Reflex tarda más de lo esperado en hidratar."
        )

    def test_deadline_is_at_least_three_seconds(self, voice_js):
        """El delay debe ser al menos 3000ms para dar margen a Reflex."""
        # Buscar Date.now() + N donde N >= 3000
        match = re.search(
            r"_bootstrapDeadline\s*=\s*now\s*\+\s*(\d+)",
            voice_js,
        )
        assert match, (
            "_bootstrapDeadline no se asigna con `now + N`. Esperaba "
            "patrón como `this._bootstrapDeadline = now + 3000`."
        )
        delay = int(match.group(1))
        assert delay >= 3000, (
            f"Bootstrap deadline es {delay}ms — muy poco. Reflex puede "
            f"tardar 1-2.5s en hidratar el historial. 3000ms da margen."
        )


class TestObserverWaitsForDeadline:
    """Mientras estamos en la ventana de bootstrap, no debe leer mensajes."""

    def test_returns_early_before_deadline(self, voice_js):
        """En el bloque del observer, si now < _bootstrapDeadline, return."""
        match = re.search(
            r"now\s*<\s*this\._bootstrapDeadline[\s\S]{0,200}?return",
            voice_js,
        )
        assert match, (
            "El observer no retorna early cuando now < _bootstrapDeadline. "
            "Sin esto, el bootstrap no espera el deadline y vuelve el bug."
        )


class TestBootstrapTakesBaselineAfterDeadline:
    """Tras el deadline, el observer toma el baseline con el contenido del
    último ashley-msg (v0.16.14: cambiado de count → text por Bug B)."""

    def test_sets_baseline_after_deadline(self, voice_js):
        """Después del deadline, debe asignar `_lastAshleyText` (el
        contenido del último ashley-msg) y marcar `_bootstrapped = true`.
        Antes usábamos `_prevMessageCount = msgs.length` pero el count
        es no fiable cuando MAX_HISTORY_MESSAGES trima — Bug B."""
        match = re.search(
            r"_lastAshleyText\s*=[\s\S]{0,400}?_bootstrapped\s*=\s*true",
            voice_js,
        )
        assert match, (
            "Tras el deadline, el observer no asigna _lastAshleyText "
            "antes de marcar _bootstrapped=true. Sin baseline de texto, "
            "el primer mensaje real podría leerse incorrectamente."
        )


class TestBootstrapPreventsReadingHistory:
    """El test crítico: si bootstrap funciona, NO se lee el último mensaje
    del historial al abrir la app."""

    def test_does_not_speak_during_bootstrap_window(self, voice_js):
        """Durante el bootstrap (cuando !_bootstrapped), no debe haber
        llamada a `this.speak()` en _tickObserver."""
        # Extraer el cuerpo de _tickObserver
        match = re.search(
            r"_tickObserver\s*\(\)\s*\{([\s\S]*?)\n    \},",
            voice_js,
        )
        assert match, "No se localizó _tickObserver"
        body = match.group(1)

        # El bloque if (!this._bootstrapped) debe terminar con `return;`
        # sin llamar a speak antes del return.
        bootstrap_block = re.search(
            r"if\s*\(\s*!this\._bootstrapped\s*\)\s*\{([\s\S]*?)return;",
            body,
        )
        assert bootstrap_block, (
            "El bloque de bootstrap no termina con return early."
        )
        block_text = bootstrap_block.group(1)
        assert "this.speak(" not in block_text, (
            "BUG 4 REGRESIÓN: durante el bootstrap, el observer llama a "
            "this.speak() — eso es lo que hacía que Ashley leyera el "
            "último mensaje del historial al abrir la app."
        )
