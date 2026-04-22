"""Tests for context_compression module.

Cubre la lógica determinista (umbral, cache, formato). NO cubre la llamada
real al modelo fast — esa se mockea para tests unitarios.
"""

import json
import os
import tempfile
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _isolate_summary_file(tmp_path, monkeypatch):
    """Evita que los tests escriban en el SUMMARY_FILE real del user."""
    tmp_file = tmp_path / "context_summary_ashley.json"
    import reflex_companion.context_compression as cc
    monkeypatch.setattr(cc, "SUMMARY_FILE", str(tmp_file))
    # Reset de la cache en memoria si la hubiera
    yield
    # cleanup automático con tmp_path


def _mk_msgs(count: int, topic: str = "SQL") -> list[dict]:
    """Genera `count` mensajes alternando user/assistant mencionando topic."""
    msgs = []
    for i in range(count):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"{topic} point number {i} here is more text"
        msgs.append({"role": role, "content": content, "timestamp": "", "id": f"m-{i}", "image": ""})
    return msgs


# ──────────────────────────────────────────────────
#  Umbral: no se comprime con historial pequeño
# ──────────────────────────────────────────────────

def test_short_history_returns_unchanged():
    from reflex_companion.context_compression import compress_history
    msgs = _mk_msgs(10)
    result = compress_history(msgs, "es")
    assert result == msgs


def test_exactly_at_threshold_returns_unchanged():
    from reflex_companion.context_compression import compress_history, COMPRESSION_THRESHOLD
    msgs = _mk_msgs(COMPRESSION_THRESHOLD)
    result = compress_history(msgs, "es")
    assert result == msgs


# ──────────────────────────────────────────────────
#  Compresión: con historial largo, llama al summarizer
# ──────────────────────────────────────────────────

def test_long_history_calls_summarizer_and_compresses():
    import reflex_companion.context_compression as cc
    msgs = _mk_msgs(40)
    fake_summary = "User and Ashley talked about SQL and streams. User is tired."

    with mock.patch.object(cc, "_call_fast_summarizer", return_value=fake_summary) as summarizer:
        result = cc.compress_history(msgs, "es")
        assert summarizer.called, "expected summarizer to be called"

    # Debe haber menos mensajes que el original
    assert len(result) < len(msgs)
    # El primer mensaje es el resumen
    assert result[0]["role"] == "system_result"
    assert fake_summary in result[0]["content"]
    # Los últimos KEEP_RECENT originales se mantienen
    assert result[-cc.KEEP_RECENT:] == msgs[-cc.KEEP_RECENT:]


def test_compressed_output_structure():
    import reflex_companion.context_compression as cc
    msgs = _mk_msgs(30)
    with mock.patch.object(cc, "_call_fast_summarizer", return_value="Recap text"):
        result = cc.compress_history(msgs, "en")
    # Summary + KEEP_RECENT
    assert len(result) == 1 + cc.KEEP_RECENT
    # Summary message tiene id especial
    assert result[0]["id"] == "_ctx_summary"


# ──────────────────────────────────────────────────
#  Caché: reuso cuando el historial no ha crecido mucho
# ──────────────────────────────────────────────────

def test_cache_reused_when_history_grows_slightly():
    import reflex_companion.context_compression as cc
    msgs = _mk_msgs(30)

    # Primera llamada — genera cache
    with mock.patch.object(cc, "_call_fast_summarizer", return_value="First recap") as s1:
        cc.compress_history(msgs, "es")
        assert s1.call_count == 1

    # Añadir 3 mensajes — por debajo del umbral REGEN_AFTER_NEW_MSGS
    msgs_plus = msgs + _mk_msgs(3)
    with mock.patch.object(cc, "_call_fast_summarizer", return_value="Should not be called") as s2:
        result = cc.compress_history(msgs_plus, "es")
        assert s2.call_count == 0, "summarizer should not run, cache valid"
    # Pero el resumen del cache sigue presente
    assert result[0]["role"] == "system_result"
    assert "First recap" in result[0]["content"]


def test_cache_regenerated_after_enough_new_messages():
    import reflex_companion.context_compression as cc
    msgs = _mk_msgs(30)

    with mock.patch.object(cc, "_call_fast_summarizer", return_value="First recap"):
        cc.compress_history(msgs, "es")

    # Añadir suficientes mensajes para pasar el threshold
    msgs_plus = msgs + _mk_msgs(cc.REGEN_AFTER_NEW_MSGS + 5)
    with mock.patch.object(cc, "_call_fast_summarizer", return_value="New recap") as s2:
        result = cc.compress_history(msgs_plus, "es")
        assert s2.call_count == 1, "summarizer should have regenerated"
    assert "New recap" in result[0]["content"]


def test_cache_invalidated_when_history_shrinks():
    """Si el user borró mensajes, el cache previo no es válido."""
    import reflex_companion.context_compression as cc
    big_msgs = _mk_msgs(40)

    with mock.patch.object(cc, "_call_fast_summarizer", return_value="Big recap"):
        cc.compress_history(big_msgs, "es")

    # Ahora "borramos" mensajes — historial más corto que lo que cubre cache
    short_msgs = _mk_msgs(25)
    with mock.patch.object(cc, "_call_fast_summarizer", return_value="Short recap") as s2:
        cc.compress_history(short_msgs, "es")
        assert s2.call_count == 1, "shrunk history should force regen"


# ──────────────────────────────────────────────────
#  Fallback: si el summarizer falla
# ──────────────────────────────────────────────────

def test_summarizer_failure_falls_back_to_raw():
    import reflex_companion.context_compression as cc
    msgs = _mk_msgs(30)

    with mock.patch.object(cc, "_call_fast_summarizer", return_value=""):
        result = cc.compress_history(msgs, "es")
    # Fallback — devuelve raw cuando no hay cache ni summary nuevo
    assert result == msgs


def test_summarizer_failure_keeps_stale_cache_if_exists():
    """Si hay cache viejo y la regeneración falla, se reutiliza el viejo."""
    import reflex_companion.context_compression as cc
    msgs = _mk_msgs(30)

    with mock.patch.object(cc, "_call_fast_summarizer", return_value="Stale but usable"):
        cc.compress_history(msgs, "es")

    msgs_plus = msgs + _mk_msgs(cc.REGEN_AFTER_NEW_MSGS + 5)
    with mock.patch.object(cc, "_call_fast_summarizer", return_value=""):
        result = cc.compress_history(msgs_plus, "es")
    # Resumen viejo sigue ahí
    assert result[0]["role"] == "system_result"
    assert "Stale but usable" in result[0]["content"]


# ──────────────────────────────────────────────────
#  Dialogue formatting (input al summarizer)
# ──────────────────────────────────────────────────

def test_format_dialogue_includes_user_and_assistant_only():
    from reflex_companion.context_compression import _format_dialogue_for_summary
    msgs = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola bobo"},
        {"role": "system_result", "content": "[ignoreme]"},
        {"role": "user", "content": "ok"},
    ]
    text = _format_dialogue_for_summary(msgs)
    assert "User: hola" in text
    assert "Ashley: hola bobo" in text
    assert "ignoreme" not in text
    assert "system_result" not in text


def test_format_dialogue_truncates_long_messages():
    from reflex_companion.context_compression import _format_dialogue_for_summary
    long_msg = [{"role": "user", "content": "x" * 1000}]
    text = _format_dialogue_for_summary(long_msg, max_chars_per_msg=100)
    # Truncado + ellipsis
    assert "..." in text
    assert len(text) < 500
