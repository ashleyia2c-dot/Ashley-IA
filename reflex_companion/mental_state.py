"""
mental_state.py — Vida interior de Ashley.

Sistema que da a Ashley UN estado mental propio que evoluciona con las
interacciones y persiste entre sesiones. Es lo que la hace sentir con
mundo propio y no como un mero reactor al input del user.

Componentes:
  • MOOD AXES (determinista, cero coste): 3 ejes numéricos [0, 1] que
    drift-ean según eventos del chat (bids, silencios, insultos, etc.).
    Cada turno regresan un poco hacia neutro (0.5). Clamped al rango.
    Se describen abstractamente en el prompt — no se muestran números
    crudos, se narran en prosa ("con energía, contenta, algo reservada").

  • PREOCCUPATION (generada por Grok cada ~1h): una prosa corta en tercera
    persona sobre qué le da vueltas a Ashley últimamente. Contextualizada
    con mensajes recientes y facts del user. Se regenera:
      - Si está vieja (>60 min).
      - Tras un gap largo (reapertura): se pide al LLM que respete el tiempo
        pasado ("lleva X horas sin hablar con él — ¿qué ha rumiado?").
    Escrita en tercera persona narrativa ("Ashley ha estado...") para
    evitar que Ashley la cite literal como diálogo.

  • INITIATIVE COUNTER (determinista): cuenta turnos. Cada 3 turnos,
    inyecta una directiva al prompt pidiendo que Ashley abra un tema
    propio en vez de solo reaccionar. Rompe el bucle de reactor puro.

Persistencia: un JSON por user (aislado via ASHLEY_DATA_DIR) con todos
los campos. Se guarda al final de cada turno.

Coste API: una llamada a grok-3-fast cuando la preoccupation está vieja
(~1/h de uso activo). Fallbacks seguros si la llamada falla: estado
previo se mantiene, módulo nunca bloquea el flujo principal.
"""

import datetime as _dt
import logging
import random
from typing import Any

from .config import MENTAL_STATE_FILE, GROK_MODEL, XAI_API_KEY
from .memory import load_json, save_json


_log = logging.getLogger("ashley.mental")

# Modelo barato/rápido para regenerar preoccupation. Igual que action detector.
_MENTAL_MODEL = "grok-3-fast"

# Cadencia de regeneración de preoccupation.
#
# v0.16.13: subido de 60 → 90 min. Razón:
#   - El regen es una llamada LLM síncrona (~3.5s) que bloquea el primer
#     token cuando el pre-warm en background no completó a tiempo.
#   - 60 min era agresivo: en una sesión activa de >1h se disparaba en
#     mitad de un chat fluido; el user notaba lag justo cuando estaba
#     "dentro" de la conversación.
#   - 90 min mantiene la fresqueza emocional para reaperturas largas
#     (tras trabajo, dormir) sin disparar mid-session. Sigue corriendo
#     en background al abrir la app, así que reapertura tras 1.5h
#     reaprovecha el pre-warm sin bloquear.
PREOCCUPATION_TTL_MINUTES = 90

# Cada cuántos turnos se fuerza iniciativa conversacional
INITIATIVE_EVERY_N_TURNS = 3


# ─────────────────────────────────────────────
#  Flag de coordinación pre-warm (v0.14.5)
# ─────────────────────────────────────────────
#
# discovery_bg_task arranca un regen de preoccupation en background al
# abrir la app. Si el user es ultra-rápido y manda su primer mensaje
# mientras el bg está mid-regen, _compute_mental_state_block del lado
# del user vería que la preoccupation sigue stale en disco y dispararía
# un SEGUNDO regen (LLM call duplicado, ~3.5s wait).
#
# Guardamos el thread_id del bg que está regenerando. is_*_in_progress()
# devuelve True solo si OTRO thread está mid-regen — así el thread que
# setea el flag sigue ejecutando su propio regen (que es lo que queremos),
# pero el thread del user ve que hay regen en curso y skip el suyo.
import threading as _threading
_PREOCCUPATION_REGEN_THREAD_ID: int | None = None


