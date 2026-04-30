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
    """v0.14.5 — actualizado a paleta wine boutique. Antes: rosa neón
    hardcodeado (#ff9aee + #2a0f3d), no encajaba en el dialog tras
    el rediseño."""
    State = _get_state()
    return rx.hstack(
        rx.box(
            rx.text(t["categoria"], font_size="10px", font_weight="bold",
                    color=COLOR_PRIMARY),
            bg=COLOR_BG_FACT_BADGE,
            padding="2px 8px", border_radius="99px",
        ),
        rx.text(t["valor"], flex="1", color=COLOR_TEXT_FACT, font_size="13px"),
        rx.button(
            "×",
            on_click=State.delete_taste(t["id"]),
            size="1", variant="ghost", color="#c8a47d",
            cursor="pointer",
            _hover={"color": "#e6b888"},
        ),
        spacing="3", align="center",
        padding_y="6px",
        border_bottom="1px solid rgba(212,163,115,0.10)",
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

        # v0.16.8 — portrait-thinking marca al panel mientras Ashley
        # piensa o stream. ashley_fx.js la detecta vía querySelector
        # para disparar playThinking(). Antes el selector vivía en
        # componentes muertos (deleted v0.16) y el sonido no sonaba.
        class_name=rx.cond(
            State.is_thinking,
            rx.cond(
                State.view_3d_mode,
                "ashley-portrait-panel mode-3d portrait-thinking",
                "ashley-portrait-panel mode-2d portrait-thinking",
            ),
            rx.cond(
                State.view_3d_mode,
                "ashley-portrait-panel mode-3d",
                "ashley-portrait-panel mode-2d",
            ),
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
        # Lado derecho: manual + focus toggle + corazón outline + cifra
        rx.box(
            # Botón del manual (?). v0.16 — el manual_button del header
            # antiguo se borró en la limpieza de dead code; éste lo
            # reemplaza en la UI nueva.
            rx.tooltip(
                rx.box(
                    rx.icon("circle-help", size=18, stroke_width=1.7),
                    on_click=State.open_manual,
                    class_name="ashley-header-action",
                ),
                content=rx.match(
                    State.language,
                    ("es", "Manual de usuario"),
                    ("fr", "Manuel d'utilisateur"),
                    "User manual",
                ),
            ),
            # Toggle TTS — voz de Ashley ON/OFF (v0.16.12). Antes vivía
            # en el sidebar viejo que se borró en la limpieza dead code.
            # Icono Volume2 cuando ON, VolumeX cuando OFF.
            rx.tooltip(
                rx.box(
                    rx.cond(
                        State.tts_enabled,
                        rx.icon("volume-2", size=18, stroke_width=1.7),
                        rx.icon("volume-x", size=18, stroke_width=1.7),
                    ),
                    on_click=State.toggle_tts,
                    class_name=rx.cond(
                        State.tts_enabled,
                        "ashley-header-action active",
                        "ashley-header-action",
                    ),
                ),
                content=rx.cond(
                    State.tts_enabled,
                    rx.match(
                        State.language,
                        ("es", "Voz de Ashley: ACTIVADA (click para silenciar)"),
                        ("fr", "Voix d'Ashley : ACTIVÉE (clic pour couper)"),
                        "Ashley's voice: ON (click to mute)",
                    ),
                    rx.match(
                        State.language,
                        ("es", "Voz de Ashley: silenciada (click para activar)"),
                        ("fr", "Voix d'Ashley : coupée (clic pour activer)"),
                        "Ashley's voice: muted (click to enable)",
                    ),
                ),
            ),
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


