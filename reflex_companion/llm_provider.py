"""
llm_provider.py — Abstracción multi-provider para el cliente LLM.

Ashley soporta TRES proveedores:
  • xAI directo (legacy) — usa xai_sdk, soporta web_search, es lo que los
    users actuales tienen configurado desde el instalador original.
  • OpenRouter (recomendado para premium) — endpoint OpenAI-compatible
    que desbloquea 300+ modelos con UNA sola API key (Claude, GPT,
    DeepSeek, Gemini, MiniMax, Grok).
  • Ollama (100% gratis, local) — el user instala Ollama en su PC desde
    ollama.com, baja el modelo que quiera (llama3, mistral, qwen,
    gemma...), y Ashley habla con él en localhost:11434 vía la API
    OpenAI-compat nativa de Ollama. Sin API key, sin internet, sin coste.

El resto del código (grok_client.py, mental_state, context_compression)
usa la API pública de este módulo sin saber qué proveedor está debajo.
Así cambiar de provider es un setting del user, no un refactor.

Web search: solo xAI lo soporta nativamente en el SDK actual. Si el user
elige OpenRouter o Ollama, web_search se desactiva silenciosamente.
Aceptable trade-off — el user eligió ganar opciones a cambio de esta
feature.

OpenAI-compat: OpenRouter y Ollama comparten el mismo path interno
(`_openai_compat_*`). La diferencia es sólo la URL base y la presencia
o no de API key. Esto mantiene el código simple: un solo cliente
para ambos, distinta config.
"""

import logging
from typing import Iterator

from .config import XAI_API_KEY, GROK_MODEL


_log = logging.getLogger("ashley.llm_provider")


# ─────────────────────────────────────────────
#  Endpoints y defaults
# ─────────────────────────────────────────────

OLLAMA_BASE_URL = "http://localhost:11434/v1"   # OpenAI-compat endpoint
OLLAMA_API_URL = "http://localhost:11434"       # Endpoint nativo (/api/tags)
OLLAMA_DEFAULT_MODEL = "llama3.2"               # fallback si el user no elige


