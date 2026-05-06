"""Guards para el cerebro JS móvil de Ashley (v0.18.2 — Capa 2).

Cubre los archivos JS del brain en assets/mobile/brain/:

  • brain.js     — orchestrator (online/offline routing)
  • llm.js       — multi-provider LLM client + streaming SSE
  • memory.js    — IndexedDB wrapper
  • parsing.js   — tag extraction (port de parsing.py)
  • prompts.js   — sync + cache + assembly
  • state.js     — mood + vulnerability triggers

Los tests son guards de REGRESIÓN sobre el source — no smoke tests del runtime
JS (no podemos ejecutar JS en pytest). Verifican estructura, exports correctos,
y que las constantes estén sincronizadas con sus equivalentes Python.

Adicionalmente, cubre los endpoints sync del backend Python:
  • /api/mobile/sync_prompts
  • /api/mobile/sync_state
  • /api/mobile/sync_push

Y la helper Python build_device_section() en prompts.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BRAIN_DIR = ROOT / "assets" / "mobile" / "brain"
API_ROUTES = ROOT / "reflex_companion" / "api_routes.py"
PROMPTS_PY = ROOT / "reflex_companion" / "prompts.py"
PROMPTS_ES = ROOT / "reflex_companion" / "prompts_es.py"
PROMPTS_EN = ROOT / "reflex_companion" / "prompts_en.py"
PROMPTS_FR = ROOT / "reflex_companion" / "prompts_fr.py"
MENTAL_STATE = ROOT / "reflex_companion" / "mental_state.py"
PARSING_PY = ROOT / "reflex_companion" / "parsing.py"


# ─────────────────────────────────────────────
#  Existencia + estructura básica
# ─────────────────────────────────────────────

def test_brain_directory_exists():
    assert BRAIN_DIR.is_dir(), f"falta el dir {BRAIN_DIR}"


@pytest.mark.parametrize("name", [
    "brain.js", "llm.js", "memory.js", "parsing.js", "prompts.js", "state.js",
    "README.md",
])
def test_brain_files_exist(name):
    p = BRAIN_DIR / name
    assert p.exists() and p.stat().st_size > 0, f"falta o vacío: {p}"


# ─────────────────────────────────────────────
#  Exports (cada módulo debe exportar lo que el orchestrator espera)
# ─────────────────────────────────────────────

def test_parsing_exports_required_functions():
    src = (BRAIN_DIR / "parsing.js").read_text(encoding="utf-8")
    for name in (
        "cleanDisplay", "extractMood", "extractAffection",
        "extractAction", "extractAllActions", "filterMobileActions",
        "SAFE_ACTIONS", "PC_ONLY_ACTIONS",
    ):
        assert f"export function {name}" in src or f"export const {name}" in src, (
            f"parsing.js no exporta {name}"
        )


def test_memory_exports_storage_api():
    src = (BRAIN_DIR / "memory.js").read_text(encoding="utf-8")
    for name in ("get", "set", "del", "keys", "clear",
                 "appendMessage", "getRecentMessages",
                 "markPendingSync", "drainPendingSync",
                 "applySyncState", "savePrompts", "loadPrompts"):
        assert f"export async function {name}" in src or f"export function {name}" in src, (
            f"memory.js no exporta {name}"
        )


def test_llm_exports_client_class():
    src = (BRAIN_DIR / "llm.js").read_text(encoding="utf-8")
    assert "export class LLMClient" in src, "llm.js no exporta LLMClient"
    assert "export async function llmFromConfig" in src
    assert "export async function saveLlmConfig" in src


def test_state_exports_mood_helpers():
    src = (BRAIN_DIR / "state.js").read_text(encoding="utf-8")
    for name in ("defaultState", "classifyUserEvent", "applyEventsToMood",
                 "describeMood", "formatMentalStateBlock",
                 "computeVulnerabilityTrigger", "markVulnerabilityUsed",
                 "formatVulnerabilityDirective"):
        assert f"export function {name}" in src or f"export const {name}" in src, (
            f"state.js no exporta {name}"
        )


def test_prompts_exports_sync_and_build():
    src = (BRAIN_DIR / "prompts.js").read_text(encoding="utf-8")
    for name in ("syncPrompts", "syncState", "syncPush", "buildSystemPrompt"):
        assert f"export async function {name}" in src, (
            f"prompts.js no exporta {name}"
        )


def test_brain_exports_send_and_online_check():
    src = (BRAIN_DIR / "brain.js").read_text(encoding="utf-8")
    assert "export async function send" in src
    assert "export async function isOnline" in src
    assert "export const Brain" in src or "export default Brain" in src


# ─────────────────────────────────────────────
#  Sincronización de constantes JS ↔ Python
# ─────────────────────────────────────────────

def test_vulnerability_constants_sync_with_python():
    """Las constantes de vulnerabilidad en state.js deben coincidir con
    mental_state.py — si no, el comportamiento difiere offline vs online."""
    js_src = (BRAIN_DIR / "state.js").read_text(encoding="utf-8")
    py_src = MENTAL_STATE.read_text(encoding="utf-8")

    pairs = [
        ("VULNERABILITY_AFFECTION_MIN", "70"),
        ("VULNERABILITY_SPONTANEOUS_AFFECTION_MIN", "80"),
        ("VULNERABILITY_COOLDOWN_DAYS", "7"),
    ]
    for name, expected in pairs:
        # JS: export const NAME = N
        js_match = re.search(rf"export const {name}\s*=\s*(\d+)", js_src)
        assert js_match, f"state.js: falta const {name}"
        assert js_match.group(1) == expected, (
            f"state.js: {name}={js_match.group(1)}, expected {expected}"
        )
        # Python: NAME = N
        py_match = re.search(rf"^{name}\s*=\s*(\d+)", py_src, re.MULTILINE)
        assert py_match, f"mental_state.py: falta {name}"
        assert py_match.group(1) == expected, (
            f"mental_state.py: {name}={py_match.group(1)}, expected {expected}"
        )


def test_long_gap_minutes_sync():
    js_src = (BRAIN_DIR / "state.js").read_text(encoding="utf-8")
    py_src = MENTAL_STATE.read_text(encoding="utf-8")
    # JS: VULNERABILITY_LONG_GAP_MINUTES = 8 * 60
    assert "VULNERABILITY_LONG_GAP_MINUTES = 8 * 60" in js_src, (
        "state.js: VULNERABILITY_LONG_GAP_MINUTES debe ser 8*60"
    )
    # Python: VULNERABILITY_LONG_GAP_MINUTES = 8 * 60  # 8 horas
    assert re.search(
        r"VULNERABILITY_LONG_GAP_MINUTES\s*=\s*8\s*\*\s*60", py_src
    ), "mental_state.py: VULNERABILITY_LONG_GAP_MINUTES debe ser 8*60"


def test_safe_actions_listed_in_parsing_js():
    """parsing.js::SAFE_ACTIONS debe contener todas las acciones safe del Python."""
    js_src = (BRAIN_DIR / "parsing.js").read_text(encoding="utf-8")
    expected_safe = [
        "save_taste", "remind", "add_important", "done_important", "save_date",
        "save_goal", "check_in_goal", "complete_goal",
    ]
    for name in expected_safe:
        assert f"'{name}'" in js_src, (
            f"parsing.js::SAFE_ACTIONS no contiene {name!r}"
        )


def test_pc_only_actions_includes_critical():
    """parsing.js::PC_ONLY_ACTIONS debe bloquear todas las actions del PC."""
    js_src = (BRAIN_DIR / "parsing.js").read_text(encoding="utf-8")
    critical = [
        "open_app", "close_window", "close_tab", "search_web",
        "play_music", "type_text", "type_in", "write_to_app",
        "volume", "screenshot",
        "click", "type_browser", "read_page", "scroll_page",
    ]
    # Match en PC_ONLY_ACTIONS export
    pc_block = re.search(
        r"PC_ONLY_ACTIONS\s*=\s*new Set\(\[(.*?)\]\)",
        js_src, re.DOTALL,
    )
    assert pc_block, "parsing.js: PC_ONLY_ACTIONS no encontrado"
    block_text = pc_block.group(1)
    for name in critical:
        assert f"'{name}'" in block_text, (
            f"parsing.js::PC_ONLY_ACTIONS no contiene {name!r} — "
            f"action del PC se ejecutaría desde móvil!"
        )


# ─────────────────────────────────────────────
#  device_section helper
# ─────────────────────────────────────────────

def test_build_device_section_exists_in_python():
    src = PROMPTS_PY.read_text(encoding="utf-8")
    assert "def build_device_section" in src, (
        "prompts.py: falta build_device_section()"
    )


def test_build_device_section_has_all_languages():
    """build_device_section debe cubrir es/en/fr para que el móvil
    funcione en cualquier idioma."""
    src = PROMPTS_PY.read_text(encoding="utf-8")
    section_match = re.search(
        r"def build_device_section[\s\S]+?(?=\ndef |\Z)", src
    )
    assert section_match, "build_device_section no encontrado"
    body = section_match.group(0)
    # Debe haber rama para cada idioma
    assert "lang == \"es\"" in body, "build_device_section: falta español"
    assert "lang == \"fr\"" in body, "build_device_section: falta francés"
    # English es el default (else)


def test_build_device_section_lists_pc_only_actions():
    """El bloque de mobile debe MENCIONAR las acciones que NO se pueden
    ejecutar — Ashley necesita esa info para responder bien."""
    src = PROMPTS_PY.read_text(encoding="utf-8")
    section_match = re.search(
        r"def build_device_section[\s\S]+?(?=\ndef |\Z)", src
    )
    body = section_match.group(0)
    for name in ("open_app", "close_window", "close_tab", "play_music"):
        assert name in body, (
            f"build_device_section debe mencionar {name!r} como NO disponible"
        )


def test_build_device_section_lists_safe_actions():
    src = PROMPTS_PY.read_text(encoding="utf-8")
    section_match = re.search(
        r"def build_device_section[\s\S]+?(?=\ndef |\Z)", src
    )
    body = section_match.group(0)
    for name in ("save_taste", "save_date", "save_goal", "remind", "add_important"):
        assert name in body, (
            f"build_device_section debe mencionar {name!r} como SÍ disponible"
        )


def test_build_device_section_returns_empty_for_desktop():
    """Para device='desktop' debe devolver "" — sino rompe el cache prefix
    en el caso normal (PC)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from reflex_companion.prompts import build_device_section
    assert build_device_section("desktop", "es") == ""
    assert build_device_section("DESKTOP", "es") == ""
    assert build_device_section("", "es") == ""
    assert build_device_section(None, "es") == ""


