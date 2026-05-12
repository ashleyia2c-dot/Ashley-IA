"""Regression tests para v0.19.43 — fix de Python procesos colgados al
cerrar Ashley.

User reportó: 'al cerrar la app de ashley no queda nada abierto en el pc,
ya pasa que se queda python corriendo despues de cerrar la app, esos
fixes ya habian sido corregidos y ahora vuelven'.

Causas raíz identificadas:

1. **`killStrayAshleyProcesses` async no se awaiteaba** en killReflex:
   `try { killStrayAshleyProcesses(); } catch {}` lanza un Promise pero
   no espera. Cuando Electron empieza a cerrarse (app.quit), el event
   loop empieza a teardown. El callback de `exec()` async puede no
   ejecutarse → sweep cancelado mid-flight → procesos huérfanos.

2. **Falta `granian.exe`, `cloudflared.exe`, `pythonw.exe` del kill list**.
   Reflex usa granian (HTTP server) que NO es python.exe — su image
   name es granian.exe. cloudflared.exe (mobile tunnel) tampoco se
   mataba. pythonw.exe (Python embeddable variant) tampoco.

3. **El regex de killStrayAshleyProcesses** solo incluía
   `python|node|bun|reflex` y matcheaba SOLO por CommandLine. Subprocess
   pythons spawned con `python -c "<inline script>"` (ej. el keyboard
   sim de actions.py:1927) no tienen el repo path en su CommandLine,
   solo en su ExecutablePath. → No los catchaba.

Fixes:
  • Nueva función killStrayAshleyProcessesSync que usa execSync (bloquea
    hasta completar antes de que Electron salga).
  • IMG list extendido: pythonw.exe, granian.exe, cloudflared.exe añadidos.
  • Helper _buildAshleySweepScript con regex extendido y match por
    ExecutablePath (cubre subprocess pythons sin path en cmdline).
"""
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_JS = REPO_ROOT / "electron" / "main.js"


@pytest.fixture(scope="module")
def main_js_source() -> str:
    return MAIN_JS.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  Fix 1 — Sync sweep en killReflex (no más async no-awaited)
# ════════════════════════════════════════════════════════════════════════


class TestSyncSweepInKillReflex:
    """v0.19.43 — killReflex debe llamar killStrayAshleyProcessesSync
    (bloqueante) NO killStrayAshleyProcesses (async sin await)."""

    def test_sync_sweep_function_exists(self, main_js_source):
        assert "function killStrayAshleyProcessesSync" in main_js_source, (
            "Falta killStrayAshleyProcessesSync. La versión async se "
            "cancelaba mid-flight cuando Electron salía → procesos huérfanos."
        )

    def test_sync_sweep_uses_execSync(self, main_js_source):
        match = re.search(
            r"function killStrayAshleyProcessesSync[\s\S]*?(?=\n\n)",
            main_js_source,
        )
        assert match, "No se localizó killStrayAshleyProcessesSync"
        body = match.group(0)
        assert "execSync" in body, (
            "killStrayAshleyProcessesSync DEBE usar execSync (bloqueante) "
            "para garantizar que el sweep complete antes de Electron quit"
        )

    def test_kill_reflex_calls_sync_sweep(self, main_js_source):
        # El cuerpo de killReflex debe llamar killStrayAshleyProcessesSync,
        # no la versión async (que no se await)
        match = re.search(
            r"function killReflex\(\)[\s\S]*?(?=\n// ─{3,}|\nfunction )",
            main_js_source,
        )
        assert match, "No se localizó killReflex"
        body = match.group(0)
        assert "killStrayAshleyProcessesSync" in body, (
            "killReflex DEBE llamar killStrayAshleyProcessesSync. La "
            "versión async (killStrayAshleyProcesses) sin await no "
            "completa antes de que Electron salga."
        )


# ════════════════════════════════════════════════════════════════════════
#  Fix 2 — Granian, cloudflared, pythonw añadidos al IMG list
# ════════════════════════════════════════════════════════════════════════


