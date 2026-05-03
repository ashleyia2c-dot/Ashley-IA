"""Tests para el fix del flash negro en transiciones de mood (v0.16.14).

CONTEXTO:
─────────
User reportó: "cuando la imagen 2D de Ashley va cambiando por unos
espacios cortos detiempo se ve todo negro , corrigelo porque parece bug".

Causa: el componente .ashley-mood-image cambia su background-image vía
inline style cuando `current_image` cambia (default → thinking → writing
→ ...). Si la imagen JPG nueva no está cacheada por el browser, hay un
flash negro de 100-300ms mientras se carga.

FIXES APLICADOS:
1. JS: `preloadMoodImages()` al arranque crea `new Image()` para cada
   mood. El browser cachea las imágenes. Los swaps son instantáneos.
2. CSS: `background-color: #1a0e14` (boutique vino oscuro) en lugar de
   transparente, para que cualquier flash futuro sea un tono cálido y
   no un rectángulo negro chillón.
3. CSS: `background-image: url('/ashley_pfp.jpg')` como fallback en el
   selector (sólo aplica antes del primer mount de React).
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASHLEY_FX = REPO_ROOT / "assets" / "ashley_fx.js"
STYLES_PY = REPO_ROOT / "reflex_companion" / "styles.py"


@pytest.fixture(scope="module")
def fx_js() -> str:
    return ASHLEY_FX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def styles_src() -> str:
    return STYLES_PY.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  JS preload
# ════════════════════════════════════════════════════════════════════════


class TestMoodImagePreload:
    def test_preload_function_exists(self, fx_js):
        assert "preloadMoodImages" in fx_js, (
            "Falta la función preloadMoodImages. Sin precarga, el browser "
            "tarda en cargar la imagen mood la primera vez que se la pide "
            "→ flash negro entre transiciones."
        )

    def test_preload_called_in_boot(self, fx_js):
        """preloadMoodImages debe llamarse en boot()."""
        match = re.search(
            r"function\s+boot\s*\(\s*\)\s*\{([\s\S]*?)\n\s*\}",
            fx_js,
        )
        assert match
        body = match.group(1)
        assert "preloadMoodImages" in body, (
            "preloadMoodImages no se llama en boot(). Debe ser una de las "
            "primeras cosas en boot para que las imágenes estén cacheadas "
            "antes de que el user interactúe."
        )

    @pytest.mark.parametrize("mood", [
        "thinking", "writing", "searching",
        "excited", "embarrassed", "tsundere", "soft",
        "surprised", "proud",
    ])
    def test_all_moods_in_preload_list(self, fx_js, mood):
        """Cada mood con asset .jpg debe estar en la lista de preload."""
        # Buscar la lista de moods en preloadMoodImages
        match = re.search(
            r"function\s+preloadMoodImages\s*\(\s*\)\s*\{([\s\S]*?)\n\s*\}",
            fx_js,
        )
        assert match, "No se localizó preloadMoodImages"
        body = match.group(1)
        assert f"'{mood}'" in body, (
            f"Mood '{mood}' no está en la lista de preload. Si Ashley "
            f"cambia a este mood, habrá flash negro."
        )

    def test_preload_keeps_references(self, fx_js):
        """Las imágenes precargadas se guardan en window.__ashleyPreloadedImages
        para evitar que el GC las descarte antes de cachearlas."""
        match = re.search(
            r"function\s+preloadMoodImages\s*\(\s*\)\s*\{([\s\S]*?)\n\s*\}",
            fx_js,
        )
        assert match
        body = match.group(1)
        assert "__ashleyPreloadedImages" in body, (
            "preloadMoodImages no guarda referencias a las imágenes. "
            "El GC puede descartarlas antes de que estén realmente "
            "cacheadas — defeats the purpose."
        )


# ════════════════════════════════════════════════════════════════════════
#  CSS — bloqueo del fallback que rompía el rendering en producción
# ════════════════════════════════════════════════════════════════════════
#
#  v0.16.14 — INTENTO original: añadir `background-color` y `background-image`
#  fallback al CSS de `.ashley-mood-image` para evitar el flash negro entre
#  transiciones de mood.
#
#  RESULTADO: en producción (.exe instalado) el panel se quedaba COMPLETAMENTE
#  negro — el fallback CSS interfería con el inline style de React de manera
#  que la imagen real nunca se mostraba.
#
#  REVERTIDO: el anti-flash se logra ÚNICAMENTE via JS preload (que está más
#  arriba en este archivo). El CSS NO debe tener background-image fallback.
#  Estos tests bloquean reintroducir las propiedades problemáticas.


class TestMoodImageCssNoBgFallback:
    def test_no_background_color_in_rule(self, styles_src):
        """`.ashley-mood-image` NO debe tener background-color hardcoded.
        En producción interfería con el inline style de React."""
        match = re.search(
            r"\.ashley-mood-image\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match
        block = match.group(1)
        assert "background-color" not in block, (
            "REGRESIÓN: .ashley-mood-image tiene background-color en CSS. "
            "Probamos esto en v0.16.14 y rompió el rendering en producción "
            "(panel completamente negro). El anti-flash va via JS preload."
        )

    def test_no_background_image_url_in_rule(self, styles_src):
        """`.ashley-mood-image` NO debe tener background-image: url(...)
        hardcoded — solo el inline style de React debe setearlo."""
        match = re.search(
            r"\.ashley-mood-image\s*\{\{([\s\S]*?)\}\}",
            styles_src,
        )
        assert match
        block = match.group(1)
        # Patrón problemático: background-image: url(...)
        bg_image_pattern = re.search(
            r"background-image\s*:\s*url\(",
            block,
        )
        assert not bg_image_pattern, (
            "REGRESIÓN: .ashley-mood-image tiene background-image: url(...) "
            "hardcoded. Eso interfería con el inline style en producción "
            "(panel negro). La imagen real viene del inline style de React."
        )


# ════════════════════════════════════════════════════════════════════════
#  Conditional clearCache (v0.16.14)
# ════════════════════════════════════════════════════════════════════════


ELECTRON_MAIN = REPO_ROOT / "electron" / "main.js"


@pytest.fixture(scope="module")
def main_js() -> str:
    return ELECTRON_MAIN.read_text(encoding="utf-8")


class TestConditionalClearCache:
    """v0.16.14 — clearCache solía correr en CADA launch. Eso borraba el
    cache de Electron incluidas las imágenes mood (~2.7MB en JPGs). El
    user reportaba flash negro porque las imágenes se re-descargaban
    cada vez.

    Fix: solo clearCache cuando el frontend se rebuildeó esta sesión
    (slow-path). En fast-path (build precompilado reusado) los hashes
    son idénticos a la sesión anterior, así que el cache es válido."""

    def test_has_rebuilt_flag(self, main_js):
        assert "frontendWasRebuiltThisSession" in main_js, (
            "Falta el flag frontendWasRebuiltThisSession. Sin él, "
            "clearCache corre en cada launch incondicionalmente y borra "
            "el cache de imágenes mood → flash negro entre transiciones."
        )

    def test_clear_cache_is_conditional(self, main_js):
        """clearCache debe estar dentro de un `if (frontendWasRebuiltThisSession)`."""
        # Buscar el bloque if que envuelve clearCache
        match = re.search(
            r"if\s*\(\s*frontendWasRebuiltThisSession\s*\)\s*\{[\s\S]{0,500}?clearCache",
            main_js,
        )
        assert match, (
            "clearCache no está dentro de un if (frontendWasRebuiltThisSession). "
            "Sin esto, corre incondicionalmente y borra cache de imágenes."
        )

    def test_fast_path_marks_not_rebuilt(self, main_js):
        """Cuando se toma fast-path, frontendWasRebuiltThisSession=false."""
        # Buscar la asignación frontendWasRebuiltThisSession = false en
        # el bloque del fast-path
        match = re.search(
            r"fast-path[\s\S]{0,500}?frontendWasRebuiltThisSession\s*=\s*false",
            main_js,
        )
        assert match, (
            "El bloque de fast-path no setea frontendWasRebuiltThisSession=false. "
            "Sin esto, clearCache se ejecuta aunque el build no haya cambiado."
        )

    def test_slow_path_marks_rebuilt(self, main_js):
        """Cuando se toma slow-path, frontendWasRebuiltThisSession=true."""
        match = re.search(
            r"_startSingleReflexProcess[\s\S]{0,800}?frontendWasRebuiltThisSession\s*=\s*true",
            main_js,
        ) or re.search(
            r"frontendWasRebuiltThisSession\s*=\s*true[\s\S]{0,500}?_startSingleReflexProcess",
            main_js,
        )
        assert match, (
            "Slow-path no marca frontendWasRebuiltThisSession=true. "
            "Necesario para invalidar cache cuando el build cambió."
        )
