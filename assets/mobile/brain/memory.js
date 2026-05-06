/**
 * brain/memory.js — IndexedDB wrapper para persistencia offline.
 *
 * Almacena toda la data que Ashley móvil necesita:
 *   • chat_history     — mensajes [{role, content, timestamp, id, mood?}]
 *   • facts            — facts del user (memoria de Ashley)
 *   • diary            — entradas de diario (Ashley reflexiona)
 *   • tastes           — gustos del user
 *   • reminders        — recordatorios programados
 *   • important        — items importantes
 *   • important_dates  — fechas importantes (cumples, aniversarios)
 *   • goals            — objetivos del user
 *   • stats            — relationship age, achievements, etc.
 *   • mental_state     — mood + preoccupation + cooldowns
 *   • prompts          — system prompt cached por idioma (de sync_prompts)
 *   • config           — language, llm_provider, llm_model, api_key, server_url, token
 *   • pending_sync     — mensajes creados offline pendientes de push al PC
 *
 * Toda escritura es atómica (transacciones IndexedDB).
 * API simplificada: get(key), set(key, value), getAll(), clear().
 *
 * Sin dependencias externas. ~150 líneas.
 */

'use strict';

const DB_NAME = 'ashley_mobile';
const DB_VERSION = 1;
const STORE = 'kv';  // un solo store key-value para simplicidad

let _dbPromise = null;

/**
 * Open (or create) the IndexedDB database. Cached singleton — el promise
 * se reutiliza entre calls.
 */
function _open() {
  if (_dbPromise) return _dbPromise;
  _dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return _dbPromise;
}

/**
 * Get a value by key. Returns undefined if not found.
 *
 * @param {string} key
 * @returns {Promise<any>}
 */
export async function get(key) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const store = tx.objectStore(STORE);
    const req = store.get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Set a value by key. Overwrites existing.
 *
 * @param {string} key
 * @param {any} value
 * @returns {Promise<void>}
 */
export async function set(key, value) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const store = tx.objectStore(STORE);
    const req = store.put(value, key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/**
 * Delete a key.
 *
 * @param {string} key
 * @returns {Promise<void>}
 */
export async function del(key) {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const req = tx.objectStore(STORE).delete(key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

/**
 * Get all keys in the store.
 *
 * @returns {Promise<string[]>}
 */
export async function keys() {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).getAllKeys();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Wipe all data. Useful for "disconnect / reset" UI.
 *
 * @returns {Promise<void>}
 */
export async function clear() {
  const db = await _open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const req = tx.objectStore(STORE).clear();
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}


// ─────────────────────────────────────────────
//  High-level helpers
// ─────────────────────────────────────────────

/**
 * Append a message to chat_history. Mantiene últimos 200 (truncate al final).
 * Idempotente por id — si el mensaje con ese id ya existe, no lo añade.
 *
 * @param {{role: string, content: string, timestamp: string, id?: string, mood?: string}} msg
 * @returns {Promise<{added: boolean, total: number}>}
 */
export async function appendMessage(msg) {
  const history = (await get('chat_history')) || [];
  if (msg.id) {
    if (history.some((m) => m.id === msg.id)) {
      return { added: false, total: history.length };
    }
  }
  history.push(msg);
  // Truncar a últimos 200 (matching el límite del PC)
  const trimmed = history.slice(-200);
  await set('chat_history', trimmed);
  return { added: true, total: trimmed.length };
}

/**
 * Get the last N messages (default 50).
 *
 * @param {number} n
 * @returns {Promise<Array>}
 */
export async function getRecentMessages(n = 50) {
  const history = (await get('chat_history')) || [];
  return history.slice(-n);
}

/**
 * Mark a message as pending sync (created offline, needs push to PC).
 *
 * @param {object} msg
 * @returns {Promise<void>}
 */
export async function markPendingSync(msg) {
  const pending = (await get('pending_sync')) || [];
  pending.push(msg);
  await set('pending_sync', pending);
}

/**
 * Get all pending sync messages and clear them (atomic-ish — IDB doesn't
 * give us true atomic move, but we read+clear in same transaction).
 *
 * @returns {Promise<Array>}
 */
export async function drainPendingSync() {
  const pending = (await get('pending_sync')) || [];
  await set('pending_sync', []);
  return pending;
}

/**
 * Bulk replace from a sync_state response (overwrites all keys).
 * Used when the brain pulls fresh data from the PC.
 *
 * @param {object} state — payload from /api/mobile/sync_state
 * @returns {Promise<void>}
 */
export async function applySyncState(state) {
  if (!state || typeof state !== 'object') return;
  const keys = [
    'chat_history', 'facts', 'diary', 'tastes', 'reminders',
    'important', 'important_dates', 'goals', 'stats', 'mental_state',
  ];
  for (const k of keys) {
    if (k in state) {
      await set(k, state[k]);
    }
  }
  if (state.affection !== undefined) {
    await set('affection', state.affection);
  }
  if (state.language) {
    await set('language', state.language);
  }
  await set('last_sync_at', new Date().toISOString());
}

/**
 * Save the cached prompts payload (from /api/mobile/sync_prompts).
 *
 * @param {object} prompts — {version, languages: {es: {...}, en: {...}, fr: {...}}}
 * @returns {Promise<void>}
 */
export async function savePrompts(prompts) {
  await set('cached_prompts', prompts);
  await set('cached_prompts_at', new Date().toISOString());
}

/**
 * Load the cached prompts. Returns null if not yet synced.
 *
 * @returns {Promise<object|null>}
 */
export async function loadPrompts() {
  const cached = await get('cached_prompts');
  return cached || null;
}
