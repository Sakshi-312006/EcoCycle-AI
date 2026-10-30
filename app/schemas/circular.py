"""Pillar 3: Pydantic schemas for Circular Recovery, Material Routing, and Reuse."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Stream 3C & Resale: Community Reuse & Secondhand Marketplace
# ---------------------------------------------------------------------------


class CircularListingTypeEnum(str, Enum):
    """Listing purpose: marketplace resale or community donation."""

    RESALE = "resale"
    DONATION = "donation"


class CircularItemCategoryEnum(str, Enum):
    """Categories for circular reuse, donation, and resale items."""

    CLOTHES = "clothes"
    BOOKS = "books"
    TOYS = "toys"
    FURNITURE = "furniture"
    APPLIANCES = "appliances"
    OTHER = "other"


class CircularConditionEnum(str, Enum):
    """Physical condition of the item."""

    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_REPAIR = "needs_repair"


class CircularListingCreate(BaseModel):
    """Schema for publishing an item for circular reuse or donation."""

    listing_type: CircularListingTypeEnum = Field(..., description="resale | donation")
    title: str = Field(..., min_length=3, max_length=150, description="Title of circular item")
    description: str = Field(..., min_length=5, max_length=2000, description="Detailed condition, dimensions, defects, and description")
    category: CircularItemCategoryEnum = Field(..., description="Category: clothes | books | toys | furniture | appliances | other")
    condition: CircularConditionEnum = Field(..., description="Item condition: like_new | good | fair | needs_repair")
    price_inr: Optional[float] = Field(
        None,
        description="Asking price in INR for resale items. Must be greater than ₹0 for resale; free (omitted or 0) for donation.",
    )
    donor_or_seller_name: str = Field(..., min_length=2, max_length=100, description="Contact name")
    image_url: Optional[str] = Field(None, max_length=500, description="Uploaded photo URL of the actual item")
    ecopass_id: Optional[str] = Field(None, max_length=50, description="EcoPass ID to receive circular diversion credits")
    beneficiary_ngo_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Optional preferred community recipient (Note: Prototype community target, not verified statutory NGO partner)",
    )

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Item title is required and cannot be empty.")
        clean = v.strip()
        if len(clean) < 3:
            raise ValueError("Item title must be at least 3 characters long.")
        return clean

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Item description is required and cannot be empty.")
        clean = v.strip()
        if len(clean) < 5:
            raise ValueError("Item description must be at least 5 characters long.")
        return clean

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ("clothing", "cloth", "clothes"):
                return "clothes"
            if v_lower in ("electronic", "electronics"):
                return "appliances"
            return v_lower
        return v

    @field_validator("donor_or_seller_name", mode="before")
    @classmethod
    def validate_contact_name(cls, v: Any) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Donor or seller name is required and cannot be empty.")
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Contact name must be at least 2 characters long.")
        return clean

    @field_validator("ecopass_id", mode="before")
    @classmethod
    def clean_ecopass_id(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

    @field_validator("image_url", mode="before")
    @classmethod
    def clean_image_url(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

    @model_validator(mode="after")
    def validate_pricing_and_listing_type(self) -> "CircularListingCreate":
        if self.listing_type == CircularListingTypeEnum.RESALE:
            if self.price_inr is None or self.price_inr <= 0:
                raise ValueError("Resale listings require an asking price greater than ₹0 (price_inr > 0).")
        elif self.listing_type == CircularListingTypeEnum.DONATION:
            if self.price_inr is not None and self.price_inr > 0:
                raise ValueError("Donation items must be free. Asking price cannot be greater than ₹0 for donations.")
            self.price_inr = 0.0
        return self


class CircularClaimRequest(BaseModel):
    """Schema for claiming or finalizing recovery of a circular listing."""

    claimer_name: str = Field(..., min_length=2, max_length=100, description="Claimer or recipient name")
    notes: Optional[str] = Field(None, max_length=500, description="Recovery notes or pickup details")


class ResaleCompleteRequest(BaseModel):
    """Schema for completing a marketplace secondhand resale transaction."""

    buyer_name: str = Field(..., min_length=2, max_length=100, description="Buyer name")
    transaction_notes: Optional[str] = Field(None, max_length=500, description="Payment confirmation or handover notes")


class CircularListingResponse(BaseModel):
    """Standard response model for circular listings."""

    id: uuid.UUID
    listing_type: str
    title: str
    description: str
    category: str
    condition: str
    price_inr: Optional[float] = Field(None, description="Asking price in INR (displayed for resale; omitted/null for donations)")
    is_free: bool = Field(False, description="True if listing is a free donation")
    donor_or_seller_name: str
    image_url: Optional[str] = Field(None, description="Uploaded photo URL of the item")
    ecopass_id: Optional[str]
    beneficiary_ngo_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def format_price_display(self) -> "CircularListingResponse":
        if str(self.listing_type).lower() == "donation":
            self.price_inr = None
            self.is_free = True
        else:
            self.is_free = False
        return self


# ---------------------------------------------------------------------------
# Stream 3A & Stream 3B: Material Recovery Facility (MRF) Categorization & Guidance
# ---------------------------------------------------------------------------


class CircularStreamTypeEnum(str, Enum):
    """Pillar 3 Circular Material Streams."""

    STREAM_3A_RIGID = "stream_3a_rigid"
    STREAM_3B_FLEXIBLE = "stream_3b_flexible"


class RigidMaterialCategoryEnum(str, Enum):
    """Stream 3A: Rigid plastics and metals."""

    PET = "pet"
    HDPE = "hdpe"
    ALUMINIUM_CANS = "aluminium_cans"
    OTHER_RIGID = "other_rigid"


class PackagingConditionEnum(str, Enum):
    """Stream 3B: Condition determining circular vs industrial recovery."""

    CLEAN_DRY = "clean_dry"
    DIRTY_CONTAMINATED = "dirty_contaminated"


class PackagingCategoryEnum(str, Enum):
    """Stream 3B: Flexible and multilayer packaging categories."""

    CLEAN_WRAPPER = "clean_wrapper"
    CONTAMINATED_PACKAGING = "contaminated_packaging"


class DestinationTypeEnum(str, Enum):
    """Approved recovery or processing destination types."""

    MECHANICAL_RECYCLING = "mechanical_recycling"
    ARTISAN_UPCYCLING = "artisan_upcycling"
    INDUSTRIAL_RECOVERY = "industrial_recovery"
    MUNICIPAL_DISPOSAL = "municipal_disposal"


class MaterialGuidanceItem(BaseModel):
    """Detailed guidance for a circular material stream."""

    category_key: str = Field(..., description="Unique category key (e.g. pet, hdpe, clean_wrapper)")
    name: str = Field(..., description="Human-readable material name")
    stream_type: CircularStreamTypeEnum = Field(..., description="Stream 3A (Rigid) or Stream 3B (Flexible)")
    spi_resin_code: Optional[str] = Field(None, description="Resin identification code (SPI #1, #2, etc.)")
    packaging_condition: Optional[PackagingConditionEnum] = Field(None, description="Packaging cleanliness condition")
    accepted_items: List[str] = Field(..., description="List of accepted items")
    rejected_items: List[str] = Field(..., description="List of rejected items")
    preparation_requirements: List[str] = Field(..., description="Preparation checklist for the citizen")
    examples: List[str] = Field(..., description="Everyday household examples")
    intended_destination: str = Field(..., description="Designated recycling, upcycling, or recovery facility")
    destination_type: DestinationTypeEnum = Field(..., description="Type of destination facility")
    credit_eligible: bool = Field(True, description="Whether verified collection qualifies for EcoCredits")
    handling_instructions: str = Field(..., description="Summary instructions for safe collection")


class CircularMaterialGuidanceRequest(BaseModel):
    """Request for targeted circular material guidance."""

    stream_type: Optional[CircularStreamTypeEnum] = Field(None, description="Optional stream filter")
    material_category: Optional[str] = Field(None, description="Selected material category key")
    packaging_condition: Optional[PackagingConditionEnum] = Field(None, description="Required for Stream 3B packaging")


class CircularMaterialCatalogResponse(BaseModel):
    """Response containing material categories, preparation guidance, and destination routing."""

    stream_type: Optional[str] = Field(None, description="Stream filter if applied")
    total_categories: int = Field(..., description="Count of material categories returned")
    materials: List[MaterialGuidanceItem] = Field(..., description="Detailed guidance items")


class CircularPickupRequest(BaseModel):
    """Request to schedule an optional pickup for sorted circular materials."""

    stream_type: CircularStreamTypeEnum = Field(..., description="stream_3a_rigid | stream_3b_flexible")
    material_category: str = Field(..., description="Material category key (pet, hdpe, aluminium_cans, other_rigid, clean_wrapper, contaminated_packaging)")
    packaging_condition: Optional[PackagingConditionEnum] = Field(
        None, description="Cleanliness condition (mandatory for stream_3b_flexible: clean_dry | dirty_contaminated)"
    )
    image_url: Optional[str] = Field(None, max_length=500, description="Optional uploaded waste photo URL")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of material or quantity")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="GPS Latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="GPS Longitude (-180 to 180)")
    address: Optional[str] = Field(None, max_length=255, description="Street address or collection landmark")
    ward_number: Optional[str] = Field(None, max_length=50, description="Municipal ward identifier")
    ecopass_id: Optional[str] = Field(None, max_length=50, description="Household EcoPass ID to receive EcoCredits on verified collection")
    estimated_weight_kg: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Estimated weight in kg")
    scheduled_time: Optional[datetime] = Field(None, description="Optional scheduled collection datetime")
    collector_id: Optional[str] = Field(None, max_length=100, description="Assigned collector identifier")
    collector_name: Optional[str] = Field(None, max_length=100, description="Assigned collector name")
    vehicle_id: Optional[str] = Field(None, max_length=50, description="Assigned collection vehicle")

    @field_validator("ecopass_id", mode="before")
    @classmethod
    def clean_ecopass_id(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class CircularPickupResponse(BaseModel):
    """Response confirming circular material pickup scheduling."""

    report_id: uuid.UUID = Field(..., description="Generated WasteReport identifier")
    pickup_id: uuid.UUID = Field(..., description="Generated PickupRequest identifier")
    stream_type: str = Field(..., description="Stream 3A or 3B")
    material_category: str = Field(..., description="Selected material key")
    material_name: str = Field(..., description="Human-readable material name")
    packaging_condition: Optional[str] = Field(None, description="Packaging condition")
    intended_destination: str = Field(..., description="Intended recycling / upcycling / industrial facility")
    destination_type: str = Field(..., description="Facility destination type")
    status: str = Field(..., description="Initial pickup status (scheduled)")
    image_url: Optional[str] = Field(None, description="Uploaded image URL if provided")
    ecopass_id: Optional[str] = Field(None, description="Registered generator EcoPass ID")
    estimated_weight_kg: Optional[float] = Field(None, description="Estimated weight in kg")
    message: str = Field(..., description="Operational status and credit notice")
    created_at: datetime = Field(..., description="Creation timestamp")


class CircularPickupDetailResponse(BaseModel):
    """Comprehensive tracking record for circular material pickup and verification."""

    pickup_id: uuid.UUID = Field(..., description="Pickup Request UUID")
    report_id: uuid.UUID = Field(..., description="Linked Waste Report UUID")
    stream_type: str = Field(..., description="Pillar 3 stream type")
    material_category: str = Field(..., description="Material category key")
    material_name: str = Field(..., description="Material title")
    packaging_condition: Optional[str] = Field(None, description="Cleanliness condition")
    intended_destination: str = Field(..., description="Intended recycling or upcycling destination")
    destination_type: str = Field(..., description="Destination category")
    status: str = Field(..., description="Pickup operational status (scheduled, in_progress, completed, cancelled)")
    collection_verified: bool = Field(..., description="True if EcoProof verification receipt has been issued")
    verified_weight_kg: Optional[float] = Field(None, description="Weight measured by collector upon handover")
    ecocredits_awarded: int = Field(0, description="EcoCredits awarded to generator (awarded ONLY after verification)")
    integrity_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 integrity receipt")
    collector_signature_id: Optional[str] = Field(None, description="Collector signature identifier")
    verified_at: Optional[datetime] = Field(None, description="Verification timestamp")
    ecopass_id: Optional[str] = Field(None, description="Generator EcoPass ID")
    address: Optional[str] = Field(None, description="Collection address")
    created_at: datetime = Field(..., description="Creation timestamp")
