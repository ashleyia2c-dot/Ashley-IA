"""Tests del topic_share detector.

El detector ahora:
  • NO dispara en momentos emocionales (triste/cansado/necesitado)
  • SOLO dispara en shares claros de preferencia/opinión
  • Cuando detecta momento emocional, inyecta bloque de ESCUCHAR
"""

from reflex_companion.topic_share import (
    is_substantive_share,
    is_emotional_moment,
    format_topic_directive,
    format_listening_hint,
    compute_directive_if_needed,
)


# ──────────────────────────────────────────────────
#  Detección de momento emocional
# ──────────────────────────────────────────────────

def test_emotional_markers_trigger():
    for msg in [
        "estoy triste hoy",
        "me siento mal",
        "estoy agotado del todo",
        "no puedo más con esto",
        "necesito hablar",
        "me da miedo fallar",
        "me siento solo ahora",
        "i'm sad today",
        "i'm exhausted",
        "je suis triste",
    ]:
        assert is_emotional_moment(msg), f"missed emotional: {msg!r}"


def test_neutral_message_not_emotional():
    for msg in [
        "hola que tal",
        "si, exacto",
        "acabo de terminar el test",
        "viste la peli nueva",
    ]:
        assert not is_emotional_moment(msg), f"false positive: {msg!r}"


# ──────────────────────────────────────────────────
#  Detección de preference share
# ──────────────────────────────────────────────────

def test_preference_share_triggers():
    """User declara gusto/opinión → dispara."""
    for msg in [
        "mi favorito es Dark Souls porque la densidad del mapa",
        "me encanta la música clásica en sesiones largas",
        "prefiero los RPGs antes que los shooters",
        "creo que ese director está sobrevalorado",
        "pienso que lo mejor es terminar antes",
    ]:
        assert is_substantive_share(msg), f"missed share: {msg!r}"


def test_emotional_with_preference_marker_does_NOT_trigger():
    """CLAVE: si el user está emocional Y menciona un gusto, el
    modo emocional gana — no disparamos directive de opinar."""
    msg = "me siento mal y no me gusta sentirme así"
    assert is_emotional_moment(msg) is True
    assert is_substantive_share(msg) is False


def test_casual_message_no_trigger():
    """Mensajes normales sin declaración de gusto → no disparan."""
    for msg in [
        "hola como estas hoy",
        "acabo de volver del trabajo",
        "estoy viendo un video random",
        "si, el que más peto en views",  # antes disparaba — ahora no porque no hay preference marker
    ]:
        assert is_substantive_share(msg) is False, f"false trigger: {msg!r}"


def test_short_message_never_triggers():
    for msg in ["si", "no", "ok", "me gusta", "", "hola"]:
        assert is_substantive_share(msg) is False


# ──────────────────────────────────────────────────
#  Formato de directivas
# ──────────────────────────────────────────────────

def test_topic_directive_is_invitation_not_imposition():
    """La directiva NO dice OBLIGATORIO/MUST/DEBES — es invitación."""
    for lang in ("es", "en", "fr"):
        out = format_topic_directive(lang)
        assert len(out) > 100
        lower = out.lower()
        assert "obligatorio" not in lower
        assert "mandatory" not in lower
        assert "must " not in lower.replace("must have", "")


def test_listening_hint_has_clear_do_dont():
    """El hint emocional tiene 'lo que haces' + 'lo que NO haces'."""
    for lang in ("es", "en", "fr"):
        out = format_listening_hint(lang)
        assert len(out) > 100
        lower = out.lower()
        # Marcador del "priority" o su equivalente
        assert "prioridad" in lower or "priorité" in lower or "priority" in lower
        # Indica acompañar/listen/accompagner
        assert any(k in lower for k in ["acompañar", "accompagner", "with him", "présente"])


# ──────────────────────────────────────────────────
#  Dispatcher: compute_directive_if_needed
# ──────────────────────────────────────────────────

def test_dispatcher_emotional_priority():
    """Si hay emoción, el listening hint gana sobre todo lo demás."""
    msg = "estoy triste y mi favorito era esa peli que veíamos"
    out = compute_directive_if_needed(msg, "es")
    assert out is not None
    # Debe ser el bloque de escuchar, NO el de opinar
    assert "ESCUCH" in out.upper() or "EMOCIONAL" in out or "ACOMPAÑAR" in out.upper()


def test_dispatcher_preference_when_not_emotional():
    msg = "mi favorito es Dark Souls porque la densidad me flipa"
    out = compute_directive_if_needed(msg, "es")
    assert out is not None
    assert "GUSTO" in out.upper() or "OPINIÓN" in out.upper()


def test_dispatcher_casual_none():
    """Mensaje normal sin declaración de gusto ni emoción → None."""
    for msg in ["si exacto", "hola qué tal", "acabé el test"]:
        assert compute_directive_if_needed(msg, "es") is None


def test_dispatcher_empty():
    assert compute_directive_if_needed("", "es") is None
    assert compute_directive_if_needed(None, "es") is None
