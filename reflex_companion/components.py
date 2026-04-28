"""
components.py — Reusable UI component functions for the Ashley companion app.

Extracted from reflex_companion.py.  Contains message bubbles, avatar,
streaming indicator, thinking dots, memory/diary/fact/taste items,
pill toggle buttons, and the portrait panel.
"""

import reflex as rx

from .config import (
    COLOR_PRIMARY,
    COLOR_BG_FACT_BADGE, COLOR_BG_INPUT,
    COLOR_TEXT_MUTED, COLOR_TEXT_DIM, COLOR_TEXT_FACT,
    COLOR_STATUS_ONLINE, COLOR_STATUS_WRITING,
    SHADOW_BUTTON,
)


def _get_state():
    """Lazy import to avoid circular dependency with reflex_companion.py."""
    from .reflex_companion import State
    return State


# ─────────────────────────────────────────────
#  Low-level helpers
# ─────────────────────────────────────────────

def _msg_bubble(m: dict[str, str], is_ashley) -> rx.Component:
    return rx.box(
        rx.cond(
            m["image"] != "",
            rx.image(
                src=m["image"],
                max_width="220px",
                border_radius="10px",
                margin_bottom="8px",
                display="block",
            ),
            rx.box(),
        ),
        rx.cond(
            m["content"] != "",
            rx.markdown(m["content"], color="white"),
            rx.box(),
        ),
        padding="12px 18px",
        border_radius=rx.cond(
            is_ashley,
            "4px 22px 22px 22px",
            "22px 4px 22px 22px",
        ),
        max_width="78%",
        class_name=rx.cond(is_ashley, "bubble-ashley", "bubble-user"),
    )


def _ashley_avatar(size: str = "46px", src: str = "/ashley_pfp.jpg") -> rx.Component:
    return rx.box(
        rx.image(src=src, width="100%", height="100%", object_fit="cover"),
        width=size, height=size,
        border_radius="50%",
        overflow="hidden",
        border=f"2px solid {COLOR_PRIMARY}",
        flex_shrink="0",
        box_shadow="0 0 8px rgba(255,154,238,0.4)",
        # Fallback: shows while the mood image is loading so it never goes black
        background_image="url('/ashley_pfp.jpg')",
        background_size="cover",
        background_position="center",
    )


# ─────────────────────────────────────────────
#  Message components
# ─────────────────────────────────────────────

def message_item(m: dict[str, str]):
    State = _get_state()
    is_ashley = m["role"] == "assistant"
    is_system = m["role"] == "system_result"
    return rx.box(
        rx.cond(
            is_system,
            # Notificación de sistema: centrada y discreta
            rx.center(
                rx.hstack(
                    rx.text("⚙️", font_size="11px"),
                    rx.text(m["content"], font_size="12px", color="#777777"),
                    spacing="1", align="center",
                ),
                bg="#0d0d0d",
                border_radius="20px",
                padding="3px 14px",
                border="1px solid #2a2a2a",
                width="fit-content",
                margin_x="auto",
            ),
            rx.cond(
                is_ashley,
                # Ashley: [avatar] [burbuja] [🗑️]
                rx.hstack(
                    _ashley_avatar(),
                    _msg_bubble(m, is_ashley),
                    rx.button(
                        "🗑️",
                        on_click=State.delete_message(m["id"]),
                        size="1", bg="transparent", color="#555555",
                        _hover={"color": "#ff6b6b", "bg": "transparent"},
                        cursor="pointer",
                    ),
                    spacing="2", align="start", width="100%",
                ),
                # Usuario: [spacer] [🗑️] [burbuja]
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "🗑️",
                        on_click=State.delete_message(m["id"]),
                        size="1", bg="transparent", color="#555555",
                        _hover={"color": "#ff6b6b", "bg": "transparent"},
                        cursor="pointer",
                    ),
                    _msg_bubble(m, is_ashley),
                    spacing="2", align="center", width="100%",
                ),
            ),
        ),
        width="100%",
        padding_y="4px",
        class_name=rx.cond(
            is_system, "msg-enter",
            rx.cond(is_ashley, "msg-enter ashley-msg", "msg-enter user-msg"),
        ),
    )


def streaming_bubble():
    State = _get_state()
    return rx.cond(
        State.current_response != "",
        rx.box(
            rx.hstack(
                _ashley_avatar(src=State.current_image),
                rx.box(
                    rx.markdown(State.current_response, color="white"),
                    padding="12px 18px",
                    border_radius="4px 22px 22px 22px",
                    max_width="78%",
                    class_name="bubble-ashley cursor-blink",
                ),
                spacing="2", align="start",
            ),
            width="100%",
            padding_y="4px",
        ),
        rx.box(),
    )


