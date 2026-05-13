# ACTION PIPELINE — Deep Notes (post v0.19.46)

> **Para Claude en sesiones futuras**: lee este doc ANTES de tocar cualquier código del action pipeline. Documenta race conditions sutiles, bugs latentes y la lógica enrevesada del speculative dispatch que ha causado múltiples regresiones falsas (v0.19.30 → v0.19.46).

---

## ⚡ v0.19.46 — DESCUBRIMIENTO RAÍZ: Chromium 130+ rechaza GET en /json/new

Sesión de debug 2026-05-12 reveló que TODA la lentitud + bugs de chain venían de un solo cambio en Chromium:

**El bug**: `browser_cdp.new_tab()` usaba `urllib.request.urlopen` con GET implícito → `/json/new` devuelve **HTTP 405 "Using unsafe HTTP verb GET. This action supports only PUT verb."** → `new_tab()` retorna `None` → caemos al poll de 10s en `play_music`/`open_url` → al final reportamos optimistic success mentiroso.

**Confirmado experimentalmente** (curl real contra Opera GX 130):
- `curl -X PUT "http://127.0.0.1:9222/json/new?<URL>"` → 200 OK + tab abierta en 50ms
- `curl "http://127.0.0.1:9222/json/new?<URL>"` (GET) → 405 instantáneo

**Síntomas que observabamos sin entender**:
- "play_music tarda 10 segundos" → era el poll fallback
- "click:like dio like al video del Warcraft" → la tab nueva nunca apareció (CDP rechazado), wait_then clickeó la tab vieja activa
- "Ashley reporta éxito pero nada pasó" → optimistic assumption tras poll timeout

**Fix v0.19.46**: `Request(endpoint, method="PUT")` en `browser_cdp.new_tab()`.

Si añades CUALQUIER endpoint CDP nuevo, **verifica el method requerido** con curl real — Chromium ha estado endureciendo CSRF endpoint por endpoint.

### Otros 5 fixes v0.19.46 (encadenados con el de PUT)

2. **YouTube 2025 selectors**: el wrapping cambió a `segmented-like-dislike-button-view-model like-button-view-model button`. Probado: hay 3 instancias de `like-button-view-model` en DOM, sólo la #1 es visible (sample[0] y sample[2] están ocultas por responsive variants).

3. **`querySelectorAll` + filter visible**: antes usábamos `querySelector` que da SOLO el primer match aunque esté oculto. Ahora iteramos `querySelectorAll` y elegimos el primero con `offsetParent !== null`.

4. **Verificación post-click via aria-pressed**: para canonicals toggleables (`like/dislike/subscribe/play/pause`) leemos aria-pressed antes/después y exigimos cambio. Sino → success=False. Antes click_by_text reportaba success=True por encontrar y clickear ALGO — incluso un `@studylikenat` (canal con "like" en el nombre).

5. **Sinónimos ordenados + whole-word**: frases largas/específicas primero (`indica que te gusta` > `me gusta` > `like`). Sinónimos ≤4 chars requieren regex `\b` (whole-word) — sino "like" matchea cualquier substring random.

6. **No speculative dispatch si chain incluye `wait_then`**: `wait_then` existe para sequenciar, pero speculative dispatch lanza threads en paralelo → wait_then despierta antes que play_music termine → click contra tab vieja. Verificado en logs (speculative=2 cuando debía ser 0). Trade-off aceptado: ~3-5s menos de TTFT speedup, pero la chain funciona DE VERDAD.

---

## TL;DR — Reglas de oro

1. **CDP /json/new requiere PUT desde Chromium 130+** — si tocas browser_cdp.py verifica method requerido con curl real.
2. **El bug "play_music abre 2 tabs" tiene 3 causas raíz independientes** — atacar una sin entender las otras genera regresiones falsas.
3. **`open_app` con queries cortas (<3 chars) es peligroso** — fuzzy match substring puede lanzar el installer o cualquier .exe random del Desktop.
4. **El speculative dispatch puede ejecutar acciones FANTASMA** si el stream falla — el thread daemon sigue corriendo y ejecuta side effects que el user nunca ve en el chat.
5. **`wait_then` requiere ejecución secuencial** — `_maybe_dispatch_speculative` early-returns si wait_then está en la chain. NO desactivar este guard.
6. **Para botones toggleables, click_by_text verifica aria-pressed** — si no cambió, success=False (puede haber clickeado el elemento equivocado).
7. **search_web SIEMPRE reporta éxito** aunque el browser no abra nada (todavía un problema, ver §4).
8. **Agentic continuation está desactivada** desde v0.19.32 — todo el código bajo `if should_continue:` es dead code.
9. **No hay timeout global del mensaje** — un single message puede tardar 60s LLM + 30s × N actions sin cap.

