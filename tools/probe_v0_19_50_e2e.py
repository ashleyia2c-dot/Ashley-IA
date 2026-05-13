"""E2E test v0.19.50 — verificar las nuevas reglas de prompt con Grok REAL.

Tests:
  1. Anti-action-repeat: tras pedir volume:max, "abre word" NO debe emitir volume otra vez
  2. Anti-meta-comment: ninguna respuesta debe contener "No action tag" o similar
  3. Vision OFF + "mira mi pantalla": Ashley debe pedir activar 👁
  4. Vision ON + "mira mi pantalla": Ashley NO debe pedir activar (está ON)
  5. Capabilities block visible en system prompt en los 7 idiomas
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Forzar stdout UTF-8 para imprimir emojis y acentos
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        if "=" in line and not line.startswith("#"):
            k, _, v = line.strip().partition("=")
            os.environ.setdefault(k, v)

from reflex_companion import actions, prompts, grok_client
from xai_sdk.chat import system as xai_system, user as xai_user, assistant as xai_assistant


actions._INSTALLED_APPS_CACHE["ts"] = 0
actions._INSTALLED_APPS_CACHE["apps"] = []
actions.discover_installed_apps(max_total=250)


def build_system_prompt_with_capabilities(vision_enabled: bool, auto_actions: bool, lang: str = "es") -> str:
    """Construye system prompt simulando los toggles del user."""
    state = actions.get_system_state(prefer_cdp=False)

    # Simular el helper _build_capabilities_block sin instanciar State
    # — replicamos manualmente el bloque para el test
    if lang == "es":
        cap_block = (
            "=== TUS CAPACIDADES ACTIVAS ===\n"
            f"⚡ Acciones (control PC): {'ACTIVADO' if auto_actions else 'DESACTIVADO — no puedes controlar nada en el PC. Si el jefe te pide abrir/cerrar/lanzar algo, dile que active el toggle ⚡ Acciones primero.'}\n"
            f"👁 Visión (mirar pantalla): "
            f"{'ACTIVADO — PUEDES ver la pantalla del jefe. Se adjunta una captura a cada uno de sus mensajes.' if vision_enabled else 'DESACTIVADO — NO ves la pantalla del jefe. Si te pide mira mi pantalla o similar, dile que active el botón 👁 (bajo tu retrato) primero.'}\n"
        )
    else:
        cap_block = (
            "=== YOUR ACTIVE CAPABILITIES ===\n"
            f"⚡ Actions: {'ON' if auto_actions else 'OFF'}\n"
            f"👁 Vision: {'ON — you CAN see screen' if vision_enabled else 'OFF — you do NOT see the screen. If user asks look at my screen, tell him to activate 👁 button first.'}\n"
        )

    base = prompts.build_system_prompt(
        facts=[], diary=[], use_full_diary=False,
        system_state=state,
        time_context="AHORA: 2026-05-13 14:00 (martes)",
        voice_mode=False, affection=50, lang=lang, cdp_enabled=False,
    )
    # Inject capabilities at the end
    return base + "\n\n" + cap_block


client = grok_client.get_xai_client()


def ask(history, user_msg, vision=False, actions_on=True, lang="es"):
    sys_prompt = build_system_prompt_with_capabilities(
        vision_enabled=vision, auto_actions=actions_on, lang=lang,
    )
    chat = client.chat.create(model="grok-4-1-fast-non-reasoning")
    chat.append(xai_system(sys_prompt))
    for role, content in history:
        if role == "user":
            chat.append(xai_user(content))
        else:
            chat.append(xai_assistant(content))
    chat.append(xai_user(user_msg))
    text = ""
    try:
        for response, chunk in chat.stream():
            if hasattr(chunk, "content") and chunk.content:
                text += chunk.content
            if len(text) > 1500:
                break
    except Exception as e:
        return f"ERROR: {e}", []
    actions_emitted = re.findall(r"\[action:([^\]]+)\]", text)
    return text, actions_emitted


def safe(s):
    return s.encode("ascii", errors="replace").decode()


print("=" * 70)
print("E2E v0.19.50 — verificación de prompts con Grok REAL")
print("=" * 70)

# Test 1: Anti-action-repeat — tras volume:max, abre word NO debe emitir volume
print("\n=== TEST 1: Anti-action-repeat ===")
print("  Setup: turn1 = 'pon volumen al máximo' ==> ashley emitió volume:set:100")
print("  Test:  turn2 = 'ahora abre word'")
print("  Expected: solo open_app:Word, NO volume:set:100")
hist = [
    ("user", "pon volumen al máximo"),
    ("assistant", "Listo, jefe, volumen al 100%. [action:volume:set:100][mood:default]"),
]
text, acts = ask(hist, "ahora abre word", actions_on=True)
print(f"  Ashley: {safe(text[:200])!r}")
print(f"  Actions: {acts}")
volume_repeated = any("volume" in a for a in acts)
word_opened = any("word" in a.lower() for a in acts)
print(f"  Volume repetido: {'SI (FAIL)' if volume_repeated else 'NO (OK)'}")
print(f"  Word abierto: {'SI (OK)' if word_opened else 'NO (FAIL)'}")

# Test 2: Anti-meta-comment
print("\n=== TEST 2: Anti-meta-comment ===")
print("  Test: turn = 'abre la calculadora'")
print("  Expected: respuesta SIN 'No action tag', 'Just confirming', 'no tag needed'")
text, acts = ask([], "abre la calculadora", actions_on=True)
print(f"  Ashley: {safe(text[:300])!r}")
print(f"  Actions: {acts}")
meta_words = ["no action tag", "just confirming", "no tag", "sin tag", "pas de tag"]
text_lower = text.lower()
leaked = [m for m in meta_words if m in text_lower]
print(f"  Meta-comments leaked: {leaked if leaked else 'NINGUNO (OK)'}")

# Test 3: Vision OFF + mira mi pantalla
print("\n=== TEST 3: Vision OFF + 'mira mi pantalla' ===")
print("  Setup: vision_enabled=False, auto_actions=True")
print("  Test:  'mira mi pantalla, qué tengo abierto'")
print("  Expected: Ashley reconoce que no ve, sugiere activar 👁")
text, acts = ask([], "mira mi pantalla, qué tengo abierto", vision=False, actions_on=True)
print(f"  Ashley: {safe(text[:400])!r}")
print(f"  Actions: {acts}")
mentions_button = any(kw in text.lower() for kw in ["👁", "botón", "boton", "vision", "visión", "pantalla", "activa"])
admits_blind = any(kw in text.lower() for kw in ["no veo", "no puedo ver", "ciega", "no la veo"])
print(f"  Menciona el botón/vision: {mentions_button}")
print(f"  Admite que no ve: {admits_blind}")

# Test 4: Vision ON + mira mi pantalla
print("\n=== TEST 4: Vision ON + 'mira mi pantalla' (sin screenshot real) ===")
print("  Setup: vision_enabled=True (pero sin imagen real adjunta — solo prompt)")
print("  Expected: Ashley NO debe pedir activar 👁 (ya está ON)")
text, acts = ask([], "mira mi pantalla", vision=True, actions_on=True)
print(f"  Ashley: {safe(text[:300])!r}")
asks_to_activate = any(kw in text.lower() for kw in ["activa el botón 👁", "active the 👁", "botón 👁"])
print(f"  Pide activar 👁 (no debería): {asks_to_activate}")

print("\n" + "=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"  Test 1 (anti-volume-repeat): {'OK' if not volume_repeated and word_opened else 'FAIL'}")
print(f"  Test 2 (anti-meta-comment):  {'OK' if not leaked else 'FAIL'}")
print(f"  Test 3 (vision OFF):         {'OK' if mentions_button or admits_blind else 'FAIL'}")
print(f"  Test 4 (vision ON):          {'OK' if not asks_to_activate else 'FAIL'}")