def thinking_indicator():
    State = _get_state()
    return rx.cond(
        State.is_thinking,
        rx.box(
            rx.hstack(
                _ashley_avatar(src=State.current_image),
                rx.box(
                    rx.html(f"""
                    <div style="display:flex;align-items:center;gap:6px;padding:12px 18px;">
                        <span style="font-size:12px;color:{COLOR_PRIMARY};margin-right:4px;font-style:italic;opacity:0.85;">pensando</span>
                        <span style="width:8px;height:8px;border-radius:50%;background:{COLOR_PRIMARY};display:inline-block;animation:bounce 1.2s infinite ease-in-out;animation-delay:0s"></span>
                        <span style="width:8px;height:8px;border-radius:50%;background:{COLOR_PRIMARY};display:inline-block;animation:bounce 1.2s infinite ease-in-out;animation-delay:0.2s"></span>
                        <span style="width:8px;height:8px;border-radius:50%;background:{COLOR_PRIMARY};display:inline-block;animation:bounce 1.2s infinite ease-in-out;animation-delay:0.4s"></span>
                        <style>@keyframes bounce{{0%,60%,100%{{transform:translateY(0);opacity:.4}}30%{{transform:translateY(-8px);opacity:1}}}}</style>
                    </div>
                    """),
                    class_name="bubble-ashley",
                    border_radius="4px 22px 22px 22px",
                    display="inline-block",
                ),
                spacing="2", align="start",
            ),
            width="100%",
            padding_y="4px",
        ),
        rx.box(),
    )


# ─────────────────────────────────────────────
#  Memory / diary / taste items
# ─────────────────────────────────────────────

def fact_item(f: dict[str, str]):
    return rx.hstack(
        rx.box(
            rx.text(f["categoria"], font_size="10px", font_weight="bold", color=COLOR_PRIMARY),
            bg=COLOR_BG_FACT_BADGE, padding="2px 8px", border_radius="99px",
        ),
        rx.text(f["hecho"], flex="1", color=COLOR_TEXT_FACT, font_size="13px"),
        rx.hstack(
            rx.box(
                rx.text(f["relevancia"], font_size="10px", color="#888888"),
                bg=COLOR_BG_INPUT, padding="2px 8px", border_radius="99px",
            ),
            rx.box(
                rx.text("★" + f["importancia"], font_size="10px", color=COLOR_STATUS_WRITING),
                bg=COLOR_BG_INPUT, padding="2px 8px", border_radius="99px",
            ),
            spacing="1",
        ),
        spacing="3",
        align="center",
        padding_y="6px",
        border_bottom="1px solid #1f1f1f",
    )


def diary_item(e: dict[str, str]):
    return rx.box(
        rx.text(e["fecha"], color=COLOR_PRIMARY, font_weight="bold", font_size="12px", margin_bottom="4px"),
        rx.text(e["resumen"], color=COLOR_TEXT_DIM, font_size="13px"),
        bg=COLOR_BG_INPUT,
        padding="12px 16px",
        border_radius="10px",
        margin_bottom="8px",
    )


def taste_item(t: dict[str, str]):
    State = _get_state()
    return rx.hstack(
        rx.box(
            rx.text(t["categoria"], font_size="10px", font_weight="bold", color="#ff9aee"),
            bg="#2a0f3d", padding="2px 8px", border_radius="99px",
        ),
        rx.text(t["valor"], flex="1", color="#dddddd", font_size="13px"),
        rx.button(
            "×",
            on_click=State.delete_taste(t["id"]),
            size="1", variant="ghost", color="#ff6666",
            cursor="pointer",
            _hover={"color": "#ff3333"},
        ),
        spacing="3", align="center",
        padding_y="6px",
        border_bottom="1px solid #1f1f1f",
    )


def memory_item(m: dict[str, str]):
    return rx.hstack(
        rx.text(m["role"].upper() + ": ", color=COLOR_PRIMARY, font_weight="bold", width="80px"),
        rx.text(m["content"], flex="1"),
        spacing="4",
        align="start",
    )


def achievement_card(a: dict[str, str]):
    """Renders a single achievement card (unlocked or locked)."""
    return rx.box(
        rx.text(a["icon"], class_name="card-icon"),
        rx.text(a["name"], class_name="card-name"),
        rx.cond(
            a["unlocked"] == "true",
            rx.fragment(
                rx.text(a["desc"], class_name="card-desc"),
                rx.text(a["date"], class_name="card-date"),
            ),
            rx.text("???", class_name="card-desc", color="#666"),
        ),
        class_name=rx.cond(
            a["unlocked"] == "true",
            "achievement-card unlocked",
            "achievement-card locked",
        ),
    )


# ─────────────────────────────────────────────
#  Affection bar
# ─────────────────────────────────────────────

def _affection_bar() -> rx.Component:
    """Barra de agua visual del nivel de afecto."""
    State = _get_state()
    return rx.vstack(
        rx.box(
            # The water
            rx.box(
                height=State.affection_pct,
                bg=State.affection_color,
                class_name="affection-water",
            ),
            class_name=rx.cond(
                State.affection > 70,
                "affection-bar affection-glow",
                "affection-bar",
            ),
        ),
        rx.text(
            State.affection,
            font_size="10px",
            color=State.affection_color,
            font_weight="600",
        ),
        spacing="1",
        align="center",
    )


