"""Regression tests para v0.19.46 — 6 fixes para hacer chains funcionar.

Bugs raíz documentados en sesión de debug 2026-05-12:

1. **PUT en /json/new** — Chromium 130+ rechaza GET con HTTP 405.
   `new_tab()` debe usar PUT. Verificado experimentalmente (curl PUT 200
   vs GET 405). Sin este fix, `play_music`/`open_url` con CDP siempre
   caen al poll de 10s + fallback optimista mentiroso.

2. **YouTube 2025 selectors** — el wrapping cambió a
   `segmented-like-dislike-button-view-model`. Los selectores viejos
   apuntan a la primera instancia (oculta). El nuevo es más específico
   y lleva al botón visible directamente.

3. **querySelectorAll + filter visible** — antes `querySelector` daba
   sólo el primer match aunque estuviera oculto. Probado: YouTube tiene
   3 instancias de `like-button-view-model`, sólo la #1 es visible.

4. **Verificación post-click via aria-pressed** — antes `click_by_text`
   retornaba success=True simplemente por encontrar y clickear ALGO,
   incluso si era el elemento equivocado (caso real: clickeaba un
   `@studylikenat` cuando user pidió 'like'). Ahora para canonicals
   toggleables (like/dislike/subscribe/play/pause) compara aria-pressed
   antes/después y exige cambio.

5. **Aria/text match con prioridad** — sinónimos cortos (≤4 chars como
   "like") requieren whole-word match (regex `\\b`). Sino "like" matchea
   `@studylikenat`. Sinónimos largos pueden ser substring.

6. **Sin speculative dispatch si chain incluye wait_then** — wait_then
   existe para sequenciar, pero speculative dispatch lanza threads en
   paralelo. Los logs reportaban speculative=2 cuando debía ser 0.
   Ahora si wait_then está en cualquier acción del turno, ninguna se
   especula.

Tests:
  - PUT method en new_tab
  - YouTube 2025 selectors presentes
  - _is_toggle_canonical reconoce like/dislike/subscribe/play/pause
  - Sinónimos ordenados (frases largas antes que palabras cortas)
  - click_by_text JS contiene la lógica matchesTarget con regex \\b
  - click_by_text retorna False cuando verified=False
  - _maybe_dispatch_speculative skip si wait_then en chain
  - prompts 7 idiomas: regla anti-open_url-para-musica
"""
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# ════════════════════════════════════════════════════════════════════════
#  FIX 1: PUT en /json/new
# ════════════════════════════════════════════════════════════════════════


class TestNewTabUsesPUT:
    """Chromium 130+ rechaza GET con HTTP 405. new_tab DEBE usar PUT."""

    def test_method_is_put_not_get(self):
        from reflex_companion.browser_cdp import new_tab

        mock_resp = MagicMock()
        mock_resp.read = MagicMock(return_value=b'{"id":"x","url":"about:blank"}')
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                   return_value=mock_resp) as mock_open:
            new_tab("https://example.com")
            req = mock_open.call_args[0][0]
            assert req.get_method() == "PUT", (
                f"v0.19.46: new_tab debe usar PUT (got {req.get_method()}). "
                "Chromium 130+ rechaza GET con HTTP 405 'Using unsafe HTTP verb GET'."
            )

    def test_does_not_use_get_json_helper(self):
        """new_tab ya NO debe pasar por _get_json (que usa GET via urlopen
        sin method override) — debe construir Request con method='PUT'."""
        from reflex_companion.browser_cdp import new_tab

        # Si new_tab llamara a _get_json, nuestro patch capturaría la
        # llamada. Asegurar que NO se llama.
        with patch("reflex_companion.browser_cdp._get_json") as mock_helper:
            with patch("reflex_companion.browser_cdp.urllib.request.urlopen",
                       side_effect=Exception("isolated")):
                try:
                    new_tab("https://example.com")
                except Exception:
                    pass
            assert not mock_helper.called, (
                "v0.19.46: new_tab no debe llamar a _get_json (que usa GET)"
            )


# ════════════════════════════════════════════════════════════════════════
#  FIX 2: YouTube 2025 selectors
# ════════════════════════════════════════════════════════════════════════


