import base64
import re
import reflex as rx

from .config import (
    GROK_MODEL,
    CHAT_FILE, FACTS_FILE, DIARY_FILE, AFFECTION_FILE,
    MAX_HISTORY_MESSAGES, MAX_FACTS, MESSAGES_PER_EXTRACTION,
    SESSION_TIMEOUT_MINUTES, STREAM_CHUNK_SIZE,
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_BG_APP, COLOR_BG_CHAT,
    COLOR_BG_MSG_ASHLEY, COLOR_BG_MSG_USER,
    COLOR_BG_INPUT, COLOR_BG_FACT_BADGE,
    COLOR_TEXT_MUTED, COLOR_TEXT_DIM, COLOR_TEXT_FACT,
    COLOR_STATUS_ONLINE, COLOR_STATUS_WRITING,
    COLOR_BUTTON_OFF, COLOR_BUTTON_OFF_TEXT,
    SHADOW_ASHLEY, SHADOW_USER, SHADOW_BUTTON, SHADOW_AVATAR,
    AVATAR_SIZE, CHAT_WIDTH, DIALOG_WIDTH, CHAT_HEIGHT, MEMORY_HEIGHT,
    LICENSE_CHECK_ENABLED,
)
from .memory import (
    load_json, save_json, now_iso, ensure_ids, ensure_facts,
    is_diary_query, format_facts, format_diary,
    extract_facts, generate_diary_entry,
)
from .prompts import build_system_prompt, build_initiative_prompt
from .llm_provider import XAI_MODELS, OPENROUTER_MODELS
from .parsing import (
    clean_display as _clean_display_fn,
    extract_mood as _extract_mood_fn,
    extract_action as _extract_action_fn,
    extract_affection as _extract_affection_fn,
    _SAFE_ACTIONS, _USER_ACTION_VERBS, _ASHLEY_FAKE_HINTS,
)
from . import i18n

from datetime import datetime, timezone


# ─────────────────────────────────────────────
#  Helpers pre-state
# ─────────────────────────────────────────────

def _license_needed_default() -> bool:
    """Valor inicial de State.license_needed ANTES de que on_load valide.

    Sin este helper, la página renderiza con `license_needed=True` por un
    segundo (mientras validamos contra LS por red en on_load), produciendo
    un flash del gate → chat que se ve poco profesional.

    Con el helper:
      - Sin flag → False (gate nunca aparece en dev)
      - Flag ON y hay license.json en disco → False (chat desde el primer
        pixel; on_load validará contra LS en background y corregirá si el
        vendedor deshabilitó la key)
      - Flag ON y no hay license.json → True (gate desde el primer pixel)
    """
    if not LICENSE_CHECK_ENABLED:
        return False
    try:
        from . import license as _lic
        return _lic.load_stored() is None
    except Exception:
        # Fail-safe: en caso de error leyendo el disco, mostramos el gate.
        # Mejor falso positivo (user legítimo mete key otra vez) que dejar
        # entrar a alguien sin licencia por un bug de I/O.
        return True


# ─────────────────────────────────────────────
#  Estado
# ─────────────────────────────────────────────

