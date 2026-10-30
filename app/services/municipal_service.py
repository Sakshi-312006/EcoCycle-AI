"""Pillar 5: Municipal Governance Dashboard Service."""

from datetime import datetime, timezone
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.cd_waste import CDEstimateRecord, CDMaterialListing
from app.models.circular import CircularListing
from app.models.ecopass import EcoCreditTransaction, EcoPassAccount
from app.models.pickup import PickupRequest, VerificationRecord
from app.models.waste import WasteReport
from app.schemas.municipal import MunicipalDashboardStats, PickupStatistics, StreamStatistics


class MunicipalService:
    """Service computing operational governance metrics from persistent records."""

    @staticmethod
    def get_dashboard_statistics(db: Session) -> MunicipalDashboardStats:
        """Derive aggregated metrics directly from stored database rows."""
        # 1. Waste reports by stream
        reports_raw = db.execute(
            select(WasteReport.category, func.count(WasteReport.id)).group_by(WasteReport.category)
        ).all()
        stream_counts = {cat: count for cat, count in reports_raw}
        stream_stats = StreamStatistics(
            wet_organic=stream_counts.get("wet_organic", 0),
            dry_recyclable=stream_counts.get("dry_recyclable", 0),
            sanitary=stream_counts.get("sanitary", 0),
            hazardous=stream_counts.get("hazardous", 0),
        )
        total_reports = sum(stream_counts.values())

        # 2. Pickups by status
        pickups_raw = db.execute(
            select(PickupRequest.status, func.count(PickupRequest.id)).group_by(PickupRequest.status)
        ).all()
        pickup_counts = {stat: count for stat, count in pickups_raw}
        pickup_stats = PickupStatistics(
            scheduled=pickup_counts.get("scheduled", 0),
            in_progress=pickup_counts.get("in_progress", 0),
            completed=pickup_counts.get("completed", 0),
            cancelled=pickup_counts.get("cancelled", 0),
        )
        total_pickups = sum(pickup_counts.values())

        # 3. Verified collection & weight
        verification_agg = db.execute(
            select(func.count(VerificationRecord.id), func.sum(VerificationRecord.actual_weight_kg))
        ).one()
        total_verified = verification_agg[0] or 0
        total_weight_kg = round(float(verification_agg[1] or 0.0), 2)

        # 4. C&D metrics
        total_cd_estimates = db.execute(select(func.count(CDEstimateRecord.id))).scalar() or 0
        total_cd_materials = db.execute(select(func.count(CDMaterialListing.id))).scalar() or 0

        # 5. Circular items
        diverted_case = case((CircularListing.status.in_(["claimed", "completed"]), 1), else_=0)
        circular_agg = db.execute(
            select(
                func.count(CircularListing.id),
                func.sum(diverted_case),
            )
        ).one()
        total_circular = circular_agg[0] or 0
        total_circular_diverted = circular_agg[1] or 0

        # 6. EcoCredits and EcoPass
        total_credits = db.execute(
            select(func.sum(EcoCreditTransaction.amount)).where(EcoCreditTransaction.amount > 0)
        ).scalar() or 0
        total_households = db.execute(select(func.count(EcoPassAccount.id))).scalar() or 0

        # 7. Ward distribution
        ward_raw = db.execute(
            select(WasteReport.ward_number, func.count(WasteReport.id))
            .where(WasteReport.ward_number.isnot(None))
            .group_by(WasteReport.ward_number)
        ).all()
        ward_coverage = {str(ward): count for ward, count in ward_raw if ward}

        return MunicipalDashboardStats(
            total_waste_reports=total_reports,
            reports_by_stream=stream_stats,
            total_pickups=total_pickups,
            pickups_by_status=pickup_stats,
            total_verified_collections=total_verified,
            total_waste_verified_kg=total_weight_kg,
            total_cd_estimates_logged=total_cd_estimates,
            total_cd_materials_listed=total_cd_materials,
            total_circular_items_listed=total_circular,
            total_circular_items_diverted=total_circular_diverted,
            total_ecocredits_circulating=total_credits,
            total_ecopass_households=total_households,
            ward_coverage=ward_coverage,
            timestamp=datetime.now(timezone.utc),
        )
