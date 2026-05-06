# Ashley Mobile Brain

El "cerebro" de Ashley portado a JavaScript para que el móvil pueda chatear
**incluso con el PC apagado** (modo offline). Cuando el PC está encendido y
reachable, el móvil delega al PC (modo online) — donde Ashley tiene features
completas (voz, actions, vision).

## Arquitectura

```
                        ┌─────────────┐
                        │  brain.js   │  Orchestrator
                        │  (entry)    │
                        └──────┬──────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼─────┐           ┌────▼─────┐          ┌────▼─────┐
   │ memory   │           │ prompts  │          │  state   │
   │ (IDB)    │           │ (sync+   │          │ (mood +  │
   │          │           │  build)  │          │  vuln)   │
   └────┬─────┘           └────┬─────┘          └──────────┘
        │                      │
        │                 ┌────▼─────┐
        │                 │ parsing  │
        │                 │ (tags)   │
        │                 └──────────┘
        │
   ┌────▼─────┐
   │   llm    │  Multi-provider client (xAI/OpenRouter)
   │          │  con streaming SSE
   └──────────┘
```

## Modos de operación

### ONLINE (PC encendido + reachable)

```
Mobile UI → POST /api/mobile/send → PC corre Ashley → respuesta sync
                                        ↓
                           Brain JS solo cachea memoria
```

El móvil delega al PC. Ashley desktop tiene acceso a:
- Wake word, voz local (TTS/STT)
- Actions del PC (open_app, close_window, etc.)
- Vision con captura de pantalla
- Compresión de historial via LLM call adicional
- Preoccupation regen periódico

### OFFLINE (PC apagado o no reachable)

```
Mobile UI → brain.send() → llm.stream() → directo a xAI/OpenRouter
                ↓
       memory + state local
                ↓
       pending_sync (se pushea al PC al volver online)
```

El móvil corre Ashley LITE:
- ✅ Personalidad completa (prompt sync del PC)
- ✅ Mood axes + vulnerability triggers
- ✅ Memoria local (chat, facts, diary, tastes, goals, etc.)
- ✅ Safe actions (save_taste, save_date, save_goal, remind, etc.)
- ✅ device_section_mobile inyectado → Ashley sabe que está en móvil
- ❌ Sin actions del PC (los tags se filtran y no se ejecutan)
- ❌ Sin preoccupation regen (usa el último cached del PC)
- ❌ Sin compresión de historial (usa solo últimos 14 mensajes raw)

## Setup en el móvil

```javascript
import Brain from './brain/brain.js';

// 1. Sync inicial (al pairing exitoso o cuando user pulse "Sync")
const serverUrl = 'http://192.168.1.42:17300';
const token = '...'; // del QR pairing
await Brain.prompts.syncPrompts(serverUrl, token);
await Brain.prompts.syncState(serverUrl, token);

// 2. Configurar BYOK (user lo introduce en settings del móvil)
await import('./brain/llm.js').then(({ saveLlmConfig }) =>
  saveLlmConfig(Brain.memory, {
    provider: 'xai',  // o 'openrouter'
    apiKey: 'xai-...',
    model: 'grok-4-1-fast-non-reasoning',  // optional
  })
);

// 3. Enviar mensaje (auto-detecta online vs offline)
const result = await Brain.send({
  text: 'hola jefe que tal el día',
  serverUrl,
  token,
  onChunk: (chunk) => uiAppendChunk(chunk),  // streaming offline
});

console.log(result.mode);          // 'online' | 'offline'
console.log(result.ashleyMessage); // {role, content, timestamp, id, mood}
```

## Sync flow

```
┌──── PC (desktop) ────┐                ┌──── Mobile ────┐
│                      │                │                │
│ /api/mobile/sync_prompts ────────────►│ brain/memory   │
│                      │                │  cached_prompts│
│ /api/mobile/sync_state  ─────────────►│                │
│   (chat, facts, diary,                │  chat_history  │
│    tastes, goals,…)                   │  facts, diary, │
│                      │                │  …             │
│                      │                │                │
│                      │◄─────────────── /api/mobile/sync_push
│ Merge cronológico    │                │  (mensajes     │
│ por timestamp        │                │   creados      │
│                      │                │   offline)     │
└──────────────────────┘                └────────────────┘
```

## Limitaciones conocidas

- **No hay sync continuo en tiempo real**: si el PC está encendido y el móvil
  también, los mensajes del móvil se ven en el PC al refrescar Reflex (después
  de reiniciar Ashley desktop), no instantáneo.
- **Mood diverge offline**: si el user chatea offline mucho tiempo, el mood
  del móvil evoluciona local. Al reconectar, last-write-wins (merge simple).
- **Sin preoccupation regen offline**: el preoccupation se regenera en el PC
  cada 90 min. Si el móvil chatea offline >90 min, su preoccupation queda
  vieja. Al reconectar, se sincroniza el nuevo del PC.
- **Sin imagen / vision offline**: el móvil offline no puede subir capturas a
  Ashley. Para vision, hay que estar online (PC procesa la imagen).

## Tests

`tests/test_mobile_brain_assets.py` — guards de regresión sobre los archivos JS:
- Existencia y exports correctos
- Sincronización de constantes (vulnerability thresholds, etc.)
- Filtrado de actions PC-only en `parsing.filterMobileActions`
- Estructura de `LLMClient`

## Archivos

| Archivo | Líneas | Rol |
|---------|--------|-----|
| `brain.js`   | ~360 | Orchestrator (online/offline routing, send) |
| `llm.js`     | ~250 | Multi-provider LLM client + streaming SSE |
| `memory.js`  | ~200 | IndexedDB wrapper |
| `parsing.js` | ~310 | Tag extraction (port de parsing.py) |
| `prompts.js` | ~210 | Sync + cache + assembly |
| `state.js`   | ~330 | Mood + vulnerability (port de mental_state.py) |

Total: ~1,660 líneas de JS, sin dependencias externas. Bundle del APK
crece ~50 KB minified.
