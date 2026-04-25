"""Tests for consecutive-user-message merging.

Ashley supports deleting any message in the chat. When the user deletes
Ashley's last reply, the history ends with a user message. If the user
then sends ANOTHER message, the naive append creates two consecutive
user turns — which xAI and some OpenRouter models reject with a 400.

`_merge_consecutive_users` normalizes that: it joins consecutive user
messages into one before the LLM call.
"""

from reflex_companion.grok_client import _merge_consecutive_users


# ══════════════════════════════════════════════════════════════════════
#  Happy path: no consecutive users → no change
# ══════════════════════════════════════════════════════════════════════

def test_empty_list_returns_empty():
    assert _merge_consecutive_users([]) == []


def test_normal_alternating_history_unchanged():
    messages = [
        {"role": "user", "content": "hola", "image": ""},
        {"role": "assistant", "content": "hey!", "image": ""},
        {"role": "user", "content": "cómo estás", "image": ""},
        {"role": "assistant", "content": "bien", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    assert result == messages  # identical, nothing to merge


def test_only_assistant_messages_unchanged():
    messages = [
        {"role": "assistant", "content": "hola jefe"},
        {"role": "assistant", "content": "sigues ahí?"},
    ]
    # assistant-assistant es raro pero válido — no tocamos
    assert _merge_consecutive_users(messages) == messages


# ══════════════════════════════════════════════════════════════════════
#  The bug case: consecutive user messages get merged
# ══════════════════════════════════════════════════════════════════════

def test_two_consecutive_user_messages_get_merged():
    """El caso clásico: user borra respuesta de Ashley, manda nuevo msg."""
    messages = [
        {"role": "assistant", "content": "hola jefe", "image": ""},
        {"role": "user", "content": "qué tal tu día", "image": ""},
        {"role": "user", "content": "perdona, olvidé la pregunta", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    assert len(result) == 2
    assert result[0]["role"] == "assistant"
    assert result[1]["role"] == "user"
    # Content combinado con separador
    assert "qué tal tu día" in result[1]["content"]
    assert "perdona, olvidé la pregunta" in result[1]["content"]


def test_three_consecutive_user_messages_merge_into_one():
    messages = [
        {"role": "user", "content": "a", "image": ""},
        {"role": "user", "content": "b", "image": ""},
        {"role": "user", "content": "c", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    assert len(result) == 1
    assert result[0]["role"] == "user"
    # Todos los contenidos presentes
    for chunk in ("a", "b", "c"):
        assert chunk in result[0]["content"]


def test_merge_preserves_non_consecutive_separators():
    """user, user, assistant, user, user → 2 merges."""
    messages = [
        {"role": "user", "content": "a", "image": ""},
        {"role": "user", "content": "b", "image": ""},
        {"role": "assistant", "content": "hola", "image": ""},
        {"role": "user", "content": "c", "image": ""},
        {"role": "user", "content": "d", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    assert len(result) == 3
    assert result[0]["role"] == "user"
    assert "a" in result[0]["content"] and "b" in result[0]["content"]
    assert result[1]["role"] == "assistant"
    assert result[2]["role"] == "user"
    assert "c" in result[2]["content"] and "d" in result[2]["content"]


# ══════════════════════════════════════════════════════════════════════
#  Image edge cases: NEVER merge if images are attached
# ══════════════════════════════════════════════════════════════════════

def test_does_not_merge_when_previous_has_image():
    """Merging would lose the image (content-parts don't concatenate)."""
    messages = [
        {"role": "user", "content": "mira esto", "image": "data:image/png;base64,xxx"},
        {"role": "user", "content": "y esto otro", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    # Deben quedar separados para preservar la imagen
    assert len(result) == 2
    assert result[0]["image"] == "data:image/png;base64,xxx"
    assert result[0]["content"] == "mira esto"
    assert result[1]["content"] == "y esto otro"


def test_does_not_merge_when_current_has_image():
    messages = [
        {"role": "user", "content": "tengo una pregunta", "image": ""},
        {"role": "user", "content": "sobre esto", "image": "data:image/png;base64,yyy"},
    ]
    result = _merge_consecutive_users(messages)
    assert len(result) == 2
    assert result[1]["image"] == "data:image/png;base64,yyy"


# ══════════════════════════════════════════════════════════════════════
#  Defensive: missing fields
# ══════════════════════════════════════════════════════════════════════

def test_handles_missing_image_field():
    """Un mensaje sin image key (ausente del dict) no debería crashear."""
    messages = [
        {"role": "user", "content": "a"},  # no image
        {"role": "user", "content": "b"},
    ]
    result = _merge_consecutive_users(messages)
    # .get("image") devuelve None que es falsy → merge procede
    assert len(result) == 1
    assert "a" in result[0]["content"]
    assert "b" in result[0]["content"]


def test_handles_none_content():
    """Mensajes con content=None deben fusionarse sin crashear."""
    messages = [
        {"role": "user", "content": None, "image": ""},
        {"role": "user", "content": "hello", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    assert len(result) == 1
    assert result[0]["content"] == "hello"  # None se trata como ""


# ══════════════════════════════════════════════════════════════════════
#  Purity: original list not mutated
# ══════════════════════════════════════════════════════════════════════

def test_does_not_mutate_input():
    messages = [
        {"role": "user", "content": "a", "image": ""},
        {"role": "user", "content": "b", "image": ""},
    ]
    original = [dict(m) for m in messages]
    _ = _merge_consecutive_users(messages)
    # Input intacto
    assert messages == original


# ══════════════════════════════════════════════════════════════════════
#  system_result messages don't interfere
# ══════════════════════════════════════════════════════════════════════

def test_system_result_between_users_prevents_merge():
    """Si hay un system_result entre dos user messages, NO fusionamos."""
    messages = [
        {"role": "user", "content": "hola", "image": ""},
        {"role": "system_result", "content": "[Sistema] reminder fired", "image": ""},
        {"role": "user", "content": "qué tal", "image": ""},
    ]
    result = _merge_consecutive_users(messages)
    # Los user NO son consecutivos (sys_result entre ellos) → sin cambios
    assert len(result) == 3
    assert [m["role"] for m in result] == ["user", "system_result", "user"]
