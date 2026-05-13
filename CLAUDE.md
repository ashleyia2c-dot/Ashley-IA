# CLAUDE.md

> **Nota para Claude**: este archivo describe el "qué" técnico de cada módulo. Para "si me piden X, ¿dónde modifico?" ver [`PROJECT_MAP.md`](./PROJECT_MAP.md).
>
> **⚠ ANTES DE TOCAR EL ACTION PIPELINE** (play_music, open_app, open_url, search_web, speculative dispatch, _finalize_response): LEE [`ACTION_PIPELINE_NOTES.md`](./ACTION_PIPELINE_NOTES.md). Documenta race conditions sutiles y bugs latentes que han causado múltiples regresiones falsas (v0.19.30 → v0.19.44). Sin leerlo, alta probabilidad de iterar parches que rompen otras cosas.

Versión actual: **v0.19.50 (Vision desacoplado + meta-filter + lanzamiento solid)** — sesión 2026-05-13: pulido final pre-grabación demo + lanzamiento. 3 fixes pequeños pero críticos:
  • **v0.19.50** — **VISION ON-DEMAND**: el screenshot adjunto a cada mensaje user (line 3252 reflex_companion.py) estaba gated por `auto_actions` — bug subtle: si user activaba ⚡ Actions para play_music+click, Ashley empezaba a adjuntar screenshot a CADA msg (~+1500 tokens invisibles); si user solo activaba 👁 Vision, "mira mi pantalla" NO funcionaba porque el screenshot path estaba acoplado a Actions. Ahora `vision_enabled` controla TODOS los paths de screenshot: per-turn attachment + bg_task proactive. Capabilities block del system prompt actualizado en EN/ES/FR — "⚡ Actions (control PC)" y "👁 Vision (mirar pantalla)" descritas como capabilities SEPARADAS para que Ashley sepa decir honestamente "no veo tu pantalla, activa el botón 👁" cuando user pide "mira mi pantalla" sin Vision ON. +1 test regression.
  • **v0.19.49** — **META-COMMENT FILTER + ANTI-ACTION-REPEAT**: bugs reportados en captura del user: (1) Ashley emitió `No action tag — just confirming the launch.` en bubble visible — texto de razonamiento interno que se filtró al chat. (2) user pidió "ahora abre lol" pero Ashley emitió `[volume:set:100]` además del open_app, arrastrando una action del turno anterior sin que se pidiera. Doble defensa: (A) `parsing.clean_display` con nuevos patterns para "no action tag", "just confirming", "sin tag de acción", "pas de tag d'action" — trailing-only regex para no romper diálogo natural mid-frase; (B) prompts × 7 idiomas con regla "NO repitas actions del turno anterior" + "NO escribas meta-comentarios" con ejemplos concretos. +21 tests regression en `test_v0_19_49_meta_filter.py`.
  • **v0.19.48** — **VISION TOGGLE SEPARADO**: descubierto vía análisis del historial real del user: 52% de calls a Grok eran INVISIBLES (10 vision + 6 followup en 11 msgs user). Causa: `discovery_bg_task` corría screen awareness cada 10min con screenshot adjunto cuando `auto_actions=ON` — el user activaba ⚡ Actions para play_music+click sin saber que también acoplaba ~$0.05-0.15/día extra en LLM calls invisibles. Fix: nuevo state `vision_enabled: bool = False` + `toggle_vision_enabled()` + bg_task usa `self.vision_enabled` (no `self.auto_actions`). Botón **👁 (eye) en portrait overlay** reemplaza el focus mode duplicado (focus sigue en el header). Tooltip i18n × 7 idiomas con AVISO del coste extra. Sección manual `vision` × 7 idiomas con cobertura completa: cómo activar, qué hace, coste transparente, privacidad. Achievement "She Sees" actualizado para requerir vision (no actions). +28 tests regression en `test_v0_19_48_vision_toggle.py`. **Reducción de coste API: ~75% si Vision OFF (~$0.20/día → ~$0.05/día)**.