def test_build_device_section_returns_text_for_mobile():
    import sys
    sys.path.insert(0, str(ROOT))
    from reflex_companion.prompts import build_device_section
    for lang in ("es", "en", "fr"):
        result = build_device_section("mobile", lang)
        assert result, f"build_device_section('mobile', {lang!r}) está vacío"
        assert len(result) > 200, (
            f"build_device_section('mobile', {lang!r}) sospechosamente corto"
        )


# ─────────────────────────────────────────────
#  Prompts es/en/fr aceptan device_section
# ─────────────────────────────────────────────

@pytest.mark.parametrize("path", [PROMPTS_ES, PROMPTS_EN, PROMPTS_FR])
def test_prompts_accept_device_section_param(path):
    src = path.read_text(encoding="utf-8")
    assert "device_section" in src, (
        f"{path.name}: falta el param device_section"
    )
    # Debe estar en la firma de build_system_prompt
    sig_match = re.search(
        r"def build_system_prompt\([\s\S]+?\) -> str:", src
    )
    assert sig_match
    assert "device_section" in sig_match.group(0), (
        f"{path.name}: device_section no está en la firma de build_system_prompt"
    )


@pytest.mark.parametrize("path", [PROMPTS_ES, PROMPTS_EN, PROMPTS_FR])
def test_prompts_inject_device_section_in_dynamic_bottom(path):
    """device_section debe ir AL INICIO del dynamic_bottom — afecta cache prefix
    solo cuando aplica (mobile), preservándolo en desktop (string vacío)."""
    src = path.read_text(encoding="utf-8")
    db_match = re.search(
        r"dynamic_bottom\s*=\s*\(\s*([\s\S]+?)\s*\)", src
    )
    assert db_match, f"{path.name}: no encontré dynamic_bottom"
    body = db_match.group(1)
    # device_section_str debe estar al INICIO de dynamic_bottom
    assert "device_section_str" in body, (
        f"{path.name}: dynamic_bottom no usa device_section_str"
    )
    # Posición: debe aparecer antes que state_section
    pos_device = body.find("device_section_str")
    pos_state = body.find("state_section")
    assert 0 <= pos_device < pos_state, (
        f"{path.name}: device_section_str debe ir antes que state_section "
        f"en dynamic_bottom"
    )


