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
