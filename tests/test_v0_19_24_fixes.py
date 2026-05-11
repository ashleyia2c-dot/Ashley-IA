"""Regression tests for v0.19.24 fixes:
- Security: C1 (export auth), C2 (tunnel detection), H1 (IP rate limit), H2 (msg cap),
            M1 (DOM key removed), M2 (proc match hardening)
- Error handling: E1 (save_history try/except), E2 (sanitize grok error),
                  E3-E8 (logger usage, parse guards)
- i18n: actions/reminders/goals/tastes/license accept lang and use _amsg
"""
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIONS = REPO_ROOT / "reflex_companion" / "actions.py"
RC = REPO_ROOT / "reflex_companion" / "reflex_companion.py"
API = REPO_ROOT / "reflex_companion" / "api_routes.py"
LIC = REPO_ROOT / "reflex_companion" / "license.py"
MEM = REPO_ROOT / "reflex_companion" / "memory.py"
REM = REPO_ROOT / "reflex_companion" / "reminders.py"
GOALS = REPO_ROOT / "reflex_companion" / "goals.py"
TASTES = REPO_ROOT / "reflex_companion" / "tastes.py"
VOICE_JS = REPO_ROOT / "assets" / "ashley_voice.js"
FX_JS = REPO_ROOT / "assets" / "ashley_fx.js"
TUNNEL_JS = REPO_ROOT / "electron" / "cloudflared-tunnel.js"


# ════════════════════════════════════════════════════════════════════════
#  SECURITY
# ════════════════════════════════════════════════════════════════════════


class TestSecurity:
    def test_export_endpoint_requires_truly_localhost(self):
        """C1 — /api/export/data debe rechazar requests que NO sean localhost
        REAL (incluyendo bypass via Cloudflare tunnel)."""
        src = API.read_text(encoding="utf-8")
        # El endpoint debe llamar _is_truly_localhost
        export_block = re.search(
            r"async def _export_data_endpoint.*?(?=\nasync def |\ndef )",
            src, re.DOTALL,
        )
        assert export_block, "_export_data_endpoint not found"
        body = export_block.group(0)
        assert "_is_truly_localhost(request)" in body, (
            "Export endpoint debe usar _is_truly_localhost para bloquear "
            "bypass via tunnel (era un C1 critical en el security audit)"
        )

    def test_is_truly_localhost_rejects_cf_headers(self):
        """C2 — _is_truly_localhost rechaza si vienen headers de Cloudflare."""
        src = API.read_text(encoding="utf-8")
        fn = re.search(
            r"def _is_truly_localhost.*?(?=\ndef )",
            src, re.DOTALL,
        )
        assert fn, "_is_truly_localhost no encontrada"
        body = fn.group(0)
        assert 'cf-connecting-ip' in body, (
            "Debe chequear cf-connecting-ip header (señal inequívoca de tunnel)"
        )
        assert 'cf-ray' in body, "Debe chequear cf-ray header"

    def test_check_mobile_auth_rate_limits_failed_by_ip(self):
        """H1 — failed auth attempts deben rate-limited por IP, no solo por token."""
        src = API.read_text(encoding="utf-8")
        fn = re.search(
            r"def _check_mobile_auth.*?(?=\ndef )",
            src, re.DOTALL,
        )
        assert fn
        body = fn.group(0)
        assert "_failed_ip_" in body or "client_ip" in body, (
            "H1: _check_mobile_auth debe rate-limit failed attempts por IP, "
            "no solo por token (token wrong = unlimited probing antes)"
        )

    def test_mobile_send_caps_message_size(self):
        """H2 — el endpoint de envío móvil debe rechazar mensajes >4KB."""
        src = API.read_text(encoding="utf-8")
        assert "MAX_MOBILE_MSG_CHARS" in src, (
            "Falta cap de tamaño del mensaje móvil para evitar drain de "
            "cuota xAI por token leak"
        )
        # Debe ser <=4096
        m = re.search(r"MAX_MOBILE_MSG_CHARS\s*=\s*(\d+)", src)
        assert m, "MAX_MOBILE_MSG_CHARS no parece numérica"
        assert int(m.group(1)) <= 4096, (
            "Cap demasiado alto — abuse window queda abierta"
        )

    def test_dom_no_longer_exposes_eleven_key(self):
        """M1 — el DOM marker NO debe llevar la API key de ElevenLabs."""
        src = RC.read_text(encoding="utf-8")
        assert '"data-el-key": State.elevenlabs_key' not in src, (
            "data-el-key con la API key plaintext en DOM era un leak gratis. "
            "Debe usar data-has-eleven-key (booleano) o no exponerla."
        )

    def test_terminate_process_requires_min_4_chars(self):
        """M2 — _terminate_process_by_name debe requerir al menos 4 chars
        para evitar match catastrófico (single char mata todo)."""
        src = ACTIONS.read_text(encoding="utf-8")
        # Extract the function body
        fn = re.search(
            r"def _terminate_process_by_name.*?(?=\ndef )",
            src, re.DOTALL,
        )
        assert fn, "_terminate_process_by_name no encontrada"
        body = fn.group(0)
        assert "len(target) < 4" in body, (
            "_terminate_process_by_name debe requerir target con 4+ chars "
            "(antes match por substring con 'e' mataba Edge, Chrome, etc)"
        )

    def test_tunnel_url_file_uses_restrictive_mode(self):
        """M3 — el archivo de tunnel URL debe escribirse con mode 0o600."""
        src = TUNNEL_JS.read_text(encoding="utf-8")
        assert "0o600" in src or "0600" in src, (
            "tunnelUrlFile debe usar mode 0o600 para que solo el user lo "
            "lea (otros users locales podrían leer la URL del tunnel)"
        )

    def test_volume_powershell_has_timeout(self):
        """M4 — subprocess.run de PowerShell para volumen debe tener timeout."""
        src = ACTIONS.read_text(encoding="utf-8")
        # Buscamos el _volume_powershell function
        fn = re.search(
            r"def _volume_powershell.*?(?=\ndef )",
            src, re.DOTALL,
        )
        assert fn
        body = fn.group(0)
        assert "timeout=5" in body or "TimeoutExpired" in body, (
            "_volume_powershell sin timeout colgaría handler para siempre"
        )


