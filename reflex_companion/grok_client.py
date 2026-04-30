"""
grok_client.py — Cliente xAI Grok con retries automáticos.

Todas las llamadas a Grok pueden fallar por razones transitorias (timeout de
red, 502 temporal del balanceador de xAI, corte de Wi-Fi durante 2 seg).
Sin retries, el usuario ve un error al toque y la conversación se congela.

Este módulo implementa exponential backoff (3 intentos: 1s, 2s, 4s) en:
  - grok_call          → llamada simple con retry directo
  - detect_intended_action → idem
  - stream_response    → retry SOLO antes del primer chunk. Si ya hemos
                         emitido tokens a la UI, no podemos rebobinar
                         (el usuario ya los vio); en ese caso propagamos.
"""

import logging
import threading
import time
from typing import Iterator

from .config import GROK_MODEL, XAI_API_KEY


_log = logging.getLogger("ashley.grok")


# ─────────────────────────────────────────────
#  Cliente xAI cacheado a nivel módulo (v0.16.13)
# ─────────────────────────────────────────────
#
# Antes: cada llamada al LLM (stream_response, grok_call, detect_intended_action,
# regenerate_preoccupation, compress_history) instanciaba un Client(api_key=...)
# nuevo. Cada nuevo cliente abre una conexión HTTP/2 nueva → pago el handshake
# TCP+TLS completo (~300-600ms desde Europa a api.x.ai en US-East). En un
# mensaje normal con 3-4 llamadas LLM eso son ~1.2-2.4 SEGUNDOS de overhead
# de red puro.
#
# Solución: un solo Client compartido, instanciado lazy y reutilizado entre
# llamadas. El SDK de xAI mantiene un pool HTTP/2 internamente — solo si el
# Client persiste. Así el handshake se paga una sola vez al iniciar la sesión
# y los siguientes requests reutilizan la conexión abierta.
#
# Thread safety: el SDK xai_sdk es thread-safe (Cliente protegido por su
# propio lock interno; cada chat.create() devuelve un objeto chat
# independiente). Aún así envolvemos la creación en un lock para evitar
# que dos threads creen 2 clientes en paralelo durante el primer uso.
_xai_client = None
_xai_client_lock = threading.Lock()
_xai_client_api_key: str | None = None  # detectar cambio de api_key en runtime


def get_xai_client():
    """Devuelve el Client xAI compartido. Lo crea si no existe.

    Si la api_key cambia (user editó settings), invalida el cache y crea
    uno nuevo con la nueva key.

    Beneficio medido: ~300-600ms ahorrados por llamada subsiguiente
    (la primera paga el handshake, las demás reutilizan).
    """
    global _xai_client, _xai_client_api_key
    from xai_sdk import Client
    current_key = XAI_API_KEY
    with _xai_client_lock:
        if _xai_client is None or _xai_client_api_key != current_key:
            _xai_client = Client(api_key=current_key)
            _xai_client_api_key = current_key
        return _xai_client


def invalidate_xai_client() -> None:
    """Fuerza recreación del cliente xAI en la próxima llamada. Llamar si
    se sabe que la conexión está corrupta (errores repetidos de network)."""
    global _xai_client, _xai_client_api_key
    with _xai_client_lock:
        _xai_client = None
        _xai_client_api_key = None


# ─────────────────────────────────────────────
#  Sampling params por defecto
# ─────────────────────────────────────────────
#
# frequency_penalty y presence_penalty son el mecanismo estándar de la
# industria contra la repetición de tokens/temas. La API de xAI los
# acepta (son compatibles con la spec OpenAI).
#
#   frequency_penalty (0–2): penaliza tokens proporcionalmente a cuántas
#     veces aparecen en el contexto. Más alto = menos repetición literal.
#   presence_penalty  (0–2): penalización binaria si un token apareció.
#     Más alto = empuja a introducir conceptos nuevos.
#
# Valores conservadores recomendados por OpenAI: frequency 0.5, presence 0.3.
# Los usamos en llamadas conversacionales/creativas (stream_response,
# grok_call, y la preoccupation del mental_state). NO los usamos en
# detect_intended_action — esa función quiere tag determinista, sin
# variabilidad.
CHAT_FREQUENCY_PENALTY = 0.5
CHAT_PRESENCE_PENALTY = 0.3


