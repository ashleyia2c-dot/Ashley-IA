"""
llm_provider.py — Abstracción multi-provider para el cliente LLM.

Ashley soporta dos proveedores:
  • xAI directo (legacy) — usa xai_sdk, soporta web_search, es lo que los
    users actuales tienen configurado desde el instalador original.
  • OpenRouter (nuevo, recomendado) — un endpoint OpenAI-compatible que
    desbloquea 300+ modelos con UNA sola API key (Claude, GPT, DeepSeek,
    Gemini, MiniMax, y también Grok). Permite al user elegir el modelo
    que encaje con su presupuesto / gusto sin cambiar de app.

El resto del código (grok_client.py, mental_state, context_compression)
usa la API pública de este módulo sin saber qué proveedor está debajo.
Así cambiar de provider es un setting del user, no un refactor.

Web search: solo xAI lo soporta nativamente en el SDK actual. Si el user
elige OpenRouter + un modelo no-Grok, web_search se desactiva
silenciosamente. Aceptable trade-off — el user eligió ganar opciones a
cambio de esta feature.
"""

import logging
from typing import Iterator, Any

from .config import XAI_API_KEY, GROK_MODEL


_log = logging.getLogger("ashley.llm_provider")


# Modelos recomendados para cada proveedor en el dropdown de settings.
# El formato es (model_id, human_label, notes).
XAI_MODELS = [
    ("grok-4-1-fast-reasoning", "Grok 4.1 Fast Reasoning (default)", "Tu modelo actual"),
    ("grok-4-1-fast-non-reasoning", "Grok 4.1 Fast", "Sin reasoning, más rápido"),
    ("grok-3-fast", "Grok 3 Fast", "Gen anterior, barato"),
]

OPENROUTER_MODELS = [
    ("anthropic/claude-sonnet-4.6", "Claude Sonnet 4.6 (premium)", "$$$ mejor carácter"),
    ("anthropic/claude-haiku-4.5", "Claude Haiku 4.5", "$$ Claude más barato"),
    ("deepseek/deepseek-chat", "DeepSeek V3.2", "$ barato, calidad decente"),
    ("google/gemini-2.5-flash", "Gemini 2.5 Flash", "$$ contexto gigante"),
    ("x-ai/grok-4.1-fast", "Grok 4.1 Fast (vía OR)", "$ mismo que xAI directo"),
    ("openai/gpt-5", "GPT-5", "$$$ alternativa premium"),
    ("minimax/minimax-m2", "MiniMax M2 Her", "$$ purpose-built companion"),
]


# ─────────────────────────────────────────────
#  Resolución de configuración activa
# ─────────────────────────────────────────────

def get_active_config() -> dict[str, str]:
    """Lee voice.json y devuelve el dict de configuración LLM activa.

    Keys devueltas:
      - provider: "xai" | "openrouter"
      - api_key: la key correspondiente al provider activo
      - model: el model ID a usar (default si vacío)
      - base_url: URL del endpoint (solo relevante para OpenRouter)
    """
    try:
        from .i18n import load_voice_config
        cfg = load_voice_config()
    except Exception:
        cfg = {}

    provider = cfg.get("llm_provider") or "xai"
    user_model = (cfg.get("llm_model") or "").strip()

    if provider == "openrouter":
        api_key = cfg.get("openrouter_key") or ""
        model = user_model or OPENROUTER_MODELS[0][0]
        base_url = "https://openrouter.ai/api/v1"
    else:
        # default xAI
        api_key = XAI_API_KEY
        model = user_model or GROK_MODEL
        base_url = ""  # xAI usa su SDK nativo

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


# ─────────────────────────────────────────────
#  Dispatch de llamadas
# ─────────────────────────────────────────────
#
# Las funciones públicas mantienen la misma firma que antes (para
# backward compat con el código que las llama), pero internamente
# eligen el backend según el provider activo.

def is_xai() -> bool:
    return get_active_config()["provider"] == "xai"


def is_openrouter() -> bool:
    return get_active_config()["provider"] == "openrouter"


def supports_web_search() -> bool:
    """Solo xAI tiene tool web_search integrado en el SDK actual."""
    return is_xai()


# ─────────────────────────────────────────────
#  OpenRouter / OpenAI-compatible path
# ─────────────────────────────────────────────

