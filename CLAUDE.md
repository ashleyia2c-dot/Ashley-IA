# CLAUDE.md

> **Nota para Claude**: este archivo describe el "qué" técnico de cada módulo. Para "si me piden X, ¿dónde modifico?" ver [`PROJECT_MAP.md`](./PROJECT_MAP.md).

Versión actual: **v0.17.4** (prompts sin ejemplos específicos de meta-frases prohibidas — Ashley los copiaba verbatim. Filtro post-stream ampliado con catch-all genérico para meta-comentarios alucinados tipo "No actions.", "Conversación fluida." que se le escapan al LLM al final de las respuestas).

Hitos recientes:
- v0.17.3 — servidor HTTP embebido reemplaza sirv → fast-path en producción → arranque cae de ~15s a ~4-6s. Port detection optimizado. `done_important` idempotente.
- v0.17.2 — boutique noir UI fluida, multi-provider onboarding, scroll mantequilla, mood images precargadas, settings instant-open, Ashley más sentimental.

## Commands

```bash
# Dev server (Electron wrapper — usa puertos dinamicos)
ashley-electron.bat          # en el escritorio

# Dev server (browser directo — puertos en rxconfig.py)
cd reflex-companion && venv\Scripts\activate && reflex run

# Tests (784 tests, ~6s)
venv\Scripts\python.exe -m pytest tests/ -v

# Build installer (.exe) — prebuild-frontend se ejecuta automático antes
cd electron && npm run build

# Diagnóstico de latencia LLM (mide TTFT real desde el PC al endpoint)
venv\Scripts\python.exe tools/diagnose_latency.py

# Simulador de tokens / coste por 10 mensajes
venv\Scripts\python.exe tools/simulate_token_usage.py
```

### Frontend build invariant (v0.13.4) + fast-path en producción (v0.17.3)

Reflex compila los componentes Python a JSX que vive en `.web/build/client/`. Electron tiene dos caminos de arranque:
- **Fast-path** (~3-5s tras v0.17.3): backend Python (--backend-only) + servidor HTTP embebido en main.js sirviendo `.web/build/client/`. Antes solo en dev — ahora **también en producción** desde v0.17.3.
- **Slow-path** (~14s): llama a `reflex run --env prod` que recompila el frontend Next.js.

El `main.js` decide automáticamente comparando **mtime de cada `.py` en `reflex_companion/` + cada asset en `assets/`** contra `mtime` de `.web/build/client/index.html`. Si cualquier fuente es más nueva → slow-path. Invariante: **el user (dev o final) NUNCA ve una UI stale respecto al código**.

En el installer, `electron/prebuild.js` corre antes de `electron-builder` y hace `reflex export --frontend-only` forzado. Si falla, el installer NO se genera (fail-loud).

**Embedded frontend server (v0.17.3):**
- `_startEmbeddedFrontendServer()` en main.js sustituye sirv-cli.
- Es un `http.createServer` que sirve `.web/build/client/` con MIME types correctos, SPA fallback, y Cache-Control inmutable para `/assets/*`.
- Vive en el proceso principal de Electron → cero subprocesos, cero spawn overhead, cero cuelgues silenciosos como pasaba con sirv en producción (v0.13.2 bug).
- `waitForReflex()` ahora pollea `/api/whisper/status` del backend cuando el embedded server está activo (porque el frontend embedded responde instantáneo y no es señal útil de readiness).
- Tests guard: `tests/test_startup_optimization.py` (16 tests).

## Architecture

**Reflex** (Python full-stack) desktop companion wrapped in **Electron**. Reflex compiles Python → React frontend + Python backend. Electron provides native window, system permissions, and packaging.

### Two servers at runtime
- **Frontend** (Next.js): serves UI on port ~17300
- **Backend** (Starlette/Python): serves WebSocket + custom API on port ~17800+
- Ports are **dynamic** — Electron finds free ports at startup (avoids Hyper-V conflicts)

