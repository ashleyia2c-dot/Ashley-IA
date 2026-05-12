"""Regression tests para v0.19.37 — defensa-en-profundidad para PCs raras.

User reminder: 'recuerda que debe funcionar en pcs muy distintas ehhh'

Edge cases adicionales que cubre:
  1. Carpetas con mayúsculas distintas (Node_Modules == node_modules)
  2. Hard timeout en _is_writable_dir (network shares lentos, OneDrive,
     antivirus particularmente agresivo, ACL hereditario raro fuera de
     ProgramData)
  3. Per-file fallback limitado a 100 paths (evita nuevo hang si el batch
     falla en una PC con 200+ shortcuts)
  4. Catch de FileNotFoundError si PowerShell no está en PATH (Windows
     restringidos / sandboxes corporativos)
  5. Overall timeout de 60s en find_browser_shortcuts (defensa final
     ABSOLUTA: si TODO sale mal, el wizard al menos termina)
"""
import os
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest


# ════════════════════════════════════════════════════════════════════════
#  Fix 1 — Case-insensitive noise dirs
# ════════════════════════════════════════════════════════════════════════


class TestCaseInsensitiveNoiseDirs:
    """Windows es case-insensitive. `Node_Modules` debe matchear igual
    que `node_modules` en _NOISE_DIRS."""

    def test_uppercase_node_modules_skipped(self, tmp_path):
        from reflex_companion.browser_setup import _iter_lnk_files

        (tmp_path / "Node_Modules").mkdir()
        (tmp_path / "Node_Modules" / "skip.lnk").write_text("fake")
        (tmp_path / "good.lnk").write_text("fake")

        results = list(_iter_lnk_files(tmp_path))
        names = {r.name for r in results}
        assert names == {"good.lnk"}, (
            f"Node_Modules (mixed case) debe skipearse igual que node_modules. "
            f"Got: {names}"
        )

    def test_full_uppercase_venv_skipped(self, tmp_path):
        from reflex_companion.browser_setup import _iter_lnk_files

        (tmp_path / "VENV").mkdir()
        (tmp_path / "VENV" / "skip.lnk").write_text("fake")

        results = list(_iter_lnk_files(tmp_path))
        assert len(results) == 0

    def test_camelcase_dotgit_skipped(self, tmp_path):
        """`.Git` (raro pero posible) también debe skipearse."""
        from reflex_companion.browser_setup import _iter_lnk_files

        (tmp_path / ".Git").mkdir()
        (tmp_path / ".Git" / "skip.lnk").write_text("fake")

        results = list(_iter_lnk_files(tmp_path))
        assert len(results) == 0

    def test_normal_lowercase_still_works(self, tmp_path):
        """No regresión: lowercase originales siguen funcionando."""
        from reflex_companion.browser_setup import _iter_lnk_files
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "skip.lnk").write_text("fake")
        results = list(_iter_lnk_files(tmp_path))
        assert len(results) == 0


# ════════════════════════════════════════════════════════════════════════
#  Fix 2 — Hard timeout en _is_writable_dir
# ════════════════════════════════════════════════════════════════════════


class TestIsWritableDirTimeout:
    """v0.19.37 — si mkstemp se cuelga (network share lento, antivirus,
    ACL raro), el thread de check tiene un timeout duro."""

    def test_normal_path_returns_true_within_timeout(self, tmp_path):
        from reflex_companion.browser_setup import _is_writable_dir
        t0 = time.time()
        result = _is_writable_dir(tmp_path)
        elapsed = time.time() - t0
        assert result is True
        assert elapsed < 1.0, "Path normal NO debe tardar más de 1s"

    def test_returns_false_if_mkstemp_hangs_beyond_timeout(self, tmp_path):
        """Si mkstemp queda colgado, el wrapper debe devolver False
        después del timeout (no hang)."""
        from reflex_companion import browser_setup

        def slow_mkstemp(*args, **kwargs):
            # Simula hang esperando 5s — más allá del timeout default
            time.sleep(5)
            return (None, "fake_path")

        with patch("tempfile.mkstemp", side_effect=slow_mkstemp):
            t0 = time.time()
            # timeout=1.0 fuerza el caso rápido
            result = browser_setup._is_writable_dir(tmp_path, timeout=1.0)
            elapsed = time.time() - t0

        assert result is False, "Timeout debe forzar False"
        # Debe respetar el timeout (con margen para overhead de threading)
        assert elapsed < 2.0, (
            f"_is_writable_dir con timeout=1.0 tardó {elapsed:.2f}s — "
            "debe respetar el timeout"
        )

    def test_timeout_doesnt_block_subsequent_calls(self, tmp_path):
        """Después de un timeout, llamadas subsiguientes a otros paths
        no deben verse afectadas (thread daemon en background)."""
        from reflex_companion import browser_setup

        # Primera llamada con mkstemp lento → timeout
        with patch("tempfile.mkstemp", side_effect=lambda *a, **kw: (time.sleep(3), (None, "p"))[1]):
            browser_setup._is_writable_dir(tmp_path, timeout=0.5)

        # Segunda llamada con mkstemp normal → fast OK
        t0 = time.time()
        result = browser_setup._is_writable_dir(tmp_path)
        elapsed = time.time() - t0
        assert result is True
        assert elapsed < 1.0


