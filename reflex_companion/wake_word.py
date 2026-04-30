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
        use_vad: bool = True,
        vad_threshold: float = 0.3,
        consecutive_required: int = 1,
    ):
        """Crea el detector. Configuración:

        Args:
            model_path: ruta al .onnx (o .tflite) entrenado
            threshold: score mínimo del wake word (default 0.5)
            cooldown_seconds: tiempo mínimo entre detecciones consecutivas
            use_vad: si True, filtra audio con Voice Activity Detection
                antes de pasar al wake word.
            vad_threshold: score mínimo del VAD para procesar el chunk
                (0.0–1.0). Speech típico >0.5, ruido <0.1.
            consecutive_required: cuántos chunks CONSECUTIVOS deben tener
                score>=threshold antes de disparar el callback. Default
                1 (legacy: cualquier pico cuenta). Subir a 2-3 filtra
                impulsos cortos como estornudos / soplidos / golpes —
                "Ashley" real dura 400-700ms = ~5-9 chunks de 80ms,
                exigir 2 consecutivos rara vez pierde la palabra real
                pero descarta los burst <160ms.
        """
        self.model_path = Path(model_path)
        self.threshold = float(threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self.use_vad = bool(use_vad)
        self.vad_threshold = float(vad_threshold)
        self.consecutive_required = max(1, int(consecutive_required))

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[DetectionCallback] = None
        self._last_detection_at: float = 0.0
        self._paused: bool = False  # set True during manual recording
        self._lock = threading.Lock()
        # Contador de chunks consecutivos por encima del threshold.
        # Se resetea cada vez que un chunk cae bajo. Cuando alcanza
        # consecutive_required, se dispara el callback.
        self._consecutive_high: int = 0

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

    def pause(self) -> None:
        """Pausa el loop sin matar el thread. Mientras está paused, los
        chunks de audio se descartan (no se procesan ni disparan callback).
        Usado durante grabación manual del user — el JS captura el mic
        con MediaRecorder y no queremos que el wake word también consume
        recursos ni dispare un STT-en-medio-de-STT.
        """
        self._paused = True

    def resume(self) -> None:
        """Reanuda el loop después de un pause(). El detector vuelve a
        procesar chunks normalmente."""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

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
            # vad_threshold > 0 activa el filtrado interno de openwakeword
            # con silero_vad.onnx (~3 MB, ya descargado al training).
            # Cuando el VAD score < threshold, openwakeword devuelve 0.0
            # automáticamente sin invocar el modelo wake word — gratis FP
            # reduction en ambient noise.
            model = Model(
                wakeword_models=[str(self.model_path)],
                inference_framework=framework,
                vad_threshold=self.vad_threshold if self.use_vad else 0.0,
            )
        except Exception as e:
            log.warning("Wake word model failed to load (framework=%s): %s",
                        framework, e)
            return

        log.info("Wake word detector started (model=%s, threshold=%.2f, vad=%s)",
                 self.model_path.name, self.threshold,
                 f"on@{self.vad_threshold}" if self.use_vad else "off")

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

                    # Si el detector está pausado (user grabando manual),
                    # consumimos el audio para no overflowear el stream
                    # pero no lo procesamos ni disparamos callback.
                    if self._paused:
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
                        # Score bajo → reset del contador de consecutivos.
                        # Si había chunks altos previos, no eran sostenidos
                        # (impulso corto tipo estornudo) — descarta.
                        self._consecutive_high = 0
                        continue

                    # Score alto → incrementa contador.
                    self._consecutive_high += 1
                    if self._consecutive_high < self.consecutive_required:
                        # Necesitamos más chunks consecutivos antes de
                        # disparar. Esto filtra impulsos <160ms (sneeze,
                        # soplido, click de mouse cerca del mic) que no
                        # mantienen score alto durante 2+ chunks.
                        continue

                    # Cooldown — evita disparos múltiples por una sola
                    # palabra del user.
                    now = time.time()
                    if now - self._last_detection_at < self.cooldown_seconds:
                        continue
                    self._last_detection_at = now
                    # Reset para el siguiente trigger (después del cooldown)
                    self._consecutive_high = 0

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
