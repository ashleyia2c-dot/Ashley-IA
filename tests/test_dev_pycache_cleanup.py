"""Guards para evitar que cambios al .py no se reflejen en runtime por
bytecode .pyc cacheado (v0.18.2 bug fix).

Bug raíz: en DEV mode, cuando el user (vía Claude) modifica reflex_companion.py
y reinicia Ashley, Python a veces sigue usando el .pyc cacheado en lugar de
recompilar el .py modificado. Resultado: cambios invisibles, debugging muy
confuso.

Defensas implementadas en electron/main.js:
  1. _clearStalePycache() borra __pycache__ antes de spawn de Reflex (DEV only)
  2. PYTHONDONTWRITEBYTECODE=1 en el env del subprocess (DEV only) — Python
     no escribe ningún .pyc, eliminando la posibilidad de stale cache.

PROD: ambas defensas se desactivan — el .py no se modifica post-install,
así que el bytecode siempre es válido y queremos cachearlo.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN_JS = ROOT / "electron" / "main.js"


def test_clear_stale_pycache_function_exists():
    src = MAIN_JS.read_text(encoding="utf-8")
    assert "function _clearStalePycache" in src, (
        "Falta _clearStalePycache() en main.js — sin ella, cambios al "
        ".py no se reflejan en runtime por bytecode stale"
    )


def test_clear_stale_pycache_only_runs_in_dev():
    """En PROD, .pyc cacheado es válido (post-install nadie modifica el .py).
    Borrarlo cada arranque desperdicia ~100ms y elimina el beneficio
    del cacheo."""
    src = MAIN_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function _clearStalePycache\(\)[\s\S]+?(?=\n\nfunction |\n// ─)",
        src,
    )
    assert section, "_clearStalePycache no encontrado o sin cierre"
    body = section.group(0)
    # Early return si no es dev mode
    assert "if (!DEV_MODE) return" in body or "if (DEV_MODE === false)" in body, (
        "_clearStalePycache debe early-return cuando NO es DEV mode"
    )


def test_clear_stale_pycache_called_on_startup():
    src = MAIN_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function startReflex[\s\S]+?(?=\nfunction |\Z)", src,
    )
    assert section
    body = section.group(0)
    assert "_clearStalePycache" in body, (
        "startReflex() debe llamar _clearStalePycache() antes de spawn"
    )


def test_pythondontwritebytecode_set_in_dev_split_process():
    """En _startSplitProcesses (fast-path), env debe incluir
    PYTHONDONTWRITEBYTECODE='1' cuando DEV_MODE."""
    src = MAIN_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function _startSplitProcesses[\s\S]+?(?=\nfunction )", src,
    )
    assert section
    body = section.group(0)
    assert "PYTHONDONTWRITEBYTECODE" in body, (
        "_startSplitProcesses debe setear PYTHONDONTWRITEBYTECODE en DEV"
    )
    # Debe ser condicional a DEV_MODE
    assert "DEV_MODE" in body, (
        "PYTHONDONTWRITEBYTECODE debe estar condicionado a DEV_MODE"
    )


def test_pythondontwritebytecode_set_in_dev_single_process():
    """Mismo guard para _startSingleReflexProcess (slow-path)."""
    src = MAIN_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function _startSingleReflexProcess[\s\S]+?(?=\nfunction |\n// )",
        src,
    )
    assert section
    body = section.group(0)
    assert "PYTHONDONTWRITEBYTECODE" in body, (
        "_startSingleReflexProcess debe setear PYTHONDONTWRITEBYTECODE en DEV"
    )
    assert "DEV_MODE" in body


def test_pythondontwritebytecode_not_global():
    """PYTHONDONTWRITEBYTECODE NO debe afectar a PROD. La forma
    `...(DEV_MODE ? {...} : {})` lo hace condicional."""
    src = MAIN_JS.read_text(encoding="utf-8")
    # Buscamos el patrón condicional ternario alrededor del env var
    pattern = re.compile(
        r"\.\.\.\(DEV_MODE\s*\?\s*\{\s*PYTHONDONTWRITEBYTECODE",
    )
    matches = list(pattern.finditer(src))
    assert len(matches) >= 2, (
        f"PYTHONDONTWRITEBYTECODE debe estar condicionado a DEV_MODE en "
        f"AMBAS funciones de spawn (split + single). Encontradas: {len(matches)}"
    )
