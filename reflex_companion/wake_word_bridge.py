"""
wake_word_bridge.py — Comunicación entre el detector (thread Python) y
el State de Reflex (asyncio).

Por qué existe este módulo:

El detector (`wake_word.py:WakeWordDetector`) corre en un threading.Thread
nativo, fuera del event loop de asyncio. Cuando detecta "Ashley", necesita
avisar al backend de Reflex para que dispare la grabación STT en el frontend.

No podemos llamar directamente a métodos del State desde el thread del
detector — Reflex requiere mutaciones del state via `async with self:`
desde dentro de un event handler async. Tampoco podemos invocar
`rx.call_script()` desde un thread externo.

Solución: shared state thread-safe (un threading.Event + un counter), con
un poller en el lado de Reflex (`@rx.event(background=True)` async loop)
que chequea el evento cada 200ms y, si hay nueva detección, dispara
`rx.call_script("ashleyVoice._startRecording()")`.

Trade-off: latencia ~100-200ms extra desde la detección al inicio de
grabación. Imperceptible para el user (compara contra los ~500ms del
modelo de wake word per se + ~200ms de cold start del MediaRecorder).

API pública:
  - signal_detection(score) — llamado desde el detector thread
  - poll_detection() — llamado desde el State bg event, returns
    (detected: bool, score: float). Resetea el flag al consumirlo.
  - reset() — limpia el estado (usado al apagar el toggle)

Es módulo-singleton: el state se guarda en variables del módulo. No hay
race conditions porque las operaciones son atomic (Event.set/is_set/clear,
asignación de un float a una variable global de Python en CPython es atomic
gracias al GIL).
"""

from __future__ import annotations

import threading
from typing import Tuple

# ─────────────────────────────────────────
#  Estado interno del bridge
# ─────────────────────────────────────────

# Event que el detector "set"-ea cuando hay detección. El poller lo lee
# y limpia. Idempotente: múltiples set() antes de un poll = una sola
# detección visible (lo que es CORRECTO — durante el cooldown del
# detector ya filtramos múltiples activations consecutivas).
_event = threading.Event()

# Score de la última detección. Se actualiza atómicamente en el set()
# y se lee en el poll. Un float assignment es atomic en CPython.
_last_score: float = 0.0

# Counter total de detecciones (debug + monitoring). Útil para verificar
# que el bridge está funcionando sin tener que esperar al poll.
_detection_count: int = 0
_count_lock = threading.Lock()


# ─────────────────────────────────────────
#  API pública
# ─────────────────────────────────────────

def signal_detection(score: float) -> None:
    """Marca una detección. Llamado desde el thread del detector.

    Args:
        score: confianza de la detección (0.0 – 1.0)
    """
    global _last_score, _detection_count
    _last_score = float(score)
    with _count_lock:
        _detection_count += 1
    _event.set()


def poll_detection() -> Tuple[bool, float]:
    """Chequea si hay una detección pendiente. Si la hay, la consume.

    Returns:
        (detected, score). Si detected=True, score es el del último
        signal_detection. Si detected=False, score es 0.0.

    Llamado desde el State bg event. Idempotente: si llamas dos veces
    seguidas, la segunda devuelve False (a menos que el detector haya
    señalado entre medio).
    """
    if _event.is_set():
        score = _last_score
        _event.clear()
        return True, score
    return False, 0.0


def reset() -> None:
    """Limpia todo el estado. Llamado al apagar el wake word
    (toggle off) para asegurar que un signal_detection rezagado no
    dispare una grabación post-apagado."""
    global _last_score
    _event.clear()
    _last_score = 0.0


def detection_count() -> int:
    """Total de detecciones desde que el módulo se cargó. Útil para
    debug y telemetry — se puede mostrar en Settings."""
    with _count_lock:
        return _detection_count
