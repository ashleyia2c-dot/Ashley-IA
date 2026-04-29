"""
profile_first_message.py — Mide cuánto tarda la fase PRE-stream del primer
mensaje del user (auto_actions=ON), que es donde el user reporta 20s de
espera.

Diferencia con profile_startup.py: ese mide el on_load (cold import, JSON
loads). Este mide lo que pasa entre que el user manda un mensaje y empieza
a streamear el LLM:

  • Captura de pantalla
  • Snapshot del estado del sistema (volumen, ventana activa) — pycaw
  • Lista de ventanas abiertas + UI Automation tabs del navegador
  • Regeneración de preoccupation (si está vencida) — LLM call
  • Compresión de historial (si >20 msgs y caché stale) — LLM call
  • Build del system_prompt completo

NO llama al LLM principal — solo mide la fase de preparación. Para el TTFT
del LLM hay log "stream TTFT=..." en _streaming_loop ya integrado.

Cómo correr:
  venv/Scripts/python.exe tools/profile_first_message.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

default_data = Path(os.getenv("APPDATA", "")) / "ashley" / "data"
if default_data.exists():
    os.environ.setdefault("ASHLEY_DATA_DIR", str(default_data))


def measure(name, fn):
    t0 = time.perf_counter()
    try:
        fn()
        ms = (time.perf_counter() - t0) * 1000
        print(f"  {name:<55s} {ms:>8.1f} ms")
        return ms
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        print(f"  {name:<55s} {ms:>8.1f} ms  [FAIL: {type(e).__name__}: {e}]")
        return ms


def main():
    print("=" * 72)
    print("  Profile: PRE-stream phase del primer user message (Acciones=ON)")
    print("=" * 72)
    print(f"Data dir: {os.environ.get('ASHLEY_DATA_DIR', '(none)')}")
    print()

    # Cargamos estado real del user (history, facts, diary, tastes)
    from reflex_companion.memory import load_json, ensure_facts, ensure_ids
    from reflex_companion.config import (
        CHAT_FILE, FACTS_FILE, DIARY_FILE, MAX_HISTORY_MESSAGES,
    )
    from reflex_companion.tastes import load_tastes

    raw_messages = load_json(CHAT_FILE, [])
    messages = ensure_ids(raw_messages[-MAX_HISTORY_MESSAGES:])
    facts = ensure_facts(load_json(FACTS_FILE, []))
    diary_data = load_json(DIARY_FILE, {"entries": [], "last_diary_at": ""})
    diary = diary_data.get("entries", [])
    tastes = load_tastes()

    print(f"State real cargado: {len(messages)} messages, {len(facts)} facts,")
    print(f"                    {len(diary)} diary entries, {len(tastes)} tastes")
    print()
    print("─── Operaciones del PC (Acciones=ON las dispara) ───")

    total = 0.0

    # 1. Screenshot
    def _screenshot():
        from reflex_companion.actions import take_screenshot_low_res
        take_screenshot_low_res()
    total += measure("take_screenshot_low_res()", _screenshot)

    # 2. State snapshot (pycaw + foreground window)
    def _state_snap():
        from reflex_companion.system_state import get_state_snapshot
        get_state_snapshot()
    total += measure("get_state_snapshot() #1 (pycaw + Win API)", _state_snap)
    total += measure("get_state_snapshot() #2 (mismo turno, sin caché)", _state_snap)

    # 3. System state (EnumWindows + UIA browser tabs)
    def _sys_state():
        from reflex_companion.actions import get_system_state
        get_system_state()
    total += measure("get_system_state() #1 (EnumWindows + UIA tabs)", _sys_state)
    total += measure("get_system_state() #2 (mismo turno, sin caché)", _sys_state)

    print()
    print("─── Compute mental state (puede llamar al LLM si preoccupation vencida) ───")

    # 4. Mental state — el caso lento es cuando preoccupation está vencida
    def _mental():
        from reflex_companion import mental_state as _ms
        state = _ms.load_state()
        if _ms.should_regenerate_preoccupation(state):
            print(f"    → preoccupation VENCIDA (last={state.get('preoccupation_generated_at') or '(never)'})")
            print(f"    → regen llamará al LLM grok-3-fast vía red...")
            _ms.regenerate_preoccupation(state, messages, facts, "es", None)
            _ms.save_state(state)
        else:
            print(f"    → preoccupation FRESCA, no se regenera")
    total += measure("compute_mental_state_block (regen if stale)", _mental)

    print()
    print("─── Compresión de historial ───")

    # 5. Compress history (LLM call si caché stale y >20 msgs)
    def _compress():
        from reflex_companion.context_compression import compress_history
        compress_history(list(messages), "es")
    total += measure("compress_history() (LLM si stale)", _compress)

    print()
    print("─── Build del system_prompt completo (sin LLM, solo string) ───")

    # 6. Build system prompt completo
    def _build_prompt():
        from reflex_companion.prompts import build_system_prompt
        build_system_prompt(
            facts, diary,
            time_context="hoy 12:00",
            voice_mode=False,
            lang="es",
            affection=50,
        )
    total += measure("build_system_prompt() (concat de string)", _build_prompt)

    # 7. Voice config reads (ocurren ~3-4 veces por turno hoy)
    def _voice_cfg():
        from reflex_companion.i18n import load_voice_config
        load_voice_config()
    total += measure("load_voice_config() #1 (disco JSON)", _voice_cfg)
    total += measure("load_voice_config() #2", _voice_cfg)
    total += measure("load_voice_config() #3", _voice_cfg)
    total += measure("load_voice_config() #4", _voice_cfg)

    print()
    print("=" * 72)
    print(f"  TOTAL pre-stream (sin contar TTFT del LLM principal): {total:>6.0f} ms")
    print("=" * 72)
    print()
    print("Notas:")
    print("  • TTFT del LLM principal aparte: ~3-4s (reasoning) o ~0.6s (non-reasoning)")
    print("  • Si compute_mental_state mostró 'VENCIDA', ese bloque solo es 1-3s extra")
    print("    LA PRIMERA VEZ tras >60min sin uso. Reapertura tras lunch = SIEMPRE ese caso.")
    print()


if __name__ == "__main__":
    main()
