"""
context_compression.py — Compresión del historial para romper la repetición.

Problema: el in-context learning. Cuando el historial tiene 40 mensajes y
en los últimos 10 Ashley mencionó "SQL" en cada uno, Grok aprende ese
patrón y lo reproduce en la respuesta 41, por mucho que el system prompt
diga "no repitas temas". El contexto domina la inercia.

Solución estándar de la industria (ChatGPT, Mem.ai, etc.): cuando el
historial crece más allá de un umbral, RESUMIR los mensajes antiguos en
un único mensaje de sistema y mantener crudos solo los N más recientes.

Así Grok ve:
  [Resumen: "el user y Ashley hablaron de su trabajo pendiente, ella le
   animó, él está cansado. Hubo bromas sobre un streamer de fondo."]
  <últimos 12 mensajes raw>

En lugar de ver 40 mensajes donde "SQL" aparece 20 veces. El resumen
captura el CONTENIDO/EMOCIÓN sin enseñar el PATRÓN de frases repetidas.

Caché: el resumen se guarda a disco con un contador de cuántos mensajes
cubría. Se regenera solo cuando han llegado ~8 mensajes nuevos por encima
del último resumen — así normalmente 1 llamada al modelo barato cada
muchos turnos.
"""

import datetime as _dt
import logging
from typing import Any

from .config import _data_path, XAI_API_KEY
from .memory import load_json, save_json


_log = logging.getLogger("ashley.compression")

# Umbral para empezar a comprimir: por debajo de esto, pasamos todos
# los mensajes crudos. Valor conservador — queremos contexto rico
# hasta que empiece a ser problemático.
COMPRESSION_THRESHOLD = 20

# Cuántos mensajes recientes mantenemos crudos cuando se comprime.
# Los recientes son los que le dan a Grok contexto inmediato de tono.
KEEP_RECENT = 12

# Cuántos mensajes nuevos (por encima de lo que cubre el resumen) tienen
# que acumularse antes de regenerar el resumen. Sin esto regenaríamos
# cada turno — caro y innecesario.
REGEN_AFTER_NEW_MSGS = 8

# Modelo rápido y barato para el resumen. Mismo que usa el critic y el
# detector de acciones.
_FAST_MODEL = "grok-3-fast"

SUMMARY_FILE = _data_path("context_summary_ashley.json")


# ─────────────────────────────────────────────
#  Flag de coordinación pre-warm (v0.14.5)
# ─────────────────────────────────────────────
#
# Mismo patrón que mental_state. discovery_bg_task arranca un regen del
# resumen en background al abrir la app. Si el user manda mensaje mientras
# corre, compress_history detectaría caché stale y dispararía un SEGUNDO
# LLM call (~3.9s extra de wait). Con el flag, devuelve el valor stale
# (o el historial raw si no hay caché todavía) sin llamada extra.
#
# Guardamos thread_id — is_compress_regen_in_progress() devuelve True solo
# si OTRO thread está regenerando. El thread que setea el flag puede
# ejecutar su propio regen sin auto-bloquearse.
import threading as _threading
_COMPRESS_REGEN_THREAD_ID: int | None = None


def is_compress_regen_in_progress() -> bool:
    """True si OTRO thread está regenerando."""
    tid = _COMPRESS_REGEN_THREAD_ID
    if tid is None:
        return False
    return tid != _threading.get_ident()


def set_compress_regen_in_progress(value: bool) -> None:
    """Solo llamado desde el bg pre-warm en reflex_companion.py."""
    global _COMPRESS_REGEN_THREAD_ID
    _COMPRESS_REGEN_THREAD_ID = (
        _threading.get_ident() if value else None
    )


# ─────────────────────────────────────────────
#  Caché persistente
# ─────────────────────────────────────────────

def _load_cache() -> dict[str, Any]:
    data = load_json(SUMMARY_FILE, None)
    if data is None:
        return {"text": "", "covers_up_to_count": 0, "generated_at": ""}
    return data


def _save_cache(data: dict[str, Any]) -> None:
    try:
        save_json(SUMMARY_FILE, data)
    except Exception as e:
        _log.warning("save cache failed: %s", e)


def invalidate_cache() -> None:
    """Utilidad para tests o forzar regeneración la próxima vez."""
    _save_cache({"text": "", "covers_up_to_count": 0, "generated_at": ""})


# ─────────────────────────────────────────────
#  Llamada al modelo fast para resumir
# ─────────────────────────────────────────────

_SUMMARY_SYSTEM = """You are writing a brief recap of a dialogue between a user
and Ashley (a tsundere AI companion). This recap will REPLACE the full
history in Ashley's context — she'll read it instead of seeing every
message. Your goal: preserve meaning and emotional context WITHOUT
reproducing the specific phrases Ashley has been saying repeatedly.

Write in {language}. 3-6 sentences. Cover:
  - What topics the conversation touched on
  - The user's current state of mind / mood if knowable
  - What Ashley has been preoccupied with (themes, not exact phrases)
  - Any unresolved threads

CRITICAL:
  - Do NOT quote verbatim. Paraphrase everything.
  - Do NOT list every exchange. Group related messages thematically.
  - Write in third person ("The user said...", "Ashley responded with...").
  - Neutral reporter tone, not dramatic or emotional.
  - Be compact. This is a memory aid, not a transcript.

Output ONLY the recap paragraph. No preamble, no labels, no markdown.
"""


