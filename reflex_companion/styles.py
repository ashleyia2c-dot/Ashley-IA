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
<style>
  html, body {{
    background: #080810 !important;
    margin: 0; padding: 0;
  }}
  .radix-themes,
  [data-is-root-theme],
  [data-radix-root] {{
    background: transparent !important;
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
  @keyframes pillPulse {{
    0%, 100% {{ box-shadow: 0 0 6px rgba(255,154,238,0.25); }}
    50%       {{ box-shadow: 0 0 14px rgba(255,154,238,0.6); }}
  }}
  @keyframes pillPulseOrange {{
    0%, 100% {{ box-shadow: 0 0 6px rgba(255,107,53,0.25); }}
    50%       {{ box-shadow: 0 0 14px rgba(255,107,53,0.6); }}
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
  /* Scroll invisible para los pills del header */
  .pills-row::-webkit-scrollbar {{ display: none; }}
  .pills-row {{ -ms-overflow-style: none; scrollbar-width: none; }}

  .msg-enter         {{ animation: fadeSlideIn 0.25s ease-out both; }}
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
  .pill-on-pink   {{ animation: pillPulse 2.2s ease-in-out infinite; }}
  .pill-on-orange {{ animation: pillPulseOrange 2.2s ease-in-out infinite; }}

  @keyframes visionPulse {{
    0%, 100% {{ text-shadow: 0 0 4px rgba(255,154,238,0.3); }}
    50%       {{ text-shadow: 0 0 12px rgba(255,154,238,0.8); }}
  }}
  .pill-on-vision {{
    animation: pillPulse 2.2s ease-in-out infinite, visionPulse 3s ease-in-out infinite;
  }}

  /* ── Glassmorphism — burbujas ────────────────────────── */
  .bubble-ashley {{
    background: rgba(110, 40, 155, 0.28) !important;
    backdrop-filter: blur(16px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(160%) !important;
    border: 1px solid rgba(255, 154, 238, 0.32) !important;
    box-shadow: 0 4px 22px rgba(255,154,238,0.16),
                inset 0 1px 0 rgba(255,255,255,0.07) !important;
  }}
  .bubble-user {{
    background: rgba(25, 55, 120, 0.28) !important;
    backdrop-filter: blur(16px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(16px) saturate(160%) !important;
    border: 1px solid rgba(100, 150, 255, 0.28) !important;
    box-shadow: 0 4px 22px rgba(100,150,255,0.12),
                inset 0 1px 0 rgba(255,255,255,0.05) !important;
  }}

  /* ── Glassmorphism — panels ──────────────────────────── */
  .glass-chat {{
    background: rgba(8, 5, 18, 0.55) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,154,238,0.08) !important;
  }}
  .glass-portrait {{
    background: rgba(12, 7, 22, 0.28) !important;
    backdrop-filter: blur(14px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(14px) saturate(140%) !important;
    border: 1px solid rgba(255,154,238,0.14) !important;
  }}
  .glass-header {{
    background: rgba(5, 3, 12, 0.78) !important;
    backdrop-filter: blur(28px) !important;
    -webkit-backdrop-filter: blur(28px) !important;
    border-bottom: 1px solid rgba(255,154,238,0.07) !important;
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

  /* ── Affection water bar ───────────────────────────── */
  .affection-bar {{
    width: 36px;
    height: 100px;
    border-radius: 18px;
    border: 2px solid rgba(255,154,238,0.25);
    background: rgba(0,0,0,0.35);
    overflow: hidden;
    position: relative;
    margin: 0 auto;
    cursor: pointer;
  }}
  .affection-water {{
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    border-radius: 0 0 16px 16px;
    transition: height 1.8s cubic-bezier(0.4, 0, 0.2, 1),
                background 2s ease;
  }}
  /* Wave effect — constant movement, never stops */
  .affection-water::before {{
    content: '';
    position: absolute;
    top: -5px;
    left: -20%;
    width: 140%;
    height: 10px;
    background: inherit;
    opacity: 0.6;
    border-radius: 50%;
    animation: affectionWave1 2.5s ease-in-out infinite;
  }}
  .affection-water::after {{
    content: '';
    position: absolute;
    top: -3px;
    left: -10%;
    width: 120%;
    height: 7px;
    background: inherit;
    opacity: 0.35;
    border-radius: 50%;
    animation: affectionWave2 3.2s ease-in-out infinite;
  }}
  @keyframes affectionWave1 {{
    0%, 100% {{ transform: translateX(-5%) scaleY(1); }}
    25% {{ transform: translateX(3%) scaleY(1.8); }}
    50% {{ transform: translateX(5%) scaleY(1); }}
    75% {{ transform: translateX(-3%) scaleY(1.4); }}
  }}
  @keyframes affectionWave2 {{
    0%, 100% {{ transform: translateX(4%) scaleY(1.2); }}
    50% {{ transform: translateX(-4%) scaleY(0.8); }}
  }}
  /* Hover — water gets agitated like you touched it */
  .affection-bar:hover .affection-water::before {{
    animation: affectionWaveHover1 0.8s ease-in-out infinite !important;
  }}
  .affection-bar:hover .affection-water::after {{
    animation: affectionWaveHover2 0.6s ease-in-out infinite !important;
  }}
  @keyframes affectionWaveHover1 {{
    0%, 100% {{ transform: translateX(-8%) scaleY(2.2); }}
    50% {{ transform: translateX(8%) scaleY(1); }}
  }}
  @keyframes affectionWaveHover2 {{
    0%, 100% {{ transform: translateX(6%) scaleY(1.8); }}
    50% {{ transform: translateX(-6%) scaleY(0.6); }}
  }}
  /* Glow when affection is high (>70) */
  .affection-glow {{
    box-shadow: 0 0 14px rgba(255,102,170,0.5),
                inset 0 0 8px rgba(255,102,170,0.2);
    animation: affectionGlowPulse 2s ease-in-out infinite;
  }}
  @keyframes affectionGlowPulse {{
    0%, 100% {{ box-shadow: 0 0 10px rgba(255,102,170,0.3), inset 0 0 6px rgba(255,102,170,0.1); }}
    50% {{ box-shadow: 0 0 20px rgba(255,102,170,0.6), inset 0 0 10px rgba(255,102,170,0.3); }}
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
    color: #ff66aa;
    text-shadow: 0 0 8px rgba(255,102,170,0.6);
  }}
  .affection-heart-float.negative {{
    animation: floatHeartDown 1.5s ease-in forwards;
    color: #6688cc;
    text-shadow: 0 0 6px rgba(100,136,204,0.4);
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
