"""Tests para optimizaciones del Settings dialog (v0.16.14).

CONTEXTO:
─────────
El user reportaba: "le doy a más ajustes y el menu tarda 1 segundo en
abrirse cuando debería ser instantáneo".

Causas identificadas tras audit profundo:

1. Settings dialog (~750 líneas con rx.cond anidados, sliders, radio
   groups, foreaches) estaba SIEMPRE en el DOM aunque show_settings=False.
   React evaluaba todas sus condicionales en CADA state change → lag
   general en la app + primera apertura era costosa por mount masivo.

2. `toggle_settings()` llamaba `refresh_ollama_status()` SÍNCRONAMENTE.
   Si el user usa Ollama, el ping con timeout 0.8s bloqueaba el UI.
   Settings tardaba 800ms-1s en aparecer aunque la apertura visual
   debería ser instantánea.

3. `grok_key_status` con `cache=False` se recomputaba en cada state
   tick — innecesario porque la API key se setea UNA vez al startup
   y no cambia durante la sesión.

FIXES APLICADOS:

1. Lazy mount del form interior con rx.cond(show_settings, form, fragment).
   La dialog.root y dialog.content quedan siempre montadas (shells
   ligeros) pero el form de 750 líneas solo se monta al abrir.

2. toggle_settings convertido en generator con yield ANTES del ping
   de Ollama. UI se actualiza inmediatamente; el ping (si aplica) corre
   en background y push el resultado cuando llega.

3. grok_key_status con cache=True.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_PY = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


@pytest.fixture(scope="module")
def rc_src() -> str:
    return RC_PY.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  Lazy mount del settings form
# ════════════════════════════════════════════════════════════════════════


class TestSettingsDialogLazyMount:
    """El form gigante del Settings debe estar dentro de un rx.cond
    para que solo se monte cuando show_settings=True."""

    def test_form_wrapped_in_rx_cond(self, rc_src):
        """Buscar el patrón `rx.cond(\n State.show_settings,\n rx.form(`
        que indica el lazy-mount del form."""
        # rx.cond(\n  State.show_settings, ... rx.form(
        pattern = (
            r"rx\.cond\(\s*\n\s*State\.show_settings\s*,\s*\n\s*rx\.form\("
        )
        match = re.search(pattern, rc_src)
        assert match, (
            "El form de Settings NO está envuelto en rx.cond(State.show_settings, ...). "
            "Sin esto, las ~750 líneas del form están siempre en el DOM y "
            "React evalúa todas las condicionales internas en cada state "
            "change → lag general."
        )

    def test_settings_dialog_still_uses_open_state(self, rc_src):
        """El dialog.root sigue usando open=State.show_settings para
        animaciones de Radix."""
        match = re.search(r"open\s*=\s*State\.show_settings", rc_src)
        assert match, (
            "rx.dialog.root debe seguir teniendo open=State.show_settings "
            "para que Radix maneje las animaciones de apertura/cierre."
        )


# ════════════════════════════════════════════════════════════════════════
#  toggle_settings non-blocking para Ollama
# ════════════════════════════════════════════════════════════════════════


class TestToggleSettingsNonBlocking:
    """toggle_settings debe yield-ear el cambio de show_settings ANTES
    de hacer el ping a Ollama (que bloquea hasta 0.8s)."""

    def test_toggle_settings_yields_before_ollama_ping(self, rc_src):
        """En toggle_settings, debe haber un yield ENTRE el set de
        show_settings y el refresh_ollama_status."""
        # Extraer el cuerpo de toggle_settings
        match = re.search(
            r"def\s+toggle_settings\s*\(\s*self\s*\)[^:]*:([\s\S]*?)\n    def ",
            rc_src,
        )
        assert match, "No se localizó def toggle_settings"
        body = match.group(1)

        # Encontrar las posiciones del set y del refresh
        set_pos = body.find("self.show_settings = not self.show_settings")
        ref_pos = body.find("self.refresh_ollama_status()")
        # Verificar que entre ambos hay un yield
        if set_pos != -1 and ref_pos != -1 and ref_pos > set_pos:
            between = body[set_pos:ref_pos]
            assert "yield" in between, (
                "toggle_settings llama refresh_ollama_status() SIN yield "
                "previo. Eso bloquea el UI hasta 0.8s en el ping. Debe "
                "yieldear ANTES del ping para que Settings se abra "
                "instantáneamente."
            )


# ════════════════════════════════════════════════════════════════════════
#  grok_key_status caching
# ════════════════════════════════════════════════════════════════════════


class TestGrokKeyStatusCached:
    def test_grok_key_status_uses_cache_true(self, rc_src):
        """grok_key_status NO debe tener cache=False. La API key se
        setea UNA vez al startup."""
        match = re.search(
            r"@rx\.var\(([^)]*)\)\s*\n\s*def\s+grok_key_status",
            rc_src,
        )
        assert match
        decorator_args = match.group(1)
        assert "cache=False" not in decorator_args, (
            "grok_key_status tiene cache=False. La API key (XAI_API_KEY) "
            "se setea UNA vez al startup desde Electron safeStorage; no "
            "cambia durante la sesión. cache=False fuerza recompute en "
            "cada state tick = waste."
        )
