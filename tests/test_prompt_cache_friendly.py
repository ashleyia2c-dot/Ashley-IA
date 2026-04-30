"""Tests para asegurar que el system prompt está optimizado para prompt
caching (xAI / OpenRouter) — v0.16.13.

Antes el prompt empezaba con secciones dinámicas (hora, mood, system_state)
que cambiaban cada mensaje → cache hit ratio del 12% medido en xAI dashboard.

Ahora la estructura es:
  TOP: secciones estables (~9.5K tokens — se cachea)
  BOTTOM: secciones dinámicas (~1.5K tokens — no cachea)

Estos tests bloquean regresión: si alguien refactoriza y vuelve a poner
la hora o el mood al inicio del prompt, el test falla con un mensaje
explicando por qué eso destruye el coste.
"""

import pytest

import os
os.environ.setdefault("XAI_API_KEY", "dummy-for-test")


# ══════════════════════════════════════════════════════════════════════
#  Cache prefix grande en los 3 idiomas
# ══════════════════════════════════════════════════════════════════════


class TestCachePrefixIsHuge:
    """Dos llamadas consecutivas al system prompt con SOLO la hora distinta
    deben compartir un prefix gigante (>95%). Si alguien rompe esta
    propiedad, el cache se cae al 12% y el coste de input se multiplica
    por 5-10×.
    """

    def _run(self, build_fn):
        """Helper: build dos prompts solo distintos en hora; mide common prefix."""
        facts = [
            {"hecho": "Vive en Barcelona", "categoria": "x",
             "relevancia": "permanente", "importancia": "8"},
        ]
        diary = [
            {"fecha": "2026-04-29", "resumen": "Hablamos sobre el bug"},
        ]
        mental = "[Estado mental] mood: contenta. Lleva pensando en: el proyecto."

        p1 = build_fn(
            facts=facts, diary=diary,
            time_context="14:23 del 29 abril",
            mental_state_block=mental,
        )
        p2 = build_fn(
            facts=facts, diary=diary,
            time_context="14:24 del 29 abril",
            mental_state_block=mental,
        )

        # Char-level common prefix (suficiente — los tokens son una función
        # determinista del texto).
        common = 0
        for i, (a, b) in enumerate(zip(p1, p2)):
            if a != b:
                common = i
                break
        else:
            common = min(len(p1), len(p2))

        return len(p1), common

    def test_es_prompt_cache_prefix_at_least_95_percent(self):
        from reflex_companion.prompts_es import build_system_prompt
        total, common = self._run(build_system_prompt)
        ratio = common / total
        assert ratio >= 0.95, (
            f"ES prompt cache prefix solo {ratio*100:.1f}% (esperado >=95%). "
            f"Total {total:,} chars, common prefix {common:,}. "
            f"Eso significa que la hora/mood/dynamic content esta en los "
            f"primeros tokens y rompe el cache. Mover dynamic_bottom al "
            f"final del prompt."
        )

    def test_en_prompt_cache_prefix_at_least_95_percent(self):
        from reflex_companion.prompts_en import build_system_prompt
        total, common = self._run(build_system_prompt)
        ratio = common / total
        assert ratio >= 0.95, (
            f"EN prompt cache prefix solo {ratio*100:.1f}% (esperado >=95%)."
        )

    def test_fr_prompt_cache_prefix_at_least_95_percent(self):
        from reflex_companion.prompts_fr import build_system_prompt
        total, common = self._run(build_system_prompt)
        ratio = common / total
        assert ratio >= 0.95, (
            f"FR prompt cache prefix solo {ratio*100:.1f}% (esperado >=95%)."
        )


# ══════════════════════════════════════════════════════════════════════
#  Hora aparece DESPUÉS de la personalidad (no antes)
# ══════════════════════════════════════════════════════════════════════


