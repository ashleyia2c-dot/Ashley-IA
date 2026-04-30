/* ashley_voice.js — Voz de Ashley (TTS + STT)
 *
 * STT: MediaRecorder → endpoint local /api/transcribe (faster-whisper en Python)
 * TTS: Web Speech (gratis) o ElevenLabs (si hay key)
 *
 * MODO DIAGNÓSTICO: esta versión loguea TODO con [ashley-voice] y muestra
 * errores visibles con alert() para poder debuggear fácilmente.
 */

(function () {
  if (window._ashleyVoiceLoaded) return;
  window._ashleyVoiceLoaded = true;

  const ELEVEN_DEFAULT_VOICE = 'EXAVITQu4vr4xnSDxMaL';
  const LOG_PREFIX = '[ashley-voice]';

  function log(...args)  { try { console.log(LOG_PREFIX, ...args); } catch {} }
  function warn(...args) { try { console.warn(LOG_PREFIX, ...args); } catch {} }
  function err(...args)  { try { console.error(LOG_PREFIX, ...args); } catch {} }

  const V = {
    // ─── State ──────────────────────────────────────────────
    lang: 'en',
    ttsEnabled: false,
    elevenKey: '',
    voiceId: ELEVEN_DEFAULT_VOICE,
    // v0.12: voice provider — 'webspeech' (default) | 'elevenlabs' | 'kokoro' | 'voicevox'
    // Everything except webspeech is handled server-side via /api/tts;
    // webspeech is handled in-browser via SpeechSynthesis.
    voiceProvider: 'webspeech',
    backendPort: '',            // resolved from DOM marker; empty = error

    mediaStream: null,
    mediaRecorder: null,
    audioChunks: [],
    isListening: false,
    isTranscribing: false,
    recordStartTs: 0,

    // VAD (Voice Activity Detection) — auto-stop tras silencio
    _vadCtx: null,          // AudioContext para analizar volumen
    _vadAnalyser: null,     // AnalyserNode
    _vadPollId: null,       // setInterval ID
    _vadHasSpeech: false,   // true tras detectar habla por primera vez
    _vadSilentFrames: 0,    // frames consecutivos bajo el threshold
    _VAD_THRESHOLD: 10,     // volumen mínimo para considerar "habla" (0-255)
    _VAD_SILENCE_SECS: 2,   // v0.16.13 — 3 → 2 para envío más reactivo tras
                            // que el user calle. Si te corta a mitad de
                            // frase por pausas naturales largas, subir a 2.5
                            // o 3. La variable también controla el comentario
                            // del log en _startVAD.

    currentAudio: null,
    lastSpokenMsgId: null,
    _bootstrapped: false,     // true tras el primer tick (baseline tomado)
    _prevMessageCount: 0,     // cantidad de mensajes Ashley en el último tick

    _alert(msg) {
      warn('ALERT:', msg);
      try { alert(msg); } catch {}
    },

    _i18n(enMsg, esMsg) {
      return this.lang === 'es' ? esMsg : enMsg;
    },

    // ─── STT — MediaRecorder + Whisper local ────────────────
    async _startRecording() {
      log('toggleListening → _startRecording');

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        this._alert(this._i18n(
          'Microphone API not available in this environment.',
          'La API de micrófono no está disponible en este entorno.'
        ));
        return;
      }

      log('Requesting getUserMedia({ audio: true })...');
      try {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        log('getUserMedia OK. Tracks:', this.mediaStream.getAudioTracks().length);
      } catch (e) {
        err('getUserMedia failed:', e);
        this._alert(this._i18n(
          'Could not access microphone.\n\nError: ' + (e.name || '') + ' — ' + (e.message || e) +
          '\n\nCheck Windows Settings → Privacy → Microphone → make sure apps can access it.',
          'No pude acceder al micrófono.\n\nError: ' + (e.name || '') + ' — ' + (e.message || e) +
          '\n\nRevisa Configuración de Windows → Privacidad → Micrófono → permite acceso a apps.'
        ));
        return;
      }

      // Validar que el stream tenga tracks activos
      const tracks = this.mediaStream.getAudioTracks();
      if (!tracks.length) {
        this._alert('Stream has no audio tracks!');
        this._releaseStream();
        return;
      }
      const t0 = tracks[0];
      log('Track:', { label: t0.label, enabled: t0.enabled, muted: t0.muted, readyState: t0.readyState });
      if (t0.readyState !== 'live' || t0.muted) {
        this._alert(this._i18n(
          'Audio track is not live (muted or stopped).\n\nreadyState: ' + t0.readyState + '\nmuted: ' + t0.muted,
          'La pista de audio no está activa.\n\nreadyState: ' + t0.readyState + '\nmuted: ' + t0.muted
        ));
        this._releaseStream();
        return;
      }

      // Elegir mimeType con fallbacks robustos
      const candidates = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/ogg',
        'audio/mp4',
        '',  // dejar que el browser elija
      ];
      let mimeType = '';
      for (const c of candidates) {
        if (c === '' || (window.MediaRecorder && MediaRecorder.isTypeSupported(c))) {
          mimeType = c;
          break;
        }
      }
      log('Selected mimeType:', mimeType || '(browser default)');

      try {
        this.mediaRecorder = mimeType
          ? new MediaRecorder(this.mediaStream, { mimeType })
          : new MediaRecorder(this.mediaStream);
        log('MediaRecorder created. state:', this.mediaRecorder.state, 'actualMimeType:', this.mediaRecorder.mimeType);
      } catch (e) {
        err('MediaRecorder construction failed:', e);
        this._releaseStream();
        this._alert('MediaRecorder construction failed: ' + (e.message || e));
        return;
      }

      this.audioChunks = [];
      this.mediaRecorder.ondataavailable = (e) => {
        log('ondataavailable, size:', e.data && e.data.size);
        if (e.data && e.data.size > 0) this.audioChunks.push(e.data);
      };
      this.mediaRecorder.onstart = () => {
        log('MediaRecorder onstart fired. state:', this.mediaRecorder.state);
      };
      this.mediaRecorder.onstop = async () => {
        const duration = ((Date.now() - this.recordStartTs) / 1000).toFixed(1);
        log('MediaRecorder onstop fired. duration:', duration + 's', 'chunks:', this.audioChunks.length);
        const blob = new Blob(this.audioChunks, { type: this.mediaRecorder.mimeType || 'audio/webm' });
        log('Blob size:', blob.size, 'bytes, type:', blob.type);
        this._releaseStream();
        this.isListening = false;
        this._updateMicState();
        if (blob.size < 1000) {
          this._alert(this._i18n(
            'Recording too short (' + blob.size + ' bytes). Hold the button and speak.',
            'Grabación demasiado corta (' + blob.size + ' bytes). Pulsa y habla unos segundos.'
          ));
          return;
        }
        await this._transcribe(blob);
      };
      this.mediaRecorder.onerror = (ev) => {
        const e = ev && ev.error;
        err('MediaRecorder ONERROR fired:', e);
        this._releaseStream();
        this.isListening = false;
        this._updateMicState();
        this._alert(this._i18n(
          'MediaRecorder crashed:\n\n' + (e && e.name ? e.name + ': ' : '') + (e && e.message ? e.message : JSON.stringify(ev)),
          'El grabador falló:\n\n' + (e && e.name ? e.name + ': ' : '') + (e && e.message ? e.message : JSON.stringify(ev))
        ));
      };

      try {
        this.mediaRecorder.start(250); // emitir chunks cada 250ms
        this.recordStartTs = Date.now();
        this.isListening = true;
        this._updateMicState();
        log('MediaRecorder.start() called successfully. state:', this.mediaRecorder.state);

        // Pausar wake word detector mientras grabamos manual. El backend
        // ignora silently si el detector no estaba corriendo (idempotente).
        this._wakeWordPause();

        // ── VAD: auto-stop tras 2s de silencio después de hablar ──
        this._startVAD();
      } catch (e) {
        err('MediaRecorder.start() failed:', e);
        this._releaseStream();
        this._alert('Could not start recording: ' + (e.message || e));
      }
    },

    _stopRecording() {
      log('toggleListening → _stopRecording');
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        try {
          this.mediaRecorder.stop();
          log('stop() called, waiting for onstop...');
        } catch (e) {
          err('stop() error:', e);
        }
      } else {
        warn('_stopRecording called but recorder not recording. state:',
             this.mediaRecorder ? this.mediaRecorder.state : 'null');
        this._releaseStream();
        this.isListening = false;
        this._updateMicState();
      }
      // Reanudar el wake word detector cuando termine la grabación manual.
      // Lo llamamos en _stopRecording (no en onstop) porque el user puede
      // pulsar stop sin que onstop se haya disparado todavía — preferimos
      // resume early que tarde.
      this._wakeWordResume();
    },

    // ── Wake word pause/resume hooks ────────────────────────
    // El backend Python tiene un detector de wake word que escucha "Ashley"
    // en background. Cuando el user pulsa el botón mic para grabar manual,
    // pausamos el detector para que no compita por el mic ni dispare un
    // STT-en-medio-de-STT. Idempotente: si el detector no está activo,
    // los endpoints son no-op (devuelven {"ok": true}).
    async _wakeWordPause() {
      try {
        const port = this._getApiPort();
        await fetch(`http://localhost:${port}/api/wake_word/pause`,
                    { method: 'POST', cache: 'no-store' });
      } catch (_e) { /* silent — no crítico */ }
    },
    async _wakeWordResume() {
      try {
        const port = this._getApiPort();
        await fetch(`http://localhost:${port}/api/wake_word/resume`,
                    { method: 'POST', cache: 'no-store' });
      } catch (_e) { /* silent — no crítico */ }
    },
    _getApiPort() {
      // Mismo patrón que el resto de fetches en este file — Electron pasa
      // ASHLEY_BACKEND_PORT via window injection, dev usa puerto default.
      return (window.ASHLEY_BACKEND_PORT || window.location.port || 17800);
    },

    // ─── VAD: Voice Activity Detection ─────────────────────
    _startVAD() {
      try {
        this._vadCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source = this._vadCtx.createMediaStreamSource(this.mediaStream);
        this._vadAnalyser = this._vadCtx.createAnalyser();
        this._vadAnalyser.fftSize = 512;
        source.connect(this._vadAnalyser);

        this._vadHasSpeech = false;
        this._vadSilentFrames = 0;
        const freqData = new Uint8Array(this._vadAnalyser.frequencyBinCount);
        const FRAMES_NEEDED = this._VAD_SILENCE_SECS * 10; // poll cada 100ms

        this._vadPollId = setInterval(() => {
          if (!this.isListening) {
            this._stopVAD();
            return;
          }
          this._vadAnalyser.getByteFrequencyData(freqData);
          const avg = freqData.reduce((a, b) => a + b, 0) / freqData.length;

          if (avg > this._VAD_THRESHOLD) {
            // Detectó sonido/habla
            this._vadHasSpeech = true;
            this._vadSilentFrames = 0;
          } else if (this._vadHasSpeech) {
            // Silencio después de hablar
            this._vadSilentFrames++;
            if (this._vadSilentFrames >= FRAMES_NEEDED) {
              log('VAD: ' + this._VAD_SILENCE_SECS + 's silence after speech → auto-stop');
              this._stopVAD();
              this._stopRecording();
            }
          }
          // Si aún no ha hablado (vadHasSpeech=false), no cuenta silencio.
          // Así el usuario puede tomarse su tiempo antes de empezar a hablar.
        }, 100);
        log('VAD started. Threshold:', this._VAD_THRESHOLD, 'Silence:', this._VAD_SILENCE_SECS + 's');
      } catch (e) {
        warn('VAD setup failed (non-critical):', e);
      }
    },

    _stopVAD() {
      if (this._vadPollId) {
        clearInterval(this._vadPollId);
        this._vadPollId = null;
      }
      if (this._vadCtx) {
        try { this._vadCtx.close(); } catch {}
        this._vadCtx = null;
      }
      this._vadAnalyser = null;
    },

    _releaseStream() {
      this._stopVAD();
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach((t) => { try { t.stop(); } catch {} });
        this.mediaStream = null;
      }
    },

    async _transcribe(blob) {
      log('_transcribe starting. blob:', blob.size, 'bytes');
      if (!this.backendPort) {
        this._alert('Backend port not configured. Restart Ashley.');
        return;
      }
      this.isTranscribing = true;
      this._updateMicState();

      // IMPORTANTE: apuntamos DIRECTO al backend Python (puerto distinto del
      // frontend). El frontend (Next.js) no tiene esta ruta y devuelve 405.
      const url = `http://127.0.0.1:${this.backendPort}/api/transcribe?lang=${encodeURIComponent(this.lang || 'en')}`;
      log('POST', url);

      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/octet-stream' },
          body: blob,
        });
        log('transcribe response status:', resp.status);
        if (!resp.ok) {
          let errMsg = 'HTTP ' + resp.status;
          try {
            const data = await resp.json();
            if (data && data.error) errMsg = data.error;
          } catch {}
          // 503 = error de carga conocido (load_error cacheado).
          // 500 = exception genérico, posiblemente primera carga aún en marcha.
          // Otros = transient.
          const helpHint = resp.status === 500
            ? '\n\nFirst use loads the speech model. Try again in 30 seconds.'
            : '';
          const helpHintEs = resp.status === 500
            ? '\n\nEl primer uso carga el modelo de voz. Prueba en 30 segundos.'
            : '';
          this._alert(this._i18n(
            'Transcription error: ' + errMsg + helpHint,
            'Error de transcripción: ' + errMsg + helpHintEs,
          ));
          return;
        }
        const data = await resp.json();
        log('transcribe result:', data);

        // ── Modelo descargándose o cargando — mostrar banner y esperar ──
        // v0.16.13 — distinguimos 2 estados:
        //   - 'downloading': primera vez real, ~245 MB de internet (~1-5 min).
        //   - 'loading':     ya en disco, cargando a RAM (~5-15s).
        // Antes solo había 'downloading' aunque el modelo ya estuviera
        // descargado, lo que confundía al user en cada primera vez por sesión.
        if (data.status === 'downloading' || data.status === 'loading') {
          const msg = this._i18n(
            data.message || (data.status === 'loading' ? 'Loading...' : 'Downloading...'),
            data.message_es || (data.status === 'loading' ? 'Cargando...' : 'Descargando...'),
          );
          this._showDownloadBanner(msg);
          log('Model ' + data.status + ' — polling /api/whisper/status until ready...');
          const ready = await this._waitForModelReady();
          this._hideDownloadBanner();
          if (ready) {
            log('Model ready — retrying transcription');
            return this._transcribe(blob);  // reintentar con el audio original
          } else {
            this._alert(this._i18n(
              'Model ' + data.status + ' failed or timed out. Please restart Ashley and try again.',
              (data.status === 'loading'
                ? 'La carga del modelo falló o tardó demasiado. Reinicia Ashley e intenta otra vez.'
                : 'La descarga del modelo falló o tardó demasiado. Reinicia Ashley e intenta otra vez.')
            ));
            return;
          }
        }

        const text = (data && data.text) ? String(data.text).trim() : '';
        if (text) {
          this._setInputValue(text);
          this._submitInputForm();   // ← auto-envía tras dictar
        } else {
          this._alert(this._i18n(
            'No speech detected. Try speaking closer to the microphone.',
            'No detecté habla. Prueba acercándote al micrófono.'
          ));
        }
      } catch (e) {
        err('transcribe fetch error:', e);
        this._alert(this._i18n(
          'Network error transcribing: ' + (e.message || e),
          'Error de red transcribiendo: ' + (e.message || e)
        ));
      } finally {
        this.isTranscribing = false;
        this._updateMicState();
      }
    },

    _setInputValue(text) {
      const ta = document.querySelector('textarea#message');
      if (!ta) return;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
      ).set;
      const existing = (ta.value || '').trim();
      const combined = existing ? (existing + ' ' + text) : text;
      setter.call(ta, combined);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      ta.style.height = 'auto';
      ta.style.height = Math.min(ta.scrollHeight, 180) + 'px';
      ta.focus();
    },

    // Auto-envía el formulario tras transcribir (UX hands-free real).
    _submitInputForm() {
      const ta = document.querySelector('textarea#message');
      if (!ta) { warn('submitInputForm: textarea#message not found'); return; }
      const form = ta.closest('form');
      if (!form) { warn('submitInputForm: no form found'); return; }
      log('Auto-submitting form after transcription');
      // Pequeño delay para que Reflex reciba el input event antes del submit
      setTimeout(() => {
        if (form.requestSubmit) {
          form.requestSubmit();
        } else {
          const btn = form.querySelector('button[type="submit"]');
          if (btn) btn.click();
        }
      }, 120);
    },

    toggleListening() {
      log('toggleListening() called. isListening:', this.isListening, 'isTranscribing:', this.isTranscribing);
      if (this.isTranscribing) {
        log('already transcribing, ignoring click');
        return;
      }
      if (this.isListening) this._stopRecording();
      else this._startRecording();
    },

    _updateMicState() {
      document.body.classList.toggle('mic-listening', this.isListening);
      document.body.classList.toggle('mic-transcribing', this.isTranscribing);
      const btn = document.querySelector('#ashley-mic-btn');
      if (btn) {
        btn.setAttribute('aria-pressed', this.isListening ? 'true' : 'false');
        btn.setAttribute('aria-busy', this.isTranscribing ? 'true' : 'false');
      }
    },

    // ─── TTS — limpieza de texto ────────────────────────────
    _cleanForSpeech(text) {
      return (text || '')
        .replace(/\[mood:[^\]]+\]/gi, '')
        .replace(/\[action:[^\]]+\]/gi, '')
        .replace(/\*[^*\n]{2,120}\*/g, '')
        .replace(/[*_`~]+/g, '')
        .replace(/\s+/g, ' ')
        .trim();
    },

    _pickWebVoice() {
      const voices = window.speechSynthesis.getVoices();
      if (!voices.length) return null;
      const prefNames = this.lang === 'es'
        ? ['Sabina', 'Helena', 'Lucia', 'Paloma', 'Monica']
        : ['Samantha', 'Zira', 'Aria', 'Ava', 'Karen', 'Jenny'];
      for (const name of prefNames) {
        const v = voices.find((x) => x.name && x.name.includes(name));
        if (v) return v;
      }
      return voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(this.lang))
          || voices[0];
    },

    _speakWebSpeech(text) {
      try {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = this.lang === 'es' ? 'es-ES' : 'en-US';
        u.rate = 1.0;
        u.pitch = 1.08;
        const v = this._pickWebVoice();
        if (v) u.voice = v;
        window.speechSynthesis.speak(u);
      } catch (e) {
        err('Web Speech TTS error:', e);
      }
    },

    // v0.12: generic backend TTS — Python route /api/tts dispatches to
    // ElevenLabs / Kokoro / VoiceVox based on voice_provider in voice.json.
    // JS doesn't know which one, just gets audio bytes back (or 204 = no
    // content, which means we should fall back to Web Speech).
    async _speakBackendTTS(text) {
      if (!this.backendPort) {
        this._alert('Backend port not configured. Restart Ashley.');
        return;
      }
      const url = `http://127.0.0.1:${this.backendPort}/api/tts`;
      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, provider: this.voiceProvider }),
        });
        // 204 = backend says "webspeech provider, you handle it"
        if (resp.status === 204) {
          this._speakWebSpeech(text);
          return;
        }
        if (!resp.ok) {
          let errMsg = 'HTTP ' + resp.status;
          try {
            const j = await resp.json();
            if (j.error) errMsg = j.error;
            if (j.detail) errMsg += ' — ' + j.detail;
          } catch {}
          err('TTS proxy error:', errMsg);
          this._alertTTSOnce(errMsg);
          this._speakWebSpeech(text);
          return;
        }
        const blob = await resp.blob();
        log('Backend TTS audio received:', blob.size, 'bytes, type:', blob.type);
        const obj = URL.createObjectURL(blob);
        this.stopSpeaking();
        const audio = new Audio(obj);
        this.currentAudio = audio;
        audio.play().catch((e) => warn('audio.play():', e));
        audio.onended = () => {
          URL.revokeObjectURL(obj);
          if (this.currentAudio === audio) this.currentAudio = null;
        };
      } catch (e) {
        err('TTS fetch error:', e);
        this._alertTTSOnce('Network: ' + (e.message || e));
        this._speakWebSpeech(text);
      }
    },

    _lastTTSError: '',
    _alertTTSOnce(msg) {
      // Solo alertamos una vez por error distinto (no spamear)
      if (msg === this._lastTTSError) return;
      this._lastTTSError = msg;
      const providerName = (this.voiceProvider || 'TTS').toString();
      this._alert(this._i18n(
        providerName + ' failed:\n\n' + msg + '\n\nFalling back to the free Windows voice. ' +
        'Check Settings or make sure the local server is running.',
        providerName + ' falló:\n\n' + msg + '\n\nUsando la voz gratuita de Windows. ' +
        'Revisa Ajustes o verifica que el servidor local esté corriendo.'
      ));
    },

    speak(text) {
      if (!this.ttsEnabled) return;
      this._doSpeak(text);
    },

    testSpeak(text) { this._doSpeak(text); },

    _doSpeak(text) {
      const clean = this._cleanForSpeech(text);
      if (!clean) return;
      // Routing basado en voice_provider — todas las opciones no-webspeech
      // pasan por /api/tts (el backend dispatcha al provider real).
      const p = (this.voiceProvider || 'webspeech').toLowerCase();
      if (p === 'webspeech') {
        this._speakWebSpeech(clean);
      } else {
        this._speakBackendTTS(clean);
      }
    },

    stopSpeaking() {
      try { window.speechSynthesis.cancel(); } catch {}
      if (this.currentAudio) {
        try { this.currentAudio.pause(); } catch {}
        this.currentAudio = null;
      }
    },

    _chatBox() { return document.getElementById('chat_messages'); },

    _latestAshleyMessage() {
      const box = this._chatBox();
      if (!box) return null;
      const msgs = box.querySelectorAll('.ashley-msg');
      return msgs.length ? msgs[msgs.length - 1] : null;
    },

    _isStreaming() {
      return !!document.querySelector('.cursor-blink');
    },

    _tickObserver() {
      const box = this._chatBox();
      if (!box) return;
      const msgs = box.querySelectorAll('.ashley-msg');

      // Primer tick: baseline del historial existente, SIN leer nada.
      // Evita que Ashley "lea" el último mensaje al abrir la app
      // (gastaría tokens de ElevenLabs inútilmente).
      if (!this._bootstrapped) {
        this._prevMessageCount = msgs.length;
        this._bootstrapped = true;
        log('TTS observer bootstrapped with', msgs.length, 'existing messages (not reading)');
        return;
      }

      if (!this.ttsEnabled) return;
      if (this._isStreaming()) return;
      if (msgs.length === 0 || msgs.length <= this._prevMessageCount) return;

      // Hay un mensaje nuevo desde el último tick → lo leemos
      this._prevMessageCount = msgs.length;
      const latest = msgs[msgs.length - 1];
      const text = (latest.textContent || '').trim();
      if (text) this.speak(text);
    },

    _syncFromState() {
      const el = document.getElementById('ashley-voice-state');
      if (!el) return;
      this.lang = el.getAttribute('data-lang') || 'en';
      this.ttsEnabled = (el.getAttribute('data-tts') || 'off') === 'on';
      this.elevenKey = el.getAttribute('data-el-key') || '';
      this.voiceId = el.getAttribute('data-voice-id') || ELEVEN_DEFAULT_VOICE;
      // v0.12: which backend voices Ashley? Defaults to webspeech if missing.
      const provider = (el.getAttribute('data-voice-provider') || '').toLowerCase();
      this.voiceProvider = provider || 'webspeech';
      this.backendPort = el.getAttribute('data-backend-port') || '';
      if (!this.backendPort) {
        warn('No backend port found in DOM marker — STT/TTS will fail');
      }
      if (!this.ttsEnabled) this.stopSpeaking();
    },

    // ─── Banner de descarga (visible al usuario) ──────────────
    _showDownloadBanner(msg) {
      let el = document.getElementById('ashley-download-banner');
      if (!el) {
        el = document.createElement('div');
        el.id = 'ashley-download-banner';
        el.style.cssText =
          'position:fixed;bottom:90px;left:50%;transform:translateX(-50%);' +
          'background:#1a1a2e;color:#ff9aee;padding:14px 28px;border-radius:14px;' +
          'border:1px solid rgba(255,154,238,0.5);font-size:13px;z-index:9999;' +
          'font-family:"Segoe UI",sans-serif;box-shadow:0 6px 30px rgba(0,0,0,0.6);' +
          'display:flex;align-items:center;gap:12px;max-width:500px;text-align:center;';
        document.body.appendChild(el);
      }
      // Spinner inline
      el.innerHTML =
        '<div style="width:20px;height:20px;border:2px solid #333;border-top-color:#ff9aee;' +
        'border-radius:50%;animation:spin 0.8s linear infinite;flex-shrink:0"></div>' +
        '<span>' + msg + '</span>';
      el.style.display = 'flex';
    },

    _hideDownloadBanner() {
      const el = document.getElementById('ashley-download-banner');
      if (el) el.style.display = 'none';
    },

    // Espera a que el modelo esté listo (polling cada 3s, max 3 min)
    async _waitForModelReady() {
      const MAX_POLLS = 60;  // 60 × 3s = 3 min
      for (let i = 0; i < MAX_POLLS; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
          const resp = await fetch(
            `http://127.0.0.1:${this.backendPort}/api/whisper/status`
          );
          if (!resp.ok) continue;
          const data = await resp.json();
          log('Whisper status poll:', data);
          if (data.loaded) return true;
          if (data.error) {
            err('Model download error:', data.error);
            return false;
          }
          // Update banner with progress dots
          const dots = '.'.repeat((i % 3) + 1);
          const msg = this._i18n(
            'Downloading speech model' + dots + ' (' + Math.round((i+1)*3/60*100) + '% time est.)',
            'Descargando modelo de voz' + dots + ' (' + Math.round((i+1)*3/60*100) + '% tiempo est.)'
          );
          this._showDownloadBanner(msg);
        } catch (e) {
          warn('Status poll error:', e);
        }
      }
      return false;  // timeout
    },

    // ─── Check del estado de Whisper ────────────────────────
    async checkWhisperStatus() {
      try {
        const resp = await fetch(`http://127.0.0.1:${this.backendPort}/api/whisper/status`);
        if (!resp.ok) {
          this._alert('Whisper status endpoint returned ' + resp.status);
          return;
        }
        const data = await resp.json();
        log('Whisper status:', data);
        const msg = this._i18n(
          'Whisper status:\nLoaded: ' + data.loaded + '\nLoading: ' + data.loading + '\nError: ' + (data.error || '(none)'),
          'Estado de Whisper:\nCargado: ' + data.loaded + '\nCargando: ' + data.loading + '\nError: ' + (data.error || '(ninguno)')
        );
        this._alert(msg);
      } catch (e) {
        this._alert('Whisper status fetch failed: ' + (e.message || e));
      }
    },

    init() {
      log('init()');
      if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = () => {
          window.speechSynthesis.getVoices();
        };
      }

      // Listener en CAPTURE phase para ganar a Reflex
      document.addEventListener('click', (e) => {
        const btn = e.target && e.target.closest && e.target.closest('#ashley-mic-btn');
        if (!btn) return;
        if (btn.disabled) {
          log('mic button clicked but disabled, ignoring');
          return;
        }
        e.preventDefault();
        e.stopPropagation();
        log('mic button click captured');
        this.toggleListening();
      }, true);

      const setupMarkerObs = () => {
        const marker = document.getElementById('ashley-voice-state');
        if (!marker) { setTimeout(setupMarkerObs, 400); return; }
        this._syncFromState();
        const mo = new MutationObserver(() => this._syncFromState());
        mo.observe(marker, { attributes: true });
        log('marker observer attached. lang:', this.lang);
      };
      setupMarkerObs();

      // El observer se auto-boostrapea en el primer tick (ver _tickObserver):
      // toma baseline del historial SIN leer, y solo lee mensajes nuevos.
      setInterval(() => this._tickObserver(), 500);
    },
  };

  window.AshleyVoice = V;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => V.init());
  } else {
    V.init();
  }
})();