Versión histórica: **v0.19.47 (Smart Ashley — discovery + disambiguation + suggestions)** — sesión 2026-05-12: Ashley necesita "mirar antes de saltar" para no equivocarse al abrir/cerrar apps. 3 features:
  • **v0.19.47** — **APP DISCOVERY UNIVERSAL**: nuevo `discover_installed_apps(max_total=80)` usa `Get-StartApps` de PowerShell como método primario — la API oficial de Windows que devuelve TODAS las apps lanzables incluyendo UWP/Microsoft Store (Calculadora, Cámara, ChatGPT, Claude), apps clásicas con .exe paths, OneDrive Desktop redirigido, y web apps de Edge. Names en el IDIOMA del SO automáticamente — i18n hecho por Windows, no por nosotros (cero regex multi-idioma frágiles). ~1.2s primera vez, cacheado 5min. Las apps que matchean APP_MAP/URL_APPS van PRIORITIZADAS (Word/Excel/Discord/Steam siempre salen aunque cap sea bajo). Fallback a parsing manual de .lnk (`_discover_via_lnk_walk`) si PowerShell falla — combinación funciona en Win 10/11 cualquier idioma cualquier setup. NO filtra uninstallers/about/help por regex — confiamos en el LLM para hacerlo semánticamente. Cacheado 5 min. Inyectado en `get_system_state` con instrucción "IGNORA las que sean uninstaller/desinstalar/about/help — son tools auxiliares". Total ~80 apps × ~25 chars = ~280 tokens en su contexto. **DISAMBIGUATION EN close_browser_tab Y close_window**: si `find_tabs_matching(hint)` devuelve >1 → NO cierra ninguno, devuelve la lista de tabs/windows con sus títulos + URLs/procesos para que Ashley sea más específica. Bug confirmado: pidió "cierra youtube" con 3 tabs YouTube → cerraba las 3 incluyendo el video de Warcraft que el user estaba viendo. Excepción: hint exact match a APP_MAP (ej. "discord", "notepad") sigue cerrando todas las instancias (intent claro). **SUGGESTIONS EN open_app FAILURE**: cuando los 7 paths fallan, llama a `collect_app_suggestions(hint, top_n=3)` que combina (1) `score_shortcut_name` para exact/prefix/substring + (2) `_fuzzy_score` FZF-style con densidad + word-start bonus para typos/acronyms. Ejemplo: "telegrm" (typo) → sugiere "Telegram". "vscode" → "Visual Studio Code" (vía word-start match). Mensaje localizado `open_not_found_suggestions` × 7 idiomas. **Tests**: +28 regression en `test_v0_19_47_smart_ashley.py` (discovery + cache + lnk filter + fuzzy scoring + disambiguation + suggestions + i18n parity). 1695 pasando (1667 antes).

Versión histórica: **v0.19.46 (CDP PUT + click verification + chain sequencing)** — sesión de debug en vivo descubrió la causa raíz REAL de toda la lentitud + bugs de chain con `play_music + click:like`:
  • **v0.19.46** — **CRITICAL CDP FIX**: Chromium 130+ (Opera GX 130, Chrome 146, Edge reciente, etc.) cambió `/json/new` de aceptar GET a EXIGIR PUT por CSRF. El error literal del browser: "Using unsafe HTTP verb GET to invoke /json/new. This action supports only PUT verb. (HTTP 405)". Nuestro `browser_cdp.new_tab()` usaba GET → siempre fallaba → caía al poll de 10s → fallback optimista mentiroso → wait_then clickeaba la tab vieja del user. Verificado experimentalmente con curl PUT (200 OK + tab abierta en 50ms) vs GET (405 instantáneo). Fix: `urllib.request.Request(endpoint, method="PUT")` en `new_tab()`. **YOUTUBE 2025 SELECTORS**: el wrapping del botón Like cambió a `segmented-like-dislike-button-view-model like-button-view-model button`. Los selectores viejos apuntaban a la primera instancia (oculta). **querySelectorAll + filter visible**: antes `querySelector` daba sólo el primer match aunque estuviera oculto. Probado experimentalmente: YouTube tiene 3 instancias de `like-button-view-model`, sólo la #1 es visible. **POST-CLICK VERIFICATION via aria-pressed**: `click_by_text` ahora lee aria-pressed antes/después del click para canonicals toggleables (like/dislike/subscribe/play/pause). Si no cambió → success=False (Ashley se disculpa en personaje). Antes reportaba success=True por encontrar y clickear ALGO, incluso un `@studylikenat` (canal con "like" en el nombre). Nuevo `_TOGGLE_CANONICALS` set + `_is_toggle_canonical()` helper. **ARIA MATCH PRIORITY**: sinónimos cortos (≤4 chars como "like") requieren whole-word match (regex `\b`). Sinónimos largos pueden ser substring. **Sinónimos reordenados**: frases largas/específicas primero (`indica que te gusta` antes que `me gusta` antes que `like`). **NO SPECULATIVE SI WAIT_THEN EN CHAIN**: `_maybe_dispatch_speculative` early-return si alguna acción es `wait_then`. wait_then existe para sequenciar pero speculative dispatch lanza threads en paralelo → wait_then despierta antes que play_music termine → click contra tab vieja. Verificado en logs del user (speculative=2 cuando debía ser 0). Trade-off: pierdes ~3-5s de TTFT speedup, pero la chain funciona DE VERDAD. **PROMPTS 7 IDIOMAS**: nueva regla "NUNCA uses open_url con URL youtube.com para música" con ejemplo del bug real (`open_url:https://www.youtube.com/watch?v=eVli-tstM5E + wait_then:5:click:like`). Bug real: Ashley emitía `open_url` en vez de `play_music` para canciones — sin dedupe ni tracking de tab. **Tests**: +19 regression en `test_v0_19_46_fixes.py` (PUT method, YT 2025 selectors, toggle canonicals, sinónimos ordenados, JS word boundary, querySelectorAll, speculative skip, prompts 7 idiomas). 1667 pasando.

