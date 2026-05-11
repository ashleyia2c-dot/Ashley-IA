"""Regression tests for v0.19.23 fixes:
1. PRIVACY: read_page action no debe leakear el contenido completo de la
   página al user en el chat. Solo Ashley lo ve en su contexto.
2. delete_message debe ESCRIBIR DIRECTO al disco sin merge (el merge re-
   añadía el msg borrado del archivo viejo).
3. message_item lleva data-msg-id estable para que el observer JS evite
   re-animación al borrar (rx.foreach usa index como key → re-mount masivo).
"""
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIONS_FILE = REPO_ROOT / "reflex_companion" / "actions.py"
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"
COMPONENTS_FILE = REPO_ROOT / "reflex_companion" / "components.py"
MEMORY_FILE = REPO_ROOT / "reflex_companion" / "memory.py"
FX_JS = REPO_ROOT / "assets" / "ashley_fx.js"
I18N_FILE = REPO_ROOT / "reflex_companion" / "i18n.py"


# ════════════════════════════════════════════════════════════════════════
#  PRIVACY — read_page page content leak fix
# ════════════════════════════════════════════════════════════════════════


class TestReadPagePrivacyLeak:
    def test_read_page_returns_ui_result_separate_from_full_content(self):
        """El action read_page debe devolver `ui_result` (corto, para mostrar
        al user) además de `result` (completo, para el contexto de Ashley)."""
        src = ACTIONS_FILE.read_text(encoding="utf-8")
        # Find the read_page block
        match = re.search(
            r'elif action_type == "read_page":(.*?)elif action_type ==',
            src,
            re.DOTALL,
        )
        assert match, "Bloque read_page no encontrado en actions.py"
        block = match.group(1)
        assert '"ui_result"' in block, (
            "read_page debe devolver `ui_result` (corto, sin leak). Sin esto, "
            "el contenido completo de la página se muestra al user en el chat "
            "→ violación de privacidad."
        )
        # Y el ui_result debe ser un mensaje genérico (no incluir el contenido)
        assert "Página leída" in block or "page read" in block.lower(), (
            "ui_result debe ser un mensaje resumen genérico, no el contenido"
        )

    def test_execute_and_record_action_propagates_ui_result(self):
        """_execute_and_record_action debe meter ui_result en el message
        record como `ui_content`, para que el render lo use."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Look for the message append in _execute_and_record_action
        match = re.search(
            r'def _execute_and_record_action.*?self\.messages\.append\(\s*\{(.*?)\}\s*\)',
            src,
            re.DOTALL,
        )
        assert match, "_execute_and_record_action no parece appendear messages"
        block = match.group(1)
        assert '"ui_content"' in block, (
            "_execute_and_record_action debe almacenar `ui_content` en el "
            "message record para preservar la versión corta del read_page"
        )
        assert 'result.get("ui_result"' in block, (
            "Debe leer ui_result del action result"
        )

    def test_message_item_renders_ui_content_when_present(self):
        """components.message_item debe usar `ui_content` si no está vacío,
        si no, fallback a `content`. Esto permite que el privacy fix funcione."""
        src = COMPONENTS_FILE.read_text(encoding="utf-8")
        # Look for the message_item function
        idx = src.find("def message_item")
        assert idx != -1, "message_item function no encontrada"
        # Check next 3000 chars
        block = src[idx:idx + 3000]
        assert 'm["ui_content"]' in block, (
            "message_item debe leer m[\"ui_content\"]"
        )
        assert "rx.cond" in block and 'm["ui_content"] != ""' in block, (
            "Debe haber un rx.cond que prefiera ui_content cuando no esté "
            "vacío y caiga a content si lo está"
        )

    def test_ensure_ids_migrates_legacy_messages_with_ui_content(self):
        """ensure_ids debe añadir `ui_content: \"\"` a mensajes viejos sin la
        key, sino el render JS crashea con `Cannot read properties of undefined`."""
        src = MEMORY_FILE.read_text(encoding="utf-8")
        idx = src.find("def ensure_ids")
        assert idx != -1, "ensure_ids no encontrada en memory.py"
        block = src[idx:idx + 1000]
        assert '"ui_content"' in block, (
            "ensure_ids debe migrar mensajes legacy añadiendo ui_content"
        )


# ════════════════════════════════════════════════════════════════════════
#  delete_message — bug del merge que re-añade el msg borrado
# ════════════════════════════════════════════════════════════════════════


class TestDeleteMessageNoMerge:
    def test_delete_message_writes_direct_no_merge(self):
        """delete_message NO debe llamar a self.save_history() — ese hace
        merge con disco que RE-AÑADIRÍA el msg borrado del archivo viejo."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Find delete_message function
        match = re.search(
            r'def delete_message\(self, msg_id: str\):(.*?)(?=\n    def |\n    async def |\n    @)',
            src,
            re.DOTALL,
        )
        assert match, "delete_message no encontrado"
        body = match.group(1)
        # Must NOT call self.save_history()
        assert "self.save_history()" not in body, (
            "delete_message NO debe llamar self.save_history() — ese hace "
            "merge con disco y re-añade el msg borrado. Debe escribir "
            "directo con save_json(CHAT_FILE, ...)"
        )
        # Must call save_json directly with CHAT_FILE
        assert "save_json(CHAT_FILE" in body, (
            "delete_message debe escribir directo al disco con "
            "save_json(CHAT_FILE, saveable) sin pasar por el merge"
        )


