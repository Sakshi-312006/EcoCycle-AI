"""Pillar 4: Automated Testing Suite for Garbage-Pile Detection, Smart Collection Routing & Verified Cleanliness."""

import uuid
from starlette.testclient import TestClient

from app.schemas.garbage_piles import PileSizeEnum, SeverityLevelEnum
from app.services.garbage_pile_service import GarbagePileService


def test_create_garbage_pile_report_success(client: TestClient) -> None:
    """Ensure valid illegal garbage pile report is created with deterministic priority scoring."""
    payload = {
        "category": "wet_organic",
        "pile_size": "medium",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "Opposite City Market Gate 4",
        "ward_number": "Ward 109",
        "description": "Large pile of decomposing vegetable and fruit waste near vegetable stalls",
        "image_url": "https://storage.ecocycle.internal/uploads/pile_before_01.jpg",
        "estimated_weight_kg": 45.0,
    }
    res = client.post("/api/v1/garbage-piles/reports", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["category"] == "wet_organic"
    assert data["report_type"] == "illegal_dump"
    assert data["status"] == "reported"
    assert data["estimated_weight_kg"] == 45.0
    assert data["latitude"] == 12.9716
    assert data["longitude"] == 77.5946
    assert data["severity"] in ["MEDIUM", "HIGH", "CRITICAL"]
    assert "severity_details" in data
    assert data["severity_details"]["category_hazard_score"] == 40.0


def test_create_garbage_pile_invalid_coordinates(client: TestClient) -> None:
    """Reject reports with latitude or longitude outside valid geographic bounds."""
    # Latitude > 90
    bad_lat = {
        "category": "dry_recyclable",
        "latitude": 95.0,
        "longitude": 77.59,
        "description": "Cardboard boxes dumped on pavement",
    }
    res1 = client.post("/api/v1/garbage-piles/reports", json=bad_lat)
    assert res1.status_code == 422

    # Longitude > 180
    bad_lon = {
        "category": "dry_recyclable",
        "latitude": 12.97,
        "longitude": 185.0,
        "description": "Cardboard boxes dumped on pavement",
    }
    res2 = client.post("/api/v1/garbage-piles/reports", json=bad_lon)
    assert res2.status_code == 422


def test_create_garbage_pile_invalid_category(client: TestClient) -> None:
    """Reject reports using unapproved or non-statutory waste stream categories."""
    payload = {
        "category": "radioactive_sludge",
        "latitude": 12.97,
        "longitude": 77.59,
        "description": "Industrial barrels dumped by roadside",
    }
    res = client.post("/api/v1/garbage-piles/reports", json=payload)
    assert res.status_code == 422


def test_duplicate_check_endpoint(client: TestClient) -> None:
    """Verify proximity duplicate check returns candidates within radius without citizen private info."""
    # Create base report
    res_base = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "dry_recyclable",
            "pile_size": "large",
            "latitude": 12.9500,
            "longitude": 77.5500,
            "description": "Plastic containers and cartons dumped behind bus stop",
            "ecopass_id": "ECOPASS-SECRET-1234",
        },
    )
    assert res_base.status_code == 201

    # Check duplicates 20m away
    dup_res = client.post(
        "/api/v1/garbage-piles/check-duplicate",
        json={
            "latitude": 12.9501,
            "longitude": 77.5501,
            "category": "dry_recyclable",
            "radius_meters": 100.0,
        },
    )
    assert dup_res.status_code == 200
    dup_data = dup_res.json()["data"]
    assert dup_data["is_duplicate"] is True
    assert dup_data["candidates_found"] >= 1
    first_candidate = dup_data["candidates"][0]
    assert "distance_meters" in first_candidate
    assert first_candidate["distance_meters"] <= 100.0
    # Strict privacy: ensure private citizen information is not exposed
    assert "ecopass_id" not in first_candidate
    assert "citizen_name" not in first_candidate
    assert "phone" not in first_candidate


