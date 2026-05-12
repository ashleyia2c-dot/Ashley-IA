"""Regression tests para v0.19.36 — HOTFIX del wizard CDP que se colgaba
para siempre tras v0.19.35.

Bug raíz: dos problemas combinados que causaban hangs en `find_browser_shortcuts`:

1. **rglob recursivo sin límite** — cuando el user tenía proyectos de
   desarrollo en el Desktop (node_modules con 100K+ files, .web/, venv/,
   etc.), `Path.rglob("*.lnk")` se metía en esas carpetas y escaneaba
   centenares de miles de archivos buscando `.lnk` (que nunca había ahí).
   Fix: nuevo `_iter_lnk_files` con depth limit + skip de noise dirs.

2. **mkstemp en ProgramData se cuelga sin admin** — `_is_writable_dir`
   intentaba crear un archivo temp en `C:\\ProgramData\\Microsoft\\Windows\\
   Start Menu\\Programs\\` para verificar permisos. Sin admin esto NO falla
   con PermissionError inmediato — se cuelga durante minutos bajo
   antivirus. `os.access` da falso positivo en este path (devuelve True).
   Fix: detectar `_is_admin()` y SKIPEAR ProgramData candidates upfront.

3. **Batch reader hanging via [Console]::In** — PowerShell 5.1 default
   Windows no maneja bien stdin redirigido vía subprocess. Cambié a
   temp file + Get-Content (más robusto cross-version).
"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ════════════════════════════════════════════════════════════════════════
#  Fix 1 — _iter_lnk_files con depth limit + noise dirs
# ════════════════════════════════════════════════════════════════════════


class TestIterLnkFilesDepthLimit:
    def test_skips_noise_dirs(self, tmp_path):
        """node_modules, .git, venv, etc. NO deben recorrerse."""
        from reflex_companion.browser_setup import _iter_lnk_files

        # Crear estructura: tmp_path/node_modules/some.lnk + tmp_path/Chrome.lnk
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "should_skip.lnk").write_text("fake")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "should_skip2.lnk").write_text("fake")
        (tmp_path / "venv").mkdir()
        (tmp_path / "venv" / "should_skip3.lnk").write_text("fake")
        (tmp_path / "Chrome.lnk").write_text("fake")

        results = list(_iter_lnk_files(tmp_path))
        names = {r.name for r in results}
        assert names == {"Chrome.lnk"}, (
            f"Solo Chrome.lnk debe aparecer, no archivos en noise dirs. "
            f"Got: {names}"
        )

    def test_skips_dotfolders(self, tmp_path):
        """Cualquier dotfolder (.config, .docker, etc.) debe skipearse."""
        from reflex_companion.browser_setup import _iter_lnk_files

        (tmp_path / ".config").mkdir()
        (tmp_path / ".config" / "skip.lnk").write_text("fake")
        (tmp_path / ".something_random").mkdir()
        (tmp_path / ".something_random" / "skip2.lnk").write_text("fake")
        (tmp_path / "Browser.lnk").write_text("fake")

        results = list(_iter_lnk_files(tmp_path))
        assert len(results) == 1
        assert results[0].name == "Browser.lnk"

    def test_respects_max_depth(self, tmp_path):
        """No debe recursar más allá de max_depth niveles."""
        from reflex_companion.browser_setup import _iter_lnk_files

        # Crear estructura profunda: tmp_path/a/b/c/d/e/deep.lnk
        deep = tmp_path
        for letter in "abcde":
            deep = deep / letter
            deep.mkdir()
        (deep / "deep.lnk").write_text("fake")
        # Y un .lnk al inicio
        (tmp_path / "shallow.lnk").write_text("fake")

        # max_depth=2 → solo encuentra shallow.lnk
        results = list(_iter_lnk_files(tmp_path, max_depth=2))
        names = {r.name for r in results}
        assert "shallow.lnk" in names
        assert "deep.lnk" not in names, "depth=2 NO debe llegar a depth=5"

    def test_default_depth_finds_typical_browser_lnk_locations(self, tmp_path):
        """Default depth (4) DEBE encontrar shortcuts en estructuras típicas:
        Programs/Google Chrome/Chrome.lnk (depth 1)."""
        from reflex_companion.browser_setup import _iter_lnk_files

        sub = tmp_path / "Google Chrome"
        sub.mkdir()
        (sub / "Chrome.lnk").write_text("fake")

        results = list(_iter_lnk_files(tmp_path))
        names = {r.name for r in results}
        assert "Chrome.lnk" in names

    def test_handles_permission_errors_gracefully(self, tmp_path, monkeypatch):
        """Si una subdir levanta PermissionError, skipea esa sin abortar."""
        from reflex_companion.browser_setup import _iter_lnk_files
        from pathlib import Path as RealPath

        (tmp_path / "good.lnk").write_text("fake")

        # Mock iterdir para que una subdir levante PermissionError
        original_iterdir = Path.iterdir

        def patched_iterdir(self):
            if str(self).endswith("forbidden"):
                raise PermissionError("simulated")
            return original_iterdir(self)

        forbidden = tmp_path / "forbidden"
        forbidden.mkdir()
        (forbidden / "blocked.lnk").write_text("fake")

        with patch.object(Path, "iterdir", patched_iterdir):
            results = list(_iter_lnk_files(tmp_path))
            names = {r.name for r in results}
        assert "good.lnk" in names, "good.lnk debe encontrarse a pesar del error"
        # blocked.lnk no debe aparecer (la subdir falló)
        assert "blocked.lnk" not in names

    def test_negative_max_depth_returns_nothing(self, tmp_path):
        """Edge case: max_depth negativo → generator vacío inmediatamente."""
        from reflex_companion.browser_setup import _iter_lnk_files
        (tmp_path / "x.lnk").write_text("fake")
        results = list(_iter_lnk_files(tmp_path, max_depth=-1))
        assert results == []


class TestNoiseDirsContent:
    """v0.19.36 — _NOISE_DIRS debe contener las carpetas más comunes
    de proyectos dev que pueden tener decenas de miles de archivos."""

    def test_includes_node_modules(self):
        from reflex_companion.browser_setup import _NOISE_DIRS
        assert "node_modules" in _NOISE_DIRS

    def test_includes_python_envs(self):
        from reflex_companion.browser_setup import _NOISE_DIRS
        for d in ("venv", ".venv", "__pycache__"):
            assert d in _NOISE_DIRS, f"Falta {d!r} en _NOISE_DIRS"

    def test_includes_git_and_vcs(self):
        from reflex_companion.browser_setup import _NOISE_DIRS
        assert ".git" in _NOISE_DIRS

    def test_includes_reflex_web_dir(self):
        """.web es donde Reflex compila el frontend → puede tener
        muchos archivos. Caso real del bug del usuario."""
        from reflex_companion.browser_setup import _NOISE_DIRS
        assert ".web" in _NOISE_DIRS


# ════════════════════════════════════════════════════════════════════════
#  Fix 2 — _is_admin + skip ProgramData cuando no admin
# ════════════════════════════════════════════════════════════════════════


class TestIsAdminHelper:
    def test_returns_bool(self):
        from reflex_companion.browser_setup import _is_admin
        result = _is_admin()
        assert isinstance(result, bool)

    def test_returns_false_when_ctypes_fails(self):
        """Si ctypes.windll.shell32 no está disponible (no Windows, mock,
        etc.) → False (asume no admin)."""
        from reflex_companion import browser_setup
        with patch("ctypes.windll.shell32.IsUserAnAdmin",
                   side_effect=Exception("not available")):
            assert browser_setup._is_admin() is False


class TestShortcutLocationsSkipsProgramDataWhenNotAdmin:
    """v0.19.36 — Bug crítico fix: ProgramData paths deben SKIPEARSE
    cuando no soy admin. Sin esto, _is_writable_dir cuelga el wizard
    indefinidamente."""

    def test_progdata_NOT_in_locations_when_not_admin(self, monkeypatch):
        """Con _is_admin = False, ProgramData no debe aparecer en
        candidates a la lista de shortcut locations."""
        from reflex_companion import browser_setup

        monkeypatch.setattr(browser_setup, "_is_admin", lambda: False)
        monkeypatch.setattr(browser_setup, "_is_writable_dir",
                            lambda p: True)  # mock writable check
        monkeypatch.setenv("USERPROFILE", "C:\\Users\\test")
        monkeypatch.setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")
        monkeypatch.setenv("PUBLIC", "C:\\Users\\Public")
        monkeypatch.setenv("PROGRAMDATA", "C:\\ProgramData")

        result = browser_setup._shortcut_locations()
        result_strs = [str(p) for p in result]
        for r in result_strs:
            assert "ProgramData" not in r, (
                f"v0.19.36 bug: ProgramData NO debe aparecer cuando no "
                f"somos admin. Got: {r}"
            )

    def test_progdata_IS_in_locations_when_admin(self, monkeypatch):
        """Con _is_admin = True, ProgramData SÍ debe estar en candidates."""
        from reflex_companion import browser_setup

        monkeypatch.setattr(browser_setup, "_is_admin", lambda: True)
        monkeypatch.setattr(browser_setup, "_is_writable_dir",
                            lambda p: True)
        monkeypatch.setenv("USERPROFILE", "C:\\Users\\test")
        monkeypatch.setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")
        monkeypatch.setenv("PUBLIC", "C:\\Users\\Public")
        monkeypatch.setenv("PROGRAMDATA", "C:\\ProgramData")

        result = browser_setup._shortcut_locations()
        result_strs = [str(p) for p in result]
        progdata_found = any("ProgramData" in r for r in result_strs)
        assert progdata_found, (
            "Cuando somos admin, ProgramData SÍ debe escanearse"
        )


# ════════════════════════════════════════════════════════════════════════
#  Fix 3 — Batch reader usa temp file en lugar de stdin (PS 5.1 compat)
# ════════════════════════════════════════════════════════════════════════


class TestBatchReaderUsesTempFile:
    """v0.19.36 — el batch reader pasa paths via temp file + Get-Content.
    Antes (v0.19.35) usaba stdin + [Console]::In.ReadLine que se colgaba
    en PowerShell 5.1 (default Windows)."""

    def test_does_not_use_stdin_redirect(self):
        from reflex_companion import browser_setup
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("reflex_companion.browser_setup.subprocess.run",
                   return_value=mock_result) as mock_run:
            browser_setup._read_lnks_batch(["A.lnk"])
            kwargs = mock_run.call_args[1]
            # input= debe ser None (paths van por temp file)
            assert kwargs.get("input") is None, (
                "Paths NO deben ir via stdin (rompe PS 5.1)"
            )

    def test_powershell_script_uses_get_content(self):
        from reflex_companion import browser_setup
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("reflex_companion.browser_setup.subprocess.run",
                   return_value=mock_result) as mock_run:
            browser_setup._read_lnks_batch(["A.lnk"])
            ps_script = mock_run.call_args[0][0][-1]
            assert "Get-Content" in ps_script

    def test_temp_file_cleaned_up_on_success(self, tmp_path, monkeypatch):
        """Después del subprocess, el temp file con los paths debe
        borrarse (no acumular basura)."""
        from reflex_companion import browser_setup
        # Forzar que el temp file aparezca en tmp_path
        monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
        files_before = set(tmp_path.iterdir())
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("reflex_companion.browser_setup.subprocess.run",
                   return_value=mock_result):
            browser_setup._read_lnks_batch(["A.lnk", "B.lnk"])
        files_after = set(tmp_path.iterdir())
        assert files_after == files_before, (
            f"Temp file no se limpió. Nuevos: {files_after - files_before}"
        )

    def test_temp_file_cleaned_up_on_subprocess_exception(self, tmp_path, monkeypatch):
        """Incluso si subprocess crashea, el temp file debe borrarse."""
        from reflex_companion import browser_setup
        monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
        files_before = set(tmp_path.iterdir())
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=Exception("boom")):
            browser_setup._read_lnks_batch(["A.lnk"])
        files_after = set(tmp_path.iterdir())
        assert files_after == files_before


# ════════════════════════════════════════════════════════════════════════
#  Fix 4 — find_browser_shortcuts fallback a per-file si batch falla
# ════════════════════════════════════════════════════════════════════════


class TestFindBrowserShortcutsFallback:
    """v0.19.36 — si _read_lnks_batch devuelve {} pero hay paths,
    fallback a _read_lnk_via_ps per-file. Asegura que aunque PowerShell
    batch falle, el wizard al menos funciona (más lento pero correcto)."""

    def test_fallback_used_when_batch_returns_empty(self, tmp_path, monkeypatch):
        from reflex_companion import browser_setup

        (tmp_path / "Chrome.lnk").write_text("fake")
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_single:
            # Batch devuelve vacío (timeout, error PowerShell)
            mock_batch.return_value = {}
            # Per-file fallback funciona
            mock_single.return_value = {
                "target": "C:\\chrome.exe", "arguments": "",
                "working_directory": "",
            }
            result = browser_setup.find_browser_shortcuts()
            # Per-file DEBE haber sido llamado (fallback activado)
            assert mock_single.called, (
                "Cuando batch falla, fallback a _read_lnk_via_ps debe activarse"
            )
            assert len(result) == 1
            assert result[0]["browser"] == "Chrome"

    def test_no_fallback_if_batch_returns_results(self, tmp_path, monkeypatch):
        """Happy path: batch funciona → fallback NO debe activarse
        (sería trabajo duplicado)."""
        from reflex_companion import browser_setup

        (tmp_path / "Chrome.lnk").write_text("fake")
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_single:
            mock_batch.return_value = {
                str(tmp_path / "Chrome.lnk"): {
                    "target": "C:\\chrome.exe", "arguments": "",
                    "working_directory": "",
                }
            }
            browser_setup.find_browser_shortcuts()
            # Per-file NO debe llamarse (batch funcionó)
            assert not mock_single.called

    def test_no_fallback_if_no_paths_to_scan(self, tmp_path, monkeypatch):
        """Si no hay paths para escanear (sin .lnk), no hay nada que
        fallbackear."""
        from reflex_companion import browser_setup

        # tmp_path vacío
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_single:
            mock_batch.return_value = {}
            result = browser_setup.find_browser_shortcuts()
            # Ni batch ni single deben llamarse (no hay paths)
            assert not mock_batch.called  # short-circuit en find
            assert not mock_single.called
            assert result == []


# ════════════════════════════════════════════════════════════════════════
#  Fix 5 — _is_writable_dir os.access pre-check (defensa adicional)
# ════════════════════════════════════════════════════════════════════════


class TestIsWritableDirOsAccessPrecheck:
    """v0.19.36 — antes de mkstemp (que puede ser lento en algunos paths
    sin permisos), hacemos un pre-check con os.access que es rápido y
    devuelve False de forma confiable para la mayoría de casos no-writable."""

    def test_returns_false_fast_when_os_access_says_no(self, tmp_path):
        from reflex_companion import browser_setup
        with patch("os.access", return_value=False) as mock_access:
            result = browser_setup._is_writable_dir(tmp_path)
            assert result is False
            assert mock_access.called

    def test_falls_through_to_mkstemp_when_os_access_says_yes(self, tmp_path):
        """Si os.access dice yes, confirmamos con mkstemp real (no podemos
        confiar 100% en os.access en Windows)."""
        from reflex_companion import browser_setup
        # tmp_path es realmente writable, ambos deben dar True
        result = browser_setup._is_writable_dir(tmp_path)
        assert result is True
