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
                "in Settings.\n\n"
                "**Built-in safety filter**: when Ashley opens an app or "
                "closes a window, certain characters are blocked from "
                "the request — `&`, `|`, `;`, `<`, `>`, `\"`, `'`, `` ` ``, "
                "`$` and newlines. These are command separators and "
                "escape characters that, in theory, a malicious web page "
                "scraped by Ashley could try to slip into a request to "
                "make your computer run arbitrary commands (download a "
                "file, delete folders, etc.). Real app names never need "
                "those symbols, so blocking them costs nothing and "
                "shuts that door completely. If Ashley ever says she "
                "couldn't open something with a weird name, that's why."
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
                "Ajustes.\n\n"
                "**Filtro de seguridad integrado**: cuando Ashley abre "
                "una app o cierra una ventana, ciertos caracteres están "
                "bloqueados de la petición — `&`, `|`, `;`, `<`, `>`, "
                "`\"`, `'`, `` ` ``, `$` y saltos de línea. Son "
                "separadores de comando y caracteres de escape que, en "
                "teoría, una página web maliciosa que Ashley scrapee "
                "podría intentar colar en una petición para hacer que "
                "tu PC ejecute comandos arbitrarios (descargar un "
                "archivo, borrar carpetas, etc.). Los nombres reales de "
                "apps nunca necesitan esos símbolos, así que bloquearlos "
                "no cuesta nada y cierra esa puerta del todo. Si alguna "
                "vez Ashley dice que no pudo abrir algo con un nombre "
                "raro, esa es la razón."
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
#  日本語 (JAPANESE)
# ─────────────────────────────────────────