Versión histórica: **v0.19.24 (audit completo — security/error-handling/i18n masivo)** — limpieza enorme tras audit exhaustivo de 4 áreas:
  • **v0.19.24** — **SECURITY**: (C1) `/api/export/data` ahora requiere `_is_truly_localhost` (antes SIN auth + accesible vía Cloudflare tunnel → cualquiera con la URL del tunnel descargaba TODO el historial); (C2) detección Cloudflare tunnel via headers `cf-connecting-ip`/`cf-ray`/`x-forwarded-for` para bloquear bypass de localhost-only; (H1) rate-limit por-IP de failed auth attempts (antes wrong token = unlimited probing); (H2) cap de 4KB en mensaje móvil para evitar drain de cuota xAI; (M1) ElevenLabs key fuera del DOM (era plaintext en `data-el-key` aunque JS no la usaba — leak gratis); (M2) `_terminate_process_by_name` requiere min 4 chars + exact/prefix match (antes substring con 1 char mataba todo proceso con ese char); (M3) tunnel URL file con mode 0o600; (M4) timeouts en subprocess.run de PowerShell (volumen, focus_window) para evitar hangs eternos. **ERROR HANDLING**: (E1) `save_history` envuelto en try/except OSError (antes disco lleno → "falló con Grok" misleading + msg perdido); (E2) `_handle_grok_error` usa logger en vez de print + sanitiza str(e) con regex para no leakear API keys al chat; (E3) `extract_facts` distingue JSONDecodeError (silencioso OK) de Exception general (loguea); (E4) `int(imp)` con guard contra corruption (antes "alta" en vez de número crasheaba TODO mensaje); (E5) `_parse_dt` logea warning cuando timestamp corrupto (antes reminder NUNCA disparaba sin warning); (E6) `play_music` con `resolved_ok` flag — distingue éxito real vs fallback a search results; (E7) discovery_bg_task usa logger en vez de print; (E8) `mobile_pair_error` mensaje genérico i18n en vez de leakear str(_e). **i18n MASIVO**: nuevo dict `_ACTION_MSGS` en actions.py con templates × 7 idiomas para 30+ keys (open_app/search_web/play_music/control_volume/focus_window/type_text/hotkey/key_press/close_window/close_browser_tab/reminders/important/goals/tastes/list_windows). Funciones aceptan `lang` propagado desde `execute_action`. `license._friendly_error` traducido a 7 idiomas. `api_routes` whisper status devuelve `messages` dict con 7 idiomas. `ashley_voice.js _i18n` extendido con 3er param `extras` para idiomas adicionales. `ashley_fx.js` update notifier con `_UPDATE_MSGS` × 7. **RESOURCE**: `_send_keys_subprocess` y `_find_and_close_tab_subprocess` con cleanup en TimeoutExpired (kill + close pipes en finally) — antes leak progresivo de FDs y zombies Python. **Tests**: +25 regression en `test_v0_19_24_fixes.py` (security + error handling + i18n + resource). 1285 pasando.

