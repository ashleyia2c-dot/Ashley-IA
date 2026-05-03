"""Tests para las optimizaciones de rendimiento general de la app
(v0.16.14).

CONTEXTO:
─────────
El user reportaba "lag general" — toda la app se sentía lenta. Tras un
audit completo se identificaron 8 puntos de mayor impacto. Estos tests
bloquean regresión a los valores costosos.

OPTIMIZACIONES APLICADAS:

1. CSS — `filter: blur(80px)` en ambient glows → blur(30px). El blur
   80px sobre 3 elementos a 70vw/60vw = millones de pixels procesados
   por frame. 30px sigue dando efecto soft sin matar la GPU.

2. CSS — `filter: blur(50px)` en portrait halo → blur(25px). Halo
   gigante (max 800px) con blur extremo era costoso por frame.

3. CSS — animation duration `portraitHaloPulse 6s` → `12s`. Misma
   sensación visual, 50% menos repaints/min.

4. JS — polling de affection 500ms → 1500ms. Affection cambia raro,
   no necesita check rápido.

5. JS — polling de achievements 300ms → 1000ms. Achievements son
   eventos raros, sonar 700ms tarde es imperceptible.

6. JS — polling de thinking/streaming 100ms → 250ms. 250ms de delay
   en sonido thinking es invisible. Reduce wakeups del main thread
   de 10/s a 4/s.

7. JS — TTS observer 500ms → 1000ms. textContent reads son
   layout-trigger; doblar el intervalo reduce competición con scroll.

8. Backend — `@rx.var(cache=False)` → `cache=True` en backend_port_marker.
   El env var es estático en runtime, recomputarlo en cada state tick
   era waste.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
STYLES_PY = REPO_ROOT / "reflex_companion" / "styles.py"
ASHLEY_FX = REPO_ROOT / "assets" / "ashley_fx.js"
ASHLEY_VOICE = REPO_ROOT / "assets" / "ashley_voice.js"
RC_PY = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


@pytest.fixture(scope="module")
def styles_src() -> str:
    return STYLES_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def fx_js() -> str:
    return ASHLEY_FX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rc_src() -> str:
    return RC_PY.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  CSS — blurs no extremos
# ════════════════════════════════════════════════════════════════════════


class TestAmbientGlowBlurReasonable:
    """Las 3 ambient glows fijas en pantalla animadas constantemente.
    blur(80px) sobre elementos 70vw causaba GPU thrash."""

    def test_ambient_glow_blur_under_50px(self, styles_src):
        match = re.search(
            r"\.ambient-glow-1[^{]*?\.ambient-glow-2[^{]*?\.ambient-glow-3\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match, "No se localizó la regla combinada de ambient-glow-1/2/3"
        block = match.group(1)
        # Buscar filter: blur(Npx)
        m = re.search(r"filter:\s*blur\((\d+)px\)", block)
        assert m, "ambient-glow no tiene filter: blur(Xpx)"
        radius = int(m.group(1))
        assert radius <= 50, (
            f"ambient-glow blur radius={radius}px es excesivo. Recordatorio: "
            f"esto se aplica a 3 elementos a 70vw simultáneamente, "
            f"animados infinitamente. >50px causa GPU thrashing constante."
        )


class TestPortraitHaloBlurReasonable:
    def test_portrait_halo_blur_under_40px(self, styles_src):
        # El halo es el ::before del .ashley-portrait-panel.mode-2d
        match = re.search(
            r"\.ashley-portrait-panel\.mode-2d::before\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match
        block = match.group(1)
        m = re.search(r"filter:\s*blur\((\d+)px\)", block)
        assert m
        radius = int(m.group(1))
        assert radius <= 40, (
            f"portrait halo blur={radius}px excesivo. Halo grande "
            f"(max 800px) animado infinitamente con blur extremo "
            f"= repaint costoso cada frame."
        )

    def test_portrait_halo_pulse_duration_at_least_8s(self, styles_src):
        """Animación debe ser lenta (>=8s) para reducir frames de repaint."""
        match = re.search(
            r"animation:\s*portraitHaloPulse\s+(\d+)s",
            styles_src,
        )
        assert match
        duration = int(match.group(1))
        assert duration >= 8, (
            f"portraitHaloPulse dura solo {duration}s. Demasiado rápido "
            f"para una animación de 'respiración suave' del halo de fondo."
        )


# ════════════════════════════════════════════════════════════════════════
#  JS — polling intervals razonables
# ════════════════════════════════════════════════════════════════════════


class TestPollingIntervalsReasonable:
    """Los pollers compiten con scroll por main thread. >=200ms para
    no crítico, >=1000ms para eventos raros."""

    def test_thinking_streaming_poll_at_least_200ms(self, fx_js):
        """Detector de .portrait-thinking / .cursor-blink para sonidos."""
        # Buscar el setInterval que tiene queries de portrait-thinking + cursor-blink
        match = re.search(
            r"document\.querySelector\(\s*['\"]\.portrait-thinking[\s\S]{0,500}?\}\s*,\s*(\d+)\s*\)",
            fx_js,
        )
        assert match, "No se localizó el poller de portrait-thinking"
        interval = int(match.group(1))
        assert interval >= 200, (
            f"poller de thinking/streaming a {interval}ms. <200ms compite "
            f"con scroll por main thread. 250ms es suficiente — el delay "
            f"para empezar el sonido es imperceptible."
        )

    def test_affection_poll_at_least_1000ms(self, fx_js):
        """Affection es un evento raro (cambia tras cada respuesta)."""
        # El poller de affection tiene .ashley-affection-number
        match = re.search(
            r"\.ashley-affection-number[\s\S]{0,2000}?\}\s*,\s*(\d+)\s*\)",
            fx_js,
        )
        assert match, "No se localizó el poller de affection"
        interval = int(match.group(1))
        assert interval >= 1000, (
            f"poller de affection a {interval}ms. Affection cambia 1 vez "
            f"por mensaje (cada 5-30 segundos). 500ms era overkill, "
            f">=1000ms es plenty."
        )

    def test_achievement_poll_at_least_700ms(self, fx_js):
        """Achievements son eventos rarísimos."""
        match = re.search(
            r"\.achievement-toast[\s\S]{0,500}?\}\s*,\s*(\d+)\s*\)",
            fx_js,
        )
        assert match
        interval = int(match.group(1))
        assert interval >= 700, (
            f"poller de achievements a {interval}ms. Achievements son "
            f"eventos extremadamente raros. >=1000ms es razonable."
        )

    def test_tts_observer_poll_at_least_700ms(self, voice_js):
        """TTS observer hace textContent reads = layout-trigger."""
        # setInterval(() => this._tickObserver(), N) — la N puede ir directo
        match = re.search(
            r"setInterval\([^,]*?_tickObserver[^,]*?,\s*(\d+)\s*\)",
            voice_js,
        )
        assert match, "No se localizó setInterval(_tickObserver, N)"
        interval = int(match.group(1))
        assert interval >= 700, (
            f"TTS observer poll a {interval}ms. textContent reads disparan "
            f"layout recalc. Un mensaje nuevo TTS-ándose 1s tarde es "
            f"imperceptible — vale la pena ahorrar el costo."
        )


# ════════════════════════════════════════════════════════════════════════
#  Backend — caching de vars estáticas
# ════════════════════════════════════════════════════════════════════════


class TestBackendVarCaching:
    def test_backend_port_marker_is_cached(self, rc_src):
        """backend_port_marker lee env var que es estática. Debe estar
        cacheada para no recomputarse en cada state tick."""
        # Buscar la decoración inmediatamente antes de def backend_port_marker
        match = re.search(
            r"@rx\.var\([^)]*\)\s*\n\s*def\s+backend_port_marker",
            rc_src,
        )
        assert match, "No se localizó @rx.var antes de backend_port_marker"
        decorator = match.group(0)
        assert "cache=False" not in decorator, (
            "backend_port_marker tiene cache=False. La env var "
            "ASHLEY_BACKEND_PORT se setea UNA vez al arrancar Electron y "
            "no cambia. cache=False fuerza recompute en cada state tick "
            "= waste."
        )
