"""Global exception handlers for FastAPI.

Translates domain exceptions, validation errors, and unhandled errors into
standardized API error responses.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.core.responses import ErrorResponse, get_current_utc

logger = get_logger("app.exception_handlers")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"Domain exception on {request.method} {request.url.path}: "
        f"[{exc.error_code}] {exc.message}"
    )
    error_payload = ErrorResponse(
        success=False,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        timestamp=get_current_utc(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(mode="json"),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI/Pydantic request validation errors (HTTP 422)."""
    details = []
    for err in exc.errors():
        field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
        details.append({
            "field": field_path,
            "message": err.get("msg", "Invalid value"),
            "code": err.get("type", "value_error"),
        })

    logger.info(f"Validation error on {request.method} {request.url.path}: {details}")

    error_payload = ErrorResponse(
        success=False,
        message="Request validation failed. Please check the submitted fields.",
        error_code="VALIDATION_ERROR",
        details=details,
        timestamp=get_current_utc(),
    )
    return JSONResponse(
        status_code=422,
        content=error_payload.model_dump(mode="json"),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard Starlette / FastAPI HTTPExceptions (404, 405, etc.)."""
    error_code = "HTTP_ERROR"
    if exc.status_code == 404:
        error_code = "ENDPOINT_NOT_FOUND"
    elif exc.status_code == 405:
        error_code = "METHOD_NOT_ALLOWED"

    error_payload = ErrorResponse(
        success=False,
        message=str(exc.detail),
        error_code=error_code,
        details=[{"path": request.url.path, "method": request.method}],
        timestamp=get_current_utc(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(mode="json"),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled server exceptions (HTTP 500)."""
    logger.exception(
        f"Unhandled server error while processing {request.method} {request.url.path}: {str(exc)}"
    )

    error_payload = ErrorResponse(
        success=False,
        message="An unexpected internal server error occurred. Please contact system support.",
        error_code="INTERNAL_SERVER_ERROR",
        details=[],
        timestamp=get_current_utc(),
    )
    return JSONResponse(
        status_code=500,
        content=error_payload.model_dump(mode="json"),
    )
