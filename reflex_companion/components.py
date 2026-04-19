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
