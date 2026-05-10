/* ════════════════════════════════════════════════════════════════════
 * Ashley 3D Bridge — IIFE en página principal de Reflex
 *
 * CRÍTICO: Reflex re-renderiza el portrait_panel en cada State change,
 * lo que destruiría el iframe (perdiendo WebGL context + recargando el
 * VRM de 47MB). Solución: el bridge CREA el iframe vía JS y lo inserta
 * en un mount div ESTÁTICO. React no toca el iframe porque no es parte
 * de su virtual DOM.
 *
 * Comunicación:
 *   State.mood (Python) → DOM data-mood en mount div → MutationObserver
 *     → postMessage al iframe → setMood() interno
 *   document.mousemove (parent) → coords normalizadas → postMessage
 * ════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const MOUNT_ID = 'ashley-3d-mount';
  const IFRAME_ID = 'ashley-3d-iframe';
  const WIDGET_URL = '/ashley_3d_widget.html';

  let iframe = null;
  let mountDiv = null;
  let iframeReady = false;
  let lastMoodSent = null;
  let lastTalkingSent = null;
  let lastCursorSent = 0;
  let mountObserver = null;
  let moodObserver = null;

  function post(msg) {
    if (!iframe || !iframe.contentWindow) return;
    try { iframe.contentWindow.postMessage(msg, '*'); } catch {}
  }

  // ─── Crear el iframe e insertarlo en el mount div ─────────────
  function createIframe(mount) {
    if (iframe && iframe.parentNode === mount) return;
    if (iframe && iframe.parentNode) iframe.parentNode.removeChild(iframe);
    iframe = document.createElement('iframe');
    iframe.id = IFRAME_ID;
    iframe.src = WIDGET_URL;
    iframe.style.cssText = 'position:absolute; inset:0; width:100%; height:100%; border:0; background:transparent; pointer-events:none;';
    iframe.setAttribute('allow', 'autoplay');
    // sandbox no — necesitamos same-origin para que esm.sh funcione bien
    mount.appendChild(iframe);
    iframeReady = false; // resetear hasta que el iframe nos diga 'ready'
  }

  // ─── Atender mensajes del iframe ──────────────────────────────
  window.addEventListener('message', (e) => {
    if (!e.data || typeof e.data !== 'object') return;
    if (e.data.type === 'ashley3d:ready') {
      iframeReady = true;
      // Reenviar mood actual por si se cargó tarde (talking solo viene de TTS events)
      const mood = (mountDiv && mountDiv.getAttribute('data-mood')) || 'default';
      lastMoodSent = mood;
      post({ type: 'ashley3d:setMood', mood });
    }
  });

  // ─── Watch de data-mood en el mount div ──────────────────────
  // NOTA: data-talking (que viene de State.is_thinking) NO se usa para
  // animar la boca — eso solo sucede cuando hay audio TTS REAL playing
  // (eventos 'ashley:ttsStart'/'ashley:ttsEnd' de ashley_voice.js).
  // Sin este cambio, la boca se movía mientras el LLM generaba texto pero
  // ANTES de que el TTS empezara a sonar — efecto no deseado.
  function watchMood(mount) {
    if (moodObserver) moodObserver.disconnect();
    moodObserver = new MutationObserver(() => {
      const mood = mount.getAttribute('data-mood') || 'default';
      if (mood !== lastMoodSent) {
        lastMoodSent = mood;
        if (iframeReady) post({ type: 'ashley3d:setMood', mood });
      }
    });
    // attributeOldValue: false (no necesitamos diff completo, solo el valor actual)
    moodObserver.observe(mount, {
      attributes: true,
      attributeFilter: ['data-mood'],
      attributeOldValue: false,
    });
  }

  // ─── AUDIO LIPSYNC (Web Audio API) ────────────────────────────
  // Monitorea TODOS los <audio> de la página (TTS de Ashley vía ElevenLabs,
  // Kokoro, VoiceVox, etc.) y manda amplitud RMS al iframe cada frame.
  // El iframe usa esa amplitud para mover los visemes en sincronía REAL
  // con la voz, no random. Si no hay audio (Web Speech API o TTS off),
  // cae en el fallback fake basado en data-talking.
  let audioCtx = null, analyser = null, dataArr = null;
  const wiredAudios = new WeakSet();
  let amplitudeRunning = false;

  function ensureAudioCtx() {
    if (audioCtx) return audioCtx;
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.4;  // suavizado natural
      dataArr = new Uint8Array(analyser.fftSize);
      // resumir ctx tras user gesture (Chrome lo bloquea sin interacción)
      const resume = () => { if (audioCtx.state === 'suspended') audioCtx.resume(); };
      document.addEventListener('click', resume);
      document.addEventListener('keydown', resume);
      document.addEventListener('touchstart', resume);
    } catch (e) {
      console.warn('[ashley3d] audioCtx falló:', e);
    }
    return audioCtx;
  }

  function wireAudioElement(audioEl) {
    if (!audioEl || wiredAudios.has(audioEl)) return;
    if (!ensureAudioCtx()) return;
    try {
      const src = audioCtx.createMediaElementSource(audioEl);
      src.connect(analyser);
      analyser.connect(audioCtx.destination);
      wiredAudios.add(audioEl);
    } catch (e) {
      // Posibles errores: ya wireado, CORS, audio cross-origin sin headers
      // (no se puede analizar audio cross-origin sin CORS). Marcamos igual
      // para no reintentar.
      wiredAudios.add(audioEl);
    }
  }

  // Loop de RMS — corre siempre tras montar audioCtx, manda amplitud al iframe.
  // OPTIMIZADO: throttle a 25fps (cada 40ms) en lugar de 60fps. La boca no
  // necesita 60fps de actualización, y reduce postMessage flood al iframe
  // significativamente — clave para evitar lag durante respuestas streaming.
  function startAmplitudeLoop() {
    if (amplitudeRunning) return;
    amplitudeRunning = true;
    let lastSent = 0;
    let lastTickAt = 0;
    function tick() {
      requestAnimationFrame(tick);
      if (!analyser || !iframeReady) return;
      const now = performance.now();
      if (now - lastTickAt < 40) return;  // cap ~25fps — skip TODO el work
      lastTickAt = now;
      analyser.getByteTimeDomainData(dataArr);
      let sum = 0;
      for (let i = 0; i < dataArr.length; i++) {
        const v = (dataArr[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / dataArr.length);
      const amp = rms < 0.005 ? 0 : Math.min(1, rms * 4);
      if (Math.abs(amp - lastSent) > 0.03 || (amp === 0 && lastSent !== 0)) {
        lastSent = amp;
        post({ type: 'ashley3d:audioAmp', amp });
      }
    }
    tick();
  }

  // Observar nuevos <audio> elements en el DOM (también capta los Audio()
  // creados en JS PERO sólo si se appendChild al DOM — ashley_voice.js NO
  // hace eso, los crea con `new Audio()` y reproduce directamente. Por eso
  // también escuchamos los eventos custom 'ashley:ttsStart'/'ashley:ttsEnd'
  // que ashley_voice.js dispatcha — esos sí nos dan el audio element y
  // sabemos exactamente cuándo el TTS empieza/termina.
  function setupAudioMonitoring() {
    document.querySelectorAll('audio').forEach(wireAudioElement);
    const obs = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.tagName === 'AUDIO') wireAudioElement(node);
          if (node.querySelectorAll) {
            node.querySelectorAll('audio').forEach(wireAudioElement);
          }
        }
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });

    // ── Eventos custom de ashley_voice.js ──
    // ashley_voice dispatcha estos eventos al iniciar/terminar play del audio
    // del backend TTS. Wireamos el audio para analysis Y forzamos talking=true
    // durante el playback completo (independientemente del data-talking).
    window.addEventListener('ashley:ttsStart', (e) => {
      const audio = e.detail?.audio;
      if (audio) wireAudioElement(audio);
      lastTalkingSent = true;
      if (iframeReady) post({ type: 'ashley3d:setTalking', talking: true });
    });
    window.addEventListener('ashley:ttsEnd', () => {
      lastTalkingSent = false;
      if (iframeReady) post({ type: 'ashley3d:setTalking', talking: false });
    });

    startAmplitudeLoop();
  }

  // ─── Cursor tracking + proximity ──────────────────────────────
  // OPTIMIZADO: el bounding rect del iframe se cachea cada 500ms en lugar
  // de calcularse en cada cursormove (getBoundingClientRect causa layout
  // thrashing si se llama 30+ veces/seg, mata el rendimiento).
  // También: cursor throttle bajado a 50ms (~20fps) — más que suficiente.
  let cachedRect = null;
  let cachedRectAt = 0;
  function getIframeRect() {
    const now = performance.now();
    if (cachedRect && now - cachedRectAt < 500) return cachedRect;
    if (!iframe) return null;
    cachedRect = iframe.getBoundingClientRect();
    cachedRectAt = now;
    return cachedRect;
  }
  function calcProximity(clientX, clientY) {
    const rect = getIframeRect();
    if (!rect || rect.width === 0 || rect.height === 0) return 0;
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = clientX - cx;
    const dy = clientY - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const radius = Math.max(rect.width, rect.height) * 0.6;
    return Math.max(0, Math.min(1, 1 - dist / radius));
  }
  // Invalidar cache del rect en resize (panel cambia tamaño)
  window.addEventListener('resize', () => { cachedRect = null; }, { passive: true });

  function setupCursorTracking() {
    document.addEventListener('mousemove', (e) => {
      const now = performance.now();
      if (now - lastCursorSent < 50) return;  // ~20fps cap (era 30fps)
      lastCursorSent = now;
      const nx = e.clientX / window.innerWidth;
      const ny = e.clientY / window.innerHeight;
      const proximity = calcProximity(e.clientX, e.clientY);
      post({ type: 'ashley3d:cursor', nx, ny, proximity });
    }, { passive: true });
  }

  // ─── Tratar de encontrar y montar el iframe ───────────────────
  function tryMount() {
    const mount = document.getElementById(MOUNT_ID);
    if (!mount) return false;
    // Si el mount actual es el mismo Y nuestro iframe sigue dentro, no hacer nada
    if (mount === mountDiv && iframe && iframe.parentNode === mount && document.body.contains(iframe)) {
      return true;
    }
    // Mount nuevo o iframe perdido → re-insertar
    mountDiv = mount;
    createIframe(mount);
    watchMood(mount);
    return true;
  }

  // ─── Init: SIEMPRE observa el DOM (no se desconecta al encontrar) ──
  // React/Reflex puede destruir el mount div en cualquier re-render.
  // Mantenemos el observer activo permanentemente para re-insertar el
  // iframe si eso pasa. Coste despreciable (1 callback por mutación).
  function init() {
    setupCursorTracking();
    setupAudioMonitoring();
    tryMount();  // intentar inmediato
    // Observer permanente del body — re-monta si React destruye el mount
    mountObserver = new MutationObserver(() => {
      tryMount();
    });
    mountObserver.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(init, 100);
  } else {
    document.addEventListener('DOMContentLoaded', () => setTimeout(init, 100));
  }
})();
