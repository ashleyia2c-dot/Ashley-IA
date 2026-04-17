"""
migrations.py — Versionado y migraciones del schema de datos de Ashley.

Problema que resolvemos:
    Cuando evoluciona la estructura de los archivos JSON en disco
    (añadimos un campo, renombramos otro, cambiamos un tipo), los
    usuarios existentes con datos del formato viejo pueden:
      - Ver todos sus logros como bloqueados (el load lee un campo
        que ya no existe)
      - Perder afecto (default 50 reemplaza el nivel viejo)
      - Crashear al cargar (el State no sabe interpretar el dict)

Solución:
    - Mantenemos un archivo `_meta.json` con la versión del schema.
    - Al arrancar, comparamos con DATA_SCHEMA_VERSION y corremos las
      migraciones que falten.
    - Cada migración es una función idempotente que transforma los
      archivos del user de la versión N a N+1.

Uso:
    En on_load() de State, llamar UNA VEZ a ``migrate_if_needed()``
    antes de cargar cualquier archivo de datos. Si todo está al día,
    es no-op en microsegundos.

Para agregar una migración nueva:
    1. Subí DATA_SCHEMA_VERSION en 1.
    2. Escribí una función ``_migrate_N_to_N_plus_1()`` que lea los
       archivos JSON crudos, los transforme, y los persista via save_json.
    3. Añadila al dict MIGRATIONS con su versión origen como key.
"""

import logging
from typing import Callable

from .config import _data_path
from .memory import load_json, save_json

_log = logging.getLogger("ashley.migrations")

# ─────────────────────────────────────────────
#  Versión actual del schema
# ─────────────────────────────────────────────
#
# IMPORTANTE: subir este número SIEMPRE que cambies el formato de un JSON
# persistido, y añadir la migración correspondiente. Nunca bajarlo.

DATA_SCHEMA_VERSION = 1

META_FILE = _data_path("_meta.json")


# ─────────────────────────────────────────────
#  Migraciones concretas (vacías por ahora)
# ─────────────────────────────────────────────
#
# Cuando llegue el momento, las migraciones futuras van aquí. Ejemplo de
# cómo quedaría una que renombra "level" a "value" en affection_ashley.json:
#
#     def _migrate_1_to_2() -> None:
#         data = load_json(_data_path("affection_ashley.json"), None)
#         if data is None:
#             return
#         if "level" in data and "value" not in data:
#             data["value"] = data.pop("level")
#             save_json(_data_path("affection_ashley.json"), data)


# Registro de migraciones: {versión_origen: función_que_migra_a_origen+1}
# Se ejecutan en orden desde la versión actual del user hasta DATA_SCHEMA_VERSION.
MIGRATIONS: dict[int, Callable[[], None]] = {
    # 1: _migrate_1_to_2,  ← se descomenta cuando exista la migración
}


# ─────────────────────────────────────────────
#  Orquestador
# ─────────────────────────────────────────────

def _read_current_version() -> int:
    """Lee la versión actual del schema en disco. 0 si no existe (fresh install)."""
    data = load_json(META_FILE, None)
    if data is None:
        return 0
    try:
        return int(data.get("schema_version", 0))
    except Exception:
        return 0


def _write_current_version(version: int) -> None:
    save_json(META_FILE, {"schema_version": int(version)})


def migrate_if_needed() -> None:
    """Aplica migraciones pendientes. Idempotente — si ya está al día, no-op.

    Protecciones:
      - Si una migración falla, abortamos y dejamos la versión como estaba.
        El user arranca con datos parcialmente migrados (mejor que perder
        todo). La migración se re-intentará en el próximo arranque.
      - save_json es atómico: no dejamos archivos a medias si crashea
        entre migraciones.
    """
    current = _read_current_version()
    target = DATA_SCHEMA_VERSION

    if current == target:
        return
    if current > target:
        _log.warning(
            "schema_version en disco (%d) es MAYOR que el de la app (%d) — "
            "usuario probablemente downgradeó. No migramos hacia atrás.",
            current, target,
        )
        return

    # Fresh install: marcamos versión actual sin correr migraciones.
    if current == 0:
        _log.info("fresh install: marcando schema_version=%d", target)
        _write_current_version(target)
        return

    _log.info("migrando schema de v%d a v%d", current, target)
    for from_version in range(current, target):
        fn = MIGRATIONS.get(from_version)
        if fn is None:
            _log.error(
                "falta migración de v%d a v%d — abortando", from_version, from_version + 1,
            )
            return
        try:
            fn()
            _write_current_version(from_version + 1)
            _log.info("migración v%d → v%d OK", from_version, from_version + 1)
        except Exception as e:
            _log.error(
                "migración v%d → v%d falló: %s — datos quedan en v%d",
                from_version, from_version + 1, e, from_version,
            )
            return
