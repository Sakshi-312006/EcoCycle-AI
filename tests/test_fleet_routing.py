"""Pillar 5: Fleet Route Optimization and Four-Compartment Capacity Tests."""

from starlette.testclient import TestClient

from app.models.pickup import PickupRequest
from app.models.waste import WasteReport
from app.services.fleet_service import FleetService


def test_haversine_distance_calculation() -> None:
    """Verify standard Haversine great-circle calculation and urban multiplier."""
    # Point A: Bengaluru (12.9716, 77.5946)
    # Point B: Mysuru (12.2958, 76.6394)
    # Known straight-line distance is approx 128 - 130 km
    dist_km = FleetService.calculate_haversine_distance(12.9716, 77.5946, 12.2958, 76.6394)
    assert 125.0 < dist_km < 135.0

    # Test identical coordinates yield 0.0 distance
    zero_dist = FleetService.calculate_haversine_distance(12.9716, 77.5946, 12.9716, 77.5946)
    assert zero_dist == 0.0

    # Test urban multiplier adds 30% detour factor
    urban_dist = FleetService.estimate_urban_distance_km(12.9716, 77.5946, 12.2958, 76.6394)
    assert round(urban_dist, 2) == round(dist_km * 1.3, 2)


def test_empty_route_case(client: TestClient) -> None:
    """Ensure route optimization returns HTTP 200 with 0 stops when no pending pickups exist."""
    res = client.get("/api/v1/fleet/route?vehicle_id=VEH-NONEXISTENT")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["total_planned_stops"] == 0
    assert data["total_estimated_distance_km"] == 0.0
    assert data["stops"] == []
    assert data["final_compartment_load"]["wet_organic"] == 0.0
    assert data["final_compartment_load"]["dry_recyclable"] == 0.0
    assert data["final_compartment_load"]["sanitary"] == 0.0
    assert data["final_compartment_load"]["hazardous"] == 0.0
    assert data["compartment_capacity"]["wet_organic"] == 100.0
    assert data["compartment_capacity"]["dry_recyclable"] == 80.0
    assert data["compartment_capacity"]["sanitary"] == 20.0
    assert data["compartment_capacity"]["hazardous"] == 10.0


def test_status_filtering_ignores_completed_and_cancelled(client: TestClient) -> None:
    """Verify that completed and cancelled pickups are strictly excluded from the planned route."""
    veh_id = "VEH-STATUS-FILTER"

    # 1. Create three reports
    r1 = client.post("/api/v1/waste-reports", json={
        "category": "dry_recyclable",
        "description": "Completed cardboard pickup",
        "latitude": 12.91,
        "longitude": 77.61,
        "estimated_weight_kg": 10.0,
    }).json()["data"]["id"]

    r2 = client.post("/api/v1/waste-reports", json={
        "category": "dry_recyclable",
        "description": "Cancelled plastic pickup",
        "latitude": 12.92,
        "longitude": 77.62,
        "estimated_weight_kg": 15.0,
    }).json()["data"]["id"]

    r3 = client.post("/api/v1/waste-reports", json={
        "category": "dry_recyclable",
        "description": "Scheduled pending pickup",
        "latitude": 12.93,
        "longitude": 77.63,
        "estimated_weight_kg": 20.0,
    }).json()["data"]["id"]

    # 2. Schedule pickups with specific vehicle
    p1_id = client.post("/api/v1/pickups", json={"report_id": r1, "vehicle_id": veh_id}).json()["data"]["id"]
    p2_id = client.post("/api/v1/pickups", json={"report_id": r2, "vehicle_id": veh_id}).json()["data"]["id"]
    p3_id = client.post("/api/v1/pickups", json={"report_id": r3, "vehicle_id": veh_id}).json()["data"]["id"]

    # 3. Transition p1 to completed and p2 to cancelled
    client.patch(f"/api/v1/pickups/{p1_id}/status", json={"status": "completed"})
    client.patch(f"/api/v1/pickups/{p2_id}/status", json={"status": "cancelled"})

    # 4. Fetch route for this vehicle
    res = client.get(f"/api/v1/fleet/route?vehicle_id={veh_id}")
    assert res.status_code == 200
    data = res.json()["data"]

    stop_pickup_ids = [s["pickup_id"] for s in data["stops"]]
    assert p3_id in stop_pickup_ids
    assert p1_id not in stop_pickup_ids
    assert p2_id not in stop_pickup_ids


