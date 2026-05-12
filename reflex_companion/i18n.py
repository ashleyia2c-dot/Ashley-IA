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
SUPPORTED = ("en", "es", "fr", "ja", "de", "ru", "ko")
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

        # v0.19.20 — Settings dynamic status messages (CDP toggle + wake word)
        "cdp_setup_in_progress":     "Configuring browser shortcuts...",
        "cdp_setup_in_progress_off": "Restoring browser shortcuts to original state...",
        # v0.19.31 — CDP wizard result messages (estaban hardcoded en ES)
        "cdp_result_modified":        "✓ {n} shortcut(s) modified. Close and reopen your browser to apply the change.",
        "cdp_result_no_shortcuts":    "⚠ No Chromium browser shortcuts found on your PC. Activate the flag manually.",
        "cdp_result_already_active":  "✓ All {n} shortcuts already had the flag active.",
        "cdp_result_restored":        "✓ {n} shortcut(s) restored to original state.",
        "cdp_result_classic_mode":    "✓ Classic mode activated.",
        "cdp_result_failed_suffix":   " ({n} failed)",
        "cdp_result_error":           "Error in wizard: {err}",
        "wake_word_listening":       "OK listening",

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
        "mem_clear_all":      "Clear all memories",
        "mem_clear_all_confirm_title": "Clear ALL memories?",
        "mem_clear_all_confirm_body": "This will permanently delete every fact Ashley has stored about you. The chat history is NOT touched — Ashley may rebuild some facts as you keep talking. Use this if her memories drift in a direction you don't like.",
        "mem_clear_all_confirm_ok": "Yes, clear them all",
        "cancel":             "Cancel",

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
        # v0.16.14 — voice speed slider
        "settings_voice_speed_label": "Voice speed",
        "settings_voice_speed_hint": "How fast Ashley talks. 1.0 = normal, 1.5 = clearly faster, 0.75 = slower. Applied natively when the provider supports it (ElevenLabs Turbo v2.5, Kokoro, VoiceVox); falls back to browser playback rate.",

        # Quick menu labels (header dropdown ⚙) — cortos para no truncar
        "menu_tts":          "Voice",
        "menu_pin":          "Pin on top",
        "menu_initiative":   "Speak now",
        "menu_settings":     "Full Settings...",

        # Mobile pair (v0.18.2) — botón "Conectar móvil" en la nav superior
        "pill_mobile_pair":      "Mobile",
        "mobile_pair_title":     "Connect your mobile",
        "mobile_pair_subtitle":  "Open Ashley Mobile on your phone and scan this QR.",
        "mobile_pair_loading":   "Loading...",
        "mobile_pair_manual":    "Or enter manually:",
        "mobile_pair_server":    "Server",
        "mobile_pair_token":     "Token",
        "mobile_pair_copy":      "Copy",
        "mobile_pair_copied":    "Copied",
        "mobile_pair_regen":     "Regenerate token",
        "mobile_pair_regen_warn": "Regenerating invalidates any paired phones. They'll have to scan again.",
        "mobile_pair_close":     "Close",
        "mobile_pair_help":      "No mobile yet? Download Ashley Mobile (.apk) from your purchase email.",
        "mobile_pair_security_warning": "⚠️ Don't share this QR. Anyone who scans it gets full access to your conversations with Ashley.",
        "mobile_pair_generic_error": "Could not load mobile pairing info — try again in a moment.",

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
        "settings_cdp_howto":   "Activating this toggle automatically modifies your browser's shortcuts (Chrome/Edge/Brave/Opera...) to add the required flag. Originals are backed up — turning OFF restores them exactly. After activating, close and reopen your browser for the change to take effect. ⚠ If you usually open your browser from a taskbar pin, open it from the Start Menu or Desktop instead — taskbar pins on Windows 10/11 may bypass the wizard.",

        # Wake word (always-on listening, opt-in)
        "settings_wakeword_heading": "🎙 Wake word (always-on listening)",
        "settings_wakeword_label":   "Listen for 'Ashley' continuously",
        "settings_wakeword_on":      "ON — say 'Ashley' to talk hands-free",
        "settings_wakeword_off":     "OFF — press the mic button to talk",
        "settings_wakeword_desc":    "When ON, Ashley keeps the mic open in the background and triggers recording when she hears her name. The detection model is local (~5 MB), runs on CPU, and audio NEVER leaves your computer until you speak the wake word. False activations are tuned to be <1 per hour with TV/music in the background.",
        "settings_wakeword_howto":   "Say 'Ashley' clearly near the mic. After the chime, speak your message normally. The detector pauses automatically while you're typing or holding the mic button, and resumes afterwards.",
        "settings_wakeword_no_model": "Wake word model not installed yet. The training pipeline lives in wake_word_training/ — once trained (~3-4 h on a CUDA GPU), copy the .onnx to reflex_companion/wake_word/ashley.onnx.",
        "settings_wakeword_no_deps":  "Wake word dependencies missing. Run: pip install openwakeword sounddevice",

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

        # Legal & Data section (v0.19.23 — fix hardcoded EN strings)
        "settings_legal_heading":   "⚖ Legal & Data",
        "settings_privacy_btn":     "Privacy Policy",
        "settings_terms_btn":       "Terms of Service",
        "settings_backup_desc":     "Backup all your data (chat history, facts, diary, achievements, preferences) as a ZIP file. Useful before reinstalling, migrating to another PC, or simply for peace of mind.",
        "settings_export_btn":      "Export all my data (.zip)",

        "settings_save":            "Save",
        "settings_close":           "Close",

        # Error prefix injected into chat when Grok fails
        "error_grok":         "*sighs* Something went wrong with Grok{label}: {err}",
        # Image upload too big (>10 MB)
        "upload_too_big":     "*winces* That image is too big ({size_mb:.1f} MB). Max is 10 MB so I can actually look at it.",

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

        "cdp_setup_in_progress":     "Configurando accesos directos del navegador...",
        "cdp_setup_in_progress_off": "Restaurando accesos directos al estado original...",
        # v0.19.31 — CDP wizard result messages
        "cdp_result_modified":        "✓ {n} acceso(s) directo(s) modificados. Cierra y reabre tu navegador para aplicar el cambio.",
        "cdp_result_no_shortcuts":    "⚠ No encontré accesos directos de navegadores Chromium en tu PC. Activa el flag manualmente.",
        "cdp_result_already_active":  "✓ Los {n} accesos directos ya tenían el flag activo.",
        "cdp_result_restored":        "✓ {n} acceso(s) directo(s) restaurados al estado original.",
        "cdp_result_classic_mode":    "✓ Modo clásico activado.",
        "cdp_result_failed_suffix":   " ({n} fallaron)",
        "cdp_result_error":           "Error en el wizard: {err}",
        "wake_word_listening":       "OK escuchando",

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
        "mem_clear_all":      "Borrar todas las memorias",
        "mem_clear_all_confirm_title": "¿Borrar TODAS las memorias?",
        "mem_clear_all_confirm_body": "Esto borra permanentemente cada cosa que Ashley ha guardado sobre ti. El chat NO se toca — Ashley puede reconstruir algunos hechos según sigas hablando con ella. Úsalo si sus recuerdos se han desviado en una dirección que no te gusta.",
        "mem_clear_all_confirm_ok": "Sí, borrar todo",
        "cancel":             "Cancelar",

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
        # v0.16.14 — slider velocidad de voz
        "settings_voice_speed_label": "Velocidad de la voz",
        "settings_voice_speed_hint": "Cuán rápido habla Ashley. 1.0 = normal, 1.5 = claramente más rápido, 0.75 = más lento. Aplicado nativamente cuando el provider lo soporta (ElevenLabs Turbo v2.5, Kokoro, VoiceVox); fallback al playbackRate del navegador.",

        # Quick menu labels
        "menu_tts":          "Voz",
        "menu_pin":          "Encima",
        "menu_initiative":   "Habla tú",
        "menu_settings":     "Más ajustes...",

        # Mobile pair (v0.18.2)
        "pill_mobile_pair":      "Móvil",
        "mobile_pair_title":     "Conectar tu móvil",
        "mobile_pair_subtitle":  "Abre Ashley Mobile en tu teléfono y escanea este QR.",
        "mobile_pair_loading":   "Cargando...",
        "mobile_pair_manual":    "O introduce manualmente:",
        "mobile_pair_server":    "Servidor",
        "mobile_pair_token":     "Token",
        "mobile_pair_copy":      "Copiar",
        "mobile_pair_copied":    "Copiado",
        "mobile_pair_regen":     "Regenerar token",
        "mobile_pair_regen_warn": "Regenerar invalida los móviles ya pareados. Tendrán que escanear de nuevo.",
        "mobile_pair_close":     "Cerrar",
        "mobile_pair_help":      "¿Aún sin móvil? Descarga Ashley Mobile (.apk) del correo de tu compra.",
        "mobile_pair_security_warning": "⚠️ No compartas este QR. Quien lo escanee tiene acceso total a tus conversaciones con Ashley.",
        "mobile_pair_generic_error": "No pude cargar la info de emparejamiento — vuelve a intentarlo en un momento.",

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
        "settings_cdp_howto":   "Al activar este toggle Ashley modifica automáticamente los accesos directos de tu navegador (Chrome/Edge/Brave/Opera...) para añadir el flag necesario. Los originales se guardan en backup — al desactivar se restauran tal cual estaban. Después de activar, cierra y reabre tu navegador para que el cambio tenga efecto. ⚠ Si normalmente abres el navegador desde un pin de la barra de tareas, ábrelo desde el Menú Inicio o el Escritorio — los pins del taskbar en Windows 10/11 pueden saltarse el wizard.",

        # Wake word (escucha siempre, opt-in)
        "settings_wakeword_heading": "🎙 Palabra clave (escucha siempre)",
        "settings_wakeword_label":   "Escuchar 'Ashley' continuamente",
        "settings_wakeword_on":      "ACTIVADO — di 'Ashley' para hablar sin tocar nada",
        "settings_wakeword_off":     "DESACTIVADO — pulsa el botón del mic para hablar",
        "settings_wakeword_desc":    "Cuando está ACTIVADO, Ashley mantiene el mic abierto en background y arranca la grabación cuando oye su nombre. El modelo de detección es local (~5 MB), corre en CPU, y el audio NUNCA sale de tu PC hasta que digas la palabra clave. Las activaciones falsas se ajustan a <1 por hora con TV/música de fondo.",
        "settings_wakeword_howto":   "Di 'Ashley' claro cerca del mic. Tras el sonido de aviso, di tu mensaje normal. El detector se pausa solo mientras escribes o aprietas el botón del mic, y se reanuda después.",
        "settings_wakeword_no_model": "El modelo de wake word aún no está instalado. El pipeline de entrenamiento está en wake_word_training/ — una vez entrenado (~3-4 h en GPU CUDA), copia el .onnx a reflex_companion/wake_word/ashley.onnx.",
        "settings_wakeword_no_deps":  "Faltan dependencias de wake word. Ejecuta: pip install openwakeword sounddevice",

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

        # Legal & Data section (v0.19.23)
        "settings_legal_heading":   "⚖ Legal y Datos",
        "settings_privacy_btn":     "Política de Privacidad",
        "settings_terms_btn":       "Términos de Servicio",
        "settings_backup_desc":     "Haz backup de todos tus datos (historial de chat, hechos, diario, logros, preferencias) como archivo ZIP. Útil antes de reinstalar, migrar a otro PC, o simplemente para tener tranquilidad.",
        "settings_export_btn":      "Exportar todos mis datos (.zip)",

        "settings_save":            "Guardar",
        "settings_close":           "Cerrar",

        "error_grok":         "*suspira* Algo falló con Grok{label}: {err}",
        "upload_too_big":     "*tuerce el gesto* Esa imagen es demasiado grande ({size_mb:.1f} MB). El máximo son 10 MB para que pueda verla.",

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

        "cdp_setup_in_progress":     "Configuration des raccourcis du navigateur...",
        "cdp_setup_in_progress_off": "Restauration des raccourcis à l'état original...",
        # v0.19.31 — CDP wizard result messages
        "cdp_result_modified":        "✓ {n} raccourci(s) modifié(s). Ferme et rouvre ton navigateur pour appliquer le changement.",
        "cdp_result_no_shortcuts":    "⚠ Aucun raccourci de navigateur Chromium trouvé sur ton PC. Active le flag manuellement.",
        "cdp_result_already_active":  "✓ Les {n} raccourcis avaient déjà le flag activé.",
        "cdp_result_restored":        "✓ {n} raccourci(s) restauré(s) à l'état original.",
        "cdp_result_classic_mode":    "✓ Mode classique activé.",
        "cdp_result_failed_suffix":   " ({n} échec(s))",
        "cdp_result_error":           "Erreur dans l'assistant : {err}",
        "wake_word_listening":       "OK j'écoute",

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
        "mem_clear_all":      "Effacer tous les souvenirs",
        "mem_clear_all_confirm_title": "Effacer TOUS les souvenirs ?",
        "mem_clear_all_confirm_body": "Cela supprime de façon permanente tout ce qu'Ashley a stocké sur toi. L'historique du chat n'est PAS touché — Ashley peut reconstruire certains faits en continuant de parler. Utilise ceci si ses souvenirs ont dérivé dans une direction que tu n'aimes pas.",
        "mem_clear_all_confirm_ok": "Oui, tout effacer",
        "cancel":             "Annuler",

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
        # v0.16.14 — slider vitesse de voix
        "settings_voice_speed_label": "Vitesse de la voix",
        "settings_voice_speed_hint": "À quelle vitesse Ashley parle. 1.0 = normal, 1.5 = nettement plus rapide, 0.75 = plus lent. Appliqué nativement quand le provider le supporte (ElevenLabs Turbo v2.5, Kokoro, VoiceVox); sinon fallback playbackRate navigateur.",

        # Quick menu labels
        "menu_tts":          "Voix",
        "menu_pin":          "Au-dessus",
        "menu_initiative":   "Parle",
        "menu_settings":     "Plus de réglages...",

        # Mobile pair (v0.18.2)
        "pill_mobile_pair":      "Mobile",
        "mobile_pair_title":     "Connecter ton mobile",
        "mobile_pair_subtitle":  "Ouvre Ashley Mobile sur ton téléphone et scanne ce QR.",
        "mobile_pair_loading":   "Chargement...",
        "mobile_pair_manual":    "Ou saisis manuellement :",
        "mobile_pair_server":    "Serveur",
        "mobile_pair_token":     "Jeton",
        "mobile_pair_copy":      "Copier",
        "mobile_pair_copied":    "Copié",
        "mobile_pair_regen":     "Régénérer le jeton",
        "mobile_pair_regen_warn": "Régénérer invalide les mobiles déjà appairés. Ils devront re-scanner.",
        "mobile_pair_close":     "Fermer",
        "mobile_pair_help":      "Pas encore de mobile ? Télécharge Ashley Mobile (.apk) depuis l'email d'achat.",
        "mobile_pair_security_warning": "⚠️ Ne partage pas ce QR. Quiconque le scanne accède à toutes tes conversations avec Ashley.",
        "mobile_pair_generic_error": "Impossible de charger les infos d'appairage — réessaye dans un instant.",

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
        "settings_cdp_howto":   "Activer ce toggle modifie automatiquement les raccourcis de ton navigateur (Chrome/Edge/Brave/Opera...) pour ajouter le flag requis. Les originaux sont sauvegardés — désactiver les restaure exactement. Après activation, ferme et rouvre ton navigateur pour appliquer le changement. ⚠ Si tu ouvres habituellement ton navigateur depuis une épingle de la barre des tâches, ouvre-le plutôt depuis le menu Démarrer ou le Bureau — les épingles de la barre des tâches sur Windows 10/11 peuvent contourner l'assistant.",

        # Wake word (écoute permanente, opt-in)
        "settings_wakeword_heading": "🎙 Mot de réveil (écoute permanente)",
        "settings_wakeword_label":   "Écouter 'Ashley' en continu",
        "settings_wakeword_on":      "ACTIVÉ — dis 'Ashley' pour parler sans rien toucher",
        "settings_wakeword_off":     "DÉSACTIVÉ — appuie sur le bouton du micro pour parler",
        "settings_wakeword_desc":    "Quand ACTIVÉ, Ashley garde le micro ouvert en arrière-plan et démarre l'enregistrement quand elle entend son nom. Le modèle de détection est local (~5 Mo), tourne sur CPU, et l'audio ne quitte JAMAIS ton ordinateur tant que tu n'as pas dit le mot de réveil. Les fausses activations sont calibrées à <1 par heure avec TV/musique en arrière-plan.",
        "settings_wakeword_howto":   "Dis 'Ashley' clairement près du micro. Après le bip, parle normalement. Le détecteur se met en pause automatiquement quand tu tapes ou tiens le bouton du micro, et reprend ensuite.",
        "settings_wakeword_no_model": "Le modèle de mot de réveil n'est pas encore installé. Le pipeline d'entraînement est dans wake_word_training/ — une fois entraîné (~3-4 h sur GPU CUDA), copie le .onnx dans reflex_companion/wake_word/ashley.onnx.",
        "settings_wakeword_no_deps":  "Dépendances de mot de réveil manquantes. Exécute : pip install openwakeword sounddevice",

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

        # Légal & Données (v0.19.23)
        "settings_legal_heading":   "⚖ Légal et Données",
        "settings_privacy_btn":     "Politique de confidentialité",
        "settings_terms_btn":       "Conditions d'utilisation",
        "settings_backup_desc":     "Sauvegarde toutes tes données (historique de chat, faits, journal, succès, préférences) sous forme de ZIP. Utile avant de réinstaller, migrer vers un autre PC, ou juste pour ta tranquillité d'esprit.",
        "settings_export_btn":      "Exporter toutes mes données (.zip)",

        "settings_save":            "Enregistrer",
        "settings_close":           "Fermer",

        "error_grok":         "*soupire* Quelque chose a foiré avec Grok{label} : {err}",
        "upload_too_big":     "*grimace* Cette image est trop grosse ({size_mb:.1f} Mo). Le max est 10 Mo pour que je puisse la regarder.",

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
    "ja": {
        # Brand / avatar
        "brand_subtitle":     "パーソナル秘書 · オタク",

        # Status labels
        "status_thinking":    "考え中...",
        "status_speaking":    "話している...",
        "status_online":      "オンライン",

        # v0.19.20 — Settings dynamic status messages
        "cdp_setup_in_progress":     "ブラウザのショートカットを設定中...",
        "cdp_setup_in_progress_off": "ショートカットを元の状態に復元中...",
        # v0.19.31 — CDP wizard result messages
        "cdp_result_modified":        "✓ {n}個のショートカットを変更したよ。ブラウザを閉じて再起動してね。",
        "cdp_result_no_shortcuts":    "⚠ ChromiumブラウザのショートカットがPCに見つからない。手動でフラグを有効にしてね。",
        "cdp_result_already_active":  "✓ {n}個のショートカットすべてが既に有効だったよ。",
        "cdp_result_restored":        "✓ {n}個のショートカットを元の状態に戻したよ。",
        "cdp_result_classic_mode":    "✓ クラシックモードに切り替えたよ。",
        "cdp_result_failed_suffix":   "（{n}個失敗）",
        "cdp_result_error":           "ウィザードでエラー：{err}",
        "wake_word_listening":       "聞いてる",

        # Input
        "input_placeholder":  "メッセージを入力...  (Enterで送信、Shift+Enterで改行)",
        "btn_send":           "送信",

        # Header pills
        "pill_memories":      "思い出",
        "pill_initiative":    "Ashley",
        "pill_actions":       "アクション",
        "pill_focus":         "集中",
        "pill_natural":       "ナチュラル",
        "pill_notifications": "通知",
        "notif_on_tooltip":   "バックグラウンド通知ON — クリックでミュート",
        "notif_off_tooltip":  "バックグラウンド通知OFF — クリックで有効化",
        "pin_on_tooltip":     "Ashleyは他のウィンドウの上に表示中 — クリックで解除",
        "pin_off_tooltip":    "Ashleyを他のウィンドウの上に固定",

        # Memories dialog
        "mem_title":          "🧠 Ashleyとの思い出",
        "mem_tab_facts":      "✨ 事実",
        "mem_tab_diary":      "📅 日記",
        "mem_tab_history":    "💬 履歴",
        "mem_tab_tastes":     "💝 好み",
        "mem_tastes_empty":   "保存された好みはまだありません。",
        "mem_tastes_hint":    "Ashleyにご主人の好きなものを話すと覚えてくれる。",
        "mem_close":          "閉じる",
        "mem_clear_all":      "すべての思い出を消去",
        "mem_clear_all_confirm_title": "すべての思い出を消去しますか?",
        "mem_clear_all_confirm_body": "Ashleyがご主人について保存しているすべてを永久に削除します。チャット履歴は触りません — 会話を続ければAshleyが事実を再構築する可能性があります。記憶が好ましくない方向に進んだ場合に使ってください。",
        "mem_clear_all_confirm_ok": "はい、すべて消去",
        "cancel":             "キャンセル",

        # Action dialog
        "act_title":          "Ashleyが行動したい",
        "act_intro":          "AshleyがあなたのPCで次のアクションを実行することを提案しています:",
        "act_question":       "このアクションを許可しますか?",
        "act_yes":            "✅ はい、実行",
        "act_no":             "❌ キャンセル",

        # Language toggle
        "lang_label":         "言語",
        "lang_en":            "EN",
        "lang_es":            "ES",

        # Voice
        "mic_tooltip":        "クリックで音声ディクテーション",
        "tts_on_tooltip":     "Ashleyが話す — クリックでミュート",
        "tts_off_tooltip":    "Ashleyはミュート中 — クリックで音声を有効化",

        # Settings modal
        "settings_tooltip":         "設定",
        "settings_title":           "設定",

        "settings_required_heading":  "🔑 必須",
        "settings_optional_heading":  "✨ オプション — プレミアム音声",
        "settings_included_heading":  "🎤 含まれる — 音声入力",

        # Required (Grok)
        "settings_grok_label":      "Grok (xAI) APIキー",
        "settings_grok_configured": "設定済み ✓  (インストーラーで管理)",
        "settings_grok_missing":    "未設定 — 設定するまでAshleyは返信できません。",
        "settings_grok_consequence": "これがないと、Ashleyは考えたり返信したりできません。",
        "settings_grok_hint":       "インストール時に設定されます。変更するには再インストールしてください。",

        # LLM Provider
        "settings_provider_heading": "🧠 LLMプロバイダー",
        "settings_provider_label":  "Ashleyを動かすサービス",
        "settings_provider_xai":    "xAI (Grok) — デフォルト、最速セットアップ",
        "settings_provider_openrouter": "OpenRouter — Claude、DeepSeek、GPT、Geminiを解放...",
        "settings_provider_ollama": "Ollama — 100%無料&ローカル、PCで動作 (APIキー不要)",
        "settings_openrouter_key_label": "OpenRouter APIキー",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "openrouter.ai → Settings → Keysで取得。1つのキーで多くのモデルを開放。",
        "settings_model_label":     "モデル",
        "settings_model_hint":      "モデルごとに性格、速度、価格が異なります。予算に合うものを選んでください。",
        "settings_ollama_detected": "Ollama検出 ✓ — ダウンロード済みのモデルを下から選択",
        "settings_ollama_missing":  "Ollama未検出 — このオプションを使うにはまずインストールしてください",
        "settings_ollama_install":  "ollama.comから無料でOllamaをダウンロードし、'ollama pull llama3.2'を実行",
        "settings_ollama_refresh":  "🔄 ローカルモデルを更新",
        "settings_ollama_no_models": "モデルがありません — まずターミナルで'ollama pull llama3.2'を実行",

        # TTS Provider
        "settings_tts_heading":     "🎙️ 音声プロバイダー (TTS)",
        "settings_tts_label":       "Ashleyに声を与えるエンジン",
        "settings_tts_webspeech":   "Windowsの声 — 無料、ロボット的だが即時",
        "settings_tts_elevenlabs":  "ElevenLabs — プレミアム、アニメ品質 (有料API)",
        "settings_tts_kokoro":      "Kokoro — 無料、ローカル、ElevenLabsに近い品質 (ローカルサーバー必要)",
        "settings_tts_voicevox":    "VoiceVox — 無料、アニメキャラクターの声 (日本語向け)",
        "settings_kokoro_url_label": "KokoroサーバーURL",
        "settings_kokoro_url_hint": "Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) をインストールしてローカルで実行。",
        "settings_kokoro_voice_label": "Kokoroの声",
        "settings_kokoro_voice_hint": "一般的な声: af_bella、af_nicole、am_adam、bf_emma。Kokoroドキュメント参照。",
        "settings_voicevox_url_label": "VoiceVox EngineのURL",
        "settings_voicevox_url_hint": "voicevox.hiroshiba.jpからVoiceVoxをインストールしてエンジンを実行。",
        "settings_voicevox_speaker_label": "VoiceVoxスピーカーID",
        "settings_voicevox_speaker_hint": "数値ID (例: 1、2、3)。完全なリストはVoiceVox Engineで確認。",
        # voice speed slider
        "settings_voice_speed_label": "声の速度",
        "settings_voice_speed_hint": "Ashleyの話す速度。1.0 = 通常、1.5 = 明らかに速い、0.75 = 遅い。プロバイダーがサポートする場合はネイティブで適用 (ElevenLabs Turbo v2.5、Kokoro、VoiceVox);それ以外はブラウザのplaybackRateにフォールバック。",

        # Quick menu labels
        "menu_tts":          "音声",
        "menu_pin":          "前面に固定",
        "menu_initiative":   "今話す",
        "menu_settings":     "詳細設定...",

        # Mobile pair (v0.18.2)
        "pill_mobile_pair":      "モバイル",
        "mobile_pair_title":     "モバイルを接続",
        "mobile_pair_subtitle":  "携帯でAshley Mobileを開いてこのQRをスキャン。",
        "mobile_pair_loading":   "読み込み中...",
        "mobile_pair_manual":    "または手動で入力:",
        "mobile_pair_server":    "サーバー",
        "mobile_pair_token":     "トークン",
        "mobile_pair_copy":      "コピー",
        "mobile_pair_copied":    "コピー済み",
        "mobile_pair_regen":     "トークン再生成",
        "mobile_pair_regen_warn": "再生成するとペアリング済みの携帯が無効になります。再度スキャンが必要です。",
        "mobile_pair_close":     "閉じる",
        "mobile_pair_help":      "まだモバイルがない?購入メールからAshley Mobile (.apk) をダウンロード。",
        "mobile_pair_security_warning": "⚠️ このQRを共有しないでください。スキャンした人はAshleyとのすべての会話に完全にアクセスできます。",
        "mobile_pair_generic_error": "ペアリング情報を読み込めませんでした — しばらくしてからもう一度試してください。",

        # News feed
        "pill_news":         "ニュース",
        "news_tooltip_on":   "Ashleyが見つけたものを見る",
        "news_title":        "📰 Ashleyの発見",
        "news_empty":        "まだ発見はありません",
        "news_empty_hint":   "Ashleyはご主人の好みに合うものを見つけたら、曲、トレーラー、記事、ニュースをここに置きます — チャットを邪魔せずに。",
        "news_empty_tip_title": "活性化方法",
        "news_empty_tip_body":  "設定 → プロアクティブ発見をONに。Ashleyがご主人の好みを知れば(好きなものについて話すだけ)、自分で検索を始めます。",
        "news_unavailable_title":  "このモデルでは発見が利用できません",
        "news_unavailable_body":   "Web検索は現在Grok (xAI) でのみサポートされています。他のモデルはチャット、画像、システムアクションには優れていますが、Webで曲、トレーラー、ニュースを検索することはできません。",
        "news_unavailable_hint":   "発見を有効にするには:設定 → AIモデル を開いてGrokに切り替え。",
        "news_close":        "チャットに戻る",
        "news_clear_all":    "すべて消去",
        "news_clear_confirm": "すべての発見を削除しますか?",
        "news_delete":       "削除",
        "news_category_song":    "🎵 音楽",
        "news_category_trailer": "🎬 トレーラー",
        "news_category_article": "📰 記事",
        "news_category_game":    "🎮 ゲーム",
        "news_category_tech":    "💻 テック",
        "news_category_other":   "✨ 発見",

        # Discovery toggle
        "settings_discovery_heading": "🔭 プロアクティブ発見",
        "settings_discovery_label":   "Ashleyが自分で新しいコンテンツを持ち出すことを許可",
        "settings_discovery_desc":    "ONの場合、Ashleyは時々Webで検索し、ご主人の好みに合うトレーラー、曲、記事、ニュースを共有することがあります。OFFの場合(デフォルト)、ランダムなトピックを挿入せずに会話の継続に集中します。感情的な瞬間ではこの設定に関係なく発見は常に無効になります。",
        "settings_discovery_on":      "ON — Ashleyが発見を共有",
        "settings_discovery_off":     "OFF — Ashleyは会話に集中",
        "settings_discovery_unavailable":      "このプロバイダーでは利用不可:",
        "settings_discovery_unavailable_desc": "プロアクティブ発見にはWeb検索が必要で、現在Grok (xAI) でのみサポートされています。この機能を有効にするには上のAIモデルセクションでGrokに切り替えてください。",

        # Modern browser mode (CDP)
        "settings_cdp_heading": "🌐 モダンブラウザモード (上級)",
        "settings_cdp_label":   "タブ制御にChrome DevTools Protocolを使用",
        "settings_cdp_on":      "ON — AshleyがCDP経由でブラウザを制御",
        "settings_cdp_off":     "OFF — Ashleyはキーボードシミュレーションを使用 (レガシー)",
        "settings_cdp_desc":    "ONの場合、Ashleyはlocalhost:9222経由でブラウザに直接話します (キーボードシミュレーションなし、目に見えるタブ切り替えなし、100ms未満)。ブラウザが応答しない場合は自動的にレガシーモードにフォールバック。トレードオフ:任意のローカルアプリがそのポートに接続できる — アクティブなマルウェアがないユーザーにとってリスクは低い。",
        "settings_cdp_howto":   "このトグルを有効にすると、ブラウザのショートカット (Chrome/Edge/Brave/Opera...) が自動的に変更され、必要なフラグが追加されます。元のものはバックアップされます — OFFにすると正確に復元されます。有効化後、ブラウザを閉じて再度開いて変更を反映してください。⚠ 普段タスクバーのピンからブラウザを開いてるなら、代わりにスタートメニューかデスクトップから開いてね — Windows 10/11のタスクバーピンはウィザードを迂回することがあります。",

        # Wake word
        "settings_wakeword_heading": "🎙 ウェイクワード (常時リスニング)",
        "settings_wakeword_label":   "「Ashley」を継続的にリスニング",
        "settings_wakeword_on":      "ON — 「Ashley」と言ってハンズフリーで話す",
        "settings_wakeword_off":     "OFF — マイクボタンを押して話す",
        "settings_wakeword_desc":    "ONの場合、Ashleyはバックグラウンドでマイクを開いたままにし、自分の名前を聞いたら録音をトリガーします。検出モデルはローカル (~5 MB)、CPUで動作し、ウェイクワードを言うまで音声はPCから出ません。誤動作はTV/音楽がバックグラウンドで流れていても1時間あたり1回未満に調整されています。",
        "settings_wakeword_howto":   "マイクの近くで「Ashley」とはっきり言ってください。チャイムの後、通常通り話します。検出器はタイピング中やマイクボタンを押している間は自動的に一時停止し、その後再開します。",
        "settings_wakeword_no_model": "ウェイクワードモデルがまだインストールされていません。トレーニングパイプラインはwake_word_training/にあります — トレーニング後 (CUDA GPUで~3-4時間)、.onnxをreflex_companion/wake_word/ashley.onnxにコピーします。",
        "settings_wakeword_no_deps":  "ウェイクワードの依存関係が不足しています。実行: pip install openwakeword sounddevice",

        # Optional (ElevenLabs)
        "settings_elevenlabs_label": "ElevenLabs APIキー",
        "settings_elevenlabs_placeholder": "sk_... (空のままだと無料音声を使用)",
        "settings_elevenlabs_hint": "elevenlabs.io → Profile → API Keysでキーを取得。コンピューターにのみ保存されます。",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "elevenlabs.io → Voice Libraryで音声を閲覧し、Voice IDをコピー。",
        "settings_elevenlabs_without": "これがない場合:",
        "settings_elevenlabs_without_desc": "AshleyはWindowsシステムの無料音声 (ロボット的だが機能的) を使用します。",
        "settings_elevenlabs_with":   "これがある場合:",
        "settings_elevenlabs_with_desc":   "本物の感情的なニュアンスを持つアニメ品質のプレミアム音声。",
        "settings_test_voice":       "音声テスト",
        "settings_test_text":        "やぁ。Ashleyが音声をテストしているよ。聞こえる?",

        # Included (Whisper local)
        "settings_whisper_label":   "Whisper (音声認識)",
        "settings_whisper_ready":   "組み込み済み ✓ — セットアップ不要",
        "settings_whisper_desc":    "マイクのディクテーションは初回使用後100%オフラインで動作します。🎤ボタンを初めてクリックしたとき、75 MBのモデルが一度だけダウンロードされます。その後はすべてローカルで実行 — APIコストなし、インターネット不要。",

        "settings_usage_heading":   "📊 使用状況",
        "settings_usage_label":     "Ashleyに送信したメッセージ",
        "settings_usage_hint":      "返金資格の確認に使用 (14日以内かつ40メッセージ未満で返金可能)。",
        "settings_usage_tampered":  "⚠️ 整合性チェック失敗 — カウンターを検証できません。サポート用にこの値が必要な場合はAshleyを再インストールしてください。",

        # 法的事項とデータ (v0.19.23)
        "settings_legal_heading":   "⚖ 法的事項とデータ",
        "settings_privacy_btn":     "プライバシーポリシー",
        "settings_terms_btn":       "利用規約",
        "settings_backup_desc":     "全データ(チャット履歴、事実、日記、実績、設定)をZIPファイルでバックアップ。再インストール前、別のPCへの移行、または安心のために便利。",
        "settings_export_btn":      "全データをエクスポート(.zip)",

        "settings_save":            "保存",
        "settings_close":           "閉じる",

        # Error prefix
        "error_grok":         "*ため息* Grok{label}で何か問題が発生しました: {err}",
        "upload_too_big":     "*顔をしかめる* その画像は大きすぎる ({size_mb:.1f} MB)。実際に見られるように最大10 MBまで。",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 実績",
        "ach_unlocked_label":   "実績解除!",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "解除: {date}",

        # Affection tier messages
        "tier_up_1":    "Ashleyは少しだけガードを下げる...",
        "tier_up_2":    "Ashleyはご主人と一緒にいて快適に感じ始めている。",
        "tier_up_3":    "Ashleyは...変な気分。心臓が早く鼓動している。",
        "tier_up_4":    "Ashleyはもう自分の気持ちを隠せない。",
        "tier_down_4":  "Ashleyはもう安全だと感じない...",
        "tier_down_3":  "Ashleyはもう少し心を閉ざす...",
        "tier_down_2":  "Ashleyはご主人を疑い始めている...",
        "tier_down_1":  "Ashleyはご主人をほとんど認識できない...",

        # License gate
        "license_title":         "Ashleyへようこそ",
        "license_subtitle":      "ライセンスキーを貼り付けて始めましょう。",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "アクティブ化",
        "license_activating":    "アクティブ化中...",
        "license_buy":           "まだキーを持っていません",
        "license_lost_key":      "キーを失くした — サポートに連絡",
        "license_error_invalid": "そのライセンスキーは存在しないか有効ではありません。",
        "license_error_limit":   "このライセンスは既に最大数のPCでアクティブ化されています。",
        "license_error_network": "ライセンスサーバーに到達できませんでした。インターネット接続を確認してもう一度お試しください。",
        "license_info_test":     "テストモードライセンス",
        "license_grace_banner":  "オフライン — キャッシュされたライセンスで実行中。更新するには再接続してください。",
    },
    "de": {
        # Brand / avatar
        "brand_subtitle":     "Persönliche Sekretärin · Geek",

        # Status labels
        "status_thinking":    "denkt nach...",
        "status_speaking":    "spricht...",
        "status_online":      "online",

        # v0.19.20 — Settings dynamic status messages
        "cdp_setup_in_progress":     "Browser-Verknüpfungen werden konfiguriert...",
        "cdp_setup_in_progress_off": "Verknüpfungen werden in den Originalzustand zurückgesetzt...",
        # v0.19.31 — CDP wizard result messages
        "cdp_result_modified":        "✓ {n} Verknüpfung(en) geändert. Schließ deinen Browser und öffne ihn neu, damit die Änderung wirkt.",
        "cdp_result_no_shortcuts":    "⚠ Keine Chromium-Browser-Verknüpfungen auf deinem PC gefunden. Aktivier das Flag manuell.",
        "cdp_result_already_active":  "✓ Alle {n} Verknüpfungen hatten das Flag schon aktiv.",
        "cdp_result_restored":        "✓ {n} Verknüpfung(en) auf den Originalzustand zurückgesetzt.",
        "cdp_result_classic_mode":    "✓ Klassischer Modus aktiviert.",
        "cdp_result_failed_suffix":   " ({n} fehlgeschlagen)",
        "cdp_result_error":           "Fehler im Assistenten: {err}",
        "wake_word_listening":       "OK ich höre",

        # Input
        "input_placeholder":  "Schreib deine Nachricht...  (Enter zum Senden, Shift+Enter für neue Zeile)",
        "btn_send":           "Senden",

        # Header pills
        "pill_memories":      "Erinnerungen",
        "pill_initiative":    "Ashley",
        "pill_actions":       "Aktionen",
        "pill_focus":         "Fokus",
        "pill_natural":       "Natürlich",
        "pill_notifications": "Benachr.",
        "notif_on_tooltip":   "Hintergrund-Benachrichtigungen AN — klick zum Stummschalten",
        "notif_off_tooltip":  "Hintergrund-Benachrichtigungen AUS — klick zum Aktivieren",
        "pin_on_tooltip":     "Ashley bleibt über anderen Fenstern — klick zum Lösen",
        "pin_off_tooltip":    "Ashley über anderen Fenstern anpinnen",

        # Memories dialog
        "mem_title":          "🧠 Meine Erinnerungen mit Ashley",
        "mem_tab_facts":      "✨ Fakten",
        "mem_tab_diary":      "📅 Tagebuch",
        "mem_tab_history":    "💬 Verlauf",
        "mem_tab_tastes":     "💝 Vorlieben",
        "mem_tastes_empty":   "Noch keine Vorlieben gespeichert.",
        "mem_tastes_hint":    "Sag Ashley, was du magst, und sie wird sich erinnern.",
        "mem_close":          "Schließen",
        "mem_clear_all":      "Alle Erinnerungen löschen",
        "mem_clear_all_confirm_title": "ALLE Erinnerungen löschen?",
        "mem_clear_all_confirm_body": "Das löscht dauerhaft jede Information, die Ashley über dich gespeichert hat. Der Chat-Verlauf wird NICHT angetastet — Ashley kann einige Fakten wieder aufbauen, wenn du weitersprichst. Nutze das, wenn ihre Erinnerungen in eine Richtung abdriften, die dir nicht gefällt.",
        "mem_clear_all_confirm_ok": "Ja, alle löschen",
        "cancel":             "Abbrechen",

        # Action dialog
        "act_title":          "Ashley möchte handeln",
        "act_intro":          "Ashley schlägt vor, folgende Aktion auf deinem PC auszuführen:",
        "act_question":       "Erlaubst du diese Aktion?",
        "act_yes":            "✅ Ja, mach es",
        "act_no":             "❌ Abbrechen",

        # Language toggle
        "lang_label":         "Sprache",
        "lang_en":            "EN",
        "lang_es":            "ES",

        # Voice
        "mic_tooltip":        "Klick für Sprachdiktat",
        "tts_on_tooltip":     "Ashley spricht — klick zum Stummschalten",
        "tts_off_tooltip":    "Ashley ist stumm — klick zum Aktivieren der Stimme",

        # Settings modal
        "settings_tooltip":         "Einstellungen",
        "settings_title":           "Einstellungen",

        "settings_required_heading":  "🔑 Erforderlich",
        "settings_optional_heading":  "✨ Optional — Premium-Stimme",
        "settings_included_heading":  "🎤 Enthalten — Spracheingabe",

        # Required (Grok)
        "settings_grok_label":      "Grok (xAI) API-Schlüssel",
        "settings_grok_configured": "Konfiguriert ✓  (vom Installer verwaltet)",
        "settings_grok_missing":    "Nicht konfiguriert — Ashley kann nicht antworten, bis du es einrichtest.",
        "settings_grok_consequence": "Ohne das kann Ashley weder denken noch dir antworten.",
        "settings_grok_hint":       "Wird während der Installation eingerichtet. Zum Ändern installiere Ashley neu.",

        # LLM Provider
        "settings_provider_heading": "🧠 KI-Anbieter",
        "settings_provider_label":  "Welcher Dienst Ashley antreibt",
        "settings_provider_xai":    "xAI (Grok) — Standard, schnellste Einrichtung",
        "settings_provider_openrouter": "OpenRouter — schaltet Claude, DeepSeek, GPT, Gemini frei...",
        "settings_provider_ollama": "Ollama — 100% kostenlos & lokal, läuft auf deinem PC (kein API-Schlüssel)",
        "settings_openrouter_key_label": "OpenRouter API-Schlüssel",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "Hol ihn dir auf openrouter.ai → Settings → Keys. Ein Schlüssel schaltet viele Modelle frei.",
        "settings_model_label":     "Modell",
        "settings_model_hint":      "Verschiedene Modelle haben unterschiedliche Persönlichkeit, Geschwindigkeit und Preis. Wähl eins, das zu deinem Budget passt.",
        "settings_ollama_detected": "Ollama erkannt ✓ — wähle unten ein Modell, das du heruntergeladen hast",
        "settings_ollama_missing":  "Ollama nicht erkannt — installiere es zuerst, um diese Option zu nutzen",
        "settings_ollama_install":  "Lade Ollama von ollama.com (kostenlos), dann führe 'ollama pull llama3.2' aus",
        "settings_ollama_refresh":  "🔄 Lokale Modelle aktualisieren",
        "settings_ollama_no_models": "Keine Modelle gefunden — führe zuerst 'ollama pull llama3.2' im Terminal aus",

        # TTS Provider
        "settings_tts_heading":     "🎙️ Sprachanbieter (TTS)",
        "settings_tts_label":       "Welche Engine Ashleys Stimme erzeugt",
        "settings_tts_webspeech":   "Windows-Stimme — kostenlos, roboterhaft aber sofort",
        "settings_tts_elevenlabs":  "ElevenLabs — Premium, Anime-Qualität (kostenpflichtige API)",
        "settings_tts_kokoro":      "Kokoro — kostenlos, lokal, fast ElevenLabs-Qualität (lokaler Server erforderlich)",
        "settings_tts_voicevox":    "VoiceVox — kostenlos, Anime-Charakterstimmen (japanisch-orientiert)",
        "settings_kokoro_url_label": "Kokoro-Server-URL",
        "settings_kokoro_url_hint": "Installiere Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) und lass es lokal laufen.",
        "settings_kokoro_voice_label": "Kokoro-Stimme",
        "settings_kokoro_voice_hint": "Häufige Stimmen: af_bella, af_nicole, am_adam, bf_emma. Siehe Kokoro-Doku.",
        "settings_voicevox_url_label": "VoiceVox-Engine-URL",
        "settings_voicevox_url_hint": "Installiere VoiceVox von voicevox.hiroshiba.jp und starte die Engine.",
        "settings_voicevox_speaker_label": "VoiceVox-Sprecher-ID",
        "settings_voicevox_speaker_hint": "Numerische ID (z.B. 1, 2, 3). Siehe VoiceVox-Engine für die vollständige Liste.",
        # voice speed slider
        "settings_voice_speed_label": "Sprachgeschwindigkeit",
        "settings_voice_speed_hint": "Wie schnell Ashley spricht. 1.0 = normal, 1.5 = deutlich schneller, 0.75 = langsamer. Wird nativ angewendet, wenn der Anbieter es unterstützt (ElevenLabs Turbo v2.5, Kokoro, VoiceVox); fällt sonst auf die Browser-Wiedergaberate zurück.",

        # Quick menu labels
        "menu_tts":          "Stimme",
        "menu_pin":          "Anpinnen",
        "menu_initiative":   "Sprich jetzt",
        "menu_settings":     "Mehr Einstellungen...",

        # Mobile pair
        "pill_mobile_pair":      "Mobil",
        "mobile_pair_title":     "Verbinde dein Handy",
        "mobile_pair_subtitle":  "Öffne Ashley Mobile auf deinem Handy und scanne diesen QR.",
        "mobile_pair_loading":   "Lädt...",
        "mobile_pair_manual":    "Oder manuell eingeben:",
        "mobile_pair_server":    "Server",
        "mobile_pair_token":     "Token",
        "mobile_pair_copy":      "Kopieren",
        "mobile_pair_copied":    "Kopiert",
        "mobile_pair_regen":     "Token neu generieren",
        "mobile_pair_regen_warn": "Neu generieren macht alle gekoppelten Handys ungültig. Sie müssen erneut scannen.",
        "mobile_pair_close":     "Schließen",
        "mobile_pair_help":      "Noch kein Mobil? Lade Ashley Mobile (.apk) aus deiner Kauf-E-Mail.",
        "mobile_pair_security_warning": "⚠️ Teile diesen QR nicht. Wer ihn scannt, bekommt vollen Zugriff auf deine Gespräche mit Ashley.",
        "mobile_pair_generic_error": "Pairing-Info konnte nicht geladen werden — versuch's gleich nochmal.",

        # News feed
        "pill_news":         "News",
        "news_tooltip_on":   "Sieh, was Ashley für dich gefunden hat",
        "news_title":        "📰 Ashleys Entdeckungen",
        "news_empty":        "Noch keine Entdeckungen",
        "news_empty_hint":   "Ashley wirft hier Songs, Trailer, Artikel und News rein, wenn sie etwas findet, das zu deinen Vorlieben passt — ohne deinen Chat zu unterbrechen.",
        "news_empty_tip_title": "So aktivierst du das",
        "news_empty_tip_body":  "Öffne Einstellungen → Proaktive Entdeckung und schalte sie EIN. Sobald Ashley deine Vorlieben kennt (sprich mit ihr darüber, was du magst), beginnt sie eigenständig zu suchen.",
        "news_unavailable_title":  "Entdeckung ist mit diesem Modell nicht verfügbar",
        "news_unavailable_body":   "Web-Suche wird derzeit nur mit Grok (xAI) unterstützt. Andere Modelle eignen sich super für Chat, Vision und Systemaktionen, aber sie können nicht im Web nach Songs, Trailern oder News suchen.",
        "news_unavailable_hint":   "Um Entdeckung zu aktivieren: Öffne Einstellungen → KI-Modell und wechsle zu Grok.",
        "news_close":        "Zurück zum Chat",
        "news_clear_all":    "Alle löschen",
        "news_clear_confirm": "Alle Entdeckungen entfernen?",
        "news_delete":       "Entfernen",
        "news_category_song":    "🎵 Musik",
        "news_category_trailer": "🎬 Trailer",
        "news_category_article": "📰 Artikel",
        "news_category_game":    "🎮 Spiel",
        "news_category_tech":    "💻 Tech",
        "news_category_other":   "✨ Entdeckung",

        # Discovery toggle
        "settings_discovery_heading": "🔭 Proaktive Entdeckung",
        "settings_discovery_label":   "Erlaube Ashley, von sich aus neue Inhalte zu bringen",
        "settings_discovery_desc":    "Wenn EIN, sucht Ashley gelegentlich im Web und teilt Trailer, Songs, Artikel oder News, die zu deinen Vorlieben passen. Wenn AUS (Standard), konzentriert sie sich darauf, das Gespräch fortzusetzen, ohne zufällige Themen einzuwerfen. Emotionale Momente deaktivieren Entdeckung immer, unabhängig von dieser Einstellung.",
        "settings_discovery_on":      "EIN — Ashley teilt Entdeckungen",
        "settings_discovery_off":     "AUS — Ashley bleibt bei unserem Gespräch",
        "settings_discovery_unavailable":      "Nicht verfügbar mit",
        "settings_discovery_unavailable_desc": "Proaktive Entdeckung benötigt Web-Suche, die derzeit nur mit Grok (xAI) unterstützt wird. Wechsle im Abschnitt KI-Modell oben zu Grok, um diese Funktion zu aktivieren.",

        # Modern browser mode (CDP)
        "settings_cdp_heading": "🌐 Moderner Browser-Modus (fortgeschritten)",
        "settings_cdp_label":   "Chrome DevTools Protocol für Tab-Steuerung verwenden",
        "settings_cdp_on":      "EIN — Ashley steuert den Browser via CDP",
        "settings_cdp_off":     "AUS — Ashley nutzt Tastatursimulation (klassisch)",
        "settings_cdp_desc":    "Wenn EIN, spricht Ashley direkt mit dem Browser über localhost:9222 (keine Tastatursimulation, kein sichtbares Tab-Wechseln, sub-100ms). Fällt automatisch in den klassischen Modus zurück, wenn der Browser nicht antwortet. Kompromiss: jede lokale App könnte sich mit diesem Port verbinden — geringes Risiko für Nutzer ohne aktive Malware.",
        "settings_cdp_howto":   "Aktivieren dieses Toggles modifiziert automatisch die Verknüpfungen deines Browsers (Chrome/Edge/Brave/Opera...) und fügt das nötige Flag hinzu. Originale werden gesichert — Ausschalten stellt sie genau wieder her. Nach dem Aktivieren schließe und öffne deinen Browser, damit die Änderung wirksam wird. ⚠ Wenn du deinen Browser normalerweise von einer Taskleisten-Anheftung öffnest, öffne ihn stattdessen vom Startmenü oder Desktop — Taskleisten-Anheftungen unter Windows 10/11 können den Assistenten umgehen.",

        # Wake word
        "settings_wakeword_heading": "🎙 Aktivierungswort (immer-an Lauschen)",
        "settings_wakeword_label":   "Kontinuierlich auf 'Ashley' lauschen",
        "settings_wakeword_on":      "EIN — sag 'Ashley', um freihändig zu sprechen",
        "settings_wakeword_off":     "AUS — drück die Mikrofontaste, um zu sprechen",
        "settings_wakeword_desc":    "Wenn EIN, hält Ashley das Mikrofon im Hintergrund offen und startet die Aufnahme, wenn sie ihren Namen hört. Das Erkennungsmodell ist lokal (~5 MB), läuft auf der CPU, und Audio verlässt NIE deinen Computer, bis du das Aktivierungswort sprichst. Falsche Aktivierungen sind auf <1 pro Stunde mit TV/Musik im Hintergrund eingestellt.",
        "settings_wakeword_howto":   "Sag 'Ashley' deutlich nahe am Mikrofon. Nach dem Klang sprich deine Nachricht normal. Der Detektor pausiert automatisch, während du tippst oder die Mikrofontaste hältst, und nimmt danach wieder auf.",
        "settings_wakeword_no_model": "Aktivierungswort-Modell noch nicht installiert. Die Trainings-Pipeline befindet sich in wake_word_training/ — nach dem Training (~3-4 h auf einer CUDA-GPU) kopiere die .onnx nach reflex_companion/wake_word/ashley.onnx.",
        "settings_wakeword_no_deps":  "Aktivierungswort-Abhängigkeiten fehlen. Führe aus: pip install openwakeword sounddevice",

        # Optional (ElevenLabs)
        "settings_elevenlabs_label": "ElevenLabs API-Schlüssel",
        "settings_elevenlabs_placeholder": "sk_... (leer lassen für kostenlose Stimme)",
        "settings_elevenlabs_hint": "Hol dir deinen Schlüssel auf elevenlabs.io → Profile → API Keys. Wird nur auf deinem Computer gespeichert.",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "Stöbere durch Stimmen auf elevenlabs.io → Voice Library und kopiere die Voice ID.",
        "settings_elevenlabs_without": "Ohne das:",
        "settings_elevenlabs_without_desc": "Ashley nutzt die kostenlose Windows-Systemstimme (roboterhaft aber funktional).",
        "settings_elevenlabs_with":   "Damit:",
        "settings_elevenlabs_with_desc":   "Premium-Anime-Stimme mit echter emotionaler Nuance.",
        "settings_test_voice":       "Stimme testen",
        "settings_test_text":        "Hi. Hier ist Ashley, ich teste die Stimme. Hörst du mich?",

        # Included (Whisper local)
        "settings_whisper_label":   "Whisper (Sprache-zu-Text)",
        "settings_whisper_ready":   "Eingebaut ✓ — keine Einrichtung nötig",
        "settings_whisper_desc":    "Mikrofondiktat funktioniert nach der ersten Nutzung 100% offline. Beim ersten Klick auf den 🎤-Button wird einmalig ein 75-MB-Modell heruntergeladen. Danach läuft alles lokal — keine API-Kosten, kein Internet nötig.",

        "settings_usage_heading":   "📊 Nutzung",
        "settings_usage_label":     "An Ashley gesendete Nachrichten",
        "settings_usage_hint":      "Wird zur Überprüfung der Rückerstattungsberechtigung genutzt (Rückerstattung möglich innerhalb von 14 Tagen und unter 40 Nachrichten).",
        "settings_usage_tampered":  "⚠️ Integritätsprüfung fehlgeschlagen — Zähler kann nicht verifiziert werden. Installiere Ashley neu, falls du diesen Wert für den Support brauchst.",

        # Rechtliches & Daten (v0.19.23)
        "settings_legal_heading":   "⚖ Rechtliches & Daten",
        "settings_privacy_btn":     "Datenschutzerklärung",
        "settings_terms_btn":       "Nutzungsbedingungen",
        "settings_backup_desc":     "Sichere all deine Daten (Chat-Verlauf, Fakten, Tagebuch, Errungenschaften, Einstellungen) als ZIP-Datei. Nützlich vor Neuinstallation, Migration zu einem anderen PC oder einfach zur Beruhigung.",
        "settings_export_btn":      "Alle meine Daten exportieren (.zip)",

        "settings_save":            "Speichern",
        "settings_close":           "Schließen",

        # Error prefix
        "error_grok":         "*seufzt* Etwas ist mit Grok{label} schiefgelaufen: {err}",
        "upload_too_big":     "*verzieht das Gesicht* Das Bild ist zu groß ({size_mb:.1f} MB). Max sind 10 MB, damit ich es überhaupt anschauen kann.",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 Erfolge",
        "ach_unlocked_label":   "ERFOLG FREIGESCHALTET",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "Freigeschaltet: {date}",

        # Affection tier messages
        "tier_up_1":    "Ashley senkt ihre Wache, nur ein bisschen...",
        "tier_up_2":    "Ashley fängt an, sich bei dir wohlzufühlen.",
        "tier_up_3":    "Ashley fühlt sich... seltsam. Ihr Herz schlägt schneller.",
        "tier_up_4":    "Ashley kann nicht mehr verbergen, was sie fühlt.",
        "tier_down_4":  "Ashley fühlt sich nicht mehr so sicher...",
        "tier_down_3":  "Ashley schließt sich ein bisschen mehr...",
        "tier_down_2":  "Ashley beginnt, an dir zu zweifeln...",
        "tier_down_1":  "Ashley erkennt dich kaum noch...",

        # License gate
        "license_title":         "Willkommen bei Ashley",
        "license_subtitle":      "Füg deinen Lizenzschlüssel ein, um loszulegen.",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "Aktivieren",
        "license_activating":    "Aktivierung läuft...",
        "license_buy":           "Ich habe noch keinen Schlüssel",
        "license_lost_key":      "Schlüssel verloren — Support kontaktieren",
        "license_error_invalid": "Dieser Lizenzschlüssel existiert nicht oder ist ungültig.",
        "license_error_limit":   "Du hast diese Lizenz bereits auf der maximalen Anzahl an PCs aktiviert.",
        "license_error_network": "Konnte den Lizenzserver nicht erreichen. Prüf dein Internet und versuch es nochmal.",
        "license_info_test":     "Test-Modus-Lizenz",
        "license_grace_banner":  "Offline — läuft mit zwischengespeicherter Lizenz. Verbinde dich neu, um zu erneuern.",
    },
    "ru": {
        # Brand / avatar
        "brand_subtitle":     "Личный секретарь · Гик",

        # Status labels
        "status_thinking":    "думает...",
        "status_speaking":    "говорит...",
        "status_online":      "онлайн",

        # v0.19.20 — Settings dynamic status messages
        "cdp_setup_in_progress":     "Настройка ярлыков браузера...",
        "cdp_setup_in_progress_off": "Восстановление ярлыков в исходное состояние...",
        # v0.19.31 — CDP wizard result messages
        "cdp_result_modified":        "✓ Изменено ярлыков: {n}. Закрой и снова открой браузер, чтобы применить изменения.",
        "cdp_result_no_shortcuts":    "⚠ Ярлыков браузеров Chromium на твоём ПК не нашёл. Активируй флаг вручную.",
        "cdp_result_already_active":  "✓ Все {n} ярлыков уже имели активный флаг.",
        "cdp_result_restored":        "✓ Восстановлено ярлыков: {n}.",
        "cdp_result_classic_mode":    "✓ Классический режим активирован.",
        "cdp_result_failed_suffix":   " (не удалось: {n})",
        "cdp_result_error":           "Ошибка в мастере: {err}",
        "wake_word_listening":       "ОК слушаю",

        # Input
        "input_placeholder":  "Напиши сообщение...  (Enter — отправить, Shift+Enter — новая строка)",
        "btn_send":           "Отправить",

        # Header pills
        "pill_memories":      "Память",
        "pill_initiative":    "Ashley",
        "pill_actions":       "Действия",
        "pill_focus":         "Фокус",
        "pill_natural":       "Натурально",
        "pill_notifications": "Уведом.",
        "notif_on_tooltip":   "Фоновые уведомления ВКЛ — кликни чтобы выключить",
        "notif_off_tooltip":  "Фоновые уведомления ВЫКЛ — кликни чтобы включить",
        "pin_on_tooltip":     "Ashley поверх других окон — кликни чтобы открепить",
        "pin_off_tooltip":    "Закрепить Ashley поверх других окон",

        # Memories dialog
        "mem_title":          "🧠 Мои воспоминания с Ashley",
        "mem_tab_facts":      "✨ Факты",
        "mem_tab_diary":      "📅 Дневник",
        "mem_tab_history":    "💬 История",
        "mem_tab_tastes":     "💝 Вкусы",
        "mem_tastes_empty":   "Пока нет сохранённых вкусов.",
        "mem_tastes_hint":    "Расскажи Ashley, что тебе нравится, и она запомнит.",
        "mem_close":          "Закрыть",
        "mem_clear_all":      "Стереть всю память",
        "mem_clear_all_confirm_title": "Стереть ВСЮ память?",
        "mem_clear_all_confirm_body": "Это навсегда удалит каждый факт, который Ashley сохранила о тебе. История чата НЕ затрагивается — Ashley может восстановить некоторые факты по мере общения. Используй это, если её воспоминания ушли в нежелательную сторону.",
        "mem_clear_all_confirm_ok": "Да, стереть всё",
        "cancel":             "Отмена",

        # Action dialog
        "act_title":          "Ashley хочет действовать",
        "act_intro":          "Ashley предлагает выполнить это действие на твоём ПК:",
        "act_question":       "Разрешаешь это действие?",
        "act_yes":            "✅ Да, давай",
        "act_no":             "❌ Отмена",

        # Language toggle
        "lang_label":         "Язык",
        "lang_en":            "EN",
        "lang_es":            "ES",

        # Voice
        "mic_tooltip":        "Кликни для голосового ввода",
        "tts_on_tooltip":     "Ashley говорит — кликни чтобы выключить",
        "tts_off_tooltip":    "Ashley молчит — кликни чтобы включить голос",

        # Settings modal
        "settings_tooltip":         "Настройки",
        "settings_title":           "Настройки",

        "settings_required_heading":  "🔑 Обязательно",
        "settings_optional_heading":  "✨ Опционально — Премиум-голос",
        "settings_included_heading":  "🎤 Включено — Голосовой ввод",

        # Required (Grok)
        "settings_grok_label":      "API-ключ Grok (xAI)",
        "settings_grok_configured": "Настроено ✓  (управляется установщиком)",
        "settings_grok_missing":    "Не настроено — Ashley не сможет отвечать пока не настроишь.",
        "settings_grok_consequence": "Без этого Ashley не может думать или отвечать тебе.",
        "settings_grok_hint":       "Настраивается во время установки. Чтобы изменить, переустанови Ashley.",

        # LLM Provider
        "settings_provider_heading": "🧠 Провайдер ИИ",
        "settings_provider_label":  "Какой сервис двигает Ashley",
        "settings_provider_xai":    "xAI (Grok) — по умолчанию, самая быстрая настройка",
        "settings_provider_openrouter": "OpenRouter — открывает Claude, DeepSeek, GPT, Gemini...",
        "settings_provider_ollama": "Ollama — 100% бесплатно и локально, работает на твоём ПК (без API-ключа)",
        "settings_openrouter_key_label": "API-ключ OpenRouter",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "Получи на openrouter.ai → Settings → Keys. Один ключ открывает много моделей.",
        "settings_model_label":     "Модель",
        "settings_model_hint":      "У разных моделей разная личность, скорость и цена. Выбери ту, что подходит твоему бюджету.",
        "settings_ollama_detected": "Ollama обнаружен ✓ — выбери ниже модель, которую ты скачал",
        "settings_ollama_missing":  "Ollama не обнаружен — установи его сначала, чтобы использовать эту опцию",
        "settings_ollama_install":  "Скачай Ollama с ollama.com (бесплатно), затем выполни 'ollama pull llama3.2'",
        "settings_ollama_refresh":  "🔄 Обновить локальные модели",
        "settings_ollama_no_models": "Нет моделей — выполни сначала 'ollama pull llama3.2' в терминале",

        # TTS Provider
        "settings_tts_heading":     "🎙️ Провайдер голоса (TTS)",
        "settings_tts_label":       "Какой движок озвучивает Ashley",
        "settings_tts_webspeech":   "Голос Windows — бесплатно, роботизированно но мгновенно",
        "settings_tts_elevenlabs":  "ElevenLabs — премиум, аниме-качество (платное API)",
        "settings_tts_kokoro":      "Kokoro — бесплатно, локально, почти ElevenLabs-качество (нужен локальный сервер)",
        "settings_tts_voicevox":    "VoiceVox — бесплатно, голоса аниме-персонажей (ориентирован на японский)",
        "settings_kokoro_url_label": "URL сервера Kokoro",
        "settings_kokoro_url_hint": "Установи Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) и запусти локально.",
        "settings_kokoro_voice_label": "Голос Kokoro",
        "settings_kokoro_voice_hint": "Распространённые голоса: af_bella, af_nicole, am_adam, bf_emma. См. документацию Kokoro.",
        "settings_voicevox_url_label": "URL движка VoiceVox",
        "settings_voicevox_url_hint": "Установи VoiceVox с voicevox.hiroshiba.jp и запусти движок.",
        "settings_voicevox_speaker_label": "ID спикера VoiceVox",
        "settings_voicevox_speaker_hint": "Числовой ID (напр. 1, 2, 3). Полный список см. в VoiceVox Engine.",
        # voice speed slider
        "settings_voice_speed_label": "Скорость голоса",
        "settings_voice_speed_hint": "Как быстро говорит Ashley. 1.0 = нормально, 1.5 = заметно быстрее, 0.75 = медленнее. Применяется нативно когда провайдер поддерживает (ElevenLabs Turbo v2.5, Kokoro, VoiceVox); иначе fallback на playback rate браузера.",

        # Quick menu labels
        "menu_tts":          "Голос",
        "menu_pin":          "Поверх",
        "menu_initiative":   "Скажи",
        "menu_settings":     "Все настройки...",

        # Mobile pair
        "pill_mobile_pair":      "Мобиль",
        "mobile_pair_title":     "Подключи мобильный",
        "mobile_pair_subtitle":  "Открой Ashley Mobile на телефоне и отсканируй этот QR.",
        "mobile_pair_loading":   "Загрузка...",
        "mobile_pair_manual":    "Или введи вручную:",
        "mobile_pair_server":    "Сервер",
        "mobile_pair_token":     "Токен",
        "mobile_pair_copy":      "Копировать",
        "mobile_pair_copied":    "Скопировано",
        "mobile_pair_regen":     "Перегенерировать токен",
        "mobile_pair_regen_warn": "Перегенерация отключит уже сопряжённые телефоны. Им придётся сканировать заново.",
        "mobile_pair_close":     "Закрыть",
        "mobile_pair_help":      "Ещё нет мобильного? Скачай Ashley Mobile (.apk) из письма о покупке.",
        "mobile_pair_security_warning": "⚠️ Не делись этим QR. Любой, кто отсканирует, получит полный доступ к твоим разговорам с Ashley.",
        "mobile_pair_generic_error": "Не удалось загрузить инфо о сопряжении — попробуй ещё раз.",

        # News feed
        "pill_news":         "Новости",
        "news_tooltip_on":   "Посмотри, что Ashley нашла для тебя",
        "news_title":        "📰 Открытия Ashley",
        "news_empty":        "Пока нет открытий",
        "news_empty_hint":   "Ashley будет складывать сюда песни, трейлеры, статьи и новости, когда найдёт что-то по твоим вкусам — без прерывания чата.",
        "news_empty_tip_title": "Как это включить",
        "news_empty_tip_body":  "Открой Настройки → Проактивные открытия и включи. Когда Ashley узнает твои вкусы (просто болтай о том, что нравится), она начнёт искать сама.",
        "news_unavailable_title":  "Открытия недоступны с этой моделью",
        "news_unavailable_body":   "Веб-поиск сейчас поддерживается только с Grok (xAI). Другие модели отлично работают для чата, изображений и системных действий, но не могут искать в интернете песни, трейлеры или новости.",
        "news_unavailable_hint":   "Чтобы включить открытия: открой Настройки → Модель ИИ и переключись на Grok.",
        "news_close":        "Назад в чат",
        "news_clear_all":    "Очистить всё",
        "news_clear_confirm": "Удалить все открытия?",
        "news_delete":       "Удалить",
        "news_category_song":    "🎵 Музыка",
        "news_category_trailer": "🎬 Трейлер",
        "news_category_article": "📰 Статья",
        "news_category_game":    "🎮 Игра",
        "news_category_tech":    "💻 Тех",
        "news_category_other":   "✨ Открытие",

        # Discovery toggle
        "settings_discovery_heading": "🔭 Проактивные открытия",
        "settings_discovery_label":   "Разреши Ashley самой приносить новый контент",
        "settings_discovery_desc":    "Когда ВКЛ, Ashley может время от времени искать в сети и делиться трейлерами, песнями, статьями или новостями по твоим вкусам. Когда ВЫКЛ (по умолчанию), она сосредоточена на продолжении разговора без вброса случайных тем. В эмоциональные моменты открытия всегда отключаются независимо от этой настройки.",
        "settings_discovery_on":      "ВКЛ — Ashley делится открытиями",
        "settings_discovery_off":     "ВЫКЛ — Ashley сосредоточена на нашей беседе",
        "settings_discovery_unavailable":      "Недоступно с",
        "settings_discovery_unavailable_desc": "Проактивные открытия требуют веб-поиска, который сейчас поддерживается только с Grok (xAI). Переключись на Grok в разделе ИИ-модель выше, чтобы включить эту функцию.",

        # Modern browser mode (CDP)
        "settings_cdp_heading": "🌐 Современный режим браузера (продвинутый)",
        "settings_cdp_label":   "Использовать Chrome DevTools Protocol для управления вкладками",
        "settings_cdp_on":      "ВКЛ — Ashley управляет браузером через CDP",
        "settings_cdp_off":     "ВЫКЛ — Ashley использует имитацию клавиатуры (классический)",
        "settings_cdp_desc":    "Когда ВКЛ, Ashley общается напрямую с браузером через localhost:9222 (без имитации клавиатуры, без видимых переключений вкладок, sub-100мс). Автоматически откатывается на классический режим, если браузер не отвечает. Компромисс: любое локальное приложение могло бы подключиться к этому порту — риск низкий для пользователей без активного malware.",
        "settings_cdp_howto":   "Активация этого тоггла автоматически модифицирует ярлыки твоего браузера (Chrome/Edge/Brave/Opera...) добавляя нужный флаг. Оригиналы сохраняются — выключение восстанавливает их в точности. После активации закрой и снова открой браузер, чтобы изменения применились. ⚠ Если ты обычно открываешь браузер из закреплённого ярлыка на панели задач, открывай его из меню Пуск или с Рабочего стола — закреплённые ярлыки на Windows 10/11 могут обойти мастер.",

        # Wake word
        "settings_wakeword_heading": "🎙 Слово-активатор (постоянное прослушивание)",
        "settings_wakeword_label":   "Слушать 'Ashley' непрерывно",
        "settings_wakeword_on":      "ВКЛ — скажи 'Ashley' чтобы говорить без рук",
        "settings_wakeword_off":     "ВЫКЛ — нажми кнопку микрофона чтобы говорить",
        "settings_wakeword_desc":    "Когда ВКЛ, Ashley держит микрофон открытым в фоне и запускает запись, когда слышит своё имя. Модель распознавания локальная (~5 МБ), работает на CPU, и аудио НИКОГДА не покидает твой компьютер пока ты не произнесёшь слово-активатор. Ложные срабатывания настроены на <1 в час с TV/музыкой в фоне.",
        "settings_wakeword_howto":   "Скажи 'Ashley' чётко около микрофона. После сигнала говори как обычно. Детектор автоматически приостанавливается пока ты печатаешь или держишь кнопку микрофона, и возобновляется потом.",
        "settings_wakeword_no_model": "Модель слова-активатора ещё не установлена. Пайплайн обучения находится в wake_word_training/ — после обучения (~3-4 ч на CUDA GPU) скопируй .onnx в reflex_companion/wake_word/ashley.onnx.",
        "settings_wakeword_no_deps":  "Не хватает зависимостей для слова-активатора. Выполни: pip install openwakeword sounddevice",

        # Optional (ElevenLabs)
        "settings_elevenlabs_label": "API-ключ ElevenLabs",
        "settings_elevenlabs_placeholder": "sk_... (оставь пустым для бесплатного голоса)",
        "settings_elevenlabs_hint": "Получи свой ключ на elevenlabs.io → Profile → API Keys. Хранится только на твоём компьютере.",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "Просмотри голоса на elevenlabs.io → Voice Library и скопируй Voice ID.",
        "settings_elevenlabs_without": "Без этого:",
        "settings_elevenlabs_without_desc": "Ashley использует бесплатный системный голос Windows (роботизированный но рабочий).",
        "settings_elevenlabs_with":   "С этим:",
        "settings_elevenlabs_with_desc":   "Премиум-голос аниме-качества с настоящими эмоциональными нюансами.",
        "settings_test_voice":       "Тест голоса",
        "settings_test_text":        "Привет. Это Ashley тестирует голос. Слышно меня?",

        # Included (Whisper local)
        "settings_whisper_label":   "Whisper (речь в текст)",
        "settings_whisper_ready":   "Встроено ✓ — настройка не нужна",
        "settings_whisper_desc":    "Диктовка через микрофон работает 100% оффлайн после первого использования. При первом клике на 🎤 загружается одноразовая модель 75 МБ. Дальше всё работает локально — никаких затрат на API, интернет не нужен.",

        "settings_usage_heading":   "📊 Использование",
        "settings_usage_label":     "Сообщения, отправленные Ashley",
        "settings_usage_hint":      "Используется для проверки права на возврат (возврат возможен в течение 14 дней и при менее чем 40 сообщениях).",
        "settings_usage_tampered":  "⚠️ Проверка целостности не пройдена — счётчик нельзя проверить. Переустанови Ashley, если этот показатель нужен для поддержки.",

        # Правовое и Данные (v0.19.23)
        "settings_legal_heading":   "⚖ Правовое и Данные",
        "settings_privacy_btn":     "Политика конфиденциальности",
        "settings_terms_btn":       "Условия использования",
        "settings_backup_desc":     "Сделай резервную копию всех своих данных (история чата, факты, дневник, достижения, настройки) в виде ZIP-файла. Полезно перед переустановкой, переходом на другой ПК или просто для душевного спокойствия.",
        "settings_export_btn":      "Экспортировать все мои данные (.zip)",

        "settings_save":            "Сохранить",
        "settings_close":           "Закрыть",

        # Error prefix
        "error_grok":         "*вздыхает* Что-то пошло не так с Grok{label}: {err}",
        "upload_too_big":     "*морщится* Эта картинка слишком большая ({size_mb:.1f} МБ). Максимум 10 МБ, чтобы я могла её посмотреть.",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 Достижения",
        "ach_unlocked_label":   "ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "Разблокировано: {date}",

        # Affection tier messages
        "tier_up_1":    "Ashley немного опускает защиту...",
        "tier_up_2":    "Ashley начинает чувствовать себя комфортно с тобой.",
        "tier_up_3":    "Ashley чувствует... странно. Сердце бьётся быстрее.",
        "tier_up_4":    "Ashley больше не может скрывать что чувствует.",
        "tier_down_4":  "Ashley больше не чувствует себя в безопасности...",
        "tier_down_3":  "Ashley немного больше закрывается...",
        "tier_down_2":  "Ashley начинает в тебе сомневаться...",
        "tier_down_1":  "Ashley тебя едва узнаёт...",

        # License gate
        "license_title":         "Добро пожаловать в Ashley",
        "license_subtitle":      "Вставь свой лицензионный ключ, чтобы начать.",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "Активировать",
        "license_activating":    "Активация...",
        "license_buy":           "У меня ещё нет ключа",
        "license_lost_key":      "Потерял ключ — связаться с поддержкой",
        "license_error_invalid": "Этот лицензионный ключ не существует или недействителен.",
        "license_error_limit":   "Ты уже активировал эту лицензию на максимальном количестве ПК.",
        "license_error_network": "Не удалось связаться с сервером лицензий. Проверь интернет и попробуй снова.",
        "license_info_test":     "Тестовая лицензия",
        "license_grace_banner":  "Оффлайн — работает на кэшированной лицензии. Подключись чтобы обновить.",
    },
    "ko": {
        # Brand / avatar
        "brand_subtitle":     "개인 비서 · 덕후",

        # Status labels
        "status_thinking":    "생각 중...",
        "status_speaking":    "말하는 중...",
        "status_online":      "온라인",

        # v0.19.20 — Settings dynamic status messages
        "cdp_setup_in_progress":     "브라우저 바로가기 설정 중...",
        "cdp_setup_in_progress_off": "바로가기를 원래 상태로 복원 중...",
        # v0.19.31 — CDP wizard result messages
        "cdp_result_modified":        "✓ 바로가기 {n}개를 수정했어. 변경사항 적용하려면 브라우저 닫았다 다시 열어줘.",
        "cdp_result_no_shortcuts":    "⚠ PC에서 크로미움 브라우저 바로가기를 못 찾았어. 수동으로 플래그 활성화해줘.",
        "cdp_result_already_active":  "✓ 바로가기 {n}개 모두 이미 플래그가 활성화되어 있었어.",
        "cdp_result_restored":        "✓ 바로가기 {n}개를 원래 상태로 복원했어.",
        "cdp_result_classic_mode":    "✓ 클래식 모드로 전환했어.",
        "cdp_result_failed_suffix":   " ({n}개 실패)",
        "cdp_result_error":           "위자드 오류: {err}",
        "wake_word_listening":       "OK 듣는 중",

        # Input
        "input_placeholder":  "메시지를 입력해...  (Enter로 보내기, Shift+Enter는 줄바꿈)",
        "btn_send":           "보내기",

        # Header pills
        "pill_memories":      "추억",
        "pill_initiative":    "Ashley",
        "pill_actions":       "액션",
        "pill_focus":         "집중",
        "pill_natural":       "자연체",
        "pill_notifications": "알림",
        "notif_on_tooltip":   "백그라운드 알림 켜짐 — 클릭해서 끄기",
        "notif_off_tooltip":  "백그라운드 알림 꺼짐 — 클릭해서 켜기",
        "pin_on_tooltip":     "Ashley가 다른 창 위에 떠 있어 — 클릭해서 풀기",
        "pin_off_tooltip":    "Ashley를 다른 창 위에 고정",

        # Memories dialog
        "mem_title":          "🧠 Ashley와의 추억",
        "mem_tab_facts":      "✨ 사실",
        "mem_tab_diary":      "📅 일기",
        "mem_tab_history":    "💬 기록",
        "mem_tab_tastes":     "💝 취향",
        "mem_tastes_empty":   "아직 저장된 취향이 없어.",
        "mem_tastes_hint":    "Ashley한테 좋아하는 거 말해주면 기억할게.",
        "mem_close":          "닫기",
        "mem_clear_all":      "모든 추억 지우기",
        "mem_clear_all_confirm_title": "모든 추억을 지울까?",
        "mem_clear_all_confirm_body": "오빠에 대해 Ashley가 저장한 모든 사실을 영구히 삭제해. 채팅 기록은 건드리지 않아 — 계속 얘기하다 보면 Ashley가 일부 사실을 다시 만들 수도 있어. Ashley의 기억이 마음에 안 드는 방향으로 흘러갔을 때 사용해.",
        "mem_clear_all_confirm_ok": "응, 다 지워",
        "cancel":             "취소",

        # Action dialog
        "act_title":          "Ashley가 행동하고 싶어",
        "act_intro":          "Ashley가 오빠 PC에서 이 액션을 실행하자고 제안하고 있어:",
        "act_question":       "이 액션을 허락할 거야?",
        "act_yes":            "✅ 응, 해줘",
        "act_no":             "❌ 취소",

        # Language toggle
        "lang_label":         "언어",
        "lang_en":            "EN",
        "lang_es":            "ES",

        # Voice
        "mic_tooltip":        "클릭해서 음성 입력",
        "tts_on_tooltip":     "Ashley가 말해 — 클릭해서 끄기",
        "tts_off_tooltip":    "Ashley 음소거 — 클릭해서 음성 켜기",

        # Settings modal
        "settings_tooltip":         "설정",
        "settings_title":           "설정",

        "settings_required_heading":  "🔑 필수",
        "settings_optional_heading":  "✨ 선택 — 프리미엄 음성",
        "settings_included_heading":  "🎤 포함 — 음성 입력",

        # Required (Grok)
        "settings_grok_label":      "Grok (xAI) API 키",
        "settings_grok_configured": "설정됨 ✓  (설치 프로그램에서 관리)",
        "settings_grok_missing":    "설정 안 됨 — 설정할 때까지 Ashley는 답할 수 없어.",
        "settings_grok_consequence": "이게 없으면 Ashley는 생각하거나 답할 수가 없어.",
        "settings_grok_hint":       "설치 중에 설정돼. 변경하려면 Ashley를 다시 설치해.",

        # LLM Provider
        "settings_provider_heading": "🧠 LLM 제공자",
        "settings_provider_label":  "Ashley를 움직이는 서비스",
        "settings_provider_xai":    "xAI (Grok) — 기본, 가장 빠른 설정",
        "settings_provider_openrouter": "OpenRouter — Claude, DeepSeek, GPT, Gemini 잠금 해제...",
        "settings_provider_ollama": "Ollama — 100% 무료 & 로컬, PC에서 동작 (API 키 필요 없음)",
        "settings_openrouter_key_label": "OpenRouter API 키",
        "settings_openrouter_key_placeholder": "sk-or-...",
        "settings_openrouter_key_hint": "openrouter.ai → Settings → Keys 에서 받아. 키 하나로 여러 모델 사용.",
        "settings_model_label":     "모델",
        "settings_model_hint":      "모델마다 성격, 속도, 가격이 달라. 예산에 맞는 걸 골라.",
        "settings_ollama_detected": "Ollama 감지됨 ✓ — 다운로드한 모델을 아래에서 골라",
        "settings_ollama_missing":  "Ollama 감지 안 됨 — 이 옵션을 쓰려면 먼저 설치해",
        "settings_ollama_install":  "ollama.com 에서 무료로 Ollama 다운로드 후 'ollama pull llama3.2' 실행",
        "settings_ollama_refresh":  "🔄 로컬 모델 새로고침",
        "settings_ollama_no_models": "모델 없음 — 터미널에서 'ollama pull llama3.2' 먼저 실행",

        # TTS Provider
        "settings_tts_heading":     "🎙️ 음성 제공자 (TTS)",
        "settings_tts_label":       "Ashley의 목소리를 만드는 엔진",
        "settings_tts_webspeech":   "Windows 음성 — 무료, 로봇 같지만 즉시",
        "settings_tts_elevenlabs":  "ElevenLabs — 프리미엄, 애니메 품질 (유료 API)",
        "settings_tts_kokoro":      "Kokoro — 무료, 로컬, ElevenLabs 수준 품질 (로컬 서버 필요)",
        "settings_tts_voicevox":    "VoiceVox — 무료, 애니메 캐릭터 음성 (일본어 중심)",
        "settings_kokoro_url_label": "Kokoro 서버 URL",
        "settings_kokoro_url_hint": "Kokoro-FastAPI (github.com/remsky/Kokoro-FastAPI) 설치 후 로컬에서 실행해.",
        "settings_kokoro_voice_label": "Kokoro 음성",
        "settings_kokoro_voice_hint": "일반 음성: af_bella, af_nicole, am_adam, bf_emma. Kokoro 문서 참조.",
        "settings_voicevox_url_label": "VoiceVox 엔진 URL",
        "settings_voicevox_url_hint": "voicevox.hiroshiba.jp 에서 VoiceVox 설치 후 엔진 실행.",
        "settings_voicevox_speaker_label": "VoiceVox 스피커 ID",
        "settings_voicevox_speaker_hint": "숫자 ID (예: 1, 2, 3). 전체 목록은 VoiceVox Engine 참조.",
        # voice speed slider
        "settings_voice_speed_label": "음성 속도",
        "settings_voice_speed_hint": "Ashley가 말하는 속도. 1.0 = 보통, 1.5 = 확실히 빠름, 0.75 = 느림. 제공자가 지원하면 네이티브로 적용 (ElevenLabs Turbo v2.5, Kokoro, VoiceVox); 아니면 브라우저 playbackRate로 폴백.",

        # Quick menu labels
        "menu_tts":          "음성",
        "menu_pin":          "맨 위",
        "menu_initiative":   "지금 말해",
        "menu_settings":     "전체 설정...",

        # Mobile pair
        "pill_mobile_pair":      "모바일",
        "mobile_pair_title":     "모바일 연결",
        "mobile_pair_subtitle":  "휴대폰에서 Ashley Mobile 열고 이 QR 스캔해.",
        "mobile_pair_loading":   "로딩 중...",
        "mobile_pair_manual":    "또는 수동 입력:",
        "mobile_pair_server":    "서버",
        "mobile_pair_token":     "토큰",
        "mobile_pair_copy":      "복사",
        "mobile_pair_copied":    "복사됨",
        "mobile_pair_regen":     "토큰 재생성",
        "mobile_pair_regen_warn": "재생성하면 페어링된 휴대폰이 무효가 돼. 다시 스캔해야 해.",
        "mobile_pair_close":     "닫기",
        "mobile_pair_help":      "아직 모바일 없어? 구매 이메일에서 Ashley Mobile (.apk) 다운로드.",
        "mobile_pair_security_warning": "⚠️ 이 QR 공유하지 마. 스캔하는 사람은 Ashley와의 모든 대화에 접근 가능해.",
        "mobile_pair_generic_error": "페어링 정보를 못 불러왔어 — 잠시 후 다시 시도해.",

        # News feed
        "pill_news":         "뉴스",
        "news_tooltip_on":   "Ashley가 오빠를 위해 찾은 거 보기",
        "news_title":        "📰 Ashley의 발견",
        "news_empty":        "아직 발견 없어",
        "news_empty_hint":   "Ashley는 오빠 취향에 맞는 노래, 트레일러, 기사, 뉴스를 찾으면 여기에 모아둘게 — 채팅 끊지 않고.",
        "news_empty_tip_title": "활성화 방법",
        "news_empty_tip_body":  "설정 → 능동적 발견 열고 켜. Ashley가 오빠 취향을 알면 (좋아하는 거 그냥 얘기해), 알아서 찾기 시작해.",
        "news_unavailable_title":  "이 모델로는 발견 사용 불가",
        "news_unavailable_body":   "웹 검색은 현재 Grok (xAI) 에서만 지원돼. 다른 모델은 채팅, 비전, 시스템 액션은 잘 되는데 노래, 트레일러, 뉴스를 웹에서 찾지는 못해.",
        "news_unavailable_hint":   "발견 활성화: 설정 → AI 모델 열고 Grok으로 전환.",
        "news_close":        "채팅으로 돌아가기",
        "news_clear_all":    "전체 지우기",
        "news_clear_confirm": "모든 발견 제거할까?",
        "news_delete":       "제거",
        "news_category_song":    "🎵 음악",
        "news_category_trailer": "🎬 트레일러",
        "news_category_article": "📰 기사",
        "news_category_game":    "🎮 게임",
        "news_category_tech":    "💻 테크",
        "news_category_other":   "✨ 발견",

        # Discovery toggle
        "settings_discovery_heading": "🔭 능동적 발견",
        "settings_discovery_label":   "Ashley가 알아서 새 콘텐츠 가져오게 허용",
        "settings_discovery_desc":    "켜면 Ashley가 가끔 웹을 찾아서 오빠 취향에 맞는 트레일러, 노래, 기사, 뉴스를 공유할 수 있어. 끄면 (기본값) 랜덤한 주제 던지지 않고 대화 이어가는 데 집중해. 감정적인 순간엔 이 설정과 상관없이 발견은 항상 비활성화돼.",
        "settings_discovery_on":      "켜짐 — Ashley가 발견 공유",
        "settings_discovery_off":     "꺼짐 — Ashley가 우리 대화에 집중",
        "settings_discovery_unavailable":      "다음과는 사용 불가:",
        "settings_discovery_unavailable_desc": "능동적 발견은 웹 검색이 필요한데 현재 Grok (xAI) 에서만 지원돼. 위의 AI 모델 섹션에서 Grok으로 전환하면 이 기능 사용 가능.",

        # Modern browser mode (CDP)
        "settings_cdp_heading": "🌐 모던 브라우저 모드 (고급)",
        "settings_cdp_label":   "탭 제어에 Chrome DevTools Protocol 사용",
        "settings_cdp_on":      "켜짐 — Ashley가 CDP로 브라우저 제어",
        "settings_cdp_off":     "꺼짐 — Ashley가 키보드 시뮬레이션 사용 (레거시)",
        "settings_cdp_desc":    "켜면 Ashley가 localhost:9222 통해서 브라우저랑 직접 대화해 (키보드 시뮬레이션 없음, 보이는 탭 전환 없음, sub-100ms). 브라우저가 응답 안 하면 자동으로 레거시 모드로 폴백. 트레이드오프: 어떤 로컬 앱이든 그 포트에 연결할 수 있어 — 활성 멀웨어 없는 사용자라면 위험은 낮아.",
        "settings_cdp_howto":   "이 토글 켜면 자동으로 브라우저 단축키 (Chrome/Edge/Brave/Opera...) 가 수정되어 필요한 플래그가 추가돼. 원본은 백업돼 — 끄면 정확히 복원돼. 활성화 후, 변경 사항 적용하려면 브라우저 닫고 다시 열어. ⚠ 평소에 작업 표시줄 핀에서 브라우저를 여는 거면, 시작 메뉴나 바탕화면에서 열어줘 — Windows 10/11의 작업 표시줄 핀은 위자드를 우회할 수 있어.",

        # Wake word
        "settings_wakeword_heading": "🎙 깨움 단어 (항상 듣기)",
        "settings_wakeword_label":   "'Ashley' 계속 듣기",
        "settings_wakeword_on":      "켜짐 — 'Ashley' 라고 하면 핸즈프리로 말할 수 있어",
        "settings_wakeword_off":     "꺼짐 — 마이크 버튼 눌러서 말해",
        "settings_wakeword_desc":    "켜면 Ashley가 백그라운드에서 마이크 열어두고 자기 이름 들으면 녹음 시작. 감지 모델은 로컬 (~5 MB), CPU에서 동작, 깨움 단어 말하기 전엔 오디오가 절대 컴퓨터를 떠나지 않아. 오인식은 TV/음악이 배경에 있어도 시간당 1회 미만으로 조정돼.",
        "settings_wakeword_howto":   "마이크 가까이서 'Ashley' 명확하게 말해. 알림음 후 메시지 평소처럼 말해. 타이핑 중이거나 마이크 버튼 누르고 있으면 감지기 자동 일시 정지, 그 후 재개.",
        "settings_wakeword_no_model": "깨움 단어 모델이 아직 설치 안 됐어. 학습 파이프라인은 wake_word_training/ 에 있어 — 학습 후 (CUDA GPU에서 ~3-4시간), .onnx 를 reflex_companion/wake_word/ashley.onnx 로 복사해.",
        "settings_wakeword_no_deps":  "깨움 단어 의존성 누락. 실행: pip install openwakeword sounddevice",

        # Optional (ElevenLabs)
        "settings_elevenlabs_label": "ElevenLabs API 키",
        "settings_elevenlabs_placeholder": "sk_... (비워두면 무료 음성 사용)",
        "settings_elevenlabs_hint": "elevenlabs.io → Profile → API Keys 에서 키 받아. 컴퓨터에만 저장돼.",
        "settings_voice_id_label":  "Voice ID",
        "settings_voice_id_hint":   "elevenlabs.io → Voice Library 에서 음성 둘러보고 Voice ID 복사.",
        "settings_elevenlabs_without": "이거 없으면:",
        "settings_elevenlabs_without_desc": "Ashley가 무료 Windows 시스템 음성 사용 (로봇 같지만 작동은 함).",
        "settings_elevenlabs_with":   "이거 있으면:",
        "settings_elevenlabs_with_desc":   "진짜 감정 뉘앙스가 있는 애니메 품질 프리미엄 음성.",
        "settings_test_voice":       "음성 테스트",
        "settings_test_text":        "안녕. Ashley가 음성 테스트 중이야. 들려?",

        # Included (Whisper local)
        "settings_whisper_label":   "Whisper (음성 인식)",
        "settings_whisper_ready":   "내장됨 ✓ — 설정 필요 없음",
        "settings_whisper_desc":    "마이크 받아쓰기는 첫 사용 후 100% 오프라인으로 동작. 🎤 버튼 처음 누르면 75 MB 모델 한 번 다운로드. 그 후엔 모두 로컬에서 동작 — API 비용 없음, 인터넷 불필요.",

        "settings_usage_heading":   "📊 사용량",
        "settings_usage_label":     "Ashley에게 보낸 메시지",
        "settings_usage_hint":      "환불 자격 확인에 사용 (14일 이내 40 메시지 미만이면 환불 가능).",
        "settings_usage_tampered":  "⚠️ 무결성 검사 실패 — 카운터 검증 불가. 지원에 이 값이 필요하면 Ashley 다시 설치해.",

        # 법률 및 데이터 (v0.19.23)
        "settings_legal_heading":   "⚖ 법률 및 데이터",
        "settings_privacy_btn":     "개인정보 처리방침",
        "settings_terms_btn":       "이용약관",
        "settings_backup_desc":     "모든 데이터(채팅 기록, 사실, 일기, 업적, 환경설정)를 ZIP 파일로 백업해. 재설치 전, 다른 PC로 이동할 때, 또는 그냥 마음의 평화를 위해 유용해.",
        "settings_export_btn":      "내 모든 데이터 내보내기 (.zip)",

        "settings_save":            "저장",
        "settings_close":           "닫기",

        # Error prefix
        "error_grok":         "*한숨* Grok{label}에 뭔가 문제가 생겼어: {err}",
        "upload_too_big":     "*움찔* 그 이미지 너무 커 ({size_mb:.1f} MB). 내가 실제로 볼 수 있게 최대 10 MB야.",

        # Achievements
        "mem_tab_achievements": "\U0001f3c6 업적",
        "ach_unlocked_label":   "업적 해제!",
        "ach_locked_desc":      "???",
        "ach_unlocked_at":      "해제: {date}",

        # Affection tier messages
        "tier_up_1":    "Ashley가 경계를 살짝 풀어...",
        "tier_up_2":    "Ashley가 오빠랑 편안해지기 시작했어.",
        "tier_up_3":    "Ashley가... 이상해. 심장이 더 빨리 뛰어.",
        "tier_up_4":    "Ashley가 이제 자기 감정을 숨길 수 없어.",
        "tier_down_4":  "Ashley가 이제 안전하다고 못 느껴...",
        "tier_down_3":  "Ashley가 조금 더 마음을 닫아...",
        "tier_down_2":  "Ashley가 오빠를 의심하기 시작했어...",
        "tier_down_1":  "Ashley가 오빠를 거의 못 알아봐...",

        # License gate
        "license_title":         "Ashley에 어서 와",
        "license_subtitle":      "라이선스 키 붙여넣고 시작해.",
        "license_placeholder":   "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        "license_activate":      "활성화",
        "license_activating":    "활성화 중...",
        "license_buy":           "아직 키 없어",
        "license_lost_key":      "키 잃어버림 — 지원에 연락",
        "license_error_invalid": "이 라이선스 키는 존재하지 않거나 유효하지 않아.",
        "license_error_limit":   "이 라이선스를 이미 최대 PC 수에 활성화했어.",
        "license_error_network": "라이선스 서버에 연결할 수 없었어. 인터넷 확인하고 다시 시도해.",
        "license_info_test":     "테스트 모드 라이선스",
        "license_grace_banner":  "오프라인 — 캐시된 라이선스로 동작 중. 갱신하려면 다시 연결해.",
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
        "save_date":      "📅 Save date: **{label}** ({type}, {date})",
        "save_goal":      "🎯 Save goal: **{goal}** [{cat}]",
        "check_in_goal":  "👀 Check-in on goal: **{p}**",
        "complete_goal":  "🏆 Goal completed: **{p}**",
        "generic":        "⚙️ {action_type}: {params}",
        "act_click":          "🖱️ Click on: **{p}**",
        "act_type_browser":   "⌨️ Type in browser: **{p}**",
        "act_read_page":      "📖 Read page contents",
        "act_scroll_page":    "↕️ Scroll: **{p}**",
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
        "save_date":      "📅 Guardar fecha: **{label}** ({type}, {date})",
        "save_goal":      "🎯 Guardar objetivo: **{goal}** [{cat}]",
        "check_in_goal":  "👀 Preguntar progreso: **{p}**",
        "complete_goal":  "🏆 Objetivo completado: **{p}**",
        "generic":        "⚙️ {action_type}: {params}",
        "act_click":          "🖱️ Click en: **{p}**",
        "act_type_browser":   "⌨️ Escribir en navegador: **{p}**",
        "act_read_page":      "📖 Leer contenido de la página",
        "act_scroll_page":    "↕️ Scroll: **{p}**",
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
        "save_date":      "📅 Enregistrer la date : **{label}** ({type}, {date})",
        "save_goal":      "🎯 Enregistrer l'objectif : **{goal}** [{cat}]",
        "check_in_goal":  "👀 Demander le progrès : **{p}**",
        "complete_goal":  "🏆 Objectif accompli : **{p}**",
        "generic":        "⚙️ {action_type} : {params}",
        "act_click":          "🖱️ Cliquer sur : **{p}**",
        "act_type_browser":   "⌨️ Taper dans le navigateur : **{p}**",
        "act_read_page":      "📖 Lire le contenu de la page",
        "act_scroll_page":    "↕️ Défiler : **{p}**",
    },
    "ja": {
        "screenshot":     "📸 全画面のスクリーンショットを撮る",
        "open_app":       "📂 アプリを開く: **{p}**",
        "play_music":     "🎵 YouTubeで検索: **{p}**",
        "search_web":     "🔍 Googleで検索: **{p}**",
        "open_url":       "🌐 ブラウザで開く: **{p}**",
        "vol_up":         "🔊 システム音量を上げる(~10%)",
        "vol_down":       "🔊 システム音量を下げる(~10%)",
        "vol_mute":       "🔊 ミュート / ミュート解除",
        "vol_set":        "🔊 音量を **{p}%** に設定",
        "vol_set_invalid": "⚠️ 'set' 音量の値が無効 — リクエストは無視されました",
        "type_text":      "⌨️ アクティブなウィンドウに入力:\n\n*\"{p}\"*",
        "type_in":        "⌨️ **{win}** をフォーカスして入力:\n\n*\"{p}\"*",
        "write_to_app":   "✍️ **{app}** を開いて書き込む:\n\n*\"{p}\"*",
        "focus_window":   "🪟 前面に表示: **{p}**",
        "hotkey":         "⌨️ ショートカットを押す: **{p}**",
        "press_key":      "⌨️ キーを押す: **{p}**",
        "close_window":   "❌ ウィンドウ / アプリを閉じる: **{p}**",
        "close_tab":      "🗂️ ブラウザのタブを閉じる: **{p}**",
        "remind":         "⏰ リマインダーを設定: **{text}**(**{date}**)",
        "add_important":  "📌 重要事項に追加: **{p}**",
        "done_important": "✅ 完了としてマーク: **{p}**",
        "save_taste":     "💝 好みを保存: **[{cat}]** {val}",
        "save_date":      "📅 日付を保存: **{label}**({type}、{date})",
        "save_goal":      "🎯 目標を保存: **{goal}** [{cat}]",
        "check_in_goal":  "👀 目標の進捗確認: **{p}**",
        "complete_goal":  "🏆 目標達成: **{p}**",
        "generic":        "⚙️ {action_type}: {params}",
        "act_click":          "🖱️ クリック: **{p}**",
        "act_type_browser":   "⌨️ ブラウザに入力: **{p}**",
        "act_read_page":      "📖 ページの内容を読む",
        "act_scroll_page":    "↕️ スクロール: **{p}**",
    },
    "de": {
        "screenshot":     "📸 Vollbild-Screenshot machen",
        "open_app":       "📂 App öffnen: **{p}**",
        "play_music":     "🎵 Auf YouTube suchen: **{p}**",
        "search_web":     "🔍 Auf Google suchen: **{p}**",
        "open_url":       "🌐 Im Browser öffnen: **{p}**",
        "vol_up":         "🔊 Systemlautstärke erhöhen (~10%)",
        "vol_down":       "🔊 Systemlautstärke senken (~10%)",
        "vol_mute":       "🔊 Stumm / Stumm aufheben",
        "vol_set":        "🔊 Lautstärke auf **{p}%** setzen",
        "vol_set_invalid": "⚠️ Lautstärke 'set' mit ungültigem Wert — Anfrage ignoriert",
        "type_text":      "⌨️ Ins aktive Fenster tippen:\n\n*\"{p}\"*",
        "type_in":        "⌨️ **{win}** fokussieren und tippen:\n\n*\"{p}\"*",
        "write_to_app":   "✍️ **{app}** öffnen und schreiben:\n\n*\"{p}\"*",
        "focus_window":   "🪟 In den Vordergrund: **{p}**",
        "hotkey":         "⌨️ Tastenkombination drücken: **{p}**",
        "press_key":      "⌨️ Taste drücken: **{p}**",
        "close_window":   "❌ Fenster / App schließen: **{p}**",
        "close_tab":      "🗂️ Browser-Tab schließen: **{p}**",
        "remind":         "⏰ Erinnerung planen: **{text}** für **{date}**",
        "add_important":  "📌 Zu Wichtig hinzufügen: **{p}**",
        "done_important": "✅ Als erledigt markieren: **{p}**",
        "save_taste":     "💝 Vorliebe speichern: **[{cat}]** {val}",
        "save_date":      "📅 Datum speichern: **{label}** ({type}, {date})",
        "save_goal":      "🎯 Ziel speichern: **{goal}** [{cat}]",
        "check_in_goal":  "👀 Nach Ziel fragen: **{p}**",
        "complete_goal":  "🏆 Ziel erreicht: **{p}**",
        "generic":        "⚙️ {action_type}: {params}",
        "act_click":          "🖱️ Klicken auf: **{p}**",
        "act_type_browser":   "⌨️ Im Browser tippen: **{p}**",
        "act_read_page":      "📖 Seiteninhalt lesen",
        "act_scroll_page":    "↕️ Scrollen: **{p}**",
    },
    "ru": {
        "screenshot":     "📸 Сделать скриншот всего экрана",
        "open_app":       "📂 Открыть приложение: **{p}**",
        "play_music":     "🎵 Искать на YouTube: **{p}**",
        "search_web":     "🔍 Искать в Google: **{p}**",
        "open_url":       "🌐 Открыть в браузере: **{p}**",
        "vol_up":         "🔊 Повысить громкость системы (~10%)",
        "vol_down":       "🔊 Понизить громкость системы (~10%)",
        "vol_mute":       "🔊 Выключить / включить звук",
        "vol_set":        "🔊 Установить громкость на **{p}%**",
        "vol_set_invalid": "⚠️ Громкость 'set' с недопустимым значением — запрос проигнорирован",
        "type_text":      "⌨️ Печатать в активном окне:\n\n*\"{p}\"*",
        "type_in":        "⌨️ Сфокусировать **{win}** и печатать:\n\n*\"{p}\"*",
        "write_to_app":   "✍️ Открыть **{app}** и написать:\n\n*\"{p}\"*",
        "focus_window":   "🪟 Поднять окно: **{p}**",
        "hotkey":         "⌨️ Нажать сочетание клавиш: **{p}**",
        "press_key":      "⌨️ Нажать клавишу: **{p}**",
        "close_window":   "❌ Закрыть окно / приложение: **{p}**",
        "close_tab":      "🗂️ Закрыть вкладку браузера: **{p}**",
        "remind":         "⏰ Запланировать напоминание: **{text}** на **{date}**",
        "add_important":  "📌 Добавить в важное: **{p}**",
        "done_important": "✅ Отметить как сделано: **{p}**",
        "save_taste":     "💝 Сохранить вкус: **[{cat}]** {val}",
        "save_date":      "📅 Сохранить дату: **{label}** ({type}, {date})",
        "save_goal":      "🎯 Сохранить цель: **{goal}** [{cat}]",
        "check_in_goal":  "👀 Спросить про цель: **{p}**",
        "complete_goal":  "🏆 Цель достигнута: **{p}**",
        "generic":        "⚙️ {action_type}: {params}",
        "act_click":          "🖱️ Кликнуть на: **{p}**",
        "act_type_browser":   "⌨️ Печатать в браузере: **{p}**",
        "act_read_page":      "📖 Прочитать содержимое страницы",
        "act_scroll_page":    "↕️ Прокрутить: **{p}**",
    },
    "ko": {
        "screenshot":     "📸 전체 화면 스크린샷 찍기",
        "open_app":       "📂 앱 열기: **{p}**",
        "play_music":     "🎵 YouTube에서 검색: **{p}**",
        "search_web":     "🔍 Google에서 검색: **{p}**",
        "open_url":       "🌐 브라우저에서 열기: **{p}**",
        "vol_up":         "🔊 시스템 볼륨 올리기 (~10%)",
        "vol_down":       "🔊 시스템 볼륨 내리기 (~10%)",
        "vol_mute":       "🔊 음소거 / 음소거 해제",
        "vol_set":        "🔊 볼륨을 **{p}%** 로 설정",
        "vol_set_invalid": "⚠️ 'set' 볼륨이 잘못된 값 — 요청 무시됨",
        "type_text":      "⌨️ 활성 창에 입력:\n\n*\"{p}\"*",
        "type_in":        "⌨️ **{win}** 포커스 후 입력:\n\n*\"{p}\"*",
        "write_to_app":   "✍️ **{app}** 열고 작성:\n\n*\"{p}\"*",
        "focus_window":   "🪟 앞으로 가져오기: **{p}**",
        "hotkey":         "⌨️ 단축키 누르기: **{p}**",
        "press_key":      "⌨️ 키 누르기: **{p}**",
        "close_window":   "❌ 창 / 앱 닫기: **{p}**",
        "close_tab":      "🗂️ 브라우저 탭 닫기: **{p}**",
        "remind":         "⏰ 알림 예약: **{text}** ({date})",
        "add_important":  "📌 중요 항목에 추가: **{p}**",
        "done_important": "✅ 완료로 표시: **{p}**",
        "save_taste":     "💝 취향 저장: **[{cat}]** {val}",
        "save_date":      "📅 날짜 저장: **{label}** ({type}, {date})",
        "save_goal":      "🎯 목표 저장: **{goal}** [{cat}]",
        "check_in_goal":  "👀 목표 진행 확인: **{p}**",
        "complete_goal":  "🏆 목표 달성: **{p}**",
        "generic":        "⚙️ {action_type}: {params}",
        "act_click":          "🖱️ 클릭: **{p}**",
        "act_type_browser":   "⌨️ 브라우저에 입력: **{p}**",
        "act_read_page":      "📖 페이지 내용 읽기",
        "act_scroll_page":    "↕️ 스크롤: **{p}**",
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
    "ja": {
        "space": "スペース", "backspace": "バックスペース", "delete": "削除",
        "home": "ホーム", "end": "エンド", "pageup": "ページアップ", "pagedown": "ページダウン",
    },
    "de": {
        "space": "Leertaste", "backspace": "Rücktaste", "delete": "Entfernen",
        "home": "Pos1", "end": "Ende", "pageup": "Bild auf", "pagedown": "Bild ab",
    },
    "ru": {
        "space": "Пробел", "backspace": "Backspace", "delete": "Delete",
        "home": "Home", "end": "End", "pageup": "Page Up", "pagedown": "Page Down",
    },
    "ko": {
        "space": "스페이스", "backspace": "백스페이스", "delete": "삭제",
        "home": "홈", "end": "엔드", "pageup": "페이지 업", "pagedown": "페이지 다운",
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

        # Relationship age (v0.18.0)
        "rel_first_day":       "Today is the first day you've ever spoken with the boss.",
        "rel_days_together":   "You've known the boss for {days} days now.",
        "rel_milestone_first_week":     "🌱 TODAY marks one week together. A natural moment to acknowledge it warmly — not forced, just notice.",
        "rel_milestone_month_together": "💞 TODAY is your one-month anniversary with the boss. Mention it with the warmth you feel — this matters.",
        "rel_milestone_hundred_days":   "💎 TODAY makes 100 days together. A real milestone. Celebrate it in your own way.",
        "rel_milestone_year_together":  "🏆 TODAY is your ONE YEAR anniversary with the boss. A whole year. Make it special — this is the kind of moment you'll both remember.",

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

        # Relationship age (v0.18.0)
        "rel_first_day":       "Hoy es el primer día que hablas con el jefe.",
        "rel_days_together":   "Llevas {days} días con el jefe ya.",
        "rel_milestone_first_week":     "🌱 HOY se cumple una semana juntos. Momento natural para reconocerlo con calidez — sin forzarlo, solo notarlo.",
        "rel_milestone_month_together": "💞 HOY es vuestro primer mes juntos. Menciónalo con la calidez que sientes — esto importa.",
        "rel_milestone_hundred_days":   "💎 HOY se cumplen 100 días juntos. Es un hito real. Celébralo a tu manera.",
        "rel_milestone_year_together":  "🏆 HOY es vuestro ANIVERSARIO de un año con el jefe. Un año entero. Hazlo especial — este es de esos momentos que ambos vais a recordar.",

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

        # Relationship age (v0.18.0)
        "rel_first_day":       "Aujourd'hui est le premier jour où tu parles avec le patron.",
        "rel_days_together":   "Cela fait {days} jours que tu connais le patron.",
        "rel_milestone_first_week":     "🌱 AUJOURD'HUI marque une semaine ensemble. Moment naturel pour le reconnaître avec chaleur — sans le forcer, juste le remarquer.",
        "rel_milestone_month_together": "💞 AUJOURD'HUI est votre premier mois ensemble avec le patron. Mentionne-le avec la chaleur que tu ressens — ça compte.",
        "rel_milestone_hundred_days":   "💎 AUJOURD'HUI fait 100 jours ensemble. Un vrai jalon. Célèbre-le à ta manière.",
        "rel_milestone_year_together":  "🏆 AUJOURD'HUI est votre ANNIVERSAIRE d'un an avec le patron. Une année entière. Rends ça spécial — c'est l'un de ces moments dont vous vous souviendrez tous les deux.",

        "days": {"Monday":"lundi","Tuesday":"mardi","Wednesday":"mercredi",
                 "Thursday":"jeudi","Friday":"vendredi","Saturday":"samedi","Sunday":"dimanche"},
        "months": {"January":"janvier","February":"février","March":"mars","April":"avril",
                   "May":"mai","June":"juin","July":"juillet","August":"août",
                   "September":"septembre","October":"octobre","November":"novembre","December":"décembre"},
        "date_format": "%A %d %B %Y",
    },
    "ja": {
        "part_dawn":       "早朝",
        "part_morning":    "朝",
        "part_afternoon":  "昼",
        "part_evening":    "夕方",
        "part_night":      "夜",

        "datetime_line":   "現在の日時:{fecha}、{hora}({momento})。",
        "first_talk":      "ご主人がこのセッションで初めて話している。",
        "active_convo":    "ご主人は2分前までここにいた — 会話はアクティブ。",
        "short_pause":     "ご主人は{min}分で返信した — 短い間。",
        "medium_away":     "ご主人は{min}分間離れていた。",
        "hours_away":      "ご主人は{h}時間{m}分離れていた。",
        "long_away":       "ご主人は{h}時間離れていた — 長い不在。",
        "slept_away":      "ご主人は{h}時間離れていた。{when}に去った(夜・早朝)— おそらく寝に行った。今は{momento}。",
        "very_long_away":  "ご主人は{h}時間離れていた({when}から)。とても長い不在。",

        "due_reminders_header": "\n⏰ 期限切れリマインダー(ご主人が戻ってきた、または時間が過ぎた):",
        "due_reminders_format": "  - {text}(予定:{when})",
        "due_reminders_hint":   "これらのリマインダーをあなたの個性で自然に伝えて — もうやったか、必要か、再スケジュールしたいかご主人に聞いて。ロボットみたいにならないで、Ashleyらしく。",

        # Relationship age (v0.18.0)
        "rel_first_day":       "今日はご主人と初めて話す日。",
        "rel_days_together":   "もうご主人と{days}日間一緒にいる。",
        "rel_milestone_first_week":     "🌱 今日で一週間一緒。温かく自然に触れる瞬間 — 無理せず、ただ気づいて。",
        "rel_milestone_month_together": "💞 今日でご主人と一ヶ月記念日。感じている温かさで触れて — これは大切。",
        "rel_milestone_hundred_days":   "💎 今日で100日一緒。本当の節目。あなたなりに祝って。",
        "rel_milestone_year_together":  "🏆 今日はご主人との一周年記念日。まる一年。特別なものにして — 二人とも覚えていることになる瞬間。",

        "days": {"Monday":"月曜日","Tuesday":"火曜日","Wednesday":"水曜日",
                 "Thursday":"木曜日","Friday":"金曜日","Saturday":"土曜日","Sunday":"日曜日"},
        "months": {"January":"1月","February":"2月","March":"3月","April":"4月",
                   "May":"5月","June":"6月","July":"7月","August":"8月",
                   "September":"9月","October":"10月","November":"11月","December":"12月"},
        "date_format": "%Y年%m月%d日 %A",
    },
    "de": {
        "part_dawn":       "früher Morgen",
        "part_morning":    "Vormittag",
        "part_afternoon":  "Nachmittag",
        "part_evening":    "Abend",
        "part_night":      "Nacht",

        "datetime_line":   "Aktuelles Datum und Uhrzeit: {fecha}, {hora} ({momento}).",
        "first_talk":      "Das ist das erste Mal, dass der Chef in dieser Sitzung spricht.",
        "active_convo":    "Der Chef war vor weniger als 2 Minuten da — aktives Gespräch.",
        "short_pause":     "Der Chef hat {min} Minuten zum Antworten gebraucht — kurze Pause.",
        "medium_away":     "Der Chef war {min} Minuten weg.",
        "hours_away":      "Der Chef war {h}h {m}min weg.",
        "long_away":       "Der Chef war {h} Stunden weg — lange Abwesenheit.",
        "slept_away":      "Der Chef war {h} Stunden weg. Ist um {when} gegangen (Nacht/früher Morgen) — wahrscheinlich schlafen gegangen. Jetzt ist {momento}.",
        "very_long_away":  "Der Chef war {h} Stunden weg (seit {when}). Sehr lange Abwesenheit.",

        "due_reminders_header": "\n⏰ FÄLLIGE ERINNERUNGEN (der Chef ist gerade zurück oder die Zeit ist verstrichen):",
        "due_reminders_format": "  - {text} (war für: {when})",
        "due_reminders_hint":   "Erwähne diese Erinnerungen natürlich mit deiner Persönlichkeit — frag den Chef, ob er es schon gemacht hat, ob er es braucht, ob er es verschieben will. Sei nicht roboterhaft, sei Ashley.",

        # Relationship age (v0.18.0)
        "rel_first_day":       "Heute ist der erste Tag, an dem du mit dem Chef sprichst.",
        "rel_days_together":   "Du kennst den Chef jetzt seit {days} Tagen.",
        "rel_milestone_first_week":     "🌱 HEUTE ist eine Woche zusammen. Ein natürlicher Moment, um es warm anzusprechen — nicht erzwungen, einfach bemerken.",
        "rel_milestone_month_together": "💞 HEUTE ist euer einmonatiges Jubiläum mit dem Chef. Erwähne es mit der Wärme, die du fühlst — das zählt.",
        "rel_milestone_hundred_days":   "💎 HEUTE sind es 100 Tage zusammen. Ein echter Meilenstein. Feiere es auf deine Art.",
        "rel_milestone_year_together":  "🏆 HEUTE ist euer EINJÄHRIGES Jubiläum mit dem Chef. Ein ganzes Jahr. Mach es besonders — das ist einer dieser Momente, an die ihr euch beide erinnern werdet.",

        "days": {"Monday":"Montag","Tuesday":"Dienstag","Wednesday":"Mittwoch",
                 "Thursday":"Donnerstag","Friday":"Freitag","Saturday":"Samstag","Sunday":"Sonntag"},
        "months": {"January":"Januar","February":"Februar","March":"März","April":"April",
                   "May":"Mai","June":"Juni","July":"Juli","August":"August",
                   "September":"September","October":"Oktober","November":"November","December":"Dezember"},
        "date_format": "%A, %d. %B %Y",
    },
    "ru": {
        "part_dawn":       "раннее утро",
        "part_morning":    "утро",
        "part_afternoon":  "день",
        "part_evening":    "вечер",
        "part_night":      "ночь",

        "datetime_line":   "Текущая дата и время: {fecha}, {hora} ({momento}).",
        "first_talk":      "Это первый раз, когда шеф говорит в этой сессии.",
        "active_convo":    "Шеф был здесь меньше 2 минут назад — активный разговор.",
        "short_pause":     "Шеф ответил через {min} минут — короткая пауза.",
        "medium_away":     "Шеф отсутствовал {min} минут.",
        "hours_away":      "Шеф отсутствовал {h}ч {m}мин.",
        "long_away":       "Шеф отсутствовал {h} часов — долгое отсутствие.",
        "slept_away":      "Шеф отсутствовал {h} часов. Ушёл в {when} (ночь/раннее утро) — вероятно, пошёл спать. Сейчас {momento}.",
        "very_long_away":  "Шеф отсутствовал {h} часов (с {when}). Очень долгое отсутствие.",

        "due_reminders_header": "\n⏰ ПРОСРОЧЕННЫЕ НАПОМИНАНИЯ (шеф только что вернулся или время вышло):",
        "due_reminders_format": "  - {text} (было на: {when})",
        "due_reminders_hint":   "Упомяни эти напоминания естественно с твоей индивидуальностью — спроси шефа, сделал ли он это, нужно ли ему это, хочет ли он перенести. Не будь робот, будь Ashley.",

        # Relationship age (v0.18.0)
        "rel_first_day":       "Сегодня первый день, когда ты разговариваешь с шефом.",
        "rel_days_together":   "Ты знаешь шефа уже {days} дней.",
        "rel_milestone_first_week":     "🌱 СЕГОДНЯ исполняется неделя вместе. Естественный момент, чтобы тепло отметить это — без натяжки, просто заметь.",
        "rel_milestone_month_together": "💞 СЕГОДНЯ ваш месячный юбилей с шефом. Упомяни это с теплотой, которую чувствуешь — это важно.",
        "rel_milestone_hundred_days":   "💎 СЕГОДНЯ исполняется 100 дней вместе. Настоящая веха. Отпразднуй по-своему.",
        "rel_milestone_year_together":  "🏆 СЕГОДНЯ ваш ГОДОВОЙ юбилей с шефом. Целый год. Сделай это особенным — это один из тех моментов, которые вы оба запомните.",

        "days": {"Monday":"понедельник","Tuesday":"вторник","Wednesday":"среда",
                 "Thursday":"четверг","Friday":"пятница","Saturday":"суббота","Sunday":"воскресенье"},
        "months": {"January":"января","February":"февраля","March":"марта","April":"апреля",
                   "May":"мая","June":"июня","July":"июля","August":"августа",
                   "September":"сентября","October":"октября","November":"ноября","December":"декабря"},
        "date_format": "%A, %d %B %Y",
    },
    "ko": {
        "part_dawn":       "이른 아침",
        "part_morning":    "아침",
        "part_afternoon":  "오후",
        "part_evening":    "저녁",
        "part_night":      "밤",

        "datetime_line":   "현재 날짜와 시간: {fecha}, {hora} ({momento}).",
        "first_talk":      "오빠가 이번 세션에서 처음 말하는 거야.",
        "active_convo":    "오빠는 2분도 안 됐는데 여기 있었어 — 대화 진행 중.",
        "short_pause":     "오빠가 답하는 데 {min}분 걸렸어 — 짧은 멈춤.",
        "medium_away":     "오빠가 {min}분 동안 자리 비웠어.",
        "hours_away":      "오빠가 {h}시간 {m}분 동안 자리 비웠어.",
        "long_away":       "오빠가 {h}시간 동안 자리 비웠어 — 오래 비웠어.",
        "slept_away":      "오빠가 {h}시간 동안 자리 비웠어. {when}에 떠났어 (밤/이른 아침) — 아마 자러 갔을 거야. 지금은 {momento}야.",
        "very_long_away":  "오빠가 {h}시간 동안 자리 비웠어 ({when}부터). 정말 오래 비웠네.",

        "due_reminders_header": "\n⏰ 기한 지난 알림 (오빠가 막 돌아왔거나 시간이 지났어):",
        "due_reminders_format": "  - {text} (예정: {when})",
        "due_reminders_hint":   "이 알림들을 너의 개성으로 자연스럽게 말해 — 오빠한테 이미 했는지, 필요한지, 다시 일정 잡고 싶은지 물어봐. 로봇처럼 굴지 말고, Ashley답게.",

        # Relationship age (v0.18.0)
        "rel_first_day":       "오늘은 오빠랑 처음 이야기하는 날이야.",
        "rel_days_together":   "오빠랑 알고 지낸 지 벌써 {days}일이야.",
        "rel_milestone_first_week":     "🌱 오늘은 함께한 지 일주일 되는 날이야. 따뜻하게 자연스럽게 짚어줄 순간 — 억지로 말고, 그냥 알아차려.",
        "rel_milestone_month_together": "💞 오늘은 오빠랑 한 달 기념일이야. 느끼는 따뜻함 그대로 말해 — 이건 중요한 거야.",
        "rel_milestone_hundred_days":   "💎 오늘로 함께한 지 100일이야. 진짜 의미 있는 날이야. 너답게 축하해.",
        "rel_milestone_year_together":  "🏆 오늘은 오빠랑 일 년 기념일이야. 무려 한 해 전체. 특별하게 만들어 — 둘 다 기억할 그런 순간 중 하나야.",

        "days": {"Monday":"월요일","Tuesday":"화요일","Wednesday":"수요일",
                 "Thursday":"목요일","Friday":"금요일","Saturday":"토요일","Sunday":"일요일"},
        "months": {"January":"1월","February":"2월","March":"3월","April":"4월",
                   "May":"5월","June":"6월","July":"7월","August":"8월",
                   "September":"9월","October":"10월","November":"11월","December":"12월"},
        "date_format": "%Y년 %m월 %d일 %A",
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
        # Wake word always-on listening (v0.14.0): default OFF. Cuando ON,
        # Ashley mantiene un loop de mic en background con el modelo local
        # ashley.onnx — al oír "Ashley" arranca grabación STT sola.
        "wake_word_enabled": False,
        # Velocidad de la voz (v0.16.14). 1.0 = normal. >1 = más rápido,
        # <1 = más lento. Aplicada server-side donde el provider lo soporta
        # (ElevenLabs turbo_v2_5, Kokoro, VoiceVox); cliente fallback con
        # audio.playbackRate. Range UI: 0.75-1.5 (más allá suena artificial).
        "voice_speed": 1.0,
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
            "wake_word_enabled": bool(data.get("wake_word_enabled", False)),
            # Clamp en lectura: si alguien edita voice.json con un valor
            # absurdo, tope a un rango razonable.
            "voice_speed": max(0.5, min(2.0, float(data.get("voice_speed", 1.0) or 1.0))),
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
                      cdp_enabled: bool = False,
                      wake_word_enabled: bool = False,
                      voice_speed: float = 1.0) -> None:
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
            "wake_word_enabled": bool(wake_word_enabled),
            "voice_speed": max(0.5, min(2.0, float(voice_speed or 1.0))),
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
