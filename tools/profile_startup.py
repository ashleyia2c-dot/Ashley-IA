"""
profile_startup.py — Mide el tiempo de cada fase del arranque de Ashley.

Objetivo: identificar dónde se va realmente el tiempo en on_load antes de
optimizar nada. "Optimizar sin medir es adivinar".

Qué NO incluye:
  - Llamadas a Grok (initial_fact_extraction, diary_entry, discovery) — son
    costosas por naturaleza y dependen de red; no tiene sentido optimizarlas
    desde la app (son latencia de LLM).
  - El rendering de Reflex (server-side React) — se mide en el navegador.

Cómo correr:
  cd reflex-companion
  venv/Scripts/python.exe tools/profile_startup.py

Salida: tabla con cada fase y su tiempo, más flagging de cuellos de botella.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Añadir el root del proyecto al path para que los imports funcionen.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Apuntar al data dir real del user para medir con datos reales.
# Si no existe, el script trabaja con defaults (sin historial).
default_data = Path(os.getenv("APPDATA", "")) / "ashley" / "data"
if default_data.exists():
    os.environ.setdefault("ASHLEY_DATA_DIR", str(default_data))

# ─────────────────────────────────────────────
#  Instrumentación
# ─────────────────────────────────────────────


class Phase:
    def __init__(self, name: str):
        self.name = name
        self.ms: float = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self.start) * 1000


phases: list[Phase] = []


def run_phase(name: str, fn):
    """Ejecuta `fn()` y guarda cuánto tardó. Captura excepciones sin detener el profiling."""
    p = Phase(name)
    try:
        with p:
            fn()
    except Exception as e:
        print(f"  ⚠ {name} falló: {type(e).__name__}: {e}")
    phases.append(p)


# ─────────────────────────────────────────────
#  Fases del arranque
# ─────────────────────────────────────────────


def profile_imports():
    """Primer import de reflex_companion — carga todos los submódulos pesados."""
    # reflex y xai-sdk son los dos grandes importantes.
    import reflex_companion.reflex_companion  # noqa: F401


def profile_migrations():
    from reflex_companion.migrations import migrate_if_needed
    migrate_if_needed()


def profile_load_language():
    from reflex_companion import i18n
    i18n.load_language()


def profile_load_voice_config():
    from reflex_companion import i18n
    i18n.load_voice_config()


def profile_load_chat():
    from reflex_companion.memory import load_json
    from reflex_companion.config import CHAT_FILE, MAX_HISTORY_MESSAGES
    raw = load_json(CHAT_FILE, [])
    _ = raw[-MAX_HISTORY_MESSAGES:]


def profile_load_facts():
    from reflex_companion.memory import load_json
    from reflex_companion.config import FACTS_FILE
    _ = load_json(FACTS_FILE, [])


def profile_load_diary():
    from reflex_companion.memory import load_json
    from reflex_companion.config import DIARY_FILE
    _ = load_json(DIARY_FILE, {"entries": [], "last_diary_at": ""})


def profile_load_tastes():
    from reflex_companion.tastes import load_tastes
    load_tastes()


def profile_load_affection():
    from reflex_companion.memory import load_json
    from reflex_companion.config import AFFECTION_FILE
    _ = load_json(AFFECTION_FILE, {"level": 50})


def profile_load_achievements():
    from reflex_companion.achievements import load_achievements
    load_achievements()


def profile_load_stats():
    from reflex_companion import stats as _stats
    _stats.load_stats()


def profile_whisper_warmup():
    """Whisper lazy-load del modelo. Esta es la operación más pesada si no está cacheado."""
    from reflex_companion.whisper_stt import warmup
    warmup()


def profile_reset_youtube():
    from reflex_companion.actions import reset_youtube_hwnd
    reset_youtube_hwnd()


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  Ashley startup profiler")
    print("=" * 60)
    print(f"Data dir: {os.environ.get('ASHLEY_DATA_DIR', '(none — using dev relative paths)')}")
    print()

    # Import es una fase aparte (una-sola-vez, cache de Python)
    print("Profiling cold import...")
    run_phase("import reflex_companion (first)", profile_imports)
    print(f"  -> {phases[-1].ms:.1f} ms")
    print()

    print("Profiling individual phases...")

    run_phase("migrate_if_needed", profile_migrations)
    run_phase("load_language", profile_load_language)
    run_phase("load_voice_config", profile_load_voice_config)
    run_phase("load chat history (JSON)", profile_load_chat)
    run_phase("load facts (JSON)", profile_load_facts)
    run_phase("load diary (JSON)", profile_load_diary)
    run_phase("load tastes (JSON)", profile_load_tastes)
    run_phase("load affection (JSON)", profile_load_affection)
    run_phase("load achievements (JSON)", profile_load_achievements)
    run_phase("load stats (HMAC + registry)", profile_load_stats)
    run_phase("reset_youtube_hwnd (actions)", profile_reset_youtube)
    run_phase("whisper warmup", profile_whisper_warmup)

    # ─────────────────────────────────────────────
    #  Report
    # ─────────────────────────────────────────────

    print()
    print("=" * 60)
    print(f"  {'Phase':<40s} {'Time (ms)':>12s}")
    print("-" * 60)

    total = 0.0
    for p in phases:
        # flag bottleneck: > 100 ms
        flag = " [SLOW]" if p.ms > 500 else (" [warn]" if p.ms > 100 else "")
        print(f"  {p.name:<40s} {p.ms:>10.1f}{flag}")
        total += p.ms

    print("-" * 60)
    print(f"  {'TOTAL':<40s} {total:>10.1f}")
    print("=" * 60)

    # ─────────────────────────────────────────────
    #  Heuristics / recommendations
    # ─────────────────────────────────────────────

    bottlenecks = [p for p in phases if p.ms > 100]
    if bottlenecks:
        print()
        print("Bottlenecks detectados (>100ms):")
        for p in bottlenecks:
            print(f"  • {p.name}: {p.ms:.1f} ms")
    else:
        print()
        print("[OK] Ningun cuello de botella >100ms detectado en I/O.")

    # Mensaje específico sobre whisper
    whisper = next((p for p in phases if "whisper" in p.name), None)
    if whisper and whisper.ms > 1000:
        print()
        print(f"[warn] Whisper warmup es {whisper.ms:.0f} ms -- ya esta en background en on_load,")
        print("  pero si se siente lento considerar lazy-load aun mas tarde (al primer")
        print("  click de mic en vez de al arrancar).")


if __name__ == "__main__":
    main()