def _call_fast_summarizer(dialogue_text: str, language: str) -> str:
    """Single call to the fast model. Returns empty string on failure.
    Dispatcha a OpenRouter o xAI según config del user."""
    lang_name = {"es": "Spanish", "en": "English", "fr": "French"}.get(
        (language or "en")[:2].lower(), "Spanish"
    )
    system_text = _SUMMARY_SYSTEM.replace("{language}", lang_name)
    user_text = f"Dialogue to summarize:\n\n{dialogue_text}\n\nRecap in {lang_name}:"

    try:
        from .llm_provider import is_openai_compat, openai_compat_complete
        if is_openai_compat():
            text = openai_compat_complete(
                messages=[{"role": "user", "content": user_text, "image": ""}],
                system_prompt=system_text,
                creative=True,
            ).strip()
        else:
            from xai_sdk import Client
            from xai_sdk.chat import system, user as xai_user
            client = Client(api_key=XAI_API_KEY)
            # Penalties altas aquí — queremos que el resumen NO copie las frases
            # literales de Ashley. Solo aplica si el modelo no es 'reasoning'.
            from .grok_client import _model_supports_penalties
            kwargs: dict = {"model": _FAST_MODEL}
            if _model_supports_penalties(_FAST_MODEL):
                kwargs["frequency_penalty"] = 1.0
                kwargs["presence_penalty"] = 0.5
            chat = client.chat.create(**kwargs)
            chat.append(system(system_text))
            chat.append(xai_user(user_text))
            result = chat.sample()
            text = (result.content if hasattr(result, "content") else str(result)).strip()

        # Cleanup común a ambos paths
        if text.startswith('"') and text.endswith('"') and len(text) > 2:
            text = text[1:-1].strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
        return text if len(text) >= 30 else ""
    except Exception as e:
        _log.warning("summarizer call failed: %s", e)
        return ""


def _format_dialogue_for_summary(msgs: list[dict], max_chars_per_msg: int = 300) -> str:
    """Formato dialogue compacto para pasar al modelo como input."""
    lines: list[str] = []
    for m in msgs:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        prefix = "User" if role == "user" else "Ashley"
        snippet = content[:max_chars_per_msg]
        if len(content) > max_chars_per_msg:
            snippet += "..."
        lines.append(f"{prefix}: {snippet}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  API pública
# ─────────────────────────────────────────────

def compress_history(messages: list[dict], language: str) -> list[dict]:
    """Devuelve una versión (potencialmente) comprimida del historial.

    Si `len(messages) <= COMPRESSION_THRESHOLD` → se devuelve tal cual.
    Si excede el umbral → devuelve [resumen_como_system_msg, ...últimos KEEP_RECENT].

    El resumen se cachea en disco y se reutiliza hasta que han llegado
    ~REGEN_AFTER_NEW_MSGS nuevos mensajes por encima. Si la generación
    del resumen falla (API down, etc.), se devuelve el historial raw
    como fallback seguro.
    """
    n = len(messages)
    if n <= COMPRESSION_THRESHOLD:
        return messages

    older_end = n - KEEP_RECENT  # índice exclusivo (no incluido)
    if older_end <= 0:
        return messages

    older_slice = messages[:older_end]
    recent_slice = messages[older_end:]

    cached = _load_cache()
    covers_count = int(cached.get("covers_up_to_count") or 0)

    # Decidir si regeneramos
    needs_regen = (
        not cached.get("text")
        or covers_count < older_end - REGEN_AFTER_NEW_MSGS
        or covers_count > older_end  # historial se encogió (borrado) → invalidar
    )

    # v0.14.5: si el bg pre-warm ya está regenerando este caché, NO
    # disparamos un segundo LLM call. Usamos el caché actual aunque
    # sea stale; el bg termina y escribe a disco, y el siguiente
    # _stream_grok ya lee la versión fresca.
    if needs_regen and is_compress_regen_in_progress():
        if cached.get("text"):
            needs_regen = False  # usar caché stale, no doble-LLM
        # Si no hay caché en absoluto, dejamos que el path normal
        # caiga al fallback "return messages" — más seguro que un
        # resumen vacío.

    summary_text = cached.get("text", "")
    if needs_regen:
        dialogue = _format_dialogue_for_summary(older_slice)
        if not dialogue.strip():
            return messages  # nada que resumir, fallback a raw
        new_summary = _call_fast_summarizer(dialogue, language)
        if new_summary:
            summary_text = new_summary
            _save_cache({
                "text": summary_text,
                "covers_up_to_count": older_end,
                "generated_at": _dt.datetime.now().isoformat(),
            })
            _log.info("context summary regenerated, covers %d msgs", older_end)
        else:
            # Generación falló — mantenemos caché previo si hay, sino raw
            if not summary_text:
                _log.warning("summary generation failed and no cache — returning raw")
                return messages
            _log.warning("summary regen failed, reusing stale cache")

    # Construir el mensaje de resumen
    lang = (language or "en").strip().lower()[:2]
    if lang == "es":
        header = "[Resumen de la conversación anterior, para que mantengas contexto sin copiar frases literales]"
    elif lang == "fr":
        header = "[Résumé de la conversation précédente, pour garder le contexte sans copier des phrases littérales]"
    else:
        header = "[Summary of earlier conversation, for context without copying literal phrases]"

    summary_msg = {
        "role": "system_result",
        "content": f"{header}\n{summary_text}",
        "timestamp": cached.get("generated_at", ""),
        "id": "_ctx_summary",
        "image": "",
    }
    return [summary_msg] + recent_slice
