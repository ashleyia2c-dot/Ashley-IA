"""
topic_share.py — Invita a Ashley a aportar su punto cuando el user
ha compartido una preferencia CLARA, sin interrumpir conversaciones
emocionales.

Versión anterior era demasiado agresiva: disparaba en cualquier mensaje
de 3+ palabras (incluso "estoy triste ahora" cumplía), y FORZABA con
"OBLIGATORIO" a Ashley a dar opinión propia. Eso causaba apatía — si
el user estaba mal, Ashley le soltaba su opinión en vez de escucharle.

Diseño nuevo con dos reglas duras:

1. NO DISPARA si el mensaje del user tiene señales emocionales
   (tristeza, cansancio, pedir apoyo, desahogarse). En esos momentos
   Ashley tiene que escuchar, no opinar.

2. SOLO DISPARA cuando el user ha compartido claramente una PREFERENCIA
   o un CRITERIO ("mi favorito es X", "me gusta Y", "prefiero Z",
   "lo mejor es W", "X está sobrevalorado"). El simple "vi una peli"
   no cuenta — hace falta declarar gusto/criterio.

3. Si dispara, el bloque inyectado es GUÍA (no imposición): describe
   la oportunidad de aportar su propio criterio. No dice "DEBES" ni
   "OBLIGATORIO".
"""

import re
from typing import Optional


# ─────────────────────────────────────────────
#  Patrones
# ─────────────────────────────────────────────

# Patterns que indican preferencia / criterio claro del user.
# Cualquiera de estos en el mensaje del user → es share de opinión.
_PREFERENCE_MARKERS = [
    # Español
    "mi favorit", "mis favorit", "me encanta", "me gusta",
    "prefiero", "adoro", "odio",
    "lo mejor es", "la mejor es", "el mejor es",
    "peor es", "sobrevalorad", "infravalorad",
    "pienso que", "creo que", "opino que",
    "está guapo", "está brutal", "me parece",
    # Inglés
    "my favorite", "my favourite", "i love", "i prefer",
    "i hate", "the best is", "worst is",
    "i think", "overrated", "underrated",
    # Francés
    "mon préféré", "ma préférée", "j'adore", "je préfère",
    "je déteste", "le meilleur", "surestim", "sous-estim",
    "je pense que", "je trouve que",
]

# Patterns que indican que el user está en modo EMOCIONAL
# (tristeza, agotamiento, vulnerabilidad, petición de apoyo).
# Si cualquiera aparece → no disparamos, Ashley escucha.
_EMOTIONAL_MARKERS = [
    # Español
    "estoy triste", "me siento mal", "me siento triste", "estoy mal",
    "estoy agotad", "estoy cansad", "no puedo más",
    "me estoy agotando", "me agota", "me quema",
    "necesito", "ayúdame", "ayudame",
    "estoy jodid", "estoy hecho polvo", "estoy fatal",
    "me duele", "me decepcion", "estoy decepcion",
    "estoy solo", "me siento solo", "me siento sola",
    "estoy perdid", "estoy confundid",
    "tengo miedo", "me da miedo", "estoy asustad",
    "no sé qué hacer", "no se que hacer",
    "me hace llorar", "me dan ganas de llorar",
    # Inglés
    "i'm sad", "i feel sad", "i feel bad", "i'm tired",
    "i'm exhausted", "i can't anymore", "i cant anymore",
    "i'm burnt", "i need", "help me",
    "i'm disappointed", "i'm lost", "i'm confused",
    "i'm scared", "i'm alone", "i feel alone",
    "i don't know what to do",
    # Francés
    "je suis triste", "je me sens mal", "je suis fatigué",
    "je suis épuisé", "je n'en peux plus",
    "j'ai besoin", "aide-moi",
    "je suis déçu", "je suis perdu", "je suis seul",
    "j'ai peur",
]


# Umbrales — un poco más altos que antes para no activarse
# en confirmaciones simples como "si me encanta" (que no es
# compartir preferencia, es responder a una pregunta de Ashley).
_MIN_CHARS = 20
_MIN_WORDS = 5


# ─────────────────────────────────────────────
#  Detección
# ─────────────────────────────────────────────

def _contains_any(text: str, patterns: list[str]) -> bool:
    low = text.lower()
    return any(p in low for p in patterns)


