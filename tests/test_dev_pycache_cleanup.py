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
    """En el .exe instalado, .pyc cacheado es válido (post-install nadie
    modifica el .py). Borrarlo cada arranque desperdicia ~100ms.
    En dev workspace (running from source), borrar siempre."""
    src = MAIN_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function _clearStalePycache\(\)[\s\S]+?(?=\n\nfunction |\n// ─)",
        src,
    )
    assert section, "_clearStalePycache no encontrado o sin cierre"
    body = section.group(0)
    # Early return si NO es dev workspace
    # Aceptamos !_isDevWorkspace() (versión actual) o !DEV_MODE (versión vieja).
    has_guard = (
        "if (!_isDevWorkspace())" in body
        or "!_isDevWorkspace()" in body
        or "if (!DEV_MODE)" in body
    )
    assert has_guard, (
        "_clearStalePycache debe early-return cuando NO es dev workspace"
    )


def test_isdev_workspace_uses_app_packaged_not_argv_flag():
    """El .bat de ashley-electron NO pasa --dev, así que DEV_MODE (basado
    en process.argv) es siempre false. Para que la limpieza de pycache
    funcione cuando el user corre desde source (dev workspace), debe
    usar !app.isPackaged que SÍ es true en ese caso."""
    src = MAIN_JS.read_text(encoding="utf-8")
    assert "function _isDevWorkspace" in src, (
        "Falta helper _isDevWorkspace() — sino el cleanup de pycache no "
        "se aplica cuando se corre via npm start sin --dev (caso real "
        "del .bat de ashley-electron)"
    )
    section = re.search(
        r"function _isDevWorkspace[\s\S]+?(?=\n\nfunction |\n// )",
        src,
    )
    assert section
    body = section.group(0)
    assert "app.isPackaged" in body, (
        "_isDevWorkspace debe usar app.isPackaged, no DEV_MODE"
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


def _isdev_check(body: str) -> bool:
    """True si el body usa _isDevWorkspace() o DEV_MODE para condicionar."""
    return ("_isDevWorkspace" in body) or ("DEV_MODE" in body)


def test_pythondontwritebytecode_set_in_dev_split_process():
    """En _startSplitProcesses (fast-path), env debe incluir
    PYTHONDONTWRITEBYTECODE='1' cuando es dev workspace."""
    src = MAIN_JS.read_text(encoding="utf-8")
    section = re.search(
        r"function _startSplitProcesses[\s\S]+?(?=\nfunction )", src,
    )
    assert section
    body = section.group(0)
    assert "PYTHONDONTWRITEBYTECODE" in body, (
        "_startSplitProcesses debe setear PYTHONDONTWRITEBYTECODE en dev"
    )
    assert _isdev_check(body), (
        "PYTHONDONTWRITEBYTECODE debe estar condicionado a _isDevWorkspace()"
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
        "_startSingleReflexProcess debe setear PYTHONDONTWRITEBYTECODE en dev"
    )
    assert _isdev_check(body)


def test_pythondontwritebytecode_not_global():
    """PYTHONDONTWRITEBYTECODE NO debe afectar al .exe instalado. La forma
    `...(_isDevWorkspace() ? {...} : {})` lo hace condicional."""
    src = MAIN_JS.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\.\.\.\(_isDevWorkspace\(\)\s*\?\s*\{\s*PYTHONDONTWRITEBYTECODE",
    )
    matches = list(pattern.finditer(src))
    assert len(matches) >= 2, (
        f"PYTHONDONTWRITEBYTECODE debe estar condicionado a _isDevWorkspace() en "
        f"AMBAS funciones de spawn (split + single). Encontradas: {len(matches)}"
    )
