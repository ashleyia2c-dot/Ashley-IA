"""Tests para v0.18.4 — TTS leía roleplay aunque _cleanForSpeech tuviera
regex para asteriscos.

Caso reportado por user (varias veces): "haz que no lea cosas entre comillas,
eso es su roleplay" → fix con regex → "sigue diciendo lo del juego de rol".

Causa raíz: Reflex renderiza Ashley vía `rx.markdown(m["content"])`. Markdown
convierte `*acción*` y `_acción_` en `<em>acción</em>`. El observer leía
`latest.textContent`, que ELIMINA los asteriscos/underscores al ser ya tags
HTML. El regex `\\*[^*\\n]{2,120}\\*` no matcheaba nada porque los marcadores
no estaban en el texto extraído.

Fix: nuevo helper `_extractSpeechText(rootEl)` que walka el DOM saltando
elementos `<em>` e `<i>` (que es donde markdown deposita el roleplay
italicizado). El regex sigue activo como fallback para texto crudo y comillas
que markdown no procesa.

Estos tests son guards estáticos contra regresión a `latest.textContent`
directo y contra eliminación del walker DOM.
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASHLEY_VOICE = REPO_ROOT / "assets" / "ashley_voice.js"


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  El walker DOM existe y es usado por el observer
# ════════════════════════════════════════════════════════════════════════


class TestExtractSpeechTextHelper:
    def test_helper_function_exists(self, voice_js):
        """Debe existir `_extractSpeechText` — el helper que walka el DOM
        saltando italics."""
        assert "_extractSpeechText" in voice_js, (
            "ashley_voice.js no define _extractSpeechText. Sin este helper, "
            "el observer cae a `latest.textContent` directo, que devuelve "
            "el texto SIN los asteriscos/underscores (markdown ya los "
            "convirtió en <em>). El regex de roleplay no matchea y la TTS "
            "lee la acción narrativa."
        )

    def test_helper_skips_em_and_i_tags(self, voice_js):
        """El walker debe saltar tags EM e I — markdown italiciza con esos."""
        # Buscamos el set de tags a saltar
        assert "'EM'" in voice_js and "'I'" in voice_js, (
            "_extractSpeechText debe declarar SKIP_TAGS = {'EM', 'I'}. "
            "Markdown convierte *...* y _..._ en <em>, y algunos parsers "
            "usan <i>. Saltarlos es lo que evita que la TTS los vocalice."
        )

    def test_helper_handles_text_nodes(self, voice_js):
        """Debe leer Node.TEXT_NODE para acumular texto."""
        assert "Node.TEXT_NODE" in voice_js, (
            "_extractSpeechText debe walkear Node.TEXT_NODE (hojas de texto). "
            "Sin esto no extrae nada útil."
        )

    def test_helper_recurses_through_children(self, voice_js):
        """Debe recursar en los hijos para no perder texto anidado."""
        # Patrón típico de recursión en walker
        assert "childNodes" in voice_js, (
            "_extractSpeechText debe iterar childNodes recursivamente. "
            "Sin recursión, sólo extrae el primer nivel y pierde texto "
            "dentro de <p>, <strong>, etc."
        )


# ════════════════════════════════════════════════════════════════════════
#  El observer USA el helper (no `latest.textContent` crudo)
# ════════════════════════════════════════════════════════════════════════


class TestObserverUsesHelper:
    def test_observer_calls_extract_speech_text(self, voice_js):
        """`_tickObserver` debe extraer texto vía `_extractSpeechText(latest)`,
        NO vía `latest.textContent` directo."""
        # Buscamos el patrón de uso real
        assert "this._extractSpeechText(latest)" in voice_js, (
            "_tickObserver no llama _extractSpeechText(latest). Si vuelve "
            "a usar `latest.textContent` directo, se pierde el filtro de "
            "<em>/<i> y la TTS lee el roleplay otra vez."
        )

    def test_bootstrap_baseline_also_uses_helper(self, voice_js):
        """El baseline al bootstrap debe usar el mismo helper para que la
        comparación posterior (text === _lastAshleyText) sea consistente."""
        assert "this._extractSpeechText(latestEl)" in voice_js, (
            "El bootstrap del observer debe usar _extractSpeechText(latestEl) "
            "para tomar baseline. Si el baseline usa textContent y el tick "
            "usa _extractSpeechText, los strings serán SIEMPRE diferentes "
            "y la TTS leerá el último mensaje del historial al iniciar."
        )

    def test_no_direct_textcontent_in_tick_check(self, voice_js):
        """En la lógica de detección de mensaje nuevo (dentro de _tickObserver
        post-bootstrap) NO debe haber `latest.textContent`. Si vuelve, el
        regex de asteriscos no matcheará y se vocalizará el roleplay."""
        # La sección crítica está entre "// Es un mensaje nuevo" y _syncFromState
        # Si alguien hace `const text = (latest.textContent || ...)` ahí, falla.
        # Buscamos específicamente esa antigua forma:
        bad_pattern = "(latest.textContent || '').trim()"
        assert bad_pattern not in voice_js, (
            f"Encontré `{bad_pattern}` en ashley_voice.js. Esto significa "
            "que alguien revirtió el fix v0.18.4. Usar textContent directo "
            "rompe el filtro de roleplay porque markdown ya quitó los "
            "asteriscos/underscores."
        )


# ════════════════════════════════════════════════════════════════════════
#  _cleanForSpeech sigue activo como fallback
# ════════════════════════════════════════════════════════════════════════


class TestCleanForSpeechRegexes:
    """El walker DOM cubre el flujo principal (Ashley → markdown → DOM),
    pero _cleanForSpeech sigue ejecutándose después como red de seguridad
    para testSpeak() con texto crudo y para comillas que markdown no procesa.
    """

    def test_does_NOT_strip_quoted_text(self, voice_js):
        """v0.19.25 — INVERTIDO: ahora SÍ leemos texto entre comillas.
        Antes _cleanForSpeech eliminaba todo "..." asumiendo roleplay
        ("se ríe", "levanta una ceja"). Pero Ashley usa comillas para
        títulos de canciones ("Manchild", "Espresso"), nombres propios,
        citas. Filtrarlos rompía la TTS — user no oía qué canción puso.
        """
        # El regex que filtraba comillas dobles rectas NO debe estar.
        # (El código de v0.18.3 era: .replace(/\"[^\"\\n]{2,120}\"/g, ''))
        assert ".replace(/\"[^\"" not in voice_js, (
            "v0.19.25: las comillas YA NO deben filtrarse — Ashley las "
            "usa para títulos de canciones / nombres / citas que SÍ debe "
            "leer la TTS"
        )

    def test_does_NOT_strip_guillemets(self, voice_js):
        """v0.19.25 — guillemets españoles «...» tampoco se filtran.
        Mismo razonamiento: pueden ser títulos en español, no roleplay.
        El roleplay real va entre asteriscos *así*."""
        # Buscar el regex específico que filtraba «...»
        assert ".replace(/«" not in voice_js, (
            "v0.19.25: guillemets ya NO se filtran — el roleplay real "
            "va entre asteriscos, no entre «»"
        )

    def test_strips_mood_action_tags(self, voice_js):
        """Tags [mood:...] y [action:...] deben filtrarse (defensa en
        profundidad — el backend ya los strippea pero a veces se cuelan)."""
        assert "\\[mood:" in voice_js, "Filtro [mood:...] desaparecido"
        assert "\\[action:" in voice_js, "Filtro [action:...] desaparecido"
