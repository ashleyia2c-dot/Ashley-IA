"""Regression tests para v0.19.40 — fix de Ashley diciendo info incorrecta
de la UI cuando una acción está bloqueada por el toggle Actions.

User reportó: 'el boton action esta en la esquina superior izquierda,
verifica lo que ashley sabe sobre los botones y sus capacidades y
actualizalo porque esta con la info de hace ya un tiempo'.

Bug:
  • En reflex_companion.py, los `blocked_trigger` (texto que se le pasa
    al LLM cuando una acción se bloquea por Actions OFF) decían "arriba
    a la derecha" / "top-right" / "en haut à droite".
  • La realidad: el botón ⚡ Actions está en la BARRA SUPERIOR del
    panel izquierdo, junto a Memories/News/Mobile/Settings (NO en la
    esquina superior derecha — esa zona tiene help/mute/fullscreen/
    affection que son OTROS botones).
  • Resultado: Ashley dirigía al user a la esquina equivocada.

Bonus: faltaban variants para ja/de/ru/ko (caían al fallback EN).

Fix v0.19.40:
  • Reescribir las 3 strings existentes (es/fr/en) describiendo la
    posición por VECINDAD a botones reconocibles ("al lado de Memories
    y News") en vez de por coordenada absoluta.
  • Añadir 4 nuevos triggers (ja/de/ru/ko) con la misma estructura.
"""
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


def _extract_blocked_trigger_block() -> str:
    """Extrae el bloque que contiene los blocked_trigger del .py."""
    src = RC_FILE.read_text(encoding="utf-8")
    # Localizar la zona de los blocked_trigger (entre el if blocked_action
    # y el yield from _stream_with_trigger)
    start = src.find("if blocked_action:")
    assert start != -1, "if blocked_action: bloque no encontrado"
    end = src.find("yield from self._stream_with_trigger(blocked_trigger)", start)
    assert end != -1, "yield from _stream_with_trigger no encontrado"
    return src[start:end]


# ════════════════════════════════════════════════════════════════════════
#  Fix 1 — Ya no decir "derecha"/"right" sobre el toggle Actions
# ════════════════════════════════════════════════════════════════════════


class TestBlockedTriggerNoLongerSaysRight:
    """v0.19.40 — el blocked_trigger NO debe decir "arriba a la derecha" /
    "top-right" / "en haut à droite" porque eso confunde al user (el
    botón está en la BARRA SUPERIOR izquierda, no en la esquina derecha)."""

    def test_es_no_longer_says_arriba_a_la_derecha(self):
        block = _extract_blocked_trigger_block()
        # Buscar el trigger ES específicamente
        es_block_match = re.search(
            r'_lang\.startswith\("es"\):.*?(?=elif _lang|else:)',
            block, re.DOTALL,
        )
        assert es_block_match, "Bloque ES no encontrado"
        es_text = es_block_match.group(0)
        assert "arriba a la derecha" not in es_text, (
            "v0.19.40 fix: ES no debe decir 'arriba a la derecha' "
            "(el ⚡ Actions está en la barra superior IZQUIERDA, junto "
            "a Memories y News)"
        )

    def test_fr_no_longer_says_haut_a_droite(self):
        block = _extract_blocked_trigger_block()
        fr_block_match = re.search(
            r'_lang\.startswith\("fr"\):.*?(?=elif _lang|else:)',
            block, re.DOTALL,
        )
        assert fr_block_match, "Bloque FR no encontrado"
        fr_text = fr_block_match.group(0)
        assert "en haut à droite" not in fr_text, (
            "FR no debe decir 'en haut à droite'"
        )

    def test_en_no_longer_says_top_right(self):
        block = _extract_blocked_trigger_block()
        # EN está en el "else:" final del if/elif chain. Buscamos a partir
        # del último "else:" en el bloque y leemos hasta el final.
        else_idx = block.rfind("else:")
        assert else_idx != -1, "else (EN fallback) no encontrado"
        en_text = block[else_idx:]
        assert "top-right" not in en_text, (
            "EN no debe decir 'top-right' (el ⚡ Actions está en la "
            "barra superior junto a Memories y News, no en la esquina derecha)"
        )


# ════════════════════════════════════════════════════════════════════════
#  Fix 2 — Todos los 7 idiomas tienen blocked_trigger ahora
# ════════════════════════════════════════════════════════════════════════