# ════════════════════════════════════════════════════════════════════════
#  Anti-flicker observer — message wrapper has stable data-msg-id
# ════════════════════════════════════════════════════════════════════════


class TestAntiFlickerObserver:
    def test_message_item_has_data_msg_id_attr(self):
        """El wrapper rx.box de message_item debe llevar data-msg-id={m["id"]}
        para que el JS observer pueda identificar mensajes ya animados."""
        src = COMPONENTS_FILE.read_text(encoding="utf-8")
        idx = src.find("def message_item")
        assert idx != -1
        # v0.19.29 — la función creció (botón 🗑️ añadido a system_result),
        # subimos el cap para que el regex llegue al wrapper rx.box final
        block = src[idx:idx + 5000]
        assert "custom_attrs" in block, (
            "message_item debe usar custom_attrs para añadir data-msg-id"
        )
        assert '"data-msg-id"' in block, (
            "El custom_attrs debe incluir 'data-msg-id'"
        )
        assert 'm["id"]' in block, (
            "El valor del data-msg-id debe ser m[\"id\"]"
        )

    def test_fx_js_has_msg_enter_dedupe_function(self):
        """ashley_fx.js debe definir _initMsgEnterDedupe y llamarla en boot()."""
        src = FX_JS.read_text(encoding="utf-8")
        assert "_initMsgEnterDedupe" in src, (
            "ashley_fx.js debe definir _initMsgEnterDedupe (anti-flicker)"
        )
        # Check it's called in boot
        boot_idx = src.find("function boot()")
        assert boot_idx != -1
        boot_block = src[boot_idx:boot_idx + 2000]
        assert "_initMsgEnterDedupe()" in boot_block, (
            "_initMsgEnterDedupe debe llamarse en boot() para iniciar el "
            "observer al cargar"
        )

    def test_fx_js_dedupe_uses_data_msg_id(self):
        """El observer debe usar data-msg-id como identificador."""
        src = FX_JS.read_text(encoding="utf-8")
        idx = src.find("_initMsgEnterDedupe")
        assert idx != -1
        # Read the function body
        block = src[idx:idx + 3000]
        assert "data-msg-id" in block, (
            "El observer debe leer 'data-msg-id' del wrapper de cada mensaje"
        )
        assert "Set(" in block or "new Set" in block, (
            "El observer debe usar un Set para track de IDs ya animados"
        )
        assert "msg-enter" in block, (
            "El observer debe quitar la clase msg-enter de mensajes ya vistos"
        )


# ════════════════════════════════════════════════════════════════════════
#  i18n — Legal & Data section translated to all 7 languages
# ════════════════════════════════════════════════════════════════════════


class TestLegalDataI18n:
    def test_legal_section_keys_present_in_all_7_langs(self):
        """Las 5 keys nuevas (settings_legal_heading, settings_privacy_btn,
        settings_terms_btn, settings_backup_desc, settings_export_btn) deben
        estar en los 7 idiomas con paridad."""
        from reflex_companion import i18n
        required_keys = {
            "settings_legal_heading",
            "settings_privacy_btn",
            "settings_terms_btn",
            "settings_backup_desc",
            "settings_export_btn",
        }
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            ui = i18n.UI[lang]
            missing = required_keys - set(ui.keys())
            assert not missing, (
                f"Language {lang!r} missing keys: {sorted(missing)}"
            )

    def test_legal_strings_actually_translated_not_english(self):
        """Las 5 keys NO deben tener el mismo valor que EN en ES/FR/JA/DE/RU/KO
        (excepto si son emoji-only o similares). Detecta copy-paste fails."""
        from reflex_companion import i18n
        en_values = {
            k: i18n.UI["en"][k]
            for k in [
                "settings_legal_heading",
                "settings_privacy_btn",
                "settings_terms_btn",
                "settings_backup_desc",
                "settings_export_btn",
            ]
        }
        for lang in ["es", "fr", "ja", "de", "ru", "ko"]:
            for key, en_val in en_values.items():
                local_val = i18n.UI[lang][key]
                # Allow if both are emoji-heavy (e.g., heading "⚖ Legal..." —
                # heading might keep ⚖ but rest must differ)
                # Strip emoji from comparison
                en_clean = re.sub(r'[^\w\s]', '', en_val).strip()
                local_clean = re.sub(r'[^\w\s]', '', local_val).strip()
                if en_clean and local_clean and len(en_clean) > 5:
                    assert en_clean.lower() != local_clean.lower(), (
                        f"{lang!r}.{key!r} == EN value (probably untranslated): "
                        f"{en_val!r} vs {local_val!r}"
                    )

    def test_no_hardcoded_legal_strings_in_components(self):
        """Privacy Policy, Terms of Service, Export all my data, Backup all
        your data NO deben aparecer como literales en reflex_companion.py
        (excepto en comentarios)."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Strip comments
        no_comments = "\n".join(
            ln for ln in src.split("\n") if not ln.strip().startswith("#")
        )
        forbidden = [
            'rx.text("Privacy Policy"',
            'rx.text("Terms of Service"',
            'rx.text("Export all my data',
            'rx.text("Backup all your data',
            'rx.button(\n                                        "Privacy Policy"',
            'rx.button(\n                                        "Terms of Service"',
            'rx.dialog.title("Privacy Policy"',
            'rx.dialog.title("Terms of Service"',
        ]
        for needle in forbidden:
            assert needle not in no_comments, (
                f"Hardcoded literal found: {needle!r}. Use State.t[...] "
                f"instead so the string gets translated."
            )