# ════════════════════════════════════════════════════════════════════════
#  ERROR HANDLING
# ════════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    def test_save_history_disk_error_doesnt_crash(self):
        """E1 — save_history wraps save_json en try/except OSError."""
        src = RC.read_text(encoding="utf-8")
        # Find save_history function
        fn = re.search(
            r"    def save_history\(self\):.*?(?=\n    def )",
            src, re.DOTALL,
        )
        assert fn
        body = fn.group(0)
        assert "except OSError" in body, (
            "E1: save_history debe envolver save_json en try/except OSError "
            "para evitar que un disk-full crashee el send_message → user "
            "ve 'falló con Grok' en vez del problema real"
        )

    def test_handle_grok_error_uses_logger_not_print(self):
        """E2 — _handle_grok_error usa logger en vez de print."""
        src = RC.read_text(encoding="utf-8")
        fn = re.search(
            r"    def _handle_grok_error.*?(?=\n    (?:def |async def ))",
            src, re.DOTALL,
        )
        assert fn
        body = fn.group(0)
        assert 'logging.getLogger("ashley.grok")' in body, (
            "_handle_grok_error debe usar logger en vez de print()"
        )
        # Debe sanitizar str(e) para no leakear API keys
        assert "redacted" in body or "sub(" in body, (
            "Debe redactar patrones que parezcan API keys del str(e)"
        )

    def test_extract_facts_distinguishes_json_decode_error(self):
        """E3 — extract_facts logea cuando el error NO es JSONDecodeError."""
        src = MEM.read_text(encoding="utf-8")
        # Find extract_facts function
        fn_idx = src.find("def extract_facts")
        assert fn_idx != -1
        block = src[fn_idx:fn_idx + 3500]
        assert "json.JSONDecodeError" in block, (
            "extract_facts debe distinguir JSONDecodeError (silencioso OK) "
            "de Exception general (bug real, debe loguear)"
        )

    def test_format_facts_guards_int_imp(self):
        """E4 — format_facts debe usar try/except para int(imp) corruption."""
        src = MEM.read_text(encoding="utf-8")
        idx = src.find("def format_facts")
        assert idx != -1
        block = src[idx:idx + 1500]
        assert "imp_int" in block, (
            "format_facts debe tener variable imp_int con try/except guard "
            "(antes int(imp) crasheaba todo si importancia era string textual)"
        )

    def test_parse_dt_logs_corruption_warning(self):
        """E5 — _parse_dt logea cuando timestamp está corrupto."""
        src = REM.read_text(encoding="utf-8")
        idx = src.find("def _parse_dt")
        assert idx != -1
        block = src[idx:idx + 800]
        assert 'logging.getLogger("ashley.reminders")' in block, (
            "_parse_dt debe loguear warning cuando timestamp está corrupto "
            "(antes el reminder NUNCA disparaba sin error visible)"
        )

    def test_play_music_propagates_search_only_failure(self):
        """E6 — play_music distingue éxito real vs fallback a search."""
        src = ACTIONS.read_text(encoding="utf-8")
        assert "resolved_ok" in src, (
            "play_music debe rastrear resolved_ok para no afirmar éxito "
            "cuando solo abrió la página de búsqueda (no un video real)"
        )
        assert "music_search_only" in src, (
            "Debe usar la key i18n music_search_only para mensaje honesto"
        )

    def test_discovery_bg_uses_logger_not_print(self):
        """E7 — discovery_bg_task logea en vez de print."""
        src = RC.read_text(encoding="utf-8")
        # Buscamos la sección Discovery BG error
        # Antes era: print(f"[Discovery BG Error] {e}")
        # Ahora debe ser logger.warning
        assert 'print(f"[Discovery BG Error]' not in src, (
            "Discovery BG debe usar logger en vez de print"
        )
        assert 'logging.getLogger("ashley.discovery")' in src, (
            "Debe usar el logger ashley.discovery"
        )


