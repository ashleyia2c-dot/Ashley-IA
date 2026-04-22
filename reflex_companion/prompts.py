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
) -> str:
    return _impl(lang).build_system_prompt(
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


def build_initiative_prompt(facts: list[dict], diary: list[dict], lang: str = "en") -> str:
    return _impl(lang).build_initiative_prompt(facts, diary)
