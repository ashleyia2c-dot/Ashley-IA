"""Regression tests for v0.19.35 fixes:

1. M3 — Batch PowerShell reader para find_browser_shortcuts.
   Antes: 1 subprocess por .lnk → ~30s en PCs pobladas.
   Ahora: 1 subprocess para TODOS los .lnk → ~3-5s.
   Tests cubren: parsing del output, error per-entry no rompe batch,
   timeout escalado, integration con find_browser_shortcuts.

2. M4 — settings_cdp_howto extendido con nota sobre taskbar pins.
   Tests verifican que los 7 idiomas tienen la palabra clave "taskbar"/
   "barre des tâches"/"タスクバー"/"Taskleisten"/"панели задач"/"작업 표시줄"
   o equivalente para confirmar la nota está presente en cada lang.
"""
from unittest.mock import patch, MagicMock
import subprocess

import pytest


# ════════════════════════════════════════════════════════════════════════
#  M3 — _read_lnks_batch + _parse_batch_lnk_output
# ════════════════════════════════════════════════════════════════════════


class TestParseBatchLnkOutput:
    """Tests del parser sin subprocess (pure function)."""

    def test_empty_input_returns_empty(self):
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        assert _parse_batch_lnk_output("") == {}

    def test_single_entry_parsed_correctly(self):
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        output = (
            "PATH=C:\\Users\\test\\Chrome.lnk\n"
            "TARGET=C:\\Program Files\\Google\\Chrome\\chrome.exe\n"
            "ARGS=--profile-directory=Default\n"
            "WD=C:\\Program Files\\Google\\Chrome\n"
            "---\n"
        )
        result = _parse_batch_lnk_output(output)
        assert "C:\\Users\\test\\Chrome.lnk" in result
        entry = result["C:\\Users\\test\\Chrome.lnk"]
        assert entry["target"] == "C:\\Program Files\\Google\\Chrome\\chrome.exe"
        assert entry["arguments"] == "--profile-directory=Default"
        assert entry["working_directory"] == "C:\\Program Files\\Google\\Chrome"

    def test_multiple_entries_parsed(self):
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        output = (
            "PATH=C:\\a.lnk\n"
            "TARGET=A.exe\n"
            "ARGS=\n"
            "WD=\n"
            "---\n"
            "PATH=C:\\b.lnk\n"
            "TARGET=B.exe\n"
            "ARGS=--foo\n"
            "WD=C:\\\n"
            "---\n"
        )
        result = _parse_batch_lnk_output(output)
        assert len(result) == 2
        assert result["C:\\a.lnk"]["target"] == "A.exe"
        assert result["C:\\b.lnk"]["arguments"] == "--foo"

    def test_error_entry_excluded_from_result(self):
        """Si un .lnk dio ERROR=, no debe aparecer en el dict."""
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        output = (
            "PATH=C:\\good.lnk\n"
            "TARGET=A.exe\n"
            "ARGS=\n"
            "WD=\n"
            "---\n"
            "PATH=C:\\corrupt.lnk\n"
            "ERROR=Cannot open shortcut\n"
            "---\n"
            "PATH=C:\\good2.lnk\n"
            "TARGET=B.exe\n"
            "ARGS=\n"
            "WD=\n"
            "---\n"
        )
        result = _parse_batch_lnk_output(output)
        assert set(result.keys()) == {"C:\\good.lnk", "C:\\good2.lnk"}
        assert "C:\\corrupt.lnk" not in result, (
            "Entry con ERROR= no debe aparecer en el resultado"
        )

    def test_handles_crlf_line_endings(self):
        """PowerShell en Windows emite CRLF — el parser debe rstripearlos."""
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        output = (
            "PATH=C:\\a.lnk\r\n"
            "TARGET=A.exe\r\n"
            "ARGS=\r\n"
            "WD=\r\n"
            "---\r\n"
        )
        result = _parse_batch_lnk_output(output)
        assert "C:\\a.lnk" in result
        assert result["C:\\a.lnk"]["target"] == "A.exe"

    def test_entry_without_target_excluded(self):
        """Entry sin TARGET= (parse rota a mitad) no debe aparecer."""
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        output = (
            "PATH=C:\\incomplete.lnk\n"
            "ARGS=--foo\n"  # Falta TARGET
            "WD=\n"
            "---\n"
        )
        result = _parse_batch_lnk_output(output)
        assert "C:\\incomplete.lnk" not in result

    def test_path_with_special_chars(self):
        """Paths con espacios, apóstrofes, símbolos se preservan tal cual."""
        from reflex_companion.browser_setup import _parse_batch_lnk_output
        path = "C:\\Users\\O'Brien\\Some Folder (x86)\\Chrome.lnk"
        output = (
            f"PATH={path}\n"
            "TARGET=chrome.exe\n"
            "ARGS=\n"
            "WD=\n"
            "---\n"
        )
        result = _parse_batch_lnk_output(output)
        assert path in result


