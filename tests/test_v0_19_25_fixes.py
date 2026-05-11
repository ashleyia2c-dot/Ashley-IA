"""Regression tests for v0.19.25 fixes:

1. TTS lee texto entre comillas (títulos canciones, nombres propios). Antes
   _cleanForSpeech eliminaba todo "..." asumiendo roleplay.

2. Reset 3D expressions a neutral cuando empieza a hablar. Antes happy de
   la pose se mantenía y el viseme se SUMABA → boca exagerada / cuadrada.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VOICE_JS = REPO_ROOT / "assets" / "ashley_voice.js"
WIDGET_HTML = REPO_ROOT / "assets" / "ashley_3d_widget.html"


# ════════════════════════════════════════════════════════════════════════
#  TTS quoted text
# ════════════════════════════════════════════════════════════════════════


class TestTTSReadsQuotedText:
    def test_clean_for_speech_no_longer_strips_double_quotes(self):
        """v0.19.25 — _cleanForSpeech NO debe quitar texto entre "...":
        son títulos de canciones, nombres, citas — la TTS los debe leer."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # Buscar el regex específico que filtraba comillas dobles
        assert '.replace(/"[^"' not in src, (
            "v0.19.25 fix: _cleanForSpeech YA NO debe contener "
            "`.replace(/\"[^\"\\n]{2,120}\"/g, '')` — eso eliminaba títulos "
            "de canciones ('Manchild', 'Espresso') que SÍ deben leerse."
        )

    def test_clean_for_speech_no_longer_strips_curly_quotes(self):
        """Comillas curly tipográficas también se preservan ahora."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # En el código original existía un regex con curly quotes
        # (“ ” y ‘ ’). Comprobamos que NO está.
        assert "[^“”" not in src and "[^‘’" not in src, (
            "Las comillas curly NO deben filtrarse en _cleanForSpeech"
        )

    def test_clean_for_speech_no_longer_strips_guillemets(self):
        """Guillemets españoles «...» tampoco se filtran."""
        src = VOICE_JS.read_text(encoding="utf-8")
        assert ".replace(/«" not in src, (
            "Guillemets españoles ya NO deben filtrarse en _cleanForSpeech"
        )

    def test_clean_for_speech_still_strips_asterisks_and_underscores(self):
        """El roleplay REAL (asteriscos y guiones bajos) SIGUE filtrado.
        El fix solo afecta a las comillas — el resto del strip está intacto."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # Asteriscos para roleplay siguen filtrados
        assert "\\*[^*\\n]{2,120}\\*" in src, (
            "El regex de asteriscos *...* sigue siendo necesario para "
            "roleplay markdown raw (fallback de _extractSpeechText)"
        )
        # Underscores para roleplay siguen filtrados
        assert "_[^_\\n]{2,120}_" in src, (
            "El regex de underscores _..._ sigue siendo necesario"
        )

    def test_clean_for_speech_still_strips_mood_action_tags(self):
        """[mood:...] y [action:...] siguen filtrados (no son texto a leer)."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # Los regex en el JS source aparecen como /\[mood:[^\]]+\]/gi —
        # buscamos el prefix `\[mood:` con escape literal del JS.
        assert r"\[mood:" in src, "[mood:...] debe seguir filtrado"
        assert r"\[action:" in src, "[action:...] debe seguir filtrado"


# ════════════════════════════════════════════════════════════════════════
#  3D expression reset on talking start
# ════════════════════════════════════════════════════════════════════════


class TestAshley3DNeutralOnTalking:
    def test_setTalking_true_neutralizes_expressions(self):
        """Cuando isTalking pasa a true, las expressions (happy/sorrow/etc.)
        deben resetearse a 0 para que el viseme no se sume sobre una boca
        ya sonriente (causaba apertura grotesca con poses como excited)."""
        src = WIDGET_HTML.read_text(encoding="utf-8")
        # Buscar el handler de setTalking
        import re
        match = re.search(
            r"case 'ashley3d:setTalking':\s*\{(.*?)\}\s*break;",
            src, re.DOTALL,
        )
        assert match, "Handler ashley3d:setTalking no encontrado"
        body = match.group(1)
        # Debe tener el array NEUTRALIZE con las 5 expressions clave
        assert "NEUTRALIZE" in body, (
            "v0.19.25: handler setTalking debe definir array NEUTRALIZE con "
            "las expressions a resetear cuando empieza a hablar"
        )
        for expr in ["happy", "sorrow", "relaxed", "angry", "surprised"]:
            assert f"'{expr}'" in body, (
                f"NEUTRALIZE debe incluir la expression '{expr}'"
            )
        # Debe llamar setValue(expr, 0) iterando sobre NEUTRALIZE
        assert "setValue(expr, 0)" in body, (
            "Debe setear cada expression NEUTRALIZE a 0 con setValue"
        )

    def test_setTalking_true_resets_proximity_smile(self):
        """Reset también proximitySmile / lastProximitySmile cuando habla."""
        src = WIDGET_HTML.read_text(encoding="utf-8")
        import re
        match = re.search(
            r"case 'ashley3d:setTalking':\s*\{(.*?)\}\s*break;",
            src, re.DOTALL,
        )
        assert match
        body = match.group(1)
        assert "proximitySmile = 0" in body, (
            "Debe resetear proximitySmile a 0 al empezar a hablar"
        )
        assert "lastProximitySmile = 0" in body, (
            "Debe resetear lastProximitySmile a 0"
        )

    def test_proximity_smile_skipped_when_talking(self):
        """El loop de animation NO debe aplicar proximity smile mientras
        isTalking — sino el smile reaplica frame-by-frame y el reset es vano."""
        src = WIDGET_HTML.read_text(encoding="utf-8")
        # Buscar el bloque del proximity smile en animate()
        import re
        # Pattern: "if (currentVrm?.expressionManager <something> isTalking"
        # Debe haber un check de !isTalking en el if
        match = re.search(
            r"if\s*\(\s*currentVrm\?\.expressionManager\s*&&\s*!isTalking\s*\)\s*\{[^}]*?proximitySmile",
            src, re.DOTALL,
        )
        assert match, (
            "El bloque de proximity smile en animate() debe estar gateado "
            "con !isTalking — sino se aplica cada frame durante el habla "
            "y derrota el reset del setTalking handler"
        )
