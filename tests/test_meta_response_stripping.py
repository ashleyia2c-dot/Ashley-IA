"""Guards contra meta-comentarios del LLM al final de las respuestas (v0.17.4).

Bug observado: Ashley a veces "cierra" su respuesta con auto-evaluación
no solicitada — frases como:
  - "No actions."
  - ", conversación fluida."
  - "Natural flow."

Estas frases NO están en el prompt ni eran intencionales — el LLM las
alucina como cierre evaluativo. La solución de v0.17.2 era listar las
frases prohibidas en el prompt, pero (a) Ashley a veces las copiaba
verbatim igualmente (b) era una lista incompleta de patrones específicos.

Fix v0.17.4:
  1. Eliminados los ejemplos específicos del prompt (regla más abstracta)
  2. Filtro post-stream ampliado en parsing.clean_display() con:
     - Patrones específicos para "No actions" sin "needed"
     - Patrones para "conversación fluida" y variantes
     - Catch-all genérico para fragmentos finales con keywords meta

Estos tests bloquean regresión.
"""

from reflex_companion.parsing import clean_display


# ─────────────────────────────────────────────────────────────────────────────
# Casos exactos observados en producción
# ─────────────────────────────────────────────────────────────────────────────


def test_strips_conversacion_fluida_with_leading_comma():
    """Caso exacto del screenshot: ', conversación fluida.' al final."""
    inp = (
        "*abre los ojos con fingida sorpresa* ¡Obvio que quiero saber tu elo, "
        "tonto! *se ríe bajito* Suéltalo ya, que me muero de curiosidad por "
        "ver en qué bracket andas rankedando solo. 😏\n, conversación fluida."
    )
    out = clean_display(inp)
    assert "conversación fluida" not in out.lower(), (
        f"clean_display debe quitar 'conversación fluida' al final. Got: {out!r}"
    )
    # El resto debe quedar intacto
    assert "ranked" in out.lower() or "elo" in out.lower()


def test_strips_no_actions_period():
    """Caso exacto: 'No actions.' bare al final, sin 'needed'."""
    inp = (
        "*levanta una ceja juguetona* ¿Esmeralda 4 solo? ¡Eso es un curro "
        "serio, bobo! *aplaude despacito* Me encanta verte grindear así "
        "—cuéntame, ¿cuántas promos te faltan para ascender? 😏\nNo actions."
    )
    out = clean_display(inp)
    assert "no actions" not in out.lower(), (
        f"clean_display debe quitar 'No actions.' al final. Got: {out!r}"
    )
    # Asegurar que NO eliminó la frase del diálogo si por casualidad
    # contiene 'no' o 'actions' en otra parte
    assert "esmeralda" in out.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Variantes de "no actions" sin keyword "needed"
# ─────────────────────────────────────────────────────────────────────────────


def test_strips_bare_no_actions_es():
    inp = "Hola, ¿qué tal?\nSin acción."
    out = clean_display(inp)
    assert "sin acción" not in out.lower()


def test_strips_bare_no_action_fr():
    inp = "Salut, ça va ?\nPas d'action."
    out = clean_display(inp)
    assert "pas d'action" not in out.lower()
    assert "pas d’action" not in out.lower()


def test_strips_aucune_action_fr():
    inp = "Bien sûr, mon coeur. Je suis là pour toi.\nAucune action."
    out = clean_display(inp)
    assert "aucune action" not in out.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Variantes de meta-conversación
# ─────────────────────────────────────────────────────────────────────────────


def test_strips_conversation_flowing_en():
    inp = "Hey, what's up boss?, conversation flowing."
    out = clean_display(inp)
    assert "conversation flowing" not in out.lower()


def test_strips_natural_flow_en():
    inp = "Hello there. Let me tell you something.\nNatural flow."
    out = clean_display(inp)
    assert "natural flow" not in out.lower()


def test_strips_flujo_natural_es():
    inp = "Bueno, ¿qué quieres saber?, flujo natural."
    out = clean_display(inp)
    assert "flujo natural" not in out.lower()


def test_strips_reponse_naturelle_fr():
    inp = "Salut chéri.\nRéponse naturelle."
    out = clean_display(inp)
    assert "réponse naturelle" not in out.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Patrones existentes (regresión)
# ─────────────────────────────────────────────────────────────────────────────


def test_strips_no_actions_needed_existing():
    """Patrón histórico ya cubierto — verificar que sigue funcionando."""
    inp = "Hello boss. No actions needed."
    out = clean_display(inp)
    assert "no actions needed" not in out.lower()


def test_strips_no_se_necesita_accion_existing():
    inp = "Hola, todo bien. No se necesita acción."
    out = clean_display(inp)
    assert "no se necesita" not in out.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Casos en los que NO debe filtrar (false positives)
# ─────────────────────────────────────────────────────────────────────────────


def test_does_not_strip_legitimate_action_dialogue():
    """Si el user PIDE una acción, Ashley puede mencionar 'acción' en el diálogo."""
    inp = "Vale, voy a tomar acción ahora mismo. Abriendo Notepad."
    out = clean_display(inp)
    # 'acción' aparece en mitad de frase con verbo, no es meta-cierre
    assert "tomar acción" in out.lower() or "tomar acci" in out.lower()