class TestReadLnksBatch:
    """Tests del batch reader con subprocess mockeado."""

    def test_empty_list_returns_empty_dict_no_subprocess(self):
        """Lista vacía no debe llamar a subprocess."""
        from reflex_companion import browser_setup
        with patch("reflex_companion.browser_setup.subprocess.run") as mock_run:
            result = browser_setup._read_lnks_batch([])
            assert result == {}
            assert not mock_run.called

    def test_subprocess_called_with_stdin_input(self):
        """El batch reader debe pasar paths via stdin (no via cmdline)."""
        from reflex_companion import browser_setup
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "PATH=A.lnk\nTARGET=A.exe\nARGS=\nWD=\n---\n"
        mock_result.stderr = ""
        with patch("reflex_companion.browser_setup.subprocess.run",
                   return_value=mock_result) as mock_run:
            browser_setup._read_lnks_batch(["A.lnk", "B.lnk", "C.lnk"])
            call_kwargs = mock_run.call_args[1]
            # stdin debe contener los paths separados por newlines
            assert "input" in call_kwargs
            stdin_data = call_kwargs["input"]
            assert "A.lnk" in stdin_data
            assert "B.lnk" in stdin_data
            assert "C.lnk" in stdin_data

    def test_timeout_returns_empty_dict(self):
        from reflex_companion import browser_setup
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="ps", timeout=10)):
            result = browser_setup._read_lnks_batch(["A.lnk"])
            assert result == {}

    def test_nonzero_returncode_returns_empty(self):
        from reflex_companion import browser_setup
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "PowerShell error"
        with patch("reflex_companion.browser_setup.subprocess.run",
                   return_value=mock_result):
            result = browser_setup._read_lnks_batch(["A.lnk"])
            assert result == {}

    def test_timeout_scales_with_batch_size(self):
        """200 paths debe tener timeout más alto que 5 paths."""
        from reflex_companion import browser_setup
        timeout_calls = []
        def capture(*args, **kwargs):
            timeout_calls.append(kwargs.get("timeout", 0))
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=capture):
            browser_setup._read_lnks_batch(["A.lnk"] * 5)
            browser_setup._read_lnks_batch(["A.lnk"] * 200)
        assert timeout_calls[1] > timeout_calls[0], (
            "Timeout debe escalar con batch size para no fallar en PCs grandes"
        )

    def test_subprocess_exception_returns_empty(self):
        from reflex_companion import browser_setup
        with patch("reflex_companion.browser_setup.subprocess.run",
                   side_effect=Exception("boom")):
            result = browser_setup._read_lnks_batch(["A.lnk"])
            assert result == {}


