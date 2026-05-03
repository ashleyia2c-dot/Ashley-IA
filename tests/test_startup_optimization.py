"""Guards para las optimizaciones de arranque (v0.17.3).

El user reportó arranques de ~15s. Hicimos 3 cambios:
  1. Reemplazo sirv-cli con servidor HTTP embebido (`_startEmbeddedFrontendServer`)
  2. Activamos fast-path en producción (antes solo en dev)
  3. Bajamos timings de port detection (timeout TCP, sleep post-kill)

Estos tests bloquean regresión: si alguien revierte alguna de estas optimizaciones
(quizás pensando que es defensive), un test rojo le explica por qué importa.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
MAIN_JS = ROOT / "electron" / "main.js"


def _read_main_js() -> str:
    return MAIN_JS.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Embedded HTTP server
# ─────────────────────────────────────────────────────────────────────────────


class TestEmbeddedFrontendServer:
    """El servidor HTTP embebido reemplaza sirv-cli y vive en main.js."""

    def test_function_exists(self):
        content = _read_main_js()
        assert "_startEmbeddedFrontendServer" in content, (
            "Falta función _startEmbeddedFrontendServer — sin esto el "
            "fast-path en producción se cuelga (v0.13.2 bug)."
        )

    def test_global_var_defined(self):
        content = _read_main_js()
        assert "let embeddedFrontendServer" in content, (
            "Falta el global `embeddedFrontendServer` para tracking de "
            "lifecycle del servidor HTTP embebido."
        )

    def test_uses_http_create_server(self):
        content = _read_main_js()
        # Buscamos http.createServer dentro de la función embebida
        assert re.search(
            r"_startEmbeddedFrontendServer[\s\S]+?http\.createServer",
            content,
        ), "El servidor embebido debe usar http.createServer (no Express, no sirv)"

    def test_binds_localhost_only(self):
        """Seguridad: NUNCA bind a 0.0.0.0 — solo localhost."""
        content = _read_main_js()
        # Buscamos el listen del servidor embebido
        match = re.search(
            r"_startEmbeddedFrontendServer[\s\S]+?\.listen\(([^,]+),\s*['\"]([^'\"]+)['\"]",
            content,
        )
        assert match, "No encontré server.listen(port, host) en _startEmbeddedFrontendServer"
        host = match.group(2)
        assert host == "127.0.0.1", (
            f"El servidor embebido bind a {host!r} — DEBE ser 127.0.0.1. "
            f"Bind a 0.0.0.0 expone el frontend a la red local."
        )

    def test_path_traversal_blocked(self):
        """Seguridad: bloquear `..` en URL paths."""
        content = _read_main_js()
        # En la función debe haber check de '..'
        match = re.search(
            r"_startEmbeddedFrontendServer[\s\S]+?createServer[\s\S]+?\.\.",
            content,
        )
        assert match, "Falta check anti-path-traversal (`..`) en URL handling"

    def test_spa_fallback(self):
        """SPA fallback: rutas no-archivo → index.html."""
        content = _read_main_js()
        # En la función debe haber lógica de fallback a index.html
        assert re.search(
            r"_startEmbeddedFrontendServer[\s\S]+?indexPath",
            content,
        ), "Falta SPA fallback a index.html en _startEmbeddedFrontendServer"

    def test_assets_immutable_cache(self):
        """Bundles hashados en /assets/ deben tener Cache-Control inmutable."""
        content = _read_main_js()
        match = re.search(
            r"_startEmbeddedFrontendServer[\s\S]+?(immutable|max-age=31536000)",
            content,
        )
        assert match, (
            "Falta Cache-Control inmutable para /assets/* — sin esto los "
            "bundles hashados se re-descargan en cada launch (lento)."
        )

    def test_html_no_cache(self):
        """index.html nunca debe cachearse — tiene refs a hashes que cambian."""
        content = _read_main_js()
        match = re.search(
            r"_startEmbeddedFrontendServer[\s\S]+?\.html[\s\S]+?(no-cache|no-store)",
            content,
        )
        assert match, (
            "index.html no tiene Cache-Control no-cache. Sin esto el browser "
            "puede cachear el HTML viejo apuntando a bundles que ya no existen."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Fast-path enabled in production
# ─────────────────────────────────────────────────────────────────────────────


class TestFastPathInProduction:
    """El fast-path debe estar activo en producción tras v0.17.3."""

    def test_no_isDev_gate_on_fast_path(self):
        """La condición de fast-path NO debe requerir isDev."""
        content = _read_main_js()
        # Buscamos el if que decide fast-path vs slow-path
        # Antes era: if (isDev && hasPrecompiled && isFresh && hasSirv)
        # Ahora debe ser: if (hasPrecompiled && isFresh)
        match = re.search(
            r"if\s*\(\s*hasPrecompiled\s*&&\s*isFresh\s*\)\s*\{",
            content,
        )
        assert match, (
            "La condición de fast-path debe ser `hasPrecompiled && isFresh` "
            "(sin isDev/hasSirv). El gate de isDev causaba arranques de "
            "~14s en producción innecesariamente."
        )

    def test_no_sirv_check_in_decision(self):
        """No debe haber referencia a hasSirv en la decisión de path."""
        content = _read_main_js()
        # hasSirv ya no existe, no debe estar en lógica de decisión
        # (puede estar en comentarios mencionando el cambio histórico)
        # Buscamos uso ACTIVO en código (no en comentarios)
        non_comment_lines = [
            ln for ln in content.splitlines()
            if not ln.strip().startswith("//") and "hasSirv" in ln
        ]
        # Permitimos referencias en logs/strings pero no en decisión
        for line in non_comment_lines:
            if "if" in line or "&&" in line or "||" in line:
                raise AssertionError(
                    f"hasSirv aparece en lógica de decisión: {line.strip()!r}. "
                    f"Sirv ya no se usa en v0.17.3."
                )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Port detection optimizations
# ─────────────────────────────────────────────────────────────────────────────


class TestPortDetectionTimings:
    """Timings de port detection deben ser agresivos pero seguros."""

    def test_tcp_timeout_under_150ms(self):
        """isPortInUse: socket.setTimeout debe ser < 150ms."""
        content = _read_main_js()
        # Buscamos socket.setTimeout dentro de isPortInUse
        match = re.search(
            r"function isPortInUse[\s\S]+?socket\.setTimeout\((\d+)\)",
            content,
        )
        assert match, "No encontré socket.setTimeout en isPortInUse"
        timeout = int(match.group(1))
        assert timeout < 150, (
            f"isPortInUse timeout = {timeout}ms — debería ser < 150ms. "
            f"Conexiones a 127.0.0.1 son <5ms, no hay razón para timeouts altos."
        )
        # También debe ser > 30 (margen para CPU ocupada)
        assert timeout >= 30, (
            f"isPortInUse timeout = {timeout}ms — muy bajo, riesgo de "
            f"falsos negativos en CPUs lentas."
        )

    def test_post_kill_sleep_under_200ms(self):
        """pickReflexPorts: el sleep tras kill debe ser < 200ms."""
        content = _read_main_js()
        # Buscamos el setTimeout en pickReflexPorts después del Promise.all de kills
        match = re.search(
            r"async function pickReflexPorts[\s\S]+?Promise\.all\([\s\S]+?\]\);[\s\S]+?setTimeout\(r => setTimeout\(r,\s*(\d+)\)",
            content,
        )
        # Pattern alternativo: la awaitable promise wrap
        if not match:
            match = re.search(
                r"async function pickReflexPorts[\s\S]+?await new Promise\(r => setTimeout\(r,\s*(\d+)\)\)",
                content,
            )
        assert match, "No encontré sleep tras kill en pickReflexPorts"
        sleep_ms = int(match.group(1))
        assert sleep_ms < 200, (
            f"Sleep post-kill = {sleep_ms}ms — debería ser < 200ms. "
            f"Windows libera sockets locales en <50ms tras taskkill /F."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Lifecycle / cleanup
# ─────────────────────────────────────────────────────────────────────────────


class TestEmbeddedServerCleanup:
    """El servidor embebido debe cerrarse en shutdown para liberar el puerto."""

    def test_close_in_killReflex(self):
        content = _read_main_js()
        # Buscamos embeddedFrontendServer.close() en killReflex
        match = re.search(
            r"function killReflex[\s\S]+?embeddedFrontendServer[\s\S]+?\.close\(\)",
            content,
        )
        assert match, (
            "killReflex no cierra embeddedFrontendServer. Sin esto el puerto "
            "queda en TIME_WAIT y la próxima sesión tarda más en encontrar "
            "puerto libre."
        )

    def test_set_to_null_after_close(self):
        content = _read_main_js()
        # Tras cerrar, debe ponerse a null para evitar double-close
        match = re.search(
            r"embeddedFrontendServer\.close\(\)[\s\S]+?embeddedFrontendServer\s*=\s*null",
            content,
        )
        assert match, (
            "embeddedFrontendServer no se pone a null tras close() — "
            "riesgo de double-close en re-entrancy."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. waitForReflex se adapta al path
# ─────────────────────────────────────────────────────────────────────────────


class TestWaitForReflexAdaptive:
    """waitForReflex debe pollar backend en fast-path, frontend en slow-path."""

    def test_polls_backend_in_fast_path(self):
        content = _read_main_js()
        # Buscamos lógica condicional basada en embeddedFrontendServer
        match = re.search(
            r"function waitForReflex[\s\S]+?embeddedFrontendServer[\s\S]+?REFLEX_BACKEND_PORT",
            content,
        )
        assert match, (
            "waitForReflex no se adapta al path. En fast-path debe pollar "
            "backend (frontend embebido responde instant → polling frontend "
            "da false positive antes de que Python esté listo)."
        )

    def test_poll_interval_under_300ms(self):
        """El interval de polling debe ser corto para detectar ready rápido."""
        content = _read_main_js()
        # Buscamos setTimeout(check, N) en waitForReflex
        match = re.search(
            r"function waitForReflex[\s\S]+?setTimeout\(check,\s*(\d+)\)",
            content,
        )
        assert match, "No encontré el polling interval en waitForReflex"
        interval = int(match.group(1))
        assert interval < 300, (
            f"Polling interval = {interval}ms. Debería ser < 300ms para "
            f"detectar ready rápido — la fase 'casi listo' es corta."
        )
