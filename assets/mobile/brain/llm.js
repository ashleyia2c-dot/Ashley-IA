/**
 * brain/llm.js — Cliente LLM multi-provider para el cerebro móvil de Ashley.
 *
 * Soporta:
 *   • xAI (Grok) — endpoint OpenAI-compatible: https://api.x.ai/v1
 *   • OpenRouter — https://openrouter.ai/api/v1
 *   • Endpoints OpenAI-compatibles custom (Ollama remoto vía Tailscale, etc.)
 *
 * Streaming via SSE (Server-Sent Events) usando fetch + ReadableStream.
 * Yields chunks de texto a medida que llegan — la UI los pinta en tiempo real.
 *
 * BYOK: el user provee su API key en settings del móvil. No la mandamos al
 * PC, no la persistimos en plaintext en server. Vive solo en IndexedDB del móvil.
 *
 * Sin dependencias externas. ~250 líneas.
 */

'use strict';

// Mapping provider → base URL (default; user puede override en settings)
const PROVIDER_URLS = {
  xai: 'https://api.x.ai/v1',
  openrouter: 'https://openrouter.ai/api/v1',
  // ollama_remote: configurado via baseUrl explícito
};

// Mapping provider → modelo default (sincronizado con desktop)
const DEFAULT_MODELS = {
  xai: 'grok-4-1-fast-non-reasoning',
  openrouter: 'x-ai/grok-4-fast',
};


/**
 * LLMClient — encapsula auth + provider config.
 *
 * Usage:
 *   const llm = new LLMClient({ provider: 'xai', apiKey: '...', model: 'grok-4-1-fast-non-reasoning' });
 *   for await (const chunk of llm.stream({ messages, systemPrompt })) {
 *     uiAppend(chunk);
 *   }
 */
export class LLMClient {
  /**
   * @param {object} cfg
   * @param {'xai'|'openrouter'|'custom'} cfg.provider
   * @param {string} cfg.apiKey
   * @param {string} [cfg.model] — defaults por provider
   * @param {string} [cfg.baseUrl] — override de URL base
   * @param {string} [cfg.referrer] — para OpenRouter HTTP-Referer (optional)
   */
  constructor({ provider, apiKey, model, baseUrl, referrer } = {}) {
    if (!provider) throw new Error('LLMClient: provider required');
    if (!apiKey) throw new Error('LLMClient: apiKey required');
    this.provider = provider;
    this.apiKey = apiKey;
    this.model = model || DEFAULT_MODELS[provider] || 'grok-4-1-fast-non-reasoning';
    this.baseUrl = baseUrl || PROVIDER_URLS[provider];
    this.referrer = referrer || 'https://ashleyia.com/mobile';
    if (!this.baseUrl) {
      throw new Error(`LLMClient: unknown provider '${provider}' and no baseUrl provided`);
    }
  }