def _openai_client():
    """Crea un cliente OpenAI-compatible apuntando al base_url configurado."""
    from openai import OpenAI
    cfg = get_active_config()
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"] or None)


def _convert_messages_for_openai(messages: list[dict]) -> list[dict]:
    """Convierte el formato interno de messages al formato OpenAI.

    Ashley internamente usa:
      - role: "user" | "assistant" | "system_result"
      - content: str
      - image: str (base64 data URL) opcional

    OpenAI usa:
      - role: "system" | "user" | "assistant"
      - content: str o lista de content parts (para vision)

    Convertimos system_result → user con prefijo [Sistema], igual que
    xAI hace internamente.
    """
    out: list[dict] = []
    for m in messages:
        role_raw = m.get("role", "user")
        content = m.get("content") or ""
        image = m.get("image") or ""

        if role_raw == "system_result":
            role = "user"
            content = f"[Sistema] {content}"
        elif role_raw == "assistant":
            role = "assistant"
        else:
            role = "user"

        if image:
            # Content parts con vision
            parts: list[dict] = [{"type": "text", "text": content}]
            # Asumimos que image es data URL base64 (así la guardamos)
            parts.append({"type": "image_url", "image_url": {"url": image}})
            out.append({"role": role, "content": parts})
        else:
            out.append({"role": role, "content": content})
    return out


def _openrouter_supports_penalties(model_name: str) -> bool:
    """Casi todos los modelos en OpenRouter aceptan los penalties, pero
    algunos (los Grok reasoning y algunos Claude en modo extended thinking)
    no. Por seguridad: reglas conservadoras.

    Como regla general, damos True excepto para los que sabemos que no.
    """
    name = (model_name or "").lower()
    # Grok fast reasoning sigue sin soportar aunque pase por OpenRouter
    if "grok" in name and "reasoning" in name and "non-reasoning" not in name:
        return False
    # Grok 4.1 fast family: OpenRouter routes directly to xAI — mismos límites
    if "grok-4.1-fast" in name or "grok-4-1-fast" in name:
        return False
    return True


def _build_sampling_kwargs(model_name: str, *, creative: bool = True) -> dict:
    """Genera los kwargs de sampling para las llamadas.

    creative=True → aplica penalties moderados contra repetición.
    creative=False → deja sampling default (para tareas deterministas
    como detect_action).
    """
    if not creative:
        return {}
    if _openrouter_supports_penalties(model_name):
        return {"frequency_penalty": 0.5, "presence_penalty": 0.3}
    return {}


def openrouter_stream(
    messages: list[dict],
    system_prompt: str,
    trigger: str | None = None,
) -> Iterator[str]:
    """Streaming de respuesta vía OpenAI-compatible endpoint (OpenRouter)."""
    client = _openai_client()
    cfg = get_active_config()
    model = cfg["model"]

    chat_messages = [{"role": "system", "content": system_prompt}]
    chat_messages.extend(_convert_messages_for_openai(messages))
    if trigger is not None:
        chat_messages.append({"role": "user", "content": trigger})

    sampling = _build_sampling_kwargs(model, creative=True)
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            stream=True,
            **sampling,
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            except (AttributeError, IndexError):
                continue
    except Exception as e:
        _log.warning("openrouter_stream failed: %s", e)
        raise


def openrouter_complete(
    messages: list[dict],
    system_prompt: str | None = None,
    *,
    creative: bool = True,
    model_override: str | None = None,
) -> str:
    """Llamada non-streaming (para critic, compression, mental_state, etc.)."""
    client = _openai_client()
    cfg = get_active_config()
    model = model_override or cfg["model"]

    chat_messages: list[dict] = []
    if system_prompt:
        chat_messages.append({"role": "system", "content": system_prompt})
    chat_messages.extend(_convert_messages_for_openai(messages))

    sampling = _build_sampling_kwargs(model, creative=creative)
    resp = client.chat.completions.create(
        model=model,
        messages=chat_messages,
        **sampling,
    )
    try:
        return resp.choices[0].message.content or ""
    except (AttributeError, IndexError):
        return ""


def openrouter_simple(system_text: str, user_text: str, *, creative: bool = True) -> str:
    """Wrapper para llamadas tipo system+user único."""
    return openrouter_complete(
        messages=[{"role": "user", "content": user_text, "image": ""}],
        system_prompt=system_text,
        creative=creative,
    )
