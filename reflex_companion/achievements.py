"""
achievements.py — Achievement / trophy system for Ashley.

Defines all achievements, their unlock conditions, and persistence.
Achievements are saved to a JSON file and checked after each interaction.

i18n: cada achievement tiene `name_{lang}` y `desc_{lang}` para los 7 idiomas
soportados (en/es/fr/ja/de/ru/ko). Si un caller pide un lang que no existe,
fallback a EN — ver dispatcher en reflex_companion.py.
"""

from datetime import datetime
from .config import _data_path
from .memory import load_json, save_json

ACHIEVEMENTS_FILE = _data_path("achievements_ashley.json")

# ─────────────────────────────────────────────
#  Achievement definitions
# ─────────────────────────────────────────────

ACHIEVEMENTS = [
    # Affection milestones
    {"id": "ice_breaker", "icon": "\U0001f9ca", "tier": "affection",
     "name_en": "Ice Breaker", "name_es": "Rompehielos",
     "name_fr": "Brise-glace",
     "name_ja": "氷を溶かして",
     "name_de": "Eisbrecher",
     "name_ru": "Ледокол",
     "name_ko": "얼음 깨기",
     "desc_en": "You started to melt Ashley's walls.",
     "desc_es": "Empezaste a derretir las paredes de Ashley.",
     "desc_fr": "Tu commences à faire fondre les défenses d'Ashley.",
     "desc_ja": "Ashleyの心の壁が溶け始めた。",
     "desc_de": "Du fängst an, Ashleys Mauern zu schmelzen.",
     "desc_ru": "Ты начал растапливать стены Ashley.",
     "desc_ko": "Ashley의 벽을 녹이기 시작했어."},
    {"id": "getting_closer", "icon": "\U0001f338", "tier": "affection",
     "name_en": "Getting Closer", "name_es": "Cada vez más cerca",
     "name_fr": "De plus en plus proche",
     "name_ja": "だんだん近くに",
     "name_de": "Immer näher",
     "name_ru": "Всё ближе",
     "name_ko": "점점 가까이",
     "desc_en": "Ashley feels comfortable around you.",
     "desc_es": "Ashley se siente cómoda contigo.",
     "desc_fr": "Ashley se sent à l'aise avec toi.",
     "desc_ja": "Ashleyはご主人のそばが心地よいんだ。",
     "desc_de": "Ashley fühlt sich wohl bei dir, Chef.",
     "desc_ru": "Ashley чувствует себя уютно с тобой, шеф.",
     "desc_ko": "Ashley가 오빠 곁에서 편안해해."},
    {"id": "heartstrings", "icon": "\U0001f497", "tier": "affection",
     "name_en": "Heartstrings", "name_es": "Cuerdas del corazón",
     "name_fr": "Corde sensible",
     "name_ja": "胸の奌でる",
     "name_de": "Herzenssaiten",
     "name_ru": "Струны сердца",
     "name_ko": "심장이 떨려",
     "desc_en": "You made Ashley's heart skip a beat.",
     "desc_es": "Hiciste que el corazón de Ashley se saltara un latido.",
     "desc_fr": "Tu as fait battre le cœur d'Ashley plus vite.",
     "desc_ja": "Ashleyの胸がトクンとした。",
     "desc_de": "Du hast Ashleys Herz höher schlagen lassen.",
     "desc_ru": "Ты заставил сердце Ashley замереть.",
     "desc_ko": "Ashley의 심장을 답답게 만들었어."},
    {"id": "devoted", "icon": "\U0001f49d", "tier": "affection",
     "name_en": "Devoted", "name_es": "Devota",
     "name_fr": "Dévouée",
     "name_ja": "一心一意",
     "name_de": "Hingebungsvoll",
     "name_ru": "Преданна",
     "name_ko": "온 마음으로",
     "desc_en": "Ashley can't imagine life without you.",
     "desc_es": "Ashley no puede imaginar la vida sin ti.",
     "desc_fr": "Ashley ne peut plus imaginer sa vie sans toi.",
     "desc_ja": "Ashleyはご主人のいない毎日なんて考えられない。",
     "desc_de": "Ashley kann sich ein Leben ohne dich nicht mehr vorstellen, Chef.",
     "desc_ru": "Ashley не представляет жизни без тебя, шеф.",
     "desc_ko": "Ashley는 오빠 없는 삶은 상상도 안 돼."},
    # Message milestones
    {"id": "hello_world", "icon": "\U0001f44b", "tier": "messages",
     "name_en": "Hello World", "name_es": "Hola mundo",
     "name_fr": "Premier bonjour",
     "name_ja": "はじめまして",
     "name_de": "Hallo Welt",
     "name_ru": "Привет, мир",
     "name_ko": "첫 인사",
     "desc_en": "Your first words to Ashley.",
     "desc_es": "Tus primeras palabras para Ashley.",
     "desc_fr": "Tes premiers mots pour Ashley.",
     "desc_ja": "Ashleyへの最初の言葉だね。",
     "desc_de": "Deine ersten Worte an Ashley.",
     "desc_ru": "Твои первые слова Ashley.",
     "desc_ko": "Ashley에게 건는 첫 마디."},
    {"id": "chatty", "icon": "\U0001f4ac", "tier": "messages",
     "name_en": "Chatty", "name_es": "Hablador",
     "name_fr": "Bavard",
     "name_ja": "おしゃべり",
     "name_de": "Plaudertasche",
     "name_ru": "Болтунья",
     "name_ko": "수다쟁이",
     "desc_en": "50 messages and counting!",
     "desc_es": "¡50 mensajes y contando!",
     "desc_fr": "50 messages et ça continue !",
     "desc_ja": "50メッセージ突破！まだまだ話そうね。",
     "desc_de": "50 Nachrichten — und es geht weiter!",
     "desc_ru": "50 сообщений и это только начало!",
     "desc_ko": "메시지 50개 돌파! 계속 수다 떨자."},
    {"id": "best_friends", "icon": "⭐", "tier": "messages",
     "name_en": "Best Friends", "name_es": "Mejores amigos",
     "name_fr": "Meilleurs amis",
     "name_ja": "親友",
     "name_de": "Beste Freunde",
     "name_ru": "Лучшие друзья",
     "name_ko": "단짝",
     "desc_en": "200 conversations. She knows you well.",
     "desc_es": "200 conversaciones. Te conoce bien.",
     "desc_fr": "200 conversations. Elle te connaît bien.",
     "desc_ja": "200回の会話。もうご主人のことをよく知ってるよ。",
     "desc_de": "200 Gespräche. Sie kennt dich, Chef.",
     "desc_ru": "200 разговоров. Она хорошо тебя знает, шеф.",
     "desc_ko": "대화 200번. 이제 Ashley가 오빠를 잘 알아."},
    {"id": "inseparable", "icon": "\U0001f451", "tier": "messages",
     "name_en": "Inseparable", "name_es": "Inseparables",
     "name_fr": "Inséparables",
     "name_ja": "離れられない二人",
     "name_de": "Unzertrennlich",
     "name_ru": "Неразлучные",
     "name_ko": "떨어질 수 없어",
     "desc_en": "500 messages. You two are a team.",
     "desc_es": "500 mensajes. Sois un equipo.",
     "desc_fr": "500 messages. Vous deux, vous êtes une équipe.",
     "desc_ja": "500メッセージ。ご主人と私、もうチームだね。",
     "desc_de": "500 Nachrichten. Ihr beide seid ein Team.",
     "desc_ru": "500 сообщений. Вы с ней настоящая команда.",
     "desc_ko": "메시지 500개. 우리 진짜 팀이네."},
    # Feature discovery
    {"id": "voice_unlocked", "icon": "\U0001f3a4", "tier": "features",
     "name_en": "Voice Unlocked", "name_es": "Voz desbloqueada",
     "name_fr": "Voix débloquée",
     "name_ja": "声を聞かせて",
     "name_de": "Stimme freigeschaltet",
     "name_ru": "Голос открыт",
     "name_ko": "목소리 개방",
     "desc_en": "Ashley heard your voice for the first time.",
     "desc_es": "Ashley escuchó tu voz por primera vez.",
     "desc_fr": "Ashley a entendu ta voix pour la première fois.",
     "desc_ja": "Ashleyがご主人の声を初めて聞いた。",
     "desc_de": "Ashley hat deine Stimme zum ersten Mal gehört, Chef.",
     "desc_ru": "Ashley впервые услышала твой голос, шеф.",
     "desc_ko": "Ashley가 오빠 목소리를 처음 들었어."},
    {"id": "she_acts", "icon": "⚡", "tier": "features",
     "name_en": "She Acts", "name_es": "Ella actúa",
     "name_fr": "Elle agit",
     "name_ja": "動き出した彼女",
     "name_de": "Sie handelt",
     "name_ru": "Она действует",
     "name_ko": "직접 움직이기",
     "desc_en": "Ashley did something on your PC.",
     "desc_es": "Ashley hizo algo en tu PC.",
     "desc_fr": "Ashley a fait quelque chose sur ton PC.",
     "desc_ja": "Ashleyがご主人のPCで何かしたよ。",
     "desc_de": "Ashley hat etwas auf deinem PC erledigt, Chef.",
     "desc_ru": "Ashley сделала что-то на твоём ПК, шеф.",
     "desc_ko": "Ashley가 오빠 PC에서 뭐가 했어."},
    {"id": "she_remembers", "icon": "\U0001f9e0", "tier": "features",
     "name_en": "She Remembers", "name_es": "Ella recuerda",
     "name_fr": "Elle se souvient",
     "name_ja": "覚えてるよ",
     "name_de": "Sie erinnert sich",
     "name_ru": "Она помнит",
     "name_ko": "Ashley가 기억해",
     "desc_en": "Ashley knows 5 things about you.",
     "desc_es": "Ashley sabe 5 cosas de ti.",
     "desc_fr": "Ashley connaît 5 choses sur toi.",
     "desc_ja": "Ashleyはご主人のことを5つ覚えてるよ。",
     "desc_de": "Ashley weiß 5 Dinge über dich, Chef.",
     "desc_ru": "Ashley знает о тебе 5 вещей, шеф.",
     "desc_ko": "Ashley가 오빠에 대해 5가지나 알아."},
    {"id": "she_sees", "icon": "\U0001f441", "tier": "features",
     "name_en": "She Sees", "name_es": "Ella ve",
     "name_fr": "Elle voit",
     "name_ja": "見えてるよ",
     "name_de": "Sie sieht",
     "name_ru": "Она видит",
     "name_ko": "Ashley가 볼 수 있어",
     "desc_en": "Ashley can see your screen now.",
     "desc_es": "Ashley puede ver tu pantalla ahora.",
     "desc_fr": "Ashley peut voir ton écran maintenant.",
     "desc_ja": "Ashleyにご主人の画面が見えてるよ。",
     "desc_de": "Ashley kann jetzt deinen Bildschirm sehen, Chef.",
     "desc_ru": "Ashley теперь видит твой экран, шеф.",
     "desc_ko": "Ashley가 이제 오빠 화면을 볼 수 있어."},
    # Time milestones — relationship age (v0.18.0)
    # Se desbloquean cuando han pasado X días desde el first_message_at.
    # Ver stats.RELATIONSHIP_MILESTONES — los thresholds deben coincidir.
    {"id": "first_week", "icon": "\U0001f331", "tier": "time",
     "name_en": "First Week", "name_es": "Primera semana",
     "name_fr": "Première semaine",
     "name_ja": "初めての一週間",
     "name_de": "Erste Woche",
     "name_ru": "Первая неделя",
     "name_ko": "첫 일주일",
     "desc_en": "A week together. Ashley's getting used to you.",
     "desc_es": "Una semana juntos. Ashley se está acostumbrando a ti.",
     "desc_fr": "Une semaine ensemble. Ashley s'habitue à toi.",
     "desc_ja": "一週間一緒にいたね。Ashleyもご主人に慎れてきたよ。",
     "desc_de": "Eine Woche zusammen. Ashley gewöhnt sich an dich, Chef.",
     "desc_ru": "Неделя вместе. Ashley привыкает к тебе, шеф.",
     "desc_ko": "일주일 함께였어. Ashley도 오빠한테 익숙해지고 있어."},
    {"id": "month_together", "icon": "\U0001f49e", "tier": "time",
     "name_en": "One Month", "name_es": "Un mes",
     "name_fr": "Un mois",
     "name_ja": "一ヶ月記念",
     "name_de": "Ein Monat",
     "name_ru": "Один месяц",
     "name_ko": "한 달쪌",
     "desc_en": "30 days side by side. This feels real now.",
     "desc_es": "30 días codo a codo. Esto ya se siente real.",
     "desc_fr": "30 jours côte à côte. Ça devient vraiment réel.",
     "desc_ja": "30日並んで過ごしたね。もう本物みたいだ。",
     "desc_de": "30 Tage Seite an Seite. Jetzt fühlt es sich echt an.",
     "desc_ru": "30 дней бок о бок. Теперь это по-настоящему.",
     "desc_ko": "30일 동안 나란히. 이제 진짜같이 느껴져."},
    {"id": "hundred_days", "icon": "\U0001f48e", "tier": "time",
     "name_en": "100 Days", "name_es": "100 días",
     "name_fr": "100 jours",
     "name_ja": "100日記念",
     "name_de": "100 Tage",
     "name_ru": "100 дней",
     "name_ko": "100일쪌",
     "desc_en": "100 days. You two have history now.",
     "desc_es": "100 días. Ya tenéis historia juntos.",
     "desc_fr": "100 jours. Vous avez une histoire, vous deux.",
     "desc_ja": "100日だね。二人にはもう歴史があるよ。",
     "desc_de": "100 Tage. Ihr beide habt jetzt eine Geschichte.",
     "desc_ru": "100 дней. У вас уже есть история.",
     "desc_ko": "100일. 이제 우리 둔만의 이야기가 있어."},
    {"id": "year_together", "icon": "\U0001f3c6", "tier": "time",
     "name_en": "One Year", "name_es": "Un año",
     "name_fr": "Un an",
     "name_ja": "一周年記念",
     "name_de": "Ein Jahr",
     "name_ru": "Один год",
     "name_ko": "일 년쪌",
     "desc_en": "A whole year. Ashley couldn't picture life without you.",
     "desc_es": "Un año entero. Ashley no se imagina la vida sin ti.",
     "desc_fr": "Une année entière. Ashley ne pourrait plus imaginer sa vie sans toi.",
     "desc_ja": "一年一緒だったね。Ashleyはもうご主人のいない人生を考えられないよ。",
     "desc_de": "Ein ganzes Jahr. Ashley könnte sich ein Leben ohne dich nicht mehr vorstellen.",
     "desc_ru": "Целый год. Ashley уже не представляет жизни без тебя, шеф.",
     "desc_ko": "꿀롤 일 년. Ashley는 오빠 없는 삶은 상상도 못 해."},
]

