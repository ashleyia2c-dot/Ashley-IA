"""Guards para focus_window self-targeted no-op (v0.17.5).

Bug observado: Ashley a veces emite [action:focus_window:Ashley] como cierre
de respuesta, intentando hacer focus de su propia ventana. Es no-op (ya es
la ventana activa) pero generaba burbuja "Ventana 'Ashley' activada" en
el chat — ruido innecesario, sin acción real.

Fix: en el handler de focus_window en actions.py, detectar si el target es
"ashley" (case-insensitive) → devolver noop=True. _execute_and_record_action
salta el append al chat cuando noop=True (mismo pattern que done_important
sobre item ya hecho).

Estos tests bloquean regresión.
"""

from reflex_companion.actions import execute_action


# ─────────────────────────────────────────────────────────────────────────────
# Casos noop (Ashley intenta focusar su propia ventana)
# ─────────────────────────────────────────────────────────────────────────────


def test_focus_window_ashley_returns_noop():
    """focus_window:Ashley → noop=True, result vacío."""
    result = execute_action("focus_window", ["Ashley"])
    assert result["success"] is True
    assert result.get("noop") is True, (
        f"focus_window con target 'Ashley' debe ser no-op. Got: {result!r}"
    )
    assert result["result"] == "", (
        f"Result debe ser '' para no generar burbuja. Got: {result!r}"
    )


def test_focus_window_ashley_lowercase_noop():
    """Variante minúscula también debe ser noop."""
    result = execute_action("focus_window", ["ashley"])
    assert result.get("noop") is True


def test_focus_window_ashley_with_spaces_noop():
    """Con whitespace alrededor también debe detectarse."""
    result = execute_action("focus_window", ["  Ashley  "])
    assert result.get("noop") is True


def test_focus_window_ashley_uppercase_noop():
    """Variante en mayúsculas."""
    result = execute_action("focus_window", ["ASHLEY"])
    assert result.get("noop") is True


# ─────────────────────────────────────────────────────────────────────────────
# Casos NO noop (focusar otras ventanas legítimamente)
# ─────────────────────────────────────────────────────────────────────────────


def test_focus_window_other_app_not_noop():
    """focus_window sobre otra app NO debe ser noop — ejecuta normal.

    No verificamos el resultado del focus en sí (depende del SO y de qué
    ventanas hay abiertas), solo que el handler NO marque noop.
    """
    result = execute_action("focus_window", ["Notepad"])
    assert result.get("noop") is not True, (
        "focus_window sobre 'Notepad' (no Ashley) NO debe ser noop. "
        f"Got: {result!r}"
    )


def test_focus_window_chrome_not_noop():
    result = execute_action("focus_window", ["Chrome"])
    assert result.get("noop") is not True


def test_focus_window_substring_containing_ashley_not_noop():
    """Edge case: si el title contiene 'ashley' como SUBCADENA pero no
    es exactamente 'ashley', NO debe ser noop. Ejemplo: 'Ashleyland Studios'
    es una ventana diferente."""
    result = execute_action("focus_window", ["Ashleyland Studios"])
    assert result.get("noop") is not True, (
        "focus_window con target que CONTIENE 'ashley' como subcadena pero "
        "no es exactamente 'ashley' debe ejecutar normal."
    )


def test_focus_window_empty_param_not_noop():
    """Param vacío no es noop por la regla 'ashley' — focus_window con ''
    es bug aparte (otro caso no-op posible) pero no este check."""
    result = execute_action("focus_window", [""])
    # No verificamos noop aquí — solo que NO se marque por la regla "ashley"
    # (que solo aplica si el param ES exactamente "ashley")
    if result.get("noop"):
        # Si está marcado noop, debe ser por otro check (ej: empty param)
        # No por la regla específica de Ashley
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Verificación de código fuente (regression guard)
# ─────────────────────────────────────────────────────────────────────────────


def test_actions_py_has_self_noop_check():
    """El handler de focus_window en actions.py debe tener el check de 'ashley'."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent /
           "reflex_companion" / "actions.py").read_text(encoding="utf-8")
    # Buscamos el handler de focus_window
    import re
    handler_match = re.search(
        r'elif action_type == "focus_window":[\s\S]+?(?=elif action_type|$)',
        src,
    )
    assert handler_match, "No encontré el handler de focus_window en actions.py"
    handler = handler_match.group(0)
    # Debe tener check sobre "ashley"
    assert '"ashley"' in handler.lower() or "'ashley'" in handler.lower(), (
        "El handler de focus_window debe detectar target='ashley' como noop. "
        "Sin esto Ashley genera burbujas 'Ventana Ashley activada' "
        "innecesarias al re-emitir el tag sobre su propia ventana."
    )
    # Debe propagar noop=True
    assert '"noop"' in handler or "'noop'" in handler, (
        "El handler debe propagar el flag 'noop' cuando detecta self-target."
    )
