from dotenv import load_dotenv
import os

load_dotenv()
XAI_API_KEY = os.getenv("XAI_API_KEY")

# ─────────────────────────────────────────────
#  Modelo
# ─────────────────────────────────────────────

# grok-4-1-fast-reasoning: modelo principal de Ashley. 2M contexto,
# $0.20/$0.50 per 1M, reasoning antes de generar → mejor matiz en
# respuestas complejas.
# OJO: la familia grok-4-1-fast (reasoning o non-reasoning) NO soporta
# frequency_penalty ni presence_penalty. La variante non-reasoning NO
# aporta nada aquí: mismo problema con penalties + peor en reasoning.
# Si en el futuro queremos penalties de forma nativa en el chat principal,
# hay que cambiar a la familia grok-3 (grok-3-fast soporta penalties).
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
MENTAL_STATE_FILE = _data_path("mental_state_ashley.json")
NEWS_FILE = _data_path("news_ashley.json")
ACTION_LOG_FILE = _data_path("actions_log_ashley.json")

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

# v0.16 — paleta wine/sepia cálida (rediseño tipo "cinema noir boutique")
# Antes: rosa neón #ff9aee + negro azulado.
# Ahora: ámbar/dorado cálido + vino burgundy + crema. Aesthetic más
# elegante, mature, "candle-lit room" en lugar de "discoteca cyberpunk".
# La transición la dispara el cambio del valor de COLOR_PRIMARY que
# se propaga vía rx.var → CSS, junto con override de body/glass en
# styles.py.
COLOR_PRIMARY = "#d4a373"          # ámbar dorado (acento principal)
COLOR_PRIMARY_HOVER = "#e6b887"    # ámbar más claro
COLOR_BG_APP = "#1a0a10"           # vino profundo (fondo base)
COLOR_BG_CHAT = "#231119"          # vino chat panel
COLOR_BG_MSG_ASHLEY = "#2d1822"    # ashley bubble vino
COLOR_BG_MSG_USER = "#3a2330"      # user bubble (vino más claro/marrón)
COLOR_BG_INPUT = "#1f0e15"         # input bg
COLOR_BG_FACT_BADGE = "#2a1419"    # fact badges
COLOR_TEXT_MUTED = "#9c8b7e"       # crema apagado
COLOR_TEXT_DIM = "#c4b3a4"         # crema medio
COLOR_TEXT_FACT = "#e8dcc4"        # crema texto principal
COLOR_STATUS_ONLINE = "#c8a47d"    # online ámbar suave
COLOR_STATUS_WRITING = "#e6b887"   # escribiendo ámbar más vivo
COLOR_BUTTON_OFF = "#3a2630"       # botón apagado
COLOR_BUTTON_OFF_TEXT = "#9c8b7e"

# ─────────────────────────────────────────────
#  Sombras (todas en tonos cálidos)
# ─────────────────────────────────────────────

SHADOW_ASHLEY = "0 4px 18px rgba(212,163,115,0.14)"
SHADOW_USER = "0 4px 18px rgba(196,127,90,0.10)"
SHADOW_BUTTON = "0 4px 18px rgba(212,163,115,0.35)"
SHADOW_AVATAR = "0 0 35px rgba(212,163,115,0.40)"

# ─────────────────────────────────────────────
#  Dimensiones UI
# ─────────────────────────────────────────────

AVATAR_SIZE = "170px"
CHAT_WIDTH = "880px"
DIALOG_WIDTH = "900px"
CHAT_HEIGHT = "58vh"
MEMORY_HEIGHT = "60vh"

# v0.15 — layout 3-columnas estilo c.ai
# Sidebar izquierdo: navegación principal (memorias, noticias, acciones,
#   toggles secundarios, idioma, ajustes, manual). Reemplaza los pills
#   horizontales del header. Ancho fijo — colapsable a iconos en
#   pantallas <1280px vía CSS @media (no implementado aún).
# Panel derecho: tarjeta de Ashley arriba (avatar + nombre + status +
#   afecto) y un área grande reservada para el modelo 3D que llegará
#   en una versión posterior. Por ahora el área 3D contiene un
#   placeholder con label.
SIDEBAR_LEFT_WIDTH = "240px"
# v0.15.2 — panel derecho ensanchado para que el área de Ashley 2D
# (mood-image que cambia con el chat) sea protagonista. Antes 360px
# era cómodo solo para el placeholder 3D; con el 2D real necesita
# más presencia visual.
PANEL_RIGHT_WIDTH = "460px"
MODEL_3D_HEIGHT = "560px"
