"""Pillar 3: Circular Recovery, Upcycling, MRF Routing, Resale, and Community Donation Endpoints."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.circular import (
    CircularClaimRequest,
    CircularConditionEnum,
    CircularItemCategoryEnum,
    CircularListingCreate,
    CircularListingResponse,
    CircularListingTypeEnum,
    CircularMaterialCatalogResponse,
    CircularMaterialGuidanceRequest,
    CircularPickupDetailResponse,
    CircularPickupRequest,
    CircularPickupResponse,
    CircularStreamTypeEnum,
    MaterialGuidanceItem,
    PackagingConditionEnum,
    ResaleCompleteRequest,
)
from app.schemas.common import APIResponse
from app.schemas.waste_workflow import ImageUploadResponse
from app.services.circular_service import CircularService
from app.services.image_upload_service import ImageUploadService

router = APIRouter(prefix="/circular", tags=["Pillar 3: Circular Recovery & MRF Routing"])


# ---------------------------------------------------------------------------
# Image Upload for Circular Materials
# ---------------------------------------------------------------------------


@router.post(
    "/upload-image",
    response_model=APIResponse[ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Circular Material Photograph",
    description="Upload a photo of rigid recyclables, flexible packaging, or circular items from camera/gallery with signature verification and size validation.",
)
async def upload_circular_image(
    file: UploadFile = File(..., description="Image file payload (JPEG, PNG, WebP)"),
) -> APIResponse[ImageUploadResponse]:
    """Securely store circular material photograph and return access URL."""
    upload_result = await ImageUploadService.save_upload(file)
    return APIResponse[ImageUploadResponse](
        success=True,
        message="Circular material photograph uploaded and verified successfully.",
        data=upload_result,
    )


# ---------------------------------------------------------------------------
# Stream 3A & Stream 3B: MRF Material Guidance & Preparation Catalog
# ---------------------------------------------------------------------------


@router.get(
    "/materials/guidance",
    response_model=APIResponse[CircularMaterialCatalogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Circular Materials Preparation & Destination Catalog",
    description="Browse material categories for Stream 3A (Rigid: PET, HDPE, aluminium, other) and Stream 3B (Flexible: clean wrappers vs contaminated packaging) with accepted items, preparation requirements, and approved destination routing.",
)
def get_circular_materials_catalog(
    stream_type: Optional[CircularStreamTypeEnum] = Query(None, description="stream_3a_rigid | stream_3b_flexible"),
    condition: Optional[PackagingConditionEnum] = Query(None, description="clean_dry | dirty_contaminated"),
) -> APIResponse[CircularMaterialCatalogResponse]:
    """Retrieve full or filtered material guidance catalog."""
    materials = CircularService.get_material_catalog(stream_type=stream_type, condition=condition)
    return APIResponse[CircularMaterialCatalogResponse](
        success=True,
        message=f"Retrieved {len(materials)} circular material guidance categories.",
        data=CircularMaterialCatalogResponse(
            stream_type=stream_type.value if stream_type else None,
            total_categories=len(materials),
            materials=materials,
        ),
    )


@router.post(
    "/materials/guidance",
    response_model=APIResponse[MaterialGuidanceItem],
    status_code=status.HTTP_200_OK,
    summary="Evaluate Material Handling Guidance",
    description="Get specific preparation instructions and intended recovery destination for a selected material category and condition.",
)
def evaluate_circular_material_guidance(
    request: CircularMaterialGuidanceRequest,
) -> APIResponse[MaterialGuidanceItem]:
    """Evaluate material guidance for specific selection."""
    item = CircularService.evaluate_material_guidance(request)
    return APIResponse[MaterialGuidanceItem](
        success=True,
        message=f"Guidance evaluated for '{item.name}'. Intended destination: {item.intended_destination}",
        data=item,
    )


# ---------------------------------------------------------------------------
# Stream 3A & Stream 3B: Optional Pickup Request & Tracking
# ---------------------------------------------------------------------------


@router.post(
    "/materials/request-pickup",
    response_model=APIResponse[CircularPickupResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request Circular Material Pickup",
    description="Schedule an optional doorstep pickup for sorted rigid or flexible packaging. Credits are awarded ONLY after physical collection verification.",
)
def request_circular_material_pickup(
    request: CircularPickupRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CircularPickupResponse]:
    """Schedule circular material collection pickup."""
    result = CircularService.request_circular_pickup(db, request)
    return APIResponse[CircularPickupResponse](
        success=True,
        message=result.message,
        data=result,
    )


@router.get(
    "/materials/pickups/{pickup_id}",
    response_model=APIResponse[CircularPickupDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Track Circular Pickup & Verified Destination",
    description="Track collection status, intended recycling destination, and EcoProof verification details (including credits awarded after verification).",
)
def get_circular_material_pickup(
    pickup_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CircularPickupDetailResponse]:
    """Retrieve circular pickup tracking and destination details."""
    details = CircularService.get_circular_pickup_details(db, pickup_id)
    return APIResponse[CircularPickupDetailResponse](
        success=True,
        message=f"Circular pickup '{pickup_id}' retrieved with status '{details.status}'.",
        data=details,
    )


# ---------------------------------------------------------------------------
# Stream 3C & Resale: Secondhand Marketplace & Community Donation Listings
# ---------------------------------------------------------------------------


@router.post(
    "/listings",
    response_model=APIResponse[CircularListingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Publish Circular Listing",
    description="List an item for secondhand resale or community NGO donation to divert usable goods from landfills.",
)
def create_circular_listing(
    listing_in: CircularListingCreate,
    db: Session = Depends(get_db),
) -> APIResponse[CircularListingResponse]:
    """Publish circular item listing."""
    listing = CircularService.create_listing(db, listing_in)
    return APIResponse[CircularListingResponse](
        success=True,
        message=f"Circular {listing.listing_type} listing '{listing.title}' created.",
        data=CircularListingResponse.model_validate(listing),
    )


@router.post(
    "/listings/with-photo",
    response_model=APIResponse[CircularListingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Publish Circular Listing with Photo (Multipart)",
    description="Upload photo and publish secondhand resale or donation item in a single multipart request.",
)
async def create_circular_listing_with_photo(
    file: UploadFile = File(..., description="Item photograph (JPEG, PNG, WebP)"),
    listing_type: CircularListingTypeEnum = Form(..., description="resale | donation"),
    title: str = Form(..., min_length=3, max_length=150),
    description: str = Form(..., min_length=5, max_length=2000),
    category: CircularItemCategoryEnum = Form(...),
    condition: CircularConditionEnum = Form(...),
    donor_or_seller_name: str = Form(..., min_length=2, max_length=100),
    price_inr: Optional[float] = Form(None),
    ecopass_id: Optional[str] = Form(None),
    beneficiary_ngo_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> APIResponse[CircularListingResponse]:
    """Upload photo and create circular listing atomically."""
    upload_res = await ImageUploadService.save_upload(file)
    listing_in = CircularListingCreate(
        listing_type=listing_type,
        title=title,
        description=description,
        category=category,
        condition=condition,
        donor_or_seller_name=donor_or_seller_name,
        price_inr=price_inr,
        image_url=upload_res.file_url,
        ecopass_id=ecopass_id,
        beneficiary_ngo_name=beneficiary_ngo_name,
    )
    listing = CircularService.create_listing(db, listing_in)
    return APIResponse[CircularListingResponse](
        success=True,
        message=f"Circular {listing.listing_type} listing '{listing.title}' created with verified photo.",
        data=CircularListingResponse.model_validate(listing),
    )


@router.get(
    "/listings",
    response_model=APIResponse[List[CircularListingResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Circular Items",
    description="Browse reusable items and donations with type, category, and status filters.",
)
def list_circular_listings(
    listing_type: Optional[CircularListingTypeEnum] = Query(None, description="resale | donation"),
    category: Optional[CircularItemCategoryEnum] = Query(None, description="Item category"),
    status_filter: Optional[str] = Query(None, alias="status", description="available | claimed | completed"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[List[CircularListingResponse]]:
    """List circular items."""
    type_val = listing_type.value if listing_type else None
    cat_val = category.value if category else None
    listings = CircularService.list_listings(
        db,
        listing_type=type_val,
        category=cat_val,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return APIResponse[List[CircularListingResponse]](
        success=True,
        message=f"Retrieved {len(listings)} circular listings.",
        data=[CircularListingResponse.model_validate(item) for item in listings],
    )


@router.get(
    "/listings/{listing_id}",
    response_model=APIResponse[CircularListingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Circular Listing Details",
    description="Retrieve details of a single circular item.",
)
def get_circular_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CircularListingResponse]:
    """Retrieve circular listing."""
    listing = CircularService.get_listing_by_id(db, listing_id)
    return APIResponse[CircularListingResponse](
        success=True,
        message="Circular listing retrieved.",
        data=CircularListingResponse.model_validate(listing),
    )


@router.post(
    "/listings/{listing_id}/claim",
    response_model=APIResponse[CircularListingResponse],
    status_code=status.HTTP_200_OK,
    summary="Claim Circular Item / Finalize Recovery",
    description="Claim a donation item for community reuse. If the donor provided an EcoPass ID, 50 diversion EcoCredits are automatically awarded to their ledger.",
)
def claim_circular_listing(
    listing_id: uuid.UUID,
    claim_in: CircularClaimRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CircularListingResponse]:
    """Claim a circular listing and disburse reward credits."""
    listing = CircularService.claim_listing(db, listing_id, claim_in)
    return APIResponse[CircularListingResponse](
        success=True,
        message=f"Item '{listing.title}' successfully claimed by '{claim_in.claimer_name}'. Diversion EcoCredits awarded to donor.",
        data=CircularListingResponse.model_validate(listing),
    )


@router.post(
    "/listings/{listing_id}/complete-sale",
    response_model=APIResponse[CircularListingResponse],
    status_code=status.HTTP_200_OK,
    summary="Complete Resale Transaction",
    description="Finalize secondhand marketplace resale transaction between buyer and seller. Transitions listing to completed.",
)
def complete_resale_listing(
    listing_id: uuid.UUID,
    request: ResaleCompleteRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CircularListingResponse]:
    """Complete a secondhand marketplace resale sale."""
    listing = CircularService.complete_resale(db, listing_id, request)
    return APIResponse[CircularListingResponse](
        success=True,
        message=f"Resale of '{listing.title}' completed with buyer '{request.buyer_name}'.",
        data=CircularListingResponse.model_validate(listing),
    )