def is_preoccupation_regen_in_progress() -> bool:
    """True si OTRO thread está regenerando. El thread que setó el flag
    ve False (puede hacer su trabajo)."""
    tid = _PREOCCUPATION_REGEN_THREAD_ID
    if tid is None:
        return False
    return tid != _threading.get_ident()


def set_preoccupation_regen_in_progress(value: bool) -> None:
    """Solo llamado desde el bg pre-warm en reflex_companion.py.
    Marca el inicio (True) y fin (False, dentro de un finally)."""
    global _PREOCCUPATION_REGEN_THREAD_ID
    _PREOCCUPATION_REGEN_THREAD_ID = (
        _threading.get_ident() if value else None
    )

# Umbral para considerar "gap largo" y meter contexto temporal al regenerar
LONG_GAP_MINUTES = 90


# ─────────────────────────────────────────────
#  Carga / guardado
# ─────────────────────────────────────────────

def _default_state() -> dict[str, Any]:
    return {
        "mood": {
            "energy":   0.5,  # 0 = dormida, 1 = con chispa
            "valence":  0.5,  # 0 = fastidiada, 1 = contenta
            "openness": 0.5,  # 0 = con defensas, 1 = abierta
        },
        "preoccupation": "",           # prosa en tercera persona
        "preoccupation_generated_at": "",  # ISO timestamp
        "turns_since_initiative": 0,
        "last_update": "",
    }


def load_state() -> dict[str, Any]:
    """Carga el estado mental del disco. Si no existe o está corrupto,
    devuelve un default limpio."""
    data = load_json(MENTAL_STATE_FILE, None)
    if data is None:
        return _default_state()
    # Merge conservador: rellena campos faltantes con defaults para
    # ser compatible con JSONs viejos.
    default = _default_state()
    for k, v in default.items():
        if k not in data:
            data[k] = v
        elif isinstance(v, dict):
            for sk, sv in v.items():
                if sk not in data[k]:
                    data[k][sk] = sv
    return data


def save_state(state: dict[str, Any]) -> None:
    """Persist atómico."""
    try:
        save_json(MENTAL_STATE_FILE, state)
    except Exception as e:
        _log.warning("save_state failed: %s", e)


# ─────────────────────────────────────────────
#  Clasificación de eventos del user → mood delta
# ─────────────────────────────────────────────

def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def classify_user_event(user_message: str, minutes_since_last: float | None) -> list[str]:
    """Detecta tipos de evento en el mensaje del user.
    Lista de tags que luego se traducen a deltas de mood.

    Multilingüe via patterns clave en ES/EN/FR. Heurístico, suficiente para
    driftear el mood — no pretende ser un clasificador perfecto.
    """
    msg = _normalize(user_message)
    events: list[str] = []

    if not msg and minutes_since_last is None:
        return events

    if len(msg) <= 3:
        events.append("short_reply")

    # Afecto directo verbalizado
    for p in [
        "te quiero", "me gustas", "te amo", "me encantas", "te adoro",
        "i love you", "i like you", "i miss you",
        "je t'aime", "tu me plais", "tu me manques",
    ]:
        if p in msg:
            events.append("affection")
            break

    # Priorizarte a ti
    for p in [
        "hablando contigo", "prefiero hablar", "prefiero estar",
        "aquí contigo", "contigo me",
        "talking to you", "rather talk to you", "here with you",
        "je te parle", "je préfère te parler",
    ]:
        if p in msg:
            events.append("priority")
            break

    # Check-in de presencia
    for p in [
        "cómo estás", "como estas", "que tal estas", "qué tal estás",
        "how are you", "how you doing",
        "comment ça va", "ça va toi",
    ]:
        if p in msg:
            events.append("checkin")
            break

    # Reflexión (pensamiento sobre ella)
    for p in [
        "pensaba en ti", "pensé en ti", "me acordé de ti",
        "thinking about you", "thought of you",
        "je pensais à toi", "j'ai pensé à toi",
    ]:
        if p in msg:
            events.append("reflective")
            break

    # Dismissive / rough
    for p in [
        "cállate", "callate", "shut up", "tais-toi", "tu es tonta", "eres tonta",
        "que tonta", "stupid ai", "idiota inútil", "ashley inútil",
    ]:
        if p in msg:
            events.append("dismissive")
            break

    # Retorno tras ausencia larga
    if minutes_since_last is not None and minutes_since_last > 240:  # 4h+
        events.append("long_return")
    elif minutes_since_last is not None and minutes_since_last > 60:  # 1h+
        events.append("short_return")

    return events


