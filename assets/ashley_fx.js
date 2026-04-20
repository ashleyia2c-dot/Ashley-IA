(function () {
  // Guard: prevent double-execution across hot-reloads
  if (window._ashleyFxLoaded) return;
  window._ashleyFxLoaded = true;

  /* ══════════════════════════════════════════
     STARFIELD
  ══════════════════════════════════════════ */
  function initStarfield() {
    if (document.getElementById('ashley-starfield')) return;

    var canvas = document.createElement('canvas');
    canvas.id = 'ashley-starfield';
    canvas.style.cssText =
      'position:fixed;top:0;left:0;width:100%;height:100%;' +
      'z-index:0;pointer-events:none;';
    document.body.insertBefore(canvas, document.body.firstChild);

    var ctx = canvas.getContext('2d');
    var W = canvas.width  = window.innerWidth;
    var H = canvas.height = window.innerHeight;

    var layers = [
      { count: 140, speedMin: 0.03, speedMax: 0.07, sizeMin: 0.2, sizeMax: 0.7,  opBase: 0.45 },
      { count:  70, speedMin: 0.07, speedMax: 0.13, sizeMin: 0.5, sizeMax: 1.1,  opBase: 0.65 },
      { count:  28, speedMin: 0.13, speedMax: 0.22, sizeMin: 0.9, sizeMax: 1.8,  opBase: 0.85 },
    ];

    var stars = [];
    layers.forEach(function (l) {
      for (var i = 0; i < l.count; i++) {
        stars.push({
          x:       Math.random() * W,
          y:       Math.random() * H,
          r:       l.sizeMin  + Math.random() * (l.sizeMax  - l.sizeMin),
          speed:   l.speedMin + Math.random() * (l.speedMax - l.speedMin),
          op:      l.opBase   * (0.5 + Math.random() * 0.5),
          twPhase: Math.random() * Math.PI * 2,
          twSpeed: 0.008 + Math.random() * 0.025,
        });
      }
    });

    function draw() {
      ctx.fillStyle = '#0a0a0a';
      ctx.fillRect(0, 0, W, H);
      for (var i = 0; i < stars.length; i++) {
        var s = stars[i];
        s.twPhase += s.twSpeed;
        var op = Math.max(0.05, s.op * (0.75 + 0.25 * Math.sin(s.twPhase)));
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,' + op + ')';
        ctx.fill();
        s.y += s.speed;
        if (s.y > H + 2) { s.y = -2; s.x = Math.random() * W; }
      }
      requestAnimationFrame(draw);
    }
    draw();

    window.addEventListener('resize', function () {
      var prevW = W, prevH = H;
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
      // Reescalar posiciones de estrellas al nuevo tamaño para que
      // cubran toda la pantalla al instante (si no, cambiar a fullscreen
      // deja todas las estrellas apiñadas en el lado izquierdo hasta que
      // respawneen por caer abajo, que tarda varios segundos).
      var scaleX = prevW > 0 ? W / prevW : 1;
      var scaleY = prevH > 0 ? H / prevH : 1;
      for (var i = 0; i < stars.length; i++) {
        stars[i].x *= scaleX;
        stars[i].y *= scaleY;
      }
    });
  }


  /* ══════════════════════════════════════════
     SOUND EFFECTS
  ══════════════════════════════════════════ */
  var _actx = null;
  var _audioReady = false;   // true solo después de que el usuario interactuó

  function getActx() {
    if (!_actx) {
      try {
        _actx = new (window.AudioContext || window.webkitAudioContext)();
      } catch (e) { return null; }
    }
    if (_actx.state === 'suspended') _actx.resume();
    return _actx;
  }

  function unlockAudio() {
    _audioReady = true;
    getActx();
    document.removeEventListener('click',     unlockAudio);
    document.removeEventListener('keydown',   unlockAudio);
    document.removeEventListener('touchstart', unlockAudio);
  }
  document.addEventListener('click',     unlockAudio, { passive: true });
  document.addEventListener('keydown',   unlockAudio, { passive: true });
  document.addEventListener('touchstart', unlockAudio, { passive: true });

  function tone(freq, dur, vol, type, freqEnd) {
    if (!_audioReady) return;
    try {
      var actx = getActx();
      if (!actx) return;
      var osc  = actx.createOscillator();
      var gain = actx.createGain();
      osc.connect(gain);
      gain.connect(actx.destination);
      osc.type = type || 'sine';
      osc.frequency.setValueAtTime(freq, actx.currentTime);
      if (freqEnd) {
        osc.frequency.linearRampToValueAtTime(freqEnd, actx.currentTime + dur);
      }
      gain.gain.setValueAtTime(0, actx.currentTime);
      gain.gain.linearRampToValueAtTime(vol, actx.currentTime + 0.012);
      gain.gain.linearRampToValueAtTime(0,   actx.currentTime + dur);
      osc.start(actx.currentTime);
      osc.stop(actx.currentTime + dur + 0.05);
    } catch (e) {}
  }

  function playSend() {
    tone(520, 0.12, 0.10, 'sine', 320);
    setTimeout(function () { tone(300, 0.09, 0.06, 'sine'); }, 90);
  }
  function playThinking() {
    tone(260, 0.35, 0.07, 'sine');
    setTimeout(function () { tone(220, 0.35, 0.05, 'sine'); }, 180);
  }
  function playWriting() {
    tone(494, 0.10, 0.09, 'sine');
    setTimeout(function () { tone(587, 0.12, 0.08, 'sine'); }, 95);
    setTimeout(function () { tone(659, 0.16, 0.07, 'sine'); }, 200);
  }
  function playResponse() {
    tone(784,  0.10, 0.10, 'sine');
    setTimeout(function () { tone(988,  0.12, 0.09, 'sine'); }, 100);
    setTimeout(function () { tone(1175, 0.18, 0.07, 'sine'); }, 210);
  }

  function playAffectionUp() {
    // Gentle ascending sparkle — 3 notes going up
    tone(660, 0.12, 0.07, 'sine');
    setTimeout(function() { tone(880, 0.12, 0.06, 'sine'); }, 100);
    setTimeout(function() { tone(1100, 0.15, 0.05, 'sine'); }, 200);
  }

  function playAffectionDown() {
    // Soft descending sad tone — 2 notes going down
    tone(440, 0.15, 0.05, 'sine');
    setTimeout(function() { tone(330, 0.20, 0.04, 'sine', 280); }, 130);
  }

  function playHeartbeat() {
    // Two beats like a heart: tum-TUM... tum-TUM
    tone(80, 0.15, 0.12, 'sine');
    setTimeout(function() { tone(60, 0.12, 0.10, 'sine'); }, 150);
    setTimeout(function() { tone(80, 0.15, 0.12, 'sine'); }, 800);
    setTimeout(function() { tone(60, 0.12, 0.10, 'sine'); }, 950);
  }

  function playAchievement() {
    // Magical ascending arpeggio — more special than affection sounds
    tone(523, 0.12, 0.08, 'sine');   // C5
    setTimeout(function() { tone(659, 0.12, 0.07, 'sine'); }, 100);   // E5
    setTimeout(function() { tone(784, 0.12, 0.07, 'sine'); }, 200);   // G5
    setTimeout(function() { tone(1047, 0.20, 0.09, 'sine'); }, 300);  // C6
    setTimeout(function() { tone(1319, 0.25, 0.06, 'sine'); }, 450);  // E6 (high sparkle)
  }


  /* ══════════════════════════════════════════
     TEXTAREA AUTO-RESIZE + ENTER-TO-SEND
  ══════════════════════════════════════════ */
  function initTextarea() {
    // Auto-resize as user types
    document.addEventListener('input', function (e) {
      if (e.target && e.target.id === 'message' && e.target.tagName === 'TEXTAREA') {
        var ta = e.target;
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 180) + 'px';
      }
    });

    // Enter = submit, Shift+Enter = newline
    document.addEventListener('keydown', function (e) {
      if (e.target && e.target.id === 'message' && e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          var form = e.target.closest('form');
          if (form) {
            // Use requestSubmit so Reflex's onSubmit handler fires correctly
            if (form.requestSubmit) {
              form.requestSubmit();
            } else {
              // Fallback for older browsers
              var btn = form.querySelector('button[type="submit"]');
              if (btn) btn.click();
            }
          }
        }
      }
    });

    // Reset textarea height after the form clears (Reflex resets value but not height)
    document.addEventListener('submit', function (e) {
      var ta = e.target && e.target.querySelector('textarea#message');
      if (ta) {
        setTimeout(function () {
          ta.style.height = 'auto';
        }, 80);
      }
    });
  }


  /* ══════════════════════════════════════════
     AUTO-SCROLL + SOUND TRIGGERS
  ══════════════════════════════════════════ */
  function initObservers() {
    var box = document.getElementById('chat_messages');
    if (!box) { setTimeout(initObservers, 300); return; }

    // Auto-scroll
    var scrollObs = new MutationObserver(function () {
      box.scrollTop = box.scrollHeight;
    });
    scrollObs.observe(box, { childList: true, subtree: true });
    box.scrollTop = box.scrollHeight;

    // ── Sound observer ──────────────────────────────
    // Wait 600 ms for React to finish rendering existing messages,
    // then snapshot the current count as baseline so we never play
    // sounds for messages that were already there on page load.
    setTimeout(function () {
      var prevMsgCount = box.querySelectorAll('.msg-enter').length;
      var prevThink    = false;
      var prevStream   = false;

      var msgObs = new MutationObserver(function () {
        var all   = box.querySelectorAll('.msg-enter');
        var delta = all.length - prevMsgCount;

        // Only play sounds for 1-2 new messages at a time.
        // A large delta (>2) means it's the initial history load —
        // we skip it to avoid a burst of sounds on first interaction.
        if (delta >= 1 && delta <= 2) {
          for (var i = prevMsgCount; i < all.length; i++) {
            if (all[i].classList.contains('user-msg'))        playSend();
            else if (all[i].classList.contains('ashley-msg')) playResponse();
          }
        }
        prevMsgCount = all.length;
      });
      msgObs.observe(box, { childList: true, subtree: false });

      // Thinking / streaming → lightweight 100 ms poll
      setInterval(function () {
        var isThink  = !!document.querySelector('.avatar-thinking');
        var isStream = !!document.querySelector('.cursor-blink');
        if (isThink  && !prevThink)  playThinking();
        if (isStream && !prevStream) playWriting();
        prevThink  = isThink;
        prevStream = isStream;
      }, 100);

    }, 600);
  }


  /* ══════════════════════════════════════════
     WINDOWS NOTIFICATIONS — background messages
  ══════════════════════════════════════════
     Cuando Ashley escribe un mensaje mientras la ventana no está
     focuseada (minimizada, Alt+Tab a otra app, etc.), le pedimos al
     main process que dispare una notificación Windows nativa. El main
     usa Electron.Notification (no la Web Notification API del renderer,
     que falla silenciosa en Electron en bastantes casos).

     Flujo:
       - Observer sobre el contenedor de mensajes para detectar nuevos
         bubbles de Ashley
       - Baseline: los mensajes que ya están al cargar NO disparan notif
       - Si la ventana está visible O el toggle está OFF → skip
       - Si no → window.ashleyNotif.show({title, body}) → IPC al main
       - Main crea la notif con icono, y maneja el click para restaurar
         la ventana
  */

  var _notifInitialMessageCount = -1;  // baseline — se setea una vez tras carga

  function _notifEnabled() {
    var el = document.getElementById('ashley-voice-state');
    if (!el) {
      console.log('[ashley-notif] no #ashley-voice-state element, defaulting ON');
      return true;
    }
    var attr = el.getAttribute('data-notifications');
    return attr !== 'off';
  }

  function _windowIsVisible() {
    // En Electron:
    //   - minimizar la ventana → document.hidden=true
    //   - Alt+Tab a otra app → hidden=false pero hasFocus()=false
    // Ambos casos queremos notificar.
    if (document.hidden) return false;
    if (typeof document.hasFocus === 'function' && !document.hasFocus()) return false;
    return true;
  }

  function _sendNotif(bodyText) {
    if (!window.ashleyNotif || typeof window.ashleyNotif.show !== 'function') {
      console.log('[ashley-notif] window.ashleyNotif.show not available — preload not loaded?');
      return;
    }
    // Limpiar preview: quitar *gestos* y normalizar espacios.
    var body = (bodyText || '').trim();
    body = body.replace(/\*[^*]+\*/g, '').replace(/\s+/g, ' ').trim();
    if (body.length > 140) body = body.slice(0, 137) + '...';
    if (!body) body = 'Ashley te escribio algo.';

    try {
      window.ashleyNotif.show({ title: 'Ashley', body: body });
      console.log('[ashley-notif] sent notif to main:', body.slice(0, 50));
    } catch (e) {
      console.log('[ashley-notif] show() threw:', e);
    }
  }

  function initNotificationObserver() {
    var box = document.getElementById('chat_messages');
    if (!box) { setTimeout(initNotificationObserver, 300); return; }

    console.log('[ashley-notif] initializing observer');

    // Baseline tras 800ms para que Reflex haya renderizado el historial.
    setTimeout(function () {
      _notifInitialMessageCount = box.querySelectorAll('.ashley-msg').length;
      console.log('[ashley-notif] baseline:', _notifInitialMessageCount, 'existing messages');
    }, 800);

    var obs = new MutationObserver(function () {
      if (_notifInitialMessageCount < 0) return;  // todavía baseline-ing
      var ashleyMsgs = box.querySelectorAll('.ashley-msg');
      if (ashleyMsgs.length <= _notifInitialMessageCount) return;

      _notifInitialMessageCount = ashleyMsgs.length;

      // Gating
      var visible = _windowIsVisible();
      var enabled = _notifEnabled();
      if (visible) {
        console.log('[ashley-notif] new msg but window visible, skipping');
        return;
      }
      if (!enabled) {
        console.log('[ashley-notif] new msg but toggle OFF, skipping');
        return;
      }

      // Preview del mensaje más reciente
      var latest = ashleyMsgs[ashleyMsgs.length - 1];
      var textNode = latest.querySelector('.msg-content, p, div');
      var body = textNode ? textNode.textContent : latest.textContent;
      _sendNotif(body);
    });
    obs.observe(box, { childList: true, subtree: true });
  }


  /* ══════════════════════════════════════════
     PIN ON TOP — data-pin observer
  ══════════════════════════════════════════
     El pill 📌/📍 del header alterna State.pin_on_top en Reflex, que a su vez
     se refleja en data-pin del marker #ashley-voice-state. Aquí observamos
     ese atributo y llamamos al IPC del main process para activar/desactivar
     setAlwaysOnTop en la BrowserWindow. */
  function initPinOnTopObserver() {
    if (!window.ashleyWindow || typeof window.ashleyWindow.setAlwaysOnTop !== 'function') {
      return;  // no estamos en Electron
    }
    function findMarker() {
      return document.getElementById('ashley-voice-state');
    }
    function apply() {
      var el = findMarker();
      if (!el) return;
      var on = el.getAttribute('data-pin') === 'on';
      try { window.ashleyWindow.setAlwaysOnTop(on); } catch (e) {}
    }
    function attach() {
      var el = findMarker();
      if (!el) { setTimeout(attach, 300); return; }
      apply();  // estado inicial
      var obs = new MutationObserver(apply);
      obs.observe(el, { attributes: true, attributeFilter: ['data-pin'] });
    }
    attach();
  }


  /* ══════════════════════════════════════════
     AUTO-RELOAD WHEN RETURNING FROM BACKGROUND
  ══════════════════════════════════════════ */
  // Si la app estuvo oculta >5 min (usuario la minimizó, durmió, etc.),
  // al volver forzamos un reload para que el backend regenere el time context
  // con la hora REAL del sistema. Sin esto, Ashley puede decir "son las 2 AM"
  // cuando en realidad son las 12 PM (estado viejo del WebSocket).
  var _hiddenAt = 0;
  var STALE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutos

  function initVisibilityReload() {
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        _hiddenAt = Date.now();
      } else if (_hiddenAt > 0) {
        var elapsed = Date.now() - _hiddenAt;
        _hiddenAt = 0;
        if (elapsed > STALE_THRESHOLD_MS) {
          console.log('[ashley-fx] App was hidden for ' + Math.round(elapsed / 60000) + ' min — reloading for fresh state');
          location.reload();
        }
      }
    });
  }


  /* ══════════════════════════════════════════
     AFFECTION SYSTEM — visual feedback
  ══════════════════════════════════════════ */
  var _lastAffection = -1;
  var _lastTier = -1;

  function _getTier(value) {
    if (value < 20) return 0;
    if (value < 40) return 1;
    if (value < 60) return 2;
    if (value < 80) return 3;
    return 4;
  }

  // ── Floating hearts ──────────────────────
  function _spawnHeart(positive, delta) {
    var bar = document.querySelector('.affection-bar');
    if (!bar) return;
    var rect = bar.getBoundingClientRect();
    var heart = document.createElement('div');
    heart.className = 'affection-heart-float ' + (positive ? 'positive' : 'negative');
    heart.innerHTML = (positive ? '\uD83D\uDC95' : '\uD83D\uDC94') + '<span class="delta">' + (positive ? '+' : '') + delta + '</span>';
    heart.style.position = 'fixed';
    heart.style.left = (rect.left + rect.width / 2 - 15) + 'px';
    heart.style.top = (rect.top - 10) + 'px';
    document.body.appendChild(heart);
    setTimeout(function() { heart.remove(); }, 2500);
  }

  // ── Tier change event ────────────────────
  function _triggerTierChange(isUp, newTier) {
    // 1. Overlay
    var overlay = document.createElement('div');
    overlay.className = 'tier-change-overlay ' + (isUp ? 'up' : 'down');
    document.body.appendChild(overlay);
    setTimeout(function() { overlay.remove(); }, isUp ? 4500 : 2500);

    // 2. Banner with message
    var stateEl = document.getElementById('ashley-voice-state');
    var lang = (stateEl && stateEl.getAttribute('data-lang')) || 'en';

    // Read tier messages from i18n (stored as data attributes on a hidden element)
    // Fallback to hardcoded if not found
    var msgKey = isUp ? ('tier_up_' + newTier) : ('tier_down_' + (newTier + 1));
    var tierMsgs = {
      en: {
        tier_up_1: "Ashley lowers her guard, just a little...",
        tier_up_2: "Ashley is starting to feel comfortable with you.",
        tier_up_3: "Ashley feels... strange. Her heart beats faster.",
        tier_up_4: "Ashley can't hide what she feels anymore.",
        tier_down_4: "Ashley doesn't feel as safe anymore...",
        tier_down_3: "Ashley closes up a little more...",
        tier_down_2: "Ashley is starting to doubt you...",
        tier_down_1: "Ashley barely recognizes you..."
      },
      es: {
        tier_up_1: "Ashley baja un poco la guardia...",
        tier_up_2: "Ashley empieza a sentirse c\u00f3moda contigo.",
        tier_up_3: "Ashley se siente... extra\u00f1a. El coraz\u00f3n le late m\u00e1s r\u00e1pido.",
        tier_up_4: "Ashley ya no puede esconder lo que siente.",
        tier_down_4: "Ashley ya no se siente tan segura...",
        tier_down_3: "Ashley se cierra un poco m\u00e1s...",
        tier_down_2: "Ashley empieza a dudar de ti...",
        tier_down_1: "Ashley casi no te reconoce..."
      }
    };
    var msgs = tierMsgs[lang] || tierMsgs.en;
    var msg = msgs[msgKey] || '';

    if (msg) {
      var prefix = isUp ? '\uD83D\uDC95 ' : '\uD83D\uDC94 ';
      var banner = document.createElement('div');
      banner.className = 'tier-banner ' + (isUp ? 'up' : 'down');
      banner.textContent = prefix + msg;
      document.body.appendChild(banner);
      setTimeout(function() { banner.remove(); }, 5000);
    }

    // 3. Sound
    if (isUp) {
      playHeartbeat();
    }
    // Down uses the existing playAffectionDown (already triggered by the observer)
  }

  // Hidratacion: la pagina renderiza con el default 50 y luego el servidor
  // inyecta el valor real via WebSocket. Sin defensa, ese salto (ej. 50->72)
  // disparaba un "tier up" fantasma cada vez que el user abria la app.
  //
  // Dos capas de defensa:
  //
  //   1. Ventana temporal (HYDRATION_WINDOW_MS): durante los primeros N ms
  //      desde que arranca el observer, CUALQUIER cambio se trata como
  //      hidratacion (actualizamos baseline en silencio).
  //   2. Delta magnitude: el servidor clampea los deltas de affection a
  //      maximo ±3 por mensaje en _apply_affection_delta (Python). Entonces
  //      un salto >3 en un solo poll NUNCA puede ser un cambio real — es
  //      siempre hidratacion tardia, reload, cross-tab merge o similar.
  //      Con esta regla no necesitamos depender solo del tiempo y manejamos
  //      el caso de maquinas lentas donde hydration tarda >2.5s.
  //
  // La ventana temporal se queda en 5s (suficiente para cold-start lento
  // de Reflex) y el clamp a 3 la complementa. Entre los dos cubrimos todos
  // los casos razonables.
  var HYDRATION_WINDOW_MS = 5000;
  var HYDRATION_MAX_REAL_DELTA = 3;  // mantener en sync con Python clamp
  var _observerStartTime = 0;

  function initAffectionObserver() {
    _observerStartTime = Date.now();
    setInterval(function() {
      var bar = document.querySelector('.affection-bar');
      if (!bar) return;
      var parent = bar.parentElement;
      if (!parent) return;
      // Find the text element showing the number (p or span after the bar)
      var texts = parent.querySelectorAll('p, span');
      var current = -1;
      for (var i = 0; i < texts.length; i++) {
        var v = parseInt(texts[i].textContent, 10);
        if (!isNaN(v) && v >= 0 && v <= 100) { current = v; break; }
      }
      if (current < 0) return;

      if (_lastAffection < 0) {
        // First read — initialize without playing sounds
        _lastAffection = current;
        _lastTier = _getTier(current);
        return;
      }

      if (current === _lastAffection) return;

      var delta = current - _lastAffection;

      // Hydration guard #1: ventana temporal inicial.
      if (Date.now() - _observerStartTime < HYDRATION_WINDOW_MS) {
        _lastAffection = current;
        _lastTier = _getTier(current);
        return;
      }

      // Hydration guard #2: magnitud del delta.
      // El servidor clampea los deltas de affection a +/-3 por mensaje, asi
      // que cualquier salto mayor que eso no puede ser real. Pasa cuando
      // hydration llega tarde (>5s), cuando el user recarga la app, o en
      // cruces entre pestanas. Silenciamos igual.
      if (Math.abs(delta) > HYDRATION_MAX_REAL_DELTA) {
        console.log('[ashley-fx] large affection delta ' + _lastAffection + '->' + current + ' (|d|=' + Math.abs(delta) + '), treating as hydration');
        _lastAffection = current;
        _lastTier = _getTier(current);
        return;
      }

      var newTier = _getTier(current);
      var oldTier = _lastTier;

      // Floating heart
      if (delta > 0) {
        _spawnHeart(true, delta);
        playAffectionUp();
      } else if (delta < 0) {
        _spawnHeart(false, delta);
        playAffectionDown();
      }

      // Tier change detection
      if (newTier !== oldTier) {
        _triggerTierChange(newTier > oldTier, newTier);
      }

      _lastAffection = current;
      _lastTier = newTier;
    }, 500);
  }


  /* ══════════════════════════════════════════
     ACHIEVEMENT SOUND OBSERVER
  ══════════════════════════════════════════ */
  var _lastAchievementToast = '';

  function initAchievementObserver() {
    setInterval(function() {
      var el = document.querySelector('.achievement-toast');
      if (!el) { _lastAchievementToast = ''; return; }
      var title = el.querySelector('.ach-title');
      if (!title) return;
      var current = title.textContent;
      if (current && current !== _lastAchievementToast) {
        _lastAchievementToast = current;
        playAchievement();
      }
    }, 300);
  }


  /* ══════════════════════════════════════════
     VERSION BADGE
     Muestra "v0.9.0" abajo a la derecha, muy discreto.
     Sólo aparece cuando corremos dentro de Electron (ahí tenemos acceso
     a la versión real del package.json via window.ashleyUpdate).
  ══════════════════════════════════════════ */
  function initVersionBadge() {
    if (!window.ashleyUpdate || typeof window.ashleyUpdate.getVersion !== 'function') {
      return;
    }
    window.ashleyUpdate.getVersion().then(function (version) {
      if (!version) return;
      var badge = document.createElement('div');
      badge.id = 'ashley-version-badge';
      badge.textContent = 'v' + version;
      badge.style.cssText =
        'position:fixed;bottom:6px;right:10px;z-index:9998;' +
        'color:rgba(255,255,255,0.28);font-size:10px;' +
        'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",monospace;' +
        'pointer-events:none;user-select:none;letter-spacing:0.5px;';
      document.body.appendChild(badge);
    }).catch(function (e) {
      console.warn('[ashley-version] failed to read version:', e);
    });
  }


  /* ══════════════════════════════════════════
     AUTO-UPDATER PILL
     Muestra un pill flotante cuando hay un update descargado.
     `window.ashleyUpdate` viene de electron/preload.js — sólo existe
     cuando Ashley corre dentro del wrapper Electron, no en un browser
     plano. En dev/web-only este bloque es no-op.
  ══════════════════════════════════════════ */
  function initUpdateNotifier() {
    if (!window.ashleyUpdate || typeof window.ashleyUpdate.on !== 'function') {
      return; // no estamos en Electron, nada que hacer
    }

    var pill = null;
    var installing = false;

    function ensurePill() {
      if (pill) return pill;
      pill = document.createElement('div');
      pill.id = 'ashley-update-pill';
      pill.style.cssText =
        'position:fixed;bottom:20px;right:20px;z-index:9999;' +
        'background:linear-gradient(135deg,#ff9aee 0%,#c86dd7 100%);' +
        'color:#0a0a0a;font-weight:600;font-size:13px;' +
        'padding:10px 16px;border-radius:20px;cursor:pointer;' +
        'box-shadow:0 4px 20px rgba(255,154,238,0.4);' +
        'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
        'transition:all 0.2s ease;user-select:none;' +
        'display:none;';
      pill.onmouseover = function () {
        pill.style.transform = 'translateY(-2px)';
        pill.style.boxShadow = '0 6px 24px rgba(255,154,238,0.55)';
      };
      pill.onmouseout = function () {
        pill.style.transform = 'translateY(0)';
        pill.style.boxShadow = '0 4px 20px rgba(255,154,238,0.4)';
      };
      pill.onclick = function () {
        if (installing) return;
        installing = true;
        pill.textContent = 'Reiniciando...';
        pill.style.cursor = 'wait';
        window.ashleyUpdate.installNow().catch(function (e) {
          console.error('[ashley-update] install failed:', e);
          installing = false;
          pill.textContent = 'Error al instalar';
        });
      };
      document.body.appendChild(pill);
      return pill;
    }

    window.ashleyUpdate.on('downloaded', function (info) {
      var p = ensurePill();
      var v = (info && info.version) ? (' v' + info.version) : '';
      p.textContent = '\u2728 Update' + v + ' listo — Click para reiniciar';
      p.style.display = 'block';
    });

    window.ashleyUpdate.on('error', function (info) {
      console.warn('[ashley-update] error:', info && info.message);
      // No mostramos errores al usuario — son típicamente "no internet" o
      // "rate limit" y no son actionable. Sólo log para debug.
    });

    window.ashleyUpdate.on('available', function (info) {
      console.log('[ashley-update] downloading v' + (info && info.version) + '...');
    });

    window.ashleyUpdate.on('download-progress', function (p) {
      console.log('[ashley-update] ' + (p && p.percent) + '%');
    });
  }


  /* ══════════════════════════════════════════
     BOOT
  ══════════════════════════════════════════ */
  function boot() {
    initStarfield();
    initTextarea();
    initObservers();
    initNotificationObserver();
    initPinOnTopObserver();
    initVisibilityReload();
    initAffectionObserver();
    initAchievementObserver();
    initVersionBadge();
    initUpdateNotifier();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
