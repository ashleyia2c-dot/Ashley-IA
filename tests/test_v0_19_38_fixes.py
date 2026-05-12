"""Regression tests para v0.19.38 — fix del 'play_music abre 2 tabs del
mismo video' (bug CRÍTICO reportado por user en producción).

Causa raíz identificada:
  • CDP path llama `_cdp.new_tab(video_url)` → browser RECIBE la request
    y abre la tab
  • PERO el HTTP response de `_get_json` puede tardar >3s en Opera (timeout
    default), devolviendo None aunque la tab YA esté abierta
  • Antes: `new_t is None` → fallthrough a `webbrowser.open(video_url)` →
    SEGUNDA tab del mismo video
  • Resultado: 2 tabs idénticas, 1 sola system_result en la UI

Fix:
  • Poll de tabs después de que `new_tab` devuelva None — si la tab
    apareció pese al timeout, NO fallback (return success).
  • Si después de 1s aún no aparece la tab, ahí sí webbrowser.open.
  • Belt-and-suspenders: post-webbrowser sweep que cierra duplicados
    si por cualquier otra razón aparecen 2+ tabs con el mismo videoId.
"""
import sys
from unittest.mock import patch, MagicMock

import pytest


def _vid_url(vid: str = "abc12345678") -> str:
    return f"https://www.youtube.com/watch?v={vid}"


@pytest.fixture
def fast_sleep():
    """Patch time.sleep so tests don't take 2-3s each (polls + verification)."""
    with patch("reflex_companion.actions.time.sleep"):
        yield


@pytest.fixture
def mock_cdp_module():
    """Inject a mock browser_cdp module so the dynamic
    `from . import browser_cdp as _cdp` inside play_music picks it up.

    `from . import X` resuelve primero como atributo del package padre,
    no de sys.modules. Si otro test ya importó browser_cdp, hay que
    parchear AMBOS lugares para que el mock funcione consistentemente."""
    import reflex_companion
    mock = MagicMock()
    mock.is_cdp_available.return_value = True
    mock.find_tabs_matching.return_value = []
    mock.list_tabs.return_value = []
    mock.close_tab.return_value = True
    mock.new_tab.return_value = None

    saved_sys = sys.modules.get("reflex_companion.browser_cdp")
    saved_attr = getattr(reflex_companion, "browser_cdp", None)

    sys.modules["reflex_companion.browser_cdp"] = mock
    reflex_companion.browser_cdp = mock

    try:
        yield mock
    finally:
        # Restaurar sys.modules
        if saved_sys is not None:
            sys.modules["reflex_companion.browser_cdp"] = saved_sys
        else:
            sys.modules.pop("reflex_companion.browser_cdp", None)
        # Restaurar atributo del package
        if saved_attr is not None:
            reflex_companion.browser_cdp = saved_attr
        elif hasattr(reflex_companion, "browser_cdp"):
            delattr(reflex_companion, "browser_cdp")


@pytest.fixture
def stub_legacy_deps():
    """Stub las dependencias del legacy path (_capture_browser_hwnd,
    _get_browser_tabs_via_uia, _get_all_browser_hwnds, webbrowser.open)
    para que los tests no hagan llamadas reales al sistema."""
    with patch("reflex_companion.actions._capture_browser_hwnd",
               return_value=None), \
         patch("reflex_companion.actions._get_browser_tabs_via_uia",
               return_value=["tab1", "tab2"]), \
         patch("reflex_companion.actions._get_all_browser_hwnds",
               return_value=[]), \
         patch("reflex_companion.actions.webbrowser.open") as mock_wbo:
        yield mock_wbo


# ════════════════════════════════════════════════════════════════════════
#  Fix 1 — Poll después de new_tab returning None
# ════════════════════════════════════════════════════════════════════════


