"""
styles.py — Global CSS styles for the Ashley companion app.

Extracted from reflex_companion.py.  Contains the ``global_styles()``
function that returns an ``rx.html`` block with all CSS animations,
glass-morphism classes, scrollbar overrides, and layout helpers.
"""

import reflex as rx

from .config import COLOR_PRIMARY


def global_styles():
    return rx.html(f"""
<!-- v0.16 — Google Fonts (serif elegante para "Ashley" branding) + sans
     limpia para chat. Cormorant Garamond es el serif boutique perfecto:
     letras finas, ascenders altos, looks expensive sin ser pretencioso. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<!-- v0.16.4 — gradient compartido para los rayos de luz cenital.
     Los polygons del SVG _light_rays_svg() rellenan con url(#ashley-ray-grad).
     Definirlo una vez aquí evita duplicar el <defs> en cada panel. -->
<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">
  <defs>
    <linearGradient id="ashley-ray-grad" x1="0" y1="0" x2="0" y2="1">
      <!-- v0.16.5 fade más temprano: la luz angelical toca cabeza
           y hombros (upper 0-50%) y se desvanece antes de tocar
           el cuerpo (50%+). Antes el fade era a 70% — los rayos
           llegaban casi al fondo del panel y se sentía "apuntando
           al espacio vacío". -->
      <stop offset="0%"  stop-color="#ffe0b3" stop-opacity="0.75"/>
      <stop offset="20%" stop-color="#ffcc88" stop-opacity="0.45"/>
      <stop offset="45%" stop-color="#ffb866" stop-opacity="0.10"/>
      <stop offset="70%" stop-color="#ffb866" stop-opacity="0"/>
    </linearGradient>
  </defs>
</svg>
<style>
  /* ── Body bg cálido con gradient diagonal de wine a casi-negro,
        más capas de luz ambient suave que se mueven. El user pidió
        "efectos de luz constantes y suaves para que el chat no se
        sienta como algo solido que no se mueve". */
  html, body {{
    background:
      radial-gradient(ellipse at top left, rgba(212,163,115,0.10) 0%, transparent 55%),
      radial-gradient(ellipse at bottom right, rgba(140,60,70,0.18) 0%, transparent 60%),
      linear-gradient(135deg, #2a0f15 0%, #150810 70%, #0a0408 100%) !important;
    background-attachment: fixed !important;
    margin: 0; padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #e8dcc4;
  }}

  /* ── Capas de luz ambient — siempre en movimiento sutil ────────
        Tres capas con frecuencias diferentes flotando lento. Crean
        la sensación de que la habitación está iluminada por varias
        velas que tiemblan suave. Pointer-events:none para que no
        bloqueen clicks. */
  .ambient-glow-1, .ambient-glow-2, .ambient-glow-3 {{
    position: fixed;
    pointer-events: none;
    z-index: 0;
    /* v0.16.14 — Quitado `will-change: transform, opacity` y reducido
       blur de 80px → 30px. El blur(80px) sobre elementos a 70vw/60vw =
       millones de pixels procesados por frame × 3 capas × 60fps.
       30px sigue dando el efecto suave de halo/vela sin matar la GPU. */
    filter: blur(30px);
  }}
  .ambient-glow-1 {{
    top: -15vh; left: -10vw;
    width: 70vw; height: 70vh;
    background: radial-gradient(ellipse,
      rgba(212,163,115,0.20) 0%,
      rgba(212,163,115,0.08) 40%,
      transparent 65%);
    animation: ambientFloat1 16s ease-in-out infinite;
  }}
  .ambient-glow-2 {{
    bottom: -10vh; right: -10vw;
    width: 60vw; height: 60vh;
    background: radial-gradient(ellipse,
      rgba(196,127,90,0.16) 0%,
      rgba(140,60,70,0.10) 40%,
      transparent 65%);
    animation: ambientFloat2 22s ease-in-out infinite;
  }}
  .ambient-glow-3 {{
    top: 30vh; left: 40vw;
    width: 35vw; height: 35vh;
    background: radial-gradient(circle,
      rgba(232,202,158,0.10) 0%,
      transparent 60%);
    animation: ambientFloat3 28s ease-in-out infinite;
  }}
  @keyframes ambientFloat1 {{
    0%, 100% {{ transform: translate(0, 0) scale(1); opacity: 0.65; }}
    33%      {{ transform: translate(3vw, 2vh) scale(1.06); opacity: 0.85; }}
    66%      {{ transform: translate(-2vw, 4vh) scale(0.95); opacity: 0.55; }}
  }}
  @keyframes ambientFloat2 {{
    0%, 100% {{ transform: translate(0, 0) scale(1); opacity: 0.55; }}
    50%      {{ transform: translate(-3vw, -2vh) scale(1.08); opacity: 0.85; }}
  }}
  @keyframes ambientFloat3 {{
    0%, 100% {{ transform: translate(0, 0) scale(1); opacity: 0.40; }}
    50%      {{ transform: translate(4vw, -3vh) scale(1.10); opacity: 0.65; }}
  }}

  /* Spotlight cálido sobre el área de la portrait — efecto vela
     iluminando por arriba como en el mockup. */
  .portrait-spotlight {{
    position: absolute;
    top: -10%; left: 50%;
    transform: translateX(-50%);
    width: 100%; height: 60%;
    background: radial-gradient(ellipse at top,
      rgba(232,202,158,0.30) 0%,
      rgba(212,163,115,0.10) 30%,
      transparent 55%);
    pointer-events: none;
    z-index: 2;
    filter: blur(20px);
    animation: spotlightFlicker 8s ease-in-out infinite;
  }}
  @keyframes spotlightFlicker {{
    0%, 100% {{ opacity: 0.85; }}
    25%      {{ opacity: 1.00; }}
    50%      {{ opacity: 0.75; }}
    75%      {{ opacity: 0.95; }}
  }}

  /* ── Tipografía elegante para "Ashley" branding ─────────── */
  .ashley-serif {{
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    font-weight: 600;
    letter-spacing: 0.01em;
    font-feature-settings: "liga" 1, "kern" 1;
  }}
  .ashley-serif-light {{
    font-family: 'Cormorant Garamond', Georgia, serif !important;
    font-weight: 400;
    letter-spacing: 0.02em;
  }}
  .radix-themes,
  [data-is-root-theme],
  [data-radix-root] {{
    background: transparent !important;
  }}

  /* v0.13.13/14: Radix Select / Popover dropdowns DENTRO del panel
     de Settings (que tiene overflow:auto + glass-morphism translúcido)
     se renderizaban SIN fondo opaco — el dropdown abría sobre el
     siguiente bloque pero su transparencia hacía que viéramos el
     texto del bloque a través de los options. La solución de solo
     z-index no bastaba: aunque estuvieran encima, sin fondo se
     veía igual de mal.
     Fix definitivo: z-index extremo + background opaco oscuro +
     borde + sombra. Targeting amplio para cubrir todos los popups
     de Radix (Select, Popover, DropdownMenu) — el bug del fondo
     transparente afecta a todos por igual cuando viven dentro de
     un container con overflow. */
  [data-radix-popper-content-wrapper],
  [data-radix-select-content],
  [data-radix-popover-content],
  [data-radix-dropdown-menu-content],
  [data-radix-menu-content],
  .rt-SelectContent,
  .rt-PopoverContent,
  .rt-DropdownMenuContent,
  .rt-BaseMenuContent {{
    z-index: 99999 !important;
    background: #18181f !important;
    border: 1px solid rgba(255, 154, 238, 0.18) !important;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7),
                0 0 0 1px rgba(255, 154, 238, 0.05) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
  }}

  /* Items individuales — fondo transparente por defecto sobre el
     fondo oscuro del wrapper. Cuando se hover/highlight, color rosa
     sutil para feedback visual. */
  [data-radix-select-item],
  [data-radix-dropdown-menu-item],
  [data-radix-menu-item],
  .rt-SelectItem,
  .rt-DropdownMenuItem {{
    background: transparent !important;
    color: #ddd !important;
    padding: 8px 12px !important;
    cursor: pointer !important;
  }}

  [data-radix-select-item][data-highlighted],
  [data-radix-dropdown-menu-item][data-highlighted],
  [data-radix-menu-item][data-highlighted],
  .rt-SelectItem:hover,
  .rt-DropdownMenuItem:hover {{
    background: rgba(255, 154, 238, 0.12) !important;
    color: #fff !important;
    outline: none !important;
  }}

  /* El item seleccionado (con check) — destacar con color primario */
  [data-radix-select-item][data-state="checked"],
  .rt-SelectItem[data-state="checked"] {{
    background: rgba(255, 154, 238, 0.18) !important;
    color: {COLOR_PRIMARY} !important;
    font-weight: 600 !important;
  }}

  /* ── Animaciones ─────────────────────────────────────── */
  @keyframes fadeSlideIn {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  @keyframes cursorBlink {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0; }}
  }}
  @keyframes avatarPulse {{
    0%, 100% {{ box-shadow: 0 0 8px rgba(255,154,238,0.5); }}
    50%       {{ box-shadow: 0 0 26px rgba(255,154,238,1), 0 0 8px rgba(255,154,238,0.6); }}
  }}
  @keyframes portraitGlow {{
    0%, 100% {{
      box-shadow: 0 0 28px rgba(255,154,238,0.3),
                  0 0  0 2px rgba(255,154,238,0.2),
                  0 10px 40px rgba(0,0,0,0.7);
    }}
    50% {{
      box-shadow: 0 0 70px rgba(255,154,238,0.85),
                  0 0  0 3px rgba(255,154,238,0.75),
                  0 10px 50px rgba(0,0,0,0.8);
    }}
  }}
  @keyframes micListening {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(255,80,120,0.6); }}
    50%       {{ box-shadow: 0 0 0 8px rgba(255,80,120,0); }}
  }}
  /* Usamos body.mic-listening (no .ashley-mic-btn.listening) porque
     Reflex re-renderiza el botón y quitaría la clase. El body no se toca. */
  body.mic-listening #ashley-mic-btn,
  body.mic-listening .ashley-mic-btn {{
    background: rgba(255,80,120,0.22) !important;
    color: #ff7088 !important;
    border: 1px solid rgba(255,80,120,0.7) !important;
    animation: micListening 1.0s ease-in-out infinite !important;
    box-shadow: 0 0 14px rgba(255,80,120,0.4) !important;
  }}
  /* Estado: transcribiendo (después de soltar el mic, esperando al backend) */
  @keyframes micTranscribing {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(100,180,255,0.5); }}
    50%       {{ box-shadow: 0 0 0 8px rgba(100,180,255,0); }}
  }}
  body.mic-transcribing #ashley-mic-btn,
  body.mic-transcribing .ashley-mic-btn {{
    background: rgba(100,180,255,0.18) !important;
    color: #64b4ff !important;
    border: 1px solid rgba(100,180,255,0.6) !important;
    animation: micTranscribing 0.9s ease-in-out infinite !important;
    cursor: wait !important;
  }}
  body.mic-transcribing #ashley-mic-btn::after,
  body.mic-transcribing .ashley-mic-btn::after {{
    content: " …";
    font-size: 11px;
  }}

  /* ── Clases funcionales ──────────────────────────────── */
  .msg-enter         {{ animation: fadeSlideIn 0.25s ease-out both; }}
  /* ── Optimistic UI (v0.16.12 — simple version) ────────────────
     El user-msg real NO anima slide-up. Razón: el optimistic JS lo
     pone en posición INMEDIATAMENTE al pulsar enter; cuando el real
     llega ms después, el observer borra el optimistic y deja al real.
     Sin esta regla, el real ejecutaría fadeSlideIn (translateY 12px
     → 0) tras el swap → el user vería su bubble "moverse" o aparecer
     de nuevo. Con animation:none, real y optimistic son visualmente
     intercambiables. */
  .user-msg.msg-enter {{ animation: none !important; }}
  .avatar-thinking   {{ animation: avatarPulse 1.4s ease-in-out infinite !important; }}
  .portrait-thinking {{ animation: portraitGlow 1.4s ease-in-out infinite !important; }}
  .portrait-idle     {{
    box-shadow: 0 0 22px rgba(255,154,238,0.2),
                0 0  0 2px rgba(255,154,238,0.1),
                0 10px 40px rgba(0,0,0,0.7);
    transition: box-shadow 0.6s ease;
  }}
  .cursor-blink::after {{
    content: '▌';
    color: {COLOR_PRIMARY};
    animation: cursorBlink 0.9s step-end infinite;
    margin-left: 2px;
  }}
  /* ── Burbujas estilo wine boutique (v0.16.1) ─────────────────
     Lora serif (más elegante para body de chat que Inter sans).
     Ashley: vino oscuro con borde ámbar suave.
     User: marrón cálido con borde más sutil.

     v0.16.7 — tipografía cambiada de Lora serif (15px) a Inter sans
     (17px) por feedback de legibilidad. El user reportó que le
     costaba leer a distancia. Inter es el font de UI más probado
     para legibilidad en pantalla — letterforms abiertos, x-height
     alto. La elegancia boutique se mantiene en el branding (Ashley
     header, name overlay) que sigue siendo Cormorant Garamond serif.

     Italics seguimos respetando para *gestos* que Ashley usa. */
  .bubble-ashley, .bubble-user {{
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
    font-size: 17px !important;
    line-height: 1.6 !important;
    letter-spacing: 0.01em !important;
    font-weight: 400 !important;
  }}
  /* CRÍTICO: rx.markdown del real renderiza <p> con marginTop/Bottom
     1em (~16px arriba y 16px abajo). Sin esto, el real es ~32px más
     alto que el optimistic JS (que usa <p style="margin:0">). Cuando
     el observer hace el swap (borra optimistic, deja real), el bubble
     cambia de altura → "se mueve". Forzar margin:0 a TODO bloque dentro
     de la burbuja iguala dimensiones → swap invisible. */
  .bubble-ashley p, .bubble-user p,
  .bubble-ashley h1, .bubble-user h1,
  .bubble-ashley h2, .bubble-user h2,
  .bubble-ashley h3, .bubble-user h3,
  .bubble-ashley h4, .bubble-user h4,
  .bubble-ashley h5, .bubble-user h5,
  .bubble-ashley h6, .bubble-user h6,
  .bubble-ashley ul, .bubble-user ul,
  .bubble-ashley ol, .bubble-user ol,
  .bubble-ashley li, .bubble-user li {{
    margin-top: 0 !important;
    margin-bottom: 0 !important;
  }}
  .bubble-ashley em, .bubble-user em,
  .bubble-ashley i, .bubble-user i {{
    font-style: italic !important;
    color: rgba(245,235,213,0.78) !important;
    /* En italic mantenemos sans (Inter italic queda elegante) — si
       prefieres serif italic para que los *gestos* destaquen como
       prosa, cambiar a 'Lora' aquí. */
  }}
  /* v0.16.6 — diferenciación clara Ashley vs User.
     User feedback: las dos burbujas se veían demasiado parecidas
     (ambos wine apagado). Ahora:
       Ashley → vino-púrpura oscuro con borde ámbar tenue
                ("color casa", refleja el ámbar de su nombre/heart)
       User   → tabac/cognac warm brown con borde crema más definido
                ("leather" — distinto pero todavía warm boutique)
     Ambos siguen siendo cálidos, pero el contraste de tono (púrpura
     vs ocre) es claro de un vistazo. */
  /* v0.16.14 — REMOVIDO backdrop-filter de las burbujas. Era el principal
     causante de tirones al scrollear: con 50 burbujas en el chat, cada
     scroll frame el compositor recalculaba 50 blur masks. Las burbujas
     ya tenían background con alpha 0.82 sobre fondo casi negro, así que
     visualmente la diferencia es mínima — pero el scroll va MUCHO más
     fluido. Mantenemos el blur solo en .glass-chat (panel padre, una
     sola instancia, no se multiplica) y en .ashley-input-pill. */
  .bubble-ashley {{
    position: relative;
    background: linear-gradient(135deg,
      rgba(50, 26, 38, 0.92) 0%,
      rgba(40, 20, 32, 0.92) 100%) !important;
    border: 1px solid rgba(212,163,115, 0.22) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.30),
                inset 0 1px 0 rgba(232,220,196,0.06) !important;
    color: #f5ebd5 !important;
  }}
  .bubble-user {{
    position: relative;
    background: linear-gradient(135deg,
      rgba(82, 55, 38, 0.92) 0%,
      rgba(64, 42, 28, 0.92) 100%) !important;
    border: 1px solid rgba(232,202,158, 0.30) !important;
    box-shadow: 0 4px 22px rgba(0,0,0,0.30),
                inset 0 1px 0 rgba(255,235,200,0.10) !important;
    color: #faf2dd !important;
  }}

  /* v0.16.9 — tails REMOVIDOS.
     Probé añadir triangulitos ::before a las burbujas para feel
     "chat-app" tipo iMessage, pero quedaron pochos: triángulos
     sólidos vs burbuja con gradient + borde + glass = costura
     visible. Modern apps de chat IA (Discord, ChatGPT, Claude
     web) NO usan tails — el avatar a la izquierda + alineación
     a derecha es suficiente para identificar al hablante.
     Vuelvo al diseño minimal sin tails. Sigo dejando
     position:relative en .bubble-* por si en el futuro se quiere
     posicionar algo absoluto dentro (timestamp, reaction, etc.). */

  /* ── Glass panels en tonos vino ─────────────────────────── */
  .glass-chat {{
    background: rgba(20, 8, 14, 0.30) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border: 1px solid rgba(212,163,115,0.10) !important;
  }}
  /* ══════════════════════════════════════════════════════════════
     v0.16 — Layout 2-columnas estilo "boutique noir"
     Portrait gigante a la izquierda + chat a la derecha
     ══════════════════════════════════════════════════════════════ */

  /* Wrapper raíz del layout 2-cols */
  .ashley-layout-2col {{
    display: flex;
    width: 100%;
    height: 100vh;
    position: relative;
    z-index: 1;  /* sobre los ambient glows */
  }}

  /* ── Panel izquierdo: portrait + nav arriba + actions abajo ──── */
  .ashley-portrait-panel {{
    position: relative;
    flex: 0 0 45%;
    max-width: 720px;
    height: 100vh;
    overflow: hidden;
    background: linear-gradient(180deg,
      rgba(35,15,20,0.6) 0%,
      rgba(20,8,12,0.85) 60%,
      rgba(15,6,10,0.95) 100%);
    border-right: 1px solid rgba(212,163,115,0.10);
  }}

  /* Imagen mood que llena el panel — con vignette y spotlight.
     v0.16.14 — Fix anti-flash entre transiciones de mood se logra
     ÚNICAMENTE via JS preload (preloadMoodImages en ashley_fx.js) que
     mete las 10 imágenes en el cache del browser al arranque. Cuando
     React cambia el inline backgroundImage, el browser ya tiene la
     imagen → swap instantáneo, sin flash.
     INTENTO PREVIO (revertido): añadir aquí background-color y un
     fallback `background-image: url(...)` rompía el inline style en
     producción — el panel se quedaba completamente negro. La imagen
     real viene del inline style en components.py (rx.box con
     style.backgroundImage). */
  .ashley-mood-image {{
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center top;
    background-repeat: no-repeat;
    opacity: 0.95;
    z-index: 1;
  }}
  /* Vignette que oscurece bordes para que el nombre se lea bien */
  .ashley-mood-vignette {{
    position: absolute;
    inset: 0;
    background:
      linear-gradient(180deg,
        rgba(20,8,12,0.20) 0%,
        transparent 25%,
        transparent 50%,
        rgba(15,6,10,0.85) 100%),
      radial-gradient(ellipse at 50% 30%,
        transparent 30%,
        rgba(15,6,10,0.45) 90%);
    pointer-events: none;
    z-index: 3;
  }}

  /* Nav horizontal arriba del panel izquierdo (Ashley/Recuerdos/...) */
  .ashley-top-nav {{
    position: absolute;
    top: 0; left: 0; right: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: space-evenly;
    padding: 18px 24px;
    background: linear-gradient(180deg,
      rgba(15,6,10,0.7) 0%,
      transparent 100%);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }}
  .ashley-nav-link {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    padding: 6px 10px;
    border-radius: 8px;
    color: #c4b3a4;
    transition: all 0.25s ease;
    user-select: none;
  }}
  .ashley-nav-link:hover {{
    color: #e8dcc4;
    background: rgba(212,163,115,0.08);
    transform: translateY(-1px);
  }}
  .ashley-nav-link.active {{
    color: {COLOR_PRIMARY};
    text-shadow: 0 0 12px rgba(212,163,115,0.5);
  }}
  .ashley-nav-link svg {{
    width: 18px; height: 18px;
    stroke-width: 1.6;
  }}
  .ashley-nav-link span {{
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.04em;
  }}

  /* Bloque inferior del panel izquierdo: nombre + status + actions */
  .ashley-portrait-overlay {{
    position: absolute;
    bottom: 0; left: 0; right: 0;
    padding: 32px 32px 32px 32px;
    z-index: 4;
    text-align: center;
    background: linear-gradient(180deg,
      transparent 0%,
      rgba(15,6,10,0.85) 70%,
      rgba(10,4,7,0.95) 100%);
  }}
  .ashley-name-large {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-weight: 600;
    font-size: 56px;
    line-height: 1;
    color: #e8dcc4;
    letter-spacing: 0.01em;
    text-shadow:
      0 2px 12px rgba(0,0,0,0.6),
      0 0 30px rgba(212,163,115,0.20);
    margin: 0;
  }}
  .ashley-status-line {{
    margin-top: 6px;
    color: {COLOR_PRIMARY};
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.05em;
  }}
  .ashley-status-line .status-dot {{
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    background: {COLOR_PRIMARY};
    margin-right: 6px;
    box-shadow: 0 0 8px rgba(212,163,115,0.7);
    animation: statusPulse 2.4s ease-in-out infinite;
  }}
  @keyframes statusPulse {{
    0%, 100% {{ opacity: 0.6; transform: scale(1); }}
    50%      {{ opacity: 1.0; transform: scale(1.15); }}
  }}

  /* Botones de acción circulares debajo del nombre (mic/✨/focus/📎) */
  .ashley-action-row {{
    display: flex;
    justify-content: center;
    gap: 14px;
    margin-top: 18px;
  }}
  .ashley-action-btn {{
    width: 42px; height: 42px;
    border-radius: 50%;
    background: rgba(35,17,25,0.5);
    border: 1px solid rgba(212,163,115,0.25);
    color: #c4b3a4;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.25s ease;
    backdrop-filter: blur(10px);
  }}
  .ashley-action-btn:hover {{
    background: rgba(212,163,115,0.15);
    border: 1px solid rgba(212,163,115,0.6);
    color: {COLOR_PRIMARY};
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(212,163,115,0.25);
  }}
  .ashley-action-btn.active {{
    background: rgba(212,163,115,0.20);
    border: 1px solid rgba(212,163,115,0.8);
    color: {COLOR_PRIMARY};
    box-shadow: 0 0 14px rgba(212,163,115,0.5);
  }}
  .ashley-action-btn svg {{
    width: 18px; height: 18px;
    stroke-width: 1.7;
  }}

  /* ── Light rays cenital v0.16.4 ───────────────────────────────
     User feedback explícito (descripción detallada):
       "rayos vienen desde arriba, cayendo verticalmente sobre el
        personaje como foco o luz cenital. Abriéndose ligeramente
        conforme bajan, creando un cono de luz invertido. Tono
        cálido amarillento/dorado. Intensidad suave y difusa, no
        rayos duros tipo láser — luz angelical, iluminación dramática
        estilo escenario. Iluminan cabeza y hombros, el cuerpo se
        desvanece hacia las sombras."

     Implementación: SVG con 5 polígonos (trapezoides finos) que
     parten de un punto cerca del top-left/top-center del panel y
     se abren hacia abajo. Gradient vertical interior (gold→transparent
     a 70% de altura) hace que la luz se desvanezca antes de llegar
     al fondo → el cuerpo queda en sombras.

     Cada rayo tiene su propio timing de pulse (independiente, fases
     desencajadas) → intensidad cambia armónicamente sin sincronizarse,
     lo que da sensación orgánica de luz natural. */

  .ashley-light-rays {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    mix-blend-mode: screen;
    z-index: 2;
  }}
  .ashley-light-rays polygon {{
    fill: url(#ashley-ray-grad);
    filter: blur(3px);
    transform-origin: 50% 0%;
    transform-box: fill-box;
  }}
  .ashley-light-rays .ray-1 {{
    animation: rayPulseA 7.5s ease-in-out infinite;
  }}
  .ashley-light-rays .ray-2 {{
    animation: rayPulseB 9.5s ease-in-out infinite;
    animation-delay: -2s;
  }}
  .ashley-light-rays .ray-3 {{
    animation: rayPulseC 6.5s ease-in-out infinite;
    animation-delay: -3.5s;
  }}
  .ashley-light-rays .ray-4 {{
    animation: rayPulseD 8.5s ease-in-out infinite;
    animation-delay: -1s;
  }}
  .ashley-light-rays .ray-5 {{
    animation: rayPulseE 10.5s ease-in-out infinite;
    animation-delay: -4s;
  }}
  @keyframes rayPulseA {{
    0%, 100% {{ opacity: 0.35; }}
    50%      {{ opacity: 0.80; }}
  }}
  @keyframes rayPulseB {{
    0%, 100% {{ opacity: 0.55; }}
    50%      {{ opacity: 0.20; }}
  }}
  @keyframes rayPulseC {{
    0%, 100% {{ opacity: 0.40; }}
    60%      {{ opacity: 0.90; }}
  }}
  @keyframes rayPulseD {{
    0%, 100% {{ opacity: 0.45; }}
    40%      {{ opacity: 0.15; }}
  }}
  @keyframes rayPulseE {{
    0%, 100% {{ opacity: 0.30; }}
    50%      {{ opacity: 0.70; }}
  }}

  /* Variante chat-panel: rayos más sutiles porque ahí no hay
     personaje; la luz es ambiental, no spotlight. */
  .ashley-chat-panel .ashley-light-rays {{
    opacity: 0.55;
  }}

  /* v0.16.5 — fix CRÍTICO: alinear rayos con la imagen del personaje.
     El user explicó: "la primera imagen el rayo TOCA al personaje, en
     la segunda cae al lado del personaje". Antes los rayos abarcaban
     todo el panel entero pero la imagen 2D es un cuadrado centrado
     más pequeño → los rayos pasaban POR EL ESPACIO VACÍO al lado de
     Ashley, no sobre ella. Ahora en mode-2d, el contenedor del SVG
     se posiciona exactamente donde está la imagen → los rayos caen
     sobre la cara/hombros de Ashley = chiaroscuro coherente. */
  .ashley-portrait-panel.mode-2d .ashley-light-rays {{
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    margin-top: -40px;
    width: 92%;
    max-width: 680px;
    height: auto;
    aspect-ratio: 1 / 1;
  }}
  /* En 3D la imagen llena el panel entero → rayos full-panel funcionan,
     no necesita override (uso default top:0,left:0,100% × 100%). */

  /* ── 2D mode (square frame) vs 3D mode (full vertical) ─────────
     v0.16.1: el user pidió que en 2D la imagen sea más cuadrada
     (no toma toda la altura del panel) y en 3D quede full vertical.
     Toggle en .ashley-portrait-panel.mode-2d / .mode-3d. */

  /* Default (3D): la imagen llena el panel vertical entero */
  .ashley-portrait-panel.mode-3d .ashley-mood-image {{
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center top;
  }}

  /* 2D v0.16.3 — imagen cuadrada CENTRADA verticalmente, MÁS grande.
     User feedback: "Ashley sea más grande, aún hay espacio horizontal
     que le sobra". Antes width=min(72%, 460px) dejaba mucho espacio
     a los lados en panels anchos. Ahora 92%, sin cap restrictivo. */
  .ashley-portrait-panel.mode-2d .ashley-mood-image {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    margin-top: -40px;
    width: 92%;
    max-width: 680px;  /* cap más alto — solo evita que en 4K llene
                          un panel gigante hasta el infinito */
    aspect-ratio: 1 / 1;
    background-size: cover;
    background-position: center top;
    border-radius: 22px;
    -webkit-mask-image: linear-gradient(180deg,
      transparent 0%,
      rgba(0,0,0,0.6) 6%,
      black 14%,
      black 86%,
      rgba(0,0,0,0.6) 94%,
      transparent 100%);
    mask-image: linear-gradient(180deg,
      transparent 0%,
      rgba(0,0,0,0.6) 6%,
      black 14%,
      black 86%,
      rgba(0,0,0,0.6) 94%,
      transparent 100%);
    box-shadow:
      0 24px 60px rgba(0,0,0,0.55),
      0 -8px 30px rgba(0,0,0,0.35);
  }}
  /* En 2D, la vignette es solo un gradient muy sutil abajo (para que
     el overlay con el nombre se lea sobre cualquier color del asset). */
  .ashley-portrait-panel.mode-2d .ashley-mood-vignette {{
    background:
      linear-gradient(180deg,
        transparent 0%,
        transparent 60%,
        rgba(15,6,10,0.7) 100%);
  }}
  /* Halo ámbar suave detrás del cuadrado 2D — subtle warm light
     coming from behind the portrait, refuerza el "spotlight" feel
     sin ser un stripe. v0.16.3: scale up para acompañar la imagen
     más grande. */
  .ashley-portrait-panel.mode-2d::before {{
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    margin-top: -40px;
    width: 105%;
    max-width: 800px;
    aspect-ratio: 1 / 1;
    background: radial-gradient(circle,
      rgba(212,163,115,0.20) 0%,
      rgba(212,163,115,0.08) 35%,
      transparent 65%);
    pointer-events: none;
    /* v0.16.14 — blur(50px) → blur(25px). Halo grande (max 800px) con
       blur extremo era costoso por frame de animación. 25px sigue dando
       el efecto soft. */
    filter: blur(25px);
    z-index: 1;
    /* Animación 6s → 12s: misma sensación de "respiración suave" pero
       60% menos repaints por minuto. */
    animation: portraitHaloPulse 12s ease-in-out infinite;
  }}
  @keyframes portraitHaloPulse {{
    0%, 100% {{ opacity: 0.7; }}
    50%      {{ opacity: 1.0; }}
  }}

  /* Toggle pill 2D | 3D — POR DEBAJO del nav, no junto al "Más
     ajustes..." (v0.16.5 fix: estaban demasiado pegados → choque
     visual). Ahora vive ~80px del top, fuera del row del nav. */
  .portrait-view-toggle {{
    position: absolute;
    top: 80px;
    right: 18px;
    z-index: 6;
    display: flex;
    background: rgba(15,6,10,0.85);
    border: 1px solid rgba(212,163,115,0.30);
    border-radius: 99px;
    overflow: hidden;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  }}
  .portrait-view-toggle .seg {{
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #9c8b7e;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.18s ease;
  }}
  .portrait-view-toggle .seg.active {{
    background: {COLOR_PRIMARY};
    color: #1a0a10;
  }}
  .portrait-view-toggle .seg:not(.active):hover {{
    color: {COLOR_PRIMARY};
    background: rgba(212,163,115,0.10);
  }}

  /* ── Panel derecho: chat + input ─────────────────────────────── */
  .ashley-chat-panel {{
    flex: 1;
    display: flex;
    flex-direction: column;
    height: 100vh;
    min-width: 0;
    position: relative;
    overflow: hidden;  /* contiene los .light-rays absolute internos */
    /* v0.16.8 — black con HINT warm en lugar de negro puro. El
       negro absoluto creaba un corte vertical brusco contra el
       portrait wine warm. Ahora gradient muy oscuro pero con
       trazos de wine — apenas perceptible como "color" pero
       suficiente para que el ojo conecte ambos paneles como una
       sola escena, no dos apps pegadas. */
    background: linear-gradient(180deg,
      #0d0610 0%,
      #08040a 50%,
      #050307 100%);
  }}
  /* Contenido del chat panel siempre por encima de los light rays
     y del mood-tint. La regla excluye los layers absolute (rays +
     tint) para que NO les pise su position:absolute → quedan a z=2
     y el contenido scrollable a z=3 encima. */
  .ashley-chat-panel > *:not(.light-rays):not(.ashley-light-rays):not(.chat-mood-tint) {{
    position: relative;
    z-index: 3;
  }}
  /* Mood tint: detrás de los light rays pero encima del bg negro
     del chat panel. Así el orden de "capas" del chat es:
        1. bg negro (panel)
        2. mood-tint (warm/pink/blue según humor — z=1)
        3. light rays (cono dorado — z=2)
        4. content (header, mensajes, input — z=3) */
  .chat-mood-tint {{
    z-index: 1 !important;
  }}

  /* ── Memorias dialog — paleta wine boutique (v0.14.5) ────────
     Antes el dialog mantenía el styling default Radix (texto blanco
     puro, tabs sin hover warm). Ahora todo se alinea con el resto
     de la app: bg wine, texto crema, accent ámbar, tabs con
     active state en ámbar. */
  .ashley-mem-dialog .rt-TabsList,
  .ashley-mem-dialog [role="tablist"] {{
    border-bottom: 1px solid rgba(212,163,115,0.18) !important;
    margin-bottom: 12px !important;
  }}
  .ashley-mem-dialog .rt-TabsTrigger,
  .ashley-mem-dialog [role="tab"] {{
    color: #9c8b7e !important;
    font-weight: 500 !important;
    transition: color 0.2s ease, border-color 0.2s ease !important;
  }}
  .ashley-mem-dialog .rt-TabsTrigger:hover,
  .ashley-mem-dialog [role="tab"]:hover {{
    color: #c4b3a4 !important;
  }}
  .ashley-mem-dialog .rt-TabsTrigger[data-state="active"],
  .ashley-mem-dialog [role="tab"][aria-selected="true"] {{
    color: {COLOR_PRIMARY} !important;
    border-bottom: 2px solid {COLOR_PRIMARY} !important;
  }}
  /* Texto general dentro del dialog → crema warm */
  .ashley-mem-dialog,
  .ashley-mem-dialog p,
  .ashley-mem-dialog span:not([style*="color"]),
  .ashley-mem-dialog div:not([style*="color"]) {{
    color: #c4b3a4;
  }}
  /* Scrollbar de los tabs scrollables → matching tema */
  .ashley-mem-dialog [data-state="active"]::-webkit-scrollbar {{ width: 4px; }}
  .ashley-mem-dialog [data-state="active"]::-webkit-scrollbar-thumb {{
    background: rgba(212,163,115,0.30); border-radius: 4px;
  }}

  .ashley-chat-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 28px 48px 20px;
    gap: 32px;
    border-bottom: 1px solid rgba(212,163,115,0.08);
    flex-shrink: 0;
  }}

  .ashley-chat-scroll {{
    flex: 1;
    overflow-y: auto;
    padding: 24px 36px;
    min-height: 0;
    /* v0.16.14 — sin promoción manual a capa GPU. Los hints de
       composición forzada en este container provocan subpixel jumps
       al scrollear (saltitos visibles). Con el blur quitado de las
       burbujas (fix #1) el scroll va fluido sin necesidad de forzarlo. */
  }}

  .ashley-chat-input-row {{
    padding: 18px 36px 28px;
    flex-shrink: 0;
  }}

  /* Input pill warm con glow ámbar.
     v0.16.8 — añadida idle breath: cuando NO está focuseado, el
     glow ámbar pulsa suave (4s) avisando que es el spot activo
     "esperándote". Al focusear, animación se detiene y se queda
     en el estado focus glow estático más intenso. */
  .ashley-input-pill {{
    background: rgba(31,14,21,0.85) !important;
    border: 1px solid rgba(212,163,115,0.25) !important;
    color: #f5ebd5 !important;
    border-radius: 28px !important;
    padding: 16px 24px !important;
    font-size: 17px !important;
    line-height: 1.5 !important;
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
    transition: border-color 0.25s ease;
    box-shadow:
      0 0 0 1px rgba(212,163,115,0.05),
      0 4px 20px rgba(0,0,0,0.3);
    animation: inputIdleBreath 4.5s ease-in-out infinite;
  }}
  .ashley-input-pill:focus,
  .ashley-input-pill:focus-within {{
    border: 1px solid rgba(212,163,115,0.55) !important;
    box-shadow:
      0 0 0 1px rgba(212,163,115,0.2),
      0 0 30px rgba(212,163,115,0.18),
      0 4px 24px rgba(0,0,0,0.4) !important;
    outline: none !important;
    /* Detenemos el breath al focusear — el focus glow es ya
       prominente, el breath sería ruido visual encima. */
    animation: none !important;
  }}
  @keyframes inputIdleBreath {{
    0%, 100% {{
      box-shadow:
        0 0 0 1px rgba(212,163,115,0.05),
        0 4px 20px rgba(0,0,0,0.3),
        0 0 12px rgba(212,163,115,0.06);
    }}
    50% {{
      box-shadow:
        0 0 0 1px rgba(212,163,115,0.10),
        0 4px 22px rgba(0,0,0,0.3),
        0 0 26px rgba(212,163,115,0.20);
    }}
  }}
  .ashley-input-pill::placeholder {{
    color: #6e5a4a !important;
  }}

  /* Send button — círculo ámbar warm con glow */
  .ashley-send-btn {{
    width: 52px; height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, #d4a373 0%, #b8825a 100%);
    color: #1a0a10;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.25s ease;
    box-shadow:
      0 4px 20px rgba(212,163,115,0.4),
      inset 0 1px 0 rgba(255,255,255,0.25);
    flex-shrink: 0;
  }}
  .ashley-send-btn:hover {{
    background: linear-gradient(135deg, #e6b887 0%, #c89968 100%);
    transform: scale(1.06) translateY(-1px);
    box-shadow:
      0 6px 28px rgba(212,163,115,0.65),
      inset 0 1px 0 rgba(255,255,255,0.3);
  }}
  .ashley-send-btn:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }}
  .ashley-send-btn svg {{
    width: 22px; height: 22px;
    stroke-width: 2;
  }}

  /* v0.16.6 — Header action button (focus toggle + futuros).
     Vive en el chat-header al lado del heart counter. Cuando el
     focus mode está activo lleva clase .active (estilo destacado).
     Mismo patrón visual que .ashley-action-btn pero más pequeño
     (38px vs 42px) para no robarle protagonismo al título Ashley. */
  .ashley-header-action {{
    width: 38px; height: 38px;
    border-radius: 50%;
    background: rgba(35,17,25,0.5);
    border: 1px solid rgba(212,163,115,0.20);
    color: #c4b3a4;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.22s ease;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    user-select: none;
  }}
  .ashley-header-action:hover {{
    background: rgba(212,163,115,0.12);
    border: 1px solid rgba(212,163,115,0.55);
    color: {COLOR_PRIMARY};
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(212,163,115,0.25);
  }}
  .ashley-header-action.active {{
    background: rgba(212,163,115,0.20);
    border: 1px solid rgba(212,163,115,0.70);
    color: {COLOR_PRIMARY};
    box-shadow: 0 0 14px rgba(212,163,115,0.45);
  }}
  .ashley-header-action.active:hover {{
    background: rgba(212,163,115,0.28);
  }}
  .ashley-header-action svg {{
    width: 18px; height: 18px;
    stroke-width: 1.7;
  }}

  /* Heart counter del chat-header — outline elegante con número.
     v0.16.1: número MÁS grande (32px) y más padding/gap, para que
     el "100" se lea sin esforzar la vista. */
  .ashley-affection-counter {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 22px 10px 16px;
    border-radius: 99px;
    background: rgba(35,17,25,0.5);
    border: 1px solid rgba(212,163,115,0.20);
    transition: all 0.3s ease;
  }}
  .ashley-affection-counter:hover {{
    background: rgba(212,163,115,0.12);
    border: 1px solid rgba(212,163,115,0.45);
  }}
  .ashley-affection-number {{
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-weight: 600;
    font-size: 32px;
    color: #e8dcc4;
    letter-spacing: 0.02em;
    line-height: 1;
    text-shadow: 0 1px 8px rgba(212,163,115,0.30);
  }}

  /* ── Affection heart (v0.16) ──────────────────────────────
     Outline elegante (no fill solid), tono ámbar/dorado cálido,
     animación de breath constante (escala sutil + glow pulsante).
     Hover: scale fuerte + glow intenso. Cuando afecto >70:
     animación más rápida + colores más cálidos (rosa-coral). */

  .heart-frame {{
    position: relative;
    width: 38px;
    height: 36px;
    cursor: pointer;
    transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    display: inline-block;
  }}
  .heart-frame:hover {{
    transform: scale(1.20);
  }}

  .ashley-heart-svg {{
    width: 100%;
    height: 100%;
    display: block;
    animation: heartBreathe 3.2s ease-in-out infinite;
  }}
  @keyframes heartBreathe {{
    0%, 100% {{
      transform: scale(1);
      filter: drop-shadow(0 0 4px rgba(212,163,115,0.45))
              drop-shadow(0 0 12px rgba(212,163,115,0.20));
    }}
    50% {{
      transform: scale(1.06);
      filter: drop-shadow(0 0 8px rgba(232,202,158,0.75))
              drop-shadow(0 0 18px rgba(212,163,115,0.40));
    }}
  }}
  .heart-frame:hover .ashley-heart-svg {{
    animation-duration: 1.5s;
    filter: drop-shadow(0 0 12px rgba(255,180,140,0.95))
            drop-shadow(0 0 24px rgba(232,202,158,0.6)) !important;
  }}

  /* Afecto >70 — respiración más viva con tinte coral */
  .heart-glow .ashley-heart-svg {{
    animation: heartBreatheGlow 2.0s ease-in-out infinite;
  }}
  @keyframes heartBreatheGlow {{
    0%, 100% {{
      transform: scale(1.02);
      filter: drop-shadow(0 0 8px rgba(255,140,120,0.65))
              drop-shadow(0 0 16px rgba(212,163,115,0.40));
    }}
    50% {{
      transform: scale(1.10);
      filter: drop-shadow(0 0 16px rgba(255,170,140,1.0))
              drop-shadow(0 0 28px rgba(232,180,150,0.7))
              drop-shadow(0 0 4px rgba(255,255,220,0.5));
    }}
  }}

  /* ── Celebrate animations al subir/bajar afecto (v0.14.5) ──
     Esto es lo que hace que subir afecto se sienta GOOD. El
     heart hace un bump claro (scale 1.5 + flash dorado) cuando
     el delta es positivo. Cuando baja, shrink + desaturación.
     ! para pisar la animación de breathe constante. */
  .heart-frame.celebrate-up .ashley-heart-svg {{
    animation: heartCelebrateUp 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
  }}
  @keyframes heartCelebrateUp {{
    0% {{
      transform: scale(1);
      filter: drop-shadow(0 0 4px rgba(212,163,115,0.45));
    }}
    25% {{
      transform: scale(1.50);
      filter: drop-shadow(0 0 28px rgba(255,200,160,1.0))
              drop-shadow(0 0 14px rgba(255,180,140,0.95))
              brightness(1.35);
    }}
    50% {{
      transform: scale(1.15);
      filter: drop-shadow(0 0 18px rgba(255,180,140,0.85))
              brightness(1.15);
    }}
    100% {{
      transform: scale(1);
      filter: drop-shadow(0 0 4px rgba(212,163,115,0.45));
    }}
  }}
  .heart-frame.celebrate-down .ashley-heart-svg {{
    animation: heartCelebrateDown 0.6s ease-out !important;
  }}
  @keyframes heartCelebrateDown {{
    0% {{
      transform: scale(1);
      filter: drop-shadow(0 0 4px rgba(212,163,115,0.45));
    }}
    40% {{
      transform: scale(0.82);
      filter: brightness(0.55) saturate(0.4);
    }}
    100% {{
      transform: scale(1);
      filter: drop-shadow(0 0 4px rgba(212,163,115,0.45));
    }}
  }}

  /* También animamos el NÚMERO al subir afecto: pulse breve con
     cambio de color (tinte ámbar más vivo brevemente). Indica
     visualmente que algo cambió sin tener que mirar el heart. */
  .heart-frame.celebrate-up + .ashley-affection-number,
  .heart-frame.celebrate-up ~ .ashley-affection-number {{
    animation: numberCelebrate 0.6s ease-out;
  }}
  @keyframes numberCelebrate {{
    0%   {{ transform: scale(1); color: #e8dcc4; }}
    35%  {{ transform: scale(1.25); color: #ffc88a; text-shadow: 0 0 14px rgba(255,200,138,0.8); }}
    100% {{ transform: scale(1); color: #e8dcc4; }}
  }}

  /* ── rx.upload sin dashed border (input redesign v0.15.1) ──
     Por defecto rx.upload pinta un drop zone con borde dashed que
     en nuestro nuevo input pill quedaba como un cuadrado feo
     alrededor del icono 📎. Eliminamos todo ese marco para que
     el botón circular interior sea lo único visible.
     Targeting amplio porque Reflex puede generar varios divs
     anidados — todos transparentes y sin padding/border. */
  .ashley-upload-clean,
  .ashley-upload-clean > div,
  .ashley-upload-clean .rx-Upload {{
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    margin: 0 !important;
    min-width: auto !important;
    width: auto !important;
    min-height: auto !important;
    height: auto !important;
    display: inline-flex !important;
  }}
  /* Ocultar el <input type="file"> nativo que el browser pinta con
     "Ningún archivo seleccionado"/"No file chosen". Lo posicionamos
     fuera de pantalla en lugar de display:none para que siga siendo
     funcional (Reflex programáticamente lo dispara al click del
     paperclip button). */
  .ashley-upload-clean input[type="file"] {{
    position: absolute !important;
    left: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    opacity: 0 !important;
    pointer-events: none !important;
  }}

  /* ── Chat scroll ─────────────────────────────────────── */
  .ashley-chat::-webkit-scrollbar {{ width: 3px; }}
  .ashley-chat::-webkit-scrollbar-track {{ background: transparent; }}
  .ashley-chat::-webkit-scrollbar-thumb {{ background: rgba(255,154,238,0.18); border-radius: 4px; }}
  .ashley-chat {{ scrollbar-width: thin; scrollbar-color: rgba(255,154,238,0.18) transparent; }}

  /* ── Textarea ────────────────────────────────────────── */
  .ashley-textarea {{
    transition: height 0.1s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    scrollbar-width: thin;
    scrollbar-color: #2a2a2a transparent;
  }}
  .ashley-textarea::-webkit-scrollbar {{ width: 4px; }}
  .ashley-textarea::-webkit-scrollbar-track {{ background: transparent; }}
  .ashley-textarea::-webkit-scrollbar-thumb {{ background: #333; border-radius: 4px; }}

  /* ── Panel sticky ────────────────────────────────────── */
  .ashley-panel {{
    position: sticky;
    top: 76px;
    align-self: flex-start;
  }}

  /* ── Floating hearts ───────────────────────────────── */
  @keyframes floatHeartUp {{
    0% {{ opacity: 1; transform: translateY(0) scale(1); }}
    70% {{ opacity: 1; transform: translateY(-60px) scale(1.1); }}
    100% {{ opacity: 0; transform: translateY(-80px) scale(0.8); }}
  }}
  @keyframes floatHeartDown {{
    0% {{ opacity: 1; transform: translateY(0) scale(1); }}
    70% {{ opacity: 0.8; transform: translateY(20px) scale(0.9); }}
    100% {{ opacity: 0; transform: translateY(30px) scale(0.7); }}
  }}
  .affection-heart-float {{
    position: absolute;
    font-size: 18px;
    pointer-events: none;
    z-index: 9999;
    text-align: center;
    line-height: 1;
  }}
  .affection-heart-float.positive {{
    animation: floatHeartUp 2s ease-out forwards;
    color: #e6b887;  /* v0.16 ámbar warm */
    text-shadow: 0 0 10px rgba(212,163,115,0.7);
  }}
  .affection-heart-float.negative {{
    animation: floatHeartDown 1.5s ease-in forwards;
    color: #8b6e5c;  /* v0.16 marrón muted */
    text-shadow: 0 0 6px rgba(139,110,92,0.5);
  }}
  .affection-heart-float .delta {{
    font-size: 11px;
    font-weight: 700;
    display: block;
  }}

  /* ── Tier change overlay ───────────────────────────── */
  @keyframes tierUpPulse {{
    0% {{ background: rgba(255,80,120,0); }}
    15% {{ background: rgba(255,80,120,0.08); }}
    30% {{ background: rgba(255,80,120,0.03); }}
    45% {{ background: rgba(255,80,120,0.08); }}
    60% {{ background: rgba(255,80,120,0.03); }}
    75% {{ background: rgba(255,80,120,0.06); }}
    100% {{ background: rgba(255,80,120,0); }}
  }}
  @keyframes tierDownFlash {{
    0% {{ background: rgba(100,120,200,0); }}
    20% {{ background: rgba(100,120,200,0.06); }}
    100% {{ background: rgba(100,120,200,0); }}
  }}
  .tier-change-overlay {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 9990;
  }}
  .tier-change-overlay.up {{
    animation: tierUpPulse 4s ease-out forwards;
  }}
  .tier-change-overlay.down {{
    animation: tierDownFlash 2s ease-out forwards;
  }}

  /* ── Tier change banner ────────────────────────────── */
  @keyframes bannerSlideIn {{
    0% {{ opacity: 0; transform: translateY(20px); }}
    15% {{ opacity: 1; transform: translateY(0); }}
    85% {{ opacity: 1; transform: translateY(0); }}
    100% {{ opacity: 0; transform: translateY(-10px); }}
  }}
  .tier-banner {{
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    padding: 12px 28px;
    border-radius: 14px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
    font-weight: 500;
    pointer-events: none;
    z-index: 9995;
    animation: bannerSlideIn 4.5s ease-out forwards;
    white-space: nowrap;
  }}
  .tier-banner.up {{
    background: rgba(255,80,120,0.15);
    color: #ff88aa;
    border: 1px solid rgba(255,80,120,0.4);
    text-shadow: 0 0 10px rgba(255,80,120,0.3);
  }}
  .tier-banner.down {{
    background: rgba(100,120,200,0.12);
    color: #8899cc;
    border: 1px solid rgba(100,120,200,0.3);
  }}

  /* ── Achievement unlock notification ───────────────── */
  @keyframes achievementSlideIn {{
    0% {{ opacity: 0; transform: translateY(30px) scale(0.9); }}
    15% {{ opacity: 1; transform: translateY(0) scale(1.05); }}
    25% {{ transform: scale(1); }}
    85% {{ opacity: 1; transform: translateY(0); }}
    100% {{ opacity: 0; transform: translateY(-15px); }}
  }}
  .achievement-toast {{
    position: fixed;
    top: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, rgba(30,20,40,0.95), rgba(50,30,60,0.95));
    border: 1px solid rgba(255,154,238,0.5);
    border-radius: 16px;
    padding: 16px 28px;
    z-index: 9997;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 8px 32px rgba(255,154,238,0.3), 0 0 60px rgba(255,154,238,0.15);
    animation: achievementSlideIn 5s ease-out forwards;
    pointer-events: none;
    min-width: 280px;
  }}
  .achievement-toast .ach-icon {{
    font-size: 32px;
    filter: drop-shadow(0 0 8px rgba(255,154,238,0.6));
  }}
  .achievement-toast .ach-text {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .achievement-toast .ach-title {{
    color: #ff9aee;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-shadow: 0 0 10px rgba(255,154,238,0.4);
  }}
  .achievement-toast .ach-subtitle {{
    font-size: 12px;
    font-weight: 600;
    color: #ffd700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }}
  .achievement-toast .ach-desc {{
    color: #ccbbdd;
    font-size: 12px;
    font-style: italic;
  }}

  /* ── Radix popups (Select / DropdownMenu / Popover) ──────
     Todo lo que se abre vía Radix Portal hereda este z-index alto y
     un fondo sólido. Esto cubre:
       • rx.select (Select.Content)
       • rx.menu  (DropdownMenu.Content) — el ⚙ del header
       • rx.popover (Popover.Content)
     Sin estas reglas, los popups se ven transparentes encima del
     avatar/chat, ilegibles.

     Pulido v0.13.4: padding más generoso, animación de entrada
     suave, hover con transición, bordes más definidos. */
  [data-radix-popper-content-wrapper] {{
    z-index: 10050 !important;
  }}
  [data-radix-select-content],
  [data-radix-menu-content],
  [data-radix-dropdown-menu-content],
  [data-radix-popover-content] {{
    background: linear-gradient(180deg, #1a1525 0%, #14101e 100%) !important;
    border: 1px solid rgba(255,154,238,0.28) !important;
    box-shadow:
      0 12px 48px rgba(0,0,0,0.85),
      0 0 0 1px rgba(255,154,238,0.06),
      inset 0 1px 0 rgba(255,255,255,0.04) !important;
    backdrop-filter: blur(16px) saturate(150%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(150%) !important;
    padding: 6px !important;
    border-radius: 12px !important;
    animation: dropdownEnter 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
  }}
  @keyframes dropdownEnter {{
    from {{ opacity: 0; transform: translateY(-4px) scale(0.98); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}
  [data-radix-select-item],
  [data-radix-select-item][data-state="checked"],
  [data-radix-menu-item],
  [data-radix-dropdown-menu-item] {{
    color: #e5e0f0 !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease !important;
  }}
  [data-radix-select-item][data-highlighted],
  [data-radix-menu-item][data-highlighted],
  [data-radix-dropdown-menu-item][data-highlighted] {{
    background: linear-gradient(90deg,
      rgba(255,154,238,0.15) 0%,
      rgba(255,154,238,0.08) 100%) !important;
    color: #ff9aee !important;
    outline: none !important;
    transform: translateX(2px) !important;
  }}
  [data-radix-menu-separator],
  [data-radix-dropdown-menu-separator] {{
    height: 1px !important;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(255,154,238,0.25) 50%,
      transparent 100%) !important;
    margin: 6px 8px !important;
  }}
  /* Items custom (rx.box que usamos en el dropdown ⚙) */
  .ashley-menu-toggle-item {{
    transition: background 0.15s ease, color 0.15s ease, transform 0.1s ease !important;
  }}
  .ashley-menu-toggle-item:hover {{
    transform: translateX(2px) !important;
  }}

  /* ── Tooltips (Radix Themes 3) — texto blanco sobre fondo oscuro ──
     v0.15.4: el override anterior solo cubría 2 selectores y muchos
     tooltips seguían viéndose con texto negro. Ampliamos a TODOS los
     posibles selectores de Radix Themes (BaseTooltipContent es el
     interno; rt-TooltipContent el del themes; data-radix-* el de la
     primitive base). Plus: forzar color en TODOS los descendientes
     porque a veces el hijo lleva una clase que pinta de negro. */
  [data-radix-tooltip-content],
  .rt-TooltipContent,
  .rt-BaseTooltipContent,
  .rt-r-tooltip,
  [role="tooltip"],
  [class*="TooltipContent"],
  [class*="BaseTooltipContent"] {{
    background: rgba(20, 10, 30, 0.96) !important;
    color: #f0e8f5 !important;
    border: 1px solid rgba(255,154,238,0.30) !important;
    box-shadow:
      0 8px 24px rgba(0,0,0,0.6),
      0 0 0 1px rgba(255,154,238,0.05) !important;
    backdrop-filter: blur(14px) !important;
    -webkit-backdrop-filter: blur(14px) !important;
    border-radius: 8px !important;
    padding: 7px 12px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
    letter-spacing: 0.01em !important;
    max-width: 280px !important;
  }}
  /* Forzar color claro en TODOS los descendientes — algunos tooltips
     envuelven el texto en un span con clase propia que pinta negro. */
  [data-radix-tooltip-content] *,
  .rt-TooltipContent *,
  .rt-BaseTooltipContent *,
  [role="tooltip"] *,
  [class*="TooltipContent"] *,
  [class*="BaseTooltipContent"] * {{
    color: #f0e8f5 !important;
  }}
  /* La flechita — fill matching del bg oscuro. Excepción al `*` de
     arriba: aquí queremos `fill`, no `color`. */
  [data-radix-tooltip-content] svg,
  .rt-TooltipContent svg,
  .rt-BaseTooltipContent svg,
  [role="tooltip"] svg,
  [class*="TooltipContent"] svg {{
    fill: rgba(20, 10, 30, 0.96) !important;
    color: rgba(20, 10, 30, 0.96) !important;
  }}

  /* ── Achievement gallery ──────────────────────────── */
  .achievement-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    padding: 8px 0;
  }}
  .achievement-card {{
    background: rgba(255,154,238,0.06);
    border: 1px solid rgba(255,154,238,0.2);
    border-radius: 14px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    text-align: center;
    transition: all 0.3s ease;
  }}
  .achievement-card.unlocked {{
    border-color: rgba(255,154,238,0.5);
    box-shadow: 0 0 20px rgba(255,154,238,0.12);
  }}
  .achievement-card.unlocked:hover {{
    transform: scale(1.03);
    box-shadow: 0 0 30px rgba(255,154,238,0.25);
  }}
  .achievement-card.locked {{
    opacity: 0.45;
    filter: grayscale(0.6);
  }}
  .achievement-card .card-icon {{
    font-size: 32px;
  }}
  .achievement-card .card-name {{
    color: #ff9aee;
    font-size: 13px;
    font-weight: 700;
  }}
  .achievement-card .card-desc {{
    color: #bbaacc;
    font-size: 11px;
    font-style: italic;
    line-height: 1.4;
  }}
  .achievement-card .card-date {{
    color: #888;
    font-size: 10px;
    margin-top: 4px;
  }}
</style>
""")
