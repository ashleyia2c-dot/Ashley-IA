"""
tastes.py — Gustos del jefe y control de discovery proactivo.
"""
import json, os, uuid
from datetime import datetime
from .config import TASTES_FILE, DISCOVERY_FILE


def _load(path):
    if not os.path.exists(path): return []
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def _load_dict(path):
    if not os.path.exists(path): return {}
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_tastes() -> list[dict]:
    return _load(TASTES_FILE)

def add_taste(categoria: str, valor: str) -> str:
    tastes = load_tastes()
    entry = {"id": str(uuid.uuid4())[:8], "categoria": categoria.lower().strip(), "valor": valor.strip(), "created_at": datetime.now().isoformat()}
    tastes.append(entry)
    _save(TASTES_FILE, tastes)
    return f"Gusto guardado: [{categoria}] {valor}"

def delete_taste(taste_id: str) -> bool:
    tastes = load_tastes()
    new = [t for t in tastes if t["id"] != taste_id]
    if len(new) < len(tastes):
        _save(TASTES_FILE, new)
        return True
    return False

def format_tastes_for_prompt(tastes: list[dict]) -> str:
    if not tastes: return ""
    by_cat: dict[str, list[str]] = {}
    for t in tastes:
        by_cat.setdefault(t["categoria"], []).append(t["valor"])
    lines = []
    for cat, vals in by_cat.items():
        lines.append(f"  {cat}: {', '.join(vals)}")
    return "\n".join(lines)

def should_run_discovery(min_hours: float = 4.0) -> bool:
    state = _load_dict(DISCOVERY_FILE)
    last = state.get("last_run_at")
    if not last: return True
    try:
        elapsed = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600
        return elapsed >= min_hours
    except: return True

def update_discovery_time():
    _save(DISCOVERY_FILE, {"last_run_at": datetime.now().isoformat()})
