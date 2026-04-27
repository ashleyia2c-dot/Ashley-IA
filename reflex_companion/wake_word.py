"""
wake_word.py — Detector de wake word "Ashley" con OpenWakeWord.

Mantiene un loop de mic en background que escucha continuamente buscando la
palabra "Ashley". Cuando la detecta con score >= threshold, dispara un
callback síncrono — el caller decide qué hacer (típicamente: empezar la
grabación STT que ya tiene Ashley implementada).

ESTADO ACTUAL (2026-04-28): este módulo está SCAFFOLDED pero NO CONECTADO
al state de Ashley todavía. Para integrarlo, hay que:
  1. Tener `wake_word_training/output/ashley/ashley.onnx` (preferido) o
     `ashley.tflite` — ver wake_word_training/README.md. El training de
     openwakeword exporta ambos formatos automáticamente.
  2. Copiarlo a `reflex_companion/wake_word/ashley.onnx`
  3. Instalar `openwakeword` (~5 MB) y `sounddevice` (~2 MB) en el venv
     principal de Ashley. Onnxruntime YA está (lo trae faster-whisper),
     así que NO hay que añadir un runtime de inferencia.
  4. Añadir `wake_word_enabled: bool = False` a State y un toggle UI
  5. En el handler del toggle, instanciar WakeWordDetector y conectar el
     callback al método que arranca grabación
  6. Pausar el detector mientras el user está grabando manualmente (el mic
     no se puede compartir entre RawInputStream y MediaRecorder del front)

INFERENCE BACKEND:
  Aceptamos modelos `.onnx` y `.tflite`. Default preferido es `.onnx`
  porque su runtime (onnxruntime, ~30 MB) ya está en el venv de Ashley.
  Para `.tflite` haría falta añadir `tflite_runtime` (~2 MB) — opción
  válida si el modelo .tflite resulta más rápido en CPU x86.

  TensorFlow completo NO se necesita. Solo es para training (en
  `wake_word_training/`, venv separado). Inferencia con openwakeword
  usa onnxruntime o tflite_runtime, no TF.

INTERACCIÓN CON EL MIC ACTUAL:
  - Ashley actualmente captura mic vía MediaRecorder en el browser/Electron
    (assets/ashley_voice.js). Eso es a nivel JS, distinto del Python backend.
  - Este detector usa sounddevice → PortAudio → mic del SO. Es otro
    consumer del mic.
  - Windows permite múltiples consumers del mismo mic (a diferencia de
    macOS), pero hay race conditions: si MediaRecorder está activo y este
    detector también, ambos reciben audio pero pueden timing-out o
    bufferear distinto. La solución correcta es: PAUSAR el detector
    cuando el user pulse el botón de grabar. Eso lo hace el integrator
    via .stop() / .start() en los eventos de start/stop_recording.

DEPS (lazy):
  - openwakeword: framework + carga del modelo
  - sounddevice: captura mic
  - onnxruntime O tflite_runtime: backend de inferencia (depende del
    formato del modelo). onnxruntime ya está en Ashley.
  - numpy: ya está como dep transitiva de Reflex

Si las deps no están, `is_available()` devuelve False y start() es un no-op
con warning. Esto deja la importación del módulo segura aunque el venv no
tenga las deps de wake word — útil porque los desarrolladores que no
trabajan en esta feature no necesitan los ~10 MB extra.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger("ashley.wake_word")


# ─────────────────────────────────────────
#  Config
# ─────────────────────────────────────────

# Chunk de audio que OpenWakeWord espera (80 ms a 16 kHz).
# El modelo procesa de a 80 ms y mantiene state interno entre chunks.
SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1280

# Threshold default. Un score por encima de esto cuenta como detección.
# 0.5 es el sweet spot inicial — el calibrado fino se hace en
# wake_word_training/scripts/05_test.py midiendo FRR/FAR.
DEFAULT_THRESHOLD = 0.5

# Cooldown post-detección. Sin esto, un solo "ashley" del user puede
# disparar 3-5 callbacks consecutivos porque el modelo mantiene score alto
# durante ~500 ms. Con 1.5s de cooldown, una sola detección humana
# corresponde a una sola llamada al callback.
COOLDOWN_SECONDS = 1.5


# ─────────────────────────────────────────
#  Disponibilidad de deps
# ─────────────────────────────────────────

def is_available() -> tuple[bool, str]:
    """¿Están instaladas las deps base necesarias para correr el detector?

    Solo checa openwakeword + sounddevice. El backend de inferencia
    (onnxruntime o tflite_runtime) se valida en start() según el formato
    del modelo — si tienes onnxruntime y un .tflite, openwakeword caerá
    automáticamente al .onnx equivalente si existe.

    Returns:
        (ok, reason). Si ok=True, reason es vacío. Si ok=False, reason
        explica qué falta. El caller puede mostrar reason al user.
    """
    try:
        import openwakeword  # noqa: F401
    except ImportError:
        return False, "openwakeword no instalado. pip install openwakeword"
    try:
        import sounddevice  # noqa: F401
    except ImportError:
        return False, "sounddevice no instalado. pip install sounddevice"
    return True, ""


def _inference_framework_for(model_path: Path) -> str:
    """Devuelve 'onnx' o 'tflite' según la extensión. Es lo que espera
    openwakeword.Model en su kwarg `inference_framework`."""
    if model_path.suffix.lower() == ".onnx":
        return "onnx"
    return "tflite"


# ─────────────────────────────────────────
#  Detector
# ─────────────────────────────────────────

DetectionCallback = Callable[[float], None]
"""Tipo del callback. Recibe el score de detección (0.0–1.0)."""


class WakeWordDetector:
    """Detector de wake word con loop de mic en background.

    Uso típico:

        det = WakeWordDetector(model_path="path/to/ashley.tflite")
        det.start(callback=lambda score: print(f"detected! ({score:.2f})"))
        # ... el detector corre en background ...
        det.stop()

    Thread safety: start/stop se pueden llamar desde cualquier thread. El
    callback siempre se invoca desde el thread interno del detector — el
    caller debe hacer dispatch al main thread si actualiza UI/state.

    Idempotencia: start() en un detector ya corriendo es no-op. stop() en
    un detector parado es no-op.
    """

    def __init__(
        self,
        model_path: str | Path,
        threshold: float = DEFAULT_THRESHOLD,
        cooldown_seconds: float = COOLDOWN_SECONDS,
    ):
        self.model_path = Path(model_path)
        self.threshold = float(threshold)
        self.cooldown_seconds = float(cooldown_seconds)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[DetectionCallback] = None
        self._last_detection_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, callback: DetectionCallback) -> tuple[bool, str]:
        """Empieza el loop. Returns (ok, reason). Si ok=False, no se
        empezó (callback nunca se invocará)."""
        with self._lock:
            if self.is_running:
                return False, "Ya está corriendo"
            ok, reason = is_available()
            if not ok:
                return False, reason
            if not self.model_path.exists():
                return False, f"No existe el modelo: {self.model_path}"

            self._callback = callback
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="wake-word-detector",
                daemon=True,
            )
            self._thread.start()
        return True, ""

    def stop(self, timeout: float = 2.0) -> bool:
        """Detiene el loop. Returns True si paró limpio, False si el
        thread no respondió en `timeout` segundos."""
        with self._lock:
            if not self.is_running:
                return True
            self._stop_event.set()
            t = self._thread
        if t is not None:
            t.join(timeout=timeout)
        return not (t is not None and t.is_alive())

    # ─────────────────────────────────────
    #  Loop interno (thread separado)
    # ─────────────────────────────────────

    def _loop(self):
        """Loop principal. Captura mic en chunks de 80ms y los pasa al
        modelo. Cuando detecta wake word con score >= threshold y pasó
        el cooldown, invoca callback."""
        import time
        try:
            import sounddevice as sd
            import numpy as np
            from openwakeword.model import Model
        except ImportError as e:
            log.warning("Wake word deps missing inside thread: %s", e)
            return

        framework = _inference_framework_for(self.model_path)
        try:
            model = Model(
                wakeword_models=[str(self.model_path)],
                inference_framework=framework,
            )
        except Exception as e:
            log.warning("Wake word model failed to load (framework=%s): %s",
                        framework, e)
            return

        log.info("Wake word detector started (model=%s, threshold=%.2f)",
                 self.model_path.name, self.threshold)

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SAMPLES,
            ) as stream:
                while not self._stop_event.is_set():
                    try:
                        # read() bloquea hasta tener CHUNK_SAMPLES.
                        # Devuelve (data, overflowed). Ignoramos overflowed
                        # — un overflow puntual no rompe la detección.
                        data, _overflowed = stream.read(CHUNK_SAMPLES)
                    except Exception as e:
                        log.warning("Mic read error: %s — retrying", e)
                        time.sleep(0.1)
                        continue

                    # data shape: (CHUNK_SAMPLES, 1). Aplanamos.
                    audio = np.asarray(data).flatten()

                    try:
                        scores = model.predict(audio)
                    except Exception as e:
                        log.warning("Inference error: %s — retrying", e)
                        time.sleep(0.05)
                        continue

                    # scores es dict {wakeword_name: score}. Tomamos el
                    # max — para un modelo de 1 wakeword (Ashley) solo
                    # hay 1 entrada, pero esto futurea soportar múltiples.
                    if not scores:
                        continue
                    max_score = max(scores.values())

                    if max_score < self.threshold:
                        continue

                    # Cooldown — evita disparos múltiples por una sola
                    # palabra del user.
                    now = time.time()
                    if now - self._last_detection_at < self.cooldown_seconds:
                        continue
                    self._last_detection_at = now

                    log.info("Wake word detected (score=%.3f)", max_score)
                    cb = self._callback
                    if cb is not None:
                        try:
                            cb(float(max_score))
                        except Exception as e:
                            log.warning("Callback raised: %s", e)
        except Exception as e:
            log.warning("Wake word loop crashed: %s", e)
        finally:
            log.info("Wake word detector stopped")
