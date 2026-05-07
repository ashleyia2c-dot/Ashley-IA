#!/usr/bin/env python3
"""
gen-icons.py — Genera iconos Android para el APK Capacitor desde
assets/ashley_pfp.jpg.

Output: mobile-app/android-overrides/icons/mipmap-{density}/ic_launcher*.png
Estos archivos se commitean al repo. El workflow CI los copia a
android/app/src/main/res/mipmap-* tras `cap add android`.

Por qué no en CI: ImageMagick NO está pre-instalado en runners
ubuntu-latest de GitHub Actions. Generar localmente y commit es más
robusto y no añade tiempo al build.

Tamaños generados (estándar Android Material):
  mdpi    48x48
  hdpi    72x72
  xhdpi   96x96
  xxhdpi  144x144
  xxxhdpi 192x192

Variantes:
  ic_launcher.png         — icono principal (cuadrado)
  ic_launcher_round.png   — para launchers que muestran círculo
  ic_launcher_foreground.png — para adaptive icons Android 8+ (1.5x)

Uso: python mobile-app/scripts/gen-icons.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow no instalado. Instalar con:")
    print("  venv\\Scripts\\pip install Pillow")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "assets" / "ashley_pfp.jpg"
OUT_DIR = ROOT / "mobile-app" / "android-overrides" / "icons"

# (density, size_px) — tamaños estándar mipmap de Android
SIZES = [
    ("mdpi",    48),
    ("hdpi",    72),
    ("xhdpi",   96),
    ("xxhdpi",  144),
    ("xxxhdpi", 192),
]


def make_square_centered(img: Image.Image, size: int) -> Image.Image:
    """Crop centrado + resize para que la cara de Ashley quede en el
    centro y no se corte. Si la imagen no es cuadrada, recorta el lado
    más largo equilibrado a ambos extremos."""
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    cropped = img.crop((left, top, left + side, top + side))
    return cropped.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: source no encontrado: {SOURCE}")
        return 1
    print(f"[gen-icons] source: {SOURCE}")
    print(f"[gen-icons] output: {OUT_DIR}")

    src = Image.open(SOURCE).convert("RGBA")
    print(f"[gen-icons] source size: {src.size}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for density, size in SIZES:
        density_dir = OUT_DIR / f"mipmap-{density}"
        density_dir.mkdir(parents=True, exist_ok=True)

        # ic_launcher.png + ic_launcher_round.png — cuadrados
        sq = make_square_centered(src, size)
        sq.save(density_dir / "ic_launcher.png", "PNG", optimize=True)
        sq.save(density_dir / "ic_launcher_round.png", "PNG", optimize=True)

        # ic_launcher_foreground.png — para adaptive icons Android 8+
        # Necesita ser 1.5x el tamaño base (108dp foreground vs 72dp safe zone)
        adaptive_size = int(size * 1.5)
        fg = make_square_centered(src, adaptive_size)
        fg.save(density_dir / "ic_launcher_foreground.png", "PNG", optimize=True)

        print(f"[gen-icons] OK mipmap-{density}: {size}x{size} + foreground {adaptive_size}x{adaptive_size}")

    print(f"\n[gen-icons] DONE. {len(SIZES)} densidades generadas en {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
