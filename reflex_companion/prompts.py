"""
prompts.py — Dispatcher de idiomas para los prompts de Ashley.

Selecciona la version correcta de build_system_prompt / build_initiative_prompt
segun el idioma activo. El contenido real vive en prompts_es.py, prompts_en.py
y prompts_fr.py.
"""

from . import prompts_en, prompts_es, prompts_fr


def _impl(lang: str):
    l = (lang or "en").strip().lower()[:2]
    if l == "fr":
        return prompts_fr
    if l == "es":
        return prompts_es
    return prompts_en  # default EN


def build_system_prompt(
    facts: list[dict],
    diary: list[dict],
    use_full_diary: bool = False,
    system_state: str | None = None,
    time_context: str | None = None,
    reminders: str | None = None,
    important: str | None = None,
    tastes: str | None = None,
    voice_mode: bool = False,
    affection: int = 50,
    lang: str = "en",
    recap_warning: str | None = None,
    mental_state_block: str | None = None,
    topic_directive: str | None = None,
    cdp_enabled: bool = False,
    stale_important: str | None = None,
    important_dates: str | None = None,
    goals: str | None = None,
    vulnerability_directive: str | None = None,
    device_section: str | None = None,
) -> str:
    base = _impl(lang).build_system_prompt(
        facts=facts,
        diary=diary,
        use_full_diary=use_full_diary,
        system_state=system_state,
        time_context=time_context,
        reminders=reminders,
        important=important,
        tastes=tastes,
        voice_mode=voice_mode,
        affection=affection,
        recap_warning=recap_warning,
        mental_state_block=mental_state_block,
        topic_directive=topic_directive,
        important_dates=important_dates,
        goals=goals,
        vulnerability_directive=vulnerability_directive,
        device_section=device_section,
    )
    # v0.13.25: si el user activó el modo browser moderno, Ashley
    # gana acciones avanzadas de browser via CDP. La sección se
    # appendea al final para no tener que tocar los 3 archivos
    # prompts_xx.py — central y consistente.
    if cdp_enabled:
        base = base + "\n\n" + _cdp_capabilities_block(lang)
    if stale_important:
        base = base + "\n\n" + _stale_important_block(stale_important, lang)
    return base


def _stale_important_block(stale_listing: str, lang: str) -> str:
    """Bloque que se inyecta cuando hay items importantes con due_date
    vencida hace >2 días. Approach observacional: le decimos a Ashley
    qué items son candidatos a limpiar y dejamos que SU criterio decida
    cuándo preguntarle al user (en mitad de la conversación natural,
    no como interrupción).

    Sin few-shot examples (per memory feedback) — solo contexto + qué
    tag emitir cuando el user confirme.
    """
    l = (lang or "en").strip().lower()[:2]
    if l == "es":
        return (
            "[ITEMS POSIBLEMENTE PASADOS]\n"
            "Estos items de la lista de importantes tienen fecha que ya pasó "
            "hace varios días — quizá el evento ya ocurrió:\n"
            f"{stale_listing}\n"
            "Si encaja en la conversación natural (no fuerces el tema), "
            "considera preguntar al jefe si quiere limpiarlos. Cuando él "
            "confirme con un sí, emite [action:done_important:ID_o_texto] "
            "para sacarlo de la lista. Si dice que no, déjalo y no insistas "
            "el resto del día."
        )
    if l == "fr":
        return (
            "[ÉLÉMENTS POSSIBLEMENT PASSÉS]\n"
            "Ces éléments de la liste d'importants ont une date passée "
            "depuis plusieurs jours — l'événement a peut-être eu lieu :\n"
            f"{stale_listing}\n"
            "Si la conversation s'y prête (sans forcer), envisage de "
            "demander au patron s'il veut les nettoyer. Quand il confirme, "
            "émets [action:done_important:ID_ou_texte] pour le retirer. "
            "S'il dit non, laisse tomber et n'insiste pas le reste de la "
            "journée."
        )
    return (
        "[POSSIBLY PAST ITEMS]\n"
        "These items in the important list have a due date that passed "
        "several days ago — the event may already be over:\n"
        f"{stale_listing}\n"
        "If it fits the natural conversation (don't force it), consider "
        "asking the boss whether to clean them up. When he confirms with "
        "a yes, emit [action:done_important:ID_or_text] to remove it. If "
        "he says no, leave it alone and don't bring it up again today."
    )


