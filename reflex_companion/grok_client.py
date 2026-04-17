from typing import Iterator

from .config import GROK_MODEL, XAI_API_KEY


def grok_call(system_text: str, user_text: str) -> str:
    """Llamada simple a Grok, sin streaming."""
    from xai_sdk import Client
    from xai_sdk.chat import system, user as xai_user

    client = Client(api_key=XAI_API_KEY)
    chat = client.chat.create(model=GROK_MODEL)
    chat.append(system(system_text))
    chat.append(xai_user(user_text))
    result = chat.sample()
    return result.content if hasattr(result, "content") else str(result)


# Modelo rápido y barato para el detector de acciones (no necesita reasoning)
_FAST_MODEL = "grok-3-fast"

def detect_intended_action(user_message: str, ashley_response: str) -> str | None:
    """
    Llamada rápida (modelo fast, sin streaming) que analiza la respuesta de Ashley
    y determina si intentó realizar una acción del sistema.

    Devuelve el tag [action:...] si detecta intención de acción, None si no.
    Esta función es el fallback cuando Ashley no incluyó el tag por sí sola.
    """
    from xai_sdk import Client
    from xai_sdk.chat import system, user as xai_user

    system_text = """Eres un detector de intenciones de acciones del sistema.

Se te dará el mensaje del usuario y la respuesta de Ashley.
Tu tarea: si el usuario pidió una acción del sistema Y Ashley no generó el tag correcto,
devuelve el tag exacto. Si el usuario no pidió ninguna acción, devuelve NONE.

Tags disponibles:
[action:play_music:BUSQUEDA]         — poner/reproducir música en YouTube
[action:search_web:BUSQUEDA]         — buscar en Google
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
- Si el usuario NO pidió ninguna acción del sistema (solo preguntó o conversó): devuelve NONE.
- Devuelve ÚNICAMENTE el tag o NONE. Cero texto adicional.

Ejemplos:
Usuario: "pon shout de tears for fears"  →  [action:play_music:Shout Tears for Fears]
Usuario: "abre paint"                    →  [action:open_app:paint]
Usuario: "abre steam"                    →  [action:open_app:steam]
Usuario: "cierra youtube"                →  [action:close_tab:YouTube]
Usuario: "cierra la pestaña de google"   →  [action:close_tab:Google]
Usuario: "cierra discord"                →  [action:close_window:discord]
Usuario: "busca recetas de pasta"        →  [action:search_web:recetas de pasta]
Usuario: "cómo estás?"                   →  NONE
Usuario: "qué hora es?"                  →  NONE"""

    user_text = f"Mensaje del usuario: {user_message}\n\nRespuesta de Ashley: {ashley_response}"

    try:
        client = Client(api_key=XAI_API_KEY)
        chat = client.chat.create(model=_FAST_MODEL)
        chat.append(system(system_text))
        chat.append(xai_user(user_text))
        result = chat.sample()
        raw = (result.content if hasattr(result, "content") else str(result)).strip()
        if raw.startswith("[action:") and raw.endswith("]"):
            return raw
        return None
    except Exception:
        return None


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
    """
    from xai_sdk import Client
    from xai_sdk.chat import system, user as xai_user, assistant, image as xai_image
    from xai_sdk.tools import web_search

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
            # Resultado de una acción ejecutada — se presenta como mensaje de usuario
            result_text = f"[Sistema] {msg['content']}"
            if msg.get("image"):
                chat.append(xai_user(xai_image(msg["image"]), result_text))
            else:
                chat.append(xai_user(result_text))

    if trigger is not None:
        chat.append(xai_user(trigger))

    for _response, chunk in chat.stream():
        yield chunk.content  # string vacío durante razonamiento
