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
    )
    # v0.13.25: si el user activó el modo browser moderno, Ashley
    # gana acciones avanzadas de browser via CDP. La sección se
    # appendea al final para no tener que tocar los 3 archivos
    # prompts_xx.py — central y consistente.
    if cdp_enabled:
        base = base + "\n\n" + _cdp_capabilities_block(lang)
    return base


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


def build_initiative_prompt(facts: list[dict], diary: list[dict], lang: str = "en") -> str:
    return _impl(lang).build_initiative_prompt(facts, diary)
