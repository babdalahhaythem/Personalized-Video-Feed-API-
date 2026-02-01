"""
Main FastAPI application entry point.
Configures logging, exception handlers, middleware, and routers.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import feed_router, health_router
from app.config import get_settings
from app.config.logging import configure_logging
from app.core.exceptions import AppException
from app.core.telemetry import setup_telemetry


# =============================================================================
# Lifespan (Startup/Shutdown)
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger = logging.getLogger(__name__)
    settings = get_settings()

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Personalization enabled: {settings.PERSONALIZATION_ENABLED}")
    logger.info(f"Kill switch active: {settings.KILL_SWITCH_ACTIVE}")

    yield

    # Shutdown
    logger.info("Shutting down application")


# =============================================================================
# Exception Handlers
# =============================================================================


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions - return generic error."""
    logger = logging.getLogger(__name__)
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            }
        },
    )


# =============================================================================
# Application Factory
# =============================================================================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Configure structured logging
    configure_logging(debug=settings.DEBUG)

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
        Personalized Video Feed API

        A rule-based ranking engine for delivering personalized video feeds.

        ## Features
        - Weighted ranking based on recency, popularity, and user affinity
        - Tenant-specific configuration
        - Feature flags with kill switch
        - Graceful degradation to fallback feed
        - Circuit breaker for resilience
        - Observability: Jason logs, Prometheus, OpenTelemetry
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Register exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Include routers
    app.include_router(health_router)
    app.include_router(feed_router)
    
    # Setup Telemetry (Metrics & Tracing)
    setup_telemetry(app)

    return app


# Create application instance
app = create_app()


# =============================================================================
# Development Entry Point
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
