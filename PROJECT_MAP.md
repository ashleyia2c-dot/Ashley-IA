# PROJECT_MAP.md

> Mapa de referencia rápido para Claude. Complementa `CLAUDE.md` (que tiene el "qué" técnico).
> Este archivo responde a **"si me piden X, ¿dónde modifico?"**.
>
> Versión actual del proyecto: **v0.17.2** · Última actualización del mapa: 2026-05-02

---

## 1. Vista general del proyecto

**Ashley** es una app de escritorio Windows (Electron + Reflex/Python) — companion IA con personalidad tsundere.

- **Modelo de negocio**: €19.99 one-time, lifetime, hasta 3 PCs por licencia, sin subs.
- **BYOK** (Bring Your Own Key): el user trae su key de xAI Grok, OpenRouter, o usa Ollama 100% local gratis.
- **Privacidad**: chat history / memoria / diario encriptados en `%APPDATA%\Ashley\data\`. Sin servidores propios.
- **Multi-idioma UI + personalidad**: EN / ES / FR.
- **Repos**:
  - App: `ashleyia2c-dot/Ashley-IA` (GitHub Releases para auto-update)
  - Landing: `ashleyia2c-dot/Ashley-IA-landing` (Cloudflare Pages, en `C:\Users\Mister Squishi\Desktop\Ashley\Ashley-IA-landing\`)
- **Pago**: LemonSqueezy.

---

## 2. Directory tree (carpetas top-level)

```
reflex-companion/
├── reflex_companion/          # ← TODO el código Python (state, UI, LLM, voice, actions)
├── electron/                  # ← Wrapper Electron (main.js, preload, onboarding, updater, builder)
├── assets/                    # ← JS frontend (TTS/STT, scroll, FX) + imágenes de moods
├── tests/                     # ← pytest, 600+ tests
├── tools/                     # ← Scripts dev (latency, profiling, token sim) — NO se incluye en build
├── venv/                      # ← Virtualenv Python (incluido en el installer)
├── .web/                      # ← Build output de Reflex (Next.js compilado)
├── .github/                   # ← GitHub Actions / workflows
├── wake_word_training/        # ← Datasets/scripts para entrenar el wake word "Ashley"
├── uploaded_files/            # ← Archivos subidos por el user en runtime
├── Description of Ashley/     # ← Notas de diseño/personalidad
├── CLAUDE.md                  # ← Doc técnica para Claude (qué es cada archivo)
├── PROJECT_MAP.md             # ← Este archivo (dónde modificar para cada tarea)
├── RELEASING.md               # ← Proceso de release (versión, build, GitHub Release)
├── THIRD-PARTY-NOTICES.txt    # ← Licencias de deps (incluido en el installer)
├── rxconfig.py                # ← Config Reflex (puertos 17300/17800, plugins)
├── requirements.txt           # ← Deps Python
└── .env / .env.example        # ← XAI_API_KEY, etc. (dev only)
```

---

## 3. "Si me piden X, modifico Y" — mapa de tareas

### 🎭 Personalidad / cómo habla Ashley
| Tarea | Archivo |
|-------|---------|
| Cambiar tono, reglas, comportamiento general | `reflex_companion/prompts_en.py` + `prompts_es.py` + `prompts_fr.py` (los 3, mantener paridad) |
| Cambiar el dispatcher de idioma | `reflex_companion/prompts.py` |
| Añadir/quitar moods | `parsing.py` (lista de moods) + `reflex_companion.py` (`current_image` var) + `assets/ashley_<mood>.jpg` + `styles.py` (animación si toca) |
| Cambiar tags `[mood:...]` `[action:...]` `[affection:...]` | `parsing.py` (`extract_action`, `clean_display`, `MOOD_PATTERN`) |
| ⚠️ **No usar few-shot examples** — Ashley los copia verbatim. Solo reglas abstractas. | (regla persistente) |

### 🎙️ Voz (TTS + STT + wake word)
| Tarea | Archivo |
|-------|---------|
| Lógica TTS frontend (ElevenLabs / Web Speech / Kokoro / VoiceVox switch) | `assets/ashley_voice.js` |
| Endpoints TTS/STT backend | `reflex_companion/api_routes.py` (`/api/tts`, `/api/transcribe`) |
| Whisper local (modelo, warmup, cache) | `reflex_companion/whisper_stt.py` + `api_routes.py` (`/api/whisper/status`) |
| Wake word detector | `reflex_companion/wake_word.py` (motor) + `wake_word_lifecycle.py` (singleton) + `wake_word_bridge.py` (Reflex bridge) |
| VAD (silencio para auto-stop) | `assets/ashley_voice.js` (constante, default 2s) |
| Persistencia config voz | `reflex_companion/i18n.py` (función `voice_config_*`) |

### ⚡ Acciones del sistema (open apps, volumen, tabs, etc.)
| Tarea | Archivo |
|-------|---------|
| Añadir/modificar acción ejecutable | `reflex_companion/actions.py` (función `do_<action>`) |
| Registrar la action en parser | `reflex_companion/parsing.py` (`extract_action`) |
| Listar la action en el prompt | `prompts_<lang>.py` (sección de acciones disponibles) |
| Descripción i18n de la action | `reflex_companion/i18n.py` (`ACT_DESC`) |
| ⚠️ **Sanitización shell** | `actions.py` tiene `_is_shell_safe()` y `_is_valid_proc_name()` — **NO bypassear** |
| Browser CDP control (Chrome) | `browser_cdp.py` + `browser_setup.py` |
| Log de acciones ejecutadas | `action_log.py` |
| Acciones "safe" (sin toggle ⚡) | `parsing.py` — `save_taste`, `remind`, `add_important`, `done_important` |

### 🧠 Memoria / estado emocional
| Tarea | Archivo |
|-------|---------|
| Chat history, facts, diario, gustos | `reflex_companion/memory.py` |
| Mood axes + preoccupation + initiative | `reflex_companion/mental_state.py` |
| Compresión de historial (cache cada 15 msgs) | `reflex_companion/context_compression.py` |
| Recordatorios | `reflex_companion/reminders.py` |
| Important items | `reflex_companion/reminders.py` (mismo módulo) |
| Gustos del user | `reflex_companion/tastes.py` |
| News context | `reflex_companion/news.py` |
| Topic share (compartir cosas con el user) | `reflex_companion/topic_share.py` |
| Recap detector | `reflex_companion/recap_detector.py` |
| Migrations de schema JSON | `reflex_companion/migrations.py` |
| System info (OS, hora, etc.) | `reflex_companion/system_state.py` |
| Stats / achievements | `reflex_companion/stats.py` + `achievements.py` |

### 🤖 LLM providers
| Tarea | Archivo |
|-------|---------|
| Dispatcher multi-provider (xAI / OpenRouter / Ollama) | `reflex_companion/llm_provider.py` |
| Cliente xAI Grok directo (streaming, retry, cache singleton) | `reflex_companion/grok_client.py` |
| Cambiar modelo default | `reflex_companion/config.py` (`GROK_MODEL`) |
| ⚠️ **Cliente cache** | Tests guard en `test_llm_client_cache.py` — NO instanciar cliente nuevo cada llamada |
| Prompt cache friendly (orden TOP-stable / BOTTOM-dynamic) | `prompts_<lang>.py` — TIME context al final |

### 🎨 UI / estilos
| Tarea | Archivo |
|-------|---------|
| Componentes de UI (chat header, portrait, dialogs) | `reflex_companion/components.py` |
| CSS, animaciones, glassmorphism, boutique noir | `reflex_companion/styles.py` |
| Estado principal + page `index()` | `reflex_companion/reflex_companion.py` |
| Strings i18n (UI) | `reflex_companion/i18n.py` |
| ⚠️ **Performance**: rx.var con `auto_deps=False, deps=[...]` | Ya hay 19 vars optimizadas. Mantener este patrón. |
| ⚠️ **Lag de scroll**: NO añadir `backdrop-filter: blur` a bubbles | (regresión conocida) |
| FX (starfield, sonidos, optimistic UI, image paste) | `assets/ashley_fx.js` |
| Scroll system (single `_following` state machine) | `assets/ashley_fx.js` (window.__ashleyScroll) |

### 🔧 Electron / native
| Tarea | Archivo |
|-------|---------|
| Wrapper principal (splash, ports, perms, shutdown) | `electron/main.js` |
| Onboarding inicial (API key + provider choice) | `electron/onboarding.html` + `main.js` (`onSubmit`, `validate`) |
| Auto-updater (electron-updater) | `electron/updater.js` |
| Preload script (IPC bridge) | `electron/preload.js` |
| Prebuild frontend antes del installer | `electron/prebuild.js` |
| Config builder + NSIS installer | `electron/package.json` (sección `build`) |
| Icono / installer assets | `electron/build-resources/icon.ico` + `installer.nsh` |
| ⚠️ **PYTHONIOENCODING=utf-8** | Ya está en spawn env — NO quitar (rompe TTS por Unicode crash en cp1252) |
| ⚠️ **Graceful shutdown** | `gracefulShutdownBackend()` libera el mic vía `/api/shutdown` antes de SIGKILL |
| ⚠️ **Conditional clearCache** | Solo en slow-path rebuild — NO clearear siempre (tirá cache de imágenes mood) |

### 🔐 Licencia / pagos
| Tarea | Archivo |
|-------|---------|
| Validación LemonSqueezy + DPAPI | `reflex_companion/license.py` |
| UI de license (input, error states) | `reflex_companion/components.py` + `reflex_companion.py` (state) |
| Tests | `tests/test_license.py` |

### 📚 Manual / ayuda in-app
| Tarea | Archivo |
|-------|---------|
| Contenido del manual (3 idiomas) | `reflex_companion/manual_content.py` |
| UI del manual | `components.py` |

### 🌐 Landing page (repo separado)
| Tarea | Archivo |
|-------|---------|
| Ubicación | `C:\Users\Mister Squishi\Desktop\Ashley\Ashley-IA-landing\` |
| Estructura | `index.html` + `styles.css` + `script.js` (i18n) + `privacy.html` + `terms.html` |
| Idioma default | EN (definido en `script.js` → `detectInitialLang()`) |
| Banner i18n en legal pages | inyectado por JS desde `localStorage.ashley_landing_lang` |
| Deploy | Auto-deploy en Cloudflare Pages al push a `main` |

---

## 4. Comandos esenciales

```bash
# Dev server (vía Electron, puertos dinámicos)
ashley-electron.bat

