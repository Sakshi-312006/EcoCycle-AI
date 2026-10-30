"""SQLAlchemy 2.x Declarative Base and Reusable Model Mixins.

All ORM models across the five pillars inherit from Base.
Compatible with SQLite (local prototype) and PostgreSQL/PostGIS (production).
"""

from datetime import datetime, timezone
import uuid
import sqlalchemy as sa
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


class UUIDMixin:
    """Provides a primary key UUID column compatible with SQLite and PostgreSQL."""

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-10,
    )


class TimestampMixin:
    """Provides automated created_at and updated_at timezone-aware timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=101,
    )