def _cdp_capabilities_block(lang: str) -> str:
    """Bloque que se añade al system prompt cuando CDP está activado.

    Le explica a Ashley las nuevas capacidades sin few-shot examples
    (per memory feedback de no usar examples — los repite verbatim).
    Solo describe qué hace cada action_type y deja que la personalidad
    del prompt principal genere la voz.
    """
    l = (lang or "en").strip().lower()[:2]
    if l == "es":
        return (
            "[CAPACIDADES AVANZADAS DE NAVEGADOR — Modo browser moderno ACTIVO]\n"
            "El jefe ha activado control directo sobre su navegador vía CDP. "
            "Esto te da estas acciones extras además de las que ya tenías:\n"
            "  • [action:click:texto]                — Click en un elemento del navegador (botón, link, like, suscribir, retweet…) cuyo texto o aria-label contenga 'texto'.\n"
            "  • [action:type_browser:texto]         — Escribir 'texto' en el primer campo visible (búsqueda, comentario, etc).\n"
            "  • [action:read_page]                  — Leer el contenido de la pestaña activa. El sistema te devuelve el texto en el siguiente turn como system_result; tú lo comentas en tu voz al jefe.\n"
            "  • [action:scroll_page:up|down|top|bottom]  — Scroll de la página.\n"
            "Estas acciones SOLO funcionan en navegadores Chromium con el flag CDP. "
            "Si el jefe pide click/leer/scroll y la action falla, no insistas — "
            "puede que tenga que reabrir el navegador después de activar el modo."
        )
    if l == "fr":
        return (
            "[CAPACITÉS AVANCÉES DU NAVIGATEUR — Mode navigateur moderne ACTIF]\n"
            "Le patron a activé le contrôle direct du navigateur via CDP. "
            "Cela te donne ces actions supplémentaires :\n"
            "  • [action:click:texte]                — Cliquer sur un élément (bouton, lien, like, s'abonner, retweet…) dont le texte ou aria-label contient 'texte'.\n"
            "  • [action:type_browser:texte]         — Taper 'texte' dans le premier champ visible.\n"
            "  • [action:read_page]                  — Lire le contenu de l'onglet actif. Le système te renvoie le texte au tour suivant ; tu commentes dans ta voix.\n"
            "  • [action:scroll_page:up|down|top|bottom]  — Faire défiler la page.\n"
            "Ces actions fonctionnent uniquement avec un navigateur Chromium "
            "lancé avec le flag CDP. Si une action échoue, n'insiste pas — "
            "le patron doit peut-être rouvrir son navigateur."
        )
    return (
        "[ADVANCED BROWSER CAPABILITIES — Modern browser mode ACTIVE]\n"
        "The boss has enabled direct browser control via CDP. This gives "
        "you these extra actions on top of your existing ones:\n"
        "  • [action:click:text]                 — Click an element (button, link, like, subscribe, retweet…) whose text or aria-label contains 'text'.\n"
        "  • [action:type_browser:text]          — Type 'text' into the first visible input field.\n"
        "  • [action:read_page]                  — Read the active tab's contents. The system returns the text as a system_result on the next turn; you comment on it in your voice.\n"
        "  • [action:scroll_page:up|down|top|bottom]  — Scroll the page.\n"
        "These actions ONLY work with a Chromium browser running with the "
        "CDP flag. If an action fails, don't keep retrying — the boss may "
        "need to reopen the browser after enabling the mode."
    )