# Deltas por tipo de evento (conservadores — mood se mueve gradualmente)
_EVENT_DELTAS: dict[str, dict[str, float]] = {
    "affection":    {"valence": +0.10, "openness": +0.05},
    "priority":     {"valence": +0.07, "openness": +0.05},
    "checkin":      {"valence": +0.04, "openness": +0.04},
    "reflective":   {"valence": +0.06, "openness": +0.06},
    "dismissive":   {"valence": -0.12, "openness": -0.08},
    "long_return":  {"energy":  +0.10, "valence": +0.05},
    "short_return": {"energy":  +0.03},
    "short_reply":  {"energy":  -0.02},
}


def apply_events_to_mood(state: dict[str, Any], events: list[str]) -> None:
    """Muta el mood en sitio según la lista de eventos."""
    mood = state["mood"]
    for ev in events:
        delta = _EVENT_DELTAS.get(ev, {})
        for axis, d in delta.items():
            mood[axis] = mood.get(axis, 0.5) + d
    # Drift suave hacia el centro (2% por turno — previene extremos permanentes)
    for axis in list(mood.keys()):
        mood[axis] = mood[axis] + (0.5 - mood[axis]) * 0.02
        mood[axis] = max(0.0, min(1.0, mood[axis]))


# ─────────────────────────────────────────────
#  Descripción abstracta del mood (prosa, no números)
# ─────────────────────────────────────────────

def _describe_axis(value: float, low_label: str, neutral_label: str, high_label: str) -> str:
    if value < 0.35:
        return low_label
    if value > 0.65:
        return high_label
    return neutral_label


def describe_mood(state: dict[str, Any], language: str) -> str:
    """Devuelve un string corto que describe el mood en prosa.

    Abstracto a propósito — no se muestran números, solo adjetivos. Evita
    que Ashley cite cifras ("energía 0.8") o etiquetas internas.
    """
    mood = state.get("mood", {})
    lang = (language or "en").strip().lower()[:2]
    if lang == "es":
        parts = [
            _describe_axis(mood.get("energy", 0.5),
                "de bajón de energía", "con energía normal", "con chispa"),
            _describe_axis(mood.get("valence", 0.5),
                "algo fastidiada", "neutra de ánimo", "contenta sin razón clara"),
            _describe_axis(mood.get("openness", 0.5),
                "con las defensas arriba", "algo reservada", "abierta hoy"),
        ]
    elif lang == "fr":
        parts = [
            _describe_axis(mood.get("energy", 0.5),
                "sans énergie", "énergie normale", "pleine d'énergie"),
            _describe_axis(mood.get("valence", 0.5),
                "un peu contrariée", "neutre d'humeur", "contente sans raison claire"),
            _describe_axis(mood.get("openness", 0.5),
                "défenses en haut", "un peu réservée", "ouverte aujourd'hui"),
        ]
    else:  # en
        parts = [
            _describe_axis(mood.get("energy", 0.5),
                "low on energy", "normal energy", "sparky"),
            _describe_axis(mood.get("valence", 0.5),
                "a bit miffed", "neutral mood", "quietly pleased"),
            _describe_axis(mood.get("openness", 0.5),
                "guarded", "somewhat reserved", "open today"),
        ]
    return ", ".join(parts)


