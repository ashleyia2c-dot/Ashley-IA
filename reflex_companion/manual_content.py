"""
manual_content.py — Contenido del manual del usuario que se abre desde
el botón ❓ en la cabecera de la app.

Estructura:
  MANUAL[lang] = {
      "title": str,                # Título del dialog
      "intro": str,                # Párrafo de bienvenida
      "sections": list[dict] = [
          {
              "id": str,           # identificador único, usado para keys
              "icon": str,         # emoji
              "title": str,
              "content_md": str,   # markdown — usado por rx.markdown
          },
          ...
      ],
  }

El markdown se renderiza con rx.markdown (que ya usa la app). Soporta
**bold**, listas con `-`, headings `##`, código inline con backticks.

Lenguajes incluidos: en (default), es, fr. Si pedimos un lang no presente
caemos a en.
"""

# ─────────────────────────────────────────
#  ENGLISH
# ─────────────────────────────────────────

_EN = {
    "title": "Welcome to Ashley — User manual",
    "intro": (
        "Ashley is a desktop AI companion that lives on your computer. "
        "She remembers your conversations, can speak and listen, and can "
        "interact with your system (open apps, control music, manage "
        "browser tabs). Everything she stores about you lives **only** "
        "on your machine — no cloud sync, no telemetry, no analytics."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Chat with Ashley",
            "content_md": (
                "Type in the input at the bottom. Press Enter to send, "
                "Shift+Enter for a new line. Ashley remembers up to 50 "
                "messages of context, plus a list of facts she extracts "
                "automatically from your conversations.\n\n"
                "**Mood tags**: Ashley uses one of 7 expressions per "
                "message (excited, embarrassed, tsundere, soft, surprised, "
                "proud, default). They drive her portrait animation in "
                "the corner.\n\n"
                "**To clear chat history**: press the trash icon in the "
                "header. Confirms before deleting. Cannot be undone."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Voice — speech-to-text and text-to-speech",
            "content_md": (
                "**Speak to Ashley**: click the 🎤 microphone button. "
                "Recording auto-stops after 4 seconds of silence. Audio "
                "is transcribed by Whisper running **locally** on your "
                "computer — never sent to any server.\n\n"
                "**Hear Ashley**: toggle TTS in Settings. Two engines:\n"
                "- **Web Speech** (free, robotic, all data stays local)\n"
                "- **ElevenLabs** (premium, sounds natural — text gets "
                "sent to elevenlabs.io for synthesis. Requires API key)\n\n"
                "**Natural mode**: 🗣 toggle in the header strips "
                "*gestures* like *smiles* from her replies — cleaner audio."
            ),
        },
        {
            "id": "wakeword",
            "icon": "👂",
            "title": "Wake word — always-on listening",
            "content_md": (
                "When ON, Ashley listens to your microphone in the "
                "background and starts recording when she hears her "
                "name. The detection model runs **100% locally** (~5 MB, "
                "CPU only). Audio NEVER leaves your computer until you "
                "speak the wake word.\n\n"
                "**Activate**: Settings → 🎙 Wake word → toggle ON.\n\n"
                "**How to use**: just say \"Ashley\" near the mic. "
                "After the chime, speak your message normally. The "
                "detector pauses automatically while you're typing or "
                "holding the mic button.\n\n"
                "**When to disable**: if you'd rather not have the mic "
                "open in the background, or if the false-positive rate "
                "annoys you. The detector is tuned for <1 false "
                "activation per hour with TV in the background, but "
                "every voice is different."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "System actions — let Ashley click for you",
            "content_md": (
                "Ashley can perform actions on your computer: open "
                "apps, control volume, play music, close browser tabs, "
                "set reminders. **Opt-in** behind the ⚡ toggle in the "
                "header.\n\n"
                "**Examples**:\n"
                "- \"Open notepad\" → launches Notepad\n"
                "- \"Volume to 50\" → sets system volume\n"
                "- \"Play that song from Stranger Things\" → opens "
                "YouTube and plays\n"
                "- \"Close YouTube tab\" → closes browser tabs by title\n"
                "- \"Remind me to call my mom in 1 hour\" → schedules "
                "a reminder\n\n"
                "**Safe actions** (no toggle needed): saving facts, "
                "marking important items, scheduling reminders.\n\n"
                "**When to disable**: if you don't trust Ashley to take "
                "the right action, or you want to avoid accidental "
                "system changes. The toggle is per-session — it "
                "doesn't persist between restarts unless you change it "
                "in Settings."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Modern browser mode (CDP)",
            "content_md": (
                "Optional advanced mode that lets Ashley control your "
                "browser **directly** through Chrome DevTools Protocol "
                "instead of simulating keystrokes. **Faster**, **no "
                "visible tab cycling**, and works even when the browser "
                "is minimized.\n\n"
                "**Activate**: Settings → 🌐 Modern browser mode → "
                "toggle ON. A wizard automatically modifies your "
                "browser shortcuts (Chrome/Edge/Brave/Opera) to add "
                "the required flag. Originals are backed up.\n\n"
                "**After activating**: close and reopen your browser "
                "for the change to take effect.\n\n"
                "**When to disable**: if you don't want a debugging "
                "port open on localhost (low risk for users without "
                "active malware, but defense-in-depth concerns)."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Memory — facts, diary, tastes",
            "content_md": (
                "Ashley remembers things about you across sessions. "
                "Three layers:\n\n"
                "**Facts**: short stuff she extracts automatically — "
                "your name, job, hobbies, recent events. Up to 300 "
                "facts. View/edit them via the 📋 icon in the header.\n\n"
                "**Diary**: longer reflections Ashley writes about how "
                "you've been recently. Auto-generated daily-ish.\n\n"
                "**Tastes**: explicit preferences (favorite genres, "
                "things you like/dislike). She updates these when you "
                "tell her \"I love...\" / \"I hate...\".\n\n"
                "All stored locally as JSON in `%APPDATA%\\ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Reminders and important items",
            "content_md": (
                "**Reminders**: Ashley can schedule things you ask her "
                "to remember. \"Remind me to call John at 3pm\" — when "
                "the time hits, she pings you (Windows notification + "
                "in-chat message).\n\n"
                "**Important items**: a separate list for things you "
                "want to track without time. \"Add `buy milk` to "
                "important\" — appears in the ⭐ icon in the header. "
                "Mark done when finished.\n\n"
                "Both stored in `%APPDATA%\\ashley\\data\\` as JSON."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Proactive discovery and news feed",
            "content_md": (
                "Optional. When ON, Ashley searches the web on her own "
                "for content matching your tastes (trailers, news, new "
                "songs). Items appear in the 📰 news feed in the header, "
                "**not** in the main chat — you choose when to read "
                "them.\n\n"
                "**Activate**: Settings → 🔭 Proactive discovery → "
                "toggle ON.\n\n"
                "**When to disable**: if you don't want Ashley using "
                "your LLM tokens to do background work, or if her "
                "discovery is hitting topics you'd rather she avoid.\n\n"
                "**Note**: requires xAI or OpenRouter as LLM provider. "
                "Disabled when using Ollama (local-only)."
            ),
        },
        {
            "id": "providers",
            "icon": "🧠",
            "title": "LLM provider — who powers Ashley's brain",
            "content_md": (
                "Three options in Settings → 🧠 LLM Provider:\n\n"
                "**xAI Grok** (default): cloud, premium quality. "
                "Requires API key from x.ai. Pay-per-token.\n\n"
                "**OpenRouter**: cloud, hundreds of models to choose "
                "from. Requires key from openrouter.ai. Pay-per-token.\n\n"
                "**Ollama** (local): runs models entirely on your "
                "computer (Llama 3.1, Mistral, etc.). Free but slower "
                "and lower quality than cloud models. Requires Ollama "
                "running at `localhost:11434`.\n\n"
                "**Privacy note**: with xAI/OpenRouter, your messages "
                "are sent to the provider. With Ollama, **nothing** "
                "leaves your computer."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Privacy — what stays local, what leaves",
            "content_md": (
                "**Stays local (always)**:\n"
                "- Chat history, facts, diary, reminders, tastes\n"
                "- Speech-to-text (Whisper runs on your CPU)\n"
                "- Wake word detection model\n"
                "- All actions Ashley performs on your system\n\n"
                "**Leaves your computer (only when needed)**:\n"
                "- Your messages to the LLM provider you chose "
                "(xAI/OpenRouter — Ollama keeps everything local)\n"
                "- Text-to-speech with ElevenLabs (the text of Ashley's "
                "reply is sent to elevenlabs.io for synthesis. Web "
                "Speech keeps it local)\n"
                "- Discovery searches when enabled (LLM-driven)\n"
                "- When you ask Ashley to play music, she does a single "
                "anonymous YouTube search to resolve the title to a video "
                "URL (no account, no cookies)\n\n"
                "**Data location**: `%APPDATA%\\ashley\\data\\`. You "
                "can wipe everything by deleting that folder.\n\n"
                "**No telemetry**: Ashley sends zero analytics, crash "
                "reports, or usage data anywhere. The only outbound "
                "connections are the ones listed above."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens and costs — when each feature costs money",
            "content_md": (
                "**Free** (no token usage):\n"
                "- Whisper STT, wake word, all local actions\n"
                "- Web Speech TTS, Ollama LLM\n\n"
                "**Costs tokens** (xAI/OpenRouter charge per message):\n"
                "- Each chat message you send Ashley\n"
                "- Discovery (if ON, periodic LLM calls in the "
                "background)\n"
                "- Diary auto-generation\n\n"
                "**Costs ElevenLabs credits** (free tier ~10k chars/mo):\n"
                "- Every TTS response, if ElevenLabs is your voice "
                "provider\n\n"
                "**Tips to save tokens**:\n"
                "- Disable Proactive Discovery when not needed\n"
                "- Use Ollama for casual chat, xAI for serious tasks\n"
                "- Use Web Speech for TTS unless you really want the "
                "premium voice"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Tips and shortcuts",
            "content_md": (
                "**Keyboard**:\n"
                "- Enter — send\n"
                "- Shift+Enter — newline in message\n"
                "- Esc — close any open dialog\n\n"
                "**Header icons** (left to right typically):\n"
                "- ❓ this manual\n"
                "- 📰 news feed (unread count badge)\n"
                "- 📋 extracted facts list\n"
                "- ⭐ important items list\n"
                "- 📔 diary\n"
                "- ⚡ system actions toggle\n"
                "- 🗣 natural voice mode\n"
                "- 🌍 language\n"
                "- ⚙️ settings\n"
                "- 🗑 clear chat\n\n"
                "**While Ashley is thinking**: the header toggles "
                "(⚡ Actions, 🗣 Natural, settings, etc.) are temporarily "
                "unresponsive while she's mid-stream. This is intentional "
                "— flipping a toggle in the middle of her response could "
                "leave her in an inconsistent state (e.g. acting with "
                "Actions on but the prompt said off). Wait for her to "
                "finish, then toggle.\n\n"
                "**Pin on top**: Settings → Pin window — keeps Ashley "
                "always visible above other windows.\n\n"
                "**Refund policy**: 14 days from purchase if you've "
                "sent fewer than 40 messages."
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  ESPAÑOL
# ─────────────────────────────────────────

_ES = {
    "title": "Bienvenido a Ashley — Manual de usuario",
    "intro": (
        "Ashley es una compañera de IA de escritorio que vive en tu PC. "
        "Recuerda tus conversaciones, puede hablar y escuchar, y puede "
        "interactuar con tu sistema (abrir apps, controlar música, "
        "gestionar pestañas del navegador). Todo lo que guarda sobre ti "
        "vive **solo** en tu máquina — sin sync a la nube, sin "
        "telemetría, sin analytics."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Chat con Ashley",
            "content_md": (
                "Escribe en el input de abajo. Enter para enviar, "
                "Shift+Enter para nueva línea. Ashley recuerda hasta 50 "
                "mensajes de contexto, más una lista de hechos que "
                "extrae automáticamente de tus conversaciones.\n\n"
                "**Tags de mood**: Ashley usa una de 7 expresiones por "
                "mensaje (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Animan su retrato en la "
                "esquina.\n\n"
                "**Borrar el chat**: pulsa el icono de papelera del "
                "header. Pide confirmación. No se puede deshacer."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Voz — habla y escucha",
            "content_md": (
                "**Hablar a Ashley**: pulsa el botón 🎤. La grabación "
                "se para sola tras 4 segundos de silencio. El audio se "
                "transcribe con Whisper corriendo **localmente** en tu "
                "PC — nunca se envía a ningún servidor.\n\n"
                "**Que Ashley te hable**: activa TTS en Ajustes. Dos "
                "motores:\n"
                "- **Web Speech** (gratis, robótico, todo local)\n"
                "- **ElevenLabs** (premium, suena natural — el texto "
                "se envía a elevenlabs.io para sintetizarse. Necesita "
                "API key)\n\n"
                "**Modo natural**: el toggle 🗣 del header quita los "
                "*gestos* tipo *sonríe* de sus respuestas — audio más "
                "limpio."
            ),
        },
        {
            "id": "wakeword",
            "icon": "👂",
            "title": "Palabra clave — escucha permanente",
            "content_md": (
                "Cuando está ACTIVADO, Ashley escucha tu micro en "
                "background y arranca grabación cuando oye su nombre. "
                "El modelo de detección corre **100% local** (~5 MB, "
                "solo CPU). El audio NUNCA sale de tu PC hasta que "
                "digas la palabra clave.\n\n"
                "**Activar**: Ajustes → 🎙 Palabra clave → ACTIVAR.\n\n"
                "**Cómo usar**: di \"Ashley\" claro cerca del mic. "
                "Tras el sonido de aviso, di tu mensaje normal. El "
                "detector se pausa solo mientras escribes o aprietas "
                "el botón del mic.\n\n"
                "**Cuándo desactivar**: si prefieres no tener el mic "
                "abierto en background, o si los falsos positivos te "
                "molestan. El detector está calibrado para <1 "
                "activación falsa por hora con TV de fondo, pero cada "
                "voz es distinta."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Acciones del sistema — deja que Ashley clique por ti",
            "content_md": (
                "Ashley puede ejecutar acciones en tu PC: abrir apps, "
                "controlar volumen, poner música, cerrar pestañas, "
                "agendar recordatorios. **Opt-in** detrás del toggle "
                "⚡ del header.\n\n"
                "**Ejemplos**:\n"
                "- \"Abre el bloc de notas\" → lanza Notepad\n"
                "- \"Volumen al 50\" → ajusta el volumen del sistema\n"
                "- \"Pon esa canción de Stranger Things\" → abre "
                "YouTube y reproduce\n"
                "- \"Cierra la pestaña de YouTube\" → cierra pestañas "
                "por título\n"
                "- \"Recuérdame llamar a mi madre en 1 hora\" → agenda "
                "un recordatorio\n\n"
                "**Acciones seguras** (no requieren toggle): guardar "
                "hechos, marcar importantes, agendar recordatorios.\n\n"
                "**Cuándo desactivar**: si no confías en que Ashley "
                "tome la acción correcta, o quieres evitar cambios "
                "accidentales del sistema. El toggle es por sesión — "
                "no persiste entre reinicios salvo que lo cambies en "
                "Ajustes."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Modo browser moderno (CDP)",
            "content_md": (
                "Modo avanzado opcional que permite a Ashley controlar "
                "tu navegador **directamente** vía Chrome DevTools "
                "Protocol en lugar de simular teclas. **Más rápido**, "
                "**sin pestañas cambiando visiblemente**, y funciona "
                "incluso si el navegador está minimizado.\n\n"
                "**Activar**: Ajustes → 🌐 Modo browser moderno → "
                "ACTIVAR. Un wizard modifica automáticamente los "
                "accesos directos de tu navegador (Chrome/Edge/Brave/"
                "Opera) para añadir el flag necesario. Los originales "
                "se guardan en backup.\n\n"
                "**Después de activar**: cierra y reabre tu navegador "
                "para que el cambio tenga efecto.\n\n"
                "**Cuándo desactivar**: si no quieres un puerto de "
                "debugging abierto en localhost (riesgo bajo si no "
                "tienes malware activo, pero por defensa en "
                "profundidad)."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Memoria — hechos, diario, gustos",
            "content_md": (
                "Ashley recuerda cosas sobre ti entre sesiones. Tres "
                "capas:\n\n"
                "**Hechos**: cosas cortas que extrae automáticamente — "
                "tu nombre, trabajo, aficiones, eventos recientes. Hasta "
                "300 hechos. Vista/edición desde el icono 📋 del header.\n\n"
                "**Diario**: reflexiones más largas que Ashley escribe "
                "sobre cómo has estado últimamente. Auto-generado "
                "diario-ish.\n\n"
                "**Gustos**: preferencias explícitas (géneros favoritos, "
                "cosas que te gustan/no). Se actualizan cuando le dices "
                "\"me encanta...\" / \"odio...\".\n\n"
                "Todo guardado local como JSON en "
                "`%APPDATA%\\ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Recordatorios e items importantes",
            "content_md": (
                "**Recordatorios**: Ashley puede agendar cosas. "
                "\"Recuérdame llamar a Juan a las 3pm\" — cuando "
                "llega la hora, te avisa (notificación de Windows + "
                "mensaje en chat).\n\n"
                "**Items importantes**: lista separada para cosas que "
                "quieres trackear sin tiempo. \"Añade `comprar leche` "
                "a importantes\" — aparecen en el ⭐ del header. Marca "
                "como hecho cuando termines.\n\n"
                "Ambos guardados en `%APPDATA%\\ashley\\data\\` como JSON."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Discovery proactivo y feed de noticias",
            "content_md": (
                "Opcional. Cuando está ACTIVADO, Ashley busca por la "
                "web cosas que coinciden con tus gustos (trailers, "
                "noticias, canciones nuevas). Los items aparecen en el "
                "feed 📰 del header, **no** en el chat principal — tú "
                "decides cuándo leerlos.\n\n"
                "**Activar**: Ajustes → 🔭 Discovery proactivo → "
                "ACTIVAR.\n\n"
                "**Cuándo desactivar**: si no quieres que Ashley use "
                "tus tokens de LLM en background, o si su discovery "
                "está tocando temas que prefieres evitar.\n\n"
                "**Nota**: requiere xAI o OpenRouter como provider de "
                "LLM. Desactivado cuando usas Ollama (solo local)."
            ),
        },
        {
            "id": "providers",
            "icon": "🧠",
            "title": "Provider de LLM — quién es el cerebro de Ashley",
            "content_md": (
                "Tres opciones en Ajustes → 🧠 LLM Provider:\n\n"
                "**xAI Grok** (default): nube, calidad premium. "
                "Necesita API key de x.ai. Pago por token.\n\n"
                "**OpenRouter**: nube, cientos de modelos a elegir. "
                "Necesita key de openrouter.ai. Pago por token.\n\n"
                "**Ollama** (local): corre modelos enteramente en tu "
                "PC (Llama 3.1, Mistral, etc.). Gratis pero más lento "
                "y de menor calidad que los modelos de nube. Necesita "
                "Ollama corriendo en `localhost:11434`.\n\n"
                "**Nota de privacidad**: con xAI/OpenRouter, tus "
                "mensajes se envían al provider. Con Ollama, **nada** "
                "sale de tu PC."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Privacidad — qué se queda local, qué sale",
            "content_md": (
                "**Se queda local (siempre)**:\n"
                "- Historial de chat, hechos, diario, recordatorios, "
                "gustos\n"
                "- Speech-to-text (Whisper corre en tu CPU)\n"
                "- Modelo de detección de wake word\n"
                "- Todas las acciones que Ashley ejecuta en tu sistema\n\n"
                "**Sale de tu PC (solo cuando hace falta)**:\n"
                "- Tus mensajes al provider de LLM elegido (xAI/"
                "OpenRouter — Ollama mantiene todo local)\n"
                "- Text-to-speech con ElevenLabs (el texto de la "
                "respuesta de Ashley se envía a elevenlabs.io para "
                "sintetizarse. Web Speech lo mantiene local)\n"
                "- Búsquedas de discovery cuando está activo (LLM-"
                "driven)\n"
                "- Cuando le pides a Ashley reproducir música, hace "
                "una búsqueda anónima en YouTube para resolver el "
                "título → URL del video (sin cuenta, sin cookies)\n\n"
                "**Ubicación de datos**: `%APPDATA%\\ashley\\data\\`. "
                "Puedes borrar todo eliminando esa carpeta.\n\n"
                "**Sin telemetría**: Ashley no envía analytics, "
                "reportes de crash o datos de uso a ningún sitio. Las "
                "únicas conexiones salientes son las listadas arriba."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens y costes — cuándo cada feature cuesta dinero",
            "content_md": (
                "**Gratis** (sin uso de tokens):\n"
                "- Whisper STT, wake word, todas las acciones locales\n"
                "- Web Speech TTS, Ollama LLM\n\n"
                "**Cuesta tokens** (xAI/OpenRouter cobran por mensaje):\n"
                "- Cada mensaje que envías a Ashley\n"
                "- Discovery (si está ON, llamadas LLM periódicas en "
                "background)\n"
                "- Auto-generación del diario\n\n"
                "**Cuesta créditos de ElevenLabs** (free tier ~10k "
                "chars/mes):\n"
                "- Cada respuesta TTS, si ElevenLabs es tu provider de "
                "voz\n\n"
                "**Tips para ahorrar tokens**:\n"
                "- Desactiva Discovery proactivo si no lo necesitas\n"
                "- Usa Ollama para chat casual, xAI para tareas serias\n"
                "- Usa Web Speech para TTS salvo que de verdad quieras "
                "la voz premium"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Tips y atajos",
            "content_md": (
                "**Teclado**:\n"
                "- Enter — enviar\n"
                "- Shift+Enter — nueva línea en el mensaje\n"
                "- Esc — cierra cualquier dialog abierto\n\n"
                "**Iconos del header** (típicamente izquierda a "
                "derecha):\n"
                "- ❓ este manual\n"
                "- 📰 feed de noticias (badge con no leídos)\n"
                "- 📋 lista de hechos extraídos\n"
                "- ⭐ items importantes\n"
                "- 📔 diario\n"
                "- ⚡ toggle de acciones del sistema\n"
                "- 🗣 modo voz natural\n"
                "- 🌍 idioma\n"
                "- ⚙️ ajustes\n"
                "- 🗑 borrar chat\n\n"
                "**Mientras Ashley está pensando**: los toggles del "
                "header (⚡ Acciones, 🗣 Natural, ajustes, etc.) están "
                "temporalmente sin responder mientras ella streamea. "
                "Es a propósito — cambiar un toggle en medio de su "
                "respuesta la dejaría inconsistente (p.ej. actuando "
                "con Acciones ON pero su prompt decía OFF). Espera a "
                "que termine, después tócalos.\n\n"
                "**Pin on top**: Ajustes → Pin window — mantiene "
                "Ashley siempre visible encima de las otras ventanas.\n\n"
                "**Política de devolución**: 14 días desde la compra "
                "si has enviado menos de 40 mensajes."
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  FRANÇAIS
# ─────────────────────────────────────────
# Traducción más sucinta — el FR comparte estructura con EN/ES y la
# mayoría de keywords (CDP, ElevenLabs, etc) son idénticos.

_FR = {
    "title": "Bienvenue à Ashley — Manuel utilisateur",
    "intro": (
        "Ashley est une compagne IA de bureau qui vit sur ton ordinateur. "
        "Elle se souvient de tes conversations, peut parler et écouter, "
        "et peut interagir avec ton système (ouvrir des apps, contrôler "
        "la musique, gérer les onglets). Tout ce qu'elle stocke sur toi "
        "vit **uniquement** sur ta machine — pas de sync cloud, pas de "
        "télémétrie, pas d'analytics."
    ),
    "sections": _ES["sections"],  # FR provisional usa contenido ES — TODO
}


# ─────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────

MANUAL = {
    "en": _EN,
    "es": _ES,
    "fr": _FR,
}


def get_manual(lang: str) -> dict:
    """Devuelve el manual en el idioma pedido. Fallback a EN si lang
    no soportado."""
    return MANUAL.get(lang, MANUAL["en"])
