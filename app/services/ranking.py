"""
Ranking engine service.
Core personalization algorithm with filtering, scoring, and sorting.
"""
import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from app.models.schemas import (
    FeedItem,
    ScoredVideo,
    TenantRankingRules,
    UserSignals,
    VideoMetadata,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Scoring Strategy (Strategy Pattern)
# =============================================================================


class ScoringStrategy(ABC):
    """Abstract base class for scoring strategies."""

    @abstractmethod
    def calculate_boost(
        self,
        video: VideoMetadata,
        user: UserSignals,
        config: TenantRankingRules,
    ) -> Tuple[float, str]:
        """
        Calculate a boost value for this strategy.

        Returns:
            Tuple of (boost_value, strategy_name)
        """
        pass


class RecencyScoring(ScoringStrategy):
    """Boost recently published videos."""

    DECAY_HOURS = 48  # Boost decays to 0 over 48 hours

    def calculate_boost(
        self,
        video: VideoMetadata,
        user: UserSignals,
        config: TenantRankingRules,
    ) -> Tuple[float, str]:
        now = time.time()
        age_hours = max(0, (now - video.published_at) / 3600)

        # Linear decay from weight to 0 over DECAY_HOURS
        if age_hours >= self.DECAY_HOURS:
            boost = 0.0
        else:
            decay_factor = 1.0 - (age_hours / self.DECAY_HOURS)
            weight = config.boost_weights.get("recency", 1.0)
            boost = weight * decay_factor

        return boost, "recency"


class AffinityScoring(ScoringStrategy):
    """Boost videos matching user's category affinities."""

    def calculate_boost(
        self,
        video: VideoMetadata,
        user: UserSignals,
        config: TenantRankingRules,
    ) -> Tuple[float, str]:
        # Find max affinity across video tags
        max_affinity = 0.0
        for tag in video.tags:
            affinity = user.affinities.get(tag, 0.0)
            max_affinity = max(max_affinity, affinity)

        weight = config.boost_weights.get("user_affinity", 1.0)
        boost = weight * max_affinity

        return boost, "affinity"


class PopularityScoring(ScoringStrategy):
    """Apply popularity weight to base score."""

    def calculate_boost(
        self,
        video: VideoMetadata,
        user: UserSignals,
        config: TenantRankingRules,
    ) -> Tuple[float, str]:
        # Popularity is applied as a multiplier, not a boost
        # This is handled differently in the engine
        weight = config.boost_weights.get("popularity", 1.0)
        return weight, "popularity"


# =============================================================================
# Ranking Engine
# =============================================================================


class RankingEngine:
    """
    Main ranking engine service.
    Orchestrates filtering, scoring, and sorting of video candidates.
    """

    def __init__(self, scoring_strategies: Optional[List[ScoringStrategy]] = None):
        """
        Initialize ranking engine with scoring strategies.

        Args:
            scoring_strategies: List of strategies to apply (default: all)
        """
        self._strategies = scoring_strategies or [
            RecencyScoring(),
            AffinityScoring(),
        ]
        self._popularity_strategy = PopularityScoring()

    def rank(
        self,
        candidates: List[VideoMetadata],
        user: UserSignals,
        config: TenantRankingRules,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Tuple[List[FeedItem], Optional[str], bool]:
        """
        Rank video candidates for a user.

        Args:
            candidates: Pool of video candidates
            user: User signals for personalization
            config: Tenant-specific ranking rules
            limit: Maximum items to return
            cursor: Pagination cursor

        Returns:
            Tuple of (feed_items, next_cursor, has_more)
        """
        offset = self._decode_cursor(cursor)

        # Step 1: Filter candidates
        filtered = self._filter_candidates(candidates, user, config)

        # Step 2: Score candidates
        scored = self._score_candidates(filtered, user, config)

        # Step 3: Sort by score (descending)
        scored.sort(key=lambda x: x.final_score, reverse=True)

        # Step 4: Apply editorial overrides
        scored = self._apply_editorial_boosts(scored, config)

        # Step 5: Paginate
        page_items = scored[offset : offset + limit]
        has_more = len(scored) > offset + limit

        # Step 6: Transform to FeedItem
        feed_items = self._to_feed_items(page_items)

        # Step 7: Generate next cursor
        next_cursor = None
        if has_more:
            next_cursor = self._encode_cursor(offset + limit)

        logger.debug(
            f"Ranked {len(candidates)} candidates -> {len(filtered)} filtered -> "
            f"returning {len(feed_items)} items"
        )

        return feed_items, next_cursor, has_more

    def _filter_candidates(
        self,
        candidates: List[VideoMetadata],
        user: UserSignals,
        config: TenantRankingRules,
    ) -> List[VideoMetadata]:
        """Apply filters to remove ineligible candidates."""
        watched_ids = set(user.watched_ids)
        exclude_tags = set(config.filters.get("exclude_tags", []))
        max_maturity = config.filters.get("max_maturity")

        filtered = []
        for video in candidates:
            # Filter: Already watched
            if video.id in watched_ids:
                continue

            # Filter: Excluded tags
            if any(tag in exclude_tags for tag in video.tags):
                continue

            # Filter: Maturity rating (simplified)
            if max_maturity and not self._is_maturity_allowed(
                video.maturity_rating, max_maturity
            ):
                continue

            filtered.append(video)

        return filtered

    def _score_candidates(
        self,
        candidates: List[VideoMetadata],
        user: UserSignals,
        config: TenantRankingRules,
    ) -> List[ScoredVideo]:
        """Calculate scores for all candidates."""
        scored = []
        popularity_weight, _ = self._popularity_strategy.calculate_boost(
            candidates[0] if candidates else VideoMetadata(
                id="", title="", score=0, published_at=0
            ),
            user,
            config,
        )

        for video in candidates:
            # Base score (popularity adjusted)
            base_score = video.score * popularity_weight

            # Calculate boosts from strategies
            total_boost = 0.0
            breakdown: Dict[str, float] = {"base": base_score}

            for strategy in self._strategies:
                boost, name = strategy.calculate_boost(video, user, config)
                total_boost += boost
                breakdown[name] = boost

            # Final score: Base * (1 + TotalBoost)
            final_score = base_score * (1.0 + total_boost)
            breakdown["total_boost"] = total_boost
            breakdown["final"] = final_score

            scored.append(
                ScoredVideo(
                    video=video,
                    final_score=final_score,
                    score_breakdown=breakdown,
                )
            )

        return scored

    def _apply_editorial_boosts(
        self,
        scored: List[ScoredVideo],
        config: TenantRankingRules,
    ) -> List[ScoredVideo]:
        """Apply editorial position overrides."""
        if not config.editorial_boosts:
            return scored

        # Extract boosted items and remove from main list
        boosted_items: Dict[int, ScoredVideo] = {}
        remaining = []

        for item in scored:
            if item.video.id in config.editorial_boosts:
                position = config.editorial_boosts[item.video.id]
                boosted_items[position] = item
            else:
                remaining.append(item)

        # Insert boosted items at specified positions
        result = remaining[:]
        for position, item in sorted(boosted_items.items()):
            insert_idx = min(position, len(result))
            result.insert(insert_idx, item)

        return result

    def _to_feed_items(self, scored: List[ScoredVideo]) -> List[FeedItem]:
        """Transform scored videos to feed items."""
        items = []
        for sv in scored:
            item = FeedItem(
                id=sv.video.id,
                title=sv.video.title,
                playback_url=f"https://cdn.example.com/v/{sv.video.id}.m3u8",
                tracking_token=f"tok_{sv.video.id}_{int(time.time())}",
                debug_score=round(sv.final_score, 2),
            )
            items.append(item)
        return items

    def _decode_cursor(self, cursor: Optional[str]) -> int:
        """Decode pagination cursor to offset."""
        if not cursor:
            return 0
        try:
            decoded = base64.b64decode(cursor).decode("utf-8")
            data = json.loads(decoded)
            return data.get("offset", 0)
        except Exception:
            logger.warning(f"Invalid cursor: {cursor}")
            return 0

    def _encode_cursor(self, offset: int) -> str:
        """Encode offset to pagination cursor."""
        data = {"offset": offset}
        return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")

    @staticmethod
    def _is_maturity_allowed(video_rating: str, max_rating: str) -> bool:
        """Check if video rating is within allowed limit."""
        ratings = ["G", "PG", "PG-13", "R", "NC-17"]
        try:
            video_idx = ratings.index(video_rating)
            max_idx = ratings.index(max_rating)
            return video_idx <= max_idx
        except ValueError:
            return True  # Unknown ratings are allowed
