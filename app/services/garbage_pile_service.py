"""Pillar 4: Garbage-Pile Detection, Smart Collection Routing & Verified Cleanliness Service.

Implements:
1. Citizen pile reporting with statutory stream validation.
2. Proximity-based duplicate detection using Haversine formula (with private identity masking).
3. Rule-based severity and priority scoring (size, hazard, aging) with full transparency.
4. Fleet vehicle capacity checking and authorization rules.
5. EcoProof cryptographic cleanup verification with SHA-256 seal (no reporting credit incentives).
6. Municipal dashboard reporting compiled directly from database records.
"""

from datetime import datetime, timezone, timedelta
import math
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictException, EntityNotFoundException, ValidationException
from app.core.logging import get_logger
from app.core.security import generate_sha256_hash
from app.models.pickup import PickupRequest, VerificationRecord
from app.models.waste import WasteReport
from app.schemas.fleet import COMPARTMENT_CAPACITIES_KG
from app.schemas.garbage_piles import (
    DuplicateCandidateItem,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    GarbagePileAssignVehicleRequest,
    GarbagePileCleanupVerifyRequest,
    GarbagePileCleanupVerifyResponse,
    GarbagePileDashboardResponse,
    GarbagePileReportCreate,
    GarbagePileReportResponse,
    PILE_SIZE_SCORE_MAP,
    PILE_SIZE_WEIGHT_MAP_KG,
    PileSizeEnum,
    STREAM_HAZARD_SCORES,
    SeverityBreakdown,
    SeverityLevelEnum,
    VehicleRecommendationResponse,
)
from app.schemas.waste import WasteStreamEnum
from app.services.fleet_service import FleetService

logger = get_logger("app.services.garbage_pile")

# Fleet vehicle configuration definitions
FLEET_VEHICLES = [
    {
        "vehicle_id": "ECO-CART-01",
        "vehicle_type": "light_cart",
        "authorized_streams": [WasteStreamEnum.WET_ORGANIC.value, WasteStreamEnum.DRY_RECYCLABLE.value],
        "max_capacity_kg": 80.0,
        "compartment_capacities": {
            WasteStreamEnum.WET_ORGANIC.value: 50.0,
            WasteStreamEnum.DRY_RECYCLABLE.value: 30.0,
            WasteStreamEnum.SANITARY.value: 0.0,
            WasteStreamEnum.HAZARDOUS.value: 0.0,
        },
        "description": "Electric narrow-lane cart. Unauthorized for sanitary and hazardous waste.",
    },
    {
        "vehicle_id": "TRUCK-COMPACTOR-02",
        "vehicle_type": "compactor_truck",
        "authorized_streams": [
            WasteStreamEnum.WET_ORGANIC.value,
            WasteStreamEnum.DRY_RECYCLABLE.value,
            WasteStreamEnum.SANITARY.value,
            WasteStreamEnum.HAZARDOUS.value,
        ],
        "max_capacity_kg": 210.0,
        "compartment_capacities": {
            WasteStreamEnum.WET_ORGANIC.value: 100.0,
            WasteStreamEnum.DRY_RECYCLABLE.value: 80.0,
            WasteStreamEnum.SANITARY.value: 20.0,
            WasteStreamEnum.HAZARDOUS.value: 10.0,
        },
        "description": "Standard 4-compartment municipal compactor truck.",
    },
    {
        "vehicle_id": "HAZMAT-VAN-03",
        "vehicle_type": "hazmat_van",
        "authorized_streams": [WasteStreamEnum.HAZARDOUS.value, WasteStreamEnum.SANITARY.value],
        "max_capacity_kg": 100.0,
        "compartment_capacities": {
            WasteStreamEnum.WET_ORGANIC.value: 0.0,
            WasteStreamEnum.DRY_RECYCLABLE.value: 0.0,
            WasteStreamEnum.SANITARY.value: 40.0,
            WasteStreamEnum.HAZARDOUS.value: 60.0,
        },
        "description": "Specialized hazmat response van with certified biohazard containment.",
    },
    {
        "vehicle_id": "HEAVY-TIPPER-04",
        "vehicle_type": "heavy_tipper",
        "authorized_streams": [WasteStreamEnum.WET_ORGANIC.value, WasteStreamEnum.DRY_RECYCLABLE.value],
        "max_capacity_kg": 1000.0,
        "compartment_capacities": {
            WasteStreamEnum.WET_ORGANIC.value: 500.0,
            WasteStreamEnum.DRY_RECYCLABLE.value: 500.0,
            WasteStreamEnum.SANITARY.value: 0.0,
            WasteStreamEnum.HAZARDOUS.value: 0.0,
        },
        "description": "Heavy municipal tipper truck for critical bulk illegal dumps.",
    },
]