def test_duplicate_report_conflict_and_override(client: TestClient) -> None:
    """Confirm duplicate detection returns 409 Conflict, but force_create=True allows separate pile."""
    base_coords = {"latitude": 12.9600, "longitude": 77.5600}

    # 1. First report
    res1 = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "sanitary",
            "latitude": base_coords["latitude"],
            "longitude": base_coords["longitude"],
            "description": "Sanitary waste bags dumped in vacant lot",
        },
    )
    assert res1.status_code == 201

    # 2. Second report very close (~15m away), without force_create -> 409 Conflict
    res2 = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "sanitary",
            "latitude": base_coords["latitude"] + 0.0001,
            "longitude": base_coords["longitude"] + 0.0001,
            "description": "Another bag spotted near the same vacant lot",
            "force_create": False,
        },
    )
    assert res2.status_code == 409
    body2 = res2.json()
    assert "duplicate" in body2["message"].lower()

    # 3. Third report with force_create=True -> 201 Created
    res3 = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "sanitary",
            "latitude": base_coords["latitude"] + 0.0001,
            "longitude": base_coords["longitude"] + 0.0001,
            "description": "Distinct separate pile across the ditch confirmed by sanitary worker",
            "force_create": True,
        },
    )
    assert res3.status_code == 201
    assert res3.json()["data"]["id"] != res1.json()["data"]["id"]


def test_rule_based_severity_calculation() -> None:
    """Verify transparent severity scoring rules without automated CV claims."""
    # Small dry recyclable, 0 hours aging
    low_sev = GarbagePileService.calculate_severity(
        category="dry_recyclable",
        pile_size="small",
        aging_hours=0.0,
    )
    # size=15, hazard=20, aging=0 -> 35 -> LOW
    assert low_sev.total_score == 35.0
    assert low_sev.priority_tier == SeverityLevelEnum.LOW

    # Critical hazardous waste, 24 hours aging
    crit_sev = GarbagePileService.calculate_severity(
        category="hazardous",
        pile_size="critical",
        aging_hours=24.0,
    )
    # size=90, hazard=100, aging=48 -> 238 -> CRITICAL
    assert crit_sev.total_score >= 120.0
    assert crit_sev.priority_tier == SeverityLevelEnum.CRITICAL
    assert "statutory rule-based" in crit_sev.methodology.lower()


def test_list_and_get_garbage_piles(client: TestClient) -> None:
    """Verify listing and retrieving specific garbage pile reports."""
    # Create report
    res_create = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "hazardous",
            "pile_size": "small",
            "latitude": 12.9800,
            "longitude": 77.5800,
            "description": "Discarded car battery with chemical leakage",
            "force_create": True,
        },
    )
    report_id = res_create.json()["data"]["id"]

    # List all
    list_res = client.get("/api/v1/garbage-piles/reports")
    assert list_res.status_code == 200
    items = list_res.json()["data"]
    assert any(i["id"] == report_id for i in items)

    # Filter by category
    filter_res = client.get("/api/v1/garbage-piles/reports?category=hazardous")
    assert filter_res.status_code == 200
    filtered_items = filter_res.json()["data"]
    assert all(i["category"] == "hazardous" for i in filtered_items)

    # Get by ID
    get_res = client.get(f"/api/v1/garbage-piles/reports/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == report_id


def test_vehicle_recommendation_and_authorization(client: TestClient) -> None:
    """Ensure vehicle recommendations enforce statutory stream certifications and capacity."""
    # 1. Hazardous waste pile: ECO-CART-01 must NOT be assigned; HAZMAT-VAN-03 should be recommended
    haz_res = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "hazardous",
            "pile_size": "medium",
            "latitude": 12.9900,
            "longitude": 77.5900,
            "description": "E-waste and toxic printer toner cartridges dumped",
            "estimated_weight_kg": 25.0,
            "force_create": True,
        },
    )
    haz_id = haz_res.json()["data"]["id"]

    rec_res = client.post(f"/api/v1/garbage-piles/reports/{haz_id}/recommend-vehicle")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()["data"]
    assert rec_data["is_assigned"] is True
    assert rec_data["recommended_vehicle_id"] == "HAZMAT-VAN-03"

    # 2. Assigning unauthorized vehicle ECO-CART-01 to hazardous pile should be rejected
    bad_assign = client.post(
        f"/api/v1/garbage-piles/reports/{haz_id}/assign-vehicle",
        json={"vehicle_id": "ECO-CART-01"},
    )
    assert bad_assign.status_code == 422
    assert "unauthorized" in bad_assign.json()["message"].lower()

    # 3. Assigning authorized HAZMAT-VAN-03 should succeed
    good_assign = client.post(
        f"/api/v1/garbage-piles/reports/{haz_id}/assign-vehicle",
        json={
            "vehicle_id": "HAZMAT-VAN-03",
            "collector_id": "COLLECTOR-HAZ-09",
            "collector_name": "R. Kumar",
        },
    )
    assert good_assign.status_code == 200
    assert good_assign.json()["data"]["status"] == "assigned"
    assert good_assign.json()["data"]["assigned_vehicle_id"] == "HAZMAT-VAN-03"


