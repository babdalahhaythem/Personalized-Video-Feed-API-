"""
Generic in-memory cache with TTL support.
Thread-safe and suitable for L1 caching.
Can be replaced with Redis adapter for production.
"""
import time
from abc import ABC, abstractmethod
from threading import Lock
from typing import Callable, Dict, Generic, Optional, TypeVar

T = TypeVar("T")


class CacheInterface(ABC, Generic[T]):
    """Abstract interface for cache implementations."""

    @abstractmethod
    def get(self, key: str) -> Optional[T]:
        """Get value by key, returns None if not found or expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Set value with optional TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key, returns True if existed."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries."""
        pass

    @abstractmethod
    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl_seconds: Optional[int] = None,
    ) -> T:
        """Get value or compute and cache it if missing."""
        pass


class CacheEntry(Generic[T]):
    """Single cache entry with expiration tracking."""

    def __init__(self, value: T, expires_at: Optional[float]) -> None:
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class InMemoryCache(CacheInterface[T]):
    """
    Thread-safe in-memory cache with TTL support.

    Usage:
        cache: CacheInterface[UserSignals] = InMemoryCache(default_ttl=300)
        signals = cache.get_or_set("user_123", lambda: fetch_signals("user_123"))
    """

    def __init__(self, default_ttl_seconds: Optional[int] = None) -> None:
        self._store: Dict[str, CacheEntry[T]] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = Lock()

    def get(self, key: str) -> Optional[T]:
        """Get value by key, returns None if not found or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None) -> None:
        """Set value with optional TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expires_at = time.time() + ttl if ttl else None
        with self._lock:
            self._store[key] = CacheEntry(value, expires_at)

    def delete(self, key: str) -> bool:
        """Delete key, returns True if existed."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._store.clear()

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl_seconds: Optional[int] = None,
    ) -> T:
        """Get value or compute and cache it if missing."""
        value = self.get(key)
        if value is not None:
            return value

        # Compute outside lock to avoid blocking
        computed_value = factory()
        self.set(key, computed_value, ttl_seconds)
        return computed_value

    def size(self) -> int:
        """Return number of entries (including possibly expired)."""
        with self._lock:
            return len(self._store)

    def cleanup_expired(self) -> int:
        """Remove expired entries, return count removed."""
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._store.items() if v.is_expired()
            ]
            for key in expired_keys:
                del self._store[key]
                removed += 1
        return removed