# ════════════════════════════════════════════════════════════════════════
#  I18N MASIVO — actions/reminders/goals/tastes
# ════════════════════════════════════════════════════════════════════════


class TestI18nMasivo:
    def test_action_msgs_dict_has_7_langs_per_key(self):
        """_ACTION_MSGS debe tener entradas para los 7 idiomas en cada key."""
        from reflex_companion import actions
        for key, langs in actions._ACTION_MSGS.items():
            for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
                assert lang in langs, (
                    f"_ACTION_MSGS[{key!r}] missing lang {lang!r}"
                )

    def test_amsg_returns_localized_for_each_lang(self):
        """_amsg debe devolver el string en el lang pedido (no fallback)."""
        from reflex_companion import actions
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            msg = actions._amsg(lang, "music_playing", title="Test")
            assert "Test" in msg, f"music_playing {lang} no incluyó title"
            # Verificar que NO es el fallback EN si pedimos otro idioma
            if lang != "en":
                en_msg = actions._amsg("en", "music_playing", title="Test")
                # Debe ser distinto si la traducción existe
                assert msg != en_msg, (
                    f"_amsg({lang!r}, 'music_playing') devolvió EN — "
                    f"falta traducción real"
                )

    def test_open_msg_supports_7_langs(self):
        """_open_msg ya no es solo en/es — usa _amsg internamente."""
        from reflex_companion import actions
        for lang in ["fr", "ja", "de", "ru", "ko"]:
            msg = actions._open_msg(lang, "launched", name="Notepad")
            # No debe ser EN ni ES default
            assert "Notepad" in msg
            en_msg = actions._open_msg("en", "launched", name="Notepad")
            assert msg != en_msg, (
                f"_open_msg({lang!r}, 'launched') devolvió EN — "
                f"está usando el fallback en vez de traducir"
            )

    def test_action_functions_accept_lang_param(self):
        """Las funciones core de actions.py deben aceptar lang param."""
        import inspect
        from reflex_companion import actions, reminders, goals, tastes
        signatures = {
            "search_web": actions.search_web,
            "open_url": actions.open_url,
            "play_music": actions.play_music,
            "control_volume": actions.control_volume,
            "focus_window": actions.focus_window,
            "type_text": actions.type_text,
            "press_hotkey": actions.press_hotkey,
            "press_key": actions.press_key,
            "close_window": actions.close_window,
            "close_browser_tab": actions.close_browser_tab,
            "add_reminder": reminders.add_reminder,
            "delete_reminder": reminders.delete_reminder,
            "add_important": reminders.add_important,
            "mark_important_done": reminders.mark_important_done,
            "mark_check_in": goals.mark_check_in,
            "complete_goal": goals.complete_goal,
            "add_taste": tastes.add_taste,
        }
        for name, fn in signatures.items():
            sig = inspect.signature(fn)
            assert "lang" in sig.parameters, (
                f"{name}() debe aceptar lang param para i18n"
            )

    def test_license_friendly_error_supports_7_langs(self):
        """_friendly_error debe devolver mensajes en los 7 idiomas."""
        from reflex_companion import license as lic
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            msg = lic._friendly_error({"error": "limit reached"}, lang=lang)
            assert msg
            # Verificar contenido distinto entre idiomas
        ja_msg = lic._friendly_error({"error": "limit"}, lang="ja")
        en_msg = lic._friendly_error({"error": "limit"}, lang="en")
        assert ja_msg != en_msg, (
            "_friendly_error(lang='ja') devolvió EN — falta traducción JA"
        )

    def test_whisper_status_has_messages_dict(self):
        """api_routes whisper status debe enviar `messages` dict con 7 idiomas."""
        src = API.read_text(encoding="utf-8")
        assert "_WHISPER_MSGS_LOADING" in src
        assert "_WHISPER_MSGS_DOWNLOAD" in src
        assert "_WHISPER_MSGS_ERROR" in src
        # Cada dict debe tener los 7 idiomas
        for dict_name in ("_WHISPER_MSGS_LOADING", "_WHISPER_MSGS_DOWNLOAD",
                          "_WHISPER_MSGS_ERROR"):
            block = re.search(rf'{dict_name}\s*=\s*\{{(.*?)\}}', src, re.DOTALL)
            assert block, f"{dict_name} dict no encontrado"
            for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
                assert f'"{lang}"' in block.group(1), (
                    f"{dict_name} missing lang {lang!r}"
                )

    def test_voice_js_i18n_helper_supports_extras_dict(self):
        """ashley_voice.js _i18n debe aceptar dict extras opcional."""
        src = VOICE_JS.read_text(encoding="utf-8")
        assert "_pickI18nMsg" in src, (
            "_pickI18nMsg helper no encontrado — necesario para leer "
            "messages dict del backend"
        )
        # _i18n debe tener 3rd param `extras` opcional
        i18n_def = re.search(r"_i18n\s*\(\s*enMsg\s*,\s*esMsg(.*?)\)\s*\{", src)
        assert i18n_def
        assert "extras" in i18n_def.group(0), (
            "_i18n debe aceptar 3er param `extras` para los 5 idiomas adicionales"
        )

    def test_fx_js_update_notifier_uses_7_langs(self):
        """ashley_fx.js update notifier debe tener i18n dict para los 7 idiomas."""
        src = FX_JS.read_text(encoding="utf-8")
        assert "_UPDATE_MSGS" in src
        assert "_updateMsg" in src
        # Buscar el dict ready y verificar los 7 idiomas
        ready_block = re.search(
            r"ready:\s*\{(.*?)\}\s*,?\s*\}", src, re.DOTALL
        )
        assert ready_block
        body = ready_block.group(1)
        for lang in ["en", "es", "fr", "ja", "de", "ru", "ko"]:
            assert f"{lang}:" in body, (
                f"_UPDATE_MSGS.ready missing lang {lang!r}"
            )


