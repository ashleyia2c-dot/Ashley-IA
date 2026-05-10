"""
export.py — Backup/export de TODOS los datos del user en un ZIP.

Por qué existe:
  1. RGPD "right to data portability" — el user tiene derecho a llevarse
     todo lo que Ashley sabe de él en formato legible.
  2. Tranquilidad — antes de upgrades / cambios de PC / desinstalar para
     reinstalar, el user puede hacer backup defensivo.
  3. Migración — facilita mover Ashley de un PC a otro (export aquí,
     copiar JSON files al nuevo PC en %APPDATA%\\Ashley\\data\\).

Qué incluye:
  - Todos los JSON files de %APPDATA%\\Ashley\\data\\
    (chat, facts, diary, reminders, achievements, mental_state, etc.)
  - voice.json + language.json (preferences)
  - Manifest README.txt explicando qué es cada archivo

Qué NO incluye (intencionadamente):
  - key.bin (API key cifrada con DPAPI — el cifrado está atado al usuario
    Windows, no se puede descifrar en otra cuenta. Inútil exportarla.)
  - license.json (atado a una activación de Lemon Squeezy específica;
    moverla a otro PC no funcionaría — toca reactivar)

v0.19.7 — feature inicial. Endpoint /api/export/data devuelve el ZIP.
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from datetime import datetime
from pathlib import Path

from .config import _data_path

_log = logging.getLogger("ashley.export")


# Archivos que SÍ exportamos (en orden de relevancia para el README)
_EXPORTABLE_JSON = [
    ("historial_ashley.json", "Chat history (last 50 messages)"),
    ("hechos_ashley.json", "Facts Ashley remembers about you"),
    ("diario_ashley.json", "Diary entries Ashley writes after sessions"),
    ("affection_ashley.json", "How much Ashley likes you (0-100)"),
    ("gustos_ashley.json", "Your taste preferences (food, music, etc.)"),
    ("recordatorios_ashley.json", "Pending reminders"),
    ("importantes_ashley.json", "Your important things list"),
    ("fechas_importantes_ashley.json", "Birthdays + anniversaries"),
    ("objetivos_ashley.json", "Your long-term goals"),
    ("achievements_ashley.json", "Achievements you unlocked"),
    ("stats_ashley.json", "Usage stats (relationship age, etc.)"),
    ("mental_state_ashley.json", "Ashley's current mood/preoccupation state"),
    ("discovery_ashley.json", "Last discovery run timestamp"),
    ("news_ashley.json", "News topics Ashley referenced"),
    ("actions_log_ashley.json", "Log of system actions Ashley executed"),
    ("language.json", "Your selected UI language"),
    ("voice.json", "Voice/TTS preferences (excluding API keys)"),
]

# Archivos que NO exportamos (con razón documentada para el manifest)
_EXCLUDED = [
    ("key.bin", "Your xAI/OpenRouter API key — encrypted with Windows DPAPI, "
                "tied to your Windows user account. Cannot be decrypted on "
                "another account or PC. To migrate: re-enter on the new PC."),
    ("license.json", "Your Lemon Squeezy license activation — tied to this "
                     "specific PC's instance ID. To migrate: deactivate from "
                     "Settings → License here, then re-activate on the new PC."),
]


def _data_dir() -> Path:
    """Devuelve el path del data dir donde viven todos los JSON files."""
    # _data_path("x") devuelve "<dir>/x", quitamos "/x" para tener el dir
    sample = _data_path("dummy")
    return Path(sample).parent


def _build_manifest(included: list[tuple[str, str, int]]) -> str:
    """Genera el README.txt del backup explicando qué hay dentro."""
    timestamp = datetime.now().isoformat(timespec="seconds")
    lines = [
        "Ashley Data Export",
        "=" * 60,
        f"Created: {timestamp}",
        f"Format: ZIP of JSON files from your %APPDATA%\\Ashley\\data\\",
        "",
        "WHAT'S INSIDE",
        "-" * 60,
    ]
    if not included:
        lines.append("(no data files found — Ashley hasn't recorded anything yet)")
    else:
        for filename, description, size_bytes in included:
            size_kb = size_bytes / 1024
            lines.append(f"  {filename:40} {size_kb:>7.1f} KB  — {description}")

    lines += [
        "",
        "WHAT'S NOT INCLUDED (intentionally)",
        "-" * 60,
    ]
    for filename, reason in _EXCLUDED:
        lines.append(f"  {filename}")
        # Word-wrap reason a ~70 chars
        words = reason.split()
        line = "    "
        for w in words:
            if len(line) + len(w) > 76:
                lines.append(line.rstrip())
                line = "    " + w + " "
            else:
                line += w + " "
        if line.strip():
            lines.append(line.rstrip())
        lines.append("")

    lines += [
        "HOW TO USE THIS BACKUP",
        "-" * 60,
        "  Restore on the same PC:",
        "    1. Close Ashley.",
        "    2. Extract this ZIP.",
        "    3. Copy the .json files into %APPDATA%\\Ashley\\data\\",
        "       (overwrite if asked).",
        "    4. Open Ashley — she remembers everything.",
        "",
        "  Migrate to another PC:",
        "    1. Install Ashley on the new PC.",
        "    2. Open it once, set your language + API key in onboarding.",
        "    3. Close Ashley.",
        "    4. Extract this ZIP, copy the .json files into",
        "       %APPDATA%\\Ashley\\data\\ on the new PC.",
        "    5. Reopen Ashley — she now remembers everything.",
        "",
        "GDPR NOTE",
        "-" * 60,
        "  Per EU GDPR Article 20 (right to data portability), you have the",
        "  right to receive your personal data in a structured, commonly used",
        "  and machine-readable format. JSON satisfies this. You can use this",
        "  export to verify what Ashley knows about you, take it elsewhere,",
        "  or delete the original files to wipe your data.",
        "",
        "QUESTIONS",
        "-" * 60,
        "  ashleyia2c@gmail.com",
    ]
    return "\n".join(lines)


def build_data_zip() -> tuple[bytes, str]:
    """Construye un ZIP en memoria con todos los datos exportables.

    Returns:
        (zip_bytes, suggested_filename)
    """
    data_dir = _data_dir()
    if not data_dir.exists():
        _log.warning("data dir does not exist: %s", data_dir)

    buf = io.BytesIO()
    included: list[tuple[str, str, int]] = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for filename, description in _EXPORTABLE_JSON:
            file_path = data_dir / filename
            if not file_path.exists():
                continue
            try:
                size = file_path.stat().st_size
                if size == 0:
                    # Skip empty files (Ashley hasn't recorded that aspect yet)
                    continue
                zf.write(file_path, arcname=filename)
                included.append((filename, description, size))
            except Exception as e:
                _log.warning("could not zip %s: %s", filename, e)
                continue

        # Manifest README
        manifest = _build_manifest(included)
        zf.writestr("README.txt", manifest.encode("utf-8"))

    buf.seek(0)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"ashley-backup-{timestamp}.zip"
    return buf.getvalue(), filename
