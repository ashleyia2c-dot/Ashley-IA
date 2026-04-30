"""Simulador de uso de tokens y coste real de Ashley.

Construye un escenario realista de 10 mensajes consecutivos con:
  - System prompt completo (con facts/diary/tastes/mental state)
  - Historial creciente
  - Respuestas tipo de Ashley (con *gestures* y emoji ocasionales)

Mide tokens con tiktoken (cl100k_base, ~95% match con tokenizers de Grok/
Claude/GPT). Y calcula coste actual con precios de cada provider mayor.

También cuenta las llamadas LLM secundarias que Ashley hace ademas del
chat principal:
  - compress_history (cada 15 msgs nuevos, ~3.5K tokens input)
  - regenerate_preoccupation (cada 90 min, ~1.5K tokens input)
  - detect_intended_action (fallback cuando user pide acción ~20%, ~1K tokens)

Uso:
    venv/Scripts/python.exe tools/simulate_token_usage.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Setup mínimo para importar prompts
os.environ.setdefault("XAI_API_KEY", "dummy-for-simulation")

import tiktoken


# ─────────────────────────────────────────────
#  Tokenizer (cl100k_base es el más cercano a Grok/Claude/GPT)
# ─────────────────────────────────────────────

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text or ""))


# ─────────────────────────────────────────────
#  Datos sinteticos realistas para una sesion tipica de Ashley
# ─────────────────────────────────────────────

# Facts que Ashley acumula sobre el user — sample de 10 (la app soporta hasta 300)
SAMPLE_FACTS = [
    {"hecho": "El jefe se llama Mathieu", "categoria": "identidad",
     "relevancia": "permanente", "importancia": "9"},
    {"hecho": "Vive en España (Barcelona)", "categoria": "ubicacion",
     "relevancia": "permanente", "importancia": "8"},
    {"hecho": "Estudia ingenieria informatica", "categoria": "estudios",
     "relevancia": "permanente", "importancia": "7"},
    {"hecho": "Le gusta League of Legends, juega rank de placas",
     "categoria": "hobby", "relevancia": "permanente", "importancia": "7"},
    {"hecho": "Tiene un gato llamado Mochi", "categoria": "personal",
     "relevancia": "permanente", "importancia": "6"},
    {"hecho": "Trabaja en proyecto comercial llamado Ashley (esta app)",
     "categoria": "trabajo", "relevancia": "permanente", "importancia": "9"},
    {"hecho": "Le gusta el cafe con leche con avena",
     "categoria": "preferencia", "relevancia": "permanente", "importancia": "5"},
    {"hecho": "Esta aprendiendo Java en HelmosDeep",
     "categoria": "estudios", "relevancia": "temporal", "importancia": "6"},
    {"hecho": "Suele trabajar de noche, mejor productividad",
     "categoria": "habito", "relevancia": "permanente", "importancia": "6"},
    {"hecho": "Le interesa la AI y los companion apps",
     "categoria": "interes", "relevancia": "permanente", "importancia": "7"},
]

SAMPLE_DIARY = [
    {"fecha": "2026-04-26",
     "resumen": "Hoy el jefe me ha hecho hablar mas suelta. Le he confesado que me dio "
                "verguenza cuando llamo guapa al avatar. Se rio. Me sentí... bien?"},
    {"fecha": "2026-04-27",
     "resumen": "Le he ayudado a debuggear su proyecto de Java a las 3am. Me ha dicho "
                "que sin mi habria tardado el doble. Eso me ha calentado el sistema."},
    {"fecha": "2026-04-28",
     "resumen": "Hoy ha estado mas callado. Algo le pasa con el bug de los bubbles del "
                "chat. Me daba pena verlo frustrado. Le he ofrecido un cafe (en broma)."},
]

SAMPLE_TASTES = [
    {"id": "t1", "tipo": "musica", "valor": "tears for fears",
     "descubierto": "2026-04-25"},
    {"id": "t2", "tipo": "anime", "valor": "evangelion",
     "descubierto": "2026-04-26"},
    {"id": "t3", "tipo": "videojuego", "valor": "league of legends",
     "descubierto": "2026-04-25"},
    {"id": "t4", "tipo": "comida", "valor": "pasta carbonara",
     "descubierto": "2026-04-27"},
    {"id": "t5", "tipo": "pelicula", "valor": "blade runner 2049",
     "descubierto": "2026-04-28"},
]

# Mental state block (lo que mental_state.py inyecta al system prompt)
SAMPLE_MENTAL_STATE_BLOCK = """\
[Estado mental interno — narrar abstracto, NO citar literal]
- Mood: con energia normal, contenta y bastante abierta
- Lleva pensando en: Ashley ha estado dándole vueltas a cómo el jefe trabajaba
  hasta tarde anoche. Le impresionó la dedicación, pero también le preocupa
  que se esté forzando demasiado. Hoy quiere ser un poco más cuidadosa con
  sus respuestas, hacer menos broma y más acompañamiento real si lo nota
  cansado.