class GarbagePileService:
    """Business logic for illegal garbage-pile monitoring, routing, and verified resolution."""

    @staticmethod
    def calculate_severity(
        category: str,
        pile_size: Optional[str] = None,
        aging_hours: float = 0.0,
    ) -> SeverityBreakdown:
        """Transparent heuristic scoring combining pile size, statutory hazard, and aging delay."""
        size_key = (pile_size or PileSizeEnum.MEDIUM.value).lower()
        size_score = PILE_SIZE_SCORE_MAP.get(size_key, 30.0)
        hazard_score = STREAM_HAZARD_SCORES.get(category.lower(), 20.0)
        aging_score = round(max(0.0, aging_hours) * 2.0, 2)
        total_score = round(size_score + hazard_score + aging_score, 2)

        if total_score >= 120.0:
            tier = SeverityLevelEnum.CRITICAL
        elif total_score >= 80.0:
            tier = SeverityLevelEnum.HIGH
        elif total_score >= 40.0:
            tier = SeverityLevelEnum.MEDIUM
        else:
            tier = SeverityLevelEnum.LOW

        return SeverityBreakdown(
            size_score=size_score,
            category_hazard_score=hazard_score,
            aging_hours=round(aging_hours, 2),
            aging_score=aging_score,
            total_score=total_score,
            priority_tier=tier,
        )

    @staticmethod
    def find_duplicate_candidates(
        db: Session,
        latitude: float,
        longitude: float,
        category: Optional[str] = None,
        radius_meters: float = 100.0,
        window_hours: float = 24.0,
        exclude_report_id: Optional[uuid.UUID] = None,
    ) -> List[DuplicateCandidateItem]:
        """Proximity check matching nearby unresolved reports within radius and lookback window.

        Strictly masks any citizen private data (names, phone numbers, EcoPass IDs).
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=window_hours)

        # Query unresolved reports (doorstep or illegal dump)
        query = select(WasteReport).where(
            WasteReport.status.in_(["reported", "assigned", "in_progress", "scheduled"]),
            WasteReport.created_at >= cutoff_time,
        )

        if category:
            query = query.where(WasteReport.category == category)
        if exclude_report_id:
            query = query.where(WasteReport.id != exclude_report_id)

        candidate_reports = db.execute(query).scalars().all()
        duplicates: List[DuplicateCandidateItem] = []

        for rep in candidate_reports:
            dist_km = FleetService.calculate_haversine_distance(
                latitude, longitude, rep.latitude, rep.longitude
            )
            dist_m = dist_km * 1000.0

            if dist_m <= radius_meters:
                duplicates.append(
                    DuplicateCandidateItem(
                        report_id=rep.id,
                        category=rep.category,
                        status=rep.status,
                        distance_meters=round(dist_m, 1),
                        reported_at=rep.created_at,
                        address=rep.address,
                    )
                )

        # Sort closest first
        duplicates.sort(key=lambda d: d.distance_meters)
        return duplicates

    @classmethod
    def check_duplicates(
        cls,
        db: Session,
        req: DuplicateCheckRequest,
    ) -> DuplicateCheckResponse:
        """Standalone check for potential duplicates before citizen submission."""
        cat_str = req.category.value if req.category else None
        candidates = cls.find_duplicate_candidates(
            db=db,
            latitude=req.latitude,
            longitude=req.longitude,
            category=cat_str,
            radius_meters=req.radius_meters,
            window_hours=req.window_hours,
        )

        is_dup = len(candidates) > 0
        message = (
            f"Found {len(candidates)} unresolved waste pile report(s) within {req.radius_meters:.0f}m."
            if is_dup
            else "No duplicate reports detected within search perimeter."
        )

        return DuplicateCheckResponse(
            is_duplicate=is_dup,
            candidates_found=len(candidates),
            candidates=candidates,
            message=message,
        )

    @classmethod
    def create_garbage_pile_report(
        cls,
        db: Session,
        report_in: GarbagePileReportCreate,
    ) -> WasteReport:
        """Register a new illegal garbage pile report.

        Validates statutory streams, executes duplicate detection (with force_create override),
        and applies deterministic severity scoring.
        """
        cat_val = report_in.category.value
        size_val = report_in.pile_size.value

        # 1. Duplicate check (unless explicitly bypassed via force_create)
        if not report_in.force_create:
            duplicates = cls.find_duplicate_candidates(
                db=db,
                latitude=report_in.latitude,
                longitude=report_in.longitude,
                category=cat_val,
                radius_meters=100.0,
                window_hours=24.0,
            )
            if duplicates:
                first_dup = duplicates[0]
                raise ConflictException(
                    message=(
                        f"Potential duplicate illegal dump reported {first_dup.distance_meters:.1f}m away "
                        f"(Report ID: {first_dup.report_id}). If this is a distinct separate pile, "
                        f"resubmit with 'force_create=true'."
                    ),
                    details=[d.model_dump(mode="json") for d in duplicates],
                )

        # 2. Determine estimated weight
        weight = report_in.estimated_weight_kg
        if weight is None or weight <= 0:
            weight = PILE_SIZE_WEIGHT_MAP_KG.get(size_val, 40.0)

        # 3. Calculate initial severity
        severity_details = cls.calculate_severity(
            category=cat_val,
            pile_size=size_val,
            aging_hours=0.0,
        )

        # 4. Save WasteReport record with report_type='illegal_dump'
        report = WasteReport(
            ecopass_id=report_in.ecopass_id,
            category=cat_val,
            description=report_in.description,
            image_url=report_in.image_url,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            address=report_in.address,
            ward_number=report_in.ward_number,
            estimated_weight_kg=weight,
            report_type="illegal_dump",
            severity=severity_details.priority_tier.value,
            status="reported",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(
            f"Created illegal garbage pile report {report.id} "
            f"[Stream: {cat_val}, Size: {size_val}, Weight: {weight}kg, Severity: {report.severity}]"
        )
        return report

    @classmethod
    def get_garbage_pile_by_id(cls, db: Session, report_id: uuid.UUID) -> WasteReport:
        """Retrieve garbage pile report with pickups."""
        report = (
            db.execute(
                select(WasteReport)
                .options(joinedload(WasteReport.pickups))
                .where(WasteReport.id == report_id)
            )
            .scalars()
            .first()
        )
        if not report:
            raise EntityNotFoundException("GarbagePileReport", str(report_id))
        return report

    @classmethod
    def list_garbage_piles(
        cls,
        db: Session,
        status: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WasteReport]:
        """List illegal garbage pile reports with filtering."""
        query = (
            select(WasteReport)
            .options(joinedload(WasteReport.pickups))
            .where(WasteReport.report_type == "illegal_dump")
            .order_by(WasteReport.created_at.desc())
        )
        if status:
            query = query.where(WasteReport.status == status)
        if category:
            query = query.where(WasteReport.category == category)
        if severity:
            query = query.where(WasteReport.severity == severity.upper())

        return list(db.execute(query.limit(limit).offset(offset)).scalars().unique().all())

    @classmethod
    def recommend_vehicle(
        cls,
        db: Session,
        report_id: uuid.UUID,
    ) -> VehicleRecommendationResponse:
        """Inspect fleet vehicle authorization, compartment capacity, and active load to recommend vehicle."""
        report = cls.get_garbage_pile_by_id(db, report_id)
        cat = report.category
        weight = report.estimated_weight_kg or 40.0

        # Query all active pickups to calculate current load per vehicle per compartment
        active_pickups = (
            db.execute(
                select(PickupRequest)
                .options(joinedload(PickupRequest.waste_report))
                .where(PickupRequest.status.in_(["scheduled", "in_progress"]))
            )
            .scalars()
            .all()
        )

        # Map current vehicle loads: {vehicle_id: {stream: total_kg}}
        current_loads: Dict[str, Dict[str, float]] = {}
        for p in active_pickups:
            if not p.vehicle_id or not p.waste_report:
                continue
            v_id = p.vehicle_id
            if v_id not in current_loads:
                current_loads[v_id] = {}
            p_cat = p.waste_report.category
            p_weight = p.waste_report.estimated_weight_kg or 10.0
            current_loads[v_id][p_cat] = current_loads[v_id].get(p_cat, 0.0) + p_weight

        # Evaluate candidate fleet vehicles
        best_candidate = None
        rejection_reasons = []

        for v in FLEET_VEHICLES:
            v_id = v["vehicle_id"]
            auth_streams = v["authorized_streams"]
            capacities = v["compartment_capacities"]

            # 1. Authorization check
            if cat not in auth_streams:
                rejection_reasons.append(
                    f"{v_id} ({v['vehicle_type']}): Not authorized for '{cat}' stream."
                )
                continue

            comp_cap = capacities.get(cat, 0.0)
            cur_load = current_loads.get(v_id, {}).get(cat, 0.0)
            remaining_cap = comp_cap - cur_load

            # 2. Capacity check
            if weight > remaining_cap:
                rejection_reasons.append(
                    f"{v_id} ({v['vehicle_type']}): Exceeds remaining {cat} capacity ({weight:.1f}kg required > {remaining_cap:.1f}kg remaining)."
                )
                continue

            # Found suitable vehicle
            best_candidate = {
                "vehicle_id": v_id,
                "vehicle_type": v["vehicle_type"],
                "compartment_capacity_kg": comp_cap,
                "current_load_kg": round(cur_load, 1),
                "remaining_capacity_kg": round(remaining_cap, 1),
                "reason": (
                    f"Vehicle '{v_id}' ({v['vehicle_type']}) is certified for '{cat}' stream "
                    f"with {remaining_cap:.1f} kg remaining compartment capacity."
                ),
            }
            break

        if best_candidate:
            return VehicleRecommendationResponse(
                report_id=report.id,
                category=cat,
                estimated_weight_kg=weight,
                recommended_vehicle_id=best_candidate["vehicle_id"],
                vehicle_type=best_candidate["vehicle_type"],
                is_assigned=True,
                reason=best_candidate["reason"],
                compartment_capacity_kg=best_candidate["compartment_capacity_kg"],
                current_load_kg=best_candidate["current_load_kg"],
                remaining_capacity_kg=best_candidate["remaining_capacity_kg"],
            )

        # No suitable vehicle found
        operational_reason = (
            f"No suitable vehicle available for {weight:.1f}kg of {cat} waste. "
            + "; ".join(rejection_reasons)
        )
        return VehicleRecommendationResponse(
            report_id=report.id,
            category=cat,
            estimated_weight_kg=weight,
            recommended_vehicle_id=None,
            vehicle_type=None,
            is_assigned=False,
            reason=operational_reason,
            compartment_capacity_kg=None,
            current_load_kg=None,
            remaining_capacity_kg=None,
        )

    @classmethod
    def assign_vehicle(
        cls,
        db: Session,
        report_id: uuid.UUID,
        assign_in: GarbagePileAssignVehicleRequest,
    ) -> Tuple[WasteReport, PickupRequest]:
        """Assign a designated vehicle to collect the pile, verifying compartment eligibility."""
        report = cls.get_garbage_pile_by_id(db, report_id)
        cat = report.category
        weight = report.estimated_weight_kg or 40.0

        # Verify vehicle eligibility from fleet definition
        matching_vehicle = next((v for v in FLEET_VEHICLES if v["vehicle_id"] == assign_in.vehicle_id), None)
        if not matching_vehicle:
            # Fallback check against known compartment capacities
            if cat not in COMPARTMENT_CAPACITIES_KG:
                raise ValidationException(f"Unsupported waste stream '{cat}'.")
        else:
            if cat not in matching_vehicle["authorized_streams"]:
                raise ValidationException(
                    f"Vehicle '{assign_in.vehicle_id}' ({matching_vehicle['vehicle_type']}) is unauthorized to carry '{cat}' waste."
                )

            # Check compartment capacity overflow against active assignments
            comp_cap = matching_vehicle["compartment_capacities"].get(cat, 0.0)
            active_vehicle_pickups = db.execute(
                select(PickupRequest)
                .options(joinedload(PickupRequest.waste_report))
                .where(
                    PickupRequest.vehicle_id == assign_in.vehicle_id,
                    PickupRequest.status.in_(["scheduled", "in_progress"]),
                )
            ).scalars().all()

            cur_load = sum(
                (p.waste_report.estimated_weight_kg or 0.0)
                for p in active_vehicle_pickups
                if p.waste_report and p.waste_report.category == cat and p.report_id != report.id
            )

            if cur_load + weight > comp_cap:
                raise ValidationException(
                    f"Vehicle '{assign_in.vehicle_id}' compartment '{cat}' capacity overflow: "
                    f"current load {cur_load:.1f}kg + pile {weight:.1f}kg exceeds capacity limit of {comp_cap:.1f}kg."
                )

        # Check existing pickup or create a new pickup request
        existing_pickup = next((p for p in report.pickups if p.status in ["scheduled", "in_progress"]), None)
        if existing_pickup:
            existing_pickup.vehicle_id = assign_in.vehicle_id
            if assign_in.collector_id:
                existing_pickup.collector_id = assign_in.collector_id
            if assign_in.collector_name:
                existing_pickup.collector_name = assign_in.collector_name
            if assign_in.scheduled_time:
                existing_pickup.scheduled_time = assign_in.scheduled_time
            pickup = existing_pickup
        else:
            pickup = PickupRequest(
                report_id=report.id,
                vehicle_id=assign_in.vehicle_id,
                collector_id=assign_in.collector_id,
                collector_name=assign_in.collector_name,
                scheduled_time=assign_in.scheduled_time,
                status="scheduled",
            )
            db.add(pickup)

        report.status = "assigned"
        db.commit()
        db.refresh(report)
        db.refresh(pickup)

        logger.info(f"Assigned vehicle {assign_in.vehicle_id} to illegal pile {report.id} (Pickup: {pickup.id})")
        return report, pickup

    @classmethod
    def verify_cleanup(
        cls,
        db: Session,
        report_id: uuid.UUID,
        verify_in: GarbagePileCleanupVerifyRequest,
    ) -> GarbagePileCleanupVerifyResponse:
        """Verify field cleanup with before/after photos and generate an immutable EcoProof SHA-256 seal.

        Strictly prevents awarding EcoCredits for simply reporting illegal piles.
        """
        report = cls.get_garbage_pile_by_id(db, report_id)

        if report.status in ["resolved", "verified"]:
            raise ConflictException("This garbage pile report has already been verified and resolved.")

        # Ensure a linked PickupRequest exists
        pickup = next((p for p in report.pickups if p.status != "cancelled"), None)
        if not pickup:
            pickup = PickupRequest(
                report_id=report.id,
                collector_id=verify_in.verifier_id,
                status="in_progress",
            )
            db.add(pickup)
            db.flush()

        # Check existing verification
        existing_verification = db.execute(
            select(VerificationRecord).where(VerificationRecord.pickup_id == pickup.id)
        ).scalar_one_or_none()
        if existing_verification:
            raise ConflictException("This collection pickup already has an EcoProof verification record.")

        verified_at = datetime.now(timezone.utc)

        # Generate cryptographic SHA-256 integrity hash
        hash_payload = (
            f"pile_cleanup:{report.id}|"
            f"pickup:{pickup.id}|"
            f"verifier:{verify_in.verifier_id}|"
            f"before_url:{report.image_url or ''}|"
            f"after_url:{verify_in.after_image_url}|"
            f"actual_weight_kg:{verify_in.actual_weight_kg:.2f}|"
            f"stream:{report.category}|"
            f"timestamp:{verified_at.isoformat()}"
        )
        integrity_hash = generate_sha256_hash(hash_payload)

        # Strict fraud prevention: 0 EcoCredits awarded for simply reporting/verifying illegal dump
        verification = VerificationRecord(
            pickup_id=pickup.id,
            verified_at=verified_at,
            actual_weight_kg=verify_in.actual_weight_kg,
            stream_confirmed=report.category,
            collector_signature_id=verify_in.verifier_id,
            after_image_url=verify_in.after_image_url,
            notes=verify_in.notes,
            integrity_hash=integrity_hash,
            ecocredits_awarded=0,  # Zero credits disbursed for illegal dump reporting
        )
        db.add(verification)

        pickup.status = "completed"
        report.status = "resolved"

        db.commit()
        db.refresh(verification)
        db.refresh(report)

        logger.info(
            f"Cleanup verified for illegal pile {report.id} by verifier {verify_in.verifier_id}. "
            f"Weight: {verify_in.actual_weight_kg}kg, Hash: {integrity_hash[:12]}..."
        )

        return GarbagePileCleanupVerifyResponse(
            report_id=report.id,
            pickup_id=pickup.id,
            status=report.status,
            before_image_url=report.image_url,
            after_image_url=verify_in.after_image_url,
            actual_weight_kg=verify_in.actual_weight_kg,
            verifier_id=verify_in.verifier_id,
            integrity_hash=integrity_hash,
            verified_at=verified_at,
            ecocredits_awarded=0,
        )

    @classmethod
    def get_dashboard_summary(cls, db: Session) -> GarbagePileDashboardResponse:
        """Compile municipal illegal garbage-pile metrics strictly from database records."""
        now = datetime.now(timezone.utc)

        # 1. Total waste reports and illegal piles
        total_reports = db.execute(select(func.count(WasteReport.id))).scalar() or 0
        illegal_reports = db.execute(
            select(WasteReport)
            .options(joinedload(WasteReport.pickups).joinedload(PickupRequest.verification))
            .where(WasteReport.report_type == "illegal_dump")
        ).scalars().unique().all()

        total_illegal = len(illegal_reports)

        # 2. Status breakdown
        status_counts: Dict[str, int] = {
            "reported": 0,
            "assigned": 0,
            "in_progress": 0,
            "resolved": 0,
            "cancelled": 0,
        }
        for r in illegal_reports:
            st = r.status.lower()
            if st in ["verified", "resolved"]:
                status_counts["resolved"] += 1
            elif st in status_counts:
                status_counts[st] += 1
            else:
                status_counts[st] = status_counts.get(st, 0) + 1

        # 3. Dynamic priority distribution
        priority_counts: Dict[str, int] = {
            SeverityLevelEnum.CRITICAL.value: 0,
            SeverityLevelEnum.HIGH.value: 0,
            SeverityLevelEnum.MEDIUM.value: 0,
            SeverityLevelEnum.LOW.value: 0,
        }
        for r in illegal_reports:
            # For unresolved reports, calculate dynamic aging
            r_created = r.created_at
            if r_created.tzinfo is None:
                r_created = r_created.replace(tzinfo=timezone.utc)
            aging_hours = (now - r_created).total_seconds() / 3600.0

            if r.status in ["reported", "assigned", "in_progress"]:
                scoring = cls.calculate_severity(
                    category=r.category,
                    aging_hours=aging_hours,
                )
                priority_counts[scoring.priority_tier.value] += 1
            else:
                sev = (r.severity or SeverityLevelEnum.LOW.value).upper()
                if sev in priority_counts:
                    priority_counts[sev] += 1
                else:
                    priority_counts[SeverityLevelEnum.LOW.value] += 1

        # 4. Count potential duplicate candidates among open reports
        open_piles = [r for r in illegal_reports if r.status in ["reported", "assigned", "in_progress"]]
        potential_dups_count = 0
        for i, pile_a in enumerate(open_piles):
            has_dup = False
            for j, pile_b in enumerate(open_piles):
                if i != j and pile_a.category == pile_b.category:
                    d_km = FleetService.calculate_haversine_distance(
                        pile_a.latitude, pile_a.longitude, pile_b.latitude, pile_b.longitude
                    )
                    if d_km * 1000.0 <= 100.0:
                        has_dup = True
                        break
            if has_dup:
                potential_dups_count += 1

        # 5. Vehicle assignment stats
        assigned_count = sum(1 for r in open_piles if r.status == "assigned" or any(p.vehicle_id for p in r.pickups))
        unassigned_count = len(open_piles) - assigned_count

        # 6. Verified cleanups and weights
        verified_cleanups = 0
        total_cleaned_weight = 0.0
        resolution_durations_hours: List[float] = []

        for r in illegal_reports:
            if r.status in ["resolved", "verified"]:
                verified_cleanups += 1
                for p in r.pickups:
                    if p.verification:
                        total_cleaned_weight += p.verification.actual_weight_kg
                        v_time = p.verification.verified_at
                        if v_time.tzinfo is None:
                            v_time = v_time.replace(tzinfo=timezone.utc)
                        r_time = r.created_at
                        if r_time.tzinfo is None:
                            r_time = r_time.replace(tzinfo=timezone.utc)
                        dur = max(0.0, (v_time - r_time).total_seconds() / 3600.0)
                        resolution_durations_hours.append(dur)

        avg_resolution_time = (
            round(sum(resolution_durations_hours) / len(resolution_durations_hours), 2)
            if resolution_durations_hours
            else None
        )

        return GarbagePileDashboardResponse(
            total_reports=total_reports,
            total_illegal_piles=total_illegal,
            status_breakdown=status_counts,
            priority_distribution=priority_counts,
            potential_duplicate_candidates_count=potential_dups_count,
            vehicle_assignment_stats={
                "assigned": assigned_count,
                "unassigned": unassigned_count,
            },
            total_verified_cleanups=verified_cleanups,
            total_cleaned_weight_kg=round(total_cleaned_weight, 2),
            average_resolution_time_hours=avg_resolution_time,
            timestamp=now,
        )