Versión histórica: **v0.19.23 (audit post-launch — privacy + delete + flicker)** — fixes de bugs encontrados al usar v0.19.22 en vivo:
  • **v0.19.23** — **PRIVACY FIX CRÍTICO**: `read_page` action leakeaba el contenido completo de la página (toda la HTML scraped) al user en el chat como mensaje system_result. Ahora devuelve `ui_result` (corto, "📄 Página leída") + `result` (completo, solo Ashley lo ve en su contexto). Migración `ensure_ids` añade `ui_content: ""` a mensajes legacy para evitar undefined en JS lookup. **DELETE MESSAGE FIX CRÍTICO**: `delete_message` llamaba a `save_history()` que hace MERGE con el archivo en disco para preservar mensajes del móvil — pero ese merge RE-AÑADÍA el msg que acabábamos de borrar (estaba en disco, no en self.messages → merge lo trataba como "msg nuevo del móvil"). Ahora `delete_message` escribe directo con `save_json(CHAT_FILE, ...)`. Trade-off: si el móvil escribió entre el último save y el delete, ese msg móvil se pierde. **ANTI-FLICKER OBSERVER**: rx.foreach usa index como React key → al borrar un msg, todos los siguientes se re-indexan → React los re-monta → la animación `.msg-enter` se re-dispara en TODOS → "todos los mensajes parpadean". Fix: `data-msg-id={m["id"]}` en el wrapper + observer JS en `ashley_fx.js::_initMsgEnterDedupe()` que mantiene un Set de IDs ya animados y quita `.msg-enter` de re-mounts. **i18n**: 5 strings hardcoded EN ("⚖ Legal & Data", "Privacy Policy", "Terms of Service", backup desc, "Export all my data") movidos a i18n.UI con traducciones nativas a los 7 idiomas (194 keys × 7, paridad). +11 tests regression en `test_v0_19_23_fixes.py`.

