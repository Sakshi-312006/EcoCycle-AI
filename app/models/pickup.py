"""Pillar 2: Pickup Requests and EcoProof Verification ORM Models."""

from datetime import datetime, timezone
from typing import Optional
import uuid
import sqlalchemy as sa
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class PickupRequest(Base, UUIDMixin, TimestampMixin):
    """Operational dispatch request linked to a waste report."""

    __tablename__ = "pickup_requests"

    report_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("waste_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collector_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collector_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vehicle_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="scheduled", index=True, nullable=False)

    # Relationships
    waste_report: Mapped["WasteReport"] = relationship("WasteReport", back_populates="pickups")
    verification: Mapped[Optional["VerificationRecord"]] = relationship(
        "VerificationRecord",
        back_populates="pickup",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def is_overdue(self) -> bool:
        """Evaluate if scheduled pickup deadline has elapsed without completion."""
        if self.status in ["completed", "resolved", "cancelled"]:
            return False
        if not self.scheduled_time:
            return False
        sched = self.scheduled_time
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > sched


class VerificationRecord(Base, UUIDMixin, TimestampMixin):
    """EcoProof collection verification event containing SHA-256 integrity hash."""

    __tablename__ = "verification_records"

    pickup_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("pickup_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    actual_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    stream_confirmed: Mapped[str] = mapped_column(String(50), nullable=False)
    collector_signature_id: Mapped[str] = mapped_column(String(100), nullable=False)
    after_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ecocredits_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    pickup: Mapped["PickupRequest"] = relationship("PickupRequest", back_populates="verification")
