"""Tests para el cache de clientes LLM (xAI + OpenAI) — v0.16.13.

Antes cada llamada al LLM creaba un nuevo `Client(api_key=...)` que
abría una conexión TCP+TLS nueva (~300-600ms desde Europa al endpoint).
En un mensaje normal con 3-4 llamadas LLM, eso son ~1.2-2.4s de
overhead de network puro.

Ahora los clientes están cacheados a nivel módulo y se reutilizan entre
llamadas → la conexión HTTP/2 se reusa → handshake solo se paga UNA vez
por sesión.

Estos tests bloquean regresión: si alguien refactoriza y vuelve a crear
clientes nuevos en cada llamada, los tests fallan inmediatamente.
"""

from unittest.mock import patch

import pytest


# ══════════════════════════════════════════════════════════════════════
#  xAI client cache (grok_client.py)
# ══════════════════════════════════════════════════════════════════════


class TestXaiClientCache:
    """get_xai_client() debe devolver el mismo Client entre llamadas
    consecutivas, e invalidar si cambia api_key."""

    def setup_method(self):
        # Reset el cache antes de cada test para aislar.
        from reflex_companion import grok_client
        grok_client._xai_client = None
        grok_client._xai_client_api_key = None

    def test_get_xai_client_returns_same_instance_on_consecutive_calls(self):
        """Dos llamadas consecutivas deben devolver el MISMO objeto.
        Sin esto, el handshake TCP+TLS se paga cada vez."""
        from reflex_companion import grok_client

        # Mock el constructor del Client para evitar llamada real al SDK.
        with patch("xai_sdk.Client") as mock_cls:
            client_a = grok_client.get_xai_client()
            client_b = grok_client.get_xai_client()
            # Mismo objeto, no dos instancias.
            assert client_a is client_b, (
                "get_xai_client() devolvió DOS instancias distintas. El "
                "cache no funciona y cada llamada paga handshake completo."
            )
            # Constructor llamado UNA sola vez (la primera).
            assert mock_cls.call_count == 1, (
                f"Client constructor invocado {mock_cls.call_count} veces "
                f"(esperado 1). Cache no funciona."
            )

    def test_get_xai_client_invalidates_on_api_key_change(self):
        """Si XAI_API_KEY cambia (user editó settings), el siguiente call
        debe crear un cliente nuevo con la nueva key."""
        from reflex_companion import grok_client

        with patch("xai_sdk.Client") as mock_cls:
            with patch.object(grok_client, "XAI_API_KEY", "key-1"):
                _ = grok_client.get_xai_client()
            with patch.object(grok_client, "XAI_API_KEY", "key-2"):
                _ = grok_client.get_xai_client()
            # Debe haber llamado al constructor 2 veces — una por cada key.
            assert mock_cls.call_count == 2

    def test_invalidate_xai_client_forces_new_instance(self):
        """invalidate_xai_client() debe forzar creación nueva en próxima call."""
        from reflex_companion import grok_client

        with patch("xai_sdk.Client") as mock_cls:
            client_a = grok_client.get_xai_client()
            grok_client.invalidate_xai_client()
            client_b = grok_client.get_xai_client()
            assert mock_cls.call_count == 2

    def test_helper_is_thread_safe(self):
        """Llamadas concurrentes desde threads no crean clientes duplicados."""
        import threading
        from reflex_companion import grok_client

        results = []
        with patch("xai_sdk.Client") as mock_cls:
            def _worker():
                results.append(grok_client.get_xai_client())

            threads = [threading.Thread(target=_worker) for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()

            # Todos deben haber recibido el mismo cliente.
            assert len(set(id(r) for r in results)) == 1, (
                "Llamadas concurrentes crearon múltiples clientes. "
                "El lock no protege bien."
            )
            # Constructor: 1 sola llamada total a pesar de 10 threads.
            assert mock_cls.call_count == 1


# ══════════════════════════════════════════════════════════════════════
#  OpenAI client cache (llm_provider.py)
# ══════════════════════════════════════════════════════════════════════


class TestOpenaiClientCache:
    """_openai_client() (OpenRouter/Ollama) debe cachear igual que xAI."""

    def setup_method(self):
        from reflex_companion import llm_provider
        llm_provider._openai_cache_client = None
        llm_provider._openai_cache_key = None

    def test_returns_same_instance_when_config_unchanged(self):
        from reflex_companion import llm_provider

        with patch.object(llm_provider, "get_active_config") as mock_cfg:
            mock_cfg.return_value = {
                "api_key": "test-key",
                "base_url": "https://openrouter.ai/api/v1",
            }
            with patch("openai.OpenAI") as mock_openai:
                a = llm_provider._openai_client()
                b = llm_provider._openai_client()
                assert a is b
                assert mock_openai.call_count == 1

    def test_invalidates_on_api_key_change(self):
        from reflex_companion import llm_provider

        with patch.object(llm_provider, "get_active_config") as mock_cfg:
            with patch("openai.OpenAI") as mock_openai:
                mock_cfg.return_value = {"api_key": "k1", "base_url": "url"}
                _ = llm_provider._openai_client()
                mock_cfg.return_value = {"api_key": "k2", "base_url": "url"}
                _ = llm_provider._openai_client()
                assert mock_openai.call_count == 2

    def test_invalidates_on_base_url_change(self):
        """Cambio de base_url (switch entre OpenRouter y Ollama) crea
        cliente nuevo."""
        from reflex_companion import llm_provider

        with patch.object(llm_provider, "get_active_config") as mock_cfg:
            with patch("openai.OpenAI") as mock_openai:
                mock_cfg.return_value = {"api_key": "k", "base_url": "url1"}
                _ = llm_provider._openai_client()
                mock_cfg.return_value = {"api_key": "k", "base_url": "url2"}
                _ = llm_provider._openai_client()
                assert mock_openai.call_count == 2

    def test_invalidate_forces_new(self):
        from reflex_companion import llm_provider

        with patch.object(llm_provider, "get_active_config") as mock_cfg:
            mock_cfg.return_value = {"api_key": "k", "base_url": "url"}
            with patch("openai.OpenAI") as mock_openai:
                _ = llm_provider._openai_client()
                llm_provider.invalidate_openai_client()
                _ = llm_provider._openai_client()
                assert mock_openai.call_count == 2


# ══════════════════════════════════════════════════════════════════════
#  Integration: callers actualizados a usar el cache
# ══════════════════════════════════════════════════════════════════════


class TestCallersUseCache:
    """Verifica que los callers (mental_state, context_compression, etc.)
    NO instancian Client directamente — todos pasan por get_xai_client()."""

    def test_grok_client_has_no_direct_client_instantiation(self):
        """Excepto dentro de get_xai_client() mismo, no debe haber otra
        línea creando Client(api_key=...) en grok_client.py."""
        import inspect
        from reflex_companion import grok_client
        source = inspect.getsource(grok_client)
        # La única línea que crea Client(api_key=...) está dentro de
        # get_xai_client. Cualquier otra línea es regresión.
        client_lines = [
            ln for ln in source.splitlines()
            if "Client(api_key" in ln and not ln.strip().startswith("#")
        ]
        assert len(client_lines) == 1, (
            f"Encontradas {len(client_lines)} líneas que instancian "
            f"Client(api_key=...) en grok_client.py — esperaba SOLO 1 "
            f"(dentro de get_xai_client). Las demás llamadas deben usar "
            f"get_xai_client() para reusar la conexión.\n"
            f"Líneas: {client_lines}"
        )

    def test_mental_state_uses_cached_client(self):
        """mental_state.regenerate_preoccupation NO debe crear Client nuevo."""
        import inspect
        from reflex_companion import mental_state
        source = inspect.getsource(mental_state)
        assert "Client(api_key" not in source, (
            "mental_state.py instancia Client(api_key=...) directamente. "
            "Debe usar get_xai_client() de grok_client para reusar conexión."
        )

    def test_context_compression_uses_cached_client(self):
        """context_compression NO debe crear Client nuevo."""
        import inspect
        from reflex_companion import context_compression
        source = inspect.getsource(context_compression)
        assert "Client(api_key" not in source, (
            "context_compression.py instancia Client(api_key=...) "
            "directamente. Debe usar get_xai_client()."
        )


# ══════════════════════════════════════════════════════════════════════
#  Configuración: STREAM_CHUNK_SIZE y REGEN_AFTER_NEW_MSGS
# ══════════════════════════════════════════════════════════════════════


class TestPerformanceConfig:
    """Constantes que afectan latencia percibida."""

    def test_stream_chunk_size_is_one(self):
        """STREAM_CHUNK_SIZE=1 → yield al UI cada token (mantequilla).
        Si alguien lo sube, los tokens aparecen en ráfagas y se siente lag."""
        from reflex_companion.config import STREAM_CHUNK_SIZE
        assert STREAM_CHUNK_SIZE == 1, (
            f"STREAM_CHUNK_SIZE={STREAM_CHUNK_SIZE}; debe ser 1 para "
            f"yield cada token y que la respuesta se sienta fluida."
        )

    def test_regen_after_new_msgs_is_at_least_15(self):
        """REGEN_AFTER_NEW_MSGS controla cada cuánto regeneramos el resumen
        del historial (LLM call ~3.5s). Demasiado bajo = LLM call frecuente
        en path crítico. 15+ es razonable para chats típicos."""
        from reflex_companion.context_compression import REGEN_AFTER_NEW_MSGS
        assert REGEN_AFTER_NEW_MSGS >= 15, (
            f"REGEN_AFTER_NEW_MSGS={REGEN_AFTER_NEW_MSGS}; valor bajo "
            f"causa regen frecuente que bloquea ~3.5s. Debe ser >=15."
        )

    def test_preoccupation_ttl_at_least_90(self):
        """TTL más largo = menos regen mid-session. 60 era agresivo;
        90+ deja conversaciones de 1-1.5h sin regen interrumpiendo."""
        from reflex_companion.mental_state import PREOCCUPATION_TTL_MINUTES
        assert PREOCCUPATION_TTL_MINUTES >= 90, (
            f"PREOCCUPATION_TTL_MINUTES={PREOCCUPATION_TTL_MINUTES}; "
            f"valor bajo dispara regen mid-session (bloquea ~3.5s). "
            f"Debe ser >=90 minutos."
        )

    def test_default_grok_model_is_not_reasoning_variant(self):
        """El modelo default NO debe ser reasoning — añade ~3.5s TTFT.

        Medido empíricamente con tools/diagnose_latency.py:
            grok-4-1-fast-reasoning:     TTFT 2.3-5.5s
            grok-4-1-fast-non-reasoning: TTFT ~0.6s

        El user reportó 6-7s totales por mensaje con reasoning. La
        variante non-reasoning baja a 2-3s manteniendo calidad para
        80% de mensajes (chat casual, gestures, acciones simples).
        Mismo precio, mismo provider, vision incluida.
        """
        from reflex_companion.config import GROK_MODEL
        # Bloquear cualquier modelo cuyo nombre acabe en "-reasoning"
        # (excluye "non-reasoning" que sí es válido).
        is_reasoning = (
            GROK_MODEL.endswith("-reasoning")
            and not GROK_MODEL.endswith("non-reasoning")
        )
        assert not is_reasoning, (
            f"GROK_MODEL={GROK_MODEL!r} es variant 'reasoning'. Eso "
            f"añade ~3.5s al TTFT de cada mensaje. Para conversación "
            f"casual usar 'grok-4-1-fast-non-reasoning' (mismo precio, "
            f"mismo provider, vision incluida, ~0.6s TTFT)."
        )