---

## 1. Flujo completo: user message → action ejecutada

### Entry point
- **`State.send_message(form_data)`** — `reflex_companion.py:3708`
  - Wrapper try/except que delega a `_send_message_impl`.

### `_send_message_impl(form_data)` — `reflex_companion.py:3724-3816`
Orden estricto:
1. Sanitiza input: `(form_data.get("message") or "").strip()` (3731) — defensa contra `None`.
2. Casos especiales (vacío, retry, etc.) líneas 3755-3775.
3. **Guard anti-doble-disparo** (3778): aborta si `is_thinking` o `current_response != ""`.
4. **Pre-yield CRÍTICO** (3788-3792): append user msg + `is_thinking=True` + `yield`. Muestra burbuja antes de tocar disco.
5. Reset counters, increment HMAC counter.
6. `yield from self._stream_grok(user_message)` (3808).
7. `yield from self._finalize_response(self._last_response)` (3809).
8. `_maybe_extract_facts()` (3815) — async fact extraction.

### `_streaming_loop(generator)` — `reflex_companion.py:2216-2297`
Invocado dentro de `_stream_grok`:
- **Línea 2239**: `_SPECULATIVE_BY_STATE[id(self)] = {}` — RESET CRÍTICO del slot al inicio del turn.
- Acumula chunks. Cada `STREAM_CHUNK_SIZE=2` (v0.16.14) actualiza `current_response` y llama `_maybe_dispatch_speculative(accumulated)` (2279).
- **Después del último chunk**: pasada extra `_maybe_dispatch_speculative` (2285) para acciones que aparecen al final del stream.

### `_finalize_response(text)` — `reflex_companion.py:3242-3577`
1. Extrae mood/affection/all_actions (3246-3251).
2. Atacha `description` a cada action (3254-3256).
3. **Fallback de detección** (3268-3282): si no hay actions y `auto_actions=ON` y user pidió o Ashley fingió → `detect_intended_action(last_msg, clean_text)` sintetiza un tag.
4. Append assistant message (3288-3294).
5. **POP del slot speculative** (3324): `specs = _SPECULATIVE_BY_STATE.pop(id(self), {}) or {}`.
6. **Itera `all_actions`**:
   - Si key matchea `specs` → `thread.join(timeout=spec_timeout)` (3349-3354).
   - **`spec_timeout = 30.0` para `_LONG_RUNNING_ACTIONS`, `1.5` para resto** (v0.19.44).
   - Si `pre_result is not None` → reusa y append `system_result` (3356-3375).
   - Else → fallback `_execute_and_record_action` (3378). **CAMINO DE DOBLE-EJECUCIÓN si thread tarda > timeout**.
7. Si `result.success=False` → `_stream_action_failure_apology` (3395).
8. **Agentic continuation: DESACTIVADA** v0.19.32 — `should_continue = False` hardcoded en línea ~3574.

### `_execute_and_record_action(action_dict)` — `reflex_companion.py:2124-2210`
1. Snapshot ANTES (`_cached_state_snapshot()`).
2. `execute_action(...)` con `prefer_cdp=self.cdp_enabled`.
3. Update `browser_opened`.
4. **NOOP guard** (2162): si `result.get("noop")` → return sin appendear bubble (importante para `done_important` ya marcado).
5. Snapshot DESPUÉS + invalida cache.
6. Append `system_result` con `ui_content` opcional (privacy v0.19.23).
7. `save_history()`, `log_action_result()`.

---

## 2. Speculative dispatch — race conditions documentadas

### Storage
- **`reflex_companion.py:55`**: `_SPECULATIVE_BY_STATE: dict[int, dict] = {}` — module-level keyed por `id(state)`.

### Lifecycle
| Punto | Líneas | Acción |
|---|---|---|
| `_streaming_loop` start | 2239 | `_SPECULATIVE_BY_STATE[id(self)] = {}` (overwrite, no merge) |
| `_maybe_dispatch_speculative` | 2033-2122 | `slot = setdefault(id(self), {})` — lee/crea |
| `_finalize_response` | 3324 | `specs = pop(id(self), {}) or {}` — pop limpia |
| Cleanup paths | varios | `pop(id(self), None)` |

