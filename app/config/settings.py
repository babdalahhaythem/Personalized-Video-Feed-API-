"""
Centralized configuration using Pydantic BaseSettings.
All environment variables are loaded here - no hardcoded values.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Personalized Feed API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Feature Flags
    PERSONALIZATION_ENABLED: bool = True
    KILL_SWITCH_ACTIVE: bool = False
    
    # Rollout Configuration
    ROLLOUT_PERCENTAGE: int = 100  # Percentage of users to receive personalized feed
    
    # Cache Configuration
    CANDIDATE_FEED_TTL: int = 30  # Seconds
    
    # Telemetry
    ENABLE_OTEL: bool = False  # Default to False to prevent gRPC errors in dev
    ENABLE_PROMETHEUS: bool = True

    # Timeouts (milliseconds) - Strict budgets per dependency
    RANKING_TIMEOUT_MS: int = 20
    CACHE_TIMEOUT_MS: int = 5
    SIGNAL_STORE_TIMEOUT_MS: int = 10

    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SEC: int = 30

    # Cache TTLs (seconds)
    TENANT_CONFIG_TTL_SEC: int = 300  # 5 minutes
    CANDIDATE_FEED_TTL_SEC: int = 300  # 5 minutes
    FALLBACK_FEED_TTL_SEC: int = 60   # 1 minute

    # Pagination
    DEFAULT_FEED_LIMIT: int = 20
    MAX_FEED_LIMIT: int = 50

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_SEC: int = 2

    # Redis (for production)
    REDIS_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance - singleton pattern."""
    return Settings()
