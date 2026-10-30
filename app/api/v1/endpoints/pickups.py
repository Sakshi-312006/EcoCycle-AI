"""Pillar 2: Pickup Requests and EcoProof Verification REST Endpoints."""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.pickup import (
    CollectionVerificationCreate,
    PickupCreate,
    PickupQRCodeResponse,
    PickupResponse,
    PickupStatusEnum,
    PickupStatusUpdate,
    PickupVerificationStatusResponse,
    VerificationResponse,
)
from app.services.pickup_service import PickupService

router = APIRouter(prefix="/pickups", tags=["Pillar 2: Pickups & EcoProof Verification"])


@router.post(
    "",
    response_model=APIResponse[PickupResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Schedule Pickup Request",
    description="Create an operational collection pickup dispatch linked to an existing waste report.",
)
def create_pickup(
    pickup_in: PickupCreate,
    db: Session = Depends(get_db),
) -> APIResponse[PickupResponse]:
    """Schedule a collection pickup."""
    pickup = PickupService.create_pickup(db, pickup_in)
    return APIResponse[PickupResponse](
        success=True,
        message=f"Pickup scheduled with status '{pickup.status}'.",
        data=PickupResponse.model_validate(pickup),
    )


@router.get(
    "",
    response_model=APIResponse[List[PickupResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Pickup Requests",
    description="Retrieve collection pickups with status and collector filters.",
)
def list_pickups(
    status_filter: Optional[PickupStatusEnum] = Query(None, alias="status", description="Filter by status"),
    collector_id: Optional[str] = Query(None, description="Filter by assigned collector"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> APIResponse[List[PickupResponse]]:
    """List collection pickups."""
    stat_val = status_filter.value if status_filter else None
    pickups = PickupService.list_pickups(
        db,
        status=stat_val,
        collector_id=collector_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse[List[PickupResponse]](
        success=True,
        message=f"Retrieved {len(pickups)} pickup requests.",
        data=[PickupResponse.model_validate(p) for p in pickups],
    )


@router.get(
    "/{pickup_id}",
    response_model=APIResponse[PickupResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Pickup Details",
    description="Retrieve pickup by ID including verification receipt if completed.",
)
def get_pickup(
    pickup_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[PickupResponse]:
    """Retrieve pickup details."""
    pickup = PickupService.get_pickup_by_id(db, pickup_id)
    return APIResponse[PickupResponse](
        success=True,
        message="Pickup retrieved.",
        data=PickupResponse.model_validate(pickup),
    )


@router.patch(
    "/{pickup_id}/status",
    response_model=APIResponse[PickupResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Pickup Status",
    description="Progress pickup status (scheduled -> in_progress -> cancelled).",
)
def update_pickup_status(
    pickup_id: uuid.UUID,
    update_in: PickupStatusUpdate,
    db: Session = Depends(get_db),
) -> APIResponse[PickupResponse]:
    """Update pickup operational status."""
    pickup = PickupService.update_status(db, pickup_id, update_in)
    return APIResponse[PickupResponse](
        success=True,
        message=f"Pickup transitioned to status '{pickup.status}'.",
        data=PickupResponse.model_validate(pickup),
    )


@router.post(
    "/{pickup_id}/verify",
    response_model=APIResponse[VerificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Verify Collection & Issue EcoProof Receipt",
    description="Confirm waste handover with actual weight, generate a cryptographic SHA-256 integrity hash, and disburse EcoCredits to the household EcoPass.",
)
def verify_collection(
    pickup_id: uuid.UUID,
    verify_in: CollectionVerificationCreate,
    db: Session = Depends(get_db),
) -> APIResponse[VerificationResponse]:
    """Issue verified EcoProof collection receipt with SHA-256 integrity digest."""
    verification = PickupService.verify_collection(db, pickup_id, verify_in)
    return APIResponse[VerificationResponse](
        success=True,
        message=f"Collection verified! Awarded {verification.ecocredits_awarded} EcoCredits. EcoProof integrity receipt issued.",
        data=VerificationResponse.model_validate(verification),
    )


@router.get(
    "/{pickup_id}/qr",
    response_model=APIResponse[PickupQRCodeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get EcoProof Verification QR Code",
    description="Generates an in-memory QR code encoding the public backend verification URL. Contains no PII, secrets, or OTPs.",
)
def get_pickup_qr_code(
    pickup_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> APIResponse[PickupQRCodeResponse]:
    """Retrieve QR code for EcoProof pickup verification."""
    base_url = str(request.base_url).rstrip("/")
    result = PickupService.generate_qr_code(db, pickup_id, base_url=base_url)
    return APIResponse[PickupQRCodeResponse](
        success=True,
        message="EcoProof verification QR code generated successfully.",
        data=result,
    )


@router.get(
    "/{pickup_id}/verify-receipt",
    response_model=APIResponse[PickupVerificationStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify EcoProof Collection Receipt",
    description="Validates cryptographic SHA-256 seal against canonical record values. Public verification endpoint encoded in QR.",
)
def verify_pickup_receipt(
    pickup_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> APIResponse[PickupVerificationStatusResponse]:
    """Verify digital chain of custody seal for waste pickup."""
    result = PickupService.verify_receipt_hash(db, pickup_id)
    return APIResponse[PickupVerificationStatusResponse](
        success=True,
        message=result.message,
        data=result,
    )
