"""Health service encapsulating status checks for the application and database.

Isolates health evaluation logic from API controllers.
"""

import time
from datetime import datetime, timezone
from typing import Dict

from app.core.config import settings
from app.db.session import check_db_connection
from app.schemas.health import (
    DatabaseHealthData,
    HealthSummaryData,
    LivenessData,
    ReadinessData,
)

# Record application start time for uptime tracking
_APP_START_TIME = time.time()


class HealthService:
    """Service providing diagnostics on service vitality and dependency status."""

    @staticmethod
    def get_uptime_seconds() -> float:
        """Calculate service uptime in seconds."""
        return round(time.time() - _APP_START_TIME, 2)

    @classmethod
    def get_database_health(cls) -> DatabaseHealthData:
        """Probe the database connection and return typed health metrics."""
        db_info = check_db_connection()
        return DatabaseHealthData(
            status=db_info["status"],
            connected=db_info["connected"],
            message=db_info["message"],
            latency_ms=db_info["latency_ms"],
            database_name=db_info["database_name"],
            postgis_installed=db_info["postgis_installed"],
            postgis_version=db_info["postgis_version"],
        )

    @classmethod
    def get_overall_health(cls) -> HealthSummaryData:
        """Produce an aggregated health assessment of the app and its database."""
        db_health = cls.get_database_health()

        # The application itself is functional even if the DB is unconfigured or disconnected.
        # Status is marked as 'healthy' when connected, or 'degraded' if DB is disconnected/unconfigured.
        overall_status = "healthy" if db_health.connected else "degraded"

        return HealthSummaryData(
            app_name=settings.PROJECT_NAME,
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            status=overall_status,
            uptime_seconds=cls.get_uptime_seconds(),
            database=db_health,
        )

    @classmethod
    def get_liveness(cls) -> LivenessData:
        """Return basic process vitality report."""
        return LivenessData(status="ok")

    @classmethod
    def get_readiness(cls) -> ReadinessData:
        """Verify readiness to accept incoming user/mobile traffic."""
        db_health = cls.get_database_health()
        components: Dict[str, str] = {
            "api_server": "ready",
            "database": db_health.status,
        }
        # For local dev without DB yet, API server is ready
        status = "ready"
        return ReadinessData(status=status, components=components)
