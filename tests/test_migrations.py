"""Tests para migrations.py — versionado del schema de datos.

Cubren:
  - Fresh install: escribe versión actual sin correr nada.
  - Al día: no-op.
  - Downgrade detectado: warning, no rompe.
  - Cadena de migraciones pendientes: corre en orden.
  - Falla en medio: preserva datos hasta la última exitosa.
"""
import json
import os
import tempfile
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_data_dir(monkeypatch):
    """Aísla el data dir en un temporal y re-importa migrations para que
    tome la ruta nueva."""
    d = tempfile.mkdtemp()
    monkeypatch.setenv("ASHLEY_DATA_DIR", d)

    # Forzar re-lectura de las rutas del módulo
    import importlib
    from reflex_companion import config as cfg
    importlib.reload(cfg)
    from reflex_companion import migrations as mg
    importlib.reload(mg)
    yield d, mg


def test_fresh_install_marks_version_no_migrations(tmp_data_dir):
    d, mg = tmp_data_dir
    # No hay _meta.json
    mg.migrate_if_needed()
    # Debe haber escrito la versión actual
    with open(os.path.join(d, "_meta.json")) as f:
        meta = json.load(f)
    assert meta["schema_version"] == mg.DATA_SCHEMA_VERSION


def test_up_to_date_is_noop(tmp_data_dir):
    d, mg = tmp_data_dir
    with open(os.path.join(d, "_meta.json"), "w") as f:
        json.dump({"schema_version": mg.DATA_SCHEMA_VERSION}, f)
    called = []
    # Inject a dummy migration that should NOT be called
    with patch.dict(mg.MIGRATIONS, {999: lambda: called.append(1)}):
        mg.migrate_if_needed()
    assert called == []


def test_downgrade_is_ignored(tmp_data_dir):
    d, mg = tmp_data_dir
    future_version = mg.DATA_SCHEMA_VERSION + 5
    with open(os.path.join(d, "_meta.json"), "w") as f:
        json.dump({"schema_version": future_version}, f)
    # Debe completar sin excepción
    mg.migrate_if_needed()
    # La versión en disco queda como estaba (no bajamos)
    with open(os.path.join(d, "_meta.json")) as f:
        meta = json.load(f)
    assert meta["schema_version"] == future_version


def test_migration_chain_runs_in_order(tmp_data_dir):
    d, mg = tmp_data_dir
    # Fingir versión 1 en disco y target en 3 con dos migraciones registradas
    with open(os.path.join(d, "_meta.json"), "w") as f:
        json.dump({"schema_version": 1}, f)
    calls = []
    def m1to2(): calls.append(1)
    def m2to3(): calls.append(2)
    with patch.object(mg, "DATA_SCHEMA_VERSION", 3), \
         patch.dict(mg.MIGRATIONS, {1: m1to2, 2: m2to3}, clear=True):
        mg.migrate_if_needed()
    assert calls == [1, 2]
    with open(os.path.join(d, "_meta.json")) as f:
        meta = json.load(f)
    assert meta["schema_version"] == 3


def test_migration_failure_preserves_last_good_version(tmp_data_dir):
    d, mg = tmp_data_dir
    with open(os.path.join(d, "_meta.json"), "w") as f:
        json.dump({"schema_version": 1}, f)
    def m1to2(): pass  # OK
    def m2to3(): raise RuntimeError("boom")
    with patch.object(mg, "DATA_SCHEMA_VERSION", 3), \
         patch.dict(mg.MIGRATIONS, {1: m1to2, 2: m2to3}, clear=True):
        mg.migrate_if_needed()
    # Debe haberse quedado en 2 (la migración exitosa), no en 1 ni en 3.
    with open(os.path.join(d, "_meta.json")) as f:
        meta = json.load(f)
    assert meta["schema_version"] == 2


def test_missing_migration_aborts_cleanly(tmp_data_dir):
    d, mg = tmp_data_dir
    with open(os.path.join(d, "_meta.json"), "w") as f:
        json.dump({"schema_version": 1}, f)
    # Target 5 pero sólo tenemos 1→2; debería parar en 2 sin crashear.
    def m1to2(): pass
    with patch.object(mg, "DATA_SCHEMA_VERSION", 5), \
         patch.dict(mg.MIGRATIONS, {1: m1to2}, clear=True):
        mg.migrate_if_needed()
    with open(os.path.join(d, "_meta.json")) as f:
        meta = json.load(f)
    assert meta["schema_version"] == 2