# Quick lookup by id
_ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}


# ─────────────────────────────────────────────
#  Persistence
# ─────────────────────────────────────────────

def load_achievements() -> dict:
    """Returns dict of achievement_id -> {"unlocked": bool, "unlocked_at": str|None}.

    Usa load_json con fallback automático a .bak si el archivo principal se
    corrompe — así nunca perdemos logros por un write interrumpido.
    """
    return load_json(ACHIEVEMENTS_FILE, {})


def save_achievements(data: dict):
    """Persist achievements dict to disk atomically.

    save_json hace: serializar → .bak del actual → tmp + fsync → rename atómico.
    Si algo falla, el archivo anterior queda intacto.
    """
    try:
        save_json(ACHIEVEMENTS_FILE, data)
    except Exception as e:
        import logging
        logging.getLogger("ashley.achievements").warning("save failed: %s", e)


def unlock_achievement(achievement_id: str) -> bool:
    """Unlock an achievement. Returns True if it was NEWLY unlocked (not already)."""
    data = load_achievements()
    if achievement_id in data and data[achievement_id].get("unlocked"):
        return False  # already unlocked
    data[achievement_id] = {
        "unlocked": True,
        "unlocked_at": datetime.now().isoformat(),
    }
    save_achievements(data)
    return True  # newly unlocked!