class TestAllSevenLanguagesHaveBlockedTrigger:
    """v0.19.40 — antes solo es/fr/en tenían variants, los 4 restantes
    (ja/de/ru/ko) caían al fallback EN. Ahora los 7 idiomas tienen su
    propia versión natural."""

    def test_es_branch_present(self):
        block = _extract_blocked_trigger_block()
        assert '_lang.startswith("es")' in block

    def test_fr_branch_present(self):
        block = _extract_blocked_trigger_block()
        assert '_lang.startswith("fr")' in block

    def test_ja_branch_present(self):
        """v0.19.40 — japonés añadido."""
        block = _extract_blocked_trigger_block()
        assert '_lang.startswith("ja")' in block, (
            "Falta variant japonés del blocked_trigger"
        )

    def test_de_branch_present(self):
        block = _extract_blocked_trigger_block()
        assert '_lang.startswith("de")' in block

    def test_ru_branch_present(self):
        block = _extract_blocked_trigger_block()
        assert '_lang.startswith("ru")' in block

    def test_ko_branch_present(self):
        block = _extract_blocked_trigger_block()
        assert '_lang.startswith("ko")' in block

    def test_each_lang_branch_mentions_actions(self):
        """Cada variant debe mencionar '⚡' o 'Actions' o equivalente."""
        block = _extract_blocked_trigger_block()
        # Split by langs
        for lang_marker in ['"es"', '"fr"', '"ja"', '"de"', '"ru"', '"ko"']:
            lang_idx = block.find(f"_lang.startswith({lang_marker})")
            assert lang_idx != -1
            # Read next ~600 chars (la rama completa)
            branch = block[lang_idx:lang_idx + 700]
            assert "⚡" in branch or "Actions" in branch, (
                f"Lang {lang_marker} debe mencionar ⚡ Actions toggle"
            )


# ════════════════════════════════════════════════════════════════════════
#  Fix 3 — Posición descrita por VECINDAD a otros botones (más estable)
# ════════════════════════════════════════════════════════════════════════


class TestPositionDescribedByNeighborhood:
    """v0.19.40 — describir la posición del ⚡ Actions por su vecindad
    a Memories/News es más robusto que decir "esquina X" (cambiará si
    reorganizamos la UI). Verificamos que TODOS los 7 idiomas mencionan
    Memories o News como referencia espacial."""

    def test_es_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        es_idx = block.find('_lang.startswith("es")')
        branch = block[es_idx:es_idx + 700]
        assert "Memories" in branch or "Recuerdos" in branch or "News" in branch, (
            "ES debe mencionar Memories/Recuerdos/News como ancla espacial"
        )

    def test_fr_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        fr_idx = block.find('_lang.startswith("fr")')
        branch = block[fr_idx:fr_idx + 700]
        assert "Memories" in branch or "News" in branch, (
            "FR debe mencionar Memories o News"
        )

    def test_en_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        else_idx = block.find("else:")
        en_branch = block[else_idx:else_idx + 800]
        assert "Memories" in en_branch and "News" in en_branch

    def test_ja_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        ja_idx = block.find('_lang.startswith("ja")')
        branch = block[ja_idx:ja_idx + 700]
        assert "Memories" in branch or "News" in branch, (
            "JA debe mencionar Memories o News"
        )

    def test_de_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        de_idx = block.find('_lang.startswith("de")')
        branch = block[de_idx:de_idx + 700]
        assert "Memories" in branch or "News" in branch

    def test_ru_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        ru_idx = block.find('_lang.startswith("ru")')
        branch = block[ru_idx:ru_idx + 700]
        assert "Memories" in branch or "News" in branch

    def test_ko_mentions_memories_or_news(self):
        block = _extract_blocked_trigger_block()
        ko_idx = block.find('_lang.startswith("ko")')
        branch = block[ko_idx:ko_idx + 700]
        assert "Memories" in branch or "News" in branch


# ════════════════════════════════════════════════════════════════════════
#  Sanity — el manual de usuario ya tiene info correcta
# ════════════════════════════════════════════════════════════════════════


class TestManualContentSanity:
    """No regresión: el manual ya describe correctamente la barra superior."""

    def test_manual_es_raw_source_describes_top_bar(self):
        """Smoke test: el .py del manual contiene la sección de barra
        superior en ES con ⚡ Acciones listado."""
        manual_path = REPO_ROOT / "reflex_companion" / "manual_content.py"
        src = manual_path.read_text(encoding="utf-8")
        assert "Barra superior" in src or "barra superior" in src, (
            "Manual debe documentar la barra superior"
        )
        assert "⚡ **Acciones**" in src, (
            "Manual debe listar ⚡ Acciones como botón de la barra superior"
        )
