"""
05_test.py — Testing real del modelo "Ashley" con tu mic en vivo.

Mide dos métricas críticas:
  1. False Reject Rate (FRR): % de veces que dices "ashley" y el modelo NO
     se activa. Objetivo: <5%. Si pasa, el wake word se siente "sordo".
  2. False Accept Rate (FAR): activaciones espontáneas con TV/música/
     conversación de fondo. Objetivo: <1 evento/hora. Si pasa, el wake word
     se siente "loco" y tira la confianza del user.

Test 1 (FRR): te pedimos que digas "ashley" 30 veces en distintos
contextos (cerca/lejos del mic, susurrando, gritando, con música, sin
música). Contamos cuántas veces detecta.

Test 2 (FAR): grabamos 10 minutos de "no-ashley" (TV puesta, conversación
de fondo, escribiendo en teclado). Contamos cuántas activaciones falsas
hubo. Multiplicamos × 6 para sacar tasa por hora.

Si los números son malos, anota qué tipo de fail (silencioso, con música,
con TV) y vuelve a la fase de augmentation con más samples de ese caso.
"""

from pathlib import Path
import sys
import time
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    print("ERROR: sounddevice no instalado. Run setup.bat primero.")
    sys.exit(1)

try:
    from openwakeword.model import Model
except ImportError:
    print("ERROR: openwakeword no instalado.")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent

# Preferimos .onnx porque su runtime ya está en el venv de Ashley (onnxruntime).
# Si solo hay .tflite, lo usamos pero requiere tflite_runtime instalado.
_ONNX_PATH = ROOT / "output" / "ashley" / "ashley.onnx"
_TFLITE_PATH = ROOT / "output" / "ashley" / "ashley.tflite"

SR = 16000
CHUNK = 1280  # 80 ms a 16 kHz — el chunk size que espera OpenWakeWord


def load_model():
    if _ONNX_PATH.exists():
        path = _ONNX_PATH
        framework = "onnx"
    elif _TFLITE_PATH.exists():
        path = _TFLITE_PATH
        framework = "tflite"
    else:
        print(f"ERROR: No existe ni {_ONNX_PATH} ni {_TFLITE_PATH}.")
        print("Run scripts/04_train.py primero.")
        sys.exit(1)
    print(f"Modelo: {path.name} (framework={framework})")
    return Model(wakeword_models=[str(path)], inference_framework=framework)


def test_frr(model, n_trials: int = 30):
    """Test 1: dice 'ashley' N veces, contamos detecciones."""
    print("\n=== TEST 1: False Reject Rate ===")
    print(f"Vamos a hacer {n_trials} pruebas. Para cada una:")
    print("  1. Pulsa Enter")
    print("  2. Espera 0.5s")
    print("  3. Di 'Ashley' una vez")
    print("  4. Verás si se detectó o no\n")
    print("Mezcla contextos: a veces susurrando, a veces gritando,")
    print("a veces con música puesta, a veces lejos del mic, etc.\n")

    detected = 0
    for i in range(1, n_trials + 1):
        input(f"[{i}/{n_trials}] Pulsa Enter y di 'Ashley'...")
        # Capturar 2.5s de audio
        audio = sd.rec(int(2.5 * SR), samplerate=SR, channels=1, dtype="int16")
        sd.wait()
        audio = audio.flatten()

        # Procesar en chunks
        max_score = 0.0
        for start in range(0, len(audio) - CHUNK, CHUNK):
            chunk = audio[start:start + CHUNK]
            scores = model.predict(chunk)
            for kw, score in scores.items():
                if score > max_score:
                    max_score = score

        if max_score >= 0.5:
            detected += 1
            print(f"   OK ({max_score:.2f})")
        else:
            print(f"   FAIL ({max_score:.2f})")

    frr = (n_trials - detected) / n_trials * 100
    print(f"\nFRR: {frr:.1f}% ({n_trials - detected}/{n_trials} no detectados)")
    if frr < 5:
        print("  → EXCELENTE")
    elif frr < 15:
        print("  → ACEPTABLE — considera más augmentation con samples difíciles")
    else:
        print("  → MALO — necesita re-training con más datos / mejor augmentation")
    return frr


def test_far(model, duration_min: int = 10):
    """Test 2: silencio + ruido de fondo, contamos activaciones falsas."""
    print(f"\n=== TEST 2: False Accept Rate ({duration_min} min) ===")
    print("Vamos a escuchar el mic durante", duration_min, "minutos.")
    print("PON LA TV / MÚSICA / CONVERSACIÓN DE FONDO.")
    print("NO digas 'Ashley' durante esto.")
    print("Cualquier activación cuenta como falso positivo.\n")
    input("Pulsa Enter cuando estés listo...")

    end = time.time() + duration_min * 60
    activations = 0
    last_activation = 0

    print(f"\nEscuchando... (Ctrl+C para parar antes)\n")
    try:
        while time.time() < end:
            audio = sd.rec(CHUNK, samplerate=SR, channels=1, dtype="int16",
                           blocking=True)
            scores = model.predict(audio.flatten())
            for kw, score in scores.items():
                if score >= 0.5 and time.time() - last_activation > 1.5:
                    activations += 1
                    last_activation = time.time()
                    elapsed_min = (time.time() - (end - duration_min * 60)) / 60
                    print(f"  [@{elapsed_min:.1f}min] FALSE POSITIVE ({score:.2f})")
    except KeyboardInterrupt:
        elapsed_min = (time.time() - (end - duration_min * 60)) / 60
        duration_min = elapsed_min  # ajustar para cálculo

    far_per_hour = activations / max(duration_min, 0.1) * 60
    print(f"\nFAR: {activations} activaciones en {duration_min:.1f} min")
    print(f"     ≈ {far_per_hour:.1f} por hora")
    if far_per_hour < 1:
        print("  → EXCELENTE")
    elif far_per_hour < 5:
        print("  → ACEPTABLE")
    else:
        print("  → MALO — el modelo se confunde con voces parecidas")
    return far_per_hour


def main():
    print("=== Wake word real-world testing ===\n")
    model = load_model()
    print(f"OK Modelo cargado")

    # Test 1 — interactivo
    frr = test_frr(model, n_trials=30)

    # Test 2 — con ruido de fondo
    print("\n" + "=" * 50)
    ans = input("¿Hacer test FAR (10 min)? [Y/n]: ").strip().lower()
    if ans != "n":
        far = test_far(model, duration_min=10)
    else:
        far = None

    print("\n=== RESUMEN ===")
    print(f"FRR: {frr:.1f}%   {'PASS' if frr < 15 else 'FAIL'}")
    if far is not None:
        print(f"FAR: {far:.1f}/h  {'PASS' if far < 5 else 'FAIL'}")

    if frr >= 15 or (far is not None and far >= 5):
        print("\nEl modelo no está listo para producción. Iterar:")
        print("  - FRR alto: añade más samples positivos en augmentation")
        print("  - FAR alto: añade más negativos similares (voces parecidas a 'Ashley')")
    else:
        print("\nOK Modelo listo. Copia ashley.tflite a reflex_companion/wake_word/")


if __name__ == "__main__":
    main()
