"""Pydantic schemas for platform and subsystem health monitoring."""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class DatabaseHealthData(BaseModel):
    """Detailed health report for PostgreSQL and PostGIS."""

    status: str = Field(..., description="Status indicator: connected | disconnected | unconfigured")
    connected: bool = Field(..., description="True if database probe succeeded")
    message: str = Field(..., description="Human-readable diagnosis or error details")
    latency_ms: Optional[float] = Field(default=None, description="Round-trip query latency in ms")
    database_name: Optional[str] = Field(default=None, description="Connected database name")
    postgis_installed: bool = Field(default=False, description="True if PostGIS extension is installed")
    postgis_version: Optional[str] = Field(default=None, description="Version string of PostGIS extension")


class HealthSummaryData(BaseModel):
    """Overall application health summary."""

    app_name: str = Field(..., description="Name of the backend service")
    version: str = Field(..., description="Service version string")
    environment: str = Field(..., description="Running environment (development, staging, production)")
    status: str = Field(..., description="Overall health status (healthy | degraded)")
    uptime_seconds: float = Field(..., description="Service running duration in seconds")
    database: DatabaseHealthData = Field(..., description="Current database connectivity status")


class LivenessData(BaseModel):
    """Service liveness probe payload."""

    status: str = Field(default="ok", description="Basic application process viability")


class ReadinessData(BaseModel):
    """Service readiness probe payload."""

    status: str = Field(..., description="Readiness status (ready | not_ready)")
    components: Dict[str, str] = Field(default_factory=dict, description="Subsystem status mapping")
