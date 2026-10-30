"""Pillar 1: Pydantic schemas for Four-Stream Waste Management."""

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator


class WasteStreamEnum(str, Enum):
    """Statutory Four-Stream Waste Classification."""

    WET_ORGANIC = "wet_organic"
    DRY_RECYCLABLE = "dry_recyclable"
    SANITARY = "sanitary"
    HAZARDOUS = "hazardous"


class WasteReportStatusEnum(str, Enum):
    """Lifecycle status for a waste collection report."""

    REPORTED = "reported"
    ASSIGNED = "assigned"
    COLLECTED = "collected"
    VERIFIED = "verified"
    CANCELLED = "cancelled"


class WasteReportCreate(BaseModel):
    """Schema for submitting a doorstep waste report."""

    category: WasteStreamEnum = Field(..., description="Waste stream: wet_organic | dry_recyclable | sanitary | hazardous")
    description: str = Field(..., min_length=3, max_length=1000, description="Description of waste content or location notes")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS Longitude (-180 to 180)")
    address: Optional[str] = Field(None, max_length=255, description="Street address or landmark")
    ward_number: Optional[str] = Field(None, max_length=50, description="Municipal ward identifier")
    ecopass_id: Optional[str] = Field(None, max_length=50, description="Optional registered household EcoPass ID")
    image_url: Optional[str] = Field(None, max_length=500, description="Optional photo URL (Note: No simulated AI claims made on image)")
    estimated_weight_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="User estimated weight in kg")
    weight_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Payload weight in kg (mapped to estimated_weight_kg)")

    @field_validator("ecopass_id", mode="before")
    @classmethod
    def normalize_ecopass_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return None

    @model_validator(mode="after")
    def resolve_weight_fields(self) -> "WasteReportCreate":
        if self.weight_kg is not None and self.estimated_weight_kg is not None:
            if abs(self.weight_kg - self.estimated_weight_kg) > 1e-4:
                raise ValueError(
                    "Conflicting values provided for 'weight_kg' and 'estimated_weight_kg'. "
                    "Please supply only one field or ensure both match."
                )
        elif self.weight_kg is not None and self.estimated_weight_kg is None:
            self.estimated_weight_kg = self.weight_kg

        return self


class WasteReportUpdate(BaseModel):
    """Schema for updating report metadata or status."""

    status: Optional[WasteReportStatusEnum] = None
    estimated_weight_kg: Optional[float] = Field(None, ge=0.0)
    address: Optional[str] = None


class WasteReportResponse(BaseModel):
    """Standard response model for waste report."""

    id: uuid.UUID
    ecopass_id: Optional[str]
    category: str
    description: str
    image_url: Optional[str]
    latitude: float
    longitude: float
    address: Optional[str]
    ward_number: Optional[str]
    estimated_weight_kg: Optional[float]
    status: str
    is_overdue: bool = Field(False, description="True if report has exceeded collection SLA without resolution")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