### Worker thread — `_maybe_dispatch_speculative` 2091-2118
```python
def _worker(action_t=a["type"], params=..., holder=result_holder, ...):
    try:
        holder["result"] = _exec_action(
            action_t, params,
            browser_opened=_bo, lang=_lang, prefer_cdp=_cdp,
        )
    except Exception as e:
        holder["result"] = {"success": False, ...}
```
Daemon thread. Snapshots de `browser_opened/cdp_enabled/auto_actions/language` (NO usa `self`).

### Key del slot
`(action_type, tuple(params))` — STRICT byte-equality.
**Solo dedupea disparos de la misma key dentro del mismo turn** (parsing en cada chunk del stream). NO dedupea acciones lógicamente equivalentes con params distintos.

### Timeout dinámico v0.19.44 — `reflex_companion.py:3349`
```python
spec_timeout = 30.0 if current_action["type"] in _LONG_RUNNING_ACTIONS else 1.5
thread.join(timeout=spec_timeout)
```
- `_LONG_RUNNING_ACTIONS` (`parsing.py:68`) = `{"play_music", "open_url", "search_web"}`.
- 30s cubre `_resolve_youtube_url`(8s) + CDP new_tab(3s) + poll(10s) + buffer.

### RACES LATENTES (no resueltas)

#### A. User envía 2 mensajes rápidos
- Reflex serializa eventos del mismo state (lock async) — generalmente OK.
- **Si segundo `_streaming_loop` llega entre yield final del primer turn y el pop del finalize**:
  - Línea 2239 hace `_SPECULATIVE_BY_STATE[id(self)] = {}` borrando threads en flight.
  - Threads daemon siguen corriendo (escriben `holder["result"]`), pero ya nadie lee.
  - **El primer turn fallback-ejecuta otra vez** → side effect duplicado.
- Mitigación parcial: guard 3778 aborta el segundo si `is_thinking`.

#### B. Stream falla mid-action
- `_stream_grok` raise → catch en `_send_message_impl` (3810-3811) → `_handle_grok_error`.
- **`_finalize_response` NO se llama** → slot NO se pope.
- Threads daemon ejecutan acciones REALES (abren tab, escriben texto) pero su resultado se pierde.
- **El user ve tabs/apps abiertas SIN system_result en el chat** — bug de UX confuso.

#### C. Crash del worker antes del `holder["result"]=`
- Silencioso. `pre_result is None` → fallback ejecuta otra vez.
- **Causa raíz histórica del bug 2-tabs**.
- v0.19.44 mitigado con timeout 30s pero no resuelto en raíz.

#### D. State change durante worker
- Snapshots se toman en líneas 2069-2072 al dispatchar.
- Si user cambia toggle CDP mid-stream, thread usa valor viejo.
- `_bo` snapshot, pero `self.browser_opened = result.get(...)` (3360-3362) puede pisar un toggle a OFF.

#### E. Memory leak
- `_SPECULATIVE_BY_STATE` y `_TURN_CACHE_BY_STATE` (línea 76) acotado pero NO limpieza periódica.
- Comentario reconoce: "si state object muere antes de finalize, entry queda huérfana hasta que `id()` se reuse".
- Práctico: no es problema real salvo stress tests.

#### F. 30s join puede colgar la UI
- Si CDP cuelga sin excepción, `_finalize_response` espera hasta 30s.
- Reflex serializa events del state → user no puede enviar otro msg durante.
- En PCs muy lentos esto es perceptible.

---

## 3. Action selection en prompts (cómo Ashley elige)

### Despachador
- **`prompts.py:18-52`** — `_impl(lang)` → módulo correcto.
- en/es/fr cargados al import; ja/de/ru/ko lazy con fallback a EN.

### Catálogo de tags
- **`prompts_es.py:549-580`** (paralelo en `prompts_en.py:563+`).
- Lista plana de `[action:NAME:PARAM]`.
- **NO hay validación de longitud de NOMBRE del param**.
- **NO hay regla anti-ambigüedad** ("si query es muy corta o ambigua, pregunta antes").

### Reglas play_music vs search_web
- **`prompts_es.py:582-643`**:
  - `play_music` = "cuando el jefe pida cambiar de canción".
  - **Búsqueda interna** (web_search del LLM, sin tag) — el 99% de las veces.
  - `[action:search_web]` solo si pide explícitamente VER el navegador.

### Reglas open_app
- **`prompts_es.py:823-829`**: "Usas open_app con el nombre común de la app. El sistema busca el ejecutable automáticamente."
- "REGLA CRÍTICA: SIEMPRE miras la lista [Ventanas abiertas] antes de actuar."
- ⚠ **Esa regla es para CERRAR, no para abrir**. Para abrir NO hay validación.
- Si user dice "abre et", Ashley puede emitir el tag literalmente.

