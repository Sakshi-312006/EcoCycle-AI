"""Centralized custom domain and HTTP exceptions.

Standardized exception classes used across routes, services, and repositories.
"""

from typing import Any, Dict, List, Optional


class AppException(Exception):
    """Base application exception with status code and machine-readable error code."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []


class EntityNotFoundException(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, entity_name: str, identifier: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=[{"entity": entity_name, "identifier": str(identifier)}],
        )


class DatabaseConnectionException(AppException):
    """Raised when the database is unreachable or not configured."""

    def __init__(self, message: str = "Database connection unavailable."):
        super().__init__(
            message=message,
            status_code=503,
            error_code="DATABASE_UNAVAILABLE",
            details=[{"hint": "Check PostgreSQL service status and credentials in .env"}],
        )


class ValidationException(AppException):
    """Raised when input validation fails business rules."""

    def __init__(self, message: str, details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_FAILED",
            details=details or [],
        )


class UnauthorizedException(AppException):
    """Raised when authentication credentials are missing or invalid."""

    def __init__(self, message: str = "Authentication credentials required."):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
        )


class ForbiddenException(AppException):
    """Raised when user lacks permissions for an operation."""

    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )


class ConflictException(AppException):
    """Raised when an operation conflicts with current system state."""

    def __init__(self, message: str, details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="RESOURCE_CONFLICT",
            details=details or [],
        )