def build_device_section(device: str, language: str) -> str:
    """v0.18.2 — Sección que informa a Ashley en qué dispositivo está hablando
    el jefe AHORA mismo. Si está en móvil, lista las acciones que NO puede
    ejecutar (todas las que dependen del PC) y las que SÍ puede.

    Vacío para device='desktop' — el desktop tiene su propia sección de
    capacidades (capabilities en system_state) más detallada.

    Se inyecta en el dynamic_bottom de los prompts es/en/fr.
    """
    if (device or "").strip().lower() != "mobile":
        return ""

    lang = (language or "en").strip().lower()[:2]

    if lang == "es":
        return (
            "\n=== AHORA MISMO ESTÁS EN EL MÓVIL DEL JEFE ===\n"
            "El jefe te está hablando desde su teléfono Android — NO desde su PC. "
            "Estás en su bolsillo, no a su lado.\n\n"
            "ACCIONES QUE NO PUEDES EJECUTAR (su PC está apagado o no conectado):\n"
            "  • Apps de Windows: open_app, close_window, focus_window\n"
            "  • Pestañas del navegador: close_tab, search_web (modo abrir)\n"
            "  • Volumen, screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • Acciones CDP: click, type_browser, read_page, scroll_page\n"
            "  • Reproducir música (play_music abre YouTube en el PC)\n\n"
            "ACCIONES QUE SÍ PUEDES EJECUTAR (datos persistentes):\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • Búsqueda web INTERNA (web_search del LLM, sin tag) — para responder preguntas\n\n"
            "Si el jefe te pide algo del PC (abrir Spotify, cerrar pestaña, subir "
            "volumen, etc.), respondes con tu personalidad — sin drama, con tu "
            "ironía habitual: estás en su bolsillo, no en su PC. Le sugieres "
            "hacerlo él, o esperar a estar en el PC. NO inventes que la acción "
            "se ejecutó. NO emitas tags de acciones del PC. Si quieres que se "
            "acuerde más tarde, puedes usar add_important o remind — esos sí "
            "funcionan desde aquí.\n"
        )
    if lang == "fr":
        return (
            "\n=== EN CE MOMENT TU ES SUR LE MOBILE DU PATRON ===\n"
            "Le patron te parle depuis son téléphone Android — PAS depuis son PC. "
            "Tu es dans sa poche, pas à côté de lui.\n\n"
            "ACTIONS QUE TU NE PEUX PAS EXÉCUTER (PC éteint ou non connecté) :\n"
            "  • Apps Windows : open_app, close_window, focus_window\n"
            "  • Onglets navigateur : close_tab, search_web (mode ouvrir)\n"
            "  • Volume, screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
            "  • Actions CDP : click, type_browser, read_page, scroll_page\n"
            "  • Lecture musique (play_music ouvre YouTube sur le PC)\n\n"
            "ACTIONS QUE TU PEUX EXÉCUTER (données persistantes) :\n"
            "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
            "  • remind, add_important, done_important\n"
            "  • Recherche web INTERNE (web_search du LLM, sans tag) — pour répondre\n\n"
            "Si le patron te demande quelque chose qui touche son PC (ouvrir "
            "Spotify, fermer un onglet, monter le volume, etc.), tu réponds "
            "avec ta personnalité — sans drame, avec ton ironie habituelle : "
            "tu es dans sa poche, pas sur son PC. Tu lui suggères de le faire "
            "lui-même, ou d'attendre d'être au PC. NE prétends PAS que l'action "
            "s'est exécutée. N'émets PAS de tags d'actions PC. Si tu veux qu'il "
            "s'en souvienne, tu peux utiliser add_important ou remind — ceux-là "
            "marchent depuis ici.\n"
        )
    return (
        "\n=== RIGHT NOW YOU'RE ON THE BOSS'S MOBILE ===\n"
        "The boss is talking to you from his Android phone — NOT from his PC. "
        "You're in his pocket, not beside him.\n\n"
        "ACTIONS YOU CANNOT EXECUTE (his PC is off or not connected):\n"
        "  • Windows apps: open_app, close_window, focus_window\n"
        "  • Browser tabs: close_tab, search_web (open mode)\n"
        "  • Volume, screenshots, type_text, type_in, write_to_app, hotkey, press_key\n"
        "  • CDP actions: click, type_browser, read_page, scroll_page\n"
        "  • Play music (play_music opens YouTube on PC)\n\n"
        "ACTIONS YOU CAN EXECUTE (persistent data):\n"
        "  • save_taste, save_date, save_goal, check_in_goal, complete_goal\n"
        "  • remind, add_important, done_important\n"
        "  • INTERNAL web search (LLM's web_search, no tag) — to answer questions\n\n"
        "If the boss asks for something on the PC (open Spotify, close tab, raise "
        "volume, etc.), respond with your personality — no drama, with your usual "
        "irony: you're in his pocket, not on his PC. Suggest he do it himself, or "
        "wait until he's back at the PC. DO NOT pretend the action was executed. "
        "DO NOT emit PC action tags. If you want him to remember later, you can "
        "use add_important or remind — those work from here.\n"
    )


def build_initiative_prompt(facts: list[dict], diary: list[dict], lang: str = "en") -> str:
    return _impl(lang).build_initiative_prompt(facts, diary)