class TestFindBrowserShortcutsUsesBatch:
    """v0.19.35 (M3) — find_browser_shortcuts ahora usa _read_lnks_batch
    en vez de N llamadas a _read_lnk_via_ps."""

    def test_calls_batch_reader_not_per_path(self, tmp_path, monkeypatch):
        """find_browser_shortcuts debe llamar a _read_lnks_batch UNA vez,
        no a _read_lnk_via_ps N veces."""
        from reflex_companion import browser_setup

        # Crear .lnk falsos en tmp_path
        lnk1 = tmp_path / "Chrome.lnk"
        lnk1.write_text("fake")
        lnk2 = tmp_path / "Edge.lnk"
        lnk2.write_text("fake")

        # Mock _shortcut_locations para devolver tmp_path
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch, \
             patch("reflex_companion.browser_setup._read_lnk_via_ps") as mock_single:
            mock_batch.return_value = {
                str(lnk1): {"target": "C:\\Program Files\\chrome.exe",
                            "arguments": "", "working_directory": ""},
                str(lnk2): {"target": "C:\\Program Files\\msedge.exe",
                            "arguments": "", "working_directory": ""},
            }
            result = browser_setup.find_browser_shortcuts()

            # _read_lnks_batch llamado exactamente 1 vez
            assert mock_batch.call_count == 1
            # _read_lnk_via_ps NO debe llamarse desde find_browser_shortcuts
            assert mock_single.call_count == 0, (
                "find_browser_shortcuts debe usar batch, no llamadas individuales"
            )
            # Deben encontrarse los 2 browsers
            assert len(result) == 2

    def test_batch_failure_returns_empty(self, tmp_path, monkeypatch):
        """Si el batch reader devuelve {} (timeout), find_browser_shortcuts
        devuelve [] sin crashear."""
        from reflex_companion import browser_setup

        (tmp_path / "Chrome.lnk").write_text("fake")
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch:
            mock_batch.return_value = {}
            result = browser_setup.find_browser_shortcuts()
            assert result == []

    def test_only_chromium_browsers_included(self, tmp_path, monkeypatch):
        """find_browser_shortcuts solo devuelve .lnk que apuntan a
        browsers Chromium conocidos (no Firefox, no Notepad, etc.)."""
        from reflex_companion import browser_setup

        for name in ["Chrome.lnk", "Firefox.lnk", "Notepad.lnk", "Edge.lnk"]:
            (tmp_path / name).write_text("fake")
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch:
            mock_batch.return_value = {
                str(tmp_path / "Chrome.lnk"): {"target": "C:\\chrome.exe",
                                                "arguments": "", "working_directory": ""},
                str(tmp_path / "Firefox.lnk"): {"target": "C:\\firefox.exe",
                                                 "arguments": "", "working_directory": ""},
                str(tmp_path / "Notepad.lnk"): {"target": "C:\\Windows\\notepad.exe",
                                                 "arguments": "", "working_directory": ""},
                str(tmp_path / "Edge.lnk"): {"target": "C:\\msedge.exe",
                                              "arguments": "", "working_directory": ""},
            }
            result = browser_setup.find_browser_shortcuts()

        target_exes = {r["target_exe"] for r in result}
        assert target_exes == {"chrome.exe", "msedge.exe"}, (
            f"Solo browsers Chromium esperados, got: {target_exes}"
        )

    def test_paths_deduplicated(self, tmp_path, monkeypatch):
        """Si _shortcut_locations devuelve dos directorios que apuntan al
        mismo .lnk, no debe aparecer duplicado en el resultado."""
        from reflex_companion import browser_setup

        (tmp_path / "Chrome.lnk").write_text("fake")
        # Devolver el mismo dir dos veces
        monkeypatch.setattr(browser_setup, "_shortcut_locations",
                            lambda: [tmp_path, tmp_path])

        with patch("reflex_companion.browser_setup._read_lnks_batch") as mock_batch:
            mock_batch.return_value = {
                str(tmp_path / "Chrome.lnk"): {"target": "C:\\chrome.exe",
                                                "arguments": "", "working_directory": ""},
            }
            result = browser_setup.find_browser_shortcuts()

        assert len(result) == 1


