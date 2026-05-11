"""Regression tests for v0.19.31 fixes:

1. CDP wizard result messages estaban hardcoded en español → user con UI
   en EN/JA/DE/etc veía ES (ej: "✓ Los 5 accesos directos ya tenían el
   flag activo." apareciendo bajo el toggle CDP en una UI inglesa).
   Fix: 7 keys nuevas en i18n.UI × 7 idiomas + lookup en
   run_cdp_setup_wizard.

2. Agentic continuation re-emitía la MISMA acción cuando el user pidió
   solo una acción terminal (típicamente play_music). Bug producción:
   "pon la música de nuevo" → Ashley emitió play_music, sonó la canción,
   luego el follow-up auto-disparó un segundo turn donde Ashley re-emitió
   play_music con la MISMA URL → 2 tabs idénticas en Opera.
   Fix: nuevo set _TERMINAL_ACTIONS en parsing.py (play_music, screenshot,
   list_windows, read_page) → el should_continue del agentic engine ahora
   skipea cuando la única acción ejecutada es terminal.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"
PARSING_FILE = REPO_ROOT / "reflex_companion" / "parsing.py"


# ════════════════════════════════════════════════════════════════════════
#  i18n — CDP wizard result messages
# ════════════════════════════════════════════════════════════════════════


class TestCDPWizardI18n:
    """Las 7 keys nuevas de cdp_result_* deben existir en los 7 idiomas
    con paridad."""

    REQUIRED_KEYS = {
        "cdp_result_modified",
        "cdp_result_no_shortcuts",
        "cdp_result_already_active",
        "cdp_result_restored",
        "cdp_result_classic_mode",
        "cdp_result_failed_suffix",
        "cdp_result_error",
    }

    def test_all_7_keys_present_in_all_7_langs(self):
        from reflex_companion import i18n
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            ui = i18n.UI[lang]
            missing = self.REQUIRED_KEYS - set(ui.keys())
            assert not missing, (
                f"Lang {lang!r} missing CDP keys: {sorted(missing)}"
            )

    def test_format_placeholders_consistent(self):
        """Las keys con {n}/{err} deben tenerlos en TODOS los idiomas."""
        from reflex_companion import i18n
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            ui = i18n.UI[lang]
            for key in ["cdp_result_modified", "cdp_result_already_active",
                        "cdp_result_restored", "cdp_result_failed_suffix"]:
                assert "{n}" in ui[key], (
                    f"{lang!r}.{key!r} debe contener {{n}}: {ui[key]!r}"
                )
            assert "{err}" in ui["cdp_result_error"], (
                f"{lang!r}.cdp_result_error debe contener {{err}}: "
                f"{ui['cdp_result_error']!r}"
            )

    def test_translations_actually_translated_not_english(self):
        """Las keys NO deben tener el mismo texto que EN en ES/FR/JA/DE/RU/KO
        (excepto símbolos comunes como ✓ ⚠ {n})."""
        from reflex_companion import i18n
        en_values = {k: i18n.UI["en"][k] for k in self.REQUIRED_KEYS}
        for lang in ["es", "fr", "ja", "de", "ru", "ko"]:
            for key, en_val in en_values.items():
                local_val = i18n.UI[lang][key]
                # Strip emoji/symbols/placeholders
                en_clean = re.sub(r'[^\w\s]|\{n\}|\{err\}', '', en_val).strip()
                local_clean = re.sub(
                    r'[^\w\s]|\{n\}|\{err\}', '', local_val
                ).strip()
                if en_clean and local_clean and len(en_clean) > 5:
                    assert en_clean.lower() != local_clean.lower(), (
                        f"{lang!r}.{key!r} == EN value (untranslated): "
                        f"{en_val!r} vs {local_val!r}"
                    )

    def test_no_hardcoded_spanish_in_run_cdp_setup_wizard(self):
        """run_cdp_setup_wizard NO debe contener strings hardcoded en
        español. Todo debe pasar por _ui[...] del dict UI[lang]."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Find the function body
        match = re.search(
            r'async def run_cdp_setup_wizard.*?(?=\n    def |\n    async def |\n    @)',
            src,
            re.DOTALL,
        )
        assert match, "run_cdp_setup_wizard no encontrada"
        body = match.group(0)
        forbidden_es_phrases = [
            "accesos directos",
            "ya tenían el flag",
            "Cierra y reabre",
            "Modo clásico activado",
            "fallaron",
            "Error en el wizard",
            "Activa el flag manualmente",
            "Chromium en tu PC",
        ]
        for phrase in forbidden_es_phrases:
            assert phrase not in body, (
                f"Hardcoded ES en run_cdp_setup_wizard: {phrase!r}. "
                f"Debe usar _ui['cdp_result_*'] en su lugar."
            )

    def test_run_cdp_setup_wizard_uses_i18n_lookups(self):
        """Verifica positivamente que las 6 keys de result se usan en el body."""
        src = RC_FILE.read_text(encoding="utf-8")
        match = re.search(
            r'async def run_cdp_setup_wizard.*?(?=\n    def |\n    async def |\n    @)',
            src,
            re.DOTALL,
        )
        body = match.group(0)
        for key in ["cdp_result_modified", "cdp_result_no_shortcuts",
                    "cdp_result_already_active", "cdp_result_restored",
                    "cdp_result_classic_mode", "cdp_result_failed_suffix",
                    "cdp_result_error"]:
            assert key in body, (
                f"run_cdp_setup_wizard debe usar _ui['{key}']"
            )


