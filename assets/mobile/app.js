/* ════════════════════════════════════════════════════════════════════
 * Ashley Mobile — client logic
 *
 * Conexión: lee server URL + pairing token de localStorage.
 * Polling: /api/mobile/chat?since=<ts> cada 2.5s para nuevos mensajes.
 * Send: POST /api/mobile/send con header X-Ashley-Token.
 * ════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ─── Storage keys ──────────────────────────────────────────────
  const STORE_SERVER_URL = 'ashley.mobile.serverUrl';
  const STORE_TOKEN      = 'ashley.mobile.token';

  // ─── State ──────────────────────────────────────────────────────
  let serverUrl = (localStorage.getItem(STORE_SERVER_URL) || '').replace(/\/$/, '');
  let token     = localStorage.getItem(STORE_TOKEN) || '';
  let lastTimestamp = '';
  let pollInterval = null;
  let isSending = false;

  // ─── DOM refs ──────────────────────────────────────────────────
  const setupScreen = document.getElementById('setup-screen');
  const appScreen   = document.getElementById('app-screen');
  const chatEl      = document.getElementById('chat');
  const inputEl     = document.getElementById('msg-input');
  const sendBtn     = document.getElementById('send-btn');
  const connStatus  = document.getElementById('conn-status');

  // Setup
  const setupServerInput = document.getElementById('setup-server-url');
  const setupTokenInput  = document.getElementById('setup-token');
  const setupConnectBtn  = document.getElementById('setup-connect-btn');
  const setupStatusEl    = document.getElementById('setup-status');
  const scanQrBtn        = document.getElementById('scan-qr-btn');

  // Scanner overlay
  const scannerOverlay  = document.getElementById('scanner-overlay');
  const scannerVideo    = document.getElementById('scanner-video');
  const scannerCanvas   = document.getElementById('scanner-canvas');
  const scannerStatus   = document.getElementById('scanner-status');
  const scannerCloseBtn = document.getElementById('scanner-close');
  let scannerStream = null;
  let scannerRafId  = null;
  let scannerDetector = null; // BarcodeDetector instance

  // Memories overlay
  const memoriesBtn   = document.getElementById('memories-btn');
  const memoriesPanel = document.getElementById('memories-panel');
  const memoriesClose = document.getElementById('memories-close');
  const memoriesList  = document.getElementById('memories-list');

  // Settings overlay
  const settingsBtn        = document.getElementById('settings-btn');
  const settingsPanel      = document.getElementById('settings-panel');
  const settingsClose      = document.getElementById('settings-close');
  const settingsServerInput= document.getElementById('settings-server-url');
  const settingsTokenInput = document.getElementById('settings-token');
  const settingsSaveBtn    = document.getElementById('settings-save-btn');
  const settingsDisconnectBtn = document.getElementById('settings-disconnect-btn');

  // Modo offline (BYOK) — v0.18.2
  const settingsOfflineProvider = document.getElementById('settings-offline-provider');
  const settingsOfflineKey      = document.getElementById('settings-offline-key');
  const settingsOfflineModel    = document.getElementById('settings-offline-model');
  const settingsOfflineTestBtn  = document.getElementById('settings-offline-test-btn');
  const settingsOfflineSaveBtn  = document.getElementById('settings-offline-save-btn');
  const settingsOfflineStatus   = document.getElementById('settings-offline-status');

  // ─── Helpers ───────────────────────────────────────────────────
  function showScreen(name) {
    setupScreen.hidden = name !== 'setup';
    appScreen.hidden   = name !== 'app';
  }

  function setStatus(text, kind) {
    connStatus.textContent = text;
    connStatus.className = 'header-status' + (kind ? ' ' + kind : '');
  }

  function setSetupStatus(text, kind) {
    setupStatusEl.textContent = text;
    setupStatusEl.className = 'setup-status' + (kind ? ' ' + kind : '');
  }

  function isAtBottom() {
    return chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight < 80;
  }
  function scrollToBottom() {
    requestAnimationFrame(() => { chatEl.scrollTop = chatEl.scrollHeight; });
  }

  // ─── API calls ─────────────────────────────────────────────────
  async function apiCall(path, options) {
    if (!serverUrl) throw new Error('No server configured');
    const opts = options || {};
    const headers = Object.assign({
      'Content-Type': 'application/json',
      'X-Ashley-Token': token || '',
    }, opts.headers || {});
    const res = await fetch(serverUrl + path, Object.assign({}, opts, { headers }));
    return res;
  }

  async function fetchStatus() {
    try {
      const res = await apiCall('/api/mobile/status', { method: 'GET' });
      if (!res.ok) return { ok: false, paired: false };
      return await res.json();
    } catch (e) {
      return { ok: false, paired: false, error: e.message };
    }
  }

  async function fetchMessages(since) {
    const qs = since ? '?since=' + encodeURIComponent(since) : '';
    const res = await apiCall('/api/mobile/chat' + qs, { method: 'GET' });
    if (!res.ok) {
      if (res.status === 401) {
        setStatus('sin emparejar', 'error');
      } else {
        setStatus('error ' + res.status, 'error');
      }
      return null;
    }
    const data = await res.json();
    return data.messages || [];
  }

  async function fetchFacts() {
    const res = await apiCall('/api/mobile/facts', { method: 'GET' });
    if (!res.ok) return [];
    const data = await res.json();
    return data.facts || [];
  }

  async function sendMessage(text) {
    // ── Online primero (PC encendido) ──
    try {
      const res = await apiCall('/api/mobile/send', {
        method: 'POST',
        body: JSON.stringify({ message: text }),
      });
      if (res.ok) return await res.json();
      const errBody = await res.text().catch(() => '');
      // Si es 401 (token mal), no caemos a offline — es config error
      if (res.status === 401) {
        throw new Error('Token inválido. Re-empareja con tu PC.');
      }
      throw new Error('send failed: ' + res.status + ' ' + errBody.slice(0, 100));
    } catch (onlineErr) {
      // ── Fallback offline si está configurado ──
      const cfg = loadOfflineConfig();
      if (!cfg || !cfg.provider || !cfg.apiKey) {
        // No hay modo offline → re-throw el error original
        throw onlineErr;
      }
      // Llamada directa al LLM (BYOK). Es chat one-shot — sin streaming
      // ni system prompt full ni state machine porque app.js es script
      // clásico (no ES modules). Para chat completo offline con prompt
      // completo + mood + memoria, el user puede usar el brain JS via
      // import dinámico (futuro: hot-load).
      try {
        const headers = {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + cfg.apiKey,
        };
        if (cfg.provider === 'openrouter') {
          headers['HTTP-Referer'] = 'https://ashleyia.com/mobile';
          headers['X-Title'] = 'Ashley Mobile';
        }
        const baseUrl = cfg.baseUrl || (
          cfg.provider === 'xai'
            ? 'https://api.x.ai/v1'
            : 'https://openrouter.ai/api/v1'
        );
        // Mensajes recientes para context (últimos 10) — el brain JS
        // hace assembly más sofisticado, esto es minimal.
        const recentMsgs = Array.from(chatEl.querySelectorAll('.msg-row'))
          .slice(-10)
          .map((row) => {
            const isUser = row.classList.contains('user');
            const bubble = row.querySelector('.msg-bubble');
            return {
              role: isUser ? 'user' : 'assistant',
              content: bubble ? bubble.textContent : '',
            };
          })
          .filter((m) => m.content);
        // El último mensaje del user todavía no está en el DOM como
        // bubble, viene como argumento `text`
        recentMsgs.push({ role: 'user', content: text });
        // System prompt minimal — explica que es Ashley en móvil sin PC
        const systemMin = (
          'You are Ashley, a tsundere AI companion (22, secretary, programmer). ' +
          'RIGHT NOW you are talking to your boss from his Android phone — his PC ' +
          'is OFF or unreachable. You CANNOT execute PC actions (open_app, close_window, ' +
          'play_music, etc.). If he asks for something on the PC, gently say you ' +
          "can't from his pocket — suggest he do it later. Reply in the language " +
          'he writes to you. Keep your tsundere personality (ironic, slightly distant, ' +
          'with warmth slipping through). Wrap gestures in *asterisks*. Add [mood:X] ' +
          'and [affection:N] tags at the end.'
        );
        const llmRes = await fetch(baseUrl + '/chat/completions', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            model: cfg.model || 'grok-4-1-fast-non-reasoning',
            messages: [{ role: 'system', content: systemMin }, ...recentMsgs],
            temperature: 0.7,
            stream: false,
          }),
        });
        if (!llmRes.ok) {
          const t = await llmRes.text().catch(() => '');
          throw new Error('Offline LLM error ' + llmRes.status + ': ' + t.slice(0, 120));
        }
        const data = await llmRes.json();
        const raw = (data.choices && data.choices[0] && data.choices[0].message
                     && data.choices[0].message.content) || '';
        // Strip tags básicos para mostrar (sincronizado con parsing.py)
        const moodMatch = raw.match(/\[\s*mood\s*:\s*(\w+)\s*\]/i);
        const mood = moodMatch ? moodMatch[1].toLowerCase() : 'default';
        const cleanText = raw
          .replace(/\[(?:mood|action|affection):[^\]]*\]/gi, '')
          .replace(/\s+$/, '')
          .trim() || '...';
        const now = new Date().toISOString();
        const tsKey = Date.now();
        const userMsg = {
          role: 'user', content: text, timestamp: now,
          id: 'mobile-offline-u-' + tsKey,
        };
        const ashleyMsg = {
          role: 'assistant', content: cleanText, timestamp: now,
          id: 'mobile-offline-a-' + tsKey, mood,
        };
        // v0.18.2 — Mark mensajes offline como pending para auto-push al
        // PC cuando vuelva a estar online. autoSyncState() los detecta y
        // pushea via /api/mobile/sync_push. Sin esto, el chat offline
        // quedaría aislado del historial del desktop.
        try {
          appendPending(userMsg);
          appendPending(ashleyMsg);
        } catch (_) { /* localStorage full or quota exceeded — silent */ }
        // Marcar que estamos offline para que el próximo autoSyncState
        // exitoso dispare flushPending automáticamente (tras detectar
        // reconexión).
        _wasOnline = false;
        return {
          ok: true,
          mode: 'offline',
          user_message: userMsg,
          ashley_message: ashleyMsg,
        };
      } catch (offlineErr) {
        // Falló el offline también → reportamos ambas razones
        throw new Error(
          'PC sin conexión y modo offline también falló: ' +
          (offlineErr.message || offlineErr)
        );
      }
    }
  }

  // ─── Render ────────────────────────────────────────────────────
  function clearChat() {
    chatEl.innerHTML = '';
  }

  function renderEmptyChat() {
    clearChat();
    const empty = document.createElement('div');
    empty.className = 'empty-chat';
    empty.textContent = 'Aún no hay mensajes. Escribe abajo para empezar.';
    chatEl.appendChild(empty);
  }

  function appendMessage(msg) {
    // Clear empty state if present
    const emptyEl = chatEl.querySelector('.empty-chat');
    if (emptyEl) emptyEl.remove();

    const role = msg.role || 'assistant';
    const row = document.createElement('div');
    row.className = 'msg-row ' + (
      role === 'user' ? 'user' :
      role === 'system' ? 'system' :
      'ashley'
    );
    row.dataset.id = msg.id || '';

    if (role === 'assistant') {
      const avatar = document.createElement('img');
      avatar.className = 'msg-avatar';
      avatar.src = serverUrl + '/ashley_pfp.jpg';
      avatar.alt = 'Ashley';
      avatar.onerror = () => { avatar.style.display = 'none'; };
      row.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = msg.content || '';

    if (msg.image) {
      const img = document.createElement('img');
      img.className = 'msg-image';
      img.src = msg.image;
      img.alt = 'image';
      bubble.appendChild(img);
    }

    row.appendChild(bubble);
    chatEl.appendChild(row);
  }

  function showTypingIndicator() {
    removeTypingIndicator();
    const row = document.createElement('div');
    row.id = 'typing-indicator';
    row.className = 'typing-indicator';
    const dots = document.createElement('div');
    dots.className = 'typing-dots';
    dots.innerHTML = '<span></span><span></span><span></span>';
    row.appendChild(dots);
    chatEl.appendChild(row);
    scrollToBottom();
  }
  function removeTypingIndicator() {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
  }

  function renderMemories(facts) {
    memoriesList.innerHTML = '';
    if (!facts || facts.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'memories-empty';
      empty.textContent = 'Ashley aún no ha guardado nada de ti.';
      memoriesList.appendChild(empty);
      return;
    }
    // Sort by importance descending, then by category
    const sorted = facts.slice().sort((a, b) => {
      const ai = parseInt(a.importancia) || parseInt(a.importance) || 0;
      const bi = parseInt(b.importancia) || parseInt(b.importance) || 0;
      return bi - ai;
    });
    sorted.forEach(f => {
      const item = document.createElement('div');
      item.className = 'memory-item';

      const cat = f.categoria || f.category || '—';
      const text = f.hecho || f.fact || f.text || '';
      const imp = f.importancia || f.importance || '';

      const catEl = document.createElement('span');
      catEl.className = 'memory-category';
      catEl.textContent = cat;
      item.appendChild(catEl);

      const textEl = document.createElement('div');
      textEl.className = 'memory-text';
      textEl.textContent = text;
      item.appendChild(textEl);

      if (imp) {
        const impEl = document.createElement('span');
        impEl.className = 'memory-importance';
        impEl.textContent = '★ ' + imp;
        textEl.appendChild(impEl);
      }

      memoriesList.appendChild(item);
    });
  }

  // ─── Polling loop ──────────────────────────────────────────────
  async function pollOnce() {
    try {
      const newMsgs = await fetchMessages(lastTimestamp);
      if (newMsgs === null) return;
      if (newMsgs.length === 0) {
        setStatus('conectada');
        return;
      }
      const wasAtBottom = isAtBottom();
      newMsgs.forEach(appendMessage);
      const lastMsg = newMsgs[newMsgs.length - 1];
      if (lastMsg && lastMsg.timestamp) {
        lastTimestamp = lastMsg.timestamp;
      }
      if (wasAtBottom) scrollToBottom();
      setStatus('conectada');
    } catch (e) {
      setStatus('error', 'error');
      console.warn('poll err:', e);
    }
  }

  function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollOnce, 2500);
  }
  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  // ─── Auto-sync (v0.18.2) ───────────────────────────────────────
  // Resync automático de TODA la data persistente (facts, diary, tastes,
  // reminders, important, dates, goals, stats, mental_state) desde el PC.
  // Triggers:
  //   • Al arrancar tras tryConnect exitoso
  //   • Al volver a foreground (visibilitychange)
  //   • Heartbeat cada 5 min mientras visible + online
  //   • Tras detectar transición offline → online
  // Throttle: mínimo 30s entre syncs para evitar spam.
  // También: pushea mensajes pending (creados offline) al PC.

  const SYNC_HEARTBEAT_MS  = 5 * 60 * 1000;   // 5 min
  const SYNC_THROTTLE_MS   = 30 * 1000;       // 30s mín entre syncs
  const STORE_PENDING      = 'ashley.mobile.pending_sync';
  const STORE_LAST_SYNC    = 'ashley.mobile.last_sync_at';
  const STORE_CACHED_FACTS = 'ashley.mobile.cached_facts';
  const STORE_CACHED_DIARY = 'ashley.mobile.cached_diary';

  let _syncHeartbeat = null;
  let _wasOnline = true;
  let _syncing = false;

  function loadPending() {
    try {
      const raw = localStorage.getItem(STORE_PENDING);
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  }
  function savePending(arr) {
    localStorage.setItem(STORE_PENDING, JSON.stringify(arr || []));
  }
  function appendPending(msg) {
    const cur = loadPending();
    cur.push(msg);
    savePending(cur);
  }

  async function autoSyncState({ force } = {}) {
    if (_syncing) return { ok: false, reason: 'busy' };
    if (!serverUrl || !token) return { ok: false, reason: 'no_creds' };
    const now = Date.now();
    const lastAt = parseInt(localStorage.getItem(STORE_LAST_SYNC) || '0', 10) || 0;
    if (!force && now - lastAt < SYNC_THROTTLE_MS) {
      return { ok: false, reason: 'throttled' };
    }
    _syncing = true;
    try {
      const res = await apiCall('/api/mobile/sync_state', { method: 'GET' });
      if (!res.ok) {
        _wasOnline = false;  // marca offline para detectar reconexión
        return { ok: false, reason: 'http_' + res.status };
      }
      const data = await res.json();
      // Cache local de los datos para que la UI tenga acceso aunque
      // el PC se apague después de este sync. Memorias panel los lee
      // directamente; chat los muestra inline.
      if (Array.isArray(data.facts)) {
        localStorage.setItem(STORE_CACHED_FACTS, JSON.stringify(data.facts));
      }
      if (Array.isArray(data.diary)) {
        localStorage.setItem(STORE_CACHED_DIARY, JSON.stringify(data.diary));
      }
      // Otros campos (tastes, important_dates, goals, stats) — guardamos
      // todo el payload para que features futuras los puedan leer sin
      // tener que re-pedirlos.
      localStorage.setItem('ashley.mobile.cached_state', JSON.stringify({
        synced_at: new Date(now).toISOString(),
        tastes: data.tastes || [],
        reminders: data.reminders || [],
        important: data.important || [],
        important_dates: data.important_dates || [],
        goals: data.goals || [],
        stats: data.stats || {},
        mental_state: data.mental_state || {},
        affection: data.affection,
        language: data.language,
      }));
      localStorage.setItem(STORE_LAST_SYNC, String(now));
      // Detectar reconexión: si estábamos offline y ahora respondió OK,
      // pushea mensajes pending al PC.
      if (!_wasOnline) {
        await flushPending();
      }
      _wasOnline = true;
      return { ok: true };
    } catch (e) {
      _wasOnline = false;
      console.warn('auto-sync failed:', e && e.message);
      return { ok: false, reason: String(e && e.message || e) };
    } finally {
      _syncing = false;
    }
  }

  async function flushPending() {
    const pending = loadPending();
    if (!pending.length) return { ok: true, added: 0 };
    try {
      const res = await apiCall('/api/mobile/sync_push', {
        method: 'POST',
        body: JSON.stringify({ messages: pending }),
      });
      if (res.ok) {
        savePending([]);
        const data = await res.json().catch(() => ({}));
        return { ok: true, added: data.added || pending.length };
      }
      // Fallo del push — los mensajes siguen en pending para reintentar
      return { ok: false, reason: 'http_' + res.status };
    } catch (e) {
      return { ok: false, reason: String(e && e.message || e) };
    }
  }

  function startSyncHeartbeat() {
    if (_syncHeartbeat) clearInterval(_syncHeartbeat);
    _syncHeartbeat = setInterval(() => {
      if (!document.hidden) {
        autoSyncState();
      }
    }, SYNC_HEARTBEAT_MS);
  }
  function stopSyncHeartbeat() {
    if (_syncHeartbeat) {
      clearInterval(_syncHeartbeat);
      _syncHeartbeat = null;
    }
  }

  // ─── Main flows ────────────────────────────────────────────────
  async function tryConnect() {
    if (!serverUrl || !token) {
      showScreen('setup');
      return false;
    }
    setStatus('conectando…');
    const status = await fetchStatus();
    if (!status.ok || !status.paired) {
      showScreen('setup');
      setSetupStatus(
        status.error
          ? 'Error de conexión: ' + status.error
          : 'Token inválido o desconocido. Verifica el código de emparejamiento.',
        'error'
      );
      // Pre-fill setup with current values for editing
      setupServerInput.value = serverUrl;
      setupTokenInput.value = token;
      return false;
    }
    showScreen('app');
    // Load initial chat
    const allMsgs = await fetchMessages('');
    if (allMsgs && allMsgs.length) {
      clearChat();
      allMsgs.forEach(appendMessage);
      lastTimestamp = allMsgs[allMsgs.length - 1].timestamp || '';
      scrollToBottom();
    } else {
      renderEmptyChat();
    }
    setStatus('conectada');
    startPolling();
    // v0.18.2 — auto-sync arranca al conectar (force=true salta throttle).
    // Mete fact/diary/tastes/etc. en localStorage para que features que
    // dependan de eso (memorias panel, modo offline) tengan data fresca.
    autoSyncState({ force: true });
    startSyncHeartbeat();
    // Si había mensajes pending del último offline, pushealos
    if (loadPending().length > 0) {
      flushPending();
    }
    return true;
  }

  async function handleSend() {
    if (isSending) return;
    const text = inputEl.value.trim();
    if (!text) return;
    isSending = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    inputEl.style.height = 'auto';

    // Optimistic: add user msg immediately
    const tempId = 'local-' + Date.now();
    appendMessage({
      role: 'user',
      content: text,
      id: tempId,
      timestamp: new Date().toISOString(),
    });
    scrollToBottom();
    showTypingIndicator();

    try {
      const data = await sendMessage(text);
      removeTypingIndicator();
      // The polling will pick up the new messages, but we can also append now
      if (data && data.ashley_message) {
        // Update lastTimestamp to skip the duplicate from polling
        const userTs = data.user_message && data.user_message.timestamp;
        const ashleyTs = data.ashley_message.timestamp;
        if (ashleyTs > lastTimestamp) lastTimestamp = ashleyTs;
        // Replace optimistic user msg with real one (same id swap)
        const tempEl = chatEl.querySelector('[data-id="' + tempId + '"]');
        if (tempEl && data.user_message) {
          tempEl.dataset.id = data.user_message.id || '';
        }
        appendMessage(data.ashley_message);
        scrollToBottom();
      }
    } catch (e) {
      removeTypingIndicator();
      const errBubble = document.createElement('div');
      errBubble.className = 'msg-row system';
      const b = document.createElement('div');
      b.className = 'msg-bubble';
      b.textContent = 'Error enviando mensaje. ' + e.message;
      errBubble.appendChild(b);
      chatEl.appendChild(errBubble);
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }

  // ─── QR Scanner ────────────────────────────────────────────────
  function setScannerStatus(text, kind) {
    scannerStatus.textContent = text;
    scannerStatus.className = 'scanner-status' + (kind ? ' ' + kind : '');
  }

  // ─── Capacitor permission helper ───────────────────────────────
  // Capacitor 6 NO pide runtime permission de CAMERA al sistema cuando se
  // llama navigator.mediaDevices.getUserMedia() desde JS. Tener CAMERA en
  // el AndroidManifest sólo declara el permiso — Android 6+ requiere que
  // la app PIDA explícitamente al user con un dialog runtime.
  // Sin esto, getUserMedia se cuelga indefinidamente esperando un stream
  // que nunca llega (el OS no abre la cámara sin permission del user).
  //
  // Solución: usar el plugin Camera de Capacitor (que sí maneja el runtime
  // permission flow) para PEDIR permission ANTES de getUserMedia.
  async function _requestCameraPermissionViaCapacitor() {
    try {
      const C = window.Capacitor;
      if (!C || !C.Plugins || !C.Plugins.Camera) {
        // No estamos en el APK Capacitor (ej: probando en browser dev) —
        // saltarse este paso. getUserMedia pedirá permission directamente.
        console.log('Capacitor.Plugins.Camera no disponible (browser dev mode)');
        return { granted: true, note: 'no_capacitor' };
      }
      // checkPermissions primero para no spamear el dialog si ya está concedido
      let status = null;
      try {
        status = await C.Plugins.Camera.checkPermissions();
      } catch (e) {
        console.warn('checkPermissions failed:', e);
      }
      if (status && status.camera === 'granted') {
        return { granted: true, note: 'already_granted' };
      }
      // Pedir explícitamente — Android muestra el dialog del sistema
      const res = await C.Plugins.Camera.requestPermissions({
        permissions: ['camera'],
      });
      const granted = (res && res.camera === 'granted');
      return { granted, note: 'requested:' + (res && res.camera) };
    } catch (e) {
      console.warn('requestCameraPermissionViaCapacitor error:', e);
      // Fallback: intentar getUserMedia igual — si Android tiene el permiso
      // a otro nivel, podría funcionar.
      return { granted: false, note: 'error:' + (e.message || e.name) };
    }
  }

  // Wrap getUserMedia con timeout — sino se cuelga indefinidamente cuando
  // el WebView no responde (ej. permission no concedida y no rejecta).
  function _getUserMediaWithTimeout(constraints, timeoutMs) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        reject(new Error('getUserMedia timeout (' + timeoutMs + 'ms)'));
      }, timeoutMs);
      navigator.mediaDevices.getUserMedia(constraints).then((stream) => {
        if (settled) {
          // Llegó tarde — liberar el stream que ya nadie usará
          try { stream.getTracks().forEach((t) => t.stop()); } catch {}
          return;
        }
        settled = true;
        clearTimeout(timer);
        resolve(stream);
      }).catch((err) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        reject(err);
      });
    });
  }

  async function openScanner() {
    if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
      setSetupStatus('Tu navegador no soporta acceso a cámara. Usa entrada manual.', 'error');
      return;
    }
    scannerOverlay.hidden = false;
    setScannerStatus('Pidiendo permiso de cámara...');

    // PASO 1 — pedir runtime permission via Capacitor (Android dialog).
    const permResult = await _requestCameraPermissionViaCapacitor();
    console.log('camera permission result:', permResult);
    if (!permResult.granted) {
      setScannerStatus(
        'Permiso de cámara denegado (' + permResult.note +
        '). Ve a Settings → Apps → Ashley → Permisos → Cámara para activar.',
        'error'
      );
      return;
    }

    setScannerStatus('Iniciando cámara...');

    // PASO 2 — abrir el stream con constraints progresivas + timeout.
    // El WebView de Capacitor a veces se cuelga si las constraints no
    // son soportadas. Timeout 5s por intento evita el "infinito".
    const attempts = [
      { video: { facingMode: 'environment' }, audio: false },
      { video: { facingMode: { ideal: 'environment' } }, audio: false },
      { video: true, audio: false },
    ];

    let lastError = null;
    scannerStream = null;
    for (let i = 0; i < attempts.length; i++) {
      try {
        scannerStream = await _getUserMediaWithTimeout(attempts[i], 5000);
        break;
      } catch (e) {
        lastError = e;
        console.warn('camera attempt', i + 1, 'failed:', e.name, e.message);
      }
    }

    if (!scannerStream) {
      const errName = (lastError && lastError.name) || 'UnknownError';
      const errMsg = (lastError && lastError.message) || '(sin detalle)';
      setScannerStatus(
        'Sin acceso a cámara: ' + errName + ' — ' + errMsg +
        '. Cierra otras apps de cámara o usa entrada manual.',
        'error'
      );
      return;
    }

    try {
      scannerVideo.srcObject = scannerStream;
      await scannerVideo.play();
      setScannerStatus('Apunta al QR del PC');
    } catch (e) {
      setScannerStatus('Error reproduciendo video: ' + (e.message || e.name), 'error');
      // Liberar stream para no dejar la cámara colgada
      try { scannerStream.getTracks().forEach((t) => t.stop()); } catch {}
      scannerStream = null;
      return;
    }

    // Detector — BarcodeDetector si está disponible (Chrome Android)
    if ('BarcodeDetector' in window) {
      try {
        scannerDetector = new window.BarcodeDetector({ formats: ['qr_code'] });
      } catch (e) {
        scannerDetector = null;
      }
    }

    if (!scannerDetector) {
      // Fallback: cargar jsQR dinámicamente desde CDN si no hay BarcodeDetector
      // Para v1 mostramos error sugiriendo manual entry
      setScannerStatus('Tu navegador no soporta detección de QR nativa. Usa entrada manual o Chrome reciente.', 'error');
      // Don't return — let the user close the overlay
    }

    if (scannerDetector) {
      scannerLoop();
    }
  }

  async function scannerLoop() {
    if (scannerOverlay.hidden) return;
    if (!scannerDetector || !scannerVideo.videoWidth) {
      scannerRafId = requestAnimationFrame(scannerLoop);
      return;
    }
    try {
      const codes = await scannerDetector.detect(scannerVideo);
      if (codes && codes.length > 0) {
        const raw = codes[0].rawValue || '';
        const handled = await onScannedQR(raw);
        if (handled) {
          closeScanner();
          return;
        }
      }
    } catch (e) {
      console.warn('detect err:', e);
    }
    scannerRafId = requestAnimationFrame(scannerLoop);
  }

  async function onScannedQR(raw) {
    // El payload del QR es JSON: {s: "http://...", t: "..."}
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setScannerStatus('QR no reconocido. ¿Es de Ashley?', 'error');
      return false;
    }
    const s = (parsed.s || parsed.server || '').trim().replace(/\/$/, '');
    const t = (parsed.t || parsed.token || '').trim();
    if (!s || !t) {
      setScannerStatus('QR incompleto.', 'error');
      return false;
    }

    setScannerStatus('Conectando a ' + s + '...', 'ok');
    serverUrl = s;
    token = t;
    const status = await fetchStatus();
    if (!status.ok || !status.paired) {
      setScannerStatus(
        status.error
          ? 'No se pudo conectar al PC. Revisa que esté encendido y misma red.'
          : 'Token rechazado por el PC. ¿QR caducado?',
        'error',
      );
      return false;
    }
    // Save
    localStorage.setItem(STORE_SERVER_URL, serverUrl);
    localStorage.setItem(STORE_TOKEN, token);
    setScannerStatus('Conectado.', 'ok');
    // Pequeña pausa para feedback visual
    await new Promise(r => setTimeout(r, 600));
    await tryConnect();
    return true;
  }

  function closeScanner() {
    scannerOverlay.hidden = true;
    if (scannerRafId) {
      cancelAnimationFrame(scannerRafId);
      scannerRafId = null;
    }
    if (scannerStream) {
      scannerStream.getTracks().forEach(t => t.stop());
      scannerStream = null;
    }
    scannerVideo.srcObject = null;
  }

  scanQrBtn.addEventListener('click', openScanner);
  scannerCloseBtn.addEventListener('click', closeScanner);
  scannerOverlay.querySelector('.overlay-backdrop').addEventListener('click', closeScanner);

  // ─── Setup flow ────────────────────────────────────────────────
  setupConnectBtn.addEventListener('click', async () => {
    const newServer = setupServerInput.value.trim().replace(/\/$/, '');
    const newToken  = setupTokenInput.value.trim();
    if (!newServer || !newToken) {
      setSetupStatus('Rellena ambos campos.', 'error');
      return;
    }
    setupConnectBtn.disabled = true;
    setSetupStatus('Probando conexión...', '');
    serverUrl = newServer;
    token = newToken;
    const status = await fetchStatus();
    if (!status.ok || !status.paired) {
      setSetupStatus(
        status.error
          ? 'No se pudo conectar: ' + status.error
          : 'Token incorrecto. Verifica el código que muestra Ashley en tu PC.',
        'error'
      );
      setupConnectBtn.disabled = false;
      return;
    }
    // Save and proceed
    localStorage.setItem(STORE_SERVER_URL, serverUrl);
    localStorage.setItem(STORE_TOKEN, token);
    setSetupStatus('Conectado.', 'ok');
    setupConnectBtn.disabled = false;
    await tryConnect();
  });

  // ─── Memories ──────────────────────────────────────────────────
  memoriesBtn.addEventListener('click', async () => {
    memoriesPanel.hidden = false;
    memoriesList.innerHTML = '<div class="memories-empty">Cargando...</div>';
    try {
      const facts = await fetchFacts();
      renderMemories(facts);
    } catch (e) {
      memoriesList.innerHTML = '<div class="memories-empty">Error cargando memorias</div>';
    }
  });
  memoriesClose.addEventListener('click', () => { memoriesPanel.hidden = true; });
  memoriesPanel.querySelector('.overlay-backdrop').addEventListener('click', () => {
    memoriesPanel.hidden = true;
  });

  // ─── Settings ──────────────────────────────────────────────────
  settingsBtn.addEventListener('click', () => {
    settingsServerInput.value = serverUrl;
    settingsTokenInput.value = token;
    // Cargar config de modo offline si existe
    const offlineCfg = loadOfflineConfig();
    if (offlineCfg) {
      settingsOfflineProvider.value = offlineCfg.provider || '';
      settingsOfflineKey.value = offlineCfg.apiKey || '';
      settingsOfflineModel.value = offlineCfg.model || '';
    } else {
      settingsOfflineProvider.value = '';
      settingsOfflineKey.value = '';
      settingsOfflineModel.value = '';
    }
    setOfflineStatus(null);
    settingsPanel.hidden = false;
  });
  settingsClose.addEventListener('click', () => { settingsPanel.hidden = true; });
  settingsPanel.querySelector('.overlay-backdrop').addEventListener('click', () => {
    settingsPanel.hidden = true;
  });
  settingsSaveBtn.addEventListener('click', async () => {
    const newServer = settingsServerInput.value.trim().replace(/\/$/, '');
    const newToken  = settingsTokenInput.value.trim();
    if (!newServer || !newToken) return;
    serverUrl = newServer;
    token = newToken;
    localStorage.setItem(STORE_SERVER_URL, serverUrl);
    localStorage.setItem(STORE_TOKEN, token);
    settingsPanel.hidden = true;
    stopPolling();
    await tryConnect();
  });
  settingsDisconnectBtn.addEventListener('click', () => {
    if (!confirm('¿Desconectar y borrar la configuración guardada?')) return;
    localStorage.removeItem(STORE_SERVER_URL);
    localStorage.removeItem(STORE_TOKEN);
    serverUrl = ''; token = ''; lastTimestamp = '';
    stopPolling();
    settingsPanel.hidden = true;
    showScreen('setup');
    setupServerInput.value = '';
    setupTokenInput.value = '';
    setSetupStatus('Configuración borrada.', '');
  });

  // ─── Modo offline (BYOK) — v0.18.2 ────────────────────────────
  // Lee/guarda config en IndexedDB del brain (compartido con brain/memory.js).
  // El config tiene {provider, apiKey, model} y permite que Ashley móvil
  // chatee directamente al LLM cuando el PC del user está apagado.
  const STORE_OFFLINE_CFG = 'ashley.mobile.offline_config';

  function loadOfflineConfig() {
    try {
      const raw = localStorage.getItem(STORE_OFFLINE_CFG);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch { return null; }
  }

  function saveOfflineConfig(cfg) {
    if (!cfg) {
      localStorage.removeItem(STORE_OFFLINE_CFG);
      return;
    }
    localStorage.setItem(STORE_OFFLINE_CFG, JSON.stringify(cfg));
  }

  function setOfflineStatus(text, kind) {
    if (!text) { settingsOfflineStatus.hidden = true; return; }
    settingsOfflineStatus.hidden = false;
    settingsOfflineStatus.textContent = text;
    settingsOfflineStatus.className = 'settings-status' + (kind ? ' ' + kind : '');
  }

  // Default models por provider
  const OFFLINE_DEFAULT_MODELS = {
    xai: 'grok-4-1-fast-non-reasoning',
    openrouter: 'x-ai/grok-4-fast',
  };
  const OFFLINE_BASE_URLS = {
    xai: 'https://api.x.ai/v1',
    openrouter: 'https://openrouter.ai/api/v1',
  };

  // Sincroniza el modelo placeholder cuando cambia el provider
  settingsOfflineProvider.addEventListener('change', () => {
    const p = settingsOfflineProvider.value;
    const def = OFFLINE_DEFAULT_MODELS[p];
    if (def && !settingsOfflineModel.value.trim()) {
      settingsOfflineModel.placeholder = def;
    }
  });

  // Test de conexión — hace una llamada mínima al endpoint
  settingsOfflineTestBtn.addEventListener('click', async () => {
    const provider = settingsOfflineProvider.value;
    const apiKey = settingsOfflineKey.value.trim();
    const model = settingsOfflineModel.value.trim() || OFFLINE_DEFAULT_MODELS[provider];

    if (!provider) {
      setOfflineStatus('Selecciona un proveedor primero.', 'error');
      return;
    }
    if (!apiKey) {
      setOfflineStatus('Falta la API key.', 'error');
      return;
    }

    setOfflineStatus('Probando conexión...', '');
    settingsOfflineTestBtn.disabled = true;
    try {
      const baseUrl = OFFLINE_BASE_URLS[provider];
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + apiKey,
      };
      if (provider === 'openrouter') {
        headers['HTTP-Referer'] = 'https://ashleyia.com/mobile';
        headers['X-Title'] = 'Ashley Mobile';
      }
      const res = await fetch(baseUrl + '/chat/completions', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: 'hi' }],
          max_tokens: 1,
          stream: false,
        }),
      });
      if (res.ok) {
        setOfflineStatus('✓ Conexión OK — modo offline listo.', 'ok');
      } else {
        const txt = await res.text().catch(() => '');
        setOfflineStatus(
          'Error ' + res.status + ': ' + (txt.slice(0, 120) || 'sin detalle'),
          'error'
        );
      }
    } catch (e) {
      setOfflineStatus('Error de red: ' + (e && e.message || e), 'error');
    } finally {
      settingsOfflineTestBtn.disabled = false;
    }
  });

  // Guardar config — solo si el provider está seleccionado y hay key
  settingsOfflineSaveBtn.addEventListener('click', () => {
    const provider = settingsOfflineProvider.value;
    const apiKey = settingsOfflineKey.value.trim();
    const model = settingsOfflineModel.value.trim();

    if (!provider) {
      // Vacío → desactivar modo offline
      saveOfflineConfig(null);
      setOfflineStatus('Modo offline desactivado.', 'ok');
      return;
    }
    if (!apiKey) {
      setOfflineStatus('Falta la API key.', 'error');
      return;
    }

    const cfg = {
      provider,
      apiKey,
      model: model || OFFLINE_DEFAULT_MODELS[provider] || null,
      baseUrl: OFFLINE_BASE_URLS[provider],
      saved_at: new Date().toISOString(),
    };
    saveOfflineConfig(cfg);
    setOfflineStatus('✓ Configuración guardada. Ashley podrá chatear sin tu PC.', 'ok');
  });

  // ─── Composer events ───────────────────────────────────────────
  sendBtn.addEventListener('click', handleSend);
  inputEl.addEventListener('keydown', (e) => {
    // Enter sends, Shift+Enter newline (only on real keyboards, not phone)
    if (e.key === 'Enter' && !e.shiftKey && !('ontouchstart' in window)) {
      e.preventDefault();
      handleSend();
    }
  });
  // Auto-resize textarea
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
  });

  // ─── Visibility detection — pause polling when hidden ─────────
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopPolling();
      stopSyncHeartbeat();
    } else if (serverUrl && token && !appScreen.hidden) {
      pollOnce();
      startPolling();
      // v0.18.2 — al volver a foreground, fuerza un sync inmediato. Si la
      // app estuvo en background N min, los datos del PC pueden haber
      // cambiado (Ashley desktop interactuó, recordatorios vencieron, etc.)
      autoSyncState({ force: true });
      startSyncHeartbeat();
      // Si hay mensajes pending creados offline mientras estaba hidden →
      // intentar push ahora que volvió.
      if (loadPending().length > 0) {
        flushPending();
      }
    }
  });

  // ─── Network status — push pending al recuperar conexión ────────
  // Si el browser detecta que volvió la red, fuerza sync. Cubre el caso
  // del user en modo avión que vuelve a la red, sin tener que esperar
  // al heartbeat de 5 min.
  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
      if (serverUrl && token && !appScreen.hidden) {
        autoSyncState({ force: true });
      }
    });
  }

  // ─── Init ──────────────────────────────────────────────────────
  tryConnect();
})();
