"""Tests bloqueando regresión de las @rx.var sin deps explícitas (v0.16.14).

CONTEXTO:
─────────
Reflex auto-detecta dependencias de @rx.var pero solo si puede analizar
estáticamente el cuerpo. Para ciertos patrones (imports lazy, accesos
indirectos, etc.) la auto-detección falla y la var ACABA recomputándose
en CADA state change.

Sin deps explícitas:
- 16 computed vars × ~200 yields por respuesta = 3200 recomputaciones/msg
- Cada una sirve string/bool/dict — trivial individualmente, suma ~50ms
  de CPU por respuesta + GC pressure

Con `auto_deps=False, deps=[...]`:
- Reflex sabe EXACTAMENTE de qué state vars depende
- Solo recomputa cuando esa var cambia
- 200 yields/msg pero cada var solo se evalúa cuando su dep cambia

ESTOS TESTS BLOQUEAN regresión a @rx.var sin deps en cualquier var
crítica del path de render.
"""

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
RC_PY = REPO_ROOT / "reflex_companion" / "reflex_companion.py"


@pytest.fixture(scope="module")
def rc_src() -> str:
    return RC_PY.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════════════
#  Lista de computed vars que DEBEN tener deps explícitas
# ════════════════════════════════════════════════════════════════════════

VARS_REQUIRING_EXPLICIT_DEPS = [
    # affection
    "affection_pct",
    "affection_color",
    # Estado visual
    "current_image",
    # i18n
    "t",
    "is_english",
    "language_label",
    # LLM provider
    "llm_model_display",
    "is_openrouter_provider",
    "is_ollama_provider",
    "is_xai_provider",
    "web_search_supported",
    "llm_provider_label",
    # Voice provider
    "is_voice_kokoro",
    "is_voice_voicevox",
    "is_voice_elevenlabs",
    "voice_provider_marker",
    # DOM markers (leídos por JS)
    "tts_marker_attr",
    "notifications_marker_attr",
    "pin_marker_attr",
]


@pytest.mark.parametrize("var_name", VARS_REQUIRING_EXPLICIT_DEPS)
def test_var_has_explicit_deps(rc_src, var_name):
    """Cada @rx.var debe tener `auto_deps=False, deps=[...]`."""
    # Buscar la decoración inmediatamente antes de def {var_name}
    pattern = (
        r"@rx\.var\(([^)]*)\)\s*\n\s*def\s+" + re.escape(var_name) + r"\s*\("
    )
    match = re.search(pattern, rc_src)
    assert match, (
        f"No se localizó @rx.var antes de def {var_name}. ¿Está sin "
        f"decorar o se renombró?"
    )
    decorator_args = match.group(1)
    assert "auto_deps=False" in decorator_args, (
        f"@rx.var de '{var_name}' NO tiene auto_deps=False. Sin esto, "
        f"Reflex auto-detecta deps y puede equivocarse → recomputación "
        f"en cada state change."
    )
    assert "deps=" in decorator_args, (
        f"@rx.var de '{var_name}' NO tiene deps=[...] explícitas. "
        f"Con auto_deps=False y sin deps, la var nunca se actualiza. "
        f"Hay que listar las state vars de las que depende."
    )


# ════════════════════════════════════════════════════════════════════════
#  Verificación adicional: las deps listadas son state vars reales
# ════════════════════════════════════════════════════════════════════════


def _state_field_names(rc_src: str) -> set[str]:
    """Extrae los nombres de campos del State class.
    Patrón: `    nombre: type = default` al inicio de línea (4 espacios)."""
    fields = set()
    # Match típico: "    chat_messages: list[dict[str, str]] = []"
    for m in re.finditer(r"\n\s{4}([a-z_][a-z0-9_]*)\s*:\s*[a-zA-Z]", rc_src):
        name = m.group(1)
        # Filtrar falsos positivos (variables locales en métodos)
        # Las del state están definidas a nivel del class, antes del primer def
        fields.add(name)
    return fields


@pytest.mark.parametrize("var_name", VARS_REQUIRING_EXPLICIT_DEPS)
def test_deps_reference_real_state_fields(rc_src, var_name):
    """Las deps listadas en `deps=[...]` deben corresponder a campos
    reales del State. Catches typos silenciosos."""
    pattern = (
        r"@rx\.var\(([^)]*)\)\s*\n\s*def\s+" + re.escape(var_name) + r"\s*\("
    )
    match = re.search(pattern, rc_src)
    assert match
    args = match.group(1)
    deps_match = re.search(r"deps\s*=\s*\[([^\]]*)\]", args)
    assert deps_match, f"No se encontró deps=[...] en {var_name}"
    deps_str = deps_match.group(1)
    # Extraer nombres entre comillas
    deps = re.findall(r"['\"]([a-z_][a-z0-9_]*)['\"]", deps_str)
    assert deps, f"deps=[] vacío en {var_name}"

    state_fields = _state_field_names(rc_src)
    for dep in deps:
        assert dep in state_fields, (
            f"@rx.var de '{var_name}' lista dep '{dep}' que NO es un "
            f"campo del State. Posible typo o el campo se renombró sin "
            f"actualizar este decorador."
        )


# ════════════════════════════════════════════════════════════════════════
#  Documentación de los benefits
# ════════════════════════════════════════════════════════════════════════


def test_count_of_optimized_vars(rc_src):
    """Documentación de cuántas vars hemos optimizado. Si este número
    BAJA, alguien quitó auto_deps=False de alguna var."""
    auto_deps_false_count = len(re.findall(
        r"@rx\.var\([^)]*auto_deps=False",
        rc_src,
    ))
    # Mínimo: las que listamos arriba (19) + 2 que ya estaban
    # (mood_overlay_color, achievements_gallery) + backend_port_marker
    assert auto_deps_false_count >= 19, (
        f"Solo {auto_deps_false_count} @rx.var tienen auto_deps=False. "
        f"Esperaba >=19 (al menos las listadas en VARS_REQUIRING_EXPLICIT_DEPS)."
    )