### Key Files

| File | Lines | Role |
|------|-------|------|
| `reflex_companion/reflex_companion.py` | ~6,131 | State class, `index()` page, app setup |
| `reflex_companion/components.py` | ~1,245 | UI components (chat header, portrait panel, dialogs) |
| `reflex_companion/styles.py` | ~1,576 | CSS animations, glassmorphism, boutique noir theme |
| `reflex_companion/parsing.py` | ~295 | Tag extraction (mood, action), safe actions list |
| `reflex_companion/api_routes.py` | ~499 | Starlette endpoints: `/api/transcribe`, `/api/tts`, `/api/whisper/status`, `/api/wake_word/*`, `/api/shutdown` |
| `reflex_companion/actions.py` | ~2,382 | Windows system actions (apps, volume, tabs, keyboard) + shell injection guards |
| `reflex_companion/grok_client.py` | ~467 | xAI Grok API streaming + cliente cacheado + retry |
| `reflex_companion/llm_provider.py` | ~399 | Multi-provider dispatch (xAI / OpenRouter / Ollama) + cliente cacheado |
| `reflex_companion/prompts.py` | ~162 | Language dispatcher (→ prompts_en.py / prompts_es.py / prompts_fr.py) |
| `reflex_companion/prompts_en.py` | ~967 | Ashley's English personality prompt (cache-friendly order) |
| `reflex_companion/prompts_es.py` | ~957 | Ashley's Spanish personality prompt |
| `reflex_companion/prompts_fr.py` | ~987 | Ashley's French personality prompt |
| `reflex_companion/i18n.py` | ~1,071 | UI translations, voice config persistence |
| `reflex_companion/memory.py` | ~277 | JSON persistence (chat, facts, diary) |
| `reflex_companion/mental_state.py` | ~601 | Mood axes + preoccupation regen + initiative counter |
| `reflex_companion/context_compression.py` | ~294 | History compression cache (regen cada 15 msgs) |
| `reflex_companion/reminders.py` | ~298 | Reminders + important items |
| `reflex_companion/tastes.py` | ~66 | User taste preferences + discovery timing |
| `reflex_companion/whisper_stt.py` | ~407 | Local Whisper STT + auto-warmup + cache detection |
| `reflex_companion/wake_word.py` | ~366 | openwakeword detector (sounddevice + VAD silero) |
| `reflex_companion/wake_word_lifecycle.py` | ~175 | Singleton thread-safe del detector |
| `reflex_companion/config.py` | ~162 | Model names, file paths, colors, thresholds |
| `electron/main.js` | ~1,439 | Electron wrapper (splash, port mgmt, permisos, graceful shutdown) |
| `assets/ashley_voice.js` | ~876 | TTS (Web Speech / ElevenLabs) + STT (MediaRecorder + Whisper) + VAD |
| `assets/ashley_fx.js` | ~1,458 | Starfield, sounds, optimistic UI, image paste, MutationObservers |

### Tools (no se incluyen en el build, solo dev)

- `tools/diagnose_latency.py` — mide TTFT real desde tu PC a xAI. Útil para detectar si lentitud viene del modelo, network o Python.
- `tools/simulate_token_usage.py` — simula tokens consumidos en 10 mensajes y calcula coste por modelo en escenarios light/medium/heavy.

### Environment Variables