# ─────────────────────────────────────────────
#  Mobile send endpoint pasa device_section='mobile'
# ─────────────────────────────────────────────

def test_mobile_send_uses_device_section_mobile():
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_send_endpoint[\s\S]+?(?=\nasync def |\ndef )", src
    )
    assert section, "_mobile_send_endpoint no encontrado"
    body = section.group(0)
    assert "build_device_section" in body, (
        "_mobile_send_endpoint debe importar build_device_section"
    )
    assert 'build_device_section("mobile"' in body, (
        "_mobile_send_endpoint debe pasar device_section=build_device_section('mobile', ...)"
    )


# ─────────────────────────────────────────────
#  Sync endpoints registrados
# ─────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/api/mobile/sync_prompts",
    "/api/mobile/sync_state",
    "/api/mobile/sync_push",
])
def test_sync_endpoint_registered(path):
    src = API_ROUTES.read_text(encoding="utf-8")
    assert path in src, f"endpoint {path} no registrado en api_routes.py"


def test_sync_endpoints_check_auth():
    """Los 3 sync endpoints deben verificar el pairing token."""
    src = API_ROUTES.read_text(encoding="utf-8")
    for fn in ("_mobile_sync_prompts_endpoint",
               "_mobile_sync_state_endpoint",
               "_mobile_sync_push_endpoint"):
        section = re.search(
            rf"{fn}[\s\S]+?(?=\nasync def |\ndef )", src
        )
        assert section, f"{fn} no encontrado"
        body = section.group(0)
        assert "_check_mobile_auth" in body, (
            f"{fn} no verifica auth — vulnerabilidad"
        )


