"""Database connection, session management, and resilience utilities.

Supports both persistent SQLite (local fast prototyping) and
PostgreSQL with PostGIS (production deployment).
"""

import os
import time
from typing import Any, Dict, Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import DatabaseConnectionException
from app.core.logging import get_logger

logger = get_logger("app.db.session")

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def get_engine() -> Optional[Engine]:
    """Retrieve or create the SQLAlchemy engine singleton safely."""
    global _engine, _SessionFactory

    db_url = settings.sqlalchemy_database_url
    if not db_url:
        return None

    if _engine is None:
        try:
            logger.info(f"Initializing database engine ({'SQLite' if db_url.startswith('sqlite') else 'PostgreSQL'})...")
            if db_url.startswith("sqlite"):
                # Ensure directory exists for file-based SQLite
                if "/" in settings.DATABASE_SQLITE_PATH or "\\" in settings.DATABASE_SQLITE_PATH:
                    dir_path = os.path.dirname(settings.DATABASE_SQLITE_PATH)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                _engine = create_engine(
                    db_url,
                    connect_args={"check_same_thread": False},
                )
            else:
                _engine = create_engine(
                    db_url,
                    pool_size=settings.DATABASE_POOL_SIZE,
                    max_overflow=settings.DATABASE_MAX_OVERFLOW,
                    pool_pre_ping=True,
                    connect_args={"connect_timeout": settings.DATABASE_TIMEOUT_SECONDS},
                )

            _SessionFactory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=_engine,
            )
            logger.info("Database engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize database engine: {e}")
            _engine = None
            _SessionFactory = None

    return _engine


def get_session_factory() -> Optional[sessionmaker]:
    """Retrieve the configured SessionLocal factory."""
    if _SessionFactory is None:
        get_engine()
    return _SessionFactory


def init_db() -> None:
    """Initialize database tables for local prototyping and development."""
    engine = get_engine()
    if engine is not None:
        try:
            from app.models import Base
            logger.info("Verifying and initializing database schema tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized successfully.")

            # Safe schema evolution for circular_listings, waste_reports, and verification_records
            try:
                with engine.connect() as conn:
                    # circular_listings.image_url
                    cols = [row[1] for row in conn.execute(text("PRAGMA table_info(circular_listings);")).fetchall()]
                    if cols and "image_url" not in cols:
                        logger.info("Migrating circular_listings: adding image_url column...")
                        conn.execute(text("ALTER TABLE circular_listings ADD COLUMN image_url VARCHAR(500);"))
                        conn.commit()
                        logger.info("Migration circular_listings image_url complete.")

                    # waste_reports.report_type and severity
                    wr_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(waste_reports);")).fetchall()]
                    if wr_cols:
                        if "report_type" not in wr_cols:
                            logger.info("Migrating waste_reports: adding report_type column...")
                            conn.execute(text("ALTER TABLE waste_reports ADD COLUMN report_type VARCHAR(50) DEFAULT 'doorstep';"))
                            conn.commit()
                        if "severity" not in wr_cols:
                            logger.info("Migrating waste_reports: adding severity column...")
                            conn.execute(text("ALTER TABLE waste_reports ADD COLUMN severity VARCHAR(50);"))
                            conn.commit()

                    # verification_records.after_image_url
                    vr_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(verification_records);")).fetchall()]
                    if vr_cols and "after_image_url" not in vr_cols:
                        logger.info("Migrating verification_records: adding after_image_url column...")
                        conn.execute(text("ALTER TABLE verification_records ADD COLUMN after_image_url VARCHAR(500);"))
                        conn.commit()

                    # cd_materials.image_url and description
                    cd_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(cd_materials);")).fetchall()]
                    if cd_cols:
                        if "image_url" not in cd_cols:
                            logger.info("Migrating cd_materials: adding image_url column...")
                            conn.execute(text("ALTER TABLE cd_materials ADD COLUMN image_url VARCHAR(500);"))
                            conn.commit()
                        if "description" not in cd_cols:
                            logger.info("Migrating cd_materials: adding description column...")
                            conn.execute(text("ALTER TABLE cd_materials ADD COLUMN description TEXT;"))
                            conn.commit()
            except Exception as m_exc:
                logger.debug(f"Schema evolution check: {m_exc}")
        except Exception as exc:
            logger.error(f"Error initializing schema tables: {exc}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    factory = get_session_factory()
    if factory is None:
        raise DatabaseConnectionException(
            "Database engine is uninitialized. Verify your configuration in .env."
        )

    session: Session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> Dict[str, Any]:
    """Perform a diagnostic health check on the database.

    Works cleanly with both SQLite and PostgreSQL/PostGIS.
    """
    engine = get_engine()
    if engine is None:
        return {
            "status": "engine_error",
            "connected": False,
            "message": "Engine initialization failed. Check database URL syntax and driver.",
            "latency_ms": None,
            "database_name": None,
            "postgis_installed": False,
            "postgis_version": None,
        }

    start_time = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            is_sqlite = engine.dialect.name == "sqlite"
            postgis_version: Optional[str] = None
            postgis_installed = False

            if is_sqlite:
                db_name = f"SQLite ({os.path.basename(settings.DATABASE_SQLITE_PATH)})"
                message = "Local persistent SQLite prototype database active."
            else:
                db_name = settings.POSTGRES_DB
                message = "PostgreSQL connection healthy."
                # Check for PostGIS extension
                try:
                    result = conn.execute(
                        text("SELECT extversion FROM pg_extension WHERE extname = 'postgis';")
                    ).fetchone()
                    if result:
                        postgis_installed = True
                        postgis_version = result[0]
                except Exception as pe:
                    logger.debug(f"PostGIS check query failed: {pe}")

            return {
                "status": "connected",
                "connected": True,
                "message": message,
                "latency_ms": latency_ms,
                "database_name": db_name,
                "postgis_installed": postgis_installed,
                "postgis_version": postgis_version,
            }
    except Exception as exc:
        logger.warning(f"Database health check probe failed: {exc}")
        return {
            "status": "disconnected",
            "connected": False,
            "message": f"Database unreachable: {str(exc)}",
            "latency_ms": None,
            "database_name": None,
            "postgis_installed": False,
            "postgis_version": None,
        }
