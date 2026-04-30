"""Diagnóstico de latencia end-to-end para Ashley.

Ejecuta varias llamadas al LLM con la config ACTUAL del user (la misma
que usa la app) y mide:

  • Cold connect: primera llamada — incluye DNS + TCP + TLS handshake.
  • Warm connect: llamadas siguientes — reusan la conexión cacheada.
  • TTFT (Time To First Token): cuánto tarda el LLM en empezar a emitir.
  • Total: tiempo hasta el último token.

El objetivo es separar:
  • Lo que cuesta NETWORK (handshake, RTT).
  • Lo que cuesta el MODELO (TTFT, reasoning step).
  • Lo que es PYTHON pre-stream (build prompt, etc.).

Cómo usarlo (desde el venv activo):
  python tools/diagnose_latency.py

El script imprime una tabla con cada fase. Si el TTFT es ~3+ segundos,
es el modelo de reasoning. Si el cold connect es ~500ms+, es la latencia
de red desde tu ubicación al endpoint.
"""

import os
import sys
import time
from pathlib import Path

# Asegurar import del paquete reflex_companion desde root del repo.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Cargar .env si existe (para XAI_API_KEY).
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def measure_one_call(client, model, system_text, user_text, label: str):
    """Hace una llamada streaming y mide TTFT + total time."""
    from xai_sdk.chat import system as xai_system, user as xai_user

    t_start = time.monotonic()

    chat = client.chat.create(model=model)
    chat.append(xai_system(system_text))
    chat.append(xai_user(user_text))

    t_after_setup = time.monotonic()

    first_token_at = None
    chunk_count = 0
    total_chars = 0

    try:
        for response, chunk in chat.stream():
            content = chunk.content if hasattr(chunk, "content") else ""
            if content:
                if first_token_at is None:
                    first_token_at = time.monotonic()
                total_chars += len(content)
                chunk_count += 1
    except Exception as e:
        print(f"  [{label}] ERROR durante stream: {e}")
        return None

    t_end = time.monotonic()

    setup_ms = (t_after_setup - t_start) * 1000
    ttft_ms = ((first_token_at or t_end) - t_after_setup) * 1000
    total_ms = (t_end - t_start) * 1000
    chars_per_sec = total_chars / max(0.001, t_end - (first_token_at or t_end))

    return {
        "label": label,
        "setup_ms": setup_ms,
        "ttft_ms": ttft_ms,
        "total_ms": total_ms,
        "chars": total_chars,
        "chunks": chunk_count,
        "chars_per_sec": chars_per_sec,
    }


def main():
    from reflex_companion.config import GROK_MODEL, XAI_API_KEY
    from reflex_companion.grok_client import get_xai_client

    if not XAI_API_KEY or len(XAI_API_KEY) < 10:
        print("ERROR: XAI_API_KEY no está configurada o es inválida.")
        print("Edita .env con tu key de xAI antes de correr este script.")
        sys.exit(1)

    print("=" * 70)
    print(f"DIAGNÓSTICO DE LATENCIA — Ashley")
    print(f"Modelo: {GROK_MODEL}")
    print(f"Provider: xAI directo (api.x.ai)")
    print("=" * 70)

    sys_prompt = (
        "Eres una asistente cálida y concisa. Responde en castellano. "
        "Máximo 2 oraciones."
    )
    user_msgs = [
        "hola, cómo estás?",
        "qué hora es ahí?",
        "cuéntame algo curioso",
    ]

    client = get_xai_client()

    print(f"\nHaciendo {len(user_msgs)} llamadas consecutivas con cliente cacheado...")
    print("(la primera incluye handshake TCP+TLS; las demás reusan conexión)\n")

    results = []
    for i, msg in enumerate(user_msgs, 1):
        label = f"Call {i}"
        if i == 1:
            label += " (cold)"
        elif i == 2:
            label += " (warm)"
        else:
            label += " (warm)"
        result = measure_one_call(client, GROK_MODEL, sys_prompt, msg, label)
        if result:
            results.append(result)
            print(
                f"  {result['label']:20} "
                f"setup={result['setup_ms']:6.0f}ms  "
                f"TTFT={result['ttft_ms']:6.0f}ms  "
                f"total={result['total_ms']:6.0f}ms  "
                f"({result['chars']} chars, {result['chars_per_sec']:.0f} chars/s)"
            )

    if not results:
        print("\nERROR: ninguna llamada tuvo éxito.")
        sys.exit(2)

    print()
    print("=" * 70)
    print("ANÁLISIS")
    print("=" * 70)

    cold_ttft = results[0]["ttft_ms"]
    warm_ttfts = [r["ttft_ms"] for r in results[1:]]
    avg_warm_ttft = sum(warm_ttfts) / max(1, len(warm_ttfts)) if warm_ttfts else 0

    print(f"\nTTFT cold (1ª llamada — handshake + reasoning + LLM): {cold_ttft:.0f}ms")
    if warm_ttfts:
        print(f"TTFT warm (avg llamadas 2-{len(results)}): {avg_warm_ttft:.0f}ms")
        handshake_overhead = cold_ttft - avg_warm_ttft
        print(f"\n-> Diferencia cold vs warm: {handshake_overhead:.0f}ms")
        print(f"  Esto es aproximadamente el handshake TCP+TLS y DNS lookup.")
        print(f"  Tras el primer mensaje, la conexion se reusa.")

    print(f"\nTTFT del MODELO solo (warm): {avg_warm_ttft:.0f}ms")
    if avg_warm_ttft > 2500:
        print("  [!] TTFT alto: el modelo 'reasoning' anade ~3s antes del primer token.")
        print("      Considera cambiar a 'grok-4-1-fast-non-reasoning' en Settings")
        print("      para bajar el TTFT a ~600ms (ahorro de ~2.5s por mensaje).")
    elif avg_warm_ttft > 1000:
        print("  TTFT moderado. Modelo no-reasoning seria ~600ms.")
    else:
        print("  TTFT bajo - el modelo responde rapido.")

    print()
    if results:
        print("Throughput de tokens (chars/sec promedio):")
        avg_cps = sum(r["chars_per_sec"] for r in results) / len(results)
        print(f"  {avg_cps:.0f} chars/s — equivale a {avg_cps / 4:.0f} tokens/s aprox.")

    print()
    print("=" * 70)
    print("RECOMENDACIONES")
    print("=" * 70)
    print()

    if cold_ttft - avg_warm_ttft > 200:
        print("[OK] Cache de cliente xAI funciona - handshake solo se paga la 1a vez.")
    else:
        print("[!]  Diferencia cold/warm es pequena - el cache puede no estar funcionando")
        print("     o la red es ya muy rapida.")

    if avg_warm_ttft > 2500 and "reasoning" in GROK_MODEL.lower() and "non-reasoning" not in GROK_MODEL.lower():
        print()
        print("[!]  Estas en modo reasoning. Trade-off:")
        print("     - Reasoning ON  -> respuestas mas elaboradas, TTFT ~3s")
        print("     - Reasoning OFF -> respuestas mas directas, TTFT ~600ms")
        print()
        print("     Para conversacion casual, non-reasoning es mas fluido.")
        print("     Cambiar en: Settings -> Modelo -> 'Grok 4.1 Fast' (no-reasoning).")

    print()


if __name__ == "__main__":
    main()