def test_sync_state_returns_critical_keys():
    """sync_state debe devolver los keys que el brain JS espera."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_sync_state_endpoint[\s\S]+?(?=\nasync def |\ndef )", src
    )
    body = section.group(0)
    for key in ("chat_history", "facts", "diary", "tastes", "reminders",
                "important", "important_dates", "goals", "stats",
                "mental_state", "affection", "language"):
        assert f'"{key}"' in body or f"'{key}'" in body, (
            f"sync_state no devuelve {key!r}"
        )


def test_sync_prompts_returns_three_languages():
    """sync_prompts debe construir prompts para es, en, fr."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_sync_prompts_endpoint[\s\S]+?(?=\nasync def |\ndef )", src
    )
    body = section.group(0)
    assert '"es"' in body and '"en"' in body and '"fr"' in body, (
        "sync_prompts debe construir es/en/fr"
    )
    assert "device_section" in body or "build_device_section" in body, (
        "sync_prompts debe inyectar device_section_mobile en cada idioma"
    )


def test_sync_push_merges_idempotent():
    """sync_push debe ser idempotente — mensajes con id duplicado se skipean."""
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"_mobile_sync_push_endpoint[\s\S]+?(?=\nasync def |\ndef )", src
    )
    body = section.group(0)
    assert "existing_ids" in body, (
        "sync_push debe mantener un set de IDs existentes para idempotencia"
    )


