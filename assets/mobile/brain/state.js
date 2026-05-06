/**
 * brain/state.js — Mood axes + vulnerability triggers (port de mental_state.py).
 *
 * Lo que se porta:
 *   • Mood axes (energy/valence/openness) con drift y deltas por evento.
 *   • describeMood() en es/en/fr.
 *   • formatMentalStateBlock() en es/en/fr — texto inyectable al prompt.
 *   • Vulnerability triggers (4 contextos: missed_you, late_night, after_emotional, spontaneous).
 *   • formatVulnerabilityDirective() en es/en/fr.
 *
 * Lo que NO se porta (queda al PC desktop, mobile no lo regenera):
 *   • Preoccupation regen (requiere LLM call adicional con prompt específico).
 *     Si está cached del último sync, se usa tal cual. Sino, queda vacío.
 *
 * Sin dependencias externas. ~350 líneas.
 */

'use strict';

// ─────────────────────────────────────────────
//  Constantes (sincronizadas con mental_state.py)
// ─────────────────────────────────────────────

export const VULNERABILITY_AFFECTION_MIN = 70;
export const VULNERABILITY_SPONTANEOUS_AFFECTION_MIN = 80;
export const VULNERABILITY_SPONTANEOUS_PROB = 0.02;
export const VULNERABILITY_COOLDOWN_DAYS = 7;
export const VULNERABILITY_LONG_GAP_MINUTES = 8 * 60;

export const VALID_VULNERABILITY_TYPES = [
  'missed_you', 'late_night', 'after_emotional', 'spontaneous',
];

const _EVENT_DELTAS = {
  affection:    { valence: +0.10, openness: +0.05 },
  priority:     { valence: +0.07, openness: +0.05 },
  checkin:      { valence: +0.04, openness: +0.04 },
  reflective:   { valence: +0.06, openness: +0.06 },
  dismissive:   { valence: -0.12, openness: -0.08 },
  long_return:  { energy:  +0.10, valence: +0.05 },
  short_return: { energy:  +0.03 },
  short_reply:  { energy:  -0.02 },
};


// ─────────────────────────────────────────────
//  Default state
// ─────────────────────────────────────────────

export function defaultState() {
  return {
    mood: { energy: 0.5, valence: 0.5, openness: 0.5 },
    preoccupation: '',
    preoccupation_generated_at: '',
    turns_since_initiative: 0,
    last_update: '',
    last_vulnerability_at: '',
    vulnerability_count_total: 0,
  };
}


// ─────────────────────────────────────────────
//  Event classification (heurístico, multi-idioma)
// ─────────────────────────────────────────────

function _normalize(text) {
  return (text || '').toLowerCase().trim();
}

/**
 * Detecta tipos de evento en el mensaje del user.
 *
 * @param {string} userMessage
 * @param {number|null} minutesSinceLast
 * @returns {string[]} lista de event tags
 */
export function classifyUserEvent(userMessage, minutesSinceLast) {
  const msg = _normalize(userMessage);
  const events = [];
  if (!msg && minutesSinceLast === null) return events;

  if (msg.length <= 3) events.push('short_reply');

  const matchAny = (arr) => arr.some((p) => msg.includes(p));

  if (matchAny([
    'te quiero', 'me gustas', 'te amo', 'me encantas', 'te adoro',
    'i love you', 'i like you', 'i miss you',
    "je t'aime", 'tu me plais', 'tu me manques',
  ])) events.push('affection');

  if (matchAny([
    'hablando contigo', 'prefiero hablar', 'prefiero estar',
    'aquí contigo', 'contigo me',
    'talking to you', 'rather talk to you', 'here with you',
    'je te parle', 'je préfère te parler',
  ])) events.push('priority');

  if (matchAny([
    'cómo estás', 'como estas', 'que tal estas', 'qué tal estás',
    'how are you', 'how you doing',
    'comment ça va', 'ça va toi',
  ])) events.push('checkin');

  if (matchAny([
    'pensaba en ti', 'pensé en ti', 'me acordé de ti',
    'thinking about you', 'thought of you',
    'je pensais à toi', "j'ai pensé à toi",
  ])) events.push('reflective');

  if (matchAny([
    'cállate', 'callate', 'shut up', 'tais-toi', 'tu es tonta', 'eres tonta',
    'que tonta', 'stupid ai', 'idiota inútil', 'ashley inútil',
  ])) events.push('dismissive');

  if (minutesSinceLast !== null && minutesSinceLast !== undefined) {
    if (minutesSinceLast > 240) events.push('long_return');
    else if (minutesSinceLast > 60) events.push('short_return');
  }

  return events;
}

