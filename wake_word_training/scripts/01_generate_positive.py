"""
01_generate_positive.py — Genera ~3000 samples sintéticos de "Ashley"
usando Piper-TTS.

Estrategia:
  - Bajamos varios voice models de Piper (hombre/mujer/joven/mayor, varios
    acentos: ES MX, ES ES, EN US, EN UK).
  - Para cada voz, generamos múltiples versiones de "ashley" variando:
      * velocidad (length_scale: 0.7 rápido → 1.4 lento)
      * tono / pitch (noise_scale: 0.3 plano → 0.9 expresivo)
  - Output WAV 16 kHz mono (formato esperado por OpenWakeWord).

El detector entrenado va a generalizar mucho mejor con muchas voces
distintas que con grabaciones reales del dueño — la diversidad sintética
es más amplia que la diversidad de "tu casa".

Tiempo estimado: ~30-60 min (depende del bandwidth para descargar voices).
"""

from pathlib import Path
import subprocess
import sys
import urllib.request
import json

# Carpetas (relativas a la raíz wake_word_training/)
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "positive"
MODELS_DIR = ROOT / "models" / "piper"

OUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Voces a usar — variadas en idioma, género, acento. Piper-TTS hostea
# todos en https://huggingface.co/rhasspy/piper-voices. Cada voz son 2
# archivos: el .onnx (modelo) y el .json (config).
#
# Si quieres añadir más voces, ve a:
# https://github.com/rhasspy/piper/blob/master/VOICES.md
# y copia el path del modelo (carpeta + filename) aquí.
VOICES = [
    # Spanish (varios acentos)
    "es/es_ES/sharvard/medium/es_ES-sharvard-medium",
    "es/es_MX/claude/high/es_MX-claude-high",
    "es/es_MX/ald/medium/es_MX-ald-medium",
    # English (varios acentos)
    "en/en_US/lessac/medium/en_US-lessac-medium",
    "en/en_US/amy/medium/en_US-amy-medium",
    "en/en_US/ryan/high/en_US-ryan-high",
    "en/en_GB/alan/medium/en_GB-alan-medium",
    "en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium",
]

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def download_voice(voice_path: str) -> tuple[Path, Path]:
    """Descarga el modelo + config de una voz si no existe localmente.
    Returns (onnx_path, json_path)."""
    voice_id = voice_path.split("/")[-1]
    onnx_url = f"{BASE_URL}/{voice_path}.onnx"
    json_url = f"{BASE_URL}/{voice_path}.onnx.json"
    onnx_local = MODELS_DIR / f"{voice_id}.onnx"
    json_local = MODELS_DIR / f"{voice_id}.onnx.json"

    for url, local in [(onnx_url, onnx_local), (json_url, json_local)]:
        if local.exists():
            continue
        print(f"  → Descargando {local.name}...")
        urllib.request.urlretrieve(url, local)
    return onnx_local, json_local


def synthesize(text: str, voice_onnx: Path, voice_json: Path,
                out_wav: Path, length_scale: float = 1.0,
                noise_scale: float = 0.667) -> bool:
    """Llama a piper-tts CLI para sintetizar `text` con la voz dada.
    length_scale: <1.0 más rápido, >1.0 más lento.
    noise_scale: variabilidad de prosody/expressivity.
    """
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "piper",
                "--model", str(voice_onnx),
                "--config", str(voice_json),
                "--output_file", str(out_wav),
                "--length_scale", str(length_scale),
                "--noise_scale", str(noise_scale),
            ],
            input=text,
            text=True,
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  ✗ {e}")
        return False


def main():
    print("=== Wake word positive samples generator ===\n")
    print(f"Output: {OUT_DIR}")
    print(f"Voices to use: {len(VOICES)}\n")

    # Descargar todas las voces primero
    print("Step 1: Downloading voice models...")
    voice_files = []
    for v in VOICES:
        try:
            onnx, json_p = download_voice(v)
            voice_files.append((v, onnx, json_p))
        except Exception as e:
            print(f"  ✗ Failed {v}: {e}")
    print(f"OK Downloaded {len(voice_files)} voices\n")

    # Variantes — combinaciones de length_scale + noise_scale
    variants = []
    for ls in [0.7, 0.85, 1.0, 1.15, 1.3]:    # 5 velocidades
        for ns in [0.4, 0.667, 0.85]:           # 3 expresividades
            variants.append((ls, ns))

    # Variantes del texto — el user puede pronunciar "ashley", "Ashley",
    # con pequeñas pausas, etc. Piper-TTS interpreta todo como "Ashley".
    text_variants = [
        "Ashley.",
        "Ashley",
        "Ashley?",
        "Ashley!",
        "Ashley,",
        "Ashley...",
    ]

    print(f"Step 2: Generating samples...")
    print(f"Voices x text-variants x prosody-variants = "
          f"{len(voice_files)} x {len(text_variants)} x {len(variants)} = "
          f"{len(voice_files) * len(text_variants) * len(variants)} samples\n")

    count = 0
    for voice_id, onnx, json_p in voice_files:
        voice_name = voice_id.split("/")[-1]
        for text in text_variants:
            for ls, ns in variants:
                fname = f"{voice_name}__{text.replace(' ', '_').replace('.', '').replace('?', 'q').replace('!', 'e').replace(',', 'c')[:20]}__ls{ls}_ns{ns}.wav"
                out = OUT_DIR / fname
                if out.exists():
                    count += 1
                    continue
                if synthesize(text, onnx, json_p, out, ls, ns):
                    count += 1
                    if count % 50 == 0:
                        print(f"  {count} samples generated...")

    print(f"\nOK Done. Generated {count} positive samples in {OUT_DIR}")
    print(f"\nNext: python scripts/02_download_negative.py")


if __name__ == "__main__":
    main()
