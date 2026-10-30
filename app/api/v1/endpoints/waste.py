"""Pillar 1: Four-Stream Waste Management REST Endpoints."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.waste import (
    WasteReportCreate,
    WasteReportResponse,
    WasteReportStatusEnum,
    WasteReportUpdate,
    WasteStreamEnum,
)
from app.schemas.waste_workflow import (
    HandlingGuidanceRequest,
    HandlingGuidanceResponse,
    ImageUploadResponse,
    PickupSubmissionRequest,
    PickupSubmissionResponse,
    WasteClassificationRequest,
    WasteClassificationResponse,
)
from app.services.image_upload_service import ImageUploadService
from app.services.waste_classifier_service import WasteClassifierService
from app.services.waste_guidance_service import WasteGuidanceService
from app.services.waste_service import WasteService
from app.services.waste_workflow_service import WasteWorkflowService

router = APIRouter(prefix="/waste-reports", tags=["Pillar 1: Four-Stream Waste Management"])


@router.post(
    "",
    response_model=APIResponse[WasteReportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Waste Report",
    description="Submit a doorstep collection report classified into one of the 4 statutory streams: wet_organic, dry_recyclable, sanitary, or hazardous.",
)
def create_waste_report(
    report_in: WasteReportCreate,
    db: Session = Depends(get_db),
) -> APIResponse[WasteReportResponse]:
    """Create a new doorstep waste report."""
    report = WasteService.create_report(db, report_in)
    return APIResponse[WasteReportResponse](
        success=True,
        message=f"Waste report logged for stream '{report.category}' in ward '{report.ward_number or 'unassigned'}'.",
        data=WasteReportResponse.model_validate(report),
    )


@router.get(
    "",
    response_model=APIResponse[List[WasteReportResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Waste Reports",
    description="Retrieve waste reports with optional filtering by stream, lifecycle status, and municipal ward.",
)
def list_waste_reports(
    category: Optional[WasteStreamEnum] = Query(None, description="Filter by stream"),
    status_filter: Optional[WasteReportStatusEnum] = Query(None, alias="status", description="Filter by status"),
    ward: Optional[str] = Query(None, description="Filter by municipal ward"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[List[WasteReportResponse]]:
    """List waste reports matching criteria."""
    cat_val = category.value if category else None
    stat_val = status_filter.value if status_filter else None
    reports = WasteService.list_reports(
        db,
        category=cat_val,
        status=stat_val,
        ward_number=ward,
        limit=limit,
        offset=offset,
    )
    return APIResponse[List[WasteReportResponse]](
        success=True,
        message=f"Retrieved {len(reports)} waste reports.",
        data=[WasteReportResponse.model_validate(r) for r in reports],
    )


@router.get(
    "/{report_id}",
    response_model=APIResponse[WasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Waste Report by ID",
    description="Fetch single waste report details.",
)
def get_waste_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[WasteReportResponse]:
    """Retrieve waste report by unique ID."""
    report = WasteService.get_report_by_id(db, report_id)
    return APIResponse[WasteReportResponse](
        success=True,
        message="Waste report retrieved.",
        data=WasteReportResponse.model_validate(report),
    )


@router.patch(
    "/{report_id}",
    response_model=APIResponse[WasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Waste Report",
    description="Update report metadata or manual status transition.",
)
def update_waste_report(
    report_id: uuid.UUID,
    update_in: WasteReportUpdate,
    db: Session = Depends(get_db),
) -> APIResponse[WasteReportResponse]:
    """Update waste report attributes."""
    report = WasteService.update_report(db, report_id, update_in)
    return APIResponse[WasteReportResponse](
        success=True,
        message="Waste report updated successfully.",
        data=WasteReportResponse.model_validate(report),
    )


# ---------------------------------------------------------------------------
# Complete Pillar 1 Workflow Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload-image",
    response_model=APIResponse[ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Waste Photograph",
    description="Accepts image file (JPEG, PNG, WebP) from Flutter camera/gallery, validates binary signature and size bounds, stores safely, and returns static URL.",
)
async def upload_waste_image(
    file: UploadFile = File(..., description="Image file payload from Flutter camera or gallery"),
) -> APIResponse[ImageUploadResponse]:
    """Securely store waste photograph and return stable access URL."""
    upload_result = await ImageUploadService.save_upload(file)
    return APIResponse[ImageUploadResponse](
        success=True,
        message="Waste photograph uploaded and verified successfully.",
        data=upload_result,
    )


@router.post(
    "/classify-image",
    response_model=APIResponse[WasteClassificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Classify Waste Photo via Vision AI Interface",
    description="Analyzes waste photo using MobileNetV3 interface. Returns statutory category, confidence score, recognized item, and fallback/confirmation flags.",
)
def classify_waste_image(
    request: WasteClassificationRequest,
) -> APIResponse[WasteClassificationResponse]:
    """Analyze image and classify into one of the four statutory streams."""
    classification = WasteClassifierService.classify_waste_image(request)
    return APIResponse[WasteClassificationResponse](
        success=True,
        message=classification.message,
        data=classification,
    )


@router.post(
    "/guidance",
    response_model=APIResponse[HandlingGuidanceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Nuanced Handling Guidance and Action Decision",
    description="Provides scientific composting/handling advice, hygiene precautions, statutory citations, and action routing (home handling vs pickup eligibility).",
)
def get_handling_guidance(
    request: HandlingGuidanceRequest,
) -> APIResponse[HandlingGuidanceResponse]:
    """Retrieve specific handling instructions and testable home vs pickup decision."""
    guidance = WasteGuidanceService.get_guidance(request)
    return APIResponse[HandlingGuidanceResponse](
        success=True,
        message=guidance.action_message,
        data=guidance,
    )


@router.post(
    "/request-pickup",
    response_model=APIResponse[PickupSubmissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Confirmed Pickup Request",
    description="Atomically creates a WasteReport and schedules a PickupRequest after citizen reviews guidance and explicitly confirms pickup. Blocks prohibited streams and prevents duplicate submissions.",
)
def request_waste_pickup(
    request: PickupSubmissionRequest,
    db: Session = Depends(get_db),
) -> APIResponse[PickupSubmissionResponse]:
    """Create waste report and schedule pickup request only after citizen confirmation."""
    submission = WasteWorkflowService.submit_pickup_request(db, request)
    return APIResponse[PickupSubmissionResponse](
        success=True,
        message=submission.message,
        data=submission,
    )

