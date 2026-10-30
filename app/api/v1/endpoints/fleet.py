"""Pillar 5: Fleet Dispatch Prioritization REST Endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.fleet import FleetPriorityQueueResponse, FleetRoutePlanResponse
from app.services.fleet_service import FleetService

router = APIRouter(prefix="/fleet", tags=["Pillar 5: Fleet Dispatch Logistics"])


@router.get(
    "/priority-queue",
    response_model=APIResponse[FleetPriorityQueueResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Rule-Based Fleet Collection Priority Queue",
    description="Returns pending collection tasks sorted by a transparent multi-factor heuristic: stream risk score (hazardous=100, sanitary=50, wet=40, dry=20), aging duration (+2.0/hr), and estimated mass density. Transparent rule-based heuristic; does not claim Google OR-Tools in this prototype.",
)
def get_fleet_priority_queue(
    db: Session = Depends(get_db),
) -> APIResponse[FleetPriorityQueueResponse]:
    """Retrieve rule-based prioritized collection queue."""
    queue = FleetService.get_priority_queue(db)
    return APIResponse[FleetPriorityQueueResponse](
        success=True,
        message=f"Calculated prioritization for {queue.total_pending_pickups} pending pickups.",
        data=queue,
    )


@router.get(
    "/route",
    response_model=APIResponse[FleetRoutePlanResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Priority-Aware Static Truck Collection Route",
    description="Calculates a static, capacity-constrained collection route for pending pickups using priority-aware nearest-neighbor heuristic and Haversine distance estimation. Enforces independent limits for wet organic (100kg), dry recyclable (80kg), sanitary (20kg), and hazardous (10kg) compartments.",
)
def get_truck_route(
    start_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Optional starting depot/truck latitude"),
    start_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Optional starting depot/truck longitude"),
    vehicle_id: Optional[str] = Query(None, description="Optional vehicle ID filter"),
    db: Session = Depends(get_db),
) -> APIResponse[FleetRoutePlanResponse]:
    """Calculate capacity-constrained, priority-aware collection route."""
    route_plan = FleetService.get_optimized_route(
        db=db,
        start_lat=start_lat,
        start_lon=start_lon,
        vehicle_id=vehicle_id,
    )
    return APIResponse[FleetRoutePlanResponse](
        success=True,
        message=f"Route calculation completed: {route_plan.total_planned_stops} stops planned, {route_plan.total_unassigned_pickups} unassigned.",
        data=route_plan,
    )
