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


def _load_with_soundfile(uri, frame_offset=0, num_frames=-1, normalize=True,
                          channels_first=True, format=None, buffer_size=4096):
    """Drop-in replacement de torchaudio.load.

    Returns:
        (waveform, sample_rate). waveform es torch.Tensor shape
        (channels, samples) si channels_first=True (default).
    """
    if hasattr(uri, "read"):
        # File-like object
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

    if not normalize:
        # soundfile normaliza int -> float automático cuando dtype='float32'.
        # Si el caller quería int crudo, escalamos de vuelta. En la práctica
        # openwakeword no usa este flag.
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


# Aplicar al import — usage típico es `import _torchaudio_patch` antes de openwakeword.
apply()
