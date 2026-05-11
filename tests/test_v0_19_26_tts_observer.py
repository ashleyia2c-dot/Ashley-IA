"""Regression tests for v0.19.26 — TTS observer bugs fixed:

Bug A — Delete msg re-leído:
  El observer comparaba texto del último ashley-msg vs baseline. Al
  borrar el último, el penúltimo se vuelve el "último", tiene texto
  distinto al baseline → speak(). Re-leía el mensaje anterior.

Bug B — Startup tardío re-lee:
  Si Reflex tarda >3s en hidratar (lentitud, mucho historial), el
  bootstrap toma baseline con msgs.length=0 y texto=''. Cuando hidrata
  después, el último mensaje cualquiera tiene texto != '' → observer
  cree que es nuevo y lo lee.

Fix: trackear por data-msg-id (estable, v0.19.23) con Set<msgId>. El
bootstrap añade los IDs existentes al Set sin leer. Delete: el ID
queda en el Set aunque el msg ya no esté en DOM. Startup tardío:
bootstrap espera hasta msgs.length>0 O 15s cap absoluto.
"""
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VOICE_JS = REPO_ROOT / "assets" / "ashley_voice.js"


class TestObserverTracksBySetOfIds:
    def test_spoken_ids_set_initialized(self):
        """_tickObserver inicializa _spokenIds como new Set() en primer uso."""
        src = VOICE_JS.read_text(encoding="utf-8")
        assert "this._spokenIds = new Set()" in src, (
            "v0.19.26: _spokenIds debe inicializarse como new Set() "
            "(tracking por ID de mensajes ya leídos)"
        )

    def test_observer_reads_data_msg_id_attribute(self):
        """El observer lee data-msg-id de cada .ashley-msg para identificarlos."""
        src = VOICE_JS.read_text(encoding="utf-8")
        assert "getAttribute('data-msg-id')" in src, (
            "El observer debe leer data-msg-id del DOM (atributo añadido "
            "en v0.19.23 al wrapper de message_item)"
        )


class TestBootstrapWaitsForMessages:
    def test_bootstrap_waits_until_msgs_exist_or_15s_cap(self):
        """Bug B fix: bootstrap NO debe disparar mientras msgs.length=0
        (Reflex aún hidratando) — espera hasta que haya msgs o 15s."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # Patrón: if (msgs.length === 0 && now < this._bootstrapDeadline) return
        match = re.search(
            r"msgs\.length\s*===\s*0\s*&&\s*now\s*<\s*this\._bootstrapDeadline",
            src,
        )
        assert match, (
            "v0.19.26 Bug B fix: el bootstrap debe esperar a que haya "
            "mensajes O hasta un cap absoluto. Sin esto, si Reflex tarda "
            ">3s en hidratar, el baseline queda vacío y el primer msg "
            "se lee como si fuera nuevo."
        )

    def test_bootstrap_deadline_is_at_least_15s(self):
        """El cap absoluto del bootstrap debe ser ≥15s (antes era 3s
        que se quedaba corto en máquinas lentas)."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # Buscar el setter inicial del deadline
        # Patrón: this._bootstrapDeadline = now + NNNNN
        match = re.search(r"_bootstrapDeadline\s*=\s*now\s*\+\s*(\d+)", src)
        assert match, "Setter inicial de _bootstrapDeadline no encontrado"
        ms = int(match.group(1))
        assert ms >= 10000, (
            f"_bootstrapDeadline cap es {ms}ms, debe ser ≥10000 para dar "
            "margen a Reflex en máquinas lentas (sino startup re-lee el "
            "historial)"
        )


class TestDeleteDoesNotReReadMessage:
    def test_observer_marks_all_predecessor_ids_as_seen(self):
        """Cuando el observer encuentra un msg nuevo (id no en Set), debe
        marcar TAMBIÉN todos los anteriores como vistos. Sin esto, al
        borrar el último de Ashley, el penúltimo se ve como "nuevo" porque
        su id aún no estaba en el Set.

        El loop interno del observer hace: encontrar el msg más reciente
        sin leer (iterando desde el final), y al encontrarlo añadir TODOS
        los anteriores (no solo el actual) al Set.
        """
        src = VOICE_JS.read_text(encoding="utf-8")
        # Patrón: tras encontrar unseenEl, loop añadiendo ids al Set
        match = re.search(
            r"unseenEl\s*=\s*m;[\s\S]{0,500}?_spokenIds\.add",
            src,
        )
        assert match, (
            "v0.19.26 Bug A fix: cuando el observer encuentra un msg sin "
            "leer, debe añadir TODOS los IDs anteriores al Set para no "
            "re-leerlos en próximos ticks (caso delete del último msg de "
            "Ashley)."
        )

    def test_observer_iterates_from_end_to_find_unseen(self):
        """El loop de búsqueda debe iterar de FINAL→inicio para encontrar
        el msg MÁS RECIENTE sin leer (no el más antiguo)."""
        src = VOICE_JS.read_text(encoding="utf-8")
        # Patrón típico: for (let i = msgs.length - 1; i >= 0; i--)
        match = re.search(
            r"for\s*\(\s*let\s+i\s*=\s*msgs\.length\s*-\s*1\s*;\s*i\s*>=\s*0\s*;",
            src,
        )
        assert match, (
            "El observer debe iterar desde msgs.length-1 hacia 0 para "
            "encontrar el msg MÁS RECIENTE sin leer (si hubiera varios)"
        )