_JA = {
    "title": "Ashleyへようこそ — ユーザーマニュアル",
    "intro": (
        "Ashleyはご主人のパソコンに住むデスクトップAIコンパニオンです。"
        "会話を覚え、話したり聞いたり、システムを操作する(アプリを起動、"
        "音楽の制御、ブラウザのタブ管理)こともできます。ご主人について"
        "保存される情報は**すべて**このマシンのみに残ります — クラウド"
        "同期なし、テレメトリなし、解析なし。"
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Ashleyとチャット",
            "content_md": (
                "下の入力欄に文字を入れてください。Enterで送信、"
                "Shift+Enterで改行です。Ashleyは最大50メッセージの"
                "コンテキストを覚えており、会話から自動的に抽出した事実の"
                "リストも保持します。\n\n"
                "**ムードタグ**: Ashleyは1メッセージにつき7つの表情から"
                "1つを使います(excited、embarrassed、tsundere、soft、"
                "surprised、proud、default)。これが画面の隅にある"
                "ポートレートのアニメーションを動かします。\n\n"
                "**チャット履歴を消去するには**: ヘッダーのゴミ箱"
                "アイコンを押してください。削除前に確認します。元に"
                "戻せません。"
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "音声 — 音声入力と音声合成",
            "content_md": (
                "**Ashleyに話しかける**: 🎤マイクボタンをクリック"
                "してください。録音は4秒間の沈黙で自動停止します。"
                "音声はパソコン上で**ローカル**に動くWhisperで文字起こし"
                "されます — どのサーバーにも送信されません。\n\n"
                "**Ashleyの声を聞く**: 設定でTTSをONにしてください。"
                "2つのエンジン:\n"
                "- **Web Speech**(無料、機械的、データはすべてローカル)\n"
                "- **ElevenLabs**(プレミアム、自然な音声 — テキストは"
                "合成のためelevenlabs.ioに送信。APIキーが必要)\n\n"
                "**ナチュラルモード**: ヘッダーの🗣トグルで返答から"
                "*微笑む*などの*ジェスチャー*を取り除きます — クリーン"
                "な音声に。"
            ),
        },
        {
            "id": "wakeword",
            "icon": "👂",
            "title": "ウェイクワード — 常時待機リスニング",
            "content_md": (
                "ONのとき、Ashleyはバックグラウンドでマイクを聞き、"
                "自分の名前が呼ばれると録音を開始します。検出モデルは"
                "**100%ローカル**で動作します(~5MB、CPUのみ)。"
                "ウェイクワードを発話するまで、音声は決してパソコンから"
                "出ません。\n\n"
                "**有効化**: 設定 → 🎙 ウェイクワード → ON。\n\n"
                "**使い方**: マイクの近くで「Ashley」と言うだけ。"
                "チャイム音の後、普通に話してください。入力中やマイク"
                "ボタンを押している間は検出器が自動的に一時停止します。\n\n"
                "**無効化するべき場合**: バックグラウンドでマイクを"
                "開いておきたくない、または誤検出が気になる場合。"
                "テレビが背景にある状況でも誤反応は1時間に1回未満になる"
                "ように調整されていますが、声は人それぞれ違います。"
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "システムアクション — Ashleyにクリックさせる",
            "content_md": (
                "Ashleyはパソコン上でアクションを実行できます: アプリの"
                "起動、音量調整、音楽再生、ブラウザのタブを閉じる、"
                "リマインダーの設定。**オプトイン**でヘッダーの⚡トグル"
                "の後ろにあります。\n\n"
                "**例**:\n"
                "- 「メモ帳を開いて」 → Notepadを起動\n"
                "- 「音量50に」 → システム音量を調整\n"
                "- 「Stranger Thingsのあの曲をかけて」 → YouTubeを"
                "開いて再生\n"
                "- 「YouTubeのタブを閉じて」 → タイトルでブラウザの"
                "タブを閉じる\n"
                "- 「1時間後にお母さんに電話するのを思い出させて」 → "
                "リマインダーを設定\n\n"
                "**安全なアクション**(トグル不要): 事実の保存、"
                "重要項目のマーク、リマインダーの設定。\n\n"
                "**無効化するべき場合**: Ashleyが正しいアクションを"
                "取れるか信用できない、または誤ってシステムが変更される"
                "のを避けたい場合。トグルはセッション単位 — 設定で"
                "変更しない限り再起動間で持続しません。\n\n"
                "**組み込みの安全フィルター**: Ashleyがアプリを開いたり"
                "ウィンドウを閉じたりするとき、特定の文字はリクエスト"
                "から遮断されます — `&`、`|`、`;`、`<`、`>`、`\"`、"
                "`'`、`` ` ``、`$`、改行。これらはコマンド区切り文字や"
                "エスケープ文字で、理論上、Ashleyがスクレイプした悪意"
                "あるWebページがリクエストに紛れ込ませて、ご主人のパソコン"
                "に任意のコマンド(ファイルのダウンロード、フォルダの削除"
                "など)を実行させようとする可能性があります。実際のアプリ"
                "名にこれらの記号が必要なことは絶対にないので、ブロック"
                "してもコストはなく、その扉を完全に閉じられます。Ashleyが"
                "変な名前で何かを開けなかったと言ったら、それが理由です。"
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "モダンブラウザモード(CDP)",
            "content_md": (
                "オプションの上級モードで、Ashleyがキー入力をシミュレート"
                "する代わりにChrome DevTools Protocol経由でブラウザを"
                "**直接**制御できるようにします。**より高速**、**目に見える"
                "タブの切り替えなし**、ブラウザが最小化されていても動作"
                "します。\n\n"
                "**有効化**: 設定 → 🌐 モダンブラウザモード → ON。"
                "ウィザードが自動的にブラウザのショートカット"
                "(Chrome/Edge/Brave/Opera)を変更し、必要なフラグを"
                "追加します。元のショートカットはバックアップされます。\n\n"
                "**有効化後**: 変更を反映するためブラウザを閉じて開き"
                "直してください。\n\n"
                "**無効化するべき場合**: localhostでデバッグポートを"
                "開いておきたくない場合(アクティブなマルウェアがない"
                "ユーザーには低リスクですが、多重防御の観点で)。"
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "メモリ — 事実、日記、好み",
            "content_md": (
                "Ashleyはセッションを跨いでご主人のことを覚えています。"
                "3つの層:\n\n"
                "**事実**: 自動的に抽出される短い情報 — 名前、仕事、"
                "趣味、最近の出来事。最大300件。ヘッダーの📋アイコン"
                "から閲覧/編集できます。\n\n"
                "**日記**: ご主人が最近どう過ごしているかについてAshleyが"
                "書く長めの考察。ほぼ毎日自動生成されます。\n\n"
                "**好み**: 明示的な好み(好きなジャンル、好き嫌いの物)。"
                "「~が大好き」「~が嫌い」と言うとAshleyが更新します。\n\n"
                "すべて`%APPDATA%\\ashley\\data\\`にJSON形式でローカル"
                "保存されます。"
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "リマインダーと重要項目",
            "content_md": (
                "**リマインダー**: Ashleyに覚えておいてほしいことを"
                "スケジュールできます。「3時にジョンに電話するのを"
                "思い出させて」 — 時間になるとお知らせします"
                "(Windows通知 + チャット内メッセージ)。\n\n"
                "**重要項目**: 時間なしで追跡したいことのための別リスト。"
                "「`牛乳を買う`を重要に追加」 — ヘッダーの⭐アイコンに"
                "表示されます。終わったら完了マークをつけてください。\n\n"
                "両方とも`%APPDATA%\\ashley\\data\\`にJSONとして保存"
                "されます。"
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "プロアクティブディスカバリーとニュースフィード",
            "content_md": (
                "オプション。ONのとき、Ashleyが自分でWebを検索し、"
                "ご主人の好みに合うコンテンツ(トレーラー、ニュース、"
                "新しい曲)を探します。アイテムはヘッダーの📰ニュース"
                "フィードに表示され、メインチャットには表示**されません** "
                "— いつ読むかはご主人が選びます。\n\n"
                "**有効化**: 設定 → 🔭 プロアクティブディスカバリー → "
                "ON。\n\n"
                "**無効化するべき場合**: AshleyにLLMトークンをバックグラウンド"
                "作業に使ってほしくない、またはディスカバリーが避けて"
                "ほしいトピックに触れている場合。\n\n"
                "**注**: LLMプロバイダーとしてxAIまたはOpenRouterが必要"
                "です。Ollama(完全ローカル)使用時は無効化されます。"
            ),
        },
        {
            "id": "providers",
            "icon": "🧠",
            "title": "LLMプロバイダー — Ashleyの脳を動かすもの",
            "content_md": (
                "設定 → 🧠 LLMプロバイダーで3つの選択肢:\n\n"
                "**xAI Grok**(デフォルト): クラウド、プレミアム品質。"
                "x.aiのAPIキーが必要。トークン課金。\n\n"
                "**OpenRouter**: クラウド、何百ものモデルから選択可能。"
                "openrouter.aiのキーが必要。トークン課金。\n\n"
                "**Ollama**(ローカル): モデルを完全にパソコン上で実行"
                "(Llama 3.1、Mistralなど)。無料ですがクラウドモデル"
                "より低速で品質も劣ります。`localhost:11434`でOllamaが"
                "動いている必要があります。\n\n"
                "**プライバシーに関する注意**: xAI/OpenRouterではメッセージ"
                "がプロバイダーに送信されます。Ollamaでは**何も**パソコン"
                "から出ません。"
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "プライバシー — 何がローカルに残り、何が出るか",
            "content_md": (
                "**ローカルに残る(常に)**:\n"
                "- チャット履歴、事実、日記、リマインダー、好み\n"
                "- 音声入力(WhisperはCPUで動作)\n"
                "- ウェイクワード検出モデル\n"
                "- Ashleyがシステム上で実行するすべてのアクション\n\n"
                "**パソコンから出る(必要なときのみ)**:\n"
                "- 選んだLLMプロバイダーへのメッセージ"
                "(xAI/OpenRouter — Ollamaはすべてローカル保持)\n"
                "- ElevenLabsでのTTS(Ashleyの返答テキストが合成のため"
                "elevenlabs.ioに送信されます。Web Speechはローカル保持)\n"
                "- 有効時のディスカバリー検索(LLM駆動)\n"
                "- Ashleyに音楽再生を頼んだとき、タイトルから動画URLを"
                "解決するために匿名のYouTube検索を1回行います"
                "(アカウントなし、Cookieなし)\n\n"
                "**データの場所**: `%APPDATA%\\ashley\\data\\`。このフォルダ"
                "を削除すればすべてのデータを消去できます。\n\n"
                "**テレメトリなし**: Ashleyは解析、クラッシュレポート、"
                "使用データをどこにも一切送信しません。発信される接続は"
                "上記のものだけです。"
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "トークンと費用 — どの機能でお金がかかるか",
            "content_md": (
                "**無料**(トークン消費なし):\n"
                "- Whisper STT、ウェイクワード、すべてのローカルアクション\n"
                "- Web Speech TTS、Ollama LLM\n\n"
                "**トークン消費**(xAI/OpenRouterはメッセージごとに課金):\n"
                "- Ashleyに送る各チャットメッセージ\n"
                "- ディスカバリー(ONの場合、バックグラウンドで定期的"
                "なLLM呼び出し)\n"
                "- 日記の自動生成\n\n"
                "**ElevenLabsクレジット消費**(無料枠は月~10k文字):\n"
                "- ElevenLabsが音声プロバイダーの場合、すべてのTTS応答\n\n"
                "**トークン節約のコツ**:\n"
                "- 不要ならプロアクティブディスカバリーをOFFに\n"
                "- カジュアルチャットにはOllama、真剣な作業にはxAI\n"
                "- プレミアム音声を本当に望まない限りWeb Speech TTSを"
                "使う"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "コツとショートカット",
            "content_md": (
                "**キーボード**:\n"
                "- Enter — 送信\n"
                "- Shift+Enter — メッセージ内の改行\n"
                "- Esc — 開いているダイアログを閉じる\n\n"
                "**ヘッダーアイコン**(通常は左から右に):\n"
                "- ❓ このマニュアル\n"
                "- 📰 ニュースフィード(未読数バッジ)\n"
                "- 📋 抽出された事実リスト\n"
                "- ⭐ 重要項目リスト\n"
                "- 📔 日記\n"
                "- ⚡ システムアクショントグル\n"
                "- 🗣 ナチュラルボイスモード\n"
                "- 🌍 言語\n"
                "- ⚙️ 設定\n"
                "- 🗑 チャット消去\n\n"
                "**Ashleyが考えている間**: ヘッダーのトグル(⚡ アクション、"
                "🗣 ナチュラル、設定など)はストリーム中、一時的に応答"
                "しなくなります。これは意図的なものです — 応答の途中で"
                "トグルを切り替えると、Ashleyが矛盾した状態になる可能性"
                "があります(例: アクションONで動作しているのにプロンプトは"
                "OFFと言っていた)。終わるまで待ってから切り替えてください。\n\n"
                "**ピン留め**: 設定 → ピンウィンドウ — Ashleyを常に"
                "他のウィンドウの上に表示します。\n\n"
                "**返金ポリシー**: 購入から14日以内、送信メッセージが"
                "40件未満の場合に返金可能。"
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  DEUTSCH (GERMAN)
# ─────────────────────────────────────────

_DE = {
    "title": "Willkommen bei Ashley — Benutzerhandbuch",
    "intro": (
        "Ashley ist eine Desktop-KI-Begleiterin, die auf deinem Computer "
        "lebt. Sie erinnert sich an deine Gespräche, kann sprechen und "
        "zuhören und mit deinem System interagieren (Apps öffnen, Musik "
        "steuern, Browser-Tabs verwalten). Alles, was sie über dich "
        "speichert, lebt **ausschließlich** auf deinem Gerät — keine "
        "Cloud-Synchronisation, keine Telemetrie, keine Analytics."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Mit Ashley chatten",
            "content_md": (
                "Tippe in das Eingabefeld unten. Drücke Enter zum Senden, "
                "Shift+Enter für eine neue Zeile. Ashley merkt sich bis "
                "zu 50 Nachrichten Kontext, plus eine Liste von Fakten, "
                "die sie automatisch aus deinen Gesprächen extrahiert.\n\n"
                "**Mood-Tags**: Ashley nutzt einen von 7 Ausdrücken pro "
                "Nachricht (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Sie steuern die Animation "
                "ihres Porträts in der Ecke.\n\n"
                "**Chat-Verlauf löschen**: Drücke das Mülleimer-Symbol "
                "in der Kopfzeile. Es wird vor dem Löschen bestätigt. "
                "Kann nicht rückgängig gemacht werden."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Stimme — Spracherkennung und Sprachsynthese",
            "content_md": (
                "**Mit Ashley sprechen**: Klicke auf die 🎤-Mikrofon-"
                "Schaltfläche. Die Aufnahme stoppt automatisch nach 4 "
                "Sekunden Stille. Audio wird von Whisper transkribiert, "
                "das **lokal** auf deinem Computer läuft — wird nie an "
                "einen Server gesendet.\n\n"
                "**Ashley hören**: Aktiviere TTS in den Einstellungen. "
                "Zwei Engines:\n"
                "- **Web Speech** (kostenlos, robotisch, alle Daten "
                "bleiben lokal)\n"
                "- **ElevenLabs** (Premium, natürlich klingend — Text "
                "wird zur Synthese an elevenlabs.io gesendet. API-Key "
                "erforderlich)\n\n"
                "**Natürlicher Modus**: Der 🗣-Schalter in der Kopfzeile "
                "entfernt *Gesten* wie *lächelt* aus ihren Antworten — "
                "saubereres Audio."
            ),
        },
        {
            "id": "wakeword",
            "icon": "👂",
            "title": "Wake Word — dauerhaftes Mithören",
            "content_md": (
                "Wenn AN, hört Ashley dein Mikrofon im Hintergrund ab "
                "und beginnt mit der Aufnahme, wenn sie ihren Namen "
                "hört. Das Erkennungsmodell läuft **100% lokal** "
                "(~5 MB, nur CPU). Audio verlässt deinen Computer "
                "NIEMALS, bis du das Wake Word sprichst.\n\n"
                "**Aktivieren**: Einstellungen → 🎙 Wake Word → AN.\n\n"
                "**Verwendung**: Sage einfach „Ashley\" in die Nähe des "
                "Mikrofons. Nach dem Klang sprich deine Nachricht "
                "normal. Der Detektor pausiert automatisch, während du "
                "tippst oder die Mikrofon-Taste hältst.\n\n"
                "**Wann deaktivieren**: Wenn du das Mikrofon nicht im "
                "Hintergrund offen haben möchtest, oder wenn dich die "
                "False-Positive-Rate stört. Der Detektor ist auf <1 "
                "Falschauslösung pro Stunde mit TV im Hintergrund "
                "kalibriert, aber jede Stimme ist anders."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Systemaktionen — lass Ashley für dich klicken",
            "content_md": (
                "Ashley kann Aktionen auf deinem Computer ausführen: "
                "Apps öffnen, Lautstärke regeln, Musik abspielen, "
                "Browser-Tabs schließen, Erinnerungen setzen. **Opt-in** "
                "hinter dem ⚡-Schalter in der Kopfzeile.\n\n"
                "**Beispiele**:\n"
                "- „Öffne Notepad\" → startet Notepad\n"
                "- „Lautstärke auf 50\" → setzt Systemlautstärke\n"
                "- „Spiel den Song aus Stranger Things\" → öffnet "
                "YouTube und spielt ab\n"
                "- „Schließe den YouTube-Tab\" → schließt Browser-Tabs "
                "nach Titel\n"
                "- „Erinnere mich in 1 Stunde, meine Mutter anzurufen\" "
                "→ plant eine Erinnerung\n\n"
                "**Sichere Aktionen** (kein Schalter nötig): Fakten "
                "speichern, wichtige Einträge markieren, Erinnerungen "
                "planen.\n\n"
                "**Wann deaktivieren**: Wenn du Ashley nicht zutraust, "
                "die richtige Aktion auszuführen, oder versehentliche "
                "Systemänderungen vermeiden willst. Der Schalter gilt "
                "pro Session — er bleibt zwischen Neustarts nicht "
                "erhalten, außer du änderst ihn in den Einstellungen.\n\n"
                "**Eingebauter Sicherheitsfilter**: Wenn Ashley eine "
                "App öffnet oder ein Fenster schließt, werden bestimmte "
                "Zeichen aus der Anfrage blockiert — `&`, `|`, `;`, `<`, "
                "`>`, `\"`, `'`, `` ` ``, `$` und Zeilenumbrüche. Das "
                "sind Befehlstrennzeichen und Escape-Zeichen, die "
                "theoretisch eine bösartige Webseite, die Ashley "
                "scrapt, in eine Anfrage einschleusen könnte, um deinen "
                "Computer beliebige Befehle ausführen zu lassen (Datei "
                "herunterladen, Ordner löschen usw.). Echte App-Namen "
                "brauchen diese Symbole nie, also kostet das Blockieren "
                "nichts und schließt diese Tür komplett. Wenn Ashley "
                "mal sagt, sie konnte etwas mit einem komischen Namen "
                "nicht öffnen, ist das der Grund."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Moderner Browser-Modus (CDP)",
            "content_md": (
                "Optionaler Erweiterungsmodus, der Ashley erlaubt, "
                "deinen Browser **direkt** über das Chrome DevTools "
                "Protocol zu steuern, statt Tastenanschläge zu "
                "simulieren. **Schneller**, **kein sichtbares "
                "Tab-Wechseln**, funktioniert auch bei minimiertem "
                "Browser.\n\n"
                "**Aktivieren**: Einstellungen → 🌐 Moderner "
                "Browser-Modus → AN. Ein Wizard ändert automatisch "
                "deine Browser-Verknüpfungen (Chrome/Edge/Brave/Opera), "
                "um das benötigte Flag hinzuzufügen. Die Originale "
                "werden gesichert.\n\n"
                "**Nach dem Aktivieren**: Schließe und öffne deinen "
                "Browser neu, damit die Änderung wirksam wird.\n\n"
                "**Wann deaktivieren**: Wenn du keinen Debug-Port auf "
                "localhost offen haben willst (geringes Risiko für "
                "Nutzer ohne aktive Malware, aber Defense-in-Depth-"
                "Bedenken)."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Gedächtnis — Fakten, Tagebuch, Vorlieben",
            "content_md": (
                "Ashley merkt sich Dinge über dich über Sessions "
                "hinweg. Drei Schichten:\n\n"
                "**Fakten**: Kurze Sachen, die sie automatisch "
                "extrahiert — dein Name, Beruf, Hobbys, kürzliche "
                "Ereignisse. Bis zu 300 Fakten. Anzeige/Bearbeitung "
                "über das 📋-Symbol in der Kopfzeile.\n\n"
                "**Tagebuch**: Längere Reflexionen, die Ashley darüber "
                "schreibt, wie es dir in letzter Zeit ging. Wird "
                "automatisch täglich-ish generiert.\n\n"
                "**Vorlieben**: Explizite Präferenzen (Lieblingsgenres, "
                "was du magst/nicht magst). Sie aktualisiert diese, "
                "wenn du sagst „Ich liebe ...\" / „Ich hasse ...\".\n\n"
                "Alles lokal als JSON in `%APPDATA%\\ashley\\data\\` "
                "gespeichert."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Erinnerungen und wichtige Einträge",
            "content_md": (
                "**Erinnerungen**: Ashley kann Dinge planen, an die du "
                "sie erinnerst. „Erinnere mich um 15 Uhr daran, John "
                "anzurufen\" — wenn die Zeit kommt, pingt sie dich "
                "(Windows-Benachrichtigung + Chat-Nachricht).\n\n"
                "**Wichtige Einträge**: Eine separate Liste für Dinge, "
                "die du ohne Zeit verfolgen willst. „Füge `Milch "
                "kaufen` zu wichtig hinzu\" — erscheint im ⭐-Symbol in "
                "der Kopfzeile. Markiere als erledigt, wenn fertig.\n\n"
                "Beide werden in `%APPDATA%\\ashley\\data\\` als JSON "
                "gespeichert."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Proaktive Discovery und News-Feed",
            "content_md": (
                "Optional. Wenn AN, sucht Ashley selbstständig im Web "
                "nach Inhalten, die zu deinen Vorlieben passen "
                "(Trailer, News, neue Songs). Einträge erscheinen im "
                "📰-News-Feed in der Kopfzeile, **nicht** im Haupt-Chat "
                "— du wählst, wann du sie liest.\n\n"
                "**Aktivieren**: Einstellungen → 🔭 Proaktive Discovery "
                "→ AN.\n\n"
                "**Wann deaktivieren**: Wenn du nicht willst, dass "
                "Ashley deine LLM-Tokens für Hintergrundarbeit nutzt, "
                "oder wenn ihre Discovery Themen anschneidet, die du "
                "lieber meidest.\n\n"
                "**Hinweis**: Erfordert xAI oder OpenRouter als "
                "LLM-Provider. Deaktiviert bei Verwendung von Ollama "
                "(nur lokal)."
            ),
        },
        {
            "id": "providers",
            "icon": "🧠",
            "title": "LLM-Provider — wer treibt Ashleys Gehirn an",
            "content_md": (
                "Drei Optionen in Einstellungen → 🧠 LLM-Provider:\n\n"
                "**xAI Grok** (Standard): Cloud, Premium-Qualität. "
                "API-Key von x.ai erforderlich. Pay-per-Token.\n\n"
                "**OpenRouter**: Cloud, hunderte Modelle zur Auswahl. "
                "Key von openrouter.ai erforderlich. Pay-per-Token.\n\n"
                "**Ollama** (lokal): Lässt Modelle vollständig auf "
                "deinem Computer laufen (Llama 3.1, Mistral usw.). "
                "Kostenlos, aber langsamer und niedrigere Qualität als "
                "Cloud-Modelle. Erfordert Ollama, das auf "
                "`localhost:11434` läuft.\n\n"
                "**Datenschutzhinweis**: Mit xAI/OpenRouter werden "
                "deine Nachrichten an den Provider gesendet. Mit "
                "Ollama verlässt **nichts** deinen Computer."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Datenschutz — was lokal bleibt, was rausgeht",
            "content_md": (
                "**Bleibt lokal (immer)**:\n"
                "- Chat-Verlauf, Fakten, Tagebuch, Erinnerungen, "
                "Vorlieben\n"
                "- Spracherkennung (Whisper läuft auf deiner CPU)\n"
                "- Wake-Word-Erkennungsmodell\n"
                "- Alle Aktionen, die Ashley auf deinem System "
                "ausführt\n\n"
                "**Verlässt deinen Computer (nur wenn nötig)**:\n"
                "- Deine Nachrichten an den gewählten LLM-Provider "
                "(xAI/OpenRouter — Ollama hält alles lokal)\n"
                "- Sprachsynthese mit ElevenLabs (der Text von Ashleys "
                "Antwort wird zur Synthese an elevenlabs.io gesendet. "
                "Web Speech hält es lokal)\n"
                "- Discovery-Suchen, wenn aktiviert (LLM-getrieben)\n"
                "- Wenn du Ashley bittest, Musik abzuspielen, macht sie "
                "eine einzige anonyme YouTube-Suche, um den Titel zu "
                "einer Video-URL aufzulösen (kein Account, keine "
                "Cookies)\n\n"
                "**Datenort**: `%APPDATA%\\ashley\\data\\`. Du kannst "
                "alles löschen, indem du diesen Ordner entfernst.\n\n"
                "**Keine Telemetrie**: Ashley sendet null Analytics, "
                "Crash-Reports oder Nutzungsdaten irgendwohin. Die "
                "einzigen ausgehenden Verbindungen sind die oben "
                "aufgelisteten."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens und Kosten — wann jedes Feature Geld kostet",
            "content_md": (
                "**Kostenlos** (kein Token-Verbrauch):\n"
                "- Whisper STT, Wake Word, alle lokalen Aktionen\n"
                "- Web Speech TTS, Ollama LLM\n\n"
                "**Kostet Tokens** (xAI/OpenRouter berechnen pro "
                "Nachricht):\n"
                "- Jede Chat-Nachricht, die du Ashley schickst\n"
                "- Discovery (wenn AN, periodische LLM-Aufrufe im "
                "Hintergrund)\n"
                "- Tagebuch-Auto-Generierung\n\n"
                "**Kostet ElevenLabs-Credits** (Free-Tier ~10k "
                "Zeichen/Monat):\n"
                "- Jede TTS-Antwort, wenn ElevenLabs dein Sprach-"
                "Provider ist\n\n"
                "**Tipps zum Token-Sparen**:\n"
                "- Deaktiviere proaktive Discovery, wenn nicht "
                "benötigt\n"
                "- Nutze Ollama für lockeren Chat, xAI für ernsthafte "
                "Aufgaben\n"
                "- Nutze Web Speech für TTS, außer du willst wirklich "
                "die Premium-Stimme"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Tipps und Shortcuts",
            "content_md": (
                "**Tastatur**:\n"
                "- Enter — senden\n"
                "- Shift+Enter — neue Zeile in der Nachricht\n"
                "- Esc — schließt jeden offenen Dialog\n\n"
                "**Kopfzeilen-Symbole** (typischerweise links nach "
                "rechts):\n"
                "- ❓ dieses Handbuch\n"
                "- 📰 News-Feed (Badge mit Ungelesenen)\n"
                "- 📋 Liste extrahierter Fakten\n"
                "- ⭐ wichtige Einträge\n"
                "- 📔 Tagebuch\n"
                "- ⚡ Schalter für Systemaktionen\n"
                "- 🗣 natürlicher Sprachmodus\n"
                "- 🌍 Sprache\n"
                "- ⚙️ Einstellungen\n"
                "- 🗑 Chat löschen\n\n"
                "**Während Ashley denkt**: Die Schalter in der "
                "Kopfzeile (⚡ Aktionen, 🗣 Natürlich, Einstellungen "
                "usw.) reagieren während ihres Streamings vorübergehend "
                "nicht. Das ist Absicht — einen Schalter mitten in "
                "ihrer Antwort umzuschalten könnte sie in einem "
                "inkonsistenten Zustand hinterlassen (z.B. mit "
                "Aktionen AN agierend, aber der Prompt sagte AUS). "
                "Warte, bis sie fertig ist, und schalte dann um.\n\n"
                "**Pin on top**: Einstellungen → Fenster anpinnen — "
                "hält Ashley immer sichtbar über anderen Fenstern.\n\n"
                "**Rückgaberichtlinie**: 14 Tage ab Kauf, wenn du "
                "weniger als 40 Nachrichten gesendet hast."
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  РУССКИЙ (RUSSIAN)
# ─────────────────────────────────────────

_RU = {
    "title": "Добро пожаловать в Ashley — Руководство пользователя",
    "intro": (
        "Ashley — это десктопная AI-компаньонка, которая живёт на "
        "твоём компьютере. Она помнит ваши разговоры, может говорить "
        "и слушать, и может взаимодействовать с системой (открывать "
        "приложения, управлять музыкой, работать со вкладками "
        "браузера). Всё, что она хранит о тебе, живёт **только** на "
        "твоей машине — без облачной синхронизации, без телеметрии, "
        "без аналитики."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Чат с Ashley",
            "content_md": (
                "Пиши в поле внизу. Enter — отправить, Shift+Enter — "
                "новая строка. Ashley помнит до 50 сообщений "
                "контекста плюс список фактов, которые она "
                "автоматически извлекает из ваших разговоров.\n\n"
                "**Mood-теги**: Ashley использует одно из 7 выражений "
                "на сообщение (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Они управляют анимацией "
                "её портрета в углу.\n\n"
                "**Очистить историю чата**: нажми иконку корзины в "
                "шапке. Запросит подтверждение. Отменить нельзя."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Голос — распознавание и синтез речи",
            "content_md": (
                "**Говорить с Ashley**: нажми кнопку 🎤. Запись "
                "автоматически останавливается через 4 секунды "
                "тишины. Аудио расшифровывает Whisper, работающий "
                "**локально** на твоём компьютере — никогда не "
                "отправляется ни на какой сервер.\n\n"
                "**Слышать Ashley**: включи TTS в настройках. Два "
                "движка:\n"
                "- **Web Speech** (бесплатно, роботизированно, все "
                "данные остаются локально)\n"
                "- **ElevenLabs** (премиум, звучит естественно — "
                "текст отправляется на elevenlabs.io для синтеза. "
                "Нужен API-ключ)\n\n"
                "**Натуральный режим**: переключатель 🗣 в шапке "
                "убирает *жесты* типа *улыбается* из ответов — более "
                "чистое аудио."
            ),
        },
        {
            "id": "wakeword",
            "icon": "👂",
            "title": "Слово активации — постоянное прослушивание",
            "content_md": (
                "Когда ВКЛ, Ashley слушает твой микрофон в фоне и "
                "начинает запись, услышав своё имя. Модель "
                "обнаружения работает **на 100% локально** (~5 МБ, "
                "только CPU). Аудио НИКОГДА не покидает твой "
                "компьютер, пока ты не произнесёшь слово активации.\n\n"
                "**Активировать**: Настройки → 🎙 Слово активации → "
                "ВКЛ.\n\n"
                "**Как использовать**: просто скажи «Ashley» рядом с "
                "микрофоном. После звукового сигнала говори своё "
                "сообщение нормально. Детектор автоматически "
                "приостанавливается, пока ты печатаешь или держишь "
                "кнопку микрофона.\n\n"
                "**Когда отключить**: если ты не хочешь, чтобы "
                "микрофон был открыт в фоне, или если тебя раздражает "
                "уровень ложных срабатываний. Детектор настроен на <1 "
                "ложного срабатывания в час с телевизором на фоне, но "
                "каждый голос разный."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Системные действия — пусть Ashley кликает за тебя",
            "content_md": (
                "Ashley может выполнять действия на твоём компьютере: "
                "открывать приложения, регулировать громкость, "
                "включать музыку, закрывать вкладки браузера, ставить "
                "напоминания. **Opt-in** за переключателем ⚡ в "
                "шапке.\n\n"
                "**Примеры**:\n"
                "- «Открой блокнот» → запускает Notepad\n"
                "- «Громкость на 50» → ставит системную громкость\n"
                "- «Включи ту песню из Stranger Things» → открывает "
                "YouTube и проигрывает\n"
                "- «Закрой вкладку YouTube» → закрывает вкладки "
                "браузера по заголовку\n"
                "- «Напомни мне позвонить маме через 1 час» → "
                "ставит напоминание\n\n"
                "**Безопасные действия** (переключатель не нужен): "
                "сохранение фактов, отметка важных пунктов, "
                "напоминания.\n\n"
                "**Когда отключить**: если ты не доверяешь Ashley "
                "выбрать правильное действие, или хочешь избежать "
                "случайных изменений в системе. Переключатель "
                "действует на сессию — не сохраняется между "
                "перезапусками, если только не изменишь его в "
                "настройках.\n\n"
                "**Встроенный фильтр безопасности**: когда Ashley "
                "открывает приложение или закрывает окно, "
                "определённые символы блокируются из запроса — `&`, "
                "`|`, `;`, `<`, `>`, `\"`, `'`, `` ` ``, `$` и "
                "переводы строк. Это разделители команд и "
                "escape-символы, которые теоретически вредоносная "
                "веб-страница, скрейпленная Ashley, могла бы попытаться "
                "подсунуть в запрос, чтобы заставить твой компьютер "
                "выполнять произвольные команды (скачать файл, "
                "удалить папки и т.д.). Реальные имена приложений "
                "никогда не нуждаются в этих символах, поэтому "
                "блокировка ничего не стоит и закрывает эту дверь "
                "полностью. Если Ashley когда-нибудь скажет, что не "
                "смогла открыть что-то со странным именем — вот "
                "почему."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Современный режим браузера (CDP)",
            "content_md": (
                "Опциональный продвинутый режим, позволяющий Ashley "
                "управлять твоим браузером **напрямую** через Chrome "
                "DevTools Protocol вместо симуляции нажатий клавиш. "
                "**Быстрее**, **без видимого переключения вкладок**, "
                "и работает даже когда браузер свёрнут.\n\n"
                "**Активировать**: Настройки → 🌐 Современный режим "
                "браузера → ВКЛ. Мастер автоматически модифицирует "
                "ярлыки твоего браузера (Chrome/Edge/Brave/Opera), "
                "добавляя нужный флаг. Оригиналы сохраняются как "
                "бэкап.\n\n"
                "**После активации**: закрой и снова открой браузер, "
                "чтобы изменения вступили в силу.\n\n"
                "**Когда отключить**: если не хочешь иметь "
                "отладочный порт открытым на localhost (низкий риск "
                "для пользователей без активного вредоносного ПО, но "
                "из соображений эшелонированной защиты)."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Память — факты, дневник, вкусы",
            "content_md": (
                "Ashley помнит вещи о тебе между сессиями. Три "
                "слоя:\n\n"
                "**Факты**: короткие вещи, которые она извлекает "
                "автоматически — твоё имя, работа, хобби, недавние "
                "события. До 300 фактов. Просмотр/редактирование "
                "через иконку 📋 в шапке.\n\n"
                "**Дневник**: более длинные размышления Ashley о "
                "том, как у тебя дела в последнее время. "
                "Автогенерируется ~ежедневно.\n\n"
                "**Вкусы**: явные предпочтения (любимые жанры, что "
                "тебе нравится/не нравится). Она обновляет их, когда "
                "ты говоришь «обожаю...» / «ненавижу...».\n\n"
                "Всё хранится локально как JSON в "
                "`%APPDATA%\\ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Напоминания и важные пункты",
            "content_md": (
                "**Напоминания**: Ashley может планировать вещи, "
                "которые ты просишь её запомнить. «Напомни мне "
                "позвонить Джону в 15:00» — когда время приходит, "
                "она пингует тебя (уведомление Windows + сообщение в "
                "чате).\n\n"
                "**Важные пункты**: отдельный список для вещей, "
                "которые ты хочешь отслеживать без времени. «Добавь "
                "`купить молоко` в важное» — появляется в иконке ⭐ "
                "в шапке. Отметь как сделано, когда закончишь.\n\n"
                "Оба хранятся в `%APPDATA%\\ashley\\data\\` как JSON."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Проактивный discovery и лента новостей",
            "content_md": (
                "Опционально. Когда ВКЛ, Ashley сама ищет в вебе "
                "контент, соответствующий твоим вкусам (трейлеры, "
                "новости, новые песни). Пункты появляются в ленте 📰 "
                "в шапке, **а не** в основном чате — ты выбираешь, "
                "когда их читать.\n\n"
                "**Активировать**: Настройки → 🔭 Проактивный "
                "discovery → ВКЛ.\n\n"
                "**Когда отключить**: если ты не хочешь, чтобы "
                "Ashley тратила твои LLM-токены на фоновую работу, "
                "или если её discovery затрагивает темы, которых "
                "лучше избегать.\n\n"
                "**Заметка**: требует xAI или OpenRouter как "
                "LLM-провайдера. Отключено при использовании Ollama "
                "(только локально)."
            ),
        },
        {
            "id": "providers",
            "icon": "🧠",
            "title": "LLM-провайдер — кто питает мозг Ashley",
            "content_md": (
                "Три варианта в Настройки → 🧠 LLM-провайдер:\n\n"
                "**xAI Grok** (по умолчанию): облако, премиум-"
                "качество. Нужен API-ключ от x.ai. Оплата за "
                "токены.\n\n"
                "**OpenRouter**: облако, сотни моделей на выбор. "
                "Нужен ключ от openrouter.ai. Оплата за токены.\n\n"
                "**Ollama** (локально): запускает модели полностью "
                "на твоём компьютере (Llama 3.1, Mistral и т.д.). "
                "Бесплатно, но медленнее и качеством ниже облачных "
                "моделей. Требует Ollama, работающий на "
                "`localhost:11434`.\n\n"
                "**Заметка о приватности**: с xAI/OpenRouter твои "
                "сообщения отправляются провайдеру. С Ollama "
                "**ничего** не покидает твой компьютер."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Приватность — что остаётся локально, что уходит",
            "content_md": (
                "**Остаётся локально (всегда)**:\n"
                "- История чата, факты, дневник, напоминания, вкусы\n"
                "- Распознавание речи (Whisper работает на твоём "
                "CPU)\n"
                "- Модель обнаружения слова активации\n"
                "- Все действия, которые Ashley выполняет в твоей "
                "системе\n\n"
                "**Покидает твой компьютер (только когда нужно)**:\n"
                "- Твои сообщения выбранному LLM-провайдеру (xAI/"
                "OpenRouter — Ollama держит всё локально)\n"
                "- Синтез речи через ElevenLabs (текст ответа Ashley "
                "отправляется на elevenlabs.io для синтеза. Web "
                "Speech держит локально)\n"
                "- Поиски discovery, когда включено (LLM-driven)\n"
                "- Когда ты просишь Ashley включить музыку, она "
                "делает один анонимный поиск в YouTube, чтобы "
                "разрешить название в URL видео (без аккаунта, без "
                "cookies)\n\n"
                "**Местоположение данных**: "
                "`%APPDATA%\\ashley\\data\\`. Ты можешь стереть всё, "
                "удалив эту папку.\n\n"
                "**Без телеметрии**: Ashley не отправляет ноль "
                "аналитики, отчётов о крашах или данных об "
                "использовании никуда. Единственные исходящие "
                "соединения — те, что перечислены выше."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Токены и затраты — когда какая фича стоит денег",
            "content_md": (
                "**Бесплатно** (без расхода токенов):\n"
                "- Whisper STT, слово активации, все локальные "
                "действия\n"
                "- Web Speech TTS, Ollama LLM\n\n"
                "**Стоит токенов** (xAI/OpenRouter берут плату за "
                "сообщение):\n"
                "- Каждое сообщение в чате, которое ты шлёшь Ashley\n"
                "- Discovery (если ВКЛ, периодические LLM-вызовы в "
                "фоне)\n"
                "- Автогенерация дневника\n\n"
                "**Стоит кредитов ElevenLabs** (бесплатный тариф "
                "~10k символов/месяц):\n"
                "- Каждый TTS-ответ, если ElevenLabs — твой "
                "голосовой провайдер\n\n"
                "**Советы по экономии токенов**:\n"
                "- Отключай проактивный Discovery, когда не нужен\n"
                "- Используй Ollama для непринуждённого чата, xAI "
                "для серьёзных задач\n"
                "- Используй Web Speech для TTS, если только ты "
                "действительно не хочешь премиум-голос"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Советы и горячие клавиши",
            "content_md": (
                "**Клавиатура**:\n"
                "- Enter — отправить\n"
                "- Shift+Enter — новая строка в сообщении\n"
                "- Esc — закрывает любой открытый диалог\n\n"
                "**Иконки шапки** (обычно слева направо):\n"
                "- ❓ это руководство\n"
                "- 📰 лента новостей (бейдж непрочитанных)\n"
                "- 📋 список извлечённых фактов\n"
                "- ⭐ важные пункты\n"
                "- 📔 дневник\n"
                "- ⚡ переключатель системных действий\n"
                "- 🗣 натуральный голосовой режим\n"
                "- 🌍 язык\n"
                "- ⚙️ настройки\n"
                "- 🗑 очистить чат\n\n"
                "**Пока Ashley думает**: переключатели в шапке "
                "(⚡ Действия, 🗣 Натуральный, настройки и т.д.) "
                "временно не реагируют, пока она стримит. Это "
                "сделано намеренно — переключение в середине её "
                "ответа могло бы оставить её в несогласованном "
                "состоянии (например, действуя с Действия ВКЛ, но "
                "промпт говорил ВЫКЛ). Подожди, пока закончит, "
                "потом переключай.\n\n"
                "**Поверх остальных**: Настройки → Закрепить окно — "
                "держит Ashley всегда видимой поверх других окон.\n\n"
                "**Политика возврата**: 14 дней с момента покупки, "
                "если ты отправил меньше 40 сообщений."
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  한국어 (KOREAN)
# ─────────────────────────────────────────

_KO = {
    "title": "Ashley에 오신 것을 환영합니다 — 사용자 매뉴얼",
    "intro": (
        "Ashley는 오빠 컴퓨터에 사는 데스크톱 AI 동반자야. "
        "대화를 기억하고, 말하고 들을 수 있고, 시스템과 상호작용도 "
        "할 수 있어 (앱 열기, 음악 제어, 브라우저 탭 관리). 오빠에 "
        "대해 저장하는 모든 건 **오직** 이 컴퓨터에만 살아 — 클라우드 "
        "동기화 없음, 텔레메트리 없음, 분석 없음."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Ashley와 채팅",
            "content_md": (
                "아래 입력란에 입력해. Enter로 전송, Shift+Enter로 "
                "줄바꿈. Ashley는 최대 50개 메시지의 컨텍스트를 "
                "기억하고, 대화에서 자동으로 추출한 사실 목록도 "
                "같이 저장해.\n\n"
                "**Mood 태그**: Ashley는 메시지마다 7가지 표정 중 "
                "하나를 사용해 (excited, embarrassed, tsundere, "
                "soft, surprised, proud, default). 이게 구석에 "
                "있는 초상화 애니메이션을 움직여.\n\n"
                "**채팅 기록 지우기**: 헤더의 휴지통 아이콘을 눌러. "
                "삭제 전에 확인해. 되돌릴 수 없어."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "음성 — 음성 인식과 음성 합성",
            "content_md": (
                "**Ashley에게 말하기**: 🎤 마이크 버튼을 클릭해. "
                "녹음은 4초간 침묵 후 자동으로 멈춰. 오디오는 "
                "컴퓨터에서 **로컬로** 실행되는 Whisper로 텍스트화돼 "
                "— 어떤 서버에도 전송되지 않아.\n\n"
                "**Ashley 듣기**: 설정에서 TTS를 켜. 두 가지 엔진:\n"
                "- **Web Speech** (무료, 기계적, 모든 데이터가 "
                "로컬에 남음)\n"
                "- **ElevenLabs** (프리미엄, 자연스럽게 들림 — "
                "합성을 위해 텍스트가 elevenlabs.io로 전송됨. API "
                "키 필요)\n\n"
                "**자연스러운 모드**: 헤더의 🗣 토글이 답변에서 "
                "*미소짓다* 같은 *제스처*를 제거해 — 더 깨끗한 "
                "오디오."
            ),
        },
        {
            "id": "wakeword",
            "icon": "👂",
            "title": "웨이크 워드 — 항상 켜진 청취",
            "content_md": (
                "켜져 있을 때 Ashley는 백그라운드에서 마이크를 듣고, "
                "자기 이름을 들으면 녹음을 시작해. 감지 모델은 "
                "**100% 로컬**로 실행돼 (~5MB, CPU만). 웨이크 "
                "워드를 말하기 전까지는 오디오가 절대 컴퓨터를 "
                "떠나지 않아.\n\n"
                "**활성화**: 설정 → 🎙 웨이크 워드 → 켜기.\n\n"
                "**사용법**: 마이크 근처에서 그냥 \"Ashley\"라고 "
                "말해. 차임 소리 후에 평소처럼 메시지를 말해. "
                "오빠가 타이핑하거나 마이크 버튼을 누르고 있는 "
                "동안 감지기는 자동으로 일시 정지돼.\n\n"
                "**비활성화할 때**: 마이크가 백그라운드에서 열려 "
                "있는 게 싫거나, 오탐률이 거슬릴 때. 감지기는 "
                "TV가 배경에 있어도 시간당 1번 미만의 오탐으로 "
                "조정되어 있지만, 목소리는 사람마다 달라."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "시스템 액션 — Ashley가 대신 클릭하게 해줘",
            "content_md": (
                "Ashley는 컴퓨터에서 액션을 수행할 수 있어: 앱 "
                "열기, 볼륨 조절, 음악 재생, 브라우저 탭 닫기, "
                "리마인더 설정. 헤더의 ⚡ 토글 뒤에 **opt-in**으로 "
                "있어.\n\n"
                "**예시**:\n"
                "- \"메모장 열어줘\" → Notepad 실행\n"
                "- \"볼륨 50으로\" → 시스템 볼륨 설정\n"
                "- \"Stranger Things 그 노래 틀어줘\" → YouTube를 "
                "열어서 재생\n"
                "- \"YouTube 탭 닫아\" → 제목으로 브라우저 탭 닫기\n"
                "- \"1시간 후에 엄마한테 전화하라고 알려줘\" → "
                "리마인더 예약\n\n"
                "**안전한 액션** (토글 필요 없음): 사실 저장, "
                "중요 항목 표시, 리마인더 예약.\n\n"
                "**비활성화할 때**: Ashley가 올바른 액션을 취할지 "
                "신뢰할 수 없거나, 실수로 시스템이 변경되는 걸 "
                "피하고 싶을 때. 토글은 세션별이야 — 설정에서 "
                "바꾸지 않는 한 재시작 사이에 유지되지 않아.\n\n"
                "**내장 안전 필터**: Ashley가 앱을 열거나 창을 "
                "닫을 때, 특정 문자가 요청에서 차단돼 — `&`, `|`, "
                "`;`, `<`, `>`, `\"`, `'`, `` ` ``, `$` 그리고 "
                "줄바꿈. 이건 명령어 구분 문자와 escape 문자야. "
                "이론적으로는 Ashley가 스크랩한 악성 웹페이지가 "
                "이걸 요청에 몰래 넣어서 컴퓨터가 임의 명령을 "
                "실행하게 만들 수 있어 (파일 다운로드, 폴더 삭제 "
                "등). 진짜 앱 이름엔 절대 이런 기호가 필요 없으니 "
                "차단해도 비용 없고 그 문을 완전히 닫는 거야. "
                "Ashley가 이상한 이름으로 뭔가 못 열었다고 하면, "
                "그게 이유야."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "최신 브라우저 모드 (CDP)",
            "content_md": (
                "Ashley가 키 입력을 시뮬레이션하는 대신 Chrome "
                "DevTools Protocol을 통해 브라우저를 **직접** "
                "제어할 수 있게 하는 선택적 고급 모드. **더 빠르고**, "
                "**보이는 탭 전환 없음**, 브라우저가 최소화되어 "
                "있어도 작동해.\n\n"
                "**활성화**: 설정 → 🌐 최신 브라우저 모드 → 켜기. "
                "마법사가 자동으로 브라우저 바로가기 (Chrome/Edge/"
                "Brave/Opera)를 수정해서 필요한 플래그를 추가해. "
                "원본은 백업돼.\n\n"
                "**활성화 후**: 변경 사항이 적용되도록 브라우저를 "
                "닫고 다시 열어줘.\n\n"
                "**비활성화할 때**: localhost에 디버깅 포트가 "
                "열려 있는 게 싫을 때 (활성 멀웨어가 없는 사용자에겐 "
                "낮은 위험이지만, 다층 방어 차원에서)."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "기억 — 사실, 일기, 취향",
            "content_md": (
                "Ashley는 세션 사이에 오빠에 대한 것들을 기억해. "
                "세 가지 층:\n\n"
                "**사실**: 자동으로 추출하는 짧은 정보 — 이름, "
                "직업, 취미, 최근 일들. 최대 300개. 헤더의 📋 "
                "아이콘으로 보기/편집.\n\n"
                "**일기**: 오빠가 최근에 어떻게 지냈는지에 대해 "
                "Ashley가 쓰는 더 긴 성찰. 거의 매일 자동 생성돼.\n\n"
                "**취향**: 명시적인 선호 (좋아하는 장르, 좋아하거나 "
                "싫어하는 것들). \"~를 사랑해\" / \"~를 싫어해\"라고 "
                "말하면 업데이트해.\n\n"
                "전부 `%APPDATA%\\ashley\\data\\`에 JSON으로 로컬 "
                "저장돼."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "리마인더와 중요 항목",
            "content_md": (
                "**리마인더**: Ashley는 기억해달라고 한 일을 예약할 "
                "수 있어. \"3시에 John한테 전화하라고 알려줘\" — "
                "시간이 되면 핑을 줘 (Windows 알림 + 채팅 메시지).\n\n"
                "**중요 항목**: 시간 없이 추적하고 싶은 것들을 "
                "위한 별도 목록. \"`우유 사기`를 중요에 추가해\" "
                "— 헤더의 ⭐ 아이콘에 나타나. 끝나면 완료로 "
                "표시해.\n\n"
                "둘 다 `%APPDATA%\\ashley\\data\\`에 JSON으로 "
                "저장돼."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "사전 탐색과 뉴스 피드",
            "content_md": (
                "선택. 켜져 있을 때 Ashley는 오빠 취향에 맞는 "
                "콘텐츠 (트레일러, 뉴스, 새 노래)를 스스로 웹에서 "
                "찾아. 항목들은 헤더의 📰 뉴스 피드에 나타나고, "
                "메인 채팅엔 **나타나지 않아** — 언제 읽을지는 "
                "오빠가 선택해.\n\n"
                "**활성화**: 설정 → 🔭 사전 탐색 → 켜기.\n\n"
                "**비활성화할 때**: Ashley가 백그라운드 작업에 "
                "LLM 토큰을 쓰는 게 싫거나, 탐색이 피하고 싶은 "
                "주제를 건드릴 때.\n\n"
                "**참고**: LLM 제공자로 xAI 또는 OpenRouter 필요. "
                "Ollama (로컬 전용) 사용 시 비활성화돼."
            ),
        },
        {
            "id": "providers",
            "icon": "🧠",
            "title": "LLM 제공자 — Ashley의 두뇌를 움직이는 것",
            "content_md": (
                "설정 → 🧠 LLM 제공자에서 세 가지 옵션:\n\n"
                "**xAI Grok** (기본): 클라우드, 프리미엄 품질. "
                "x.ai의 API 키 필요. 토큰당 과금.\n\n"
                "**OpenRouter**: 클라우드, 수백 개 모델 중 선택 "
                "가능. openrouter.ai의 키 필요. 토큰당 과금.\n\n"
                "**Ollama** (로컬): 모델을 컴퓨터에서 완전히 "
                "실행 (Llama 3.1, Mistral 등). 무료지만 클라우드 "
                "모델보다 느리고 품질이 낮음. `localhost:11434`에 "
                "Ollama가 실행 중이어야 해.\n\n"
                "**프라이버시 참고**: xAI/OpenRouter에선 메시지가 "
                "제공자에게 전송돼. Ollama에선 **아무것도** 컴퓨터를 "
                "떠나지 않아."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "프라이버시 — 무엇이 로컬에 남고 무엇이 나가는지",
            "content_md": (
                "**로컬에 남음 (항상)**:\n"
                "- 채팅 기록, 사실, 일기, 리마인더, 취향\n"
                "- 음성 인식 (Whisper는 CPU에서 실행)\n"
                "- 웨이크 워드 감지 모델\n"
                "- Ashley가 시스템에서 수행하는 모든 액션\n\n"
                "**컴퓨터를 떠남 (필요할 때만)**:\n"
                "- 선택한 LLM 제공자에게 보내는 메시지 (xAI/"
                "OpenRouter — Ollama는 모든 걸 로컬에 유지)\n"
                "- ElevenLabs로 음성 합성 (Ashley 답변 텍스트가 "
                "합성을 위해 elevenlabs.io로 전송됨. Web Speech는 "
                "로컬 유지)\n"
                "- 활성화된 경우 탐색 검색 (LLM 기반)\n"
                "- Ashley에게 음악 재생을 요청하면, 제목을 비디오 "
                "URL로 변환하기 위해 익명의 YouTube 검색 1회 수행 "
                "(계정 없음, 쿠키 없음)\n\n"
                "**데이터 위치**: `%APPDATA%\\ashley\\data\\`. 이 "
                "폴더를 삭제하면 모든 걸 지울 수 있어.\n\n"
                "**텔레메트리 없음**: Ashley는 분석, 크래시 보고서, "
                "사용 데이터를 어디에도 전혀 보내지 않아. 유일한 "
                "외부 연결은 위에 나열된 것들뿐이야."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "토큰과 비용 — 어떤 기능이 언제 돈이 드는지",
            "content_md": (
                "**무료** (토큰 사용 없음):\n"
                "- Whisper STT, 웨이크 워드, 모든 로컬 액션\n"
                "- Web Speech TTS, Ollama LLM\n\n"
                "**토큰 비용** (xAI/OpenRouter는 메시지당 과금):\n"
                "- Ashley에게 보내는 모든 채팅 메시지\n"
                "- 탐색 (켜져 있으면 백그라운드에서 주기적인 "
                "LLM 호출)\n"
                "- 일기 자동 생성\n\n"
                "**ElevenLabs 크레딧 비용** (무료 등급 월 "
                "~10k자):\n"
                "- ElevenLabs가 음성 제공자라면 모든 TTS 응답\n\n"
                "**토큰 절약 팁**:\n"
                "- 필요 없을 땐 사전 탐색 끄기\n"
                "- 가벼운 채팅엔 Ollama, 진지한 작업엔 xAI 사용\n"
                "- 정말 프리미엄 음성을 원하지 않는 한 Web Speech "
                "TTS 사용"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "팁과 단축키",
            "content_md": (
                "**키보드**:\n"
                "- Enter — 전송\n"
                "- Shift+Enter — 메시지 내 줄바꿈\n"
                "- Esc — 열린 다이얼로그 닫기\n\n"
                "**헤더 아이콘** (보통 왼쪽에서 오른쪽):\n"
                "- ❓ 이 매뉴얼\n"
                "- 📰 뉴스 피드 (안 읽은 수 배지)\n"
                "- 📋 추출된 사실 목록\n"
                "- ⭐ 중요 항목\n"
                "- 📔 일기\n"
                "- ⚡ 시스템 액션 토글\n"
                "- 🗣 자연스러운 음성 모드\n"
                "- 🌍 언어\n"
                "- ⚙️ 설정\n"
                "- 🗑 채팅 지우기\n\n"
                "**Ashley가 생각하는 동안**: 헤더의 토글들 (⚡ "
                "액션, 🗣 자연스러움, 설정 등)은 그녀가 스트리밍 "
                "중일 때 일시적으로 응답하지 않아. 의도적인 거야 "
                "— 응답 도중에 토글을 바꾸면 일관성 없는 상태가 "
                "될 수 있어 (예: 액션 켜진 채로 행동하는데 프롬프트는 "
                "꺼졌다고 했을 때). 끝날 때까지 기다렸다가 토글해.\n\n"
                "**위에 고정**: 설정 → 창 고정 — Ashley를 항상 "
                "다른 창들 위에 보이게 유지해.\n\n"
                "**환불 정책**: 구매 후 14일 이내, 메시지를 40개 "
                "미만 보냈을 때."
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────

MANUAL = {
    "en": _EN,
    "es": _ES,
    "fr": _FR,
    "ja": _JA,
    "de": _DE,
    "ru": _RU,
    "ko": _KO,
}


def get_manual(lang: str) -> dict:
    """Devuelve el manual en el idioma pedido. Fallback a EN si lang
    no soportado."""
    return MANUAL.get(lang, MANUAL["en"])
