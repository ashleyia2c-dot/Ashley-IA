/**
 * brain/parsing.js — Port de reflex_companion/parsing.py a JavaScript.
 *
 * Tag extraction + display cleaner para que el brain JS pueda parsear
 * las respuestas del LLM igual que lo hace Ashley desktop.
 *
 * Sin dependencias. Pure functions. Mismo comportamiento que el Python
 * original — los tests guard verifican parity.
 */

'use strict';

// ─────────────────────────────────────────────
//  Constants (sincronizadas con parsing.py)
// ─────────────────────────────────────────────

// Acciones "seguras" que se ejecutan SIEMPRE (sin toggle ⚡ Acciones).
// Operan sobre datos persistentes, no sobre el sistema.
export const SAFE_ACTIONS = new Set([
  'save_taste', 'remind', 'add_important', 'done_important', 'save_date',
  'save_goal', 'check_in_goal', 'complete_goal',
]);

// Acciones que requieren PC (NO disponibles desde el móvil).
// Si Ashley emite una de estas en móvil, el brain las descarta y emite
// un noop signal — no se ejecuta nada.
export const PC_ONLY_ACTIONS = new Set([
  'screenshot', 'open_app', 'play_music', 'search_web', 'open_url',
  'volume', 'type_text', 'type_in', 'write_to_app', 'focus_window',
  'hotkey', 'press_key', 'close_window', 'close_tab',
  // Browser CDP (definitivamente PC-only)
  'click', 'type_browser', 'read_page', 'scroll_page',
]);

// Lista de tipos para limpieza de tags bare (sin prefijo "action:")
const _BARE_ACTION_TYPES = [
  'screenshot', 'open_app', 'play_music', 'search_web', 'open_url',
  'volume', 'type_text', 'type_in', 'write_to_app', 'focus_window',
  'hotkey', 'press_key', 'close_window', 'close_tab',
  'click', 'type_browser', 'read_page', 'scroll_page',
  'remind', 'add_important', 'done_important', 'save_taste',
  'save_date', 'save_goal', 'check_in_goal', 'complete_goal',
];


// ─────────────────────────────────────────────
//  clean_display — strip tags + meta + artefactos
// ─────────────────────────────────────────────

/**
 * Limpia el texto para mostrar al user. Elimina:
 *   - [mood:X], [action:Y], [affection:Z]
 *   - Tags bare sin "action:" prefix
 *   - "undefined" sueltos (renderizado roto)
 *   - Code blocks vacíos / con "undefined"
 *   - Meta-comentarios sobre la propia respuesta
 *   - Tags vacíos [], [mood:], etc.
 *   - Líneas en blanco consecutivas
 *
 * @param {string|null|undefined} text
 * @returns {string}
 */