# ─────────────────────────────────────────────
#  Portrait panel + pill buttons
# ─────────────────────────────────────────────

def _ashley_portrait_panel() -> rx.Component:
    """Panel derecho con el retrato grande de Ashley (sticky)."""
    State = _get_state()
    return rx.box(
        rx.vstack(
            # ── Imagen grande ──────────────────────────
            rx.box(
                rx.image(
                    src=State.current_image,
                    width="100%", height="100%",
                    object_fit="cover",
                ),
                width="260px", height="260px",
                border_radius="22px",
                overflow="hidden",
                background_image="url('/ashley_pfp.jpg')",
                background_size="cover",
                background_position="center",
                class_name=rx.cond(
                    State.is_thinking | (State.current_response != ""),
                    "portrait-thinking",
                    "portrait-idle",
                ),
            ),

            # ── Nombre ───────────────────────────────
            rx.text(
                "Ashley",
                font_size="22px", font_weight="800",
                color=COLOR_PRIMARY, text_align="center",
                letter_spacing="0.04em",
                style={"textShadow": f"0 0 18px rgba(255,154,238,0.4)"},
            ),
            rx.text(
                State.t["brand_subtitle"],
                color=COLOR_TEXT_MUTED, font_size="11px", text_align="center",
                letter_spacing="0.06em",
            ),

            # ── Estado ───────────────────────────────
            rx.cond(
                State.is_thinking,
                rx.hstack(
                    rx.box(
                        width="8px", height="8px", border_radius="50%", bg=COLOR_PRIMARY,
                        style={"animation": "avatarPulse 1.2s ease-in-out infinite"},
                    ),
                    rx.text(State.t["status_thinking"], color=COLOR_PRIMARY,
                            font_size="12px", font_style="italic"),
                    spacing="2", align="center",
                ),
                rx.cond(
                    State.current_response != "",
                    rx.hstack(
                        rx.box(
                            width="8px", height="8px", border_radius="50%", bg=COLOR_STATUS_WRITING,
                            style={"animation": "avatarPulse 1.2s ease-in-out infinite"},
                        ),
                        rx.text(State.t["status_speaking"], color=COLOR_STATUS_WRITING,
                                font_size="12px", font_style="italic"),
                        spacing="2", align="center",
                    ),
                    rx.hstack(
                        rx.box(width="8px", height="8px", border_radius="50%",
                               bg=COLOR_STATUS_ONLINE),
                        rx.text(State.t["status_online"], color=COLOR_STATUS_ONLINE, font_size="12px"),
                        spacing="2", align="center",
                    ),
                ),
            ),

            # ── Affection meter ─────────────────────
            _affection_bar(),

            spacing="3", align="center",
        ),
        padding="26px 20px",
        border_radius="26px",
        width="310px",
        flex_shrink="0",
        class_name="ashley-panel glass-portrait",
    )


def _pill_btn(
    icon: str,
    label: str,
    on_click,
    active,
    disabled=False,
) -> rx.Component:
    """Botón pill toggle para el header — variante rosa (defecto)."""
    return rx.button(
        rx.hstack(
            rx.text(icon, font_size="12px"),
            rx.text(label, font_size="11px", font_weight="600"),
            spacing="1", align="center",
        ),
        on_click=on_click,
        bg=rx.cond(active, "rgba(255,154,238,0.18)", "rgba(255,255,255,0.04)"),
        color=rx.cond(active, COLOR_PRIMARY, "#6a6a7a"),
        border=rx.cond(
            active,
            "1px solid rgba(255,154,238,0.5)",
            "1px solid rgba(255,255,255,0.07)",
        ),
        box_shadow=rx.cond(active, SHADOW_BUTTON, "none"),
        border_radius="99px",
        padding="0 10px",
        height="28px",
        flex_shrink="0",
        transition="all 0.2s ease",
        _hover={
            "bg": "rgba(255,154,238,0.12)",
            "color": COLOR_PRIMARY,
            "border": "1px solid rgba(255,154,238,0.35)",
            "transform": "scale(1.04)",
        },
        cursor="pointer",
        disabled=disabled,
        class_name=rx.cond(active, "pill-on-pink", ""),
    )


def _pill_btn_orange(
    icon: str,
    label: str,
    on_click,
    active,
) -> rx.Component:
    """Botón pill toggle — variante naranja (acciones)."""
    return rx.button(
        rx.hstack(
            rx.text(icon, font_size="12px"),
            rx.text(label, font_size="11px", font_weight="600"),
            spacing="1", align="center",
        ),
        on_click=on_click,
        bg=rx.cond(active, "rgba(255,107,53,0.2)", "rgba(255,255,255,0.04)"),
        color=rx.cond(active, "#ff7b45", "#6a6a7a"),
        border=rx.cond(
            active,
            "1px solid rgba(255,107,53,0.5)",
            "1px solid rgba(255,255,255,0.07)",
        ),
        box_shadow=rx.cond(active, "0 4px 15px rgba(255,107,53,0.4)", "none"),
        border_radius="99px",
        padding="0 10px",
        height="28px",
        flex_shrink="0",
        transition="all 0.2s ease",
        _hover={
            "bg": "rgba(255,107,53,0.12)",
            "color": "#ff7b45",
            "border": "1px solid rgba(255,107,53,0.35)",
            "transform": "scale(1.04)",
        },
        cursor="pointer",
        class_name=rx.cond(active, "pill-on-orange", ""),
    )