### CDP block del system prompt
- **`prompts.py:201-298`** — appendea cuando `cdp_enabled=True`.
- Solo describe `click/type_browser/read_page/scroll_page`.
- **NO menciona play_music/open_url/search_web** aunque también usen CDP.

---

## 4. play_music / open_url / search_web — flujos

### `play_music(query, browser_already_open, prefer_cdp, lang)` — `actions.py:956-1326`
Returns `tuple[str, bool, bool]` = `(mensaje, browser_opened, success)`.

**Flujo**:
1. **Resolve URL** (998-1004): `_resolve_youtube_url(query)` con timeout 8s. Si falla → URL = página results, `resolved_ok=False`.
2. **Pre-action dedupe v0.19.41** (1019-1042): si `prefer_cdp` y CDP disponible:
   - Busca videoId 11-char en URL del request.
   - Compara case-sensitive contra `list_tabs()` URLs.
   - Si ya existe → return early sin abrir.
3. **CDP path** (1045-1164):
   - Cierra todas las tabs YT anteriores por URL match (1057-1063).
   - `new_t = _cdp.new_tab(video_url)` — timeout interno 3.0s.
   - Si OK → return.
   - **Si `new_t is None`** → poll defensivo:
     - Phase 1: 4 polls × 250ms = 1s (PCs rápidos).
     - Phase 2: 12 polls × 750ms = 9s (PCs lentos).
     - Total max **10s**. **NUNCA fallback a webbrowser.open** desde aquí (v0.19.39).
     - Si tras 10s no aparece → asume optimista, return success.
   - Si CDP **throws excepción** → fallback a webbrowser.open path.
4. **Webbrowser fallback** (1166-1326):
   - Pre-action `_count_tabs_fresh()` via UIA.
   - `webbrowser.open(video_url)`.
   - `_capture_browser_hwnd(wait=2.0)`.
   - **Belt-and-suspenders sweep** v0.19.38 (1210-1245): cierra dupes por videoId si CDP disponible.
   - `time.sleep(2.0)` post-action.
   - 4 cases verificador (1259-1326).

**Latencia worst-case**: 8s resolve + 0.6s sleep + 10s poll + 2s sleep = **>20s**.

### `_open_url_cdp_safe(url, prefer_cdp, dedupe)` — `actions.py:1345-1466`
Returns `tuple[bool, bool]` = `(already_open, opened_ok)`.

3 fases:
1. **Dedupe** (si `dedupe=True`): normaliza URL (`_normalize_url_for_match` strip `#` + trailing `/`), compara con `list_tabs()`. Si match → `_cdp.activate_tab()` y return `(True, True)`.
2. **CDP new_tab + poll** mismo patrón que play_music (1+9s = 10s max).
3. **Fallback `webbrowser.open(url)`** — solo si CDP throw excepción O CDP no disponible.

### `open_url(url, prefer_cdp, lang)` — `actions.py:1482-1491`
- Añade `https://` prefix si falta.
- Llama `_open_url_cdp_safe(dedupe=True)`.
- Si already_open → mensaje `url_already_open`.

### `search_web(query, prefer_cdp, lang)` — `actions.py:1471-1477`
- Construye URL Google search.
- Llama `_open_url_cdp_safe(dedupe=False)` — cada búsqueda quiere resultados frescos.
- ⚠ **Devuelve siempre `_amsg(..., "search_web")` ignorando `opened_ok`** — NO propaga fallo.

---

## 5. BUG: `open_app` lanza el installer (caso "abre et")

### `open_app(app_name, lang)` — `actions.py:773-876`

Resolución en orden:
1. **URL_APPS dict** (777-779): match exacto sobre `key.lower().strip()` para 17 webs.
2. **APP_MAP lookup** (781): `exe = APP_MAP.get(key, key)` — si no match, `exe = key` literal.
3. **Protocolo URI** (`steam://`, etc.) → `os.startfile`.
4. **`os.startfile(exe)` directo** (792-796): busca en registro Windows. Para "et" → FileNotFoundError.
5. **PowerShell `Start-Process`** (804-814) si `_is_shell_safe(exe)`.
6. **`_search_desktop(hint)`** (817-834): ⚠ **AQUÍ ESTÁ EL BUG**.
7. `_search_start_menu` (837-844).
8. Common roots (846-867).
9. Return error.

