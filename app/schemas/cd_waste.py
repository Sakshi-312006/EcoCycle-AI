"""Pillar 3: Construction & Demolition (C&D) Estimation and Material Schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, Field, model_validator


class CDMaterialDensityEnum(str, Enum):
    """Standard volumetric bulk density values for construction debris (kg/m³)."""

    CONCRETE_RUBBLE = "concrete_rubble"    # ~1500 kg/m³
    BRICK_MASONRY = "brick_masonry"        # ~1800 kg/m³
    MIXED_CD = "mixed_cd"                  # ~1300 kg/m³
    TILES_CERAMIC = "tiles_ceramic"        # ~1600 kg/m³
    SOIL_EXCAVATION = "soil_excavation"    # ~1400 kg/m³


class CDEstimateRequest(BaseModel):
    """Request schema for estimating C&D debris volume and mass."""

    project_name: str = Field(..., min_length=3, max_length=150, description="Site project name or address")
    location: str = Field(..., min_length=3, max_length=255, description="Physical site address")
    material_type: CDMaterialDensityEnum = Field(..., description="Debris material type")
    length_m: Optional[float] = Field(None, gt=0.0, description="Length in meters")
    width_m: Optional[float] = Field(None, gt=0.0, description="Width in meters")
    height_m: Optional[float] = Field(None, gt=0.0, description="Height in meters")
    user_volume_m3: Optional[float] = Field(None, gt=0.0, description="Direct volume in cubic meters if dimensions unavailable")

    @model_validator(mode="after")
    def validate_dimensions_or_volume(self):
        has_dims = self.length_m is not None and self.width_m is not None and self.height_m is not None
        has_vol = self.user_volume_m3 is not None
        if not (has_dims or has_vol):
            raise ValueError("Must provide either (length_m, width_m, height_m) or direct user_volume_m3.")
        return self


class CDEstimateResponse(BaseModel):
    """Formula-based estimation output clearly disclaiming AI/point-cloud claims."""

    id: uuid.UUID
    project_name: str
    location: str
    material_type: str
    length_m: Optional[float]
    width_m: Optional[float]
    height_m: Optional[float]
    estimated_volume_m3: float
    material_density_kg_m3: float
    estimated_mass_kg: float
    estimated_metric_tons: float
    estimation_method: str = Field(
        default="formula_geometric_bounding_box",
        description="Calculation algorithm identifier",
    )
    disclaimer: str = Field(
        default="Formula-based estimate using geometric dimensions and standard material density. Not AI or 3D point-cloud scanned.",
        description="Methodology and accuracy disclaimer",
    )
    created_at: datetime

    class Config:
        from_attributes = True


class CDMaterialCategoryEnum(str, Enum):
    """Categories of salvageable construction materials."""

    BRICKS = "bricks"
    TILES = "tiles"
    CONCRETE_BLOCKS = "concrete_blocks"
    AGGREGATE = "aggregate"
    TIMBER = "timber"
    STEEL_SCRAP = "steel_scrap"
    DOORS_WINDOWS = "doors_windows"
    REUSABLE_STEEL = "reusable_steel"
    OTHER = "other"


class CDRubbleCategoryEnum(str, Enum):
    """Categories of broken construction and demolition rubble for recycling (Stream A)."""

    BROKEN_CONCRETE = "broken_concrete"
    BRICK_MASONRY = "brick_masonry"
    MIXED_CD_RUBBLE = "mixed_cd_rubble"
    TILES_CERAMIC = "tiles_ceramic"
    SOIL_EXCAVATION = "soil_excavation"


# Configurable bulk density assumptions in tonnes/m³ (1.0 t/m³ = 1000 kg/m³)
CD_BULK_DENSITIES_TONNES_M3 = {
    CDRubbleCategoryEnum.BROKEN_CONCRETE.value: 1.5,
    CDRubbleCategoryEnum.BRICK_MASONRY.value: 1.8,
    CDRubbleCategoryEnum.MIXED_CD_RUBBLE.value: 1.3,
    CDRubbleCategoryEnum.TILES_CERAMIC.value: 1.6,
    CDRubbleCategoryEnum.SOIL_EXCAVATION.value: 1.4,
}


class CDMaterialConditionEnum(str, Enum):
    """Condition rating for reusable materials."""

    REUSABLE_EXCELLENT = "reusable_excellent"
    REUSABLE_GOOD = "reusable_good"
    RECYCLABLE_SCRAP = "recyclable_scrap"


class CDMaterialStatusEnum(str, Enum):
    """Lifecycle status for salvageable construction materials."""

    AVAILABLE = "available"
    RESERVED = "reserved"
    COLLECTED = "collected"


ALLOWED_CD_MATERIAL_STATUSES = {s.value for s in CDMaterialStatusEnum}


class CDMaterialCreate(BaseModel):
    """Schema for listing reusable construction materials for salvage/resale."""

    title: str = Field(..., min_length=3, max_length=150, description="Listing title, e.g. 'Red clay bricks - 1200 pieces'")
    material_category: CDMaterialCategoryEnum = Field(..., description="Category: bricks, tiles, doors_windows, etc.")
    quantity: float = Field(..., gt=0.0, description="Quantity available")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement: pieces, sq_meters, metric_tons")
    condition: CDMaterialConditionEnum = Field(..., description="reusable_excellent | reusable_good | recyclable_scrap")
    price_inr: float = Field(default=0.0, ge=0.0, description="Price in INR (0.0 for free recovery)")
    location: str = Field(..., min_length=3, max_length=255, description="Pickup location")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Seller or site contact phone")
    description: Optional[str] = Field(None, max_length=2000, description="Detailed condition, dimensions, and defects")
    image_url: Optional[str] = Field(None, max_length=500, description="Photograph of reusable item")


class CDMaterialResponse(BaseModel):
    """Schema for listed reusable construction materials."""

    id: uuid.UUID
    title: str
    material_category: str
    quantity: float
    unit: str
    condition: str
    price_inr: float
    location: str
    contact_phone: Optional[str]
    description: Optional[str] = None
    image_url: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Stream A: C&D Rubble Reporting, Vehicle Dispatch & Chain of Custody Schemas
# ---------------------------------------------------------------------------


class CDWasteReportCreate(BaseModel):
    """Submission schema for construction & demolition rubble (Stream A)."""

    project_name: str = Field(..., min_length=3, max_length=150, description="Construction / demolition project or site name")
    contractor_name: Optional[str] = Field(None, max_length=100, description="Contractor / company name")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Site manager phone number")
    material_category: CDRubbleCategoryEnum = Field(..., description="broken_concrete | brick_masonry | mixed_cd_rubble | tiles_ceramic | soil_excavation")
    description: str = Field(..., min_length=5, max_length=2000, description="Description of debris and site access")
    image_url: Optional[str] = Field(None, max_length=500, description="Photograph URL from image upload service")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Site GPS latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Site GPS longitude")
    address: str = Field(..., min_length=3, max_length=255, description="Physical site address")
    landmark: Optional[str] = Field(None, max_length=255, description="Nearest road, cross, or landmark")

    # Dimensions or direct volume
    length_m: Optional[float] = Field(None, gt=0.0, le=100.0, description="Estimated length in meters")
    width_m: Optional[float] = Field(None, gt=0.0, le=100.0, description="Estimated width in meters")
    height_m: Optional[float] = Field(None, gt=0.0, le=100.0, description="Estimated average height in meters")
    user_volume_m3: Optional[float] = Field(None, gt=0.0, le=10000.0, description="Direct volume in cubic meters if irregular")
    custom_density_tonnes_m3: Optional[float] = Field(None, ge=0.5, le=3.5, description="Optional custom bulk density in tonnes/m³")

    request_pickup: bool = Field(False, description="Set True to immediately request fleet pickup collection")
    intended_destination: Optional[str] = Field(
        default="Authorized C&D Recycling Facility",
        description="Target recycling destination or processing yard",
    )

    @model_validator(mode="after")
    def validate_dimensions_or_volume(self):
        has_dims = self.length_m is not None and self.width_m is not None and self.height_m is not None
        has_vol = self.user_volume_m3 is not None
        if not (has_dims or has_vol):
            raise ValueError("Must provide either (length_m, width_m, height_m) or direct user_volume_m3.")
        return self


class CDWasteReportResponse(BaseModel):
    """Complete representation of a registered C&D waste report."""

    id: uuid.UUID
    project_name: str
    contractor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    material_category: str
    description: str
    image_url: Optional[str] = None
    latitude: float
    longitude: float
    address: str
    landmark: Optional[str] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    estimated_volume_m3: float
    bulk_density_tonnes_m3: float
    estimated_weight_tonnes: float
    estimated_weight_kg: float
    status: str
    pickup_id: Optional[uuid.UUID] = None
    assigned_vehicle_id: Optional[str] = None
    intended_destination: str
    destination_facility_name: Optional[str] = None
    collected_at: Optional[datetime] = None
    facility_received_at: Optional[datetime] = None
    facility_received_weight_tonnes: Optional[float] = None
    processing_status: str
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CDVehicleRecommendationResponse(BaseModel):
    """Fleet recommendation tailored for bulk C&D transport."""

    report_id: uuid.UUID
    material_category: str
    estimated_weight_tonnes: float
    recommended_vehicle_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_assigned: bool = Field(..., description="True if a suitable vehicle is eligible and recommended")
    reason: str = Field(..., description="Operational explanation or rejection justification")
    max_capacity_tonnes: Optional[float] = None
    disclaimer: str = Field(
        default="Vehicle recommendation checks bulk C&D tipper authorization and payload capacity. No real-time GPS telemetry claimed.",
        description="Integrity disclaimer",
    )


class CDVehicleAssignRequest(BaseModel):
    """Dispatch vehicle assignment request for C&D rubble pickup."""

    vehicle_id: str = Field(..., min_length=1, max_length=50, description="Assigned fleet vehicle ID")
    collector_id: Optional[str] = Field(None, max_length=100, description="Driver or heavy equipment operator ID")
    collector_name: Optional[str] = Field(None, max_length=100, description="Driver or heavy equipment operator name")
    scheduled_time: Optional[datetime] = Field(None, description="Planned collection time window")


class CDCollectionEventRequest(BaseModel):
    """Field collection confirmation recorded by driver or site supervisor."""

    collector_id: str = Field(..., min_length=1, max_length=100, description="Driver or supervisor badge / ID")
    collection_evidence_image_url: Optional[str] = Field(None, max_length=500, description="Loading or site cleared photo")
    actual_weight_tonnes: Optional[float] = Field(None, gt=0.0, le=100.0, description="Field measured or estimated weight in tonnes")
    notes: Optional[str] = Field(None, max_length=1000, description="Site loading and access notes")


class CDFacilityReceiptRequest(BaseModel):
    """Recording of material arrival at an authorized C&D recycling facility."""

    facility_name: str = Field(..., min_length=3, max_length=255, description="Name of receiving C&D recycling facility")
    received_weight_tonnes: float = Field(..., gt=0.0, le=100.0, description="Actual scale weighbridge weight in tonnes")
    weighbridge_ticket_id: Optional[str] = Field(None, max_length=100, description="Weighbridge ticket or slip number")
    weighbridge_slip_url: Optional[str] = Field(None, max_length=500, description="Photo of weighbridge slip")
    notes: Optional[str] = Field(None, max_length=1000, description="Facility intake quality and contamination notes")


class CDProcessingCompletionRequest(BaseModel):
    """Recording of mechanical crushing, screening, or sorting completion."""

    output_material_type: str = Field(..., min_length=3, max_length=100, description="e.g. recycled_concrete_aggregate_20mm, manufactured_sand")
    output_tonnes: float = Field(..., gt=0.0, le=100.0, description="Weight of processed output material in tonnes")
    processing_evidence: str = Field(..., min_length=3, max_length=1000, description="Crushing batch reference or facility run log")
    notes: Optional[str] = Field(None, max_length=1000, description="Quality testing or processing notes")


class CDDisposalRecordResponse(BaseModel):
    """Full digital chain of custody tracking across all lifecycle stages."""

    report_id: uuid.UUID
    project_name: str
    location: str
    material_category: str
    estimated_volume_m3: float
    bulk_density_tonnes_m3: float
    estimated_weight_tonnes: float
    status: str
    pickup_id: Optional[uuid.UUID] = None
    assigned_vehicle_id: Optional[str] = None
    collected_at: Optional[datetime] = None
    collector_id: Optional[str] = None
    collection_evidence_image_url: Optional[str] = None
    collection_weight_tonnes: Optional[float] = None
    intended_destination: str
    facility_name: Optional[str] = None
    facility_received_at: Optional[datetime] = None
    facility_received_weight_tonnes: Optional[float] = None
    weighbridge_ticket_id: Optional[str] = None
    weight_discrepancy_tonnes: Optional[float] = Field(
        None,
        description="Calculated variance: facility_received_weight_tonnes - estimated_weight_tonnes",
    )
    processing_status: str
    processing_completed_at: Optional[datetime] = None
    processed_output_type: Optional[str] = None
    processed_output_tonnes: Optional[float] = None
    processing_evidence: Optional[str] = None
    integrity_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 digital chain of custody seal")
    record_type: str = Field(
        default="Internal application digital disposal tracking record",
        description="Manifest classification",
    )
    disclaimer: str = Field(
        default="Internal application tracking record. Does not represent official statutory government CPCB manifest. Output aggregate is uncertified.",
        description="Statutory and certification disclaimer",
    )


class CDHashVerificationResponse(BaseModel):
    """Response schema for verifying cryptographic chain of custody seal."""

    report_id: uuid.UUID
    is_valid: bool = Field(..., description="True if stored hash matches recomputed canonical digest")
    status: str = Field(..., description="verified | mismatch | unsealed")
    hash_format: Optional[str] = Field(None, description="v2_strengthened | v1_legacy | None")
    stored_hash: Optional[str] = Field(None, description="SHA-256 digest currently stored on record")
    computed_hash: Optional[str] = Field(None, description="Recomputed SHA-256 digest from canonical record values")
    message: str = Field(..., description="Verification summary and format details")
    disclaimer: str = Field(
        default="SHA-256 cryptographic verification confirms that record fields match the digest issued at processing completion. It does not replace physical weighbridge slips or civil engineering lab aggregate tests.",
        description="Integrity and legal disclaimer",
    )


class CDDashboardResponse(BaseModel):
    """Aggregated operational metrics for C&D recycling and salvage marketplace."""

    total_cd_reports: int = Field(..., description="Total C&D rubble reports logged")
    reports_by_material: dict = Field(..., description="Count of reports per C&D rubble category")
    total_pickups: int = Field(..., description="Total C&D pickup requests")
    pickups_by_status: dict = Field(..., description="Pickups grouped by status")
    total_estimated_volume_m3: float = Field(..., description="Cumulative estimated rubble volume in m³")
    total_estimated_weight_tonnes: float = Field(..., description="Cumulative estimated rubble weight in tonnes")
    total_collected_weight_tonnes: float = Field(..., description="Actual weight collected in tonnes")
    material_awaiting_facility_receipt_tonnes: float = Field(..., description="Collected weight in transit to facility")
    material_awaiting_processing_tonnes: float = Field(..., description="Weight received at facility awaiting crushing")
    total_processed_tonnes: float = Field(..., description="Total rubble crushed into aggregate/sand")
    reusable_materials_listed_count: int = Field(..., description="Count of reusable items posted in marketplace")
    reusable_materials_by_status: dict = Field(..., description="Reusable listings by status (available, reserved, collected)")
    reusable_materials_diverted_count: int = Field(..., description="Reusable items claimed or collected")
    disposal_stage_breakdown: dict = Field(..., description="Count of reports at each lifecycle stage")
    timestamp: datetime = Field(..., description="Metrics computation timestamp")