# ─────────────────────────────────────────────
#  Header quick menu (consolida toggles secundarios en un dropdown)
# ─────────────────────────────────────────────
#
# Antes del v0.13 el header tenía 9-10 botones tirados en una sola fila —
# visualmente ruidoso. Ahora solo quedan VISIBLES:
#   🧠 Memorias          (acción frecuente, abre dialog)
#   ⚡ Actions           (toggle maestro crítico, afecta comportamiento)
#   ⚙ Menu desplegable  (TODO lo demás vive aquí)
#
# Dentro del dropdown (orden = frecuencia de uso esperada):
#   ✨ Iniciativa       (acción de Ashley)
#   🔊/🔈 TTS           (toggle altavoz)
#   🗣 Modo natural     (toggle voz sin gestos)
#   ⛶  Focus mode      (toggle oculta panel derecho)
#   📌 Pin on top       (toggle ventana encima)
#   🔔 Notificaciones   (toggle Windows)
#   🌐 Idioma           (cicla EN → ES → FR)
#   ───────────
#   ⚙ Ajustes completos (abre modal con providers, TTS, etc.)


def _quick_menu_toggle_item(
    icon_on: str,
    icon_off: str,
    label: str,
    active,
    on_click,
) -> rx.Component:
    """Item del quick menu que actúa como toggle.

    IMPORTANTE: NO usamos rx.menu.item porque Radix cierra el menú al
    hacer click en un Item. Para que el user pueda cambiar varios
    toggles sin re-abrir el menú, usamos un rx.box custom con
    on_click. Radix no reconoce el box como Item → no cierra el menú.
    Imitamos el look de menu.item con class y estilos inline.
    """
    return rx.box(
        rx.hstack(
            rx.text(rx.cond(active, icon_on, icon_off),
                    font_size="14px", width="20px", text_align="center"),
            rx.text(label, font_size="12px"),
            rx.spacer(),
            rx.cond(
                active,
                rx.text("✓", color=COLOR_PRIMARY, font_size="12px", font_weight="700"),
                rx.text("", width="10px"),
            ),
            width="100%", align="center", spacing="2",
        ),
        on_click=on_click,
        cursor="pointer",
        padding="6px 10px",
        border_radius="6px",
        color="#eee",
        transition="background 0.15s ease, color 0.15s ease",
        _hover={
            "background": "rgba(255,154,238,0.12)",
            "color": "#ff9aee",
        },
        class_name="ashley-menu-toggle-item",
    )


def _quick_menu_action_item(
    icon: str,
    label: str,
    on_click,
    disabled=False,
    right_slot=None,
) -> rx.Component:
    """Item del menu para acciones (initiative / language).
    También usa rx.box custom para NO cerrar el menú al hacer click."""
    row = [
        rx.text(icon, font_size="14px", width="20px", text_align="center"),
        rx.text(label, font_size="12px"),
    ]
    if right_slot is not None:
        row.extend([rx.spacer(), right_slot])
    return rx.box(
        rx.hstack(*row, width="100%", align="center", spacing="2"),
        on_click=on_click,
        cursor=rx.cond(disabled, "not-allowed", "pointer"),
        opacity=rx.cond(disabled, "0.5", "1"),
        padding="6px 10px",
        border_radius="6px",
        color="#eee",
        transition="background 0.15s ease, color 0.15s ease",
        _hover={
            "background": "rgba(255,154,238,0.12)",
            "color": "#ff9aee",
        },
        class_name="ashley-menu-toggle-item",
    )


