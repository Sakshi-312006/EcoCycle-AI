"""Structured logging configuration for EcoCycle AI.

Provides consistent log formatting across modules and services.
"""

import logging
import sys
from app.core.config import settings


class ColouredFormatter(logging.Formatter):
    """Clean formatter with ISO-style timestamps and log levels."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{record.levelname:<7}] [{record.name}]: {record.getMessage()}"
        if record.exc_info:
            log_msg += f"\n{self.formatException(record.exc_info)}"
        return log_msg


def setup_logging() -> None:
    """Initialize structured application logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate lines
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(ColouredFormatter())
    root_logger.addHandler(handler)

    # Tone down excessively noisy external libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retrieve a configured logger instance with the given module name."""
    return logging.getLogger(name)
