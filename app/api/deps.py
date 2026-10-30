"""Common API dependencies for dependency injection in route endpoints."""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.session import get_db


def get_app_settings() -> Settings:
    """Dependency provider for application settings."""
    return settings


# Re-export get_db for easy route dependency injection
__all__ = ["get_db", "get_app_settings", "Session", "Depends"]
