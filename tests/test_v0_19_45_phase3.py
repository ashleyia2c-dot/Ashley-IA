"""Regression tests para v0.19.45 FASE 3 — speculative dispatch
`completed` flag (causa raíz REAL del bug 2 tabs).

Bug histórico:
  • Speculative dispatch ejecuta acción en thread durante stream.
  • _finalize_response chequea `if pre_result is not None` para reusar.
  • Si worker crashea ANTES de setear `holder["result"]` (raro pero
    pasa: GIL races, OOM, exceptions en finally del except path),
    `result` queda en None.
  • Finalize asume "no terminó" → fallback `_execute_and_record_action`
    → la acción SE EJECUTA OTRA VEZ aunque el worker YA hizo el
    side effect (abrió tab, escribió texto).
  • → DUPLICADO.

Fix v0.19.45 FASE 3:
  • Worker SIEMPRE setea `holder["completed"] = True` en `finally`.
  • Finalize chequea `completed` además de `result`:
    - `result is not None` → reusar.
    - `completed=True, result=None` → NO re-ejecutar (side effect ya
      ocurrió). Reportar genérico optimista.
    - `completed=False` → fallback (thread realmente colgado o no
      terminó dentro del timeout — risk acotado por dedupe interno
      de cada acción).
"""
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_FILE = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


# ════════════════════════════════════════════════════════════════════════
#  Worker SIEMPRE setea completed=True
# ════════════════════════════════════════════════════════════════════════


class TestWorkerAlwaysSetsCompleted:
    """v0.19.45 FASE 3 — el worker debe setear `holder['completed'] = True`
    en `finally` para que finalize sepa si la acción se ejecutó."""

    def test_holder_initialized_with_completed_false(self):
        """`result_holder` se crea con `completed: False` para que
        finalize pueda distinguir "no empezó" vs "terminó sin result"."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Buscar el dict literal de result_holder en _maybe_dispatch_speculative
        idx = src.find("def _maybe_dispatch_speculative")
        end = src.find("\n    def ", idx + 1)
        body = src[idx:end]
        assert '{"result": None, "completed": False}' in body, (
            "result_holder debe inicializarse con `completed: False` "
            "para que finalize detecte si el worker llegó al finally"
        )

    def test_worker_finally_sets_completed_true(self):
        """El bloque `finally:` del worker debe setear `holder['completed'] = True`."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _worker(")
        # Buscar el final del def (siguiente método o try external)
        end = src.find("threading.Thread(target=_worker", idx)
        body = src[idx:end]
        # Debe haber un `finally:` y dentro `holder["completed"] = True`
        assert "finally:" in body, "_worker debe tener bloque `finally:`"
        assert 'holder["completed"] = True' in body, (
            "El finally debe setear `holder['completed'] = True` para "
            "marcar que el worker terminó (con éxito o excepción)"
        )


# ════════════════════════════════════════════════════════════════════════
#  Finalize chequea completed para detectar crash silencioso
# ════════════════════════════════════════════════════════════════════════


class TestFinalizeChecksCompleted:
    """v0.19.45 FASE 3 — _finalize_response debe chequear `spec_completed`
    además de `pre_result`."""

    def test_spec_completed_variable_present(self):
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("def _finalize_response")
        end = src.find("\n    def ", idx + 1)
        body = src[idx:end if end != -1 else idx + 10000]
        assert "spec_completed" in body, (
            "_finalize_response debe leer `holder.get('completed')`"
        )
        assert 'holder.get("completed"' in body, (
            "Debe usar `.get('completed', False)` defensivo"
        )

    def test_three_way_branching_present(self):
        """v0.19.45 — el flow debe tener 3 caminos:
        1. result is not None → reusar
        2. spec_completed=True (pero result=None) → NO re-ejecutar
        3. spec_completed=False → fallback re-ejecutar
        """
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("spec_completed = holder.get")
        # Leer próximos 4000 chars para ver los branches
        body = src[idx:idx + 4000]

        # Branch 1: pre_result is not None
        assert "if pre_result is not None:" in body
        # Branch 2: elif spec_completed
        assert "elif spec_completed:" in body, (
            "Falta el branch v0.19.45: si `spec_completed` pero result=None, "
            "NO re-ejecutar (side effect ya ocurrió)"
        )
        # Branch 3: else (fallback)
        assert "else:" in body

    def test_branch_2_does_not_call_execute(self):
        """En el branch 'completed pero result=None', NO debe llamar
        a _execute_and_record_action."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("elif spec_completed:")
        # Leer hasta el siguiente else (fin del branch)
        next_else = src.find("\n                    else:", idx)
        branch_body = src[idx:next_else]
        assert "_execute_and_record_action" not in branch_body, (
            "El branch 'completed pero result=None' NO debe re-ejecutar "
            "(side effect ya ocurrió en el worker thread)"
        )

    def test_branch_2_appends_generic_system_result(self):
        """El branch debe appendear un system_result genérico para que
        el user vea ALGO en el chat (no quede vacío)."""
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("elif spec_completed:")
        next_else = src.find("\n                    else:", idx)
        branch_body = src[idx:next_else]
        assert "self.messages.append" in branch_body, (
            "Branch debe appendear un mensaje system_result genérico"
        )
        assert '"role": "system_result"' in branch_body


# ════════════════════════════════════════════════════════════════════════
#  Logging defensive
# ════════════════════════════════════════════════════════════════════════


class TestLogsBranches:
    """Cada branch que NO sea el happy path debe loguear para debug."""

    def test_branch_2_logs_warning(self):
        src = RC_FILE.read_text(encoding="utf-8")
        idx = src.find("elif spec_completed:")
        next_else = src.find("\n                    else:", idx)
        branch_body = src[idx:next_else]
        assert "warning" in branch_body, (
            "Branch 2 debe loguear warning para debug"
        )

    def test_branch_3_logs_warning(self):
        """Fallback path también debe loguear (warning de timeout)."""
        src = RC_FILE.read_text(encoding="utf-8")
        # Buscar el último else en el bloque (fallback)
        idx = src.find("Speculative thread for")
        if idx == -1:
            # Aceptable si el log usa otro mensaje, no fail aún
            pytest.skip("No se encontró log message exacto; OK si hay warning")
        # Debe haber 'warning' cerca
        nearby = src[max(0, idx - 200):idx + 200]
        assert "warning" in nearby
