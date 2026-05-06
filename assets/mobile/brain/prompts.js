/**
 * brain/prompts.js — Sync + cache + ensamblado del system prompt para móvil.
 *
 * Flujo:
 *   1. Al pulsar "Sync" o automáticamente al detectar conexión con el PC,
 *      se llama a /api/mobile/sync_prompts para descargar los prompts en
 *      los 3 idiomas (es/en/fr) y se guardan en IndexedDB.
 *   2. Cuando el brain JS necesita el system prompt para un chat (online u
 *      offline), llama a buildSystemPrompt() — que toma el prompt cacheado
 *      y le APPENDEA las secciones dinámicas (mood, time, facts inline,
 *      etc.) construidas localmente.
 *
 * Dependencias: brain/memory.js, brain/state.js
 */

'use strict';

import * as memory from './memory.js';
import * as state from './state.js';


// ─────────────────────────────────────────────
//  Sync from PC
// ─────────────────────────────────────────────

/**
 * Descarga los prompts pre-construidos del PC y los cachea localmente.
 *
 * @param {string} serverUrl — base URL del PC (sin trailing slash)
 * @param {string} token — pairing token
 * @returns {Promise<{ok: boolean, version?: string, error?: string}>}
 */
export async function syncPrompts(serverUrl, token) {
  if (!serverUrl || !token) return { ok: false, error: 'missing_credentials' };
  try {
    const res = await fetch(`${serverUrl}/api/mobile/sync_prompts`, {
      headers: { 'X-Ashley-Token': token },
    });
    if (!res.ok) {
      return { ok: false, error: `HTTP ${res.status}` };
    }
    const payload = await res.json();
    await memory.savePrompts(payload);
    return { ok: true, version: payload.version };
  } catch (e) {
    return { ok: false, error: String(e?.message || e) };
  }
}

/**
 * Descarga toda la data de Ashley (chat history, facts, etc.) del PC y
 * la guarda en IndexedDB.
 *
 * @param {string} serverUrl
 * @param {string} token
 * @returns {Promise<{ok: boolean, error?: string}>}
 */
export async function syncState(serverUrl, token) {
  if (!serverUrl || !token) return { ok: false, error: 'missing_credentials' };
  try {
    const res = await fetch(`${serverUrl}/api/mobile/sync_state`, {
      headers: { 'X-Ashley-Token': token },
    });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const payload = await res.json();
    await memory.applySyncState(payload);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: String(e?.message || e) };
  }
}

/**
 * Push pending mensajes al PC (mensajes creados offline que no llegaron).
 *
 * @param {string} serverUrl
 * @param {string} token
 * @returns {Promise<{ok: boolean, added?: number, error?: string}>}
 */
export async function syncPush(serverUrl, token) {
  if (!serverUrl || !token) return { ok: false, error: 'missing_credentials' };
  const pending = await memory.drainPendingSync();
  if (pending.length === 0) return { ok: true, added: 0 };
  try {
    const res = await fetch(`${serverUrl}/api/mobile/sync_push`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Ashley-Token': token,
      },
      body: JSON.stringify({ messages: pending }),
    });
    if (!res.ok) {
      // Re-encolar lo que no pudimos pushear
      for (const m of pending) await memory.markPendingSync(m);
      return { ok: false, error: `HTTP ${res.status}` };
    }
    const data = await res.json();
    return { ok: true, added: data.added || pending.length };
  } catch (e) {
    for (const m of pending) await memory.markPendingSync(m);
    return { ok: false, error: String(e?.message || e) };
  }
}


// ─────────────────────────────────────────────
//  Assembly
// ─────────────────────────────────────────────

/**
 * Construye el system prompt final para enviar al LLM.
 *
 * Toma el prompt cacheado del PC (que ya incluye stable_top + personalidad +
 * device_section_mobile) y le APPENDEA las secciones dinámicas construidas
 * localmente (time, mood, vulnerability si aplica, facts cortos, etc.).
 *
 * Estrategia: el prompt cacheado del PC se construyó con facts=[], diary=[]
 * (vacío por defecto). Aquí no podemos meter facts/diary inline en el prompt
 * server-built, así que lo APPENDEAMOS como anexo al final. El LLM lee todo
 * el prompt — no importa el orden para comprensión, solo afecta caching.
 *
 * @param {object} params
 * @param {string} params.language — 'es' | 'en' | 'fr'
 * @param {object} [params.stateOverride] — para tests
 * @returns {Promise<string>} — system prompt completo
 */
