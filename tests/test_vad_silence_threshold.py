"""Test para el threshold de silencio del VAD (Voice Activity Detection).

El VAD vive en assets/ashley_voice.js y controla cuántos segundos de
silencio espera el sistema antes de cortar la grabación y enviar el
mensaje al backend.

Antes era 3s; el user pidió 2s para que el envío sea más reactivo.

Si alguien lo sube a >3s sin razón documentada, el flujo de voz se
siente "lento" — el user calla y tiene que esperar varios segundos para
que el mensaje se envíe. Este test bloquea esa regresión.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ASHLEY_VOICE_JS = REPO_ROOT / "assets" / "ashley_voice.js"


@pytest.fixture(scope="module")
def voice_js() -> str:
    return ASHLEY_VOICE_JS.read_text(encoding="utf-8")


def test_vad_silence_threshold_at_most_2_seconds(voice_js):
    """_VAD_SILENCE_SECS no debe ser mayor que 2 — el user lo pidió a 2s
    para que el envío sea reactivo cuando el user para de hablar.
    """
    match = re.search(
        r"_VAD_SILENCE_SECS\s*:\s*(\d+(?:\.\d+)?)",
        voice_js,
    )
    assert match, "No se encontró _VAD_SILENCE_SECS en ashley_voice.js"
    value = float(match.group(1))
    assert value <= 2, (
        f"_VAD_SILENCE_SECS={value}; debe ser <=2 segundos. Valor mayor "
        f"hace que el sistema espere demasiado antes de enviar el mensaje "
        f"tras que el user pare de hablar — feel laggy."
    )


def test_vad_silence_threshold_above_zero(voice_js):
    """No debe ser 0 ni negativo (eso cortaría la grabación al instante)."""
    match = re.search(
        r"_VAD_SILENCE_SECS\s*:\s*(\d+(?:\.\d+)?)",
        voice_js,
    )
    assert match
    value = float(match.group(1))
    assert value >= 1, (
        f"_VAD_SILENCE_SECS={value}; debe ser >=1 segundo. Menos corta "
        f"a mitad de pausa natural ('eh...', 'pues...', '...').".replace("Â", "")
    )
