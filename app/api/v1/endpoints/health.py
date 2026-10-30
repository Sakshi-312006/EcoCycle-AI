"""Health and diagnostic endpoints for application vitality and database state."""

from fastapi import APIRouter, status
from app.schemas.common import APIResponse
from app.schemas.health import (
    DatabaseHealthData,
    HealthSummaryData,
    LivenessData,
    ReadinessData,
)
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get(
    "",
    response_model=APIResponse[HealthSummaryData],
    status_code=status.HTTP_200_OK,
    summary="Application Health Summary",
    description="Returns high-level health, uptime, environment, and dependency summary.",
)
async def get_health_summary() -> APIResponse[HealthSummaryData]:
    """Retrieve combined application and database health status."""
    data = HealthService.get_overall_health()
    msg = "EcoCycle AI application is healthy" if data.status == "healthy" else "EcoCycle AI application running (database degraded or unconfigured)"
    return APIResponse[HealthSummaryData](
        success=True,
        message=msg,
        data=data,
    )


@router.get(
    "/db",
    response_model=APIResponse[DatabaseHealthData],
    status_code=status.HTTP_200_OK,
    summary="Database Connectivity Probe",
    description="Dedicated PostgreSQL and PostGIS diagnostic check. Reports connectivity, latency, and extension status.",
)
async def get_database_health() -> APIResponse[DatabaseHealthData]:
    """Retrieve detailed database health metrics."""
    data = HealthService.get_database_health()
    return APIResponse[DatabaseHealthData](
        success=data.connected,
        message=data.message,
        data=data,
    )


@router.get(
    "/live",
    response_model=APIResponse[LivenessData],
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Standard Kubernetes/container liveness probe. Indicates if the HTTP server process is running.",
)
async def get_liveness() -> APIResponse[LivenessData]:
    """Liveness probe confirming the server process is responsive."""
    return APIResponse[LivenessData](
        success=True,
        message="Service is alive",
        data=HealthService.get_liveness(),
    )


@router.get(
    "/ready",
    response_model=APIResponse[ReadinessData],
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Indicates whether the service is prepared to handle user requests.",
)
async def get_readiness() -> APIResponse[ReadinessData]:
    """Readiness probe checking backend components."""
    data = HealthService.get_readiness()
    return APIResponse[ReadinessData](
        success=True,
        message="Service is ready",
        data=data,
    )