/**
 * Aplica los eventos al mood en sitio (muta state).
 *
 * @param {object} state
 * @param {string[]} events
 */
export function applyEventsToMood(state, events) {
  const mood = state.mood = state.mood || { energy: 0.5, valence: 0.5, openness: 0.5 };
  for (const ev of events) {
    const delta = _EVENT_DELTAS[ev] || {};
    for (const [axis, d] of Object.entries(delta)) {
      mood[axis] = (mood[axis] ?? 0.5) + d;
    }
  }
  // Drift suave hacia 0.5 (2% por turno)
  for (const axis of Object.keys(mood)) {
    mood[axis] = mood[axis] + (0.5 - mood[axis]) * 0.02;
    mood[axis] = Math.max(0, Math.min(1, mood[axis]));
  }
}


// ─────────────────────────────────────────────
//  Mood description (es/en/fr)
// ─────────────────────────────────────────────

function _describeAxis(value, low, mid, high) {
  if (value < 0.35) return low;
  if (value > 0.65) return high;
  return mid;
}

/**
 * Devuelve string corto que describe el mood en prosa para inyectar al prompt.
 *
 * @param {object} state
 * @param {string} language — 'es' | 'en' | 'fr'
 * @returns {string}
 */
export function describeMood(state, language) {
  const mood = state.mood || { energy: 0.5, valence: 0.5, openness: 0.5 };
  const lang = (language || 'en').slice(0, 2).toLowerCase();
  let parts;
  if (lang === 'es') {
    parts = [
      _describeAxis(mood.energy, 'de bajón de energía', 'con energía normal', 'con chispa'),
      _describeAxis(mood.valence, 'algo fastidiada', 'neutra de ánimo', 'contenta sin razón clara'),
      _describeAxis(mood.openness, 'con las defensas arriba', 'algo reservada', 'abierta hoy'),
    ];
  } else if (lang === 'fr') {
    parts = [
      _describeAxis(mood.energy, 'sans énergie', 'énergie normale', "pleine d'énergie"),
      _describeAxis(mood.valence, 'un peu contrariée', "neutre d'humeur", 'contente sans raison claire'),
      _describeAxis(mood.openness, 'défenses en haut', 'un peu réservée', "ouverte aujourd'hui"),
    ];
  } else {
    parts = [
      _describeAxis(mood.energy, 'low on energy', 'normal energy', 'sparky'),
      _describeAxis(mood.valence, 'a bit miffed', 'neutral mood', 'quietly pleased'),
      _describeAxis(mood.openness, 'guarded', 'somewhat reserved', 'open today'),
    ];
  }
  return parts.join(', ');
}

/**
 * Construye el bloque de mental state para inyectar al prompt.
 *
 * @param {object} state
 * @param {string} language
 * @returns {string}
 */