# ════════════════════════════════════════════════════════════════════════
#  RESOURCE — Subprocess cleanup
# ════════════════════════════════════════════════════════════════════════


class TestResourceCleanup:
    def test_send_keys_subprocess_cleans_up_on_timeout(self):
        """_send_keys_subprocess debe matar el proceso + cerrar pipes en timeout."""
        src = ACTIONS.read_text(encoding="utf-8")
        idx = src.find("def _send_keys_subprocess")
        assert idx != -1
        # Cap a 5000 chars (el script Python embedded es enorme)
        block = src[idx:idx + 5000]
        assert "TimeoutExpired" in block, (
            "_send_keys_subprocess debe atrapar TimeoutExpired explícitamente"
        )
        assert "proc.kill()" in block, (
            "Debe matar el proceso huérfano en timeout"
        )
        assert "pipe.close()" in block, (
            "Debe cerrar stdout/stderr pipes en finally"
        )

    def test_find_and_close_tab_subprocess_cleans_up_on_timeout(self):
        """_find_and_close_tab_subprocess debe limpiar en timeout también."""
        src = ACTIONS.read_text(encoding="utf-8")
        start = src.find("def _find_and_close_tab_subprocess")
        assert start != -1
        # Buscar la siguiente función outer-level — sabemos que es
        # `close_browser_tab` (lo verificó grep antes).
        end = src.find("def close_browser_tab", start + 100)
        assert end != -1, "close_browser_tab next-def anchor no encontrada"
        block = src[start:end]
        assert "TimeoutExpired" in block, (
            "_find_and_close_tab_subprocess debe atrapar TimeoutExpired "
            "(antes timeout dejaba el subprocess huérfano)"
        )
        assert "proc.kill()" in block, "Debe matar el proceso en timeout"