def _model_supports_penalties(model_name: str) -> bool:
    """Modelos de xAI que NO aceptan frequency_penalty / presence_penalty.
    Si pasamos estos params a estos modelos → 400 INVALID_ARGUMENT.

    Basado en doc de xAI + errores empíricos observados:
      • Todos los *-reasoning (grok-4-1-fast-reasoning, grok-4.20-*-reasoning):
        reasoning mode no acepta penalties.
      • TODA la familia grok-4-1-fast (reasoning o non-reasoning):
        el 'fast' family de 4.1 elimina penalty support para optimizar
        latencia. Así lo confirmó el servidor con un 400 en runtime aun
        con la variante non-reasoning.

    Soportan (según testeo):
      • grok-3, grok-3-fast, grok-3-mini y sus -mini variants
      • grok-4 estándar (no fast)
      • grok-4.20-*-non-reasoning (probablemente — no testeado)

    Ante duda, preferimos falso (no enviar penalties) — un falso negativo
    solo nos cuesta un poco de diversidad léxica; un falso positivo
    rompe el request entero con un 400.
    """
    name = (model_name or "").lower()
    # Reasoning mode nunca soporta — ojo con "non-reasoning" que contiene "reasoning"
    if name.endswith("-reasoning") and not name.endswith("non-reasoning"):
        return False
    # La familia grok-4-1-fast rechaza penalties incluso en non-reasoning
    if name.startswith("grok-4-1-fast") or name.startswith("grok-4.1-fast"):
        return False
    return True


def _chat_create(client, **kwargs):
    """Wrapper sobre client.chat.create que añade los penalties de
    conversación por defecto — SOLO si el modelo los soporta. Si el
    modelo es tipo 'reasoning', se omiten silenciosamente.
    """
    model_name = kwargs.get("model") or ""
    if _model_supports_penalties(model_name):
        kwargs.setdefault("frequency_penalty", CHAT_FREQUENCY_PENALTY)
        kwargs.setdefault("presence_penalty", CHAT_PRESENCE_PENALTY)
    return client.chat.create(**kwargs)


# ─────────────────────────────────────────────
#  Retry helper
# ─────────────────────────────────────────────

# Errores que merecen retry. Si el mensaje de la excepción contiene
# cualquiera de estos substrings, reintentamos con backoff.
_RETRYABLE_SIGNALS = (
    "timeout", "timed out", "connection reset", "connection aborted",
    "502", "503", "504", "temporarily unavailable", "try again",
    "econnreset", "socket hang up", "network is unreachable",
)

# Errores donde NO tiene sentido retryar — devolvemos al toque.
# 401/403 = API key mala. 400 = request mal formado. 404 = endpoint no existe.
_NON_RETRYABLE_SIGNALS = (
    "401", "403", "invalid api key", "unauthorized", "forbidden",
    "400", "bad request",
)


def _is_retryable(err: Exception) -> bool:
    msg = str(err).lower()
    if any(sig in msg for sig in _NON_RETRYABLE_SIGNALS):
        return False
    if any(sig in msg for sig in _RETRYABLE_SIGNALS):
        return True
    # Por defecto asumimos transitorio para errores desconocidos (genéricos
    # de red). Mejor reintentar y que fallen los 3 que bloquear en el 1º.
    return True


def _with_retry(fn, *args, max_attempts: int = 3, base_delay: float = 1.0, **kwargs):
    """Llama a fn() con retries; backoff exponencial 1s → 2s → 4s."""
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if attempt == max_attempts or not _is_retryable(e):
                _log.warning(
                    "grok call failed (attempt %d/%d, retryable=%s): %s",
                    attempt, max_attempts, _is_retryable(e), e,
                )
                raise
            delay = base_delay * (2 ** (attempt - 1))
            _log.warning(
                "grok transient error (attempt %d/%d), retry in %.1fs: %s",
                attempt, max_attempts, delay, e,
            )
            time.sleep(delay)
    # No debería llegar aquí pero por si acaso.
    if last_err:
        raise last_err


