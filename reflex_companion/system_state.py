"""
system_state.py — Snapshot del estado del sistema (Windows).

Usado para dos propósitos:

1. **Contexto al LLM**: antes de mandar el mensaje del user, inyectamos un
   resumen del estado actual del PC en el prompt. Sin esto, cuando el user
   dice "súbele al máximo" o "bájalo a la mitad", Ashley no tiene un punto
   de partida — adivina. Con esto puede decidir el `set:N` correcto.

2. **Verificación post-action**: tras ejecutar una acción, releemos el
   estado y comparamos. Si Ashley emitió `volume:set:100` pero el sistema
   reporta volumen=0, sabemos que algo falló (Ashley emitió mal el param,
   o la acción no aplicó). Lo logueamos para análisis posterior.

Las funciones devuelven None / "" si no pueden leer el estado (p.ej.
falta pycaw, no es Windows). Los callers deben manejarlo gracefully.
"""

from typing import Optional


def get_system_volume() -> Optional[int]:
    """Volumen master del sistema en porcentaje 0-100. None si falla."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(iface, POINTER(IAudioEndpointVolume))
        scalar = vol.GetMasterVolumeLevelScalar()
        return int(round(scalar * 100))
    except Exception:
        return None


def get_volume_muted() -> Optional[bool]:
    """True si el sistema está muteado, False si no, None si falla."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(iface, POINTER(IAudioEndpointVolume))
        return bool(vol.GetMute())
    except Exception:
        return None


def get_active_window_title() -> str:
    """Título de la ventana activa (foreground). '' si falla."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:
        return ""


def get_state_snapshot() -> dict:
    """Snapshot dict completo del estado relevante. Llamado:
      - Antes de cada mensaje del user (para inyectar contexto al LLM)
      - Después de cada acción ejecutada (para comparación post-action)
    """
    return {
        "volume_pct": get_system_volume(),
        "volume_muted": get_volume_muted(),
        "active_window": get_active_window_title(),
    }


def format_state_for_prompt(snapshot: Optional[dict] = None,
                             lang: str = "en") -> str:
    """Formatea el snapshot como string corto para inyectar al prompt
    del LLM. Solo incluye campos no-None — si pycaw falla en algún
    sistema, no metemos 'volume=None' en el prompt.

    Output ejemplo (es):
      [Estado actual del PC: volumen=65%, no muteado, ventana=Spotify]
    """
    if snapshot is None:
        snapshot = get_state_snapshot()

    parts = []
    vol = snapshot.get("volume_pct")
    muted = snapshot.get("volume_muted")
    if vol is not None:
        if lang.startswith("es"):
            parts.append(f"volumen={vol}%")
        elif lang.startswith("fr"):
            parts.append(f"volume={vol}%")
        else:
            parts.append(f"volume={vol}%")
    if muted is True:
        if lang.startswith("es"):
            parts.append("muteado")
        elif lang.startswith("fr"):
            parts.append("muet")
        else:
            parts.append("muted")
    elif muted is False:
        if lang.startswith("es"):
            parts.append("no muteado")
        elif lang.startswith("fr"):
            parts.append("non muet")
        else:
            parts.append("not muted")

    win = snapshot.get("active_window") or ""
    if win:
        # Truncar títulos largos para no llenar el prompt
        win_short = win[:60] + "…" if len(win) > 60 else win
        if lang.startswith("es"):
            parts.append(f"ventana activa={win_short!r}")
        elif lang.startswith("fr"):
            parts.append(f"fenêtre active={win_short!r}")
        else:
            parts.append(f"active window={win_short!r}")

    if not parts:
        return ""

    if lang.startswith("es"):
        return f"[Estado del PC ahora mismo: {', '.join(parts)}]"
    elif lang.startswith("fr"):
        return f"[État du PC en ce moment: {', '.join(parts)}]"
    return f"[PC state right now: {', '.join(parts)}]"
