"""Pillar 1: Pydantic schemas for the complete waste identification and handling workflow.

Supports:
1. Secure image upload response
2. AI classification request and response with confidence thresholding & fallbacks
3. Specific handling guidance with scientific, safety, and statutory advice
4. Home-handling vs pickup decision outcomes
5. Explicit pickup submission after user confirmation
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator

from app.schemas.voice import LanguageCodeEnum
from app.schemas.waste import WasteStreamEnum


class ActionOutcomeEnum(str, Enum):
    """Explicit testable decision outcomes following handling guidance."""

    HOME_HANDLING_RECOMMENDED = "HOME_HANDLING_RECOMMENDED"
    COLLECTION_APPROPRIATE = "COLLECTION_APPROPRIATE"
    SPECIAL_HANDLING_REQUIRED = "SPECIAL_HANDLING_REQUIRED"
    UNCERTAIN_CONFIRMATION_REQUIRED = "UNCERTAIN_CONFIRMATION_REQUIRED"


class ImageUploadResponse(BaseModel):
    """Metadata response for a securely stored waste photo upload."""

    file_id: uuid.UUID = Field(..., description="Unique upload identifier")
    filename: str = Field(..., description="Server-sanitized stored filename")
    file_url: str = Field(..., description="Static HTTP access URL for Flutter client")
    content_type: str = Field(..., description="Validated MIME type (image/jpeg, image/png, image/webp)")
    size_bytes: int = Field(..., description="Uploaded payload size in bytes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Upload timestamp")


class WasteClassificationRequest(BaseModel):
    """Request payload to analyze an uploaded waste photo."""

    image_url: str = Field(..., min_length=1, max_length=500, description="URL or identifier of uploaded image")
    user_hint: Optional[str] = Field(None, max_length=100, description="Optional user descriptive hint or candidate item")
    confirmed_category: Optional[WasteStreamEnum] = Field(
        None, description="Optional manual selection/confirmation by citizen if model was uncertain or weights missing"
    )


class WasteClassificationResponse(BaseModel):
    """Classification response with category, confidence, item-level predictions, and fallback indicators."""

    predicted_category: Optional[WasteStreamEnum] = Field(
        None, description="Predicted statutory stream (wet_organic, dry_recyclable, sanitary, hazardous)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    item_prediction: Optional[str] = Field(None, description="Item-level prediction if specifically recognized with high support")
    item_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Item-level prediction confidence")
    is_manual_selection: bool = Field(False, description="True if category was confirmed manually by citizen")
    requires_confirmation: bool = Field(..., description="True if low-confidence or model weights unverified")
    fallback_triggered: bool = Field(..., description="True if safe fallback mode activated")
    model_info: Dict[str, Any] = Field(..., description="Metadata on classifier architecture, weights status, and threshold")
    suggested_action: str = Field(..., description="Action prompt for client: confirm_category | proceed_to_guidance | retake_photo")
    message: str = Field(..., description="Clear explanation of classification state")


class HandlingGuidanceRequest(BaseModel):
    """Request for category- and item-specific waste handling guidance."""

    category: WasteStreamEnum = Field(..., description="Confirmed or selected waste category")
    item: Optional[str] = Field(None, max_length=100, description="Optional specific item key or name (e.g. raw_fruit_scraps)")
    language: LanguageCodeEnum = Field(default=LanguageCodeEnum.EN, description="Target localized language")
    has_home_composting_setup: bool = Field(default=False, description="Whether citizen has active home composting facility")
    is_potentially_infectious: bool = Field(default=False, description="Flag for potentially blood/pathogen-contaminated items")


class HandlingGuidanceResponse(BaseModel):
    """Comprehensive handling guidance with scientific, safety, and statutory advice."""

    category: WasteStreamEnum = Field(..., description="Target waste stream")
    item: Optional[str] = Field(None, description="Specific item analyzed, if recognized")
    item_or_stream: str = Field(..., description="Descriptive identifier of item or generic stream")
    language: str = Field(..., description="Language code")
    title: str = Field(..., description="Localized headline/title")
    scientific_guidance: str = Field(..., description="Practical and scientific handling/composting instructions")
    safety_precautions: str = Field(..., description="Hygiene and protective handling measures")
    statutory_guidance: Optional[str] = Field(None, description="Verified statutory rules (e.g. SWM Rules 2016)")
    statutory_reference: Optional[str] = Field(None, description="Specific legal or regulatory citation")
    statutory_requirement: Optional[str] = Field(None, description="Direct statutory mandate separate from scientific advice")
    official_source_title: Optional[str] = Field(None, description="Authoritative gazette notification or standard title")
    official_source_url: Optional[str] = Field(None, description="Official government/CPCB reference link")
    rule_or_schedule_reference: Optional[str] = Field(None, description="Exact statutory rule number or schedule")
    verification_date: Optional[str] = Field("2026-10-29", description="Date of legal/scientific verification")
    home_handling_suitable: bool = Field(..., description="True if citizen can safely process waste at home")
    collection_recommended: bool = Field(..., description="True if municipal/commercial collection is advised")
    pickup_available: bool = Field(..., description="True if doorstep pickup is enabled for this category/state")
    ordinary_pickup_allowed: bool = Field(..., description="Statutory and operational permission for ordinary doorstep pickup")
    specialized_disposal_required: bool = Field(False, description="True if bio-medical CBWTF or hazardous drop-off is mandatory")
    requires_human_review: bool = Field(False, description="True if contamination or stream requires manual triage")
    action_outcome: ActionOutcomeEnum = Field(..., description="Decision outcome: HOME_HANDLING_RECOMMENDED, etc.")
    action_message: str = Field(..., description="User guidance explaining next steps")
    allowed_next_actions: List[str] = Field(..., description="Permitted user actions in Flutter UI")


class PickupSubmissionRequest(BaseModel):
    """Atomic request to create a waste report and dispatch pickup ONLY after explicit citizen confirmation."""

    confirmed_category: WasteStreamEnum = Field(..., description="Citizen-confirmed waste category")
    item: Optional[str] = Field(None, max_length=100, description="Optional specific item identified")
    image_url: Optional[str] = Field(None, max_length=500, description="Validated photo URL")
    description: str = Field(..., min_length=3, max_length=1000, description="Description or location notes")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Citizen GPS latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Citizen GPS longitude")
    address: Optional[str] = Field(None, max_length=255, description="Street address or landmark")
    ward_number: Optional[str] = Field(None, max_length=50, description="Municipal ward")
    ecopass_id: Optional[str] = Field(None, max_length=50, description="Optional household EcoPass ID")
    estimated_weight_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Estimated weight in kg")
    collector_id: Optional[str] = Field(None, max_length=100, description="Assigned collector ID (optional)")
    collector_name: Optional[str] = Field(None, max_length=100, description="Assigned collector name (optional)")
    vehicle_id: Optional[str] = Field(None, max_length=50, description="Assigned vehicle ID (optional)")
    scheduled_time: Optional[datetime] = Field(None, description="Requested pickup time")

    @field_validator("ecopass_id", mode="before")
    @classmethod
    def clean_ecopass_id(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class PickupSubmissionResponse(BaseModel):
    """Response containing created waste report and scheduled pickup request details."""

    report_id: uuid.UUID = Field(..., description="Generated WasteReport UUID")
    pickup_id: uuid.UUID = Field(..., description="Generated PickupRequest UUID")
    category: str = Field(..., description="Confirmed waste stream")
    status: str = Field(..., description="Initial pickup status (scheduled)")
    collector_name: Optional[str] = Field(None, description="Assigned collector name")
    vehicle_id: Optional[str] = Field(None, description="Assigned vehicle identifier")
    scheduled_time: Optional[datetime] = Field(None, description="Scheduled collection timestamp")
    message: str = Field(..., description="Confirmation message for the Flutter app")
    created_at: datetime = Field(..., description="Creation timestamp")