# ════════════════════════════════════════════════════════════════════════
#  Agentic continuation — terminal actions skip
# ════════════════════════════════════════════════════════════════════════


class TestAgenticContinuationSkipsTerminalActions:
    """play_music ejecutado UNA VEZ no debe disparar un follow-up turn
    donde Ashley re-emite play_music con la misma URL."""

    def test_terminal_actions_set_exists_and_includes_play_music(self):
        from reflex_companion.parsing import _TERMINAL_ACTIONS
        assert "play_music" in _TERMINAL_ACTIONS, (
            "play_music DEBE estar en _TERMINAL_ACTIONS — bug producción "
            "v0.19.30: 2 tabs idénticas tras 'pon música'"
        )

    def test_terminal_actions_includes_other_self_contained(self):
        from reflex_companion.parsing import _TERMINAL_ACTIONS
        # Estas también son atómicas y no deben triggear continuation
        for action in ["screenshot", "list_windows", "read_page"]:
            assert action in _TERMINAL_ACTIONS, (
                f"{action!r} debe estar en _TERMINAL_ACTIONS"
            )

    def test_terminal_actions_excludes_open_url(self):
        """open_url NO debe ser terminal — multi-step legítimo: 'abre YT
        y busca X' necesita el follow-up turn para emitir search_web."""
        from reflex_companion.parsing import _TERMINAL_ACTIONS
        assert "open_url" not in _TERMINAL_ACTIONS, (
            "open_url no debe ser terminal (rompe flujo multi-step)"
        )

    def test_terminal_actions_excludes_search_web(self):
        from reflex_companion.parsing import _TERMINAL_ACTIONS
        assert "search_web" not in _TERMINAL_ACTIONS, (
            "search_web no debe ser terminal (rompe flujo multi-step)"
        )

    def test_terminal_actions_excludes_open_app(self):
        """open_app puede estar al inicio de un plan ('abre Spotify y pon
        canción X'). Mantenerlo NO terminal."""
        from reflex_companion.parsing import _TERMINAL_ACTIONS
        assert "open_app" not in _TERMINAL_ACTIONS

    def test_should_continue_skips_when_only_action_is_terminal(self):
        """El check de should_continue en _finalize_response debe excluir
        casos donde la única acción ejecutada es terminal."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Localiza el inicio del bloque should_continue y mira los
        # próximos ~600 chars (contiene el bloque entero).
        idx = src.find("should_continue = (")
        assert idx != -1, "should_continue no encontrado"
        block = src[idx:idx + 600]
        assert "not all_terminal" in block, (
            "should_continue debe verificar `not all_terminal` para "
            "skipear el follow-up cuando la única acción fue terminal"
        )

    def test_finalize_response_imports_terminal_actions(self):
        """El import de _TERMINAL_ACTIONS debe estar al top del archivo."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Buscar en los primeros 100 lines
        head = "\n".join(src.split("\n")[:100])
        assert "_TERMINAL_ACTIONS" in head, (
            "Import de _TERMINAL_ACTIONS desde .parsing debe estar al top"
        )

    def test_all_terminal_check_uses_executed_results(self):
        """Verifica el patrón: all(r.get("action",{}).get("type") in
        _TERMINAL_ACTIONS for r in executed_results)"""
        src = RC_FILE.read_text(encoding="utf-8")
        # Buscar en una ventana razonable cerca de should_continue
        idx = src.find("all_terminal")
        assert idx != -1
        # Mirar 300 chars antes para ver la asignación
        block = src[max(0, idx - 50):idx + 400]
        assert "_TERMINAL_ACTIONS" in block, (
            "El check all_terminal debe usar _TERMINAL_ACTIONS"
        )
        assert "executed_results" in block, (
            "El check all_terminal debe iterar sobre executed_results"
        )