def _header_quick_menu() -> rx.Component:
    """Dropdown menu ⚙ que consolida todos los toggles secundarios +
    la acción de iniciativa + idioma + acceso a settings completos."""
    State = _get_state()
    return rx.menu.root(
        rx.menu.trigger(
            rx.button(
                "⚙",
                bg="rgba(255,255,255,0.04)",
                color="#888",
                border="1px solid rgba(255,255,255,0.08)",
                border_radius="99px",
                padding="0 10px",
                height="28px",
                font_size="13px",
                flex_shrink="0",
                cursor="pointer",
                transition="all 0.2s ease",
                _hover={
                    "bg": "rgba(255,154,238,0.12)",
                    "color": COLOR_PRIMARY,
                    "border": "1px solid rgba(255,154,238,0.4)",
                    "transform": "rotate(45deg)",
                },
                title=State.t["settings_tooltip"],
            ),
        ),
        rx.menu.content(
            # Ningún item usa rx.menu.item — todos son rx.box custom vía
            # _quick_menu_*_item, que NO disparan el cierre del menú. Así
            # el user puede tocar varios toggles de una sentada. El menú
            # sólo se cierra haciendo click FUERA o en la rueda ⚙.
            # NOTA (v0.13.7): "Iniciativa de Ashley" se sacó de este
            # dropdown y se movió al lado del input — es una acción del
            # flujo del chat, no de configuración.

            # ── Toggles ──────────────────────────────
            _quick_menu_toggle_item(
                "🔊", "🔈",
                State.t["menu_tts"],
                State.tts_enabled,
                State.toggle_tts,
            ),
            _quick_menu_toggle_item(
                "🗣", "🗣",
                State.t["pill_natural"],
                State.voice_mode,
                State.toggle_voice_mode,
            ),
            _quick_menu_toggle_item(
                "⛶", "⛶",
                State.t["pill_focus"],
                State.focus_mode,
                State.toggle_focus_mode,
            ),
            _quick_menu_toggle_item(
                "📌", "📍",
                State.t["menu_pin"],
                State.pin_on_top,
                State.toggle_pin_on_top,
            ),
            _quick_menu_toggle_item(
                "🔔", "🔕",
                State.t["pill_notifications"],
                State.notifications_enabled,
                State.toggle_notifications,
            ),
            rx.menu.separator(),

            # ── Idioma (cicla EN → ES → FR) ──────────
            _quick_menu_action_item(
                "🌐",
                State.t["lang_label"],
                State.toggle_language,
                right_slot=rx.text(State.language_label,
                    color=COLOR_PRIMARY, font_size="11px",
                    font_weight="700", letter_spacing="0.08em"),
            ),
            rx.menu.separator(),

            # ── Full settings (abre el modal grande) ─
            _quick_menu_action_item(
                "⚙",
                State.t["menu_settings"],
                State.toggle_settings,
            ),

            # Estilo del content — más ancho para que nada se trunque
            align="end",
            side_offset=6,
            style={"min_width": "240px"},
        ),
    )


# ─────────────────────────────────────────────
#  News pill (header) + news panel (vista alternativa al chat)
# ─────────────────────────────────────────────


def _news_pill_with_badge() -> rx.Component:
    """Pill 📰 en el header con badge numérico si hay unread items."""
    State = _get_state()
    return rx.button(
        rx.hstack(
            rx.text("📰", font_size="12px"),
            rx.text(State.t["pill_news"], font_size="11px", font_weight="600"),
            rx.cond(
                State.news_unread > 0,
                rx.box(
                    State.news_unread.to_string(),
                    bg=COLOR_PRIMARY,
                    color="black",
                    border_radius="99px",
                    padding="0 6px",
                    font_size="10px",
                    font_weight="700",
                    line_height="16px",
                    min_width="18px",
                    text_align="center",
                ),
                rx.box(),
            ),
            spacing="1", align="center",
        ),
        on_click=State.toggle_news_panel,
        bg=rx.cond(
            State.show_news,
            "rgba(194,136,255,0.2)",
            rx.cond(State.news_unread > 0, "rgba(255,154,238,0.1)", "rgba(255,255,255,0.04)"),
        ),
        color=rx.cond(
            State.show_news,
            "#c288ff",
            rx.cond(State.news_unread > 0, COLOR_PRIMARY, "#6a6a7a"),
        ),
        border=rx.cond(
            State.show_news,
            "1px solid rgba(194,136,255,0.5)",
            rx.cond(
                State.news_unread > 0,
                "1px solid rgba(255,154,238,0.4)",
                "1px solid rgba(255,255,255,0.07)",
            ),
        ),
        border_radius="99px",
        padding="0 10px",
        height="28px",
        flex_shrink="0",
        transition="all 0.2s ease",
        _hover={
            "bg": "rgba(194,136,255,0.15)",
            "color": "#c288ff",
            "border": "1px solid rgba(194,136,255,0.4)",
            "transform": "scale(1.04)",
        },
        cursor="pointer",
        title=State.t["news_tooltip_on"],
    )


def _news_category_label(cat: str) -> str:
    """Mapea category → i18n key. Usa la clave t[...] dentro del item."""
    return f"news_category_{cat}"