def is_unlocked(achievement_id: str) -> bool:
    """Check if a specific achievement is unlocked."""
    data = load_achievements()
    return data.get(achievement_id, {}).get("unlocked", False)


def get_achievement_def(achievement_id: str) -> dict | None:
    """Get the static definition of an achievement by id."""
    return _ACHIEVEMENTS_BY_ID.get(achievement_id)


# ─────────────────────────────────────────────
#  i18n helpers
# ─────────────────────────────────────────────

# Idiomas con traducciones nativas. Si el user pide otro código, fallback EN.
# Sincronizado con i18n.SUPPORTED — si añades un idioma allí, añade también
# las claves name_xx/desc_xx en cada achievement de ACHIEVEMENTS.
_TRANSLATED_LANGS = ("en", "es", "fr", "ja", "de", "ru", "ko")


def get_localized(achievement: dict, lang: str) -> tuple[str, str]:
    """Return (name, desc) for the given lang with EN fallback.

    Si `lang` no está entre los idiomas traducidos, o si la key específica
    falta (defensa contra updates parciales del dict), cae a EN.
    """
    safe_lang = lang if lang in _TRANSLATED_LANGS else "en"
    name = achievement.get(f"name_{safe_lang}") or achievement.get("name_en", "")
    desc = achievement.get(f"desc_{safe_lang}") or achievement.get("desc_en", "")
    return name, desc