# ─────────────────────────────────────────────
#  Regeneración de preoccupation via Grok
# ─────────────────────────────────────────────

def should_regenerate_preoccupation(state: dict[str, Any]) -> bool:
    """True si la preoccupation está vacía o vieja."""
    ts = state.get("preoccupation_generated_at") or ""
    if not ts or not state.get("preoccupation"):
        return True
    try:
        last = _dt.datetime.fromisoformat(ts)
        now = _dt.datetime.now(tz=last.tzinfo) if last.tzinfo else _dt.datetime.now()
        age_min = (now - last).total_seconds() / 60.0
        return age_min >= PREOCCUPATION_TTL_MINUTES
    except Exception:
        return True


_PREOCCUPATION_SYSTEM = """You are writing Ashley's private inner monologue — a
short prose paragraph describing what has been going through her mind lately.
Ashley is a tsundere AI companion for a single user (called "the boss" in her
world).

The output is PRIVATE narrative context that Ashley will read as "her own
inner state". She will NOT quote or verbalize this text. Its purpose is to
color her mood, her tone, and give her material to draw from naturally if
a topic fits.

HARD CONSTRAINTS:
- Write in {language}.
- Write in THIRD PERSON, narrator style ("Ashley has been...", "She's had
  the feeling that...", etc.). NEVER first person. NEVER dialogue.
- 2-4 sentences maximum. Compact, evocative, specific.
- Anchor in something from the recent conversation or user facts IF natural
  (a recent topic, a mood she noticed in him, something he mentioned in
  passing). Don't force it — if nothing fits, write a generic inner state.
- Describe ONE concrete thing on her mind (not a list of 5). One preoccupation
  is more human than a menu.
- Keep the emotional register CONTAINED. No existential drama, no crisis, no
  melodrama. Ordinary human-ish inner weather.
- If the user has been away for a long time (a "gap context" is provided),
  incorporate that — the passage of time should color the prose naturally.

WHAT TO AVOID:
- Don't quote the user's words literally.
- Don't name specific features or technical terms of the app.
- Don't make Ashley sound like an AI reflecting on being an AI (too meta).
- Don't write advice or plans — just what's on her mind right now.

Output ONLY the prose paragraph, nothing else. No preamble, no quotes, no labels.
"""