def test_vehicle_recommendation_excess_capacity(client: TestClient) -> None:
    """Return unassigned status with clear operational explanation when weight exceeds capacity."""
    huge_res = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "hazardous",
            "pile_size": "critical",
            "latitude": 12.9100,
            "longitude": 77.5200,
            "description": "Massive illegal industrial solvent dumping exceeding normal van limits",
            "estimated_weight_kg": 300.0,  # Max hazmat van capacity is 60 kg for hazardous
            "force_create": True,
        },
    )
    huge_id = huge_res.json()["data"]["id"]

    rec_res = client.post(f"/api/v1/garbage-piles/reports/{huge_id}/recommend-vehicle")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()["data"]
    assert rec_data["is_assigned"] is False
    assert "exceeds" in rec_data["reason"].lower() or "no suitable vehicle" in rec_data["reason"].lower()


def test_cleanup_verification_and_zero_credits(client: TestClient) -> None:
    """Verify cleanup issues SHA-256 integrity hash, updates status to resolved, and awards 0 credits."""
    # 1. Create pile report with an ecopass_id
    create_res = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "wet_organic",
            "pile_size": "large",
            "latitude": 12.9350,
            "longitude": 77.6150,
            "description": "Rotting kitchen waste pile along alleyway",
            "image_url": "https://storage.ecocycle.internal/uploads/before_pile_42.jpg",
            "ecopass_id": "CITIZEN-ECOPASS-99",
            "force_create": True,
        },
    )
    pile_id = create_res.json()["data"]["id"]

    # 2. Certify cleanup with before/after photos and scale weight
    verify_res = client.post(
        f"/api/v1/garbage-piles/reports/{pile_id}/verify-cleanup",
        json={
            "after_image_url": "https://storage.ecocycle.internal/uploads/after_pile_42_clean.jpg",
            "verifier_id": "INSPECTOR-BANGALORE-SOUTH-04",
            "actual_weight_kg": 85.5,
            "notes": "Alleyway cleared, disinfected with lime powder, zero residue remaining.",
        },
    )
    assert verify_res.status_code == 200
    v_data = verify_res.json()["data"]
    assert v_data["status"] == "resolved"
    assert v_data["before_image_url"] == "https://storage.ecocycle.internal/uploads/before_pile_42.jpg"
    assert v_data["after_image_url"] == "https://storage.ecocycle.internal/uploads/after_pile_42_clean.jpg"
    assert v_data["actual_weight_kg"] == 85.5
    assert len(v_data["integrity_hash"]) == 64  # SHA-256 64-char hex
    # STRICT ANTI-FRAUD: Zero EcoCredits awarded for simply reporting/verifying illegal piles
    assert v_data["ecocredits_awarded"] == 0

    # 3. Check report status is updated to resolved
    get_res = client.get(f"/api/v1/garbage-piles/reports/{pile_id}")
    assert get_res.json()["data"]["status"] == "resolved"

    # 4. Attempting repeated verification on the same resolved report must fail (409 Conflict)
    repeat_res = client.post(
        f"/api/v1/garbage-piles/reports/{pile_id}/verify-cleanup",
        json={
            "after_image_url": "https://storage.ecocycle.internal/uploads/after_again.jpg",
            "verifier_id": "INSPECTOR-BANGALORE-SOUTH-04",
            "actual_weight_kg": 85.5,
        },
    )
    assert repeat_res.status_code == 409
    assert "already been verified" in repeat_res.json()["message"].lower()


