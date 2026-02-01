"""Models package - domain entities and interfaces."""
from .interfaces import (
    CandidateRepository,
    FeatureFlagService,
    TenantConfigRepository,
    UserSignalRepository,
)
from .schemas import (
    ErrorResponse,
    FeedItem,
    FeedRequest,
    FeedResponse,
    ScoredVideo,
    TenantRankingRules,
    UserSignals,
    VideoMetadata,
)

__all__ = [
    # Interfaces
    "CandidateRepository",
    "FeatureFlagService",
    "TenantConfigRepository",
    "UserSignalRepository",
    # Schemas
    "ErrorResponse",
    "FeedItem",
    "FeedRequest",
    "FeedResponse",
    "ScoredVideo",
    "TenantRankingRules",
    "UserSignals",
    "VideoMetadata",
]
