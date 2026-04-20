from dotenv import load_dotenv
import os

load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")

# ─────────────────────────────────────────────
#  Modelo
# ─────────────────────────────────────────────

GROK_MODEL = "grok-4-1-fast-reasoning"

# ─────────────────────────────────────────────
#  Archivos de datos
# ─────────────────────────────────────────────
# En modo dev: rutas relativas (../filename.json) — comportamiento de siempre.
# En modo prod (Electron con ASHLEY_DATA_DIR definido): %APPDATA%\Ashley\data\
# El modo se decide en runtime leyendo la env var que pasa Electron.

def _data_path(filename: str) -> str:
    env_dir = os.getenv("ASHLEY_DATA_DIR")
    if env_dir:
        try:
            os.makedirs(env_dir, exist_ok=True)
        except Exception as e:
            # Si esto falla, todos los writes siguientes van a fallar.
            # Logueamos para que quede traza en soporte (antes era silencioso).
            import logging
            logging.getLogger("ashley.config").warning(
                "could not create data dir %s: %s", env_dir, e,
            )
        return os.path.join(env_dir, filename)
    return f"../{filename}"

CHAT_FILE = _data_path("historial_ashley.json")
FACTS_FILE = _data_path("hechos_ashley.json")
DIARY_FILE = _data_path("diario_ashley.json")
REMINDERS_FILE = _data_path("recordatorios_ashley.json")
IMPORTANT_FILE = _data_path("importantes_ashley.json")
TASTES_FILE = _data_path("gustos_ashley.json")
DISCOVERY_FILE = _data_path("discovery_ashley.json")
AFFECTION_FILE = _data_path("affection_ashley.json")
LICENSE_FILE = _data_path("license.json")
STATS_FILE = _data_path("stats_ashley.json")

# ─────────────────────────────────────────────
#  Licencia (Lemon Squeezy)
# ─────────────────────────────────────────────
# Mientras LICENSE_CHECK_ENABLED=False el gate está completamente desactivado
# y Ashley arranca sin pedir key. Lo ponemos en True el día del launch.
# Los IDs son los de nuestro producto en LS (store "Ashley IA").

LICENSE_CHECK_ENABLED = False
LEMONSQUEEZY_STORE_ID = 348957
LEMONSQUEEZY_PRODUCT_ID = 984701

# ─────────────────────────────────────────────
#  Memoria y comportamiento
# ─────────────────────────────────────────────

MAX_HISTORY_MESSAGES = 50
MAX_FACTS = 300
MESSAGES_PER_EXTRACTION = 40
SESSION_TIMEOUT_MINUTES = 30
STREAM_CHUNK_SIZE = 5

# ─────────────────────────────────────────────
#  Colores
# ─────────────────────────────────────────────

COLOR_PRIMARY = "#ff9aee"
COLOR_PRIMARY_HOVER = "#ffb8f5"
COLOR_BG_APP = "#0a0a0a"
COLOR_BG_CHAT = "#0f0f0f"
COLOR_BG_MSG_ASHLEY = "#3a1f4d"
COLOR_BG_MSG_USER = "#1f2a44"
COLOR_BG_INPUT = "#1a1a1a"
COLOR_BG_FACT_BADGE = "#2a0f3d"
COLOR_TEXT_MUTED = "#bbbbbb"
COLOR_TEXT_DIM = "#cccccc"
COLOR_TEXT_FACT = "#dddddd"
COLOR_STATUS_ONLINE = "#88ff99"
COLOR_STATUS_WRITING = "#ffcc88"
COLOR_BUTTON_OFF = "#333333"
COLOR_BUTTON_OFF_TEXT = "#aaaaaa"

# ─────────────────────────────────────────────
#  Sombras
# ─────────────────────────────────────────────

SHADOW_ASHLEY = "0 4px 15px rgba(255,154,238,0.15)"
SHADOW_USER = "0 4px 15px rgba(100,150,255,0.15)"
SHADOW_BUTTON = "0 4px 15px rgba(255,154,238,0.35)"
SHADOW_AVATAR = "0 0 25px rgba(255,154,238,0.4)"

# ─────────────────────────────────────────────
#  Dimensiones UI
# ─────────────────────────────────────────────

AVATAR_SIZE = "170px"
CHAT_WIDTH = "880px"
DIALOG_WIDTH = "900px"
CHAT_HEIGHT = "58vh"
MEMORY_HEIGHT = "60vh"
