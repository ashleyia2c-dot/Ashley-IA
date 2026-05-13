"""Conteo EXACTO de tokens por llamada al LLM.

Hace llamadas reales a xAI con prompts realistas (incluyen system_state,
lista de apps, etc.) y lee el campo `usage` del response — no estima,
es lo que xAI cuenta y nos cobra.

Reporta:
  - prompt_tokens         (input total)
  - cached_prompt_tokens  (cache hits — más baratos)
  - completion_tokens     (output)
  - total_tokens
  - coste estimado USD
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, _, v = line.strip().partition("=")
            os.environ.setdefault(k, v)

from reflex_companion import actions, prompts, grok_client
from xai_sdk.chat import system as xai_system, user as xai_user, assistant as xai_assistant

# Pricing oficial xAI (grok-4-1-fast-non-reasoning, según docs.x.ai/docs/models)
PRICE_INPUT_PER_M = 0.20         # $/M input tokens
PRICE_OUTPUT_PER_M = 0.50        # $/M output tokens
PRICE_CACHED_INPUT_PER_M = 0.05  # $/M cached input tokens (4× más barato)


def cost(prompt_tokens, cached_tokens, completion_tokens):
    """Coste total en USD para una llamada."""
    fresh_input = prompt_tokens - cached_tokens
    return (
        fresh_input * PRICE_INPUT_PER_M / 1_000_000
        + cached_tokens * PRICE_CACHED_INPUT_PER_M / 1_000_000
        + completion_tokens * PRICE_OUTPUT_PER_M / 1_000_000
    )


# Pre-cargar discovery
print("Pre-cargando discovery de apps...")
actions._INSTALLED_APPS_CACHE["ts"] = 0
actions._INSTALLED_APPS_CACHE["apps"] = []
apps = actions.discover_installed_apps(max_total=250)
state = actions.get_system_state(prefer_cdp=False)
print(f"  {len(apps)} apps en system_state ({len(state)} chars)\n")

# Construir prompt completo
system_prompt = prompts.build_system_prompt(
    facts=[
        {"hecho": "El jefe se llama Mathieu.", "categoria": "identidad",
         "importancia": "alta", "ts": "2026-01-01"},
        {"hecho": "Le gusta Sabrina Carpenter.", "categoria": "gustos",
         "importancia": "media", "ts": "2026-04-15"},
    ],
    diary=[],
    use_full_diary=False,
    system_state=state,
    time_context="AHORA: 2026-05-12 14:30 (jueves)",
    voice_mode=False,
    affection=50,
    lang="es",
    cdp_enabled=True,
)
print(f"System prompt: {len(system_prompt)} chars\n")

client = grok_client.get_xai_client()


def run_call(label, history, user_msg):
    """Hace una llamada y reporta el usage exacto."""
    chat = client.chat.create(model="grok-4-1-fast-non-reasoning")
    chat.append(xai_system(system_prompt))
    for role, content in history:
        if role == "user":
            chat.append(xai_user(content))
        else:
            chat.append(xai_assistant(content))
    chat.append(xai_user(user_msg))

    # Streaming hasta el final, luego leer usage
    response = None
    for resp, chunk in chat.stream():
        response = resp
    if response is None:
        return None

    usage = response.usage
    pt = usage.prompt_tokens
    ct = usage.cached_prompt_text_tokens
    ot = usage.completion_tokens
    total = usage.total_tokens
    rt = usage.reasoning_tokens

    fresh = pt - ct
    c = cost(pt, ct, ot)

    print(f"--- {label} ---")
    print(f"  user msg: {user_msg!r}")
    print(f"  prompt_tokens:        {pt:>6}  (fresh={fresh:>5}, cached={ct:>5})")
    print(f"  completion_tokens:    {ot:>6}")
    print(f"  reasoning_tokens:     {rt:>6}")
    print(f"  total_tokens:         {total:>6}")
    print(f"  COSTE:                ${c:.6f}  (~${c*1000:.3f}/1k mensajes)")
    print()
    return {"prompt": pt, "cached": ct, "completion": ot, "cost": c}


print("=" * 70)
print("CASOS DE USO REAL — token counts EXACTOS de xAI")
print("=" * 70)
print()

# Caso 1: mensaje muy simple (saludo)
r1 = run_call("CASO 1: Saludo simple sin acción", [], "hola ashley que tal")

# Caso 2: action request simple
r2 = run_call("CASO 2: Pedir abrir una app", [], "abre el bloc de notas")

# Caso 3: música con chain
r3 = run_call("CASO 3: Música + click like (chain)",
              [], "ponme expresso de sabrina y dale like")

# Caso 4: conversación con history (típico turno 5+)
history_typical = [
    ("user", "hola ashley"),
    ("assistant", "*sonrío* Hola jefe, ¿qué tal el día? [mood:soft][affection:0]"),
    ("user", "bien, programando"),
    ("assistant", "Trabajando duro como siempre. ¿En qué proyecto? [mood:default][affection:0]"),
    ("user", "ashley, otro tema"),
    ("assistant", "Te escucho. [mood:default][affection:0]"),
]
r4 = run_call("CASO 4: Mensaje en turno 4 con history",
              history_typical, "abre vscode")

# Caso 5: pregunta web (Ashley puede usar tool web_search internamente)
r5 = run_call("CASO 5: Pregunta info (puede usar web_search interno)",
              [], "qué tiempo va a hacer mañana en madrid")

# Caso 6: segundo turno (verifica si cache hit aumentó)
r6 = run_call("CASO 6: 2do turno tras CASO 1 (cache hit esperado)",
              [
                  ("user", "hola ashley que tal"),
                  ("assistant", "*sonrío* Hola jefe, todo bien por aquí. [mood:soft]"),
              ],
              "abre la calculadora")

print("=" * 70)
print("RESUMEN — coste estimado por mensaje promedio")
print("=" * 70)

all_costs = [r1, r2, r3, r4, r5, r6]
avg_cost = sum(r["cost"] for r in all_costs if r) / len([r for r in all_costs if r])
avg_prompt = sum(r["prompt"] for r in all_costs if r) / len([r for r in all_costs if r])
avg_cached = sum(r["cached"] for r in all_costs if r) / len([r for r in all_costs if r])
avg_completion = sum(r["completion"] for r in all_costs if r) / len([r for r in all_costs if r])

print(f"  Promedio:")
print(f"    prompt_tokens:     {avg_prompt:>7.0f}")
print(f"    cached:            {avg_cached:>7.0f}  ({100*avg_cached/avg_prompt:.0f}% hit ratio)")
print(f"    completion_tokens: {avg_completion:>7.0f}")
print(f"    coste/mensaje:     ${avg_cost:.6f}")
print(f"    coste/100 msgs:    ${avg_cost*100:.4f}")
print(f"    coste/1000 msgs:   ${avg_cost*1000:.3f}")
print()
print(f"  Pricing usado (Grok 4.1 Fast non-reasoning, oficial xAI):")
print(f"    Input fresh:   ${PRICE_INPUT_PER_M}/M tokens")
print(f"    Input cached:  ${PRICE_CACHED_INPUT_PER_M}/M tokens")
print(f"    Output:        ${PRICE_OUTPUT_PER_M}/M tokens")
