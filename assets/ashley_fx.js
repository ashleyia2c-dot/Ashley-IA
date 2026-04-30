(function () {
  // Guard: prevent double-execution across hot-reloads
  if (window._ashleyFxLoaded) return;
  window._ashleyFxLoaded = true;

  /* ══════════════════════════════════════════
     STARFIELD
  ══════════════════════════════════════════ */
  function createStarfieldCanvas() {
    var c = document.createElement('canvas');
    c.id = 'ashley-starfield';
    // v0.15.5 — z-index alto + mix-blend-mode:screen es la combinación
    // a prueba de balas:
    //   • z-index: 9000 → siempre encima de cualquier glass panel,
    //     sidebar, chat, lo que sea. No depende de stacking contexts.
    //   • pointer-events: none → no interfiere con clicks/scroll.
    //   • mix-blend-mode: screen → los píxeles negros del canvas son
    //     "transparentes" en blend (negro+X = X), los blancos iluminan
    //     (255+X = saturado a 255). Resultado: estrellas blancas
    //     visibles sobre cualquier bg, sin oscurecer NADA del UI.
    c.style.cssText =
      'position:fixed;top:0;left:0;width:100vw;height:100vh;' +
      'z-index:9000;pointer-events:none;display:block;' +
      'mix-blend-mode:screen;-webkit-mix-blend-mode:screen;';
    // Lo metemos al final del body para que esté en el último layer.
    document.body.appendChild(c);
    return c;
  }

  function initStarfield() {
    // v0.15.5 — vuelta al método JS-only con guardián MutationObserver.
    //
    // Historia: probamos a renderizar el canvas via Reflex (rx.el.canvas)
    // pero o no rendered o desaparecía igual. El método original (JS
    // crea + body.insertBefore) funcionaba antes del rediseño, así que
    // volvemos. ÚNICA novedad: un MutationObserver que vigila si React
    // remueve el canvas durante una re-hidratación, y lo recrea +
    // re-arranca el loop de dibujo. Garantiza que las estrellas
    // siempre estén ahí, suceda lo que suceda con la hidratación.
    var canvas = document.getElementById('ashley-starfield');
    if (canvas && canvas._starfieldInitialized) return;
    if (!canvas) {
      canvas = createStarfieldCanvas();
    }
    canvas._starfieldInitialized = true;

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
      // v0.15.5 — vuelvo a fillRect opaco con #080810 (mismo color que
      // el body bg). Funciona porque al ser opaco GARANTIZA que el
      // canvas se vea aunque algo lo cubra parcialmente o haya
      // problemas con clearRect+layers. Las estrellas se dibujan
      // sobre este fondo controlado.
      ctx.fillStyle = '#080810';
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

    // ── Guardián anti-React: si React/Next.js remueve el canvas
    // durante una re-hidratación, lo recreamos. Sin este observer
    // las estrellas a veces desaparecían tras un rato sin avisar.
    try {
      var observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          var m = mutations[i];
          for (var j = 0; j < m.removedNodes.length; j++) {
            if (m.removedNodes[j].id === 'ashley-starfield') {
              // Reset y recrear
              canvas._starfieldInitialized = false;
              window._ashleyFxLoaded = false;
              setTimeout(function () {
                window._ashleyFxLoaded = true;
                initStarfield();
              }, 50);
              return;
            }
          }
        }
      });
      observer.observe(document.body, { childList: true });
    } catch (e) {
      // MutationObserver puede fallar en entornos exóticos —
      // no bloqueamos el resto.
    }

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

  // v0.16.3 — sonidos rediseñados para encajar con el tema visual
  // wine boutique noir. Antes: tones brillantes 800-1300Hz tipo synth
  // bell discoteca. Ahora: tones warm 200-650Hz con lowpass filter +
  // harmonic overtones + decay exponencial → "soft chime" tipo pequeña
  // campana de boutique, gentle bell de hotel, no notification stridente.
  //
  // Helper warmTone() añade:
  //   • Lowpass filter (suaviza los harmónicos altos)
  //   • Overtone a 2×freq con vol=15% del principal (rico, no plano)
  //   • Attack 25ms (suave) + decay exponencial (natural fade)

  function tone(freq, dur, vol, type, freqEnd) {
    // Mantengo el original tone() por compat con código legacy
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

  function warmTone(freq, dur, vol, opts) {
    // opts = { wave: 'sine'|'triangle', overtone: bool, filterFreq: Hz }
    if (!_audioReady) return;
    try {
      var actx = getActx();
      if (!actx) return;
      opts = opts || {};
      var t = actx.currentTime;

      // Cadena: osc → lowpass → gain → destination
      var osc = actx.createOscillator();
      var gain = actx.createGain();
      var filter = actx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(opts.filterFreq || (freq * 3.5), t);
      filter.Q.setValueAtTime(1.0, t);
      osc.connect(filter);
      filter.connect(gain);
      gain.connect(actx.destination);
      osc.type = opts.wave || 'sine';
      osc.frequency.setValueAtTime(freq, t);

      // Attack suave 25ms + decay exponencial natural
      gain.gain.setValueAtTime(0, t);
      gain.gain.linearRampToValueAtTime(vol, t + 0.025);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      osc.start(t);
      osc.stop(t + dur + 0.05);

      // Overtone harmónico — añade riqueza sin estridencia
      if (opts.overtone !== false) {
        var harm = actx.createOscillator();
        var hg = actx.createGain();
        harm.connect(hg);
        hg.connect(actx.destination);
        harm.type = 'sine';
        harm.frequency.setValueAtTime(freq * 2, t);
        hg.gain.setValueAtTime(0, t);
        hg.gain.linearRampToValueAtTime(vol * 0.15, t + 0.030);
        hg.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.7);
        harm.start(t);
        harm.stop(t + dur * 0.7 + 0.05);
      }
    } catch (e) {}
  }

  // v0.16.5: volúmenes subidos (~2x) — el user reportó que no oía
  // los sonidos. Antes 0.06-0.10 era casi inaudible sobre música/
  // ruido ambiente. Ahora 0.16-0.22 — perceptible pero todavía no
  // estridente.

  function playSend() {
    // User envió mensaje — soft tap warm. Frecuencia baja (G3) tipo
    // golpe de wood puro, decay rápido.
    warmTone(196, 0.20, 0.18, { wave: 'sine' });
  }
  function playThinking() {
    // Ashley está pensando. Tono medio-bajo, dur larga.
    warmTone(220, 0.50, 0.12, { wave: 'sine' });
  }
  function playWriting() {
    // Ashley empezó a escribir — mini chord ascendente warm (G3→C4).
    warmTone(196, 0.18, 0.14, { wave: 'sine' });
    setTimeout(function () { warmTone(262, 0.22, 0.12, { wave: 'sine' }); }, 80);
  }
  function playResponse() {
    // Ashley terminó — triada major C4-E4-G4 ascendente warm.
    warmTone(262, 0.32, 0.18, { wave: 'sine' });
    setTimeout(function () { warmTone(330, 0.32, 0.16, { wave: 'sine' }); }, 90);
    setTimeout(function () { warmTone(392, 0.44, 0.15, { wave: 'sine' }); }, 200);
  }

  function playAffectionUp() {
    // Afecto sube — E4 → G4 → B4.
    warmTone(330, 0.38, 0.18, { wave: 'sine' });
    setTimeout(function () { warmTone(392, 0.38, 0.16, { wave: 'sine' }); }, 110);
    setTimeout(function () { warmTone(494, 0.55, 0.15, { wave: 'sine' }); }, 230);
  }
  function playAffectionDown() {
    // Afecto baja — E4 → C4 minor 3rd descendente.
    warmTone(330, 0.45, 0.14, { wave: 'sine' });
    setTimeout(function () { warmTone(262, 0.60, 0.12, { wave: 'sine' }); }, 150);
  }

  function playHeartbeat() {
    // Latido suave, mantiene el original — bass tones funcionan bien.
    warmTone(110, 0.20, 0.10, { wave: 'sine', overtone: false });
    setTimeout(function () { warmTone(82, 0.16, 0.08, { wave: 'sine', overtone: false }); }, 150);
    setTimeout(function () { warmTone(110, 0.20, 0.10, { wave: 'sine', overtone: false }); }, 800);
    setTimeout(function () { warmTone(82, 0.16, 0.08, { wave: 'sine', overtone: false }); }, 950);
  }

  function playAchievement() {
    // Logro desbloqueado — arpegio rico mayor (C4 E4 G4 C5 E5) +
    // ligero shimmer al final. Es el sonido más prominente porque
    // pasa raramente y debe sentirse SPECIAL.
    warmTone(262, 0.25, 0.09, { wave: 'sine' });
    setTimeout(function () { warmTone(330, 0.25, 0.08, { wave: 'sine' }); }, 100);
    setTimeout(function () { warmTone(392, 0.30, 0.08, { wave: 'sine' }); }, 200);
    setTimeout(function () { warmTone(523, 0.45, 0.10, { wave: 'sine' }); }, 320);
    setTimeout(function () { warmTone(659, 0.55, 0.07, { wave: 'sine' }); }, 480);
  }

  // v0.16.3 — nuevos sonidos para más eventos del chat
  function playHeartHover() {
    // Hover sobre el corazón — tap suave warm, muy bajo vol.
    warmTone(440, 0.15, 0.04, { wave: 'sine' });
  }
  function playToggleOn() {
    // Activar un toggle (Acciones, etc.) — soft click ascendente.
    warmTone(330, 0.10, 0.06, { wave: 'sine' });
    setTimeout(function () { warmTone(440, 0.12, 0.05, { wave: 'sine' }); }, 60);
  }
  function playToggleOff() {
    // Desactivar — descendente.
    warmTone(440, 0.10, 0.05, { wave: 'sine' });
    setTimeout(function () { warmTone(330, 0.12, 0.04, { wave: 'sine' }); }, 60);
  }


  /* ══════════════════════════════════════════
     TEXTAREA AUTO-RESIZE + ENTER-TO-SEND + OPTIMISTIC SEND (v0.14.4)
  ══════════════════════════════════════════
     v0.14.4 — el "optimistic UI" anterior NO funcionaba porque mi
     listener era en bubbling phase del submit → React resetea el
     form ANTES de bubblear → al leer ta.value yo veía "". Ahora:

       1. Al pulsar Enter (o click Send), interceptamos en el evento
          ANTES de submit, leemos ta.value cuando aún está poblado.
       2. Construimos el bubble fake al instante en JS, lo metemos
          al DOM. Sin animación de fadeIn (instant feel).
       3. Limpiamos el textarea EN JS también (instant), no esperamos
          a que Reflex lo haga.
       4. Llamamos requestSubmit() para que Reflex procese normal.
       5. Cuando el real llega del backend, el observer lo detecta
          y elimina el fake.

     Resultado: lo que el user ve es 0ms de delay entre Enter y bubble. */

  function _getPendingImageUrl(form) {
    if (!form) return null;
    var parent = form.parentElement;
    if (!parent) return null;
    var img = parent.querySelector('img[src^="data:image"]');
    return img ? img.src : null;
  }

  function _doOptimisticSend(form) {
    // Lee texto + imagen del form actual. Crea el bubble fake en DOM
    // SIN tocar ta.value (clave: si limpiamos antes del submit, Reflex
    // recibe FormData vacío). Reflex limpia el textarea solo via
    // reset_on_submit=True después.
    if (!form) return false;
    var ta = form.querySelector('textarea#message');
    if (!ta) return false;

    var text = (ta.value || '').trim();
    var imageUrl = _getPendingImageUrl(form);

    if (!text && !imageUrl) return false;

    if (typeof _showOptimisticUserBubble === 'function') {
      _showOptimisticUserBubble(text, imageUrl);
    }
    return true;
  }

  function initTextarea() {
    // Auto-resize as user types
    document.addEventListener('input', function (e) {
      if (e.target && e.target.id === 'message' && e.target.tagName === 'TEXTAREA') {
        var ta = e.target;
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 180) + 'px';
      }
    });

    // Enter = submit form, Shift+Enter = newline.
    // Disparamos el optimistic ANTES de requestSubmit (síncrono en
    // el handler del usuario, ta.value todavía poblado).
    document.addEventListener('keydown', function (e) {
      if (e.target && e.target.id === 'message' && e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          var form = e.target.closest('form');
          if (!form) return;

          _doOptimisticSend(form);

          if (form.requestSubmit) {
            form.requestSubmit();
          } else {
            var btn = form.querySelector('button[type="submit"]');
            if (btn) btn.click();
          }
        }
      }
    });

    // Click en send button — interceptamos en CAPTURE phase para
    // disparar optimistic ANTES de que React maneje el click.
    document.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest && e.target.closest('.ashley-send-btn');
      if (!btn) return;
      var form = btn.closest('form');
      if (!form) return;
      _doOptimisticSend(form);
      // No preventDefault — dejamos que el click llegue al button para
      // que dispare submit del form normal. Reflex procesa el data
      // que ya capturó del textarea antes de nuestro reset (lo lee
      // del FormData del submit event que viene a continuación).
    }, true /* CAPTURE phase, antes de React */);

    // Reset textarea height tras submit del form (Reflex resetea
    // .value pero no la height auto-resize)
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
    var msgsBox = document.getElementById('chat_messages');
    if (!msgsBox) { setTimeout(initObservers, 300); return; }

    // v0.16.5 fix scroll: en el layout nuevo el id `chat_messages` vive
    // en el vstack INTERNO (sin overflow). El scroll real ocurre en el
    // ancestro con clase `.ashley-chat-scroll` (overflow-y:auto). Antes
    // hacíamos `chat_messages.scrollTop = scrollHeight` lo que era
    // un no-op porque ese elemento no scrollea — por eso el chat al
    // abrir aparecía arriba del todo.
    //
    // closest() camina hacia arriba y encuentra el primer ancestor con
    // la clase. Si por alguna razón no existe (layout futuro), caemos
    // al box original como fallback.
    var box = msgsBox.closest('.ashley-chat-scroll') || msgsBox;

    // Auto-scroll inteligente — solo pega al fondo si el user YA estaba
    // cerca del fondo. Si el user scrolleó arriba (para releer algo),
    // respetamos su posición y NO le pegamos abajo cuando Ashley actualiza
    // su mensaje en stream. Cuando el user vuelve cerca del fondo
    // (scroll manual o navegando), volvemos al modo "stick".
    var stickToBottom = true;
    var STICK_MARGIN_PX = 80;  // dentro de 80px del fondo = "stuck"

    function recomputeStick() {
      var distanceFromBottom = box.scrollHeight - box.scrollTop - box.clientHeight;
      stickToBottom = distanceFromBottom < STICK_MARGIN_PX;
    }

    // Scroll listeners en el container scrollable (no en chat_messages).
    box.addEventListener('scroll', recomputeStick, { passive: true });
    box.addEventListener('wheel', function () {
      setTimeout(recomputeStick, 0);
    }, { passive: true });

    // El observer mira mutations sobre msgsBox (donde se añaden los
    // .msg-enter) pero la acción de scroll se aplica al container.
    var scrollObs = new MutationObserver(function () {
      if (stickToBottom) {
        box.scrollTop = box.scrollHeight;
      }
    });
    scrollObs.observe(msgsBox, { childList: true, subtree: true, characterData: true });

    // v0.16.5 — Initial scroll polling más agresivo (40 intentos × 75ms
    // = 3s) y aplicado al container correcto. React puede seguir
    // renderizando mensajes durante el primer segundo, y los assets
    // de imagen (avatar, mood-image) cambian el scrollHeight cuando
    // cargan — necesitamos seguir empujando al fondo durante un rato.
    var _initialScrollAttempts = 0;
    function _initialScroll() {
      box.scrollTop = box.scrollHeight;
      _initialScrollAttempts++;
      if (_initialScrollAttempts < 40) {
        setTimeout(_initialScroll, 75);
      }
    }
    _initialScroll();
    stickToBottom = true;

    // Re-trigger initial scroll cuando la fuente principal (Cormorant
    // Garamond) termina de cargar — eso re-mide los altos de las
    // burbujas y puede haber cambiado el scrollHeight.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        box.scrollTop = box.scrollHeight;
      }).catch(function () {});
    }

    // ── Sound observer ──────────────────────────────
    // Wait 600 ms for React to finish rendering existing messages,
    // then snapshot the current count as baseline so we never play
    // sounds for messages that were already there on page load.
    setTimeout(function () {
      // v0.14.3 — el conteo IGNORA optimistic bubbles. Estos son fakes
      // que añadimos en JS para feedback instantáneo; cuando el real
      // de React llega, lo detectamos como un "+1 real" y eliminamos
      // el fake en el mismo tick para evitar duplicados visibles.
      var REAL_SEL = '.msg-enter:not(.ashley-optimistic)';
      var prevMsgCount = box.querySelectorAll(REAL_SEL).length;
      var prevThink    = false;
      var prevStream   = false;

      var msgObs = new MutationObserver(function () {
        var all   = box.querySelectorAll(REAL_SEL);
        var delta = all.length - prevMsgCount;

        // Si llegó un nuevo real, borrar TODOS los optimistic.
        // El fake fue temporal — su trabajo era cubrir el gap hasta
        // que el real llegara. Una vez aquí, ya no hace falta.
        if (delta >= 1 && typeof _purgeOptimistic === 'function') {
          try { _purgeOptimistic(); } catch (_e) {}
        }

        // Sonidos: solo 1-2 nuevos a la vez. delta>2 = history load,
        // skip para no sonar burst al abrir la app.
        if (delta >= 1 && delta <= 2) {
          for (var i = prevMsgCount; i < all.length; i++) {
            var el = all[i];
            // user-msg NO suena aquí — playSend ya sonó al insertar el
            // optimistic bubble. Si por algún path raro un user-msg llega
            // sin optimistic previo, aceptamos silencio (mejor que doble
            // sonido).
            if (el.classList.contains('ashley-msg')) playResponse();
          }
        }
        prevMsgCount = all.length;
      });
      // v0.16.5: subtree=true — Reflex puede meter wrappers entre
      // chat_messages y los .msg-enter; con subtree=false el observer
      // perdía los mensajes y los sonidos no disparaban.
      msgObs.observe(box, { childList: true, subtree: true });

      // Thinking / streaming → lightweight 100 ms poll.
      // v0.16.5 fix: el selector era `.avatar-thinking` que no existe
      // en la UI nueva (la clase real es `.portrait-thinking` en el
      // avatar de Ashley). Por eso playThinking() jamás disparaba.
      setInterval(function () {
        var isThink  = !!document.querySelector('.portrait-thinking');
        var isStream = !!document.querySelector('.cursor-blink');
        if (isThink  && !prevThink)  playThinking();
        if (isStream && !prevStream) playWriting();
        prevThink  = isThink;
        prevStream = isStream;
      }, 100);

    }, 600);
  }


  /* ══════════════════════════════════════════
     OPTIMISTIC UI — bubble fake temporal (v0.16.12 — simple)
  ══════════════════════════════════════════
     Filosofía:
       El user pulsa enter y necesita ver SU mensaje + oír sonido AL
       INSTANTE. Reflex tarda ~100-200ms en montar el real — durante
       ese gap mostramos un bubble fake.

     Vida del fake:
       1. JS lo añade al final del chat al pulsar enter + playSend().
       2. React monta el real ms después. Observer detecta y BORRA el
          fake. El real toma su lugar.
       3. CSS .user-msg.msg-enter { animation: none } evita que el real
          ejecute slide-up tras el swap → el bubble queda donde estaba
          el fake, sin "se mueve".
       4. CSS reset margin del <p>/<h*>/<li> dentro de bubble-* iguala
          dimensiones del real (que usa Markdown) con el fake (que usa
          <p style="margin:0">). Sin esto el real es ~32px más alto
          y el bubble crecía al swap.

     Lo que NO hace este código (a propósito):
       - NO mantiene el fake permanente — era source de bugs raros
         al borrar mensajes y al recibir respuestas de Ashley.
       - NO oculta el real con display:none — rompía la lógica de
         eliminación de mensajes.
       - NO posiciona el fake activamente — React maneja el orden via
         state.messages.
       Cero pelea contra React: el fake es 100% temporal, el real es
       el bubble permanente. */

  function _buildFakeBubble(text, imageUrl) {
    // Bubble simple hand-rolled. Sin botón 🗑️ — el optimistic es facade
    // visual; el real (oculto) tiene su botón funcional, pero el user
    // no puede acceder a él. Si hace falta borrar, reload y aparecerá
    // el real con su botón. Trade-off aceptable para la ilusión sin
    // artefactos.
    var wrapper = document.createElement('div');
    wrapper.className = 'user-msg ashley-optimistic';
    wrapper.style.cssText =
      'width:100%;padding-top:4px;padding-bottom:4px;animation:none;';
    var row = document.createElement('div');
    row.style.cssText =
      'display:flex;align-items:center;justify-content:flex-end;' +
      'width:100%;gap:8px;';
    var bubble = document.createElement('div');
    bubble.className = 'bubble-user';
    bubble.style.cssText =
      'padding:12px 18px;border-radius:22px 4px 22px 22px;' +
      'max-width:78%;white-space:pre-wrap;word-wrap:break-word;';
    if (imageUrl) {
      var img = document.createElement('img');
      img.src = imageUrl;
      img.style.cssText =
        'max-width:220px;border-radius:10px;' +
        'display:block;margin-bottom:8px;';
      bubble.appendChild(img);
    }
    if (text) {
      var p = document.createElement('p');
      p.textContent = text;
      p.style.cssText = 'margin:0;';
      bubble.appendChild(p);
    }
    row.appendChild(bubble);
    wrapper.appendChild(row);
    return wrapper;
  }

  function _showOptimisticUserBubble(text, imageUrl) {
    var box = document.getElementById('chat_messages');
    if (!box) return;

    // Limpiar cualquier fake anterior (defensivo — observer ya lo borra
    // cuando llega el real, pero si el user envía dos mensajes muy
    // rápido seguidos, podría quedar uno).
    var prev = box.querySelectorAll('.ashley-optimistic');
    for (var i = 0; i < prev.length; i++) prev[i].remove();

    // Crear y añadir al final.
    var wrapper = _buildFakeBubble(text, imageUrl);
    box.appendChild(wrapper);

    // Sonido AL INSTANTE — alineado con la aparición visual.
    if (typeof playSend === 'function') {
      try { playSend(); } catch (_e) {}
    }

    // Scroll al fondo.
    var scrollBox = box.closest('.ashley-chat-scroll') || box;
    scrollBox.scrollTop = scrollBox.scrollHeight;
  }

  // Borra todos los fakes activos. Llamada por el observer cuando
  // detecta que llegó un real (delta positivo de mensajes).
  function _purgeOptimistic() {
    var box = document.getElementById('chat_messages');
    if (!box) return;
    var fakes = box.querySelectorAll('.ashley-optimistic');
    for (var i = 0; i < fakes.length; i++) fakes[i].remove();
  }

  function initOptimisticUI() {
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (!form || form.tagName !== 'FORM') return;
      var ta = form.querySelector('textarea#message');
      if (!ta) return;

      var text = (ta.value || '').trim();

      // Detectar imagen pendiente (preview encima del input — el
      // selector busca un <img> con src data: cerca del textarea).
      var imageUrl = null;
      var pendingImg = form.parentElement &&
        form.parentElement.querySelector('img[src^="data:image"]');
      if (pendingImg) imageUrl = pendingImg.src;

      if (text || imageUrl) {
        _showOptimisticUserBubble(text, imageUrl);
      }
    });
  }


  /* ══════════════════════════════════════════
     IMAGE PASTE — Ctrl+V para pegar imagen al chat (v0.14.1)
  ══════════════════════════════════════════
     User pidió "como en las apps pro de IA, si copio una imagen
     con Ctrl+C poder pegarla con Ctrl+V". El textarea capta el
     paste, extraemos el File del clipboard, lo inyectamos en el
     input file oculto del rx.upload via DataTransfer + dispatch
     change → Reflex procesa via handle_upload existente y rellena
     pending_image como con el botón 📎.

     Funciona con: screenshot del recortes (Win+Shift+S),
     copiar imagen del navegador, copiar archivo de imagen del
     explorador, etc. */

  function initImagePaste() {
    document.addEventListener('paste', function (e) {
      // Solo cuando el textarea del chat está focuseado
      var ta = e.target;
      if (!ta || ta.id !== 'message') return;

      var cb = e.clipboardData || window.clipboardData;
      if (!cb || !cb.items) return;

      for (var i = 0; i < cb.items.length; i++) {
        var item = cb.items[i];
        if (item.kind !== 'file') continue;
        if (item.type.indexOf('image') !== 0) continue;

        var file = item.getAsFile();
        if (!file) continue;

        // El clipboard suele entregar la imagen como "image.png"
        // sin más. Ponemos un timestamp para distinguir si el user
        // pega varias en sucesión.
        var ext = (file.type.split('/')[1] || 'png').split('+')[0];
        var renamed = new File(
          [file],
          'pasted-' + Date.now() + '.' + ext,
          { type: file.type }
        );

        // Buscar el input file oculto del rx.upload. Solo hay uno
        // en la página (id="img_upload" en el wrapper, el input es
        // hijo). Selector amplio por si Reflex cambia la estructura.
        var fileInput = document.querySelector('input[type="file"]');
        if (!fileInput) {
          console.warn('[ashley-paste] no file input found');
          return;
        }

        // DataTransfer es la única forma legal de setear input.files
        // programáticamente. dispatchEvent('change') hace que react-
        // dropzone (subyacente a rx.upload) recoja el archivo y llame
        // al on_drop handler → handle_upload en Python.
        try {
          var dt = new DataTransfer();
          dt.items.add(renamed);
          fileInput.files = dt.files;
          fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (err) {
          console.warn('[ashley-paste] failed:', err);
          return;
        }

        // No preventDefault sobre el resto — si paste contenía texto
        // además de imagen (raro pero posible), dejamos que el texto
        // se pegue normal. Solo absorbemos la imagen.
        e.preventDefault();
        return;
      }
    });
  }


  /* ══════════════════════════════════════════
     INTERACTIVE SOUNDS — hover + click (v0.16.5)
  ══════════════════════════════════════════
     User reportó "no hay sonido cuando paso el ratón por los botones
     ni cuando clickeo". Tenía las funciones playToggleOn/playHeartHover
     definidas pero nunca las wireé a eventos reales.

     Approach: event delegation en document. Mouseover/click bubbles a
     document, así que un solo listener captura TODOS los botones,
     incluso los que React añade después. */

  function initInteractiveSounds() {
    // Selectores de elementos "interactivos" que merecen sonido:
    var SEL = '.ashley-nav-link, .ashley-action-btn, .heart-frame, ' +
              '.ashley-toggle-seg, .ashley-send-btn, ' +
              '.ashley-mic-btn, button[type="submit"]';

    // ── Hover: track el último botón hovered. Solo dispara sonido
    // cuando entras a uno NUEVO. Mouseover bubbles, mouseenter no —
    // así que usamos mouseover + tracking de "elemento actual".
    var lastHovered = null;
    document.addEventListener('mouseover', function (e) {
      if (!_audioReady) return;
      var btn = e.target.closest(SEL);
      if (btn === lastHovered) return;
      if (btn) {
        lastHovered = btn;
        // Tap muy suave warm — el "sonidito" boutique al hover
        warmTone(740, 0.08, 0.06, { wave: 'sine', overtone: false });
      } else {
        lastHovered = null;
      }
    }, { passive: true });

    // ── Click: sound on press. Skip send button (la animación del
    // mensaje + playSend del observer ya dan feedback). Heart tiene
    // su propio tono más rico. Resto: playToggleOn genérico.
    document.addEventListener('click', function (e) {
      if (!_audioReady) return;
      var btn = e.target.closest(SEL);
      if (!btn) return;
      // Send button: deja que el msg observer reproduzca playSend
      if (btn.classList.contains('ashley-send-btn') ||
          btn.getAttribute('type') === 'submit') {
        return;
      }
      // Heart: sound más rico (es el único elemento "afectivo")
      if (btn.classList.contains('heart-frame')) {
        warmTone(523, 0.20, 0.14, { wave: 'sine' });
        setTimeout(function () { warmTone(659, 0.22, 0.10, { wave: 'sine' }); }, 70);
        return;
      }
      // Resto de botones: click warm corto
      warmTone(440, 0.10, 0.10, { wave: 'sine' });
      setTimeout(function () { warmTone(587, 0.12, 0.08, { wave: 'sine' }); }, 55);
    }, { passive: true });
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
  // v0.14.3 — antes 5 min era demasiado agresivo. El user reportaba
  // que minimizar 10-30 min "reseteaba" la sesión: recarga del
  // frontend, scroll arriba, mood overlay perdido, follow-up proactivo
  // disparado, etc. Y el motivo original (refrescar time context) ya
  // no aplica — _build_time_context() usa datetime.now() en cada turn,
  // así que el time es fresh per-message sin necesidad de reload.
  //
  // Subido a 60 min: solo recargamos si la app estuvo oculta >1h
  // (caso real de "te fuiste a dormir / a trabajar"). Para gaps cortos
  // <60 min mantenemos la sesión viva — el user vuelve y todo está
  // como lo dejó.
  //
  // ADEMÁS marcamos sessionStorage antes del reload para que la
  // sesión recargada sepa "esto fue auto-reload, no abrir engagement
  // proactivo de nuevo" — el user no necesita un saludo cada vez que
  // vuelve de un break.
  var _hiddenAt = 0;
  var STALE_THRESHOLD_MS = 60 * 60 * 1000; // 60 minutos (era 5)

  function initVisibilityReload() {
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        _hiddenAt = Date.now();
      } else if (_hiddenAt > 0) {
        var elapsed = Date.now() - _hiddenAt;
        _hiddenAt = 0;
        if (elapsed > STALE_THRESHOLD_MS) {
          console.log('[ashley-fx] App was hidden for ' + Math.round(elapsed / 60000) + ' min — reloading for fresh state');
          try { sessionStorage.setItem('ashley_auto_reload', '1'); } catch (e) {}
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
    // v0.14.5 — antes era .affection-bar (layout viejo). El rediseño
    // v0.16 sustituyó la barra vertical por el SVG .heart-frame.
    var bar = document.querySelector('.heart-frame');
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

  // ── Celebrate animation on heart itself (v0.14.5) ────
  // Disparada cada vez que el afecto cambia. Le da al heart un
  // bump visual claro: scale + glow burst arriba (subir), shrink+desat
  // (bajar). Es lo que hace que subir el afecto se sienta tactile,
  // no solo el numerito cambiando.
  function _celebrateHeart(isUp) {
    var heartEl = document.querySelector('.heart-frame');
    if (!heartEl) return;
    var cls = isUp ? 'celebrate-up' : 'celebrate-down';
    heartEl.classList.remove('celebrate-up', 'celebrate-down');
    // Force reflow para que el reset registre y la animación reinicie
    void heartEl.offsetWidth;
    heartEl.classList.add(cls);
    var dur = isUp ? 800 : 600;
    setTimeout(function () { heartEl.classList.remove(cls); }, dur);
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
      // v0.14.5 — buscamos el .ashley-affection-number (el "100" del
      // header del chat). Antes el observer iteraba el parent de
      // .affection-bar buscando un text con número 0-100, pero ese
      // selector ya no existe en el layout v0.16.
      var numEl = document.querySelector('.ashley-affection-number');
      if (!numEl) return;
      var current = parseInt(numEl.textContent, 10);
      if (isNaN(current) || current < 0 || current > 100) return;

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

      // Floating heart + celebrate animation on the heart itself
      if (delta > 0) {
        _spawnHeart(true, delta);
        _celebrateHeart(true);
        playAffectionUp();
      } else if (delta < 0) {
        _spawnHeart(false, delta);
        _celebrateHeart(false);
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
    // v0.16 — starfield desactivado en el rediseño boutique noir.
    // initStarfield();
    initTextarea();
    initObservers();
    initInteractiveSounds();  // v0.16.5 — hover/click sounds
    initImagePaste();          // v0.14.1 — Ctrl+V de imagen al chat
    initOptimisticUI();        // v0.14.3 — bubble fake instantáneo
    initNotificationObserver();
    initPinOnTopObserver();
    initVisibilityReload();
    initAffectionObserver();
    initAchievementObserver();
    initVersionBadge();
    initUpdateNotifier();
  }

  // v0.15.4 — el canvas de starfield ahora lo renderiza Reflex
  // (rx.el.canvas en index()). Pero el script defer puede correr
  // antes de que React monte el árbol → no encuentra el canvas →
  // las estrellas no arrancan.
  // Solución: si al hacer boot el canvas no existe todavía,
  // reintentamos cada 100ms hasta máximo 2s. Una vez detectado,
  // boot() arranca el loop de estrellas y el resto de inits.
  function bootWhenReady() {
    var canvas = document.getElementById('ashley-starfield');
    if (canvas) {
      boot();
      return;
    }
    var tries = 0;
    var iv = setInterval(function () {
      tries++;
      if (document.getElementById('ashley-starfield') || tries > 20) {
        clearInterval(iv);
        boot();
      }
    }, 100);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootWhenReady);
  } else {
    bootWhenReady();
  }

})();