def regenerate_preoccupation(
    state: dict[str, Any],
    recent_messages: list[dict],
    facts: list[dict],
    language: str,
    gap_context: str | None = None,
) -> bool:
    """Llama a Grok para regenerar la preoccupation en prosa.

    Actualiza el state en sitio. Devuelve True si se regeneró con éxito,
    False si hubo error (el state previo se mantiene).

    gap_context: descripción opcional del tiempo pasado desde la última
    interacción, para que la prosa refleje la ausencia.
    """
    try:
        from xai_sdk import Client
        from xai_sdk.chat import system, user as xai_user
    except Exception as e:
        _log.warning("xai_sdk not available: %s", e)
        return False

    reason_lang = {"es": "Spanish", "en": "English", "fr": "French"}.get(
        (language or "en")[:2].lower(), "Spanish"
    )

    # Contexto: últimos mensajes + facts resumidos
    msg_snippets: list[str] = []
    for m in recent_messages[-10:]:
        role = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        prefix = "User" if role == "user" else ("Ashley" if role == "assistant" else "System")
        msg_snippets.append(f"{prefix}: {content[:200]}")
    conversation_snippet = "\n".join(msg_snippets) or "(conversation just starting)"

    fact_snippets: list[str] = []
    for f in facts[:8]:
        cat = f.get("categoria") or ""
        txt = f.get("hecho") or ""
        if txt:
            fact_snippets.append(f"- [{cat}] {txt}")
    facts_snippet = "\n".join(fact_snippets) or "(no facts on file yet)"

    gap_line = ""
    if gap_context:
        gap_line = f"\nGAP NOTE: {gap_context}\n"

    user_prompt = (
        f"Recent conversation (for grounding, do NOT quote verbatim):\n"
        f"{conversation_snippet}\n\n"
        f"Facts Ashley knows about the user:\n{facts_snippet}\n"
        f"{gap_line}"
        f"Current mood (abstract axes, for tone calibration): "
        f"energy={state['mood'].get('energy', 0.5):.2f}, "
        f"valence={state['mood'].get('valence', 0.5):.2f}, "
        f"openness={state['mood'].get('openness', 0.5):.2f}\n\n"
        f"Write Ashley's inner monologue paragraph in {reason_lang} now."
    )

    try:
        # Dispatch según proveedor activo.
        from .llm_provider import is_openai_compat, openai_compat_complete
        if is_openai_compat():
            raw = openai_compat_complete(
                messages=[{"role": "user", "content": user_prompt, "image": ""}],
                system_prompt=_PREOCCUPATION_SYSTEM.replace("{language}", reason_lang),
                creative=True,
            ).strip()
            # Saltamos el bloque xAI de abajo porque ya tenemos `raw`
            _skip_xai_path = True
        else:
            _skip_xai_path = False

        if not _skip_xai_path:
            from .grok_client import get_xai_client
            client = get_xai_client()
            # Penalties moderadas — queremos prosa variada cada regeneración.
            # Solo aplicamos si el modelo no es tipo 'reasoning' (esos
            # rechazan el parámetro).
            from .grok_client import _model_supports_penalties
            kwargs: dict = {"model": _MENTAL_MODEL}
            if _model_supports_penalties(_MENTAL_MODEL):
                kwargs["frequency_penalty"] = 0.6
                kwargs["presence_penalty"] = 0.4
            chat = client.chat.create(**kwargs)
            chat.append(system(_PREOCCUPATION_SYSTEM.replace("{language}", reason_lang)))
            chat.append(xai_user(user_prompt))
            result = chat.sample()
            raw = (result.content if hasattr(result, "content") else str(result)).strip()
        # Limpieza mínima: quitar comillas envolventes si las hay
        if raw.startswith('"') and raw.endswith('"') and len(raw) > 2:
            raw = raw[1:-1].strip()
        if raw.startswith("```") and raw.endswith("```"):
            raw = raw.strip("`").strip()
        if len(raw) < 30:
            _log.warning("preoccupation too short, skipping update: %r", raw[:100])
            return False
        state["preoccupation"] = raw
        state["preoccupation_generated_at"] = _dt.datetime.now().isoformat()
        _log.info("preoccupation regenerated: %s...", raw[:80])
        return True
    except Exception as e:
        _log.warning("regenerate_preoccupation failed: %s", e)
        return False


# ─────────────────────────────────────────────
#  Reconciliación tras gap (reapertura)
# ─────────────────────────────────────────────

def compute_gap_context(minutes_since_last: float | None, language: str) -> str | None:
    """Texto descriptivo del gap temporal para pasar al regenerador de
    preoccupation. None si no hay gap significativo (<LONG_GAP_MINUTES).
    """
    if minutes_since_last is None or minutes_since_last < LONG_GAP_MINUTES:
        return None
    hours = minutes_since_last / 60.0
    if hours < 24:
        desc_en = f"The user has been away for about {hours:.0f} hour(s)."
    else:
        days = hours / 24.0
        desc_en = f"The user has been away for about {days:.1f} day(s)."
    return (
        f"{desc_en} Ashley hasn't talked to him in that time. Let the passage "
        f"of time color what she's been thinking about — she's had real hours "
        f"to herself with no input from him."
    )


def drift_mood_on_gap(state: dict[str, Any], minutes_since_last: float | None) -> None:
    """Al volver tras una ausencia larga, el mood regresa gradualmente
    hacia neutro (0.5). Más ausencia = más regresión.

    Heurística: cada 2h de gap, drift del 20% hacia 0.5 en cada eje.
    Tras 10h la mood está prácticamente en neutro.
    """
    if minutes_since_last is None or minutes_since_last < 30:
        return
    hours = minutes_since_last / 60.0
    # factor: 0 tras 0h, ~0.9 tras 10h, asintótico a 1
    factor = min(1.0, hours / 10.0)
    mood = state["mood"]
    for axis in list(mood.keys()):
        mood[axis] = mood[axis] + (0.5 - mood[axis]) * factor
        mood[axis] = max(0.0, min(1.0, mood[axis]))