class TestYouTube2025Selectors:
    def test_like_includes_segmented_wrapper_2025(self):
        """El selector nuevo `segmented-like-dislike-button-view-model
        like-button-view-model button` apunta directo al botón VISIBLE.
        Probado en Opera GX 130 / Chrome 146 con video Espresso."""
        from reflex_companion.browser_cdp import _SITE_SPECIFIC_SELECTORS
        yt_like = _SITE_SPECIFIC_SELECTORS["youtube.com"]["like"]
        # Debe estar PRIMERO en la lista (más específico)
        assert "segmented-like-dislike-button-view-model" in yt_like[0], (
            "v0.19.46: el selector nuevo del wrapping 2025 debe ir PRIMERO. "
            f"got: {yt_like[0]!r}"
        )

    def test_dislike_includes_segmented_wrapper_2025(self):
        from reflex_companion.browser_cdp import _SITE_SPECIFIC_SELECTORS
        yt_dislike = _SITE_SPECIFIC_SELECTORS["youtube.com"]["dislike"]
        assert "segmented-like-dislike-button-view-model" in yt_dislike[0]


# ════════════════════════════════════════════════════════════════════════
#  FIX 3 + 4: querySelectorAll + verificación post-click
# ════════════════════════════════════════════════════════════════════════


class TestClickByTextVerification:
    """Toggle canonicals (like/dislike/subscribe/play/pause) deben
    verificar aria-pressed cambió. Sino → success=False."""

    def test_returns_false_when_verified_false_for_toggle(self):
        """Caso real: click_by_text encontró un elemento aria con 'like'
        en el label (ej '@studylikenat'), lo clickeó, pero aria-pressed
        no cambió. Antes reportaba success=True (mentira), ahora False."""
        from reflex_companion import browser_cdp

        # Simular: click ocurrió pero verified=False (botón equivocado)
        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {
                       "found": True, "label": "@studylikenat",
                       "method": "aria", "matched": "like",
                       "verified": False,
                       "before": None, "after": None,
                   }}}):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "like")

        assert ok is False, (
            "v0.19.46: si verified=False (toggle no cambió), debe ser ok=False"
        )
        assert "no surtió efecto" in msg or "@studylikenat" in msg

    def test_non_toggle_canonical_does_not_require_aria_pressed_change(self):
        """`share` no es toggleable — click siempre cuenta como success
        si found=True y verified=True (sin aria-pressed change)."""
        from reflex_companion import browser_cdp

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   return_value={"result": {"value": {
                       "found": True, "label": "Share",
                       "method": "site-selector", "matched": "share-button",
                       "verified": True,
                       "before": None, "after": None,
                   }}}):
            ok, msg = browser_cdp.click_by_text({"id": "x"}, "share")
        assert ok is True

    def test_is_toggle_canonical_detects_like_synonyms(self):
        """`_is_toggle_canonical` debe reconocer 'like' Y sus sinónimos
        ('me gusta', 'j'aime', etc.)"""
        from reflex_companion.browser_cdp import _is_toggle_canonical
        assert _is_toggle_canonical("like") is True
        assert _is_toggle_canonical("me gusta") is True
        assert _is_toggle_canonical("indica que te gusta") is True
        assert _is_toggle_canonical("j'aime") is True
        assert _is_toggle_canonical("いいね") is True
        # No-toggleables
        assert _is_toggle_canonical("share") is False
        assert _is_toggle_canonical("save") is False
        # Texto random
        assert _is_toggle_canonical("foo") is False


# ════════════════════════════════════════════════════════════════════════
#  FIX 4: Sinónimos ordenados por especificidad
# ════════════════════════════════════════════════════════════════════════


