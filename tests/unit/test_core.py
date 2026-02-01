
import logging
import time
import pytest
from unittest.mock import MagicMock, patch

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.core.telemetry import setup_telemetry
from fastapi import FastAPI


class TestCircuitBreaker:
    def test_initial_state(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        assert cb.state == CircuitState.CLOSED
        assert cb.name == "test"

    def test_successful_call(self):
        cb = CircuitBreaker("test")
        mock_func = MagicMock(return_value="success")

        result = cb.call(mock_func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        mock_func.assert_called_once()

    def test_call_opens_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        mock_func = MagicMock(side_effect=Exception("Error"))

        # 1st failure
        with pytest.raises(Exception):
            cb.call(mock_func)
        assert cb.state == CircuitState.CLOSED

        # 2nd failure -> Open
        with pytest.raises(Exception):
            cb.call(mock_func)
        assert cb._failure_count == 2
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_raises_error_no_fallback(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        # Open it
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception))
        except:
            pass

        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not run")

    def test_fallback_usage(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout_sec=1)
        mock_func = MagicMock(side_effect=Exception("Error"))
        mock_fallback = MagicMock(return_value="fallback")

        # 1. Error with fallback provided -> returns fallback, circuit tracks failure
        res = cb.call(mock_func, fallback=mock_fallback)
        assert res == "fallback"
        assert cb._failure_count == 1
        assert cb.state == CircuitState.OPEN

        # 2. Circuit is OPEN. Call with fallback -> returns fallback immediately
        res2 = cb.call(lambda: "success", fallback=mock_fallback)
        assert res2 == "fallback"

    def test_recovery_half_open(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout_sec=0.1)
        # Open it
        try:
             cb.call(lambda: (_ for _ in ()).throw(Exception))
        except:
            pass

        time.sleep(0.15) # Wait for timeout

        # Should attempt reset (HALF_OPEN)
        # Make a successful call
        res = cb.call(lambda: "recovered")
        assert res == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_manual_reset(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        try:
             cb.call(lambda: (_ for _ in ()).throw(Exception))
        except:
            pass
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED


class TestTelemetry:
    @patch("app.core.telemetry.get_settings")
    @patch("app.core.telemetry.Instrumentator")
    def test_setup_telemetry_prometheus_enabled(self, mock_instrumentator, mock_get_settings):
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.ENABLE_PROMETHEUS = True
        mock_settings.ENABLE_OTEL = False
        mock_get_settings.return_value = mock_settings

        app = FastAPI()
        setup_telemetry(app)

        mock_instrumentator.assert_called_once()
        mock_instrumentator.return_value.instrument.assert_called_once_with(app)

    @patch("app.core.telemetry.get_settings")
    @patch("app.core.telemetry.BatchSpanProcessor")
    @patch("app.core.telemetry.FastAPIInstrumentor")
    def test_setup_telemetry_otel_enabled(self, mock_fastapi_instr, mock_processor, mock_get_settings):
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.ENABLE_PROMETHEUS = False
        mock_settings.ENABLE_OTEL = True
        mock_settings.APP_NAME = "test"
        mock_settings.APP_VERSION = "1.0"
        mock_settings.DEBUG = False
        mock_get_settings.return_value = mock_settings

        app = FastAPI()
        setup_telemetry(app)

        mock_fastapi_instr.instrument_app.assert_called_once()
        mock_processor.assert_called_once()


from app.core.cache import InMemoryCache

class TestInMemoryCache:
    def test_get_set(self):
        cache = InMemoryCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"
        assert cache.get("missing") is None

    def test_expiration(self):
        cache = InMemoryCache(default_ttl_seconds=0.1)
        cache.set("key", "value")
        assert cache.get("key") == "value"

        time.sleep(0.15)
        # Should expire
        assert cache.get("key") is None
        # Should be removed from store
        assert cache.size() == 0

    def test_explicit_ttl(self):
        cache = InMemoryCache()
        cache.set("short", "val", ttl_seconds=0.1)
        cache.set("long", "val", ttl_seconds=10)

        time.sleep(0.15)
        assert cache.get("short") is None
        assert cache.get("long") == "val"

    def test_delete_clear(self):
        cache = InMemoryCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")

        assert cache.delete("k1") is True
        assert cache.get("k1") is None
        assert cache.delete("missing") is False

        cache.clear()
        assert cache.size() == 0
        assert cache.get("k2") is None

    def test_get_or_set(self):
        cache = InMemoryCache()

        # 1. Miss -> factory
        factory = MagicMock(return_value="computed")
        val = cache.get_or_set("key", factory)
        assert val == "computed"
        factory.assert_called_once()

        # 2. Hit -> no factory
        val2 = cache.get_or_set("key", factory)
        assert val2 == "computed"
        factory.assert_called_once() # count stays 1

    def test_cleanup_expired(self):
        cache = InMemoryCache()
        cache.set("k1", "v1", ttl_seconds=0.01)
        cache.set("k2", "v2", ttl_seconds=10)

        time.sleep(0.05)

        # k1 expired but might still be in dict structure until accessed or cleaned
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("k1") is None
        assert cache.get("k2") == "v2"

