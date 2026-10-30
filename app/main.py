"""EcoCycle AI Backend Application Entrypoint.

Modular FastAPI application factory configuring middleware, exception handlers,
structured logging, database connection lifespans, and OpenAPI documentation.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.endpoints.health import router as health_root_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exception_handlers import (
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.responses import APIResponse
from app.db.session import check_db_connection, get_engine, init_db

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    # 1. Startup phase
    setup_logging()
    logger.info("=" * 60)
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION})")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")
    logger.info(f"CORS Allowed Origins: {settings.CORS_ORIGINS}")

    # Check database status gracefully (non-fatal if disconnected/unconfigured)
    db_status = check_db_connection()
    if db_status["connected"]:
        postgis_info = f" (PostGIS {db_status['postgis_version']})" if db_status["postgis_installed"] else ""
        logger.info(f"Database: Connected to '{db_status['database_name']}' in {db_status['latency_ms']}ms{postgis_info}")
        init_db()
    else:
        logger.warning(
            f"Database: Offline / {db_status['status']}. "
            f"Details: {db_status['message']}. Application will operate in degraded mode."
        )

    logger.info("Application initialization complete. Ready for requests.")
    logger.info("=" * 60)

    yield

    # 2. Shutdown phase
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    engine = get_engine()
    if engine is not None:
        try:
            engine.dispose()
            logger.info("Database connection pool disposed.")
        except Exception as e:
            logger.warning(f"Error disposing database pool: {e}")
    logger.info("Shutdown complete.")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} API",
        version=settings.VERSION,
        description="""
# EcoCycle AI Backend API

Large-scale waste intelligence, reverse logistics, and circular recovery platform backend.

### Architecture Pillars:
1. **Pillar 1:** Four-stream waste segregation and doorstep collection with household EcoPass.
2. **Pillar 2:** Construction & Demolition (C&D) waste volume estimation and recycling pipeline.
3. **Pillar 3:** Circular recovery, material reuse, donation matching, and marketplace listings.
4. **Pillar 4:** Multi-compartment fleet routing with EcoProof integrity receipts.
5. **Pillar 5:** Voice accessibility (MeitY Bhashini), municipal ward operations, and compliance.

### Integration Notice:
This backend exposes RESTful endpoints designed for integration with the mobile Flutter application
and municipal command consoles.
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Centralized Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # 3. Mount Route Endpoints
    # Ensure upload directory exists and mount static file serving
    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
    app.mount("/static/uploads", StaticFiles(directory=settings.STORAGE_LOCAL_PATH), name="uploads")

    # Root diagnostic endpoint directly at /health
    app.include_router(health_root_router)

    # Versioned API routes under /api/v1
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    # Root endpoint for basic discovery
    @app.get("/", tags=["System Root"], summary="API Root Overview")
    async def root_index() -> APIResponse[dict]:
        return APIResponse[dict](
            success=True,
            message=f"Welcome to {settings.PROJECT_NAME} API",
            data={
                "project": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "docs_url": "/docs",
                "redoc_url": "/redoc",
                "health_url": "/health",
                "api_v1_url": f"{settings.API_V1_STR}/health",
            },
        )

    return app


# Application entrypoint instance
app = create_application()