# Modelos recomendados para cada proveedor en el dropdown de settings.
# El formato es (model_id, human_label, notes).
XAI_MODELS = [
    ("grok-4-1-fast-reasoning", "Grok 4.1 Fast Reasoning", "Más elaborado, ~3.5s extra de TTFT"),
    ("grok-4-1-fast-non-reasoning", "Grok 4.1 Fast (default)", "Sin reasoning, ~0.6s TTFT"),
    ("grok-3-fast", "Grok 3 Fast", "Gen anterior, 25x más caro"),
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

# Modelos populares de Ollama como sugerencia. La lista REAL se obtiene de
# /api/tags (los que el user tenga bajados). Esto es sólo un fallback
# cuando Ollama no responde (para que el dropdown no esté vacío).
OLLAMA_SUGGESTED_MODELS = [
    ("llama3.2", "Llama 3.2 (3B) — rápido, calidad decente", "Default recomendado"),
    ("llama3.1:8b", "Llama 3.1 8B — calidad alta", "Más lento, mejor respuesta"),
    ("qwen2.5:7b", "Qwen 2.5 7B — multilingüe fuerte", "Bueno para ES/FR"),
    ("mistral", "Mistral 7B", "Gen anterior sólida"),
    ("gemma2:9b", "Gemma 2 9B (Google)", "Alternativa a Llama"),
]


# ─────────────────────────────────────────────
#  Capabilities por modelo (v0.19.51)
# ─────────────────────────────────────────────
#
# Tabla declarativa de qué soporta cada modelo. Usado por la UI de
# Settings para mostrar al user QUÉ pierde/gana al elegir cada uno.
# Sin esto, el user activaba Vision con un modelo text-only y la app
# tiraba HTTP 400 silencioso o respuestas que ignoraban la imagen.
#
# Categorías:
#   - vision:      acepta image content parts (screenshot adjunto)
#   - web_search:  tool nativo de búsqueda web (solo xAI SDK)
#   - actions:     fiabilidad para emitir [action:...] tags y JSON
#                  estricto (compress, mental_state, extract_facts).
#                  "high"=modelo grande que sigue protocolo ✓
#                  "low" =modelo pequeño que puede ignorar/romper tags
#   - quality:     calidad subjetiva como companion ("excellent",
#                  "good", "ok", "basic"). Usado en el banner UI.
#
# Si un modelo no está en este dict, asumimos defaults conservadores:
# vision=False, web_search=False, actions="low", quality="basic".

_MODEL_CAPABILITIES = {
    # ── xAI ──
    "grok-4-1-fast-reasoning": {
        "vision": True, "web_search": True, "actions": "high",
        "quality": "excellent",
    },
    "grok-4-1-fast-non-reasoning": {
        "vision": True, "web_search": True, "actions": "high",
        "quality": "excellent",
    },
    "grok-3-fast": {
        "vision": True, "web_search": True, "actions": "high",
        "quality": "good",
    },
    # ── OpenRouter ──
    "anthropic/claude-sonnet-4.6": {
        "vision": True, "web_search": False, "actions": "high",
        "quality": "excellent",
    },
    "anthropic/claude-haiku-4.5": {
        "vision": True, "web_search": False, "actions": "high",
        "quality": "good",
    },
    "deepseek/deepseek-chat": {
        "vision": False, "web_search": False, "actions": "high",
        "quality": "good",
    },
    "google/gemini-2.5-flash": {
        "vision": True, "web_search": False, "actions": "high",
        "quality": "good",
    },
    "x-ai/grok-4.1-fast": {
        "vision": True, "web_search": False, "actions": "high",
        "quality": "excellent",
    },
    "openai/gpt-5": {
        "vision": True, "web_search": False, "actions": "high",
        "quality": "excellent",
    },
    "minimax/minimax-m2": {
        "vision": False, "web_search": False, "actions": "high",
        "quality": "good",
    },
    # ── Ollama (sugeridos) ──
    "llama3.2": {
        "vision": False, "web_search": False, "actions": "low",
        "quality": "basic",
    },
    "llama3.1:8b": {
        "vision": False, "web_search": False, "actions": "ok",
        "quality": "ok",
    },
    "qwen2.5:7b": {
        "vision": False, "web_search": False, "actions": "ok",
        "quality": "ok",
    },
    "mistral": {
        "vision": False, "web_search": False, "actions": "low",
        "quality": "basic",
    },
    "gemma2:9b": {
        "vision": False, "web_search": False, "actions": "ok",
        "quality": "ok",
    },
    # Modelos Ollama vision (no en sugerencias pero el user puede bajarlos)
    "llava": {
        "vision": True, "web_search": False, "actions": "low",
        "quality": "basic",
    },
    "llama3.2-vision": {
        "vision": True, "web_search": False, "actions": "ok",
        "quality": "ok",
    },
}


def get_model_capabilities(model_id: str) -> dict:
    """Devuelve dict de capabilities para un model_id. Defaults conservadores
    si el modelo no está en la tabla (ej. modelos Ollama que el user bajó
    pero no son los sugeridos).

    Para modelos Ollama unknown, hacemos best-guess por nombre:
      - Si contiene "vision" o "vl" o "llava" → vision=True
      - Si parece un modelo grande (13b+/70b+) → actions=ok+
      - Sino: defaults conservadores.
    """
    if model_id in _MODEL_CAPABILITIES:
        return dict(_MODEL_CAPABILITIES[model_id])

    # Heuristics para Ollama models no listados
    name = model_id.lower()
    vision = any(kw in name for kw in ("vision", "vl", "llava", "bakllava"))

    # Estimación de tamaño por nombre — modelos grandes suelen seguir
    # mejor los tags. Esto NO garantiza nada, solo evita banner pesimista
    # innecesariamente.
    # Cubre :Nb (Ollama tags) y -Nb (Hugging Face naming).
    actions_level = "low"
    quality = "basic"
    for big_indicator in (":13b", ":34b", ":70b", "-13b", "-34b", "-70b", "-large"):
        if big_indicator in name:
            actions_level = "high"
            quality = "good"
            break
    else:
        for med_indicator in (":7b", ":8b", ":9b", "-7b", "-8b", "-9b"):
            if med_indicator in name:
                actions_level = "ok"
                quality = "ok"
                break

    return {
        "vision": vision,
        "web_search": False,
        "actions": actions_level,
        "quality": quality,
    }


# ─────────────────────────────────────────────
#  Resolución de configuración activa
# ─────────────────────────────────────────────

def get_active_config() -> dict[str, str]:
    """Lee voice.json y devuelve el dict de configuración LLM activa.

    Keys devueltas:
      - provider: "xai" | "openrouter" | "ollama"
      - api_key: la key correspondiente al provider activo (dummy para ollama)
      - model: el model ID a usar (default si vacío)
      - base_url: URL del endpoint (solo relevante para OpenAI-compat paths)

    v0.19.51 — Validación de credenciales: si el user seleccionó OpenRouter
    PERO no proporcionó la api_key, hacemos fallback transparente a xAI
    (con XAI_API_KEY del env) y logueamos warning. Sino, el primer LLM call
    crasheaba con `OpenAIError: Missing credentials` y rompía on_load
    completamente — la app entera no funcionaba hasta que el user supiera
    abrir Settings y completar la key (que a menudo no es obvio si llegó
    aquí por accidente cambiando el dropdown).
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
        # v0.19.51 — fallback a xAI si no hay key OpenRouter
        if not api_key:
            _log.warning(
                "Provider=openrouter pero openrouter_key vacía — "
                "fallback transparente a xAI (XAI_API_KEY del env). "
                "El user debe completar la key en Settings."
            )
            provider = "xai"
            api_key = XAI_API_KEY
            # Si user_model parece de OpenRouter (tiene "/"), descartamos
            # y usamos default xAI para que la llamada no falle por
            # model no-existente en xAI.
            if "/" in user_model:
                user_model = ""
        else:
            model = user_model or OPENROUTER_MODELS[0][0]
            base_url = "https://openrouter.ai/api/v1"
            return {
                "provider": provider,
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
            }
    elif provider == "ollama":
        # Ollama no usa API key real — pero el OpenAI SDK requiere algo no-vacío
        # para inicializar el cliente, así que le pasamos "ollama" como dummy.
        api_key = "ollama"
        model = user_model or OLLAMA_DEFAULT_MODEL
        base_url = OLLAMA_BASE_URL
        return {
            "provider": provider,
            "api_key": api_key,
            "model": model,
            "base_url": base_url,
        }

    # default xAI (también cuando hicimos fallback desde openrouter sin key)
    api_key = XAI_API_KEY
    model = user_model or GROK_MODEL
    base_url = ""  # xAI usa su SDK nativo
    return {
        "provider": "xai",
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


# ─────────────────────────────────────────────
#  Flags de provider
# ─────────────────────────────────────────────

def is_xai() -> bool:
    return get_active_config()["provider"] == "xai"


def is_openrouter() -> bool:
    return get_active_config()["provider"] == "openrouter"


def is_ollama() -> bool:
    return get_active_config()["provider"] == "ollama"


def is_openai_compat() -> bool:
    """True si el provider usa un endpoint OpenAI-compatible (OpenRouter o Ollama).
    Ambos se sirven con el mismo código interno — sólo cambia base_url."""
    return is_openrouter() or is_ollama()


def supports_web_search() -> bool:
    """Solo xAI tiene tool web_search integrado en el SDK actual."""
    return is_xai()


# ─────────────────────────────────────────────
#  Ollama helpers: detección y listado de modelos locales
# ─────────────────────────────────────────────

def is_ollama_available(timeout: float = 1.0) -> bool:
    """Ping rápido a Ollama para ver si está corriendo en localhost:11434.

    Usado desde la UI de Settings para mostrar 'Ollama detectado ✓' o un
    link a ollama.com. No cachea — la UI refresca cuando abren Settings
    (Ollama puede arrancar/cerrar sin que Ashley se entere).
    """
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(f"{OLLAMA_API_URL}/api/version")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def list_ollama_models() -> list[str]:
    """Lista los modelos locales que el user tiene descargados con Ollama.

    Formato devuelto: ["llama3.2:latest", "qwen2.5:7b", ...] — strings
    listos para pasar como model_id al API.

    Si Ollama no está corriendo, devuelve []. El UI en ese caso muestra
    un estado 'no detectado' con instrucciones de instalación.
    """
    import urllib.request
    import json as _json
    try:
        req = urllib.request.Request(f"{OLLAMA_API_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as r:
            data = _json.loads(r.read().decode("utf-8"))
        out: list[str] = []
        for m in data.get("models", []):
            name = m.get("name") or m.get("model") or ""
            if name:
                out.append(name)
        return out
    except Exception as e:
        _log.info("list_ollama_models: Ollama not available (%s)", e)
        return []


# ─────────────────────────────────────────────
#  OpenAI-compatible path (OpenRouter + Ollama)
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  Cliente OpenAI cacheado (v0.16.13)
# ─────────────────────────────────────────────
#
# Igual que el Client xAI: el SDK de OpenAI mantiene un pool HTTP/2 cuando
# el cliente persiste. Crear uno nuevo cada llamada paga ~300-600ms de
# handshake TCP+TLS. Lo cacheamos aquí, invalidando si cambia api_key o
# base_url (cuando el user edita Settings).
import threading as _threading

_openai_cache_client = None
_openai_cache_key: tuple[str, str] | None = None
_openai_cache_lock = _threading.Lock()


def _openai_client():
    """Devuelve el cliente OpenAI-compatible compartido. Lo crea si no
    existe, o si la api_key/base_url cambiaron desde la última vez."""
    global _openai_cache_client, _openai_cache_key
    from openai import OpenAI
    cfg = get_active_config()
    current_key = (cfg["api_key"] or "", cfg["base_url"] or "")
    with _openai_cache_lock:
        if _openai_cache_client is None or _openai_cache_key != current_key:
            _openai_cache_client = OpenAI(
                api_key=cfg["api_key"],
                base_url=cfg["base_url"] or None,
            )
            _openai_cache_key = current_key
        return _openai_cache_client


def invalidate_openai_client() -> None:
    """Fuerza recreación en próxima llamada. Útil tras error de network."""
    global _openai_cache_client, _openai_cache_key
    with _openai_cache_lock:
        _openai_cache_client = None
        _openai_cache_key = None


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


def _openai_compat_supports_penalties(model_name: str) -> bool:
    """Casi todos los modelos en OpenRouter/Ollama aceptan penalties, pero
    algunos (Grok reasoning y algunos Claude extended thinking) no.

    Como regla general: True excepto para los que sabemos que no.
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
    if _openai_compat_supports_penalties(model_name):
        return {"frequency_penalty": 0.5, "presence_penalty": 0.3}
    return {}


def openai_compat_stream(
    messages: list[dict],
    system_prompt: str,
    trigger: str | None = None,
) -> Iterator[str]:
    """Streaming de respuesta vía OpenAI-compatible endpoint.

    Funciona tanto con OpenRouter como con Ollama — la diferencia es
    sólo el base_url que sale de get_active_config().
    """
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
        _log.warning("openai_compat_stream failed (provider=%s): %s", cfg["provider"], e)
        raise


def openai_compat_complete(
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


def openai_compat_simple(system_text: str, user_text: str, *, creative: bool = True) -> str:
    """Wrapper para llamadas tipo system+user único."""
    return openai_compat_complete(
        messages=[{"role": "user", "content": user_text, "image": ""}],
        system_prompt=system_text,
        creative=creative,
    )


# ─────────────────────────────────────────────
#  Backward-compat aliases
# ─────────────────────────────────────────────
#
# El código histórico llama a las funciones como "openrouter_*". Mantener
# los alias evita romper callers en una versión; los deprecaremos en la
# siguiente release.

openrouter_stream = openai_compat_stream
openrouter_complete = openai_compat_complete
openrouter_simple = openai_compat_simple
