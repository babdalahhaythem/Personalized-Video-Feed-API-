"""
Structured logging configuration.
Outputs logs in JSON format for production observability.
"""
import json
import logging
import sys
from typing import Any, Dict

from pydantic import BaseModel


class LogRecord(BaseModel):
    """Structured log record schema."""
    timestamp: str
    level: str
    logger: str
    message: str
    context: Dict[str, Any]


class JsonFormatter(logging.Formatter):
    """Format log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the record as JSON."""
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add request context if present (e.g. from middleware)
        if hasattr(record, "request_id"):
            log_obj["request_id"] = getattr(record, "request_id")
        if hasattr(record, "tenant_id"):
            log_obj["tenant_id"] = getattr(record, "tenant_id")

        return json.dumps(log_obj)


def configure_logging(debug: bool = False) -> None:
    """Configure root logger with JSON formatter."""
    handler = logging.StreamHandler(sys.stdout)
    
    if debug:
        # Human-readable format for debugging
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    else:
        # JSON format for production
        formatter = JsonFormatter()

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").handlers = [handler]  # Use our handler