### `score_shortcut_name(name, hint)` — `actions.py:261-293`
```
100 → name == hint                       (exact)
 80 → name.startswith(hint)              (prefix)
 60 → hint in name                       (HINT IS SUBSTRING OF NAME)  ← culpable
 30 → name in hint
  0 → otherwise
```

### El bug paso a paso (caso "abre et")
1. Ashley emite `[action:open_app:et]`.
2. `app_name = "et"` (sin sanitización).
3. `_search_desktop("et")` itera `*.lnk/*.url/*.exe` en Desktop.
4. Score `"et" in "ashley-setup-0.19.44"` → True → score=60.
5. **`_SHORTCUT_REJECT_TOKENS`** (253-258): `("uninstall", "unins000", "remove", "readme", "manual", "helper", "crash", "reporter", "redistributable", "config")`.
   - ⚠ **NO incluye `"setup"` ni `"installer"`**.
6. Como `len("Ashley-Setup-0.19.44") < len(otros candidatos)`, gana en tiebreaker `(-score, len(name))`.
7. → `os.startfile(shortcut)` ejecuta el installer.

### Gaps identificados
- **No hay sanitización del input**: `app_name = " ".join(params)` — sin minimum length check.
- **`score_shortcut_name` no tiene mínimo de longitud para hint**.
- **No hay fuzzy matching real** (Levenshtein) — solo substring crudo.
- **Desktop check va ANTES de Start Menu** (intencional, comentario líneas 816-821: "el escritorio es señal fuerte de intención"). Esto AGRAVA el bug.
- **No hay short-circuit explícito si hay exact match** — el scoring lo prioriza (100>60) pero solo si existe.

---

## 6. CDP layer (`browser_cdp.py`)

### Funciones expuestas
- **`is_cdp_available(port=9222)`** (102-127): GET `/json/version`, valida `Browser` matchea `_CHROMIUM_BROWSER_MARKERS`. v0.19.34 (H5).
- **`get_browser_info(port)`** (130-136): debug.
- **`list_tabs(port)`** (139-155): GET `/json/list` (fallback `/json`), filtra `type=='page'`. Si no responde → `[]`. ⚠ **Caller no puede distinguir "no browser" de "browser sin tabs"**.
- **`close_tab(tab_id, port)`** (158-171): GET `/json/close/{id}`. Returns bool. Idempotente.
- **`new_tab(url, port)`** (174-186): GET `/json/new?{encoded_url}` con timeout **3.0s** (más generoso que default 1.5).
- **`activate_tab(tab_id, port)`** (189-206): POST→fallback GET `/json/activate/{id}`.
- **`find_tabs_matching(hint, port)`** (213-224): substring case-insensitive del **TITLE** (no URL — fuente del bug pre-v0.19.41).
- **`close_tabs_matching(hint, exclude, port)`** (227-253).
- WebSocket layer (294+): `_ws_send`, `evaluate_js`, `click_by_selector`, `click_by_text`.

### Timeouts internos
- `_DEFAULT_TIMEOUT = 1.5s` (línea 72) para todas las HTTP excepto `new_tab` (3.0s).
- `_ws_send` default `timeout=10.0s`.

### "CDP no disponible" vs "timeout"
- `_get_json` catch-all `(URLError, ConnectionRefusedError, TimeoutError, JSONDecodeError, OSError)` → return None.
- `is_cdp_available` lo trata todo igual. **No distingue browser-cerrado de browser-overloaded**.

---

## 7. BUGS LATENTES (priorizados)

### CRÍTICOS (afectan al user)

#### #1 — `open_app` substring match con queries cortas
- Síntoma: "abre et" lanza Ashley installer.
- **Fix safe-ish**: añadir `"setup"`, `"installer"`, `"install_"` a `_SHORTCUT_REJECT_TOKENS` + minimum hint length 3 en `score_shortcut_name`.
- **Fix mejor**: requerir score>=80 (prefix) si hint < 5 chars.

#### #2 — Speculative dispatch ejecuta acciones FANTASMA si stream falla
- Síntoma: user ve tab abierta sin `system_result` en chat tras LLM error.
- **Fix safe-ish**: en `_handle_grok_error`, llamar `_pop_speculative_and_join_or_kill(timeout=2)` para cancelar/esperar threads en flight.
- **Fix mejor**: meter el speculative dispatch en un `concurrent.futures.Executor` cancellable.

