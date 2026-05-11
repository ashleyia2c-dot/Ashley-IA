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
#  Agentic continuation — DISABLED en v0.19.32
# ════════════════════════════════════════════════════════════════════════
#
# Bug producción reportado por el user:
#   "TIENE QUE SER UNA SOLA VEZ PARA TODO ok? si el user pide cualquier
#    cosa una sola vez, pues es una sola vez, no solo musica"
#
# v0.19.32 desactiva la continuation por completo. La justificación
# completa está en el comment del código de _finalize_response.
# ════════════════════════════════════════════════════════════════════════


class TestAgenticContinuationDisabled:
    """v0.19.32 — La agentic continuation auto-replay quedó desactivada.
    Si el user pide UNA cosa, Ashley la hace UNA vez. Si pide multi-step,
    Ashley emite múltiples tags en LA MISMA respuesta (extract_all_actions
    soporta eso desde v0.13.5)."""

    def test_should_continue_is_hardcoded_false(self):
        """should_continue = False debe estar literal en el código."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("should_continue = ")
        assert idx != -1, "should_continue no encontrado"
        # Mirar la asignación en sí
        block = src[idx:idx + 100]
        assert "should_continue = False" in block, (
            "should_continue debe ser False literal en v0.19.32+ — "
            "evita que Ashley re-emita acciones tras single-action requests"
        )

    def test_no_executed_count_eq_1_check_active(self):
        """El check viejo `executed_count == 1` ya no debe estar activo."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Si aparece, debe ser solo en comments (líneas que empiezan con #)
        for ln in src.split("\n"):
            stripped = ln.strip()
            if stripped.startswith("#"):
                continue
            assert "executed_count == 1" not in ln, (
                f"`executed_count == 1` activo en línea: {ln!r}. "
                f"v0.19.32 desactiva la continuation, este check ya no aplica."
            )

    def test_terminal_actions_set_still_defined(self):
        """_TERMINAL_ACTIONS se mantiene en parsing.py por si algún día
        se re-habilita la continuation con trigger más restrictivo. NO
        eliminar el set (rompe import)."""
        from reflex_companion.parsing import _TERMINAL_ACTIONS
        assert "play_music" in _TERMINAL_ACTIONS
