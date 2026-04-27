"""Tests para reflex_companion/wake_word.py.

Estos tests NO requieren openwakeword ni sounddevice instalados — todos los
imports de esas libs están mockeados con sys.modules patching antes de que
el thread del detector intente importarlas.

Foco de los tests:
  - El módulo importa limpio sin deps (invariante crítico)
  - is_available() reporta correctamente
  - start() falla limpio cuando faltan deps o modelo
  - El loop interno detecta cuando score >= threshold y respeta cooldown
  - stop() para el thread limpio
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path
from unittest import mock

import pytest

from reflex_companion import wake_word


# ══════════════════════════════════════════════════════════════════════
#  Imports / availability
# ══════════════════════════════════════════════════════════════════════

def test_module_imports_without_deps():
    """El módulo wake_word debe poder importarse aunque openwakeword y
    sounddevice no estén instalados. Esto preserva el invariante de
    'la gente que no usa esta feature no necesita instalar 600 MB'."""
    # Si la línea `import wake_word` arriba falló, este test ni siquiera
    # se ejecutaría. Llegar aquí ya es éxito.
    assert hasattr(wake_word, "WakeWordDetector")
    assert hasattr(wake_word, "is_available")


def test_is_available_returns_tuple_of_bool_and_str():
    ok, reason = wake_word.is_available()
    assert isinstance(ok, bool)
    assert isinstance(reason, str)
    if not ok:
        assert reason  # debe explicar qué falta


def test_inference_framework_for_extension():
    """El detector elige onnx vs tflite según la extensión del modelo —
    eso determina qué runtime se usa (onnxruntime ya está en Ashley,
    tflite_runtime sería dep extra)."""
    assert wake_word._inference_framework_for(Path("ashley.onnx")) == "onnx"
    assert wake_word._inference_framework_for(Path("ashley.tflite")) == "tflite"
    # Default cuando la extensión no match — caemos a tflite (el default
    # de openwakeword)
    assert wake_word._inference_framework_for(Path("ashley.bin")) == "tflite"
    # Case-insensitive
    assert wake_word._inference_framework_for(Path("ashley.ONNX")) == "onnx"


# ══════════════════════════════════════════════════════════════════════
#  Construcción del detector
# ══════════════════════════════════════════════════════════════════════

def test_detector_initial_state(tmp_path):
    det = wake_word.WakeWordDetector(model_path=tmp_path / "fake.tflite")
    assert det.is_running is False
    assert det.threshold == wake_word.DEFAULT_THRESHOLD
    assert det.cooldown_seconds == wake_word.COOLDOWN_SECONDS


def test_detector_custom_threshold(tmp_path):
    det = wake_word.WakeWordDetector(
        model_path=tmp_path / "fake.tflite",
        threshold=0.7,
        cooldown_seconds=3.0,
    )
    assert det.threshold == 0.7
    assert det.cooldown_seconds == 3.0


# ══════════════════════════════════════════════════════════════════════
#  start() failure modes
# ══════════════════════════════════════════════════════════════════════

def test_start_fails_when_deps_missing(tmp_path, monkeypatch):
    """Si openwakeword/sounddevice no están, start debe devolver
    (False, reason) sin lanzar el thread."""
    monkeypatch.setattr(wake_word, "is_available",
                        lambda: (False, "fake missing"))
    det = wake_word.WakeWordDetector(model_path=tmp_path / "fake.tflite")
    ok, reason = det.start(callback=lambda s: None)
    assert ok is False
    assert "fake missing" in reason
    assert det.is_running is False


def test_start_fails_when_model_file_missing(tmp_path, monkeypatch):
    """Si el .tflite no existe, start debe devolver (False, reason)."""
    monkeypatch.setattr(wake_word, "is_available", lambda: (True, ""))
    det = wake_word.WakeWordDetector(
        model_path=tmp_path / "does-not-exist.tflite",
    )
    ok, reason = det.start(callback=lambda s: None)
    assert ok is False
    assert "No existe el modelo" in reason
    assert det.is_running is False


def test_start_idempotent(tmp_path, monkeypatch):
    """start() en un detector ya corriendo es no-op (devuelve False)."""
    # Mockear is_available + creamos un dummy model file
    monkeypatch.setattr(wake_word, "is_available", lambda: (True, ""))
    model_path = tmp_path / "ashley.tflite"
    model_path.write_bytes(b"\x00" * 100)

    det = wake_word.WakeWordDetector(model_path=model_path)
    # Forzamos is_running True manualmente para evitar el thread real
    fake_thread = mock.MagicMock()
    fake_thread.is_alive.return_value = True
    det._thread = fake_thread

    ok, reason = det.start(callback=lambda s: None)
    assert ok is False
    assert "Ya está corriendo" in reason


def test_stop_when_not_running(tmp_path):
    """stop() en un detector parado es no-op (returns True)."""
    det = wake_word.WakeWordDetector(model_path=tmp_path / "fake.tflite")
    assert det.stop() is True


# ══════════════════════════════════════════════════════════════════════
#  Loop interno con mocks
# ══════════════════════════════════════════════════════════════════════
#
# Mockeamos openwakeword.model.Model y sounddevice via sys.modules patch.
# El detector importa esas libs DENTRO de _loop() — al patchar sys.modules
# antes de que start() arranque el thread, el import dentro del loop
# encuentra los mocks.

def _make_fake_modules(scores_sequence):
    """Construye fake openwakeword y sounddevice modules.

    scores_sequence: lista de dicts {wakeword: score} — uno por cada chunk
    que el modelo procesa. Cuando se agota la secuencia, el loop sigue
    recibiendo el último score (para no romper el while infinito).
    """
    import numpy as np

    # ── Fake openwakeword ──────────────────────────────────────
    fake_oww = mock.MagicMock()
    fake_model_class = mock.MagicMock()

    state = {"i": 0}

    def predict(audio_chunk):
        i = state["i"]
        if i < len(scores_sequence):
            state["i"] = i + 1
            return scores_sequence[i]
        # Una vez agotada la secuencia, devolvemos un score bajo
        # para no disparar más callbacks
        return {"ashley": 0.0}

    fake_model_instance = mock.MagicMock()
    fake_model_instance.predict.side_effect = predict
    fake_model_class.return_value = fake_model_instance
    fake_oww.model.Model = fake_model_class

    # ── Fake sounddevice ───────────────────────────────────────
    fake_sd = mock.MagicMock()
    fake_stream = mock.MagicMock()
    # read() devuelve (audio, overflowed)
    fake_stream.read.return_value = (
        np.zeros((wake_word.CHUNK_SAMPLES, 1), dtype="int16"), False,
    )
    # InputStream() debe ser usable como context manager
    fake_input_stream = mock.MagicMock()
    fake_input_stream.__enter__ = mock.MagicMock(return_value=fake_stream)
    fake_input_stream.__exit__ = mock.MagicMock(return_value=False)
    fake_sd.InputStream = mock.MagicMock(return_value=fake_input_stream)

    return fake_oww, fake_sd


def _patch_audio_libs(monkeypatch, scores_sequence):
    """Inyecta fake openwakeword y sounddevice en sys.modules para que el
    thread del detector los encuentre."""
    fake_oww, fake_sd = _make_fake_modules(scores_sequence)
    monkeypatch.setitem(sys.modules, "openwakeword", fake_oww)
    monkeypatch.setitem(sys.modules, "openwakeword.model", fake_oww.model)
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)
    # is_available debe pasar — los imports en sus checks ahora resuelven
    # a los mocks
    monkeypatch.setattr(wake_word, "is_available", lambda: (True, ""))


def test_callback_invoked_when_score_above_threshold(tmp_path, monkeypatch):
    """Cuando el modelo devuelve score >= threshold, callback se invoca
    con ese score."""
    _patch_audio_libs(monkeypatch, [
        {"ashley": 0.1},   # bajo — no callback
        {"ashley": 0.85},  # alto — debe callback
    ])

    model_path = tmp_path / "ashley.tflite"
    model_path.write_bytes(b"\x00" * 100)

    received = []
    detected_event = threading.Event()

    def on_detect(score):
        received.append(score)
        detected_event.set()

    det = wake_word.WakeWordDetector(model_path=model_path, threshold=0.5)
    ok, reason = det.start(callback=on_detect)
    assert ok, reason

    # Esperamos a que detecte (timeout corto — los mocks son síncronos)
    assert detected_event.wait(timeout=2.0), "Callback no se invocó a tiempo"
    det.stop()

    assert len(received) >= 1
    assert received[0] >= 0.5


def test_callback_not_invoked_when_score_below_threshold(tmp_path, monkeypatch):
    """Si todos los scores son < threshold, callback nunca se invoca."""
    # Le damos solo scores bajos
    _patch_audio_libs(monkeypatch, [{"ashley": 0.1}] * 10)

    model_path = tmp_path / "ashley.tflite"
    model_path.write_bytes(b"\x00" * 100)

    received = []
    det = wake_word.WakeWordDetector(model_path=model_path, threshold=0.5)
    ok, reason = det.start(callback=lambda s: received.append(s))
    assert ok, reason

    # Le damos tiempo a procesar varios chunks
    time.sleep(0.3)
    det.stop()

    assert received == []


def test_cooldown_prevents_double_trigger(tmp_path, monkeypatch):
    """Dos scores altos consecutivos en menos de cooldown_seconds = un
    solo callback. Sin cooldown, el modelo dispararía 5+ veces por una
    sola palabra del user."""
    # 5 chunks consecutivos con score alto
    _patch_audio_libs(monkeypatch, [{"ashley": 0.9}] * 5)

    model_path = tmp_path / "ashley.tflite"
    model_path.write_bytes(b"\x00" * 100)

    received = []
    det = wake_word.WakeWordDetector(
        model_path=model_path,
        threshold=0.5,
        cooldown_seconds=10.0,  # cooldown largo: solo el primer trigger pasa
    )
    ok, reason = det.start(callback=lambda s: received.append(s))
    assert ok, reason

    time.sleep(0.3)
    det.stop()

    assert len(received) == 1, f"Esperado 1 callback con cooldown, hubo {len(received)}"


def test_stop_returns_quickly(tmp_path, monkeypatch):
    """stop() debe parar el thread en pocos cientos de ms — no quedarse
    colgado esperando un read del mic. El stop_event se chequea cada
    iteración."""
    _patch_audio_libs(monkeypatch, [{"ashley": 0.0}] * 100)

    model_path = tmp_path / "ashley.tflite"
    model_path.write_bytes(b"\x00" * 100)

    det = wake_word.WakeWordDetector(model_path=model_path)
    ok, reason = det.start(callback=lambda s: None)
    assert ok, reason

    t0 = time.time()
    stopped_clean = det.stop(timeout=2.0)
    elapsed = time.time() - t0

    assert stopped_clean, "stop() no paró el thread limpio"
    assert elapsed < 2.0, f"stop() tardó {elapsed:.2f}s — demasiado"
    assert det.is_running is False
