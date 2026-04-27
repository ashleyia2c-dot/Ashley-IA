"""
02_download_negative.py — Descarga datasets públicos de audio que NO contienen
"ashley" para entrenar al modelo a NO activarse en falso.

Estrategia: usar el dataset de "background features" que el repo de
OpenWakeWord ya provee — son ~30000 clips de habla, ruido, música. Cubre
los falsos positivos más comunes (TV, conversación, gente que dice nombres
parecidos).

Si quieres añadir más variedad post-hoc (ej: tu casa con la TV puesta), puedes
grabarlo y meterlo manualmente en data/negative/.

Tiempo: ~10-15 min de descarga (~2 GB).
"""

from pathlib import Path
import urllib.request
import zipfile
import shutil

ROOT = Path(__file__).resolve().parent.parent
NEG_DIR = ROOT / "data" / "negative"
NEG_DIR.mkdir(parents=True, exist_ok=True)

# OpenWakeWord publica un dataset pre-procesado de "no wake word" que es
# perfecto para training. Está en HuggingFace.
NEGATIVE_FEATURES_URL = (
    "https://huggingface.co/datasets/davidscripka/openwakeword-features/"
    "resolve/main/openwakeword_features_part1.tar"
)

# Backup: dataset MUSAN (más grande, más variado pero requiere registration en
# OpenSLR). Si el primary URL falla, escribir tu propio script de download.
# https://www.openslr.org/17/

DEST_FILE = NEG_DIR / "openwakeword_features.tar"


def download_with_progress(url: str, dest: Path):
    """urllib con progress bar simple."""
    print(f"Downloading {url}")
    print(f"  → {dest}")

    def progress_hook(block_num, block_size, total_size):
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        pct = min(100.0, downloaded * 100.0 / total_size)
        mb_done = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        # \r para sobreescribir la línea
        print(f"  {pct:5.1f}%  [{mb_done:.1f} / {mb_total:.1f} MB]",
              end="\r", flush=True)

    urllib.request.urlretrieve(url, dest, progress_hook)
    print()


def main():
    print("=== Wake word negative samples downloader ===\n")

    if DEST_FILE.exists() and DEST_FILE.stat().st_size > 100_000_000:
        print(f"OK Already have {DEST_FILE.name} ({DEST_FILE.stat().st_size / 1024 / 1024:.0f} MB)")
        print("(Skip download — delete file to re-download)")
    else:
        try:
            download_with_progress(NEGATIVE_FEATURES_URL, DEST_FILE)
        except Exception as e:
            print(f"\nERROR: {e}")
            print("\nFallback options:")
            print("  1. Check internet connection")
            print("  2. Manually download from:")
            print(f"     {NEGATIVE_FEATURES_URL}")
            print(f"     and place at: {DEST_FILE}")
            return

    # Extract si es .tar
    print("\nExtracting...")
    if str(DEST_FILE).endswith(".tar"):
        import tarfile
        with tarfile.open(DEST_FILE, "r") as tar:
            tar.extractall(NEG_DIR)
        print(f"OK Extracted to {NEG_DIR}")
    elif str(DEST_FILE).endswith(".zip"):
        with zipfile.ZipFile(DEST_FILE) as z:
            z.extractall(NEG_DIR)
        print(f"OK Extracted to {NEG_DIR}")

    print(f"\nNext: python scripts/03_augment.py")


if __name__ == "__main__":
    main()