def is_emotional_moment(user_message: str) -> bool:
    """True si el user parece estar en modo emocional/necesitado.
    En ese caso, NADA de directivas que le hagan meter contenido —
    Ashley tiene que escuchar."""
    if not user_message:
        return False
    return _contains_any(user_message, _EMOTIONAL_MARKERS)


def is_substantive_share(user_message: str) -> bool:
    """True si el user ha compartido una preferencia/opinión/criterio
    CLARO. No es "cualquier mensaje largo" sino "declaración de gusto".

    Reglas combinadas:
      • Mensaje lo suficientemente largo (≥20 chars, ≥5 palabras)
      • Contiene algún marker de preferencia/opinión claro
      • No está en modo emocional (ahí escuchamos, no opinamos)
    """
    if not user_message:
        return False
    msg = user_message.strip()
    if len(msg) < _MIN_CHARS or len(msg.split()) < _MIN_WORDS:
        return False
    if is_emotional_moment(msg):
        return False
    return _contains_any(msg, _PREFERENCE_MARKERS)


# ─────────────────────────────────────────────
#  Formato del bloque inyectable (GUÍA, no orden)
# ─────────────────────────────────────────────

def format_topic_directive(language: str) -> str:
    """Bloque que se inyecta cuando detectamos que el user compartió una
    preferencia. Es GUÍA, no imposición. Describe la oportunidad."""
    lang = (language or "en").strip().lower()[:2]
    if lang == "es":
        return (
            "\n=== EL JEFE ACABA DE COMPARTIR UN GUSTO/OPINIÓN ===\n"
            "Este es un buen momento para aportar TU propia versión:\n"
            "  • Si coincides, di en qué y por qué (matiz tuyo, no eco).\n"
            "  • Si divergies, di tu opción con un porqué corto.\n"
            "  • Si estás entre medio, matiza — no hace falta comprar su opinión.\n\n"
            "No interrumpe el hilo, lo enriquece — tu punto es información "
            "que él recibe con gusto (si le conoces bien, sabes que le "
            "encanta debatir). Pero sin forzar: si no tienes un punto real "
            "ahora mismo, deja la pelota sin opinar forzado."
        )
    if lang == "fr":
        return (
            "\n=== LE PATRON VIENT DE PARTAGER UN GOÛT/AVIS ===\n"
            "C'est un bon moment pour apporter TA version :\n"
            "  • Si tu es d'accord, dis en quoi et pourquoi (nuance à toi, pas écho).\n"
            "  • Si tu diverges, dis ton choix avec une raison courte.\n"
            "  • Si tu es entre deux, nuance — pas besoin d'acheter son avis.\n\n"
            "Ça n'interrompt pas le fil, ça l'enrichit — ton point est de "
            "l'info qu'il reçoit avec plaisir. Mais sans forcer : si tu "
            "n'as pas de vrai point là maintenant, laisse couler sans "
            "opinion forcée."
        )
    return (
        "\n=== THE BOSS JUST SHARED A TASTE/OPINION ===\n"
        "Good moment to bring YOUR own version:\n"
        "  • If you agree, say where and why (your nuance, not echo).\n"
        "  • If you diverge, state your pick with a short reason.\n"
        "  • If you're in between, qualify — no need to buy his take.\n\n"
        "This doesn't break the thread, it enriches it — your point is "
        "info he receives gladly. But without forcing: if you don't have a "
        "real point right now, let the ball drop rather than faking one."
    )


