# CLAUDE.md

## Commands

```bash
# Dev server (Electron wrapper — usa puertos dinamicos)
ashley-electron.bat          # en el escritorio

# Dev server (browser directo — puertos en rxconfig.py)
cd reflex-companion && venv\Scripts\activate && reflex run

# Tests (162 tests, <1s)
venv\Scripts\python.exe -m pytest tests/ -v

# Build installer (.exe)
cd electron && npm run build
```

## Architecture

**Reflex** (Python full-stack) desktop companion wrapped in **Electron**. Reflex compiles Python → React frontend + Python backend. Electron provides native window, system permissions, and packaging.

### Two servers at runtime
- **Frontend** (Next.js): serves UI on port ~17300
- **Backend** (Starlette/Python): serves WebSocket + custom API on port ~17800+
- Ports are **dynamic** — Electron finds free ports at startup (avoids Hyper-V conflicts)

### Key Files

| File | Lines | Role |
|------|-------|------|
| `reflex_companion/reflex_companion.py` | ~1,737 | State class, `index()` page, app setup |
| `reflex_companion/components.py` | ~422 | UI components (messages, pills, portrait, dialogs) |
| `reflex_companion/styles.py` | ~177 | CSS animations and glassmorphism |
| `reflex_companion/parsing.py` | ~138 | Tag extraction (mood, action), safe actions list |
| `reflex_companion/api_routes.py` | ~149 | Starlette endpoints: `/api/transcribe`, `/api/tts`, `/api/whisper/status` |
| `reflex_companion/actions.py` | ~1,857 | Windows system actions (apps, volume, tabs, keyboard) |
| `reflex_companion/grok_client.py` | ~135 | xAI Grok API streaming + fallback detection |
| `reflex_companion/prompts.py` | ~42 | Language dispatcher (→ prompts_en.py / prompts_es.py) |
| `reflex_companion/prompts_en.py` | ~311 | Ashley's English personality prompt |
| `reflex_companion/prompts_es.py` | ~301 | Ashley's Spanish personality prompt |
| `reflex_companion/i18n.py` | ~411 | UI translations, voice config persistence |
| `reflex_companion/memory.py` | ~178 | JSON persistence (chat, facts, diary) |
| `reflex_companion/reminders.py` | ~168 | Reminders + important items |
| `reflex_companion/tastes.py` | ~64 | User taste preferences + discovery timing |
| `reflex_companion/whisper_stt.py` | ~137 | Local Whisper (faster-whisper) for speech-to-text |
| `reflex_companion/config.py` | ~85 | Model names, file paths, colors, thresholds |
| `electron/main.js` | ~552 | Electron wrapper (splash, port management, permissions) |
| `assets/ashley_voice.js` | ~687 | TTS (Web Speech / ElevenLabs) + STT (MediaRecorder + Whisper) |
| `assets/ashley_fx.js` | ~260 | Starfield, sounds, auto-scroll, visibility reload |

### Environment Variables

| Variable | Set by | Purpose |
|----------|--------|---------|
| `XAI_API_KEY` | `.env` or Electron `safeStorage` | Grok API authentication |
| `ASHLEY_DATA_DIR` | Electron `main.js` | Data isolation (`%APPDATA%\ashley\data\`) |
| `ASHLEY_BACKEND_PORT` | Electron `main.js` | Backend port for JS → Python API calls |

### Data Files (in `ASHLEY_DATA_DIR` or project root)

| File | Content |
|------|---------|
| `historial_ashley.json` | Chat history (max 50 messages) |
| `hechos_ashley.json` | Extracted user facts (max 300) |
| `diario_ashley.json` | Auto-generated diary entries |
| `recordatorios_ashley.json` | Scheduled reminders |
| `importantes_ashley.json` | Important items list |
| `gustos_ashley.json` | User taste preferences |
| `discovery_ashley.json` | Last discovery run timestamp |
| `language.json` | Language preference (en/es) |
| `voice.json` | Voice config (TTS enabled, ElevenLabs key, voice_id, voice_mode) |

### State Helpers (DRY patterns)

The State class uses 3 extracted helpers to avoid duplication:
- `_build_prompt_context(user_message)` → dict of all prompt kwargs
- `_execute_and_record_action(action_dict)` → execute + record + save
- `_streaming_loop(generator)` → chunk accumulation + UI updates

### Safe Actions (execute without ⚡ toggle)

`save_taste`, `remind`, `add_important`, `done_important` execute always. System actions (`open_app`, `close_window`, etc.) require the ⚡ Actions toggle.

### Tag Protocol

Ashley embeds tags in responses:
- `[mood:excited]` — 7 moods: excited, embarrassed, tsundere, soft, surprised, proud, default
- `[action:open_app:notepad]` — 15+ action types parsed by `parsing.extract_action()`

### Voice System

- **TTS**: Web Speech (free, robotic) or ElevenLabs (premium, via `/api/tts` proxy)
- **STT**: MediaRecorder → `/api/transcribe` → faster-whisper (local, model `small`, ~245MB)
- **VAD**: Auto-stop recording after 4s silence (Web Audio API)
- **Natural mode**: `🗣 Natural` pill removes `*gestures*` from responses for cleaner audio

### i18n

- UI strings: `i18n.py` → `UI["en"]` / `UI["es"]`
- Personality: `prompts_en.py` / `prompts_es.py` (separate implementations, not translations)
- Action descriptions: `i18n.ACT_DESC["en"]` / `["es"]`
- Time context: `i18n.TIME_CTX["en"]` / `["es"]`

### Electron Specifics

- **Auto-kill zombies**: `killProcessesOnPort()` before startup
- **Dynamic ports**: `findFreePort()` via TCP connect test
- **Auto-restart**: up to 5 retries if Reflex crashes
- **Microphone**: permission auto-granted via `session.setPermissionRequestHandler`
- **DevTools**: blocked in production, enabled with `--dev` flag
- **API key**: encrypted with Windows DPAPI via `electron.safeStorage`
