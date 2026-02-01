"""
Custom exception hierarchy for centralized error handling.
All exceptions map to appropriate HTTP status codes.
"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to API response format."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(AppException):
    """Invalid input data."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} not found: {identifier}",
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class RateLimitError(AppException):
    """Too many requests."""

    def __init__(self, retry_after: int = 1) -> None:
        super().__init__(
            message="Too many requests. Please slow down.",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after},
        )


class ServiceUnavailableError(AppException):
    """Dependency service is unavailable."""

    def __init__(self, service_name: str) -> None:
        super().__init__(
            message=f"Service temporarily unavailable: {service_name}",
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service_name},
        )


class RankingServiceError(AppException):
    """Ranking engine failed."""

    def __init__(self, reason: str = "Unknown error") -> None:
        super().__init__(
            message=f"Ranking service error: {reason}",
            status_code=500,
            error_code="RANKING_ERROR",
            details={"reason": reason},
        )


class CacheError(AppException):
    """Cache operation failed."""

    def __init__(self, operation: str, reason: str = "Unknown") -> None:
        super().__init__(
            message=f"Cache {operation} failed: {reason}",
            status_code=500,
            error_code="CACHE_ERROR",
            details={"operation": operation, "reason": reason},
        )


class CircuitBreakerOpenError(AppException):
    """Circuit breaker is open - service calls blocked."""

    def __init__(self, service_name: str) -> None:
        super().__init__(
            message=f"Circuit breaker open for: {service_name}",
            status_code=503,
            error_code="CIRCUIT_BREAKER_OPEN",
            details={"service": service_name},
        )