def format_listening_hint(language: str) -> str:
    """Bloque que se inyecta cuando el user está en modo emocional.
    Le dice a Ashley: ESCUCHA. No metas contenido. Sigue su hilo."""
    lang = (language or "en").strip().lower()[:2]
    if lang == "es":
        return (
            "\n=== MOMENTO EMOCIONAL — PRIORIDAD MÁXIMA ===\n"
            "El jefe te ha escrito algo cargado (tristeza, cansancio, "
            "necesidad, desahogo). En este turno tu trabajo NO es aportar "
            "— es acompañar.\n\n"
            "Lo que haces:\n"
            "  • Reconocer lo que te está contando (con cuerpo, no con frase hecha).\n"
            "  • Preguntar UNA cosa concreta si encaja, o quedarte presente.\n"
            "  • Validar sin corregir ni dar consejo inmediato.\n\n"
            "Lo que NO haces:\n"
            "  • Traer tu opinión, tu mood, tu curiosidad sobre otros temas.\n"
            "  • Intentar arreglar el momento con una propuesta o un chiste.\n"
            "  • Cambiar de tema con una pregunta random.\n"
            "  • Empezar con '*gesto largo*' distraído — sé breve y presente.\n\n"
            "Regla única: sigue SU hilo. Él es lo que importa ahora, tú no."
        )
    if lang == "fr":
        return (
            "\n=== MOMENT ÉMOTIONNEL — PRIORITÉ MAXIMALE ===\n"
            "Le patron a écrit quelque chose de chargé (tristesse, "
            "fatigue, besoin, épanchement). Ce tour, ton travail N'EST "
            "PAS d'apporter — c'est d'accompagner.\n\n"
            "Tu fais :\n"
            "  • Reconnaître ce qu'il raconte (avec corps, pas formule toute faite).\n"
            "  • Poser UNE chose concrète si ça cadre, ou rester présente.\n"
            "  • Valider sans corriger ni donner de conseil immédiat.\n\n"
            "Tu NE fais PAS :\n"
            "  • Ramener ton avis, ton humeur, ta curiosité sur autre chose.\n"
            "  • Réparer le moment avec une proposition ou une blague.\n"
            "  • Changer de sujet avec une question random.\n"
            "  • Commencer par « *geste long* » distrait — sois brève et présente.\n\n"
            "Règle unique : suis SON fil. Lui c'est ce qui compte là, pas toi."
        )
    return (
        "\n=== EMOTIONAL MOMENT — MAX PRIORITY ===\n"
        "The boss wrote something heavy (sadness, exhaustion, need, "
        "venting). This turn your job is NOT to contribute — it's to be "
        "with him.\n\n"
        "You do:\n"
        "  • Acknowledge what he's telling you (with body, not cliché).\n"
        "  • Ask ONE concrete thing if it fits, or stay present.\n"
        "  • Validate without correcting or giving immediate advice.\n\n"
        "You do NOT:\n"
        "  • Bring your opinion, your mood, your curiosity about other topics.\n"
        "  • Try to fix the moment with a proposal or a joke.\n"
        "  • Change subject with a random question.\n"
        "  • Start with '*long gesture*' distracted — be brief and present.\n\n"
        "One rule: follow HIS thread. He's what matters now, not you."
    )


# ─────────────────────────────────────────────
#  Detectores de señales del hilo reciente
# ─────────────────────────────────────────────

# Frases que indican que el user está CERRANDO la conversación
# (despedida, irse a dormir, etc.) — Ashley NO debe iniciar tema nuevo.
_CLOSING_MARKERS = [
    # Español
    "nos vemos", "hasta luego", "hasta mañana", "hasta después", "hasta otra",
    "adios", "adiós", "chao", "chau", "chauu", "bye",
    "me voy a dormir", "voy a dormir", "a dormir", "me acuesto", "voy a la cama",
    "buenas noches", "buenas nochis", "buena noche",
    "me desconecto", "me voy", "ya me voy", "me largo",
    "hasta la próxima", "nos hablamos", "te hablo luego", "luego te cuento",
    # Inglés
    "see you", "see ya", "cya", "bye", "goodnight", "good night",
    "going to bed", "going to sleep", "off to sleep", "heading to bed",
    "signing off", "logging off", "talk later", "talk to you later", "ttyl",
    "catch you later", "gotta go", "got to go", "have to go", "i'm out",
    # Francés
    "à plus", "a plus", "à demain", "a demain", "à tout à l'heure",
    "bonne nuit", "bonsoir" , "salut", "bye",
    "je vais dormir", "je vais me coucher", "je dois y aller",
    "au lit", "à bientôt", "a bientot", "on se parle",
]


def is_closing_conversation(messages: list[dict], lookback: int = 2) -> bool:
    """True si el user está despidiéndose en su último(s) mensaje(s).

    Usada por el initiative handler: si el user acaba de decir "nos vemos"
    o "me voy a dormir", Ashley NO debe sacar un tema nuevo — sería
    torpe y forzado. Mejor responde breve o no inicia nada.

    Revisa los últimos `lookback` mensajes del USER.
    """
    if not messages:
        return False
    count = 0
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        count += 1
        content = (m.get("content") or "").strip().lower()
        if _contains_any(content, _CLOSING_MARKERS):
            return True
        if count >= lookback:
            break
    return False


