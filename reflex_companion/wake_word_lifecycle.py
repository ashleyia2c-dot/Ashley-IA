"""
wake_word_lifecycle.py — Manejo del ciclo de vida del detector.

El detector (`WakeWordDetector`) tiene que vivir como singleton del
proceso, fuera del State de Reflex (que se recrea por cada sesión / tab
abierta). Este módulo provee start/stop/pause/resume thread-safe del
detector global.

Flujo típico:
  - User activa el toggle "Wake word" en Settings
    → State llama `start_detector()` que:
        1. verifica que el modelo .onnx existe
        2. verifica que las deps están instaladas
        3. instancia WakeWordDetector si no existe
        4. arranca el thread del detector
  - User pulsa el botón de mic para grabar manualmente
    → JS hace POST a `/api/wake_word_pause` que llama `pause_detector()`
  - User suelta el botón / la grabación termina
    → JS hace POST a `/api/wake_word_resume` que llama `resume_detector()`
  - User desactiva el toggle
    → State llama `stop_detector()` que para el thread y libera el mic

API:
  - start_detector(model_path, threshold, ...) → (ok, reason)
  - stop_detector() → bool
  - pause_detector() → None
  - resume_detector() → None
  - is_running() → bool
  - is_paused() → bool

El callback de detección está hardcoded a `wake_word_bridge.signal_detection`
— el caller (State) polea el bridge en su bg event loop. Esto desacopla
completamente el detector (thread Python) del State (asyncio Reflex).
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from . import wake_word, wake_word_bridge

log = logging.getLogger("ashley.wake_word.lifecycle")

# Singleton del detector. Se inicializa lazy en start_detector().
# El _lock protege la mutación de _detector — los métodos pause/resume/stop
# son llamados desde múltiples threads (Starlette HTTP handler, Reflex
# bg event, etc.).
_detector: Optional[wake_word.WakeWordDetector] = None
_lock = threading.Lock()


# ─────────────────────────────────────────
#  API pública
# ─────────────────────────────────────────

def start_detector(
    model_path: str | Path,
    threshold: float = 0.5,
    cooldown_seconds: float = 1.5,
    use_vad: bool = True,
) -> tuple[bool, str]:
    """Arranca el detector con los parámetros dados.

    Si ya estaba corriendo (e.g. el user toggleó OFF→ON sin que el
    OFF se procesara), lo paramos y reiniciamos con los nuevos params.

    Returns:
        (ok, reason). ok=True si el detector está corriendo después de
        esta llamada. reason explica el motivo si ok=False.
    """
    global _detector

    with _lock:
        # Si ya hay uno corriendo, lo paramos para reiniciar con params nuevos
        if _detector is not None and _detector.is_running:
            log.info("Detector ya corriendo — reiniciando con nuevos params")
            _detector.stop()
            _detector = None

        # Reset bridge para no consumir signals stale del detector anterior
        wake_word_bridge.reset()

        # Asegurar feature extraction models (melspectrogram, embedding,
        # silero_vad). openwakeword no los incluye en el pip package — los
        # descarga on-demand desde GitHub releases (~5 MB total, una sola
        # vez por venv). Sin esto, AudioFeatures crashea con NO_SUCHFILE.
        try:
            from openwakeword.utils import download_models
            download_models([])  # solo features, no wake words pre-trained
        except Exception as e:
            log.warning("download_models failed: %s — detector puede crashear", e)

        det = wake_word.WakeWordDetector(
            model_path=model_path,
            threshold=threshold,
            cooldown_seconds=cooldown_seconds,
            use_vad=use_vad,
        )
        ok, reason = det.start(
            callback=lambda score: wake_word_bridge.signal_detection(score),
        )
        if not ok:
            log.warning("start_detector failed: %s", reason)
            return False, reason

        _detector = det
        log.info("Wake word detector started (path=%s, threshold=%.2f)",
                 model_path, threshold)
        return True, ""


def stop_detector(timeout: float = 2.0) -> bool:
    """Detiene el detector y libera el mic.

    Returns:
        True si paró limpio (o no estaba corriendo). False si el thread
        no respondió en `timeout`.
    """
    global _detector
    with _lock:
        if _detector is None or not _detector.is_running:
            wake_word_bridge.reset()
            return True
        ok = _detector.stop(timeout=timeout)
        wake_word_bridge.reset()
        if ok:
            _detector = None
            log.info("Wake word detector stopped")
        else:
            log.warning("Detector thread no paró en %ss", timeout)
        return ok


def pause_detector() -> None:
    """Pausa el detector sin matar el thread. El audio se sigue
    consumiendo del mic pero los chunks se descartan en lugar de
    procesarse. Ideal para evitar conflicto cuando el user inicia
    grabación manual con el botón mic."""
    with _lock:
        if _detector is not None and _detector.is_running:
            _detector.pause()
            log.info("Wake word detector paused")


def resume_detector() -> None:
    """Reanuda el detector después de un pause(). El próximo chunk se
    procesa normalmente."""
    with _lock:
        if _detector is not None and _detector.is_running:
            _detector.resume()
            log.info("Wake word detector resumed")


def is_running() -> bool:
    """¿Está el detector activo y procesando audio?"""
    with _lock:
        return _detector is not None and _detector.is_running


def is_paused() -> bool:
    """¿Está paused (running pero descartando chunks)?"""
    with _lock:
        return _detector is not None and _detector.is_paused