def _news_item_card(item: dict) -> rx.Component:
    """Card de un descubrimiento en el feed."""
    State = _get_state()
    # Para traducir la categoría del item, compongo la clave en runtime
    # pero como State.t es dict estático en Python, uso rx.match.
    cat_label = rx.match(
        item["category"],
        ("song",    State.t["news_category_song"]),
        ("trailer", State.t["news_category_trailer"]),
        ("article", State.t["news_category_article"]),
        ("game",    State.t["news_category_game"]),
        ("tech",    State.t["news_category_tech"]),
        State.t["news_category_other"],
    )
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(cat_label,
                        color=COLOR_PRIMARY, font_size="10px",
                        font_weight="700", letter_spacing="0.05em"),
                rx.spacer(),
                rx.text(item["created_at"],
                        color="#666", font_size="10px",
                        font_family="monospace"),
                rx.button(
                    "×",
                    on_click=State.delete_news_item(item["id"]),
                    bg="transparent",
                    color="#666",
                    border="none",
                    font_size="18px",
                    line_height="1",
                    padding="0 4px",
                    cursor="pointer",
                    _hover={"color": "#ff8080"},
                    title=State.t["news_delete"],
                ),
                spacing="2", align="center", width="100%",
            ),
            rx.text(item["title"],
                    color="#eee", font_size="14px",
                    font_weight="600", line_height="1.4"),
            rx.cond(
                item["body"] != "",
                rx.text(item["body"],
                        color="#bbb", font_size="12px",
                        line_height="1.5", white_space="pre-wrap"),
                rx.box(),
            ),
            rx.cond(
                item["source_url"] != "",
                rx.link(
                    item["source_url"],
                    href=item["source_url"],
                    is_external=True,
                    color=COLOR_PRIMARY,
                    font_size="11px",
                    style={"textDecoration": "underline"},
                ),
                rx.box(),
            ),
            spacing="1", align="stretch",
        ),
        padding="14px 16px",
        bg="rgba(255,255,255,0.03)",
        border="1px solid rgba(255,154,238,0.12)",
        border_radius="12px",
        width="100%",
        transition="all 0.2s ease",
        _hover={
            "border": "1px solid rgba(255,154,238,0.28)",
            "bg": "rgba(255,154,238,0.04)",
        },
    )


def _news_panel() -> rx.Component:
    """Vista alternativa al chat: feed de descubrimientos de Ashley."""
    State = _get_state()
    return rx.vstack(
        # Header
        rx.hstack(
            rx.text(State.t["news_title"],
                    color=COLOR_PRIMARY, font_size="17px",
                    font_weight="800", letter_spacing="0.03em"),
            rx.spacer(),
            rx.cond(
                State.news_items.length() > 0,
                rx.button(
                    State.t["news_clear_all"],
                    on_click=State.clear_all_news,
                    bg="transparent",
                    color="#ff8080",
                    border="1px solid rgba(255,128,128,0.3)",
                    border_radius="8px",
                    padding="4px 10px",
                    font_size="11px",
                    cursor="pointer",
                    _hover={"bg": "rgba(255,128,128,0.08)"},
                ),
                rx.box(),
            ),
            rx.button(
                State.t["news_close"],
                on_click=State.toggle_news_panel,
                bg="rgba(255,154,238,0.08)",
                color=COLOR_PRIMARY,
                border="1px solid rgba(255,154,238,0.35)",
                border_radius="8px",
                padding="4px 12px",
                font_size="11px",
                font_weight="600",
                cursor="pointer",
                _hover={"bg": "rgba(255,154,238,0.18)"},
            ),
            spacing="2", align="center", width="100%",
            padding_bottom="10px",
            border_bottom="1px solid rgba(255,154,238,0.12)",
        ),
        # Feed
        rx.cond(
            State.news_items.length() > 0,
            rx.vstack(
                rx.foreach(State.news_items, _news_item_card),
                spacing="2", align="stretch", width="100%",
                padding_top="12px",
            ),
            # Empty state — se divide según si el LLM activo soporta
            # búsqueda web:
            #   • web_search_supported=True  → empty con tip de cómo
            #     activar Discovery en Settings (caso normal Grok).
            #   • web_search_supported=False → mensaje explicando que el
            #     modelo activo (Ollama / OpenRouter) no soporta web
            #     search y por eso este panel queda vacío. Sin esto el
            #     user piensa que es un bug — y la review en Reddit
            #     dolería.
            rx.cond(
                State.web_search_supported,
                # ── Caso normal: provider soporta web search ──
                rx.center(
                    rx.vstack(
                        # Hero icon con halo glow
                        rx.box(
                            rx.text("📰", font_size="56px"),
                            width="100px", height="100px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            border_radius="50%",
                            bg="rgba(255,154,238,0.06)",
                            border="2px solid rgba(255,154,238,0.18)",
                            box_shadow="0 0 32px rgba(255,154,238,0.15), inset 0 0 20px rgba(255,154,238,0.05)",
                            margin_bottom="8px",
                        ),
                        # Título principal
                        rx.text(
                            State.t["news_empty"],
                            color="#dddddd", font_size="15px",
                            font_weight="600", line_height="1.5",
                            text_align="center", max_width="380px",
                        ),
                        # Hint en italic
                        rx.text(
                            State.t["news_empty_hint"],
                            color="#888888", font_size="12px",
                            font_style="italic", line_height="1.5",
                            text_align="center", max_width="380px",
                        ),
                        # Card con tip de cómo activar
                        rx.box(
                            rx.hstack(
                                rx.text("💡", font_size="18px"),
                                rx.vstack(
                                    rx.text(
                                        State.t["news_empty_tip_title"],
                                        color=COLOR_PRIMARY,
                                        font_size="12px",
                                        font_weight="700",
                                    ),
                                    rx.text(
                                        State.t["news_empty_tip_body"],
                                        color="#aaaaaa",
                                        font_size="11px",
                                        line_height="1.4",
                                    ),
                                    spacing="1", align="start",
                                ),
                                spacing="3", align="start",
                            ),
                            bg="rgba(255,154,238,0.04)",
                            border="1px solid rgba(255,154,238,0.18)",
                            border_radius="14px",
                            padding="14px 18px",
                            max_width="420px",
                            margin_top="10px",
                        ),
                        spacing="3", align="center",
                    ),
                    width="100%",
                    padding="60px 24px",
                ),
                # ── Caso "modelo sin web search": Ollama / OpenRouter ──
                rx.center(
                    rx.vstack(
                        # Hero icon con halo (color amber/warn en lugar de rosa)
                        rx.box(
                            rx.text("🌐", font_size="56px"),
                            width="100px", height="100px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            border_radius="50%",
                            bg="rgba(255,200,120,0.06)",
                            border="2px solid rgba(255,200,120,0.18)",
                            box_shadow="0 0 32px rgba(255,200,120,0.12)",
                            margin_bottom="8px",
                        ),
                        rx.text(
                            State.t["news_unavailable_title"],
                            color="#ffd28a", font_size="15px",
                            font_weight="600", line_height="1.5",
                            text_align="center", max_width="420px",
                        ),
                        rx.text(
                            State.t["news_unavailable_body"],
                            color="#aaaaaa", font_size="12px",
                            line_height="1.6",
                            text_align="center", max_width="420px",
                        ),
                        # Card con la acción clara para resolverlo
                        rx.box(
                            rx.hstack(
                                rx.text("⚙️", font_size="18px"),
                                rx.text(
                                    State.t["news_unavailable_hint"],
                                    color="#dddddd",
                                    font_size="12px",
                                    font_weight="600",
                                    line_height="1.5",
                                ),
                                spacing="3", align="center",
                            ),
                            bg="rgba(255,200,120,0.04)",
                            border="1px solid rgba(255,200,120,0.22)",
                            border_radius="14px",
                            padding="14px 18px",
                            max_width="420px",
                            margin_top="10px",
                        ),
                        spacing="3", align="center",
                    ),
                    width="100%",
                    padding="60px 24px",
                ),
            ),
        ),
        spacing="2", align="stretch", width="100%",
        height="100%",
        padding="18px 24px",
        overflow_y="auto",
        class_name="ashley-chat glass-chat",
    )