export function cleanDisplay(text) {
  if (text === null || text === undefined) return '';
  if (typeof text !== 'string') {
    try { text = String(text); } catch { return ''; }
  }

  // Tags estándar [mood:X] [action:Y] [affection:Z]
  text = text.replace(/\[(?:mood|action|affection):[^\]]*\]/gi, '');
  // Tag parcial al final (durante streaming)
  text = text.replace(/\[(?:mood|action|affection)[^\]]*$/gi, '');
  // Variantes con whitespace en affection
  text = text.replace(/\[\s*affection\s*:\s*[^\]]*\]/gi, '');
  // v0.18.2 — Ashley a veces inventa [system:proactive_message] / [system:X]
  // como si fuera marker interno (alucinación, no está en el protocolo).
  // Strippear cualquier [system:...] del display.
  text = text.replace(/\[\s*system\s*:[^\]]*\]/gi, '');
  text = text.replace(/\[\s*system\s*:[^\]]*$/gi, '');  // parcial al final
  text = text.replace(/\[\s*system\s*\]/gi, '');         // bare

  // Tags bare sin "action:" prefix
  const bareList = _BARE_ACTION_TYPES.join('|');
  const bareRe = new RegExp(`\\[\\s*(?:${bareList})\\s*:[^\\]]*\\]`, 'gi');
  text = text.replace(bareRe, '');
  const barePartialRe = new RegExp(`\\[\\s*(?:${bareList})\\s*:[^\\]]*$`, 'gi');
  text = text.replace(barePartialRe, '');

  // "undefined" sueltos
  text = text.replace(/(?:\s|^)undefined(?:\s|$|[\.\!\?\,\;])/gi, '');
  text = text.replace(/\bundefined\b/gi, '');

  // Code blocks con "undefined"
  text = text.replace(/```[^`]*?undefined[^`]*?```/gis, '');
  text = text.replace(/```[^`]*?undefined[^`]*?(?:\n\n|$)/gis, '\n\n');
  text = text.replace(/`[^`]*?undefined[^`]*?`/gi, '');

  // Code blocks vacíos
  text = text.replace(/```[a-zA-Z]*[ \t]*\n?\s*\n?[ \t]*```/gs, '');

  // Backticks sin cerrar al final/inicio
  text = text.replace(/\n*```[a-zA-Z]*[ \t]*\n*\s*$/, '');
  text = text.replace(/^\s*```[a-zA-Z]*[ \t]*\n*/, '');

  // Inline backticks vacíos (no parte de fenced)
  text = text.replace(/(?<!`)`\s*`(?!`)/g, '');
  text = text.replace(/\n*[ \t]*(?<!`)`\s*$/, '');

  // Meta-comentarios sobre la respuesta (red de seguridad post-stream)
  const metaPatterns = [
    /\bno\s+actions?\s+(?:needed|required|necessary|to\s+take|to\s+execute|taken|executed|performed)\.?\s*/gi,
    /\bnothing\s+to\s+do\s+here\.?\s*/gi,
    /\bno\s+action\s+is\s+(?:needed|required)\.?\s*/gi,
    /\bno\s+(?:se\s+)?necesita(?:n)?\s+acci[oó]n(?:es)?\.?\s*/gi,
    /\bno\s+(?:hay|requiere)\s+acci[oó]n(?:es)?\.?\s*/gi,
    /\bsin\s+acci[oó]n(?:es)?\s+que\s+(?:ejecutar|tomar)\.?\s*/gi,
    /\bpas\s+d['’]action\s+(?:n[eé]cessaire|requise)\.?\s*/gi,
    /\baucune\s+action\s+(?:requise|n[eé]cessaire)\.?\s*/gi,
    /(?:^|[\.\n])\s*no\s+actions?\.?\s*$/gim,
    /(?:^|[\.\n])\s*sin\s+acci[oó]n(?:es)?\.?\s*$/gim,
    /(?:^|[\.\n])\s*pas\s+d['’]actions?\.?\s*$/gim,
    /(?:^|[\.\n])\s*aucune\s+action\.?\s*$/gim,
    /,?\s*conversaci[oó]n\s+(?:fluida|natural|fluida\s+y\s+natural)\.?\s*$/gim,
    /,?\s*conversation\s+(?:flowing|fluid|natural|flowing\s+naturally)\.?\s*$/gim,
    /,?\s*conversation\s+(?:fluide|naturelle)\.?\s*$/gim,
    /,?\s*flujo\s+(?:natural|fluido|de\s+conversaci[oó]n)\.?\s*$/gim,
    /,?\s*natural\s+(?:flow|conversation\s+flow)\.?\s*$/gim,
    /,?\s*r[eé]ponse\s+(?:naturelle|fluide)\.?\s*$/gim,
  ];
  for (const pat of metaPatterns) {
    text = text.replace(pat, '');
  }

  // Catch-all: fragmento meta tras coma/punto al final
  const metaKeywords =
    '(?:fluid[ae]?|fluide|flowing|naturalmente|naturellement|narrativ[oa]?|' +
    'narrative|grindeand[oa]?|conversaci[oó]n|conversation|response|' +
    'r[eé]ponse|respuesta|conclusi[oó]n|conclusion|ending|cierre)';
  const catchAll = new RegExp(
    '(?:[,.!?]\\s+|\\s*\\n\\s*)' +
    '(?:\\([^)]{0,40}\\)|\\b\\w+(?:\\s+\\w+){0,3}\\s+)' +
    `\\b${metaKeywords}\\b` +
    '[\\s.!?]*$',
    'i'
  );
  text = text.replace(catchAll, '');

  // Tags vacíos / mal formados
  text = text.replace(/\[\s*\]/g, '');
  text = text.replace(/\[\s*\w+\s*:\s*\]/g, '');
  text = text.replace(/\[\s*\w+\s*:\s*\w+\s*:\s*\]/g, '');

  // Líneas en blanco consecutivas
  text = text.replace(/\n{3,}/g, '\n\n');

  return text.trim();
}


// ─────────────────────────────────────────────
//  Tag extractors
// ─────────────────────────────────────────────

/**
 * Extrae [mood:xxx]. Devuelve {clean, mood}. Default: "default".
 *
 * @param {string} text
 * @returns {{clean: string, mood: string}}
 */
export function extractMood(text) {
  const matches = [...text.matchAll(/\[\s*mood\s*:\s*(\w+)\s*\]/gi)];
  const mood = matches.length > 0 ? matches[0][1].toLowerCase() : 'default';
  const clean = text.replace(/\[\s*mood\s*:[^\]]*\]/gi, '').trim();
  return { clean, mood };
}

/**
 * Extrae [affection:+N]. Clamp [-3, +3]. Default 0 si no hay tag.
 *
 * @param {string} text
 * @returns {{clean: string, delta: number}}
 */
export function extractAffection(text) {
  const matches = [...text.matchAll(/\[\s*affection\s*:\s*([+-]?\d+)\s*\]/gi)];
  let delta = 0;
  if (matches.length > 0) {
    const n = parseInt(matches[0][1], 10);
    if (!isNaN(n)) delta = Math.max(-3, Math.min(3, n));
  }
  const clean = text.replace(/\[\s*affection\s*:[^\]]*\]/gi, '').trim();
  return { clean, delta };
}

/**
 * Extrae UNA acción [action:tipo:params]. Devuelve {clean, action} o {clean, null}.
 * Parsing por tipo (sincronizado con parsing.py::extract_action).
 *
 * @param {string} text
 * @returns {{clean: string, action: {type: string, params: string[]}|null}}
 */
export function extractAction(text) {
  const match = text.match(/\[action:([^\]]+)\]/);
  if (!match) return { clean: text, action: null };

  const fullTag = match[0];
  const content = match[1];

  const colon = content.indexOf(':');
  let aType, rest;
  if (colon === -1) {
    aType = content;
    rest = '';
  } else {
    aType = content.slice(0, colon);
    rest = content.slice(colon + 1);
  }

  // Parseo por tipo (mismo que Python)
  const TEXT_ACTIONS = ['type_text', 'search_web', 'open_url', 'play_music'];
  let params;
  if (TEXT_ACTIONS.includes(aType)) {
    params = rest ? [rest] : [];
  } else if (aType === 'type_in' || aType === 'write_to_app' || aType === 'save_taste' || aType === 'save_goal') {
    const inner = rest.indexOf(':');
    if (inner === -1) {
      params = rest ? [rest] : [];
    } else {
      params = [rest.slice(0, inner), rest.slice(inner + 1)];
    }
  } else if (aType === 'remind' || aType === 'add_important') {
    // remind/add_important: parse_remind_params (puede llevar fecha YYYY-MM-DDTHH:MM)
    params = parseRemindParams(rest);
  } else if (aType === 'done_important') {
    params = rest ? [rest] : [];
  } else if (aType === 'save_date') {
    // save_date:TYPE:DATE:LABEL
    params = rest.split(':', 3);
    // Hacer que se mantenga el resto si LABEL contiene ":"
    const firstColon = rest.indexOf(':');
    const secondColon = firstColon !== -1 ? rest.indexOf(':', firstColon + 1) : -1;
    if (secondColon !== -1) {
      params = [rest.slice(0, firstColon), rest.slice(firstColon + 1, secondColon), rest.slice(secondColon + 1)];
    } else if (firstColon !== -1) {
      params = [rest.slice(0, firstColon), rest.slice(firstColon + 1)];
    } else {
      params = rest ? [rest] : [];
    }
  } else if (aType === 'check_in_goal' || aType === 'complete_goal') {
    params = rest ? [rest] : [];
  } else {
    // Default: split por ":"
    params = rest ? rest.split(':') : [];
  }

  const clean = text.replace(fullTag, '').trim();
  return { clean, action: { type: aType, params } };
}

/**
 * Extrae TODAS las acciones del texto en orden.
 *
 * @param {string} text
 * @returns {{clean: string, actions: Array<{type: string, params: string[]}>}}
 */
export function extractAllActions(text) {
  const actions = [];
  let remaining = text;
  while (true) {
    const { clean, action } = extractAction(remaining);
    if (action === null) break;
    actions.push(action);
    remaining = clean;
  }
  return { clean: remaining, actions };
}


// ─────────────────────────────────────────────
//  parse_remind_params — port de reminders.py
// ─────────────────────────────────────────────

/**
 * Parsea "YYYY-MM-DDTHH:MM:SS:texto" o "YYYY-MM-DDTHH:MM:texto" en [iso, texto].
 * Si no hace match con un datetime ISO, devuelve [rest] como texto plano.
 *
 * @param {string} rest
 * @returns {string[]}
 */
function parseRemindParams(rest) {
  if (!rest) return [];
  // Match ISO datetime al inicio: YYYY-MM-DDTHH:MM[:SS]
  const m = rest.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?)(?::|$)(.*)$/);
  if (!m) return [rest];
  return [m[1], m[2]];
}


// ─────────────────────────────────────────────
//  Filtro de actions PC-only para móvil
// ─────────────────────────────────────────────

/**
 * Filtra una lista de actions, excluyendo las PC-only (no ejecutables en móvil).
 * Si hay actions de PC, devuelve {filtered, blocked} para que el brain
 * pueda informar al user / no cite ejecuciones falsas.
 *
 * @param {Array<{type: string, params: string[]}>} actions
 * @returns {{
 *   safe: Array<{type: string, params: string[]}>,
 *   blocked: Array<{type: string, params: string[]}>
 * }}
 */
export function filterMobileActions(actions) {
  const safe = [];
  const blocked = [];
  for (const a of actions) {
    if (PC_ONLY_ACTIONS.has(a.type)) {
      blocked.push(a);
    } else {
      safe.push(a);
    }
  }
  return { safe, blocked };
}