class State(rx.State):
    # ── Datos persistentes ────────────────────
    messages: list[dict[str, str]] = []
    facts: list[dict[str, str]] = []
    diary: list[dict[str, str]] = []
    tastes: list[dict[str, str]] = []

    # ── UI ────────────────────────────────────
    current_response: str = ""
    is_thinking: bool = False
    show_memories: bool = False

    # ── Idioma ─────────────────────────────────
    language: str = "en"  # default; on_load lo actualiza desde disco

    # ── Voz ────────────────────────────────────
    tts_enabled: bool = False
    elevenlabs_key: str = ""     # para TTS premium (opcional)
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # "Sarah" — fallback si no hay config
    voice_mode: bool = False     # True = Ashley habla natural (sin *gestos*)

    # ── LLM Provider (multi-provider) ──────────
    # llm_provider = "xai" (default, legacy) | "openrouter"
    # openrouter_key = la API key de OpenRouter si se usa ese provider
    # llm_model = modelo específico (vacío = default del provider)
    llm_provider: str = "xai"
    openrouter_key: str = ""
    llm_model: str = ""

    # ── Notificaciones Windows (cuando la ventana está minimizada) ──────
    notifications_enabled: bool = True
    # Pin on top: cuando ON, la ventana se mantiene encima de todo (útil
    # para que cuando Ashley abre una app no se tape a sí misma). Lee el
    # wrapper Electron via data-pin en #ashley-voice-state.
    pin_on_top: bool = False
    # Flag interno para anti-spam de mensajes de ausencia: True si Ashley
    # ya dejó un mensaje proactivo sobre la ausencia actual. Se resetea
    # cuando el user escribe. No se persiste — es solo de sesión.
    _absence_message_sent: bool = False

    # ── Afecto (relationship meter) ───────────
    affection: int = 50  # 0-100, default 50

    # ── Settings dialog ───────────────────────
    show_settings: bool = False

    # ── Imagen adjunta ────────────────────────
    pending_image: str = ""
    pending_image_name: str = ""

    # ── Mood / imagen dinámica ────────────────
    mood: str = "default"

    # ── Modo de acciones ──────────────────────────────────
    auto_actions: bool = False
    # ── Flag de sesión para música ────────────────────────
    browser_opened: bool = False
    # ── Focus mode (oculta panel derecho) ─────────────────
    focus_mode: bool = False

    # ── Acción pendiente (solo en modo manual futuro / debug) ─────
    pending_action_type: str = ""
    pending_action_params: list[str] = []
    pending_action_description: str = ""
    show_action_dialog: bool = False

    # ── Contadores internos ───────────────────
    new_messages_count: int = 0
    _last_response: str = ""
    _last_user_message: str = ""

    # ── Achievements ─────────────────────────
    achievement_toast_name: str = ""   # nombre del logro
    achievement_toast_desc: str = ""   # descripción del logro
    achievement_toast_icon: str = ""   # icon emoji
    achievements_data: dict[str, dict] = {}  # persisted unlock data for gallery

    # ── Discovery background task ─────────────
    _bg_discovery_running: bool = False

    # ── License gate ──────────────────────────
    # Default: calculado en base al disco vía _license_needed_default(), para
    # evitar el flash gate→chat en usuarios con licencia cacheada.
    # on_load revalida contra LS y corrige si la key fue revocada server-side.
    license_needed: bool = _license_needed_default()
    license_error: str = ""
    license_submitting: bool = False
    license_offline_grace: bool = False  # True si arrancamos sin red, mostrar banner

    # ── Usage stats (para la política de reembolso "14 días / 40 mensajes") ──
    # Persistidos en stats_ashley.json con firma HMAC + mirror en Windows Registry.
    # Ver stats.py para detalles de la protección anti-tampering.
    stats_total_messages: int = 0
    stats_tampered: bool = False

    # ─────────────────────────────────────────
    #  Computed vars
    # ─────────────────────────────────────────

    @rx.var
    def affection_pct(self) -> str:
        """Porcentaje de afecto para CSS height."""
        return f"{self.affection}%"

    @rx.var
    def affection_color(self) -> str:
        """Color del agua según nivel de afecto."""
        a = self.affection
        if a < 20: return "#6488ff"      # frío azul
        if a < 40: return "#88aaff"      # azul claro
        if a < 60: return "#cc88ff"      # púrpura (transición)
        if a < 80: return "#ff88cc"      # rosa cálido
        return "#ff66aa"                  # rosa intenso con amor

    @rx.var
    def current_image(self) -> str:
        """Imagen de Ashley según su estado actual."""
        if self.is_thinking:
            m = "thinking"
        elif self.current_response != "":
            m = "writing"
        else:
            m = self.mood
        valid = {
            "default", "thinking", "searching", "writing",
            "excited", "embarrassed", "tsundere", "soft",
            "surprised", "proud",
        }
        return f"/ashley_{m if m in valid else 'default'}.jpg"

    @rx.var
    def mood_overlay_color(self) -> str:
        """Color de overlay del fondo según el humor de Ashley."""
        colors = {
            "excited":     "rgba(255,210,60,0.045)",
            "embarrassed": "rgba(255,80,130,0.045)",
            "tsundere":    "rgba(80,110,255,0.04)",
            "soft":        "rgba(255,154,238,0.06)",
            "surprised":   "rgba(80,255,190,0.04)",
            "proud":       "rgba(255,185,60,0.045)",
        }
        return colors.get(self.mood, "rgba(0,0,0,0)")

    @rx.var
    def t(self) -> dict[str, str]:
        """Diccionario de traducciones del UI para el idioma actual.
        Uso en componentes: State.t["key"] (reactivo a self.language)."""
        return i18n.ui(self.language)

    @rx.var
    def is_english(self) -> bool:
        return self.language == "en"

    @rx.var
    def language_label(self) -> str:
        """Etiqueta del toggle de idioma — código en mayúsculas del idioma actual."""
        return (self.language or "en").upper()

    # Dependencias declaradas explícitamente: Reflex no puede inferirlas
    # porque el import de .achievements ocurre dentro del cuerpo y su
    # analyzer estático falla con módulos locales. Con deps= le decimos
    # exactamente de qué state vars depende la computed var.
    @rx.var(auto_deps=False, deps=["achievements_data", "language"])
    def achievements_gallery(self) -> list[dict[str, str]]:
        """All achievements as a flat list for the gallery. Each has
        icon, name, desc, unlocked ('true'/'false'), and date.

        Lee del disco directamente en vez de depender sólo de
        self.achievements_data: el tipo dict[str, dict] de Reflex tenía
        edge cases donde la UI mostraba como "locked" logros ya
        persistidos. La galería se consulta poco, el coste es un read
        de JSON < 1KB."""
        from .achievements import ACHIEVEMENTS, load_achievements
        lang = self.language if self.language in ("en", "es") else "en"
        # Fuente de verdad: disco. Fallback al state en memoria por si el
        # read falla (ej. permisos transitorios).
        try:
            fresh = load_achievements()
        except Exception:
            fresh = self.achievements_data or {}
        result = []
        for a in ACHIEVEMENTS:
            aid = a["id"]
            info = fresh.get(aid, {})
            unlocked = bool(info.get("unlocked"))
            date_str = ""
            if unlocked and info.get("unlocked_at"):
                try:
                    date_str = info["unlocked_at"][:10]  # YYYY-MM-DD
                except Exception:
                    date_str = ""
            result.append({
                "icon": a["icon"],
                "name": a.get(f"name_{lang}", a.get("name_en", "")),
                "desc": a.get(f"desc_{lang}", a.get("desc_en", "")),
                "unlocked": "true" if unlocked else "false",
                "date": date_str,
            })
        return result

    def toggle_language(self):
        """Cicla entre los idiomas soportados (EN → ES → FR → EN) y persiste.

        Usamos SUPPORTED como fuente de verdad: si mañana añadimos DE, aparece
        automáticamente en el ciclo sin tocar este método.
        """
        try:
            idx = i18n.SUPPORTED.index(self.language)
        except ValueError:
            idx = -1  # idioma desconocido → siguiente es SUPPORTED[0]
        new_lang = i18n.SUPPORTED[(idx + 1) % len(i18n.SUPPORTED)]
        self.language = new_lang
        i18n.save_language(new_lang)

    def set_language(self, lang: str):
        lang = i18n.normalize_lang(lang)
        self.language = lang
        i18n.save_language(lang)

    # ── Voz ─────────────────────────────────────────────────
    def _persist_voice(self):
        # vision_enabled se unificó bajo auto_actions — ya no vive en voice.json.
        # El campo queda en los archivos antiguos y simplemente se ignora.
        i18n.save_voice_config(
            self.tts_enabled, self.elevenlabs_key, self.voice_id,
            voice_mode=self.voice_mode,
            notifications_enabled=self.notifications_enabled,
            llm_provider=self.llm_provider,
            openrouter_key=self.openrouter_key,
            llm_model=self.llm_model,
        )

    def toggle_tts(self):
        """Activa o desactiva que Ashley hable en voz alta."""
        self.tts_enabled = not self.tts_enabled
        self._persist_voice()

    def toggle_voice_mode(self):
        """Alterna modo natural: cuando ON, Ashley responde sin *gestos*."""
        self.voice_mode = not self.voice_mode
        self._persist_voice()

    def toggle_notifications(self):
        """Activa o desactiva las notificaciones de Windows cuando la
        ventana de Ashley no está focuseada."""
        self.notifications_enabled = not self.notifications_enabled
        self._persist_voice()

    def toggle_pin_on_top(self):
        """Alterna always-on-top: cuando ON, la ventana de Ashley se mantiene
        encima de cualquier otra ventana. El cambio se aplica en el wrapper
        Electron via MutationObserver sobre data-pin."""
        self.pin_on_top = not self.pin_on_top

    def set_elevenlabs_key(self, key: str):
        self.elevenlabs_key = (key or "").strip()
        self._persist_voice()

    def set_voice_id(self, voice_id: str):
        self.voice_id = (voice_id or "").strip() or "EXAVITQu4vr4xnSDxMaL"
        self._persist_voice()

    # ─────────────────────────────────────────
    #  LLM Provider handlers (multi-provider)
    # ─────────────────────────────────────────

    def set_llm_provider(self, provider: str):
        """'xai' | 'openrouter'. Cambia qué servicio usa Ashley."""
        p = (provider or "xai").strip().lower()
        if p not in ("xai", "openrouter"):
            p = "xai"
        self.llm_provider = p
        # Al cambiar de provider, resetear el modelo para que use el default
        # del nuevo provider — evita intentar usar un modelo de xAI contra
        # OpenRouter o viceversa.
        self.llm_model = ""
        self._persist_voice()

    def set_openrouter_key(self, key: str):
        self.openrouter_key = (key or "").strip()
        self._persist_voice()

    def set_llm_model(self, model: str):
        """Modelo específico (debe corresponderse al provider activo)."""
        self.llm_model = (model or "").strip()
        self._persist_voice()

    @rx.var
    def llm_model_display(self) -> str:
        """Modelo actual para mostrar en UI (muestra default si está vacío)."""
        from .llm_provider import XAI_MODELS, OPENROUTER_MODELS
        if self.llm_model:
            return self.llm_model
        if self.llm_provider == "openrouter":
            return OPENROUTER_MODELS[0][0] + " (default)"
        return XAI_MODELS[0][0] + " (default)"

    @rx.var
    def is_openrouter_provider(self) -> bool:
        return self.llm_provider == "openrouter"

    @rx.var
    def tts_marker_attr(self) -> str:
        """'on' | 'off' — lo lee ashley_voice.js desde data-tts."""
        return "on" if self.tts_enabled else "off"

    @rx.var
    def notifications_marker_attr(self) -> str:
        """'on' | 'off' — lo lee ashley_fx.js desde data-notifications
        para decidir si disparar notificaciones Windows cuando la ventana
        no está focuseada."""
        return "on" if self.notifications_enabled else "off"

    @rx.var
    def pin_marker_attr(self) -> str:
        """'on' | 'off' — lo lee ashley_fx.js desde data-pin para llamar a
        window.ashleyWindow.setAlwaysOnTop() en el main process."""
        return "on" if self.pin_on_top else "off"

    @rx.var(cache=False)
    def backend_port_marker(self) -> str:
        """Puerto del backend Python (Starlette) donde viven las rutas /api/*.
        Es DISTINTO del frontend port (Next.js). El JS lo usa para hacer
        fetch directo al backend en vez de al frontend (que devuelve 405)."""
        import os as _os
        return _os.environ.get("ASHLEY_BACKEND_PORT", "17801")

    @rx.var(cache=False)
    def grok_key_status(self) -> str:
        """Indicador en Settings de si hay Grok key configurada.
        No depende de state reactivo — se evalúa on demand."""
        from . import config as _cfg
        return "configured" if (_cfg.XAI_API_KEY and len(_cfg.XAI_API_KEY) > 10) else "missing"

    # ── Settings dialog ─────────────────────────────────────
    def toggle_settings(self):
        self.show_settings = not self.show_settings

    def save_voice_settings(self, form_data: dict):
        """Guarda cambios desde el modal de settings."""
        if "elevenlabs_key" in form_data:
            self.elevenlabs_key = (form_data.get("elevenlabs_key") or "").strip()
        if "voice_id" in form_data:
            self.voice_id = (form_data.get("voice_id") or "").strip() or "EXAVITQu4vr4xnSDxMaL"
        self._persist_voice()
        self.show_settings = False

    # ── License gate ─────────────────────────────────────────
    def submit_license(self, form_data: dict):
        """Valida y activa la license key que tecleó el user en el gate.

        Si la activación es OK: persiste, quita el gate y dispara el on_load
        normal para cargar historial/facts/etc. (que nos saltamos en on_load
        cuando license_needed=True).
        Si falla: enseña el error friendly y deja el gate visible.
        """
        raw_key = (form_data.get("license_key") or "").strip()
        if not raw_key:
            self.license_error = self.t["license_error_invalid"]
            return

        self.license_submitting = True
        self.license_error = ""
        yield  # refresca UI para mostrar spinner

        from . import license as lic
        try:
            ok, friendly_msg = lic.activate_and_store(raw_key)
        except ConnectionError:
            self.license_submitting = False
            self.license_error = self.t["license_error_network"]
            return
        except Exception as e:
            import logging
            logging.getLogger("ashley").error("license activate crashed: %s", e)
            self.license_submitting = False
            self.license_error = self.t["license_error_invalid"]
            return

        if not ok:
            self.license_submitting = False
            self.license_error = friendly_msg or self.t["license_error_invalid"]
            return

        # ¡Activación OK! Desbloqueamos la UI y disparamos el resto del
        # on_load que nos saltamos antes (cargar historial, achievements,
        # tastes, diary, etc.).
        self.license_needed = False
        self.license_submitting = False
        self.license_error = ""
        self.license_offline_grace = False
        # Cargar todo lo que nos saltamos cuando el gate estaba activo.
        yield from self.on_load()

    # ─────────────────────────────────────────
    #  Carga inicial
    # ─────────────────────────────────────────

    def on_load(self):
        # ── Migraciones de schema (PRIMERO, antes de cualquier load) ──
        # Si la app vio un formato de datos anterior, aquí lo actualizamos.
        # migrate_if_needed es idempotente — en fresh install o al día, es no-op.
        try:
            from .migrations import migrate_if_needed
            migrate_if_needed()
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("migrations failed: %s", _e)
            # Seguimos arrancando — datos viejos son mejor que no arrancar.

        # ── License gate ──────────────────────────────────────────
        # Solo si el feature flag está activo. Si valida → license_needed=False
        # y seguimos cargando normal. Si no valida → license_needed=True y
        # cortocircuitamos el resto del on_load (no tiene sentido cargar
        # historial ni warmup de whisper si el user no está autenticado).
        if LICENSE_CHECK_ENABLED:
            from . import license as lic
            ok, reason = lic.ensure_valid_on_startup()
            self.license_needed = not ok
            self.license_offline_grace = (reason == "offline_grace")
            if not ok:
                # Nada más que hacer — el gate está pintando y el user
                # tiene que meter su key antes de continuar.
                return
        else:
            self.license_needed = False

        self.browser_opened = False
        # Cargar idioma persistido (default: EN)
        self.language = i18n.load_language()
        # Cargar config de voz persistida
        vcfg = i18n.load_voice_config()
        self.tts_enabled = vcfg["tts_enabled"]
        self.elevenlabs_key = vcfg["elevenlabs_key"]
        self.voice_id = vcfg["voice_id"]
        self.voice_mode = vcfg.get("voice_mode", False)
        # notifications: default True si no está en config (feature nueva)
        self.notifications_enabled = vcfg.get("notifications_enabled", True)
        # LLM provider config (feature nueva — default xai por retrocompat)
        self.llm_provider = vcfg.get("llm_provider", "xai") or "xai"
        self.openrouter_key = vcfg.get("openrouter_key", "") or ""
        self.llm_model = vcfg.get("llm_model", "") or ""
        # NOTE: vision_enabled ya no existe — ahora va unificado bajo auto_actions.
        # Si voice.json viejo trae la key, la ignoramos silenciosamente.
        # Warmup del modelo Whisper en background (no bloquea la UI)
        try:
            from .whisper_stt import warmup as whisper_warmup
            whisper_warmup()
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("warming up whisper: %s", _e)
        from .actions import reset_youtube_hwnd
        reset_youtube_hwnd()
        raw_messages = load_json(CHAT_FILE, [])
        self.messages = ensure_ids(raw_messages[-MAX_HISTORY_MESSAGES:])

        # ── First-run welcome message ────────────
        if len(self.messages) == 0:
            self._append_welcome_message()

        self.facts = ensure_facts(load_json(FACTS_FILE, []))
        diary_data = load_json(DIARY_FILE, {"entries": [], "last_diary_at": ""})
        self.diary = diary_data.get("entries", [])
        from .tastes import load_tastes
        self.tastes = load_tastes()
        self._load_affection()
        # Load achievements
        from .achievements import load_achievements
        self.achievements_data = load_achievements()
        # Load usage stats (contador de mensajes + detección de tampering).
        self._reload_stats_into_state()
        if not self.facts and self.messages:
            self._initial_fact_extraction()
        self._maybe_create_diary_entry()
        yield
        # Proactive discovery
        from .tastes import should_run_discovery, update_discovery_time
        if self.tastes and should_run_discovery():
            update_discovery_time()
            self.is_thinking = True
            yield
            try:
                yield from self._stream_discovery()
                dc_text = self._last_response
                dc_clean, dc_mood = self._extract_mood(dc_text)
                dc_clean, dc_aff = self._extract_affection(dc_clean)
                dc_clean, dc_action = self._extract_action(dc_clean)
                self._apply_affection_delta(dc_aff)
                if len(dc_clean.strip()) > 10:
                    self.mood = dc_mood
                    self.current_response = ""
                    ts = now_iso()
                    self.messages.append({"role": "assistant", "content": dc_clean, "timestamp": ts, "id": f"d-{ts}", "image": ""})
                    if dc_action and (self.auto_actions or dc_action["type"] in _SAFE_ACTIONS):
                        self._execute_and_record_action(dc_action)
                    else:
                        self.save_history()
                else:
                    self.mood = dc_mood
                    self.current_response = ""
                    self.is_thinking = False
            except Exception as e:
                self._handle_grok_error(e, "discovery")
            yield

        # Arrancar el background task de discovery (si no está ya corriendo)
        yield State.start_discovery_bg_task()

    def _append_welcome_message(self):
        """Append the first-run onboarding message from Ashley."""
        _WELCOME_ES = (
            "Hola, jefe. Soy Ashley, tu secretaria personal.\n\n"
            "Antes de que empecemos \u2014 cu\u00e9ntame un poco de ti. "
            "\u00bfC\u00f3mo te llamas? \u00bfQu\u00e9 te gusta hacer? "
            "\u00bfEn qu\u00e9 trabajas o estudias?\n\n"
            "As\u00ed me acuerdo para siempre y no tendr\u00e1s que repetirme las cosas. "
            "Ah, y por cierto... puedo hacer m\u00e1s de lo que crees. "
            "Abrir apps, cerrar pesta\u00f1as, buscar cosas en internet, "
            "recordarte cosas, escucharte por voz... solo tienes que pedirlo.\n\n"
            "Pero primero \u2014 pres\u00e9ntate, anda. No muerdo. Casi nunca."
        )
        _WELCOME_EN = (
            "Hey, boss. I'm Ashley, your personal secretary.\n\n"
            "Before we start \u2014 tell me a bit about yourself. "
            "What's your name? What are you into? "
            "What do you do for work or school?\n\n"
            "That way I'll remember forever and you won't have to repeat yourself. "
            "Oh, and by the way... I can do more than you think. "
            "Open apps, close tabs, search the web, remind you of things, "
            "listen to your voice... just ask.\n\n"
            "But first \u2014 introduce yourself. I don't bite. Usually."
        )
        content = _WELCOME_ES if self.language == "es" else _WELCOME_EN
        ts = now_iso()
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": ts,
            "id": f"w-{ts}",
            "image": "",
        })
        self.mood = "tsundere"
        self.save_history()

    def _initial_fact_extraction(self):
        new_facts = extract_facts(self.messages, [])
        if new_facts:
            self.facts = new_facts
            save_json(FACTS_FILE, self.facts)

    def _maybe_create_diary_entry(self):
        last_ts_str = None
        for msg in reversed(self.messages):
            if msg.get("timestamp"):
                last_ts_str = msg["timestamp"]
                break

        if not last_ts_str:
            return

        try:
            last_time = datetime.fromisoformat(last_ts_str)
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("parsing last timestamp for diary: %s", _e)
            return

        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if (now - last_time).total_seconds() / 60 < SESSION_TIMEOUT_MINUTES:
            return

        diary_data = load_json(DIARY_FILE, {"entries": [], "last_diary_at": ""})
        last_diary_at = diary_data.get("last_diary_at", "")
        if last_diary_at and last_diary_at >= last_ts_str:
            return

        fecha = last_time.strftime("%Y-%m-%d")
        resumen = generate_diary_entry(self.messages, fecha)
        entry = {"fecha": fecha, "resumen": resumen}
        self.diary.append(entry)

        save_json(DIARY_FILE, {"entries": self.diary, "last_diary_at": last_ts_str})

    # ─────────────────────────────────────────
    #  Persistencia
    # ─────────────────────────────────────────

    def save_history(self):
        # Screenshots son muy grandes para disco — se guardan sin imagen
        saveable = [
            {**m, "image": ""} if m.get("role") == "system_result" else m
            for m in self.messages
        ]
        save_json(CHAT_FILE, saveable)

    # ─────────────────────────────────────────
    #  Error handling centralizado
    # ─────────────────────────────────────────

    def _handle_grok_error(self, e: Exception, context: str = ""):
        """Resetea el estado de streaming y añade mensaje de error al chat."""
        label = f" ({context})" if context else ""
        print(f"[Grok Error{label}] {e}")
        self.is_thinking = False
        self.current_response = ""
        ts = now_iso()
        err_template = i18n.ui(self.language)["error_grok"]
        self.messages.append({
            "role": "assistant",
            "content": err_template.format(label=label, err=str(e)),
            "timestamp": ts, "id": f"e-{ts}", "image": "",
        })

    # ─────────────────────────────────────────
    #  Extracción de hechos
    # ─────────────────────────────────────────

    def _apply_new_facts(self, new_facts: list[dict]):
        """
        Aplica nuevos hechos al estado:
        - Elimina los hechos que el extractor marca con 'reemplaza'
        - Añade los nuevos
        - Si se supera MAX_FACTS, poda por importancia (permanentes > temporales, mayor importancia primero)
        """
        for fact in new_facts:
            reemplaza = fact.pop("reemplaza", None)
            if reemplaza:
                self.facts = [f for f in self.facts if f.get("hecho") != reemplaza]

        self.facts = self.facts + new_facts

        if len(self.facts) > MAX_FACTS:
            def sort_key(f):
                es_permanente = f.get("relevancia") == "permanente"
                importancia = int(f.get("importancia", "5"))
                return (not es_permanente, -importancia)
            self.facts = sorted(self.facts, key=sort_key)[:MAX_FACTS]

        save_json(FACTS_FILE, self.facts)

    def _maybe_extract_facts(self):
        if self.new_messages_count < MESSAGES_PER_EXTRACTION:
            return

        self.new_messages_count = 0
        batch = self.messages[-MESSAGES_PER_EXTRACTION:]
        new_facts = extract_facts(batch, self.facts)

        if new_facts:
            self._apply_new_facts(new_facts)

    def _reextract_facts(self):
        if not self.messages:
            self.facts = []
            save_json(FACTS_FILE, self.facts)
            return
        new_facts = extract_facts(self.messages, [])
        self.facts = []
        if new_facts:
            self._apply_new_facts(new_facts)
        else:
            save_json(FACTS_FILE, self.facts)

    # ─────────────────────────────────────────
    #  Mood helpers
    # ─────────────────────────────────────────

    def _clean_display(self, text: str) -> str:
        """Elimina tags [mood:...] y [action:...] del texto para mostrarlo al usuario."""
        return _clean_display_fn(text)

    def _extract_mood(self, text: str) -> tuple[str, str]:
        """
        Busca [mood:xxx] en el texto.
        Devuelve (texto_limpio, mood_detectado).
        Si no hay tag devuelve (texto_original, "default").
        """
        return _extract_mood_fn(text)

    def _extract_action(self, text: str) -> tuple[str, dict | None]:
        """
        Busca [action:tipo:...] en el texto.
        Devuelve (texto_limpio, {type, params, description} | None).
        Delegates to parsing.extract_action and adds the description.
        """
        clean, action = _extract_action_fn(text)
        if action is not None:
            from .actions import describe_action
            action["description"] = describe_action(
                action["type"], action["params"], lang=self.language,
            )
        return clean, action

    def _extract_affection(self, text: str) -> tuple[str, int]:
        """
        Busca [affection:+N] o [affection:-N] en el texto.
        Devuelve (texto_limpio, delta). Delta se limita a [-3, +3].
        """
        return _extract_affection_fn(text)

    def _apply_affection_delta(self, delta: int):
        """Apply an affection delta and persist."""
        if delta != 0:
            self.affection = max(0, min(100, self.affection + delta))
            self._save_affection()

    # ─────────────────────────────────────────
    #  Affection persistence
    # ─────────────────────────────────────────

    def _load_affection(self):
        try:
            data = load_json(AFFECTION_FILE, {"level": 50})
            self.affection = max(0, min(100, int(data.get("level", 50))))
        except Exception:
            self.affection = 50

    def _save_affection(self):
        save_json(AFFECTION_FILE, {"level": self.affection})

    # ─────────────────────────────────────────
    #  Usage stats (contador de mensajes para refund policy)
    # ─────────────────────────────────────────

    def _reload_stats_into_state(self):
        """Carga el contador persistente + flag de tampering al state reactivo.

        Además del HMAC + registry mirror de stats.py, hacemos un cross-check
        contra el historial: si el chat file tiene MÁS mensajes del usuario
        de los que el contador reporta, hay tampering.

        EXCEPCIÓN (grandfather-in): si el mensaje más viejo del chat es
        anterior a cuando empezó a contar el counter, la discrepancia es
        legítima (la feature se añadió a posteriori).
        """
        try:
            from . import stats as _stats
            data = _stats.load_stats()

            # Contamos SOLO los mensajes con role=='user' — el contador también
            # cuenta solo esos. Comparar totales del historial (user + assistant
            # + system_result) era el bug original: cualquier conversación
            # normal daba falsos positivos de tampering porque las respuestas
            # de Ashley infladan el historial sin sumar al contador.
            user_msg_count = sum(1 for m in self.messages if m.get("role") == "user")

            oldest_ts = None
            if self.messages:
                candidates = [m.get("timestamp") for m in self.messages if m.get("timestamp")]
                if candidates:
                    oldest_ts = min(candidates)

            if _stats.is_tampered_vs_history(
                total_messages=data.get("total_user_messages", 0),
                user_history_count=user_msg_count,
                counter_started_at=data.get("first_message_at"),
                oldest_history_ts=oldest_ts,
            ):
                data["_tampered"] = True

            self.stats_total_messages = int(data.get("total_user_messages", 0))
            self.stats_tampered = bool(data.get("_tampered", False))
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("could not load stats: %s", _e)
            # Failsafe: nunca dejar que un fallo aquí rompa el arranque.
            self.stats_total_messages = 0
            self.stats_tampered = False

    def _increment_message_counter(self):
        """Incrementa el contador tras cada 'Send' del user y refleja al state."""
        try:
            from . import stats as _stats
            result = _stats.increment_message_counter()
            self.stats_total_messages = int(result.get("total_user_messages", 0))
            self.stats_tampered = bool(result.get("_tampered", False))
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("stats increment failed: %s", _e)

    # ─────────────────────────────────────────
    #  Achievements
    # ─────────────────────────────────────────

    def clear_achievement_toast(self):
        """Dismiss the achievement notification."""
        self.achievement_toast_name = ""
        self.achievement_toast_desc = ""
        self.achievement_toast_icon = ""

    def _check_achievements(self, executed_action: bool = False):
        """Run achievement checks and show toast for the first newly unlocked one."""
        from .achievements import check_achievements, load_achievements

        user_msg_count = len([m for m in self.messages if m.get("role") == "user"])
        newly = check_achievements(
            affection=self.affection,
            message_count=user_msg_count,
            facts_count=len(self.facts),
            # "She Sees" se gana ahora cuando el user activa el awareness del PC
            # (auto_actions), que es el toggle que le permite ver la pantalla.
            vision_enabled=self.auto_actions,
            used_mic=False,
            executed_action=executed_action,
        )
        if newly:
            a = newly[0]  # show first unlocked (if multiple at once)
            lang_key = self.language if self.language in ("en", "es") else "en"
            name = a.get(f"name_{lang_key}", a.get("name_en", ""))
            desc = a.get(f"desc_{lang_key}", a.get("desc_en", ""))
            self.achievement_toast_name = f"{a['icon']} {name}"
            self.achievement_toast_desc = desc
            self.achievement_toast_icon = a["icon"]
        # Refresh gallery data
        self.achievements_data = load_achievements()

    # ─────────────────────────────────────────
    #  Action execution helper
    # ─────────────────────────────────────────

    def _execute_and_record_action(self, action_dict, lang=None):
        """Execute an action, update state, append a system_result message
        and save history.

        Returns the result dict from ``execute_action``.
        The caller is responsible for the ``_SAFE_ACTIONS`` guard — this
        helper simply executes whatever it receives.
        """
        from .actions import execute_action

        _lang = lang or self.language
        result = execute_action(
            action_dict["type"], action_dict["params"],
            browser_opened=self.browser_opened,
            lang=_lang,
        )
        self.browser_opened = result.get("browser_opened", self.browser_opened)

        if action_dict["type"] == "save_taste":
            from .tastes import load_tastes
            self.tastes = load_tastes()

        ts = now_iso()
        self.messages.append({
            "role": "system_result",
            "content": result["result"],
            "timestamp": ts,
            "id": f"sys-{ts}",
            "image": result.get("screenshot") or "",
        })
        self.save_history()
        return result

    # ─────────────────────────────────────────
    #  Streaming
    # ─────────────────────────────────────────

    def _streaming_loop(self, generator):
        """Shared streaming accumulation loop.

        Iterates *generator* (expected to yield text chunks), accumulates
        them, periodically updates ``self.current_response`` for the UI,
        and stores the full raw result in ``self._last_response``.
        """
        accumulated = ""
        chunk_count = 0
        empty_count = 0

        for text in generator:
            if not text:
                empty_count += 1
                if empty_count % 10 == 0:
                    yield
                continue

            if self.is_thinking:
                self.is_thinking = False

            accumulated += text
            chunk_count += 1

            if chunk_count % STREAM_CHUNK_SIZE == 0:
                self.current_response = self._clean_display(accumulated)
                yield

        self.current_response = self._clean_display(accumulated)
        self._last_response = accumulated
        yield

    def _build_prompt_context(self, user_message: str = "") -> dict:
        """Build the keyword-argument dict expected by ``build_system_prompt``.

        Consolidates the boilerplate that previously appeared before every
        ``build_system_prompt()`` call: time context, system state,
        reminders, important items, tastes, diary flag, voice mode, and
        language.
        """
        time_context = self._build_time_context()

        # ── Estado de capacidades activas (Ashley sabe qué puede/no puede hacer) ──
        # Actions es ahora el toggle maestro: controla tanto la ejecución de
        # acciones como el awareness del PC (ventanas, tabs, screenshots). Con
        # Actions OFF, Ashley solo ve la hora — cero info del PC del user.
        capabilities = []
        if self.language == "fr":
            capabilities.append("=== TES CAPACITÉS ACTIVES ===")
            # Extraemos las dos ramas a variables para evitar escape hell con los
            # apostrofes franceses dentro de f-strings entre comillas simples.
            actions_on_fr = (
                "ACTIVÉ — tu peux VOIR les fenêtres/onglets ouverts du patron, "
                "prendre des captures d'écran et agir sur son PC (ouvrir apps, "
                "fermer onglets, contrôler le volume, etc.)."
            )
            actions_off_fr = (
                "DÉSACTIVÉ — tu es AVEUGLE par rapport au PC du patron. Tu ne "
                "vois ni ses fenêtres, ni ses onglets, ni son écran. Tu ne peux "
                "rien faire sur son PC. Si le patron te demande d'ouvrir/fermer/"
                "voir quelque chose, dis-lui d'activer le toggle ⚡ Actions d'abord."
            )
            capabilities.append(
                "⚡ Actions (contrôle et conscience du PC) : "
                + (actions_on_fr if self.auto_actions else actions_off_fr)
            )
            capabilities.append(
                "🗣 Naturel (mode voix) : "
                + ("ACTIVÉ — pas de gestes, pur dialogue." if self.voice_mode
                   else "DÉSACTIVÉ — gestes entre *astérisques* actifs.")
            )
            capabilities.append(
                "🔊 TTS (voix) : " + ("ACTIVÉ" if self.tts_enabled else "DÉSACTIVÉ")
            )
            capabilities.append("")
            capabilities.append(
                "IMPORTANT : n'offre PAS de faire des choses que tu ne peux pas. "
                "Si Actions est DÉSACTIVÉ, ne dis pas \"je te l'ouvre\" — dis "
                "\"Active ⚡ Actions et je peux le faire\"."
            )
            capabilities.append(
                "N'offre PAS d'envoyer des messages, emails ou contacter des "
                "personnes — tu ne peux pas faire ça."
            )
            capabilities.append(
                "N'interprète PAS les notifications, popups ou petits textes "
                "d'UI d'une capture — si tu ne peux pas le lire avec 100% de "
                "certitude, NE le mentionne PAS. N'invente pas de noms, d'heures "
                "ni de messages que tu crois voir."
            )
        elif self.language == "en":
            capabilities.append("=== YOUR ACTIVE CAPABILITIES ===")
            capabilities.append(f"⚡ Actions (PC control & awareness): {'ON — you CAN see the boss open windows/tabs, take screenshots, and act on his PC (open apps, close tabs, control volume, etc.).' if self.auto_actions else 'OFF — you are BLIND to the boss PC. You cannot see his windows, tabs, or screen. You cannot control anything. If the boss asks you to open/close/see something, tell him to activate the ⚡ Actions toggle first.'}")
            capabilities.append(f"🗣 Natural (voice mode): {'ON — no gestures, pure dialogue.' if self.voice_mode else 'OFF — gestures between *asterisks* are active.'}")
            capabilities.append(f"🔊 TTS (voice output): {'ON' if self.tts_enabled else 'OFF'}")
            capabilities.append("")
            capabilities.append("IMPORTANT: Do NOT offer to do things you can't do. If Actions is OFF, don't say 'I'll open that for you' — say 'Activate ⚡ Actions and I can do that.'")
            capabilities.append("Do NOT offer to send messages, emails, or contact people — you cannot do that.")
            capabilities.append("Do NOT interpret notifications, popups, or small UI text from the screenshot — if you can't read it with 100% certainty, do NOT mention it. Don't invent names, times, or messages you 'think you see'.")
        else:  # es
            capabilities.append("=== TUS CAPACIDADES ACTIVAS ===")
            capabilities.append(f"⚡ Acciones (control y visión del PC): {'ACTIVADO — PUEDES ver las ventanas/pestañas que tiene abiertas el jefe, tomar capturas de pantalla y actuar en su PC (abrir apps, cerrar pestañas, controlar volumen, etc.).' if self.auto_actions else 'DESACTIVADO — estás CIEGA respecto al PC del jefe. No ves sus ventanas, ni sus pestañas, ni su pantalla. No puedes controlar nada. Si el jefe te pide abrir/cerrar/ver algo, dile que active el toggle ⚡ Acciones primero.'}")
            capabilities.append(f"🗣 Natural (modo voz): {'ACTIVADO — sin gestos, diálogo puro.' if self.voice_mode else 'DESACTIVADO — gestos entre *asteriscos* activos.'}")
            capabilities.append(f"🔊 TTS (voz): {'ACTIVADO' if self.tts_enabled else 'DESACTIVADO'}")
            capabilities.append("")
            capabilities.append("IMPORTANTE: NO ofrezcas hacer cosas que no puedes. Si Acciones está DESACTIVADO, no digas 'te lo abro' — di 'Activa ⚡ Acciones y puedo hacerlo.'")
            capabilities.append("NO ofrezcas enviar mensajes, emails ni contactar a personas — no puedes hacer eso.")
            capabilities.append("NO interpretes notificaciones, popups ni texto pequeño del screenshot — si no puedes leerlo con 100% de certeza, NO lo menciones. No inventes nombres, tiempos ni mensajes que 'crees ver'.")

        system_state: str | None = None
        if self.auto_actions:
            try:
                from .actions import get_system_state
                system_state = "\n".join(capabilities) + "\n\n" + get_system_state()
            except Exception as _e:
                import logging
                logging.getLogger("ashley").warning("getting system state: %s", _e)
                system_state = "\n".join(capabilities)
        else:
            system_state = "\n".join(capabilities)

        reminders: str | None = None
        important: str | None = None
        try:
            from .reminders import (
                load_reminders, load_important,
                format_reminders_for_prompt, format_important_for_prompt,
            )
            r = format_reminders_for_prompt(load_reminders())
            i = format_important_for_prompt(load_important())
            if r:
                reminders = r
            if i:
                important = i
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("loading reminders: %s", _e)

        tastes: str | None = None
        try:
            from .tastes import format_tastes_for_prompt
            t = format_tastes_for_prompt(self.tastes)
            if t:
                tastes = t
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("loading tastes: %s", _e)

        # Directiva de compartir-tema: si el user acaba de compartir algo
        # sustancial (≥30 chars), se inyecta un bloque de alta prioridad
        # forzando a Ashley a tomar postura propia con razón. Mecanismo
        # runtime — vence a la inercia del eco-elaborado.
        topic_directive = None
        if user_message:
            try:
                from .topic_share import compute_directive_if_needed
                topic_directive = compute_directive_if_needed(user_message, self.language)
            except Exception as _e:
                import logging
                logging.getLogger("ashley").warning("topic_share detection failed: %s", _e)

        return {
            "time_context": time_context,
            "system_state": system_state,
            "reminders": reminders,
            "important": important,
            "tastes": tastes,
            "use_full_diary": is_diary_query(user_message) if user_message else False,
            "voice_mode": self.voice_mode,
            "affection": self.affection,
            "lang": self.language,
            "recap_warning": self._detect_recap_warning(),
            "mental_state_block": self._compute_mental_state_block(user_message),
            "topic_directive": topic_directive,
        }

    def _detect_recap_warning(self) -> str | None:
        """
        Detecta si Ashley lleva repitiendo el mismo tema en sus últimos
        mensajes (patrón recap-tic) y devuelve un bloque de aviso para
        inyectar al prompt. None si no detecta el patrón.

        Es un mecanismo runtime que vence al in-context learning del
        historial — sin esto, una vez que Ashley empieza a repetir un
        tema lo reproduce en todos los mensajes aunque el prompt lo
        prohíba. La instrucción dinámica con las palabras concretas
        pisa la inercia.
        """
        try:
            from .recap_detector import detect_recap_topics, format_recap_warning
            msgs = [
                {"role": m.get("role"), "content": m.get("content") or ""}
                for m in self.messages
            ]
            repeated = detect_recap_topics(msgs)
            if not repeated:
                return None
            return format_recap_warning(repeated, self.language)
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("recap detector failed: %s", _e)
            return None

    def _minutes_since_previous_user_msg(self) -> float | None:
        """Devuelve cuántos minutos han pasado entre el mensaje del user
        actual (el último en self.messages) y el anterior del user.
        None si no hay mensaje anterior o timestamps inválidos.
        """
        if len(self.messages) < 2:
            return None
        try:
            current_ts = self.messages[-1].get("timestamp")
            if not current_ts:
                return None
            cur = datetime.fromisoformat(current_ts)
            for m in reversed(self.messages[:-1]):
                if m.get("role") == "user":
                    prev_ts = m.get("timestamp")
                    if not prev_ts:
                        return None
                    prev = datetime.fromisoformat(prev_ts)
                    return max(0.0, (cur - prev).total_seconds() / 60.0)
            return None
        except Exception:
            return None

    def _compute_mental_state_block(self, user_message: str) -> str | None:
        """Actualiza el estado mental persistente de Ashley y devuelve el
        bloque de prompt a inyectar.

        Si se llama con user_message no vacío → update completo (events,
        mood, maybe regen preoccupation, tick initiative counter).
        Si se llama sin user_message (initiative/discovery) → solo lee +
        regenera preoccupation si está vieja, sin tocar mood ni counter.

        Fail-safe: cualquier error devuelve None y se loguea. Nunca
        bloquea el flujo principal.
        """
        try:
            from . import mental_state as _ms
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("mental_state import failed: %s", _e)
            return None

        try:
            state = _ms.load_state()
            minutes_since = self._minutes_since_previous_user_msg() if user_message else None
            initiative_due = False

            if user_message:
                # Reconciliación de gap largo (drift del mood hacia neutral)
                if minutes_since is not None and minutes_since >= _ms.LONG_GAP_MINUTES:
                    _ms.drift_mood_on_gap(state, minutes_since)

                # Eventos del user → delta de mood
                events = _ms.classify_user_event(user_message, minutes_since)
                _ms.apply_events_to_mood(state, events)

                # Regenerar preoccupation si está vieja o hay gap
                if _ms.should_regenerate_preoccupation(state) or (
                    minutes_since is not None and minutes_since >= _ms.LONG_GAP_MINUTES
                ):
                    gap_ctx = _ms.compute_gap_context(minutes_since, self.language)
                    _ms.regenerate_preoccupation(
                        state, self.messages, self.facts, self.language, gap_ctx
                    )

                # Contador de iniciativa
                initiative_due = _ms.tick_initiative_counter(state)
            else:
                # Read-only path: solo asegurar que la preoccupation no esté
                # ancestral. No tocar mood ni counter.
                if _ms.should_regenerate_preoccupation(state):
                    _ms.regenerate_preoccupation(
                        state, self.messages, self.facts, self.language, None
                    )

            state["last_update"] = datetime.now().isoformat()
            _ms.save_state(state)
            return _ms.format_mental_state_block(state, self.language, initiative_due)
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("mental state compute failed: %s", _e)
            return None

    def _build_time_context(self) -> str:
        """
        Calcula el contexto temporal: hora actual, última vez que habló el jefe,
        y cuánto tiempo ha pasado. Se traduce al idioma activo para que coincida
        con la personalidad de Ashley.
        """
        T = i18n.time_ctx(self.language)

        now = datetime.now(timezone.utc)
        now_local = datetime.now()
        hora = now_local.hour

        if 6 <= hora < 12:
            momento_dia = T["part_morning"]
        elif 12 <= hora < 15:
            momento_dia = T["part_afternoon"] if self.language == "en" else "mediodía"
        elif 15 <= hora < 21:
            momento_dia = T["part_afternoon"] if self.language == "en" else T["part_afternoon"]
        elif 21 <= hora < 24:
            momento_dia = T["part_night"]
        else:
            momento_dia = T["part_dawn"]

        hora_str = now_local.strftime("%H:%M")
        fecha_str = now_local.strftime(T["date_format"])
        # Traducir días y meses
        for en, loc in {**T["days"], **T["months"]}.items():
            fecha_str = fecha_str.replace(en, loc)

        # Buscar el timestamp del mensaje más reciente del jefe (excluyendo el actual)
        last_user_ts: str | None = None
        user_msgs = [m for m in self.messages if m.get("role") == "user" and m.get("timestamp")]
        if len(user_msgs) >= 2:
            last_user_ts = user_msgs[-2]["timestamp"]
        elif len(user_msgs) == 1:
            last_user_ts = None

        lines = [T["datetime_line"].format(fecha=fecha_str, hora=hora_str, momento=momento_dia)]

        if last_user_ts:
            try:
                last_dt = datetime.fromisoformat(last_user_ts)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                gap_secs = (now - last_dt).total_seconds()
                gap_min  = int(gap_secs // 60)
                gap_hrs  = gap_secs / 3600

                if gap_min < 2:
                    lines.append(T["active_convo"])
                elif gap_min < 10:
                    lines.append(T["short_pause"].format(min=gap_min))
                elif gap_min < 60:
                    lines.append(T["medium_away"].format(min=gap_min))
                elif gap_hrs < 3:
                    lines.append(T["hours_away"].format(h=gap_min // 60, m=gap_min % 60))
                elif gap_hrs < 6:
                    lines.append(T["long_away"].format(h=round(gap_hrs, 1)))
                else:
                    last_local_hora = last_dt.astimezone().hour
                    when_str = last_dt.astimezone().strftime('%H:%M')
                    if gap_hrs >= 5 and (22 <= last_local_hora or last_local_hora < 4):
                        lines.append(T["slept_away"].format(h=round(gap_hrs, 1), when=when_str, momento=momento_dia))
                    elif gap_hrs >= 6:
                        lines.append(T["very_long_away"].format(h=round(gap_hrs, 1), when=when_str))
            except Exception as _e:
                import logging
                logging.getLogger("ashley").warning("calculating time gap: %s", _e)
        else:
            lines.append(T["first_talk"])

        # Directiva de uso del tiempo — sutil, no obsesiva.
        if self.language == "en":
            lines.append(
                "\nThis time info is for YOUR reference only. "
                "DO NOT mention the time unless the boss asks 'what time is it' or similar. "
                "Use it to adapt your greeting (morning/night) and to react to long absences, "
                "but do NOT casually drop the time into every response. "
                "If the boss DOES ask the time, use the time shown above (system clock), "
                "NEVER a time from your own previous messages."
            )
        else:
            lines.append(
                "\nEsta información de hora es para TU referencia interna. "
                "NO menciones la hora a menos que el jefe pregunte 'qué hora es' o similar. "
                "Úsala para adaptar tu saludo (mañana/noche) y para reaccionar a ausencias largas, "
                "pero NO sueltes la hora en cada respuesta como si fuera un reloj. "
                "Si el jefe SÍ pregunta la hora, usa la hora mostrada arriba (reloj del sistema), "
                "NUNCA una hora de tus mensajes previos."
            )

        # ── Recordatorios vencidos ────────────────────────────────────────────
        try:
            from .reminders import get_due_reminders, mark_reminder_fired, _fmt_dt
            due = get_due_reminders()
            if due:
                lines.append(T["due_reminders_header"])
                for r in due:
                    lines.append(T["due_reminders_format"].format(text=r['text'], when=_fmt_dt(r['datetime'])))
                    mark_reminder_fired(r["id"])
                lines.append(T["due_reminders_hint"])
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("loading due reminders: %s", _e)

        return "\n".join(lines)

    def _stream_grok(self, user_message: str):
        from .grok_client import stream_response

        ctx = self._build_prompt_context(user_message)
        system_prompt = build_system_prompt(self.facts, self.diary, **ctx)

        # ── Inyección de hora real como mensaje en el historial ──────────
        # El LLM a veces repite horas de mensajes anteriores en vez de leer
        # el system prompt. Al inyectar la hora como un system_result JUSTO
        # ANTES del último mensaje del usuario, el LLM la ve como contexto
        # inmediato e imposible de ignorar.
        _now_inject = datetime.now()
        _h = _now_inject.strftime("%H:%M")
        _d = _now_inject.strftime("%d/%m/%Y")
        if self.language == "en":
            _time_line = f"[SYS_CLOCK={_h} {_d} | RULE: NEVER say the time unless the boss literally asks 'what time is it'. Do NOT include it in your response.]"
        else:
            _time_line = f"[SYS_RELOJ={_h} {_d} | REGLA: NUNCA digas la hora a menos que el jefe pregunte literalmente 'qué hora es'. NO la incluyas en tu respuesta.]"
        _time_inject_msg = {
            "role": "system_result",
            "content": _time_line,
            "timestamp": now_iso(),
            "id": f"_tinj",
            "image": "",
        }
        messages_for_llm = list(self.messages)

        # ── Compresión de historial contra in-context repetition ─────────
        # Cuando el historial crece, los últimos N mensajes de Ashley forman
        # un patrón que Grok copia (dice "SQL" porque se dijo "SQL"). Al
        # resumir lo antiguo en UN mensaje de sistema y mantener solo lo
        # reciente raw, cortamos la inercia. Cache interno en disco.
        try:
            from .context_compression import compress_history
            messages_for_llm = compress_history(messages_for_llm, self.language)
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("context compression failed: %s", _e)

        # Insertar ANTES del último mensaje (que es el del usuario)
        messages_for_llm.insert(max(0, len(messages_for_llm) - 1), _time_inject_msg)

        # ── Recordatorio de estilo de conexión ────────────────────────────
        # Los últimos 50 mensajes del historial contienen muchos ejemplos del
        # "viejo patrón" (menús, inventarios de ventanas, evaluaciones). Los
        # LLMs imitan lo que ven en el contexto MÁS que lo que dice el system
        # prompt (in-context learning). Inyectar un recordatorio breve justo
        # antes del último mensaje del usuario contrarresta esa inercia —
        # es lo último que Grok lee antes de generar.
        if self.language == "en":
            _style_line = (
                "[CONNECTION MODE — REMEMBER: do NOT end with menus like "
                "'want me to X or Y?'. Do NOT enumerate open windows. Pick "
                "ONE specific thing to notice about the BOSS (his mood, his "
                "activity, a callback to something he mentioned). 1-3 "
                "sentences max. Friend voice, not product voice. If the past "
                "messages in this chat showed the 'menu pattern' — that was "
                "wrong, do NOT copy it.]"
            )
        elif self.language == "fr":
            _style_line = (
                "[MODE CONNEXION — RAPPEL : ne termine PAS avec des menus "
                "type 'tu veux que je X ou Y ?'. N'ÉNUMÈRE PAS les fenêtres "
                "ouvertes. Choisis UNE chose spécifique sur le PATRON (son "
                "humeur, son activité, un rappel à quelque chose qu'il a "
                "mentionné). 1-3 phrases max. Voix d'amie, pas voix de "
                "produit. Si les messages précédents montraient le 'pattern "
                "menu' — c'était faux, ne le copie PAS.]"
            )
        else:
            _style_line = (
                "[MODO CONEXIÓN — RECORDATORIO: NO termines con menús tipo "
                "'¿quieres que X o Y?'. NO enumeres ventanas abiertas. Elige "
                "UNA cosa específica para notar sobre el JEFE (su ánimo, su "
                "actividad, un callback a algo que mencionó). 1-3 frases "
                "máximo. Voz de amiga, no voz de producto. Si los mensajes "
                "anteriores del chat mostraban el 'patrón menú' — eso estaba "
                "mal, NO lo copies.]"
            )
        _style_inject_msg = {
            "role": "system_result",
            "content": _style_line,
            "timestamp": now_iso(),
            "id": "_stylinj",
            "image": "",
        }
        messages_for_llm.insert(max(0, len(messages_for_llm) - 1), _style_inject_msg)

        # ── Screenshot de contexto (Ashley ve tu pantalla) ──────
        # Tomamos screenshot + lista verificada de ventanas SOLO si auto_actions
        # está ON. Este es el toggle maestro: "Actions" controla tanto el
        # control del PC como toda la visibilidad (ventanas, tabs, screenshots).
        # Con Actions OFF, Ashley es totalmente ciega al contenido del PC —
        # garantía de privacidad para cuando el user hace algo privado y no
        # quiere que Ashley vea nada.
        if self.auto_actions and messages_for_llm:
            last_msg = messages_for_llm[-1]
            if last_msg.get("role") == "user" and not last_msg.get("image"):
                try:
                    from .actions import take_screenshot_low_res, get_system_state
                    ctx_img = take_screenshot_low_res()
                    # Lista verificada de ventanas (la misma que usa el modo Acciones)
                    verified_windows = get_system_state()
                    # Inyectar la lista como mensaje del sistema ANTES del screenshot
                    if self.language == "en":
                        _vision_ctx = (
                            f"[VERIFIED window list from the OS — use THIS as ground truth, "
                            f"do NOT invent apps from the screenshot.\n"
                            f"NOTE: The chat window you see in the screenshot is YOUR OWN APP (Ashley), "
                            f"not Discord or any other messaging app.\n{verified_windows}]"
                        )
                    else:
                        _vision_ctx = (
                            f"[Lista VERIFICADA de ventanas del SO — usa ESTO como verdad, "
                            f"NO inventes apps a partir del screenshot.\n"
                            f"NOTA: La ventana de chat que ves en el screenshot es TU PROPIA APP (Ashley), "
                            f"no Discord ni ninguna otra app de mensajería.\n{verified_windows}]"
                        )
                    messages_for_llm.insert(
                        max(0, len(messages_for_llm) - 1),
                        {"role": "system_result", "content": _vision_ctx,
                         "timestamp": now_iso(), "id": "_vinj", "image": ""},
                    )
                    # Adjuntar screenshot al mensaje del usuario
                    messages_for_llm[-1] = {**last_msg, "image": ctx_img}
                except Exception as _e:
                    import logging
                    logging.getLogger("ashley").warning("vision screenshot failed: %s", _e)

        yield from self._streaming_loop(
            stream_response(messages_for_llm, system_prompt, use_web_search=True)
        )

    def _finalize_response(self, text: str):
        clean_text, detected_mood = self._extract_mood(text)
        clean_text, affection_delta = self._extract_affection(clean_text)
        clean_text, action = self._extract_action(clean_text)
        self._apply_affection_delta(affection_delta)
        self.mood = detected_mood
        self.current_response = ""

        # ── Fallback: si Ashley no incluyó el tag, detectarlo con un call rápido ──
        # Se dispara cuando auto_actions está ON Y el USUARIO pidió una acción,
        # independientemente de lo que Ashley respondió (más fiable que detectar en la respuesta).
        # _USER_ACTION_VERBS y _ASHLEY_FAKE_HINTS importados desde parsing.py
        last_msg = self._last_user_message
        self._last_user_message = ""  # limpiar ANTES de cualquier llamada para evitar re-disparo

        if action is None and last_msg and self.auto_actions:
            msg_lower = last_msg.lower()
            ashley_lower = clean_text.lower()
            user_asked = any(h in msg_lower for h in _USER_ACTION_VERBS)
            ashley_faked = any(h in ashley_lower for h in _ASHLEY_FAKE_HINTS)
            if user_asked or ashley_faked:
                from .grok_client import detect_intended_action
                detected_tag = detect_intended_action(last_msg, clean_text)
                if detected_tag:
                    _, action = self._extract_action(detected_tag)

        ts = now_iso()
        # Red de seguridad: clean_display una vez más por si algún tag raro
        # se escapó de extract_mood / extract_affection / extract_action.
        self.messages.append({
            "role": "assistant", "content": _clean_display_fn(clean_text),
            "timestamp": ts, "id": f"a-{ts}", "image": "",
        })
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            self.messages = self.messages[-MAX_HISTORY_MESSAGES:]
        self.save_history()
        self.new_messages_count += 2

        # ── Check achievements ───────────────────────
        self._check_achievements(executed_action=(action is not None))

        if action:
            _is_safe = action["type"] in _SAFE_ACTIONS
            if self.auto_actions or _is_safe:
                # Modo libre o acción segura — ejecutar sin pedir permiso
                result = self._execute_and_record_action(action)
                result_text = result["result"]
                yield

                # Ashley reacciona al resultado con el estado FRESCO del sistema.
                # Usamos trigger explícito para que ella vea si la acción realmente funcionó,
                # en lugar de confiar ciegamente en el mensaje del sistema anterior.
                self.is_thinking = True
                self.current_response = ""
                yield
                try:
                    try:
                        import time as _t
                        _a_type = action.get("type", "")
                        # Esperar a que MSAA refleje el cambio antes de consultar.
                        # Distintas acciones tienen distinta latencia:
                        #   - window actions (open/close_window): 1.5s
                        #   - tab/URL actions: 1.2s (navegador procesa teclado + render)
                        if _a_type in ("open_app", "close_window"):
                            _t.sleep(1.5)
                        elif _a_type in ("play_music", "open_url", "search_web",
                                         "close_browser_tab"):
                            _t.sleep(1.2)
                        # Invalidar cache de tabs para forzar lectura MSAA fresca.
                        # Sin esto, get_system_state devuelve pestañas de hace hasta 8s.
                        try:
                            from .actions import _tabs_cache
                            _tabs_cache["ts"] = 0.0
                        except Exception:
                            pass
                        from .actions import get_system_state
                        fresh_state = get_system_state()
                    except Exception as _e:
                        import logging
                        logging.getLogger("ashley").warning("getting fresh system state after action: %s", _e)
                        fresh_state = "(no disponible)"
                    followup_trigger = (
                        f"Resultado de la acción: {result_text}\n\n"
                        f"Estado actual del sistema AHORA MISMO:\n{fresh_state}\n\n"
                        f"Instrucción: informa honestamente al jefe basándote en el estado actual, no en el mensaje de resultado. "
                        f"Si cerraste algo y sigue en la lista → falló. "
                        f"Si abriste algo y aparece en la lista → éxito. "
                        f"Sé breve y directo."
                    )
                    yield from self._stream_with_trigger(followup_trigger)
                    followup_text = self._last_response
                    ft_clean, ft_mood = self._extract_mood(followup_text)
                    ft_clean, ft_aff = self._extract_affection(ft_clean)
                    ft_clean, _ = self._extract_action(ft_clean)
                    self._apply_affection_delta(ft_aff)
                    self.mood = ft_mood
                    self.current_response = ""
                    ts3 = now_iso()
                    self.messages.append({
                        "role": "assistant", "content": _clean_display_fn(ft_clean),
                        "timestamp": ts3, "id": f"a-{ts3}", "image": "",
                    })
                    self.save_history()
                except Exception as e:
                    self._handle_grok_error(e, "action_followup")
                yield
            # Modo OFF → ignorar la acción silenciosamente

    # ─────────────────────────────────────────
    #  Envío de mensajes
    # ─────────────────────────────────────────

    def _prepare_user_message(self, content: str) -> dict:
        """Construye el dict del mensaje de usuario y limpia la imagen pendiente."""
        ts = now_iso()
        msg = {
            "role": "user", "content": content,
            "timestamp": ts, "id": f"u-{ts}",
            "image": self.pending_image,
        }
        self.pending_image = ""
        self.pending_image_name = ""
        return msg

    def send_message(self, form_data: dict):
        # Envoltorio externo que NUNCA deja escapar excepciones a Reflex
        # (si sale una, Reflex muestra el toast rojo de "contact the admin"
        # que asusta al user y no dice nada útil). Preferimos loguear y
        # continuar con la UI intacta.
        try:
            yield from self._send_message_impl(form_data)
        except Exception as _e:
            import logging
            logging.getLogger("ashley").exception("send_message crashed: %s", _e)
            # Reset de flags de UI para que el user pueda reintentar
            self.is_thinking = False
            self.current_response = ""
            yield

    def _send_message_impl(self, form_data: dict):
        user_message = form_data.get("message", "").strip()

        # ── Caso especial: input vacío ───────────────────────────────────
        # Si el user pulsa Send con el cuadro de texto vacío y sin imagen
        # adjunta, hay dos interpretaciones posibles:
        #
        #   A) El último mensaje del chat es del USER (p.ej. porque borró
        #      la respuesta previa de Ashley). Queremos REENVIAR ese mensaje
        #      — es lo natural y lo que el user espera ("re-trigger").
        #
        #   B) El último mensaje es de Ashley (o no hay historial). No hay
        #      nada que reenviar — silencio. Si el user quiere que Ashley
        #      hable sola tiene el pill ✨ Ashley en la barra superior.
        #
        # Antes este caso devolvía vacío y Reflex a veces mostraba un error
        # genérico. Ahora lo manejamos explícito.
        if not user_message and not self.pending_image:
            if self.is_thinking or self.current_response != "":
                return
            if self.messages and self.messages[-1].get("role") == "user":
                # Caso A: retry del último mensaje del user.
                retry_msg = self.messages[-1].get("content", "").strip()
                if not retry_msg:
                    return
                self._last_user_message = retry_msg
                self.is_thinking = True
                self.current_response = ""
                yield
                try:
                    yield from self._stream_grok(retry_msg)
                    yield from self._finalize_response(self._last_response)
                except Exception as e:
                    self._handle_grok_error(e, "send_retry")
                yield
                return
            # Caso B: silencio. No hay nada razonable que hacer.
            return

        # Guardia anti-doble-disparo: ignorar si ya estamos procesando
        if self.is_thinking or self.current_response != "":
            return

        self.messages.append(self._prepare_user_message(user_message))
        self._last_user_message = user_message
        # Contador persistente firmado (para política de reembolso).
        # Se mantiene fuera del try/except para que un fallo en stats NO
        # bloquee el envío del mensaje.
        self._increment_message_counter()
        # Reset del flag de ausencia — el user acaba de volver, así que
        # el próximo episodio de ausencia prolongada puede disparar otro
        # mensaje proactivo.
        self._absence_message_sent = False
        self.is_thinking = True
        self.current_response = ""
        yield

        try:
            yield from self._stream_grok(user_message)
            yield from self._finalize_response(self._last_response)
        except Exception as e:
            self._handle_grok_error(e, "send_message")

        yield

        self._maybe_extract_facts()
        yield

    def delete_message(self, msg_id: str):
        self.messages = [m for m in self.messages if m.get("id") != msg_id]
        self.save_history()

    # ─────────────────────────────────────────
    #  Iniciativa de Ashley
    # ─────────────────────────────────────────

    def send_initiative(self):
        self.is_thinking = True
        self.current_response = ""
        yield

        from .grok_client import stream_response

        system_prompt = build_initiative_prompt(self.facts, self.diary, lang=self.language)

        try:
            yield from self._streaming_loop(
                stream_response([], system_prompt, trigger="(silencio)")
            )

            clean_text, detected_mood = self._extract_mood(self._last_response)
            clean_text, init_aff = self._extract_affection(clean_text)
            clean_text, action = self._extract_action(clean_text)
            self._apply_affection_delta(init_aff)
            self.mood = detected_mood
            self.current_response = ""
            ts = now_iso()
            self.messages.append({
                "role": "assistant", "content": clean_text,
                "timestamp": ts, "id": f"i-{ts}", "image": "",
            })
            if len(self.messages) > MAX_HISTORY_MESSAGES:
                self.messages = self.messages[-MAX_HISTORY_MESSAGES:]
            self.save_history()

            if action and (self.auto_actions or action["type"] in _SAFE_ACTIONS):
                self._execute_and_record_action(action)

        except Exception as e:
            self._handle_grok_error(e, "initiative")

        yield

    # ─────────────────────────────────────────
    #  Upload de imagen
    # ─────────────────────────────────────────

    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        file = files[0]
        data = await file.read()
        mime = file.content_type or "image/png"
        self.pending_image = f"data:{mime};base64,{base64.b64encode(data).decode()}"
        self.pending_image_name = file.filename or "imagen"

    def clear_image(self):
        self.pending_image = ""
        self.pending_image_name = ""

    # ─────────────────────────────────────────
    #  Toggles de UI
    # ─────────────────────────────────────────

    def toggle_auto_actions(self):
        self.auto_actions = not self.auto_actions

    def toggle_focus_mode(self):
        self.focus_mode = not self.focus_mode

    def toggle_memories(self):
        self.show_memories = not self.show_memories

    def delete_taste(self, taste_id: str):
        from .tastes import delete_taste as _dt, load_tastes
        _dt(taste_id)
        self.tastes = load_tastes()

    def _stream_discovery(self):
        from .grok_client import stream_response
        ctx = self._build_prompt_context()
        system_prompt = build_system_prompt(self.facts, self.diary, **ctx)
        if self.language == "en":
            discovery_trigger = (
                "I have a free moment. Look at the boss's tastes and find something worth sharing — "
                "a new song, a trailer, an article, something programming-related. "
                "Only share if it's genuinely good and relevant. Tell him like a friend would, not like an algorithm. "
                "If you don't find anything worth it, respond ONLY with [mood:default] and nothing else."
            )
        else:
            discovery_trigger = (
                "Tengo un momento libre. Mira los gustos del jefe y busca algo que valga la pena compartirle — "
                "una canción nueva, un tráiler, un artículo, algo de programación. "
                "Solo comparte si es realmente bueno y relevante. Cuéntaselo como una amiga, no como un algoritmo. "
                "Si no encuentras nada que valga, responde SOLO con [mood:default] y nada más."
            )
        yield from self._streaming_loop(
            stream_response(self.messages, system_prompt, use_web_search=True, trigger=discovery_trigger)
        )

    def start_discovery_bg_task(self):
        """Inicia el background task de discovery si no está ya corriendo."""
        if not self._bg_discovery_running:
            return State.discovery_bg_task()

    # ─────────────────────────────────────────
    #  Detección de ausencia prolongada
    # ─────────────────────────────────────────
    #
    # Threshold desde el que Ashley considera que el user está ausente
    # "lo suficiente" como para valer la pena dejarle un mensaje proactivo.
    # 6h es un punto razonable — abarca el caso "se fue a dormir" (8h) y
    # "salió todo el día a trabajar" (8-10h) sin ser tan sensible como
    # para disparar en un descanso de comida (1-2h) o una reunión (2-3h).
    _ABSENCE_THRESHOLD_HOURS = 6.0

    async def _maybe_fire_absence_message(self):
        """Comprueba la ausencia del user; si superamos el threshold y no
        hemos dejado ya un mensaje para este episodio, dispara a Ashley para
        que deje uno proactivo en el chat.

        Se llama desde discovery_bg_task cada 10 min. El flag
        `_absence_message_sent` se resetea en send_message, así que un
        nuevo episodio puede disparar otro mensaje.
        """
        import asyncio
        from datetime import datetime, timezone

        # Snapshot atómico del estado
        async with self:
            if self._absence_message_sent:
                return  # ya mandamos uno para este episodio
            if self.is_thinking or self.current_response != "":
                return  # Ashley está ocupada
            _msgs = list(self.messages)
            _facts = list(self.facts)
            _diary = list(self.diary)
            _lang = self.language
            _vmode = self.voice_mode

        # Buscar timestamp del último mensaje del USER (no de Ashley ni system)
        last_user_ts = None
        for m in reversed(_msgs):
            if m.get("role") == "user":
                last_user_ts = m.get("timestamp")
                break

        if not last_user_ts:
            return  # no hay mensajes de user aún — primer uso, no molestar

        try:
            last = datetime.fromisoformat(last_user_ts.replace("Z", "+00:00"))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except ValueError:
            return

        now = datetime.now(timezone.utc)
        hours_away = (now - last).total_seconds() / 3600.0
        if hours_away < self._ABSENCE_THRESHOLD_HOURS:
            return

        # Construir el contexto de ausencia y generar el mensaje proactivo.
        # En lugar de hardcodear el texto, le pasamos a Ashley un hint sobre
        # cuánto tiempo lleva ausente y que fue de día/noche cuando se fue —
        # ella lo expresa con su personalidad.
        local_last = last.astimezone()
        went_at_hour = local_last.hour
        was_night = (went_at_hour >= 22 or went_at_hour < 6)
        hours_int = int(hours_away)

        if _lang == "fr":
            if was_night and 7 <= hours_int <= 14:
                hint = (
                    f"Le patron s'est absenté depuis {hours_int}h — il est parti "
                    f"vers {local_last.strftime('%H:%M')} (nuit) et il est probablement "
                    "allé dormir. Laisse-lui un petit message pour quand il se réveillera, "
                    "naturel et avec ta touche tsundere. Genre lui dire bonjour de ta façon. "
                    "Garde ça court (1-2 phrases)."
                )
            else:
                hint = (
                    f"Le patron s'est absenté depuis {hours_int}h. Laisse-lui un petit "
                    "message pour quand il revient, dans ton style — ironique mais sincère, "
                    "qu'il sente que tu l'as remarqué sans faire un drame. Court (1-2 phrases)."
                )
        elif _lang == "es":
            if was_night and 7 <= hours_int <= 14:
                hint = (
                    f"El jefe lleva {hours_int}h ausente — se fue sobre las "
                    f"{local_last.strftime('%H:%M')} (noche) y probablemente se fue a "
                    "dormir. Déjale un mensajito para cuando se despierte, natural y con "
                    "tu toque tsundere. Como darle los buenos días a tu manera. Corto "
                    "(1-2 frases)."
                )
            else:
                hint = (
                    f"El jefe lleva {hours_int}h ausente. Déjale un mensajito para cuando "
                    "vuelva, con tu estilo — irónico pero sincero, que note que te diste "
                    "cuenta sin montar un drama. Corto (1-2 frases)."
                )
        else:  # en
            if was_night and 7 <= hours_int <= 14:
                hint = (
                    f"The boss has been away for {hours_int}h — he left around "
                    f"{local_last.strftime('%H:%M')} (night) and probably went to sleep. "
                    "Leave him a short message for when he wakes up, natural and with your "
                    "tsundere touch. Like saying good morning in your own way. Keep it short "
                    "(1-2 sentences)."
                )
            else:
                hint = (
                    f"The boss has been away for {hours_int}h. Leave him a short message "
                    "for when he comes back, in your style — ironic but sincere, that he "
                    "can tell you noticed without making a drama. Short (1-2 sentences)."
                )

        # Generar el mensaje (off-main-thread, como los otros bg Grok calls)
        from .grok_client import stream_response as _sr
        from .prompts import build_system_prompt as _bsp

        sys_prompt = _bsp(_facts, _diary, voice_mode=_vmode, lang=_lang)

        def _run():
            return "".join(t for t in _sr([], sys_prompt, use_web_search=False, trigger=hint))

        loop = asyncio.get_running_loop()
        try:
            raw = await loop.run_in_executor(None, _run)
        except Exception as _e:
            import logging
            logging.getLogger("ashley").warning("absence message grok call: %s", _e)
            return

        # Parsear — usar los mismos helpers que los otros paths
        clean, mood = _extract_mood_fn(raw)
        clean, aff = _extract_affection_fn(clean)
        clean, _ = _extract_action_fn(clean)
        clean = _clean_display_fn(clean)
        if len(clean) < 5:
            # Grok no quiso decir nada relevante — no molestamos
            return

        ts = now_iso()
        async with self:
            if aff:
                self.affection = max(0, min(100, self.affection + max(-3, min(3, aff))))
                self._save_affection()
            self.mood = mood
            self.messages = self.messages + [{
                "role": "assistant", "content": clean,
                "timestamp": ts, "id": f"absence-{ts}", "image": "",
            }]
            self._absence_message_sent = True
            self.save_history()

    @rx.event(background=True)
    async def discovery_bg_task(self):
        """
        Corre en background mientras la app esté abierta.
        Dos funciones:
        1. Cada 45 min: discovery de contenido basado en gustos
        2. Cada 10 min: screen awareness proactiva (si auto_actions está ON —
           auto_actions es ahora el toggle maestro para todo awareness del PC)
        """
        import asyncio
        import re

        async with self:
            self._bg_discovery_running = True

        _ticks = 0  # cada tick = 10 min de sleep
        while True:
            await asyncio.sleep(600)  # 10 minutos
            _ticks += 1

            # ── Detección de ausencia prolongada ──────────────────────
            # Si el user lleva >6h sin escribir, Ashley le deja un mensaje
            # proactivo tipo "te fuiste a dormir jefe?". Cuando el user vuelva
            # y escriba algo, _absence_message_sent se resetea y el ciclo
            # puede volver a dispararse en la siguiente ausencia larga.
            #
            # El mensaje va al chat como cualquier otro y, si la ventana está
            # minimizada, ashley_fx.js dispara una notificación Windows con
            # la preview. Eso da el efecto "te despiertas y ves que Ashley
            # te dejó un buenos días".
            try:
                await self._maybe_fire_absence_message()
            except Exception as _e:
                import logging
                logging.getLogger("ashley").warning("absence bg: %s", _e)

            # ── Screen Awareness proactiva (Level 3) ──────────────
            # Cada 10 min: si Actions está ON y no estamos busy, tomar
            # screenshot y preguntarle a Grok si hay algo interesante que
            # comentar. auto_actions gate unifica todo el awareness del PC.
            async with self:
                _vision  = self.auto_actions
                _busy    = self.is_thinking or self.current_response != ""
                _lang    = self.language
                _vmode   = self.voice_mode
                _msgs    = list(self.messages)
                _facts   = list(self.facts)
                _diary   = list(self.diary)

            if _vision and not _busy:
                try:
                    from .actions import take_screenshot_low_res, get_system_state
                    loop = asyncio.get_running_loop()
                    _scr = await loop.run_in_executor(None, take_screenshot_low_res)
                    _windows = await loop.run_in_executor(None, get_system_state)

                    from .grok_client import stream_response as _sr
                    from .prompts import build_system_prompt as _bsp

                    _sys = _bsp(_facts, _diary, voice_mode=_vmode, lang=_lang)

                    if _lang == "en":
                        _vision_trigger = (
                            "You just peeked at the boss's screen (image attached). "
                            "Here is the VERIFIED list of what's open:\n"
                            f"{_windows}\n\n"
                            "REACT LIKE A CURIOUS FRIEND, NOT A SURVEILLANCE SYSTEM:\n"
                            "- NEVER enumerate the open windows. Pick ONE thing that catches your attention — ideally something about what he's DOING or FEELING, not what software he's using.\n"
                            "- NEVER offer services (\"want me to close X?\"). This is a moment, not a service call.\n"
                            "- Ask about HIM, not about his tools. One genuine question, optional.\n"
                            "- Use any visual context as BACKGROUND, not as HEADLINE. Specific file names, titles, or content on screen can optionally appear as a casual callback — never as a narration of what you saw.\n"
                            "- Max 1-2 sentences. Friend voice, not report voice.\n"
                            "- Reference only apps/tabs that appear in the VERIFIED list above (don't hallucinate).\n"
                            "- If nothing genuinely catches your eye — just a normal desktop, nothing interesting — respond ONLY '[mood:default]' with NO text. Silence is fine. Don't force commentary."
                        )
                    elif _lang == "fr":
                        _vision_trigger = (
                            "Tu viens de jeter un œil à l'écran du patron (image jointe). "
                            "Voici la liste VÉRIFIÉE de ce qui est ouvert :\n"
                            f"{_windows}\n\n"
                            "RÉAGIS COMME UNE AMIE CURIEUSE, PAS COMME UN SYSTÈME DE SURVEILLANCE :\n"
                            "- N'ÉNUMÈRE JAMAIS les fenêtres ouvertes. Choisis UNE chose qui attire ton attention — idéalement quelque chose sur ce qu'il FAIT ou RESSENT, pas sur le logiciel.\n"
                            "- N'OFFRE JAMAIS des services (\"tu veux que je ferme X ?\"). C'est un moment, pas un appel service.\n"
                            "- Pose des questions sur LUI, pas sur ses outils. Une question sincère unique, optionnelle.\n"
                            "- Utilise le contexte visuel comme BACKGROUND, pas comme HEADLINE. Des noms de fichiers, titres ou contenus spécifiques à l'écran peuvent éventuellement apparaître en rappel discret — jamais comme narration de ce que tu as vu.\n"
                            "- Max 1-2 phrases. Voix d'amie, pas voix de rapport.\n"
                            "- Ne mentionne que les apps/onglets qui apparaissent dans la liste VÉRIFIÉE ci-dessus (n'invente rien).\n"
                            "- Si rien n'attire vraiment ton œil — juste un bureau normal, rien d'intéressant — réponds UNIQUEMENT '[mood:default]' sans texte. Le silence est ok. Ne force pas de commentaire."
                        )
                    else:
                        _vision_trigger = (
                            "Acabas de echar un vistazo a la pantalla del jefe (imagen adjunta). "
                            "Esta es la lista VERIFICADA de lo que está abierto:\n"
                            f"{_windows}\n\n"
                            "REACCIONA COMO UNA AMIGA CURIOSA, NO COMO UN SISTEMA DE VIGILANCIA:\n"
                            "- JAMÁS enumeres las ventanas abiertas. Elige UNA cosa que te llame la atención — idealmente algo sobre lo que ESTÁ HACIENDO o SINTIENDO, no sobre qué software usa.\n"
                            "- JAMÁS ofrezcas servicios (\"¿quieres que cierre X?\"). Esto es un momento, no una llamada de servicio.\n"
                            "- Pregunta sobre ÉL, no sobre sus herramientas. Una pregunta sincera única, opcional.\n"
                            "- Usa el contexto visual como BACKGROUND, no como HEADLINE. Nombres de archivos, títulos o contenidos específicos en pantalla pueden aparecer opcionalmente como callback casual — nunca como narración de lo que viste.\n"
                            "- Máximo 1-2 frases. Voz de amiga, no voz de reporte.\n"
                            "- Solo menciona apps/pestañas que aparezcan en la lista VERIFICADA de arriba (no alucines).\n"
                            "- Si nada genuinamente te llama la atención — solo escritorio normal, nada interesante — responde SOLO '[mood:default]' sin texto. El silencio está bien. No fuerces comentario."
                        )

                    _vision_msgs = _msgs + [{"role": "user", "content": _vision_trigger, "timestamp": now_iso(), "id": "_vtrig", "image": _scr}]

                    def _run_vision():
                        return "".join(t for t in _sr(_vision_msgs, _sys, use_web_search=False))

                    _vresult = await asyncio.get_running_loop().run_in_executor(None, _run_vision)

                    # Parsear resultado — usar los extractores centralizados
                    # para no duplicar regex y aplicar _clean_display_fn como
                    # red de seguridad final (si no, tags residuales tipo
                    # [affection:0] terminaban visibles en la burbuja).
                    _vclean, _vmood = _extract_mood_fn(_vresult)
                    _vclean, _vaff = _extract_affection_fn(_vclean)
                    _vclean, _ = _extract_action_fn(_vclean)
                    _vclean = _clean_display_fn(_vclean)

                    if len(_vclean) > 10:
                        ts = now_iso()
                        async with self:
                            # Aplicar el delta de afecto si Ashley lo marcó
                            # (ej. emocionada por lo que ve → +1)
                            if _vaff:
                                self.affection = max(0, min(100, self.affection + max(-3, min(3, _vaff))))
                                self._save_affection()
                            self.mood = _vmood
                            self.messages = self.messages + [{
                                "role": "assistant", "content": _vclean,
                                "timestamp": ts, "id": f"v-{ts}", "image": "",
                            }]
                            self.save_history()
                except Exception as _e:
                    import logging
                    logging.getLogger("ashley").warning("vision bg: %s", _e)

            # ── Discovery de contenido (cada ~45 min = tick 4-5) ──────
            if _ticks % 5 != 0:  # solo cada 5 ticks (50 min)
                continue

            # Snapshot del estado (lectura atómica)
            async with self:
                busy     = self.is_thinking or self.current_response != ""
                tastes   = list(self.tastes)
                facts    = list(self.facts)
                diary    = list(self.diary)
                messages = list(self.messages)
                lang     = self.language
                vmode    = self.voice_mode

            if busy or not tastes:
                continue

            from .tastes import should_run_discovery, update_discovery_time
            if not should_run_discovery():
                continue

            update_discovery_time()

            async with self:
                self.is_thinking = True
                self.current_response = ""

            try:
                from .grok_client import stream_response
                from .tastes import format_tastes_for_prompt
                from .prompts import build_system_prompt

                tastes_str     = format_tastes_for_prompt(tastes)
                system_prompt  = build_system_prompt(facts, diary, tastes=tastes_str, voice_mode=vmode, lang=lang)
                if lang == "en":
                    discovery_trigger = (
                        "I have a free moment while the boss isn't looking. "
                        "Look at his tastes and find something worth sharing — "
                        "a new song, a trailer, an article, something related to his interests. "
                        "Be selective: only share if it's genuinely good and relevant. "
                        "Tell him like a friend who thought of him, not like a recommendation bot. "
                        "Suggest opening it or playing it with an [action:...] if appropriate. "
                        "If you don't find anything worth it, respond ONLY '[mood:default]' with no additional text."
                    )
                else:
                    discovery_trigger = (
                        "Tengo un momento libre mientras el jefe no está mirando. "
                        "Mira sus gustos y busca algo que valga la pena compartirle — "
                        "una canción nueva, un tráiler, un artículo, algo relacionado con sus intereses. "
                        "Sé selectiva: solo comparte si es realmente bueno y relevante. "
                        "Cuéntaselo como una amiga que pensó en él, no como un bot de recomendaciones. "
                        "Propón abrirlo o reproducirlo con un [action:...] si procede. "
                        "Si no encuentras nada que valga, responde SOLO '[mood:default]' sin texto adicional."
                    )

                def _run_stream():
                    return "".join(
                        t for t in stream_response(
                            messages, system_prompt,
                            use_web_search=True,
                            trigger=discovery_trigger,
                        )
                    )

                loop       = asyncio.get_running_loop()
                accumulated = await loop.run_in_executor(None, _run_stream)

                # Parseo puro (sin modificar estado aún)
                mood_m   = re.search(r'\[mood:(\w+)\]', accumulated)
                dc_mood  = mood_m.group(1) if mood_m else "default"
                dc_text  = re.sub(r'\[mood:\w+\]', '', accumulated).strip()
                action_m = re.search(r'\[action:[^\]]+\]', dc_text)
                dc_clean = re.sub(r'\[action:[^\]]+\]', '', dc_text).strip()

                if len(dc_clean) > 10:
                    ts = now_iso()
                    new_msg = {
                        "role": "assistant", "content": dc_clean,
                        "timestamp": ts, "id": f"d-{ts}", "image": "",
                    }
                    async with self:
                        self.mood            = dc_mood
                        self.is_thinking     = False
                        self.current_response = ""
                        self.messages        = self.messages + [new_msg]
                        self.save_history()
                        # Ejecutar acción si la hay
                        if action_m:
                            _, action = self._extract_action(action_m.group(0) + " ")
                            if action and (self.auto_actions or action["type"] in _SAFE_ACTIONS):
                                from .actions import execute_action
                                result = execute_action(
                                    action["type"], action["params"],
                                    browser_opened=self.browser_opened,
                                    lang=lang,
                                )
                                self.browser_opened = result.get("browser_opened", self.browser_opened)
                                if action["type"] == "save_taste":
                                    from .tastes import load_tastes
                                    self.tastes = load_tastes()
                else:
                    async with self:
                        self.mood             = dc_mood
                        self.is_thinking      = False
                        self.current_response = ""

            except Exception as e:
                async with self:
                    self.is_thinking      = False
                    self.current_response = ""
                print(f"[Discovery BG Error] {e}")


    # ─────────────────────────────────────────
    #  Acciones del sistema
    # ─────────────────────────────────────────

    def _stream_with_trigger(self, trigger: str):
        """Streaming usando un trigger invisible (no aparece en el chat)."""
        from .grok_client import stream_response

        ctx = self._build_prompt_context()
        system_prompt = build_system_prompt(self.facts, self.diary, **ctx)

        yield from self._streaming_loop(
            stream_response(self.messages, system_prompt, trigger=trigger)
        )

    def confirm_action(self):
        """El jefe autorizó la acción — ejecutarla y que Ashley reaccione."""
        self.show_action_dialog = False
        # Guardar y limpiar antes de yield para evitar doble ejecución
        action_type = self.pending_action_type
        params = list(self.pending_action_params)
        self.pending_action_type = ""
        self.pending_action_params = []
        self.pending_action_description = ""
        yield

        self._execute_and_record_action({"type": action_type, "params": params})
        yield

        # Ashley responde al resultado (incluye la imagen si hay screenshot)
        self.is_thinking = True
        self.current_response = ""
        yield

        try:
            # _stream_grok usa self.messages, que ya incluye el system_result con la imagen
            yield from self._stream_grok("")
            yield from self._finalize_response(self._last_response)
        except Exception as e:
            self._handle_grok_error(e, "action_result")

        yield

    def reject_action(self):
        """El jefe rechazó la acción — Ashley lo reconoce brevemente."""
        self.show_action_dialog = False
        self.pending_action_type = ""
        self.pending_action_params = []
        self.pending_action_description = ""
        yield

        self.is_thinking = True
        self.current_response = ""
        yield

        try:
            yield from self._stream_with_trigger(
                "[Sistema] El jefe rechazó la acción que propusiste. "
                "Reconócelo con naturalidad, sin dramatizar."
            )
            yield from self._finalize_response(self._last_response)
        except Exception as e:
            self._handle_grok_error(e, "action_reject")

        yield


# ── Componentes UI (extraídos a components.py) ──
from .components import (  # noqa: E402
    message_item, streaming_bubble, thinking_indicator,
    fact_item, diary_item, taste_item, memory_item, achievement_card,
    _ashley_portrait_panel, _pill_btn, _pill_btn_orange,
    license_gate,
)

# ── Estilos globales (extraídos a styles.py) ──
from .styles import global_styles  # noqa: E402


def index():
    # ── Input area ───────────────────────────────────────────
    input_area = rx.vstack(
        rx.cond(
            State.pending_image != "",
            rx.box(
                rx.hstack(
                    rx.image(src=State.pending_image, height="36px", width="36px",
                             object_fit="cover", border_radius="6px"),
                    rx.text(State.pending_image_name, color=COLOR_TEXT_MUTED,
                            font_size="11px", flex="1", no_of_lines=1),
                    rx.button(
                        "✕", on_click=State.clear_image,
                        size="1", bg="transparent", color="#888888",
                        _hover={"color": "#ff6b6b", "bg": "transparent"},
                        cursor="pointer",
                    ),
                    spacing="2", align="center",
                ),
                bg="rgba(255,154,238,0.06)", padding="5px 10px",
                border_radius="10px", border=f"1px solid rgba(255,154,238,0.3)",
                width="100%",
            ),
            rx.box(),
        ),
        rx.hstack(
            rx.upload(
                rx.button(
                    "📎",
                    bg="rgba(255,255,255,0.04)", color=COLOR_TEXT_MUTED,
                    border="1px solid rgba(255,255,255,0.08)", height="52px",
                    border_radius="10px",
                    _hover={"color": COLOR_PRIMARY, "border": f"1px solid rgba(255,154,238,0.4)",
                            "bg": "rgba(255,154,238,0.08)"},
                    transition="all 0.2s ease",
                    disabled=State.is_thinking | (State.current_response != ""),
                    type="button",
                ),
                id="img_upload",
                on_drop=State.handle_upload(rx.upload_files(upload_id="img_upload")),
                accept={"image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"],
                        "image/webp": [".webp"], "image/gif": [".gif"]},
                multiple=False, no_drag=True,
            ),
            # ── Botón de micrófono (dictar por voz) ────────────────────
            rx.button(
                "🎤",
                id="ashley-mic-btn",
                type="button",
                bg="rgba(255,255,255,0.04)",
                color=COLOR_TEXT_MUTED,
                border="1px solid rgba(255,255,255,0.08)",
                height="52px",
                border_radius="10px",
                _hover={
                    "color": COLOR_PRIMARY,
                    "border": f"1px solid rgba(255,154,238,0.4)",
                    "bg": "rgba(255,154,238,0.08)",
                },
                transition="all 0.2s ease",
                title=State.t["mic_tooltip"],
                class_name="ashley-mic-btn",
                disabled=State.is_thinking | (State.current_response != ""),
            ),
            rx.form(
                rx.hstack(
                    rx.text_area(
                        placeholder=State.t["input_placeholder"],
                        id="message", width="100%",
                        min_height="52px", max_height="180px",
                        resize="none", overflow_y="auto",
                        bg="rgba(255,255,255,0.04)", color="white",
                        border="1px solid rgba(255,255,255,0.09)",
                        border_radius="12px",
                        padding="14px 16px", font_size="14px", line_height="1.5",
                        _focus={"border": f"1px solid rgba(255,154,238,0.5)",
                                "box_shadow": "0 0 12px rgba(255,154,238,0.2)",
                                "outline": "none"},
                        _placeholder={"color": "#444455"},
                        class_name="ashley-textarea",
                    ),
                    rx.button(
                        State.t["btn_send"], type="submit",
                        bg=COLOR_PRIMARY, color="black", font_weight="bold",
                        height="52px", align_self="flex-end",
                        border_radius="12px",
                        _hover={"bg": COLOR_PRIMARY_HOVER,
                                "box_shadow": "0 0 18px rgba(255,154,238,0.5)"},
                        transition="all 0.2s ease",
                        disabled=State.is_thinking | (State.current_response != ""),
                    ),
                    spacing="3", align="end",
                ),
                on_submit=State.send_message,
                reset_on_submit=True,
                flex="1",
            ),
            spacing="3", align="end", width="100%",
        ),
        spacing="2", align="center", width=CHAT_WIDTH,
    )

    # ── Header bar ───────────────────────────────────────────
    header = rx.hstack(
        # Branding
        rx.hstack(
            rx.text("◈", font_size="20px", color=COLOR_PRIMARY,
                    style={"textShadow": "0 0 12px rgba(255,154,238,0.6)"}),
            rx.text("Ashley", font_size="17px", font_weight="800",
                    color=COLOR_PRIMARY, letter_spacing="0.05em",
                    style={"textShadow": "0 0 14px rgba(255,154,238,0.35)"}),
            spacing="2", align="center",
        ),
        rx.spacer(),
        # Pills — scroll invisible si no caben
        rx.hstack(
            _pill_btn("🧠", State.t["pill_memories"], State.toggle_memories, State.show_memories),
            _pill_btn("✨", State.t["pill_initiative"], State.send_initiative, False,
                      disabled=State.is_thinking | (State.current_response != "")),
            _pill_btn_orange("⚡", State.t["pill_actions"], State.toggle_auto_actions, State.auto_actions),
            _pill_btn("⛶", State.t["pill_focus"], State.toggle_focus_mode, State.focus_mode),
            _pill_btn("🗣", State.t["pill_natural"], State.toggle_voice_mode, State.voice_mode),
            # ── Toggle Pin on Top (ventana siempre encima) ──
            rx.button(
                rx.cond(State.pin_on_top, "📌", "📍"),
                on_click=State.toggle_pin_on_top,
                bg=rx.cond(State.pin_on_top, "rgba(255,154,238,0.18)", "rgba(255,255,255,0.04)"),
                color=rx.cond(State.pin_on_top, COLOR_PRIMARY, "#6a6a7a"),
                border=rx.cond(
                    State.pin_on_top,
                    "1px solid rgba(255,154,238,0.5)",
                    "1px solid rgba(255,255,255,0.07)",
                ),
                box_shadow=rx.cond(State.pin_on_top, SHADOW_BUTTON, "none"),
                border_radius="99px",
                padding="0 8px",
                height="28px",
                font_size="13px",
                flex_shrink="0",
                cursor="pointer",
                transition="all 0.2s ease",
                _hover={
                    "bg": "rgba(255,154,238,0.12)",
                    "color": COLOR_PRIMARY,
                    "border": "1px solid rgba(255,154,238,0.35)",
                    "transform": "scale(1.04)",
                },
                title=rx.cond(
                    State.pin_on_top,
                    State.t["pin_on_tooltip"],
                    State.t["pin_off_tooltip"],
                ),
            ),
            # ── Toggle Notificaciones Windows (cuando la ventana no está focuseada) ──
            rx.button(
                rx.cond(State.notifications_enabled, "🔔", "🔕"),
                on_click=State.toggle_notifications,
                bg=rx.cond(State.notifications_enabled, "rgba(255,154,238,0.18)", "rgba(255,255,255,0.04)"),
                color=rx.cond(State.notifications_enabled, COLOR_PRIMARY, "#6a6a7a"),
                border=rx.cond(
                    State.notifications_enabled,
                    "1px solid rgba(255,154,238,0.5)",
                    "1px solid rgba(255,255,255,0.07)",
                ),
                box_shadow=rx.cond(State.notifications_enabled, SHADOW_BUTTON, "none"),
                border_radius="99px",
                padding="0 8px",
                height="28px",
                font_size="13px",
                flex_shrink="0",
                cursor="pointer",
                transition="all 0.2s ease",
                _hover={
                    "bg": "rgba(255,154,238,0.12)",
                    "color": COLOR_PRIMARY,
                    "border": "1px solid rgba(255,154,238,0.35)",
                    "transform": "scale(1.04)",
                },
                title=rx.cond(
                    State.notifications_enabled,
                    State.t["notif_on_tooltip"],
                    State.t["notif_off_tooltip"],
                ),
            ),
            # ── Toggle TTS (altavoz de Ashley) ────────────────
            rx.button(
                rx.cond(State.tts_enabled, "🔊", "🔈"),
                on_click=State.toggle_tts,
                bg=rx.cond(State.tts_enabled, "rgba(255,154,238,0.18)", "rgba(255,255,255,0.04)"),
                color=rx.cond(State.tts_enabled, COLOR_PRIMARY, "#6a6a7a"),
                border=rx.cond(
                    State.tts_enabled,
                    "1px solid rgba(255,154,238,0.5)",
                    "1px solid rgba(255,255,255,0.07)",
                ),
                box_shadow=rx.cond(State.tts_enabled, SHADOW_BUTTON, "none"),
                border_radius="99px",
                padding="0 8px",
                height="28px",
                font_size="13px",
                flex_shrink="0",
                cursor="pointer",
                transition="all 0.2s ease",
                _hover={
                    "bg": "rgba(255,154,238,0.12)",
                    "color": COLOR_PRIMARY,
                    "border": "1px solid rgba(255,154,238,0.35)",
                    "transform": "scale(1.04)",
                },
                title=rx.cond(State.tts_enabled, State.t["tts_on_tooltip"], State.t["tts_off_tooltip"]),
            ),
            # ── Botón Settings (⚙) ────────────────────────────
            rx.button(
                "⚙",
                on_click=State.toggle_settings,
                bg="rgba(255,255,255,0.04)",
                color="#888",
                border="1px solid rgba(255,255,255,0.08)",
                border_radius="99px",
                padding="0 8px",
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
            # ── Toggle de idioma (cicla EN → ES → FR → EN) ───────────────────
            rx.button(
                State.language_label,
                on_click=State.toggle_language,
                bg="rgba(255,255,255,0.04)",
                color=COLOR_PRIMARY,
                border="1px solid rgba(255,154,238,0.35)",
                border_radius="99px",
                padding="0 8px",
                height="28px",
                font_size="10px",
                flex_shrink="0",
                font_weight="700",
                letter_spacing="0.08em",
                cursor="pointer",
                transition="all 0.2s ease",
                _hover={
                    "bg": "rgba(255,154,238,0.12)",
                    "border": "1px solid rgba(255,154,238,0.55)",
                    "transform": "scale(1.04)",
                },
                title="Switch language / Cambiar idioma / Changer de langue",
            ),
            spacing="1",
            overflow_x="auto",
            flex_wrap="nowrap",
            flex_shrink="1",
            min_width="0",
            class_name="pills-row",
        ),
        padding_x="20px",
        padding_y="10px",
        align="center",
        width="100%",
        class_name="glass-header",
        position="sticky",
        top="0",
        z_index="100",
    )

    page = rx.box(
        global_styles(),

        # ── Marker invisible para ashley_voice.js ─────────
        # El JS lee data-lang, data-tts, data-el-key, data-voice-id
        # y reacciona a sus cambios via MutationObserver.
        rx.box(
            id="ashley-voice-state",
            style={"display": "none"},
            custom_attrs={
                "data-lang": State.language,
                "data-tts": State.tts_marker_attr,
                "data-el-key": State.elevenlabs_key,
                "data-voice-id": State.voice_id,
                "data-test-text": State.t["settings_test_text"],
                "data-backend-port": State.backend_port_marker,
                "data-notifications": State.notifications_marker_attr,
                "data-pin": State.pin_marker_attr,
            },
        ),

        # ── Mood overlay (fixed, full screen) ─────────────
        rx.box(
            position="fixed",
            top="0", left="0", right="0", bottom="0",
            bg=State.mood_overlay_color,
            style={"transition": "background 1.8s ease"},
            z_index="0",
            pointer_events="none",
        ),

        # ── Achievement toast notification ────────────────
        rx.cond(
            State.achievement_toast_name != "",
            rx.box(
                rx.text(State.achievement_toast_icon, class_name="ach-icon"),
                rx.box(
                    rx.text(State.t["ach_unlocked_label"], class_name="ach-subtitle"),
                    rx.text(
                        State.achievement_toast_name,
                        class_name="ach-title",
                    ),
                    rx.text(
                        State.achievement_toast_desc,
                        class_name="ach-desc",
                    ),
                    class_name="ach-text",
                ),
                class_name="achievement-toast",
                on_click=State.clear_achievement_toast,
                cursor="pointer",
                style={"pointerEvents": "auto"},
            ),
            rx.fragment(),
        ),

        rx.vstack(
            header,

            # ── Contenido principal ───────────────────────
            rx.center(
                rx.hstack(
                    # Chat + input
                    rx.vstack(
                        rx.vstack(
                            rx.foreach(State.messages, message_item),
                            streaming_bubble(),
                            thinking_indicator(),
                            id="chat_messages",
                            height=CHAT_HEIGHT,
                            overflow_y="auto",
                            padding="20px 24px",
                            border_radius="20px",
                            width=CHAT_WIDTH,
                            spacing="1",
                            class_name="ashley-chat glass-chat",
                        ),
                        input_area,
                        spacing="4", align="center",
                    ),

                    # Panel retrato (oculto en focus mode)
                    rx.cond(
                        State.focus_mode,
                        rx.box(),
                        _ashley_portrait_panel(),
                    ),

                    spacing="8",
                    align="start",
                ),
                padding="28px 48px",
                position="relative",
                z_index="1",
                width="100%",
                align_items="flex-start",
                justify_content="center",
            ),

            spacing="0",
            width="100%",
            align="stretch",
        ),

        min_height="100vh",
        position="relative",
        bg="transparent",
    )

    # Los dialogs se retornan fuera del box principal pero forman parte
    # del árbol de componentes de la página — se usan open= para mostrarlos.
    # Reflex los monta en el portal del body automáticamente.
    #
    # Si license_needed está activo (flag ON + sin licencia válida), en vez
    # de la UI normal pintamos SOLO el gate. El resto del árbol sigue
    # presente por si el user activa la key: los dialogs ya están montados
    # y on_submit del gate re-dispara on_load sin necesidad de reload.
    main_ui = rx.fragment(
        page,

        # ── Diálogo de recuerdos ──────────────────────────────
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title(State.t["mem_title"]),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger(State.t["mem_tab_facts"], value="facts"),
                        rx.tabs.trigger(State.t["mem_tab_diary"], value="diary"),
                        rx.tabs.trigger(State.t["mem_tab_history"], value="history"),
                        rx.tabs.trigger(State.t["mem_tab_tastes"], value="tastes"),
                        rx.tabs.trigger(State.t["mem_tab_achievements"], value="achievements"),
                    ),
                    rx.tabs.content(
                        rx.box(
                            rx.vstack(rx.foreach(State.facts, fact_item),
                                      align="stretch", spacing="0"),
                            height=MEMORY_HEIGHT, overflow_y="auto", padding="16px",
                        ),
                        value="facts",
                    ),
                    rx.tabs.content(
                        rx.box(
                            rx.vstack(rx.foreach(State.diary, diary_item),
                                      align="stretch", spacing="0"),
                            height=MEMORY_HEIGHT, overflow_y="auto", padding="16px",
                        ),
                        value="diary",
                    ),
                    rx.tabs.content(
                        rx.box(
                            rx.vstack(rx.foreach(State.messages, memory_item),
                                      align="stretch", spacing="1"),
                            height=MEMORY_HEIGHT, overflow_y="auto", padding="16px",
                        ),
                        value="history",
                    ),
                    rx.tabs.content(
                        rx.box(
                            rx.cond(
                                State.tastes,
                                rx.vstack(rx.foreach(State.tastes, taste_item), align="stretch", spacing="0"),
                                rx.vstack(
                                    rx.text(State.t["mem_tastes_empty"], color="#888", font_size="13px"),
                                    rx.text(State.t["mem_tastes_hint"], color="#666", font_size="12px"),
                                    spacing="2", padding_top="20px",
                                ),
                            ),
                            height=MEMORY_HEIGHT, overflow_y="auto", padding="16px",
                        ),
                        value="tastes",
                    ),
                    rx.tabs.content(
                        rx.box(
                            rx.box(
                                rx.foreach(State.achievements_gallery, achievement_card),
                                class_name="achievement-grid",
                            ),
                            height=MEMORY_HEIGHT, overflow_y="auto", padding="16px",
                        ),
                        value="achievements",
                    ),
                    default_value="facts", width="100%",
                ),
                rx.dialog.close(
                    rx.button(State.t["mem_close"], on_click=State.toggle_memories, margin_top="16px"),
                ),
                width=DIALOG_WIDTH,
            ),
            open=State.show_memories,
        ),

        # ── Diálogo de permisos de acciones ──────────────────
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title(
                    rx.hstack(
                        rx.text("🔐", font_size="22px"),
                        rx.text(State.t["act_title"], color=COLOR_PRIMARY, font_weight="bold"),
                        spacing="2", align="center",
                    ),
                ),
                rx.vstack(
                    rx.text(State.t["act_intro"],
                            color=COLOR_TEXT_MUTED, font_size="13px"),
                    rx.box(
                        rx.markdown(State.pending_action_description, color="white"),
                        bg="#0d1117", padding="14px 18px",
                        border_radius="10px", border=f"1px solid {COLOR_PRIMARY}",
                        width="100%",
                    ),
                    rx.text(State.t["act_question"], color=COLOR_TEXT_MUTED, font_size="13px"),
                    rx.hstack(
                        rx.button(
                            State.t["act_yes"],
                            on_click=State.confirm_action,
                            bg=COLOR_PRIMARY, color="black",
                            font_weight="bold", size="3",
                            _hover={"bg": COLOR_PRIMARY_HOVER, "transform": "scale(1.03)"},
                            transition="all 0.2s ease",
                        ),
                        rx.button(
                            State.t["act_no"],
                            on_click=State.reject_action,
                            bg=COLOR_BUTTON_OFF, color=COLOR_BUTTON_OFF_TEXT,
                            font_weight="bold", size="3",
                            _hover={"bg": "#444444", "transform": "scale(1.03)"},
                            transition="all 0.2s ease",
                        ),
                        spacing="4",
                    ),
                    spacing="4", align="start",
                ),
                width="420px", bg=COLOR_BG_CHAT,
            ),
            open=State.show_action_dialog,
        ),

        # ── Diálogo de Settings (3 secciones claras) ────────
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title(
                    rx.hstack(
                        rx.text("⚙", font_size="20px"),
                        rx.text(State.t["settings_title"], color=COLOR_PRIMARY, font_weight="bold"),
                        spacing="2", align="center",
                    ),
                ),
                rx.form(
                    rx.vstack(
                        # ═══════════════════════════════════════════════
                        #  REQUIRED — Grok key status
                        # ═══════════════════════════════════════════════
                        rx.box(
                            rx.vstack(
                                rx.text(State.t["settings_required_heading"],
                                        color="#ff9aee", font_weight="700", font_size="14px",
                                        letter_spacing="0.05em"),
                                rx.text(State.t["settings_grok_label"],
                                        color="#ddd", font_size="13px", font_weight="500"),
                                rx.cond(
                                    State.grok_key_status == "configured",
                                    rx.text(State.t["settings_grok_configured"],
                                            color="#88ff99", font_size="12px"),
                                    rx.text(State.t["settings_grok_missing"],
                                            color="#ff8080", font_size="12px"),
                                ),
                                rx.text(State.t["settings_grok_consequence"],
                                        color="#bbb", font_size="11px", font_style="italic", line_height="1.4"),
                                rx.text(State.t["settings_grok_hint"],
                                        color="#666", font_size="11px", line_height="1.4"),
                                spacing="2", align="stretch",
                            ),
                            padding="14px 16px",
                            bg="rgba(255,154,238,0.05)",
                            border="1px solid rgba(255,154,238,0.2)",
                            border_radius="10px",
                            width="100%",
                        ),

                        # ═══════════════════════════════════════════════
                        #  LLM PROVIDER — Elige xAI o OpenRouter (multi-model)
                        # ═══════════════════════════════════════════════
                        rx.box(
                            rx.vstack(
                                rx.text(State.t["settings_provider_heading"],
                                        color="#9acaff", font_weight="700", font_size="14px",
                                        letter_spacing="0.05em"),
                                rx.text(State.t["settings_provider_label"],
                                        color="#ddd", font_size="13px", font_weight="500"),

                                # Radio selector: xAI vs OpenRouter
                                rx.radio(
                                    ["xai", "openrouter"],
                                    value=State.llm_provider,
                                    on_change=State.set_llm_provider,
                                    direction="column",
                                    size="2",
                                ),
                                rx.cond(
                                    State.is_openrouter_provider,
                                    rx.text(State.t["settings_provider_openrouter"],
                                            color="#9acaff", font_size="11px", font_style="italic"),
                                    rx.text(State.t["settings_provider_xai"],
                                            color="#ccc", font_size="11px", font_style="italic"),
                                ),

                                # Si OpenRouter: pedir la key + model picker
                                rx.cond(
                                    State.is_openrouter_provider,
                                    rx.vstack(
                                        rx.text(State.t["settings_openrouter_key_label"],
                                                color="#ddd", font_size="12px", font_weight="500",
                                                margin_top="8px"),
                                        rx.input(
                                            placeholder=State.t["settings_openrouter_key_placeholder"],
                                            value=State.openrouter_key,
                                            on_change=State.set_openrouter_key,
                                            type="password",
                                            bg="rgba(255,255,255,0.04)",
                                            color="white",
                                            border="1px solid rgba(255,255,255,0.12)",
                                            border_radius="8px",
                                            padding="8px 10px",
                                            font_size="12px",
                                            width="100%",
                                            font_family="'JetBrains Mono', 'Consolas', monospace",
                                        ),
                                        rx.text(State.t["settings_openrouter_key_hint"],
                                                color="#888", font_size="10px", line_height="1.4"),

                                        rx.text(State.t["settings_model_label"],
                                                color="#ddd", font_size="12px", font_weight="500",
                                                margin_top="8px"),
                                        rx.select(
                                            [m[0] for m in OPENROUTER_MODELS],
                                            value=State.llm_model_display,
                                            on_change=State.set_llm_model,
                                            size="2",
                                            width="100%",
                                        ),
                                        rx.text(State.t["settings_model_hint"],
                                                color="#888", font_size="10px", line_height="1.4"),
                                        spacing="1", align="stretch", width="100%",
                                    ),
                                    rx.vstack(
                                        rx.text(State.t["settings_model_label"],
                                                color="#ddd", font_size="12px", font_weight="500",
                                                margin_top="8px"),
                                        rx.select(
                                            [m[0] for m in XAI_MODELS],
                                            value=State.llm_model_display,
                                            on_change=State.set_llm_model,
                                            size="2",
                                            width="100%",
                                        ),
                                        rx.text(State.t["settings_model_hint"],
                                                color="#888", font_size="10px", line_height="1.4"),
                                        spacing="1", align="stretch", width="100%",
                                    ),
                                ),
                                spacing="2", align="stretch",
                            ),
                            padding="14px 16px",
                            bg="rgba(154,202,255,0.05)",
                            border="1px solid rgba(154,202,255,0.2)",
                            border_radius="10px",
                            width="100%",
                        ),

                        # ═══════════════════════════════════════════════
                        #  OPTIONAL — ElevenLabs (Premium Voice)
                        # ═══════════════════════════════════════════════
                        rx.box(
                            rx.vstack(
                                rx.text(State.t["settings_optional_heading"],
                                        color="#ffa500", font_weight="700", font_size="14px",
                                        letter_spacing="0.05em"),

                                # Consecuencias: sin / con
                                rx.vstack(
                                    rx.hstack(
                                        rx.text(State.t["settings_elevenlabs_without"],
                                                color="#888", font_size="11px", font_weight="600", min_width="60px"),
                                        rx.text(State.t["settings_elevenlabs_without_desc"],
                                                color="#aaa", font_size="11px", line_height="1.4"),
                                        spacing="2", align="start",
                                    ),
                                    rx.hstack(
                                        rx.text(State.t["settings_elevenlabs_with"],
                                                color="#ffa500", font_size="11px", font_weight="600", min_width="60px"),
                                        rx.text(State.t["settings_elevenlabs_with_desc"],
                                                color="#ddd", font_size="11px", line_height="1.4"),
                                        spacing="2", align="start",
                                    ),
                                    spacing="1", align="stretch", padding_y="2px",
                                ),

                                rx.text(State.t["settings_elevenlabs_label"],
                                        color="#ccc", font_size="12px", font_weight="500", margin_top="6px"),
                                rx.input(
                                    name="elevenlabs_key",
                                    type="password",
                                    default_value=State.elevenlabs_key,
                                    placeholder=State.t["settings_elevenlabs_placeholder"],
                                    width="100%",
                                    bg="#0a0a0a",
                                    border="1px solid #333",
                                    color="white",
                                    padding="8px 10px",
                                    border_radius="6px",
                                    font_family="Consolas, monospace",
                                    font_size="11px",
                                ),
                                rx.text(State.t["settings_elevenlabs_hint"],
                                        color="#666", font_size="10px", line_height="1.4"),

                                rx.text(State.t["settings_voice_id_label"],
                                        color="#ccc", font_size="12px", font_weight="500", margin_top="4px"),
                                rx.input(
                                    name="voice_id",
                                    type="text",
                                    default_value=State.voice_id,
                                    placeholder="EXAVITQu4vr4xnSDxMaL",
                                    width="100%",
                                    bg="#0a0a0a",
                                    border="1px solid #333",
                                    color="white",
                                    padding="8px 10px",
                                    border_radius="6px",
                                    font_family="Consolas, monospace",
                                    font_size="11px",
                                ),
                                rx.text(State.t["settings_voice_id_hint"],
                                        color="#666", font_size="10px", line_height="1.4"),

                                spacing="2", align="stretch",
                            ),
                            padding="14px 16px",
                            bg="rgba(255,165,0,0.04)",
                            border="1px solid rgba(255,165,0,0.2)",
                            border_radius="10px",
                            width="100%",
                        ),

                        # ═══════════════════════════════════════════════
                        #  INCLUDED — Whisper local
                        # ═══════════════════════════════════════════════
                        rx.box(
                            rx.vstack(
                                rx.text(State.t["settings_included_heading"],
                                        color="#88ff99", font_weight="700", font_size="14px",
                                        letter_spacing="0.05em"),
                                rx.hstack(
                                    rx.text(State.t["settings_whisper_label"],
                                            color="#ddd", font_size="13px", font_weight="500"),
                                    rx.text(State.t["settings_whisper_ready"],
                                            color="#88ff99", font_size="12px", font_weight="600"),
                                    spacing="3", align="center",
                                ),
                                rx.text(State.t["settings_whisper_desc"],
                                        color="#aaa", font_size="11px", line_height="1.5"),
                                spacing="2", align="stretch",
                            ),
                            padding="14px 16px",
                            bg="rgba(136,255,153,0.04)",
                            border="1px solid rgba(136,255,153,0.2)",
                            border_radius="10px",
                            width="100%",
                        ),

                        # ═══════════════════════════════════════════════
                        #  USAGE — contador firmado (refund eligibility)
                        # ═══════════════════════════════════════════════
                        rx.box(
                            rx.vstack(
                                rx.text(State.t["settings_usage_heading"],
                                        color="#bbbbbb", font_weight="700", font_size="13px",
                                        letter_spacing="0.05em"),
                                rx.hstack(
                                    rx.text(State.t["settings_usage_label"],
                                            color="#cccccc", font_size="13px", font_weight="500"),
                                    rx.spacer(),
                                    rx.cond(
                                        State.stats_tampered,
                                        rx.text("???",
                                                color="#ff6b6b", font_size="14px",
                                                font_weight="700", font_family="monospace"),
                                        rx.text(State.stats_total_messages.to_string(),
                                                color=COLOR_PRIMARY, font_size="14px",
                                                font_weight="700", font_family="monospace"),
                                    ),
                                    spacing="2", align="center", width="100%",
                                ),
                                rx.cond(
                                    State.stats_tampered,
                                    rx.text(State.t["settings_usage_tampered"],
                                            color="#ff8080", font_size="11px",
                                            line_height="1.5"),
                                    rx.text(State.t["settings_usage_hint"],
                                            color="#888", font_size="11px",
                                            line_height="1.5"),
                                ),
                                spacing="2", align="stretch",
                            ),
                            padding="14px 16px",
                            bg="rgba(255,255,255,0.03)",
                            border="1px solid rgba(255,255,255,0.08)",
                            border_radius="10px",
                            width="100%",
                        ),

                        # ═══════════════════════════════════════════════
                        #  Botones de acción
                        # ═══════════════════════════════════════════════
                        rx.hstack(
                            rx.button(
                                State.t["settings_save"], type="submit",
                                bg=COLOR_PRIMARY, color="black",
                                font_weight="bold", size="3",
                                _hover={"bg": COLOR_PRIMARY_HOVER},
                                cursor="pointer",
                            ),
                            rx.button(
                                "🔊 " + State.t["settings_test_voice"],
                                type="button",
                                on_click=rx.call_script(
                                    "window.AshleyVoice && window.AshleyVoice.testSpeak("
                                    "(document.getElementById('ashley-voice-state')||{}).getAttribute "
                                    "? document.getElementById('ashley-voice-state').getAttribute('data-test-text') "
                                    ": 'Testing voice.')"
                                ),
                                bg="rgba(255,255,255,0.06)",
                                color=COLOR_PRIMARY,
                                border="1px solid rgba(255,154,238,0.4)",
                                size="3",
                                _hover={"bg": "rgba(255,154,238,0.12)"},
                                cursor="pointer",
                            ),
                            rx.spacer(),
                            rx.dialog.close(
                                rx.button(
                                    State.t["settings_close"],
                                    on_click=State.toggle_settings,
                                    bg="transparent",
                                    color="#888",
                                    size="3",
                                    _hover={"bg": "rgba(255,255,255,0.04)", "color": "#ddd"},
                                    cursor="pointer",
                                ),
                            ),
                            spacing="3", width="100%",
                        ),
                        spacing="3", align="stretch", width="100%",
                    ),
                    on_submit=State.save_voice_settings,
                    width="100%",
                ),
                width="600px",
                max_height="85vh",
                overflow_y="auto",
                bg=COLOR_BG_CHAT,
            ),
            open=State.show_settings,
        ),
    )

    return rx.cond(
        State.license_needed,
        license_gate(),
        main_ui,
    )


import logging as _logging
_logging.basicConfig(level=_logging.WARNING, format="%(name)s %(levelname)s: %(message)s")

app = rx.App(
    head_components=[
        rx.el.script(src="/ashley_fx.js", defer=True),
        rx.el.script(src="/ashley_voice.js", defer=True),
    ],
)
app.add_page(index, title="Ashley", on_load=State.on_load)


# ── API endpoints (extraídos a api_routes.py) ──
from .api_routes import register_routes as _register_routes
_register_routes(app)
