"""Tests para reflex_companion/browser_setup.py — el wizard que añade
--remote-debugging-port=9222 a los .lnk de browsers Chromium.

Cobertura:
  • Pure functions (escape, hash-based backup paths, friendly names)
  • _is_writable_dir con tmp_path real
  • _shortcut_locations con monkeypatched env vars (M5)
  • _migrate_legacy_backup (filesystem real)
  • add_cdp_flag / remove_cdp_flag con mocks de PowerShell subprocess
  • configure_all_shortcuts integration con find_browser_shortcuts mockeado
  • Status codes estables (C3) — el contador "skipped" funciona aunque
    los mensajes humanos cambien de idioma
"""
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from reflex_companion import browser_setup as bs
from reflex_companion.browser_setup import (
    CDP_FLAG,
    STATUS_MODIFIED,
    STATUS_ALREADY_HAD_FLAG,
    STATUS_NO_FLAG_TO_REMOVE,
    STATUS_FAILED,
    _backup_path_for,
    _browser_friendly_name,
    _is_writable_dir,
    _migrate_legacy_backup,
    _ps_escape_single_quoted,
    _shortcut_locations,
    add_cdp_flag,
    configure_all_shortcuts,
    find_browser_shortcuts,
    remove_cdp_flag,
)


# ════════════════════════════════════════════════════════════════════════
#  Pure functions
# ════════════════════════════════════════════════════════════════════════


class TestPSEscape:
    """v0.19.34 (C2) — Escape para PowerShell single-quoted strings."""

    def test_no_apostrophe_unchanged(self):
        assert _ps_escape_single_quoted("C:\\Users\\Mathieu\\Desktop\\a.lnk") == \
            "C:\\Users\\Mathieu\\Desktop\\a.lnk"

    def test_single_apostrophe_doubled(self):
        assert _ps_escape_single_quoted("O'Brien") == "O''Brien"

    def test_multiple_apostrophes(self):
        assert _ps_escape_single_quoted("don't can't won't") == "don''t can''t won''t"

    def test_path_with_apostrophe(self):
        # Caso real del bug C2
        result = _ps_escape_single_quoted("C:\\Users\\O'Brien\\Desktop\\Chrome.lnk")
        assert result == "C:\\Users\\O''Brien\\Desktop\\Chrome.lnk"

    def test_empty_string(self):
        assert _ps_escape_single_quoted("") == ""

    def test_only_apostrophes(self):
        assert _ps_escape_single_quoted("'''") == "''''''"

    def test_dollar_sign_unchanged(self):
        # PowerShell single-quoted NO interpola $vars, así que no escapamos
        assert _ps_escape_single_quoted("$env:HOME") == "$env:HOME"

    def test_backtick_unchanged(self):
        # PowerShell single-quoted NO interpreta backticks
        assert _ps_escape_single_quoted("hello`world") == "hello`world"


class TestBrowserFriendlyName:
    @pytest.mark.parametrize("exe,expected", [
        ("chrome.exe", "Chrome"),
        ("CHROME.EXE", "Chrome"),  # case insensitive
        ("msedge.exe", "Edge"),
        ("brave.exe", "Brave"),
        ("opera.exe", "Opera"),
        ("operagx.exe", "Opera GX"),
        ("vivaldi.exe", "Vivaldi"),
    ])
    def test_known_browsers(self, exe, expected):
        assert _browser_friendly_name(exe) == expected

    def test_unknown_browser_returns_input(self):
        assert _browser_friendly_name("firefox.exe") == "firefox.exe"


