"""Pillar 4: Garbage-Pile Detection, Smart Collection Routing & Verified Cleanliness Schemas.

Covers:
1. Citizen Garbage-Pile Reporting with GPS, size, weight, and description.
2. Duplicate report detection within spatial/temporal windows (masking private citizen data).
3. Transparent rule-based severity and priority scoring (no fake CV claims).
4. Capacity-aware and authorization-checked vehicle assignment.
5. EcoProof cryptographic cleanup verification with before/after photos (no reporting rewards).
6. Municipal illegal dumping dashboard aggregates.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator

from app.schemas.waste import WasteStreamEnum


class PileSizeEnum(str, Enum):
    """Estimated volumetric pile dimensions with standard heuristic baseline weights."""

    SMALL = "small"          # ~15 kg
    MEDIUM = "medium"        # ~40 kg
    LARGE = "large"          # ~100 kg
    CRITICAL = "critical"    # ~250 kg


class SeverityLevelEnum(str, Enum):
    """Transparent rule-based priority levels for dispatch queues."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Weight mapping heuristics for pile sizes when not explicitly weighed
PILE_SIZE_WEIGHT_MAP_KG: Dict[str, float] = {
    PileSizeEnum.SMALL.value: 15.0,
    PileSizeEnum.MEDIUM.value: 40.0,
    PileSizeEnum.LARGE.value: 100.0,
    PileSizeEnum.CRITICAL.value: 250.0,
}

# Base score contribution by pile size
PILE_SIZE_SCORE_MAP: Dict[str, float] = {
    PileSizeEnum.SMALL.value: 15.0,
    PileSizeEnum.MEDIUM.value: 30.0,
    PileSizeEnum.LARGE.value: 60.0,
    PileSizeEnum.CRITICAL.value: 90.0,
}

# Statutory hazard weights
STREAM_HAZARD_SCORES: Dict[str, float] = {
    WasteStreamEnum.HAZARDOUS.value: 100.0,
    WasteStreamEnum.SANITARY.value: 50.0,
    WasteStreamEnum.WET_ORGANIC.value: 40.0,
    WasteStreamEnum.DRY_RECYCLABLE.value: 20.0,
}


class SeverityBreakdown(BaseModel):
    """Transparent rule-based scoring explaining the priority tier calculation."""

    size_score: float = Field(..., description="Base points from estimated pile size")
    category_hazard_score: float = Field(..., description="Statutory hazard points (hazardous=100, sanitary=50, wet=40, dry=20)")
    aging_hours: float = Field(..., description="Hours elapsed since report was registered")
    aging_score: float = Field(..., description="Aging urgency points (+2.0 pts per unresolved hour)")
    total_score: float = Field(..., description="Composite priority score")
    priority_tier: SeverityLevelEnum = Field(..., description="Calculated priority tier: CRITICAL | HIGH | MEDIUM | LOW")
    methodology: str = Field(
        default="Statutory rule-based heuristic (size + category hazard + aging). Does not claim automated computer-vision mass assessment.",
        description="Integrity disclaimer",
    )


class DuplicateCandidateItem(BaseModel):
    """Nearby unresolved candidate report. Omits private citizen identity."""

    report_id: uuid.UUID
    category: str
    status: str
    distance_meters: float
    reported_at: datetime
    address: Optional[str] = None


