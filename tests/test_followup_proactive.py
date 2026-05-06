"""Guards para el sistema de followup proactivo cada ~15 min (v0.18.1).

Concepto: si el user lleva 15-360 min sin escribir, Ashley puede mandar un
follow-up CORTO siguiendo el hilo. Hasta 2 followups consecutivos sin
respuesta — luego para hasta que el user vuelva a escribir.

Tests cubren:
  1. Constantes correctas (15 min, 2 max unanswered, 6h handoff)
  2. Existencia de _maybe_fire_followup_message en State
  3. State vars _consecutive_unanswered_followups y _last_followup_at
  4. Reset del counter en send_message
  5. Hook en discovery_bg_task (es llamado cada tick)

NOTA: no podemos instanciar el State de Reflex en un test unitario sin
tirar de toda la app. Los tests verifican el código FUENTE — son guards
contra regresión, no smoke tests del runtime.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RC = ROOT / "reflex_companion" / "reflex_companion.py"


def _read_rc() -> str:
    return RC.read_text(encoding="utf-8")


# ─────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────


def test_followup_gap_minutes_is_15():
    """La cadencia debe ser 15 min según la solicitud del user."""
    src = _read_rc()
    assert "_FOLLOWUP_GAP_MINUTES = 15" in src, (
        "Cadencia de followup debe ser 15 minutos."
    )


def test_followup_max_unanswered_is_2():
    """Tras 2 followups sin respuesta, parar — según solicitud del user."""
    src = _read_rc()
    assert "_FOLLOWUP_MAX_UNANSWERED = 2" in src, (
        "Max unanswered followups debe ser 2 (user lo pidió explícito)."
    )


def test_followup_absence_handoff_at_6h():
    """Tras 6h, el absence message system toma over (no duplicar)."""
    src = _read_rc()
    assert "_FOLLOWUP_ABSENCE_HANDOFF_MINUTES = 360" in src, (
        "Hand-off al absence message debe ser a las 360 min (6h)."
    )


# ─────────────────────────────────────────────
#  State vars
# ─────────────────────────────────────────────


def test_consecutive_unanswered_followups_var_exists():
    src = _read_rc()
    assert "_consecutive_unanswered_followups: int = 0" in src, (
        "Falta state var _consecutive_unanswered_followups."
    )


def test_last_followup_at_var_exists():
    src = _read_rc()
    assert "_last_followup_at: str = " in src, (
        "Falta state var _last_followup_at."
    )


# ─────────────────────────────────────────────
#  Reset en send_message
# ─────────────────────────────────────────────


def test_send_message_resets_followup_counter():
    """Cuando el user escribe, el counter de followups debe resetearse —
    así el siguiente periodo de ausencia puede disparar nuevos followups."""
    import re
    src = _read_rc()
    # Buscamos la asignación a 0 del counter en proximidad razonable de
    # _absence_message_sent = False (mismo bloque de resets en send_message).
    pattern = re.compile(
        r"self\._absence_message_sent = False[\s\S]{0,500}"
        r"self\._consecutive_unanswered_followups = 0",
    )
    assert pattern.search(src), (
        "send_message no resetea _consecutive_unanswered_followups. "
        "Sin esto, una vez Ashley llega al límite de 2 followups, NUNCA "
        "más volverá a fire (counter quedaría siempre en 2)."
    )


# ─────────────────────────────────────────────
#  Existencia del método
# ─────────────────────────────────────────────


def test_maybe_fire_followup_method_exists():
    src = _read_rc()
    assert "async def _maybe_fire_followup_message" in src, (
        "Falta método _maybe_fire_followup_message."
    )


def test_followup_uses_unanswered_gate():
    """El método debe chequear _consecutive_unanswered_followups antes de fire."""
    import re
    src = _read_rc()
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"self\._consecutive_unanswered_followups\s*>=\s*self\._FOLLOWUP_MAX_UNANSWERED",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no chequea el gate de max unanswered."
    )


def test_followup_uses_cooldown_gate():
    """El método debe chequear cooldown desde último followup."""
    import re
    src = _read_rc()
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"self\._last_followup_at",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no usa _last_followup_at para cooldown."
    )


def test_followup_uses_15min_gate_against_user_msg():
    """El método debe verificar que han pasado >=15 min desde último msg user."""
    import re
    src = _read_rc()
    # Busca la sección del método con el gate FOLLOWUP_GAP_MINUTES contra minutes_since_user
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"minutes_since_user\s*<\s*self\._FOLLOWUP_GAP_MINUTES",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no chequea el gate de 15 min "
        "desde último mensaje del user."
    )


def test_followup_handsoff_at_6h():
    """Tras 6h, no fire (deja el trabajo al absence message system)."""
    import re
    src = _read_rc()
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"minutes_since_user\s*>=\s*self\._FOLLOWUP_ABSENCE_HANDOFF_MINUTES",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no chequea handoff a las 6h. "
        "Sin esto, en absence largo podríamos duplicar mensajes con absence msg."
    )


def test_followup_skips_if_closing_conversation():
    """Si user se despidió, no molestar."""
    import re
    src = _read_rc()
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"is_closing_conversation",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no usa is_closing_conversation."
    )


def test_followup_skips_if_no_user_message():
    """Si no hay mensaje user previo, no fire (eso es startup engagement)."""
    import re
    src = _read_rc()
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"if not last_user_ts",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no skip cuando no hay user message previo."
    )


def test_followup_skips_if_busy():
    """Si Ashley está pensando o streameando, no fire."""
    import re
    src = _read_rc()
    pattern = re.compile(
        r"async def _maybe_fire_followup_message[\s\S]+?"
        r"self\.is_thinking",
    )
    assert pattern.search(src), (
        "_maybe_fire_followup_message no chequea is_thinking."
    )


def test_followup_increments_counter_on_fire():
    """Cuando fire (con o sin texto), counter debe incrementar."""
    import re
    src = _read_rc()
    method_match = re.search(
        r"async def _maybe_fire_followup_message[\s\S]+?(?=\n    (?:async )?def )",
        src,
    )
    assert method_match, "No encontré el método completo"
    method_body = method_match.group(0)
    # Debe tener al menos una asignación += 1 al counter
    assert "self._consecutive_unanswered_followups += 1" in method_body, (
        "Counter no se incrementa al fire un followup. Sin esto, Ashley "
        "spamearía followups indefinidamente."
    )


def test_followup_marks_silent_responses_too():
    """Si Ashley elige silencio (responde solo [mood:default] sin texto),
    aún debe contar para el counter para no spammear."""
    import re
    src = _read_rc()
    method_match = re.search(
        r"async def _maybe_fire_followup_message[\s\S]+?(?=\n    (?:async )?def )",
        src,
    )
    body = method_match.group(0)
    # Buscar el path donde clean está corto (silencio) y aún incrementa counter
    pattern = re.compile(
        r"if len\(clean\)\s*<\s*5:[\s\S]{0,300}"
        r"self\._consecutive_unanswered_followups\s*\+=\s*1",
    )
    assert pattern.search(body), (
        "Cuando Ashley elige silencio, el counter sigue debiéndose incrementar "
        "para no fire infinitamente."
    )


# ─────────────────────────────────────────────
#  Hook en discovery_bg_task
# ─────────────────────────────────────────────


def test_followup_called_from_discovery_bg_task():
    """_maybe_fire_followup_message debe ser llamado desde discovery_bg_task
    (que tickea cada 10 min)."""
    import re
    src = _read_rc()
    bg_match = re.search(
        r"async def discovery_bg_task[\s\S]+?(?=\n    (?:async )?def )",
        src,
    )
    assert bg_match, "No encontré discovery_bg_task"
    body = bg_match.group(0)
    assert "_maybe_fire_followup_message" in body, (
        "discovery_bg_task no llama _maybe_fire_followup_message. "
        "Sin esto el followup nunca se dispara."
    )


# ─────────────────────────────────────────────
#  Independencia del absence system
# ─────────────────────────────────────────────


def test_followup_uses_separate_counter_from_absence():
    """El followup debe usar _consecutive_unanswered_followups,
    NO _consecutive_unanswered_proactive (que es del absence system)."""
    import re
    src = _read_rc()
    method_match = re.search(
        r"async def _maybe_fire_followup_message[\s\S]+?(?=\n    (?:async )?def )",
        src,
    )
    body = method_match.group(0)
    # No debe usar el counter del absence system
    assert "_consecutive_unanswered_proactive" not in body, (
        "_maybe_fire_followup_message NO debe modificar el counter del absence "
        "system. Cada uno tiene su propio counter para no interferir."
    )


def test_followup_has_separate_message_id():
    """Followup debe usar prefix 'followup-' en el ID, distinto del 'absence-'."""
    import re
    src = _read_rc()
    method_match = re.search(
        r"async def _maybe_fire_followup_message[\s\S]+?(?=\n    (?:async )?def )",
        src,
    )
    body = method_match.group(0)
    assert '"id": f"followup-' in body, (
        "Mensaje de followup debe usar prefix 'followup-' en su ID para "
        "distinguirse del absence message."
    )


# ─────────────────────────────────────────────
#  Idiomas (3 hints traducidos)
# ─────────────────────────────────────────────


def test_followup_has_three_language_hints():
    """El hint debe estar traducido en es/en/fr — paridad multi-idioma."""
    import re
    src = _read_rc()
    method_match = re.search(
        r"async def _maybe_fire_followup_message[\s\S]+?(?=\n    (?:async )?def )",
        src,
    )
    body = method_match.group(0)
    # Buscar marcadores de los 3 idiomas
    assert 'if _lang == "es"' in body or '_lang == "es"' in body, "Falta hint ES"
    assert '_lang == "fr"' in body, "Falta hint FR"
    # EN es el else final
    assert "else:" in body, "Falta hint EN (else)"
