"""
Unit tests for RankingEngine service.
"""
from app.models.schemas import (
    VideoMetadata,
)
from app.services.ranking import RankingEngine


class TestRankingEngine:
    def test_ranking_flow_happy_path(
            self, sample_video, sample_user_signals, sample_config
    ):
        """Test standard ranking flow with one candidate."""
        engine = RankingEngine()

        # Setup candidate
        candidates = [sample_video]

        # Execute rank
        items, next_cursor, has_more = engine.rank(
            candidates=candidates,
            user=sample_user_signals,
            config=sample_config,
            limit=10,
        )

        assert len(items) == 1
        assert items[0].id == sample_video.id
        # Score check: Base(80) * Popularity(1.0) * (1 + Recency + Affinity)
        # Recency should be close to 1.0 (fresh)
        # Affinity should be 1.0 (matches 'sports')
        # Approx: 80 * (1 + 1 + 1) = 240
        assert items[0].debug_score > 80.0
        assert not has_more
        assert next_cursor is None

    def test_filtering_watched_videos(
            self, sample_video, sample_user_signals, sample_config
    ):
        """Test that watched videos are excluded."""
        engine = RankingEngine()

        # User has watched this video
        sample_user_signals.watched_ids = [sample_video.id]

        items, _, _ = engine.rank(
            candidates=[sample_video],
            user=sample_user_signals,
            config=sample_config,
        )

        assert len(items) == 0

    def test_filtering_maturity(
            self, sample_video, sample_user_signals, sample_config
    ):
        """Test maturity rating filter."""
        engine = RankingEngine()

        # Video is R rated
        sample_video.maturity_rating = "R"

        # Config allows max PG-13
        sample_config.filters["max_maturity"] = "PG-13"

        items, _, _ = engine.rank(
            candidates=[sample_video],
            user=sample_user_signals,
            config=sample_config,
        )

        assert len(items) == 0

        # Relax config
        sample_config.filters["max_maturity"] = "R"
        items_ok, _, _ = engine.rank(
            candidates=[sample_video],
            user=sample_user_signals,
            config=sample_config,
        )
        assert len(items_ok) == 1

    def test_pagination(
            self, sample_user_signals, sample_config
    ):
        """Test cursor-based pagination."""
        engine = RankingEngine()

        # Create 10 videos
        candidates = [
            VideoMetadata(
                id=f"v{i}",
                title=f"Video {i}",
                score=100 - i,  # Descending score
                published_at=1700000000,
            )
            for i in range(10)
        ]

        # Request page 1 (limit=3)
        p1_items, p1_cursor, p1_more = engine.rank(
            candidates=candidates,
            user=sample_user_signals,
            config=sample_config,
            limit=3,
        )

        assert len(p1_items) == 3
        assert p1_items[0].id == "v0"
        assert p1_more is True
        assert p1_cursor is not None

        # Request page 2 using cursor
        p2_items, p2_cursor, p2_more = engine.rank(
            candidates=candidates,
            user=sample_user_signals,
            config=sample_config,
            limit=3,
            cursor=p1_cursor,
        )

        assert len(p2_items) == 3
        assert p2_items[0].id == "v3"  # 0,1,2 were page 1
        assert p2_more is True