Versión histórica: **v0.19.22 (manual de usuario reescrito + 7 idiomas)** — fixes acumulados durante el ciclo de grabación demo + lanzamiento Lemon Squeezy:
  • **v0.19.22** — manual de usuario completo en `manual_content.py` (~2900 líneas) con 16 secciones por idioma cubriendo TODAS las features v0.18-0.19: chat, voice (4 TTS engines + STT + wake word + speak now), system actions, modern browser mode (CDP), memory, reminders, **goals & check-ins** (NEW), **bond/affection/days together/birthday** (NEW), discovery, **Ashley 3D VRM** (NEW), **mobile companion** (NEW), LLM provider, privacy + RGPD export (NEW), tokens & costs, **license & refund** (NEW), shortcuts. **Bug crítico arreglado**: `manual_dialog` solo soportaba en/es/fr — los 4 idiomas nuevos (ja/de/ru/ko) veían EN aunque el contenido EXISTÍA. Plus restyle al theme warm boutique noir (era hot pink #ff9aee → ámbar #d4a373 + glass-morphism + serif para el título). Datos viejos arreglados: VAD silence 4s→2s, header icons matchean la barra real (💎🧠📰⚡📱⚙️ no 📋⭐📔🌍🗣), path correcto `%APPDATA%\\Ashley\\data\\`.
  • **v0.19.21** — fix botón ✨ (initiative) que flasheaba bubble vacía al inicio del chat (sin mensajes user). Gate al top de `send_initiative`: `if not any(m.get("role") == "user" for m in self.messages): return`. +3 tests regression en `test_initiative_gates.py` (verifican que el gate va antes de `is_thinking` y antes del primer `yield`).
  • **v0.19.20** — fix CRÍTICO `UnboundLocalError 'params'` en `parsing.extract_action()`: el branch fallthrough faltaba el `else: params = rest.split(":") if rest else []`. Crasheaba TODAS las acciones que no eran `play_youtube/save_taste/remind/add_important/done_important/save_date/save_goal/check_in_goal/complete_goal` (volume_up/down/set, open_app, close_window, screenshot, hotkey, press_key, focus_window). +10 tests regression en `test_parsing.py::TestExtractActionFallthroughBranch`. Plus 3 keys i18n nuevas × 7 idiomas: `cdp_setup_in_progress`, `cdp_setup_in_progress_off`, `wake_word_listening` (antes hardcoded ES "Configurando accesos..." y "OK escuchando").
  • **v0.19.19** — `_is_writable_dir()` filter en `browser_setup._shortcut_locations()` para que el toggle CDP no reporte "(1 fallaron)" por shortcuts en ProgramData (necesitan admin).
  • **v0.19.18** — license key input migrado de `rx.input` (Radix TextField) a `rx.el.input` (raw HTML) para que el styling custom no fuera overrideado por Radix CSS (texto ilegible).
  • **v0.19.17/16/15/14/13** — installer fixes: NSIS `$_` escape, `oneClick: true` (rollback de `false` que cerraba wizard silencioso), bypass del `tunnel()` del package npm cloudflared con `spawn()` directo, CleanupOrphanInstallDir + CleanupStaleUpdaterState macros.

Tests: 1249 (+13 vs v0.19.0). Cache prefix preservado al 100% en los 7 idiomas.

Versión histórica: **v0.19.0 (Ashley en 3D + 4 idiomas nuevos)** — el salto visual + ampliación de mercado más grande de la app:
  • **Ashley en 3D (VRM)**: nuevo `assets/ashley_3d_widget.html` con three-vrm 3.x + MToon. Carga `assets/3d/ashley.vrm` en un iframe que sobrevive re-renders de React. Bridge IIFE (`ashley_3d_bridge.js`) crea el iframe vía JS en un mount div estático para no perder el WebGL context (ni recargar 47MB) en cada State change. Features: poses (wave/tsundere/coolFingers), parpadeo + saccades de ojos, head bob mientras habla, lipsync REAL via Web Audio API (analiza el audio TTS de ElevenLabs/Kokoro/VoiceVox en tiempo real), expression boost al final de cada frase, proximity smile cuando el cursor se acerca. Performance: amp 25fps + cursor 20fps + render 30fps + bbox cacheado 500ms para evitar layout thrashing durante streaming.
  • **4 idiomas nuevos** (ja, de, ru, ko): `prompts_ja.py` (991 líneas, ご主人 + tsundere refinada), `prompts_de.py` (1163, "Chef" + verschmitzt), `prompts_ru.py` (1066, «шеф» + ironía RU), `prompts_ko.py` (955, 오빠 + 반말 + K-drama lead). Total `i18n.py` ahora 2403 líneas con UI/ACT_DESC/KEY_LABELS/TIME_CTX para 7 idiomas (paridad de 186/31/7/26 keys verificada por test).
  • **TTS no lee roleplay** (v0.18.4): nuevo `_extractSpeechText` walker DOM que SALTA `<em>`/`<i>` (donde markdown deposita `*acción*`/`_acción_`). Antes el regex no matcheaba porque markdown ya había convertido los marcadores en tags HTML.
  • **Bug fix burbuja vacía** (v0.18.5): la "agentic continuation" ya NO se dispara para acciones safe/conversacionales (check_in_goal, save_taste, etc.). Plus guarda defensiva en los 3 paths que appendean assistant message tras strippear tags.

Tests: 1236 (+295 vs v0.18.0). Cache prefix preservado al 100% en los 7 idiomas. Coste extra por mensaje (3D + nuevos idiomas): 0 tokens (el 3D vive entero en el cliente).

Hitos recientes:
- v0.18.6 — i18n.py 2403 líneas, 7 idiomas con paridad verificada por test.
- v0.18.5 — fix bubble vacía después de [check_in_goal:...] u otra safe action.
- v0.18.4 — TTS DOM walker para no leer *roleplay* italicizado por markdown.
- v0.18.3 — TTS bridge para 3D Ashley (CustomEvents `ashley:ttsStart`/`ttsEnd`).
- v0.18.0 — Tier 1 vínculo: días juntos + cumpleaños + goals tracking.
- v0.17.4 — prompts sin ejemplos meta + filtro post-stream ampliado con catch-all.

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
