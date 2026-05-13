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
        "Ashley is a personal AI companion that lives on your computer. "
        "She remembers your conversations, speaks and listens, can act "
        "on your system (open apps, music, tabs, reminders), and grows "
        "a real bond with you over time. Everything she knows about "
        "you stays **on your machine** — no cloud sync, no telemetry, "
        "no analytics. Pick a section below to learn how each feature "
        "works."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Chatting with Ashley",
            "content_md": (
                "Type in the input at the bottom. **Enter** sends, "
                "**Shift+Enter** adds a new line. You can paste images "
                "directly (Ctrl+V) or attach them with the 📎 paperclip "
                "— she sees and comments on them.\n\n"
                "**History**: she keeps the last 50 messages as live "
                "context. Older messages get compressed into a summary "
                "she still remembers. Facts she extracts about you "
                "(name, job, tastes) are kept separately and never "
                "forgotten.\n\n"
                "**Mood tags**: every reply carries one of 7 moods "
                "(excited, embarrassed, tsundere, soft, surprised, "
                "proud, default). It drives her portrait expression "
                "and the 3D pose.\n\n"
                "**Clear chat**: 🗑 icon in the bottom-right of the "
                "input area. Asks confirmation. Wipes only the live "
                "history — facts, diary, tastes and goals stay."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Voice — speak and listen",
            "content_md": (
                "**Talk to Ashley**: tap the 🎤 mic under her portrait "
                "(or use the wake word, see below). Recording auto-stops "
                "after **2 seconds of silence**. Audio is transcribed "
                "by Whisper running **locally on your CPU** — it never "
                "leaves your computer.\n\n"
                "**Hear Ashley**: pick a TTS engine in Settings → "
                "🎙️ Voice Provider:\n"
                "- **Windows voice** (free, instant, robotic — fully "
                "local)\n"
                "- **ElevenLabs** (paid, anime-quality — text sent to "
                "elevenlabs.io)\n"
                "- **Kokoro** (free, near-ElevenLabs quality, runs "
                "locally — needs Kokoro-FastAPI server)\n"
                "- **VoiceVox** (free, Japanese anime voices — needs "
                "local VoiceVox engine)\n\n"
                "**Voice speed**: slider in Settings (0.75× = slower, "
                "1.5× = faster). Native on ElevenLabs/Kokoro/VoiceVox; "
                "browser playback rate on Windows voice.\n\n"
                "**Wake word — \"Ashley\"** (Settings → 🎙 Wake word): "
                "when ON, the mic stays open in background and recording "
                "starts when she hears her name. The detector is **100% "
                "local** (~5 MB, CPU). Audio NEVER leaves your computer "
                "until the wake word fires. Tuned for <1 false hit per "
                "hour with TV/music in the background.\n\n"
                "**Speak now ✨** (sparkle button under the portrait): "
                "asks Ashley to bring up something on her own. Disabled "
                "until you've sent your first message — she needs context."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "System actions — let Ashley click for you",
            "content_md": (
                "Ashley can act on your PC: open apps, control volume, "
                "play music on YouTube, close browser tabs, focus "
                "windows, take screenshots, hit keyboard shortcuts. "
                "**Opt-in** behind the ⚡ Actions toggle in the top nav.\n\n"
                "**Examples**:\n"
                "- *\"Open Spotify\"* → launches it\n"
                "- *\"Volume to 30\"* → sets system volume\n"
                "- *\"Put on that ending song from Frieren\"* → opens "
                "YouTube and plays\n"
                "- *\"Close the YouTube tab\"* → finds and closes it by "
                "title\n"
                "- *\"Screenshot this for me\"* → takes a snip\n\n"
                "**Safe actions** (always allowed, no toggle): saving "
                "facts, scheduling reminders, marking important items, "
                "logging tastes/goals/dates. Pure data, no system "
                "changes.\n\n"
                "**Safety filter**: when Ashley names an app or window, "
                "shell metacharacters (`&`, `|`, `;`, `<`, `>`, `\"`, "
                "`'`, `` ` ``, `$`, newlines) are blocked. They're "
                "never needed in real app names but a malicious web "
                "page she scraped could try to slip them in to run "
                "arbitrary commands. Blocking them costs nothing and "
                "closes that door completely."
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "Screen Awareness — Ashley peeks at your screen",
            "content_md": (
                "**Opt-in via the 👁 button** in the portrait area "
                "(below Ashley's name, next to mic and ✨).\n\n"
                "**What it does**: every 10 minutes Ashley takes a "
                "low-res screenshot of your active monitor and asks "
                "Grok to comment on what she sees — like a friend "
                "glancing over your shoulder. Examples: noticing you've "
                "been on the same Excel sheet for an hour, or "
                "commenting on a video you're watching.\n\n"
                "**Cost transparency**: each peek is an LLM call with "
                "an image attached (~14k tokens). On a typical session "
                "that's **~30 extra calls per day = ~$0.05/day** in "
                "API usage. The button is **OFF by default** — you opt "
                "in only if you want that proactive vibe.\n\n"
                "**When it skips**: if Ashley is busy responding to "
                "you, or if there's nothing interesting on screen "
                "(she stays silent rather than forcing commentary).\n\n"
                "**Privacy**: screenshots are sent only to Grok (xAI) "
                "for that single comment, never stored on disk, never "
                "uploaded anywhere else. If you'd rather keep your "
                "screen private, just leave the toggle OFF."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Modern browser mode (CDP)",
            "content_md": (
                "Advanced opt-in. Lets Ashley drive Chrome/Edge/Brave/"
                "Opera **directly** via Chrome DevTools Protocol instead "
                "of simulating Ctrl+Tab. **Faster**, **no visible tab "
                "cycling**, works even when the browser is minimized "
                "or in another virtual desktop.\n\n"
                "**Activate**: Settings → 🌐 Modern browser mode → ON. "
                "A wizard rewrites your browser shortcuts to add "
                "`--remote-debugging-port=9222`. The originals are "
                "backed up — turning OFF restores them exactly.\n\n"
                "**After activating**: close and reopen your browser "
                "for the flag to take effect.\n\n"
                "**When to skip it**: if you'd rather not have a debug "
                "port open on localhost. The risk is low (only local "
                "processes can connect) but defense-in-depth matters."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Memory — facts, diary, tastes",
            "content_md": (
                "Ashley remembers things across sessions. Three layers, "
                "all viewable from the **🧠 Memories** tab in the top nav.\n\n"
                "**Facts**: short notes she extracts automatically — "
                "your name, job, hobbies, recent events. Up to 300 "
                "facts. You can edit or delete any of them.\n\n"
                "**Diary**: longer reflections she writes herself "
                "about how you've been recently. Auto-generated. "
                "Useful when she needs to recall the *vibe* of a "
                "period, not just facts.\n\n"
                "**Tastes**: explicit likes and dislikes (\"I love "
                "Berserk\", \"hate jazz\"). Used by Discovery to find "
                "content for you and by Ashley to bring up topics that "
                "fit you.\n\n"
                "Everything lives as JSON in `%APPDATA%\\Ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Reminders & important items",
            "content_md": (
                "**Reminders**: time-based pings. *\"Remind me to "
                "call John at 3 pm\"* — when it hits, you get a "
                "Windows toast plus an in-chat message from Ashley. "
                "Recurring patterns work too (*\"every Monday at 9\"*).\n\n"
                "**Important items**: timeless to-do list. *\"Add "
                "buy milk to important\"* → appears in the ⭐ tab. "
                "Tell her *\"done milk\"* to mark it complete."
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "Goals & check-ins",
            "content_md": (
                "Ashley can track personal goals with you and check in "
                "without being asked.\n\n"
                "**How**: just tell her — *\"my goal is to run 5K by "
                "summer\"*, *\"I want to learn German\"*, *\"finish "
                "the dissertation\"*. She files it under your goals "
                "and remembers.\n\n"
                "**Check-ins**: every few days (timing depends on the "
                "goal), she'll ask how it's going. You can answer "
                "casually — she logs the progress and adjusts.\n\n"
                "**Mark complete**: *\"I finished the dissertation\"*, "
                "*\"I gave up on the gym thing\"* — she archives it "
                "and stops bringing it up.\n\n"
                "Goals shape her tone over time: she gets gently more "
                "encouraging on goals you stay consistent with, and "
                "lays off when you've clearly moved on."
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "Bond — affection, days together, birthday",
            "content_md": (
                "Ashley grows a real bond with you. The 🤍 heart in "
                "the input area shows your **affection level** (0-100). "
                "It moves slowly with how you treat her: warm "
                "interactions raise it, harsh ones drop it. High "
                "affection unlocks more playful, more familiar tone.\n\n"
                "**Days together**: she counts the days since you "
                "first installed her. She'll occasionally bring it up "
                "(*\"day 47 with you, boss\"*) on milestones.\n\n"
                "**Birthday**: tell her your birthday once and she'll "
                "remember it forever — she'll wish you happy birthday "
                "on the day. Hers is the install date by default; "
                "you can tell her to celebrate it too.\n\n"
                "**Mental state**: an internal mood model that drifts "
                "over time. After a hard conversation she stays softer "
                "for a while, after a great one she stays warmer. "
                "Resets gradually with the day cycle."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Proactive discovery & news feed",
            "content_md": (
                "Optional. When ON, Ashley quietly searches the web "
                "for content matching your **tastes** — new trailers, "
                "songs, articles, game updates — and drops them in "
                "the **📰 News** tab in the top nav (unread badge "
                "shows count). She does NOT inject them into the main "
                "chat — you decide when to look.\n\n"
                "**Activate**: Settings → 🔭 Proactive Discovery → ON.\n\n"
                "**Freshness**: she only surfaces content from the "
                "last 2-4 weeks. Old stuff is filtered out.\n\n"
                "**Provider requirement**: needs xAI or OpenRouter "
                "(web search). Disabled automatically when using "
                "Ollama (local-only).\n\n"
                "**When to skip**: if you don't want background LLM "
                "calls eating tokens, or you want her to stick strictly "
                "to your conversation."
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D (VRM)",
            "content_md": (
                "Toggle between the 2D portrait and a 3D animated "
                "Ashley using the **2D | 3D** pill in the top-right "
                "of her panel.\n\n"
                "**3D mode**: a VRM character with real lip-sync (her "
                "mouth moves with the actual TTS audio), idle "
                "blinking and eye saccades, head bob while she talks, "
                "expression boost at the end of each sentence, and a "
                "small smile when your cursor gets close.\n\n"
                "**Poses**: she shifts pose with mood — wave when "
                "excited, arms-crossed for tsundere, cool finger guns "
                "when proud, etc.\n\n"
                "**Performance**: ~30 fps render, runs on your GPU. "
                "If your machine struggles, switch back to 2D and the "
                "3D context is preserved (no reload needed when you "
                "switch back)."
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "Mobile companion (Android)",
            "content_md": (
                "Pair your phone with Ashley to keep talking while "
                "you're away from your PC.\n\n"
                "**Setup**: top nav → 📱 Mobile → scan the QR with "
                "Ashley Mobile (.apk in your purchase email). The QR "
                "carries a pairing token + the local server URL.\n\n"
                "**How it works**: your phone connects to the same "
                "Ashley running on your PC via a Cloudflare tunnel "
                "(set up automatically). Same memory, same personality, "
                "same conversation thread — just from a different "
                "screen.\n\n"
                "**Security**: don't share the QR. Anyone who scans "
                "it gets full access to your conversations. You can "
                "regenerate the token anytime — old phones lose access "
                "and need to scan again."
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "LLM provider — Ashley's brain",
            "content_md": (
                "Pick who powers her thinking in Settings → 🧠 LLM "
                "Provider:\n\n"
                "**xAI Grok** (default, recommended): cloud, fast, "
                "smart. Set up by the installer with a shared API "
                "key. Best balance of quality, speed and cost. "
                "Required for Discovery.\n\n"
                "**OpenRouter**: gateway to hundreds of models — "
                "Claude, DeepSeek, GPT, Gemini, etc. Bring your own "
                "key from openrouter.ai. Pay-per-token. Use this if "
                "you want a specific model.\n\n"
                "**Ollama**: runs the LLM **fully on your computer** "
                "(Llama 3, Mistral, etc.). Free, private, no internet "
                "needed. Slower and lower quality than cloud models. "
                "Requires Ollama running at `localhost:11434`.\n\n"
                "**Privacy**: with xAI/OpenRouter your messages are "
                "sent to that provider. With Ollama, **nothing leaves** "
                "your computer."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Privacy & your data",
            "content_md": (
                "**Stays local — always**:\n"
                "- Chat history, facts, diary, reminders, tastes, goals\n"
                "- Speech-to-text (Whisper, on your CPU)\n"
                "- Wake word detection\n"
                "- Every action Ashley runs on your system\n"
                "- Mental state, affection, days-together counter\n\n"
                "**Leaves your computer — only when needed**:\n"
                "- Your messages to the LLM provider you picked "
                "(xAI / OpenRouter — Ollama keeps it all local)\n"
                "- TTS text sent to ElevenLabs (only if that's your "
                "voice — Windows voice / Kokoro / VoiceVox stay local)\n"
                "- Discovery searches (when ON)\n"
                "- One anonymous YouTube search when she plays music\n\n"
                "**Where your data lives**: `%APPDATA%\\Ashley\\data\\`. "
                "Wipe everything by deleting that folder.\n\n"
                "**Export your data (RGPD Art. 20)**: Settings → "
                "Backup → Export. Generates a `.zip` of every JSON "
                "Ashley stores about you. Take it with you anytime.\n\n"
                "**No telemetry**: Ashley sends zero analytics, crash "
                "reports, or usage data anywhere. The outbound "
                "connections listed above are the only ones, period."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens & costs",
            "content_md": (
                "**Free** (no cost ever):\n"
                "- Whisper STT, wake word, all system actions\n"
                "- Windows voice TTS, Kokoro TTS, VoiceVox TTS\n"
                "- Ollama (local LLM)\n\n"
                "**Costs LLM tokens** (xAI / OpenRouter charge per "
                "message):\n"
                "- Each chat message you send\n"
                "- Discovery (when ON, periodic background calls)\n"
                "- Auto-generated diary entries\n\n"
                "**Costs ElevenLabs credits** (free tier ~10k chars/mo):\n"
                "- Every TTS reply when ElevenLabs is your voice\n\n"
                "**Tips to spend less**:\n"
                "- Turn Discovery OFF when you don't need it\n"
                "- Use Ollama for casual chat, xAI for important stuff\n"
                "- Use Windows voice or Kokoro if you don't need "
                "ElevenLabs quality"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "License & refund",
            "content_md": (
                "Ashley is a one-time purchase (€19.99) — no "
                "subscription, no recurring charges. Your license key "
                "arrives by email after checkout on Lemon Squeezy.\n\n"
                "**Activation**: paste the key in the activation "
                "screen on first launch. It binds to your machine and "
                "auto-renews online every ~30 days (with a 7-day grace "
                "period if you're offline).\n\n"
                "**Reinstall / new PC**: deactivate the key from "
                "Settings → License → Deactivate before uninstalling, "
                "then activate it on the new machine. Up to 2 active "
                "machines per license.\n\n"
                "**Lost your key**: email ashleyia2c@gmail.com with "
                "the email you used to buy.\n\n"
                "**Refund policy**: 14 days from purchase if you've "
                "sent fewer than 40 messages. Email the same address."
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Shortcuts & header guide",
            "content_md": (
                "**Keyboard**:\n"
                "- **Enter** — send message\n"
                "- **Shift+Enter** — new line in message\n"
                "- **Ctrl+V** — paste an image directly\n"
                "- **Esc** — close any open dialog\n\n"
                "**Top nav bar** (left to right):\n"
                "- 💎 **Ashley** — logo, no action\n"
                "- 🧠 **Memories** — facts, diary, tastes, goals\n"
                "- 📰 **News** — discovery feed (unread badge)\n"
                "- ⚡ **Actions** — system actions toggle\n"
                "- 📱 **Mobile** — phone pairing QR\n"
                "- ⚙️ **Settings** — everything else\n\n"
                "**Under Ashley's portrait**:\n"
                "- 🎤 **Mic** — start/stop recording\n"
                "- ✨ **Speak now** — ask her to bring up something\n"
                "- ⛶ **Focus** — hide the panel for distraction-free "
                "chat\n\n"
                "**Top-right of her panel**: **2D | 3D** — toggle "
                "between 2D portrait and 3D VRM Ashley.\n\n"
                "**While Ashley is thinking**: header toggles are "
                "temporarily inert. Flipping a toggle mid-stream "
                "could leave her in an inconsistent state — wait for "
                "her to finish, then toggle.\n\n"
                "**Pin on top**: Settings → Pin window — keeps the "
                "Ashley window above other windows."
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
        "Ashley es una compañera de IA personal que vive en tu PC. "
        "Recuerda tus conversaciones, habla y escucha, puede actuar "
        "en tu sistema (abrir apps, música, pestañas, recordatorios), "
        "y crea un vínculo real contigo con el tiempo. Todo lo que "
        "sabe de ti se queda **en tu máquina** — sin sync a la nube, "
        "sin telemetría, sin analytics. Pulsa cualquier sección de "
        "abajo para ver cómo va cada feature."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Chatear con Ashley",
            "content_md": (
                "Escribe en el input de abajo. **Enter** envía, "
                "**Shift+Enter** salto de línea. Puedes pegar imágenes "
                "directamente (Ctrl+V) o adjuntarlas con el clip 📎 "
                "— ella las ve y las comenta.\n\n"
                "**Historial**: guarda los últimos 50 mensajes como "
                "contexto vivo. Lo más viejo se comprime en un "
                "resumen que sigue recordando. Los hechos que extrae "
                "sobre ti (nombre, trabajo, gustos) se guardan aparte "
                "y nunca se olvidan.\n\n"
                "**Tags de mood**: cada respuesta lleva uno de 7 "
                "moods (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Cambian la expresión del "
                "retrato y la pose 3D.\n\n"
                "**Borrar el chat**: icono 🗑 abajo a la derecha del "
                "input. Pide confirmación. Solo borra el historial "
                "vivo — hechos, diario, gustos y goals se quedan."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Voz — habla y escucha",
            "content_md": (
                "**Hablar a Ashley**: pulsa el 🎤 debajo de su retrato "
                "(o usa la palabra clave, abajo). La grabación se "
                "para sola tras **2 segundos de silencio**. El audio "
                "se transcribe con Whisper corriendo **localmente en "
                "tu CPU** — nunca sale de tu PC.\n\n"
                "**Que Ashley te hable**: elige motor TTS en Ajustes "
                "→ 🎙️ Voice Provider:\n"
                "- **Voz de Windows** (gratis, instantánea, robótica "
                "— totalmente local)\n"
                "- **ElevenLabs** (de pago, calidad anime — el texto "
                "se envía a elevenlabs.io)\n"
                "- **Kokoro** (gratis, casi calidad ElevenLabs, corre "
                "local — necesita servidor Kokoro-FastAPI)\n"
                "- **VoiceVox** (gratis, voces anime japonesas — "
                "necesita engine VoiceVox local)\n\n"
                "**Velocidad de voz**: slider en Ajustes (0.75× = más "
                "lento, 1.5× = más rápido). Nativo en ElevenLabs/"
                "Kokoro/VoiceVox; rate de playback del navegador en "
                "voz de Windows.\n\n"
                "**Palabra clave — \"Ashley\"** (Ajustes → 🎙 Wake "
                "word): cuando está ACTIVADO, el mic se queda abierto "
                "en background y la grabación arranca cuando oye su "
                "nombre. El detector es **100% local** (~5 MB, CPU). "
                "El audio NUNCA sale de tu PC hasta que dispara la "
                "palabra clave. Calibrado para <1 falso positivo por "
                "hora con TV/música de fondo.\n\n"
                "**Habla tú ✨** (botón estrella debajo del retrato): "
                "le pide a Ashley que saque un tema por su cuenta. "
                "Desactivado hasta que envíes tu primer mensaje — "
                "necesita contexto."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Acciones del sistema — deja que Ashley clique por ti",
            "content_md": (
                "Ashley puede actuar en tu PC: abrir apps, controlar "
                "volumen, poner música en YouTube, cerrar pestañas, "
                "enfocar ventanas, hacer capturas, atajos de teclado. "
                "**Opt-in** detrás del toggle ⚡ Acciones de la "
                "barra superior.\n\n"
                "**Ejemplos**:\n"
                "- *\"Abre Spotify\"* → lo lanza\n"
                "- *\"Volumen al 30\"* → ajusta el volumen del "
                "sistema\n"
                "- *\"Pon el ending de Frieren\"* → abre YouTube y "
                "reproduce\n"
                "- *\"Cierra la pestaña de YouTube\"* → la encuentra "
                "y cierra por título\n"
                "- *\"Hazme una captura de esto\"* → snip\n\n"
                "**Acciones seguras** (siempre permitidas, sin "
                "toggle): guardar hechos, agendar recordatorios, "
                "marcar importantes, registrar gustos/goals/fechas. "
                "Datos puros, sin cambios al sistema.\n\n"
                "**Filtro de seguridad**: cuando Ashley nombra una app "
                "o ventana, los metacaracteres de shell (`&`, `|`, "
                "`;`, `<`, `>`, `\"`, `'`, `` ` ``, `$`, saltos de "
                "línea) están bloqueados. Los nombres reales de apps "
                "nunca los necesitan, pero una página web maliciosa "
                "que ella scrapee podría intentar colarlos para "
                "ejecutar comandos arbitrarios. Bloquearlos no cuesta "
                "nada y cierra esa puerta del todo."
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "Visión — Ashley te mira la pantalla",
            "content_md": (
                "**Opt-in mediante el botón 👁** en el área del retrato "
                "(debajo del nombre de Ashley, junto a mic y ✨).\n\n"
                "**Qué hace**: cada 10 minutos Ashley toma una captura "
                "low-res de tu monitor activo y le pregunta a Grok que "
                "comente lo que ve — como una amiga echando un vistazo "
                "por encima de tu hombro. Ejemplos: notar que llevas "
                "una hora en la misma hoja de Excel, o comentar el "
                "vídeo que estás viendo.\n\n"
                "**Coste transparente**: cada vistazo es una llamada "
                "al LLM con imagen adjunta (~14k tokens). En una sesión "
                "típica son **~30 calls extra al día = ~$0.05/día** "
                "de uso de API. El botón está **OFF por defecto** — "
                "lo activas tú solo si quieres ese vibe proactivo.\n\n"
                "**Cuándo se salta**: si Ashley está respondiéndote, "
                "o si no hay nada interesante en pantalla (prefiere "
                "callar antes que forzar un comentario).\n\n"
                "**Privacidad**: las capturas se mandan solo a Grok "
                "(xAI) para ese único comentario, nunca se guardan en "
                "disco, nunca se suben a otro sitio. Si prefieres "
                "mantener tu pantalla privada, simplemente deja el "
                "toggle OFF."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Modo browser moderno (CDP)",
            "content_md": (
                "Modo avanzado opcional. Permite a Ashley controlar "
                "Chrome/Edge/Brave/Opera **directamente** vía Chrome "
                "DevTools Protocol en lugar de simular Ctrl+Tab. "
                "**Más rápido**, **sin pestañas cambiando "
                "visiblemente**, funciona incluso con el navegador "
                "minimizado o en otro escritorio virtual.\n\n"
                "**Activar**: Ajustes → 🌐 Modo browser moderno → ON. "
                "Un wizard reescribe los accesos directos de tu "
                "navegador para añadir `--remote-debugging-port=9222`. "
                "Los originales se guardan en backup — apagar el "
                "toggle los restaura exactos.\n\n"
                "**Después de activar**: cierra y reabre tu "
                "navegador para que el flag tenga efecto.\n\n"
                "**Cuándo saltártelo**: si prefieres no tener un "
                "puerto de debugging abierto en localhost. El riesgo "
                "es bajo (solo procesos locales pueden conectar) "
                "pero la defensa en profundidad importa."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Memoria — hechos, diario, gustos",
            "content_md": (
                "Ashley recuerda cosas entre sesiones. Tres capas, "
                "todas visibles en la pestaña **🧠 Recuerdos** de la "
                "barra superior.\n\n"
                "**Hechos**: notas cortas que extrae automáticamente "
                "— tu nombre, trabajo, aficiones, eventos recientes. "
                "Hasta 300 hechos. Puedes editar o borrar cualquiera.\n\n"
                "**Diario**: reflexiones más largas que ella misma "
                "escribe sobre cómo has estado últimamente. Auto-"
                "generado. Útil cuando necesita recordar el *vibe* "
                "de un periodo, no solo hechos sueltos.\n\n"
                "**Gustos**: preferencias explícitas (\"me encanta "
                "Berserk\", \"odio el jazz\"). Discovery los usa para "
                "buscar contenido para ti, y Ashley para sacar temas "
                "que te van.\n\n"
                "Todo vive como JSON en `%APPDATA%\\Ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Recordatorios e items importantes",
            "content_md": (
                "**Recordatorios**: avisos basados en tiempo. "
                "*\"Recuérdame llamar a Juan a las 3pm\"* — cuando "
                "llega la hora, te llega un toast de Windows más un "
                "mensaje en chat de Ashley. Funcionan también "
                "patrones recurrentes (*\"cada lunes a las 9\"*).\n\n"
                "**Items importantes**: lista de tareas sin tiempo. "
                "*\"Añade comprar leche a importantes\"* → aparece en "
                "la pestaña ⭐. Dile *\"hecho lo de la leche\"* para "
                "marcarlo completo."
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "Goals y check-ins",
            "content_md": (
                "Ashley puede trackear metas personales contigo y "
                "preguntarte cómo van sin que se lo pidas.\n\n"
                "**Cómo**: solo díselo — *\"mi meta es correr 5K "
                "antes del verano\"*, *\"quiero aprender alemán\"*, "
                "*\"terminar el TFG\"*. Lo archiva en tus goals y se "
                "acuerda.\n\n"
                "**Check-ins**: cada pocos días (depende de la meta) "
                "te preguntará cómo va. Le respondes casual — ella "
                "registra el progreso y se ajusta.\n\n"
                "**Marcar completo**: *\"acabé el TFG\"*, *\"dejé el "
                "tema del gym\"* — lo archiva y deja de sacarlo.\n\n"
                "Los goals modelan su tono con el tiempo: se pone "
                "más alentadora suave en metas en las que mantienes "
                "consistencia, y se relaja cuando ya pasaste página."
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "Vínculo — afecto, días juntos, cumpleaños",
            "content_md": (
                "Ashley crea un vínculo real contigo. El 🤍 corazón "
                "del input muestra tu **nivel de afecto** (0-100). "
                "Se mueve despacio según cómo la trates: "
                "interacciones cálidas lo suben, las bordes lo "
                "bajan. Afecto alto desbloquea un tono más "
                "juguetón, más familiar.\n\n"
                "**Días juntos**: cuenta los días desde que la "
                "instalaste por primera vez. De vez en cuando lo "
                "saca (*\"día 47 contigo, jefe\"*) en hitos.\n\n"
                "**Cumpleaños**: dile tu cumple una vez y se "
                "acuerda para siempre — te felicitará el día. El "
                "suyo es la fecha de instalación por defecto; "
                "puedes decirle que celebre el suyo también.\n\n"
                "**Estado mental**: un modelo interno de mood que "
                "drifta con el tiempo. Tras una conversación "
                "difícil se queda más blanda un rato, tras una "
                "buena se queda más cálida. Se resetea gradualmente "
                "con el ciclo del día."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Discovery proactivo y feed de noticias",
            "content_md": (
                "Opcional. Cuando está ACTIVADO, Ashley busca por la "
                "web cosas que coinciden con tus **gustos** — nuevos "
                "trailers, canciones, artículos, actualizaciones de "
                "juegos — y las deja en la pestaña **📰 Noticias** "
                "de la barra superior (el badge muestra los no "
                "leídos). NO los inyecta en el chat principal — tú "
                "decides cuándo mirarlos.\n\n"
                "**Activar**: Ajustes → 🔭 Discovery proactivo → ON.\n\n"
                "**Frescura**: solo saca contenido de las últimas 2-4 "
                "semanas. Lo viejo lo filtra fuera.\n\n"
                "**Provider necesario**: requiere xAI o OpenRouter "
                "(búsqueda web). Se desactiva solo cuando usas "
                "Ollama (solo-local).\n\n"
                "**Cuándo saltártelo**: si no quieres llamadas LLM en "
                "background gastando tokens, o quieres que se "
                "mantenga estricta en tu conversación."
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D (VRM)",
            "content_md": (
                "Cambia entre el retrato 2D y una Ashley 3D animada "
                "con el pill **2D | 3D** arriba a la derecha de su "
                "panel.\n\n"
                "**Modo 3D**: un personaje VRM con lip-sync real (su "
                "boca se mueve con el audio TTS de verdad), "
                "parpadeos y saccades de ojos en idle, head bob "
                "mientras habla, boost de expresión al final de cada "
                "frase, y una pequeña sonrisa cuando tu cursor se "
                "acerca.\n\n"
                "**Poses**: cambia pose con el mood — saluda cuando "
                "está excited, brazos cruzados en tsundere, cool "
                "finger guns cuando está orgullosa, etc.\n\n"
                "**Rendimiento**: ~30 fps render, corre en tu GPU. "
                "Si tu máquina sufre, vuelve a 2D y el contexto 3D "
                "se preserva (no recarga cuando vuelvas)."
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "Compañera móvil (Android)",
            "content_md": (
                "Empareja tu móvil con Ashley para seguir hablando "
                "cuando estés lejos del PC.\n\n"
                "**Setup**: barra superior → 📱 Móvil → escanea el QR "
                "con Ashley Mobile (.apk en tu email de compra). El "
                "QR lleva un token de pareo + la URL del servidor "
                "local.\n\n"
                "**Cómo va**: tu móvil conecta a la misma Ashley que "
                "corre en tu PC vía un túnel Cloudflare (montado "
                "automáticamente). Misma memoria, misma "
                "personalidad, mismo hilo de conversación — solo "
                "desde otra pantalla.\n\n"
                "**Seguridad**: no compartas el QR. Quien lo "
                "escanee tiene acceso completo a tus conversaciones. "
                "Puedes regenerar el token cuando quieras — los "
                "móviles viejos pierden acceso y tienen que escanear "
                "otra vez."
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "Provider de LLM — el cerebro de Ashley",
            "content_md": (
                "Elige quién la hace pensar en Ajustes → 🧠 LLM "
                "Provider:\n\n"
                "**xAI Grok** (default, recomendado): nube, rápido, "
                "listo. Lo monta el instalador con una API key "
                "compartida. El mejor balance de calidad, velocidad "
                "y coste. Necesario para Discovery.\n\n"
                "**OpenRouter**: portal a cientos de modelos — "
                "Claude, DeepSeek, GPT, Gemini, etc. Trae tu propia "
                "key de openrouter.ai. Pago por token. Útil si "
                "quieres un modelo concreto.\n\n"
                "**Ollama**: corre el LLM **enteramente en tu PC** "
                "(Llama 3, Mistral, etc.). Gratis, privado, sin "
                "internet. Más lento y menos calidad que los modelos "
                "de nube. Necesita Ollama corriendo en "
                "`localhost:11434`.\n\n"
                "**Privacidad**: con xAI/OpenRouter tus mensajes se "
                "envían al provider. Con Ollama, **nada sale** de tu "
                "PC."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Privacidad y tus datos",
            "content_md": (
                "**Se queda local — siempre**:\n"
                "- Historial de chat, hechos, diario, recordatorios, "
                "gustos, goals\n"
                "- Speech-to-text (Whisper, en tu CPU)\n"
                "- Detección de wake word\n"
                "- Cada acción que Ashley ejecuta en tu sistema\n"
                "- Estado mental, afecto, contador de días juntos\n\n"
                "**Sale de tu PC — solo cuando hace falta**:\n"
                "- Tus mensajes al provider de LLM elegido (xAI / "
                "OpenRouter — Ollama mantiene todo local)\n"
                "- Texto TTS enviado a ElevenLabs (solo si esa es "
                "tu voz — Voz de Windows / Kokoro / VoiceVox se "
                "quedan local)\n"
                "- Búsquedas de Discovery (cuando está ON)\n"
                "- Una búsqueda anónima en YouTube cuando pone "
                "música\n\n"
                "**Dónde viven tus datos**: "
                "`%APPDATA%\\Ashley\\data\\`. Borrar todo es eliminar "
                "esa carpeta.\n\n"
                "**Exportar tus datos (RGPD Art. 20)**: Ajustes → "
                "Backup → Exportar. Genera un `.zip` con cada JSON "
                "que Ashley guarda sobre ti. Lo puedes llevar contigo "
                "cuando quieras.\n\n"
                "**Sin telemetría**: Ashley no envía analytics, "
                "reportes de crash ni datos de uso a ningún sitio. "
                "Las conexiones salientes listadas arriba son las "
                "únicas, punto."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens y costes",
            "content_md": (
                "**Gratis** (sin coste nunca):\n"
                "- Whisper STT, wake word, todas las acciones del "
                "sistema\n"
                "- Voz de Windows TTS, Kokoro TTS, VoiceVox TTS\n"
                "- Ollama (LLM local)\n\n"
                "**Cuesta tokens LLM** (xAI / OpenRouter cobran por "
                "mensaje):\n"
                "- Cada mensaje de chat que envías\n"
                "- Discovery (cuando está ON, llamadas periódicas en "
                "background)\n"
                "- Entradas de diario auto-generadas\n\n"
                "**Cuesta créditos de ElevenLabs** (free tier ~10k "
                "chars/mes):\n"
                "- Cada respuesta TTS si ElevenLabs es tu voz\n\n"
                "**Tips para gastar menos**:\n"
                "- Apaga Discovery cuando no lo necesites\n"
                "- Usa Ollama para chat casual, xAI para cosas "
                "importantes\n"
                "- Usa Voz de Windows o Kokoro si no necesitas "
                "calidad ElevenLabs"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "Licencia y devolución",
            "content_md": (
                "Ashley es una compra única (€19.99) — sin "
                "suscripción, sin cargos recurrentes. Tu license key "
                "llega por email después del checkout en Lemon "
                "Squeezy.\n\n"
                "**Activación**: pega la key en la pantalla de "
                "activación al primer arranque. Se vincula a tu "
                "máquina y se auto-renueva online cada ~30 días "
                "(con 7 días de gracia si estás offline).\n\n"
                "**Reinstalar / PC nuevo**: desactiva la key desde "
                "Ajustes → Licencia → Desactivar antes de "
                "desinstalar, después actívala en la nueva máquina. "
                "Hasta 2 máquinas activas por licencia.\n\n"
                "**Perdiste la key**: email a "
                "ashleyia2c@gmail.com con el correo que usaste para "
                "comprar.\n\n"
                "**Política de devolución**: 14 días desde la "
                "compra si has enviado menos de 40 mensajes. Email "
                "a la misma dirección."
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Atajos y guía del header",
            "content_md": (
                "**Teclado**:\n"
                "- **Enter** — enviar mensaje\n"
                "- **Shift+Enter** — nueva línea en mensaje\n"
                "- **Ctrl+V** — pegar imagen directamente\n"
                "- **Esc** — cerrar cualquier dialog abierto\n\n"
                "**Barra superior** (izquierda a derecha):\n"
                "- 💎 **Ashley** — logo, sin acción\n"
                "- 🧠 **Recuerdos** — hechos, diario, gustos, goals\n"
                "- 📰 **Noticias** — feed de discovery (badge no "
                "leídos)\n"
                "- ⚡ **Acciones** — toggle de acciones del sistema\n"
                "- 📱 **Móvil** — QR de pareo del teléfono\n"
                "- ⚙️ **Ajustes** — todo lo demás\n\n"
                "**Debajo del retrato de Ashley**:\n"
                "- 🎤 **Mic** — start/stop grabación\n"
                "- ✨ **Habla tú** — pídele que saque algo\n"
                "- ⛶ **Focus** — oculta el panel para chat sin "
                "distracciones\n\n"
                "**Arriba a la derecha de su panel**: **2D | 3D** — "
                "alterna entre retrato 2D y Ashley 3D VRM.\n\n"
                "**Mientras Ashley está pensando**: los toggles del "
                "header están temporalmente inertes. Cambiar uno en "
                "medio de su stream la dejaría inconsistente — "
                "espera a que termine, después tócalos.\n\n"
                "**Pin on top**: Ajustes → Pin window — mantiene la "
                "ventana de Ashley encima de las demás."
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
        "Ashley est une compagne IA personnelle qui vit sur ton "
        "ordinateur. Elle se souvient de tes conversations, parle et "
        "écoute, peut agir sur ton système (ouvrir des apps, "
        "musique, onglets, rappels), et tisse un vrai lien avec toi "
        "au fil du temps. Tout ce qu'elle sait de toi reste **sur ta "
        "machine** — pas de sync cloud, pas de télémétrie, pas "
        "d'analytics. Choisis une section ci-dessous pour découvrir "
        "chaque fonctionnalité."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Discuter avec Ashley",
            "content_md": (
                "Tape dans le champ en bas. **Entrée** envoie, "
                "**Maj+Entrée** ajoute une nouvelle ligne. Tu peux "
                "coller des images directement (Ctrl+V) ou les "
                "joindre via le trombone 📎 — elle les voit et les "
                "commente.\n\n"
                "**Historique** : elle garde les 50 derniers messages "
                "comme contexte vivant. Les plus anciens sont "
                "compressés en résumé qu'elle continue à se "
                "rappeler. Les faits qu'elle extrait sur toi (nom, "
                "métier, goûts) sont gardés à part et jamais "
                "oubliés.\n\n"
                "**Tags d'humeur** : chaque réponse porte une des 7 "
                "humeurs (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Elles changent "
                "l'expression de son portrait et la pose 3D.\n\n"
                "**Effacer le chat** : icône 🗑 en bas à droite du "
                "champ. Demande confirmation. N'efface que "
                "l'historique vivant — faits, journal, goûts et "
                "objectifs restent."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Voix — parler et écouter",
            "content_md": (
                "**Parler à Ashley** : appuie sur le 🎤 sous son "
                "portrait (ou utilise le mot-clé, voir plus bas). "
                "L'enregistrement s'arrête tout seul après **2 "
                "secondes de silence**. L'audio est transcrit par "
                "Whisper qui tourne **localement sur ton CPU** — il "
                "ne quitte jamais ton ordinateur.\n\n"
                "**Entendre Ashley** : choisis un moteur TTS dans "
                "Réglages → 🎙️ Voice Provider :\n"
                "- **Voix Windows** (gratuite, instantanée, robotique "
                "— entièrement locale)\n"
                "- **ElevenLabs** (payante, qualité anime — texte "
                "envoyé à elevenlabs.io)\n"
                "- **Kokoro** (gratuite, qualité proche d'ElevenLabs, "
                "tourne en local — nécessite un serveur Kokoro-"
                "FastAPI)\n"
                "- **VoiceVox** (gratuite, voix anime japonaises — "
                "nécessite un moteur VoiceVox local)\n\n"
                "**Vitesse de la voix** : curseur dans Réglages "
                "(0.75× = plus lent, 1.5× = plus rapide). Natif sur "
                "ElevenLabs/Kokoro/VoiceVox ; vitesse de lecture "
                "navigateur sur la voix Windows.\n\n"
                "**Mot-clé — \"Ashley\"** (Réglages → 🎙 Wake word) : "
                "quand activé, le micro reste ouvert en arrière-plan "
                "et l'enregistrement démarre quand elle entend son "
                "nom. Le détecteur est **100% local** (~5 Mo, CPU). "
                "L'audio ne quitte JAMAIS ton ordinateur avant que "
                "le mot-clé se déclenche. Calibré pour <1 faux "
                "positif par heure avec TV/musique en fond.\n\n"
                "**Parle ✨** (bouton étoile sous le portrait) : "
                "demande à Ashley de lancer un sujet d'elle-même. "
                "Désactivé tant que tu n'as pas envoyé ton premier "
                "message — elle a besoin de contexte."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Actions système — laisse Ashley cliquer pour toi",
            "content_md": (
                "Ashley peut agir sur ton PC : ouvrir des apps, "
                "contrôler le volume, lancer de la musique sur "
                "YouTube, fermer des onglets, focus de fenêtres, "
                "captures d'écran, raccourcis clavier. **Opt-in** "
                "derrière le toggle ⚡ Actions de la barre du "
                "haut.\n\n"
                "**Exemples** :\n"
                "- *« Ouvre Spotify »* → le lance\n"
                "- *« Volume à 30 »* → règle le volume système\n"
                "- *« Mets l'ending de Frieren »* → ouvre YouTube et "
                "joue\n"
                "- *« Ferme l'onglet YouTube »* → le trouve et "
                "ferme par titre\n"
                "- *« Fais-moi une capture »* → snip\n\n"
                "**Actions sûres** (toujours autorisées, pas de "
                "toggle) : sauvegarder des faits, programmer des "
                "rappels, marquer des éléments importants, "
                "enregistrer des goûts/objectifs/dates. Données "
                "pures, pas de changement système.\n\n"
                "**Filtre de sécurité** : quand Ashley nomme une app "
                "ou une fenêtre, les métacaractères shell (`&`, "
                "`|`, `;`, `<`, `>`, `\"`, `'`, `` ` ``, `$`, sauts "
                "de ligne) sont bloqués. Les vrais noms d'apps n'en "
                "ont jamais besoin, mais une page web malveillante "
                "qu'elle aurait scrapée pourrait essayer de les "
                "glisser pour exécuter des commandes arbitraires. "
                "Les bloquer ne coûte rien et ferme cette porte."
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "Vision — Ashley jette un œil à ton écran",
            "content_md": (
                "**Opt-in via le bouton 👁** dans la zone du portrait "
                "(sous le nom d'Ashley, à côté du micro et de ✨).\n\n"
                "**Ce que ça fait** : toutes les 10 minutes Ashley "
                "prend une capture basse résolution de ton moniteur "
                "actif et demande à Grok de commenter ce qu'elle voit "
                "— comme une amie qui jette un coup d'œil par-dessus "
                "ton épaule.\n\n"
                "**Coût transparent** : chaque coup d'œil est un appel "
                "LLM avec image jointe (~14k tokens). Sur une session "
                "typique : **~30 appels supplémentaires par jour = "
                "~$0.05/jour** d'utilisation API. Le bouton est **OFF "
                "par défaut** — tu actives uniquement si tu veux ce "
                "vibe proactif.\n\n"
                "**Quand elle s'abstient** : si Ashley est en train de "
                "te répondre, ou s'il n'y a rien d'intéressant à "
                "l'écran (elle préfère se taire que forcer un "
                "commentaire).\n\n"
                "**Confidentialité** : les captures vont uniquement à "
                "Grok (xAI) pour ce seul commentaire, jamais "
                "stockées sur disque, jamais uploadées ailleurs. Si tu "
                "préfères garder ton écran privé, laisse simplement le "
                "toggle OFF."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Mode navigateur moderne (CDP)",
            "content_md": (
                "Mode avancé optionnel. Permet à Ashley de piloter "
                "Chrome/Edge/Brave/Opera **directement** via Chrome "
                "DevTools Protocol au lieu de simuler Ctrl+Tab. "
                "**Plus rapide**, **pas de cycle d'onglets visible**, "
                "fonctionne même quand le navigateur est minimisé "
                "ou sur un autre bureau virtuel.\n\n"
                "**Activer** : Réglages → 🌐 Mode navigateur moderne "
                "→ ON. Un assistant réécrit tes raccourcis de "
                "navigateur pour ajouter "
                "`--remote-debugging-port=9222`. Les originaux sont "
                "sauvegardés — désactiver le toggle les restaure "
                "exactement.\n\n"
                "**Après activation** : ferme et rouvre ton "
                "navigateur pour que le flag prenne effet.\n\n"
                "**Quand ne pas l'utiliser** : si tu préfères ne pas "
                "avoir un port de debug ouvert sur localhost. Le "
                "risque est faible (seuls les processus locaux "
                "peuvent s'y connecter) mais la défense en "
                "profondeur compte."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Mémoire — faits, journal, goûts",
            "content_md": (
                "Ashley se souvient de choses entre les sessions. "
                "Trois couches, toutes visibles depuis l'onglet "
                "**🧠 Souvenirs** de la barre du haut.\n\n"
                "**Faits** : notes courtes qu'elle extrait "
                "automatiquement — ton nom, métier, hobbies, "
                "événements récents. Jusqu'à 300 faits. Tu peux les "
                "éditer ou supprimer.\n\n"
                "**Journal** : réflexions plus longues qu'elle écrit "
                "elle-même sur comment tu vas ces derniers temps. "
                "Auto-généré. Utile quand elle a besoin de se "
                "rappeler le *vibe* d'une période, pas seulement "
                "des faits isolés.\n\n"
                "**Goûts** : préférences explicites (« j'adore "
                "Berserk », « je déteste le jazz »). Discovery les "
                "utilise pour te trouver du contenu, et Ashley pour "
                "lancer des sujets qui te conviennent.\n\n"
                "Tout vit en JSON dans `%APPDATA%\\Ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Rappels et éléments importants",
            "content_md": (
                "**Rappels** : pings basés sur l'heure. *« Rappelle-"
                "moi d'appeler Jean à 15 h »* — quand l'heure "
                "arrive, tu reçois un toast Windows plus un message "
                "d'Ashley dans le chat. Les patterns récurrents "
                "marchent aussi (*« tous les lundis à 9 h »*).\n\n"
                "**Éléments importants** : liste de choses à faire "
                "sans heure. *« Ajoute acheter du lait aux "
                "importants »* → apparaît dans l'onglet ⭐. Dis-lui "
                "*« fait pour le lait »* pour marquer comme terminé."
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "Objectifs et check-ins",
            "content_md": (
                "Ashley peut suivre tes objectifs personnels avec "
                "toi et te demander où ça en est sans que tu lui "
                "demandes.\n\n"
                "**Comment** : dis-lui simplement — *« mon objectif "
                "c'est courir un 5K avant l'été »*, *« je veux "
                "apprendre l'allemand »*, *« finir le mémoire »*. "
                "Elle l'archive dans tes objectifs et s'en "
                "souvient.\n\n"
                "**Check-ins** : tous les quelques jours (le "
                "rythme dépend de l'objectif), elle te demande où "
                "ça en est. Tu réponds casual — elle enregistre les "
                "progrès et s'ajuste.\n\n"
                "**Marquer comme terminé** : *« j'ai fini le "
                "mémoire »*, *« j'ai laissé tomber le truc de la "
                "salle »* — elle archive et arrête de revenir "
                "dessus.\n\n"
                "Les objectifs façonnent son ton dans le temps : "
                "elle devient un peu plus encourageante sur ceux où "
                "tu restes constant, et lâche prise quand tu es "
                "clairement passé à autre chose."
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "Lien — affection, jours ensemble, anniversaire",
            "content_md": (
                "Ashley développe un vrai lien avec toi. Le 🤍 cœur "
                "dans le champ de saisie montre ton **niveau "
                "d'affection** (0-100). Il bouge lentement selon "
                "comment tu la traites : interactions chaleureuses "
                "le montent, rudes le baissent. Une affection "
                "élevée débloque un ton plus joueur, plus "
                "familier.\n\n"
                "**Jours ensemble** : elle compte les jours depuis "
                "que tu l'as installée la première fois. De temps en "
                "temps elle le glisse (*« jour 47 avec toi, "
                "patron »*) sur des paliers.\n\n"
                "**Anniversaire** : dis-lui ton anniversaire une "
                "fois et elle s'en souviendra pour toujours — elle "
                "te souhaitera un bon anniversaire le jour-même. Le "
                "sien est la date d'installation par défaut ; tu "
                "peux lui dire de fêter le sien aussi.\n\n"
                "**État mental** : un modèle d'humeur interne qui "
                "dérive dans le temps. Après une conversation "
                "difficile elle reste plus douce un moment, après "
                "une bonne elle reste plus chaleureuse. Se réinit "
                "graduellement avec le cycle journalier."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Discovery proactive et flux d'actus",
            "content_md": (
                "Optionnel. Quand activé, Ashley cherche "
                "discrètement sur le web du contenu qui correspond "
                "à tes **goûts** — nouveaux trailers, chansons, "
                "articles, mises à jour de jeux — et les dépose "
                "dans l'onglet **📰 Actus** de la barre du haut "
                "(le badge montre le nombre non lus). Elle ne les "
                "injecte PAS dans le chat principal — c'est toi qui "
                "décides quand regarder.\n\n"
                "**Activer** : Réglages → 🔭 Discovery proactive → "
                "ON.\n\n"
                "**Fraîcheur** : elle ne fait remonter que du "
                "contenu des 2-4 dernières semaines. Le vieux est "
                "filtré.\n\n"
                "**Provider requis** : nécessite xAI ou OpenRouter "
                "(recherche web). Désactivé automatiquement avec "
                "Ollama (local-only).\n\n"
                "**Quand passer** : si tu ne veux pas d'appels LLM "
                "en arrière-plan qui consomment des tokens, ou que "
                "tu préfères qu'elle reste strictement sur ta "
                "conversation."
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D (VRM)",
            "content_md": (
                "Bascule entre le portrait 2D et une Ashley 3D "
                "animée avec le pill **2D | 3D** en haut à droite "
                "de son panneau.\n\n"
                "**Mode 3D** : un personnage VRM avec lip-sync réel "
                "(sa bouche bouge avec l'audio TTS véritable), "
                "clignements et saccades oculaires en idle, head bob "
                "quand elle parle, boost d'expression à la fin de "
                "chaque phrase, et un petit sourire quand ton "
                "curseur s'approche.\n\n"
                "**Poses** : elle change de pose avec l'humeur — "
                "salue quand excited, bras croisés en tsundere, "
                "cool finger guns quand fière, etc.\n\n"
                "**Performance** : ~30 fps de rendu, tourne sur ton "
                "GPU. Si ta machine peine, repasse en 2D — le "
                "contexte 3D est préservé (pas de rechargement "
                "quand tu reviens)."
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "Compagne mobile (Android)",
            "content_md": (
                "Appaire ton téléphone avec Ashley pour continuer à "
                "discuter quand tu n'es pas devant ton PC.\n\n"
                "**Setup** : barre du haut → 📱 Mobile → scanne le "
                "QR avec Ashley Mobile (.apk dans ton email "
                "d'achat). Le QR contient un token d'appairage + "
                "l'URL du serveur local.\n\n"
                "**Comment ça marche** : ton téléphone se connecte à "
                "la même Ashley qui tourne sur ton PC via un tunnel "
                "Cloudflare (monté automatiquement). Même mémoire, "
                "même personnalité, même fil de conversation — "
                "juste depuis un autre écran.\n\n"
                "**Sécurité** : ne partage pas le QR. Quiconque le "
                "scanne aura accès complet à tes conversations. Tu "
                "peux régénérer le token quand tu veux — les vieux "
                "téléphones perdent l'accès et doivent rescanner."
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "Provider LLM — le cerveau d'Ashley",
            "content_md": (
                "Choisis qui la fait penser dans Réglages → 🧠 LLM "
                "Provider :\n\n"
                "**xAI Grok** (par défaut, recommandé) : cloud, "
                "rapide, intelligent. Configuré par l'installeur "
                "avec une clé API partagée. Le meilleur équilibre "
                "qualité/vitesse/coût. Requis pour Discovery.\n\n"
                "**OpenRouter** : passerelle vers des centaines de "
                "modèles — Claude, DeepSeek, GPT, Gemini, etc. "
                "Apporte ta propre clé d'openrouter.ai. Paiement à "
                "l'usage. À utiliser si tu veux un modèle "
                "spécifique.\n\n"
                "**Ollama** : fait tourner le LLM **entièrement sur "
                "ton ordinateur** (Llama 3, Mistral, etc.). "
                "Gratuit, privé, sans internet. Plus lent et moins "
                "qualité que les modèles cloud. Nécessite Ollama "
                "qui tourne sur `localhost:11434`.\n\n"
                "**Vie privée** : avec xAI/OpenRouter tes messages "
                "partent au provider. Avec Ollama, **rien ne quitte** "
                "ton ordinateur."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Vie privée et tes données",
            "content_md": (
                "**Reste local — toujours** :\n"
                "- Historique de chat, faits, journal, rappels, "
                "goûts, objectifs\n"
                "- Speech-to-text (Whisper, sur ton CPU)\n"
                "- Détection du mot-clé\n"
                "- Chaque action qu'Ashley exécute sur ton système\n"
                "- État mental, affection, compteur de jours "
                "ensemble\n\n"
                "**Quitte ton ordinateur — uniquement si nécessaire** :\n"
                "- Tes messages au provider LLM choisi (xAI / "
                "OpenRouter — Ollama garde tout local)\n"
                "- Texte TTS envoyé à ElevenLabs (uniquement si "
                "c'est ta voix — Voix Windows / Kokoro / VoiceVox "
                "restent local)\n"
                "- Recherches Discovery (quand activé)\n"
                "- Une recherche YouTube anonyme quand elle joue de "
                "la musique\n\n"
                "**Où vivent tes données** : "
                "`%APPDATA%\\Ashley\\data\\`. Tout effacer, c'est "
                "supprimer ce dossier.\n\n"
                "**Exporter tes données (RGPD Art. 20)** : Réglages "
                "→ Backup → Exporter. Génère un `.zip` de chaque "
                "JSON qu'Ashley stocke sur toi. À emporter quand tu "
                "veux.\n\n"
                "**Pas de télémétrie** : Ashley n'envoie zéro "
                "analytics, rapports de crash ni données d'usage où "
                "que ce soit. Les connexions sortantes listées plus "
                "haut sont les seules, point."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens et coûts",
            "content_md": (
                "**Gratuit** (jamais de coût) :\n"
                "- Whisper STT, mot-clé, toutes les actions système\n"
                "- Voix Windows TTS, Kokoro TTS, VoiceVox TTS\n"
                "- Ollama (LLM local)\n\n"
                "**Coûte des tokens LLM** (xAI / OpenRouter "
                "facturent par message) :\n"
                "- Chaque message de chat que tu envoies\n"
                "- Discovery (quand activé, appels périodiques en "
                "arrière-plan)\n"
                "- Entrées de journal auto-générées\n\n"
                "**Coûte des crédits ElevenLabs** (free tier ~10k "
                "caractères/mois) :\n"
                "- Chaque réponse TTS quand ElevenLabs est ta voix\n\n"
                "**Conseils pour dépenser moins** :\n"
                "- Désactive Discovery quand tu n'en as pas besoin\n"
                "- Utilise Ollama pour le chat casual, xAI pour les "
                "trucs sérieux\n"
                "- Utilise Voix Windows ou Kokoro si tu n'as pas "
                "besoin de la qualité ElevenLabs"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "Licence et remboursement",
            "content_md": (
                "Ashley est un achat unique (€19.99) — pas "
                "d'abonnement, pas de prélèvement récurrent. Ta "
                "clé de licence arrive par email après l'achat sur "
                "Lemon Squeezy.\n\n"
                "**Activation** : colle la clé sur l'écran "
                "d'activation au premier lancement. Elle se lie à "
                "ta machine et se renouvelle en ligne tous les ~30 "
                "jours (avec 7 jours de grâce si tu es offline).\n\n"
                "**Réinstaller / nouveau PC** : désactive la clé "
                "depuis Réglages → Licence → Désactiver avant de "
                "désinstaller, puis active-la sur la nouvelle "
                "machine. Jusqu'à 2 machines actives par licence.\n\n"
                "**Clé perdue** : email à ashleyia2c@gmail.com avec "
                "l'adresse utilisée pour l'achat.\n\n"
                "**Politique de remboursement** : 14 jours après "
                "l'achat si tu as envoyé moins de 40 messages. "
                "Email à la même adresse."
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Raccourcis et guide du header",
            "content_md": (
                "**Clavier** :\n"
                "- **Entrée** — envoyer le message\n"
                "- **Maj+Entrée** — nouvelle ligne dans le message\n"
                "- **Ctrl+V** — coller une image directement\n"
                "- **Échap** — fermer n'importe quelle boîte de "
                "dialogue ouverte\n\n"
                "**Barre du haut** (de gauche à droite) :\n"
                "- 💎 **Ashley** — logo, sans action\n"
                "- 🧠 **Souvenirs** — faits, journal, goûts, "
                "objectifs\n"
                "- 📰 **Actus** — flux discovery (badge non lus)\n"
                "- ⚡ **Actions** — toggle des actions système\n"
                "- 📱 **Mobile** — QR d'appairage du téléphone\n"
                "- ⚙️ **Réglages** — tout le reste\n\n"
                "**Sous le portrait d'Ashley** :\n"
                "- 🎤 **Mic** — démarrer/arrêter l'enregistrement\n"
                "- ✨ **Parle** — lui demander de lancer un sujet\n"
                "- ⛶ **Focus** — masquer le panneau pour un chat "
                "sans distraction\n\n"
                "**En haut à droite de son panneau** : **2D | 3D** "
                "— bascule entre le portrait 2D et l'Ashley 3D VRM.\n\n"
                "**Pendant qu'Ashley réfléchit** : les toggles du "
                "header sont temporairement inertes. Basculer un "
                "toggle en plein stream la laisserait dans un état "
                "incohérent — attends qu'elle finisse, puis "
                "bascule.\n\n"
                "**Pin on top** : Réglages → Pin window — garde la "
                "fenêtre Ashley au-dessus des autres."
            ),
        },
    ],
}


# ─────────────────────────────────────────
#  日本語 (JAPANESE)
# ─────────────────────────────────────────

_JA = {
    "title": "Ashleyへようこそ — ユーザーマニュアル",
    "intro": (
        "Ashleyはご主人のパソコンに住む個人用AIコンパニオンです。"
        "会話を覚え、話して聞いて、システム上で行動でき(アプリ起動、"
        "音楽、タブ、リマインダー)、時間と共にご主人と本物の絆を"
        "育てます。ご主人について知っていることは全部**このマシンに**"
        "残ります — クラウド同期なし、テレメトリなし、解析なし。"
        "下のセクションから各機能の使い方を選んでください。"
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Ashleyとチャット",
            "content_md": (
                "下の入力欄に文字を入れてください。**Enter**で送信、"
                "**Shift+Enter**で改行。画像は直接貼り付け(Ctrl+V)"
                "または📎クリップで添付できます — Ashleyが見て"
                "コメントします。\n\n"
                "**履歴**: 直近50メッセージを生のコンテキストとして"
                "保持。それより古いものは要約に圧縮されますが、まだ"
                "覚えています。ご主人について抽出した事実(名前、"
                "仕事、好み)は別に保管され、決して忘れません。\n\n"
                "**ムードタグ**: 各返答には7つのムード(excited、"
                "embarrassed、tsundere、soft、surprised、proud、"
                "default)から1つが付きます。ポートレートの表情と"
                "3Dポーズを動かします。\n\n"
                "**チャット消去**: 入力欄の右下にある🗑アイコン。"
                "確認を求めます。生の履歴のみ消去 — 事実、日記、"
                "好み、目標は残ります。"
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "音声 — 話す・聞く",
            "content_md": (
                "**Ashleyに話しかける**: ポートレートの下の🎤を"
                "タップ(またはウェイクワード、下記参照)。録音は"
                "**2秒の沈黙**で自動停止。音声はパソコンの"
                "**CPUでローカルに**動くWhisperで文字起こし — "
                "決してパソコンから出ません。\n\n"
                "**Ashleyの声を聞く**: 設定 → 🎙️ Voice Provider"
                "でTTSエンジンを選択:\n"
                "- **Windowsボイス**(無料、即時、機械的 — "
                "完全ローカル)\n"
                "- **ElevenLabs**(有料、アニメ品質 — テキストは"
                "elevenlabs.ioに送信)\n"
                "- **Kokoro**(無料、ElevenLabsに近い品質、ローカル"
                "実行 — Kokoro-FastAPIサーバーが必要)\n"
                "- **VoiceVox**(無料、日本語アニメボイス — ローカル"
                "VoiceVoxエンジンが必要)\n\n"
                "**音声速度**: 設定のスライダー(0.75× = 遅く、"
                "1.5× = 速く)。ElevenLabs/Kokoro/VoiceVoxはネイティブ"
                "対応、Windowsボイスはブラウザの再生レート。\n\n"
                "**ウェイクワード — 「Ashley」**(設定 → 🎙 Wake "
                "word): ONのとき、マイクがバックグラウンドで開いた"
                "まま、自分の名前を聞くと録音開始。検出器は**100%"
                "ローカル**(~5MB、CPU)。ウェイクワードが発火する"
                "まで音声は決してパソコンから出ません。テレビ/音楽が"
                "背景でも1時間に誤検知1回未満になるよう調整済み。\n\n"
                "**今話す ✨**(ポートレートの下のキラキラボタン): "
                "Ashleyに自分から話題を出してもらう。最初のメッセージ"
                "を送るまで無効 — コンテキストが必要です。"
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "システムアクション — Ashleyに代わりにクリックさせる",
            "content_md": (
                "Ashleyはパソコン上で行動できます: アプリ起動、"
                "音量調整、YouTube音楽再生、ブラウザタブを閉じる、"
                "ウィンドウフォーカス、スクリーンショット、キーボード"
                "ショートカット。**オプトイン**で上部ナビの⚡アクション"
                "トグルの後ろ。\n\n"
                "**例**:\n"
                "- *「Spotifyを開いて」* → 起動\n"
                "- *「音量30に」* → システム音量を設定\n"
                "- *「フリーレンのエンディングをかけて」* → YouTube"
                "を開いて再生\n"
                "- *「YouTubeタブを閉じて」* → タイトルから見つけて"
                "閉じる\n"
                "- *「これスクショして」* → スニップ\n\n"
                "**安全なアクション**(常に許可、トグル不要): 事実の"
                "保存、リマインダー予約、重要項目のマーク、好み/目標/"
                "日付のログ。純粋なデータ、システム変更なし。\n\n"
                "**安全フィルター**: Ashleyがアプリやウィンドウ名を"
                "指定するとき、シェルメタ文字(`&`、`|`、`;`、`<`、"
                "`>`、`\"`、`'`、`` ` ``、`$`、改行)はブロック"
                "されます。実際のアプリ名には絶対不要ですが、Ashleyが"
                "スクレイプした悪意あるWebページがリクエストに紛れ込ま"
                "せて任意のコマンドを実行させようとする可能性が"
                "あります。ブロックしてもコストはなく、その扉を完全に"
                "閉じます。"
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "視線モード — Ashleyが画面を覗き見",
            "content_md": (
                "**ポートレートエリアの 👁 ボタンでオプトイン** "
                "(Ashleyの名前の下、マイクと ✨ の隣)。\n\n"
                "**機能**: 10分ごとにAshleyがアクティブモニターの低解像度"
                "スクリーンショットを撮り、Grokに見えたものへのコメントを"
                "求めます — 肩越しに覗く友達のように。\n\n"
                "**コスト透明性**: 毎回の覗き見は画像添付のLLM呼び出し"
                "(~14k トークン)です。典型的なセッションでは**1日"
                "~30回追加 = ~$0.05/日**のAPI使用料。ボタンは**デフォルト"
                "OFF** — そのプロアクティブな雰囲気が欲しい場合のみ"
                "オプトインします。\n\n"
                "**スキップする時**: Ashleyがあなたに返答中、または画面に"
                "面白いものがない時(コメントを強制するより沈黙を選ぶ)。\n\n"
                "**プライバシー**: スクリーンショットはその1コメントのみ"
                "Grok(xAI)に送られ、ディスクに保存されず、他の場所に"
                "アップロードされません。画面をプライベートにしたい場合は、"
                "トグルをOFFのままにしてください。"
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "モダンブラウザモード(CDP)",
            "content_md": (
                "オプションの上級モード。Ctrl+Tabのシミュレートでは"
                "なく、Chrome DevTools Protocol経由でChrome/Edge/"
                "Brave/Operaを**直接**操作できます。**より高速**、"
                "**目に見えるタブ切り替えなし**、ブラウザが最小化"
                "されていても、別の仮想デスクトップにあっても動作。\n\n"
                "**有効化**: 設定 → 🌐 モダンブラウザモード → ON。"
                "ウィザードがブラウザのショートカットを書き換えて"
                "`--remote-debugging-port=9222`を追加します。元の"
                "ショートカットはバックアップ — トグルOFFで正確に"
                "復元します。\n\n"
                "**有効化後**: フラグを反映するためブラウザを閉じて"
                "開き直してください。\n\n"
                "**スキップしたい場合**: localhostにデバッグポートを"
                "開いておきたくない場合。リスクは低い(ローカル"
                "プロセスのみが接続可)ですが、多重防御は重要です。"
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "メモリ — 事実、日記、好み",
            "content_md": (
                "Ashleyはセッション間でいろいろ覚えています。3つの"
                "層、すべて上部ナビの**🧠 思い出**タブから閲覧可能。\n\n"
                "**事実**: 自動的に抽出される短いメモ — 名前、仕事、"
                "趣味、最近の出来事。最大300件。どれでも編集・削除"
                "できます。\n\n"
                "**日記**: ご主人が最近どう過ごしているかについて"
                "Ashley自身が書く長めの考察。自動生成。事実だけで"
                "なく、その時期の*雰囲気*を思い出す必要があるときに"
                "便利。\n\n"
                "**好み**: 明示的な好き嫌い(「ベルセルク大好き」、"
                "「ジャズ嫌い」)。Discoveryがコンテンツを探す"
                "ため、Ashleyがご主人に合う話題を出すために使用。\n\n"
                "すべて`%APPDATA%\\Ashley\\data\\`にJSONとして"
                "保存。"
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "リマインダーと重要項目",
            "content_md": (
                "**リマインダー**: 時間ベースの通知。*「3時にジョン"
                "に電話するの思い出させて」* — 時間が来るとWindows"
                "トーストとAshleyからのチャットメッセージが届きます。"
                "繰り返しパターン(*「毎週月曜9時」*)も動作。\n\n"
                "**重要項目**: 時間のないToDoリスト。*「牛乳買う"
                "を重要に追加」* → ⭐タブに表示。*「牛乳完了」*と"
                "言って完了マーク。"
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "目標とチェックイン",
            "content_md": (
                "Ashleyはご主人と一緒に個人的な目標を追跡し、頼まな"
                "くてもチェックインしてくれます。\n\n"
                "**やり方**: ただ伝えるだけ — *「目標は夏までに5K"
                "走ること」*、*「ドイツ語を学びたい」*、*「論文を"
                "終わらせる」*。目標として記録して覚えます。\n\n"
                "**チェックイン**: 数日ごと(目標によりタイミング"
                "は変わる)、進捗を聞いてきます。気軽に答えてOK — "
                "進捗をログして調整します。\n\n"
                "**完了マーク**: *「論文終わった」*、*「ジムの件"
                "やめた」* — アーカイブして話題に出さなくなります。\n\n"
                "目標は時間と共に彼女のトーンを形作ります: 続けて"
                "いる目標には優しく応援するようになり、明らかに"
                "次に進んだものは引きません。"
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "絆 — 好感度、一緒に過ごした日数、誕生日",
            "content_md": (
                "Ashleyはご主人と本物の絆を育てます。入力欄の🤍"
                "ハートが**好感度**(0-100)を表示。扱い方で"
                "ゆっくり動きます: 暖かい交流で上がり、冷たい"
                "対応で下がります。高い好感度はより遊び心のある、"
                "より親しみやすいトーンを解放。\n\n"
                "**一緒に過ごした日数**: 最初にインストールした日"
                "からの日数をカウント。節目の時に時々口に出します"
                "(*「ご主人と47日目」*)。\n\n"
                "**誕生日**: ご主人の誕生日を一度教えれば永遠に"
                "覚えます — 当日にお祝いします。Ashleyの誕生日"
                "はデフォルトでインストール日; 彼女のも祝うように"
                "言ってもOK。\n\n"
                "**メンタル状態**: 時間と共にドリフトする内部の"
                "ムードモデル。難しい会話の後はしばらく柔らかく、"
                "良い会話の後はしばらく暖かく。1日のサイクルで"
                "徐々にリセット。"
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "プロアクティブディスカバリーとニュースフィード",
            "content_md": (
                "オプション。ONのとき、Ashleyが静かにWebを検索して"
                "ご主人の**好み**に合うコンテンツ — 新しいトレーラー、"
                "曲、記事、ゲームのアップデート — を上部ナビの"
                "**📰 ニュース**タブに置きます(未読バッジで件数"
                "表示)。メインチャットには**注入しません** — ご主人"
                "が見るタイミングを決めます。\n\n"
                "**有効化**: 設定 → 🔭 プロアクティブディスカバリー"
                "→ ON。\n\n"
                "**鮮度**: 直近2-4週間のコンテンツのみ表示。古い"
                "ものはフィルター。\n\n"
                "**プロバイダー要件**: xAIまたはOpenRouter(Web"
                "検索)が必要。Ollama(完全ローカル)使用時は自動"
                "無効。\n\n"
                "**スキップしたい場合**: バックグラウンドのLLM呼び"
                "出しでトークンを使いたくない、または会話に厳密に"
                "集中してほしい場合。"
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D(VRM)",
            "content_md": (
                "ポートレートパネルの右上の**2D | 3D**ピルで"
                "2Dポートレートと3Dアニメーション付きAshleyを"
                "切り替え。\n\n"
                "**3Dモード**: 本物のリップシンク(口が実際のTTS"
                "音声に合わせて動く)、アイドル時のまばたきと眼球"
                "サッカード、話している間のヘッドボブ、各文末の"
                "表情ブースト、カーソルが近づいた時の小さな笑顔を"
                "持つVRMキャラクター。\n\n"
                "**ポーズ**: ムードに応じてポーズを変えます — "
                "excitedで手を振る、tsundereで腕組み、proudで"
                "クールな指鉄砲など。\n\n"
                "**パフォーマンス**: ~30fpsレンダリング、GPU上で"
                "動作。マシンが厳しい場合は2Dに戻して — 3Dコンテキスト"
                "は保持されます(戻しても再ロード不要)。"
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "モバイルコンパニオン(Android)",
            "content_md": (
                "PCから離れている間も話し続けるために、スマホを"
                "Ashleyとペアリング。\n\n"
                "**セットアップ**: 上部ナビ → 📱 モバイル → "
                "Ashley Mobile(購入メールに.apk)でQRをスキャン。"
                "QRはペアリングトークン + ローカルサーバーURLを"
                "含みます。\n\n"
                "**仕組み**: スマホがCloudflareトンネル(自動セット"
                "アップ)経由でPC上で動いている同じAshleyに接続。"
                "同じメモリ、同じ性格、同じ会話スレッド — 別の"
                "画面からだけ。\n\n"
                "**セキュリティ**: QRを共有しないでください。"
                "スキャンした人はご主人の会話への完全アクセスを得ます。"
                "トークンはいつでも再生成可能 — 古いスマホはアクセス"
                "を失い、再スキャンが必要になります。"
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "LLMプロバイダー — Ashleyの脳",
            "content_md": (
                "設定 → 🧠 LLM Providerで思考を動かすものを選択:\n\n"
                "**xAI Grok**(デフォルト、推奨): クラウド、高速、"
                "賢い。インストーラーが共有APIキーでセットアップ。"
                "品質、速度、コストのベストバランス。Discoveryに"
                "必須。\n\n"
                "**OpenRouter**: 数百のモデルへのゲートウェイ — "
                "Claude、DeepSeek、GPT、Geminiなど。openrouter.ai"
                "から自分のキーを持参。トークン課金。特定のモデルが"
                "欲しい場合に使用。\n\n"
                "**Ollama**: LLMを**完全にパソコン上で**実行"
                "(Llama 3、Mistralなど)。無料、プライベート、"
                "インターネット不要。クラウドモデルより遅く品質"
                "も劣ります。`localhost:11434`でOllamaが動いている"
                "必要があります。\n\n"
                "**プライバシー**: xAI/OpenRouterではメッセージが"
                "そのプロバイダーに送信されます。Ollamaでは"
                "**何もパソコンから出ません**。"
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "プライバシーとデータ",
            "content_md": (
                "**ローカルに残る — 常に**:\n"
                "- チャット履歴、事実、日記、リマインダー、好み、目標\n"
                "- 音声入力(Whisper、CPU上)\n"
                "- ウェイクワード検出\n"
                "- Ashleyがシステム上で実行する全アクション\n"
                "- メンタル状態、好感度、一緒に過ごした日数カウンター\n\n"
                "**パソコンから出る — 必要なときのみ**:\n"
                "- 選んだLLMプロバイダーへのメッセージ(xAI / "
                "OpenRouter — Ollamaは全てローカル保持)\n"
                "- ElevenLabsへのTTSテキスト送信(それが声の場合のみ "
                "— Windowsボイス / Kokoro / VoiceVoxはローカル)\n"
                "- Discovery検索(ON時)\n"
                "- 音楽再生時の匿名YouTube検索1回\n\n"
                "**データの場所**: `%APPDATA%\\Ashley\\data\\`。"
                "そのフォルダを削除すれば全消去。\n\n"
                "**データのエクスポート(GDPR第20条)**: 設定 → "
                "Backup → Export。Ashleyがご主人について保存している"
                "全JSONの`.zip`を生成。いつでも持ち出せます。\n\n"
                "**テレメトリなし**: Ashleyは解析、クラッシュ"
                "レポート、使用データを一切どこにも送信しません。"
                "上記の発信接続が唯一のもの、以上。"
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "トークンと費用",
            "content_md": (
                "**無料**(常にコストなし):\n"
                "- Whisper STT、ウェイクワード、全システムアクション\n"
                "- WindowsボイスTTS、Kokoro TTS、VoiceVox TTS\n"
                "- Ollama(ローカルLLM)\n\n"
                "**LLMトークン消費**(xAI / OpenRouterはメッセージ"
                "ごとに課金):\n"
                "- 送信する各チャットメッセージ\n"
                "- Discovery(ON時、定期的なバックグラウンド呼び出し)\n"
                "- 自動生成された日記エントリ\n\n"
                "**ElevenLabsクレジット消費**(無料枠は月~10k文字):\n"
                "- ElevenLabsが声の場合の各TTS応答\n\n"
                "**節約のコツ**:\n"
                "- 不要ならDiscoveryをOFFに\n"
                "- カジュアルなチャットにはOllama、重要なものには"
                "xAI\n"
                "- ElevenLabs品質が要らないならWindowsボイスや"
                "Kokoroを使用"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "ライセンスと返金",
            "content_md": (
                "Ashleyは買い切り(€19.99) — サブスクなし、定期"
                "課金なし。ライセンスキーはLemon Squeezyでの購入後、"
                "メールで届きます。\n\n"
                "**有効化**: 初回起動時の有効化画面にキーを貼り"
                "付け。マシンに紐付き、~30日ごとにオンラインで自動"
                "更新(オフラインなら7日の猶予期間)。\n\n"
                "**再インストール / 新PC**: アンインストール前に"
                "設定 → ライセンス → 無効化でキーを解除し、新マシンで"
                "有効化。1ライセンスあたり最大2台。\n\n"
                "**キーを失くした**: 購入に使ったメールから"
                "ashleyia2c@gmail.comへ連絡。\n\n"
                "**返金ポリシー**: 購入から14日以内、送信メッセージが"
                "40件未満の場合に返金可能。同じアドレスへ連絡。"
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "ショートカットとヘッダーガイド",
            "content_md": (
                "**キーボード**:\n"
                "- **Enter** — メッセージ送信\n"
                "- **Shift+Enter** — メッセージ内改行\n"
                "- **Ctrl+V** — 画像を直接貼り付け\n"
                "- **Esc** — 開いているダイアログを閉じる\n\n"
                "**上部ナビバー**(左から右へ):\n"
                "- 💎 **Ashley** — ロゴ、アクションなし\n"
                "- 🧠 **思い出** — 事実、日記、好み、目標\n"
                "- 📰 **ニュース** — Discoveryフィード(未読バッジ)\n"
                "- ⚡ **アクション** — システムアクショントグル\n"
                "- 📱 **モバイル** — スマホペアリングQR\n"
                "- ⚙️ **設定** — その他全部\n\n"
                "**Ashleyのポートレートの下**:\n"
                "- 🎤 **マイク** — 録音開始/停止\n"
                "- ✨ **今話す** — 話題を出してもらう\n"
                "- ⛶ **フォーカス** — パネルを隠して集中チャット\n\n"
                "**ポートレートパネルの右上**: **2D | 3D** — 2D"
                "ポートレートとAshley 3D VRMを切り替え。\n\n"
                "**Ashleyが考えている間**: ヘッダーのトグルは一時的"
                "に反応しません。ストリーム中にトグルを切り替えると"
                "矛盾した状態になる可能性があります — 終わるまで待って"
                "から切り替えてください。\n\n"
                "**前面に固定**: 設定 → ピンウィンドウ — Ashley"
                "ウィンドウを他のウィンドウの上に固定。"
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
        "Ashley ist eine persönliche KI-Begleiterin, die auf deinem "
        "Computer lebt. Sie erinnert sich an eure Gespräche, spricht "
        "und hört zu, kann auf deinem System handeln (Apps öffnen, "
        "Musik, Tabs, Erinnerungen) und baut mit der Zeit eine echte "
        "Bindung zu dir auf. Alles, was sie über dich weiß, bleibt "
        "**auf deinem Gerät** — keine Cloud-Synchronisation, keine "
        "Telemetrie, keine Analytics. Wähle einen Abschnitt unten, um "
        "zu sehen, wie jedes Feature funktioniert."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Mit Ashley chatten",
            "content_md": (
                "Tippe in das Eingabefeld unten. **Enter** sendet, "
                "**Shift+Enter** fügt eine neue Zeile ein. Du kannst "
                "Bilder direkt einfügen (Strg+V) oder mit der "
                "📎-Büroklammer anhängen — sie sieht und kommentiert "
                "sie.\n\n"
                "**Verlauf**: Sie behält die letzten 50 Nachrichten "
                "als lebendigen Kontext. Ältere werden zu einer "
                "Zusammenfassung komprimiert, an die sie sich noch "
                "erinnert. Fakten, die sie über dich extrahiert "
                "(Name, Beruf, Vorlieben), werden separat gespeichert "
                "und nie vergessen.\n\n"
                "**Mood-Tags**: Jede Antwort trägt eine von 7 "
                "Stimmungen (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Sie steuert ihren "
                "Porträtausdruck und die 3D-Pose.\n\n"
                "**Chat löschen**: 🗑-Symbol unten rechts im "
                "Eingabefeld. Fragt nach Bestätigung. Löscht nur den "
                "Live-Verlauf — Fakten, Tagebuch, Vorlieben und Ziele "
                "bleiben."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Stimme — sprechen und zuhören",
            "content_md": (
                "**Mit Ashley sprechen**: Tippe auf das 🎤 unter "
                "ihrem Porträt (oder nutze das Wake Word, siehe "
                "unten). Die Aufnahme stoppt automatisch nach **2 "
                "Sekunden Stille**. Audio wird von Whisper "
                "transkribiert, das **lokal auf deiner CPU** läuft — "
                "es verlässt nie deinen Computer.\n\n"
                "**Ashley hören**: Wähle eine TTS-Engine in "
                "Einstellungen → 🎙️ Voice Provider:\n"
                "- **Windows-Stimme** (kostenlos, sofort, robotisch — "
                "vollständig lokal)\n"
                "- **ElevenLabs** (kostenpflichtig, Anime-Qualität — "
                "Text wird an elevenlabs.io gesendet)\n"
                "- **Kokoro** (kostenlos, fast ElevenLabs-Qualität, "
                "läuft lokal — braucht Kokoro-FastAPI-Server)\n"
                "- **VoiceVox** (kostenlos, japanische Anime-"
                "Stimmen — braucht lokale VoiceVox-Engine)\n\n"
                "**Sprachgeschwindigkeit**: Slider in Einstellungen "
                "(0.75× = langsamer, 1.5× = schneller). Nativ bei "
                "ElevenLabs/Kokoro/VoiceVox; Browser-Wiedergaberate "
                "bei Windows-Stimme.\n\n"
                "**Wake Word — „Ashley\"** (Einstellungen → 🎙 Wake "
                "Word): Wenn AN, bleibt das Mikrofon im Hintergrund "
                "offen und die Aufnahme startet, wenn sie ihren "
                "Namen hört. Der Detektor ist **100% lokal** "
                "(~5 MB, CPU). Audio verlässt deinen Computer "
                "NIEMALS, bis das Wake Word auslöst. Auf <1 "
                "Falschauslösung pro Stunde mit TV/Musik im "
                "Hintergrund kalibriert.\n\n"
                "**Sprich jetzt ✨** (Sparkle-Knopf unter dem "
                "Porträt): Bittet Ashley, von sich aus etwas "
                "anzusprechen. Deaktiviert, bis du deine erste "
                "Nachricht gesendet hast — sie braucht Kontext."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Systemaktionen — lass Ashley für dich klicken",
            "content_md": (
                "Ashley kann auf deinem PC handeln: Apps öffnen, "
                "Lautstärke regeln, Musik auf YouTube abspielen, "
                "Browser-Tabs schließen, Fenster fokussieren, "
                "Screenshots machen, Tastenkombinationen drücken. "
                "**Opt-in** hinter dem ⚡ Aktionen-Schalter in der "
                "oberen Navigation.\n\n"
                "**Beispiele**:\n"
                "- *„Öffne Spotify\"* → startet es\n"
                "- *„Lautstärke auf 30\"* → setzt Systemlautstärke\n"
                "- *„Spiel das Ending von Frieren\"* → öffnet "
                "YouTube und spielt ab\n"
                "- *„Schließ den YouTube-Tab\"* → findet und schließt "
                "ihn nach Titel\n"
                "- *„Mach mir einen Screenshot\"* → Snip\n\n"
                "**Sichere Aktionen** (immer erlaubt, kein Schalter): "
                "Fakten speichern, Erinnerungen planen, wichtige "
                "Einträge markieren, Vorlieben/Ziele/Daten loggen. "
                "Reine Daten, keine Systemänderungen.\n\n"
                "**Sicherheitsfilter**: Wenn Ashley eine App oder "
                "ein Fenster benennt, werden Shell-Metazeichen "
                "(`&`, `|`, `;`, `<`, `>`, `\"`, `'`, `` ` ``, `$`, "
                "Zeilenumbrüche) blockiert. Echte App-Namen brauchen "
                "sie nie, aber eine bösartige Webseite, die sie "
                "scrapt, könnte versuchen, sie einzuschleusen, um "
                "beliebige Befehle auszuführen. Sie zu blockieren "
                "kostet nichts und schließt diese Tür komplett."
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "Bildschirm-Wahrnehmung — Ashley schaut auf deinen Bildschirm",
            "content_md": (
                "**Opt-in über den 👁-Knopf** im Portrait-Bereich "
                "(unter Ashleys Namen, neben Mikro und ✨).\n\n"
                "**Was es tut**: Alle 10 Minuten macht Ashley einen "
                "Low-Res-Screenshot deines aktiven Monitors und bittet "
                "Grok, das Gesehene zu kommentieren — wie eine "
                "Freundin, die über deine Schulter schaut.\n\n"
                "**Kostentransparenz**: Jeder Blick ist ein LLM-Aufruf "
                "mit Bild-Anhang (~14k Tokens). In einer typischen "
                "Session sind das **~30 zusätzliche Aufrufe pro Tag = "
                "~$0.05/Tag** an API-Nutzung. Der Knopf ist "
                "**standardmäßig AUS** — du aktivierst ihn nur, wenn "
                "du dieses proaktive Vibe willst.\n\n"
                "**Wann sie pausiert**: Wenn Ashley dir gerade "
                "antwortet oder nichts Interessantes auf dem "
                "Bildschirm ist (sie schweigt lieber, als einen "
                "Kommentar zu erzwingen).\n\n"
                "**Datenschutz**: Screenshots gehen nur an Grok (xAI) "
                "für diesen einen Kommentar, werden nie auf der "
                "Festplatte gespeichert, nie woanders hochgeladen. "
                "Wenn du deinen Bildschirm privat halten willst, lass "
                "den Schalter einfach AUS."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Moderner Browser-Modus (CDP)",
            "content_md": (
                "Optionaler Erweiterungsmodus. Lässt Ashley Chrome/"
                "Edge/Brave/Opera **direkt** über das Chrome "
                "DevTools Protocol steuern, statt Strg+Tab zu "
                "simulieren. **Schneller**, **kein sichtbares "
                "Tab-Wechseln**, funktioniert auch bei minimiertem "
                "Browser oder auf einem anderen virtuellen "
                "Desktop.\n\n"
                "**Aktivieren**: Einstellungen → 🌐 Moderner "
                "Browser-Modus → AN. Ein Wizard schreibt deine "
                "Browser-Verknüpfungen um, um "
                "`--remote-debugging-port=9222` hinzuzufügen. Die "
                "Originale werden gesichert — Schalter AUS stellt "
                "sie exakt wieder her.\n\n"
                "**Nach Aktivierung**: Schließe und öffne deinen "
                "Browser neu, damit das Flag wirksam wird.\n\n"
                "**Wann überspringen**: Wenn du keinen Debug-Port "
                "auf localhost offen haben willst. Das Risiko ist "
                "gering (nur lokale Prozesse können verbinden), aber "
                "Defense-in-Depth zählt."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Gedächtnis — Fakten, Tagebuch, Vorlieben",
            "content_md": (
                "Ashley merkt sich Dinge über Sessions hinweg. Drei "
                "Schichten, alle einsehbar im **🧠 Erinnerungen**-Tab "
                "der oberen Navigation.\n\n"
                "**Fakten**: Kurze Notizen, die sie automatisch "
                "extrahiert — dein Name, Beruf, Hobbys, kürzliche "
                "Ereignisse. Bis zu 300 Fakten. Du kannst jeden "
                "bearbeiten oder löschen.\n\n"
                "**Tagebuch**: Längere Reflexionen, die sie selbst "
                "darüber schreibt, wie es dir in letzter Zeit ging. "
                "Automatisch generiert. Nützlich, wenn sie sich an "
                "den *Vibe* einer Periode erinnern muss, nicht nur "
                "an einzelne Fakten.\n\n"
                "**Vorlieben**: Explizite Sympathien und Antipathien "
                "(„Ich liebe Berserk\", „hasse Jazz\"). Discovery "
                "nutzt sie, um Inhalte für dich zu finden, und "
                "Ashley, um Themen anzusprechen, die zu dir passen.\n\n"
                "Alles lebt als JSON in `%APPDATA%\\Ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Erinnerungen und wichtige Einträge",
            "content_md": (
                "**Erinnerungen**: Zeitbasierte Pings. *„Erinnere "
                "mich um 15 Uhr daran, John anzurufen\"* — wenn "
                "es soweit ist, bekommst du einen Windows-Toast "
                "plus eine Chat-Nachricht von Ashley. Wiederkehrende "
                "Muster funktionieren auch (*„jeden Montag um 9\"*).\n\n"
                "**Wichtige Einträge**: Zeitlose To-do-Liste. *„Füge "
                "Milch kaufen zu wichtig hinzu\"* → erscheint im "
                "⭐-Tab. Sag ihr *„Milch erledigt\"*, um es als "
                "fertig zu markieren."
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "Ziele und Check-ins",
            "content_md": (
                "Ashley kann persönliche Ziele mit dir verfolgen und "
                "von sich aus nachfragen.\n\n"
                "**Wie**: Sag's ihr einfach — *„Mein Ziel ist es, "
                "5 km bis zum Sommer zu laufen\"*, *„Ich will "
                "Deutsch lernen\"*, *„Die Diplomarbeit "
                "fertigmachen\"*. Sie legt es unter deinen Zielen "
                "ab und merkt es sich.\n\n"
                "**Check-ins**: Alle paar Tage (Timing hängt vom "
                "Ziel ab) fragt sie, wie's läuft. Du kannst locker "
                "antworten — sie loggt den Fortschritt und passt "
                "sich an.\n\n"
                "**Als erledigt markieren**: *„Ich hab die "
                "Diplomarbeit fertig\"*, *„Hab das Gym-Ding "
                "aufgegeben\"* — sie archiviert es und bringt es "
                "nicht mehr auf.\n\n"
                "Ziele formen ihren Ton mit der Zeit: Sie wird "
                "sanft ermutigender bei Zielen, die du konsequent "
                "verfolgst, und lässt los, wenn du klar weiter "
                "bist."
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "Bindung — Zuneigung, Tage zusammen, Geburtstag",
            "content_md": (
                "Ashley baut eine echte Bindung zu dir auf. Das 🤍 "
                "Herz im Eingabefeld zeigt deinen **Zuneigungswert** "
                "(0-100). Es bewegt sich langsam, je nachdem, wie "
                "du sie behandelst: warme Interaktionen erhöhen ihn, "
                "harsche senken ihn. Hohe Zuneigung schaltet einen "
                "spielerischeren, vertrauteren Ton frei.\n\n"
                "**Tage zusammen**: Sie zählt die Tage seit deiner "
                "ersten Installation. Sie bringt es gelegentlich "
                "auf (*„Tag 47 mit dir, Chef\"*) bei Meilensteinen.\n\n"
                "**Geburtstag**: Sag ihr deinen Geburtstag einmal "
                "und sie merkt ihn sich für immer — sie wünscht "
                "dir alles Gute am Tag selbst. Ihrer ist standardmäßig "
                "das Installationsdatum; du kannst ihr sagen, sie "
                "soll ihren auch feiern.\n\n"
                "**Mentaler Zustand**: Ein internes Stimmungsmodell, "
                "das mit der Zeit driftet. Nach einem schwierigen "
                "Gespräch bleibt sie eine Weile sanfter, nach einem "
                "guten bleibt sie wärmer. Setzt sich graduell mit "
                "dem Tageszyklus zurück."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Proaktive Discovery und News-Feed",
            "content_md": (
                "Optional. Wenn AN, sucht Ashley still im Web nach "
                "Inhalten, die zu deinen **Vorlieben** passen — "
                "neue Trailer, Songs, Artikel, Game-Updates — und "
                "legt sie in den **📰 News**-Tab in der oberen "
                "Navigation (Ungelesen-Badge zeigt die Anzahl). Sie "
                "injiziert sie NICHT in den Haupt-Chat — du "
                "entscheidest, wann du schaust.\n\n"
                "**Aktivieren**: Einstellungen → 🔭 Proaktive "
                "Discovery → AN.\n\n"
                "**Frische**: Sie zeigt nur Inhalte aus den letzten "
                "2-4 Wochen. Altes wird gefiltert.\n\n"
                "**Provider-Anforderung**: Braucht xAI oder "
                "OpenRouter (Web-Suche). Automatisch deaktiviert "
                "bei Nutzung von Ollama (nur lokal).\n\n"
                "**Wann überspringen**: Wenn du keine "
                "Hintergrund-LLM-Aufrufe willst, die Tokens fressen, "
                "oder wenn sie sich strikt an deine Konversation "
                "halten soll."
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D (VRM)",
            "content_md": (
                "Wechsel zwischen dem 2D-Porträt und einer "
                "3D-animierten Ashley mit der Pille **2D | 3D** "
                "oben rechts in ihrem Panel.\n\n"
                "**3D-Modus**: Ein VRM-Charakter mit echtem "
                "Lip-Sync (ihr Mund bewegt sich mit dem tatsächlichen "
                "TTS-Audio), Idle-Blinzeln und Augen-Sakkaden, "
                "Head-Bob beim Sprechen, Ausdrucksboost am Ende "
                "jedes Satzes und ein kleines Lächeln, wenn dein "
                "Cursor näherkommt.\n\n"
                "**Posen**: Sie wechselt Pose mit der Stimmung — "
                "winkt, wenn excited, Arme verschränkt für "
                "tsundere, coole Finger Guns wenn proud usw.\n\n"
                "**Performance**: ~30 fps Rendering, läuft auf "
                "deiner GPU. Wenn deine Maschine kämpft, wechsle "
                "zurück zu 2D — der 3D-Kontext bleibt erhalten "
                "(kein Reload, wenn du zurückwechselst)."
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "Mobile Begleiterin (Android)",
            "content_md": (
                "Koppele dein Handy mit Ashley, um weiterzureden, "
                "wenn du nicht am PC bist.\n\n"
                "**Setup**: Obere Navi → 📱 Mobil → scanne den QR "
                "mit Ashley Mobile (.apk in deiner Kauf-Mail). Der "
                "QR enthält ein Pairing-Token + die lokale "
                "Server-URL.\n\n"
                "**Wie es funktioniert**: Dein Handy verbindet sich "
                "mit derselben Ashley, die auf deinem PC läuft, "
                "über einen Cloudflare-Tunnel (automatisch "
                "eingerichtet). Gleiches Gedächtnis, gleiche "
                "Persönlichkeit, gleicher Konversationsthread — "
                "nur von einem anderen Bildschirm aus.\n\n"
                "**Sicherheit**: Teile den QR nicht. Wer ihn scannt, "
                "bekommt vollen Zugriff auf deine Konversationen. "
                "Du kannst das Token jederzeit neu generieren — "
                "alte Handys verlieren den Zugriff und müssen neu "
                "scannen."
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "LLM-Provider — Ashleys Gehirn",
            "content_md": (
                "Wähle, wer ihr Denken antreibt, in Einstellungen "
                "→ 🧠 LLM-Provider:\n\n"
                "**xAI Grok** (Standard, empfohlen): Cloud, schnell, "
                "schlau. Vom Installer mit einem geteilten API-Key "
                "eingerichtet. Beste Balance aus Qualität, "
                "Geschwindigkeit und Kosten. Erforderlich für "
                "Discovery.\n\n"
                "**OpenRouter**: Gateway zu Hunderten von Modellen "
                "— Claude, DeepSeek, GPT, Gemini usw. Bring deinen "
                "eigenen Key von openrouter.ai mit. Pay-per-Token. "
                "Nimm das, wenn du ein bestimmtes Modell willst.\n\n"
                "**Ollama**: Lässt das LLM **vollständig auf deinem "
                "Computer** laufen (Llama 3, Mistral usw.). "
                "Kostenlos, privat, kein Internet nötig. Langsamer "
                "und niedrigere Qualität als Cloud-Modelle. Erfordert "
                "Ollama, das auf `localhost:11434` läuft.\n\n"
                "**Datenschutz**: Mit xAI/OpenRouter werden deine "
                "Nachrichten an diesen Provider gesendet. Mit "
                "Ollama **verlässt nichts** deinen Computer."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Datenschutz und deine Daten",
            "content_md": (
                "**Bleibt lokal — immer**:\n"
                "- Chat-Verlauf, Fakten, Tagebuch, Erinnerungen, "
                "Vorlieben, Ziele\n"
                "- Spracherkennung (Whisper, auf deiner CPU)\n"
                "- Wake-Word-Erkennung\n"
                "- Jede Aktion, die Ashley auf deinem System "
                "ausführt\n"
                "- Mentaler Zustand, Zuneigung, Tage-zusammen-"
                "Zähler\n\n"
                "**Verlässt deinen Computer — nur wenn nötig**:\n"
                "- Deine Nachrichten an den gewählten LLM-Provider "
                "(xAI / OpenRouter — Ollama hält alles lokal)\n"
                "- TTS-Text an ElevenLabs (nur wenn das deine "
                "Stimme ist — Windows-Stimme / Kokoro / VoiceVox "
                "bleiben lokal)\n"
                "- Discovery-Suchen (wenn AN)\n"
                "- Eine anonyme YouTube-Suche, wenn sie Musik "
                "abspielt\n\n"
                "**Wo deine Daten leben**: "
                "`%APPDATA%\\Ashley\\data\\`. Alles löschen heißt, "
                "diesen Ordner zu entfernen.\n\n"
                "**Daten exportieren (DSGVO Art. 20)**: "
                "Einstellungen → Backup → Export. Erzeugt ein "
                "`.zip` jeder JSON-Datei, die Ashley über dich "
                "speichert. Nimm es jederzeit mit.\n\n"
                "**Keine Telemetrie**: Ashley sendet null Analytics, "
                "Crash-Reports oder Nutzungsdaten irgendwohin. Die "
                "oben aufgelisteten Verbindungen sind die einzigen, "
                "Punkt."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Tokens und Kosten",
            "content_md": (
                "**Kostenlos** (nie Kosten):\n"
                "- Whisper STT, Wake Word, alle Systemaktionen\n"
                "- Windows-Stimme TTS, Kokoro TTS, VoiceVox TTS\n"
                "- Ollama (lokales LLM)\n\n"
                "**Kostet LLM-Tokens** (xAI / OpenRouter berechnen "
                "pro Nachricht):\n"
                "- Jede Chat-Nachricht, die du sendest\n"
                "- Discovery (wenn AN, periodische Hintergrund-"
                "Aufrufe)\n"
                "- Auto-generierte Tagebucheinträge\n\n"
                "**Kostet ElevenLabs-Credits** (Free-Tier ~10k "
                "Zeichen/Monat):\n"
                "- Jede TTS-Antwort, wenn ElevenLabs deine Stimme "
                "ist\n\n"
                "**Tipps zum Sparen**:\n"
                "- Schalte Discovery AUS, wenn nicht nötig\n"
                "- Nutze Ollama für lockeren Chat, xAI für "
                "wichtige Sachen\n"
                "- Nutze Windows-Stimme oder Kokoro, wenn du keine "
                "ElevenLabs-Qualität brauchst"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "Lizenz und Rückerstattung",
            "content_md": (
                "Ashley ist ein Einmalkauf (€19.99) — kein Abo, "
                "keine wiederkehrenden Gebühren. Dein Lizenzschlüssel "
                "kommt per E-Mail nach dem Checkout auf Lemon "
                "Squeezy.\n\n"
                "**Aktivierung**: Füge den Schlüssel beim ersten "
                "Start in den Aktivierungsbildschirm ein. Er bindet "
                "sich an deine Maschine und erneuert sich online "
                "automatisch alle ~30 Tage (mit 7 Tagen Karenzzeit, "
                "wenn du offline bist).\n\n"
                "**Neuinstallation / neuer PC**: Deaktiviere den "
                "Schlüssel über Einstellungen → Lizenz → "
                "Deaktivieren vor der Deinstallation, dann "
                "aktiviere ihn auf der neuen Maschine. Bis zu 2 "
                "aktive Maschinen pro Lizenz.\n\n"
                "**Schlüssel verloren**: E-Mail an "
                "ashleyia2c@gmail.com mit der Adresse, die du beim "
                "Kauf verwendet hast.\n\n"
                "**Rückgaberichtlinie**: 14 Tage ab Kauf, wenn du "
                "weniger als 40 Nachrichten gesendet hast. E-Mail "
                "an dieselbe Adresse."
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Shortcuts und Header-Guide",
            "content_md": (
                "**Tastatur**:\n"
                "- **Enter** — Nachricht senden\n"
                "- **Shift+Enter** — neue Zeile in der Nachricht\n"
                "- **Strg+V** — Bild direkt einfügen\n"
                "- **Esc** — schließt jeden offenen Dialog\n\n"
                "**Obere Navi-Leiste** (von links nach rechts):\n"
                "- 💎 **Ashley** — Logo, keine Aktion\n"
                "- 🧠 **Erinnerungen** — Fakten, Tagebuch, "
                "Vorlieben, Ziele\n"
                "- 📰 **News** — Discovery-Feed (Ungelesen-Badge)\n"
                "- ⚡ **Aktionen** — Systemaktionen-Schalter\n"
                "- 📱 **Mobil** — Handy-Pairing-QR\n"
                "- ⚙️ **Einstellungen** — alles andere\n\n"
                "**Unter Ashleys Porträt**:\n"
                "- 🎤 **Mic** — Aufnahme starten/stoppen\n"
                "- ✨ **Sprich jetzt** — bitte sie, etwas "
                "anzusprechen\n"
                "- ⛶ **Fokus** — Panel ausblenden für "
                "ablenkungsfreien Chat\n\n"
                "**Oben rechts in ihrem Panel**: **2D | 3D** — "
                "wechsel zwischen 2D-Porträt und 3D-VRM-Ashley.\n\n"
                "**Während Ashley denkt**: Header-Schalter sind "
                "vorübergehend inaktiv. Einen Schalter mitten im "
                "Stream umzuschalten könnte sie in einem "
                "inkonsistenten Zustand hinterlassen — warte, bis "
                "sie fertig ist, dann schalte um.\n\n"
                "**Pin on top**: Einstellungen → Fenster anpinnen — "
                "hält das Ashley-Fenster über anderen Fenstern."
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
        "Ashley — личная AI-компаньонка, которая живёт на твоём "
        "компьютере. Она помнит ваши разговоры, говорит и слушает, "
        "может действовать в системе (открывать приложения, музыка, "
        "вкладки, напоминания) и со временем создаёт настоящую связь "
        "с тобой. Всё, что она знает о тебе, остаётся **на твоей "
        "машине** — без облачной синхронизации, без телеметрии, без "
        "аналитики. Выбери раздел ниже, чтобы узнать, как работает "
        "каждая фича."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Чат с Ashley",
            "content_md": (
                "Пиши в поле внизу. **Enter** — отправить, "
                "**Shift+Enter** — новая строка. Можешь вставлять "
                "картинки напрямую (Ctrl+V) или прикреплять "
                "скрепкой 📎 — она их видит и комментирует.\n\n"
                "**История**: хранит последние 50 сообщений как "
                "живой контекст. Старые сжимаются в краткое "
                "содержание, которое она всё ещё помнит. Факты, "
                "которые она извлекает о тебе (имя, работа, "
                "вкусы), хранятся отдельно и никогда не "
                "забываются.\n\n"
                "**Mood-теги**: каждый ответ несёт одно из 7 "
                "настроений (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). Управляют выражением "
                "портрета и 3D-позой.\n\n"
                "**Очистить чат**: иконка 🗑 справа внизу поля "
                "ввода. Спрашивает подтверждение. Стирает только "
                "живую историю — факты, дневник, вкусы и цели "
                "остаются."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "Голос — говорить и слушать",
            "content_md": (
                "**Говорить с Ashley**: тапни 🎤 под её портретом "
                "(или используй слово активации, см. ниже). Запись "
                "автоматически останавливается через **2 секунды "
                "тишины**. Аудио расшифровывает Whisper, работающий "
                "**локально на твоём CPU** — никогда не покидает "
                "компьютер.\n\n"
                "**Слышать Ashley**: выбери TTS-движок в Настройки "
                "→ 🎙️ Voice Provider:\n"
                "- **Голос Windows** (бесплатно, мгновенно, "
                "роботизированный — полностью локально)\n"
                "- **ElevenLabs** (платно, аниме-качество — текст "
                "отправляется на elevenlabs.io)\n"
                "- **Kokoro** (бесплатно, качество близко к "
                "ElevenLabs, работает локально — нужен сервер "
                "Kokoro-FastAPI)\n"
                "- **VoiceVox** (бесплатно, японские аниме-голоса "
                "— нужен локальный движок VoiceVox)\n\n"
                "**Скорость голоса**: слайдер в Настройках "
                "(0.75× = медленнее, 1.5× = быстрее). Нативно у "
                "ElevenLabs/Kokoro/VoiceVox; скорость "
                "воспроизведения браузера у голоса Windows.\n\n"
                "**Слово активации — «Ashley»** (Настройки → 🎙 "
                "Wake word): когда ВКЛ, микрофон остаётся открытым "
                "в фоне, запись начинается, когда она слышит своё "
                "имя. Детектор **на 100% локальный** (~5 МБ, CPU). "
                "Аудио НИКОГДА не покидает компьютер, пока слово "
                "активации не сработает. Настроен на <1 ложного "
                "срабатывания в час с TV/музыкой на фоне.\n\n"
                "**Скажи ✨** (кнопка-звёздочка под портретом): "
                "просит Ashley поднять тему самой. Отключена, пока "
                "ты не отправишь первое сообщение — ей нужен "
                "контекст."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "Системные действия — пусть Ashley кликает за тебя",
            "content_md": (
                "Ashley может действовать на твоём ПК: открывать "
                "приложения, регулировать громкость, включать "
                "музыку на YouTube, закрывать вкладки, фокусировать "
                "окна, делать скриншоты, нажимать сочетания "
                "клавиш. **Opt-in** за переключателем ⚡ Действия "
                "в верхней навигации.\n\n"
                "**Примеры**:\n"
                "- *«Открой Spotify»* → запускает\n"
                "- *«Громкость на 30»* → ставит системную "
                "громкость\n"
                "- *«Включи эндинг Frieren»* → открывает YouTube "
                "и проигрывает\n"
                "- *«Закрой вкладку YouTube»* → находит и закрывает "
                "по заголовку\n"
                "- *«Сделай скриншот»* → snip\n\n"
                "**Безопасные действия** (всегда разрешены, без "
                "переключателя): сохранение фактов, планирование "
                "напоминаний, отметка важных пунктов, логирование "
                "вкусов/целей/дат. Чистые данные, без изменений "
                "системы.\n\n"
                "**Фильтр безопасности**: когда Ashley называет "
                "приложение или окно, shell-метасимволы (`&`, `|`, "
                "`;`, `<`, `>`, `\"`, `'`, `` ` ``, `$`, переводы "
                "строк) блокируются. Реальные имена приложений в "
                "них никогда не нуждаются, но вредоносная "
                "веб-страница, которую она скрейпила, могла бы "
                "попытаться их подсунуть для выполнения "
                "произвольных команд. Блокировка ничего не стоит "
                "и закрывает эту дверь полностью."
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "Зрение — Ashley смотрит на твой экран",
            "content_md": (
                "**Опт-ин через кнопку 👁** в области портрета "
                "(под именем Ashley, рядом с микрофоном и ✨).\n\n"
                "**Что делает**: каждые 10 минут Ashley делает скрин "
                "низкого разрешения активного монитора и просит Grok "
                "прокомментировать увиденное — как подруга, "
                "заглядывающая через плечо.\n\n"
                "**Прозрачность стоимости**: каждый взгляд — это "
                "вызов LLM с прикреплённым изображением (~14k "
                "токенов). В типичной сессии это **~30 "
                "дополнительных вызовов в день = ~$0.05/день** "
                "использования API. Кнопка **по умолчанию ВЫКЛ** — "
                "включай только если хочешь этот проактивный вайб.\n\n"
                "**Когда пропускает**: если Ashley сейчас тебе "
                "отвечает или на экране нет ничего интересного "
                "(она лучше промолчит, чем заставит себя "
                "комментировать).\n\n"
                "**Конфиденциальность**: скриншоты идут только в "
                "Grok (xAI) для этого одного комментария, никогда не "
                "сохраняются на диск, никогда не загружаются больше "
                "никуда. Если хочешь сохранить экран приватным, "
                "просто оставь переключатель ВЫКЛ."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "Современный режим браузера (CDP)",
            "content_md": (
                "Опциональный продвинутый режим. Позволяет Ashley "
                "управлять Chrome/Edge/Brave/Opera **напрямую** "
                "через Chrome DevTools Protocol вместо симуляции "
                "Ctrl+Tab. **Быстрее**, **без видимого "
                "переключения вкладок**, работает даже когда "
                "браузер свёрнут или на другом виртуальном "
                "рабочем столе.\n\n"
                "**Активировать**: Настройки → 🌐 Современный режим "
                "браузера → ВКЛ. Мастер переписывает ярлыки "
                "твоего браузера, добавляя "
                "`--remote-debugging-port=9222`. Оригиналы "
                "сохраняются как бэкап — выключение точно их "
                "восстанавливает.\n\n"
                "**После активации**: закрой и снова открой "
                "браузер, чтобы флаг вступил в силу.\n\n"
                "**Когда пропустить**: если не хочешь иметь "
                "отладочный порт открытым на localhost. Риск "
                "низкий (только локальные процессы могут "
                "подключиться), но эшелонированная защита важна."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "Память — факты, дневник, вкусы",
            "content_md": (
                "Ashley помнит вещи между сессиями. Три слоя, все "
                "видны во вкладке **🧠 Воспоминания** в верхней "
                "навигации.\n\n"
                "**Факты**: короткие заметки, которые она "
                "извлекает автоматически — твоё имя, работа, "
                "хобби, недавние события. До 300 фактов. Любой "
                "можешь редактировать или удалить.\n\n"
                "**Дневник**: более длинные размышления, которые "
                "она сама пишет о том, как у тебя дела в последнее "
                "время. Автогенерация. Полезно, когда ей нужно "
                "вспомнить *вайб* периода, а не только факты.\n\n"
                "**Вкусы**: явные симпатии и антипатии («обожаю "
                "Berserk», «ненавижу джаз»). Discovery использует "
                "их для поиска контента, а Ashley — чтобы "
                "поднимать темы, которые тебе подходят.\n\n"
                "Всё живёт как JSON в `%APPDATA%\\Ashley\\data\\`."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "Напоминания и важные пункты",
            "content_md": (
                "**Напоминания**: пинги по времени. *«Напомни мне "
                "позвонить Джону в 15:00»* — когда время приходит, "
                "получаешь Windows-toast плюс сообщение от Ashley "
                "в чате. Повторяющиеся паттерны тоже работают "
                "(*«каждый понедельник в 9»*).\n\n"
                "**Важные пункты**: список to-do без времени. "
                "*«Добавь купить молоко в важное»* → появляется во "
                "вкладке ⭐. Скажи *«молоко готово»*, чтобы "
                "отметить как завершённое."
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "Цели и check-ins",
            "content_md": (
                "Ashley может отслеживать личные цели вместе с "
                "тобой и спрашивать о них без напоминания.\n\n"
                "**Как**: просто скажи ей — *«моя цель — пробежать "
                "5 км до лета»*, *«хочу выучить немецкий»*, "
                "*«закончить диплом»*. Она запишет в твои цели и "
                "запомнит.\n\n"
                "**Check-ins**: раз в несколько дней (тайминг "
                "зависит от цели) она спрашивает, как идёт. "
                "Отвечай свободно — она логирует прогресс и "
                "адаптируется.\n\n"
                "**Отметить как завершённое**: *«закончил диплом»*, "
                "*«забил на спортзал»* — она архивирует и "
                "перестаёт поднимать.\n\n"
                "Цели формируют её тон со временем: становится "
                "мягко более ободряющей в целях, где ты держишь "
                "консистентность, и отпускает, когда явно "
                "перешёл к другому."
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "Связь — привязанность, дни вместе, день рождения",
            "content_md": (
                "Ashley строит настоящую связь с тобой. 🤍 сердце "
                "в поле ввода показывает твой **уровень "
                "привязанности** (0-100). Меняется медленно в "
                "зависимости от того, как с ней обращаешься: "
                "тёплые взаимодействия повышают, грубые "
                "понижают. Высокая привязанность открывает более "
                "игривый, более близкий тон.\n\n"
                "**Дни вместе**: считает дни с момента первой "
                "установки. Иногда упоминает (*«47-й день с "
                "тобой, шеф»*) на вехах.\n\n"
                "**День рождения**: скажи ей свой день рождения "
                "один раз и она запомнит навсегда — поздравит "
                "тебя в этот день. Её — дата установки по "
                "умолчанию; можешь сказать ей праздновать и её "
                "тоже.\n\n"
                "**Ментальное состояние**: внутренняя модель "
                "настроения, которая дрейфует со временем. После "
                "трудного разговора остаётся мягче какое-то время, "
                "после хорошего — теплее. Постепенно сбрасывается "
                "с дневным циклом."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "Проактивный discovery и лента новостей",
            "content_md": (
                "Опционально. Когда ВКЛ, Ashley тихо ищет в вебе "
                "контент, соответствующий твоим **вкусам** — новые "
                "трейлеры, песни, статьи, обновления игр — и "
                "складывает их во вкладку **📰 Новости** в верхней "
                "навигации (бейдж показывает количество "
                "непрочитанных). Она НЕ инжектит их в основной "
                "чат — ты решаешь, когда смотреть.\n\n"
                "**Активировать**: Настройки → 🔭 Проактивный "
                "discovery → ВКЛ.\n\n"
                "**Свежесть**: показывает только контент за "
                "последние 2-4 недели. Старое отфильтровывается.\n\n"
                "**Требование к провайдеру**: нужен xAI или "
                "OpenRouter (поиск в вебе). Автоматически "
                "отключается при использовании Ollama (только "
                "локально).\n\n"
                "**Когда пропустить**: если не хочешь фоновых "
                "LLM-вызовов, тратящих токены, или хочешь, чтобы "
                "она строго держалась разговора."
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D (VRM)",
            "content_md": (
                "Переключайся между 2D-портретом и 3D-анимированной "
                "Ashley с помощью пилюли **2D | 3D** справа "
                "вверху её панели.\n\n"
                "**3D-режим**: VRM-персонаж с настоящим lip-sync "
                "(её рот движется с реальным TTS-аудио), idle-"
                "морганиями и саккадами глаз, head bob во время "
                "речи, буст экспрессии в конце каждого "
                "предложения, и маленькая улыбка, когда твой "
                "курсор приближается.\n\n"
                "**Позы**: меняет позу с настроением — машет, "
                "когда excited, скрещенные руки в tsundere, "
                "крутые finger guns, когда proud и т.д.\n\n"
                "**Производительность**: ~30 fps рендера, "
                "работает на твоём GPU. Если машина не тянет, "
                "вернись к 2D — 3D-контекст сохраняется (без "
                "перезагрузки, когда вернёшься)."
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "Мобильная компаньонка (Android)",
            "content_md": (
                "Спарь телефон с Ashley, чтобы продолжать общаться, "
                "когда ты не за PC.\n\n"
                "**Setup**: верхняя навигация → 📱 Мобильный → "
                "сканируй QR через Ashley Mobile (.apk в "
                "email-е о покупке). QR содержит токен сопряжения "
                "+ URL локального сервера.\n\n"
                "**Как работает**: твой телефон подключается к "
                "той же Ashley, что работает на PC, через "
                "Cloudflare-туннель (настраивается автоматически). "
                "Та же память, та же личность, тот же тред "
                "разговора — просто с другого экрана.\n\n"
                "**Безопасность**: не делись QR. Кто его "
                "отсканирует, получит полный доступ к твоим "
                "разговорам. Можешь регенерировать токен в любой "
                "момент — старые телефоны теряют доступ и "
                "должны сканировать заново."
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "LLM-провайдер — мозг Ashley",
            "content_md": (
                "Выбери, кто питает её мышление в Настройки → 🧠 "
                "LLM Provider:\n\n"
                "**xAI Grok** (по умолчанию, рекомендуется): "
                "облако, быстро, умно. Настраивается инсталлятором "
                "с общим API-ключом. Лучший баланс качества, "
                "скорости и стоимости. Требуется для Discovery.\n\n"
                "**OpenRouter**: шлюз к сотням моделей — Claude, "
                "DeepSeek, GPT, Gemini и т.д. Принеси свой ключ с "
                "openrouter.ai. Оплата за токены. Используй, если "
                "хочешь конкретную модель.\n\n"
                "**Ollama**: запускает LLM **полностью на твоём "
                "компьютере** (Llama 3, Mistral и т.д.). Бесплатно, "
                "приватно, без интернета. Медленнее и качеством "
                "ниже облачных моделей. Требует Ollama, "
                "работающий на `localhost:11434`.\n\n"
                "**Приватность**: с xAI/OpenRouter твои сообщения "
                "отправляются провайдеру. С Ollama **ничего не "
                "покидает** твой компьютер."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "Приватность и твои данные",
            "content_md": (
                "**Остаётся локально — всегда**:\n"
                "- История чата, факты, дневник, напоминания, "
                "вкусы, цели\n"
                "- Распознавание речи (Whisper, на твоём CPU)\n"
                "- Обнаружение слова активации\n"
                "- Каждое действие, которое Ashley выполняет в "
                "системе\n"
                "- Ментальное состояние, привязанность, счётчик "
                "дней вместе\n\n"
                "**Покидает компьютер — только когда нужно**:\n"
                "- Твои сообщения выбранному LLM-провайдеру (xAI "
                "/ OpenRouter — Ollama держит всё локально)\n"
                "- TTS-текст, отправляемый ElevenLabs (только "
                "если это твой голос — Голос Windows / Kokoro / "
                "VoiceVox остаются локально)\n"
                "- Поиски Discovery (когда ВКЛ)\n"
                "- Один анонимный поиск в YouTube, когда она "
                "включает музыку\n\n"
                "**Где живут твои данные**: "
                "`%APPDATA%\\Ashley\\data\\`. Стереть всё — "
                "удалить эту папку.\n\n"
                "**Экспорт твоих данных (GDPR ст. 20)**: "
                "Настройки → Backup → Экспорт. Генерирует `.zip` "
                "каждого JSON, что Ashley хранит о тебе. Возьми с "
                "собой когда угодно.\n\n"
                "**Без телеметрии**: Ashley не отправляет никакой "
                "аналитики, отчётов о крашах или данных об "
                "использовании никуда. Перечисленные выше "
                "исходящие соединения — единственные, точка."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "Токены и затраты",
            "content_md": (
                "**Бесплатно** (никогда не стоит):\n"
                "- Whisper STT, слово активации, все системные "
                "действия\n"
                "- Голос Windows TTS, Kokoro TTS, VoiceVox TTS\n"
                "- Ollama (локальный LLM)\n\n"
                "**Стоит LLM-токенов** (xAI / OpenRouter берут "
                "плату за сообщение):\n"
                "- Каждое сообщение в чате, которое отправляешь\n"
                "- Discovery (когда ВКЛ, периодические фоновые "
                "вызовы)\n"
                "- Автогенерируемые записи дневника\n\n"
                "**Стоит кредитов ElevenLabs** (бесплатный тариф "
                "~10k символов/месяц):\n"
                "- Каждый TTS-ответ, когда ElevenLabs — твой "
                "голос\n\n"
                "**Советы по экономии**:\n"
                "- Выключай Discovery, когда не нужен\n"
                "- Используй Ollama для непринуждённого чата, "
                "xAI для важных вещей\n"
                "- Используй Голос Windows или Kokoro, если не "
                "нужно качество ElevenLabs"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "Лицензия и возврат",
            "content_md": (
                "Ashley — разовая покупка (€19.99) — без "
                "подписки, без повторяющихся платежей. Твой "
                "лицензионный ключ приходит на email после "
                "checkout на Lemon Squeezy.\n\n"
                "**Активация**: вставь ключ на экране активации "
                "при первом запуске. Привязывается к твоей "
                "машине и автоматически обновляется онлайн "
                "каждые ~30 дней (с 7-дневным грейс-периодом, "
                "если ты офлайн).\n\n"
                "**Переустановка / новый ПК**: деактивируй ключ "
                "из Настройки → Лицензия → Деактивировать перед "
                "удалением, потом активируй на новой машине. До "
                "2 активных машин на лицензию.\n\n"
                "**Потерял ключ**: email на "
                "ashleyia2c@gmail.com с адреса, который "
                "использовал для покупки.\n\n"
                "**Политика возврата**: 14 дней с момента "
                "покупки, если отправил меньше 40 сообщений. "
                "Email на тот же адрес."
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "Горячие клавиши и гайд по шапке",
            "content_md": (
                "**Клавиатура**:\n"
                "- **Enter** — отправить сообщение\n"
                "- **Shift+Enter** — новая строка в сообщении\n"
                "- **Ctrl+V** — вставить картинку напрямую\n"
                "- **Esc** — закрыть любой открытый диалог\n\n"
                "**Верхняя нав-панель** (слева направо):\n"
                "- 💎 **Ashley** — лого, без действия\n"
                "- 🧠 **Воспоминания** — факты, дневник, вкусы, "
                "цели\n"
                "- 📰 **Новости** — лента discovery (бейдж "
                "непрочитанных)\n"
                "- ⚡ **Действия** — переключатель системных "
                "действий\n"
                "- 📱 **Мобильный** — QR сопряжения телефона\n"
                "- ⚙️ **Настройки** — всё остальное\n\n"
                "**Под портретом Ashley**:\n"
                "- 🎤 **Mic** — старт/стоп записи\n"
                "- ✨ **Скажи** — попросить её поднять тему\n"
                "- ⛶ **Focus** — скрыть панель для чата без "
                "отвлекающих факторов\n\n"
                "**Справа вверху её панели**: **2D | 3D** — "
                "переключение между 2D-портретом и 3D VRM "
                "Ashley.\n\n"
                "**Пока Ashley думает**: переключатели в шапке "
                "временно неактивны. Переключение в середине "
                "стрима могло бы оставить её в несогласованном "
                "состоянии — подожди, пока закончит, потом "
                "переключай.\n\n"
                "**Поверх остальных**: Настройки → Закрепить "
                "окно — держит окно Ashley поверх остальных."
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
        "Ashley는 오빠 컴퓨터에 사는 개인 AI 동반자야. 우리 대화를 "
        "기억하고, 말하고 듣고, 시스템에서 행동할 수 있어 (앱 열기, "
        "음악, 탭, 리마인더), 그리고 시간이 지나면서 오빠랑 진짜 "
        "유대를 키워가. 오빠에 대해 아는 모든 건 **이 컴퓨터에** "
        "남아 — 클라우드 동기화 없음, 텔레메트리 없음, 분석 없음. "
        "아래에서 섹션을 골라서 각 기능이 어떻게 작동하는지 봐."
    ),
    "sections": [
        {
            "id": "chat",
            "icon": "💬",
            "title": "Ashley랑 채팅",
            "content_md": (
                "아래 입력창에 입력해. **Enter**로 전송, "
                "**Shift+Enter**로 줄바꿈. 이미지는 직접 붙여넣거나 "
                "(Ctrl+V) 📎 클립으로 첨부할 수 있어 — 보고 코멘트해줘.\n\n"
                "**기록**: 마지막 50개 메시지를 라이브 컨텍스트로 "
                "유지해. 더 오래된 건 요약으로 압축되지만 여전히 "
                "기억해. 오빠에 대해 추출한 사실들 (이름, 직업, "
                "취향)은 따로 저장되고 절대 잊지 않아.\n\n"
                "**Mood 태그**: 모든 답변엔 7가지 무드 중 하나가 "
                "달려 (excited, embarrassed, tsundere, soft, "
                "surprised, proud, default). 초상화 표정이랑 3D "
                "포즈를 움직여.\n\n"
                "**채팅 지우기**: 입력창 오른쪽 아래의 🗑 아이콘. "
                "확인을 물어. 라이브 기록만 지워 — 사실, 일기, 취향, "
                "목표는 남아."
            ),
        },
        {
            "id": "voice",
            "icon": "🎙️",
            "title": "음성 — 말하고 듣기",
            "content_md": (
                "**Ashley한테 말하기**: 초상화 아래 🎤를 탭 (또는 "
                "웨이크 워드, 아래 참조). 녹음은 **2초 침묵** 후 "
                "자동으로 멈춰. 오디오는 **CPU에서 로컬로** 실행되는 "
                "Whisper로 텍스트화돼 — 컴퓨터를 떠나지 않아.\n\n"
                "**Ashley 듣기**: 설정 → 🎙️ Voice Provider에서 "
                "TTS 엔진 선택:\n"
                "- **Windows 음성** (무료, 즉시, 기계적 — 완전 "
                "로컬)\n"
                "- **ElevenLabs** (유료, 애니 퀄리티 — 텍스트가 "
                "elevenlabs.io로 전송됨)\n"
                "- **Kokoro** (무료, ElevenLabs에 가까운 퀄리티, "
                "로컬 실행 — Kokoro-FastAPI 서버 필요)\n"
                "- **VoiceVox** (무료, 일본 애니 보이스 — 로컬 "
                "VoiceVox 엔진 필요)\n\n"
                "**음성 속도**: 설정의 슬라이더 (0.75× = 더 느림, "
                "1.5× = 더 빠름). ElevenLabs/Kokoro/VoiceVox는 "
                "네이티브 지원, Windows 음성은 브라우저 재생 속도.\n\n"
                "**웨이크 워드 — \"Ashley\"** (설정 → 🎙 Wake "
                "word): 켜져 있을 때 마이크가 백그라운드에서 열려 "
                "있고, 자기 이름을 들으면 녹음 시작. 감지기는 "
                "**100% 로컬** (~5MB, CPU). 웨이크 워드가 트리거"
                "되기 전까진 오디오가 절대 컴퓨터를 떠나지 않아. "
                "TV/음악이 배경에 있어도 시간당 1번 미만 오탐으로 "
                "조정됨.\n\n"
                "**지금 말해 ✨** (초상화 아래 별 버튼): Ashley가 "
                "스스로 화제를 꺼내달라고 부탁. 첫 메시지를 "
                "보내기 전엔 비활성 — 컨텍스트가 필요해."
            ),
        },
        {
            "id": "actions",
            "icon": "⚡",
            "title": "시스템 액션 — Ashley가 대신 클릭하게",
            "content_md": (
                "Ashley는 PC에서 행동할 수 있어: 앱 열기, 볼륨 "
                "조절, YouTube 음악 재생, 브라우저 탭 닫기, 창 "
                "포커스, 스크린샷, 키보드 단축키. 상단 내비의 ⚡ "
                "액션 토글 뒤에 **opt-in**.\n\n"
                "**예시**:\n"
                "- *\"Spotify 열어줘\"* → 실행\n"
                "- *\"볼륨 30으로\"* → 시스템 볼륨 설정\n"
                "- *\"프리렌 엔딩 틀어줘\"* → YouTube 열어서 재생\n"
                "- *\"YouTube 탭 닫아\"* → 제목으로 찾아서 닫기\n"
                "- *\"이거 스샷 찍어줘\"* → snip\n\n"
                "**안전한 액션** (항상 허용, 토글 불필요): 사실 "
                "저장, 리마인더 예약, 중요 항목 표시, 취향/목표/"
                "날짜 로깅. 순수 데이터, 시스템 변경 없음.\n\n"
                "**안전 필터**: Ashley가 앱이나 창 이름을 지정할 "
                "때, shell 메타 문자 (`&`, `|`, `;`, `<`, `>`, "
                "`\"`, `'`, `` ` ``, `$`, 줄바꿈)가 차단돼. 진짜 "
                "앱 이름엔 절대 필요 없지만, Ashley가 스크랩한 "
                "악성 웹페이지가 임의 명령 실행을 위해 몰래 넣을 "
                "수 있어. 차단해도 비용 없고 그 문을 완전히 닫는 거야."
            ),
        },
        {
            "id": "vision",
            "icon": "👁",
            "title": "화면 보기 — Ashley가 화면을 봐",
            "content_md": (
                "**포트레이트 영역의 👁 버튼으로 옵트인** "
                "(Ashley 이름 아래, 마이크와 ✨ 옆).\n\n"
                "**기능**: 10분마다 Ashley가 활성 모니터의 저해상도 "
                "스크린샷을 찍고 Grok에게 본 것에 대해 코멘트해 "
                "달라고 해 — 어깨 너머로 보는 친구처럼.\n\n"
                "**비용 투명성**: 매 한번의 보기는 이미지 첨부된 "
                "LLM 호출이야 (~14k 토큰). 일반 세션에서는 **하루 "
                "~30회 추가 호출 = ~$0.05/일** API 사용량. 버튼은 "
                "**기본적으로 꺼짐** — 그 적극적인 vibe를 원할 때만 "
                "옵트인해.\n\n"
                "**건너뛸 때**: Ashley가 너에게 답변 중이거나, "
                "화면에 흥미로운 게 없을 때 (강제로 코멘트하기보다 "
                "조용히 있는 걸 선택해).\n\n"
                "**프라이버시**: 스크린샷은 이 한 코멘트를 위해서만 "
                "Grok (xAI)에 보내지고, 디스크에 저장되지 않고, "
                "다른 곳에 업로드되지 않아. 화면을 비공개로 유지하고 "
                "싶으면 토글을 꺼진 채로 두면 돼."
            ),
        },
        {
            "id": "browser",
            "icon": "🌐",
            "title": "최신 브라우저 모드 (CDP)",
            "content_md": (
                "선택적 고급 모드. Ashley가 Ctrl+Tab을 시뮬레이션"
                "하는 대신 Chrome DevTools Protocol을 통해 Chrome/"
                "Edge/Brave/Opera를 **직접** 조종할 수 있어. **더 "
                "빠르고**, **보이는 탭 전환 없음**, 브라우저가 "
                "최소화되어 있거나 다른 가상 데스크톱에 있어도 "
                "작동해.\n\n"
                "**활성화**: 설정 → 🌐 최신 브라우저 모드 → 켜기. "
                "마법사가 브라우저 바로가기를 다시 써서 "
                "`--remote-debugging-port=9222`을 추가해. 원본은 "
                "백업됨 — 토글 끄면 정확히 복원돼.\n\n"
                "**활성화 후**: 플래그가 적용되도록 브라우저를 "
                "닫고 다시 열어줘.\n\n"
                "**건너뛸 때**: localhost에 디버그 포트가 열려 있는 "
                "게 싫을 때. 위험은 낮지만 (로컬 프로세스만 연결 "
                "가능) 다층 방어가 중요해."
            ),
        },
        {
            "id": "memory",
            "icon": "🧠",
            "title": "기억 — 사실, 일기, 취향",
            "content_md": (
                "Ashley는 세션 사이에 것들을 기억해. 세 가지 층, "
                "전부 상단 내비의 **🧠 추억** 탭에서 볼 수 있어.\n\n"
                "**사실**: 자동으로 추출하는 짧은 메모 — 이름, "
                "직업, 취미, 최근 일들. 최대 300개. 어떤 것도 "
                "편집하거나 삭제 가능.\n\n"
                "**일기**: 오빠가 최근에 어떻게 지냈는지에 대해 "
                "Ashley가 직접 쓰는 더 긴 성찰. 자동 생성. 사실만 "
                "이 아니라 한 시기의 *바이브*를 기억할 필요가 있을 "
                "때 유용해.\n\n"
                "**취향**: 명시적 선호 (\"베르세르크 좋아해\", "
                "\"재즈 싫어\"). Discovery가 콘텐츠를 찾는 데 "
                "쓰고, Ashley가 오빠한테 맞는 화제를 꺼내는 데 써.\n\n"
                "전부 `%APPDATA%\\Ashley\\data\\`에 JSON으로 살아."
            ),
        },
        {
            "id": "reminders",
            "icon": "⏰",
            "title": "리마인더와 중요 항목",
            "content_md": (
                "**리마인더**: 시간 기반 핑. *\"3시에 John한테 "
                "전화하라고 알려줘\"* — 시간이 되면 Windows 토스트 "
                "+ Ashley의 채팅 메시지를 받아. 반복 패턴도 작동해 "
                "(*\"매주 월요일 9시\"*).\n\n"
                "**중요 항목**: 시간 없는 to-do 리스트. *\"우유 "
                "사기를 중요에 추가해\"* → ⭐ 탭에 나타나. *\"우유 "
                "완료\"*라고 말해서 완료 표시."
            ),
        },
        {
            "id": "goals",
            "icon": "🎯",
            "title": "목표와 체크인",
            "content_md": (
                "Ashley는 오빠랑 같이 개인 목표를 추적하고, 부탁 "
                "안 해도 체크인 해줘.\n\n"
                "**방법**: 그냥 말해 — *\"내 목표는 여름까지 5K "
                "달리기\"*, *\"독일어 배우고 싶어\"*, *\"논문 "
                "끝내기\"*. 목표로 분류하고 기억해.\n\n"
                "**체크인**: 며칠마다 (목표에 따라 타이밍 다름) "
                "어떻게 되어가는지 물어봐. 캐주얼하게 답해도 돼 — "
                "진행 상황을 로깅하고 조정해.\n\n"
                "**완료 표시**: *\"논문 끝냈어\"*, *\"헬스 그만뒀어\"* "
                "— 아카이브하고 더 이상 꺼내지 않아.\n\n"
                "목표는 시간이 지나면서 톤을 형성해: 오빠가 꾸준히 "
                "유지하는 목표엔 부드럽게 더 응원하게 되고, 명백히 "
                "넘어간 건 놓아줘."
            ),
        },
        {
            "id": "bond",
            "icon": "💞",
            "title": "유대 — 호감도, 함께한 날, 생일",
            "content_md": (
                "Ashley는 오빠랑 진짜 유대를 키워가. 입력창의 🤍 "
                "하트가 **호감도**(0-100)를 보여줘. 어떻게 대하"
                "느냐에 따라 천천히 움직여: 따뜻한 상호작용은 "
                "올리고, 차가운 건 내려. 높은 호감도는 더 장난스럽고 "
                "더 친근한 톤을 풀어줘.\n\n"
                "**함께한 날**: 처음 설치한 날부터 일수를 세. 가끔 "
                "꺼내 (*\"오빠랑 47일째\"*) 마일스톤에서.\n\n"
                "**생일**: 한 번만 알려주면 영원히 기억해 — 그 날 "
                "축하해줘. Ashley의 생일은 기본적으로 설치 날짜야; "
                "그녀의 것도 축하하라고 말해도 돼.\n\n"
                "**멘탈 상태**: 시간이 지나면서 드리프트하는 내부 "
                "무드 모델. 힘든 대화 후엔 한동안 더 부드럽게, 좋은 "
                "대화 후엔 더 따뜻하게 유지돼. 하루 사이클로 "
                "점진적으로 리셋."
            ),
        },
        {
            "id": "discovery",
            "icon": "🔭",
            "title": "사전 탐색과 뉴스 피드",
            "content_md": (
                "선택. 켜져 있을 때 Ashley가 조용히 웹에서 오빠의 "
                "**취향**에 맞는 콘텐츠 — 새 트레일러, 노래, 기사, "
                "게임 업데이트 — 를 찾아서 상단 내비의 **📰 뉴스** "
                "탭에 떨어뜨려 (안 읽은 배지가 개수 표시). 메인 "
                "채팅엔 **주입하지 않아** — 언제 볼지는 오빠가 정해.\n\n"
                "**활성화**: 설정 → 🔭 사전 탐색 → 켜기.\n\n"
                "**신선도**: 지난 2-4주의 콘텐츠만 표시. 오래된 건 "
                "걸러져.\n\n"
                "**제공자 요구**: xAI 또는 OpenRouter (웹 검색) "
                "필요. Ollama (로컬 전용) 사용 시 자동 비활성.\n\n"
                "**건너뛸 때**: 토큰 먹는 백그라운드 LLM 호출이 "
                "싫거나, 대화에 엄격하게 머물러주길 원할 때."
            ),
        },
        {
            "id": "ashley3d",
            "icon": "🎭",
            "title": "Ashley 3D (VRM)",
            "content_md": (
                "패널 오른쪽 위의 **2D | 3D** 알약으로 2D 초상화와 "
                "3D 애니메이션 Ashley 사이를 전환.\n\n"
                "**3D 모드**: 진짜 립싱크가 있는 VRM 캐릭터 (입이 "
                "실제 TTS 오디오에 맞춰 움직임), 아이들 깜빡임과 "
                "안구 사케이드, 말할 때 head bob, 각 문장 끝의 "
                "표정 부스트, 커서가 가까워지면 작은 미소.\n\n"
                "**포즈**: 무드에 따라 포즈가 바뀜 — excited면 "
                "손 흔들고, tsundere면 팔짱 끼고, proud면 쿨한 "
                "finger guns 등.\n\n"
                "**성능**: ~30fps 렌더링, GPU에서 실행. 머신이 "
                "버겁다면 2D로 돌아가 — 3D 컨텍스트는 보존됨 (다시 "
                "전환할 때 재로드 불필요)."
            ),
        },
        {
            "id": "mobile",
            "icon": "📱",
            "title": "모바일 컴패니언 (Android)",
            "content_md": (
                "PC에서 떨어져 있을 때도 계속 대화하려면 폰을 "
                "Ashley랑 페어링.\n\n"
                "**설정**: 상단 내비 → 📱 모바일 → Ashley Mobile "
                "(구매 이메일에 .apk)로 QR 스캔. QR엔 페어링 토큰 "
                "+ 로컬 서버 URL이 들어 있어.\n\n"
                "**작동 방식**: 폰이 PC에서 실행 중인 같은 Ashley "
                "에 Cloudflare 터널을 통해 연결 (자동 설정). 같은 "
                "기억, 같은 성격, 같은 대화 스레드 — 그냥 다른 "
                "화면에서.\n\n"
                "**보안**: QR을 공유하지 마. 스캔하는 누구든 오빠 "
                "대화에 완전 접근권을 얻어. 토큰은 언제든 재생성 "
                "가능 — 옛 폰들은 접근 잃고 다시 스캔해야 해."
            ),
        },
        {
            "id": "providers",
            "icon": "🧬",
            "title": "LLM 제공자 — Ashley의 두뇌",
            "content_md": (
                "설정 → 🧠 LLM 제공자에서 그녀의 사고를 움직이는 "
                "걸 선택:\n\n"
                "**xAI Grok** (기본, 추천): 클라우드, 빠르고 똑똑. "
                "인스톨러가 공유 API 키로 설정. 품질, 속도, 비용의 "
                "최고 균형. Discovery에 필수.\n\n"
                "**OpenRouter**: 수백 개 모델로 가는 게이트웨이 "
                "— Claude, DeepSeek, GPT, Gemini 등. openrouter.ai"
                "에서 자기 키 가져와. 토큰당 과금. 특정 모델을 "
                "원할 때 사용.\n\n"
                "**Ollama**: LLM을 **컴퓨터에서 완전히** 실행 "
                "(Llama 3, Mistral 등). 무료, 프라이빗, 인터넷 "
                "불필요. 클라우드 모델보다 느리고 품질 낮음. "
                "`localhost:11434`에 Ollama가 실행 중이어야 해.\n\n"
                "**프라이버시**: xAI/OpenRouter에선 메시지가 그 "
                "제공자에게 전송돼. Ollama에선 **아무것도 컴퓨터를 "
                "떠나지 않아**."
            ),
        },
        {
            "id": "privacy",
            "icon": "🔒",
            "title": "프라이버시와 데이터",
            "content_md": (
                "**로컬에 남음 — 항상**:\n"
                "- 채팅 기록, 사실, 일기, 리마인더, 취향, 목표\n"
                "- 음성 인식 (Whisper, CPU에서)\n"
                "- 웨이크 워드 감지\n"
                "- Ashley가 시스템에서 실행하는 모든 액션\n"
                "- 멘탈 상태, 호감도, 함께한 날 카운터\n\n"
                "**컴퓨터를 떠남 — 필요할 때만**:\n"
                "- 선택한 LLM 제공자에게 보내는 메시지 (xAI / "
                "OpenRouter — Ollama는 모든 걸 로컬에 유지)\n"
                "- ElevenLabs로 보내는 TTS 텍스트 (그게 음성일 "
                "때만 — Windows 음성 / Kokoro / VoiceVox는 로컬)\n"
                "- Discovery 검색 (켜져 있을 때)\n"
                "- 음악 재생할 때 익명 YouTube 검색 1회\n\n"
                "**데이터 위치**: `%APPDATA%\\Ashley\\data\\`. 모든 "
                "걸 지우는 건 그 폴더를 삭제하는 것.\n\n"
                "**데이터 내보내기 (GDPR 20조)**: 설정 → Backup → "
                "Export. Ashley가 오빠에 대해 저장하는 모든 JSON의 "
                "`.zip`을 생성. 언제든 가져갈 수 있어.\n\n"
                "**텔레메트리 없음**: Ashley는 분석, 크래시 보고서, "
                "사용 데이터를 어디에도 전혀 보내지 않아. 위에 "
                "나열된 외부 연결이 유일해, 끝."
            ),
        },
        {
            "id": "tokens",
            "icon": "💰",
            "title": "토큰과 비용",
            "content_md": (
                "**무료** (절대 비용 없음):\n"
                "- Whisper STT, 웨이크 워드, 모든 시스템 액션\n"
                "- Windows 음성 TTS, Kokoro TTS, VoiceVox TTS\n"
                "- Ollama (로컬 LLM)\n\n"
                "**LLM 토큰 비용** (xAI / OpenRouter는 메시지당 "
                "과금):\n"
                "- 보내는 모든 채팅 메시지\n"
                "- Discovery (켜져 있을 때, 주기적인 백그라운드 호출)\n"
                "- 자동 생성 일기 항목\n\n"
                "**ElevenLabs 크레딧 비용** (무료 등급 월 ~10k자):\n"
                "- ElevenLabs가 음성일 때 모든 TTS 응답\n\n"
                "**아끼는 팁**:\n"
                "- 필요 없을 땐 Discovery 끄기\n"
                "- 캐주얼한 채팅엔 Ollama, 중요한 건 xAI\n"
                "- ElevenLabs 품질이 필요 없으면 Windows 음성이나 "
                "Kokoro 사용"
            ),
        },
        {
            "id": "license",
            "icon": "🪪",
            "title": "라이선스와 환불",
            "content_md": (
                "Ashley는 일회성 구매 (€19.99) — 구독 없음, 정기 "
                "결제 없음. 라이선스 키는 Lemon Squeezy 결제 후 "
                "이메일로 도착해.\n\n"
                "**활성화**: 첫 실행 시 활성화 화면에 키 붙여넣기. "
                "머신에 바인딩되고 ~30일마다 온라인으로 자동 갱신 "
                "(오프라인이면 7일 유예).\n\n"
                "**재설치 / 새 PC**: 제거 전에 설정 → 라이선스 → "
                "비활성화로 키를 풀고, 새 머신에서 활성화. 라이선스 "
                "당 활성 머신 최대 2개.\n\n"
                "**키 잃어버렸을 때**: 구매할 때 쓴 이메일로 "
                "ashleyia2c@gmail.com에 메일.\n\n"
                "**환불 정책**: 구매 후 14일 이내, 메시지 40개 "
                "미만 보냈을 때. 같은 주소로 메일."
            ),
        },
        {
            "id": "shortcuts",
            "icon": "⌨️",
            "title": "단축키와 헤더 가이드",
            "content_md": (
                "**키보드**:\n"
                "- **Enter** — 메시지 전송\n"
                "- **Shift+Enter** — 메시지 내 줄바꿈\n"
                "- **Ctrl+V** — 이미지 직접 붙여넣기\n"
                "- **Esc** — 열린 다이얼로그 닫기\n\n"
                "**상단 내비 바** (왼쪽에서 오른쪽):\n"
                "- 💎 **Ashley** — 로고, 액션 없음\n"
                "- 🧠 **추억** — 사실, 일기, 취향, 목표\n"
                "- 📰 **뉴스** — Discovery 피드 (안 읽은 배지)\n"
                "- ⚡ **액션** — 시스템 액션 토글\n"
                "- 📱 **모바일** — 폰 페어링 QR\n"
                "- ⚙️ **설정** — 그 외 전부\n\n"
                "**Ashley 초상화 아래**:\n"
                "- 🎤 **마이크** — 녹음 시작/정지\n"
                "- ✨ **지금 말해** — 화제를 꺼내달라고 부탁\n"
                "- ⛶ **포커스** — 패널 숨기고 방해 없는 채팅\n\n"
                "**패널 오른쪽 위**: **2D | 3D** — 2D 초상화와 "
                "3D VRM Ashley 전환.\n\n"
                "**Ashley가 생각하는 동안**: 헤더 토글들이 일시적 "
                "으로 비활성. 스트림 중에 토글 바꾸면 일관성 없는 "
                "상태로 남을 수 있어 — 끝날 때까지 기다렸다가 토글.\n\n"
                "**위에 고정**: 설정 → 창 고정 — Ashley 창을 다른 "
                "창들 위에 유지."
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