# ─────────────────────────────────────────────
#  Llamada simple (sin streaming)
# ─────────────────────────────────────────────

def grok_call(system_text: str, user_text: str) -> str:
    """Llamada simple al LLM activo, sin streaming. Con retries automáticos.
    Dispatcha a xAI directo, OpenRouter u Ollama según la config del user.
    Nombre 'grok_call' se mantiene por backward compat histórica."""
    from .llm_provider import is_openai_compat, openai_compat_simple

    def _once():
        if is_openai_compat():
            return openai_compat_simple(system_text, user_text, creative=True)
        # Path xAI directo (legacy) — cliente cacheado para reusar conexión.
        from xai_sdk.chat import system, user as xai_user
        client = get_xai_client()
        chat = _chat_create(client, model=GROK_MODEL)
        chat.append(system(system_text))
        chat.append(xai_user(user_text))
        result = chat.sample()
        return result.content if hasattr(result, "content") else str(result)

    return _with_retry(_once)


# Modelo rápido y barato para el detector de acciones (no necesita reasoning)
_FAST_MODEL = "grok-3-fast"


def detect_intended_action(user_message: str, ashley_response: str) -> str | None:
    """
    Llamada rápida (modelo fast, sin streaming) que analiza la respuesta de Ashley
    y determina si intentó realizar una acción del sistema.

    Devuelve el tag [action:...] si detecta intención de acción, None si no.
    Esta función es el fallback cuando Ashley no incluyó el tag por sí sola.

    Con retries: si la llamada falla transitoriamente no rompemos el flujo
    del usuario — simplemente devolvemos None (no hay fallback action).
    """
    from xai_sdk.chat import system, user as xai_user

    system_text = """Eres un detector de intenciones de acciones del sistema.

Se te dará el mensaje del usuario y la respuesta de Ashley.
Tu tarea: si el usuario pidió una acción del sistema Y Ashley no generó el tag correcto,
devuelve el tag exacto. Si el usuario no pidió ninguna acción, devuelve NONE.

Tags disponibles:
[action:play_music:BUSQUEDA]         — poner/reproducir música en YouTube
[action:search_web:BUSQUEDA]         — ABRIR una pestaña del NAVEGADOR en Google con la búsqueda. SOLO si el usuario pidió explícitamente abrir el navegador/Google ("abre Google con X", "muéstrame los resultados", "abre una pestaña buscando Y"). NUNCA para un simple "busca X" o "dime sobre X" — para eso Ashley tiene búsqueda interna y debe responder en el chat.
[action:open_url:URL]                — abrir una URL
[action:open_app:NOMBRE]             — abrir una aplicación o programa
[action:close_window:HINT]           — cerrar una ventana o aplicación (HINT = fragmento del título)
[action:close_tab:HINT]              — cerrar una pestaña del navegador (HINT = fragmento del título)
[action:screenshot]                  — captura de pantalla
[action:volume:up]                   — subir volumen
[action:volume:down]                 — bajar volumen
[action:volume:mute]                 — silenciar/activar audio
[action:volume:set:N]                — volumen a N%
[action:type_text:TEXTO]             — escribir texto
[action:focus_window:TITULO]         — enfocar/traer al frente una ventana
[action:hotkey:TECLA1:TECLA2]        — atajo de teclado
[action:press_key:TECLA]             — tecla suelta

Reglas estrictas:
- Analiza el mensaje del USUARIO para determinar qué acción pidió.
- Para play_music: extrae el nombre de la canción/artista del mensaje del usuario.
- Para open_app: usa el nombre exacto de la app que pidió el usuario.
- Para close_tab/close_window: usa el nombre/fragmento más específico posible del mensaje del usuario.
- Para search_web: SOLO dispararlo si el usuario dijo ABRIR Google/navegador/pestaña explícitamente. "Busca X" NO es search_web — es una petición de información que Ashley resuelve con su búsqueda interna sin tag.
- Si el usuario NO pidió ninguna acción del sistema (solo preguntó o conversó o pidió información): devuelve NONE.
- Devuelve ÚNICAMENTE el tag o NONE. Cero texto adicional.

Ejemplos:
Usuario: "pon shout de tears for fears"  →  [action:play_music:Shout Tears for Fears]
Usuario: "abre paint"                    →  [action:open_app:paint]
Usuario: "abre steam"                    →  [action:open_app:steam]
Usuario: "cierra youtube"                →  [action:close_tab:YouTube]
Usuario: "cierra la pestaña de google"   →  [action:close_tab:Google]
Usuario: "cierra discord"                →  [action:close_window:discord]
Usuario: "busca recetas de pasta"        →  NONE  (pide info — Ashley responde con búsqueda interna, sin tag)
Usuario: "dime qué hay nuevo de RimWorld" →  NONE  (pide info en chat)
Usuario: "¿sabes algo de la película X?" →  NONE  (pide info en chat)
Usuario: "abre Google y busca recetas"   →  [action:search_web:recetas de pasta]
Usuario: "llévame a Google con X"        →  [action:search_web:X]
Usuario: "abre una pestaña buscando Y"   →  [action:search_web:Y]
Usuario: "muéstrame los resultados de Z" →  [action:search_web:Z]
Usuario: "cómo estás?"                   →  NONE
Usuario: "qué hora es?"                  →  NONE"""

    user_text = f"Mensaje del usuario: {user_message}\n\nRespuesta de Ashley: {ashley_response}"

    def _once():
        from .llm_provider import is_openai_compat, openai_compat_complete
        if is_openai_compat():
            # En OpenRouter/Ollama siempre usamos el MISMO modelo del user
            # (no un modelo 'fast' separado). Queremos output determinista
            # para detectar tags, sin penalties.
            raw = openai_compat_complete(
                messages=[{"role": "user", "content": user_text, "image": ""}],
                system_prompt=system_text,
                creative=False,
            ).strip()
        else:
            client = get_xai_client()
            chat = client.chat.create(model=_FAST_MODEL)
            chat.append(system(system_text))
            chat.append(xai_user(user_text))
            result = chat.sample()
            raw = (result.content if hasattr(result, "content") else str(result)).strip()
        if raw.startswith("[action:") and raw.endswith("]"):
            return raw
        return None

    try:
        return _with_retry(_once)
    except Exception:
        # Esta función es fallback — si aun con 3 retries no funciona,
        # seguimos sin acción detectada, sin romper el flujo del usuario.
        return None


