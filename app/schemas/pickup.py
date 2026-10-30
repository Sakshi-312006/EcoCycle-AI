"""Pillar 2: Pydantic schemas for Pickup Requests and EcoProof Verification."""

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class PickupStatusEnum(str, Enum):
    """Status lifecycle for doorstep pickup requests."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PickupCreate(BaseModel):
    """Schema for scheduling a pickup from an existing waste report."""

    report_id: uuid.UUID = Field(..., description="Target waste report ID")
    collector_id: Optional[str] = Field(None, max_length=100, description="Assigned sanitation worker ID")
    collector_name: Optional[str] = Field(None, max_length=100, description="Assigned sanitation worker name")
    vehicle_id: Optional[str] = Field(None, max_length=50, description="Assigned fleet compartment vehicle number")
    scheduled_time: Optional[datetime] = Field(None, description="Planned pickup timestamp")


class PickupStatusUpdate(BaseModel):
    """Schema for progressing pickup lifecycle status."""

    status: PickupStatusEnum = Field(..., description="New status")
    notes: Optional[str] = Field(None, max_length=255)


class CollectionVerificationCreate(BaseModel):
    """Schema for verifying waste collection and issuing EcoProof receipt."""

    actual_weight_kg: float = Field(..., gt=0.0, le=5000.0, description="Weighed waste mass in kg")
    stream_confirmed: str = Field(..., description="Confirmed waste stream (wet_organic, dry_recyclable, sanitary, hazardous)")
    collector_signature_id: str = Field(..., min_length=2, max_length=100, description="Collector staff ID certifying pickup")
    notes: Optional[str] = Field(None, max_length=500, description="Condition of segregation notes")


class VerificationResponse(BaseModel):
    """EcoProof collection verification receipt with SHA-256 integrity digest."""

    id: uuid.UUID
    pickup_id: uuid.UUID
    verified_at: datetime
    actual_weight_kg: float
    stream_confirmed: str
    collector_signature_id: str
    notes: Optional[str]
    integrity_hash: str = Field(..., description="SHA-256 cryptographic digest of verification fields")
    ecocredits_awarded: int = Field(default=0, description="EcoCredits awarded to linked household EcoPass")
    hash_explanation: str = Field(
        default="SHA-256 provides record tamper-detection; it verifies record immutability, not physical proof of real-world occurrence.",
        description="Integrity guarantee disclaimer",
    )

    class Config:
        from_attributes = True


class PickupResponse(BaseModel):
    """Detailed pickup response model."""

    id: uuid.UUID
    report_id: uuid.UUID
    collector_id: Optional[str]
    collector_name: Optional[str]
    vehicle_id: Optional[str]
    scheduled_time: Optional[datetime]
    status: str
    is_overdue: bool = Field(False, description="True if scheduled deadline has elapsed without completion or cancellation")
    created_at: datetime
    updated_at: datetime
    verification: Optional[VerificationResponse] = None

    class Config:
        from_attributes = True


class PickupQRCodeResponse(BaseModel):
    """QR code response encoding stable verification URL for EcoProof receipt."""

    pickup_id: uuid.UUID
    verification_url: str = Field(..., description="Stable public backend verification URL encoded in the QR")
    qr_code_data_url: str = Field(..., description="Base64-encoded PNG data URI of the QR code (data:image/png;base64,...)")
    is_verified: bool = Field(..., description="True if pickup collection has been verified with an EcoProof receipt")
    status: str = Field(..., description="Lifecycle status of the pickup: scheduled | in_progress | completed | cancelled")
    integrity_hash: Optional[str] = Field(None, description="SHA-256 integrity hash if sealed")
    disclaimer: str = Field(
        default="The QR code encodes a verification URL for backend integrity validation. The QR image itself does not prove real-world authenticity.",
        description="Integrity and authenticity disclaimer",
    )


class PickupVerificationStatusResponse(BaseModel):
    """Cryptographic verification result for an EcoProof pickup receipt."""

    pickup_id: uuid.UUID
    is_valid: bool = Field(..., description="True if stored integrity hash matches computed canonical hash")
    status: str = Field(..., description="verified | unverified | mismatch")
    verified_at: Optional[datetime] = None
    actual_weight_kg: Optional[float] = None
    stream_confirmed: Optional[str] = None
    collector_signature_id: Optional[str] = None
    stored_hash: Optional[str] = None
    computed_hash: Optional[str] = None
    ecocredits_awarded: Optional[int] = None
    message: str = Field(..., description="Detailed verification status message")
    disclaimer: str = Field(
        default="SHA-256 verification confirms record tamper-evidence and ledger immutability; it does not replace physical weighbridge slips.",
        description="Integrity guarantee disclaimer",
    )