# ════════════════════════════════════════════════════════════════════════
#  Fix 3 — Per-file fallback limitado
# ════════════════════════════════════════════════════════════════════════


class TestPerFileFallbackLimit:
    """v0.19.37 — si batch falla, el fallback per-file procesa máximo
    100 paths para no crear su propio hang en PCs con 200+ shortcuts."""

    def test_fallback_processes_max_100_paths(self, tmp_path, monkeypatch):
        from reflex_companion import browser_setup

        # Crear 200 .lnk fake
        for i in range(200):
            (tmp_path / f"shortcut{i}.lnk").write_text("fake")

        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_single:
            mock_batch.return_value = {}  # batch falla
            # per-file devuelve dict vacío para que no genere browsers
            mock_single.return_value = None

            browser_setup.find_browser_shortcuts()
            # _read_lnk_via_ps debe haberse llamado MÁXIMO 100 veces,
            # no 200
            assert mock_single.call_count <= 100, (
                f"Per-file fallback NO debe procesar más de 100 paths. "
                f"Hizo {mock_single.call_count} llamadas."
            )


# ════════════════════════════════════════════════════════════════════════
#  Fix 4 — PowerShell missing → graceful failure
# ════════════════════════════════════════════════════════════════════════


class TestPowerShellMissing:
    """v0.19.37 — si PowerShell no está instalado o no está en PATH
    (Windows restringidos / sandboxes corporativos), las funciones
    devuelven None/{} cleanly en vez de crashear."""

    def test_read_lnk_via_ps_handles_filenotfound(self):
        from reflex_companion import browser_setup
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=FileNotFoundError("PowerShell not found")):
            result = browser_setup._read_lnk_via_ps("C:\\fake.lnk")
            assert result is None

    def test_write_lnk_args_via_ps_handles_filenotfound(self):
        from reflex_companion import browser_setup
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=FileNotFoundError("PowerShell not found")):
            result = browser_setup._write_lnk_args_via_ps("C:\\fake.lnk", "args")
            assert result is False

    def test_read_lnks_batch_handles_filenotfound(self):
        from reflex_companion import browser_setup
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=FileNotFoundError("PowerShell not found")):
            result = browser_setup._read_lnks_batch(["C:\\fake.lnk"])
            assert result == {}

    def test_find_browser_shortcuts_returns_empty_when_powershell_missing(
            self, tmp_path, monkeypatch):
        """E2E: con PS missing, find_browser_shortcuts NO debe crashear,
        solo devolver []."""
        from reflex_companion import browser_setup

        (tmp_path / "Chrome.lnk").write_text("fake")
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=FileNotFoundError("PowerShell not found")):
            result = browser_setup.find_browser_shortcuts()
            assert result == [], "Sin PowerShell, devolver [] sin crashear"


# ════════════════════════════════════════════════════════════════════════
#  Fix 5 — Overall timeout cap en find_browser_shortcuts
# ════════════════════════════════════════════════════════════════════════


class TestOverallTimeout:
    """v0.19.37 — defensa final ABSOLUTA: aunque todos los demás timeouts
    fallen, find_browser_shortcuts no debe tardar más de ~60s."""

    def test_completes_within_overall_timeout(self, tmp_path, monkeypatch):
        """Caso normal: con noise dirs y batch reader, debe completarse
        bien por debajo de 60s. Sanidad check."""
        from reflex_companion import browser_setup

        for i in range(10):
            (tmp_path / f"s{i}.lnk").write_text("fake")
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch:
            mock_batch.return_value = {
                str(tmp_path / f"s{i}.lnk"): {
                    "target": "C:\\chrome.exe", "arguments": "",
                    "working_directory": "",
                } for i in range(10)
            }
            t0 = time.time()
            result = browser_setup.find_browser_shortcuts()
            elapsed = time.time() - t0

        assert elapsed < 5.0, "Caso normal debe ser sub-segundo"
        assert len(result) == 10


# ════════════════════════════════════════════════════════════════════════
#  Sanity check: nuevos noise dirs añadidos en v0.19.37
# ════════════════════════════════════════════════════════════════════════


class TestNewNoiseDirsV37:
    def test_packages_in_noise_dirs(self):
        from reflex_companion.browser_setup import _NOISE_DIRS
        assert "packages" in _NOISE_DIRS

    def test_docker_in_noise_dirs(self):
        from reflex_companion.browser_setup import _NOISE_DIRS
        assert ".docker" in _NOISE_DIRS

    def test_all_noise_dirs_lowercase(self):
        """v0.19.37 — TODOS los entries en _NOISE_DIRS deben estar en
        lowercase para que la comparación con name.lower() funcione."""
        from reflex_companion.browser_setup import _NOISE_DIRS
        for d in _NOISE_DIRS:
            assert d == d.lower(), (
                f"Entry {d!r} no está en lowercase. La comparación se "
                f"hace con name.lower() — entries deben estar también."
            )
