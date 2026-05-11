"""Regression tests for v0.19.33 fix:

Apology auto-retry desactivada — consistente con v0.19.32 que desactivó
la agentic continuation del path de éxito.

Bug observado: cuando una acción reportaba `success=False` (fallo real
o falso), `_stream_action_failure_apology` extraía cualquier action
nueva de la respuesta de Ashley y la ejecutaba como "retry automático".
En el caso de un FALSO fallo (acción que sí funcionó pero el código
reportó failed), eso causaba doble ejecución: el primer call abría una
tab, el "retry" abría otra.

User reportó:
"desactuvalo, porque si hay un falso fallo pasa que abre cosas dos veces"

Fix: en `_stream_action_failure_apology`, descartar el follow_action
extraído (asignar a `_discarded_follow`) en lugar de ejecutarlo.
La apology sigue mostrando la disculpa de Ashley, pero NO ejecuta
ninguna acción adicional. Si el fallo era real, el user puede reintentar
manualmente; si era falso, no se duplica nada.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


class TestApologyNoAutoRetry:
    """v0.19.33 — La apology tras action failure NO debe ejecutar
    automáticamente otra action que Ashley emita en su disculpa."""

    def test_apology_discards_follow_action_not_executes(self):
        """En _stream_action_failure_apology, el action extraído debe ir
        a una variable descarte (_discarded_follow), NO a follow_action
        usable para ejecución."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Localiza la función _stream_action_failure_apology
        idx = src.find("def _stream_action_failure_apology")
        assert idx != -1, "_stream_action_failure_apology no encontrada"
        # Lee 3000 chars del cuerpo
        body = src[idx:idx + 6000]
        # Debe usar _discarded_follow (o nombre similar) para descartar
        assert "_discarded_follow" in body, (
            "_stream_action_failure_apology debe descartar el action "
            "extraído de la apology con `_discarded_follow` (no `follow_action`). "
            "Ejecutar follow_action causa duplicados en falsos fallos."
        )

    def test_apology_does_NOT_call_execute_and_record_action(self):
        """No debe haber un `_execute_and_record_action(follow_action)`
        dentro del cuerpo de la apology — esa era la línea que causaba
        el doble-open."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _stream_action_failure_apology")
        assert idx != -1
        body = src[idx:idx + 6000]
        assert "_execute_and_record_action(follow_action)" not in body, (
            "_stream_action_failure_apology NO debe ejecutar follow_action. "
            "Esa línea causaba el bug de doble apertura en falsos fallos."
        )
        assert "_execute_and_record_action(follow" not in body, (
            "Variantes parciales tampoco — ningún execute con follow_*"
        )

    def test_apology_does_NOT_have_recursive_apology_call(self):
        """La apology recursiva (self._stream_action_failure_apology dentro
        de sí misma) era parte del retry loop — NO debe quedar."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _stream_action_failure_apology")
        assert idx != -1
        # Cuerpo: desde la def hasta la siguiente def
        # Buscamos la siguiente "def " para acotar
        next_def = src.find("\n    def ", idx + 1)
        if next_def == -1:
            next_def = idx + 5000
        body = src[idx:next_def]
        # Contar ocurrencias de _stream_action_failure_apology
        # 1 = la def en sí. Más de 1 = retry recursivo presente.
        count = body.count("_stream_action_failure_apology")
        assert count == 1, (
            f"_stream_action_failure_apology debe aparecer 1 vez (su def). "
            f"Encontradas: {count}. Si hay más, hay un retry recursivo "
            f"que debería eliminarse."
        )

    def test_apology_still_appends_apology_message(self):
        """La apology DEBE seguir appendeando el mensaje de disculpa de
        Ashley (eso es el feature) — solo se quita la ejecución del action."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _stream_action_failure_apology")
        body = src[idx:idx + 6000]
        # Verificar que aún appendea con role assistant
        assert "self.messages.append" in body, (
            "La apology debe seguir appendeando el mensaje de disculpa"
        )
        assert "ap_display" in body, (
            "Debe seguir usando ap_display (texto limpio sin tags)"
        )

    def test_apology_path_still_called_from_finalize_response(self):
        """El call site de la apology desde _finalize_response debe seguir
        funcionando — solo desactivamos el auto-retry interno, no la
        apology entera."""
        src = RC_FILE.read_text(encoding="utf-8")
        # En _finalize_response debe haber una llamada a apology cuando
        # action falla
        match = re.search(
            r'if\s+not\s+result\.get\("success".*?\):\s*\n\s*yield\s+from\s+self\._stream_action_failure_apology',
            src,
        )
        assert match, (
            "El call site de _stream_action_failure_apology desde "
            "_finalize_response (cuando una action falla) debe seguir "
            "presente. v0.19.33 solo desactiva el retry INTERNO."
        )


class TestApologyOnlyApologizesOnce:
    """v0.19.33 — Una acción que falla debe disparar EXACTAMENTE 1 apology,
    no una cascada de retries con apologies recursivas."""

    def test_no_auto_iter_count_increment_in_apology(self):
        """El contador _auto_iter_count se usaba para limitar retries en
        cascada. Sin retries, no debe haber `self._auto_iter_count += 1`
        dentro de la apology."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _stream_action_failure_apology")
        next_def = src.find("\n    def ", idx + 1)
        if next_def == -1:
            next_def = idx + 5000
        body = src[idx:next_def]
        assert "self._auto_iter_count += 1" not in body, (
            "v0.19.33 desactivó el retry → no debe incrementar "
            "_auto_iter_count dentro de la apology"
        )
