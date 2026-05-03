"""Tests para el sistema de auto-scroll del chat (v0.16.14, REWRITE).

CONTEXTO:
─────────
El user reportó scroll lag y "saltitos" durante uso normal del chat.
Tras múltiples intentos de fix incremental que NO solucionaban el
problema, se reescribió el sistema completo desde cero con principios
claros:

1. Una sola variable de estado: `_following` (bool).
2. Solo eventos de scroll del USER actualizan `_following`.
3. Scrolls programáticos se distinguen vía `_suppressUntil` (timestamp).
4. Auto-scroll solo si `_following=true` Y `scrollHeight` creció.
5. Initial scroll: una sola pasada al detectar container + retry tras
   fonts.ready. SIN polling agresivo.

ESTOS TESTS BLOQUEAN:
─────────────────────
- Que alguien reintroduzca `STICK_MARGIN_PX`, `userHasScrolled`,
  `isProgrammaticScroll` (los flags antiguos del modelo defectuoso).
- Que las burbujas vuelvan a tener `backdrop-filter` (causaba 50 blur
  recalcs por scroll frame).
- Que el scroll container reciba hints de capa GPU (`will-change`,
  `translateZ`) — causaban subpixel jumps.
- Que el rewrite pierda alguna de sus invariantes clave.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
STYLES_PY = REPO_ROOT / "reflex_companion" / "styles.py"
ASHLEY_FX = REPO_ROOT / "assets" / "ashley_fx.js"


@pytest.fixture(scope="module")
def styles_src() -> str:
    return STYLES_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def fx_js() -> str:
    return ASHLEY_FX.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  CSS — fix #1: NO blur en burbujas individuales
# ════════════════════════════════════════════════════════════════════════


class TestBubblesNoBackdropFilter:
    """El bug crítico de scroll lag. Cada bubble con `backdrop-filter:
    blur` significa N recalculaciones de blur por scroll frame."""

    def test_bubble_ashley_no_backdrop_filter(self, styles_src):
        match = re.search(
            r"\.bubble-ashley\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match, "No se localizó la regla .bubble-ashley"
        block = match.group(1)
        assert "backdrop-filter" not in block, (
            "REGRESIÓN: .bubble-ashley tiene backdrop-filter de nuevo. "
            "Con 50 burbujas en el chat, scroll → 50 blur recalcs por "
            "frame → tirones."
        )

    def test_bubble_user_no_backdrop_filter(self, styles_src):
        match = re.search(
            r"\.bubble-user\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match
        block = match.group(1)
        assert "backdrop-filter" not in block


# ════════════════════════════════════════════════════════════════════════
#  CSS — fix #2: NO hints de capa GPU en scroll container
# ════════════════════════════════════════════════════════════════════════


class TestChatScrollNoForcedGpuLayer:
    """`will-change: transform` y `transform: translateZ(0)` en el scroll
    container provocaban subpixel rendering jumps en algunos Chromium."""

    def test_no_will_change(self, styles_src):
        match = re.search(
            r"\.ashley-chat-scroll\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match
        block = match.group(1)
        assert "will-change" not in block

    def test_no_translate_z(self, styles_src):
        match = re.search(
            r"\.ashley-chat-scroll\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match
        block = match.group(1)
        assert "translateZ" not in block and "translate3d" not in block


# ════════════════════════════════════════════════════════════════════════
#  JS — el rewrite usa el modelo simple, no el viejo
# ════════════════════════════════════════════════════════════════════════


class TestRewriteModelInPlace:
    """El rewrite v0.16.14 usa exactamente estas variables de estado.
    Bloqueamos regresiones a los flags del modelo defectuoso anterior."""

    def test_uses_following_flag(self, fx_js):
        """`_following` es la única variable de estado de la decision."""
        assert "_following" in fx_js, (
            "El rewrite no usa _following. Es la variable principal del "
            "modelo simple — sin ella el rewrite no está completo."
        )

    def test_uses_suppress_until_timestamp(self, fx_js):
        """`_suppressUntil` distingue scroll user vs programático."""
        assert "_suppressUntil" in fx_js, (
            "Falta _suppressUntil. Sin él no podemos diferenciar nuestro "
            "scrollTop=X de un scroll del user → race condition."
        )

    def test_no_old_stick_margin(self, fx_js):
        """STICK_MARGIN_PX era del modelo viejo. Reemplazado por
        NEAR_BOTTOM_PX en el nuevo modelo (más claro)."""
        assert "STICK_MARGIN_PX" not in fx_js, (
            "REGRESIÓN: STICK_MARGIN_PX está de vuelta. Es del modelo viejo "
            "que tenía bugs. Usa NEAR_BOTTOM_PX."
        )

    def test_no_old_user_has_scrolled(self, fx_js):
        """userHasScrolled era un parche; el rewrite no lo necesita
        porque el initial scroll ya no hace polling agresivo. Buscamos
        solo en código (no en comentarios ni strings)."""
        # Strip comentarios de línea (/* ... */ multiline + // ...)
        no_block_comments = re.sub(r"/\*[\s\S]*?\*/", "", fx_js)
        no_line_comments = re.sub(r"//[^\n]*", "", no_block_comments)
        assert "userHasScrolled" not in no_line_comments, (
            "REGRESIÓN: userHasScrolled está de vuelta en CÓDIGO (no "
            "comentario). Era parche del modelo viejo."
        )

    def test_no_old_is_programmatic_scroll(self, fx_js):
        """isProgrammaticScroll era una bool flag con timing frágil
        (rAF). _suppressUntil con timestamp es más robusto."""
        assert "isProgrammaticScroll" not in fx_js, (
            "REGRESIÓN: isProgrammaticScroll bool flag está de vuelta. "
            "El rewrite usa _suppressUntil (timestamp) que es robusto "
            "ante eventos scroll que llegan en frame siguientes."
        )

    def test_uses_near_bottom_px_constant(self, fx_js):
        assert "NEAR_BOTTOM_PX" in fx_js


# ════════════════════════════════════════════════════════════════════════
#  JS — invariantes clave del rewrite
# ════════════════════════════════════════════════════════════════════════


class TestRewriteInvariants:
    """Cada invariante crítica del rewrite tiene su test que la blockea."""

    def test_scroll_listener_skips_during_suppress_window(self, fx_js):
        """El listener de `scroll` debe ignorar eventos cuando
        Date.now() < _suppressUntil — son consecuencia de nuestro set."""
        match = re.search(
            r"addEventListener\(\s*['\"]scroll['\"][\s\S]{0,300}?\}\s*,\s*\{\s*passive",
            fx_js,
        )
        assert match, "No se localizó el listener de scroll del rewrite"
        block = match.group(0)
        assert "_suppressUntil" in block, (
            "El listener de scroll no comprueba _suppressUntil. Sin esto "
            "nuestros propios scrollTop= disparan el listener y ensucian "
            "_following."
        )

    def test_following_only_updated_in_user_scroll(self, fx_js):
        """`_following = ...` debe aparecer en sitios controlados:
        1. Declaración inicial (var _following = true)
        2. Scroll listener (recompute on user scroll)
        3. forceFollow API pública (cuando user clickea Send y queremos
           garantizar que sigue a Ashley)
        Total: máximo 3 asignaciones. Más indica lógica acumulada."""
        no_block_comments = re.sub(r"/\*[\s\S]*?\*/", "", fx_js)
        no_line_comments = re.sub(r"//[^\n]*", "", no_block_comments)
        assignments = re.findall(
            r"\b_following\s*=(?!=)\s*",
            no_line_comments,
        )
        assert len(assignments) <= 3, (
            f"Múltiples asignaciones a _following en código ({len(assignments)}). "
            f"Esperado: 1 declaración + 1 listener + 1 forceFollow."
        )

    def test_mutation_observer_uses_raf_throttle(self, fx_js):
        """El MutationObserver de chat-scroll coalesca burst de mutations
        con rAF. Lo identificamos por la variable scrollObs."""
        match = re.search(
            r"scrollObs\s*=\s*new\s+MutationObserver[\s\S]{0,800}?observe\(",
            fx_js,
        )
        assert match, "No se localizó scrollObs"
        block = match.group(0)
        assert "requestAnimationFrame" in block

    def test_mutation_observer_checks_scrollheight_grew(self, fx_js):
        """Solo scrolleamos si scrollHeight creció — sin esto los
        re-renders fantasma de Reflex causan saltitos."""
        match = re.search(
            r"scrollObs\s*=\s*new\s+MutationObserver[\s\S]{0,1200}?observe\(",
            fx_js,
        )
        assert match, "No se localizó scrollObs"
        block = match.group(0)
        assert "_lastScrollHeight" in block, (
            "El observer no comprueba _lastScrollHeight. Sin esto, "
            "mutations sin cambio real fuerzan scroll → saltitos."
        )

    def test_initial_scroll_is_single_pass(self, fx_js):
        """No debe haber polling agresivo de initial scroll. El rewrite
        hace UNA pasada al inicio + retry tras fonts.ready."""
        # El polling viejo era `setTimeout(_initialScroll, 75)`
        assert "_initialScroll" not in fx_js, (
            "REGRESIÓN: _initialScroll polling está de vuelta. Era del "
            "modelo viejo que peleaba con el user durante 3s."
        )
        # Tampoco debe haber un loop de 40 attempts × 75ms
        assert "_initialScrollAttempts" not in fx_js

    def test_fonts_ready_only_scrolls_if_following(self, fx_js):
        """Si el user scrolleó arriba durante load de fonts, NO le
        movemos cuando termina."""
        match = re.search(
            r"document\.fonts\.ready[\s\S]{0,300}?\}\)\.catch",
            fx_js,
        )
        assert match
        block = match.group(0)
        assert "_following" in block, (
            "fonts.ready callback no respeta _following. Si user scrolleó "
            "arriba durante load, le tirará de vuelta abajo."
        )


# ════════════════════════════════════════════════════════════════════════
#  Comportamiento esperado documentado
# ════════════════════════════════════════════════════════════════════════


class TestNearBottomThreshold:
    """NEAR_BOTTOM_PX define cuán cerca del fondo cuenta como 'siguiendo'.
    Demasiado pequeño: el user pierde el follow al estar 'casi' abajo.
    Demasiado grande: el user no puede scrollear levemente sin que el
    sistema crea que sigue stuck."""

    def test_near_bottom_is_reasonable(self, fx_js):
        # Buscamos la asignación de variable, no menciones en comentarios.
        match = re.search(
            r"var\s+NEAR_BOTTOM_PX\s*=\s*(\d+)",
            fx_js,
        )
        assert match, "No se localizó var NEAR_BOTTOM_PX = ..."
        threshold = int(match.group(1))
        assert 20 <= threshold <= 100, (
            f"NEAR_BOTTOM_PX={threshold} fuera de rango razonable [20-100]. "
            f"Demasiado bajo: touchpad momentum scroll perdido. "
            f"Demasiado alto: user no puede levantar la vista sin perder "
            f"control."
        )


class TestSuppressWindow:
    """SUPPRESS_MS debe ser > 16ms (un frame) para cubrir el delay
    típico entre scrollTop= y el evento `scroll` resultante."""

    def test_suppress_window_covers_event_delay(self, fx_js):
        match = re.search(
            r"SUPPRESS_MS\s*=\s*(\d+)",
            fx_js,
        )
        assert match
        ms = int(match.group(1))
        assert ms >= 32, (
            f"SUPPRESS_MS={ms} es muy corto. Chromium puede entregar el "
            f"evento scroll resultante de scrollTop= varios ms después; "
            f"un valor <32ms es propenso a race conditions."
        )
        assert ms <= 200, (
            f"SUPPRESS_MS={ms} es excesivo. Bloquea scroll del user "
            f"justo después de un auto-scroll legítimo."
        )


class TestForceFollowAPI:
    """v0.16.14 — el auto-scroll expone window.__ashleyScroll.forceFollow()
    para que el optimistic UI fuerce _following=true cuando el user envía
    un mensaje. Sin esto, si el user había scrolleado arriba antes de
    pulsar Send, el chat NO seguía la respuesta de Ashley."""

    def test_window_ashley_scroll_exposed(self, fx_js):
        assert "window.__ashleyScroll" in fx_js, (
            "El auto-scroll no expone window.__ashleyScroll. Sin esto, "
            "el optimistic UI no puede sincronizarse con el sistema → "
            "el chat no sigue a Ashley si user scrolleó arriba antes de "
            "enviar."
        )

    def test_force_follow_exists(self, fx_js):
        assert "forceFollow" in fx_js, (
            "Falta el método forceFollow. Es el que el optimistic UI "
            "llama al hacer submit para garantizar que el chat sigue a "
            "Ashley."
        )

    def test_optimistic_ui_uses_force_follow(self, fx_js):
        """El optimistic UI submit handler debe llamar forceFollow."""
        # Buscar la llamada a forceFollow en el bloque post-playSend
        match = re.search(
            r"playSend[\s\S]{0,500}?__ashleyScroll[\s\S]{0,200}?forceFollow",
            fx_js,
        )
        assert match, (
            "El optimistic UI no llama __ashleyScroll.forceFollow() tras "
            "el playSend. Sin esto, _following queda desincronizado y el "
            "chat no sigue a Ashley."
        )