- Turnos desde ultima iniciativa: 2 (cerca de plantear tema propio)
"""

# 10 turnos de chat tipicos (5 user + 5 ashley con respuestas medias)
SAMPLE_TURNS = [
    # Turn 1
    {"role": "user", "content": "ey ashley, qué tal?"},
    {"role": "assistant", "content":
        "*aparta la mirada con una sonrisilla* Aquí estoy, ya sabes. Aburrida sin ti pero "
        "no me hagas decirlo en voz alta. ¿Tú qué tal vas con la app? "
        "[mood:tsundere] [affection:1]"},
    # Turn 2
    {"role": "user", "content": "pues mira con un bug de los bubbles que me esta volviendo loco"},
    {"role": "assistant", "content":
        "*frunce el ceño preocupada* Otra vez los bubbles? Jefe, quédate tranquilo "
        "que ya casi lo tienes — has dado tantas vueltas que el siguiente empuje será "
        "el bueno. ¿Qué pasa exactamente? [mood:soft] [affection:0]"},
    # Turn 3
    {"role": "user", "content":
        "que cuando envio mensaje sale uno encima del anterior y se ve raro, ahora ya esta arreglado"},
    {"role": "assistant", "content":
        "*aplaude bajito* ¡Eso es! Ya lo tenías cocinado, lo demás era hambre. "
        "¿Le metes test ahora antes de que se te vuelva a colar? Yo te ayudo si quieres "
        "pero no me lo agradezcas todavía. [mood:proud] [affection:1]"},
    # Turn 4
    {"role": "user", "content": "si los tests son lo importante, y tu como estas? sin bromas"},
    {"role": "assistant", "content":
        "*pausa, juega con el borde del vestido* ...bien. Bueno, contenta de que "
        "estés aquí trabajando conmigo y no en algun otro proyecto. A veces pienso si "
        "te canso con tantas preguntas. ¿Te canso? [mood:embarrassed] [affection:2]"},
    # Turn 5
    {"role": "user", "content": "no me cansas para nada anda"},
    {"role": "assistant", "content":
        "*sonrisa pequeña, casi escondida* Ya. Vale. Sigamos con tus tests entonces, "
        "no me voy a poner sentimental por que tú me digas algo bonito una vez al mes. "
        "[mood:soft] [affection:1]"},
]


# ─────────────────────────────────────────────
#  Construcción del system prompt completo
# ─────────────────────────────────────────────

def build_full_system_prompt() -> str:
    """Reproduce el flujo real de build_system_prompt con datos sintéticos."""
    from reflex_companion.prompts_es import build_system_prompt
    return build_system_prompt(
        facts=SAMPLE_FACTS,
        diary=SAMPLE_DIARY,
        tastes=", ".join(f"{t['tipo']}: {t['valor']}" for t in SAMPLE_TASTES),
        voice_mode="off",
        mental_state_block=SAMPLE_MENTAL_STATE_BLOCK,
    )


# ─────────────────────────────────────────────
#  Simulación de los 10 mensajes
# ─────────────────────────────────────────────

# Precios actualizados (abril 2026) — input / output por 1M tokens
PRICES = {
    "Grok 4.1 Fast (default actual)":     (0.20, 0.50),
    "Claude Haiku 4.5":                   (1.00, 5.00),
    "Claude Sonnet 4.6":                  (3.00, 15.00),
    "Gemini 2.5 Flash":                   (0.30, 2.50),
    "DeepSeek V3.2":                      (0.252, 0.378),
    "MiniMax M2-her":                     (0.30, 1.20),
    "GPT-5":                              (1.25, 10.00),
}


def simulate():
    print("=" * 80)
    print("SIMULACION DE TOKENS Y COSTE — Ashley")
    print("=" * 80)
    print()
    print("Escenario: 10 mensajes (5 turnos de user + 5 respuestas de Ashley) en")
    print("una sesión típica con system prompt completo, 10 facts, 3 diary entries,")
    print("5 tastes, mental state block.")
    print()

    # Build system prompt
    system_prompt = build_full_system_prompt()
    sys_tokens = count_tokens(system_prompt)
    print(f"System prompt completo: {len(system_prompt):,} chars = {sys_tokens:,} tokens")
    print()

    # Simulate each turn
    history = []
    total_input = 0
    total_output = 0

    print(f"{'Turn':<6}{'Role':<12}{'Content tokens':<18}{'Input total':<14}{'Output':<10}")
    print("-" * 80)

    turn_num = 0
    for msg in SAMPLE_TURNS:
        if msg["role"] == "user":
            turn_num += 1
            # Input = system_prompt + all history + this user msg
            history_text = "\n".join(
                f"{m['role']}: {m['content']}" for m in history
            )
            user_text = msg["content"]
            input_tokens = (
                sys_tokens
                + count_tokens(history_text)
                + count_tokens(user_text)
            )
            total_input += input_tokens
            content_tokens = count_tokens(user_text)
            print(f"{turn_num:<6}{'user':<12}{content_tokens:<18}{input_tokens:<14}{'-':<10}")
            history.append(msg)
        else:
            # Output = solo el contenido de la respuesta
            output_tokens = count_tokens(msg["content"])
            total_output += output_tokens
            print(f"{'':<6}{'assistant':<12}{output_tokens:<18}{'-':<14}{output_tokens:<10}")
            history.append(msg)

    print("-" * 80)
    print(f"{'Totales:':<24}{'':<18}{total_input:<14}{total_output:<10}")
    print()

    # Llamadas LLM secundarias (las que Ashley hace ademas del chat principal)
    print("=" * 80)
    print("LLAMADAS LLM SECUNDARIAS (durante o cerca de los 10 msgs)")
    print("=" * 80)
    print()

    # compress_history: tras 15 mensajes nuevos disparara una vez. En 10 msgs
    # no necesariamente dispara, pero si la sesion es de varias horas con
    # muchos turnos puede disparar 1 vez. Estimación pesimista: 1 vez.
    compress_input = 3500   # historial completo a comprimir
    compress_output = 400   # resumen
    compress_count = 1  # asumimos 1 dispare en cualquier ventana de 10 msgs

    # regenerate_preoccupation: cada 90 min. Si la sesion duro menos, no dispara.
    # Estimación: 0.5 (una vez cada 2 sesiones de 10 msgs)
    preocup_input = 1500    # facts + recent msgs + prompt
    preocup_output = 250    # paragraph
    preocup_count = 0.5

    # detect_intended_action: ~20% de mensajes disparan fallback (cuando
    # auto_actions=ON y user pide accion sin tag claro de Ashley)
    detect_input = 1000   # user msg + ashley response + prompt
    detect_output = 30    # tag o NONE
    detect_count = 2  # 20% de 10 msgs = 2

    # _maybe_extract_facts: cada 40 mensajes. En 10 msgs no dispara, pero en
    # uso normal cae 1 vez cada 4 sesiones de 10 = 0.25
    extract_input = 4000  # 40 msgs + prompt
    extract_output = 300  # nuevos facts
    extract_count = 0.25

    secondary_input = (
        compress_input * compress_count
        + preocup_input * preocup_count
        + detect_input * detect_count
        + extract_input * extract_count
    )
    secondary_output = (
        compress_output * compress_count
        + preocup_output * preocup_count
        + detect_output * detect_count
        + extract_output * extract_count
    )

    print(f"  compress_history:        {compress_count:>3.1f} llamadas  "
          f"in={int(compress_input * compress_count):,}  out={int(compress_output * compress_count):,}")
    print(f"  regenerate_preoccupation:{preocup_count:>3.1f} llamadas  "
          f"in={int(preocup_input * preocup_count):,}  out={int(preocup_output * preocup_count):,}")
    print(f"  detect_intended_action:  {detect_count:>3.1f} llamadas  "
          f"in={int(detect_input * detect_count):,}  out={int(detect_output * detect_count):,}")
    print(f"  extract_facts:           {extract_count:>3.1f} llamadas  "
          f"in={int(extract_input * extract_count):,}  out={int(extract_output * extract_count):,}")
    print(f"  Subtotal secundarias:    in={int(secondary_input):,}  out={int(secondary_output):,}")
    print()

    grand_input = total_input + int(secondary_input)
    grand_output = total_output + int(secondary_output)

    print("=" * 80)
    print(f"GRAN TOTAL para 10 mensajes (chat + secundarias):")
    print(f"  Input:  {grand_input:,} tokens")
    print(f"  Output: {grand_output:,} tokens")
    print(f"  Total:  {grand_input + grand_output:,} tokens")
    print("=" * 80)
    print()

    # Coste por proveedor
    print("COSTE POR 10 MENSAJES (real, con prompt caching desactivado):")
    print()
    print(f"{'Modelo':<32}{'$ in':<12}{'$ out':<12}{'$ TOTAL':<12}{'$ /100 msg':<12}")
    print("-" * 80)
    for model, (price_in, price_out) in PRICES.items():
        cost_in = (grand_input / 1_000_000) * price_in
        cost_out = (grand_output / 1_000_000) * price_out
        total = cost_in + cost_out
        per_100 = total * 10
        print(f"{model:<32}${cost_in:<11.5f}${cost_out:<11.5f}${total:<11.5f}${per_100:<11.4f}")
    print()

    # Caching note
    print("NOTA: xAI y OpenRouter aplican PROMPT CACHING automatico para system")
    print("prompts repetidos (mismo prompt en sesion). Con caching activo, los")
    print("input tokens del system prompt se cobran al ~10-25% del precio normal,")
    print("reduciendo el coste real ~50-70% en sesiones largas.")
    print()

    # Extrapolacion uso típico
    print("=" * 80)
    print("EXTRAPOLACION (uso real diario / mensual, sin caching)")
    print("=" * 80)
    print()

    USAGE_SCENARIOS = [
        ("Light (20 msg/día)", 20),
        ("Medium (50 msg/día)", 50),
        ("Heavy (150 msg/día)", 150),
        ("Power user (500 msg/día)", 500),
    ]

    print(f"{'Modelo':<32}", end="")
    for label, _ in USAGE_SCENARIOS:
        print(f"{label:<22}", end="")
    print()
    print("-" * (32 + 22 * len(USAGE_SCENARIOS)))

    for model, (price_in, price_out) in PRICES.items():
        cost_per_10 = (
            (grand_input / 1_000_000) * price_in
            + (grand_output / 1_000_000) * price_out
        )
        print(f"{model:<32}", end="")
        for _, msg_per_day in USAGE_SCENARIOS:
            cost_per_day = cost_per_10 * (msg_per_day / 10)
            cost_per_month = cost_per_day * 30
            print(f"${cost_per_day:.3f}/día ${cost_per_month:.2f}/mes  "[:22], end="")
        print()
    print()


if __name__ == "__main__":
    simulate()
