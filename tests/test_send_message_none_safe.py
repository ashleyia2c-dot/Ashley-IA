"""Test de regresión: _send_message_impl debe manejar form_data con
'message': None sin crashear.

Bug reportado por user (v0.16.14): el botón Enviar no procesaba el click.
Causa: Reflex envía `{"message": None}` cuando el textarea está vacío
en ciertos paths (especialmente al re-enviar tras borrar mensaje).
`form_data.get("message", "").strip()` parece defensivo pero NO lo es:
si la key existe con valor None, `.get()` devuelve None (NO el default
""), y `.strip()` crashea con AttributeError.

Síntoma visible al user: clic en Enviar → no pasa nada (el AttributeError
en el handler hace que Reflex aborte el evento sin procesar).

Fix: usar `(form_data.get("message") or "").strip()` para defensar
explícitamente contra None.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_PY = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


@pytest.fixture(scope="module")
def rc_src() -> str:
    return RC_PY.read_text(encoding="utf-8")


def test_send_message_handles_none_in_form_data(rc_src):
    """La línea de extracción debe tolerar form_data['message'] is None."""
    # Buscar todas las líneas que extraen 'message' del form_data
    matches = re.findall(
        r"form_data\.get\(['\"]message['\"][^)]*\)\.strip",
        rc_src,
    )
    if matches:
        # Si la línea es solo `.get("message", "").strip()`, falla con None.
        # La forma defensiva es `(get(...) or "")`.strip()`.
        assert False, (
            "Detectada extracción del form_data sin defensa contra None: "
            f"{matches}. Reflex puede mandar {{'message': None}} y "
            ".strip() crasheará. Usar `(form_data.get('message') or '').strip()`"
        )


def test_send_message_uses_or_defense(rc_src):
    """Debe haber al menos una extracción que use `or ''` para None safety."""
    pattern = r"form_data\.get\(['\"]message['\"]\)\s*or\s*['\"]"
    assert re.search(pattern, rc_src), (
        "_send_message_impl no usa el patrón `(form_data.get('message') or '')` "
        "que es la única forma de manejar el caso `{'message': None}` que "
        "Reflex envía cuando el textarea está vacío."
    )


def test_strip_on_none_would_crash():
    """Confirma que el bug original es real: None.strip() crashea."""
    with pytest.raises(AttributeError):
        result = None
        result.strip()


def test_get_with_default_does_not_help_with_none():
    """Confirma que .get(k, default) NO maneja None — solo key missing."""
    d = {"message": None}
    # NO devuelve "" — devuelve None.
    val = d.get("message", "")
    assert val is None, (
        "Si la key 'message' tiene valor None, .get('message', '') retorna "
        "None — NO el default vacío. Hay que usar `(... or '')`."
    )


def test_or_pattern_handles_all_cases():
    """El patrón `(d.get(k) or "")` funciona en los 3 casos."""
    # Key missing → default None → or "" → ""
    assert ({}.get("message") or "") == ""
    # Key existe con None → or "" → ""
    assert ({"message": None}.get("message") or "") == ""
    # Key existe con "" → or "" → "" (sigue funcionando)
    assert ({"message": ""}.get("message") or "") == ""
    # Key existe con texto → texto preservado
    assert ({"message": "hola"}.get("message") or "") == "hola"
