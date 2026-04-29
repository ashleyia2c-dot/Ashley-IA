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
    SIDEBAR_LEFT_WIDTH, PANEL_RIGHT_WIDTH, MODEL_3D_HEIGHT,
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
    State = _get_state()
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
            # Botón ❌ — borra este fact específico. Útil cuando Ashley
            # insiste con un tema que el user prefiere olvidar (un dato
            # personal, una preferencia obsoleta, lo que sea).
            rx.tooltip(
                rx.button(
                    "✕",
                    on_click=State.delete_fact(f["hecho"]),
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    cursor="pointer",
                    style={"opacity": "0.5", "_hover": {"opacity": "1", "color": "#ff6688"}},
                ),
                content="Borrar este recuerdo",
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


# ─────────────────────────────────────────────
#  Layout 3-columnas estilo c.ai (v0.15)
# ─────────────────────────────────────────────

def _sidebar_nav_item(
    icon: str,
    label,  # rx.Var o string
    on_click,
    active=None,
    badge=None,
    accent_color: str = COLOR_PRIMARY,
    title=None,
) -> rx.Component:
    """Item del sidebar izquierdo. Acción primaria (Memorias/Noticias/Acciones).

    accent_color permite a Acciones usar el naranja distintivo en lugar
    del rosa del resto. badge es un componente opcional (típicamente el
    contador de noticias unread). active enciende el highlight de la
    barra lateral izquierda + el fondo sutil + el color del icono.
    """
    bg_active   = f"linear-gradient(90deg, rgba(255,255,255,0.04) 0%, transparent 100%)"
    bg_hover    = "rgba(255,255,255,0.04)"
    txt_active  = accent_color
    txt_idle    = "#a8a8b8"

    if active is None:
        # Item sin estado activo (acción pura, ej: ⚙ Ajustes, ❓ Manual)
        bg = "transparent"
        txt = txt_idle
        border_left = "3px solid transparent"
    else:
        bg = rx.cond(active, bg_active, "transparent")
        txt = rx.cond(active, txt_active, txt_idle)
        border_left = rx.cond(
            active,
            f"3px solid {accent_color}",
            "3px solid transparent",
        )

    children = [
        rx.text(icon, font_size="15px", width="22px", text_align="center"),
        rx.text(label, font_size="13px", font_weight="500", flex="1"),
    ]
    if badge is not None:
        children.append(badge)

    return rx.box(
        rx.hstack(*children, align="center", spacing="3", width="100%"),
        on_click=on_click,
        cursor="pointer",
        padding="10px 14px",
        padding_left="11px",  # 14 - 3 del border-left
        border_radius="0 10px 10px 0",
        background=bg,
        color=txt,
        border_left=border_left,
        transition="background 0.15s ease, color 0.15s ease",
        _hover={
            "background": bg_hover,
            "color": accent_color,
        },
        title=title or "",
        class_name="ashley-nav-item",
    )


def _sidebar_toggle_row(icon_on: str, icon_off: str, label, active, on_click) -> rx.Component:
    """Fila compacta para toggles secundarios (TTS, Natural, Focus, Pin, Notif).

    Más compacto que _sidebar_nav_item — pensado para la sección de
    abajo donde van toggles que NO son la acción principal del momento.
    Incluye un check ✓ a la derecha cuando está activo, para que sea
    obvio el estado sin tener que adivinar por el color.
    """
    return rx.box(
        rx.hstack(
            rx.text(
                rx.cond(active, icon_on, icon_off),
                font_size="13px", width="20px", text_align="center",
            ),
            rx.text(label, font_size="12px", flex="1"),
            rx.cond(
                active,
                rx.text("●", color=COLOR_PRIMARY, font_size="9px"),
                rx.text("○", color="#444", font_size="9px"),
            ),
            spacing="2", align="center", width="100%",
        ),
        on_click=on_click,
        cursor="pointer",
        padding="6px 14px",
        border_radius="6px",
        color=rx.cond(active, "#ddd", "#888"),
        transition="background 0.15s ease, color 0.15s ease",
        _hover={
            "background": "rgba(255,255,255,0.04)",
            "color": COLOR_PRIMARY,
        },
    )


def _sidebar_section_label(text) -> rx.Component:
    """Subtítulo de sección dentro del sidebar (uppercase, pequeño, gris).

    text puede ser un rx.Var (i18n) o un string literal en inglés.
    """
    return rx.text(
        text,
        font_size="10px",
        color="#666",
        font_weight="700",
        letter_spacing="0.1em",
        text_transform="uppercase",
        padding="0 14px",
        margin_top="4px",
    )


def _sidebar_news_badge() -> rx.Component:
    """Badge con el contador de noticias unread, solo visible si >0."""
    State = _get_state()
    return rx.cond(
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
    )


def left_sidebar() -> rx.Component:
    """Sidebar izquierdo de navegación — sustituye a los pills del header.

    Estructura:
      • ACCIONES PRIMARIAS — Memorias, Noticias (con badge), Acciones (naranja)
      • TOGGLES — Natural, TTS, Focus, Pin on top, Notificaciones
      • FOOTER — Idioma (cicla), Ajustes, Manual

    El sidebar es sticky (no se va con el scroll del chat) y tiene su
    propio fondo glassmorphism distinto al del chat (ligeramente más
    oscuro para diferenciarse).
    """
    State = _get_state()

    return rx.vstack(
        # ── Sección: acciones primarias ─────────────────────────
        rx.vstack(
            _sidebar_nav_item(
                "🧠",
                State.t["pill_memories"],
                State.toggle_memories,
                active=State.show_memories,
            ),
            _sidebar_nav_item(
                "📰",
                State.t["pill_news"],
                State.toggle_news_panel,
                active=State.show_news,
                badge=_sidebar_news_badge(),
            ),
            _sidebar_nav_item(
                "⚡",
                State.t["pill_actions"],
                State.toggle_auto_actions,
                active=State.auto_actions,
                accent_color="#ff7b45",  # naranja distintivo (igual que el pill)
            ),
            spacing="0", align="stretch", width="100%",
            padding_y="8px",
        ),

        # ── Separador ────────────────────────────────────────────
        rx.divider(border_color="rgba(255,255,255,0.05)", margin_y="0"),

        # ── Sección: toggles secundarios ──────────────────────────
        rx.vstack(
            _sidebar_section_label(rx.match(
                State.language,
                ("es", "AJUSTES RÁPIDOS"),
                ("fr", "RÉGLAGES RAPIDES"),
                "QUICK SETTINGS",
            )),
            _sidebar_toggle_row(
                "🗣", "🗣",
                State.t["pill_natural"],
                State.voice_mode,
                State.toggle_voice_mode,
            ),
            _sidebar_toggle_row(
                "🔊", "🔈",
                State.t["menu_tts"],
                State.tts_enabled,
                State.toggle_tts,
            ),
            _sidebar_toggle_row(
                "⛶", "⛶",
                State.t["pill_focus"],
                State.focus_mode,
                State.toggle_focus_mode,
            ),
            _sidebar_toggle_row(
                "📌", "📍",
                State.t["menu_pin"],
                State.pin_on_top,
                State.toggle_pin_on_top,
            ),
            _sidebar_toggle_row(
                "🔔", "🔕",
                State.t["pill_notifications"],
                State.notifications_enabled,
                State.toggle_notifications,
            ),
            spacing="0", align="stretch", width="100%",
            padding_y="8px",
        ),

        # ── Spacer empuja el footer al fondo ─────────────────────
        rx.spacer(),

        # ── Footer: idioma, ajustes, manual ──────────────────────
        rx.divider(border_color="rgba(255,255,255,0.05)", margin_y="0"),
        rx.vstack(
            _sidebar_nav_item(
                "🌐",
                rx.hstack(
                    rx.text(State.t["lang_label"], font_size="13px"),
                    rx.spacer(),
                    rx.text(
                        State.language_label,
                        color=COLOR_PRIMARY,
                        font_size="10px",
                        font_weight="700",
                        letter_spacing="0.08em",
                    ),
                    width="100%", align="center",
                ),
                State.toggle_language,
            ),
            _sidebar_nav_item(
                "⚙",
                State.t["menu_settings"],
                State.toggle_settings,
            ),
            _sidebar_nav_item(
                "❓",
                rx.match(
                    State.language,
                    ("es", "Manual"),
                    ("fr", "Manuel"),
                    "Manual",
                ),
                State.open_manual,
            ),
            spacing="0", align="stretch", width="100%",
            padding_y="8px",
        ),

        spacing="0", align="stretch",
        height="100%",
        width=SIDEBAR_LEFT_WIDTH,
        flex_shrink="0",
        class_name="ashley-sidebar glass-sidebar",
    )


def _affection_heart() -> rx.Component:
    """v0.16 — corazón outline elegante con respiración constante.

    Mockup-style: solo el outline (no fill solid), tono ámbar warm,
    animación de "breath" perpetua (escala sutil + glow pulsante).
    Hover: animación se acelera + glow más intenso.
    Afecto >70: respiración más viva con tinte coral.

    El SVG usa fill ámbar dorado (#d4a373) por defecto, fill coral
    cuando .heart-glow activo (CSS hace el override del color de
    forma estática). El outline es el mismo path pero con stroke
    más definido — da peso visual sin parecer un emoji.
    """
    State = _get_state()
    return rx.tooltip(
        rx.box(
            rx.html("""
            <svg class="ashley-heart-svg" viewBox="0 0 100 90" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
              <defs>
                <linearGradient id="ashley-heart-warm" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stop-color="#e8caa0"/>
                  <stop offset="100%" stop-color="#c08858"/>
                </linearGradient>
              </defs>
              <path d="M50,82 C50,82 8,57 8,30 C8,16 19,5 30,5 C39,5 46,11 50,18 C54,11 61,5 70,5 C81,5 92,16 92,30 C92,57 50,82 50,82 Z"
                    fill="url(#ashley-heart-warm)"
                    stroke="#f0d5b0"
                    stroke-width="2"
                    stroke-linejoin="round"
                    opacity="0.95"/>
            </svg>
            """),
            class_name=rx.cond(
                State.affection > 70,
                "heart-frame heart-glow",
                "heart-frame",
            ),
        ),
        content=rx.match(
            State.language,
            ("es", "Cuánto te quiere Ashley"),
            ("fr", "Affection d'Ashley"),
            "How much Ashley likes you",
        ),
    )


# ─────────────────────────────────────────────
#  Layout 2-cols boutique noir (v0.16)
# ─────────────────────────────────────────────

def _ambient_lights() -> rx.Component:
    """Capas de luz ambient animadas detrás del layout — efecto vela
    constante y suave, definido por completo en styles.py
    (clases ambient-glow-1/2/3, animaciones ambientFloat)."""
    return rx.fragment(
        rx.box(class_name="ambient-glow-1"),
        rx.box(class_name="ambient-glow-2"),
        rx.box(class_name="ambient-glow-3"),
    )


def _light_rays_svg() -> rx.Component:
    """Rayos de luz cenital — SVG con 5 polygons fanning desde el top
    del panel hacia abajo. Cada uno tiene su propia animación de pulse
    de opacity (en styles.py: rayPulseA-E). Conjuntamente crean el
    efecto de "luz angelical" / "spotlight de teatro" que el user pidió.

    El gradient (#ashley-ray-grad) está en defs global de styles.py,
    fade gold→transparent a 70% de altura. Eso hace que los rayos
    iluminen la parte superior (cara/hombros de Ashley) y se
    desvanezcan antes de tocar el cuerpo — chiaroscuro suave.

    Ángulos: los rayos parten desde un origen virtual en x=42-48
    (centrado-ligeramente-izquierda) y se abren a x=8-90 al fondo.
    transform-origin top → en futuras animaciones se podrían rotar
    suaves para sensación de "luz que respira". """
    return rx.html("""
    <svg class="ashley-light-rays" viewBox="0 0 100 100" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
      <polygon class="ray ray-1" points="38,-5 41,-5 14,108 8,108"/>
      <polygon class="ray ray-2" points="40.5,-5 43.5,-5 30,108 22,108"/>
      <polygon class="ray ray-3" points="43,-5 46,-5 50,108 42,108"/>
      <polygon class="ray ray-4" points="45.5,-5 48.5,-5 70,108 62,108"/>
      <polygon class="ray ray-5" points="48,-5 51,-5 90,108 82,108"/>
    </svg>
    """)


def _top_nav_link(icon_name: str, label, on_click, is_active=None) -> rx.Component:
    """Link del nav superior — icono Lucide + label pequeño debajo.
    Tono cream apagado, hover ámbar suave, .active highlights con glow."""
    base_class = "ashley-nav-link"
    if is_active is None:
        return rx.box(
            rx.icon(icon_name, size=18, stroke_width=1.6),
            rx.text(label, font_size="11px"),
            on_click=on_click,
            class_name=base_class,
        )
    return rx.box(
        rx.icon(icon_name, size=18, stroke_width=1.6),
        rx.text(label, font_size="11px"),
        on_click=on_click,
        class_name=rx.cond(is_active, base_class + " active", base_class),
    )


def _top_nav_bar() -> rx.Component:
    """Barra horizontal arriba del panel izquierdo. Sustituye al
    sidebar vertical del layout anterior."""
    State = _get_state()
    return rx.hstack(
        _top_nav_link(
            "diamond",
            rx.match(State.language, ("es", "Ashley"), ("fr", "Ashley"), "Ashley"),
            None,  # logo, sin acción
        ),
        _top_nav_link(
            "brain",
            State.t["pill_memories"],
            State.toggle_memories,
            State.show_memories,
        ),
        _top_nav_link(
            "newspaper",
            State.t["pill_news"],
            State.toggle_news_panel,
            State.show_news,
        ),
        _top_nav_link(
            "zap",
            State.t["pill_actions"],
            State.toggle_auto_actions,
            State.auto_actions,
        ),
        _top_nav_link(
            "settings",
            State.t["menu_settings"],
            State.toggle_settings,
        ),
        spacing="0",
        class_name="ashley-top-nav",
    )


def _portrait_action_btn(icon_name: str, on_click=None, button_id=None,
                          class_name="", is_active=None,
                          stroke_width: float = 1.7,
                          title=None) -> rx.Component:
    """Botón circular debajo del nombre Ashley. Iconos Lucide warm tone.

    Notas sobre title: puede ser str literal o un Reflex Var (típico:
    State.t["mic_tooltip"]). NUNCA hacer `if title:` porque Reflex Vars
    no son truthy-checkable — siempre pasamos el kwarg si no es None.
    """
    base = "ashley-action-btn"
    # class_name/button_id en mi uso son siempre Python strings (no Vars),
    # así que `if class_name:` y `if button_id:` son seguros.
    classes = base + (" " + class_name if class_name else "")
    if is_active is not None:
        classes_var = rx.cond(is_active, classes + " active", classes)
    else:
        classes_var = classes
    kwargs = {}
    if on_click is not None:
        kwargs["on_click"] = on_click
    if button_id:
        kwargs["id"] = button_id
    if title is not None:
        # Pasamos el title sin evaluar truthy — Reflex Var no se puede
        # convertir a bool. Si el caller pasó "", se mostrará tooltip
        # vacío (browsers lo ignoran).
        kwargs["title"] = title
    return rx.box(
        rx.icon(icon_name, size=18, stroke_width=stroke_width),
        class_name=classes_var,
        **kwargs,
    )


def _portrait_overlay() -> rx.Component:
    """Bloque inferior del panel izquierdo: nombre serif grande + status
    pulsante + fila de botones de acción (mic/sparkles/focus).

    v0.16.1 — el user pidió mover el paperclip al área del input. Ahora
    quedan solo 3 acciones aquí (las que son "de Ashley", no del input
    en sí): micrófono, iniciativa, focus mode.
    """
    State = _get_state()
    return rx.box(
        # Nombre Ashley grande serif
        rx.text("Ashley", class_name="ashley-name-large"),

        # Status — cambia entre "pensando.../hablando.../en línea"
        rx.cond(
            State.is_thinking,
            rx.box(
                rx.html('<span class="status-dot"></span>'),
                rx.text(State.t["status_thinking"], display="inline"),
                class_name="ashley-status-line",
            ),
            rx.cond(
                State.current_response != "",
                rx.box(
                    rx.html('<span class="status-dot"></span>'),
                    rx.text(State.t["status_speaking"], display="inline"),
                    class_name="ashley-status-line",
                ),
                rx.box(
                    rx.html('<span class="status-dot"></span>'),
                    rx.text(State.t["status_online"], display="inline"),
                    class_name="ashley-status-line",
                ),
            ),
        ),

        # Fila de acciones (paperclip ya no, vive en el input)
        rx.hstack(
            # 🎤 mic — JS observer escucha #ashley-mic-btn para start/stop
            _portrait_action_btn(
                "mic",
                button_id="ashley-mic-btn",
                class_name="ashley-mic-btn",
                title=State.t["mic_tooltip"],
            ),
            # ✨ initiative — Ashley habla por su cuenta
            _portrait_action_btn(
                "sparkles",
                on_click=State.send_initiative,
                title=State.t["menu_initiative"],
            ),
            # ⛶ focus — toggle modo focus (oculta panel)
            _portrait_action_btn(
                "focus",
                on_click=State.toggle_focus_mode,
                is_active=State.focus_mode,
                title=State.t["pill_focus"],
            ),
            spacing="3",
            class_name="ashley-action-row",
        ),

        class_name="ashley-portrait-overlay",
    )


def _portrait_view_toggle() -> rx.Component:
    """Pill toggle 2D | 3D arriba-derecha del portrait panel.

    En 2D la imagen aparece en un cuadrado contenido (no se deforma).
    En 3D la imagen llena toda la columna vertical (preview de cómo
    quedará el viewer 3D futuro). State persiste entre clicks via
    State.view_3d_mode.
    """
    State = _get_state()
    return rx.box(
        rx.button(
            "2D",
            on_click=State.set_view_3d_mode_false,
            class_name=rx.cond(~State.view_3d_mode, "seg active", "seg"),
            type="button",
        ),
        rx.button(
            "3D",
            on_click=State.set_view_3d_mode_true,
            class_name=rx.cond(State.view_3d_mode, "seg active", "seg"),
            type="button",
        ),
        class_name="portrait-view-toggle",
    )


def left_portrait_panel() -> rx.Component:
    """Panel izquierdo — portrait + nav arriba + overlay abajo.

    Modos (toggle 2D/3D, v0.16.1):
      • mode-2d: imagen en cuadrado contenido (no deformada). Espacio
        debajo para nombre/actions con respiración.
      • mode-3d: imagen full-vertical (preview del viewer 3D futuro).

    Capas:
      1. mood-image — imagen actual (cambia con el chat)
      2. light-rays — sunbeams diagonales animados (boutique noir vibe)
      3. portrait-spotlight — luz cálida arriba que titila como vela
      4. mood-vignette — gradient para legibilidad del texto
      5. portrait-view-toggle — pill 2D|3D arriba-derecha
      6. top-nav-bar — Ashley/Recuerdos/Noticias/Acciones/Ajustes
      7. portrait-overlay — nombre serif + status + 3 actions
    """
    State = _get_state()
    return rx.box(
        # Imagen mood (cambia con el chat)
        rx.box(
            class_name="ashley-mood-image",
            style={
                "backgroundImage": "url('" + State.current_image + "')",
            },
        ),
        # Light rays cenital (cono de luz angelical desde arriba)
        _light_rays_svg(),
        # Spotlight cálido
        rx.box(class_name="portrait-spotlight"),
        # Vignette
        rx.box(class_name="ashley-mood-vignette"),
        # Toggle 2D | 3D
        _portrait_view_toggle(),
        # Nav arriba
        _top_nav_bar(),
        # Overlay con nombre/status/actions
        _portrait_overlay(),

        class_name=rx.cond(
            State.view_3d_mode,
            "ashley-portrait-panel mode-3d",
            "ashley-portrait-panel mode-2d",
        ),
    )


def _chat_header_bar() -> rx.Component:
    """Header del panel derecho — Ashley en serif grande + focus toggle
    + heart counter.

    v0.16.6: añadido el botón de focus toggle AQUÍ (no solo en el
    portrait overlay) porque al activar focus mode el portrait se
    oculta — y con él el botón. El user quedaba atrapado en focus
    sin forma de volver. Ahora el toggle vive también en el chat
    header (siempre visible). Ambos botones disparan la misma acción.
    """
    State = _get_state()
    return rx.box(
        # Lado izquierdo: nombre serif
        rx.text("Ashley", class_name="ashley-serif", font_size="32px"),
        # Lado derecho: focus toggle + corazón outline + cifra
        rx.box(
            # Focus mode toggle — el icono cambia según estado
            rx.tooltip(
                rx.box(
                    rx.cond(
                        State.focus_mode,
                        rx.icon("panel-left-open", size=18, stroke_width=1.7),
                        rx.icon("maximize", size=18, stroke_width=1.7),
                    ),
                    on_click=State.toggle_focus_mode,
                    class_name=rx.cond(
                        State.focus_mode,
                        "ashley-header-action active",
                        "ashley-header-action",
                    ),
                ),
                content=rx.cond(
                    State.focus_mode,
                    rx.match(
                        State.language,
                        ("es", "Volver al modo normal"),
                        ("fr", "Retourner au mode normal"),
                        "Back to normal view",
                    ),
                    rx.match(
                        State.language,
                        ("es", "Centrar el chat (focus)"),
                        ("fr", "Centrer le chat (focus)"),
                        "Center chat (focus mode)",
                    ),
                ),
            ),
            # Corazón + cifra
            rx.box(
                _affection_heart(),
                rx.text(State.affection, class_name="ashley-affection-number"),
                class_name="ashley-affection-counter",
                display="flex",
                align_items="center",
            ),
            display="flex",
            align_items="center",
            style={"gap": "14px"},
        ),
        class_name="ashley-chat-header",
    )


def _ashley_character_card() -> rx.Component:
    """Tarjeta superior del panel derecho con avatar + nombre + status.

    Versión más compacta del portrait panel actual — el área grande de
    abajo se reserva para el modelo 3D futuro. Mantiene la info clave:
    avatar (que cambia con el mood), nombre, status pulse, y el corazón
    de afecto a la derecha (en vez de barra horizontal, mucho más bonito).
    """
    State = _get_state()

    return rx.hstack(
        # ── Lado izquierdo: avatar + info textual ────────────────
        rx.vstack(
            # Avatar pequeño + nombre + status en horizontal
            rx.hstack(
                rx.box(
                    rx.image(
                        src=State.current_image,
                        width="100%", height="100%",
                        object_fit="cover",
                    ),
                    width="56px", height="56px",
                    border_radius="50%",
                    overflow="hidden",
                    border=f"2px solid {COLOR_PRIMARY}",
                    flex_shrink="0",
                    background_image="url('/ashley_pfp.jpg')",
                    background_size="cover",
                    background_position="center",
                    class_name=rx.cond(
                        State.is_thinking | (State.current_response != ""),
                        "portrait-thinking",
                        "portrait-idle",
                    ),
                ),
                rx.vstack(
                    rx.text(
                        "Ashley",
                        font_size="17px", font_weight="800",
                        color=COLOR_PRIMARY, letter_spacing="0.04em",
                        style={"textShadow": "0 0 12px rgba(255,154,238,0.35)"},
                    ),
                    # Status row (igual que portrait pero menos vertical)
                    rx.cond(
                        State.is_thinking,
                        rx.hstack(
                            rx.box(
                                width="7px", height="7px", border_radius="50%", bg=COLOR_PRIMARY,
                                style={"animation": "avatarPulse 1.2s ease-in-out infinite"},
                            ),
                            rx.text(State.t["status_thinking"], color=COLOR_PRIMARY,
                                    font_size="11px", font_style="italic"),
                            spacing="2", align="center",
                        ),
                        rx.cond(
                            State.current_response != "",
                            rx.hstack(
                                rx.box(
                                    width="7px", height="7px", border_radius="50%", bg=COLOR_STATUS_WRITING,
                                    style={"animation": "avatarPulse 1.2s ease-in-out infinite"},
                                ),
                                rx.text(State.t["status_speaking"], color=COLOR_STATUS_WRITING,
                                        font_size="11px", font_style="italic"),
                                spacing="2", align="center",
                            ),
                            rx.hstack(
                                rx.box(width="7px", height="7px", border_radius="50%",
                                       bg=COLOR_STATUS_ONLINE),
                                rx.text(State.t["status_online"], color=COLOR_STATUS_ONLINE, font_size="11px"),
                                spacing="2", align="center",
                            ),
                        ),
                    ),
                    spacing="1", align="start",
                ),
                spacing="3", align="center", width="100%",
            ),

            # Subtítulo / brand
            rx.text(
                State.t["brand_subtitle"],
                color=COLOR_TEXT_MUTED, font_size="10px",
                letter_spacing="0.05em",
                margin_top="2px",
            ),

            spacing="2",
            align="stretch",
            flex="1",
            min_width="0",
        ),

        # ── Lado derecho: el corazón de afecto ──────────────────
        # padding_bottom mantiene espacio para la cifra (que está en
        # absolute bottom:-20 dentro del heart-frame).
        rx.box(
            _affection_heart(),
            padding_top="2px",
            padding_bottom="24px",
            flex_shrink="0",
        ),

        spacing="3",
        align="center",
        padding="16px 18px",
        border_radius="14px",
        width="100%",
        class_name="ashley-character-card",
    )


def _view_2d_3d_toggle() -> rx.Component:
    """Toggle pill 2D | 3D para alternar la vista del panel derecho.

    v0.15.4: el 2D (imagen mood-image cuadrada) ya funciona; el 3D
    (placeholder vertical) está reservado para cuando el viewer real
    aterrice. El user puede hacer ping-pong entre vistas.
    """
    State = _get_state()

    def _seg(label: str, is_active, on_click):
        return rx.button(
            label,
            on_click=on_click,
            type="button",
            bg=rx.cond(is_active, COLOR_PRIMARY, "transparent"),
            color=rx.cond(is_active, "black", "#aaa"),
            border="none",
            border_radius="0",
            padding="5px 14px",
            font_size="11px",
            font_weight="800",
            letter_spacing="0.05em",
            cursor="pointer",
            transition="all 0.18s ease",
            _hover={
                "bg": rx.cond(is_active, COLOR_PRIMARY, "rgba(255,154,238,0.10)"),
                "color": rx.cond(is_active, "black", COLOR_PRIMARY),
            },
        )

    return rx.hstack(
        _seg("2D", ~State.view_3d_mode, State.set_view_3d_mode_false),
        _seg("3D",  State.view_3d_mode, State.set_view_3d_mode_true),
        spacing="0",
        background="rgba(15,8,25,0.85)",
        border="1px solid rgba(255,154,238,0.30)",
        border_radius="99px",
        overflow="hidden",
        backdrop_filter="blur(14px)",
        style={
            "WebkitBackdropFilter": "blur(14px)",
            "boxShadow": "0 4px 14px rgba(0,0,0,0.4)",
        },
        position="absolute",
        top="12px",
        right="12px",
        z_index="10",
    )


def _ashley_2d_view() -> rx.Component:
    """Vista 2D — imagen mood-image en un área CUADRADA.

    aspect-ratio 1/1 → la imagen no se deforma. object-fit: cover hace
    crop centrado si el asset no es 1:1, pero mantiene proporciones.
    """
    State = _get_state()
    return rx.box(
        rx.image(
            src=State.current_image,
            width="100%", height="100%",
            object_fit="cover",
            style={"objectPosition": "center top"},
        ),
        width="100%",
        # aspect-ratio = 1/1 → cuadrado perfecto, height = width
        style={"aspectRatio": "1 / 1"},
        background_image="url('/ashley_pfp.jpg')",
        background_size="cover",
        background_position="center",
        class_name=rx.cond(
            State.is_thinking | (State.current_response != ""),
            "ashley-2d-portrait portrait-thinking",
            "ashley-2d-portrait portrait-idle",
        ),
        border_radius="18px",
        overflow="hidden",
    )


def _ashley_3d_placeholder() -> rx.Component:
    """Vista 3D — placeholder VERTICAL para el futuro modelo 3D.

    Vertical (aspect-ratio 3/4) anticipa el formato típico de un VRM
    full-body o Live2D rig. Cuando el viewer real esté listo, el
    contenido interior se reemplaza pero el contenedor mantiene sus
    proporciones.
    """
    State = _get_state()
    return rx.center(
        rx.vstack(
            rx.text(
                "✨",
                font_size="56px",
                style={"filter": "drop-shadow(0 0 24px rgba(255,154,238,0.6))"},
            ),
            rx.text(
                rx.match(
                    State.language,
                    ("es", "Modelo 3D"),
                    ("fr", "Modèle 3D"),
                    "3D Model",
                ),
                color="#dadaee", font_size="15px", font_weight="700",
                letter_spacing="0.10em",
                margin_top="8px",
            ),
            rx.text(
                rx.match(
                    State.language,
                    ("es", "próximamente"),
                    ("fr", "bientôt disponible"),
                    "coming soon"),
                color="#888", font_size="12px", font_style="italic",
                letter_spacing="0.05em",
            ),
            spacing="1", align="center",
        ),
        width="100%",
        # 3:4 — más alto que ancho, anticipa el viewer full-body
        style={"aspectRatio": "3 / 4"},
        background="linear-gradient(160deg, rgba(255,154,238,0.06) 0%, rgba(60,30,90,0.10) 50%, rgba(20,10,40,0.06) 100%)",
        border="1px solid rgba(255,154,238,0.18)",
        border_radius="18px",
        box_shadow="inset 0 0 80px rgba(255,154,238,0.06), 0 8px 32px rgba(0,0,0,0.4)",
        overflow="hidden",
    )


def _model_3d_placeholder() -> rx.Component:
    """Área grande del panel derecho — toggle 2D ↔ 3D (v0.15.4).

    La estructura es un wrapper relative + el toggle absoluto arriba a
    la derecha + el contenido (2D o 3D según State.view_3d_mode).
    """
    State = _get_state()
    return rx.box(
        # Toggle pill 2D | 3D arriba-derecha
        _view_2d_3d_toggle(),

        # Contenido — switch según mode
        rx.cond(
            State.view_3d_mode,
            _ashley_3d_placeholder(),
            _ashley_2d_view(),
        ),

        width="100%",
        position="relative",
    )


def right_panel() -> rx.Component:
    """Panel derecho — tarjeta de Ashley arriba + área 2D/3D abajo.

    v0.15.4: el área de visualización ya no usa flex=1 (que estiraba
    la imagen 2D y la deformaba). Ahora usa aspect-ratio:
       • 2D mode → 1/1 cuadrado (no deforma la portrait)
       • 3D mode → 3/4 vertical (anticipa el VRM full-body)
    El user alterna con el toggle pill 2D | 3D arriba-derecha del área.

    Sticky igual que el sidebar izquierdo. Si el contenido total cabe
    en el viewport, queda fijo; si no, scrollea naturalmente con la
    página. focus_mode oculta todo el panel.
    """
    State = _get_state()
    return rx.vstack(
        _ashley_character_card(),
        _model_3d_placeholder(),
        spacing="3",
        align="stretch",
        # Sin height fijo: el panel toma el espacio que necesita su
        # contenido (card + área aspect-ratio). En 4K queda compacto
        # arriba-derecha y se ven las estrellas debajo.
        width=PANEL_RIGHT_WIDTH,
        flex_shrink="0",
        class_name="ashley-right-panel",
    )