# ─────────────────────────────────────────────
#  Normalización del historial
# ─────────────────────────────────────────────

def _merge_consecutive_users(messages: list[dict]) -> list[dict]:
    """Fusiona mensajes USER consecutivos en uno solo antes de pasarlos al LLM.

    Cuándo pasa esto:
      • El user borra la última respuesta de Ashley → el último mensaje
        del historial es del user → escribe algo nuevo → ahora hay dos
        user messages consecutivos en el historial.
      • xAI y algunos modelos de OpenRouter rechazan este patrón con un
        400 "consecutive user turns". Antes del fix, este caso disparaba
        un error toast al user.

    Qué hace el merge:
      • Combina los content de los user consecutivos con un separador.
      • NO fusiona si alguno tenía image adjunta — mantener imagen
        requiere dejar los mensajes separados (los content-parts de
        vision no se concatenan limpiamente).
      • system_result + user se mantienen como están — eso ES válido.

    La UI sigue viendo los mensajes separados (esta función trabaja
    sobre una copia del historial que solo se pasa al LLM).
    """
    out: list[dict] = []
    for m in messages:
        if (
            out
            and m.get("role") == "user"
            and out[-1].get("role") == "user"
            and not out[-1].get("image")
            and not m.get("image")
        ):
            prev = out[-1]
            prev_content = prev.get("content") or ""
            new_content = m.get("content") or ""
            merged_content = (prev_content + "\n\n" + new_content).strip()
            out[-1] = {**prev, "content": merged_content}
        else:
            out.append(m)
    return out


# ─────────────────────────────────────────────
#  Streaming con retry antes del primer chunk
# ─────────────────────────────────────────────

