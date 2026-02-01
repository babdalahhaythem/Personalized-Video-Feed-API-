"""
Health check router for observability.
"""
from fastapi import APIRouter

from app.api.dependencies import get_ranking_circuit_breaker
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health Check")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/health/ready", summary="Readiness Check")
async def readiness_check() -> dict:
    """
    Readiness check for Kubernetes.
    Returns status of circuit breakers and dependencies.
    """
    circuit_breaker = get_ranking_circuit_breaker()
    settings = get_settings()

    return {
        "status": "ready",
        "circuit_breaker": {
            "name": circuit_breaker.name,
            "state": circuit_breaker.state.value,
        },
        "feature_flags": {
            "personalization_enabled": settings.PERSONALIZATION_ENABLED,
            "kill_switch_active": settings.KILL_SWITCH_ACTIVE,
        },
    }