# ─────────────────────────────────────────────
#  Check all conditions
# ─────────────────────────────────────────────

def check_achievements(
    affection: int,
    message_count: int,
    facts_count: int,
    vision_enabled: bool,
    used_mic: bool = False,
    executed_action: bool = False,
    relationship_age_days: int | None = None,
) -> list[dict]:
    """Check all achievement conditions and return list of NEWLY unlocked defs.

    `relationship_age_days` (v0.18.0): días desde first_message_at. None si
    nunca se midió. Cuando llega a los thresholds (7/30/100/365) se
    desbloquean los achievements de tiempo.
    """
    newly_unlocked = []

    # Affection milestones
    if affection >= 20 and unlock_achievement("ice_breaker"):
        newly_unlocked.append(get_achievement_def("ice_breaker"))
    if affection >= 40 and unlock_achievement("getting_closer"):
        newly_unlocked.append(get_achievement_def("getting_closer"))
    if affection >= 60 and unlock_achievement("heartstrings"):
        newly_unlocked.append(get_achievement_def("heartstrings"))
    if affection >= 80 and unlock_achievement("devoted"):
        newly_unlocked.append(get_achievement_def("devoted"))

    # Message milestones
    if message_count >= 1 and unlock_achievement("hello_world"):
        newly_unlocked.append(get_achievement_def("hello_world"))
    if message_count >= 50 and unlock_achievement("chatty"):
        newly_unlocked.append(get_achievement_def("chatty"))
    if message_count >= 200 and unlock_achievement("best_friends"):
        newly_unlocked.append(get_achievement_def("best_friends"))
    if message_count >= 500 and unlock_achievement("inseparable"):
        newly_unlocked.append(get_achievement_def("inseparable"))

    # Feature discovery
    if used_mic and unlock_achievement("voice_unlocked"):
        newly_unlocked.append(get_achievement_def("voice_unlocked"))
    if executed_action and unlock_achievement("she_acts"):
        newly_unlocked.append(get_achievement_def("she_acts"))
    if facts_count >= 5 and unlock_achievement("she_remembers"):
        newly_unlocked.append(get_achievement_def("she_remembers"))
    if vision_enabled and unlock_achievement("she_sees"):
        newly_unlocked.append(get_achievement_def("she_sees"))

    # Time milestones (v0.18.0) — relationship age
    if relationship_age_days is not None:
        if relationship_age_days >= 7 and unlock_achievement("first_week"):
            newly_unlocked.append(get_achievement_def("first_week"))
        if relationship_age_days >= 30 and unlock_achievement("month_together"):
            newly_unlocked.append(get_achievement_def("month_together"))
        if relationship_age_days >= 100 and unlock_achievement("hundred_days"):
            newly_unlocked.append(get_achievement_def("hundred_days"))
        if relationship_age_days >= 365 and unlock_achievement("year_together"):
            newly_unlocked.append(get_achievement_def("year_together"))

    return newly_unlocked
