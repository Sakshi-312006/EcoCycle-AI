"""Pillar 2/3: Construction & Demolition (C&D) Estimation, Material Marketplace & Rubble Recycling Endpoints."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import ValidationException
from app.models.cd_waste import CDWasteReport
from app.schemas.cd_waste import (
    ALLOWED_CD_MATERIAL_STATUSES,
    CDCollectionEventRequest,
    CDDashboardResponse,
    CDDisposalRecordResponse,
    CDEstimateRequest,
    CDEstimateResponse,
    CDFacilityReceiptRequest,
    CDHashVerificationResponse,
    CDMaterialCategoryEnum,
    CDMaterialConditionEnum,
    CDMaterialCreate,
    CDMaterialResponse,
    CDProcessingCompletionRequest,
    CDRubbleCategoryEnum,
    CDVehicleAssignRequest,
    CDVehicleRecommendationResponse,
    CDWasteReportCreate,
    CDWasteReportResponse,
)
from app.schemas.common import APIResponse
from app.schemas.waste_workflow import ImageUploadResponse
from app.services.cd_service import CDService
from app.services.image_upload_service import ImageUploadService

router = APIRouter(prefix="/cd-waste", tags=["Pillar 2: Construction & Demolition (C&D)"])


def _to_cd_report_response(report: CDWasteReport) -> CDWasteReportResponse:
    """Helper to convert CDWasteReport ORM to CDWasteReportResponse."""
    return CDWasteReportResponse(
        id=report.id,
        project_name=report.project_name,
        contractor_name=report.contractor_name,
        contact_phone=report.contact_phone,
        material_category=report.material_category,
        description=report.description,
        image_url=report.image_url,
        latitude=report.latitude,
        longitude=report.longitude,
        address=report.address,
        landmark=report.landmark,
        length_m=report.length_m,
        width_m=report.width_m,
        height_m=report.height_m,
        estimated_volume_m3=report.estimated_volume_m3,
        bulk_density_tonnes_m3=report.bulk_density_tonnes_m3,
        estimated_weight_tonnes=report.estimated_weight_tonnes,
        estimated_weight_kg=round(report.estimated_weight_tonnes * 1000.0, 2),
        status=report.status,
        pickup_id=report.pickup_id,
        assigned_vehicle_id=report.assigned_vehicle_id,
        intended_destination=report.intended_destination,
        destination_facility_name=report.destination_facility_name,
        collected_at=report.collected_at,
        facility_received_at=report.facility_received_at,
        facility_received_weight_tonnes=report.facility_received_weight_tonnes,
        processing_status=report.processing_status,
        processing_completed_at=report.processing_completed_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.post(
    "/upload-image",
    response_model=APIResponse[ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload C&D Rubble or Material Photograph",
    description="Accepts image file (JPEG, PNG, WebP) from Flutter camera/gallery, validates magic bytes and size bounds, stores safely, and returns static URL.",
)
async def upload_cd_image(
    file: UploadFile = File(..., description="Image file payload from camera or gallery"),
) -> APIResponse[ImageUploadResponse]:
    """Securely store C&D photograph and return static URL."""
    upload_result = await ImageUploadService.save_upload(file)
    return APIResponse[ImageUploadResponse](
        success=True,
        message="C&D photograph uploaded and verified successfully.",
        data=upload_result,
    )


# ---------------------------------------------------------------------------
# Stream A: C&D Rubble Reporting, Vehicle Dispatch & Chain of Custody
# ---------------------------------------------------------------------------


@router.post(
    "/reports",
    response_model=APIResponse[CDWasteReportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit C&D Rubble Waste Report",
    description="Submits a construction & demolition waste report for broken rubble (Stream A). Calculates formula-based volume & mass estimate from dimensions or direct volume. Supports optional fleet pickup request.",
)
def create_cd_waste_report(
    report_in: CDWasteReportCreate,
    db: Session = Depends(get_db),
) -> APIResponse[CDWasteReportResponse]:
    """Create a new C&D rubble waste report."""
    report = CDService.create_waste_report(db, report_in)
    return APIResponse[CDWasteReportResponse](
        success=True,
        message=f"C&D rubble report registered with status '{report.status}' ({report.estimated_weight_tonnes} tonnes estimated).",
        data=_to_cd_report_response(report),
    )


@router.get(
    "/reports",
    response_model=APIResponse[List[CDWasteReportResponse]],
    status_code=status.HTTP_200_OK,
    summary="List C&D Rubble Waste Reports",
    description="Retrieve logged C&D rubble reports with optional filters for category and lifecycle status.",
)
def list_cd_waste_reports(
    category: Optional[str] = Query(None, description="Filter by rubble category: broken_concrete, brick_masonry, mixed_cd_rubble, etc."),
    status: Optional[str] = Query(None, description="Filter by status: reported, pickup_requested, assigned, collected, received_at_facility, processing_completed"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[List[CDWasteReportResponse]]:
    """List C&D rubble reports."""
    reports = CDService.list_waste_reports(db, category=category, status=status, limit=limit, offset=offset)
    return APIResponse[List[CDWasteReportResponse]](
        success=True,
        message=f"Retrieved {len(reports)} C&D rubble report(s).",
        data=[_to_cd_report_response(r) for r in reports],
    )


@router.get(
    "/reports/{report_id}",
    response_model=APIResponse[CDWasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get C&D Rubble Waste Report by ID",
    description="Fetch single C&D waste report details and current lifecycle status.",
)
def get_cd_waste_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CDWasteReportResponse]:
    """Retrieve C&D rubble report by ID."""
    report = CDService.get_waste_report_by_id(db, report_id)
    return APIResponse[CDWasteReportResponse](
        success=True,
        message="C&D rubble report retrieved successfully.",
        data=_to_cd_report_response(report),
    )


@router.post(
    "/reports/{report_id}/recommend-vehicle",
    response_model=APIResponse[CDVehicleRecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="Recommend C&D Fleet Vehicle",
    description="Recommends a suitable hydraulic tipper or heavy dump truck based on estimated rubble tonnage.",
)
def recommend_cd_vehicle(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CDVehicleRecommendationResponse]:
    """Recommend eligible C&D hauler."""
    rec = CDService.recommend_vehicle(db, report_id)
    return APIResponse[CDVehicleRecommendationResponse](
        success=True,
        message=rec.reason,
        data=rec,
    )


@router.post(
    "/reports/{report_id}/assign-vehicle",
    response_model=APIResponse[CDWasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign C&D Hauling Vehicle",
    description="Assigns an authorized tipper truck to collect C&D rubble, rejecting incompatible or overloaded vehicles.",
)
def assign_cd_vehicle(
    report_id: uuid.UUID,
    assign_in: CDVehicleAssignRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CDWasteReportResponse]:
    """Assign collection vehicle for C&D rubble."""
    report = CDService.assign_vehicle(db, report_id, assign_in)
    return APIResponse[CDWasteReportResponse](
        success=True,
        message=f"Vehicle '{assign_in.vehicle_id}' assigned successfully.",
        data=_to_cd_report_response(report),
    )


@router.post(
    "/reports/{report_id}/collect",
    response_model=APIResponse[CDWasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Record C&D Site Collection",
    description="Driver or site supervisor confirms rubble loading with photo evidence and scale weight.",
)
def record_cd_collection(
    report_id: uuid.UUID,
    collect_in: CDCollectionEventRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CDWasteReportResponse]:
    """Confirm rubble pickup collection."""
    report = CDService.record_collection(db, report_id, collect_in)
    return APIResponse[CDWasteReportResponse](
        success=True,
        message=f"Collection recorded for C&D rubble ({report.collection_weight_tonnes} tonnes).",
        data=_to_cd_report_response(report),
    )


@router.post(
    "/reports/{report_id}/receive-facility",
    response_model=APIResponse[CDWasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Record Facility Weighbridge Receipt",
    description="Records material arrival at an authorized C&D recycling facility with actual weighbridge scale weight and slip.",
)
def record_cd_facility_receipt(
    report_id: uuid.UUID,
    receipt_in: CDFacilityReceiptRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CDWasteReportResponse]:
    """Record facility intake and weighbridge verification."""
    report = CDService.record_facility_receipt(db, report_id, receipt_in)
    return APIResponse[CDWasteReportResponse](
        success=True,
        message=f"Facility receipt recorded at '{receipt_in.facility_name}' ({receipt_in.received_weight_tonnes} tonnes).",
        data=_to_cd_report_response(report),
    )


@router.post(
    "/reports/{report_id}/complete-processing",
    response_model=APIResponse[CDWasteReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Record Crushing & Recycling Completion",
    description="Records completion of mechanical crushing/screening into recycled aggregate or sand. Issues SHA-256 digital seal.",
)
def complete_cd_processing(
    report_id: uuid.UUID,
    proc_in: CDProcessingCompletionRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CDWasteReportResponse]:
    """Certify crushing and material recovery completion."""
    report = CDService.complete_processing(db, report_id, proc_in)
    return APIResponse[CDWasteReportResponse](
        success=True,
        message=f"Recycling processing completed into '{proc_in.output_material_type}' ({proc_in.output_tonnes} tonnes). Sealed with SHA-256.",
        data=_to_cd_report_response(report),
    )


@router.get(
    "/reports/{report_id}/disposal-record",
    response_model=APIResponse[CDDisposalRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Digital Disposal Record & Chain of Custody",
    description="Retrieve end-to-end traceable digital chain of custody across all stages from generation to recycled output.",
)
def get_cd_disposal_record(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CDDisposalRecordResponse]:
    """Fetch digital chain of custody record."""
    record = CDService.get_disposal_record(db, report_id)
    return APIResponse[CDDisposalRecordResponse](
        success=True,
        message="Digital disposal record compiled successfully.",
        data=record,
    )


@router.get(
    "/reports/{report_id}/verify-hash",
    response_model=APIResponse[CDHashVerificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify C&D Cryptographic Custody Seal",
    description="Verifies the digital SHA-256 chain of custody seal against canonical v2 strengthened or legacy v1 formats. Read-only verification that does not mutate records.",
)
def verify_cd_disposal_hash(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CDHashVerificationResponse]:
    """Verify digital chain of custody seal for C&D rubble disposal."""
    result = CDService.verify_hash(db, report_id)
    return APIResponse[CDHashVerificationResponse](
        success=True,
        message=result.message,
        data=result,
    )


@router.get(
    "/dashboard",
    response_model=APIResponse[CDDashboardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get C&D Recycling & Salvage Dashboard Metrics",
    description="Aggregated operational analytics compiled strictly from stored database records.",
)
def get_cd_dashboard_metrics(
    db: Session = Depends(get_db),
) -> APIResponse[CDDashboardResponse]:
    """Retrieve C&D dashboard metrics."""
    metrics = CDService.get_cd_dashboard(db)
    return APIResponse[CDDashboardResponse](
        success=True,
        message="C&D operational metrics retrieved successfully.",
        data=metrics,
    )


@router.post(
    "/estimates",
    response_model=APIResponse[CDEstimateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Calculate C&D Debris Volume & Weight Estimate",
    description="Formula-based estimation calculating volume (m³) and tonnage from dimensions (L x W x H) or user-supplied volume using standard material bulk densities. Note: Formula-based geometric estimate; not AI or 3D point-cloud scanned.",
)
def calculate_cd_estimate(
    req: CDEstimateRequest,
    db: Session = Depends(get_db),
) -> APIResponse[CDEstimateResponse]:
    """Calculate formula-based debris volume and mass."""
    record = CDService.calculate_estimate(db, req)
    tonnage = round(record.estimated_mass_kg / 1000.0, 2)
    response_data = CDEstimateResponse(
        id=record.id,
        project_name=record.project_name,
        location=record.location,
        material_type=record.material_type,
        length_m=record.length_m,
        width_m=record.width_m,
        height_m=record.height_m,
        estimated_volume_m3=record.estimated_volume_m3,
        material_density_kg_m3=record.material_density_kg_m3,
        estimated_mass_kg=record.estimated_mass_kg,
        estimated_metric_tons=tonnage,
        estimation_method=record.estimation_method,
        disclaimer=record.disclaimer,
        created_at=record.created_at,
    )
    return APIResponse[CDEstimateResponse](
        success=True,
        message=f"Estimated {record.estimated_volume_m3} m³ ({tonnage} metric tons) of {record.material_type} via formula.",
        data=response_data,
    )


@router.get(
    "/estimates",
    response_model=APIResponse[List[CDEstimateResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Historical C&D Estimates",
    description="Retrieve historical volume calculations logged across demolition projects.",
)
def list_cd_estimates(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[List[CDEstimateResponse]]:
    """List historical calculation estimates."""
    records = CDService.list_estimates(db, limit=limit, offset=offset)
    data = [
        CDEstimateResponse(
            id=r.id,
            project_name=r.project_name,
            location=r.location,
            material_type=r.material_type,
            length_m=r.length_m,
            width_m=r.width_m,
            height_m=r.height_m,
            estimated_volume_m3=r.estimated_volume_m3,
            material_density_kg_m3=r.material_density_kg_m3,
            estimated_mass_kg=r.estimated_mass_kg,
            estimated_metric_tons=round(r.estimated_mass_kg / 1000.0, 2),
            estimation_method=r.estimation_method,
            disclaimer=r.disclaimer,
            created_at=r.created_at,
        )
        for r in records
    ]
    return APIResponse[List[CDEstimateResponse]](
        success=True,
        message=f"Retrieved {len(records)} C&D estimate records.",
        data=data,
    )


@router.post(
    "/materials",
    response_model=APIResponse[CDMaterialResponse],
    status_code=status.HTTP_201_CREATED,
    summary="List Reusable Construction Materials",
    description="Post salvageable bricks, tiles, concrete blocks, or timber for reuse/circular recovery.",
)
def create_cd_material(
    mat_in: CDMaterialCreate,
    db: Session = Depends(get_db),
) -> APIResponse[CDMaterialResponse]:
    """Create reusable material listing."""
    listing = CDService.create_material(db, mat_in)
    return APIResponse[CDMaterialResponse](
        success=True,
        message=f"Material listing '{listing.title}' created.",
        data=CDMaterialResponse.model_validate(listing),
    )


@router.get(
    "/materials",
    response_model=APIResponse[List[CDMaterialResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Reusable Construction Materials",
    description="Browse available salvaged materials with category and condition filters.",
)
def list_cd_materials(
    category: Optional[CDMaterialCategoryEnum] = Query(None, description="Material category"),
    condition: Optional[CDMaterialConditionEnum] = Query(None, description="Condition rating"),
    status_filter: Optional[str] = Query(None, alias="status", description="available | reserved | collected"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[List[CDMaterialResponse]]:
    """List materials with filters."""
    cat_val = category.value if category else None
    cond_val = condition.value if condition else None
    status_val = status_filter.strip() if status_filter else None
    listings = CDService.list_materials(
        db,
        category=cat_val,
        condition=cond_val,
        status=status_val,
        limit=limit,
        offset=offset,
    )
    return APIResponse[List[CDMaterialResponse]](
        success=True,
        message=f"Retrieved {len(listings)} material listings.",
        data=[CDMaterialResponse.model_validate(m) for m in listings],
    )


@router.get(
    "/materials/{material_id}",
    response_model=APIResponse[CDMaterialResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Material Listing Details",
    description="Retrieve details of a single reusable material item.",
)
def get_cd_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[CDMaterialResponse]:
    """Retrieve material listing."""
    listing = CDService.get_material_by_id(db, material_id)
    return APIResponse[CDMaterialResponse](
        success=True,
        message="Material listing retrieved.",
        data=CDMaterialResponse.model_validate(listing),
    )


@router.patch(
    "/materials/{material_id}/status",
    response_model=APIResponse[CDMaterialResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Material Availability Status",
    description="Change material status: available -> reserved -> collected.",
)
def update_cd_material_status(
    material_id: uuid.UUID,
    status_value: str = Query(..., description="available | reserved | collected"),
    db: Session = Depends(get_db),
) -> APIResponse[CDMaterialResponse]:
    """Update material status with whitespace stripping and strict validation."""
    normalized_status = status_value.strip() if status_value else ""
    if normalized_status not in ALLOWED_CD_MATERIAL_STATUSES:
        raise ValidationException(
            f"Invalid status '{normalized_status or status_value}'. Allowed values: available, reserved, collected.",
            details=[{
                "field": "status_value",
                "message": "Must be one of: available, reserved, collected",
                "code": "invalid_choice",
            }],
        )

    listing = CDService.update_material_status(db, material_id, normalized_status)
    return APIResponse[CDMaterialResponse](
        success=True,
        message=f"Material status updated to '{listing.status}'.",
        data=CDMaterialResponse.model_validate(listing),
    )
