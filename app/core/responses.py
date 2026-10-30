"""Standard API response and error formatting schemas.

Guarantees a consistent envelope structure for all responses across the platform.
"""

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


def get_current_utc() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class APIResponse(BaseModel, Generic[DataT]):
    """Standard success response wrapper."""

    success: bool = Field(default=True, description="Indicates if the request succeeded")
    message: str = Field(default="Operation completed successfully", description="User-facing summary message")
    data: Optional[DataT] = Field(default=None, description="Response payload")
    timestamp: datetime = Field(default_factory=get_current_utc, description="UTC timestamp of the response")


class ErrorDetail(BaseModel):
    """Detailed error item for debugging and form validation feedback."""

    field: Optional[str] = Field(default=None, description="Field name if validation error")
    message: str = Field(..., description="Specific error description")
    code: Optional[str] = Field(default=None, description="Specific error code or error type")


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    success: bool = Field(default=False, description="Always false for error responses")
    message: str = Field(..., description="High-level error summary")
    error_code: str = Field(default="INTERNAL_ERROR", description="Machine-readable error identifier")
    details: List[Any] = Field(default_factory=list, description="List of granular error details")
    timestamp: datetime = Field(default_factory=get_current_utc, description="UTC timestamp of the error")