class TestKillImagesExpanded:
    """v0.19.43 — el sweep por image name debe incluir TODOS los
    binarios que Ashley puede spawnar."""

    def test_pythonw_exe_in_kill_list(self, main_js_source):
        """python-embed bundle incluye pythonw.exe (Python sin consola).
        Si algún path la usa, sin esto se queda colgada."""
        # Buscar el array de IMG names en killReflex
        match = re.search(
            r"function killReflex\(\)[\s\S]*?(?=\n// ─{3,}|\nfunction )",
            main_js_source,
        )
        body = match.group(0)
        assert "'pythonw.exe'" in body or '"pythonw.exe"' in body, (
            "pythonw.exe DEBE estar en el sweep. python-embed lo incluye."
        )

    def test_granian_exe_in_kill_list(self, main_js_source):
        """granian es el HTTP server de Reflex. Su image es granian.exe,
        NO python.exe — sin esto, queda corriendo el server tras cerrar."""
        match = re.search(
            r"function killReflex\(\)[\s\S]*?(?=\n// ─{3,}|\nfunction )",
            main_js_source,
        )
        body = match.group(0)
        assert "'granian.exe'" in body or '"granian.exe"' in body, (
            "granian.exe DEBE estar en el sweep. Es el HTTP server de "
            "Reflex y su image NO es python.exe."
        )

    def test_cloudflared_exe_in_kill_list(self, main_js_source):
        """cloudflared.exe es el tunnel para mobile companion. Si user
        lo activó y cierra Ashley, sin esto sigue corriendo."""
        match = re.search(
            r"function killReflex\(\)[\s\S]*?(?=\n// ─{3,}|\nfunction )",
            main_js_source,
        )
        body = match.group(0)
        assert "'cloudflared.exe'" in body or '"cloudflared.exe"' in body, (
            "cloudflared.exe DEBE estar en el sweep. Es el tunnel del "
            "mobile companion."
        )


# ════════════════════════════════════════════════════════════════════════
#  Fix 3 — Sweep matchea por ExecutablePath además de CommandLine
# ════════════════════════════════════════════════════════════════════════


class TestSweepMatchesByExecutablePath:
    """v0.19.43 — el sweep CIM debe matchear ExecutablePath además de
    CommandLine. Subprocess pythons spawned con `python -c "<script>"`
    no tienen el repo path en su CommandLine pero su ExecutablePath
    sí está bajo Programs\\Ashley o el repo path."""

    def test_helper_function_exists(self, main_js_source):
        assert "_buildAshleySweepScript" in main_js_source, (
            "Falta _buildAshleySweepScript helper centralizado para "
            "construir el script de sweep (sync + async lo comparten)"
        )

    def test_sweep_script_matches_executablepath(self, main_js_source):
        match = re.search(
            r"function _buildAshleySweepScript[\s\S]*?(?=\n\n)",
            main_js_source,
        )
        assert match, "No se localizó _buildAshleySweepScript"
        body = match.group(0)
        assert "ExecutablePath" in body, (
            "El sweep DEBE matchear por ExecutablePath además de "
            "CommandLine. Subprocess pythons sin repo path en cmdline "
            "se identifican por ExecutablePath del bundle."
        )

    def test_sweep_script_matches_programs_ashley_path(self, main_js_source):
        """En producción, los binarios están en %LOCALAPPDATA%\\Programs\\
        Ashley\\... — debe matchearse esa marca para catchear todo lo
        bundled aunque no tenga PROJECT_ROOT en cmdline."""
        match = re.search(
            r"function _buildAshleySweepScript[\s\S]*?(?=\n\n)",
            main_js_source,
        )
        body = match.group(0)
        assert "Programs" in body and "Ashley" in body, (
            "El sweep debe incluir match por path '\\Programs\\Ashley\\*' "
            "para production builds donde los binarios viven en "
            "%LOCALAPPDATA%\\Programs\\Ashley\\..."
        )

    def test_sweep_script_includes_granian_and_cloudflared_in_regex(
            self, main_js_source):
        """El regex Name -match debe incluir granian y cloudflared."""
        match = re.search(
            r"function _buildAshleySweepScript[\s\S]*?(?=\n\n)",
            main_js_source,
        )
        body = match.group(0)
        # Buscar la regex que matchea Name
        assert "granian" in body, (
            "El regex de Name del sweep debe incluir granian"
        )
        assert "cloudflared" in body, (
            "El regex de Name del sweep debe incluir cloudflared"
        )
        assert "pythonw" in body, (
            "El regex de Name del sweep debe incluir pythonw"
        )


# ════════════════════════════════════════════════════════════════════════
#  Sanity: main.js sigue siendo JS válido
# ════════════════════════════════════════════════════════════════════════


class TestMainJsSyntaxValid:
    """Después de cambios estructurales, verificar sintaxis JS."""

    def test_main_js_syntax_valid(self, main_js_source):
        import shutil as _sh
        import subprocess as _sp
        node = _sh.which("node")
        if not node:
            pytest.skip("node no disponible")
        result = _sp.run(
            [node, "--check", str(MAIN_JS)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, (
            f"main.js tiene syntax errors:\n{result.stderr}"
        )
