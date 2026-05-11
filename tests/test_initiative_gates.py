"""Tests for the initiative gating helpers (v0.13.2).

Bug que motivó esto: el user dijo "no me hables más de SQL" y luego
"nos vemos, me voy a dormir". Al pulsar el pill ✨ Ashley el bot sacó
un comentario sobre SQL — peor escenario posible.

Los helpers nuevos en topic_share.py:
  • is_closing_conversation: detecta despedidas/buenas noches.
  • extract_banned_topics: extrae temas que el user pidió evitar.

El handler send_initiative ahora los usa para gatear el comportamiento.
"""

from reflex_companion.topic_share import (
    is_closing_conversation,
    extract_banned_topics,
)


# ══════════════════════════════════════════════════════════════════════
#  is_closing_conversation
# ══════════════════════════════════════════════════════════════════════

def test_closing_empty_messages_returns_false():
    assert is_closing_conversation([]) is False


def test_closing_detects_spanish_goodbyes():
    cases = [
        "nos vemos",
        "Hasta luego!!!",
        "buenas noches jefe",
        "me voy a dormir",
        "voy a la cama, hasta mañana",
        "chao chau",
    ]
    for msg in cases:
        messages = [{"role": "user", "content": msg}]
        assert is_closing_conversation(messages) is True, f"missed: {msg!r}"


def test_closing_detects_english_goodbyes():
    cases = [
        "see you",
        "goodnight",
        "going to bed",
        "talk to you later",
        "gotta go",
        "ttyl",
    ]
    for msg in cases:
        messages = [{"role": "user", "content": msg}]
        assert is_closing_conversation(messages) is True, f"missed: {msg!r}"


def test_closing_detects_french_goodbyes():
    cases = [
        "à plus",
        "bonne nuit",
        "je vais dormir",
        "je vais me coucher",
    ]
    for msg in cases:
        messages = [{"role": "user", "content": msg}]
        assert is_closing_conversation(messages) is True, f"missed: {msg!r}"


def test_closing_ignores_normal_message():
    messages = [
        {"role": "user", "content": "qué hora es"},
        {"role": "user", "content": "como va el código de ayer"},
    ]
    assert is_closing_conversation(messages) is False


def test_closing_only_looks_at_user_messages():
    """Si Ashley dice 'buenas noches', NO cuenta."""
    messages = [
        {"role": "assistant", "content": "buenas noches jefe"},
        {"role": "user", "content": "qué tal"},
    ]
    assert is_closing_conversation(messages) is False


def test_closing_respects_lookback():
    """Sólo mira los últimos N mensajes del user."""
    messages = [
        {"role": "user", "content": "buenas noches"},  # viejo
        {"role": "user", "content": "qué tal el día"},  # reciente
    ]
    # Lookback=1 → solo ve "qué tal" → False
    assert is_closing_conversation(messages, lookback=1) is False
    # Lookback=2 → ve también "buenas noches" → True
    assert is_closing_conversation(messages, lookback=2) is True


# ══════════════════════════════════════════════════════════════════════
#  extract_banned_topics
# ══════════════════════════════════════════════════════════════════════

def test_banned_empty_returns_empty():
    assert extract_banned_topics([]) == []


def test_banned_extracts_spanish_no_me_hables():
    messages = [{"role": "user", "content": "no me hables más de SQL"}]
    topics = extract_banned_topics(messages)
    assert any("sql" in t.lower() for t in topics)


def test_banned_extracts_english_dont_talk_about():
    messages = [{"role": "user", "content": "don't talk about work please"}]
    topics = extract_banned_topics(messages)
    assert any("work" in t.lower() for t in topics)


def test_banned_extracts_dejame_en_paz():
    messages = [{"role": "user", "content": "déjame en paz con la programación"}]
    topics = extract_banned_topics(messages)
    assert len(topics) >= 1
    assert any("programaci" in t.lower() for t in topics)


def test_banned_no_match_for_normal_message():
    messages = [{"role": "user", "content": "qué tal te fue hoy"}]
    assert extract_banned_topics(messages) == []


def test_banned_only_looks_at_user_messages():
    """Si Ashley dijo 'no me hables de SQL', NO cuenta."""
    messages = [
        {"role": "assistant", "content": "no me hables más de SQL"},
        {"role": "user", "content": "qué tal"},
    ]
    assert extract_banned_topics(messages) == []


def test_banned_combines_multiple_messages():
    messages = [
        {"role": "user", "content": "no me hables de SQL"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "stop talking about Bee también"},
    ]
    topics = extract_banned_topics(messages)
    # Debe capturar ambos
    assert any("sql" in t.lower() for t in topics)
    assert any("bee" in t.lower() for t in topics)


