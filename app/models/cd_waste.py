"""Pillar 3: Construction & Demolition (C&D) Waste ORM Models."""

from datetime import datetime
from typing import Optional
import uuid
import sqlalchemy as sa
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class CDEstimateRecord(Base, UUIDMixin, TimestampMixin):
    """Formula-based geometric volume and tonnage estimation calculation log."""

    __tablename__ = "cd_estimates"

    project_name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    material_type: Mapped[str] = mapped_column(String(100), nullable=False)
    length_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    material_density_kg_m3: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_mass_kg: Mapped[float] = mapped_column(Float, nullable=False)
    estimation_method: Mapped[str] = mapped_column(
        String(100),
        default="formula_geometric_bounding_box",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(255),
        default="Formula-based geometric calculation. Not 3D point cloud or AI scanned.",
        nullable=False,
    )


class CDMaterialListing(Base, UUIDMixin, TimestampMixin):
    """Reusable and salvageable construction material marketplace listing."""

    __tablename__ = "cd_materials"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    material_category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    price_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="available", index=True, nullable=False)


class CDWasteReport(Base, UUIDMixin, TimestampMixin):
    """Construction & Demolition waste report (Stream A: rubble for recycling)."""

    __tablename__ = "cd_waste_reports"

    project_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contractor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    material_category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    landmark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Volume and mass estimation
    length_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    user_volume_m3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    bulk_density_tonnes_m3: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_weight_tonnes: Mapped[float] = mapped_column(Float, nullable=False)
    estimation_method: Mapped[str] = mapped_column(
        String(100),
        default="formula_geometric_bounding_box",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(255),
        default="Rough geometric bounding-box estimate. Not weighbridge certified.",
        nullable=False,
    )

    # Lifecycle & Chain of Custody
    status: Mapped[str] = mapped_column(String(50), default="reported", index=True, nullable=False)
    # reported | pickup_requested | assigned | collected | received_at_facility | processing_completed | cancelled

    waste_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("waste_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    pickup_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        ForeignKey("pickup_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_vehicle_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    intended_destination: Mapped[str] = mapped_column(
        String(255),
        default="Authorized C&D Recycling Facility",
        nullable=False,
    )
    destination_facility_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Collection Stage
    collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    collector_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    collection_evidence_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    collection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collection_weight_tonnes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Facility Receipt Stage
    facility_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    facility_received_weight_tonnes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weighbridge_ticket_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weighbridge_slip_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    facility_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing Stage
    processing_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    # pending | in_progress | completed
    processing_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_output_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processed_output_tonnes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    integrity_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