export async function buildSystemPrompt({ language = 'es', stateOverride } = {}) {
  const cachedPrompts = await memory.loadPrompts();
  if (!cachedPrompts) {
    throw new Error('prompts_not_synced — call syncPrompts() first');
  }
  const lang = (language || 'es').slice(0, 2).toLowerCase();
  const langPrompts = cachedPrompts.languages?.[lang] ||
                      cachedPrompts.languages?.es ||
                      cachedPrompts.languages?.en;
  if (!langPrompts || !langPrompts.system_prompt) {
    throw new Error(`prompts_missing_for_lang_${lang}`);
  }

  let basePrompt = langPrompts.system_prompt;

  // Construir el bloque de mental state local
  const stateData = stateOverride || (await memory.get('mental_state')) || state.defaultState();
  const mentalBlock = state.formatMentalStateBlock(stateData, lang);

  // Time context
  const timeBlock = _buildTimeBlock(lang);

  // Facts (inline al final del prompt como anexo)
  const facts = (await memory.get('facts')) || [];
  const factsBlock = _formatFactsForPrompt(facts, lang);

  // Diary corto (últimas 3 entradas)
  const diary = (await memory.get('diary')) || [];
  const diaryBlock = _formatDiaryForPrompt(diary.slice(-3), lang);

  // Tastes
  const tastes = (await memory.get('tastes')) || [];
  const tastesBlock = _formatTastesForPrompt(tastes, lang);

  // Append todo al final del prompt cacheado
  const dynamic = (
    `\n${mentalBlock}` +
    `${tastesBlock}` +
    `${factsBlock}` +
    `${diaryBlock}` +
    `${timeBlock}`
  );

  return basePrompt + dynamic;
}


// ─────────────────────────────────────────────
//  Helpers para secciones dinámicas
// ─────────────────────────────────────────────

function _buildTimeBlock(lang) {
  const now = new Date();
  const hh = now.getHours().toString().padStart(2, '0');
  const mm = now.getMinutes().toString().padStart(2, '0');
  const dateStr = now.toLocaleDateString(
    lang === 'es' ? 'es-ES' : lang === 'fr' ? 'fr-FR' : 'en-US',
    { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
  );
  if (lang === 'es') {
    return `\n=== TIEMPO ===\nFecha actual: ${dateStr}\nHora local: ${hh}:${mm}\n`;
  }
  if (lang === 'fr') {
    return `\n=== TEMPS ===\nDate actuelle : ${dateStr}\nHeure locale : ${hh}:${mm}\n`;
  }
  return `\n=== TIME ===\nCurrent date: ${dateStr}\nLocal time: ${hh}:${mm}\n`;
}

function _formatFactsForPrompt(facts, lang) {
  if (!Array.isArray(facts) || facts.length === 0) return '';
  const header = lang === 'es' ? '\n=== HECHOS DEL JEFE (memoria de Ashley) ===\n'
              : lang === 'fr' ? '\n=== FAITS SUR LE PATRON (mémoire d\'Ashley) ===\n'
              : '\n=== FACTS ABOUT THE BOSS (Ashley\'s memory) ===\n';
  // Limit a 30 facts más recientes para no romper el prompt
  const recent = facts.slice(-30);
  const lines = recent.map((f) => {
    const cat = f.categoria || f.category || '';
    const txt = f.hecho || f.fact || f.text || '';
    return `- [${cat}] ${txt}`;
  });
  return header + lines.join('\n') + '\n';
}

function _formatDiaryForPrompt(diary, lang) {
  if (!Array.isArray(diary) || diary.length === 0) return '';
  const header = lang === 'es' ? '\n=== ÚLTIMAS SESIONES (diario) ===\n'
              : lang === 'fr' ? '\n=== DERNIÈRES SESSIONS (journal) ===\n'
              : '\n=== RECENT SESSIONS (diary) ===\n';
  const lines = diary.map((d) => {
    const ts = d.timestamp || d.fecha || '';
    const txt = d.entrada || d.entry || d.text || '';
    return `[${ts}] ${txt}`;
  });
  return header + lines.join('\n\n') + '\n';
}

function _formatTastesForPrompt(tastes, lang) {
  if (!Array.isArray(tastes) || tastes.length === 0) return '';
  const header = lang === 'es' ? '\n=== GUSTOS DEL JEFE ===\n'
              : lang === 'fr' ? '\n=== GOÛTS DU PATRON ===\n'
              : '\n=== THE BOSS\'S TASTES ===\n';
  const grouped = {};
  for (const t of tastes) {
    const cat = t.categoria || t.category || 'otros';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(t.valor || t.value || t.text || '');
  }
  const lines = Object.entries(grouped).map(([cat, items]) => `${cat}: ${items.join(', ')}`);
  return header + lines.join('\n') + '\n';
}
