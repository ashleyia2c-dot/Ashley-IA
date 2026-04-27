"""Monkey-patch para `torchaudio.load` que evita la dependencia de torchcodec.

PyTorch 2.12 (nightly) movió el backend de carga de audio a torchcodec, que
en Windows requiere FFmpeg DLLs "full-shared" instaladas externamente. En
nuestro venv torchcodec no puede cargar libtorchcodec_core?.dll porque no
encuentra las dependencias FFmpeg.

Este patch sustituye `torchaudio.load` por una versión basada en `soundfile`
(que ya está en el venv vía librosa). Soundfile lee .wav y .flac sin
dependencias externas usando libsndfile que viene bundled con la wheel.

USO: importar este módulo ANTES de que openwakeword.data o cualquier código
que llame a torchaudio.load se ejecute. El patch es global del proceso.
"""

import logging

import numpy as np
import soundfile as sf
import torch
import torchaudio

_log = logging.getLogger(__name__)
_original_load = getattr(torchaudio, "load", None)


# Sample rate target. openwakeword (y la mayoría de modelos audio modernos)
# trabajan en 16 kHz. Piper-sample-generator genera a 22050 — sin resample
# en el load, openwakeword.data.augment_clips explota con
# `ValueError: Error! Clip does not have the correct sample rate!`.
_TARGET_SR = 16000


def _resample_to_16k(audio: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """Resamplea (channels, samples) a 16 kHz si hace falta.

    Usa scipy.signal.resample_poly que es rápido y suficientemente preciso
    para este caso (no necesitamos calidad audiophile). Si ya está a 16 kHz,
    no hace nada — return identical.
    """
    if sr == _TARGET_SR:
        return audio, sr
    from math import gcd
    # Reducir up/down al ratio más simple posible para que resample_poly
    # no haga cálculos enormes (e.g. 22050→16000 = 320/441 simplificado).
    g = gcd(_TARGET_SR, sr)
    up = _TARGET_SR // g
    down = sr // g
    from scipy.signal import resample_poly
    resampled = resample_poly(audio, up, down, axis=-1)
    return resampled.astype(audio.dtype), _TARGET_SR


def _load_with_soundfile(uri, frame_offset=0, num_frames=-1, normalize=True,
                          channels_first=True, format=None, buffer_size=4096):
    """Drop-in replacement de torchaudio.load con resample automático a 16 kHz.

    Returns:
        (waveform, sample_rate). waveform es torch.Tensor shape
        (channels, samples) si channels_first=True (default). sample_rate
        siempre será 16000 — los archivos a otro SR se resamplean transparentemente.
    """
    if hasattr(uri, "read"):
        audio, sr = sf.read(uri, dtype="float32")
    else:
        kwargs = {"dtype": "float32"}
        if frame_offset > 0:
            kwargs["start"] = frame_offset
        if num_frames > 0:
            kwargs["frames"] = num_frames
        audio, sr = sf.read(str(uri), **kwargs)

    # soundfile devuelve (samples,) para mono, (samples, channels) para multi
    if audio.ndim == 1:
        audio = audio[np.newaxis, :]  # (1, samples)
    else:
        audio = audio.T  # (channels, samples)

    # Resample a 16 kHz (no-op si ya está)
    audio, sr = _resample_to_16k(audio, sr)

    if not normalize:
        # soundfile normaliza int -> float automático cuando dtype='float32'.
        # Si el caller quería int crudo, escalamos de vuelta.
        audio = (audio * 32768).astype(np.int16)

    tensor = torch.from_numpy(np.ascontiguousarray(audio))
    if not channels_first:
        tensor = tensor.transpose(0, 1)
    return tensor, sr


def apply():
    """Aplica el patch. Idempotente — múltiples llamadas son no-op."""
    if getattr(torchaudio.load, "_is_soundfile_patch", False):
        return
    _load_with_soundfile._is_soundfile_patch = True
    torchaudio.load = _load_with_soundfile
    _log.info("torchaudio.load monkey-patched to use soundfile (avoiding torchcodec)")
    # NO llamamos _patch_openwakeword_trim_mmap aquí porque:
    # (a) sobreescribiría el fix directo aplicado a venv/.../data.py
    # (b) la función _patch en este módulo tiene exactamente el mismo
    #     código del fix directo, así que llamarla es redundante
    # El fix de trim_mmap vive solo en venv/.../openwakeword/data.py


def _patch_openwakeword_trim_mmap():
    """Parchea openwakeword.data.trim_mmap para que funcione en Windows.

    El bug original: trim_mmap abre el .npy con np.load(mmap_mode='r'),
    crea un nuevo .npy con datos trimmed, y luego hace os.remove(original).
    En Linux funciona porque permite borrar archivos abiertos. En Windows
    da WinError 32 'archivo está siendo utilizado por otro proceso' porque
    el mmap aún tiene el handle.

    Fix: liberar el mmap explícitamente (`del mmap_file1` + gc.collect()
    + mmap_file1._mmap.close()) antes del os.remove. Numpy memory-maps
    se cierran cuando el objeto se destruye, pero Windows necesita un
    flush ciclo de GC explícito para garantizarlo.
    """
    try:
        from openwakeword import data as _ow_data
    except ImportError:
        _log.info("openwakeword not yet imported, trim_mmap patch skipped")
        return

    if getattr(_ow_data.trim_mmap, "_is_windows_patch", False):
        return

    import os as _os
    import gc as _gc
    from numpy.lib.format import open_memmap as _open_memmap
    from tqdm import tqdm as _tqdm

    def trim_mmap_windows_safe(mmap_path):
        """Drop-in replacement de openwakeword.data.trim_mmap con cleanup
        explícito del mmap antes del os.remove."""
        # Identificar la última fila no-cero
        mmap_file1 = np.load(mmap_path, mmap_mode='r')
        i = -1
        while np.all(mmap_file1[i, :, :] == 0):
            i -= 1
        N_new = mmap_file1.shape[0] + i + 1

        # Crear el nuevo mmap (path .npy → .npy2)
        output_file2 = mmap_path.replace(".npy", "") + "2.npy"
        mmap_file2 = _open_memmap(
            output_file2, mode='w+', dtype=np.float32,
            shape=(N_new, mmap_file1.shape[1], mmap_file1.shape[2]),
        )

        # Copiar en batches
        for j in _tqdm(range(0, mmap_file1.shape[0], 1024),
                       total=mmap_file1.shape[0]//1024,
                       desc="Trimming empty rows"):
            if j + 1024 > N_new:
                mmap_file2[j:N_new] = mmap_file1[j:N_new].copy()
                mmap_file2.flush()
            else:
                mmap_file2[j:j+1024] = mmap_file1[j:j+1024].copy()
                mmap_file2.flush()

        # ── PATCH: liberar AMBOS mmaps antes del os.remove ──
        # Eliminar refs y forzar GC para que Python libere los handles
        # del SO. Sin esto, Windows mantiene los archivos lockeados.
        try:
            mmap_file1._mmap.close()
        except (AttributeError, BufferError):
            pass
        try:
            mmap_file2._mmap.close()
        except (AttributeError, BufferError):
            pass
        del mmap_file1
        del mmap_file2
        _gc.collect()
        # ────────────────────────────────────────────────────

        _os.remove(mmap_path)
        _os.rename(output_file2, mmap_path)

    trim_mmap_windows_safe._is_windows_patch = True
    _ow_data.trim_mmap = trim_mmap_windows_safe
    _log.info("openwakeword.data.trim_mmap patched for Windows")


# Aplicar al import — usage típico es `import _torchaudio_patch` antes de openwakeword.
apply()