def test_banned_handles_missing_content():
    """Defensive: mensaje sin content no debe crashear."""
    messages = [
        {"role": "user"},
        {"role": "user", "content": None},
        {"role": "user", "content": "no me hables de música"},
    ]
    topics = extract_banned_topics(messages)
    assert any("m" in t.lower() for t in topics)  # 'música' incluido


def test_banned_truncates_long_topics():
    """No queremos capturar 200 chars como 'topic'. Cap a 60 chars."""
    long_msg = "no me hables de " + ("a" * 200)
    messages = [{"role": "user", "content": long_msg}]
    topics = extract_banned_topics(messages)
    for t in topics:
        assert len(t) <= 60


# ══════════════════════════════════════════════════════════════════════
#  v0.19.21 — Gate al inicio del chat (no flash bubble)
# ══════════════════════════════════════════════════════════════════════
#
# Bug: el user reportó que al iniciar el chat con Ashley (sin haber
# enviado ningún mensaje todavía, solo está el welcome de Ashley en el
# historial), pulsar el botón ✨ creaba un mensaje que se borraba al
# segundo. Causa: el trigger del initiative pide a Ashley que "mire el
# hilo reciente" pero solo está su propio welcome → genera [mood:default]
# silencioso → el `current_response` flashea durante el stream y se
# limpia al final. El user lo ve como "crea un mensaje y se borra".
#
# Fix (en reflex_companion.py:send_initiative): gate al top del handler
# que retorna inmediatamente si NO hay ningún mensaje del user en el
# historial. Sin flash, sin llamada a la API, sin gasto de tokens.

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


def _send_initiative_body() -> str:
    """Extrae el cuerpo de send_initiative para verificar el gate."""
    src = RC_FILE.read_text(encoding="utf-8")
    # Capturamos desde "def send_initiative" hasta la siguiente def al mismo nivel
    match = re.search(
        r"    def send_initiative\(self\):.*?(?=\n    (?:def |async def |# ─))",
        src,
        re.DOTALL,
    )
    assert match, "No se encontró send_initiative en reflex_companion.py"
    return match.group(0)


def test_send_initiative_gates_before_any_user_message():
    """send_initiative debe retornar early si no hay mensajes del user.

    El gate va ANTES de tocar `is_thinking` y de cualquier `yield` —
    si tocara is_thinking primero el spinner aparecería y desaparecería
    causando flash similar al original.
    """
    body = _send_initiative_body()
    # El gate debe usar el mismo patrón que _run_startup_engagement
    # (any(m.get("role") == "user" for m in self.messages)) y retornar.
    gate_pattern = re.search(
        r"if not any\(\s*m\.get\(\s*[\"']role[\"']\s*\)\s*==\s*[\"']user[\"'].*?for m in self\.messages\s*\):\s*\n\s*(#[^\n]*\n\s*)*return",
        body,
        re.DOTALL,
    )
    assert gate_pattern is not None, (
        "send_initiative debe gatear con `if not any(m.get('role') == 'user' "
        "for m in self.messages): return` ANTES de tocar is_thinking. Sin "
        "este gate, clickear ✨ al inicio del chat crea un flash de bubble "
        "vacía que se borra ~1s después (Ashley no tiene contexto y "
        "devuelve [mood:default] silencioso)."
    )


def test_send_initiative_gate_is_before_is_thinking():
    """El gate DEBE estar antes de `self.is_thinking = True`. Si va
    después, ya hay efecto secundario visible y el flash persiste."""
    body = _send_initiative_body()
    gate_idx = body.find("if not any(")
    is_thinking_idx = body.find("self.is_thinking = True")
    assert gate_idx != -1, "Falta el gate `if not any(...)`"
    assert is_thinking_idx != -1, "Falta `self.is_thinking = True`"
    assert gate_idx < is_thinking_idx, (
        "El gate debe ir ANTES de `self.is_thinking = True`. Si va "
        "después, el spinner se enciende y se apaga produciendo flash."
    )


def test_send_initiative_gate_is_before_first_yield():
    """El gate debe ir antes del primer `yield`. Cualquier yield ya
    fuerza un re-render del UI."""
    body = _send_initiative_body()
    gate_idx = body.find("if not any(")
    yield_match = re.search(r"\n        yield\b", body)
    assert gate_idx != -1, "Falta el gate `if not any(...)`"
    assert yield_match is not None, "Falta `yield` en send_initiative"
    assert gate_idx < yield_match.start(), (
        "El gate debe ir ANTES del primer `yield`. Cualquier yield "
        "fuerza render del UI y produce flash visible."
    )
