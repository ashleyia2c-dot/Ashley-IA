"""
03_augment.py — Aplica augmentation al dataset positivo para que el modelo
sea robusto a condiciones reales (ruido de fondo, ecos de cuarto, distorsión
del mic, distintas distancias del speaker).

Sin augmentation, el modelo entrenado solo con audio sintético "limpio" de
piper-tts FALLA en escenarios reales: el user dice "Ashley" desde el sofá
con la TV puesta y el modelo no oye nada porque nunca vio audio así durante
training.

Augmentations aplicadas (cada positivo genera N variantes):
  - Background noise mix (de los negativos): mete TV, música, calle al fondo
  - Reverb / room acoustics: simula que está en distintos cuartos
  - Volume gain: simula que está más cerca o más lejos del mic
  - Time stretch: simula que habla más rápido o lento
  - Pitch shift: ligero, simula vocal variation

Tiempo: ~15-30 min según número de samples.
"""

from pathlib import Path
import random
import numpy as np
import soundfile as sf
from tqdm import tqdm

try:
    from audiomentations import (
        Compose, AddGaussianNoise, AddBackgroundNoise,
        TimeStretch, PitchShift, Gain, RoomSimulator,
    )
except ImportError:
    print("ERROR: audiomentations no instalado. Run setup.bat primero.")
    exit(1)

ROOT = Path(__file__).resolve().parent.parent
POS_DIR = ROOT / "data" / "positive"
NEG_DIR = ROOT / "data" / "negative"
AUG_DIR = ROOT / "data" / "augmented"
AUG_DIR.mkdir(parents=True, exist_ok=True)

# Cuántas variantes por sample positivo. 3-5 es razonable: con 3000 positivos
# eso da 9000-15000 augmented samples.
N_AUGMENTATIONS_PER_SAMPLE = 4

SR = 16000  # OpenWakeWord espera 16 kHz mono


def build_augmentation_pipeline() -> Compose:
    """Pipeline de augmentations. Cada llamada aplica un subset random."""
    return Compose([
        # Pitch shift suave (variación vocal natural)
        PitchShift(min_semitones=-2, max_semitones=2, p=0.5),
        # Time stretch (velocidad ligeramente distinta)
        TimeStretch(min_rate=0.92, max_rate=1.08, p=0.5),
        # Volume (más cerca / más lejos del mic)
        Gain(min_gain_db=-12, max_gain_db=6, p=0.7),
        # Ruido gaussiano (hiss del mic barato)
        AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.015, p=0.6),
        # Background noise de los negativos (TV, música, calle, etc.)
        AddBackgroundNoise(
            sounds_path=str(NEG_DIR),
            min_snr_db=3, max_snr_db=20,
            p=0.7,
        ),
        # Reverb de cuarto (eco)
        RoomSimulator(p=0.4),
    ])


def main():
    print("=== Wake word augmentation pipeline ===\n")

    # Verificar que hay positivos
    pos_files = sorted(POS_DIR.glob("*.wav"))
    if not pos_files:
        print(f"ERROR: No positive samples in {POS_DIR}.")
        print("Run scripts/01_generate_positive.py first.")
        return

    # Verificar que hay negativos para usar como background
    neg_files = list(NEG_DIR.rglob("*.wav"))
    if not neg_files:
        print(f"ERROR: No negative samples in {NEG_DIR}.")
        print("Run scripts/02_download_negative.py first.")
        return

    print(f"Positive samples: {len(pos_files)}")
    print(f"Negative samples (for background mix): {len(neg_files)}")
    print(f"Augmentations per positive: {N_AUGMENTATIONS_PER_SAMPLE}")
    print(f"Expected output: ~{len(pos_files) * N_AUGMENTATIONS_PER_SAMPLE} augmented samples\n")

    pipeline = build_augmentation_pipeline()

    failed = 0
    for pos_path in tqdm(pos_files, desc="Augmenting"):
        try:
            audio, sr = sf.read(pos_path)
            if sr != SR:
                # Resample si hace falta (piper a veces da 22050)
                from librosa import resample
                audio = resample(audio, orig_sr=sr, target_sr=SR)
                sr = SR
            # Mono
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            audio = audio.astype(np.float32)

            for i in range(N_AUGMENTATIONS_PER_SAMPLE):
                augmented = pipeline(samples=audio, sample_rate=sr)
                out_name = f"{pos_path.stem}_aug{i}.wav"
                out_path = AUG_DIR / out_name
                sf.write(out_path, augmented, sr)
        except Exception as e:
            failed += 1
            if failed < 5:
                print(f"\n  Warning: failed on {pos_path.name}: {e}")

    print(f"\nOK Done. {len(pos_files) * N_AUGMENTATIONS_PER_SAMPLE - failed} augmented samples")
    if failed:
        print(f"   ({failed} originals failed — check format / corrupt files)")
    print(f"\nNext: python scripts/04_train.py")


if __name__ == "__main__":
    main()
