"""
Domain models using Pydantic.
All data structures for the personalization system.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Domain Models (Internal)
# =============================================================================


class UserSignals(BaseModel):
    """
    User's historical interaction data.
    Fetched from SignalStore (Redis in production).
    """

    user_hash: str = Field(..., description="Anonymized user identifier")
    watched_ids: List[str] = Field(
        default_factory=list,
        description="Video IDs the user has watched",
    )
    affinities: Dict[str, float] = Field(
        default_factory=dict,
        description="Category affinity scores (0.0-1.0)",
    )
    last_demographics: Dict[str, str] = Field(
        default_factory=dict,
        description="Demographic hints from SDK",
    )

    @property
    def is_cold_start(self) -> bool:
        """Check if user has no history (cold start)."""
        return len(self.watched_ids) == 0 and len(self.affinities) == 0


class VideoMetadata(BaseModel):
    """
    Video candidate with metadata for ranking.
    Fetched from CandidateCache (Redis in production).
    """

    id: str = Field(..., description="Unique video identifier")
    title: str = Field(..., description="Video title")
    score: float = Field(..., ge=0, le=100, description="Base popularity score")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    maturity_rating: str = Field(default="G", description="Content rating")
    published_at: int = Field(..., description="Unix timestamp of publication")


class TenantRankingRules(BaseModel):
    """
    Tenant-specific personalization configuration.
    Loaded from TenantConfigCache (in-memory L1).
    """

    tenant_id: str = Field(..., description="Tenant identifier")
    boost_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "recency": 1.0,
            "popularity": 1.0,
            "user_affinity": 1.0,
        },
        description="Weight multipliers for ranking factors",
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Content filters (e.g., max_maturity, exclude_tags)",
    )
    editorial_boosts: Dict[str, int] = Field(
        default_factory=dict,
        description="Video ID -> fixed position (editorial override)",
    )


class ScoredVideo(BaseModel):
    """Internal model for ranked video with computed score."""

    video: VideoMetadata
    final_score: float
    score_breakdown: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# API Models (External)
# =============================================================================


class FeedRequest(BaseModel):
    """Request parameters for feed endpoint."""

    limit: int = Field(default=20, ge=1, le=50, description="Number of items")
    cursor: Optional[str] = Field(default=None, description="Pagination cursor")


class FeedItem(BaseModel):
    """Single item in feed response."""

    id: str = Field(..., description="Video ID")
    title: str = Field(..., description="Video title")
    playback_url: str = Field(..., description="Streaming URL")
    tracking_token: str = Field(..., description="Analytics token")
    debug_score: Optional[float] = Field(
        default=None,
        description="Computed score (debug only)",
    )


class FeedResponse(BaseModel):
    """Feed endpoint response."""

    items: List[FeedItem] = Field(..., description="Ranked video items")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor for next page",
    )
    has_more: bool = Field(..., description="More items available")
    degraded: bool = Field(
        default=False,
        description="True if fallback feed was returned due to error/latency",
    )
    is_personalized: bool = Field(
        default=True,
        description="Whether personalization was applied",
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: Dict[str, Any] = Field(..., description="Error details")