# Dev server (browser directo, puertos en rxconfig.py)
cd reflex-companion && venv\Scripts\activate && reflex run

# Tests (~600 tests, ~6s)
venv\Scripts\python.exe -m pytest tests/ -v

# Test específico
venv\Scripts\python.exe -m pytest tests/test_<name>.py -v

# Build installer (auto-prebuild incluido)
cd electron && npm run build

# Release a GitHub
cd electron && npm run release

# Diagnóstico latencia LLM
venv\Scripts\python.exe tools/diagnose_latency.py

# Simulación tokens/coste
venv\Scripts\python.exe tools/simulate_token_usage.py
```

---

## 5. Invariantes críticos (NO romper)

1. **Frontend build mtime check** — `main.js` compara mtimes de `.py` y `assets/` vs `.web/build/client/index.html`. Si fuente más nueva → slow-path rebuild. NUNCA mostrar UI stale.
2. **Sanitización shell** en `actions.py` (`_is_shell_safe`, `_is_valid_proc_name`). Bloquea metacaracteres `& | ; < > $ \` ' " \n`. Tests guard en `test_shell_injection_guards.py`.
3. **PYTHONIOENCODING=utf-8** en spawn env — sin esto, prints con `→` etc. crashean en Windows cp1252.
4. **Graceful shutdown** del wake word detector — sin esto, mic queda colgado tras cerrar app.
5. **LLM client cache singleton** — `get_xai_client()` y `_openai_client()`. Tests guard en `test_llm_client_cache.py`.
6. **Prompt cache prefix ≥95%** — TOP estable, BOTTOM dinámico, TIME al final del todo. Tests guard en `test_prompt_cache_friendly.py`.
7. **`@rx.var(auto_deps=False, deps=[...])`** — 19 vars optimizadas. Tests guard en `test_reflex_var_deps.py`.
8. **NO `backdrop-filter: blur` en `.bubble-*`** — causa lag de scroll. Tests guard en `test_chat_scroll_perf.py`.
9. **NO few-shot examples en prompts** — Ashley los copia verbatim. Solo reglas abstractas (regla del user, no test).
10. **Optimistic UI** — `assets/ashley_fx.js` flujo simple (fake bubble + observer purge). Tests guard en `test_optimistic_ui_assets.py` bloquean regresión a la lógica compleja anterior.
11. **Lazy mount del settings dialog** — wrap en `rx.cond(State.show_settings, ...)`. Tests guard en `test_settings_lazy_mount.py`.
12. **Mood image preload solo por JS** — NO añadir CSS `background-image` fallback (rompió producción una vez).

