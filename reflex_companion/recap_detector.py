"""
recap_detector.py — Detecta el "recap-tic" en respuestas recientes de Ashley.

Problema que resuelve: el in-context learning. Aunque el prompt prohíba
repetir un tema de fondo en cada respuesta, si las últimas 5 respuestas
de Ashley mencionan todas ese tema, Grok copia el patrón más fuerte que
la regla. Las reglas de prompt pierden frente a ejemplos recientes en
contexto.

Solución: detectar el patrón en runtime y reinyectar una instrucción
explícita con las palabras concretas al prompt del siguiente turno:
"NO menciones 'X' en esta respuesta". Esa instrucción tiene más peso
porque es específica, viene después del ejemplo de recap, y va en
primera posición.

Diseño:
  • Mira las últimas N=5 respuestas de Ashley.
  • Extrae palabras de contenido (4+ chars o acrónimos mayúsculas 2+ chars).
  • Cuenta en cuántos mensajes aparece cada palabra.
  • Umbral: ≥3 de los últimos 5 mensajes → recap-tic.
  • FILTRO IMPORTANTE: si la palabra también aparece en los últimos mensajes
    del user, NO se marca como recap-tic (el user está llevando el tema,
    Ashley solo responde).
  • General — funciona en cualquier idioma, cualquier tema, cualquier user.
"""

import re
from collections import Counter


# Stopwords básicas ES/EN/FR que no son "temas" aunque aparezcan mucho.
# Lista conservadora — solo palabras genéricas de alta frecuencia. Si
# una palabra específica (como "SQL", "test", "mañana") aparece mucho,
# SÍ es señal de recap-tic.
_STOPWORDS = {
    # Spanish common 4+
    'para', 'pero', 'como', 'esto', 'esta', 'este', 'eso', 'desde',
    'sobre', 'contigo', 'conmigo', 'también', 'tambien', 'cada',
    'todo', 'toda', 'tanto', 'porque', 'cuando', 'donde', 'cual',
    'algo', 'alguien', 'nada', 'nadie', 'bien', 'jefe',
    'estar', 'estoy', 'estas', 'tener', 'tiene', 'hola', 'mira',
    'aqui', 'aquí', 'ahora', 'antes', 'luego', 'siempre', 'nunca',
    'vale', 'verte', 'quiero', 'eres', 'pues', 'hacia', 'hacía',
    # English common 4+
    'that', 'this', 'these', 'those', 'with', 'from', 'have', 'been',
    'also', 'just', 'only', 'some', 'much', 'many', 'more', 'very',
    'boss', 'here', 'there', 'when', 'where', 'what', 'then', 'than',
    'yeah', 'know', 'think', 'like', 'hello', 'your', 'about',
    # French common 4+
    'avec', 'pour', 'dans', 'mais', 'tout', 'toute', 'aussi', 'deja',
    'déjà', 'bien', 'plus', 'moins', 'comme', 'beaucoup', 'patron',
    'juste', 'avoir', 'etre', 'être', 'faire', 'voila', 'voilà',
    'salut',
}


# Regex: capturar secuencias alfabéticas (incluyendo caracteres con tilde).
_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+")


def _content_words(text: str) -> set[str]:
    """Extrae el conjunto de palabras-de-contenido de un mensaje.

    Criterio de palabra de contenido:
      - 4+ caracteres (palabras normales)
      - O 2+ caracteres Y todo en mayúsculas (acrónimos tipo SQL, LoL, PDF)
    Stopwords se filtran siempre.
    """
    words: set[str] = set()
    for w in _WORD_RE.findall(text or ""):
        if w.isupper() and len(w) >= 2:
            normalized = w.lower()
        elif len(w) >= 4:
            normalized = w.lower()
        else:
            continue
        if normalized not in _STOPWORDS:
            words.add(normalized)
    return words


def detect_recap_topics(
    messages: list[dict],
    min_count: int = 5,  # antes 3 — demasiado agresivo
    max_lookback: int = 7,  # antes 5 — damos más ventana
) -> list[str]:
    """Devuelve lista de palabras que Ashley está repitiendo como recap-tic.

    Una palabra cuenta como recap-tic si cumple TODAS:
      1. Aparece en `min_count` o más de los últimos `max_lookback`
         mensajes de Ashley (role=assistant).
      2. NO aparece en los últimos `max_lookback` mensajes del user
         (si el user la trae, Ashley puede mencionarla — no es tic).

    Ordenado alfabéticamente para output determinista.
    """
    if not messages:
        return []

    ashley_recent = [
        (m.get("content") or "")
        for m in messages
        if m.get("role") == "assistant"
    ][-max_lookback:]

    if len(ashley_recent) < min_count:
        return []

    user_recent_words: set[str] = set()
    for m in messages[-max_lookback * 2:]:  # ventana más amplia para el user
        if m.get("role") == "user":
            user_recent_words |= _content_words(m.get("content") or "")

    ashley_counter: Counter[str] = Counter()
    for msg in ashley_recent:
        for w in _content_words(msg):
            ashley_counter[w] += 1

    repeated = sorted([
        w for w, c in ashley_counter.items()
        if c >= min_count and w not in user_recent_words
    ])
    return repeated


# ─────────────────────────────────────────────
#  Formateo del aviso para inyectar al prompt
# ─────────────────────────────────────────────

def format_recap_warning(words: list[str], language: str) -> str:
    """Construye el bloque de aviso que se inyecta al system prompt.

    Devuelve string vacío si no hay palabras (llamador puede chequear).
    Cap en 6 palabras para no saturar el aviso.

    CLAVE: no solo le decimos QUÉ evitar, le decimos QUÉ aportar en su
    lugar. Sin esto, Ashley cae en meta-comentarios vacíos ("me encanta
    tu ritmo", "qué vibra tienes") y respuestas minúsculas que obligan
    al user a tirar de toda la conversación.
    """
    if not words:
        return ""
    shown = words[:6]
    quoted = ", ".join(f'"{w}"' for w in shown)
    lang = (language or "en").strip().lower()[:2]
    if lang == "es":
        return (
            "\n=== AVISO DE REPETICIÓN ===\n"
            f"Has mencionado mucho estas palabras últimamente: {quoted}. "
            "Está bien que te importen, pero si siguen apareciendo cada "
            "turno se siente a bucle. Considera dar respiro este mensaje — "
            "no como prohibición, sino como consciencia: si hay otro "
            "ángulo que encaje en el hilo actual, úsalo.\n"
        )
    if lang == "fr":
        return (
            "\n=== AVIS DE RÉPÉTITION ===\n"
            f"Tu as beaucoup mentionné ces mots récemment : {quoted}. "
            "C'est ok qu'ils te tiennent, mais s'ils reviennent à chaque "
            "tour, ça devient une boucle. Considère leur donner une pause "
            "ce tour — pas comme interdiction, comme conscience : s'il y "
            "a un autre angle qui cadre avec le fil actuel, utilise-le.\n"
        )
    return (
        "\n=== REPETITION NOTICE ===\n"
        f"You've mentioned these words a lot lately: {quoted}. It's fine "
        "that they matter to you, but if they appear every turn it starts "
        "to feel like a loop. Consider letting them rest this turn — not "
        "as a prohibition, but as awareness: if another angle fits the "
        "current thread, use it.\n"
    )