# ════════════════════════════════════════════════════════════════════════
#  M4 — settings_cdp_howto extendido con nota de taskbar
# ════════════════════════════════════════════════════════════════════════


class TestTaskbarNoteInHowto:
    """v0.19.35 (M4) — el howto debe contener una nota sobre taskbar pins
    en los 7 idiomas, ya que pins modernos pueden saltarse el wizard."""

    # Marcadores específicos de cada idioma para verificar la presencia
    # de la nota sobre el taskbar pin (sin depender de palabra exacta).
    TASKBAR_MARKERS = {
        "en": ["taskbar pin"],
        "es": ["pin de la barra de tareas", "pins del taskbar"],
        "fr": ["barre des tâches"],
        "ja": ["タスクバー"],
        "de": ["Taskleisten"],
        "ru": ["панели задач"],
        "ko": ["작업 표시줄"],
    }

    def test_all_7_langs_mention_taskbar(self):
        from reflex_companion import i18n
        for lang, markers in self.TASKBAR_MARKERS.items():
            howto = i18n.UI[lang]["settings_cdp_howto"]
            assert any(m in howto for m in markers), (
                f"Lang {lang!r} settings_cdp_howto debe mencionar taskbar "
                f"pins. Markers buscados: {markers}. Got: {howto[:200]!r}"
            )

    def test_all_7_langs_mention_start_menu_or_desktop_alternative(self):
        """La nota debe sugerir abrir desde Start Menu o Desktop como
        alternativa al taskbar pin."""
        from reflex_companion import i18n
        # Marcadores aceptables (cualquiera de los dos en cada idioma)
        ALTERNATIVES = {
            "en": ["Start Menu", "Desktop"],
            "es": ["Menú Inicio", "Escritorio"],
            "fr": ["menu Démarrer", "Bureau"],
            "ja": ["スタートメニュー", "デスクトップ"],
            "de": ["Startmenü", "Desktop"],
            "ru": ["меню Пуск", "Рабочего стола", "Рабочий стол"],
            "ko": ["시작 메뉴", "바탕화면"],
        }
        for lang, alternatives in ALTERNATIVES.items():
            howto = i18n.UI[lang]["settings_cdp_howto"]
            assert any(a in howto for a in alternatives), (
                f"Lang {lang!r} debe sugerir abrir desde Start Menu/Desktop "
                f"como alternativa al taskbar pin. Markers: {alternatives}. "
                f"Got: {howto[:200]!r}"
            )

    def test_warning_emoji_present_for_visibility(self):
        """La nota usa el emoji ⚠ para distinguirla visualmente del
        primer paragraph del howto. Verificar en los 7 langs."""
        from reflex_companion import i18n
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            howto = i18n.UI[lang]["settings_cdp_howto"]
            assert "⚠" in howto, (
                f"Lang {lang!r} debe tener ⚠ para distinguir la nota "
                f"del taskbar visualmente"
            )

    def test_close_reopen_browser_message_preserved(self):
        """La fix M4 EXTIENDE el howto, no lo reemplaza. El mensaje
        original 'close and reopen browser' debe seguir presente."""
        from reflex_companion import i18n
        # Marcadores del mensaje original (cierra+abre navegador)
        ORIGINAL_MARKERS = {
            "en": ["close and reopen", "close", "reopen"],
            "es": ["cierra y reabre", "reabre"],
            "fr": ["ferme et rouvre", "rouvre"],
            "ja": ["閉じて再度開いて", "再度開"],
            "de": ["schließe und öffne", "öffne"],
            "ru": ["закрой и снова открой", "снова открой"],
            "ko": ["다시 열어", "닫고 다시"],
        }
        for lang, markers in ORIGINAL_MARKERS.items():
            howto = i18n.UI[lang]["settings_cdp_howto"]
            assert any(m in howto for m in markers), (
                f"Lang {lang!r} debe preservar el mensaje original sobre "
                f"reabrir navegador. Markers: {markers}"
            )
