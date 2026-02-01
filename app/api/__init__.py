"""API package - FastAPI routes and dependencies."""
from .dependencies import get_feed_service
from .routers import feed_router, health_router

__all__ = ["feed_router", "get_feed_service", "health_router"]
