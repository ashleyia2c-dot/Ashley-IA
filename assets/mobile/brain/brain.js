/**
 * brain/brain.js — Orchestrator del cerebro móvil de Ashley.
 *
 * Es el "main entry point" para chatear con Ashley desde el móvil. Combina
 * todos los módulos del brain:
 *
 *   memory.js   ←→  brain.js  ←→  llm.js
 *                       ↕
 *                  prompts.js
 *                       ↕
 *                   state.js
 *                       ↕
 *                  parsing.js
 *
 * Modos de operación:
 *   • ONLINE  — el PC del user está reachable. Las llamadas /api/mobile/send
 *               van directamente al PC (sin LLM client local). Es la manera
 *               por defecto desde v0.18.2 cuando el PC está encendido.
 *   • OFFLINE — el PC no responde. Brain usa LLM client local (BYOK)
 *               + memoria cached + prompts cached para chatear sin PC.
 *               Los mensajes se guardan en pending_sync y se pushean al
 *               PC cuando vuelve a estar online.
 *
 * Detección de modo: ping a /api/mobile/status. Si responde 200, online.
 * Si timeout o error de red, offline.
 *
 * Dependencias: brain/memory.js, brain/llm.js, brain/prompts.js,
 *               brain/state.js, brain/parsing.js
 */

'use strict';

import * as memory from './memory.js';
import * as parsing from './parsing.js';
import * as state from './state.js';
import * as prompts from './prompts.js';
import { LLMClient, llmFromConfig } from './llm.js';


// ─────────────────────────────────────────────
//  Connectivity detection
// ─────────────────────────────────────────────

const _ONLINE_TIMEOUT_MS = 3000;
const _ONLINE_CACHE_MS = 30 * 1000;  // 30s
let _lastOnlineCheck = { at: 0, online: false };

/**
 * Verifica si el PC del user es reachable.
 * Cacheado durante 30s para evitar pings excesivos.
 *
 * @param {string} serverUrl
 * @param {string} token
 * @returns {Promise<boolean>}
 */
export async function isOnline(serverUrl, token) {
  const now = Date.now();
  if (now - _lastOnlineCheck.at < _ONLINE_CACHE_MS) {
    return _lastOnlineCheck.online;
  }
  if (!serverUrl) {
    _lastOnlineCheck = { at: now, online: false };
    return false;
  }
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), _ONLINE_TIMEOUT_MS);
    const res = await fetch(`${serverUrl}/api/mobile/status`, {
      headers: token ? { 'X-Ashley-Token': token } : {},
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    _lastOnlineCheck = { at: now, online: res.ok };
    return res.ok;
  } catch {
    _lastOnlineCheck = { at: now, online: false };
    return false;
  }
}

/**
 * Forzar refresh del cache de online status.
 */
export function invalidateOnlineCache() {
  _lastOnlineCheck = { at: 0, online: false };
}


// ─────────────────────────────────────────────
//  Send message (modo dual: online o offline)
// ─────────────────────────────────────────────

/**
 * Envía un mensaje del user. Routea al PC si online, al brain JS si offline.
 *
 * @param {object} params
 * @param {string} params.text — mensaje del user
 * @param {string} params.serverUrl — base URL del PC
 * @param {string} params.token — pairing token
 * @param {function(string): void} [params.onChunk] — callback streaming chunks (offline only)
 * @param {AbortSignal} [params.signal] — para cancelar mid-stream
 * @returns {Promise<{userMessage: object, ashleyMessage: object, mode: 'online'|'offline'}>}
 */
export async function send({ text, serverUrl, token, onChunk, signal } = {}) {
  if (!text || !text.trim()) throw new Error('empty_message');

  const online = await isOnline(serverUrl, token);
  if (online) {
    return await _sendOnline({ text, serverUrl, token });
  }
  return await _sendOffline({ text, onChunk, signal });
}


/**
 * ONLINE — manda el mensaje al PC vía /api/mobile/send.
 * El PC corre Ashley con sus features completas. Devuelve respuesta sync.
 */
