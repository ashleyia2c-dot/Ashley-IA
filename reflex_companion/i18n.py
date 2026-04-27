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
SUPPORTED = ("en", "es", "fr")
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
        "pill_notifications": "Notify",
        "notif_on_tooltip":   "Background notifications ON — click to mute",
        "notif_off_tooltip":  "Background notifications OFF — click to enable",
        "pin_on_tooltip":     "Ashley stays on top of other windows — click to unpin",
        "pin_off_tooltip":    "Pin Ashley on top of other windows",

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

        # LLM Provider (new — multi-provider support)
        "settings_provider_heading": "🧠 LLM Provider",
        "settings_provider_label":  "Which service powers Ashley",
        "settings_provider_xai":    "xAI (Grok) — default, fastest setup",
        "settings_provider_openrouter": "OpenRouter — unlocks Claude, DeepSeek, GPT, Gemini...",
        "settings_provider_ollama": "Ollama — 100% free & local, runs on your PC (no API key)",
        "settings_openrouter_key_label": "OpenRouter API key",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "Get it at openrouter.ai → Settings → Keys. One key unlocks many models.",
        "settings_model_label":     "Model",
        "settings_model_hint":      "Different models have different personality, speed, and price. Pick one that fits your budget.",
        "settings_ollama_detected": "Ollama detected ✓ — pick a model you've downloaded below",
        "settings_ollama_missing":  "Ollama not detected — install it first to use this option",
        "settings_ollama_install":  "Download Ollama from ollama.com (free), then run 'ollama pull llama3.2'",
        "settings_ollama_refresh":  "🔄 Refresh local models",
        "settings_ollama_no_models": "No models found — run 'ollama pull llama3.2' in terminal first",

        # TTS Provider (new — multi-backend voice)
        "settings_tts_heading":     "🎙️ Voice Provider (TTS)",
        "settings_tts_label":       "Which engine voices Ashley",
        "settings_tts_webspeech":   "Windows voice — free, robotic but instant",
        "settings_tts_elevenlabs":  "ElevenLabs — premium, anime-quality (paid API)",
        "settings_tts_kokoro":      "Kokoro — free, local, near-ElevenLabs quality (requires local server)",
        "settings_tts_voicevox":    "VoiceVox — free, anime character voices (Japanese-focused)",
        "settings_kokoro_url_label": "Kokoro server URL",
        "settings_kokoro_url_hint": "Install Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) and run it locally.",
        "settings_kokoro_voice_label": "Kokoro voice",
        "settings_kokoro_voice_hint": "Common voices: af_bella, af_nicole, am_adam, bf_emma. See Kokoro docs.",
        "settings_voicevox_url_label": "VoiceVox Engine URL",
        "settings_voicevox_url_hint": "Install VoiceVox from voicevox.hiroshiba.jp and run the engine.",
        "settings_voicevox_speaker_label": "VoiceVox speaker ID",
        "settings_voicevox_speaker_hint": "Numeric ID (e.g. 1, 2, 3). See the VoiceVox Engine for full list.",

        # Quick menu labels (header dropdown ⚙) — cortos para no truncar
        "menu_tts":          "Voice",
        "menu_pin":          "Pin on top",
        "menu_initiative":   "Speak now",
        "menu_settings":     "Full Settings...",

        # News feed (v0.13.3) — Ashley pone aquí sus descubrimientos
        "pill_news":         "News",
        "news_tooltip_on":   "See what Ashley found for you",
        "news_title":        "📰 Ashley's discoveries",
        "news_empty":        "No discoveries yet",
        "news_empty_hint":   "Ashley will drop songs, trailers, articles and news here when she finds something that matches your tastes — without interrupting your chat.",
        "news_empty_tip_title": "How to fill this",
        "news_empty_tip_body":  "Open Settings → Proactive Discovery and turn it ON. Once Ashley knows your tastes (just chat about what you like), she'll start searching on her own.",
        # Mostrado cuando el modelo activo NO soporta web search (Ollama/OpenRouter).
        "news_unavailable_title":  "Discovery isn't available with this model",
        "news_unavailable_body":   "Web search is currently only supported with Grok (xAI). Other models work great for chat, vision and system actions, but they can't browse the web for songs, trailers or news.",
        "news_unavailable_hint":   "To enable Discovery: open Settings → AI Model and switch to Grok.",
        "news_close":        "Back to chat",
        "news_clear_all":    "Clear all",
        "news_clear_confirm": "Remove all discoveries?",
        "news_delete":       "Remove",
        "news_category_song":    "🎵 Music",
        "news_category_trailer": "🎬 Trailer",
        "news_category_article": "📰 Article",
        "news_category_game":    "🎮 Game",
        "news_category_tech":    "💻 Tech",
        "news_category_other":   "✨ Discovery",

        # Discovery toggle (v0.13)
        "settings_discovery_heading": "🔭 Proactive Discovery",
        "settings_discovery_label":   "Allow Ashley to bring up new content on her own",
        "settings_discovery_desc":    "When ON, Ashley may occasionally search the web and share trailers, songs, articles or news that match your tastes. When OFF (default), she focuses on continuing your conversation without injecting random topics. Emotional moments always disable discovery regardless of this setting.",
        "settings_discovery_on":      "ON — Ashley shares discoveries",
        "settings_discovery_off":     "OFF — Ashley sticks to our conversation",
        # Mostrado cuando el toggle está disabled porque el provider no soporta web search.
        "settings_discovery_unavailable":      "Not available with",
        "settings_discovery_unavailable_desc": "Proactive Discovery requires web search, which is currently only supported with Grok (xAI). Switch to Grok in the AI Model section above to enable this feature.",

        # Modern browser mode (CDP)
        "settings_cdp_heading": "🌐 Modern browser mode (advanced)",
        "settings_cdp_label":   "Use Chrome DevTools Protocol for tab control",
        "settings_cdp_on":      "ON — Ashley controls the browser via CDP",
        "settings_cdp_off":     "OFF — Ashley uses keyboard simulation (legacy)",
        "settings_cdp_desc":    "When ON, Ashley talks directly to the browser through localhost:9222 (no keyboard simulation, no visible tab cycling, sub-100ms). Falls back to legacy mode automatically if the browser doesn't respond. Trade-off: any local app could connect to that port — risk is low for users without active malware.",
        "settings_cdp_howto":   "Activating this toggle automatically modifies your browser's shortcuts (Chrome/Edge/Brave/Opera...) to add the required flag. Originals are backed up — turning OFF restores them exactly. After activating, close and reopen your browser for the change to take effect.",

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

        "settings_usage_heading":   "📊 Usage",
        "settings_usage_label":     "Messages sent to Ashley",
        "settings_usage_hint":      "Used to verify refund eligibility (refund available within 14 days and under 40 messages).",
        "settings_usage_tampered":  "⚠️ Integrity check failed — counter cannot be verified. Reinstall Ashley if you need this value for support.",

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

        # License gate (shown when LICENSE_CHECK_ENABLED)
        "license_title":         "Welcome to Ashley",
        "license_subtitle":      "Paste your license key to get started.",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "Activate",
        "license_activating":    "Activating...",
        "license_buy":           "I don't have a key yet",
        "license_lost_key":      "Lost my key — contact support",
        "license_error_invalid": "That license key doesn't exist or isn't valid.",
        "license_error_limit":   "You've already activated this license on the maximum number of PCs.",
        "license_error_network": "Could not reach the license server. Check your internet and try again.",
        "license_info_test":     "Test-mode license",
        "license_grace_banner":  "Offline — running on cached license. Reconnect to renew.",
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
        "pill_notifications": "Avisos",
        "notif_on_tooltip":   "Notificaciones en segundo plano ACTIVADAS — click para silenciar",
        "notif_off_tooltip":  "Notificaciones en segundo plano DESACTIVADAS — click para activar",
        "pin_on_tooltip":     "Ashley se mantiene encima de otras ventanas — click para soltar",
        "pin_off_tooltip":    "Fijar Ashley encima de otras ventanas",

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

        "settings_provider_heading": "🧠 Proveedor de IA",
        "settings_provider_label":  "Qué servicio mueve a Ashley",
        "settings_provider_xai":    "xAI (Grok) — default, setup instantáneo",
        "settings_provider_openrouter": "OpenRouter — desbloquea Claude, DeepSeek, GPT, Gemini...",
        "settings_provider_ollama": "Ollama — 100% gratis y local, corre en tu PC (sin API key)",
        "settings_openrouter_key_label": "Clave de OpenRouter",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "Sácala en openrouter.ai → Settings → Keys. Una sola clave abre muchos modelos.",
        "settings_model_label":     "Modelo",
        "settings_model_hint":      "Cada modelo tiene distinta personalidad, velocidad y precio. Elige el que te encaje.",
        "settings_ollama_detected": "Ollama detectado ✓ — elige un modelo de los que tengas bajados",
        "settings_ollama_missing":  "Ollama no detectado — instálalo primero para usar esta opción",
        "settings_ollama_install":  "Descarga Ollama en ollama.com (gratis), luego ejecuta 'ollama pull llama3.2'",
        "settings_ollama_refresh":  "🔄 Refrescar modelos locales",
        "settings_ollama_no_models": "No hay modelos — ejecuta 'ollama pull llama3.2' en la terminal",

        # TTS Provider
        "settings_tts_heading":     "🎙️ Proveedor de voz (TTS)",
        "settings_tts_label":       "Qué motor le pone voz a Ashley",
        "settings_tts_webspeech":   "Voz de Windows — gratis, robótica pero instantánea",
        "settings_tts_elevenlabs":  "ElevenLabs — premium, calidad anime (API de pago)",
        "settings_tts_kokoro":      "Kokoro — gratis, local, calidad casi-ElevenLabs (requiere servidor local)",
        "settings_tts_voicevox":    "VoiceVox — gratis, voces de personajes anime (enfocado al japonés)",
        "settings_kokoro_url_label": "URL del servidor Kokoro",
        "settings_kokoro_url_hint": "Instala Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) y lánzalo localmente.",
        "settings_kokoro_voice_label": "Voz de Kokoro",
        "settings_kokoro_voice_hint": "Voces comunes: af_bella, af_nicole, am_adam, bf_emma. Ver docs de Kokoro.",
        "settings_voicevox_url_label": "URL del motor VoiceVox",
        "settings_voicevox_url_hint": "Instala VoiceVox desde voicevox.hiroshiba.jp y arranca el motor.",
        "settings_voicevox_speaker_label": "ID del speaker VoiceVox",
        "settings_voicevox_speaker_hint": "ID numérico (p.ej. 1, 2, 3). Consulta el motor para la lista completa.",

        # Quick menu labels
        "menu_tts":          "Voz",
        "menu_pin":          "Encima",
        "menu_initiative":   "Habla tú",
        "menu_settings":     "Más ajustes...",

        # News feed
        "pill_news":         "Noticias",
        "news_tooltip_on":   "Ver lo que Ashley encontró para ti",
        "news_title":        "📰 Descubrimientos de Ashley",
        "news_empty":        "Aún no hay descubrimientos",
        "news_empty_hint":   "Ashley dejará aquí canciones, tráilers, artículos y noticias cuando encuentre algo que encaje con tus gustos — sin interrumpir el chat.",
        "news_empty_tip_title": "Cómo activarlo",
        "news_empty_tip_body":  "Abre Ajustes → Descubrimiento proactivo y actívalo. Cuando Ashley sepa tus gustos (solo charla con ella sobre lo que te gusta), empezará a buscar por su cuenta.",
        "news_unavailable_title":  "Descubrimientos no disponibles con este modelo",
        "news_unavailable_body":   "La búsqueda web solo funciona con Grok (xAI). Otros modelos funcionan perfectamente para chatear, ver imágenes y ejecutar acciones del sistema, pero no pueden buscar en internet canciones, tráilers ni noticias.",
        "news_unavailable_hint":   "Para activarlo: abre Ajustes → Modelo de IA y cambia a Grok.",
        "news_close":        "Volver al chat",
        "news_clear_all":    "Borrar todo",
        "news_clear_confirm": "¿Eliminar todos los descubrimientos?",
        "news_delete":       "Quitar",
        "news_category_song":    "🎵 Música",
        "news_category_trailer": "🎬 Tráiler",
        "news_category_article": "📰 Artículo",
        "news_category_game":    "🎮 Juego",
        "news_category_tech":    "💻 Tech",
        "news_category_other":   "✨ Descubrimiento",

        # Discovery toggle
        "settings_discovery_heading": "🔭 Descubrimiento proactivo",
        "settings_discovery_label":   "Deja que Ashley saque temas nuevos por su cuenta",
        "settings_discovery_desc":    "Cuando está ACTIVADO, Ashley puede buscar en internet y compartir tráilers, canciones, artículos o noticias según tus gustos. Cuando está DESACTIVADO (default), se centra en continuar la conversación sin meter temas random. En momentos emocionales el discovery se desactiva siempre, esté como esté este ajuste.",
        "settings_discovery_on":      "ACTIVADO — Ashley comparte descubrimientos",
        "settings_discovery_off":     "DESACTIVADO — Ashley sigue nuestra conversación",
        "settings_discovery_unavailable":      "No disponible con",
        "settings_discovery_unavailable_desc": "El descubrimiento proactivo requiere búsqueda web, que solo funciona con Grok (xAI). Cambia a Grok en la sección 'Modelo de IA' de arriba para activar esta función.",

        # Modo browser moderno (CDP)
        "settings_cdp_heading": "🌐 Modo browser moderno (avanzado)",
        "settings_cdp_label":   "Usar Chrome DevTools Protocol para controlar pestañas",
        "settings_cdp_on":      "ACTIVADO — Ashley controla el navegador vía CDP",
        "settings_cdp_off":     "DESACTIVADO — Ashley usa simulación de teclado (clásico)",
        "settings_cdp_desc":    "Cuando está ACTIVADO, Ashley se conecta directamente al navegador en localhost:9222 — sin simulación de teclas, sin pestañas cambiando visiblemente, sub-100ms. Cae automático al modo clásico si el navegador no responde. Trade-off: cualquier app local podría conectarse a ese puerto — riesgo bajo si no tienes malware activo.",
        "settings_cdp_howto":   "Al activar este toggle Ashley modifica automáticamente los accesos directos de tu navegador (Chrome/Edge/Brave/Opera...) para añadir el flag necesario. Los originales se guardan en backup — al desactivar se restauran tal cual estaban. Después de activar, cierra y reabre tu navegador para que el cambio tenga efecto.",

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

        "settings_usage_heading":   "📊 Uso",
        "settings_usage_label":     "Mensajes enviados a Ashley",
        "settings_usage_hint":      "Se usa para verificar elegibilidad de reembolso (14 días y menos de 40 mensajes).",
        "settings_usage_tampered":  "⚠️ Error de integridad — el contador no se puede verificar. Reinstala Ashley si necesitas este valor para soporte.",

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

        # License gate
        "license_title":         "Bienvenido a Ashley",
        "license_subtitle":      "Pega tu license key para empezar.",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "Activar",
        "license_activating":    "Activando...",
        "license_buy":           "No tengo key aún",
        "license_lost_key":      "Perdí mi key — contactar soporte",
        "license_error_invalid": "Esa license key no existe o no es válida.",
        "license_error_limit":   "Ya activaste esta licencia en el número máximo de PCs.",
        "license_error_network": "No pude conectar con el servidor de licencias. Revisa tu internet e inténtalo de nuevo.",
        "license_info_test":     "Licencia de prueba",
        "license_grace_banner":  "Sin conexión — usando licencia cacheada. Reconecta para renovar.",
    },
    "fr": {
        "brand_subtitle":     "Secrétaire personnelle · Geek",

        "status_thinking":    "réfléchit...",
        "status_speaking":    "parle...",
        "status_online":      "en ligne",

        "input_placeholder":  "Écris ton message...  (Entrée pour envoyer, Maj+Entrée = nouvelle ligne)",
        "btn_send":           "Envoyer",

        "pill_memories":      "Souvenirs",
        "pill_initiative":    "Ashley",
        "pill_actions":       "Actions",
        "pill_focus":         "Focus",
        "pill_natural":       "Naturel",
        "pill_notifications": "Notifs",
        "notif_on_tooltip":   "Notifications en arrière-plan ACTIVÉES — clique pour couper",
        "notif_off_tooltip":  "Notifications en arrière-plan DÉSACTIVÉES — clique pour activer",
        "pin_on_tooltip":     "Ashley reste au-dessus des autres fenêtres — clique pour libérer",
        "pin_off_tooltip":    "Épingler Ashley au-dessus des autres fenêtres",

        "mem_title":          "🧠 Mes souvenirs avec Ashley",
        "mem_tab_facts":      "✨ Faits",
        "mem_tab_diary":      "📅 Journal",
        "mem_tab_history":    "💬 Historique",
        "mem_tab_tastes":     "💝 Goûts",
        "mem_tastes_empty":   "Aucun goût enregistré pour l'instant.",
        "mem_tastes_hint":    "Dis à Ashley ce que tu aimes et elle s'en souviendra.",
        "mem_close":          "Fermer",

        "act_title":          "Ashley veut agir",
        "act_intro":          "Ashley propose de réaliser l'action suivante sur ton PC :",
        "act_question":       "Tu autorises cette action ?",
        "act_yes":            "✅ Oui, vas-y",
        "act_no":             "❌ Annuler",

        "lang_label":         "Langue",
        "lang_en":            "EN",
        "lang_es":            "ES",

        "mic_tooltip":        "Clique pour dicter à la voix",
        "tts_on_tooltip":     "Ashley parle — clique pour couper",
        "tts_off_tooltip":    "Ashley est muette — clique pour activer la voix",

        "settings_tooltip":         "Paramètres",
        "settings_title":           "Paramètres",

        "settings_required_heading":  "🔑 Obligatoire",
        "settings_optional_heading":  "✨ Optionnel — Voix premium",
        "settings_included_heading":  "🎤 Inclus — Entrée vocale",

        "settings_grok_label":      "Clé Grok (xAI)",
        "settings_grok_configured": "Configurée ✓  (gérée par l'installeur)",
        "settings_grok_missing":    "Non configurée — Ashley ne peut pas répondre tant que tu ne la mets pas.",
        "settings_grok_consequence": "Sans ça, Ashley ne peut pas penser ni te répondre.",
        "settings_grok_hint":       "Configurée pendant l'installation. Pour la changer, réinstalle Ashley.",

        "settings_provider_heading": "🧠 Fournisseur IA",
        "settings_provider_label":  "Quel service alimente Ashley",
        "settings_provider_xai":    "xAI (Grok) — défaut, setup instantané",
        "settings_provider_openrouter": "OpenRouter — débloque Claude, DeepSeek, GPT, Gemini...",
        "settings_provider_ollama": "Ollama — 100% gratuit et local, tourne sur ton PC (sans clé API)",
        "settings_openrouter_key_label": "Clé OpenRouter",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "Obtiens-la sur openrouter.ai → Settings → Keys. Une seule clé, plein de modèles.",
        "settings_model_label":     "Modèle",
        "settings_model_hint":      "Chaque modèle a sa personnalité, sa vitesse et son prix. Choisis celui qui te convient.",
        "settings_ollama_detected": "Ollama détecté ✓ — choisis un modèle que tu as déjà téléchargé",
        "settings_ollama_missing":  "Ollama non détecté — installe-le d'abord pour utiliser cette option",
        "settings_ollama_install":  "Télécharge Ollama sur ollama.com (gratuit), puis lance 'ollama pull llama3.2'",
        "settings_ollama_refresh":  "🔄 Rafraîchir les modèles locaux",
        "settings_ollama_no_models": "Aucun modèle — lance 'ollama pull llama3.2' dans le terminal",

        # TTS Provider
        "settings_tts_heading":     "🎙️ Fournisseur voix (TTS)",
        "settings_tts_label":       "Quel moteur donne sa voix à Ashley",
        "settings_tts_webspeech":   "Voix de Windows — gratuit, robotique mais instantané",
        "settings_tts_elevenlabs":  "ElevenLabs — premium, qualité anime (API payante)",
        "settings_tts_kokoro":      "Kokoro — gratuit, local, qualité quasi-ElevenLabs (serveur local requis)",
        "settings_tts_voicevox":    "VoiceVox — gratuit, voix de personnages anime (orienté japonais)",
        "settings_kokoro_url_label": "URL du serveur Kokoro",
        "settings_kokoro_url_hint": "Installe Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) et lance-le localement.",
        "settings_kokoro_voice_label": "Voix Kokoro",
        "settings_kokoro_voice_hint": "Voix courantes : af_bella, af_nicole, am_adam, bf_emma. Voir docs Kokoro.",
        "settings_voicevox_url_label": "URL du moteur VoiceVox",
        "settings_voicevox_url_hint": "Installe VoiceVox depuis voicevox.hiroshiba.jp et lance le moteur.",
        "settings_voicevox_speaker_label": "ID du speaker VoiceVox",
        "settings_voicevox_speaker_hint": "ID numérique (ex. 1, 2, 3). Voir le moteur VoiceVox pour la liste complète.",

        # Quick menu labels
        "menu_tts":          "Voix",
        "menu_pin":          "Au-dessus",
        "menu_initiative":   "Parle",
        "menu_settings":     "Plus de réglages...",

        # News feed
        "pill_news":         "Actus",
        "news_tooltip_on":   "Voir ce qu'Ashley a trouvé pour toi",
        "news_title":        "📰 Découvertes d'Ashley",
        "news_empty":        "Pas encore de découvertes",
        "news_empty_hint":   "Ashley déposera ici des chansons, bandes-annonces, articles et actus quand elle trouve quelque chose qui colle à tes goûts — sans interrompre le chat.",
        "news_empty_tip_title": "Comment l'activer",
        "news_empty_tip_body":  "Ouvre Réglages → Découverte proactive et active-le. Une fois qu'Ashley connaît tes goûts (parle-lui de ce que tu aimes), elle commencera à chercher d'elle-même.",
        "news_unavailable_title":  "Découvertes non disponibles avec ce modèle",
        "news_unavailable_body":   "La recherche web n'est disponible qu'avec Grok (xAI). Les autres modèles fonctionnent très bien pour discuter, voir des images et exécuter des actions système, mais ne peuvent pas chercher sur internet des chansons, bandes-annonces ou actus.",
        "news_unavailable_hint":   "Pour activer : ouvre Réglages → Modèle IA et passe sur Grok.",
        "news_close":        "Retour au chat",
        "news_clear_all":    "Tout effacer",
        "news_clear_confirm": "Supprimer toutes les découvertes ?",
        "news_delete":       "Supprimer",
        "news_category_song":    "🎵 Musique",
        "news_category_trailer": "🎬 Bande-annonce",
        "news_category_article": "📰 Article",
        "news_category_game":    "🎮 Jeu",
        "news_category_tech":    "💻 Tech",
        "news_category_other":   "✨ Découverte",

        # Discovery toggle
        "settings_discovery_heading": "🔭 Découverte proactive",
        "settings_discovery_label":   "Laisse Ashley apporter de nouveaux sujets d'elle-même",
        "settings_discovery_desc":    "Quand ACTIVÉ, Ashley peut chercher sur le web et partager des bandes-annonces, chansons, articles ou actus liés à tes goûts. Quand DÉSACTIVÉ (défaut), elle se concentre sur la continuité de la conversation sans injecter de sujets aléatoires. En moment émotionnel, la découverte est toujours désactivée, peu importe ce réglage.",
        "settings_discovery_on":      "ACTIVÉ — Ashley partage ses découvertes",
        "settings_discovery_off":     "DÉSACTIVÉ — Ashley reste sur notre conversation",
        "settings_discovery_unavailable":      "Non disponible avec",
        "settings_discovery_unavailable_desc": "La découverte proactive nécessite la recherche web, qui n'est disponible qu'avec Grok (xAI). Passe sur Grok dans la section 'Modèle IA' ci-dessus pour activer cette fonctionnalité.",

        # Mode navigateur moderne (CDP)
        "settings_cdp_heading": "🌐 Mode navigateur moderne (avancé)",
        "settings_cdp_label":   "Utiliser Chrome DevTools Protocol pour le contrôle des onglets",
        "settings_cdp_on":      "ACTIVÉ — Ashley contrôle le navigateur via CDP",
        "settings_cdp_off":     "DÉSACTIVÉ — Ashley utilise la simulation clavier (classique)",
        "settings_cdp_desc":    "Quand ACTIVÉ, Ashley parle directement au navigateur via localhost:9222 — pas de simulation clavier, pas d'onglets visibles qui défilent, sub-100ms. Bascule automatiquement au mode classique si le navigateur ne répond pas. Compromis : n'importe quelle app locale pourrait se connecter à ce port — risque faible sans malware actif.",
        "settings_cdp_howto":   "Activer ce toggle modifie automatiquement les raccourcis de ton navigateur (Chrome/Edge/Brave/Opera...) pour ajouter le flag requis. Les originaux sont sauvegardés — désactiver les restaure exactement. Après activation, ferme et rouvre ton navigateur pour appliquer le changement.",

        "settings_elevenlabs_label": "Clé ElevenLabs",
        "settings_elevenlabs_placeholder": "sk_... (laisse vide pour voix gratuite)",
        "settings_elevenlabs_hint": "Obtiens ta clé sur elevenlabs.io → Profile → API Keys. Stockée uniquement sur ta machine.",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "Cherche des voix sur elevenlabs.io → Voice Library et copie le Voice ID.",
        "settings_elevenlabs_without": "Sans ça :",
        "settings_elevenlabs_without_desc": "Ashley utilise la voix gratuite du système Windows (robotique mais fonctionnelle).",
        "settings_elevenlabs_with":   "Avec ça :",
        "settings_elevenlabs_with_desc":   "Voix anime premium avec de l'émotion réelle et des nuances de personnalité.",
        "settings_test_voice":      "Tester la voix",
        "settings_test_text":       "Salut. C'est Ashley, je teste la voix. Tu m'entends bien ?",

        "settings_whisper_label":   "Whisper (voix vers texte)",
        "settings_whisper_ready":   "Inclus ✓ — aucune configuration",
        "settings_whisper_desc":    "La dictée au micro marche 100% hors-ligne après la première utilisation. La première fois que tu cliques sur 🎤, un modèle de 75 Mo se télécharge (une seule fois). Ensuite, tout tourne localement — aucun coût d'API, pas besoin d'internet.",

        "settings_usage_heading":   "📊 Utilisation",
        "settings_usage_label":     "Messages envoyés à Ashley",
        "settings_usage_hint":      "Sert à vérifier l'éligibilité au remboursement (14 jours et moins de 40 messages).",
        "settings_usage_tampered":  "⚠️ Erreur d'intégrité — le compteur ne peut pas être vérifié. Réinstalle Ashley si tu as besoin de cette valeur pour le support.",

        "settings_save":            "Enregistrer",
        "settings_close":           "Fermer",

        "error_grok":         "*soupire* Quelque chose a foiré avec Grok{label} : {err}",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 Succès",
        "ach_unlocked_label":   "SUCCÈS DÉBLOQUÉ !",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "Débloqué le : {date}",

        # Affection tier messages
        "tier_up_1":    "Ashley baisse un peu sa garde...",
        "tier_up_2":    "Ashley commence à se sentir à l'aise avec toi.",
        "tier_up_3":    "Ashley se sent... bizarre. Son cœur bat plus vite.",
        "tier_up_4":    "Ashley ne peut plus cacher ce qu'elle ressent.",
        "tier_down_4":  "Ashley ne se sent plus en sécurité...",
        "tier_down_3":  "Ashley se referme un peu plus...",
        "tier_down_2":  "Ashley commence à douter de toi...",
        "tier_down_1":  "Ashley te reconnaît à peine...",

        # License gate
        "license_title":         "Bienvenue chez Ashley",
        "license_subtitle":      "Colle ta license key pour commencer.",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "Activer",
        "license_activating":    "Activation...",
        "license_buy":           "Je n'ai pas encore de key",
        "license_lost_key":      "J'ai perdu ma key — contacter le support",
        "license_error_invalid": "Cette license key n'existe pas ou n'est pas valide.",
        "license_error_limit":   "Tu as déjà activé cette licence sur le nombre maximum de PCs.",
        "license_error_network": "Impossible de joindre le serveur de licences. Vérifie ta connexion et réessaie.",
        "license_info_test":     "Licence de test",
        "license_grace_banner":  "Hors ligne — licence mise en cache. Reconnecte-toi pour renouveler.",
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
        "vol_set_invalid": "⚠️ Volume 'set' with invalid value — request was ignored",
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
        "vol_set_invalid": "⚠️ Volumen 'set' con valor inválido — petición ignorada",
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
    "fr": {
        "screenshot":     "📸 Prendre une capture plein écran",
        "open_app":       "📂 Ouvrir l'application : **{p}**",
        "play_music":     "🎵 Chercher sur YouTube : **{p}**",
        "search_web":     "🔍 Chercher sur Google : **{p}**",
        "open_url":       "🌐 Ouvrir dans le navigateur : **{p}**",
        "vol_up":         "🔊 Monter le volume système (~10%)",
        "vol_down":       "🔊 Baisser le volume système (~10%)",
        "vol_mute":       "🔊 Couper / activer le son",
        "vol_set":        "🔊 Mettre le volume à **{p}%**",
        "vol_set_invalid": "⚠️ Volume 'set' avec valeur invalide — requête ignorée",
        "type_text":      "⌨️ Écrire dans la fenêtre active :\n\n*\"{p}\"*",
        "type_in":        "⌨️ Mettre **{win}** au premier plan et écrire :\n\n*\"{p}\"*",
        "write_to_app":   "✍️ Ouvrir **{app}** et écrire :\n\n*\"{p}\"*",
        "focus_window":   "🪟 Mettre au premier plan : **{p}**",
        "hotkey":         "⌨️ Appuyer sur le raccourci : **{p}**",
        "press_key":      "⌨️ Appuyer sur la touche : **{p}**",
        "close_window":   "❌ Fermer la fenêtre / appli : **{p}**",
        "close_tab":      "🗂️ Fermer l'onglet du navigateur : **{p}**",
        "remind":         "⏰ Programmer un rappel : **{text}** pour le **{date}**",
        "add_important":  "📌 Ajouter aux importants : **{p}**",
        "done_important": "✅ Marquer comme fait : **{p}**",
        "save_taste":     "💝 Enregistrer ce goût : **[{cat}]** {val}",
        "generic":        "⚙️ {action_type} : {params}",
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
    "fr": {
        "space": "Espace", "backspace": "Retour arrière", "delete": "Suppr",
        "home": "Origine", "end": "Fin", "pageup": "Page préc.", "pagedown": "Page suiv.",
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
    "fr": {
        "part_dawn":       "petit matin",
        "part_morning":    "matin",
        "part_afternoon":  "après-midi",
        "part_evening":    "soir",
        "part_night":      "nuit",

        "datetime_line":   "Date et heure actuelles : {fecha}, {hora} ({momento}).",
        "first_talk":      "C'est la première fois que le patron parle dans cette session.",
        "active_convo":    "Le patron était là il y a moins de 2 minutes — conversation active.",
        "short_pause":     "Le patron a mis {min} minutes à répondre — petite pause.",
        "medium_away":     "Le patron a été absent {min} minutes.",
        "hours_away":      "Le patron a été absent {h}h {m}min.",
        "long_away":       "Le patron a été absent {h} heures — longue absence.",
        "slept_away":      "Le patron a été absent {h} heures. Parti à {when} (nuit/petit matin) — il a probablement dormi. Il est maintenant {momento}.",
        "very_long_away":  "Le patron a été absent {h} heures (depuis {when}). Très longue absence.",

        "due_reminders_header": "\n⏰ RAPPELS EN RETARD (le patron vient de revenir ou le moment est passé) :",
        "due_reminders_format": "  - {text} (pour : {when})",
        "due_reminders_hint":   "Mentionne ces rappels naturellement avec ta personnalité — demande au patron s'il l'a fait, s'il en a besoin, s'il veut le reprogrammer. Pas robotique, sois Ashley.",

        "days": {"Monday":"lundi","Tuesday":"mardi","Wednesday":"mercredi",
                 "Thursday":"jeudi","Friday":"vendredi","Saturday":"samedi","Sunday":"dimanche"},
        "months": {"January":"janvier","February":"février","March":"mars","April":"avril",
                   "May":"mai","June":"juin","July":"juillet","August":"août",
                   "September":"septembre","October":"octobre","November":"novembre","December":"décembre"},
        "date_format": "%A %d %B %Y",
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
    """Devuelve toda la config de voz + LLM del user.

    vision_enabled queda en archivos viejos pero se ignora (la feature se
    unificó bajo auto_actions).

    CAMPOS LLM (multi-provider, desde v0.11):
      - llm_provider: "xai" | "openrouter" | "ollama"
      - openrouter_key: API key para OpenRouter (si provider=openrouter)
      - llm_model: modelo específico a usar (vacío = default del provider)

    CAMPOS TTS (multi-backend, desde v0.12):
      - voice_provider: "webspeech" (Windows free) | "elevenlabs" (premium)
        | "kokoro" (local 100% free) | "voicevox" (anime/Japanese-focused)
      - kokoro_url: URL del Kokoro-FastAPI local (user lo arranca aparte)
      - kokoro_voice: ID de voz de Kokoro (p.ej. 'af_bella')
      - voicevox_url: URL del VoiceVox Engine local
      - voicevox_speaker: ID numérico del speaker de VoiceVox
    """
    from .memory import load_json
    default = {
        "tts_enabled": False,
        "elevenlabs_key": "",
        "openai_key": "",
        "voice_id": DEFAULT_VOICE_ID,
        "voice_mode": False,  # True = Ashley habla natural, sin *gestos*
        "notifications_enabled": True,  # default ON — diferenciador clave
        "llm_provider": "xai",
        "openrouter_key": "",
        "llm_model": "",
        # TTS multi-backend
        "voice_provider": "webspeech",
        "kokoro_url": "http://localhost:8880",
        "kokoro_voice": "af_bella",
        "voicevox_url": "http://localhost:50021",
        "voicevox_speaker": "1",  # speaker ID como string para uniformar con inputs
        # Discovery proactivo (v0.13): default OFF — al abrir la app Ashley
        # retoma el hilo de la conversación en lugar de soltar noticias
        # random. Cuando el user lo activa, Ashley vuelve a buscar cosas
        # en internet según los gustos (trailers, noticias, canciones...).
        "discovery_enabled": False,
        # Modo browser moderno (CDP, v0.13.25): default OFF. Cuando ON,
        # Ashley intenta usar el Chrome DevTools Protocol para controlar
        # el browser sin SendInput. Requiere arrancar el browser con el
        # flag --remote-debugging-port=9222.
        "cdp_enabled": False,
    }
    data = load_json(VOICE_FILE, None)
    if data is None:
        return default
    try:
        # Back-compat: si el user tenía elevenlabs_key rellena y no existe
        # voice_provider, lo inicializamos a "elevenlabs" para no romper su
        # experiencia. Si no tenía key, queda en "webspeech".
        legacy_has_eleven = bool(data.get("elevenlabs_key"))
        default_voice_provider = "elevenlabs" if legacy_has_eleven else "webspeech"
        return {
            "tts_enabled": bool(data.get("tts_enabled", False)),
            "elevenlabs_key": str(data.get("elevenlabs_key", "")),
            "openai_key": str(data.get("openai_key", "")),
            "voice_id": str(data.get("voice_id", DEFAULT_VOICE_ID)) or DEFAULT_VOICE_ID,
            "voice_mode": bool(data.get("voice_mode", False)),
            "notifications_enabled": bool(data.get("notifications_enabled", True)),
            "llm_provider": str(data.get("llm_provider", "xai")) or "xai",
            "openrouter_key": str(data.get("openrouter_key", "")),
            "llm_model": str(data.get("llm_model", "")),
            "voice_provider": str(data.get("voice_provider", default_voice_provider)) or default_voice_provider,
            "kokoro_url": str(data.get("kokoro_url", "http://localhost:8880")) or "http://localhost:8880",
            "kokoro_voice": str(data.get("kokoro_voice", "af_bella")) or "af_bella",
            "voicevox_url": str(data.get("voicevox_url", "http://localhost:50021")) or "http://localhost:50021",
            "voicevox_speaker": str(data.get("voicevox_speaker", "1")) or "1",
            "discovery_enabled": bool(data.get("discovery_enabled", False)),
            "cdp_enabled": bool(data.get("cdp_enabled", False)),
        }
    except Exception:
        return default


def save_voice_config(tts_enabled: bool, elevenlabs_key: str, voice_id: str,
                      openai_key: str = "", voice_mode: bool = False,
                      notifications_enabled: bool = True,
                      llm_provider: str = "xai",
                      openrouter_key: str = "",
                      llm_model: str = "",
                      voice_provider: str = "webspeech",
                      kokoro_url: str = "http://localhost:8880",
                      kokoro_voice: str = "af_bella",
                      voicevox_url: str = "http://localhost:50021",
                      voicevox_speaker: str = "1",
                      discovery_enabled: bool = False,
                      cdp_enabled: bool = False) -> None:
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
            "notifications_enabled": bool(notifications_enabled),
            "llm_provider": str(llm_provider or "xai"),
            "openrouter_key": str(openrouter_key or ""),
            "llm_model": str(llm_model or ""),
            "voice_provider": str(voice_provider or "webspeech"),
            "kokoro_url": str(kokoro_url or "http://localhost:8880"),
            "kokoro_voice": str(kokoro_voice or "af_bella"),
            "voicevox_url": str(voicevox_url or "http://localhost:50021"),
            "voicevox_speaker": str(voicevox_speaker or "1"),
            "discovery_enabled": bool(discovery_enabled),
            "cdp_enabled": bool(cdp_enabled),
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
