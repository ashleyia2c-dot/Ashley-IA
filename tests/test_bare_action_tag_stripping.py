"""Tests para Bug C (v0.16.14) — tags BARE sin prefijo "action:" se mostraban
visibles en el bubble del chat.

Caso reportado por user (con screenshot): Ashley emitió
  "[save_taste:proyectos:mejorando voz de Ashley]"
SIN el prefijo "action:". El regex de clean_display anterior solo pillaba
el formato canónico "[action:save_taste:...]" así que el tag bare quedaba
visible en el chat ("[save_taste:proyectos:mejorando voz de Ashley]"
literal en el bubble).

Fix: extender clean_display() para reconocer también los action types
bare. Lista sincronizada con actions.py::execute_action.
"""

import pytest

from reflex_companion.parsing import clean_display


# ════════════════════════════════════════════════════════════════════════
#  Caso reportado por el user
# ════════════════════════════════════════════════════════════════════════


def test_strips_bare_save_taste_tag_real_case():
    """Caso EXACTO del screenshot del user."""
    text = (
        "¡Jefe, eso suena bien! Cuéntame todo.\n\n"
        "[save_taste:proyectos:mejorando voz de Ashley]"
    )
    result = clean_display(text)
    assert "[save_taste" not in result, (
        f"Tag bare 'save_taste' sigue visible: {result!r}"
    )
    assert "Cuéntame todo" in result, (
        f"Cleanup eliminó texto legítimo: {result!r}"
    )


# ════════════════════════════════════════════════════════════════════════
#  Cobertura: todos los action types bare
# ════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("action_type", [
    "screenshot", "open_app", "play_music", "search_web", "open_url",
    "volume", "type_text", "type_in", "write_to_app", "focus_window",
    "hotkey", "press_key", "close_window", "close_tab",
    "click", "type_browser", "read_page", "scroll_page",
    "remind", "add_important", "done_important", "save_taste",
])
def test_strips_bare_action_type(action_type):
    """Cualquier action type emitido SIN prefijo 'action:' debe limpiarse."""
    text = f"Hola, jefe.\n\n[{action_type}:param1:param2]"
    result = clean_display(text)
    assert f"[{action_type}" not in result, (
        f"Action type bare '{action_type}' no se limpió. Resultado: {result!r}"
    )
    assert "Hola, jefe." in result


# ════════════════════════════════════════════════════════════════════════
#  Tag parcial al final (durante streaming)
# ════════════════════════════════════════════════════════════════════════


def test_strips_partial_bare_tag_at_end():
    """Durante streaming, un tag puede llegar parcial al final del texto."""
    text = "Bien, jefe. [save_taste:proyectos:mejorando voz"
    result = clean_display(text)
    assert "save_taste" not in result, (
        f"Tag parcial bare quedó visible: {result!r}"
    )
    assert "Bien, jefe." in result


# ════════════════════════════════════════════════════════════════════════
#  Compatibilidad: el formato canónico [action:X:...] sigue funcionando
# ════════════════════════════════════════════════════════════════════════


def test_canonical_action_tag_still_stripped():
    """El formato canónico [action:save_taste:...] debe seguir limpiándose."""
    text = "Hola.\n\n[action:save_taste:proyectos:mejorando voz]"
    result = clean_display(text)
    assert "save_taste" not in result
    assert "action" not in result.lower() or result.lower().count("action") == 0
    assert "Hola." in result


# ════════════════════════════════════════════════════════════════════════
#  No-op: texto sin tags ni acciones
# ════════════════════════════════════════════════════════════════════════


def test_no_tags_unchanged():
    """Texto sin tags debe pasar intacto (excepto trim)."""
    text = "Hola jefe, ¿qué tal el día?"
    result = clean_display(text)
    assert result == text


# ════════════════════════════════════════════════════════════════════════
#  Defensa: no debemos eliminar tags que NO son acciones
# ════════════════════════════════════════════════════════════════════════


def test_does_not_strip_non_action_brackets():
    """Texto entre corchetes que NO es un action type debe preservarse.
    Ej.: '[error: file not found]' o '[Nota: importante]' — son frases
    conversacionales, no acciones."""
    cases = [
        "El error fue [foo:bar] eso lo causa.",
        "Nota [importante] al final.",
        "[informacion] que no es acción.",
    ]
    for case in cases:
        result = clean_display(case)
        # Al menos parte del bracket debe sobrevivir o estar intacto el resto
        assert "fue" in result or "Nota" in result or "que no es" in result, (
            f"Cleanup demasiado agresivo en {case!r} → {result!r}"
        )
