"""
Feed service - main business logic orchestrator.
Coordinates data fetching, feature flags, circuit breaker, and ranking.
Implements graceful degradation to fallback feed on any failure.
"""
import logging
import time
from typing import Optional, Tuple

from app.config.settings import get_settings
from app.core.circuit_breaker import CircuitBreaker
from app.models.interfaces import (
    CandidateRepository,
    FeatureFlagService,
    TenantConfigRepository,
    UserSignalRepository,
)
from app.models.schemas import (
    FeedItem,
    FeedResponse,
    UserSignals,
)
from app.services.ranking import RankingEngine

logger = logging.getLogger(__name__)


class FeedService:
    """
    Main feed service orchestrating personalization flow.

    Responsibilities:
    - Check feature flags
    - Fetch data from repositories
    - Apply ranking through circuit breaker
    - Handle graceful degradation
    """

    def __init__(
            self,
            user_signal_repo: UserSignalRepository,
            candidate_repo: CandidateRepository,
            tenant_config_repo: TenantConfigRepository,
            feature_flag_service: FeatureFlagService,
            ranking_engine: RankingEngine,
            circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        """
        Initialize feed service with dependencies.

        Args:
            user_signal_repo: Repository for user signals
            candidate_repo: Repository for video candidates
            tenant_config_repo: Repository for tenant configuration
            feature_flag_service: Service for feature flag evaluation
            ranking_engine: Engine for ranking videos
            circuit_breaker: Optional circuit breaker for ranking calls
        """
        self._user_signal_repo = user_signal_repo
        self._candidate_repo = candidate_repo
        self._tenant_config_repo = tenant_config_repo
        self._feature_flags = feature_flag_service
        self._ranking_engine = ranking_engine
        self._circuit_breaker = circuit_breaker or CircuitBreaker(
            name="ranking_service",
            failure_threshold=5,
            recovery_timeout_sec=30,
        )

    async def get_feed(
            self,
            tenant_id: str,
            user_hash: str,
            limit: int = 20,
            cursor: Optional[str] = None,
    ) -> FeedResponse:
        """
        Get personalized feed for a user.

        Args:
            tenant_id: Tenant identifier
            user_hash: Anonymized user identifier
            limit: Maximum items to return
            cursor: Pagination cursor

        Returns:
            FeedResponse with ranked items or fallback
        """
        start_time = time.time()
        settings = get_settings()

        # Step 1: Check feature flags (FAST - in-memory)
        personalization_enabled = self._feature_flags.is_personalization_enabled(
            tenant_id, user_hash
        )

        # Rollout Logic
        user_hash_int = sum(ord(c) for c in user_hash)
        if (user_hash_int % 100) >= settings.ROLLOUT_PERCENTAGE:
            logger.info(f"User {user_hash} excluded from personalization by rollout")
            personalization_enabled = False

        if not personalization_enabled:
            logger.info(f"Personalization disabled for tenant={tenant_id}")
            return await self._get_fallback_feed(tenant_id, limit)

        # Step 2: Fetch data (with graceful degradation)
        try:
            feed_response = await self._get_personalized_feed(
                tenant_id, user_hash, limit, cursor
            )
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Personalized feed served: tenant={tenant_id}, "
                f"user={user_hash[:8]}..., items={len(feed_response.items)}, "
                f"elapsed_ms={elapsed_ms:.2f}"
            )
            return feed_response

        except Exception as e:
            logger.error(
                f"Personalization failed, falling back: tenant={tenant_id}, "
                f"error={str(e)}"
            )
            # Return degraded response check
            return await self._get_fallback_feed(tenant_id, limit, degraded=True)

    async def _get_personalized_feed(
            self,
            tenant_id: str,
            user_hash: str,
            limit: int,
            cursor: Optional[str],
    ) -> FeedResponse:
        """
        Execute full personalization flow.
        Wrapped by circuit breaker for resilience.
        """
        # Fetch data in parallel (in production, use asyncio.gather)
        user_signals = await self._user_signal_repo.get_signals(user_hash)
        candidates = await self._candidate_repo.get_candidates(tenant_id)
        config = await self._tenant_config_repo.get_config(tenant_id)

        # Handle missing data gracefully
        if user_signals is None:
            user_signals = UserSignals(user_hash=user_hash)

        if not candidates:
            logger.warning(f"No candidates for tenant={tenant_id}")
            return await self._get_fallback_feed(tenant_id, limit, degraded=True)

        if config is None:
            config = self._tenant_config_repo.get_default_config(tenant_id)

        # Candidate Bounding
        if len(candidates) > 200:
            candidates = candidates[:200]

        # Execute ranking through circuit breaker
        items, next_cursor, has_more = self._circuit_breaker.call(
            func=lambda: self._ranking_engine.rank(
                candidates=candidates,
                user=user_signals,
                config=config,
                limit=limit,
                cursor=cursor,
            ),
            fallback=lambda: self._get_fallback_items_sync(candidates, limit),
        )

        return FeedResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            is_personalized=True,
            degraded=False,
        )

    async def _get_fallback_feed(
            self,
            tenant_id: str,
            limit: int,
            degraded: bool = False,
    ) -> FeedResponse:
        """
        Get non-personalized fallback feed.
        Used when personalization is disabled or fails.
        """
        fallback_videos = await self._candidate_repo.get_fallback_feed(tenant_id)

        items = [
            FeedItem(
                id=video.id,
                title=video.title,
                playback_url=f"https://cdn.example.com/v/{video.id}.m3u8",
                tracking_token=f"fallback_{video.id}_{int(time.time())}",
                debug_score=video.score,
            )
            for video in fallback_videos[:limit]
        ]

        logger.info(f"Fallback feed served: tenant={tenant_id}, items={len(items)}")

        return FeedResponse(
            items=items,
            next_cursor=None,
            has_more=False,
            is_personalized=False,
            degraded=degraded,
        )

    def _get_fallback_items_sync(
            self,
            candidates: list,
            limit: int,
    ) -> Tuple[list, Optional[str], bool]:
        """
        Synchronous fallback for circuit breaker.
        """
        sorted_candidates = sorted(
            candidates, key=lambda v: v.score, reverse=True
        )[:limit]

        items = [
            FeedItem(
                id=video.id,
                title=video.title,
                playback_url=f"https://cdn.example.com/v/{video.id}.m3u8",
                tracking_token=f"cb_fallback_{video.id}_{int(time.time())}",
                debug_score=video.score,
            )
            for video in sorted_candidates
        ]

        return items, None, False