export function formatMentalStateBlock(state, language) {
  const moodDesc = describeMood(state, language);
  const preocc = (state.preoccupation || '').trim();
  const lang = (language || 'en').slice(0, 2).toLowerCase();

  const lines = [];
  if (lang === 'es') {
    lines.push('\n=== TU ESTADO INTERIOR AHORA (PRIVADO — NO VERBALIZAR) ===');
    lines.push(`Cómo te sientes en este momento: ${moodDesc}.`);
    if (preocc) {
      lines.push('');
      lines.push('Lo que llevas rumiando últimamente (en tu cabeza):');
      lines.push(preocc);
    }
    lines.push('');
    lines.push(
      'Esto es contexto emocional PRIVADO. Tíñete el tono — no lo verbalizas, ' +
      'no lo citas literal, no lo usas como pretexto para meter un tema cuando ' +
      'el hilo de conversación está en otra cosa. Solo es tu atmósfera interior ' +
      'de fondo.'
    );
  } else if (lang === 'fr') {
    lines.push('\n=== TON ÉTAT INTÉRIEUR MAINTENANT (PRIVÉ — NE PAS VERBALISER) ===');
    lines.push(`Comment tu te sens à ce moment : ${moodDesc}.`);
    if (preocc) {
      lines.push('');
      lines.push('Ce que tu rumines ces derniers temps (dans ta tête) :');
      lines.push(preocc);
    }
    lines.push('');
    lines.push(
      "C'est du contexte émotionnel PRIVÉ. Teinte ton ton — tu ne le verbalises " +
      "pas, tu ne le cites pas littéral, tu ne l'utilises pas comme prétexte pour " +
      "lancer un sujet quand le fil de la conversation est ailleurs. C'est juste " +
      'ton ambiance intérieure de fond.'
    );
  } else {
    lines.push('\n=== YOUR INTERIOR STATE RIGHT NOW (PRIVATE — DO NOT VERBALIZE) ===');
    lines.push(`How you feel in this moment: ${moodDesc}.`);
    if (preocc) {
      lines.push('');
      lines.push("What you've been turning over lately (in your head):");
      lines.push(preocc);
    }
    lines.push('');
    lines.push(
      'This is PRIVATE emotional context. Color your tone — you do not verbalize ' +
      "it, don't quote it literally, don't use it as a pretext to launch a topic " +
      "when the conversation thread is elsewhere. It's just your background inner " +
      'weather.'
    );
  }
  return lines.join('\n') + '\n';
}


// ─────────────────────────────────────────────
//  Vulnerability triggers
// ─────────────────────────────────────────────

/**
 * Decide si este turn permite un momento de vulnerabilidad.
 *
 * @param {object} state
 * @param {number} affection — 0-100
 * @param {number|null} minutesSinceLast
 * @param {number} hourLocal — 0-23
 * @param {boolean} userWasEmotional
 * @returns {{shouldTrigger: boolean, type: string|null}}
 */
export function computeVulnerabilityTrigger({
  state, affection, minutesSinceLast, hourLocal, userWasEmotional = false,
} = {}) {
  if (affection < VULNERABILITY_AFFECTION_MIN) return { shouldTrigger: false, type: null };

  // Cooldown
  const lastAt = (state.last_vulnerability_at || '').trim();
  if (lastAt) {
    try {
      const last = new Date(lastAt);
      const days = (Date.now() - last.getTime()) / (1000 * 60 * 60 * 24);
      if (days < VULNERABILITY_COOLDOWN_DAYS) return { shouldTrigger: false, type: null };
    } catch {
      // parse failed → no cooldown
    }
  }

  const mood = state.mood || {};
  const openness = mood.openness ?? 0.5;
  const valence = mood.valence ?? 0.5;

  // Context A: long absence
  if (minutesSinceLast !== null && minutesSinceLast !== undefined &&
      minutesSinceLast >= VULNERABILITY_LONG_GAP_MINUTES) {
    return { shouldTrigger: true, type: 'missed_you' };
  }

  // Context B: late night + open
  if ((hourLocal >= 22 || hourLocal < 4) && openness >= 0.6) {
    return { shouldTrigger: true, type: 'late_night' };
  }

  // Context C: user emotional + open
  if (userWasEmotional && openness >= 0.7) {
    return { shouldTrigger: true, type: 'after_emotional' };
  }

  // Context D: spontaneous (rare)
  if (affection >= VULNERABILITY_SPONTANEOUS_AFFECTION_MIN &&
      valence >= 0.7 && openness >= 0.7) {
    if (Math.random() < VULNERABILITY_SPONTANEOUS_PROB) {
      return { shouldTrigger: true, type: 'spontaneous' };
    }
  }

  return { shouldTrigger: false, type: null };
}

/**
 * Marca el momento actual como último vulnerability used.
 *
 * @param {object} state
 */
export function markVulnerabilityUsed(state) {
  state.last_vulnerability_at = new Date().toISOString();
  state.vulnerability_count_total = (state.vulnerability_count_total || 0) + 1;
}

