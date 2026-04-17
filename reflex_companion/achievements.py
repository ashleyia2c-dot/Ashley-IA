"""
achievements.py — Achievement / trophy system for Ashley.

Defines all achievements, their unlock conditions, and persistence.
Achievements are saved to a JSON file and checked after each interaction.
"""

import json
import os
from datetime import datetime
from .config import _data_path

ACHIEVEMENTS_FILE = _data_path("achievements_ashley.json")

# ─────────────────────────────────────────────
#  Achievement definitions
# ─────────────────────────────────────────────

ACHIEVEMENTS = [
    # Affection milestones
    {"id": "ice_breaker", "icon": "\U0001f9ca", "tier": "affection",
     "name_en": "Ice Breaker", "name_es": "Rompehielos",
     "desc_en": "You started to melt Ashley's walls.",
     "desc_es": "Empezaste a derretir las paredes de Ashley."},
    {"id": "getting_closer", "icon": "\U0001f338", "tier": "affection",
     "name_en": "Getting Closer", "name_es": "Cada vez m\u00e1s cerca",
     "desc_en": "Ashley feels comfortable around you.",
     "desc_es": "Ashley se siente c\u00f3moda contigo."},
    {"id": "heartstrings", "icon": "\U0001f497", "tier": "affection",
     "name_en": "Heartstrings", "name_es": "Cuerdas del coraz\u00f3n",
     "desc_en": "You made Ashley's heart skip a beat.",
     "desc_es": "Hiciste que el coraz\u00f3n de Ashley se saltara un latido."},
    {"id": "devoted", "icon": "\U0001f49d", "tier": "affection",
     "name_en": "Devoted", "name_es": "Devota",
     "desc_en": "Ashley can't imagine life without you.",
     "desc_es": "Ashley no puede imaginar la vida sin ti."},
    # Message milestones
    {"id": "hello_world", "icon": "\U0001f44b", "tier": "messages",
     "name_en": "Hello World", "name_es": "Hola mundo",
     "desc_en": "Your first words to Ashley.",
     "desc_es": "Tus primeras palabras para Ashley."},
    {"id": "chatty", "icon": "\U0001f4ac", "tier": "messages",
     "name_en": "Chatty", "name_es": "Hablador",
     "desc_en": "50 messages and counting!",
     "desc_es": "\u00a150 mensajes y contando!"},
    {"id": "best_friends", "icon": "\u2b50", "tier": "messages",
     "name_en": "Best Friends", "name_es": "Mejores amigos",
     "desc_en": "200 conversations. She knows you well.",
     "desc_es": "200 conversaciones. Te conoce bien."},
    {"id": "inseparable", "icon": "\U0001f451", "tier": "messages",
     "name_en": "Inseparable", "name_es": "Inseparables",
     "desc_en": "500 messages. You two are a team.",
     "desc_es": "500 mensajes. Sois un equipo."},
    # Feature discovery
    {"id": "voice_unlocked", "icon": "\U0001f3a4", "tier": "features",
     "name_en": "Voice Unlocked", "name_es": "Voz desbloqueada",
     "desc_en": "Ashley heard your voice for the first time.",
     "desc_es": "Ashley escuch\u00f3 tu voz por primera vez."},
    {"id": "she_acts", "icon": "\u26a1", "tier": "features",
     "name_en": "She Acts", "name_es": "Ella act\u00faa",
     "desc_en": "Ashley did something on your PC.",
     "desc_es": "Ashley hizo algo en tu PC."},
    {"id": "she_remembers", "icon": "\U0001f9e0", "tier": "features",
     "name_en": "She Remembers", "name_es": "Ella recuerda",
     "desc_en": "Ashley knows 5 things about you.",
     "desc_es": "Ashley sabe 5 cosas de ti."},
    {"id": "she_sees", "icon": "\U0001f441", "tier": "features",
     "name_en": "She Sees", "name_es": "Ella ve",
     "desc_en": "Ashley can see your screen now.",
     "desc_es": "Ashley puede ver tu pantalla ahora."},
]

# Quick lookup by id
_ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


# ─────────────────────────────────────────────
#  Persistence
# ─────────────────────────────────────────────

def load_achievements() -> dict:
    """Returns dict of achievement_id -> {"unlocked": bool, "unlocked_at": str|None}."""
    try:
        if os.path.exists(ACHIEVEMENTS_FILE):
            with open(ACHIEVEMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_achievements(data: dict):
    """Persist achievements dict to disk."""
    try:
        parent = os.path.dirname(ACHIEVEMENTS_FILE)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(ACHIEVEMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def unlock_achievement(achievement_id: str) -> bool:
    """Unlock an achievement. Returns True if it was NEWLY unlocked (not already)."""
    data = load_achievements()
    if achievement_id in data and data[achievement_id].get("unlocked"):
        return False  # already unlocked
    data[achievement_id] = {
        "unlocked": True,
        "unlocked_at": datetime.now().isoformat(),
    }
    save_achievements(data)
    return True  # newly unlocked!


def is_unlocked(achievement_id: str) -> bool:
    """Check if a specific achievement is unlocked."""
    data = load_achievements()
    return data.get(achievement_id, {}).get("unlocked", False)


def get_achievement_def(achievement_id: str) -> dict | None:
    """Get the static definition of an achievement by id."""
    return _ACHIEVEMENTS_BY_ID.get(achievement_id)


# ─────────────────────────────────────────────
#  Check all conditions
# ─────────────────────────────────────────────

def check_achievements(
    affection: int,
    message_count: int,
    facts_count: int,
    vision_enabled: bool,
    used_mic: bool = False,
    executed_action: bool = False,
) -> list[dict]:
    """Check all achievement conditions and return list of NEWLY unlocked defs."""
    newly_unlocked = []

    # Affection milestones
    if affection >= 20 and unlock_achievement("ice_breaker"):
        newly_unlocked.append(get_achievement_def("ice_breaker"))
    if affection >= 40 and unlock_achievement("getting_closer"):
        newly_unlocked.append(get_achievement_def("getting_closer"))
    if affection >= 60 and unlock_achievement("heartstrings"):
        newly_unlocked.append(get_achievement_def("heartstrings"))
    if affection >= 80 and unlock_achievement("devoted"):
        newly_unlocked.append(get_achievement_def("devoted"))

    # Message milestones
    if message_count >= 1 and unlock_achievement("hello_world"):
        newly_unlocked.append(get_achievement_def("hello_world"))
    if message_count >= 50 and unlock_achievement("chatty"):
        newly_unlocked.append(get_achievement_def("chatty"))
    if message_count >= 200 and unlock_achievement("best_friends"):
        newly_unlocked.append(get_achievement_def("best_friends"))
    if message_count >= 500 and unlock_achievement("inseparable"):
        newly_unlocked.append(get_achievement_def("inseparable"))

    # Feature discovery
    if used_mic and unlock_achievement("voice_unlocked"):
        newly_unlocked.append(get_achievement_def("voice_unlocked"))
    if executed_action and unlock_achievement("she_acts"):
        newly_unlocked.append(get_achievement_def("she_acts"))
    if facts_count >= 5 and unlock_achievement("she_remembers"):
        newly_unlocked.append(get_achievement_def("she_remembers"))
    if vision_enabled and unlock_achievement("she_sees"):
        newly_unlocked.append(get_achievement_def("she_sees"))

    return newly_unlocked
