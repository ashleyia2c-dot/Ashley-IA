"""Tests para el fix de Bug 2 (v0.16.14) — TTS no sonaba en chat tras
agregar voice_speed.

Bug reportado por user: tras añadir el slider de velocidad de voz, la
voz dejó de funcionar en el chat (sí en Settings → Probar voz). User
testimonia: "antes funcionaba sin problemas, cuando agregaste lo de la
velocidad de la voz".

Causa identificada: Chrome autoplay policy. La "transient user
activation" del click en el botón Send dura ~5 segundos. Cuando el
stream de Grok tarda más que eso, audio.play() se llama sin activación
y rechaza con NotAllowedError. En Settings funciona porque "Probar voz"
reproduce el audio inmediatamente al click.

Fix aplicado: dos líneas de defensa.
1. Electron webPreferences.autoplayPolicy='no-user-gesture-required'
   — desactiva la restricción a nivel del browser. Es seguro en una app
   desktop (es código local, no web pública).
2. JS: si audio.play() rechaza con NotAllowedError, fallback a Web
   Speech para que el user al menos escuche algo. Y separa la asignación
   de playbackRate a `loadedmetadata` cuando difiere de 1.0 (evita race
   con la decodificación inicial).
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ELECTRON_MAIN = REPO_ROOT / "electron" / "main.js"
ASHLEY_VOICE = REPO_ROOT / "assets" / "ashley_voice.js"


@pytest.fixture(scope="module")
def main_js() -> str:
    return ELECTRON_MAIN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  Layer 1: Electron webPreferences.autoplayPolicy
# ════════════════════════════════════════════════════════════════════════


class TestElectronAutoplayPolicy:
    """Sin esto, audio.play() falla con NotAllowedError en chat tras los
    primeros ~5s sin interacción."""

    def test_main_window_disables_autoplay_restriction(self, main_js):
        """La main window debe tener autoplayPolicy='no-user-gesture-required'."""
        assert "autoplayPolicy" in main_js, (
            "electron/main.js no configura autoplayPolicy. Sin esto, el "
            "browser embebido bloquea audio.play() programático tras los "
            "5s de transient activation del click en Send."
        )
        assert "'no-user-gesture-required'" in main_js, (
            "El valor de autoplayPolicy debe ser 'no-user-gesture-required'. "
            "Otros valores (default 'document-user-activation-required' o "
            "'user-gesture-required') causan el bug."
        )


# ════════════════════════════════════════════════════════════════════════
#  Layer 2: JS — Fallback en NotAllowedError + playbackRate seguro
# ════════════════════════════════════════════════════════════════════════


class TestJSFallbackOnAutoplayBlocked:
    """Si por algún motivo Electron NO honra autoplayPolicy (versión vieja,
    bug, build inesperada), el JS debe degradar a Web Speech para que el
    user al menos escuche algo."""

    def test_handles_notallowed_error(self, voice_js):
        """Cuando audio.play() rechaza con NotAllowedError, debe llamar a
        _speakWebSpeech como fallback."""
        # El handler debe revisar e.name === 'NotAllowedError'
        assert "NotAllowedError" in voice_js, (
            "ashley_voice.js no maneja NotAllowedError de audio.play(). "
            "Si el autoplayPolicy de Electron falla, el user no oye nada y "
            "no sabe por qué. Debe hacer fallback a Web Speech."
        )

    def test_fallback_to_webspeech_in_play_rejection(self, voice_js):
        """En la rama de rejection de play(), debe haber una llamada a
        _speakWebSpeech."""
        # Buscar el bloque del play() rejection
        match = re.search(
            r"audio\.play\(\)\s*REJECTED[\s\S]{0,800}?_speakWebSpeech",
            voice_js,
        )
        assert match, (
            "El handler de audio.play() rechazado debe llamar a "
            "_speakWebSpeech como fallback para que el user oiga algo."
        )


class TestPlaybackRateNoRaceCondition:
    """Asignar audio.playbackRate ANTES de que el audio cargue metadata
    puede tener side effects sutiles en Chromium. Si speed = 1.0 (default),
    no asignamos nada → comportamiento idéntico al pre-v0.16.14 que el
    user confirma que funcionaba."""

    def test_playbackrate_only_set_when_speed_differs(self, voice_js):
        """Si speed === 1.0, no debe haber asignación directa de playbackRate
        (preserva el comportamiento pre-voice_speed que funcionaba)."""
        # Buscar el guard que evita asignar cuando speed ~= 1.0
        match = re.search(
            r"Math\.abs\(speed\s*-\s*1\.0\)\s*>\s*0\.\d+",
            voice_js,
        )
        assert match, (
            "ashley_voice.js no protege contra setear playbackRate cuando "
            "speed=1.0 (default). Esto evita race conditions con la "
            "decodificación inicial. Debe haber un guard como "
            "`if (Math.abs(speed - 1.0) > 0.001)`."
        )

    def test_playbackrate_set_in_loadedmetadata_event(self, voice_js):
        """Cuando se aplica playbackRate, debe ser dentro de un listener
        de loadedmetadata para evitar race con la carga del audio."""
        # Buscar el patrón de loadedmetadata + playbackRate
        match = re.search(
            r"loadedmetadata[\s\S]{0,300}?playbackRate",
            voice_js,
        )
        assert match, (
            "playbackRate debe asignarse dentro de un listener de "
            "loadedmetadata para que el audio aplique el cambio sin "
            "race con la decodificación. Asignación directa antes de "
            "play() puede causar problemas en Chromium."
        )


# ════════════════════════════════════════════════════════════════════════
#  Diagnóstico — logs visibles en DevTools
# ════════════════════════════════════════════════════════════════════════


class TestDiagnosticLogs:
    """Si el bug vuelve, los logs deben ser claros para diagnosticar
    rápidamente sin tener que añadir prints a la deriva."""

    def test_logs_when_play_resolves(self, voice_js):
        """Cuando play() se resuelve, debe haber un log indicándolo."""
        assert "audio.play() RESOLVED" in voice_js, (
            "Sin un log de RESOLVED, no podemos saber si el problema es "
            "que play() falla o que el audio simplemente no sale por los "
            "altavoces (problema HW o config OS)."
        )

    def test_logs_when_play_rejects(self, voice_js):
        """Cuando play() rechaza, debe haber un log con name+message."""
        assert "audio.play() REJECTED" in voice_js, (
            "Sin un log de REJECTED, los rechazos pasan silenciosos y no "
            "podemos diagnosticar el problema desde DevTools."
        )
