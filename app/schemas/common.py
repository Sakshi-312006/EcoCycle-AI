"""Common reusable Pydantic schemas across all API endpoints."""

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


def get_current_utc() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class APIResponse(BaseModel, Generic[DataT]):
    """Standard success response wrapper envelope."""

    success: bool = Field(default=True, description="Indicates whether the request succeeded")
    message: str = Field(default="Success", description="Human-readable message")
    data: Optional[DataT] = Field(default=None, description="Actual data payload")
    timestamp: datetime = Field(default_factory=get_current_utc, description="UTC timestamp of response")


class ErrorResponse(BaseModel):
    """Standard error response wrapper envelope."""

    success: bool = Field(default=False, description="Always false for error responses")
    message: str = Field(..., description="High-level error summary")
    error_code: str = Field(..., description="Machine-readable error identifier")
    details: List[Any] = Field(default_factory=list, description="Granular error items")
    timestamp: datetime = Field(default_factory=get_current_utc, description="UTC timestamp of error")


class PaginationParams(BaseModel):
    """Common pagination query parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number starting at 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