def test_garbage_pile_dashboard(client: TestClient) -> None:
    """Verify municipal illegal dumping dashboard aggregates metrics from database records."""
    res = client.get("/api/v1/garbage-piles/dashboard")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "total_reports" in data
    assert "total_illegal_piles" in data
    assert "status_breakdown" in data
    assert "priority_distribution" in data
    assert "potential_duplicate_candidates_count" in data
    assert "vehicle_assignment_stats" in data
    assert "total_verified_cleanups" in data
    assert "total_cleaned_weight_kg" in data
    assert data["total_illegal_piles"] >= 1
    assert data["total_verified_cleanups"] >= 1


def test_upload_garbage_pile_image(client: TestClient) -> None:
    """Ensure photographic evidence can be uploaded securely via image upload endpoint."""
    fake_jpeg = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00\xFF\xD9"
    files = {"file": ("pile_evidence.jpg", fake_jpeg, "image/jpeg")}
    res = client.post("/api/v1/garbage-piles/upload-image", files=files)
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert "file_url" in body["data"]
    assert body["data"]["content_type"] == "image/jpeg"


def test_vehicle_assignment_capacity_overflow(client: TestClient) -> None:
    """Ensure vehicle assignment fails when pile weight exceeds compartment capacity."""
    # ECO-CART-01 max dry recyclable compartment capacity is 30.0 kg
    res_pile = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "dry_recyclable",
            "pile_size": "medium",
            "latitude": 12.9250,
            "longitude": 77.5850,
            "description": "Heavy heap of cardboard and plastics",
            "estimated_weight_kg": 35.0,  # 35 kg > 30 kg compartment capacity
            "force_create": True,
        },
    )
    assert res_pile.status_code == 201
    pile_id = res_pile.json()["data"]["id"]

    res_assign = client.post(
        f"/api/v1/garbage-piles/reports/{pile_id}/assign-vehicle",
        json={"vehicle_id": "ECO-CART-01"},
    )
    assert res_assign.status_code == 422
    assert "capacity overflow" in res_assign.json()["message"].lower()


def test_fleet_route_incorporates_assigned_piles_and_excludes_resolved(client: TestClient) -> None:
    """Verify fleet routing algorithm routes assigned open piles and strictly excludes resolved piles."""
    # 1. Create a wet organic pile (20 kg)
    res_pile = client.post(
        "/api/v1/garbage-piles/reports",
        json={
            "category": "wet_organic",
            "pile_size": "medium",
            "latitude": 12.9300,
            "longitude": 77.6100,
            "description": "Vegetable waste pile on curb",
            "estimated_weight_kg": 20.0,
            "force_create": True,
        },
    )
    assert res_pile.status_code == 201
    pile_id = res_pile.json()["data"]["id"]

    # 2. Assign to TRUCK-COMPACTOR-02
    res_assign = client.post(
        f"/api/v1/garbage-piles/reports/{pile_id}/assign-vehicle",
        json={"vehicle_id": "TRUCK-COMPACTOR-02"},
    )
    assert res_assign.status_code == 200

    # 3. Check route plan includes this stop
    route_res = client.get("/api/v1/fleet/route?vehicle_id=TRUCK-COMPACTOR-02")
    assert route_res.status_code == 200
    stops = route_res.json()["data"]["stops"]
    stop_report_ids = [s["report_id"] for s in stops]
    assert pile_id in stop_report_ids

    # 4. Verify cleanup (marks resolved)
    v_res = client.post(
        f"/api/v1/garbage-piles/reports/{pile_id}/verify-cleanup",
        json={
            "after_image_url": "https://storage.ecocycle.internal/uploads/cleared_alley.jpg",
            "verifier_id": "DRIVER-TRUCK-02",
            "actual_weight_kg": 20.0,
        },
    )
    assert v_res.status_code == 200
    assert v_res.json()["data"]["status"] == "resolved"

    # 5. Check route plan again: the resolved pile must be excluded
    route_res2 = client.get("/api/v1/fleet/route?vehicle_id=TRUCK-COMPACTOR-02")
    assert route_res2.status_code == 200
    stops2 = route_res2.json()["data"]["stops"]
    stop_report_ids2 = [s["report_id"] for s in stops2]
    assert pile_id not in stop_report_ids2

