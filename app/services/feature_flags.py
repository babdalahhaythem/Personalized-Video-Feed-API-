"""
Feature flag service implementation.
Controls feature rollout and kill switch.
"""
import hashlib
from typing import Optional

from app.config import get_settings
from app.models.interfaces import FeatureFlagService


class ConfigBasedFeatureFlagService(FeatureFlagService):
    """
    Feature flag service backed by application settings.
    Supports percentage-based rollout using consistent hashing.
    """

    def __init__(self, rollout_percentage: float = 100.0) -> None:
        """
        Initialize feature flag service.

        Args:
            rollout_percentage: Percentage of users to enable (0-100)
        """
        self._rollout_percentage = rollout_percentage

    def is_personalization_enabled(self, tenant_id: str, user_hash: str) -> bool:
        """
        Check if personalization is enabled for this request.

        Uses consistent hashing to ensure the same user always gets
        the same result (important for A/B testing consistency).
        """
        settings = get_settings()

        # Global kill switch takes precedence
        if self.is_kill_switch_active():
            return False

        # Check if personalization is globally enabled
        if not settings.PERSONALIZATION_ENABLED:
            return False

        # Percentage-based rollout
        if self._rollout_percentage < 100.0:
            return self._is_user_in_rollout(user_hash)

        return True

    def is_kill_switch_active(self) -> bool:
        """Check if global kill switch is activated."""
        settings = get_settings()
        return settings.KILL_SWITCH_ACTIVE

    def _is_user_in_rollout(self, user_hash: str) -> bool:
        """
        Determine if user is in the rollout percentage.
        Uses MD5 hash mod 100 for consistent assignment.
        """
        hash_bytes = hashlib.md5(user_hash.encode()).digest()
        hash_value = int.from_bytes(hash_bytes[:4], byteorder="big")
        bucket = hash_value % 100
        return bucket < self._rollout_percentage

    def set_rollout_percentage(self, percentage: float) -> None:
        """Update rollout percentage (for dynamic configuration)."""
        self._rollout_percentage = max(0.0, min(100.0, percentage))