class DuplicateCheckRequest(BaseModel):
    """Payload to check proximity to existing open waste piles."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS Longitude (-180 to 180)")
    category: Optional[WasteStreamEnum] = Field(None, description="Optional stream to match")
    radius_meters: float = Field(default=100.0, ge=1.0, le=5000.0, description="Proximity search radius in meters")
    window_hours: float = Field(default=24.0, ge=0.5, le=168.0, description="Lookback time window in hours")


class DuplicateCheckResponse(BaseModel):
    """Result of spatial/temporal duplicate detection."""

    is_duplicate: bool = Field(..., description="True if unresolved candidate reports found within radius and window")
    candidates_found: int = Field(..., description="Count of duplicate candidates found")
    candidates: List[DuplicateCandidateItem] = Field(default_factory=list, description="Candidate report metadata")
    message: str = Field(..., description="Human-readable duplicate status summary")


class GarbagePileReportCreate(BaseModel):
    """Citizen or worker submission of an illegal garbage pile."""

    category: WasteStreamEnum = Field(..., description="Statutory waste stream")
    pile_size: PileSizeEnum = Field(default=PileSizeEnum.MEDIUM, description="Estimated visual volume: small | medium | large | critical")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS Longitude")
    address: Optional[str] = Field(None, max_length=255, description="Street address, landmark, or corner")
    ward_number: Optional[str] = Field(None, max_length=50, description="Municipal ward identifier")
    description: str = Field(..., min_length=3, max_length=1000, description="Specific description of waste pile")
    image_url: Optional[str] = Field(None, max_length=500, description="Uploaded before-photo URL from ImageUploadService")
    estimated_weight_kg: Optional[float] = Field(None, ge=0.1, le=5000.0, description="Estimated payload weight in kg")
    ecopass_id: Optional[str] = Field(None, max_length=50, description="Optional reporting citizen EcoPass ID")
    force_create: bool = Field(False, description="Set True to override duplicate warning and confirm separate distinct pile")

    @field_validator("ecopass_id", mode="before")
    @classmethod
    def clean_ecopass_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return None


class GarbagePileReportResponse(BaseModel):
    """Complete representation of a registered garbage pile report."""

    id: uuid.UUID
    category: str
    report_type: str = "illegal_dump"
    pile_size: Optional[str] = None
    estimated_weight_kg: float
    latitude: float
    longitude: float
    address: Optional[str] = None
    ward_number: Optional[str] = None
    description: str
    image_url: Optional[str] = None
    status: str
    severity: str
    severity_details: Optional[SeverityBreakdown] = None
    created_at: datetime
    pickup_id: Optional[uuid.UUID] = None
    assigned_vehicle_id: Optional[str] = None


class VehicleRecommendationResponse(BaseModel):
    """Automated vehicle suitability and capacity verification."""

    report_id: uuid.UUID
    category: str
    estimated_weight_kg: float
    recommended_vehicle_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_assigned: bool = Field(..., description="True if a valid vehicle is eligible and assigned/recommended")
    reason: str = Field(..., description="Operational justification or unassigned rejection reason")
    compartment_capacity_kg: Optional[float] = None
    current_load_kg: Optional[float] = None
    remaining_capacity_kg: Optional[float] = None
    disclaimer: str = Field(
        default="Vehicle suitability verified against static statutory compartments and waste authorizations. Does not claim live GPS telemetry.",
        description="Operational notice",
    )


class GarbagePileAssignVehicleRequest(BaseModel):
    """Request to assign or dispatch a specific fleet vehicle to a pile."""

    vehicle_id: str = Field(..., min_length=1, max_length=50, description="Target fleet vehicle ID")
    collector_id: Optional[str] = Field(None, max_length=100, description="Assigned driver or sanitary supervisor ID")
    collector_name: Optional[str] = Field(None, max_length=100, description="Name of assigned driver or sanitary supervisor")
    scheduled_time: Optional[datetime] = Field(None, description="Planned collection time window")


class GarbagePileCleanupVerifyRequest(BaseModel):
    """Request by municipal collector or sanitary inspector to certify cleanup."""

    after_image_url: str = Field(..., min_length=1, max_length=500, description="Photo evidence of cleaned site")
    verifier_id: str = Field(..., min_length=1, max_length=100, description="Collector or inspector badge / identity ID")
    actual_weight_kg: float = Field(..., gt=0.0, le=5000.0, description="Actual scale weight collected in kg")
    notes: Optional[str] = Field(None, max_length=1000, description="Field notes on cleanup completion")


class GarbagePileCleanupVerifyResponse(BaseModel):
    """EcoProof cryptographic receipt confirming field resolution of garbage pile."""

    report_id: uuid.UUID
    pickup_id: uuid.UUID
    status: str = "resolved"
    before_image_url: Optional[str] = None
    after_image_url: str
    actual_weight_kg: float
    verifier_id: str
    integrity_hash: str
    verified_at: datetime
    ecocredits_awarded: int = Field(default=0, description="Always 0: citizen reporting does not disburse EcoCredits to prevent fraud")
    verification_method: str = Field(
        default="Manual field inspector certification with before/after cryptographic SHA-256 seal. No automated CV certification claimed.",
        description="Integrity and verification disclaimer",
    )


class GarbagePileDashboardResponse(BaseModel):
    """Aggregated municipal analytics on illegal dumping, response velocity, and cleanliness."""

    total_reports: int = Field(..., description="Total waste reports in database")
    total_illegal_piles: int = Field(..., description="Total illegal dumping reports")
    status_breakdown: Dict[str, int] = Field(..., description="Counts grouped by lifecycle status")
    priority_distribution: Dict[str, int] = Field(..., description="Counts grouped by severity priority tier")
    potential_duplicate_candidates_count: int = Field(..., description="Open reports that have nearby duplicate candidates")
    vehicle_assignment_stats: Dict[str, int] = Field(..., description="Assigned vs unassigned breakdown")
    total_verified_cleanups: int = Field(..., description="Count of successfully cleared and certified piles")
    total_cleaned_weight_kg: float = Field(..., description="Cumulative weight of waste removed from verified piles")
    average_resolution_time_hours: Optional[float] = Field(None, description="Average time in hours from reporting to verified cleanup")
    timestamp: datetime = Field(..., description="Calculation timestamp")