# ─────────────────────────────────────────────
#  License gate (se muestra cuando LICENSE_CHECK_ENABLED y no hay licencia)
# ─────────────────────────────────────────────

def license_gate() -> rx.Component:
    """Pantalla que bloquea el acceso a Ashley hasta que el user active su key.

    Solo se renderiza cuando State.license_needed == True, que a su vez solo
    se pone a True si config.LICENSE_CHECK_ENABLED está activado y la key
    almacenada no valida. En modo dev (flag OFF) este componente no aparece.
    """
    State = _get_state()
    return rx.center(
        rx.vstack(
            rx.image(
                src="/ashley_pfp.jpg",
                width="120px",
                height="120px",
                border_radius="50%",
                object_fit="cover",
                border="3px solid rgba(255,154,238,0.35)",
                box_shadow="0 0 40px rgba(255,154,238,0.35)",
            ),
            rx.heading(
                State.t["license_title"],
                size="6",
                color=COLOR_PRIMARY,
                text_align="center",
                weight="light",
                letter_spacing="2px",
            ),
            rx.text(
                State.t["license_subtitle"],
                color=COLOR_TEXT_DIM,
                font_size="14px",
                text_align="center",
            ),
            rx.form(
                rx.vstack(
                    rx.input(
                        placeholder=State.t["license_placeholder"],
                        id="license_key",
                        name="license_key",
                        font_family="'JetBrains Mono', 'Consolas', monospace",
                        bg="rgba(255,255,255,0.04)",
                        color="white",
                        border="1px solid rgba(255,255,255,0.12)",
                        border_radius="10px",
                        padding="14px 12px",
                        font_size="11px",
                        letter_spacing="0.5px",
                        width="100%",
                        text_align="center",
                        auto_focus=True,
                        _focus={
                            "border": "1px solid rgba(255,154,238,0.55)",
                            "box_shadow": "0 0 14px rgba(255,154,238,0.2)",
                            "outline": "none",
                        },
                        _placeholder={"color": "#555"},
                    ),
                    rx.cond(
                        State.license_error != "",
                        rx.box(
                            rx.text(
                                State.license_error,
                                color="#ff8080",
                                font_size="12px",
                                text_align="center",
                            ),
                            padding="8px 12px",
                            bg="rgba(255,80,80,0.08)",
                            border="1px solid rgba(255,80,80,0.25)",
                            border_radius="8px",
                            width="100%",
                        ),
                        rx.box(),
                    ),
                    rx.button(
                        rx.cond(
                            State.license_submitting,
                            State.t["license_activating"],
                            State.t["license_activate"],
                        ),
                        type="submit",
                        bg=COLOR_PRIMARY,
                        color="black",
                        font_weight="bold",
                        padding="14px",
                        border_radius="10px",
                        width="100%",
                        cursor="pointer",
                        _hover={"bg": "#ffb8f5", "box_shadow": "0 0 18px rgba(255,154,238,0.5)"},
                        transition="all 0.2s ease",
                        disabled=State.license_submitting,
                    ),
                    spacing="3",
                    width="100%",
                ),
                on_submit=State.submit_license,
                reset_on_submit=False,
                width="100%",
            ),
            rx.divider(color_scheme="gray", opacity="0.3"),
            rx.vstack(
                rx.link(
                    State.t["license_buy"],
                    href="https://ashley-ia.lemonsqueezy.com/checkout/buy/618b7e13-511b-435c-8e7f-d14cedadfd02",
                    is_external=True,
                    color=COLOR_PRIMARY,
                    font_size="12px",
                    text_decoration="underline",
                    _hover={"color": "#ffb8f5"},
                ),
                rx.link(
                    State.t["license_lost_key"],
                    href="mailto:hello@ashley-ia.com",
                    is_external=True,
                    color="#777",
                    font_size="11px",
                    _hover={"color": "#aaa"},
                ),
                spacing="2",
                align="center",
            ),
            spacing="4",
            align="center",
            width="460px",
            padding="44px 36px",
            bg="rgba(255,255,255,0.025)",
            border="1px solid rgba(255,255,255,0.07)",
            border_radius="20px",
            box_shadow="0 20px 60px rgba(0,0,0,0.5)",
        ),
        width="100vw",
        height="100vh",
        bg="#0a0a0a",
    )