#### #3 — `search_web` siempre reporta éxito aunque browser no abra
- Síntoma: user pide "busca X", nada pasa, Ashley dice "✓ búsqueda abierta".
- **Fix trivial**: línea `actions.py:1476-1477` propagar `opened_ok` del helper.

### MEDIOS

#### #4 — Worker crash silencioso vs timeout
- Si worker crashea ANTES de `holder["result"]=`, `pre_result is None` → fallback ejecuta otra vez.
- Mitigado parcialmente con timeout 30s pero la raíz sigue.
- **Fix**: el worker debe siempre setear `holder["result"]` (incluso en error path) Y `holder["completed"] = True`. El fallback solo se ejecuta si `not holder.get("completed")`.

#### #5 — Acciones no idempotentes (`hotkey`, `press_key`, `type_text`) doble-ejecución
- Si timeout 1.5s expira mid-thread, fallback ejecuta otra vez.
- En PC lento, escribir texto puede tardar >1.5s → se escribe 2 veces.
- **Fix**: añadir `type_text/hotkey/press_key` a `_LONG_RUNNING_ACTIONS` para que tengan timeout 30s.

#### #6 — No hay timeout global del mensaje
- LLM 60s + 30s × N actions = puede colgar minutos.
- **Fix**: cap total de 90s en `_send_message_impl` con `asyncio.wait_for`.

### MENORES (cleanup, no afectan bugs activos)

#### #7 — `_TERMINAL_ACTIONS` set zombie
- Sin uso desde v0.19.32.
- **Fix**: borrar el set y referencias.

#### #8 — Docstring `play_music` desactualizada
- Comentario dice "navega tab existente" pero v0.13.25 lo eliminó.
- **Fix**: actualizar docstring línea 967-970.

#### #9 — `_USER_ACTION_VERBS` no detecta argumento
- Detecta verbo `"abre "` pero no valida que lo siguiente sea sensato.
- Bug del "abre et" sale por aquí también.

#### #10 — `extract_all_actions` NO dedupea `type_text/hotkey/etc.`
- Si Ashley emite `[action:close_tab:youtube][action:close_tab:youtube]` se ejecutan ambos.
- Comentario explícito en `parsing.py:336-337`.

---

## 8. Decision tree para futuras sesiones

### "El user reporta bug de play_music"
1. ¿2 tabs del mismo video? → revisa speculative dispatch race (sección 2). NO toques `play_music` directo.
2. ¿1 tab pero canción equivocada? → revisa `_resolve_youtube_url` y prompts.
3. ¿0 tabs y "Playing: X" en chat? → revisa el optimismo del CDP poll (línea 1146-1156).
4. ¿Lentitud? → es el HTTP scrape de `_resolve_youtube_url`. Si el speculative dispatch funciona correcto, el user NO debería notarlo.

### "El user reporta bug de open_app"
1. ¿Lanza app equivocada? → `score_shortcut_name` substring match (sección 5). Revisar `_SHORTCUT_REJECT_TOKENS` y minimum length.
2. ¿No encuentra app? → orden de búsqueda en `open_app` (Desktop → Start Menu → Program Files).

