"""API routers package."""
from .feed import router as feed_router
from .health import router as health_router

__all__ = ["feed_router", "health_router"]
