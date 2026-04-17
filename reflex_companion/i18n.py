"""
i18n.py — Sistema de traducciones de Ashley.

Cubre todo el chrome de UI, descripciones de acciones, mensajes de error,
y fragmentos del contexto de tiempo que se inyectan en el prompt de Ashley.

La personalidad de Ashley (system prompt) vive en prompts.py / prompts_en.py.
"""

import json
import os
from .config import _data_path


LANG_FILE = _data_path("language.json")
VOICE_FILE = _data_path("voice.json")
SUPPORTED = ("en", "es")
DEFAULT_LANG = "en"

DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # ElevenLabs "Sarah" — multilingüe, neutro


# ═══════════════════════════════════════════════════════════════════════════
#  UI CHROME — todas las strings visibles del UI (botones, diálogos, etc.)
# ═══════════════════════════════════════════════════════════════════════════

UI = {
    "en": {
        # Brand / avatar
        "brand_subtitle":     "Personal secretary · Geek",

        # Status labels
        "status_thinking":    "thinking...",
        "status_speaking":    "speaking...",
        "status_online":      "online",

        # Input
        "input_placeholder":  "Type your message...  (Enter to send, Shift+Enter for new line)",
        "btn_send":           "Send",

        # Header pills
        "pill_memories":      "Memories",
        "pill_initiative":    "Ashley",
        "pill_actions":       "Actions",
        "pill_focus":         "Focus",
        "pill_natural":       "Natural",
        "pill_vision":        "Vision",

        # Memories dialog
        "mem_title":          "🧠 My memories with Ashley",
        "mem_tab_facts":      "✨ Facts",
        "mem_tab_diary":      "📅 Diary",
        "mem_tab_history":    "💬 History",
        "mem_tab_tastes":     "💝 Tastes",
        "mem_tastes_empty":   "No tastes saved yet.",
        "mem_tastes_hint":    "Tell Ashley what you like and she'll remember.",
        "mem_close":          "Close",

        # Action dialog
        "act_title":          "Ashley wants to act",
        "act_intro":           "Ashley is proposing to perform this action on your PC:",
        "act_question":        "Do you authorize this action?",
        "act_yes":            "✅ Yes, do it",
        "act_no":             "❌ Cancel",

        # Language toggle
        "lang_label":         "Language",
        "lang_en":            "EN",
        "lang_es":            "ES",

        # Voice
        "mic_tooltip":        "Hold to speak / click to toggle dictation",
        "tts_on_tooltip":     "Ashley speaks — click to mute",
        "tts_off_tooltip":    "Ashley is muted — click to enable voice",

        # Settings modal — estructura: REQUIRED / OPTIONAL / INCLUDED
        "settings_tooltip":         "Settings",
        "settings_title":           "Settings",

        "settings_required_heading":  "🔑 Required",
        "settings_optional_heading":  "✨ Optional — Premium Voice",
        "settings_included_heading":  "🎤 Included — Voice Input",

        # Required (Grok)
        "settings_grok_label":      "Grok (xAI) API key",
        "settings_grok_configured": "Configured ✓  (managed by the installer)",
        "settings_grok_missing":    "Not configured — Ashley can't reply until you set it up.",
        "settings_grok_consequence": "Without this, Ashley can't think or respond to you.",
        "settings_grok_hint":       "This is set up during installation. To change it, reinstall Ashley.",

        # Optional (ElevenLabs)
        "settings_elevenlabs_label": "ElevenLabs API key",
        "settings_elevenlabs_placeholder": "sk_... (leave empty to use free voice)",
        "settings_elevenlabs_hint": "Get your key at elevenlabs.io → Profile → API Keys. Stored only on your computer.",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "Browse voices at elevenlabs.io → Voice Library and copy the Voice ID.",
        "settings_elevenlabs_without": "Without this:",
        "settings_elevenlabs_without_desc": "Ashley uses the free Windows system voice (robotic but functional).",
        "settings_elevenlabs_with":   "With this:",
        "settings_elevenlabs_with_desc":   "Anime-quality premium voice with real emotional nuance.",
        "settings_test_voice":       "Test voice",
        "settings_test_text":        "Hi there. This is Ashley testing the voice. Can you hear me?",

        # Included (Whisper local)
        "settings_whisper_label":   "Whisper (speech-to-text)",
        "settings_whisper_ready":   "Built in ✓ — no setup needed",
        "settings_whisper_desc":    "Microphone dictation works 100% offline after the first use. On first click of the 🎤 button, a one-time 75 MB model downloads. After that, everything runs locally — no API costs, no internet required.",

        "settings_save":            "Save",
        "settings_close":           "Close",

        # Error prefix injected into chat when Grok fails
        "error_grok":         "*sighs* Something went wrong with Grok{label}: {err}",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 Achievements",
        "ach_unlocked_label":   "ACHIEVEMENT UNLOCKED",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "Unlocked: {date}",

        # Affection tier messages
        "tier_up_1":    "Ashley lowers her guard, just a little...",
        "tier_up_2":    "Ashley is starting to feel comfortable with you.",
        "tier_up_3":    "Ashley feels... strange. Her heart beats faster.",
        "tier_up_4":    "Ashley can't hide what she feels anymore.",
        "tier_down_4":  "Ashley doesn't feel as safe anymore...",
        "tier_down_3":  "Ashley closes up a little more...",
        "tier_down_2":  "Ashley is starting to doubt you...",
        "tier_down_1":  "Ashley barely recognizes you...",
    },
    "es": {
        "brand_subtitle":     "Secretaria personal · Friki",

        "status_thinking":    "pensando...",
        "status_speaking":    "hablando...",
        "status_online":      "en línea",

        "input_placeholder":  "Escribe tu mensaje...  (Enter para enviar, Shift+Enter = nueva línea)",
        "btn_send":           "Enviar",

        "pill_memories":      "Recuerdos",
        "pill_initiative":    "Ashley",
        "pill_actions":       "Acciones",
        "pill_focus":         "Focus",
        "pill_natural":       "Natural",
        "pill_vision":        "Visión",

        "mem_title":          "🧠 Mis Recuerdos con Ashley",
        "mem_tab_facts":      "✨ Hechos",
        "mem_tab_diary":      "📅 Diario",
        "mem_tab_history":    "💬 Historial",
        "mem_tab_tastes":     "💝 Gustos",
        "mem_tastes_empty":   "Sin gustos guardados aún.",
        "mem_tastes_hint":    "Cuéntale a Ashley lo que te gusta y ella lo recordará.",
        "mem_close":          "Cerrar",

        "act_title":          "Ashley quiere actuar",
        "act_intro":          "Ashley propone realizar la siguiente acción en tu PC:",
        "act_question":       "¿Autorizas esta acción?",
        "act_yes":            "✅ Sí, hazlo",
        "act_no":             "❌ Cancela",

        "lang_label":         "Idioma",
        "lang_en":            "EN",
        "lang_es":            "ES",

        "mic_tooltip":        "Click para dictar por voz",
        "tts_on_tooltip":     "Ashley habla — click para silenciar",
        "tts_off_tooltip":    "Ashley silenciada — click para activar voz",

        "settings_tooltip":         "Ajustes",
        "settings_title":           "Ajustes",

        "settings_required_heading":  "🔑 Obligatorio",
        "settings_optional_heading":  "✨ Opcional — Voz premium",
        "settings_included_heading":  "🎤 Incluido — Entrada de voz",

        "settings_grok_label":      "Clave de Grok (xAI)",
        "settings_grok_configured": "Configurada ✓  (gestionada por el instalador)",
        "settings_grok_missing":    "No configurada — Ashley no puede responder hasta que la pongas.",
        "settings_grok_consequence": "Sin esto, Ashley no puede pensar ni responderte.",
        "settings_grok_hint":       "Se configura durante la instalación. Para cambiarla, reinstala Ashley.",

        "settings_elevenlabs_label": "Clave de ElevenLabs",
        "settings_elevenlabs_placeholder": "sk_... (déjalo vacío para voz gratuita)",
        "settings_elevenlabs_hint": "Consigue tu clave en elevenlabs.io → Profile → API Keys. Se guarda solo en tu equipo.",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "Busca voces en elevenlabs.io → Voice Library y copia el Voice ID.",
        "settings_elevenlabs_without": "Sin esto:",
        "settings_elevenlabs_without_desc": "Ashley usa la voz gratuita del sistema Windows (robótica pero funcional).",
        "settings_elevenlabs_with":   "Con esto:",
        "settings_elevenlabs_with_desc":   "Voz anime premium con emoción real y matices de personalidad.",
        "settings_test_voice":      "Probar voz",
        "settings_test_text":       "Hola. Soy Ashley probando la voz. ¿Me oyes bien?",

        "settings_whisper_label":   "Whisper (voz a texto)",
        "settings_whisper_ready":   "Incluido ✓ — sin configuración",
        "settings_whisper_desc":    "El dictado por micrófono funciona 100% offline tras el primer uso. La primera vez que pulses 🎤 se descarga un modelo de 75 MB (una sola vez). Después, todo corre localmente — sin costes de API, sin necesidad de internet.",

        "settings_save":            "Guardar",
        "settings_close":           "Cerrar",

        "error_grok":         "*suspira* Algo falló con Grok{label}: {err}",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 Logros",
        "ach_unlocked_label":   "\u00a1LOGRO DESBLOQUEADO!",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "Desbloqueado: {date}",

        # Affection tier messages
        "tier_up_1":    "Ashley baja un poco la guardia...",
        "tier_up_2":    "Ashley empieza a sentirse cómoda contigo.",
        "tier_up_3":    "Ashley se siente... extraña. El corazón le late más rápido.",
        "tier_up_4":    "Ashley ya no puede esconder lo que siente.",
        "tier_down_4":  "Ashley ya no se siente tan segura...",
        "tier_down_3":  "Ashley se cierra un poco más...",
        "tier_down_2":  "Ashley empieza a dudar de ti...",
        "tier_down_1":  "Ashley casi no te reconoce...",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  ACTION DESCRIPTIONS — lo que ve el usuario en el diálogo de confirmación
# ═══════════════════════════════════════════════════════════════════════════

ACT_DESC = {
    "en": {
        "screenshot":     "📸 Take a full-screen screenshot",
        "open_app":       "📂 Open the application: **{p}**",
        "play_music":     "🎵 Search on YouTube: **{p}**",
        "search_web":     "🔍 Search on Google: **{p}**",
        "open_url":       "🌐 Open in the browser: **{p}**",
        "vol_up":         "🔊 Raise system volume (~10%)",
        "vol_down":       "🔊 Lower system volume (~10%)",
        "vol_mute":       "🔊 Mute / unmute audio",
        "vol_set":        "🔊 Set volume to **{p}%**",
        "type_text":      "⌨️ Type into the active window:\n\n*\"{p}\"*",
        "type_in":        "⌨️ Focus **{win}** and type:\n\n*\"{p}\"*",
        "write_to_app":   "✍️ Open **{app}** and write:\n\n*\"{p}\"*",
        "focus_window":   "🪟 Bring to front: **{p}**",
        "hotkey":         "⌨️ Press shortcut: **{p}**",
        "press_key":      "⌨️ Press key: **{p}**",
        "close_window":   "❌ Close window / app: **{p}**",
        "close_tab":      "🗂️ Close browser tab: **{p}**",
        "remind":         "⏰ Schedule reminder: **{text}** for **{date}**",
        "add_important":  "📌 Add to important: **{p}**",
        "done_important": "✅ Mark as done: **{p}**",
        "save_taste":     "💝 Save taste: **[{cat}]** {val}",
        "generic":        "⚙️ {action_type}: {params}",
    },
    "es": {
        "screenshot":     "📸 Tomar una captura de tu pantalla completa",
        "open_app":       "📂 Abrir la aplicación: **{p}**",
        "play_music":     "🎵 Buscar en YouTube: **{p}**",
        "search_web":     "🔍 Buscar en Google: **{p}**",
        "open_url":       "🌐 Abrir en el navegador: **{p}**",
        "vol_up":         "🔊 Subir el volumen del sistema (~10%)",
        "vol_down":       "🔊 Bajar el volumen del sistema (~10%)",
        "vol_mute":       "🔊 Silenciar / activar el audio",
        "vol_set":        "🔊 Establecer el volumen al **{p}%**",
        "type_text":      "⌨️ Escribir en la ventana activa:\n\n*\"{p}\"*",
        "type_in":        "⌨️ Enfocar **{win}** y escribir:\n\n*\"{p}\"*",
        "write_to_app":   "✍️ Abrir **{app}** y escribir:\n\n*\"{p}\"*",
        "focus_window":   "🪟 Traer al frente la ventana: **{p}**",
        "hotkey":         "⌨️ Pulsar atajo de teclado: **{p}**",
        "press_key":      "⌨️ Pulsar tecla: **{p}**",
        "close_window":   "❌ Cerrar ventana / app: **{p}**",
        "close_tab":      "🗂️ Cerrar pestaña del navegador: **{p}**",
        "remind":         "⏰ Programar recordatorio: **{text}** para el **{date}**",
        "add_important":  "📌 Añadir a importantes: **{p}**",
        "done_important": "✅ Marcar como hecho: **{p}**",
        "save_taste":     "💝 Guardar gusto: **[{cat}]** {val}",
        "generic":        "⚙️ {action_type}: {params}",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  KEY LABELS — nombres legibles de teclas
# ═══════════════════════════════════════════════════════════════════════════

KEY_LABELS = {
    "en": {
        "space": "Space", "backspace": "Backspace", "delete": "Delete",
        "home": "Home", "end": "End", "pageup": "Page Up", "pagedown": "Page Down",
    },
    "es": {
        "space": "Espacio", "backspace": "Retroceso", "delete": "Suprimir",
        "home": "Inicio", "end": "Fin", "pageup": "Re Pág", "pagedown": "Av Pág",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  TIME CONTEXT — strings que se inyectan al prompt de Ashley (su input)
#  Deben coincidir con el idioma en que Ashley está operando
# ═══════════════════════════════════════════════════════════════════════════

TIME_CTX = {
    "en": {
        "part_dawn":       "early morning",
        "part_morning":    "morning",
        "part_afternoon":  "afternoon",
        "part_evening":    "evening",
        "part_night":      "night",

        "datetime_line":   "Current date and time: {fecha}, {hora} ({momento}).",
        "first_talk":      "This is the first time the boss speaks in this session.",
        "active_convo":    "The boss was here less than 2 minutes ago — active conversation.",
        "short_pause":     "The boss took {min} minutes to respond — short pause.",
        "medium_away":     "The boss was away for {min} minutes.",
        "hours_away":      "The boss was away for {h}h {m}min.",
        "long_away":       "The boss was away for {h} hours — long absence.",
        "slept_away":      "The boss was away for {h} hours. Left at {when} (night/early morning) — probably went to sleep. It's now {momento}.",
        "very_long_away":  "The boss was away for {h} hours (since {when}). Very long absence.",

        "due_reminders_header": "\n⏰ DUE REMINDERS (boss just came back or the time has passed):",
        "due_reminders_format": "  - {text} (was due: {when})",
        "due_reminders_hint":   "Mention these reminders naturally with your personality — ask the boss if he did it, if he needs it, if he wants to reschedule. Don't be robotic, be Ashley.",

        "days": {"Monday":"Monday","Tuesday":"Tuesday","Wednesday":"Wednesday",
                 "Thursday":"Thursday","Friday":"Friday","Saturday":"Saturday","Sunday":"Sunday"},
        "months": {"January":"January","February":"February","March":"March","April":"April",
                   "May":"May","June":"June","July":"July","August":"August",
                   "September":"September","October":"October","November":"November","December":"December"},
        "date_format": "%A, %B %d, %Y",
    },
    "es": {
        "part_dawn":       "madrugada",
        "part_morning":    "mañana",
        "part_afternoon":  "tarde",
        "part_evening":    "tarde-noche",
        "part_night":      "noche",

        "datetime_line":   "Fecha y hora actual: {fecha}, {hora} ({momento}).",
        "first_talk":      "Es la primera vez que el jefe habla en esta sesión.",
        "active_convo":    "El jefe estaba aquí hace menos de 2 minutos — conversación activa.",
        "short_pause":     "El jefe tardó {min} minutos en responder — pausa corta.",
        "medium_away":     "El jefe estuvo {min} minutos ausente.",
        "hours_away":      "El jefe estuvo {h}h {m}min ausente.",
        "long_away":       "El jefe estuvo {h} horas ausente — ausencia larga.",
        "slept_away":      "El jefe estuvo {h} horas ausente. Se fue a las {when} (noche/madrugada) — probablemente fue a dormir. Ahora es {momento}.",
        "very_long_away":  "El jefe estuvo {h} horas ausente (desde las {when}). Ausencia muy larga.",

        "due_reminders_header": "\n⏰ RECORDATORIOS VENCIDOS (el jefe acaba de volver o el tiempo llegó):",
        "due_reminders_format": "  - {text} (era para: {when})",
        "due_reminders_hint":   "Menciona estos recordatorios de forma natural con tu personalidad — pregunta al jefe si ya lo hizo, si lo necesita, si quiere reprogramarlo. No seas robótica, sé Ashley.",

        "days": {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles",
                 "Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"},
        "months": {"January":"enero","February":"febrero","March":"marzo","April":"abril",
                   "May":"mayo","June":"junio","July":"julio","August":"agosto",
                   "September":"septiembre","October":"octubre","November":"noviembre","December":"diciembre"},
        "date_format": "%A, %d de %B de %Y",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    l = lang.strip().lower()[:2]
    return l if l in SUPPORTED else DEFAULT_LANG


def load_language() -> str:
    """Carga el idioma persistido. Si el archivo está corrupto, loguea un
    warning y cae al default — así podemos rastrearlo en soporte en vez
    de ver a un user con idioma "incorrecto" sin saber por qué."""
    from .memory import load_json
    data = load_json(LANG_FILE, None)
    if data is None:
        return DEFAULT_LANG
    try:
        return normalize_lang(data.get("language"))
    except Exception as e:
        import logging
        logging.getLogger("ashley.i18n").warning(
            "load_language: invalid language.json (%s), using default", e,
        )
        return DEFAULT_LANG


def save_language(lang: str) -> None:
    """Persist selected language atomically via memory.save_json."""
    from .memory import save_json
    try:
        save_json(LANG_FILE, {"language": normalize_lang(lang)})
    except Exception as e:
        import logging
        logging.getLogger("ashley.i18n").warning("save_language failed: %s", e)


def load_voice_config() -> dict:
    """Devuelve tts_enabled, elevenlabs_key, openai_key, voice_id, voice_mode, vision_enabled."""
    from .memory import load_json
    default = {
        "tts_enabled": False,
        "elevenlabs_key": "",
        "openai_key": "",
        "voice_id": DEFAULT_VOICE_ID,
        "voice_mode": False,  # True = Ashley habla natural, sin *gestos*
        "vision_enabled": False,
    }
    data = load_json(VOICE_FILE, None)
    if data is None:
        return default
    try:
        return {
            "tts_enabled": bool(data.get("tts_enabled", False)),
            "elevenlabs_key": str(data.get("elevenlabs_key", "")),
            "openai_key": str(data.get("openai_key", "")),
            "voice_id": str(data.get("voice_id", DEFAULT_VOICE_ID)) or DEFAULT_VOICE_ID,
            "voice_mode": bool(data.get("voice_mode", False)),
            "vision_enabled": bool(data.get("vision_enabled", False)),
        }
    except Exception:
        return default


def save_voice_config(tts_enabled: bool, elevenlabs_key: str, voice_id: str,
                      openai_key: str = "", voice_mode: bool = False,
                      vision_enabled: bool = False) -> None:
    """Persist voice config atomically. El archivo contiene la API key de
    ElevenLabs del user — un write corrupto perdería su config de voz
    entera. Con save_json atómico + .bak, nunca pasa."""
    from .memory import save_json
    try:
        save_json(VOICE_FILE, {
            "tts_enabled": bool(tts_enabled),
            "elevenlabs_key": str(elevenlabs_key or ""),
            "openai_key": str(openai_key or ""),
            "voice_id": str(voice_id or DEFAULT_VOICE_ID),
            "voice_mode": bool(voice_mode),
            "vision_enabled": bool(vision_enabled),
        })
    except Exception as e:
        import logging
        logging.getLogger("ashley.i18n").warning("save_voice_config failed: %s", e)


def ui(lang: str) -> dict[str, str]:
    return UI.get(normalize_lang(lang), UI[DEFAULT_LANG])


def act_desc(lang: str) -> dict[str, str]:
    return ACT_DESC.get(normalize_lang(lang), ACT_DESC[DEFAULT_LANG])


def key_labels(lang: str) -> dict[str, str]:
    return KEY_LABELS.get(normalize_lang(lang), KEY_LABELS[DEFAULT_LANG])


def time_ctx(lang: str) -> dict:
    return TIME_CTX.get(normalize_lang(lang), TIME_CTX[DEFAULT_LANG])
