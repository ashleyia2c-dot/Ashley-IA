"""
06_install_in_ashley.py — Copia el modelo entrenado a su lugar de
runtime en la app de Ashley.

Ejecuta esto DESPUÉS de que `04_train.py` termine con éxito:
  - Verifica que `output/ashley.onnx` existe
  - Verifica que las deps de inferencia están instaladas en el venv
    PRINCIPAL de Ashley (no en este venv de training)
  - Copia el modelo a `reflex_companion/wake_word/ashley.onnx`
  - Imprime un mensaje listo para activar el toggle

Tras esto, abrir Ashley → Settings → 🎙 Wake word → ACTIVAR. El detector
arranca automáticamente y queda escuchando.
"""

from pathlib import Path
import shutil
import sys
import subprocess

# Forzar UTF-8 en stdout para evitar UnicodeEncodeError con emojis ⚙️ 🎙
# cuando el script se redirige a un archivo en Windows (cp1252 default).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent

SRC = ROOT / "output" / "ashley.onnx"
SRC_DATA = ROOT / "output" / "ashley.onnx.data"
DEST_DIR = PROJECT_ROOT / "reflex_companion" / "wake_word"
DEST = DEST_DIR / "ashley.onnx"
DEST_DATA = DEST_DIR / "ashley.onnx.data"

# Venv principal de Ashley (no el de training)
ASHLEY_VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"


def ensure_ashley_deps():
    """Verifica que openwakeword + sounddevice están en el venv de Ashley.
    Si faltan, los instala. También descarga los feature extraction
    models (melspec + embedding + silero_vad) en el venv si no están.
    """
    if not ASHLEY_VENV_PYTHON.exists():
        print(f"WARNING: no se encontró el venv de Ashley en {ASHLEY_VENV_PYTHON}")
        print("Asume que ya tienes los packages instalados manualmente.")
        return

    # Test imports en el venv de Ashley
    check_cmd = [
        str(ASHLEY_VENV_PYTHON), "-c",
        "import openwakeword, sounddevice; print('OK')",
    ]
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    if result.returncode == 0 and "OK" in result.stdout:
        print(f"OK Deps de wake word presentes en venv de Ashley")
    else:
        print(f"Faltan deps en venv de Ashley:")
        print(f"  {result.stderr.strip()}")
        print(f"Instalando openwakeword + sounddevice en venv de Ashley...")
        install_cmd = [
            str(ASHLEY_VENV_PYTHON), "-m", "pip", "install",
            "openwakeword", "sounddevice",
        ]
        subprocess.run(install_cmd, check=True)
        print(f"OK Deps instaladas")

    # Pre-descargar feature extraction models (melspectrogram + embedding
    # + silero_vad) en el venv de Ashley — son ~5 MB y openwakeword los
    # necesita para AudioFeatures. Si no se descargan ahora, se
    # descargan al primer toggle ON, lo cual añade ~10s de delay.
    print(f"Descargando feature models (melspec + embedding + VAD ~5 MB)...")
    download_cmd = [
        str(ASHLEY_VENV_PYTHON), "-c",
        "from openwakeword.utils import download_models; download_models([])",
    ]
    result = subprocess.run(download_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"OK Feature models presentes en venv de Ashley")
    else:
        print(f"WARNING: download_models falló: {result.stderr.strip()[:200]}")
        print(f"Se descargarán al primer toggle ON del wake word.")


def main():
    print("=== Install ashley.onnx en la app ===\n")

    # Paso 1: verificar que el modelo existe
    if not SRC.exists():
        print(f"ERROR: no existe {SRC}")
        print(f"Run scripts/04_train.py primero.")
        sys.exit(1)
    size_kb = SRC.stat().st_size / 1024
    print(f"OK Modelo encontrado: {SRC.name} ({size_kb:.1f} KB)")

    # Paso 2: deps de runtime en venv de Ashley
    ensure_ashley_deps()

    # Paso 3: copiar
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, DEST)
    print(f"OK Copiado: {DEST}")
    if SRC_DATA.exists():
        shutil.copy2(SRC_DATA, DEST_DATA)
        print(f"OK Copiado: {DEST_DATA.name} (pesos)")

    # Paso 4: instrucciones finales
    print()
    print("=== Listo ===")
    print()
    print("Próximos pasos:")
    print("  1. Abre Ashley (o reinicia si ya está abierta)")
    print("  2. Pulsa el icono ⚙️ del header → Settings")
    print("  3. Busca '🎙 Wake word' y activa el toggle")
    print("  4. Di 'Ashley' cerca del mic — la grabación STT arranca sola")
    print()
    print("Si los falsos positivos te molestan, sube el threshold de 0.65")
    print("a 0.75 en reflex_companion/reflex_companion.py:toggle_wake_word_enabled")


if __name__ == "__main__":
    main()