# ─────────────────────────────────────────────
#  LLM client — providers + auth headers
# ─────────────────────────────────────────────

def test_llm_supports_xai_and_openrouter():
    src = (BRAIN_DIR / "llm.js").read_text(encoding="utf-8")
    assert "https://api.x.ai/v1" in src, "llm.js: falta URL xAI"
    assert "https://openrouter.ai/api/v1" in src, "llm.js: falta URL OpenRouter"


def test_llm_uses_bearer_auth():
    src = (BRAIN_DIR / "llm.js").read_text(encoding="utf-8")
    assert "Authorization" in src and "Bearer" in src, (
        "llm.js debe usar Bearer auth (compatible OpenAI API)"
    )


def test_llm_streams_via_sse():
    """El cliente LLM debe parsear SSE (data: ...\\n\\n) y soportar [DONE]."""
    src = (BRAIN_DIR / "llm.js").read_text(encoding="utf-8")
    assert "[DONE]" in src, "llm.js: falta handling de SSE [DONE]"
    assert "data:" in src, "llm.js: falta parse de líneas SSE 'data:'"
    assert "ReadableStream" in src or "getReader" in src, (
        "llm.js: falta lectura streaming del response body"
    )


# ─────────────────────────────────────────────
#  Brain orchestrator — modo dual
# ─────────────────────────────────────────────

def test_brain_routes_online_to_pc_endpoint():
    src = (BRAIN_DIR / "brain.js").read_text(encoding="utf-8")
    # Online mode debe usar /api/mobile/send
    assert "/api/mobile/send" in src, (
        "brain.js: modo online debe llamar /api/mobile/send"
    )
    # X-Ashley-Token para auth
    assert "X-Ashley-Token" in src


def test_brain_routes_offline_to_local_llm():
    src = (BRAIN_DIR / "brain.js").read_text(encoding="utf-8")
    assert "llmFromConfig" in src, (
        "brain.js: modo offline debe cargar LLM client local"
    )
    assert "buildSystemPrompt" in src, (
        "brain.js: modo offline debe construir prompt local"
    )


def test_brain_filters_pc_actions_offline():
    src = (BRAIN_DIR / "brain.js").read_text(encoding="utf-8")
    assert "filterMobileActions" in src, (
        "brain.js debe filtrar actions PC-only en offline"
    )


def test_brain_marks_offline_messages_for_sync():
    src = (BRAIN_DIR / "brain.js").read_text(encoding="utf-8")
    # Los mensajes offline deben ir a pending_sync para push posterior
    assert "markPendingSync" in src, (
        "brain.js: mensajes offline deben marcarse para sync_push"
    )


def test_brain_applies_safe_actions_locally():
    """En offline, las safe actions (save_taste, save_date, etc.) deben
    aplicarse a la memoria local — sino se pierden hasta el push."""
    src = (BRAIN_DIR / "brain.js").read_text(encoding="utf-8")
    assert "_applySafeAction" in src, (
        "brain.js: falta _applySafeAction para offline mode"
    )
    # Cubrir los casos críticos
    for action in ("save_taste", "save_date", "save_goal", "remind"):
        assert f"=== '{action}'" in src or f"== '{action}'" in src or f"'{action}'" in src, (
            f"brain.js::_applySafeAction no maneja {action!r}"
        )
