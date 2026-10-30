"""Pillar 4: Garbage-Pile Detection, Smart Collection Routing & Verified Cleanliness Endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.waste import WasteReport
from app.schemas.common import APIResponse
from app.schemas.waste_workflow import ImageUploadResponse
from app.schemas.garbage_piles import (
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    GarbagePileAssignVehicleRequest,
    GarbagePileCleanupVerifyRequest,
    GarbagePileCleanupVerifyResponse,
    GarbagePileDashboardResponse,
    GarbagePileReportCreate,
    GarbagePileReportResponse,
    VehicleRecommendationResponse,
)
from app.services.garbage_pile_service import GarbagePileService
from app.services.image_upload_service import ImageUploadService

router = APIRouter(prefix="/garbage-piles", tags=["Pillar 4: Garbage-Pile Detection & Cleanliness"])


@router.post(
    "/upload-image",
    response_model=APIResponse[ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Garbage Pile Photograph Evidence",
    description="Accepts JPEG, PNG, or WebP photo payload, validates magic bytes and size bounds, stores securely, and returns static access URL.",
)
async def upload_pile_image(
    file: UploadFile = File(..., description="Photographic evidence from camera or gallery"),
) -> APIResponse[ImageUploadResponse]:
    """Securely upload photographic evidence for illegal dump."""
    upload_res = await ImageUploadService.save_upload(file)
    return APIResponse[ImageUploadResponse](
        success=True,
        message="Garbage pile photo uploaded and validated successfully.",
        data=upload_res,
    )


def _to_pile_response(report: WasteReport) -> GarbagePileReportResponse:
    """Helper to convert WasteReport ORM to GarbagePileReportResponse with dynamic scoring."""
    now = datetime.now(timezone.utc)
    r_time = report.created_at
    if r_time.tzinfo is None:
        r_time = r_time.replace(tzinfo=timezone.utc)
    aging = max(0.0, (now - r_time).total_seconds() / 3600.0)

    severity_breakdown = GarbagePileService.calculate_severity(
        category=report.category,
        aging_hours=aging,
    )

    active_pickup = next((p for p in report.pickups if p.status != "cancelled"), None) if report.pickups else None
    pickup_id = active_pickup.id if active_pickup else None
    assigned_vehicle = active_pickup.vehicle_id if active_pickup else None

    return GarbagePileReportResponse(
        id=report.id,
        category=report.category,
        report_type=report.report_type or "illegal_dump",
        pile_size=None,
        estimated_weight_kg=report.estimated_weight_kg or 40.0,
        latitude=report.latitude,
        longitude=report.longitude,
        address=report.address,
        ward_number=report.ward_number,
        description=report.description,
        image_url=report.image_url,
        status=report.status,
        severity=report.severity or severity_breakdown.priority_tier.value,
        severity_details=severity_breakdown,
        created_at=report.created_at,
        pickup_id=pickup_id,
        assigned_vehicle_id=assigned_vehicle,
    )


@router.post(
    "/check-duplicate",
    response_model=APIResponse[DuplicateCheckResponse],
    status_code=status.HTTP_200_OK,
    summary="Check Proximity for Duplicate Garbage Pile Reports",
    description="Calculates Haversine distance against unresolved reports within configurable radius and lookback window. Masks citizen private identity.",
)
def check_duplicate_piles(
    req: DuplicateCheckRequest,
    db: Session = Depends(get_db),
) -> APIResponse[DuplicateCheckResponse]:
    """Check if a nearby garbage pile has already been logged."""
    dup_res = GarbagePileService.check_duplicates(db=db, req=req)
    return APIResponse[DuplicateCheckResponse](
        success=True,
        message=dup_res.message,
        data=dup_res,
    )


@router.post(
    "/reports",
    response_model=APIResponse[GarbagePileReportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit an Illegal Garbage-Pile Report",
    description="Registers an illegal garbage dump report. Checks proximity for duplicates (returns 409 Conflict unless force_create=True). Scores priority deterministically.",
)
def submit_garbage_pile_report(
    report_in: GarbagePileReportCreate,
    db: Session = Depends(get_db),
) -> APIResponse[GarbagePileReportResponse]:
    """Submit a citizen or worker report of an illegal garbage pile."""
    report = GarbagePileService.create_garbage_pile_report(db=db, report_in=report_in)
    return APIResponse[GarbagePileReportResponse](
        success=True,
        message=f"Garbage pile report logged successfully with severity tier '{report.severity}'.",
        data=_to_pile_response(report),
    )


@router.get(
    "/reports",
    response_model=APIResponse[List[GarbagePileReportResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Illegal Garbage Pile Reports",
    description="Retrieves illegal dump reports with optional filtering by status, category, and severity tier.",
)
def list_garbage_pile_reports(
    status: Optional[str] = Query(None, description="Filter by status (reported, assigned, in_progress, resolved, cancelled)"),
    category: Optional[str] = Query(None, description="Filter by statutory stream (wet_organic, dry_recyclable, sanitary, hazardous)"),
    severity: Optional[str] = Query(None, description="Filter by priority tier (LOW, MEDIUM, HIGH, CRITICAL)"),
    limit: int = Query(50, ge=1, le=100, description="Max items to retrieve"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> APIResponse[List[GarbagePileReportResponse]]:
    """List logged garbage piles."""
    reports = GarbagePileService.list_garbage_piles(
        db=db,
        status=status,
        category=category,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return APIResponse[List[GarbagePileReportResponse]](
        success=True,
        message=f"Retrieved {len(reports)} garbage pile report(s).",
        data=[_to_pile_response(r) for r in reports],
    )


@router.get(
    "/reports/{report_id}",
    response_model=APIResponse[GarbagePileReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Garbage Pile Report Details",
    description="Retrieves a specific illegal dump report including location, current status, severity breakdown, and linked dispatch.",
)
def get_garbage_pile_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[GarbagePileReportResponse]:
    """Fetch garbage pile report by ID."""
    report = GarbagePileService.get_garbage_pile_by_id(db=db, report_id=report_id)
    return APIResponse[GarbagePileReportResponse](
        success=True,
        message="Garbage pile report retrieved successfully.",
        data=_to_pile_response(report),
    )


@router.post(
    "/reports/{report_id}/recommend-vehicle",
    response_model=APIResponse[VehicleRecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="Recommend Eligible Fleet Vehicle for Garbage Pile",
    description="Evaluates candidate vehicles based on waste stream certification, compartment capacity limits, and current active load.",
)
def recommend_vehicle_for_pile(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[VehicleRecommendationResponse]:
    """Recommend an eligible vehicle from the municipal fleet."""
    rec = GarbagePileService.recommend_vehicle(db=db, report_id=report_id)
    return APIResponse[VehicleRecommendationResponse](
        success=True,
        message=rec.reason,
        data=rec,
    )


@router.post(
    "/reports/{report_id}/assign-vehicle",
    response_model=APIResponse[GarbagePileReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Collection Vehicle to Garbage Pile",
    description="Assigns a vehicle to collect the pile, creating or updating a PickupRequest dispatch.",
)
def assign_vehicle_to_pile(
    report_id: uuid.UUID,
    assign_in: GarbagePileAssignVehicleRequest,
    db: Session = Depends(get_db),
) -> APIResponse[GarbagePileReportResponse]:
    """Assign or dispatch a collection vehicle."""
    report, _ = GarbagePileService.assign_vehicle(db=db, report_id=report_id, assign_in=assign_in)
    return APIResponse[GarbagePileReportResponse](
        success=True,
        message=f"Vehicle '{assign_in.vehicle_id}' assigned successfully.",
        data=_to_pile_response(report),
    )


@router.post(
    "/reports/{report_id}/verify-cleanup",
    response_model=APIResponse[GarbagePileCleanupVerifyResponse],
    status_code=status.HTTP_200_OK,
    summary="Certify Garbage Pile Cleanup with EcoProof Verification",
    description="Field verifier submits after-photo and scale weight. Issues cryptographic SHA-256 integrity seal. Awards 0 reporting credits.",
)
def verify_pile_cleanup(
    report_id: uuid.UUID,
    verify_in: GarbagePileCleanupVerifyRequest,
    db: Session = Depends(get_db),
) -> APIResponse[GarbagePileCleanupVerifyResponse]:
    """Verify site clearance and issue EcoProof receipt."""
    verify_res = GarbagePileService.verify_cleanup(db=db, report_id=report_id, verify_in=verify_in)
    return APIResponse[GarbagePileCleanupVerifyResponse](
        success=True,
        message="Cleanup verified and sealed with cryptographic SHA-256 integrity hash.",
        data=verify_res,
    )


@router.get(
    "/dashboard",
    response_model=APIResponse[GarbagePileDashboardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Municipal Illegal Dumping & Cleanliness Analytics",
    description="Aggregated operational analytics compiled strictly from stored database records.",
)
def get_garbage_pile_dashboard(
    db: Session = Depends(get_db),
) -> APIResponse[GarbagePileDashboardResponse]:
    """Retrieve municipal cleanliness dashboard metrics."""
    dashboard = GarbagePileService.get_dashboard_summary(db=db)
    return APIResponse[GarbagePileDashboardResponse](
        success=True,
        message="Municipal illegal dumping metrics calculated successfully.",
        data=dashboard,
    )
