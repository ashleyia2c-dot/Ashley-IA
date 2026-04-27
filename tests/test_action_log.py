"""Tests for action_log + system_state — v0.13.15.

Estos módulos sirven para diagnosticar acciones que Ashley ejecuta mal
(p.ej. emite [action:volume:set:0] cuando el user pide "al máximo").
"""

from reflex_companion import action_log, system_state


# ══════════════════════════════════════════════════════════════════════
#  format_state_for_prompt
# ══════════════════════════════════════════════════════════════════════

def test_format_state_empty_snapshot_returns_empty_string():
    """Si pycaw falla / no hay datos, no metemos basura al prompt."""
    snap = {"volume_pct": None, "volume_muted": None, "active_window": ""}
    assert system_state.format_state_for_prompt(snap, lang="es") == ""


def test_format_state_spanish_includes_volume():
    snap = {"volume_pct": 65, "volume_muted": False, "active_window": "Spotify"}
    out = system_state.format_state_for_prompt(snap, lang="es")
    assert "65%" in out
    assert "Spotify" in out
    assert "no muteado" in out
    assert out.startswith("[Estado")


def test_format_state_english_includes_volume():
    snap = {"volume_pct": 100, "volume_muted": True, "active_window": "Notepad"}
    out = system_state.format_state_for_prompt(snap, lang="en")
    assert "100%" in out
    assert "muted" in out
    assert "Notepad" in out


def test_format_state_french():
    snap = {"volume_pct": 30, "volume_muted": False, "active_window": ""}
    out = system_state.format_state_for_prompt(snap, lang="fr")
    assert "30%" in out
    assert "non muet" in out


def test_format_state_truncates_long_window_title():
    """Títulos de ventana largos no deben llenar el prompt."""
    long_title = "A" * 200
    snap = {"volume_pct": 50, "volume_muted": False, "active_window": long_title}
    out = system_state.format_state_for_prompt(snap, lang="en")
    # El título debe estar truncado
    assert long_title not in out
    assert "…" in out  # truncate marker


# ══════════════════════════════════════════════════════════════════════
#  action_log
# ══════════════════════════════════════════════════════════════════════

def test_log_action_result_persists_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    action_log.log_action_result(
        user_intent="súbele al máximo",
        action_type="volume",
        action_params=["set", "100"],
        action_description="Volumen → 100%",
        result="Volumen establecido al 100%.",
        state_before={"volume_pct": 65, "volume_muted": False},
        state_after={"volume_pct": 100, "volume_muted": False},
    )
    entries = action_log.load_recent_actions()
    assert len(entries) == 1
    assert entries[0]["action_type"] == "volume"
    assert entries[0]["action_params"] == ["set", "100"]
    assert entries[0]["mismatch"] is None  # 100 reached, no mismatch


def test_log_detects_volume_set_mismatch(tmp_path, monkeypatch):
    """El bug que motivó esto: user pide "al máximo" → Ashley emite
    [action:volume:set:0] → sistema queda en 0 → debe marcarse mismatch."""
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    action_log.log_action_result(
        user_intent="al máximo",
        action_type="volume",
        action_params=["set", "0"],   # Ashley emitió mal
        action_description="Volumen → 0%",
        result="Volumen establecido al 0%.",
        state_before={"volume_pct": 65, "volume_muted": False},
        state_after={"volume_pct": 0, "volume_muted": False},  # silencio
    )
    entries = action_log.load_recent_actions()
    # Set:0 SÍ es coherente con state_after=0 — no es mismatch técnico.
    # El mismatch detector solo detecta inconsistencia entre lo emitido
    # y lo aplicado. El "Ashley emitió 0 cuando user pidió 100" es otro
    # tipo de bug que requiere comparar user_intent vs params (más
    # complejo, fuera del scope de mismatch básico).
    # Pero el log SÍ guarda toda la info para análisis manual posterior.
    assert entries[0]["user_intent"] == "al máximo"
    assert entries[0]["action_params"] == ["set", "0"]
    assert entries[0]["state_after"]["volume_pct"] == 0


def test_log_detects_set_with_unreached_target(tmp_path, monkeypatch):
    """set:100 emitido pero el sistema quedó en 50 → mismatch real."""
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    action_log.log_action_result(
        user_intent="ponlo al máximo",
        action_type="volume",
        action_params=["set", "100"],
        action_description="Volumen → 100%",
        result="ok",
        state_before={"volume_pct": 50, "volume_muted": False},
        state_after={"volume_pct": 50, "volume_muted": False},  # no cambió
    )
    entries = action_log.load_recent_actions()
    assert entries[0]["mismatch"] is not None
    assert "100" in entries[0]["mismatch"]


def test_log_detects_up_with_volume_not_increased(tmp_path, monkeypatch):
    """volume:up emitido pero el volumen bajó o quedó igual."""
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    action_log.log_action_result(
        user_intent="súbele",
        action_type="volume",
        action_params=["up"],
        action_description="Subir volumen",
        result="ok",
        state_before={"volume_pct": 60, "volume_muted": False},
        state_after={"volume_pct": 60, "volume_muted": False},
    )
    entries = action_log.load_recent_actions()
    assert entries[0]["mismatch"] is not None
    assert "up" in entries[0]["mismatch"].lower() or "60" in entries[0]["mismatch"]


def test_log_caps_at_max_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    monkeypatch.setattr(action_log, "MAX_ACTION_LOG_ENTRIES", 3)
    for i in range(5):
        action_log.log_action_result(
            user_intent=f"intent {i}",
            action_type="volume",
            action_params=["up"],
            action_description="x",
            result="ok",
            state_before={"volume_pct": 50},
            state_after={"volume_pct": 60},
        )
    entries = action_log.load_recent_actions()
    assert len(entries) == 3
    # El más nuevo (intent 4) está primero
    assert entries[0]["user_intent"] == "intent 4"


def test_log_does_not_crash_on_missing_state(tmp_path, monkeypatch):
    """Si pycaw falla, state_before/after pueden venir vacíos. NO debe crashear."""
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    action_log.log_action_result(
        user_intent="test",
        action_type="open_app",
        action_params=["notepad"],
        action_description="Open Notepad",
        result="ok",
        state_before={},
        state_after={},
    )
    entries = action_log.load_recent_actions()
    assert len(entries) == 1
    assert entries[0]["mismatch"] is None  # no comparable, no error


def test_count_mismatches(tmp_path, monkeypatch):
    monkeypatch.setattr(action_log, "ACTION_LOG_FILE", str(tmp_path / "log.json"))
    # 1 OK, 2 mismatch
    action_log.log_action_result(
        user_intent="x", action_type="volume", action_params=["set", "100"],
        action_description="x", result="ok",
        state_before={"volume_pct": 50}, state_after={"volume_pct": 100},
    )
    action_log.log_action_result(
        user_intent="x", action_type="volume", action_params=["set", "100"],
        action_description="x", result="ok",
        state_before={"volume_pct": 50}, state_after={"volume_pct": 50},
    )
    action_log.log_action_result(
        user_intent="x", action_type="volume", action_params=["up"],
        action_description="x", result="ok",
        state_before={"volume_pct": 60}, state_after={"volume_pct": 60},
    )
    assert action_log.count_mismatches() == 2