| Variable | Set by | Purpose |
|----------|--------|---------|
| `XAI_API_KEY` | `.env` or Electron `safeStorage` | Grok API authentication |
| `ASHLEY_DATA_DIR` | Electron `main.js` | Data isolation (`%APPDATA%\Ashley\data\`) |
| `ASHLEY_BACKEND_PORT` | Electron `main.js` | Backend port for JS → Python API calls |
| `ASHLEY_WHISPER_MODEL` | optional override | tiny/base/small/medium/large-v3 (default `small`) |
| `ASHLEY_WHISPER_DEVICE` | optional override | cpu/cuda |

### Data Files (in `ASHLEY_DATA_DIR` o project root)

| File | Content |
|------|---------|
| `historial_ashley.json` | Chat history (max 50 messages) |
| `hechos_ashley.json` | Extracted user facts (max 300) |
| `diario_ashley.json` | Auto-generated diary entries |
| `recordatorios_ashley.json` | Scheduled reminders |
| `importantes_ashley.json` | Important items list |
| `gustos_ashley.json` | User taste preferences |
| `discovery_ashley.json` | Last discovery run timestamp |
| `language.json` | Language preference (en/es/fr) |
| `voice.json` | Voice config (TTS, ElevenLabs key, voice_id, voice_mode, llm_provider, llm_model) |
| `mental_state_ashley.json` | Mood axes + preoccupation + last_update |
| `models/whisper/models--Systran--faster-whisper-{size}-direct/` | Whisper model files (sin symlinks, persiste entre runs) |

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
- `[affection:+1]` — delta of affection (-2 to +2)

### Voice System

- **TTS**: Web Speech (free, robotic) o ElevenLabs (premium, vía `/api/tts` proxy)
- **STT**: MediaRecorder → `/api/transcribe` → faster-whisper (local, modelo `small`, ~245MB)
- **VAD**: Auto-stop recording después de **2s** de silencio (Web Audio API). v0.16.13 — bajado de 3s para envío más reactivo.
- **Wake word**: openwakeword (`ashley.onnx`) + sounddevice + silero VAD. `consecutive_required=2` evita falsos positivos de estornudos/soplidos.
- **Whisper auto-warmup**: el modelo se pre-carga en background al iniciar la app (paralelo con preoccupation/compress regen). La primera vez que el user activa voz, ya está en RAM → cero banner "cargando".

### Performance — Prompt caching y LLM client cache (v0.16.13)

**System prompt order (cache-friendly)**:
- TOP: secciones estables (personalidad, reglas, ejemplos hardcoded ~9.5K tokens). Se cachea.
- BOTTOM: secciones dinámicas (`{state_section}{tastes_section}{reminders_section}{important_section}{mental_section}{time_section}`, ~1.5K tokens). No se cachea.
- TIME al final del todo (cambia cada segundo). Antes iba arriba → cache hit ratio 12% medido en xAI dashboard. Ahora prefix idéntico al 99.9% → esperado >85% cache hit.

**LLM client cache**:
- `grok_client.get_xai_client()` — singleton thread-safe del `xai_sdk.Client`. Reutiliza la conexión HTTP/2 entre llamadas. Antes cada llamada creaba cliente nuevo → handshake TCP+TLS de ~300-500ms × 3-4 llamadas/mensaje.
- `llm_provider._openai_client()` — mismo patrón para OpenRouter/Ollama. Invalida cache si cambia api_key/base_url.
- Tests guard: `tests/test_llm_client_cache.py` bloquea regresión a instanciaciones directas.

**Modelo default**:
- `GROK_MODEL = "grok-4-1-fast-non-reasoning"` (era `-reasoning`). TTFT mide 0.6s vs 3.5s. Mismo precio, mismo provider, vision incluida. Ver `tools/diagnose_latency.py`.

**Pre-warm en background**:
- `_prewarm_session_state` paraleliza con `asyncio.gather`: preoccupation regen + compress_history + whisper model load. Las 3 tareas independientes corren mientras el user explora la UI.

**Constantes**:
- `STREAM_CHUNK_SIZE = 2` (v0.16.14 — bajado de 4 a 2 tras revisión visual; balance entre fluidez y throughput)
- `REGEN_AFTER_NEW_MSGS = 15` (compress regen menos frecuente)
- `PREOCCUPATION_TTL_MINUTES = 90` (preoccupation regen menos frecuente)

### Optimistic UI (v0.16.13)

Cuando el user pulsa enter, el bubble aparece al instante con sonido — sin esperar al backend.

**Flujo simple**:
1. JS añade fake bubble + `playSend()` al final de `chat_messages`.
2. React monta el real ms después.
3. Observer detecta delta>=1 user-msg → llama `_purgeOptimistic()` → borra el fake.
4. CSS `.user-msg.msg-enter { animation: none }` evita slide-up del real → swap invisible.
5. CSS reset `margin: 0` para `<p>/<h*>/<li>` en `.bubble-*` iguala dimensiones fake/real.

**Tests guard**: `tests/test_optimistic_ui_assets.py` bloquea regresión a la lógica compleja anterior (`_enforceOptimistic`, `.user-msg-shown`, etc.).

### Graceful shutdown (v0.16.13)

Al cerrar la app, Electron llama `/api/shutdown` antes de SIGKILL para que Python:
1. Pare el `wake_word_detector` → libera el handle del mic (PortAudio).
2. Llame `os._exit(0)`.

Sin esto, `taskkill /F` dejaba el mic colgado hasta reboot ("apps usando tu mic" permanente). Ver `electron/main.js` → `gracefulShutdownBackend()` cableado en `window-all-closed`, `before-quit`, `SIGINT`, `SIGTERM`.

### Security — Shell injection guards

`actions.py` tiene `_is_shell_safe()` y `_is_valid_proc_name()` que bloquean metacaracteres de shell (`& | ; < > $ \` ' " \n`) antes de pasar params a `subprocess`/PowerShell. Defensa contra prompt injection indirecta (LLM engañado vía web_search/news scrape emite tags maliciosas).

