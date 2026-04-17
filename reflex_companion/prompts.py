"""
prompts.py — Dispatcher de idiomas para los prompts de Ashley.

Selecciona la version correcta de build_system_prompt / build_initiative_prompt
segun el idioma activo. El contenido real vive en prompts_es.py y prompts_en.py.
"""

from . import prompts_en, prompts_es


def _impl(lang: str):
    l = (lang or "en").strip().lower()[:2]
    return prompts_en if l == "en" else prompts_es


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
    )


def build_initiative_prompt(facts: list[dict], diary: list[dict], lang: str = "en") -> str:
    return _impl(lang).build_initiative_prompt(facts, diary)