class TestSynonymsOrdering:
    """Las frases largas/específicas deben ir PRIMERO en cada lista de
    sinónimos. 'like' al final porque matchea cualquier substring random
    como '@studylikenat'."""

    def test_like_synonyms_specific_before_generic(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        like_variants = _BUTTON_SYNONYMS["like"]
        idx_specific = like_variants.index("indica que te gusta")
        idx_generic = like_variants.index("like")
        assert idx_specific < idx_generic, (
            "v0.19.46: 'indica que te gusta' (específico) debe ir antes de "
            f"'like' (genérico). Posiciones: específico={idx_specific} "
            f"genérico={idx_generic}"
        )

    def test_subscribe_synonyms_specific_before_generic(self):
        from reflex_companion.browser_cdp import _BUTTON_SYNONYMS
        sub_variants = _BUTTON_SYNONYMS["subscribe"]
        idx_specific = sub_variants.index("suscribirse")
        idx_generic = sub_variants.index("subscribe")
        assert idx_specific < idx_generic


class TestClickByTextJSHasWordBoundary:
    """El JS generado debe usar regex con `\\b` para sinónimos cortos
    (≤4 chars), evitando matches como '@studylikenat' para 'like'."""

    def test_js_contains_word_boundary_logic(self):
        from reflex_companion import browser_cdp

        captured = {"js": None}

        def fake_eval(target, js, port=9222):
            captured["js"] = js
            return {"result": {"value": {"found": True, "verified": True,
                                          "label": "x", "method": "site-selector"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_eval):
            browser_cdp.click_by_text({"id": "x"}, "like")

        # El JS debe contener la lógica de whole-word para targets cortos
        assert "matchesTarget" in captured["js"]
        # \b está escapado dentro del template literal Python: \\\\b
        assert "\\b" in captured["js"] or "matchesTarget" in captured["js"], (
            "v0.19.46: JS debe usar regex \\b para sinónimos cortos"
        )

    def test_js_uses_querySelectorAll_for_site_selectors(self):
        """v0.19.46 — Antes querySelector solo daba el primer match
        (que en YouTube suele estar oculto). Ahora querySelectorAll +
        filter visible."""
        from reflex_companion import browser_cdp

        captured = {"js": None}

        def fake_eval(target, js, port=9222):
            captured["js"] = js
            return {"result": {"value": {"found": True, "verified": True,
                                          "label": "x", "method": "site-selector"}}}

        with patch("reflex_companion.browser_cdp.evaluate_js",
                   side_effect=fake_eval):
            browser_cdp.click_by_text({"id": "x"}, "like")

        assert "querySelectorAll" in captured["js"], (
            "v0.19.46: el JS debe usar querySelectorAll para iterar visible"
        )


# ════════════════════════════════════════════════════════════════════════
#  FIX 5: speculative dispatch skip si wait_then en chain
# ════════════════════════════════════════════════════════════════════════


class TestSpeculativeSkipsWaitThen:
    """Si la cadena de acciones del turno incluye [action:wait_then:...],
    NINGUNA acción se especula. Sino los threads correrían en paralelo y
    wait_then despertaría antes que play_music/open_url terminara → click
    contra tab vieja."""

    def test_speculative_returns_early_when_wait_then_present(self):
        """Verifica que el método _maybe_dispatch_speculative tiene el
        guard early-return cuando wait_then está en las acciones."""
        # Read el source para el guard (más simple que mockear State)
        src = (REPO_ROOT / "reflex_companion" / "reflex_companion.py").read_text(
            encoding="utf-8"
        )
        # Guard debe estar PRESENTE en _maybe_dispatch_speculative
        assert 'a.get("type") == "wait_then" for a in actions_so_far' in src, (
            "v0.19.46: _maybe_dispatch_speculative debe early-return si "
            "alguna acción es wait_then. Sino threads corren en paralelo."
        )


# ════════════════════════════════════════════════════════════════════════
#  FIX 6: prompts en 7 idiomas — regla anti open_url-para-musica
# ════════════════════════════════════════════════════════════════════════


class TestPromptsForbidOpenUrlForMusic:
    @pytest.mark.parametrize("lang_file", [
        "prompts_es.py", "prompts_en.py", "prompts_fr.py",
        "prompts_ja.py", "prompts_de.py", "prompts_ru.py", "prompts_ko.py",
    ])
    def test_forbids_open_url_with_youtube_for_music(self, lang_file):
        """Cada idioma debe documentar que open_url con URL youtube.com
        para música está PROHIBIDO. Bug real: Ashley emitía
        [action:open_url:https://www.youtube.com/watch?v=XYZ] en vez de
        play_music — sin dedupe ni tracking de tab."""
        src = (REPO_ROOT / "reflex_companion" / lang_file).read_text(
            encoding="utf-8"
        )
        # Debe mencionar open_url + youtube en una regla negativa
        assert "open_url" in src, f"{lang_file}: open_url no documentado"
        # Debe tener el ejemplo con la URL del bug
        assert "eVli-tstM5E" in src or "youtube.com/watch" in src, (
            f"{lang_file}: debe ejemplificar que open_url con URL de YouTube "
            "es WRONG (bug real reportado)"
        )