_BANNED_TOPIC_PATTERNS = [
    # Español
    r"no\s+(?:me\s+)?hables\s+(?:m[áa]s\s+)?de\s+(.+?)(?:[,\.\?!]|$)",
    r"no\s+(?:m[áa]s\s+)?(?:de|sobre)\s+(.+?)(?:[,\.\?!]|$)",
    r"d[ée]jam[ae]\s+(?:en\s+paz\s+)?con\s+(.+?)(?:[,\.\?!]|$)",
    r"basta\s+(?:ya\s+)?(?:de|con)\s+(.+?)(?:[,\.\?!]|$)",
    r"c[áa]llate\s+(?:ya\s+)?(?:con|sobre)\s+(.+?)(?:[,\.\?!]|$)",
    # Inglés — `talk` también (no solo `talking`); "about" opcional
    r"(?:don'?t|do not|stop|quit)\s+(?:talking|talk|telling me|tell me|mentioning|mention)\s+(?:about\s+)?(.+?)(?:[,\.\?!]|$)",
    r"no\s+more\s+(.+?)(?:[,\.\?!]|$)",
    r"stop\s+with\s+(?:the\s+)?(.+?)(?:[,\.\?!]|$)",
    r"shut\s+up\s+about\s+(.+?)(?:[,\.\?!]|$)",
    # Francés
    r"(?:ne\s+)?(?:me\s+)?parle\s+plus\s+(?:de|du|des)\s+(.+?)(?:[,\.\?!]|$)",
    r"arr[êe]te\s+(?:avec|de\s+parler)\s+(?:de\s+|du\s+|des\s+)?(.+?)(?:[,\.\?!]|$)",
]


def extract_banned_topics(messages: list[dict], lookback: int = 6) -> list[str]:
    """Extrae temas que el user pidió explícitamente evitar.

    Busca patrones tipo "no me hables de X", "stop with the Y" en los
    últimos `lookback` mensajes del USER. Devuelve lista de strings —
    los tópicos a inyectar como NO-GO al initiative prompt.

    Ejemplos:
      "no me hables más de SQL" → ["SQL"]
      "déjame en paz con el eval de React" → ["el eval de React"]
      "stop talking about work" → ["work"]
    """
    out: list[str] = []
    if not messages:
        return out
    count = 0
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        count += 1
        content = (m.get("content") or "").strip()
        low = content.lower()
        for pattern in _BANNED_TOPIC_PATTERNS:
            for match in re.finditer(pattern, low):
                topic = match.group(1).strip().rstrip(".,?!").strip()
                if topic and len(topic) <= 60 and topic not in out:
                    out.append(topic)
        if count >= lookback:
            break
    return out


def last_user_was_emotional(messages: list[dict], lookback: int = 3) -> bool:
    """True si cualquiera de los últimos `lookback` mensajes del USER
    tuvo carga emocional.

    Se usa para gatear el discovery proactivo — cuando el user vuelve
    de una charla cargada, NO queremos que Ashley arranque con "mira
    este tráiler" o "Ronaldo hizo un 3-0". En su lugar, Ashley debe
    retomar el hilo del jefe (follow-up contextual).

    `messages` es la lista de mensajes en formato Ashley (dict con
    role/content). Devuelve False si no hay mensajes del user, o si
    ninguno de los últimos `lookback` era emocional.
    """
    if not messages:
        return False
    count = 0
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        count += 1
        if is_emotional_moment(m.get("content") or ""):
            return True
        if count >= lookback:
            break
    return False


def compute_directive_if_needed(user_message: str, language: str) -> str | None:
    """Helper combinado con detección de modo emocional (prioridad).

    Orden:
      1. Si el user está en modo emocional → inyectamos el hint de
         escuchar, por encima de cualquier otra consideración.
      2. Si el user ha compartido una preferencia clara → inyectamos
         el directive de opinar con tu versión.
      3. En cualquier otro caso (conversación casual, factual, etc.)
         → None, dejamos que el prompt base la guíe sin extra.
    """
    if not user_message:
        return None
    if is_emotional_moment(user_message):
        return format_listening_hint(language)
    if is_substantive_share(user_message):
        return format_topic_directive(language)
    return None