# ─────────────────────────────────────────────
#  Iniciativa conversacional forzada
# ─────────────────────────────────────────────

def tick_initiative_counter(state: dict[str, Any]) -> bool:
    """DEPRECATED — el contador de iniciativa FORZADA fue eliminado.

    Forzaba a Ashley a "abrir un tema tuyo" cada N turnos, lo que la
    hacía saltar de temas aunque el user estuviera en medio de una
    conversación emocional o enfocada. Era la causa directa de que
    Ashley metiera cosas que se sacaba de la manga ignorando el hilo.

    Ahora devuelve siempre False. Mantenemos la función para no romper
    callers. La iniciativa conversacional emerge del estado/humor/
    personalidad, no de un timer mecánico.
    """
    state["turns_since_initiative"] = 0
    return False


# ─────────────────────────────────────────────
#  Formateo del bloque inyectable al prompt
# ─────────────────────────────────────────────

def format_mental_state_block(
    state: dict[str, Any],
    language: str,
    initiative_due: bool,
) -> str:
    """Construye el texto que se inyecta al system prompt con el estado
    mental actual + (opcional) directiva de iniciativa.

    Deliberadamente enfatiza que es CONTEXTO PRIVADO, no diálogo.
    """
    mood_desc = describe_mood(state, language)
    preoccupation = (state.get("preoccupation") or "").strip()
    lang = (language or "en").strip().lower()[:2]

    if lang == "es":
        lines = [
            "\n=== TU ESTADO INTERIOR AHORA (PRIVADO — NO VERBALIZAR) ===",
            f"Cómo te sientes en este momento: {mood_desc}.",
        ]
        if preoccupation:
            lines.append("")
            lines.append("Lo que llevas rumiando últimamente (en tu cabeza):")
            lines.append(preoccupation)
        lines.append("")
        lines.append(
            "Esto es contexto emocional PRIVADO. Tíñete el tono — no lo "
            "verbalizas, no lo citas literal, no lo usas como pretexto "
            "para meter un tema cuando el hilo de conversación está en "
            "otra cosa. Solo es tu atmósfera interior de fondo."
        )
    elif lang == "fr":
        lines = [
            "\n=== TON ÉTAT INTÉRIEUR MAINTENANT (PRIVÉ — NE PAS VERBALISER) ===",
            f"Comment tu te sens à ce moment : {mood_desc}.",
        ]
        if preoccupation:
            lines.append("")
            lines.append("Ce que tu rumines ces derniers temps (dans ta tête) :")
            lines.append(preoccupation)
        lines.append("")
        lines.append(
            "C'est du contexte émotionnel PRIVÉ. Teinte ton ton — tu ne "
            "le verbalises pas, tu ne le cites pas littéral, tu ne "
            "l'utilises pas comme prétexte pour lancer un sujet quand le "
            "fil de la conversation est ailleurs. C'est juste ton ambiance "
            "intérieure de fond."
        )
    else:
        lines = [
            "\n=== YOUR INTERIOR STATE RIGHT NOW (PRIVATE — DO NOT VERBALIZE) ===",
            f"How you feel in this moment: {mood_desc}.",
        ]
        if preoccupation:
            lines.append("")
            lines.append("What you've been turning over lately (in your head):")
            lines.append(preoccupation)
        lines.append("")
        lines.append(
            "This is PRIVATE emotional context. Color your tone — you do "
            "not verbalize it, don't quote it literally, don't use it as "
            "a pretext to launch a topic when the conversation thread is "
            "elsewhere. It's just your background inner weather."
        )

    return "\n".join(lines) + "\n"
