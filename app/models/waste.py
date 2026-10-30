"""Pillar 1: Four-Stream Waste Management ORM Models.

Supports the four statutory streams:
- wet_organic
- dry_recyclable
- sanitary
- hazardous (special-care / domestic hazardous)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
import uuid
import sqlalchemy as sa
from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class WasteReport(Base, UUIDMixin, TimestampMixin):
    """Doorstep waste collection reporting record."""

    __tablename__ = "waste_reports"

    ecopass_id: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ward_number: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    estimated_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), default="doorstep", index=True, nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="reported", index=True, nullable=False)

    # Relationships
    pickups: Mapped[List["PickupRequest"]] = relationship(
        "PickupRequest",
        back_populates="waste_report",
        cascade="all, delete-orphan",
    )

    @property
    def is_overdue(self) -> bool:
        """Evaluate if an unresolved waste report has exceeded the statutory 24-hour collection SLA."""
        if self.status in ["collected", "verified", "cancelled", "resolved"]:
            return False
        if not self.created_at:
            return False
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > (created + timedelta(hours=24))
