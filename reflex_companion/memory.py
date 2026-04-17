import json
import logging
import os
from datetime import datetime, timezone

DIARY_KEYWORDS = [
    "ayer", "anteayer", "lunes", "martes", "miércoles", "jueves", "viernes",
    "sábado", "domingo", "semana pasada", "semana anterior", "el otro día",
    "qué hablamos", "qué dijiste", "qué pasó", "recuerdas cuando", "qué hice",
    "anteriormente", "la última vez",
]

_log = logging.getLogger("ashley.io")


# ─────────────────────────────────────────────
#  I/O atómico con fallback
# ─────────────────────────────────────────────
#
# Objetivo: bajo ninguna circunstancia perdemos los datos del usuario.
#
# save_json:
#   1. Serializamos primero a memoria (si el JSON es inválido aborta
#      aquí SIN tocar el archivo real).
#   2. Si el archivo real existe y parsea OK, lo copiamos a `.bak`.
#      Este respaldo es nuestra red de seguridad.
#   3. Escribimos a `archivo.tmp` + fsync (bytes en disco físico).
#   4. os.replace(tmp, archivo) — operación atómica del filesystem:
#      pasa del todo o no pasa. Sin archivo a medias.
#
# load_json:
#   1. Intenta leer `archivo`.
#   2. Si está corrupto (JSON inválido) → intenta `archivo.bak`.
#   3. Si ambos están rotos → devuelve `default` y loguea.

def _is_valid_json_file(path: str) -> bool:
    """True si el archivo existe y parsea como JSON válido."""
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except Exception:
        return False


def load_json(path: str, default):
    """Carga JSON del disco con recuperación automática desde .bak.

    Si `path` no existe o está corrupto, intenta `path.bak` (copia válida
    anterior). Si ambos fallan, devuelve `default` y loguea un warning
    para que quede trazado en soporte.
    """
    for candidate in (path, path + ".bak"):
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            if candidate.endswith(".bak"):
                _log.warning(
                    "load_json: main file %s was corrupt, recovered from .bak",
                    path,
                )
            return data
        except Exception as e:
            _log.warning("load_json: failed to read %s: %s", candidate, e)
            continue
    return default


def save_json(path: str, data):
    """Escritura atómica con .bak previo. Nunca deja el archivo a medias.

    Pasos:
      1. Serializar en memoria (falla limpia si data no es JSON-friendly).
      2. Respaldar la versión actual a .bak si existía y era válida.
      3. Escribir al .tmp con fsync forzado.
      4. os.replace(.tmp, archivo) → atómico.

    Si algún paso falla, el archivo original queda intacto. En el peor
    caso (crash entre 2 y 4) el user conserva el archivo original +
    posiblemente un .tmp huérfano que no se usa.
    """
    # 1. Serializar primero — si data es inválida, fallamos sin tocar disco.
    serialized = json.dumps(data, ensure_ascii=False, indent=2)

    # Crear directorio padre si hace falta.
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    # 2. Backup del actual si es válido.
    if _is_valid_json_file(path):
        try:
            import shutil
            shutil.copy2(path, path + ".bak")
        except Exception as e:
            _log.warning("save_json: could not backup %s: %s", path, e)
            # seguimos — el backup es best-effort, no vale parar por él

    # 3. Escribir a .tmp con fsync.
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(serialized)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # Algunos filesystems (red, VMs) no soportan fsync —
                # mejor que perder el write, pero no siempre disponible.
                pass

        # 4. Rename atómico. En Windows, os.replace sobrescribe limpio.
        os.replace(tmp, path)
    except Exception as e:
        # Algo catastrófico pasó — el archivo original sigue intacto
        # gracias a que NO lo tocamos hasta el replace. Limpiamos el
        # .tmp huérfano si quedó.
        _log.error("save_json: write failed for %s: %s", path, e)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise


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