Aplicado en: `open_app`, `close_window`, `focus_window`, `_find_window_title_by_hint`. El fallback `subprocess.Popen(exe, shell=True)` en `open_app` fue eliminado.

Manual del user explica qué caracteres están bloqueados y por qué (sección `actions` en `manual_content.py` para EN/ES/FR).

### Tests

784 tests organizados por área:

- `test_optimistic_ui_assets.py` (15) — CSS animation:none, margin reset, observer behavior, no regresión a lógica compleja.
- `test_llm_client_cache.py` (15) — Cache singleton, thread-safe, invalidación.
- `test_prompt_cache_friendly.py` (10) — Cache prefix >=95% en es/en/fr.
- `test_lifecycle_and_voice_button.py` (12) — TTS toggle UI, /api/shutdown, gracefulShutdownBackend.
- `test_shell_injection_guards.py` (21) — Sanitización contra payloads de inyección.
- `test_vad_silence_threshold.py` (2) — VAD entre 1-2s.
- `test_whisper_cache_detection.py` (7) — `is_cached_on_disk()` + api_routes distingue loading/downloading.
- `test_message_merging.py` (~20) — Fusión de user-user consecutivos para xAI/OpenRouter.
- `test_shell_injection_guards.py` — Anti-injection guards.
- `test_news.py`, `test_memory.py`, `test_reminders.py`, `test_tastes.py`, `test_achievements.py`, etc.

### i18n

- UI strings: `i18n.py` → `UI["en"]` / `UI["es"]` / `UI["fr"]`
- Personality: `prompts_en.py` / `prompts_es.py` / `prompts_fr.py` (separate implementations)
- Action descriptions: `i18n.ACT_DESC["en/es/fr"]`
- Time context: `i18n.TIME_CTX["en/es/fr"]`

### Electron Specifics

- **Auto-kill zombies**: `killProcessesOnPort()` + `killStrayAshleyProcesses()` antes del startup
- **Dynamic ports**: `findFreePort()` via TCP connect test
- **Auto-restart**: hasta 5 retries si Reflex crashea
- **Microphone**: permission auto-granted via `session.setPermissionRequestHandler`
- **DevTools**: blocked in production, enabled with `--dev` flag
- **API key**: encrypted with Windows DPAPI via `electron.safeStorage`
- **Graceful shutdown**: POST a `/api/shutdown` antes de `taskkill /F` para liberar el mic
