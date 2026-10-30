"""Pillar 3: Construction & Demolition (C&D) Estimation, Material Salvage & Rubble Recycling Service."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, EntityNotFoundException, ValidationException
from app.core.security import generate_sha256_hash
from app.models.cd_waste import CDEstimateRecord, CDMaterialListing, CDWasteReport
from app.models.pickup import PickupRequest
from app.models.waste import WasteReport
from app.schemas.cd_waste import (
    ALLOWED_CD_MATERIAL_STATUSES,
    CD_BULK_DENSITIES_TONNES_M3,
    CDCollectionEventRequest,
    CDDashboardResponse,
    CDDisposalRecordResponse,
    CDEstimateRequest,
    CDFacilityReceiptRequest,
    CDHashVerificationResponse,
    CDMaterialCreate,
    CDProcessingCompletionRequest,
    CDVehicleAssignRequest,
    CDVehicleRecommendationResponse,
    CDWasteReportCreate,
)

# Standard density dictionary in kg/m³
MATERIAL_DENSITIES = {
    "concrete_rubble": 1500.0,
    "brick_masonry": 1800.0,
    "mixed_cd": 1300.0,
    "tiles_ceramic": 1600.0,
    "soil_excavation": 1400.0,
}

# C&D Transport Fleet definitions
CD_FLEET_VEHICLES = [
    {
        "vehicle_id": "HEAVY-TIPPER-04",
        "vehicle_type": "heavy_tipper",
        "max_capacity_tonnes": 1.0,
        "authorized": True,
        "description": "Compact municipal tipper suitable for small rubble batches up to 1.0 tonne.",
    },
    {
        "vehicle_id": "TIPPER-TRUCK-05",
        "vehicle_type": "medium_tipper",
        "max_capacity_tonnes": 5.0,
        "authorized": True,
        "description": "Standard 5-tonne hydraulic tipper truck for bulk construction & demolition rubble.",
    },
    {
        "vehicle_id": "DUMP-TRUCK-06",
        "vehicle_type": "heavy_dump_truck",
        "max_capacity_tonnes": 12.0,
        "authorized": True,
        "description": "Heavy 12-tonne commercial demolition dump truck.",
    },
]

INCOMPATIBLE_VEHICLES = {
    "ECO-CART-01": "Light electric 3-wheeler cart (max 80kg) is strictly unauthorized for heavy C&D rubble.",
    "TRUCK-COMPACTOR-02": "Hydraulic compactor truck is strictly incompatible with rigid concrete and masonry rubble (causes hydraulic blade damage).",
    "HAZMAT-VAN-03": "Specialized biohazard response van is unauthorized for construction rubble.",
}


class CDService:
    """Service handling geometric formula C&D estimation, material salvage, and Stream A rubble recycling."""

    @staticmethod
    def calculate_estimate(db: Session, req: CDEstimateRequest) -> CDEstimateRecord:
        """Compute formula-based geometric volume and bulk mass estimate."""
        if req.length_m and req.width_m and req.height_m:
            volume_m3 = round(req.length_m * req.width_m * req.height_m, 3)
        else:
            volume_m3 = round(req.user_volume_m3 or 0.0, 3)

        density = MATERIAL_DENSITIES.get(req.material_type.value, 1400.0)
        mass_kg = round(volume_m3 * density, 2)

        record = CDEstimateRecord(
            project_name=req.project_name,
            location=req.location,
            material_type=req.material_type.value,
            length_m=req.length_m,
            width_m=req.width_m,
            height_m=req.height_m,
            estimated_volume_m3=volume_m3,
            material_density_kg_m3=density,
            estimated_mass_kg=mass_kg,
            estimation_method="formula_geometric_bounding_box",
            disclaimer="Formula-based estimate using geometric dimensions and standard material density. Not AI or 3D point-cloud scanned.",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def list_estimates(db: Session, limit: int = 50, offset: int = 0) -> List[CDEstimateRecord]:
        """Fetch historical calculation estimates."""
        return list(
            db.execute(select(CDEstimateRecord).order_by(desc(CDEstimateRecord.created_at)).limit(limit).offset(offset))
            .scalars()
            .all()
        )

    @staticmethod
    def create_material(db: Session, mat_in: CDMaterialCreate) -> CDMaterialListing:
        """Register reusable salvageable building material listing."""
        listing = CDMaterialListing(
            title=mat_in.title,
            material_category=mat_in.material_category.value,
            quantity=mat_in.quantity,
            unit=mat_in.unit,
            condition=mat_in.condition.value,
            price_inr=mat_in.price_inr,
            location=mat_in.location,
            contact_phone=mat_in.contact_phone,
            description=mat_in.description,
            image_url=mat_in.image_url,
            status="available",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def get_material_by_id(db: Session, material_id: uuid.UUID) -> CDMaterialListing:
        """Fetch material listing by ID."""
        listing = db.execute(select(CDMaterialListing).where(CDMaterialListing.id == material_id)).scalar_one_or_none()
        if not listing:
            raise EntityNotFoundException("CDMaterialListing", str(material_id))
        return listing

    @staticmethod
    def list_materials(
        db: Session,
        category: Optional[str] = None,
        condition: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CDMaterialListing]:
        """List salvageable materials with optional filters."""
        query = select(CDMaterialListing).order_by(desc(CDMaterialListing.created_at))
        if category:
            query = query.where(CDMaterialListing.material_category == category)
        if condition:
            query = query.where(CDMaterialListing.condition == condition)
        if status:
            query = query.where(CDMaterialListing.status == status)

        return list(db.execute(query.limit(limit).offset(offset)).scalars().all())

    @staticmethod
    def update_material_status(db: Session, material_id: uuid.UUID, status: str) -> CDMaterialListing:
        """Update material listing availability status."""
        normalized_status = status.strip() if status else ""
        if normalized_status not in ALLOWED_CD_MATERIAL_STATUSES:
            raise ValidationException(
                f"Invalid status '{normalized_status or status}'. Allowed values: available, reserved, collected.",
                details=[{
                    "field": "status_value",
                    "message": "Must be one of: available, reserved, collected",
                    "code": "invalid_choice",
                }],
            )

        listing = CDService.get_material_by_id(db, material_id)
        listing.status = normalized_status
        db.commit()
        db.refresh(listing)
        return listing

    # -----------------------------------------------------------------------
    # Stream A: Rubble Reporting, Vehicle Recommendation & Chain of Custody
    # -----------------------------------------------------------------------

    @classmethod
    def create_waste_report(cls, db: Session, report_in: CDWasteReportCreate) -> CDWasteReport:
        """Register a C&D rubble report with formula-based volumetric estimation and optional pickup."""
        # 1. Calculate volume
        if report_in.length_m and report_in.width_m and report_in.height_m:
            volume_m3 = round(report_in.length_m * report_in.width_m * report_in.height_m, 3)
        else:
            volume_m3 = round(report_in.user_volume_m3 or 0.0, 3)

        # 2. Bulk density & mass calculation
        cat_key = report_in.material_category.value
        density = report_in.custom_density_tonnes_m3 or CD_BULK_DENSITIES_TONNES_M3.get(cat_key, 1.5)
        weight_tonnes = round(volume_m3 * density, 2)
        weight_kg = round(weight_tonnes * 1000.0, 2)

        # 3. Create backing WasteReport for fleet and pickup compatibility
        waste_report = WasteReport(
            category="dry_recyclable",
            description=f"C&D Rubble: {cat_key} - {report_in.project_name}. {report_in.description}",
            image_url=report_in.image_url,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            address=report_in.address,
            ward_number=report_in.landmark,
            estimated_weight_kg=weight_kg,
            report_type="cd_waste",
            severity="MEDIUM",
            status="reported",
        )
        db.add(waste_report)
        db.flush()

        # 4. Optional pickup request
        pickup_id = None
        initial_status = "reported"
        if report_in.request_pickup:
            pickup = PickupRequest(
                report_id=waste_report.id,
                status="scheduled",
            )
            db.add(pickup)
            db.flush()
            pickup_id = pickup.id
            initial_status = "pickup_requested"
            waste_report.status = "assigned"

        # 5. Create CDWasteReport record
        cd_report = CDWasteReport(
            project_name=report_in.project_name,
            contractor_name=report_in.contractor_name,
            contact_phone=report_in.contact_phone,
            material_category=cat_key,
            description=report_in.description,
            image_url=report_in.image_url,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            address=report_in.address,
            landmark=report_in.landmark,
            length_m=report_in.length_m,
            width_m=report_in.width_m,
            height_m=report_in.height_m,
            user_volume_m3=report_in.user_volume_m3,
            estimated_volume_m3=volume_m3,
            bulk_density_tonnes_m3=density,
            estimated_weight_tonnes=weight_tonnes,
            status=initial_status,
            waste_report_id=waste_report.id,
            pickup_id=pickup_id,
            intended_destination=report_in.intended_destination or "Authorized C&D Recycling Facility",
        )
        db.add(cd_report)
        db.commit()
        db.refresh(cd_report)
        return cd_report

    @classmethod
    def get_waste_report_by_id(cls, db: Session, report_id: uuid.UUID) -> CDWasteReport:
        """Fetch C&D waste report by ID."""
        report = db.execute(select(CDWasteReport).where(CDWasteReport.id == report_id)).scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("CDWasteReport", str(report_id))
        return report

    @classmethod
    def list_waste_reports(
        cls,
        db: Session,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CDWasteReport]:
        """List C&D waste reports with optional category and status filters."""
        query = select(CDWasteReport).order_by(desc(CDWasteReport.created_at))
        if category:
            query = query.where(CDWasteReport.material_category == category)
        if status:
            query = query.where(CDWasteReport.status == status)

        return list(db.execute(query.limit(limit).offset(offset)).scalars().all())

    @classmethod
    def recommend_vehicle(cls, db: Session, report_id: uuid.UUID) -> CDVehicleRecommendationResponse:
        """Evaluate bulk C&D rubble volume and weight to recommend an appropriate tipper truck."""
        report = cls.get_waste_report_by_id(db, report_id)
        weight_tonnes = report.estimated_weight_tonnes

        # Evaluate available C&D haulers
        for v in CD_FLEET_VEHICLES:
            if weight_tonnes <= v["max_capacity_tonnes"]:
                return CDVehicleRecommendationResponse(
                    report_id=report.id,
                    material_category=report.material_category,
                    estimated_weight_tonnes=weight_tonnes,
                    recommended_vehicle_id=v["vehicle_id"],
                    vehicle_type=v["vehicle_type"],
                    is_assigned=True,
                    reason=(
                        f"Vehicle '{v['vehicle_id']}' ({v['vehicle_type']}) has a capacity of "
                        f"{v['max_capacity_tonnes']} tonnes, which accommodates the estimated {weight_tonnes:.2f} tonnes of rubble."
                    ),
                    max_capacity_tonnes=v["max_capacity_tonnes"],
                )

        # Exceeds maximum vehicle payload
        return CDVehicleRecommendationResponse(
            report_id=report.id,
            material_category=report.material_category,
            estimated_weight_tonnes=weight_tonnes,
            recommended_vehicle_id=None,
            vehicle_type=None,
            is_assigned=False,
            reason=(
                f"Estimated debris mass ({weight_tonnes:.2f} tonnes) exceeds single-vehicle payload limit (12.0 tonnes). "
                f"Multi-truck dispatch or heavy articulated hauler required."
            ),
            max_capacity_tonnes=None,
        )

    @classmethod
    def assign_vehicle(cls, db: Session, report_id: uuid.UUID, assign_in: CDVehicleAssignRequest) -> CDWasteReport:
        """Assign an eligible C&D tipper truck to collect rubble, verifying compatibility and capacity."""
        report = cls.get_waste_report_by_id(db, report_id)
        v_id = assign_in.vehicle_id

        # Check incompatible vehicles
        if v_id in INCOMPATIBLE_VEHICLES:
            raise ValidationException(
                f"Incompatible vehicle assignment: {INCOMPATIBLE_VEHICLES[v_id]}",
                details=[{"vehicle_id": v_id, "reason": INCOMPATIBLE_VEHICLES[v_id]}],
            )

        # Check vehicle capacity limits
        matching_v = next((v for v in CD_FLEET_VEHICLES if v["vehicle_id"] == v_id), None)
        if matching_v and report.estimated_weight_tonnes > matching_v["max_capacity_tonnes"]:
            raise ValidationException(
                f"Capacity overflow: Vehicle '{v_id}' maximum capacity is {matching_v['max_capacity_tonnes']} tonnes; "
                f"cannot carry estimated load of {report.estimated_weight_tonnes:.2f} tonnes.",
                details=[{
                    "vehicle_id": v_id,
                    "max_capacity_tonnes": matching_v["max_capacity_tonnes"],
                    "required_tonnes": report.estimated_weight_tonnes,
                }],
            )

        # Update or create linked PickupRequest
        if report.pickup_id:
            pickup = db.get(PickupRequest, report.pickup_id)
            if pickup:
                pickup.vehicle_id = v_id
                pickup.collector_id = assign_in.collector_id
                pickup.collector_name = assign_in.collector_name
                pickup.scheduled_time = assign_in.scheduled_time
                pickup.status = "scheduled"
        else:
            pickup = PickupRequest(
                report_id=report.waste_report_id,
                vehicle_id=v_id,
                collector_id=assign_in.collector_id,
                collector_name=assign_in.collector_name,
                scheduled_time=assign_in.scheduled_time,
                status="scheduled",
            )
            db.add(pickup)
            db.flush()
            report.pickup_id = pickup.id

        report.assigned_vehicle_id = v_id
        report.status = "assigned"
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def record_collection(cls, db: Session, report_id: uuid.UUID, collect_in: CDCollectionEventRequest) -> CDWasteReport:
        """Record site collection of rubble with photo evidence and scale weight."""
        report = cls.get_waste_report_by_id(db, report_id)

        if report.status not in ["assigned", "pickup_requested", "reported"]:
            raise ConflictException(
                f"Cannot record collection for C&D report in status '{report.status}'. Must be assigned or requested."
            )

        report.collected_at = datetime.now(timezone.utc)
        report.collector_id = collect_in.collector_id
        report.collection_evidence_image_url = collect_in.collection_evidence_image_url
        report.collection_notes = collect_in.notes
        report.collection_weight_tonnes = collect_in.actual_weight_tonnes or report.estimated_weight_tonnes
        report.status = "collected"

        # Synchronize linked WasteReport
        if report.waste_report_id:
            waste_report = db.get(WasteReport, report.waste_report_id)
            if waste_report and waste_report.id == report.waste_report_id and waste_report.report_type == "cd_waste":
                waste_report.status = "collected"

        # Synchronize linked PickupRequest
        if report.pickup_id:
            pickup = db.get(PickupRequest, report.pickup_id)
            if pickup:
                pickup.status = "completed"

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def record_facility_receipt(cls, db: Session, report_id: uuid.UUID, receipt_in: CDFacilityReceiptRequest) -> CDWasteReport:
        """Record weighbridge receipt at an authorized C&D recycling facility."""
        report = cls.get_waste_report_by_id(db, report_id)

        if report.status in ["received_at_facility", "processing_completed"]:
            raise ConflictException("Material has already been received at the facility.")

        if report.status != "collected":
            raise ValidationException(
                f"Cannot record facility receipt before collection is completed. Current status: '{report.status}'."
            )

        report.destination_facility_name = receipt_in.facility_name
        report.facility_received_at = datetime.now(timezone.utc)
        report.facility_received_weight_tonnes = receipt_in.received_weight_tonnes
        report.weighbridge_ticket_id = receipt_in.weighbridge_ticket_id
        report.weighbridge_slip_url = receipt_in.weighbridge_slip_url
        report.facility_notes = receipt_in.notes
        report.status = "received_at_facility"

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def generate_canonical_custody_payload_v2(
        cls,
        report_id: uuid.UUID | str,
        material_category: str,
        estimated_weight_tonnes: float,
        destination_facility_name: str,
        facility_received_weight_tonnes: float,
        output_material_type: str,
        output_tonnes: float,
        completed_at: datetime,
    ) -> str:
        """Deterministic canonical v2 custody payload for cryptographic sealing."""
        if completed_at.tzinfo is None:
            completed_at_utc = completed_at.replace(tzinfo=timezone.utc)
        else:
            completed_at_utc = completed_at.astimezone(timezone.utc)
        dt_iso = completed_at_utc.isoformat()

        cat = str(material_category).strip().lower()
        facility = str(destination_facility_name).strip()
        out_type = str(output_material_type).strip().lower()
        est_wt = f"{float(estimated_weight_tonnes):.2f}"
        rec_wt = f"{float(facility_received_weight_tonnes):.2f}"
        out_wt = f"{float(output_tonnes):.2f}"

        return (
            f"v2|cd_disposal:{str(report_id)}|"
            f"category:{cat}|"
            f"estimated_weight_tonnes:{est_wt}|"
            f"facility:{facility}|"
            f"received_weight_tonnes:{rec_wt}|"
            f"output_type:{out_type}|"
            f"output_tonnes:{out_wt}|"
            f"completed_at:{dt_iso}"
        )

    @classmethod
    def generate_legacy_custody_payload_v1(
        cls,
        report_id: uuid.UUID | str,
        destination_facility_name: Optional[str],
        facility_received_weight_tonnes: Optional[float],
        output_material_type: Optional[str],
        output_tonnes: Optional[float],
        completed_at: datetime,
        force_utc_tz: bool = True,
    ) -> str:
        """Legacy v1 payload matching original complete_processing seal format."""
        if force_utc_tz:
            dt = completed_at.replace(tzinfo=timezone.utc) if completed_at.tzinfo is None else completed_at.astimezone(timezone.utc)
        else:
            dt = completed_at.replace(tzinfo=None)
        dt_iso = dt.isoformat()
        rec_wt = f"{float(facility_received_weight_tonnes):.2f}" if facility_received_weight_tonnes is not None else "0.00"
        out_wt = f"{float(output_tonnes):.2f}" if output_tonnes is not None else "0.00"
        return (
            f"cd_disposal:{str(report_id)}|"
            f"facility:{destination_facility_name or ''}|"
            f"received_weight_tonnes:{rec_wt}|"
            f"output_type:{output_material_type or ''}|"
            f"output_tonnes:{out_wt}|"
            f"completed_at:{dt_iso}"
        )

    @classmethod
    def complete_processing(cls, db: Session, report_id: uuid.UUID, proc_in: CDProcessingCompletionRequest) -> CDWasteReport:
        """Record crushing and screening completion into recycled aggregate with SHA-256 digital seal."""
        report = cls.get_waste_report_by_id(db, report_id)

        if report.status == "processing_completed":
            raise ConflictException("Processing has already been completed for this material batch.")

        if report.status != "received_at_facility":
            raise ValidationException(
                f"Cannot complete processing before facility receipt is recorded. Current status: '{report.status}'."
            )

        completed_at = datetime.now(timezone.utc)
        report.processing_status = "completed"
        report.processing_completed_at = completed_at
        report.processed_output_type = proc_in.output_material_type
        report.processed_output_tonnes = proc_in.output_tonnes
        report.processing_evidence = proc_in.processing_evidence
        report.status = "processing_completed"

        # Generate cryptographic SHA-256 chain-of-custody seal (Canonical v2)
        seal_payload = cls.generate_canonical_custody_payload_v2(
            report_id=report.id,
            material_category=report.material_category,
            estimated_weight_tonnes=report.estimated_weight_tonnes,
            destination_facility_name=report.destination_facility_name or "",
            facility_received_weight_tonnes=report.facility_received_weight_tonnes or 0.0,
            output_material_type=proc_in.output_material_type,
            output_tonnes=proc_in.output_tonnes,
            completed_at=completed_at,
        )
        report.integrity_hash = generate_sha256_hash(seal_payload)

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def verify_hash(cls, db: Session, report_id: uuid.UUID) -> CDHashVerificationResponse:
        """Verify digital chain of custody seal against canonical v2 strengthened or legacy v1 formats.

        Read-only verification; does not mutate records.
        """
        report = cls.get_waste_report_by_id(db, report_id)

        # Check if record has been sealed
        if not report.integrity_hash or report.status != "processing_completed" or not report.processing_completed_at:
            return CDHashVerificationResponse(
                report_id=report.id,
                is_valid=False,
                status="unsealed",
                hash_format=None,
                stored_hash=report.integrity_hash,
                computed_hash=None,
                message="Report processing is not completed or has not been sealed with a cryptographic hash.",
            )

        completed_at = report.processing_completed_at

        # 1. Check Canonical v2 format
        v2_payload = cls.generate_canonical_custody_payload_v2(
            report_id=report.id,
            material_category=report.material_category,
            estimated_weight_tonnes=report.estimated_weight_tonnes,
            destination_facility_name=report.destination_facility_name or "",
            facility_received_weight_tonnes=report.facility_received_weight_tonnes or 0.0,
            output_material_type=report.processed_output_type or "",
            output_tonnes=report.processed_output_tonnes or 0.0,
            completed_at=completed_at,
        )
        v2_hash = generate_sha256_hash(v2_payload)
        if report.integrity_hash == v2_hash:
            return CDHashVerificationResponse(
                report_id=report.id,
                is_valid=True,
                status="verified",
                hash_format="v2_strengthened",
                stored_hash=report.integrity_hash,
                computed_hash=v2_hash,
                message="Cryptographic custody seal verified successfully against canonical v2 strengthened format.",
            )

        # 2. Check Legacy v1 format (checking both UTC and naive ISO representation)
        v1_payload = cls.generate_legacy_custody_payload_v1(
            report_id=report.id,
            destination_facility_name=report.destination_facility_name,
            facility_received_weight_tonnes=report.facility_received_weight_tonnes,
            output_material_type=report.processed_output_type,
            output_tonnes=report.processed_output_tonnes,
            completed_at=completed_at,
            force_utc_tz=True,
        )
        v1_hash = generate_sha256_hash(v1_payload)
        if report.integrity_hash == v1_hash:
            return CDHashVerificationResponse(
                report_id=report.id,
                is_valid=True,
                status="verified",
                hash_format="v1_legacy",
                stored_hash=report.integrity_hash,
                computed_hash=v1_hash,
                message="Cryptographic custody seal verified successfully against legacy v1 format.",
            )

        v1_naive_payload = cls.generate_legacy_custody_payload_v1(
            report_id=report.id,
            destination_facility_name=report.destination_facility_name,
            facility_received_weight_tonnes=report.facility_received_weight_tonnes,
            output_material_type=report.processed_output_type,
            output_tonnes=report.processed_output_tonnes,
            completed_at=completed_at,
            force_utc_tz=False,
        )
        v1_naive_hash = generate_sha256_hash(v1_naive_payload)
        if report.integrity_hash == v1_naive_hash:
            return CDHashVerificationResponse(
                report_id=report.id,
                is_valid=True,
                status="verified",
                hash_format="v1_legacy",
                stored_hash=report.integrity_hash,
                computed_hash=v1_naive_hash,
                message="Cryptographic custody seal verified successfully against legacy v1 format.",
            )

        # 3. Hash mismatch / record tampering detected
        return CDHashVerificationResponse(
            report_id=report.id,
            is_valid=False,
            status="mismatch",
            hash_format=None,
            stored_hash=report.integrity_hash,
            computed_hash=v2_hash,
            message="Cryptographic custody seal mismatch. Record data may have been altered or tampered with.",
        )

    @classmethod
    def get_disposal_record(cls, db: Session, report_id: uuid.UUID) -> CDDisposalRecordResponse:
        """Compile complete digital disposal record and chain of custody with variance analysis."""
        report = cls.get_waste_report_by_id(db, report_id)

        variance = None
        if report.facility_received_weight_tonnes is not None:
            variance = round(report.facility_received_weight_tonnes - report.estimated_weight_tonnes, 2)

        return CDDisposalRecordResponse(
            report_id=report.id,
            project_name=report.project_name,
            location=f"{report.address}, {report.landmark or ''}".strip(", "),
            material_category=report.material_category,
            estimated_volume_m3=report.estimated_volume_m3,
            bulk_density_tonnes_m3=report.bulk_density_tonnes_m3,
            estimated_weight_tonnes=report.estimated_weight_tonnes,
            status=report.status,
            pickup_id=report.pickup_id,
            assigned_vehicle_id=report.assigned_vehicle_id,
            collected_at=report.collected_at,
            collector_id=report.collector_id,
            collection_evidence_image_url=report.collection_evidence_image_url,
            collection_weight_tonnes=report.collection_weight_tonnes,
            intended_destination=report.intended_destination,
            facility_name=report.destination_facility_name,
            facility_received_at=report.facility_received_at,
            facility_received_weight_tonnes=report.facility_received_weight_tonnes,
            weighbridge_ticket_id=report.weighbridge_ticket_id,
            weight_discrepancy_tonnes=variance,
            processing_status=report.processing_status,
            processing_completed_at=report.processing_completed_at,
            processed_output_type=report.processed_output_type,
            processed_output_tonnes=report.processed_output_tonnes,
            processing_evidence=report.processing_evidence,
            integrity_hash=report.integrity_hash,
        )

    @classmethod
    def get_cd_dashboard(cls, db: Session) -> CDDashboardResponse:
        """Compile aggregated operational C&D metrics directly from stored database rows."""
        now = datetime.now(timezone.utc)

        # 1. Rubble reports
        reports = list(db.execute(select(CDWasteReport)).scalars().all())
        total_reports = len(reports)

        reports_by_mat: Dict[str, int] = {}
        disposal_stages: Dict[str, int] = {
            "reported": 0,
            "pickup_requested": 0,
            "assigned": 0,
            "collected": 0,
            "received_at_facility": 0,
            "processing_completed": 0,
        }
        total_est_vol = 0.0
        total_est_weight = 0.0
        total_coll_weight = 0.0
        awaiting_receipt_weight = 0.0
        awaiting_proc_weight = 0.0
        total_proc_weight = 0.0

        total_pickups = 0
        pickups_by_status: Dict[str, int] = {}

        for r in reports:
            reports_by_mat[r.material_category] = reports_by_mat.get(r.material_category, 0) + 1
            if r.status in disposal_stages:
                disposal_stages[r.status] += 1

            total_est_vol += r.estimated_volume_m3
            total_est_weight += r.estimated_weight_tonnes

            if r.pickup_id:
                total_pickups += 1

            if r.status in ["collected", "received_at_facility", "processing_completed"]:
                if r.collection_weight_tonnes:
                    total_coll_weight += r.collection_weight_tonnes

            if r.status == "collected":
                awaiting_receipt_weight += (r.collection_weight_tonnes or r.estimated_weight_tonnes)

            if r.status == "received_at_facility":
                awaiting_proc_weight += (r.facility_received_weight_tonnes or r.estimated_weight_tonnes)

            if r.status == "processing_completed":
                if r.processed_output_tonnes:
                    total_proc_weight += r.processed_output_tonnes

        # 2. Pickups
        if reports:
            pickup_ids = [r.pickup_id for r in reports if r.pickup_id]
            if pickup_ids:
                p_rows = db.execute(
                    select(PickupRequest.status, func.count(PickupRequest.id))
                    .where(PickupRequest.id.in_(pickup_ids))
                    .group_by(PickupRequest.status)
                ).all()
                for st, cnt in p_rows:
                    pickups_by_status[st] = cnt

        # 3. Stream B: Reusable materials
        materials = list(db.execute(select(CDMaterialListing)).scalars().all())
        total_materials = len(materials)
        mat_by_status: Dict[str, int] = {"available": 0, "reserved": 0, "collected": 0}
        diverted_count = 0

        for m in materials:
            st = m.status.lower()
            mat_by_status[st] = mat_by_status.get(st, 0) + 1
            if st in ["reserved", "collected"]:
                diverted_count += 1

        return CDDashboardResponse(
            total_cd_reports=total_reports,
            reports_by_material=reports_by_mat,
            total_pickups=total_pickups,
            pickups_by_status=pickups_by_status,
            total_estimated_volume_m3=round(total_est_vol, 2),
            total_estimated_weight_tonnes=round(total_est_weight, 2),
            total_collected_weight_tonnes=round(total_coll_weight, 2),
            material_awaiting_facility_receipt_tonnes=round(awaiting_receipt_weight, 2),
            material_awaiting_processing_tonnes=round(awaiting_proc_weight, 2),
            total_processed_tonnes=round(total_proc_weight, 2),
            reusable_materials_listed_count=total_materials,
            reusable_materials_by_status=mat_by_status,
            reusable_materials_diverted_count=diverted_count,
            disposal_stage_breakdown=disposal_stages,
            timestamp=now,
        )