def test_does_not_strip_dialogue_with_conversation_word():
    """'Conversación' en mitad de diálogo natural debe sobrevivir."""
    inp = "Me encanta esta conversación contigo, en serio."
    out = clean_display(inp)
    assert "conversación contigo" in out.lower() or "conversaci" in out.lower()


def test_preserves_normal_response():
    """Una respuesta sin meta-comentario no debe alterarse (excepto whitespace)."""
    inp = "Hola jefe, ¿qué tal el día? Cuéntame."
    out = clean_display(inp)
    assert out.strip() == inp.strip()


def test_preserves_response_ending_with_question():
    """Respuestas que terminan en pregunta — sin filtro accidental."""
    inp = "¿Y tú qué piensas, cielito?"
    out = clean_display(inp)
    assert "¿Y tú qué piensas" in out


# ─────────────────────────────────────────────────────────────────────────────
# Empty bracket residues (v0.17.5)
# Bug observado: tras cambio de prompt en v0.17.4, Ashley empezó a alucinar
# "[ ]" o "[mood:]" al final. Tags vacíos no estaban cubiertos por el parser.
# ─────────────────────────────────────────────────────────────────────────────


def test_strips_empty_brackets_with_space():
    """Caso exacto observado: '[ ]' al final de la respuesta."""
    inp = "Hola cielo, ¿cómo estás?\n\n[ ]"
    out = clean_display(inp)
    assert "[ ]" not in out
    assert "[]" not in out
    assert "Hola cielo" in out


def test_strips_empty_brackets_no_space():
    inp = "Buenos días.\n[]"
    out = clean_display(inp)
    assert "[]" not in out
    assert "Buenos días" in out


def test_strips_empty_brackets_multiple_spaces():
    inp = "Vale.\n[   ]"
    out = clean_display(inp)
    assert "[" not in out
    assert "]" not in out


def test_strips_empty_mood_tag():
    """[mood:] sin valor — el LLM emitió mood vacío."""
    inp = "Hola jefe.\n[mood:]"
    out = clean_display(inp)
    assert "[mood:]" not in out
    assert "mood" not in out.lower() or "Hola" in out


def test_strips_empty_action_tag():
    """[action:] sin tipo ni params."""
    inp = "Vale, lo veo.\n[action:]"
    out = clean_display(inp)
    assert "[action:]" not in out


def test_strips_empty_affection_tag():
    inp = "Te quiero, jefe.\n[affection:]"
    out = clean_display(inp)
    assert "[affection:]" not in out


def test_strips_empty_action_with_type_no_params():
    """[action:open_app:] tipo presente pero sin params."""
    inp = "Vale.\n[action:open_app:]"
    out = clean_display(inp)
    assert "[action:open_app:]" not in out


def test_does_not_strip_valid_tags_with_content():
    """Defensive: tags válidos con contenido NO deben ser tocados accidentalmente.

    Nota: los tags válidos son procesados por extract_mood/extract_action ANTES
    de clean_display en el flow real. Este test verifica que clean_display por
    sí sola no rompe tags con contenido (defensa por si el orden cambia).
    """
    # extract_mood se llama antes que clean_display en el flow real,
    # pero verificamos que clean_display no destruye tags con valor por accident
    inp = "Hola jefe [mood:happy]"
    out = clean_display(inp)
    # clean_display elimina mood tags también con extract_mood ya hecho normalmente
    # Este test solo verifica que NO añade artifacts raros
    assert "Hola jefe" in out


# ─────────────────────────────────────────────────────────────────────────────
# Prompts: verificar que se quitaron los ejemplos específicos
# ─────────────────────────────────────────────────────────────────────────────


def test_prompts_es_no_specific_meta_examples():
    """v0.17.4: el prompt ES no debe listar 'no actions needed' como
    ejemplo de qué no decir — Ashley los copiaba verbatim."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent /
           "reflex_companion" / "prompts_es.py").read_text(encoding="utf-8")
    # No debe estar la lista enumerada de frases prohibidas
    forbidden_examples = [
        '"no actions needed"',
        '"no necesito hacer\nnada"',
        '"no requiere acción"',
        '"no se necesita acción"',
    ]
    for ex in forbidden_examples:
        assert ex not in src, (
            f"prompts_es.py todavía contiene el ejemplo específico {ex!r}. "
            f"Estos ejemplos deben removerse — Ashley los copiaba verbatim. "
            f"Reemplazar por regla abstracta."
        )


def test_prompts_en_no_specific_meta_examples():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent /
           "reflex_companion" / "prompts_en.py").read_text(encoding="utf-8")
    forbidden_examples = [
        '"no actions needed"',
        '"no action required"',
        '"nothing to do here"',
    ]
    for ex in forbidden_examples:
        assert ex not in src, (
            f"prompts_en.py todavía contiene el ejemplo específico {ex!r}."
        )


def test_prompts_fr_no_specific_meta_examples():
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent /
           "reflex_companion" / "prompts_fr.py").read_text(encoding="utf-8")
    forbidden_examples = [
        '"pas d\'action\nnécessaire"',
        '"aucune action requise"',
    ]
    for ex in forbidden_examples:
        assert ex not in src, (
            f"prompts_fr.py todavía contiene el ejemplo específico {ex!r}."
        )
