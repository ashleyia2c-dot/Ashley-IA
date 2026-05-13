"""Regression tests para v0.19.49 — filtro meta-narrativa + anti-action-repeat.

Bugs reportados:

1. **Meta-comment leak**: Ashley emitió en bubble visible:
   "No action tag — just confirming the launch."
   Era texto de razonamiento interno que se filtró al chat.

2. **Action repeat**: user pidió "ahora abre lol" pero Ashley emitió
   [action:volume:set:100] otra vez (del turno anterior) además de
   open_app:LoL. Sin que se le pidiera.

Fixes:
  • parsing.clean_display: nuevos patterns para "no action tag",
    "just confirming", "no tag needed", etc en EN/ES/FR.
  • prompts × 7 idiomas: regla "no repitas actions del turno anterior".
  • prompts × 7 idiomas: regla "no escribas meta-comentarios".
"""
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  Filtro de meta-narrativa "No action tag — just confirming"
# ════════════════════════════════════════════════════════════════════════


class TestMetaNarrativeFilter:
    def test_filters_real_user_bug_text(self):
        """Caso EXACTO reportado en la captura del user."""
        from reflex_companion.parsing import clean_display
        text = (
            "Ya está, boss — League of Legends lanzado y a todo volumen "
            "con E.T. de fondo. Dale unos segundos para que cargue la "
            "ventana, y prepárate para dominar. ¿Vas a jugar una ranked "
            "rápida o qué?\n"
            "No action tag — just confirming the launch."
        )
        cleaned = clean_display(text).strip()
        assert "No action tag" not in cleaned, (
            f"v0.19.49: 'No action tag — just confirming the launch.' "
            f"debe filtrarse del display. Got: {cleaned[-100:]!r}"
        )
        assert "just confirming the launch" not in cleaned.lower()
        # El contenido principal debe preservarse
        assert "League of Legends" in cleaned
        assert "ranked" in cleaned

    @pytest.mark.parametrize("variant", [
        "Listo, boss. No tag needed.",
        "Abriéndolo. Just confirming the launch.",
        "Hecho, boss. Sin tag de acción — solo confirmo.",
        "Voilà. Pas de tag d'action — juste confirmer.",
        "Done. No tags emitted.",
    ])
    def test_filters_meta_variants(self, variant):
        """Variantes en EN/ES/FR del meta-comment final."""
        from reflex_companion.parsing import clean_display
        cleaned = clean_display(variant).strip()
        # No debe quedar ningún meta-comment evidente
        bad_phrases = ["no tag", "no action tag", "just confirming",
                       "sin tag", "pas de tag", "tag d'action",
                       "tag emitted"]
        cleaned_lower = cleaned.lower()
        for bad in bad_phrases:
            assert bad not in cleaned_lower, (
                f"v0.19.49: '{bad}' debe filtrarse de variant {variant!r}. "
                f"Got: {cleaned!r}"
            )

    def test_does_not_filter_legitimate_dialogue(self):
        """Diálogo natural que MENCIONA 'tag' o 'confirming' a mitad de
        frase NO debe ser filtrado — solo trailing meta-comments."""
        from reflex_companion.parsing import clean_display
        legitimate = "Just confirming with you, boss. ¿Quieres que siga?"
        cleaned = clean_display(legitimate).strip()
        # El diálogo debe preservarse intacto (no es trailing meta)
        assert "Just confirming with you" in cleaned
        assert "boss" in cleaned


# ════════════════════════════════════════════════════════════════════════
#  Prompts: regla anti-repetir actions del turno anterior
# ════════════════════════════════════════════════════════════════════════


class TestPromptForbidsActionRepeat:
    @pytest.mark.parametrize("lang_file", [
        "prompts_es.py", "prompts_en.py", "prompts_fr.py",
        "prompts_ja.py", "prompts_de.py", "prompts_ru.py", "prompts_ko.py",
    ])
    def test_prompt_documents_no_action_repeat_rule(self, lang_file):
        """Cada idioma debe documentar la regla 'no repitas actions del
        turno anterior'."""
        src = (REPO_ROOT / "reflex_companion" / lang_file).read_text(
            encoding="utf-8",
        )
        # Indicadores en cada idioma de que la regla está presente
        # (multiple alternative phrasings — basta con una)
        anchors = [
            "del turno anterior",  # ES
            "previous turn",       # EN
            "tour précédent",      # FR
            "前のターン",          # JA
            "vorigen turn",        # DE (case insensitive)
            "предыдущего хода",    # RU
            "이전 턴",              # KO
        ]
        # Buscar el ejemplo concreto de volume + open_app que viene en todos
        has_volume_set_100_example = "volume:set:100" in src
        has_anti_repeat_anchor = any(a.lower() in src.lower() for a in anchors)
        assert has_anti_repeat_anchor and has_volume_set_100_example, (
            f"v0.19.49 ({lang_file}): debe tener regla anti-repetir actions"
            " con ejemplo [volume:set:100][open_app:Spotify] (mal) vs solo"
            " [open_app:Spotify] (bien)"
        )


# ════════════════════════════════════════════════════════════════════════
#  Prompts: regla anti-meta-comments
# ════════════════════════════════════════════════════════════════════════


class TestPromptForbidsMetaComments:
    @pytest.mark.parametrize("lang_file", [
        "prompts_es.py", "prompts_en.py", "prompts_fr.py",
        "prompts_ja.py", "prompts_de.py", "prompts_ru.py", "prompts_ko.py",
    ])
    def test_prompt_documents_no_meta_comments(self, lang_file):
        """Cada idioma debe documentar 'no escribas meta-comments tipo
        No action tag — just confirming'."""
        import re
        src = (REPO_ROOT / "reflex_companion" / lang_file).read_text(
            encoding="utf-8",
        )
        # El ejemplo del bug debe aparecer (allow whitespace between words
        # for line-wrapped strings)
        normalized = re.sub(r"\s+", " ", src).lower()
        assert "no action tag" in normalized, (
            f"v0.19.49 ({lang_file}): debe documentar 'No action tag' como"
            " ejemplo de meta-comment a NO escribir"
        )
        assert "just confirming" in normalized, (
            f"v0.19.49 ({lang_file}): debe documentar 'just confirming'"
            " como ejemplo de meta-comment a NO escribir"
        )