---

## 6. Convenciones del codebase

- **3 idiomas siempre paritarios**: cualquier string de UI o personalidad va en `prompts_en/es/fr.py` y `i18n.py` con las 3 claves.
- **Tags de Ashley**: `[mood:<name>]`, `[action:<type>:<param>]`, `[affection:<delta>]`. Parser en `parsing.py`.
- **Safe actions** (siempre ejecutan): `save_taste`, `remind`, `add_important`, `done_important`.
- **System actions** (requieren ⚡ toggle): `open_app`, `close_window`, `volume_*`, `key_*`, etc.
- **Data dir**: todo persistido en `%APPDATA%\Ashley\data\` en producción, project root en dev (`ASHLEY_DATA_DIR` env var).
- **Versionado**: en `electron/package.json` (la única source of truth para builds/updates).
- **Style guide**: el código existente prefiere comentarios en español para lógica de negocio, inglés para identifiers.

---

## 7. Tests organizados por área

```
tests/
├── test_actions_*           # Acciones del sistema, sanitización shell
├── test_grok_*              # xAI Grok client, sampling
├── test_llm_*               # Multi-provider, cache, message merging
├── test_memory.py           # Persistencia JSON
├── test_mental_state.py     # Mood axes, preoccupation, initiative
├── test_context_compression # Compresión historial
├── test_reminders.py        # Recordatorios + important
├── test_tastes.py           # Gustos
├── test_achievements.py     # Achievements
├── test_news.py             # News context
├── test_topic_share.py      # Topic share
├── test_recap_detector.py   # (no existe, solo en notas?)
├── test_parsing.py          # Tag extraction
├── test_prompts.py          # Prompts EN/ES/FR
├── test_prompt_cache_friendly  # Cache prefix ≥95%
├── test_i18n.py             # UI strings
├── test_migrations.py       # Schema JSON migrations
├── test_license.py          # LemonSqueezy
├── test_whisper*.py         # STT, cache detection, warmup
├── test_wake_word.py        # Wake word detector
├── test_vad_silence_threshold  # VAD 2s
├── test_voice_speed.py      # TTS playbackRate
├── test_tts_*               # TTS backends, autoplay, observer
├── test_optimistic_ui_assets   # Scroll + bubble swap
├── test_lifecycle_and_voice_button  # Shutdown + UI
├── test_shell_injection_guards # Anti-injection
├── test_python_utf8_encoding   # PYTHONIOENCODING
├── test_send_message_none_safe # Form data safety
├── test_app_perf_optimizations # Performance regressions
├── test_llm_client_cache    # Singleton client
├── test_reflex_var_deps     # @rx.var explicit deps
├── test_settings_lazy_mount # Lazy mount dialog
├── test_chat_scroll_perf    # No backdrop-filter
├── test_mood_image_preload  # JS preload only
└── test_bare_action_tag_stripping  # clean_display strips bare tags
```

---

## 8. Reglas de comportamiento del user (memoria persistente)

- **No few-shot examples para Ashley** — los copia verbatim o hace lo opuesto.
- **No romper features que funcionan** — verificar todas las branches antes de cambiar; preguntar si dudo.
- **Modo enseñanza** — si es código de escuela (ej: HelmosDeep), explicar profundo para que pueda defender el código en orales.
- **HelmosDeep level cap** — no exceder Java POO lecciones 6-8.
- **No auto-build/release después de cambios** — esperar instrucción explícita ("estamos probando").

---

## 9. Estado actual / pendiente (snapshot 2026-05-02)

- ✅ v0.17.2 publicada con: scroll fluido, multi-provider onboarding, mood preload, settings instant, landing actualizada, Ashley sentimental, prompts limpios, DevTools off auto.
- ⏳ Beta test pendiente con la hermana (LemonSqueezy Test Mode).
- ⏳ Decidir si traducir privacy/terms HTML a ES/FR (ahora hay banner notice).
- ⏳ Faheem rigger — deadline 2 mayo incumplido, escalar 3-4 mayo.
- ⏳ Completar onboarding LemonSqueezy para activar producción real.
