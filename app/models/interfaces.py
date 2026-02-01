"""
Repository interfaces (abstractions).
Using Protocol for structural subtyping (duck typing with type hints).
These define the contracts that data access implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Protocol, runtime_checkable

from app.models.schemas import TenantRankingRules, UserSignals, VideoMetadata


@runtime_checkable
class UserSignalRepository(Protocol):
    """
    Interface for user signal data access.
    Production: Redis/Scylla implementation.
    Testing: In-memory mock implementation.
    """

    async def get_signals(self, user_hash: str) -> Optional[UserSignals]:
        """
        Fetch user signals by hash.

        Args:
            user_hash: Anonymized user identifier

        Returns:
            UserSignals if found, None for cold-start users
        """
        ...

    async def save_signals(self, signals: UserSignals) -> None:
        """
        Persist user signals.

        Args:
            signals: User signal data to save
        """
        ...


@runtime_checkable
class CandidateRepository(Protocol):
    """
    Interface for video candidate data access.
    Production: Redis L2 cache backed by Postgres.
    Testing: In-memory mock implementation.
    """

    async def get_candidates(self, tenant_id: str) -> List[VideoMetadata]:
        """
        Fetch all active video candidates for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of video candidates (may be empty)
        """
        ...

    async def get_fallback_feed(self, tenant_id: str) -> List[VideoMetadata]:
        """
        Fetch pre-computed fallback feed (trending videos).
        Used when personalization is disabled or fails.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of trending videos (fallback)
        """
        ...


@runtime_checkable
class TenantConfigRepository(Protocol):
    """
    Interface for tenant configuration access.
    Production: In-memory L1 cache with CMS sync.
    Testing: In-memory mock implementation.
    """

    async def get_config(self, tenant_id: str) -> Optional[TenantRankingRules]:
        """
        Fetch tenant ranking configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            TenantRankingRules if configured, None for default
        """
        ...

    def get_default_config(self, tenant_id: str) -> TenantRankingRules:
        """
        Get default configuration for unknown tenants.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Default TenantRankingRules
        """
        ...


class FeatureFlagService(ABC):
    """
    Abstract base class for feature flag evaluation.
    Supports kill switch and gradual rollout.
    """

    @abstractmethod
    def is_personalization_enabled(self, tenant_id: str, user_hash: str) -> bool:
        """
        Check if personalization is enabled for this request.

        Args:
            tenant_id: Tenant identifier
            user_hash: User identifier for percentage rollout

        Returns:
            True if personalization should be applied
        """
        pass

    @abstractmethod
    def is_kill_switch_active(self) -> bool:
        """
        Check if global kill switch is activated.

        Returns:
            True if all personalization should be disabled
        """
        pass
