"""Application configuration module using Pydantic Settings.

Reads environment variables from system environment and .env file.
Provides validated, typed configurations across the application.
"""

from typing import List, Optional, Union
import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings and environment configuration for EcoCycle AI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "EcoCycle AI"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "development-secret-key-ecocycle-ai-secure-min-32-chars"
    DEFAULT_REPORT_SLA_HOURS: int = 24
    DEFAULT_PICKUP_SLA_HOURS: int = 24

    # Server Settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://10.0.2.2:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Allow CORS_ORIGINS as a comma-delimited string, JSON array string, or list."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return []

    # Database Configuration (PostgreSQL / PostGIS with SQLite Prototype Fallback)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "ecocycle_ai"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_TIMEOUT_SECONDS: int = 3
    DATABASE_URL: Optional[str] = None
    DATABASE_SQLITE_PATH: str = "./data/ecocycle_dev.db"

    @property
    def is_postgres_configured(self) -> bool:
        """Check if explicit PostgreSQL credentials or remote database URL have been configured."""
        if self.DATABASE_URL and "postgres" in self.DATABASE_URL.lower():
            return True
        return bool(self.POSTGRES_USER and self.POSTGRES_PASSWORD)

    @property
    def is_db_configured(self) -> bool:
        """Check if any database (SQLite or PostgreSQL) is configured."""
        return True

    @property
    def sqlalchemy_database_url(self) -> str:
        """Construct SQLAlchemy connection URL.

        Uses PostgreSQL/PostGIS if configured; otherwise defaults to persistent SQLite.
        """
        if self.DATABASE_URL and len(self.DATABASE_URL.strip()) > 0:
            return self.DATABASE_URL

        if self.is_postgres_configured:
            return (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        # Default local persistent SQLite prototype
        return f"sqlite:///{self.DATABASE_SQLITE_PATH}"

    # Storage & Upload Configuration
    STORAGE_LOCAL_PATH: str = "./data/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # Waste AI Classification Configuration
    CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.70
    CLASSIFIER_MODEL_PATH: str = "./data/models/mobilenetv3_waste.pt"

    # Future Pillars Integration Placeholders
    ECOPROOF_SALT: str = "ecoproof-verification-salt-placeholder"
    OSRM_BASE_URL: str = "http://localhost:5000"
    BHASHINI_USER_ID: Optional[str] = None
    BHASHINI_API_KEY: Optional[str] = None
    BHASHINI_PIPELINE_ENDPOINT: Optional[str] = None
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883


# Global settings singleton
settings = Settings()