class TestCDPNewTabNoneButTabAppeared:
    """Caso típico Opera: new_tab() devuelve None por timeout HTTP,
    pero el browser SÍ abrió la tab. No debe fallthrough a webbrowser.open."""

    def test_polls_for_tab_after_new_tab_none(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Cuando new_tab → None Y la tab APARECE en poll, retornar success
        sin fallthrough a webbrowser.open."""
        from reflex_companion import actions

        target_url = _vid_url("abc12345678")

        # find_tabs_matching: primera vez vacío (loop close-old-yt),
        # luego devuelve la tab que abrió CDP (visible en poll)
        polled_state = {"calls": 0}

        def fake_find_tabs(*_args, **_kwargs):
            polled_state["calls"] += 1
            if polled_state["calls"] == 1:
                return []  # Loop close-old-yt: no hay tabs viejas
            # En polls subsiguientes: ya hay tab (CDP sí abrió)
            return [{
                "id": "tab1", "title": "Music - YouTube",
                "url": target_url,
            }]

        mock_cdp_module.list_tabs.side_effect = fake_find_tabs
        mock_cdp_module.find_tabs_matching.side_effect = fake_find_tabs  # legacy compat
        mock_cdp_module.new_tab.return_value = None  # ← Bug trigger

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Music")):
            msg, browser_opened, success = actions.play_music(
                "test music", prefer_cdp=True, lang="en",
            )

        # CRÍTICO: webbrowser.open NO debe haberse llamado, porque el
        # poll detectó que la tab apareció vía CDP
        assert not stub_legacy_deps.called, (
            "BUG REGRESIÓN v0.19.38: cuando new_tab=None pero la tab ya "
            "está abierta (visible en poll), NO debe caer a webbrowser.open. "
            "Eso abría 2 tabs del mismo video en producción."
        )
        assert success is True

    def test_no_fallback_when_poll_exhausts_without_tab_appearing(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """v0.19.39 — REGLA NUEVA: si CDP estaba disponible y new_tab fue
        llamado, NUNCA hacemos fallback a webbrowser.open desde el path
        CDP. Aunque el poll de 10s no encuentre la tab, asumimos que el
        browser eventualmente la abrirá (mejor que duplicar en PCs lentos).

        Antes (v0.19.38): poll fallaba → fallback → 2 tabs en PCs lentos.
        Ahora (v0.19.39): poll falla → return success optimista, NO fallback.
        """
        from reflex_companion import actions

        # find_tabs_matching siempre devuelve [] → tab nunca aparece
        mock_cdp_module.find_tabs_matching.return_value = []
        mock_cdp_module.list_tabs.return_value = []
        mock_cdp_module.new_tab.return_value = None

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(_vid_url("xyz98765432"), "Music")):
            msg, _, success = actions.play_music("test", prefer_cdp=True, lang="en")

        # CRÍTICO v0.19.39: NO debe haber fallback a webbrowser.open
        # incluso si el poll falla totalmente
        assert not stub_legacy_deps.called, (
            "v0.19.39: con CDP disponible, NUNCA fallback a webbrowser.open "
            "desde el path CDP. Si la HTTP request se envió, asumimos que "
            "el browser eventualmente abrirá la tab. Hacer fallback duplica "
            "tabs en PCs lentos donde el browser tarda >10s en cold start."
        )

    def test_falls_back_only_when_cdp_path_throws_exception(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """v0.19.39 — el ÚNICO caso donde fallbackeamos a webbrowser.open
        desde el path CDP es cuando CDP REALMENTE lanzó una excepción
        (no solo lento)."""
        from reflex_companion import actions

        # CDP path crashea con excepción real
        mock_cdp_module.find_tabs_matching.side_effect = RuntimeError("CDP crashed")
        mock_cdp_module.list_tabs.side_effect = RuntimeError("CDP crashed")

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(_vid_url("crash1234567"), "Music")):
            actions.play_music("test", prefer_cdp=True, lang="en")

        # Excepción real → SÍ debe fallback (red de seguridad)
        assert stub_legacy_deps.called, (
            "Cuando CDP path REALMENTE crashea con excepción (no solo "
            "lento), SÍ debe fallback a webbrowser.open como red de seguridad"
        )


class TestCDPNewTabSuccessNoFallthrough:
    """Happy path: new_tab → dict con id → return early, sin fallthrough."""

    def test_new_tab_success_no_webbrowser_open(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        from reflex_companion import actions

        url = _vid_url("ok123456789")
        mock_cdp_module.new_tab.return_value = {"id": "new1", "url": url}
        mock_cdp_module.find_tabs_matching.return_value = []  # no old tabs
        mock_cdp_module.list_tabs.return_value = []  # v0.19.41 path

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(url, "OK Music")):
            msg, browser_opened, success = actions.play_music(
                "ok", prefer_cdp=True, lang="en",
            )

        assert success is True
        assert not stub_legacy_deps.called, (
            "Happy path CDP (new_tab devuelve dict válido) NO debe "
            "caer a webbrowser.open"
        )


# ════════════════════════════════════════════════════════════════════════
#  Fix 2 — Belt-and-suspenders dedupe sweep
# ════════════════════════════════════════════════════════════════════════


class TestPostActionDedupeSweep:
    """v0.19.38 — si tras toda la lógica resultan 2+ tabs con el mismo
    videoId, el sweep final cierra los extras."""

    def test_closes_duplicates_when_cdp_threw_and_legacy_path_ran(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """v0.19.39 — sweep se ejecuta cuando CDP path lanzó excepción y
        caímos a webbrowser.open. Si tras eso hay 2+ tabs con el mismo
        videoId, sweep cierra los extras.

        (En v0.19.39, este es el ÚNICO escenario donde sweep corre desde
        CDP-then-legacy, porque con poll exhausto NO caemos a legacy.)
        """
        from reflex_companion import actions

        target_url = _vid_url("dup12345678")
        target_vid = "dup12345678"

        # CDP path crashea → fallback a legacy → webbrowser.open → sweep
        # ve los dos tabs (uno del browser que abrió pre-crash, otro
        # de webbrowser.open). Sweep cierra el extra.
        call_count = {"n": 0}

        def fake_find_tabs(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Init dedupe check al top de play_music — no existing
                return []
            # Sweep call (después de webbrowser.open) ve los duplicados
            return [
                {"id": "tab1", "title": "Dup - YT", "url": target_url},
                {"id": "tab2", "title": "Dup - YT", "url": target_url},
            ]

        # Hacemos que el CDP path crashee para que caiga a legacy
        # (close_tab del loop close-old-yt OK, pero new_tab raises)
        mock_cdp_module.list_tabs.side_effect = fake_find_tabs
        mock_cdp_module.find_tabs_matching.side_effect = fake_find_tabs  # legacy compat
        mock_cdp_module.new_tab.side_effect = RuntimeError("simulated CDP crash")

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Dup Music")):
            actions.play_music("dup", prefer_cdp=True, lang="en")

        # Sweep debe haber cerrado el duplicado
        close_calls = mock_cdp_module.close_tab.call_args_list
        close_ids = [c.args[0] if c.args else c.kwargs.get("tab_id")
                     for c in close_calls]
        assert "tab2" in close_ids, (
            f"Sweep debe cerrar la tab duplicada (tab2). "
            f"Close calls IDs: {close_ids}"
        )

    def test_sweep_not_called_when_only_one_tab(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Caso normal: solo 1 tab tras la acción → sweep NO cierra nada."""
        from reflex_companion import actions

        target_url = _vid_url("solo12345678")
        call_count = {"n": 0}

        def fake_find_tabs(*_args, **_kwargs):
            call_count["n"] += 1
            # Calls 1 (init dedupe) y 2 (close-old-yt loop): no hay tabs
            # viejas → no se cierran (el_one NO está aún)
            if call_count["n"] <= 2:
                return []
            # Sweep call: ahora sí hay 1 tab (la nueva), pero solo 1 → no
            # debe cerrarse
            return [
                {"id": "the_one", "title": "Solo - YT", "url": target_url},
            ]

        # Forzar fallback via CDP exception
        mock_cdp_module.list_tabs.side_effect = fake_find_tabs
        mock_cdp_module.find_tabs_matching.side_effect = fake_find_tabs  # legacy compat
        mock_cdp_module.new_tab.side_effect = RuntimeError("CDP crash")

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Solo")):
            actions.play_music("solo", prefer_cdp=True, lang="en")

        # close_tab no debe llamarse para "the_one" (es la única tras la acción)
        close_calls = mock_cdp_module.close_tab.call_args_list
        close_ids = [c.args[0] if c.args else c.kwargs.get("tab_id")
                     for c in close_calls]
        assert "the_one" not in close_ids, (
            "El sweep NO debe cerrar tabs cuando solo hay 1"
        )


# ════════════════════════════════════════════════════════════════════════
#  v0.19.39 — Slow PC scenarios (cold browser start, HDD, antivirus)
# ════════════════════════════════════════════════════════════════════════


class TestSlowPCScenarios:
    """v0.19.39 — el problema específico del user: en PCs gama baja
    el browser puede tardar mucho en abrir la tab. NUNCA debemos
    abrir una segunda tab por impaciencia."""

    def test_extended_poll_finds_tab_after_slow_browser(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """Simula PC lento: tab aparece SOLO después del 6º poll attempt
        (~5s). El código v0.19.38 con poll de 1s habría caído a fallback.
        v0.19.39 con poll de 10s debe encontrarla."""
        from reflex_companion import actions

        target_url = _vid_url("slow12345678")
        call_count = {"n": 0}

        def fake_find_tabs(*_args, **_kwargs):
            call_count["n"] += 1
            # Calls 1-2: init dedupe + close-old-yt loop → []
            # Calls 3-7: poll attempts 1-5 → [] (browser still loading)
            # Call 8+: poll attempt 6 finalmente ve la tab
            if call_count["n"] < 8:
                return []
            return [{
                "id": "slow_tab",
                "title": "Slow Music - YouTube",
                "url": target_url,
            }]

        mock_cdp_module.list_tabs.side_effect = fake_find_tabs
        mock_cdp_module.find_tabs_matching.side_effect = fake_find_tabs  # legacy compat
        mock_cdp_module.new_tab.return_value = None  # CDP timeout en PC lento

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Slow Music")):
            msg, _, success = actions.play_music(
                "slow song", prefer_cdp=True, lang="en",
            )

        assert success is True
        assert not stub_legacy_deps.called, (
            "v0.19.39: en PC lento donde tab tarda 5s en aparecer, NO "
            "debe haber fallback a webbrowser.open. El poll de 10s la encuentra."
        )

    def test_extended_poll_maxes_at_10_seconds(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        """El poll NO debe esperar más de ~10s incluso si la tab nunca aparece.
        Después de 10s asumimos optimistamente que el browser la abrirá."""
        from reflex_companion import actions

        # find_tabs_matching siempre [] → tab nunca aparece
        mock_cdp_module.find_tabs_matching.return_value = []
        mock_cdp_module.list_tabs.return_value = []
        mock_cdp_module.new_tab.return_value = None

        # Trackear cuántas calls a find_tabs_matching hizo el código
        # (debería ser limitado: dedupe init + close-old-yt + 4+12 polls)
        call_count = {"n": 0}
        original_side_effect = mock_cdp_module.find_tabs_matching.side_effect
        def counted(hint, port=9222):
            call_count["n"] += 1
            return []
        mock_cdp_module.find_tabs_matching.side_effect = counted

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(_vid_url("never1234567"), "Never")):
            actions.play_music("never", prefer_cdp=True, lang="en")

        # Polls: 4 fast + 12 slow = 16 + init dedupe (1) + close-old-yt (1) = 18 max
        # No fallback (sin webbrowser.open) por filosofía v0.19.39
        assert not stub_legacy_deps.called, (
            "Con poll exhausto (10s pasados sin tab), NO debe fallback. "
            "Esperamos optimismamente que el browser la abrirá eventualmente."
        )
        # Sanity: no se polea más de ~20 veces
        assert call_count["n"] <= 25, (
            f"find_tabs_matching llamada {call_count['n']} veces — "
            "demasiado, debería capped a ~18"
        )


# ════════════════════════════════════════════════════════════════════════
#  Fix 3 — Validar dedupe inicial (regresión guard v0.19.29)
# ════════════════════════════════════════════════════════════════════════


class TestPreActionDedupeStillWorks:
    """No regresión del dedupe v0.19.29 — si ya hay una tab con el
    videoId al inicio, NO reabrir."""

    def test_existing_tab_returns_early(
            self, fast_sleep, mock_cdp_module, stub_legacy_deps):
        from reflex_companion import actions

        target_url = _vid_url("existing123")
        existing_tab = [
            {"id": "old1", "title": "Existing", "url": target_url}
        ]
        mock_cdp_module.find_tabs_matching.return_value = existing_tab
        mock_cdp_module.list_tabs.return_value = existing_tab  # v0.19.41 path

        with patch("reflex_companion.actions._resolve_youtube_url",
                   return_value=(target_url, "Existing")):
            msg, _, success = actions.play_music(
                "existing", prefer_cdp=True, lang="en",
            )

        assert success is True
        # No abrió tab nueva (ni CDP ni fallback)
        assert not mock_cdp_module.new_tab.called, (
            "Dedupe al inicio debe retornar early ANTES de llamar new_tab"
        )
        assert not stub_legacy_deps.called, (
            "Dedupe al inicio debe retornar early ANTES de webbrowser.open"
        )