### "El user reporta que Ashley abre/escribe cosas que no le pidió"
1. ¿Hay `[action:...]` en el último msg de Ashley? → bug de selección, revisar prompts (sección 3).
2. ¿NO hay tag pero sí side effect? → speculative dispatch fantasma (#2 latente, sección 7).

### "El user reporta lentitud"
- HTTP scrape YouTube: 1-3s típico, 8s timeout. No hay forma simple de acelerar.
- CDP polling: max 10s, solo cuando `new_tab()` returns None.
- Speculative dispatch DEBE ocultar esto durante stream — si NO lo oculta, hay un bug en el dispatch (race con timeout).

### "Quiero añadir una action nueva"
- Añadir handler en `execute_action` (`actions.py:2400+`).
- Decidir si es safe (no necesita Actions toggle) → añadir a `_SAFE_ACTIONS` en `parsing.py:42-46`.
- Decidir si tiene polling/scrape interno largo → añadir a `_LONG_RUNNING_ACTIONS` (`parsing.py:68`).
- Si es no-idempotente Y rápida (<1.5s) → speculative dispatch funcional. Sino, añadir a `_LONG_RUNNING_ACTIONS`.
- Documentar tag en `prompts_es.py:549-580` y todos los demás idiomas.

---

## 9. Versiones recientes — qué arregló cada una

| Versión | Bug | Causa raíz | Fix |
|---|---|---|---|
| **0.19.45** | múltiples (ver abajo) | múltiples | **5 fases + chain action** |
| 0.19.30 | 2 tabs (asumido LLM emite 2 tags) | dedupe by exact key en `extract_all_actions` | dedupe by videoId YouTube |
| 0.19.31 | terminal action gate | `_TERMINAL_ACTIONS` set | (luego desactivado) |
| 0.19.32 | re-emisión de acciones | agentic continuation activa | desactivada `should_continue=False` |
| 0.19.33 | apology re-ejecuta | apology auto-retry | descartar follow_action en apology |
| 0.19.34 | CDP wizard audit | tests + i18n + security | múltiples fixes browser_setup/cdp |
| 0.19.35 | M3 batch lnk + M4 taskbar | rglob lento + i18n | _read_lnks_batch + nota taskbar |
| 0.19.36 | wizard CDP cuelga | rglob 274K archivos + ProgramData mkstemp | _iter_lnk_files + _is_admin skip |
| 0.19.37 | varios edge cases | case-sensitivity + timeouts | hard timeouts + case-insensitive |
| 0.19.38 | 2 tabs (asumido CDP timing) | poll defensivo | poll URL-based |
| 0.19.39 | 2 tabs (asumido fallback) | webbrowser.open desde CDP | NO fallback excepto exception |
| 0.19.40 | Ashley dice ubicación errónea | trigger blocked_action | "barra superior" + 7 idiomas |
| 0.19.41 | 2 tabs (asumido title match) | `find_tabs_matching("youtube")` falla en Opera | URL-based matching |
| 0.19.42 | open_url/search_web sin CDP | usaban webbrowser.open directo | añadido CDP path con dedupe |
| 0.19.43 | python procesos colgados | killStrayAshleyProcesses async no awaited + IMG list incompleta | sync sweep + IMG list expandida |
| **0.19.44** | **2 tabs (causa raíz REAL)** | **`thread.join(timeout=1.0)` en finalize era demasiado corto para play_music (~20s)** | **timeout dinámico 30s para `_LONG_RUNNING_ACTIONS`** |
| **(post 0.19.44)** | "abre et" lanza installer | `score_shortcut_name` substring match + `_SHORTCUT_REJECT_TOKENS` no incluye "setup" | **PENDIENTE** |

---

## 10. Files críticos (paths absolutos)

| File | Líneas | Rol |
|---|---|---|
| `reflex_companion/reflex_companion.py` | 7165 | State, send_message, finalize, speculative storage |
| `reflex_companion/actions.py` | 3234 | execute_action, open_app, play_music, open_url, score_shortcut_name |
| `reflex_companion/parsing.py` | 486 | extract_action, _SAFE_ACTIONS, _LONG_RUNNING_ACTIONS, _TERMINAL_ACTIONS (zombie), _USER_ACTION_VERBS |
| `reflex_companion/browser_cdp.py` | 625 | is_cdp_available, list_tabs, new_tab, close_tab, find_tabs_matching, click_by_text |
| `reflex_companion/prompts.py` | 478 | dispatcher + CDP/device blocks |
| `reflex_companion/prompts_es.py` | ~960 | catálogo tags + reglas play_music/search_web/open_app |

---

## 11. Para Claude futuro: qué NO hacer

1. **NO añadas otro layer de "fix" al play_music sin verificar que la causa raíz NO sea speculative dispatch.** Mira primero `_LONG_RUNNING_ACTIONS` y el timeout dinámico.
2. **NO uses `find_tabs_matching("youtube")`** — usa `list_tabs() + URL filter` siempre. (Bug v0.19.41 explica por qué).
3. **NO añadas `webbrowser.open` como fallback dentro del CDP path** — duplica tabs en PCs lentos. Solo en `except Exception`.
4. **NO toques la agentic continuation sin hablar con el user primero** — desactivada por decisión consciente.
5. **NO reinstales el installer cada fix** — el user puede testear con `ashley-electron.bat` que corre desde el source.
6. **NO subestimes el costo de CDP polling lento** — en PCs gama baja, 10s es el cap pero llega fácil.
7. **NO confíes en que el LLM dedupea por sí mismo** — emite tags duplicados con frecuencia.

## 12b. v0.19.45 — todo lo aplicado en una sola release

Acumula 6 cambios distintos (FASE 1-5 + wait_then) tras sesión larga:

### FASE 1 — safety en `open_app` + propagación de `success`
- `score_shortcut_name`: hints <3 chars siempre 0; hints 3-4 chars solo
  exact/prefix (no substring 60-pts).
- `_SHORTCUT_REJECT_TOKENS` añade `"setup"`, `"installer"`.
- Bug "abre et" → no más launching del Ashley-Setup.exe.
- `search_web` / `open_url` ahora retornan `(msg, success)` en vez de
  solo `msg`. `execute_action` propaga el success real.

### FASE 2 — multilingual click + site-specific selectors
- `_BUTTON_SYNONYMS` en browser_cdp.py: like/dislike/subscribe/share/
  save/play/pause con variantes en 7 idiomas.
- `_SITE_SPECIFIC_SELECTORS`: para youtube.com/twitter.com/x.com,
  selectores CSS estables (`like-button-view-model button`) que NO
  dependen del idioma del aria-label.
- `click_by_text` cascada: site-selector → aria-label sinónimos →
  innerText sinónimos.

### FASE 3 — `holder.completed` flag (causa raíz del 2-tabs)
- Worker speculative ahora setea `holder["completed"] = True` en
  `finally` (no solo `holder["result"]`).
- `_finalize_response` tiene 3-way branch:
  1. `pre_result is not None` → reusar.
  2. `spec_completed=True, result=None` → NO re-ejecutar (side
     effect ya ocurrió). Mensaje genérico al user.
  3. `spec_completed=False` → fallback re-execute (riesgo controlado).
- Causa raíz del bug 2-tabs estaba en branch 2 mal manejado.

### FASE 4 — prompts anti-ambigüedad + tabs context
- ES/EN/FR/JA/DE/RU/KO: regla "abre et" → si query <3 chars o
  ambigua, PREGUNTAR antes de actuar.
- `get_system_state(prefer_cdp=True)` enriquece con tabs+URLs
  vía CDP. Cache buckets separados (CDP vs UIA) para toggle mid-session.

### FASE 5 — close-old-yt + redundant play_music+search_web
- `_last_ashley_music_tab_id` global: solo cierra la tab que
  Ashley abrió antes. Preserva videos del user (Warcraft, etc.).
- Captura id tanto en happy path (`new_tab` returns dict) como en
  poll path (`_tab_appeared`).
- Regla en prompts 7 idiomas: NUNCA emit play_music + search_web
  para misma canción.

### Continuation re-habilitada (comment-only)
- v0.19.32 había desactivado por causar duplicados.
- v0.19.45 re-habilitada PERO con safeguards:
  - Trigger nuevo: "COMENTA el resultado, NO emitas tag".
  - Post-stream STRIP de cualquier action tag (LLM disobedient).
  - NO se llama `_execute_and_record_action` sobre tags leaked.
- Skip cuando: no executed_results / all safe_conversational /
  action es noop / counter >= 1.
- Solución al bug "ella dice que no lo hizo pero sí lo hizo" —
  ahora ve el system_result y comenta con precisión.

### `[action:wait_then:N:NESTED]` — chains
- Nueva action para casos "play_music y luego dale like".
- Sintaxis: `[action:wait_then:5:click:like]` = sleep 5s + click:like.
- delay capeado [1, 20]s (timeout 30s del speculative dispatch).
- Recursión: nested CANNOT be wait_then (anti-bomb).
- Text-based nested (play_music/click/etc.): params rejoin con ":".
- En `_LONG_RUNNING_ACTIONS` para que finalize use timeout 30s.

### Otros menores
- Affection counter centrado (Cormorant Garamond baseline issue):
  `transform: translateY(-2px)` en `.ashley-affection-number`.

### Stats v0.19.45
- Suite: **1646 tests pasando** (de 1531 en v0.19.43, +115 nuevos).
- Archivos modificados: `actions.py`, `reflex_companion.py`,
  `parsing.py`, `browser_cdp.py`, `prompts_*.py × 7`, `styles.py`.
- Bugs resueltos: 6 reportados por user durante la sesión.
- Bugs LATENTES aún: speculative fantasma si stream falla (#2),
  memory leak `_SPECULATIVE_BY_STATE` acotado.

## 12. Para Claude futuro: qué SÍ hacer

1. **LEE este archivo completo antes de tocar el action pipeline.**
2. **Si haces una hipótesis sobre causa raíz, escríbela y pídele al user verificar el síntoma EXACTO antes de hacer commit.**
3. **No hagas builds de installer hasta que el user confirme que el fix funciona en `ashley-electron.bat`.**
4. **Cada fix nuevo: añade tests de regresión específicos, no genéricos.**
5. **Si tocas speculative dispatch, agentic continuation, o el flow de finalize_response, RE-LEE secciones 1-2 de este doc.**
