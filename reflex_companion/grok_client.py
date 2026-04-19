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
import time
from typing import Iterator

from .config import GROK_MODEL, XAI_API_KEY


_log = logging.getLogger("ashley.grok")


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
    """Llamada simple a Grok, sin streaming. Con retries automáticos."""
    from xai_sdk import Client
    from xai_sdk.chat import system, user as xai_user

    def _once():
        client = Client(api_key=XAI_API_KEY)
        chat = client.chat.create(model=GROK_MODEL)
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
    from xai_sdk import Client
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
        client = Client(api_key=XAI_API_KEY)
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
#  Streaming con retry antes del primer chunk
# ─────────────────────────────────────────────

def stream_response(
    messages: list[dict],
    system_prompt: str,
    use_web_search: bool = False,
    trigger: str | None = None,
) -> Iterator[str]:
    """
    Genera chunks de texto de la respuesta de Grok.
    Devuelve strings vacíos durante la fase de razonamiento.

    - messages:       historial (ya incluye el último mensaje del usuario)
    - use_web_search: activa la búsqueda web via Agent Tools API
    - trigger:        mensaje de usuario artificial (útil en initiative)

    Retries: si la conexión inicial falla (antes del primer chunk), hasta
    3 intentos con 1s/2s/4s. Si falla mid-stream (ya emitimos tokens),
    propagamos la excepción — no podemos rebobinar tokens que ya vio el
    user en la UI.
    """
    from xai_sdk import Client
    from xai_sdk.chat import system, user as xai_user, assistant, image as xai_image
    from xai_sdk.tools import web_search

    def _open_stream():
        """Prepara el chat y devuelve el iterador de chunks de Grok."""
        tools = [web_search()] if use_web_search else []
        client = Client(api_key=XAI_API_KEY)
        chat = client.chat.create(model=GROK_MODEL, tools=tools if tools else None)
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