def stream_response(
    messages: list[dict],
    system_prompt: str,
    use_web_search: bool = False,
    trigger: str | None = None,
    fast_mode: bool = False,
) -> Iterator[str]:
    """
    Genera chunks de texto de la respuesta de Grok.
    Devuelve strings vacíos durante la fase de razonamiento.

    - messages:       historial (ya incluye el último mensaje del usuario)
    - use_web_search: activa la búsqueda web via Agent Tools API
    - trigger:        mensaje de usuario artificial (útil en initiative)
    - fast_mode:      si True, fuerza el modelo non-reasoning incluso si el
                      user tiene reasoning configurado. Para follow-ups
                      automáticos (continuation, apology) donde Ashley ya
                      tiene plan claro y reasoning añade ~3s de TTFT
                      innecesario. Solo aplica al path xAI directo.

    Retries: si la conexión inicial falla (antes del primer chunk), hasta
    3 intentos con 1s/2s/4s. Si falla mid-stream (ya emitimos tokens),
    propagamos la excepción — no podemos rebobinar tokens que ya vio el
    user en la UI.
    """
    from .llm_provider import is_openai_compat, openai_compat_stream

    # Normalizar historial: fusionar user-user consecutivos (pasa cuando
    # el user borra la última respuesta de Ashley y escribe otra cosa).
    messages = _merge_consecutive_users(messages)

    # Si el user usa OpenRouter/Ollama → path OpenAI-compatible. Sin
    # web_search (no soportado en ese path) y sin el formato xai_sdk.
    # Nota sobre fast_mode: solo aplica al path xAI (donde sabemos que
    # existe grok-4-1-fast-non-reasoning como alternativa rápida). En
    # OR/Ollama mantenemos el modelo que el user eligió — no podemos
    # asumir cuál sería el equivalente "fast" del modelo configurado
    # (Claude Sonnet/Haiku, Gemini Flash/Pro, Llama X/Y, etc.). El cap
    # de 1 follow-up sigue ayudando ahí. Si el provider soporta prompt
    # caching automático (xAI/OpenRouter sí), el system prompt repetido
    # en el follow-up se sirve cacheado y baja el TTFT también.
    if is_openai_compat():
        # Retry de apertura manejado implícitamente por openai_compat_stream
        # (aunque si falla mid-stream también propaga, igual que xAI).
        try:
            yield from openai_compat_stream(messages, system_prompt, trigger=trigger)
        except Exception as e:
            _log.warning("openai_compat_stream failed, propagating: %s", e)
            raise
        return

    # Path xAI directo (legacy) — usa cliente cacheado.
    from xai_sdk.chat import system, user as xai_user, assistant, image as xai_image
    from xai_sdk.tools import web_search

    # fast_mode: para follow-ups internos (continuation, apology) usamos
    # non-reasoning. Benchmark live (2026-04): TTFT reasoning ~3.4s vs
    # non-reasoning ~0.6s = ahorro de ~2.8s por follow-up. El user ve
    # el chat principal con su modelo elegido (fast_mode=False); solo
    # los turns automáticos invisibles usan el modelo rápido.
    _model_to_use = (
        "grok-4-1-fast-non-reasoning" if fast_mode else GROK_MODEL
    )

    def _open_stream():
        """Prepara el chat y devuelve el iterador de chunks de Grok."""
        tools = [web_search()] if use_web_search else []
        client = get_xai_client()
        chat = _chat_create(
            client,
            model=_model_to_use,
            tools=tools if tools else None,
        )
        chat.append(system(system_prompt))
        for msg in messages:
            if msg["role"] == "user":
                if msg.get("image"):
                    chat.append(xai_user(xai_image(msg["image"]), msg["content"]))
                else:
                    chat.append(xai_user(msg["content"]))
            elif msg["role"] == "assistant":
                chat.append(assistant(msg["content"]))
            elif msg["role"] == "system_result":
                result_text = f"[Sistema] {msg['content']}"
                if msg.get("image"):
                    chat.append(xai_user(xai_image(msg["image"]), result_text))
                else:
                    chat.append(xai_user(result_text))
        if trigger is not None:
            chat.append(xai_user(trigger))
        return chat.stream()

    # Retry sólo la apertura del stream — una vez empezado, no rebobinamos.
    stream = _with_retry(_open_stream)
    for _response, chunk in stream:
        yield chunk.content  # string vacío durante razonamiento
