"""
Dependency injection container.
Creates and wires all application components.
Uses FastAPI's dependency injection system.
"""
from functools import lru_cache
from typing import Generator

from app.config import Settings, get_settings
from app.core.cache import InMemoryCache
from app.core.circuit_breaker import CircuitBreaker
from app.repositories.memory import (
    InMemoryCandidateRepository,
    InMemoryTenantConfigRepository,
    InMemoryUserSignalRepository,
)
from app.services.feature_flags import ConfigBasedFeatureFlagService
from app.services.feed import FeedService
from app.services.ranking import RankingEngine


# =============================================================================
# Singleton Instances (Application Lifetime)
# =============================================================================


@lru_cache()
def get_user_signal_repository() -> InMemoryUserSignalRepository:
    """Get singleton user signal repository."""
    return InMemoryUserSignalRepository()


@lru_cache()
def get_candidate_repository() -> InMemoryCandidateRepository:
    """Get singleton candidate repository."""
    return InMemoryCandidateRepository()


@lru_cache()
def get_tenant_config_repository() -> InMemoryTenantConfigRepository:
    """Get singleton tenant config repository."""
    return InMemoryTenantConfigRepository()


@lru_cache()
def get_feature_flag_service() -> ConfigBasedFeatureFlagService:
    """Get singleton feature flag service."""
    return ConfigBasedFeatureFlagService(rollout_percentage=100.0)


@lru_cache()
def get_ranking_engine() -> RankingEngine:
    """Get singleton ranking engine."""
    return RankingEngine()


@lru_cache()
def get_ranking_circuit_breaker() -> CircuitBreaker:
    """Get singleton circuit breaker for ranking service."""
    settings = get_settings()
    return CircuitBreaker(
        name="ranking_service",
        failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout_sec=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SEC,
    )


# =============================================================================
# Request-Scoped Dependencies (Per-Request Lifetime)
# =============================================================================


def get_feed_service() -> FeedService:
    """
    Get feed service with all dependencies wired.
    This is the main entry point for the feed endpoint.
    """
    return FeedService(
        user_signal_repo=get_user_signal_repository(),
        candidate_repo=get_candidate_repository(),
        tenant_config_repo=get_tenant_config_repository(),
        feature_flag_service=get_feature_flag_service(),
        ranking_engine=get_ranking_engine(),
        circuit_breaker=get_ranking_circuit_breaker(),
    )


# =============================================================================
# Cleanup Functions
# =============================================================================


def clear_caches() -> None:
    """Clear all cached singleton instances (for testing)."""
    get_user_signal_repository.cache_clear()
    get_candidate_repository.cache_clear()
    get_tenant_config_repository.cache_clear()
    get_feature_flag_service.cache_clear()
    get_ranking_engine.cache_clear()
    get_ranking_circuit_breaker.cache_clear()