  /**
   * Build the headers for a request.
   */
  _headers() {
    const h = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.apiKey}`,
    };
    if (this.provider === 'openrouter') {
      // OpenRouter recomienda HTTP-Referer + X-Title para tracking
      h['HTTP-Referer'] = this.referrer;
      h['X-Title'] = 'Ashley Mobile';
    }
    return h;
  }

  /**
   * Build the JSON body for chat/completions.
   */
  _body({ messages, systemPrompt, temperature = 0.7, stream = true }) {
    const finalMessages = [];
    if (systemPrompt) {
      finalMessages.push({ role: 'system', content: systemPrompt });
    }
    for (const m of messages) {
      // Aceptamos {role, content} o el formato completo {role, content, image, ...}
      finalMessages.push({
        role: m.role,
        content: m.content || '',
      });
    }
    return {
      model: this.model,
      messages: finalMessages,
      temperature,
      stream,
    };
  }

  /**
   * Streaming generator. Yields strings (text chunks) as they arrive.
   *
   * @param {object} params
   * @param {Array<{role: string, content: string}>} params.messages
   * @param {string} [params.systemPrompt]
   * @param {number} [params.temperature]
   * @param {AbortSignal} [params.signal] — para cancelar mid-stream
   * @yields {string}
   */
  async *stream({ messages, systemPrompt, temperature = 0.7, signal } = {}) {
    const body = this._body({ messages, systemPrompt, temperature, stream: true });
    const res = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`LLM HTTP ${res.status}: ${errText.slice(0, 300)}`);
    }
    if (!res.body) {
      // Fallback: provider no soporta streaming, devolver todo de golpe
      const data = await res.json();
      const content = data?.choices?.[0]?.message?.content || '';
      if (content) yield content;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE: cada evento separado por \n\n, líneas "data: ...\n"
        let nlIdx;
        while ((nlIdx = buffer.indexOf('\n\n')) !== -1) {
          const event = buffer.slice(0, nlIdx);
          buffer = buffer.slice(nlIdx + 2);

          for (const rawLine of event.split('\n')) {
            const line = rawLine.trim();
            if (!line.startsWith('data:')) continue;
            const payload = line.slice(5).trim();
            if (payload === '[DONE]') {
              return;
            }
            try {
              const obj = JSON.parse(payload);
              const delta = obj?.choices?.[0]?.delta?.content;
              if (typeof delta === 'string' && delta.length > 0) {
                yield delta;
              }
            } catch {
              // SSE puede tener líneas no-JSON (heartbeats), ignorar
            }
          }
        }
      }
    } finally {
      try { reader.releaseLock(); } catch {}
    }
  }

  /**
   * Non-streaming completion. Returns full text.
   *
   * @param {object} params — same shape as stream()
   * @returns {Promise<string>}
   */
  async complete({ messages, systemPrompt, temperature = 0.7, signal } = {}) {
    const body = this._body({ messages, systemPrompt, temperature, stream: false });
    const res = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: this._headers(),
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`LLM HTTP ${res.status}: ${errText.slice(0, 300)}`);
    }
    const data = await res.json();
    return data?.choices?.[0]?.message?.content || '';
  }

  /**
   * Quick health-check. Tries a 1-token completion to verify
   * connectivity + valid API key. Returns true if works.
   *
   * @returns {Promise<{ok: boolean, error?: string}>}
   */
  async health() {
    try {
      const res = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: this._headers(),
        body: JSON.stringify({
          model: this.model,
          messages: [{ role: 'user', content: 'hi' }],
          max_tokens: 1,
          stream: false,
        }),
      });
      if (!res.ok) {
        const t = await res.text().catch(() => '');
        return { ok: false, error: `HTTP ${res.status}: ${t.slice(0, 200)}` };
      }
      return { ok: true };
    } catch (e) {
      return { ok: false, error: String(e?.message || e) };
    }
  }
}


/**
 * Helper: construye un LLMClient desde la config guardada en IndexedDB.
 * Devuelve null si no hay config válida (user no configuró BYOK).
 *
 * @param {object} memory — módulo brain/memory.js (importado por el caller)
 * @returns {Promise<LLMClient|null>}
 */
export async function llmFromConfig(memory) {
  const cfg = (await memory.get('llm_config')) || {};
  if (!cfg.provider || !cfg.apiKey) return null;
  try {
    return new LLMClient({
      provider: cfg.provider,
      apiKey: cfg.apiKey,
      model: cfg.model,
      baseUrl: cfg.baseUrl,
    });
  } catch (e) {
    console.warn('llmFromConfig: invalid config:', e);
    return null;
  }
}


/**
 * Save LLM config in memory. The user provides this in mobile settings.
 *
 * @param {object} memory
 * @param {{provider: string, apiKey: string, model?: string, baseUrl?: string}} cfg
 * @returns {Promise<void>}
 */
export async function saveLlmConfig(memory, cfg) {
  if (!cfg || !cfg.provider || !cfg.apiKey) {
    throw new Error('saveLlmConfig: provider + apiKey required');
  }
  await memory.set('llm_config', {
    provider: cfg.provider,
    apiKey: cfg.apiKey,
    model: cfg.model || DEFAULT_MODELS[cfg.provider] || null,
    baseUrl: cfg.baseUrl || null,
    saved_at: new Date().toISOString(),
  });
}
