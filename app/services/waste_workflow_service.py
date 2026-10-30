"""Pillar 1: Waste Workflow Orchestration Service.

Coordinates the transition from guidance confirmation to waste reporting and pickup dispatch:
1. Reuses uploaded image identifier and confirmed stream category
2. Enforces pickup eligibility (rejects infectious or prohibited streams)
3. Prevents duplicate report/pickup generation caused by rapid resubmissions
4. Atomically creates WasteReport and schedules PickupRequest via existing services
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.models.pickup import PickupRequest
from app.models.waste import WasteReport
from app.schemas.pickup import PickupCreate
from app.schemas.waste import WasteReportCreate, WasteStreamEnum
from app.schemas.waste_workflow import (
    ActionOutcomeEnum,
    HandlingGuidanceRequest,
    PickupSubmissionRequest,
    PickupSubmissionResponse,
)
from app.services.pickup_service import PickupService
from app.services.waste_guidance_service import WasteGuidanceService
from app.services.waste_service import WasteService


class WasteWorkflowService:
    """Orchestrates end-to-end doorstep collection submission only after citizen approval."""

    @classmethod
    def submit_pickup_request(
        cls,
        db: Session,
        request: PickupSubmissionRequest,
    ) -> PickupSubmissionResponse:
        """Create waste report and dispatch pickup atomically, preventing duplicates."""
        # 1. Eligibility Check: Verify the stream and item allow ordinary doorstep collection
        guidance_req = HandlingGuidanceRequest(
            category=request.confirmed_category,
            item=request.item,
            is_potentially_infectious=(request.item == "medical_bandages" and "infectious" in request.description.lower()),
        )
        guidance = WasteGuidanceService.get_guidance(guidance_req)

        if guidance.action_outcome == ActionOutcomeEnum.SPECIAL_HANDLING_REQUIRED:
            raise ValidationException(
                f"Ordinary doorstep pickup is prohibited for '{guidance.title}'. "
                f"Reason: {guidance.safety_precautions}. Please refer to: {guidance.statutory_reference or 'Local authority guidelines'}."
            )

        # 2. Duplicate Prevention: Check for identical recent submissions (within 5 minutes)
        five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        duplicate_query = select(WasteReport).where(
            WasteReport.category == request.confirmed_category.value,
            WasteReport.created_at >= five_mins_ago,
        )

        if request.image_url:
            duplicate_query = duplicate_query.where(WasteReport.image_url == request.image_url)
        else:
            duplicate_query = duplicate_query.where(
                WasteReport.latitude == request.latitude,
                WasteReport.longitude == request.longitude,
                WasteReport.description == request.description,
            )

        existing_report = db.execute(duplicate_query.order_by(desc(WasteReport.created_at))).scalars().first()
        if existing_report:
            # Check if this report already has a pickup scheduled
            existing_pickup = db.execute(
                select(PickupRequest).where(PickupRequest.report_id == existing_report.id)
            ).scalars().first()

            if existing_pickup:
                return PickupSubmissionResponse(
                    report_id=existing_report.id,
                    pickup_id=existing_pickup.id,
                    category=existing_report.category,
                    status=existing_pickup.status,
                    collector_name=existing_pickup.collector_name,
                    vehicle_id=existing_pickup.vehicle_id,
                    scheduled_time=existing_pickup.scheduled_time,
                    created_at=existing_pickup.created_at,
                    message="Existing active pickup request detected. Duplicate submission prevented.",
                )

        # 3. Create Waste Report using existing WasteService
        report_in = WasteReportCreate(
            category=request.confirmed_category,
            description=request.description,
            latitude=request.latitude,
            longitude=request.longitude,
            address=request.address,
            ward_number=request.ward_number,
            ecopass_id=request.ecopass_id,
            image_url=request.image_url,
            estimated_weight_kg=request.estimated_weight_kg,
        )
        report = WasteService.create_report(db, report_in)

        # 4. Schedule Pickup Request using existing PickupService
        pickup_in = PickupCreate(
            report_id=report.id,
            collector_id=request.collector_id,
            collector_name=request.collector_name,
            vehicle_id=request.vehicle_id,
            scheduled_time=request.scheduled_time,
        )
        pickup = PickupService.create_pickup(db, pickup_in)

        return PickupSubmissionResponse(
            report_id=report.id,
            pickup_id=pickup.id,
            category=report.category,
            status=pickup.status,
            collector_name=pickup.collector_name,
            vehicle_id=pickup.vehicle_id,
            scheduled_time=pickup.scheduled_time,
            created_at=pickup.created_at,
            message="Doorstep pickup successfully confirmed and scheduled.",
        )

