"""
Circuit Breaker pattern implementation for resilience.
Prevents cascading failures by stopping calls to failing services.
"""
import time
from enum import Enum
from threading import Lock
from typing import Callable, TypeVar, Optional
import logging

from app.core.exceptions import CircuitBreakerOpenError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.

    Usage:
        breaker = CircuitBreaker("ranking_service", failure_threshold=5)
        result = breaker.call(lambda: ranking_service.rank(videos))
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_sec: int = 30,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout_sec = recovery_timeout_sec

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def name(self) -> str:
        """Circuit breaker name."""
        return self._name

    def call(self, func: Callable[[], T], fallback: Optional[Callable[[], T]] = None) -> T:
        """
        Execute function through circuit breaker.

        Args:
            func: The function to execute
            fallback: Optional fallback if circuit is open

        Returns:
            Result from func or fallback

        Raises:
            CircuitBreakerOpenError: If open and no fallback provided
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker '{self._name}' entering HALF_OPEN")
                else:
                    if fallback:
                        logger.warning(f"Circuit breaker '{self._name}' OPEN, using fallback")
                        return fallback()
                    raise CircuitBreakerOpenError(self._name)

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                logger.warning(f"Circuit breaker '{self._name}' caught error, using fallback: {e}")
                return fallback()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(f"Circuit breaker '{self._name}' recovered to CLOSED")

    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker '{self._name}' OPENED after "
                    f"{self._failure_count} failures"
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self._recovery_timeout_sec

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit breaker '{self._name}' manually reset")
