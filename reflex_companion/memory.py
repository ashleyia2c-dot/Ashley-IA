import json
import os
from datetime import datetime, timezone

DIARY_KEYWORDS = [
    "ayer", "anteayer", "lunes", "martes", "miércoles", "jueves", "viernes",
    "sábado", "domingo", "semana pasada", "semana anterior", "el otro día",
    "qué hablamos", "qué dijiste", "qué pasó", "recuerdas cuando", "qué hice",
    "anteriormente", "la última vez",
]


# ─────────────────────────────────────────────
#  I/O
# ─────────────────────────────────────────────

def load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_ids(messages: list[dict]) -> list[dict]:
    """Compatibilidad: añade id e image a mensajes sin ellos."""
    for i, msg in enumerate(messages):
        if not msg.get("id"):
            msg["id"] = f"legacy-{i}-{msg.get('timestamp', now_iso())}"
        if "image" not in msg:
            msg["image"] = ""
    return messages


def ensure_facts(facts: list[dict]) -> list[dict]:
    """Compatibilidad: añade importancia a hechos antiguos que no la tienen."""
    for f in facts:
        if "importancia" not in f:
            f["importancia"] = "5"
    return facts


# ─────────────────────────────────────────────
#  Helpers de formato
# ─────────────────────────────────────────────

def is_diary_query(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in DIARY_KEYWORDS)


def format_facts(facts: list[dict]) -> str:
    if not facts:
        return "Ningún recuerdo registrado aún."
    by_cat: dict[str, list[str]] = {}
    for f in facts:
        cat = f.get("categoria", "general")
        imp = f.get("importancia", "5")
        by_cat.setdefault(cat, []).append((int(imp), f["hecho"]))
    lines = []
    for cat, items in by_cat.items():
        lines.append(f"[{cat.upper()}]")
        for imp, hecho in sorted(items, reverse=True):
            lines.append(f"  • {hecho}")
    return "\n".join(lines)


def format_diary(entries: list[dict], limit: int = 3) -> str:
    if not entries:
        return "Sin entradas de diario aún."
    return "\n".join(
        f"📅 {e['fecha']}: {e['resumen']}" for e in entries[-limit:]
    )


# ─────────────────────────────────────────────
#  Extracción de memoria
# ─────────────────────────────────────────────

def extract_facts(messages: list[dict], existing_facts: list[dict]) -> list[dict]:
    from .grok_client import grok_call

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    existing_text = (
        "\n".join(f"• {f['hecho']}" for f in existing_facts)
        if existing_facts else "Ninguno aún."
    )

    system_text = """Eres un extractor de memoria a largo plazo. Analiza conversaciones y extrae hechos permanentes sobre el usuario (el "jefe").

CAPTURA:
- Preferencias explícitas ("me gusta X", "prefiero Y", "odio Z")
- Proyectos activos con nombre y propósito claro
- Hábitos, rutinas o patrones recurrentes
- Decisiones importantes tomadas
- Datos personales relevantes: trabajo, tecnologías, horarios, contexto
- Patrones emocionales que se repiten

IGNORA:
- Saludos, despedidas y relleno conversacional
- Estados temporales sin patrón ("hoy estoy cansado")
- Cosas ya implícitas en hechos registrados
- Todo lo que dice Ashley (solo importa el jefe)
- Hechos triviales sin utilidad futura

ACTUALIZACIÓN DE HECHOS:
- Si un hecho nuevo contradice o supera a uno existente, usa el campo "reemplaza" con el texto exacto del hecho viejo.
- Ejemplo: si ya existe "El jefe usa Python 3.9" y ahora dice que usa Python 3.12, el nuevo hecho debe tener "reemplaza": "El jefe usa Python 3.9"

IMPORTANCIA (1-10):
- 9-10: Datos centrales de identidad, proyectos principales, preferencias fuertes
- 7-8: Hábitos relevantes, tecnologías usadas habitualmente, decisiones importantes
- 5-6: Preferencias secundarias, datos útiles pero no críticos
- 3-4: Información contextual interesante
- 1-2: Detalles menores, curiosidades

REGLAS:
- Cada hecho debe ser autónomo y comprensible sin contexto
- Prioriza calidad sobre cantidad: 2 hechos buenos > 8 mediocres
- Si no hay nada digno de recordar, devuelve exactamente: []

Devuelve SOLO un array JSON válido, sin texto extra ni bloques de código:
[{"hecho": "...", "categoria": "gustos|habitos|decisiones|datos|proyectos|personalidad", "relevancia": "permanente|temporal", "importancia": 8, "reemplaza": "texto exacto del hecho que reemplaza (omitir si no reemplaza nada)"}]"""

    user_text = (
        f"Hechos ya registrados (no duplicar, usar 'reemplaza' si alguno queda obsoleto):\n{existing_text}\n\n"
        f"Conversación a analizar:\n{history_text}"
    )

    raw = grok_call(system_text, user_text).strip()

    if "```" in raw:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        raw = raw[start:end] if start != -1 else "[]"

    try:
        new_facts = json.loads(raw)
        if not isinstance(new_facts, list):
            return []
        today = datetime.now().strftime("%Y-%m-%d")
        for f in new_facts:
            f.setdefault("fecha", today)
            # importancia siempre como string para Reflex (list[dict[str, str]])
            f["importancia"] = str(f.get("importancia", 5))
            # reemplaza solo se mantiene si tiene valor
            if "reemplaza" in f and not f["reemplaza"]:
                del f["reemplaza"]
        return new_facts
    except Exception:
        return []


def generate_diary_entry(messages: list[dict], fecha: str) -> str:
    from .grok_client import grok_call

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    system_text = (
        "Eres Ashley. Escribe una entrada de diario íntima de 3-4 líneas sobre esta sesión. "
        "En primera persona, como si escribieras para ti misma en privado. "
        "Captura el tono emocional, no solo los temas. Sé concisa y honesta."
    )
    return grok_call(system_text, f"Sesión del {fecha}:\n{history_text}")
