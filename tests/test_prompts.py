"""
Tests for reflex_companion.prompts — language dispatch and prompt construction.
"""

import pytest

from reflex_companion.prompts import build_system_prompt, build_initiative_prompt


# ── Language selection ───────────────────────────────────────────────────────


def test_build_system_prompt_english():
    """lang='en' produces the English prompt with 'TAGS -- READ FIRST'."""
    result = build_system_prompt([], [], lang="en")
    assert "TAGS — READ FIRST" in result


def test_build_system_prompt_spanish():
    """lang='es' produces the Spanish prompt with 'TAGS -- LEER PRIMERO'."""
    result = build_system_prompt([], [], lang="es")
    assert "TAGS — LEER PRIMERO" in result


def test_build_system_prompt_french():
    """lang='fr' produces the French prompt with 'TAGS — À LIRE EN PREMIER'."""
    result = build_system_prompt([], [], lang="fr")
    assert "TAGS — À LIRE EN PREMIER" in result
    # Content check: the FR-specific term must appear (not a fallback to EN).
    assert "patron" in result.lower()


def test_build_system_prompt_default_is_english():
    """Default lang (no arg) produces English prompt."""
    result = build_system_prompt([], [])
    assert "TAGS — READ FIRST" in result


def test_unsupported_lang_falls_back_to_english():
    """Unknown lang codes fall back to English instead of crashing."""
    result = build_system_prompt([], [], lang="de")
    assert "TAGS — READ FIRST" in result


def test_build_initiative_prompt_french():
    """Initiative prompt also has a French version."""
    result = build_initiative_prompt([], [], lang="fr")
    assert "Ashley" in result
    assert "patron" in result.lower()


# ── voice_mode ───────────────────────────────────────────────────────────────


def test_voice_mode_true_english():
    """voice_mode=True with lang='en' injects NATURAL VOICE MODE section."""
    result = build_system_prompt([], [], voice_mode=True, lang="en")
    assert "NATURAL VOICE MODE" in result


def test_voice_mode_true_spanish():
    """voice_mode=True with lang='es' injects MODO VOZ NATURAL section."""
    result = build_system_prompt([], [], voice_mode=True, lang="es")
    assert "MODO VOZ NATURAL" in result


def test_voice_mode_true_french():
    """voice_mode=True with lang='fr' injects MODE VOIX NATURELLE section."""
    result = build_system_prompt([], [], voice_mode=True, lang="fr")
    assert "MODE VOIX NATURELLE" in result


def test_voice_mode_false_english():
    """voice_mode=False with lang='en' does NOT contain voice mode section."""
    result = build_system_prompt([], [], voice_mode=False, lang="en")
    assert "NATURAL VOICE MODE" not in result


def test_voice_mode_false_spanish():
    """voice_mode=False with lang='es' does NOT contain MODO VOZ NATURAL."""
    result = build_system_prompt([], [], voice_mode=False, lang="es")
    assert "MODO VOZ NATURAL" not in result


# ── build_initiative_prompt ──────────────────────────────────────────────────


def test_initiative_prompt_english():
    """English initiative prompt contains 'You are Ashley'."""
    result = build_initiative_prompt([], [], lang="en")
    assert "You are Ashley" in result


def test_initiative_prompt_spanish():
    """Spanish initiative prompt contains 'Eres Ashley'."""
    result = build_initiative_prompt([], [], lang="es")
    assert "Eres Ashley" in result


# ── system_state injection ───────────────────────────────────────────────────


def test_system_state_injected_english():
    """system_state parameter text appears in the English prompt."""
    result = build_system_prompt([], [], system_state="Open windows: Notepad", lang="en")
    assert "Open windows: Notepad" in result
    assert "SYSTEM STATE" in result


def test_system_state_injected_spanish():
    """system_state parameter text appears in the Spanish prompt."""
    result = build_system_prompt([], [], system_state="Ventanas abiertas: Bloc de notas", lang="es")
    assert "Ventanas abiertas: Bloc de notas" in result
    assert "ESTADO DEL SISTEMA" in result


def test_system_state_absent_when_none():
    """When system_state is None, no SYSTEM STATE section header appears."""
    result = build_system_prompt([], [], system_state=None, lang="en")
    assert "=== SYSTEM STATE (updated now) ===" not in result


# ── time_context injection ───────────────────────────────────────────────────


def test_time_context_injected_english():
    """time_context parameter text appears in the English prompt."""
    result = build_system_prompt([], [], time_context="Now: 14:30, idle 5m", lang="en")
    assert "Now: 14:30, idle 5m" in result
    assert "TIME" in result


def test_time_context_injected_spanish():
    """time_context parameter text appears in the Spanish prompt."""
    result = build_system_prompt([], [], time_context="Ahora: 14:30, ausente 5m", lang="es")
    assert "Ahora: 14:30, ausente 5m" in result
    assert "TIEMPO" in result


def test_time_context_absent_when_none():
    """When time_context is None, no TIME section appears in English."""
    result = build_system_prompt([], [], time_context=None, lang="en")
    # "=== TIME ===" should not appear, but "TIME" may appear in other contexts
    assert "=== TIME ===" not in result


# ── tastes injection ─────────────────────────────────────────────────────────


def test_tastes_injected_english():
    """tastes parameter text appears in the English prompt."""
    result = build_system_prompt([], [], tastes="musica: rock, jazz", lang="en")
    assert "musica: rock, jazz" in result
    assert "BOSS'S TASTES" in result


def test_tastes_injected_spanish():
    """tastes parameter text appears in the Spanish prompt."""
    result = build_system_prompt([], [], tastes="musica: rock, jazz", lang="es")
    assert "musica: rock, jazz" in result
    assert "GUSTOS DEL JEFE" in result


def test_tastes_absent_when_none():
    """When tastes is None, no TASTES section header appears."""
    result = build_system_prompt([], [], tastes=None, lang="en")
    assert "=== THE BOSS'S TASTES ===" not in result


# ── reminders injection ─────────────────────────────────────────────────────


def test_reminders_injected_english():
    """reminders parameter text appears in the English prompt."""
    result = build_system_prompt([], [], reminders="- [abc1] Call doctor", lang="en")
    assert "- [abc1] Call doctor" in result
    assert "PENDING REMINDERS" in result


def test_reminders_injected_spanish():
    """reminders parameter text appears in the Spanish prompt."""
    result = build_system_prompt([], [], reminders="- [abc1] Llamar al medico", lang="es")
    assert "- [abc1] Llamar al medico" in result
    assert "RECORDATORIOS PENDIENTES" in result


def test_reminders_absent_when_none():
    """When reminders is None, no PENDING REMINDERS section appears."""
    result = build_system_prompt([], [], reminders=None, lang="en")
    assert "=== PENDING REMINDERS ===" not in result
