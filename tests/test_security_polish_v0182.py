"""Guards de los 3 polish de seguridad + 1 bug fix (v0.18.2 final).

1. Filtro [system:X] del display — Ashley a veces alucina ese tag.
2. Aviso de seguridad en el dialog QR del desktop.
3. Rate limiting (60 req/min por token) — anti-spam si el QR se filtra.
4. Auto-rotation del token cada 30 días — limita el blast radius.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARSING_PY = ROOT / "reflex_companion" / "parsing.py"
PARSING_JS = ROOT / "assets" / "mobile" / "brain" / "parsing.js"
APP_JS = ROOT / "assets" / "mobile" / "app.js"
COMPONENTS_PY = ROOT / "reflex_companion" / "components.py"
I18N_PY = ROOT / "reflex_companion" / "i18n.py"
API_ROUTES = ROOT / "reflex_companion" / "api_routes.py"


# ─────────────────────────────────────────────
#  Bug fix: filtro [system:X]
# ─────────────────────────────────────────────

def test_python_clean_display_strips_system_tag():
    """clean_display debe eliminar [system:proactive_message] y similares
    que Ashley alucina en sus respuestas (no están en el protocolo)."""
    import importlib
    import sys
    # Forzar re-import (por si pycache stale)
    for mod in list(sys.modules.keys()):
        if mod.startswith("reflex_companion."):
            del sys.modules[mod]
    sys.path.insert(0, str(ROOT))
    from reflex_companion.parsing import clean_display

    cases = [
        # Casos reales reportados por user
        ("Te mira con calidez [system:proactive_message]\nHola jefe.",
         "should_strip"),
        ("[system:proactive_message]\nBuenas tardes.",
         "should_strip"),
        ("Mensaje normal [system:something_else] más texto",
         "should_strip"),
        ("Con espacios [ system : foo ] y ya",
         "should_strip"),
        # Y caso negativo: NO debe tocar la palabra "system" en texto natural
        # (sin corchetes), solo el marker [system:X]
        ("This is a system message about updates", "keep_word"),
    ]
    for text, expectation in cases:
        result = clean_display(text)
        if expectation == "should_strip":
            assert "[system" not in result.lower(), (
                f"clean_display NO eliminó [system:X] de: {text!r} → {result!r}"
            )
        elif expectation == "keep_word":
            # La palabra "system" sin corchetes NO debe tocarse
            assert "system" in result.lower(), (
                f"clean_display borró palabra 'system' inesperadamente: "
                f"{text!r} → {result!r}"
            )


def test_js_clean_display_strips_system_tag():
    """parsing.js::cleanDisplay debe tener el mismo filtro."""
    src = PARSING_JS.read_text(encoding="utf-8")
    # Buscar el regex que elimina [system:X]
    assert "system" in src, "parsing.js no tiene filtro de [system:X]"
    # Patrón típico
    assert re.search(r"system\\s\*:.*\]", src) or "[system" in src, (
        "parsing.js no parece eliminar [system:X]"
    )


def test_app_js_offline_path_strips_system_tag():
    """El path offline de sendMessage en app.js (sin brain) también debe
    strippear [system:X] del display."""
    src = APP_JS.read_text(encoding="utf-8")
    section = re.search(
        r"async function sendMessage[\s\S]+?(?=\n  async function |\n  function )",
        src,
    )
    assert section
    body = section.group(0)
    assert "system" in body, (
        "app.js offline path NO strippea [system:X]"
    )


# ─────────────────────────────────────────────
#  Aviso de seguridad en dialog QR
# ─────────────────────────────────────────────

def test_security_warning_i18n_keys_in_three_languages():
    src = I18N_PY.read_text(encoding="utf-8")
    occurrences = src.count('"mobile_pair_security_warning":')
    assert occurrences >= 3, (
        f"mobile_pair_security_warning solo en {occurrences}/3 idiomas (es/en/fr)"
    )


def test_security_warning_displayed_in_dialog():
    src = COMPONENTS_PY.read_text(encoding="utf-8")
    section = re.search(
        r"def mobile_pair_dialog\(\)[\s\S]+?(?=\ndef |\Z)", src,
    )
    assert section
    body = section.group(0)
    assert "mobile_pair_security_warning" in body, (
        "Dialog QR NO muestra el aviso de seguridad"
    )


# ─────────────────────────────────────────────
#  Rate limiting
# ─────────────────────────────────────────────

def test_rate_limit_function_exists():
    src = API_ROUTES.read_text(encoding="utf-8")
    assert "_is_rate_limited" in src, (
        "Falta _is_rate_limited() — anti-spam contra QR filtrado"
    )


def test_rate_limit_constants_reasonable():
    src = API_ROUTES.read_text(encoding="utf-8")
    # 60 req/min es generoso para user normal (~10/min real) pero corta abuso
    m = re.search(r"_RATE_LIMIT_MAX_PER_MIN\s*=\s*(\d+)", src)
    assert m, "_RATE_LIMIT_MAX_PER_MIN no definido"
    n = int(m.group(1))
    assert 30 <= n <= 200, f"rate limit {n}/min fuera de rango razonable"


def test_rate_limit_uses_sliding_window():
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"def _is_rate_limited[\s\S]+?(?=\ndef )", src,
    )
    assert section
    body = section.group(0)
    # Debe purgar timestamps fuera de ventana
    assert "cutoff" in body or "window" in body.lower(), (
        "_is_rate_limited debe usar sliding window (purgar timestamps viejos)"
    )


def test_rate_limit_thread_safe():
    """El log de rate limit se accede desde múltiples requests concurrentes
    — debe estar protegido con lock."""
    src = API_ROUTES.read_text(encoding="utf-8")
    assert "_rate_limit_lock" in src, (
        "Rate limit dict debe tener lock para thread-safety"
    )
    section = re.search(
        r"def _is_rate_limited[\s\S]+?(?=\ndef )", src,
    )
    body = section.group(0)
    assert "lock" in body.lower(), (
        "_is_rate_limited debe usar el lock al modificar el dict"
    )


def test_check_mobile_auth_includes_rate_limit():
    src = API_ROUTES.read_text(encoding="utf-8")
    section = re.search(
        r"def _check_mobile_auth[\s\S]+?(?=\ndef )", src,
    )
    assert section
    body = section.group(0)
    assert "_is_rate_limited" in body, (
        "_check_mobile_auth DEBE chequear rate limit (sino es bypass trivial)"
    )


def test_rate_limit_runtime_blocks_after_max():
    """Verifica el comportamiento real: tras 60 requests en 1 min, el 61
    es rechazado."""
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("reflex_companion."):
            del sys.modules[mod]
    sys.path.insert(0, str(ROOT))
    from reflex_companion.api_routes import (
        _is_rate_limited, _RATE_LIMIT_MAX_PER_MIN, _rate_limit_log,
    )
    test_token = "test-rate-limit-token-xyz"
    # Limpiar estado previo
    _rate_limit_log.pop(test_token, None)
    # Hacer MAX requests — todos OK
    for i in range(_RATE_LIMIT_MAX_PER_MIN):
        assert _is_rate_limited(test_token) is False, (
            f"Request {i+1}/{_RATE_LIMIT_MAX_PER_MIN} bloqueado prematuramente"
        )
    # El siguiente DEBE bloquearse
    assert _is_rate_limited(test_token) is True, (
        f"Request {_RATE_LIMIT_MAX_PER_MIN+1} NO bloqueado — rate limit roto"
    )
    # Cleanup
    _rate_limit_log.pop(test_token, None)


# ─────────────────────────────────────────────
#  Auto-rotation del token (30 días)
# ─────────────────────────────────────────────

def test_token_record_has_created_at():
    src = API_ROUTES.read_text(encoding="utf-8")
    assert "_generate_new_token_record" in src or "_TOKEN_ROTATION_DAYS" in src
    assert "created_at" in src, (
        "Token record debe incluir created_at para auto-rotation"
    )


def test_token_rotation_constant():
    src = API_ROUTES.read_text(encoding="utf-8")
    m = re.search(r"_TOKEN_ROTATION_DAYS\s*=\s*(\d+)", src)
    assert m, "Falta _TOKEN_ROTATION_DAYS constante"
    days = int(m.group(1))
    assert 7 <= days <= 90, f"rotation cada {days} días fuera de rango"


def test_read_pairing_token_rotates_old_token():
    """Si el token tiene más de N días, _read_pairing_token debe regenerar
    automáticamente."""
    import sys, os, json, tempfile, shutil
    from datetime import datetime, timezone, timedelta
    for mod in list(sys.modules.keys()):
        if mod.startswith("reflex_companion."):
            del sys.modules[mod]
    sys.path.insert(0, str(ROOT))
    # Setup: temp data dir con un token "viejo" (40 días)
    tmpdir = tempfile.mkdtemp(prefix="ashley_test_rotation_")
    try:
        os.environ["ASHLEY_DATA_DIR"] = tmpdir
        from reflex_companion import api_routes
        # Crear archivo con token viejo
        old_created = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        old_token_data = {
            "token": "ancient-token-must-rotate",
            "created_at": old_created,
        }
        with open(os.path.join(tmpdir, "mobile_pairing.json"), "w") as f:
            json.dump(old_token_data, f)
        # Llamar — debe rotar
        new_token = api_routes._read_pairing_token()
        assert new_token != "ancient-token-must-rotate", (
            "_read_pairing_token NO rota el token viejo (>30 días)"
        )
        # El archivo debe contener el nuevo
        with open(os.path.join(tmpdir, "mobile_pairing.json"), "r") as f:
            data = json.load(f)
        assert data["token"] == new_token
        assert "created_at" in data
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.environ.pop("ASHLEY_DATA_DIR", None)


def test_read_pairing_token_keeps_fresh_token():
    """Token reciente NO debe rotarse (sino los users con móvil pareado
    pierden la conexión cada vez)."""
    import sys, os, json, tempfile, shutil
    from datetime import datetime, timezone, timedelta
    for mod in list(sys.modules.keys()):
        if mod.startswith("reflex_companion."):
            del sys.modules[mod]
    sys.path.insert(0, str(ROOT))
    tmpdir = tempfile.mkdtemp(prefix="ashley_test_rotation_")
    try:
        os.environ["ASHLEY_DATA_DIR"] = tmpdir
        from reflex_companion import api_routes
        # Token reciente (5 días)
        recent_created = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        with open(os.path.join(tmpdir, "mobile_pairing.json"), "w") as f:
            json.dump({"token": "fresh-token-keep", "created_at": recent_created}, f)
        result = api_routes._read_pairing_token()
        assert result == "fresh-token-keep", (
            "Token reciente NO debe rotarse — móviles ya pareados perderían conexión"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.environ.pop("ASHLEY_DATA_DIR", None)


def test_legacy_token_gets_timestamp_added():
    """Un token legacy (sin created_at) NO debe rotarse pero SÍ recibir
    un timestamp para que la próxima rotación funcione."""
    import sys, os, json, tempfile, shutil
    for mod in list(sys.modules.keys()):
        if mod.startswith("reflex_companion."):
            del sys.modules[mod]
    sys.path.insert(0, str(ROOT))
    tmpdir = tempfile.mkdtemp(prefix="ashley_test_rotation_")
    try:
        os.environ["ASHLEY_DATA_DIR"] = tmpdir
        from reflex_companion import api_routes
        # Token legacy: solo "token", sin "created_at"
        with open(os.path.join(tmpdir, "mobile_pairing.json"), "w") as f:
            json.dump({"token": "legacy-token-keep"}, f)
        result = api_routes._read_pairing_token()
        assert result == "legacy-token-keep", (
            "Token legacy NO debe rotarse en primera lectura"
        )
        # Debe haber añadido created_at
        with open(os.path.join(tmpdir, "mobile_pairing.json"), "r") as f:
            data = json.load(f)
        assert "created_at" in data, (
            "Token legacy debe recibir created_at para futuro auto-rotation"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.environ.pop("ASHLEY_DATA_DIR", None)