def test_priority_aware_ordering(client: TestClient) -> None:
    """Verify urgent/hazardous stops are prioritized on the route before lower-risk streams."""
    depot_lat, depot_lon = 12.90, 77.50
    veh_id = "VEH-PRIORITY-ORDER"

    # Stop A: Dry recyclable (low risk weight 20 pts) located VERY CLOSE to depot (0.01 deg away)
    r_dry = client.post("/api/v1/waste-reports", json={
        "category": "dry_recyclable",
        "description": "Nearby dry waste",
        "latitude": 12.91,
        "longitude": 77.51,
        "estimated_weight_kg": 5.0,
    }).json()["data"]["id"]
    p_dry = client.post("/api/v1/pickups", json={"report_id": r_dry, "vehicle_id": veh_id}).json()["data"]["id"]

    # Stop B: Hazardous waste (urgent risk weight 100 pts) located FURTHER from depot (0.05 deg away)
    r_haz = client.post("/api/v1/waste-reports", json={
        "category": "hazardous",
        "description": "Urgent chemical solvents",
        "latitude": 12.95,
        "longitude": 77.55,
        "estimated_weight_kg": 4.0,
    }).json()["data"]["id"]
    p_haz = client.post("/api/v1/pickups", json={"report_id": r_haz, "vehicle_id": veh_id}).json()["data"]["id"]

    # Request route from depot
    res = client.get(f"/api/v1/fleet/route?start_lat={depot_lat}&start_lon={depot_lon}&vehicle_id={veh_id}")
    assert res.status_code == 200
    stops = res.json()["data"]["stops"]

    # Stop 1 must be hazardous (URGENT tier) despite being geographically farther from start
    assert len(stops) == 2
    assert stops[0]["pickup_id"] == p_haz
    assert stops[0]["priority_tier"] == "URGENT"
    assert stops[0]["category"] == "hazardous"

    # Stop 2 is the dry recyclable stop
    assert stops[1]["pickup_id"] == p_dry
    assert stops[1]["category"] == "dry_recyclable"


def test_four_compartment_capacity_and_overflow(client: TestClient) -> None:
    """Enforce individual compartment limits and verify capacity overflow handling."""
    veh_id = "VEH-CAPACITY-ISOLATED"

    # Hazardous compartment limit: 10 kg
    # Stop 1: Hazardous 7.0 kg (fits, 7 / 10 kg)
    r_h1 = client.post("/api/v1/waste-reports", json={
        "category": "hazardous",
        "description": "Hazardous batch 1",
        "latitude": 12.94,
        "longitude": 77.64,
        "estimated_weight_kg": 7.0,
    }).json()["data"]["id"]
    p_h1 = client.post("/api/v1/pickups", json={"report_id": r_h1, "vehicle_id": veh_id}).json()["data"]["id"]

    # Stop 2: Hazardous 5.0 kg (exceeds remaining 3.0 kg, overflow!)
    r_h2 = client.post("/api/v1/waste-reports", json={
        "category": "hazardous",
        "description": "Hazardous batch 2",
        "latitude": 12.95,
        "longitude": 77.65,
        "estimated_weight_kg": 5.0,
    }).json()["data"]["id"]
    p_h2 = client.post("/api/v1/pickups", json={"report_id": r_h2, "vehicle_id": veh_id}).json()["data"]["id"]

    # Stop 3: Wet organic 50.0 kg (fits in wet_organic 100 kg compartment independently)
    r_w1 = client.post("/api/v1/waste-reports", json={
        "category": "wet_organic",
        "description": "Kitchen organic waste",
        "latitude": 12.96,
        "longitude": 77.66,
        "estimated_weight_kg": 50.0,
    }).json()["data"]["id"]
    p_w1 = client.post("/api/v1/pickups", json={"report_id": r_w1, "vehicle_id": veh_id}).json()["data"]["id"]

    res = client.get(f"/api/v1/fleet/route?vehicle_id={veh_id}")
    assert res.status_code == 200
    data = res.json()["data"]

    planned_ids = [s["pickup_id"] for s in data["stops"]]
    unassigned_ids = [u["pickup_id"] for u in data["unassigned_pickups"]]

    # p_h1 and p_w1 must be planned
    assert p_h1 in planned_ids
    assert p_w1 in planned_ids

    # p_h2 must be flagged unassigned due to hazardous capacity overflow
    assert p_h2 in unassigned_ids
    overflow_item = next(u for u in data["unassigned_pickups"] if u["pickup_id"] == p_h2)
    assert "Capacity overflow for compartment 'hazardous'" in overflow_item["reason"]

    # Check final load
    load = data["final_compartment_load"]
    assert load["hazardous"] == 7.0
    assert load["wet_organic"] == 50.0
    assert load["dry_recyclable"] == 0.0
    assert load["sanitary"] == 0.0

    # Check utilization percentages
    util = data["final_compartment_utilization"]
    assert util["hazardous_percent"] == 70.0  # 7 / 10
    assert util["wet_organic_percent"] == 50.0  # 50 / 100