class TestTimeIsAfterPersonality:
    """La sección de TIEMPO debe aparecer DESPUÉS de la sección de
    personalidad. Si está antes, cualquier cambio de hora rompe el cache."""

    def test_es_time_after_principles(self):
        from reflex_companion.prompts_es import build_system_prompt
        prompt = build_system_prompt(
            facts=[], diary=[], time_context="14:23",
        )
        principles_idx = prompt.find("PRINCIPIOS DE CONEXIÓN")
        time_idx = prompt.find("=== TIEMPO ===")
        assert principles_idx > 0, "No se encontró sección PRINCIPIOS"
        assert time_idx > 0, "No se encontró sección TIEMPO"
        assert time_idx > principles_idx, (
            f"En ES, la sección TIEMPO está ANTES de los PRINCIPIOS "
            f"(time={time_idx}, principles={principles_idx}). Eso rompe "
            f"el cache prefix. TIEMPO debe ir al final del prompt."
        )

    def test_en_time_after_principles(self):
        from reflex_companion.prompts_en import build_system_prompt
        prompt = build_system_prompt(
            facts=[], diary=[], time_context="14:23",
        )
        principles_idx = prompt.find("CONNECTION PRINCIPLES")
        time_idx = prompt.find("=== TIME ===")
        assert principles_idx > 0
        assert time_idx > 0
        assert time_idx > principles_idx, (
            f"EN: TIME section antes de CONNECTION PRINCIPLES rompe cache."
        )

    def test_fr_time_after_principles(self):
        from reflex_companion.prompts_fr import build_system_prompt
        prompt = build_system_prompt(
            facts=[], diary=[], time_context="14:23",
        )
        principles_idx = prompt.find("PRINCIPES DE CONNEXION")
        time_idx = prompt.find("=== TEMPS ===")
        assert principles_idx > 0
        assert time_idx > 0
        assert time_idx > principles_idx, (
            f"FR: section TEMPS avant PRINCIPES casse le cache."
        )


# ══════════════════════════════════════════════════════════════════════
#  Mental state aparece DESPUÉS de la personalidad
# ══════════════════════════════════════════════════════════════════════


class TestMentalStateIsAfterPersonality:
    """El bloque de estado mental también va al final — cambia cada turno
    con mood updates."""

    def test_es_mental_after_principles(self):
        from reflex_companion.prompts_es import build_system_prompt
        prompt = build_system_prompt(
            facts=[], diary=[],
            mental_state_block="[Estado mental] mood: contenta",
        )
        principles_idx = prompt.find("PRINCIPIOS DE CONEXIÓN")
        mental_idx = prompt.find("[Estado mental]")
        assert principles_idx > 0
        assert mental_idx > 0
        assert mental_idx > principles_idx, (
            "ES: bloque [Estado mental] está antes de PRINCIPIOS — eso "
            "rompe el cache cada turno (mood cambia con cada interacción)."
        )


# ══════════════════════════════════════════════════════════════════════
#  La hora SIGUE siendo accesible para Ashley (no se perdió contenido)
# ══════════════════════════════════════════════════════════════════════


class TestDynamicContentStillPresent:
    """Después del reorder, el contenido dinámico tiene que seguir
    apareciendo en el prompt — solo cambió de posición."""

    def test_time_content_present(self):
        from reflex_companion.prompts_es import build_system_prompt
        prompt = build_system_prompt(
            facts=[], diary=[],
            time_context="Son las 14:23 del 29 de abril",
        )
        assert "14:23" in prompt, (
            "El contenido de time_context se perdió tras el reorder."
        )

    def test_mental_content_present(self):
        from reflex_companion.prompts_es import build_system_prompt
        unique_marker = "preocupacion-test-marker-xyz-123"
        prompt = build_system_prompt(
            facts=[], diary=[],
            mental_state_block=f"[Estado] {unique_marker}",
        )
        assert unique_marker in prompt, (
            "El contenido del mental_state_block se perdió tras el reorder."
        )

    def test_facts_content_present(self):
        from reflex_companion.prompts_es import build_system_prompt
        prompt = build_system_prompt(
            facts=[{"hecho": "MARKER_FACT_QWERTY", "categoria": "x",
                    "relevancia": "permanente", "importancia": "5"}],
            diary=[],
        )
        assert "MARKER_FACT_QWERTY" in prompt