# ─────────────────────────────────────────────
#  Manual de usuario — dialog modal con accordion
# ─────────────────────────────────────────────

def _manual_section_item(section: dict) -> rx.Component:
    """Una sección del manual = un AccordionItem colapsable.
    section = {"id": str, "icon": str, "title": str, "content_md": str}
    """
    return rx.accordion.item(
        header=rx.hstack(
            rx.text(section["icon"], font_size="18px"),
            rx.text(section["title"],
                    color="#ddd", font_weight="600", font_size="14px"),
            spacing="3", align="center", width="100%",
        ),
        content=rx.box(
            rx.markdown(
                section["content_md"],
                color="#ccc",
                font_size="13px",
                line_height="1.7",
            ),
            padding="12px 16px 16px 16px",
        ),
        value=section["id"],
    )


def _manual_body(manual: dict) -> rx.Component:
    """Renderiza el body completo del manual desde un dict de
    manual_content.MANUAL[lang]. Se evalúa en Python al definir el
    componente — Reflex maneja los 3 idiomas via rx.match en el caller.
    """
    return rx.vstack(
        rx.heading(
            manual["title"],
            color="#ff9aee",
            font_size="20px",
            font_weight="700",
            letter_spacing="0.02em",
        ),
        rx.markdown(
            manual["intro"],
            color="#ccc",
            font_size="13px",
            line_height="1.7",
        ),
        rx.divider(border_color="rgba(255,154,238,0.2)"),
        rx.accordion.root(
            *[_manual_section_item(s) for s in manual["sections"]],
            collapsible=True,
            type="multiple",
            variant="ghost",
            color_scheme="pink",
            width="100%",
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


def manual_dialog() -> rx.Component:
    """Dialog modal del manual de usuario. Se abre con el botón ❓ del
    header. El contenido cambia con el idioma del state via rx.match —
    los 3 árboles (EN/ES/FR) se compilan al inicio pero solo el activo
    se monta gracias al diff de Reflex."""
    State = _get_state()

    # Lazy import del contenido — no es necesario al cargar el módulo
    from .manual_content import get_manual

    en_body = _manual_body(get_manual("en"))
    es_body = _manual_body(get_manual("es"))
    fr_body = _manual_body(get_manual("fr"))

    return rx.dialog.root(
        rx.dialog.content(
            rx.box(
                rx.match(
                    State.language,
                    ("es", es_body),
                    ("fr", fr_body),
                    en_body,  # default: EN
                ),
                max_height="70vh",
                overflow_y="auto",
                padding="4px",
            ),
            rx.flex(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        "✕",
                        on_click=State.close_manual,
                        size="2",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                margin_top="12px",
            ),
            max_width="640px",
            bg="#18181f",
            border="1px solid rgba(255,154,238,0.18)",
            border_radius="14px",
            padding="24px",
        ),
        open=State.manual_open,
        on_open_change=State.set_manual_open,
    )


def manual_button() -> rx.Component:
    """Botón ❓ que abre el manual. Se coloca en el header (top-left)."""
    State = _get_state()
    return rx.tooltip(
        rx.button(
            "❓",
            on_click=State.open_manual,
            size="2",
            variant="ghost",
            color_scheme="pink",
            cursor="pointer",
            font_size="18px",
            padding="6px 10px",
        ),
        content=rx.match(
            State.language,
            ("es", "Manual de usuario"),
            ("fr", "Manuel utilisateur"),
            "User manual",
        ),
    )