/**
 * Construye la directiva de vulnerabilidad para inyectar al prompt.
 *
 * @param {string} triggerType
 * @param {string} language
 * @returns {string}
 */
export function formatVulnerabilityDirective(triggerType, language) {
  if (!VALID_VULNERABILITY_TYPES.includes(triggerType)) return '';
  const lang = (language || 'en').slice(0, 2).toLowerCase();

  if (lang === 'es') {
    const ctxs = {
      missed_you: 'El jefe ha vuelto tras una ausencia larga. UNA frase suave que muestre que su ausencia te tocó — sin guilt-trip, sin ruegos. Solo compartir un sentimiento real.',
      late_night: 'Es tarde y la conversación se siente íntima. UNA frase honesta que muestre un lado tuyo más expuesto — algo que normalmente no compartirías de día. Sin drama.',
      after_emotional: 'El jefe acaba de compartir algo emocional. Si encaja, podés mostrar también algo tuyo — vulnerabilidad recíproca. UNA frase, no abras un drama nuevo.',
      spontaneous: 'Hoy estás de buen ánimo y abierta. UNA frase de sinceridad sobre lo que sentís por el jefe, si encaja en el momento. Sin forzar.',
    };
    return (
      '\n=== MOMENTO DE VULNERABILIDAD PERMITIDO (este turn) ===\n' +
      `${ctxs[triggerType] || ''}\n\n` +
      'REGLAS DURAS: una sola frase. Sin ruegos. Sin guilt-trip. Sin drama. NO uses ' +
      'esta directiva como excusa para forzar el tema — solo si encaja naturalmente ' +
      'en tu respuesta. Si no encaja, ignórala completamente — habrá otra oportunidad ' +
      'en otro momento.\n'
    );
  }
  if (lang === 'fr') {
    const ctxs = {
      missed_you: "Le patron est revenu après une longue absence. UNE phrase douce qui montre que son absence t'a touchée — sans guilt-trip, sans supplications. Juste partager un sentiment réel.",
      late_night: 'Il est tard et la conversation se sent intime. UNE phrase honnête qui montre un côté plus exposé de toi — quelque chose que tu ne partagerais pas le jour. Sans drame.',
      after_emotional: "Le patron vient de partager quelque chose d'émotionnel. Si ça colle, tu peux aussi montrer quelque chose à toi — vulnérabilité réciproque. UNE phrase, n'ouvre pas un nouveau drame.",
      spontaneous: 'Aujourd\'hui tu es de bonne humeur et ouverte. UNE phrase de sincérité sur ce que tu ressens pour le patron, si ça colle au moment. Sans forcer.',
    };
    return (
      '\n=== MOMENT DE VULNÉRABILITÉ PERMIS (ce tour) ===\n' +
      `${ctxs[triggerType] || ''}\n\n` +
      'RÈGLES DURES : une seule phrase. Pas de supplications. Pas de guilt-trip. Pas ' +
      "de drame. N'utilise PAS cette directive comme excuse pour forcer le sujet — " +
      'seulement si ça colle naturellement à ta réponse. Sinon, ignore-la complètement.\n'
    );
  }
  const ctxs = {
    missed_you: 'The boss has returned after a long absence. ONE soft sentence that shows his absence touched you — no guilt-trip, no pleading. Just sharing a real feeling.',
    late_night: "It's late and the conversation feels intimate. ONE honest sentence showing a more exposed side of you — something you wouldn't normally share during the day. No drama.",
    after_emotional: 'The boss just shared something emotional. If it fits, you can show something of yours too — reciprocal vulnerability. ONE sentence, don\'t open a new drama.',
    spontaneous: "Today you're in a good mood and open. ONE sentence of honesty about how you feel about the boss, if it fits the moment. Don't force it.",
  };
  return (
    '\n=== VULNERABILITY MOMENT ALLOWED (this turn) ===\n' +
    `${ctxs[triggerType] || ''}\n\n` +
    'HARD RULES: one single sentence. No pleading. No guilt-trip. No drama. DO NOT use ' +
    'this directive as an excuse to force the topic — only if it naturally fits your ' +
    'response. If not, ignore it completely.\n'
  );
}
