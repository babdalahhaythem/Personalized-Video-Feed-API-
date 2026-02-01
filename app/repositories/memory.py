"""
In-memory repository implementations.
Used for prototyping and testing.
Production would replace these with Redis/Postgres implementations.
"""
import time
from typing import Dict, List, Optional

from app.core.cache import CacheInterface, InMemoryCache
from app.models.schemas import TenantRankingRules, UserSignals, VideoMetadata


class InMemoryUserSignalRepository:
    """
    In-memory implementation of UserSignalRepository.
    Simulates Redis/Scylla user signal store.
    """

    def __init__(self, cache: Optional[CacheInterface[UserSignals]] = None) -> None:
        self._cache = cache or InMemoryCache[UserSignals]()
        self._initialize_mock_data()

    def _initialize_mock_data(self) -> None:
        """Load mock user signals for testing."""
        mock_users = [
            UserSignals(
                user_hash="user_sporty",
                watched_ids=["v2"],  # Already watched Tennis
                affinities={"sports": 0.9, "football": 0.8, "strategy": 0.1},
            ),
            UserSignals(
                user_hash="user_newsy",
                watched_ids=["n1"],  # Already watched Election
                affinities={"politics": 0.9, "finance": 0.7},
            ),
            UserSignals(
                user_hash="user_new",
                watched_ids=[],
                affinities={},
            ),
        ]
        for user in mock_users:
            self._cache.set(user.user_hash, user)

    async def get_signals(self, user_hash: str) -> Optional[UserSignals]:
        """Fetch user signals by hash."""
        signals = self._cache.get(user_hash)
        if signals is None:
            # Cold start user - return empty signals
            return UserSignals(user_hash=user_hash)
        return signals

    async def save_signals(self, signals: UserSignals) -> None:
        """Persist user signals."""
        self._cache.set(signals.user_hash, signals)


class InMemoryCandidateRepository:
    """
    In-memory implementation of CandidateRepository.
    Simulates Redis L2 cache for video candidates.
    """

    def __init__(
        self,
        cache: Optional[CacheInterface[List[VideoMetadata]]] = None,
    ) -> None:
        self._cache = cache or InMemoryCache[List[VideoMetadata]]()
        self._fallback_cache: Dict[str, List[VideoMetadata]] = {}
        self._initialize_mock_data()

    def _initialize_mock_data(self) -> None:
        """Load mock video candidates for testing."""
        now = int(time.time())
        hour = 3600

        sports_videos = [
            VideoMetadata(
                id="v1",
                title="Amazing Goal Messi",
                score=95,
                tags=["sports", "football", "viral"],
                published_at=now - (2 * hour),
            ),
            VideoMetadata(
                id="v2",
                title="Tennis Highlights",
                score=80,
                tags=["sports", "tennis"],
                published_at=now - (24 * hour),
            ),
            VideoMetadata(
                id="v3",
                title="Chess Championship",
                score=60,
                tags=["strategy", "board_games"],
                published_at=now - (48 * hour),
            ),
            VideoMetadata(
                id="v4",
                title="Funny Cat Fails",
                score=85,
                tags=["viral", "animals"],
                published_at=now - (12 * hour),
            ),
            VideoMetadata(
                id="v5",
                title="Live: Stadium Construction",
                score=40,
                tags=["news", "construction"],
                published_at=now - (1 * hour),
            ),
        ]

        news_videos = [
            VideoMetadata(
                id="n1",
                title="Election Results",
                score=99,
                tags=["politics", "news"],
                published_at=now - (1 * hour),
            ),
            VideoMetadata(
                id="n2",
                title="Weather Forecast",
                score=70,
                tags=["news", "weather"],
                published_at=now - (4 * hour),
            ),
            VideoMetadata(
                id="n3",
                title="Tech Stock Crash",
                score=88,
                tags=["finance", "tech"],
                published_at=now - (10 * hour),
            ),
            VideoMetadata(
                id="n4",
                title="Cute Panda Born",
                score=92,
                tags=["animals", "positive"],
                published_at=now - (72 * hour),
            ),
        ]

        self._cache.set("tenant_sports", sports_videos)
        self._cache.set("tenant_news", news_videos)

        # Pre-compute fallback (sorted by popularity)
        self._fallback_cache["tenant_sports"] = sorted(
            sports_videos, key=lambda v: v.score, reverse=True
        )[:3]
        self._fallback_cache["tenant_news"] = sorted(
            news_videos, key=lambda v: v.score, reverse=True
        )[:3]

    async def get_candidates(self, tenant_id: str) -> List[VideoMetadata]:
        """Fetch all active video candidates for a tenant."""
        candidates = self._cache.get(tenant_id)
        return candidates if candidates else []

    async def get_fallback_feed(self, tenant_id: str) -> List[VideoMetadata]:
        """Fetch pre-computed fallback feed (trending videos)."""
        return self._fallback_cache.get(tenant_id, [])


class InMemoryTenantConfigRepository:
    """
    In-memory implementation of TenantConfigRepository.
    Simulates L1 cache for tenant configuration.
    """

    def __init__(
        self,
        cache: Optional[CacheInterface[TenantRankingRules]] = None,
    ) -> None:
        self._cache = cache or InMemoryCache[TenantRankingRules]()
        self._initialize_mock_data()

    def _initialize_mock_data(self) -> None:
        """Load mock tenant configurations for testing."""
        configs = [
            TenantRankingRules(
                tenant_id="tenant_sports",
                boost_weights={
                    "recency": 1.5,
                    "popularity": 0.5,
                    "user_affinity": 2.0,
                },
                filters={"exclude_tags": ["politics"]},
            ),
            TenantRankingRules(
                tenant_id="tenant_news",
                boost_weights={
                    "recency": 2.0,
                    "popularity": 1.0,
                    "user_affinity": 0.5,
                },
                filters={"max_maturity": "PG"},
            ),
        ]
        for config in configs:
            self._cache.set(config.tenant_id, config)

    async def get_config(self, tenant_id: str) -> Optional[TenantRankingRules]:
        """Fetch tenant ranking configuration."""
        return self._cache.get(tenant_id)

    def get_default_config(self, tenant_id: str) -> TenantRankingRules:
        """Get default configuration for unknown tenants."""
        return TenantRankingRules(tenant_id=tenant_id)