def test_invalid_coordinates_reported_as_unroutable(client: TestClient, db_session_fixture) -> None:
    """Verify that null-island or out-of-bounds coordinates are excluded and reported as unroutable."""
    veh_id = "VEH-INVALID-TEST"

    # Insert a report with (0.0, 0.0) Null Island coordinates directly
    report_null = WasteReport(
        category="wet_organic",
        description="Null island coordinate report",
        latitude=0.0,
        longitude=0.0,
        status="reported",
    )
    db_session_fixture.add(report_null)
    db_session_fixture.commit()

    pickup_null = PickupRequest(
        report_id=report_null.id,
        vehicle_id=veh_id,
        status="scheduled",
    )
    db_session_fixture.add(pickup_null)
    db_session_fixture.commit()
    null_id_str = str(pickup_null.id)

    res = client.get(f"/api/v1/fleet/route?vehicle_id={veh_id}")
    assert res.status_code == 200
    data = res.json()["data"]

    assert len(data["stops"]) == 0
    assert len(data["unassigned_pickups"]) >= 1
    unassigned = next(u for u in data["unassigned_pickups"] if u["pickup_id"] == null_id_str)
    assert "Null Island" in unassigned["reason"]


def test_depot_vs_fallback_origin_documentation(client: TestClient) -> None:
    """Ensure depot coordinates are accurately described and fallback is clearly documented."""
    veh_id = "VEH-DEPOT-TEST"

    # Create one pickup so a fallback anchor can exist
    r = client.post("/api/v1/waste-reports", json={
        "category": "dry_recyclable",
        "description": "Depot test item",
        "latitude": 12.98,
        "longitude": 77.58,
        "estimated_weight_kg": 5.0,
    }).json()["data"]["id"]
    client.post("/api/v1/pickups", json={"report_id": r, "vehicle_id": veh_id})

    # 1. With depot provided
    depot_res = client.get(f"/api/v1/fleet/route?start_lat=12.97&start_lon=77.59&vehicle_id={veh_id}")
    assert depot_res.status_code == 200
    depot_origin = depot_res.json()["data"]["start_origin"]
    assert depot_origin["origin_type"] == "provided_depot"
    assert "provided dispatch depot" in depot_origin["description"]

    # 2. When depot is omitted, verify fallback_first_pickup explanation
    no_depot_res = client.get(f"/api/v1/fleet/route?vehicle_id={veh_id}")
    assert no_depot_res.status_code == 200
    fallback_origin = no_depot_res.json()["data"]["start_origin"]
    assert fallback_origin["origin_type"] == "fallback_first_pickup"
    assert "not a physical municipal depot" in fallback_origin["description"]