async function _sendOnline({ text, serverUrl, token }) {
  const res = await fetch(`${serverUrl}/api/mobile/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Ashley-Token': token,
    },
    body: JSON.stringify({ message: text }),
  });
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    throw new Error(`send_online_failed: HTTP ${res.status}: ${errText.slice(0, 200)}`);
  }
  const data = await res.json();
  // Guardar también en local memory para que el offline tenga la conversación
  if (data.user_message) await memory.appendMessage(data.user_message);
  if (data.ashley_message) await memory.appendMessage(data.ashley_message);
  return {
    userMessage: data.user_message,
    ashleyMessage: data.ashley_message,
    mode: 'online',
  };
}


/**
 * OFFLINE — corre Ashley LOCALMENTE en el móvil usando BYOK.
 *
 * Pasos:
 *   1. Append user message a memoria local + pending_sync.
 *   2. Cargar LLM client desde config (BYOK del user).
 *   3. Construir system prompt local (incluye device_section_mobile).
 *   4. Stream LLM response.
 *   5. Parse tags ([mood:X] [action:Y] [affection:Z]).
 *   6. Filter actions PC-only (no se ejecutan).
 *   7. Apply safe actions a memoria (save_taste, remind, etc.).
 *   8. Update mood + vulnerability state.
 *   9. Append Ashley message a memoria + pending_sync.
 */
async function _sendOffline({ text, onChunk, signal }) {
  const llm = await llmFromConfig(memory);
  if (!llm) {
    throw new Error('offline_llm_not_configured — set provider + apiKey in mobile settings');
  }

  // 1. Append user msg
  const now = new Date();
  const userId = `mobile-u-${now.toISOString()}`;
  const userMsg = {
    role: 'user',
    content: text,
    timestamp: now.toISOString(),
    id: userId,
  };
  await memory.appendMessage(userMsg);
  await memory.markPendingSync(userMsg);

  // 2. Build system prompt
  const language = (await memory.get('language')) || 'es';
  let systemPrompt;
  try {
    systemPrompt = await prompts.buildSystemPrompt({ language });
  } catch (e) {
    // Reencolar mensaje user para retry posterior
    throw new Error(`prompt_build_failed: ${e.message || e}`);
  }

  // 3. Update mood with the user event
  const mentalState = (await memory.get('mental_state')) || state.defaultState();
  const recentMessages = await memory.getRecentMessages(20);
  const minutesSince = _minutesSinceLastUserMessage(recentMessages);
  const events = state.classifyUserEvent(text, minutesSince);
  state.applyEventsToMood(mentalState, events);

  // 4. Vulnerability check
  const affection = (await memory.get('affection')) ?? 50;
  const userEmotional = _isEmotionalMessage(text);
  const vuln = state.computeVulnerabilityTrigger({
    state: mentalState,
    affection,
    minutesSinceLast: minutesSince,
    hourLocal: now.getHours(),
    userWasEmotional: userEmotional,
  });
  if (vuln.shouldTrigger && vuln.type) {
    systemPrompt += '\n' + state.formatVulnerabilityDirective(vuln.type, language);
    state.markVulnerabilityUsed(mentalState);
  }
  await memory.set('mental_state', mentalState);

  // 5. Stream LLM response
  const chatMessages = recentMessages
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .slice(-14)
    .map((m) => ({ role: m.role, content: m.content || '' }));
  // El último mensaje (el actual del user) ya fue añadido a recent → asegurar que está
  if (chatMessages.length === 0 || chatMessages[chatMessages.length - 1].content !== text) {
    chatMessages.push({ role: 'user', content: text });
  }

  let raw = '';
  try {
    for await (const chunk of llm.stream({
      messages: chatMessages,
      systemPrompt,
      temperature: 0.7,
      signal,
    })) {
      raw += chunk;
      if (onChunk) {
        try { onChunk(chunk); } catch {}
      }
    }
  } catch (e) {
    throw new Error(`llm_stream_failed: ${e.message || e}`);
  }

  // 6. Parse response
  const moodResult = parsing.extractMood(raw);
  let cleanText = moodResult.clean;
  const mood = moodResult.mood;

  const affResult = parsing.extractAffection(cleanText);
  cleanText = affResult.clean;
  const affDelta = affResult.delta;

  const allActions = parsing.extractAllActions(cleanText);
  cleanText = allActions.clean;
  const { safe: safeActions, blocked: blockedActions } = parsing.filterMobileActions(allActions.actions);

  cleanText = parsing.cleanDisplay(cleanText);
  if (!cleanText) cleanText = '...';

  // 7. Apply safe actions to memory (save_taste, remind, add_important, etc.)
  for (const action of safeActions) {
    try {
      await _applySafeAction(action);
    } catch (e) {
      console.warn('Failed to apply action', action, e);
    }
  }

  // 8. Update affection
  const newAffection = Math.max(0, Math.min(100, affection + affDelta));
  await memory.set('affection', newAffection);

  // 9. Append Ashley msg
  const ashleyId = `mobile-a-${now.toISOString()}`;
  const ashleyMsg = {
    role: 'assistant',
    content: cleanText,
    timestamp: new Date().toISOString(),
    id: ashleyId,
    mood,
    blocked_actions: blockedActions.length > 0 ? blockedActions : undefined,
  };
  await memory.appendMessage(ashleyMsg);
  await memory.markPendingSync(ashleyMsg);

  return {
    userMessage: userMsg,
    ashleyMessage: ashleyMsg,
    mode: 'offline',
  };
}


// ─────────────────────────────────────────────
//  Safe action application (offline)
// ─────────────────────────────────────────────

/**
 * Aplica una safe action a la memoria local. Estas son las que NO requieren
 * el PC (operan sobre datos persistentes).
 */
async function _applySafeAction(action) {
  const { type, params } = action;
  const now = new Date().toISOString();

  if (type === 'save_taste' && params.length >= 2) {
    const tastes = (await memory.get('tastes')) || [];
    tastes.push({ categoria: params[0], valor: params[1], timestamp: now });
    await memory.set('tastes', tastes);
  } else if (type === 'add_important' && params.length >= 1) {
    const important = (await memory.get('important')) || [];
    important.push({
      id: `mobile-imp-${now}`,
      texto: params[params.length - 1],
      due_date: params.length >= 2 ? params[0] : null,
      created_at: now,
      done: false,
    });
    await memory.set('important', important);
  } else if (type === 'done_important' && params.length >= 1) {
    const important = (await memory.get('important')) || [];
    const target = (params[0] || '').toLowerCase();
    for (const item of important) {
      if (item.id === params[0] || (item.texto || '').toLowerCase().includes(target)) {
        item.done = true;
        item.done_at = now;
      }
    }
    await memory.set('important', important);
  } else if (type === 'remind' && params.length >= 2) {
    const reminders = (await memory.get('reminders')) || [];
    reminders.push({
      id: `mobile-rem-${now}`,
      datetime: params[0],
      texto: params[1],
      created_at: now,
    });
    await memory.set('reminders', reminders);
  } else if (type === 'save_date' && params.length >= 3) {
    const dates = (await memory.get('important_dates')) || [];
    dates.push({
      id: `mobile-date-${now}`,
      type: params[0],
      date: params[1],
      label: params[2],
      created_at: now,
    });
    await memory.set('important_dates', dates);
  } else if (type === 'save_goal' && params.length >= 2) {
    const goals = (await memory.get('goals')) || [];
    goals.push({
      id: `mobile-goal-${now}`,
      goal: params[1],
      category: params[0],
      created_at: now,
      completed: false,
    });
    await memory.set('goals', goals);
  } else if (type === 'check_in_goal' && params.length >= 1) {
    const goals = (await memory.get('goals')) || [];
    const target = (params[0] || '').toLowerCase();
    for (const g of goals) {
      if (g.id === params[0] || (g.goal || '').toLowerCase().includes(target)) {
        g.last_check_in = now;
      }
    }
    await memory.set('goals', goals);
  } else if (type === 'complete_goal' && params.length >= 1) {
    const goals = (await memory.get('goals')) || [];
    const target = (params[0] || '').toLowerCase();
    for (const g of goals) {
      if (g.id === params[0] || (g.goal || '').toLowerCase().includes(target)) {
        g.completed = true;
        g.completed_at = now;
      }
    }
    await memory.set('goals', goals);
  }
}


// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function _minutesSinceLastUserMessage(messages) {
  const userMsgs = messages.filter((m) => m.role === 'user' && m.timestamp);
  if (userMsgs.length < 2) return null;
  try {
    const last = new Date(userMsgs[userMsgs.length - 2].timestamp);
    return (Date.now() - last.getTime()) / (1000 * 60);
  } catch {
    return null;
  }
}

function _isEmotionalMessage(text) {
  const lower = (text || '').toLowerCase();
  const markers = [
    'me siento', 'estoy triste', 'estoy mal', 'estoy cansado',
    'me duele', 'no puedo más',
    'i feel', 'i\'m sad', 'i\'m tired', 'i\'m hurt', 'i can\'t',
    'je me sens', 'je suis triste', 'je suis fatigué',
  ];
  return markers.some((m) => lower.includes(m));
}


// ─────────────────────────────────────────────
//  Public API
// ─────────────────────────────────────────────

export const Brain = {
  send,
  isOnline,
  invalidateOnlineCache,
  // Re-exports para conveniencia (no es necesario importar los submódulos)
  memory,
  parsing,
  state,
  prompts,
};

export default Brain;
