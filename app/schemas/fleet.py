"""Pillar 5: Fleet Dispatch Prioritization Schemas."""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field


class PrioritizedPickupItem(BaseModel):
    """An individual pickup scored and ranked by deterministic dispatch heuristic."""

    pickup_id: uuid.UUID
    report_id: uuid.UUID
    category: str
    ward_number: Optional[str]
    latitude: float
    longitude: float
    estimated_weight_kg: Optional[float]
    reported_at: datetime
    aging_hours: float = Field(..., description="Duration elapsed since report was registered")
    priority_score: float = Field(..., description="Deterministic priority score (higher = collect first)")
    priority_tier: str = Field(..., description="URGENT | HIGH | STANDARD | LOW")
    scoring_breakdown: dict = Field(..., description="Factor breakdown explaining the heuristic calculation")


class FleetPriorityQueueResponse(BaseModel):
    """Fleet collection queue ranked by transparent risk and aging rules."""

    total_pending_pickups: int
    optimization_method: str = Field(
        default="heuristic_risk_aging_density_rules",
        description="Scoring methodology",
    )
    algorithm_note: str = Field(
        default="Deterministic prioritization prioritizing biohazardous waste, aging delay, and dense streams. Prototype does not claim Google OR-Tools multi-compartment solver.",
        description="Methodology and operational disclaimer",
    )
    items: List[PrioritizedPickupItem]


# Statutory Four-Compartment Vehicle Capacities (kg)
COMPARTMENT_CAPACITIES_KG: dict = {
    "wet_organic": 100.0,
    "dry_recyclable": 80.0,
    "sanitary": 20.0,
    "hazardous": 10.0,
}


class CompartmentLoad(BaseModel):
    """Payload weight (kg) inside each independent vehicle compartment."""

    wet_organic: float = Field(default=0.0, ge=0.0, description="Wet organic load in kg (max 100 kg)")
    dry_recyclable: float = Field(default=0.0, ge=0.0, description="Dry recyclable load in kg (max 80 kg)")
    sanitary: float = Field(default=0.0, ge=0.0, description="Sanitary load in kg (max 20 kg)")
    hazardous: float = Field(default=0.0, ge=0.0, description="Hazardous load in kg (max 10 kg)")


class CompartmentCapacity(BaseModel):
    """Maximum static capacity (kg) for each vehicle compartment."""

    wet_organic: float = Field(default=100.0, description="Max wet organic capacity (kg)")
    dry_recyclable: float = Field(default=80.0, description="Max dry recyclable capacity (kg)")
    sanitary: float = Field(default=20.0, description="Max sanitary capacity (kg)")
    hazardous: float = Field(default=10.0, description="Max hazardous capacity (kg)")


class CompartmentUtilization(BaseModel):
    """Utilization percentage for each individual compartment and overall vehicle."""

    wet_organic_percent: float = Field(..., description="Wet organic compartment utilization %")
    dry_recyclable_percent: float = Field(..., description="Dry recyclable compartment utilization %")
    sanitary_percent: float = Field(..., description="Sanitary compartment utilization %")
    hazardous_percent: float = Field(..., description="Hazardous compartment utilization %")
    total_loaded_weight_kg: float = Field(..., description="Total weight loaded across all compartments in kg")
    total_vehicle_capacity_kg: float = Field(default=210.0, description="Total vehicle capacity in kg (100+80+20+10)")
    overall_utilization_percent: float = Field(..., description="Overall vehicle capacity utilization %")


class RouteStopItem(BaseModel):
    """A planned collection stop along the optimized static truck route."""

    stop_number: int = Field(..., ge=1, description="Sequential stop order on the route (1, 2, ...)")
    pickup_id: uuid.UUID
    report_id: uuid.UUID
    category: str = Field(..., description="Waste category of this pickup stop")
    ward_number: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float
    collected_weight_kg: float = Field(..., description="Weight collected at this stop in kg")
    priority_score: float = Field(..., description="Heuristic priority score")
    priority_tier: str = Field(..., description="URGENT | HIGH | STANDARD | LOW")
    estimated_leg_distance_km: float = Field(..., description="Estimated distance from previous stop (or start origin) in km")
    cumulative_estimated_distance_km: float = Field(..., description="Total cumulative distance up to this stop in km")
    compartment_load_after_stop: CompartmentLoad = Field(..., description="State of all four compartments after completing this stop")


class UnassignedPickupItem(BaseModel):
    """A pickup excluded from the route due to capacity limits or invalid data."""

    pickup_id: uuid.UUID
    report_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    estimated_weight_kg: Optional[float] = None
    priority_score: Optional[float] = None
    priority_tier: Optional[str] = None
    reason: str = Field(..., description="Detailed explanation why pickup was not included")


class StartOrigin(BaseModel):
    """Starting point of the collection route."""

    latitude: float
    longitude: float
    origin_type: str = Field(..., description="'provided_depot' | 'fallback_first_pickup'")
    description: str = Field(..., description="Explanation of how the starting coordinate was established")


class FleetRoutePlanResponse(BaseModel):
    """Optimized static truck collection route with compartment capacity management."""

    total_planned_stops: int = Field(..., description="Count of successfully routed stops")
    total_unassigned_pickups: int = Field(..., description="Count of pickups deferred or unroutable")
    total_estimated_distance_km: float = Field(..., description="Total estimated travel distance in km")
    distance_calculation_method: str = Field(
        default="haversine_great_circle_with_1.3x_urban_factor",
        description="Calculation method used for static distance estimation",
    )
    disclaimer: str = Field(
        default="Distances are static geometric estimates calculated via the Haversine formula with a 1.3x urban routing multiplier. This does not represent live GPS telemetry, OSRM road graph navigation, or real-time traffic conditions.",
        description="Integrity and operational disclaimer",
    )
    start_origin: Optional[StartOrigin] = None
    compartment_capacity: CompartmentCapacity = Field(default_factory=CompartmentCapacity)
    final_compartment_load: CompartmentLoad
    final_compartment_utilization: CompartmentUtilization
    stops: List[RouteStopItem]
    unassigned_pickups: List[UnassignedPickupItem]
