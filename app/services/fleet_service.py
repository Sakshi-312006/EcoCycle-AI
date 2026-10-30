"""Pillar 5: Fleet Dispatch Prioritization and Route Optimization Service."""

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.pickup import PickupRequest
from app.models.waste import WasteReport
from app.schemas.fleet import (
    COMPARTMENT_CAPACITIES_KG,
    CompartmentCapacity,
    CompartmentLoad,
    CompartmentUtilization,
    FleetPriorityQueueResponse,
    FleetRoutePlanResponse,
    PrioritizedPickupItem,
    RouteStopItem,
    StartOrigin,
    UnassignedPickupItem,
)

# Stream Risk Weights (Statutory Biohazard & Decomposition Urgency)
STREAM_RISK_WEIGHTS = {
    "hazardous": 100.0,      # Urgent chemical/flammable safety hazard
    "sanitary": 50.0,        # Pathogenic contamination risk
    "wet_organic": 40.0,     # Putrefaction, leachate & odor generation
    "dry_recyclable": 20.0,  # Stable inert packaging
}


class FleetService:
    """Deterministic, rule-based pickup prioritization engine."""

    @staticmethod
    def get_priority_queue(db: Session) -> FleetPriorityQueueResponse:
        """Score and sort active pickups by multi-factor hazard, aging, and mass heuristic."""
        now = datetime.now(timezone.utc)

        pickups = list(
            db.execute(
                select(PickupRequest)
                .options(joinedload(PickupRequest.waste_report))
                .join(WasteReport, PickupRequest.report_id == WasteReport.id)
                .where(
                    PickupRequest.status.in_(["scheduled", "in_progress"]),
                    WasteReport.report_type.in_(["doorstep", "illegal_dump"]),
                )
            )
            .scalars()
            .all()
        )

        prioritized_items: List[PrioritizedPickupItem] = []

        for p in pickups:
            report = p.waste_report
            if not report:
                continue

            stream_risk = STREAM_RISK_WEIGHTS.get(report.category, 20.0)

            # Aging in hours
            report_time = report.created_at
            if report_time.tzinfo is None:
                report_time = report_time.replace(tzinfo=timezone.utc)

            aging_hours = max(0.1, round((now - report_time).total_seconds() / 3600.0, 2))
            aging_score = round(aging_hours * 2.0, 2)

            # Mass score
            est_weight = report.estimated_weight_kg if report.estimated_weight_kg is not None else 5.0
            mass_score = round(est_weight * 0.5, 2)

            # Total score
            priority_score = round(stream_risk + aging_score + mass_score, 2)

            if priority_score >= 100:
                tier = "URGENT"
            elif priority_score >= 60:
                tier = "HIGH"
            elif priority_score >= 35:
                tier = "STANDARD"
            else:
                tier = "LOW"

            scoring_breakdown = {
                "stream_risk_points": stream_risk,
                "aging_duration_points": aging_score,
                "mass_density_points": mass_score,
            }

            prioritized_items.append(
                PrioritizedPickupItem(
                    pickup_id=p.id,
                    report_id=report.id,
                    category=report.category,
                    ward_number=report.ward_number,
                    latitude=report.latitude,
                    longitude=report.longitude,
                    estimated_weight_kg=report.estimated_weight_kg,
                    reported_at=report.created_at,
                    aging_hours=aging_hours,
                    priority_score=priority_score,
                    priority_tier=tier,
                    scoring_breakdown=scoring_breakdown,
                )
            )

        # Sort descending by priority score
        prioritized_items.sort(key=lambda item: item.priority_score, reverse=True)

        return FleetPriorityQueueResponse(
            total_pending_pickups=len(prioritized_items),
            items=prioritized_items,
        )

    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate straight-line great-circle distance between two GPS coordinates in kilometers."""
        earth_radius_km = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return earth_radius_km * c

    @classmethod
    def estimate_urban_distance_km(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate static estimated driving distance in km with 1.3x urban road network detour factor."""
        straight_line = cls.calculate_haversine_distance(lat1, lon1, lat2, lon2)
        return round(straight_line * 1.3, 3)

    @classmethod
    def get_optimized_route(
        cls,
        db: Session,
        start_lat: Optional[float] = None,
        start_lon: Optional[float] = None,
        vehicle_id: Optional[str] = None,
    ) -> FleetRoutePlanResponse:
        """Calculate a static, capacity-constrained collection route for pending pickups.

        Follows priority-aware nearest-neighbor routing while enforcing independent
        four-compartment vehicle capacity limits:
        - wet_organic: 100 kg
        - dry_recyclable: 80 kg
        - sanitary: 20 kg
        - hazardous: 10 kg
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch pending pickups only (scheduled and in_progress)
        query = (
            select(PickupRequest)
            .options(joinedload(PickupRequest.waste_report))
            .join(WasteReport, PickupRequest.report_id == WasteReport.id)
            .where(
                PickupRequest.status.in_(["scheduled", "in_progress"]),
                WasteReport.report_type.in_(["doorstep", "illegal_dump"]),
            )
        )
        if vehicle_id:
            query = query.where(PickupRequest.vehicle_id == vehicle_id)

        pickups = list(db.execute(query).scalars().all())

        unassigned_pickups: List[UnassignedPickupItem] = []
        routable_candidates: List[dict] = []

        # 2. Validate linked reports, categories, and coordinates
        for p in pickups:
            report = p.waste_report
            if not report:
                unassigned_pickups.append(
                    UnassignedPickupItem(
                        pickup_id=p.id,
                        reason="Missing linked waste report record",
                    )
                )
                continue

            lat = report.latitude
            lon = report.longitude
            if lat is None or lon is None:
                unassigned_pickups.append(
                    UnassignedPickupItem(
                        pickup_id=p.id,
                        report_id=report.id,
                        category=report.category,
                        reason="Missing GPS coordinates on waste report",
                    )
                )
                continue

            if math.isnan(lat) or math.isnan(lon) or not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
                unassigned_pickups.append(
                    UnassignedPickupItem(
                        pickup_id=p.id,
                        report_id=report.id,
                        category=report.category,
                        reason=f"Invalid GPS coordinates ({lat}, {lon}) outside valid bounds [-90, 90], [-180, 180]",
                    )
                )
                continue

            # Flag null-island placeholder coordinates
            if abs(lat) < 1e-5 and abs(lon) < 1e-5:
                unassigned_pickups.append(
                    UnassignedPickupItem(
                        pickup_id=p.id,
                        report_id=report.id,
                        category=report.category,
                        reason="Invalid coordinates: Null Island (0.0, 0.0) placeholder",
                    )
                )
                continue

            # Calculate deterministic priority score & tier
            stream_risk = STREAM_RISK_WEIGHTS.get(report.category, 20.0)
            report_time = report.created_at
            if report_time.tzinfo is None:
                report_time = report_time.replace(tzinfo=timezone.utc)

            aging_hours = max(0.1, round((now - report_time).total_seconds() / 3600.0, 2))
            aging_score = round(aging_hours * 2.0, 2)
            raw_weight = report.estimated_weight_kg if report.estimated_weight_kg is not None else 5.0
            est_weight = max(0.1, round(raw_weight, 2))
            mass_score = round(est_weight * 0.5, 2)
            priority_score = round(stream_risk + aging_score + mass_score, 2)

            if priority_score >= 100:
                tier = "URGENT"
            elif priority_score >= 60:
                tier = "HIGH"
            elif priority_score >= 35:
                tier = "STANDARD"
            else:
                tier = "LOW"

            routable_candidates.append({
                "pickup": p,
                "report": report,
                "lat": lat,
                "lon": lon,
                "weight": est_weight,
                "category": report.category,
                "priority_score": priority_score,
                "priority_tier": tier,
            })

        current_loads: Dict[str, float] = {
            "wet_organic": 0.0,
            "dry_recyclable": 0.0,
            "sanitary": 0.0,
            "hazardous": 0.0,
        }

        # 3. Handle empty route case gracefully
        if not routable_candidates:
            start_origin = None
            if start_lat is not None and start_lon is not None:
                start_origin = StartOrigin(
                    latitude=start_lat,
                    longitude=start_lon,
                    origin_type="provided_depot",
                    description=f"Route starts at provided dispatch depot ({start_lat:.4f}, {start_lon:.4f})",
                )

            return FleetRoutePlanResponse(
                total_planned_stops=0,
                total_unassigned_pickups=len(unassigned_pickups),
                total_estimated_distance_km=0.0,
                start_origin=start_origin,
                compartment_capacity=CompartmentCapacity(),
                final_compartment_load=CompartmentLoad(),
                final_compartment_utilization=CompartmentUtilization(
                    wet_organic_percent=0.0,
                    dry_recyclable_percent=0.0,
                    sanitary_percent=0.0,
                    hazardous_percent=0.0,
                    total_loaded_weight_kg=0.0,
                    total_vehicle_capacity_kg=210.0,
                    overall_utilization_percent=0.0,
                ),
                stops=[],
                unassigned_pickups=unassigned_pickups,
            )

        # 4. Establish start origin
        has_provided_depot = start_lat is not None and start_lon is not None
        if has_provided_depot:
            current_lat = start_lat
            current_lon = start_lon
            start_origin = StartOrigin(
                latitude=start_lat,
                longitude=start_lon,
                origin_type="provided_depot",
                description=f"Route starts at provided dispatch depot ({start_lat:.4f}, {start_lon:.4f})",
            )
        else:
            # Fallback: start at the highest priority candidate anchor stop
            tier_rank = {"URGENT": 4, "HIGH": 3, "STANDARD": 2, "LOW": 1}
            sorted_by_priority = sorted(
                routable_candidates,
                key=lambda c: (tier_rank.get(c["priority_tier"], 0), c["priority_score"]),
                reverse=True,
            )
            anchor = sorted_by_priority[0]
            current_lat = anchor["lat"]
            current_lon = anchor["lon"]
            start_origin = StartOrigin(
                latitude=anchor["lat"],
                longitude=anchor["lon"],
                origin_type="fallback_first_pickup",
                description="No depot coordinates were provided. The route sequence begins at the first prioritized collection point as a starting anchor (leg distance 0.0 km). This anchor is an initial pickup location, not a physical municipal depot.",
            )

        planned_stops: List[RouteStopItem] = []
        cumulative_distance = 0.0
        stop_number = 1

        # 5. Priority-Aware Nearest-Neighbor Tour
        tier_sequence = ["URGENT", "HIGH", "STANDARD", "LOW"]

        for target_tier in tier_sequence:
            tier_items = [c for c in routable_candidates if c["priority_tier"] == target_tier]
            if not tier_items:
                continue

            while tier_items:
                if not has_provided_depot and stop_number == 1:
                    # Anchor stop was selected as the first pickup point
                    best_idx = 0
                    best_distance = 0.0
                else:
                    best_idx = 0
                    best_distance = cls.estimate_urban_distance_km(
                        current_lat, current_lon, tier_items[0]["lat"], tier_items[0]["lon"]
                    )
                    for idx in range(1, len(tier_items)):
                        d = cls.estimate_urban_distance_km(
                            current_lat, current_lon, tier_items[idx]["lat"], tier_items[idx]["lon"]
                        )
                        if d < best_distance:
                            best_distance = d
                            best_idx = idx

                chosen = tier_items.pop(best_idx)
                cat = chosen["category"]
                weight = chosen["weight"]
                cap = COMPARTMENT_CAPACITIES_KG.get(cat, 100.0)
                current_load = current_loads.get(cat, 0.0)
                remaining_cap = round(cap - current_load, 2)

                # 6. Capacity constraints check
                if weight > remaining_cap:
                    unassigned_pickups.append(
                        UnassignedPickupItem(
                            pickup_id=chosen["pickup"].id,
                            report_id=chosen["report"].id,
                            category=cat,
                            estimated_weight_kg=weight,
                            priority_score=chosen["priority_score"],
                            priority_tier=chosen["priority_tier"],
                            reason=f"Capacity overflow for compartment '{cat}': required {weight:.2f} kg exceeds remaining capacity {remaining_cap:.2f} kg (capacity limit: {cap:.2f} kg)",
                        )
                    )
                    continue

                # Add stop to planned route
                current_loads[cat] = round(current_loads[cat] + weight, 2)
                cumulative_distance = round(cumulative_distance + best_distance, 3)
                current_lat = chosen["lat"]
                current_lon = chosen["lon"]

                planned_stops.append(
                    RouteStopItem(
                        stop_number=stop_number,
                        pickup_id=chosen["pickup"].id,
                        report_id=chosen["report"].id,
                        category=cat,
                        ward_number=chosen["report"].ward_number,
                        address=chosen["report"].address,
                        latitude=chosen["lat"],
                        longitude=chosen["lon"],
                        collected_weight_kg=weight,
                        priority_score=chosen["priority_score"],
                        priority_tier=chosen["priority_tier"],
                        estimated_leg_distance_km=round(best_distance, 3),
                        cumulative_estimated_distance_km=cumulative_distance,
                        compartment_load_after_stop=CompartmentLoad(**current_loads),
                    )
                )
                stop_number += 1

        # 7. Calculate final compartment utilization
        wet_pct = round((current_loads["wet_organic"] / 100.0) * 100.0, 1)
        dry_pct = round((current_loads["dry_recyclable"] / 80.0) * 100.0, 1)
        san_pct = round((current_loads["sanitary"] / 20.0) * 100.0, 1)
        haz_pct = round((current_loads["hazardous"] / 10.0) * 100.0, 1)
        total_weight = round(sum(current_loads.values()), 2)
        overall_pct = round((total_weight / 210.0) * 100.0, 1)

        return FleetRoutePlanResponse(
            total_planned_stops=len(planned_stops),
            total_unassigned_pickups=len(unassigned_pickups),
            total_estimated_distance_km=cumulative_distance,
            start_origin=start_origin,
            compartment_capacity=CompartmentCapacity(),
            final_compartment_load=CompartmentLoad(**current_loads),
            final_compartment_utilization=CompartmentUtilization(
                wet_organic_percent=wet_pct,
                dry_recyclable_percent=dry_pct,
                sanitary_percent=san_pct,
                hazardous_percent=haz_pct,
                total_loaded_weight_kg=total_weight,
                total_vehicle_capacity_kg=210.0,
                overall_utilization_percent=overall_pct,
            ),
            stops=planned_stops,
            unassigned_pickups=unassigned_pickups,
        )