class TestBackupPathFor:
    def test_returns_path_in_backup_dir(self, tmp_path, monkeypatch):
        # Apuntamos el data_path al tmp_path
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        result = _backup_path_for("C:\\Users\\test\\Desktop\\Chrome.lnk")
        assert result.parent.name == "browser_lnk_backups"
        assert result.name.startswith("Chrome.")
        assert result.name.endswith(".lnk.bak")

    def test_same_path_same_backup(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        a = _backup_path_for("C:\\Users\\x\\Chrome.lnk")
        b = _backup_path_for("C:\\Users\\x\\Chrome.lnk")
        assert a == b

    def test_different_paths_different_backups(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        # Mismo basename, paths distintos → backups distintos (hash difiere)
        a = _backup_path_for("C:\\Users\\x\\Chrome.lnk")
        b = _backup_path_for("C:\\Users\\y\\Chrome.lnk")
        assert a != b

    def test_basename_with_spaces_preserved(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        result = _backup_path_for("C:\\Users\\x\\Google Chrome.lnk")
        assert result.name.startswith("Google Chrome.")


class TestCDPFlag:
    def test_uses_default_port_from_browser_cdp(self):
        """v0.19.34 (M2) — CDP_FLAG debe construirse desde DEFAULT_CDP_PORT,
        no hardcoded. Single source of truth."""
        from reflex_companion.browser_cdp import DEFAULT_CDP_PORT
        assert CDP_FLAG == f"--remote-debugging-port={DEFAULT_CDP_PORT}"

    def test_default_port_is_9222(self):
        from reflex_companion.browser_cdp import DEFAULT_CDP_PORT
        assert DEFAULT_CDP_PORT == 9222


# ════════════════════════════════════════════════════════════════════════
#  _is_writable_dir — usa tmp_path real
# ════════════════════════════════════════════════════════════════════════


class TestIsWritableDir:
    def test_nonexistent_path_returns_false(self, tmp_path):
        assert _is_writable_dir(tmp_path / "does_not_exist") is False

    def test_writable_tmp_path_returns_true(self, tmp_path):
        assert _is_writable_dir(tmp_path) is True

    def test_no_orphan_test_files_left(self, tmp_path):
        """v0.19.34 (H1) — tempfile.mkstemp + unlink no debe dejar
        archivos huérfanos en happy path."""
        before = list(tmp_path.iterdir())
        _is_writable_dir(tmp_path)
        after = list(tmp_path.iterdir())
        assert before == after, (
            f"_is_writable_dir dejó archivos huérfanos: "
            f"{set(after) - set(before)}"
        )

    def test_tempfile_prefix_recognizable(self, tmp_path):
        """Si el archivo queda (race con antivirus), al menos tiene prefix
        recognizable para limpieza manual."""
        # Test indirecto: leemos el código source y verificamos el prefix
        import inspect
        src = inspect.getsource(_is_writable_dir)
        assert "ashley-write-test-" in src


# ════════════════════════════════════════════════════════════════════════
#  _shortcut_locations — handle missing env vars (M5)
# ════════════════════════════════════════════════════════════════════════


class TestShortcutLocationsM5:
    def test_missing_userprofile_skips_desktop(self, monkeypatch, tmp_path):
        """v0.19.34 (M5) — si USERPROFILE no existe, no debe construir
        Path('') / 'Desktop' (que sería relativo al CWD).

        Usamos tmp_path como APPDATA writable para tener al menos un
        candidato que pase el filter, pero verificamos que ningún path
        relativo (que vendría de Path('')) salga en el resultado.
        """
        monkeypatch.delenv("USERPROFILE", raising=False)
        monkeypatch.delenv("PUBLIC", raising=False)
        monkeypatch.delenv("PROGRAMDATA", raising=False)
        monkeypatch.setenv("APPDATA", str(tmp_path))

        # Crear las carpetas mínimas para que pase el writable check
        (tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs").mkdir(
            parents=True, exist_ok=True,
        )

        result = _shortcut_locations()
        # NINGÚN path debe ser relativo
        for p in result:
            assert p.is_absolute(), (
                f"Path relativo en _shortcut_locations: {p}. "
                f"Bug M5: env vars vacías construían Path('') / 'Desktop'."
            )

    def test_all_env_vars_missing_returns_empty(self, monkeypatch):
        """Si TODAS las env vars de Windows faltan, devolvemos lista vacía
        en vez de paths relativos al CWD."""
        for var in ("USERPROFILE", "APPDATA", "PUBLIC", "PROGRAMDATA"):
            monkeypatch.delenv(var, raising=False)
        result = _shortcut_locations()
        assert result == []

    def test_empty_string_env_var_skipped(self, monkeypatch):
        """Env var seteada a string vacío también debe skipearse."""
        for var in ("USERPROFILE", "APPDATA", "PUBLIC", "PROGRAMDATA"):
            monkeypatch.setenv(var, "")
        result = _shortcut_locations()
        # Path("") / "Desktop" sería relativo — no debe aparecer
        for p in result:
            assert p.is_absolute(), f"Path relativo: {p}"


# ════════════════════════════════════════════════════════════════════════
#  _migrate_legacy_backup — filesystem real
# ════════════════════════════════════════════════════════════════════════


class TestMigrateLegacyBackup:
    def test_no_legacy_no_op(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake lnk")
        # No legacy .bak existe → nada que hacer, no crashea
        _migrate_legacy_backup(str(lnk))

    def test_legacy_moved_to_new_location(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake lnk")
        legacy = tmp_path / "Chrome.lnk.bak"
        legacy.write_text("legacy backup content")

        _migrate_legacy_backup(str(lnk))

        # Legacy ya no existe
        assert not legacy.exists()
        # New backup existe con el contenido
        new_path = _backup_path_for(str(lnk))
        assert new_path.exists()
        assert new_path.read_text() == "legacy backup content"

    def test_legacy_skipped_if_new_already_exists(self, tmp_path, monkeypatch):
        """Si ya migramos antes (new existe), borramos el legacy duplicado
        en vez de sobrescribir el new."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake lnk")
        new_path = _backup_path_for(str(lnk))
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text("ORIGINAL backup, no tocar")

        legacy = tmp_path / "Chrome.lnk.bak"
        legacy.write_text("legacy duplicate")

        _migrate_legacy_backup(str(lnk))

        # Legacy borrado
        assert not legacy.exists()
        # New preservado (no sobrescrito)
        assert new_path.read_text() == "ORIGINAL backup, no tocar"


# ════════════════════════════════════════════════════════════════════════
#  add_cdp_flag / remove_cdp_flag con mocks de PowerShell
# ════════════════════════════════════════════════════════════════════════


def _mock_ps_run(stdout: str, stderr: str = "", returncode: int = 0):
    """Helper para mockear subprocess.run de PowerShell."""
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


class TestAddCDPFlag:
    def test_returns_3_tuple_with_status(self, tmp_path, monkeypatch):
        """v0.19.34 (C3) — add_cdp_flag DEBE devolver 3-tuple
        (ok, msg, status)."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")

        # Mock _read_lnk_via_ps a "ya tenía el flag"
        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_read.return_value = {
                "target": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "arguments": CDP_FLAG,
                "working_directory": "",
            }
            result = add_cdp_flag(str(lnk))

        assert isinstance(result, tuple)
        assert len(result) == 3
        ok, msg, status = result
        assert ok is True
        assert status == STATUS_ALREADY_HAD_FLAG

    def test_already_had_flag_status(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")

        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_read.return_value = {"target": "chrome.exe", "arguments": CDP_FLAG}
            ok, msg, status = add_cdp_flag(str(lnk))

        assert ok is True
        assert status == STATUS_ALREADY_HAD_FLAG

    def test_modified_status_when_flag_added(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake lnk")

        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read, \
             patch("reflex_companion.browser_setup._write_lnk_args_via_ps") as mock_write:
            mock_read.return_value = {"target": "chrome.exe", "arguments": ""}
            mock_write.return_value = True
            ok, msg, status = add_cdp_flag(str(lnk))

        assert ok is True
        assert status == STATUS_MODIFIED
        # Verifica que llamó a _write con el flag añadido
        write_call_args = mock_write.call_args[0]
        assert CDP_FLAG in write_call_args[1]

    def test_failed_status_when_read_fails(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_read.return_value = None
            ok, msg, status = add_cdp_flag("C:\\fake.lnk")
        assert ok is False
        assert status == STATUS_FAILED

    def test_failed_status_when_write_fails(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")

        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read, \
             patch("reflex_companion.browser_setup._write_lnk_args_via_ps") as mock_write:
            mock_read.return_value = {"target": "chrome.exe", "arguments": ""}
            mock_write.return_value = False
            ok, msg, status = add_cdp_flag(str(lnk))
        assert ok is False
        assert status == STATUS_FAILED

    def test_existing_args_preserved(self, tmp_path, monkeypatch):
        """Si el .lnk ya tenía args (ej: --profile-directory=Default),
        los preservamos al añadir el CDP flag."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")

        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read, \
             patch("reflex_companion.browser_setup._write_lnk_args_via_ps") as mock_write:
            mock_read.return_value = {
                "target": "chrome.exe",
                "arguments": '--profile-directory="Default"',
            }
            mock_write.return_value = True
            ok, msg, status = add_cdp_flag(str(lnk))

        new_args = mock_write.call_args[0][1]
        assert "--profile-directory" in new_args
        assert CDP_FLAG in new_args


class TestRemoveCDPFlag:
    def test_returns_3_tuple_with_status(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")
        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_read.return_value = {"target": "chrome.exe", "arguments": ""}
            result = remove_cdp_flag(str(lnk))
        assert isinstance(result, tuple) and len(result) == 3

    def test_no_flag_to_remove_status(self, tmp_path, monkeypatch):
        """v0.19.34 (C3) — si el .lnk no tenía el flag, status =
        STATUS_NO_FLAG_TO_REMOVE (NO STATUS_MODIFIED)."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")
        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_read.return_value = {"target": "chrome.exe", "arguments": ""}
            ok, msg, status = remove_cdp_flag(str(lnk))
        assert ok is True
        assert status == STATUS_NO_FLAG_TO_REMOVE

    def test_restores_from_backup_if_exists(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("modified content")
        bak = _backup_path_for(str(lnk))
        bak.parent.mkdir(parents=True, exist_ok=True)
        bak.write_text("ORIGINAL content")

        ok, msg, status = remove_cdp_flag(str(lnk))

        assert ok is True
        assert status == STATUS_MODIFIED
        assert lnk.read_text() == "ORIGINAL content"

    def test_string_replace_when_no_backup(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        lnk = tmp_path / "Chrome.lnk"
        lnk.write_text("fake")
        with patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read, \
             patch("reflex_companion.browser_setup._write_lnk_args_via_ps") as mock_write:
            mock_read.return_value = {
                "target": "chrome.exe",
                "arguments": f"--profile=Default {CDP_FLAG}",
            }
            mock_write.return_value = True
            ok, msg, status = remove_cdp_flag(str(lnk))
        assert ok is True
        assert status == STATUS_MODIFIED
        # Args escritos no deben contener CDP_FLAG
        new_args = mock_write.call_args[0][1]
        assert CDP_FLAG not in new_args
        assert "--profile=Default" in new_args


# ════════════════════════════════════════════════════════════════════════
#  configure_all_shortcuts — integration
# ════════════════════════════════════════════════════════════════════════


class TestConfigureAllShortcuts:
    """v0.19.34 (C3) — el contador "skipped" usa status_code, NO
    string match en mensajes ES."""

    def test_returns_correct_keys(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find:
            mock_find.return_value = []
            result = configure_all_shortcuts(enable=True)
        assert set(result.keys()) == {"shortcuts", "modified", "skipped", "failed", "total"}
        assert result["total"] == 0

    def test_counts_status_modified_correctly(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        fake_shortcuts = [
            {"path": str(tmp_path / "Chrome.lnk"), "browser": "Chrome",
             "target_exe": "chrome.exe", "has_cdp_flag": False, "arguments": ""},
        ]
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add:
            mock_find.return_value = fake_shortcuts
            mock_add.return_value = (True, "msg", STATUS_MODIFIED)
            result = configure_all_shortcuts(enable=True)
        assert result["modified"] == 1
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert result["total"] == 1

    def test_counts_status_already_correctly(self, tmp_path, monkeypatch):
        """v0.19.34 (C3) — si add_cdp_flag devuelve STATUS_ALREADY_HAD_FLAG,
        debe contarse como skipped, NO como modified."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        fake_shortcuts = [
            {"path": str(tmp_path / f"Chrome{i}.lnk"), "browser": "Chrome",
             "target_exe": "chrome.exe", "has_cdp_flag": True, "arguments": CDP_FLAG}
            for i in range(5)
        ]
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add:
            mock_find.return_value = fake_shortcuts
            mock_add.return_value = (True, "ya tenía", STATUS_ALREADY_HAD_FLAG)
            result = configure_all_shortcuts(enable=True)
        assert result["skipped"] == 5
        assert result["modified"] == 0
        assert result["failed"] == 0

    def test_counts_status_failed_correctly(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        fake_shortcuts = [
            {"path": str(tmp_path / "Chrome.lnk"), "browser": "Chrome",
             "target_exe": "chrome.exe", "has_cdp_flag": False, "arguments": ""},
        ]
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add:
            mock_find.return_value = fake_shortcuts
            mock_add.return_value = (False, "no pude", STATUS_FAILED)
            result = configure_all_shortcuts(enable=True)
        assert result["failed"] == 1
        assert result["modified"] == 0
        assert result["skipped"] == 0

    def test_skipped_count_does_NOT_depend_on_spanish_strings(self, tmp_path, monkeypatch):
        """REGRESIÓN C3 — si el mensaje human-facing cambia (ej: traducimos
        a inglés), el contador `skipped` debe seguir funcionando porque
        depende del status_code, no del string match."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        # Mock con MENSAJE EN INGLÉS (ya tenía no aparece) pero status correcto
        fake_shortcuts = [
            {"path": str(tmp_path / "Chrome.lnk"), "browser": "Chrome",
             "target_exe": "chrome.exe", "has_cdp_flag": True, "arguments": CDP_FLAG},
        ]
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add:
            mock_find.return_value = fake_shortcuts
            # Mensaje en inglés (no contiene "ya tenía") + status correcto
            mock_add.return_value = (True, "Chrome.lnk: already had the flag", STATUS_ALREADY_HAD_FLAG)
            result = configure_all_shortcuts(enable=True)
        assert result["skipped"] == 1, (
            "El contador `skipped` debe basarse en status_code, NO en "
            "string match del mensaje. Si está en inglés también debe contarse."
        )

    def test_mixed_results_counts_correctly(self, tmp_path, monkeypatch):
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        fake_shortcuts = [
            {"path": str(tmp_path / f"s{i}.lnk"), "browser": "Chrome",
             "target_exe": "chrome.exe", "has_cdp_flag": False, "arguments": ""}
            for i in range(6)
        ]
        results_iter = iter([
            (True, "msg", STATUS_MODIFIED),
            (True, "msg", STATUS_MODIFIED),
            (True, "msg", STATUS_ALREADY_HAD_FLAG),
            (True, "msg", STATUS_ALREADY_HAD_FLAG),
            (True, "msg", STATUS_ALREADY_HAD_FLAG),
            (False, "fail", STATUS_FAILED),
        ])
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add:
            mock_find.return_value = fake_shortcuts
            mock_add.side_effect = lambda p: next(results_iter)
            result = configure_all_shortcuts(enable=True)
        assert result["modified"] == 2
        assert result["skipped"] == 3
        assert result["failed"] == 1
        assert result["total"] == 6

    def test_disable_uses_remove_cdp_flag(self, tmp_path, monkeypatch):
        """enable=False debe llamar a remove_cdp_flag, NO a add_cdp_flag."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        fake = [{"path": str(tmp_path / "x.lnk"), "browser": "Chrome",
                 "target_exe": "chrome.exe", "has_cdp_flag": True, "arguments": CDP_FLAG}]
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add, \
             patch("reflex_companion.browser_setup.remove_cdp_flag") as mock_remove:
            mock_find.return_value = fake
            mock_remove.return_value = (True, "msg", STATUS_MODIFIED)
            configure_all_shortcuts(enable=False)
            assert mock_remove.called
            assert not mock_add.called

    def test_status_field_in_per_shortcut_result(self, tmp_path, monkeypatch):
        """Cada entry en `shortcuts` debe tener un campo `status`."""
        from reflex_companion import config
        monkeypatch.setattr(config, "_data_path",
                            lambda f: str(tmp_path / f))
        fake = [{"path": str(tmp_path / "x.lnk"), "browser": "Chrome",
                 "target_exe": "chrome.exe", "has_cdp_flag": False, "arguments": ""}]
        with patch("reflex_companion.browser_setup.find_browser_shortcuts") as mock_find, \
             patch("reflex_companion.browser_setup.add_cdp_flag") as mock_add:
            mock_find.return_value = fake
            mock_add.return_value = (True, "msg", STATUS_MODIFIED)
            result = configure_all_shortcuts(enable=True)
        assert "status" in result["shortcuts"][0]
        assert result["shortcuts"][0]["status"] == STATUS_MODIFIED


# ════════════════════════════════════════════════════════════════════════
#  Logging coverage (M6)
# ════════════════════════════════════════════════════════════════════════


class TestLoggingPresent:
    """v0.19.34 (M6) — browser_setup debe usar logging para todos los
    paths de error/warning. Sin esto los problemas son invisibles."""

    def test_module_has_logger(self):
        assert hasattr(bs, "_log")
        assert bs._log.name == "ashley.browser_setup"

    def test_timeout_logs_warning(self, caplog):
        """Un TimeoutExpired en _read_lnk_via_ps debe loguear."""
        import subprocess
        with patch("reflex_companion.browser_setup.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=5)
            with caplog.at_level("WARNING", logger="ashley.browser_setup"):
                result = bs._read_lnk_via_ps("C:\\fake.lnk")
            assert result is None
            assert any("timeout" in r.message.lower() for r in caplog.records), (
                "Timeout en _read_lnk_via_ps debe loguearse como warning"
            )

    def test_nonzero_returncode_logs_warning(self, caplog):
        with patch("reflex_companion.browser_setup.subprocess.run") as mock_run:
            mock_run.return_value = _mock_ps_run(
                stdout="", stderr="some error", returncode=1,
            )
            with caplog.at_level("WARNING", logger="ashley.browser_setup"):
                result = bs._read_lnk_via_ps("C:\\fake.lnk")
            assert result is None
            assert any("falló" in r.message or "failed" in r.message.lower()
                       for r in caplog.records)


# ════════════════════════════════════════════════════════════════════════
#  Verify-on-write (M1)
# ════════════════════════════════════════════════════════════════════════


class TestVerifyOnWrite:
    """v0.19.34 (M1) — si stderr no vacío tras write, re-leemos el .lnk
    para verificar que la escritura persistió."""

    def test_stderr_empty_no_verify(self):
        """Happy path: stderr vacío → no re-leemos (ahorra subprocess call)."""
        with patch("reflex_companion.browser_setup.subprocess.run") as mock_run, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_run.return_value = _mock_ps_run(stdout="", stderr="", returncode=0)
            ok = bs._write_lnk_args_via_ps("C:\\fake.lnk", "--remote-debugging-port=9222")
            assert ok is True
            # Verify NO se llamó (stderr empty)
            assert not mock_read.called

    def test_stderr_nonempty_triggers_verify_match(self):
        """Stderr non-vacío + write OK → re-leemos. Si match, devuelve True."""
        with patch("reflex_companion.browser_setup.subprocess.run") as mock_run, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_run.return_value = _mock_ps_run(
                stdout="", stderr="COM warning", returncode=0,
            )
            mock_read.return_value = {
                "target": "chrome.exe",
                "arguments": "--remote-debugging-port=9222",
            }
            ok = bs._write_lnk_args_via_ps("C:\\fake.lnk", "--remote-debugging-port=9222")
            assert ok is True
            assert mock_read.called  # se llamó verify

    def test_stderr_nonempty_verify_mismatch_returns_false(self):
        """Stderr non-vacío + verify NO match → return False (write no persistió)."""
        with patch("reflex_companion.browser_setup.subprocess.run") as mock_run, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_read:
            mock_run.return_value = _mock_ps_run(
                stdout="", stderr="COM error", returncode=0,
            )
            # Verify devuelve args distintos a lo que escribimos
            mock_read.return_value = {
                "target": "chrome.exe",
                "arguments": "old args",
            }
            ok = bs._write_lnk_args_via_ps("C:\\fake.lnk", "--remote-debugging-port=9222")
            assert ok is False
