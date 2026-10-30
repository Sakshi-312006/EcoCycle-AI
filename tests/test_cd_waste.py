"""Pillar 3: Construction & Demolition (C&D) Estimation and Material tests."""

import uuid
from starlette.testclient import TestClient


def test_cd_estimate_with_dimensions(client: TestClient) -> None:
    """Test formula-based geometric volume and tonnage estimation."""
    payload = {
        "project_name": "Metro Extension Demolition",
        "location": "Site 4B, Outer Ring Road",
        "material_type": "concrete_rubble",
        "length_m": 10.0,
        "width_m": 4.0,
        "height_m": 2.0,
    }
    response = client.post("/api/v1/cd-waste/estimates", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]

    # 10 * 4 * 2 = 80 m3
    assert data["estimated_volume_m3"] == 80.0
    # 80 m3 * 1500 kg/m3 = 120,000 kg
    assert data["estimated_mass_kg"] == 120000.0
    assert data["estimated_metric_tons"] == 120.0
    assert data["estimation_method"] == "formula_geometric_bounding_box"
    assert "Formula-based estimate" in data["disclaimer"]
    assert "Not AI or 3D point-cloud scanned" in data["disclaimer"]


def test_cd_estimate_with_user_volume(client: TestClient) -> None:
    """Test estimate using direct user volume when dimensions are irregular."""
    payload = {
        "project_name": "Commercial Renovation Pile",
        "location": "Indiranagar 100ft Road",
        "material_type": "brick_masonry",
        "user_volume_m3": 15.0,
    }
    response = client.post("/api/v1/cd-waste/estimates", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["estimated_volume_m3"] == 15.0
    # 15 m3 * 1800 kg/m3 = 27,000 kg (27 metric tons)
    assert data["estimated_mass_kg"] == 27000.0
    assert data["estimated_metric_tons"] == 27.0


def test_cd_estimate_validation_error(client: TestClient) -> None:
    """Ensure missing both dimensions and user volume raises HTTP 422."""
    payload = {
        "project_name": "Incomplete Demolition Site",
        "location": "Whitefield",
        "material_type": "mixed_cd",
    }
    response = client.post("/api/v1/cd-waste/estimates", json=payload)
    assert response.status_code == 422
    assert "Must provide either" in response.json()["message"] or "details" in response.json()


def test_cd_materials_crud(client: TestClient) -> None:
    """Test creating, listing, and updating reusable salvaged materials."""
    # 1. Create listing
    mat_payload = {
        "title": "Clean Red Clay Bricks",
        "material_category": "bricks",
        "quantity": 1500.0,
        "unit": "pieces",
        "condition": "reusable_excellent",
        "price_inr": 7500.0,
        "location": "Koramangala Site 6",
        "contact_phone": "+91-9876543210",
    }
    create_res = client.post("/api/v1/cd-waste/materials", json=mat_payload)
    assert create_res.status_code == 201
    mat = create_res.json()["data"]
    mat_id = mat["id"]
    assert mat["material_category"] == "bricks"
    assert mat["status"] == "available"

    # 2. List with category filter
    list_res = client.get("/api/v1/cd-waste/materials?category=bricks")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # 3. Update status to reserved
    patch_res = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=reserved")
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "reserved"


def test_cd_material_status_whitespace_normalization(client: TestClient) -> None:
    """Ensure leading and trailing whitespace is stripped from status_value before persisting."""
    # 1. Create material
    mat_res = client.post(
        "/api/v1/cd-waste/materials",
        json={
            "title": "Ceramic Floor Tiles - 40 sq meters",
            "material_category": "tiles",
            "quantity": 40.0,
            "unit": "sq_meters",
            "condition": "reusable_good",
            "price_inr": 2000.0,
            "location": "Jayanagar 4th Block",
        },
    )
    mat_id = mat_res.json()["data"]["id"]

    # 2. Update with trailing whitespace: 'reserved '
    patch_res = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=reserved%20")
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "reserved"

    # Verify GET returns normalized status without trailing space
    get_res = client.get(f"/api/v1/cd-waste/materials/{mat_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["status"] == "reserved"

    # 3. Update with both leading and trailing whitespace: '  collected  '
    patch_res2 = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=%20%20collected%20%20")
    assert patch_res2.status_code == 200
    assert patch_res2.json()["data"]["status"] == "collected"

    # Verify GET returns normalized 'collected'
    get_res2 = client.get(f"/api/v1/cd-waste/materials/{mat_id}")
    assert get_res2.status_code == 200
    assert get_res2.json()["data"]["status"] == "collected"

    # 4. Update with leading whitespace: '  available'
    patch_res3 = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=%20%20available")
    assert patch_res3.status_code == 200
    assert patch_res3.json()["data"]["status"] == "available"

    get_res3 = client.get(f"/api/v1/cd-waste/materials/{mat_id}")
    assert get_res3.status_code == 200
    assert get_res3.json()["data"]["status"] == "available"


def test_cd_material_status_invalid_values(client: TestClient) -> None:
    """Ensure invalid status values are rejected with HTTP 422."""
    mat_res = client.post(
        "/api/v1/cd-waste/materials",
        json={
            "title": "Granite Slabs",
            "material_category": "other",
            "quantity": 10.0,
            "unit": "pieces",
            "condition": "reusable_good",
            "price_inr": 5000.0,
            "location": "Hebbal",
        },
    )
    mat_id = mat_res.json()["data"]["id"]

    # Arbitrary invalid status
    res1 = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=damaged")
    assert res1.status_code == 422
    data1 = res1.json()
    assert data1["success"] is False
    assert "available, reserved, collected" in data1["message"]

    # Empty whitespace status
    res2 = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=%20%20")
    assert res2.status_code == 422
    data2 = res2.json()
    assert data2["success"] is False

    # Status with invalid casing or typo
    res3 = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=RESERVED")
    assert res3.status_code == 422

    # Status with typo
    res4 = client.patch(f"/api/v1/cd-waste/materials/{mat_id}/status?status_value=reserve")
    assert res4.status_code == 422


def test_cd_material_status_nonexistent_id(client: TestClient) -> None:
    """Ensure updating status of a nonexistent material returns HTTP 404."""
    nonexistent_id = str(uuid.uuid4())
    res = client.patch(f"/api/v1/cd-waste/materials/{nonexistent_id}/status?status_value=reserved")
    assert res.status_code == 404
    data = res.json()
    assert data["success"] is False
    assert data["error_code"] == "RESOURCE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Stream A & End-to-End Disposal Tracking Tests
# ---------------------------------------------------------------------------


def test_cd_upload_image(client: TestClient) -> None:
    """Ensure photographic evidence can be uploaded for C&D rubble or salvage."""
    fake_jpeg = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00\xFF\xD9"
    files = {"file": ("rubble_pile.jpg", fake_jpeg, "image/jpeg")}
    res = client.post("/api/v1/cd-waste/upload-image", files=files)
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert "file_url" in body["data"]
    assert body["data"]["content_type"] == "image/jpeg"


def test_cd_waste_report_creation_with_dimensions(client: TestClient) -> None:
    """Ensure C&D rubble report is created with geometric dimensions and density calculations."""
    payload = {
        "project_name": "Metro Station Foundation Demolition",
        "contractor_name": "Larsen Infrastructure Ltd",
        "contact_phone": "+91-9876543210",
        "material_category": "broken_concrete",
        "description": "Reinforced concrete footing rubble from pillar demolition",
        "image_url": "https://storage.ecocycle.internal/uploads/rubble_01.jpg",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "address": "Outer Ring Road, Kadubeesanahalli",
        "landmark": "Near Cisco Campus",
        "length_m": 4.0,
        "width_m": 2.5,
        "height_m": 1.0,
        "request_pickup": False,
    }
    res = client.post("/api/v1/cd-waste/reports", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]

    # Volume = 4.0 * 2.5 * 1.0 = 10.0 m³
    assert data["estimated_volume_m3"] == 10.0
    # broken_concrete density = 1.5 tonnes/m³
    assert data["bulk_density_tonnes_m3"] == 1.5
    # Weight = 10.0 * 1.5 = 15.0 tonnes (15,000 kg)
    assert data["estimated_weight_tonnes"] == 15.0
    assert data["estimated_weight_kg"] == 15000.0
    assert data["status"] == "reported"
    assert data["pickup_id"] is None


def test_cd_waste_report_creation_with_direct_volume(client: TestClient) -> None:
    """Ensure C&D report calculates weight using direct volume and custom/default density."""
    payload = {
        "project_name": "Commercial Building Brickwork Renovation",
        "material_category": "brick_masonry",
        "description": "Irregular heap of broken red clay bricks and mortar",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "MG Road commercial complex",
        "user_volume_m3": 5.0,
        "request_pickup": True,
    }
    res = client.post("/api/v1/cd-waste/reports", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]

    assert data["estimated_volume_m3"] == 5.0
    # brick_masonry density = 1.8 tonnes/m³ -> 5.0 * 1.8 = 9.0 tonnes
    assert data["bulk_density_tonnes_m3"] == 1.8
    assert data["estimated_weight_tonnes"] == 9.0
    assert data["status"] == "pickup_requested"
    assert data["pickup_id"] is not None


def test_cd_waste_report_invalid_coordinates(client: TestClient) -> None:
    """Reject C&D reports with coordinates outside valid geographic bounds."""
    # Latitude > 90
    bad_lat = {
        "project_name": "Invalid Site",
        "material_category": "broken_concrete",
        "description": "Debris pile",
        "latitude": 95.0,
        "longitude": 77.59,
        "address": "North Pole",
        "user_volume_m3": 2.0,
    }
    res1 = client.post("/api/v1/cd-waste/reports", json=bad_lat)
    assert res1.status_code == 422

    # Longitude > 180
    bad_lon = {
        "project_name": "Invalid Site",
        "material_category": "broken_concrete",
        "description": "Debris pile",
        "latitude": 12.97,
        "longitude": 185.0,
        "address": "Pacific Ocean",
        "user_volume_m3": 2.0,
    }
    res2 = client.post("/api/v1/cd-waste/reports", json=bad_lon)
    assert res2.status_code == 422


def test_cd_waste_report_invalid_measurements(client: TestClient) -> None:
    """Reject C&D reports with negative or missing dimensions and direct volume."""
    # Missing both dimensions and direct volume
    payload_missing = {
        "project_name": "Incomplete Measurements Site",
        "material_category": "mixed_cd_rubble",
        "description": "Rubble pile with no dimensions given",
        "latitude": 12.92,
        "longitude": 77.60,
        "address": "Koramangala",
    }
    res1 = client.post("/api/v1/cd-waste/reports", json=payload_missing)
    assert res1.status_code == 422

    # Negative dimension
    payload_negative = {
        "project_name": "Negative Measurements Site",
        "material_category": "mixed_cd_rubble",
        "description": "Rubble pile with negative length",
        "latitude": 12.92,
        "longitude": 77.60,
        "address": "Koramangala",
        "length_m": -5.0,
        "width_m": 2.0,
        "height_m": 1.0,
    }
    res2 = client.post("/api/v1/cd-waste/reports", json=payload_negative)
    assert res2.status_code == 422

    # Excessive dimension > 100m
    payload_excess = {
        "project_name": "Excessive Measurements Site",
        "material_category": "mixed_cd_rubble",
        "description": "Rubble pile over 100m long",
        "latitude": 12.92,
        "longitude": 77.60,
        "address": "Koramangala",
        "length_m": 150.0,
        "width_m": 2.0,
        "height_m": 1.0,
    }
    res3 = client.post("/api/v1/cd-waste/reports", json=payload_excess)
    assert res3.status_code == 422


def test_cd_vehicle_recommendation_and_assignment(client: TestClient) -> None:
    """Recommend suitable heavy tipper vehicle for rubble and assign it."""
    # Create report with 3.0 m³ of mixed C&D (1.3 t/m³ -> 3.9 tonnes)
    res_create = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Flyover Repair Demolition",
            "material_category": "mixed_cd_rubble",
            "description": "Concrete and brick fragments from barrier wall removal",
            "latitude": 12.9400,
            "longitude": 77.6100,
            "address": "Silk Board Junction",
            "user_volume_m3": 3.0,
            "request_pickup": True,
        },
    )
    report_id = res_create.json()["data"]["id"]

    # 1. Recommend vehicle
    rec_res = client.post(f"/api/v1/cd-waste/reports/{report_id}/recommend-vehicle")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()["data"]
    assert rec_data["is_assigned"] is True
    # 3.9 tonnes <= 5.0 tonnes -> TIPPER-TRUCK-05
    assert rec_data["recommended_vehicle_id"] == "TIPPER-TRUCK-05"
    assert rec_data["max_capacity_tonnes"] == 5.0

    # 2. Assign TIPPER-TRUCK-05
    assign_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/assign-vehicle",
        json={
            "vehicle_id": "TIPPER-TRUCK-05",
            "collector_id": "DRIVER-C&D-11",
            "collector_name": "S. Patil",
        },
    )
    assert assign_res.status_code == 200
    data = assign_res.json()["data"]
    assert data["status"] == "assigned"
    assert data["assigned_vehicle_id"] == "TIPPER-TRUCK-05"


def test_cd_vehicle_incompatible_and_overflow_rejected(client: TestClient) -> None:
    """Ensure e-carts/compactor trucks are rejected, and payload capacity overflow is blocked."""
    # 1. Create 4.0 tonne report
    res_create = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Hospital Annex Demolition",
            "material_category": "broken_concrete",
            "description": "Massive concrete slabs",
            "latitude": 12.9500,
            "longitude": 77.5800,
            "address": "Jayanagar",
            "user_volume_m3": 3.0,  # 3.0 * 1.5 = 4.5 tonnes
        },
    )
    report_id = res_create.json()["data"]["id"]

    # 2. Attempt assigning ECO-CART-01 -> 422 Unprocessable (incompatible)
    bad_cart = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/assign-vehicle",
        json={"vehicle_id": "ECO-CART-01"},
    )
    assert bad_cart.status_code == 422
    assert "incompatible" in bad_cart.json()["message"].lower()

    # 3. Attempt assigning TRUCK-COMPACTOR-02 -> 422 Unprocessable (incompatible hydraulic compactor)
    bad_compactor = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/assign-vehicle",
        json={"vehicle_id": "TRUCK-COMPACTOR-02"},
    )
    assert bad_compactor.status_code == 422
    assert "incompatible" in bad_compactor.json()["message"].lower()

    # 4. Attempt assigning HEAVY-TIPPER-04 (max 1.0 tonne) for a 4.5 tonne load -> 422 Overflow
    overflow_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/assign-vehicle",
        json={"vehicle_id": "HEAVY-TIPPER-04"},
    )
    assert overflow_res.status_code == 422
    assert "capacity overflow" in overflow_res.json()["message"].lower()


def test_cd_end_to_end_chain_of_custody_and_discrepancy(client: TestClient) -> None:
    """Test full Stream A chain of custody: Report -> Assign -> Collect -> Facility Receipt -> Processing -> SHA-256 seal."""
    # 1. Create report (10.0 tonnes estimated)
    create_res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Bridge Deck Replacement",
            "contractor_name": "Karnataka Urban Infra",
            "material_category": "broken_concrete",
            "description": "Chipped bridge deck concrete aggregate",
            "latitude": 12.9600,
            "longitude": 77.6400,
            "address": "HAL Airport Road",
            "user_volume_m3": 6.67,  # 6.67 * 1.5 ≈ 10.0 tonnes
            "request_pickup": True,
        },
    )
    assert create_res.status_code == 201
    report_id = create_res.json()["data"]["id"]
    estimated_tonnes = create_res.json()["data"]["estimated_weight_tonnes"]

    # 2. Assign heavy dump truck (12.0 tonnes capacity)
    assign_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/assign-vehicle",
        json={"vehicle_id": "DUMP-TRUCK-06", "collector_id": "DRIVER-HEAVY-01"},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["data"]["status"] == "assigned"

    # 3. Record field collection
    collect_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/collect",
        json={
            "collector_id": "DRIVER-HEAVY-01",
            "collection_evidence_image_url": "https://storage.ecocycle.internal/uploads/loaded_truck_06.jpg",
            "actual_weight_tonnes": 10.2,
            "notes": "Truck loaded via front-end loader; tarp secured.",
        },
    )
    assert collect_res.status_code == 200
    assert collect_res.json()["data"]["status"] == "collected"
    assert collect_res.json()["data"]["collected_at"] is not None

    # 4. Record facility weighbridge receipt (actual scale weight: 10.45 tonnes)
    receipt_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/receive-facility",
        json={
            "facility_name": "BBMP Chiguru C&D Processing Plant, Bangalore South",
            "received_weight_tonnes": 10.45,
            "weighbridge_ticket_id": "WB-TICKET-2026-9811",
            "weighbridge_slip_url": "https://storage.ecocycle.internal/uploads/weighbridge_slip_9811.jpg",
            "notes": "Aggregate inspected. Clean concrete, negligible rebar contamination.",
        },
    )
    assert receipt_res.status_code == 200
    assert receipt_res.json()["data"]["status"] == "received_at_facility"
    assert receipt_res.json()["data"]["facility_received_weight_tonnes"] == 10.45

    # 5. Complete processing into recycled concrete aggregate
    proc_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/complete-processing",
        json={
            "output_material_type": "recycled_concrete_aggregate_20mm",
            "output_tonnes": 9.85,
            "processing_evidence": "Crusher Run Batch #CR-2026-B8; primary jaw + secondary cone crusher log attached.",
            "notes": "Passed 20mm sieve test. Slag and fines diverted to M-sand washing unit.",
        },
    )
    assert proc_res.status_code == 200
    proc_data = proc_res.json()["data"]
    assert proc_data["status"] == "processing_completed"
    assert proc_data["processing_status"] == "completed"
    assert proc_data["processing_completed_at"] is not None

    # 6. Retrieve digital disposal record & verify variance and SHA-256 seal
    disp_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/disposal-record")
    assert disp_res.status_code == 200
    disp_data = disp_res.json()["data"]
    assert disp_data["status"] == "processing_completed"
    assert disp_data["facility_name"] == "BBMP Chiguru C&D Processing Plant, Bangalore South"
    assert disp_data["facility_received_weight_tonnes"] == 10.45
    # Variance = 10.45 - estimated_tonnes
    expected_variance = round(10.45 - estimated_tonnes, 2)
    assert disp_data["weight_discrepancy_tonnes"] == expected_variance
    assert disp_data["processed_output_type"] == "recycled_concrete_aggregate_20mm"
    assert disp_data["processed_output_tonnes"] == 9.85
    assert len(disp_data["integrity_hash"]) == 64  # SHA-256 seal


def test_cd_lifecycle_transitions_invalid_order_and_duplicates(client: TestClient) -> None:
    """Ensure lifecycle stages cannot be skipped and repeated transitions are rejected."""
    # Create fresh report in reported status
    res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Pipeline Trench Rubble",
            "material_category": "broken_concrete",
            "description": "Trench rubble",
            "latitude": 12.92,
            "longitude": 77.61,
            "address": "BTM Layout",
            "user_volume_m3": 2.0,
        },
    )
    report_id = res.json()["data"]["id"]

    # 1. Attempting facility receipt BEFORE collection -> 422 Unprocessable
    bad_receipt = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/receive-facility",
        json={"facility_name": "Test Plant", "received_weight_tonnes": 3.0},
    )
    assert bad_receipt.status_code == 422
    assert "cannot record facility receipt before collection" in bad_receipt.json()["message"].lower()

    # 2. Attempting complete processing BEFORE facility receipt -> 422 Unprocessable
    bad_proc = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/complete-processing",
        json={"output_material_type": "aggregate", "output_tonnes": 2.5, "processing_evidence": "Log"},
    )
    assert bad_proc.status_code == 422
    assert "cannot complete processing before facility receipt" in bad_proc.json()["message"].lower()


def test_cd_dashboard_metrics(client: TestClient) -> None:
    """Verify C&D operational dashboard returns aggregates compiled directly from stored records."""
    res = client.get("/api/v1/cd-waste/dashboard")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "total_cd_reports" in data
    assert "reports_by_material" in data
    assert "total_pickups" in data
    assert "pickups_by_status" in data
    assert "total_estimated_volume_m3" in data
    assert "total_estimated_weight_tonnes" in data
    assert "total_collected_weight_tonnes" in data
    assert "material_awaiting_facility_receipt_tonnes" in data
    assert "material_awaiting_processing_tonnes" in data
    assert "total_processed_tonnes" in data
    assert "reusable_materials_listed_count" in data
    assert "reusable_materials_by_status" in data
    assert "reusable_materials_diverted_count" in data
    assert "disposal_stage_breakdown" in data
    assert data["total_cd_reports"] >= 1


def test_cd_collection_synchronizes_waste_report_status_and_prevents_duplicate(client: TestClient) -> None:
    """Fix 1: Verify collection synchronizes linked WasteReport.status to 'collected',

    updates PickupRequest to 'completed', and prevents duplicate collection attempts.
    """
    # 1. Create C&D rubble report with pickup requested
    create_res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Metro Viaduct Pier Demolition",
            "contractor_name": "L&T Construction",
            "contact_phone": "+91-9888877777",
            "material_category": "broken_concrete",
            "description": "Crushed concrete pier rubble",
            "latitude": 12.915,
            "longitude": 77.620,
            "address": "Silk Board Junction, Outer Ring Rd",
            "user_volume_m3": 0.5,
            "request_pickup": True,
        },
    )
    assert create_res.status_code == 201
    cd_data = create_res.json()["data"]
    cd_report_id = cd_data["id"]
    pickup_id = cd_data["pickup_id"]
    assert cd_data["status"] == "pickup_requested"
    assert pickup_id is not None

    from tests.conftest import TestingSessionLocal
    from app.models.cd_waste import CDWasteReport

    with TestingSessionLocal() as session:
        cd_record = session.get(CDWasteReport, uuid.UUID(cd_report_id))
        waste_report_id = str(cd_record.waste_report_id)

    assert waste_report_id is not None

    # Verify initial statuses of linked entities
    w_res = client.get(f"/api/v1/waste-reports/{waste_report_id}")
    assert w_res.status_code == 200
    assert w_res.json()["data"]["status"] == "assigned"

    p_res = client.get(f"/api/v1/pickups/{pickup_id}")
    assert p_res.status_code == 200
    assert p_res.json()["data"]["status"] == "scheduled"

    # 2. Assign vehicle
    assign_res = client.post(
        f"/api/v1/cd-waste/reports/{cd_report_id}/assign-vehicle",
        json={
            "vehicle_id": "HEAVY-TIPPER-04",
            "collector_id": "DRIVER-01",
            "collector_name": "Ravi Kumar",
        },
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["data"]["status"] == "assigned"

    # 3. Record collection event
    collect_res = client.post(
        f"/api/v1/cd-waste/reports/{cd_report_id}/collect",
        json={
            "collector_id": "DRIVER-01",
            "actual_weight_tonnes": 0.75,
            "collection_evidence_image_url": "https://storage.ecocycle.internal/uploads/pier_loaded.jpg",
            "notes": "Loaded onto Heavy Tipper 04",
        },
    )
    assert collect_res.status_code == 200
    assert collect_res.json()["data"]["status"] == "collected"

    # Verify linked WasteReport is synchronized to 'collected'
    w_after = client.get(f"/api/v1/waste-reports/{waste_report_id}")
    assert w_after.status_code == 200
    assert w_after.json()["data"]["status"] == "collected"

    # Verify linked PickupRequest is synchronized to 'completed'
    p_after = client.get(f"/api/v1/pickups/{pickup_id}")
    assert p_after.status_code == 200
    assert p_after.json()["data"]["status"] == "completed"

    # 4. Duplicate collection prevention: subsequent collection attempts must be rejected with 409 Conflict
    dup_res = client.post(
        f"/api/v1/cd-waste/reports/{cd_report_id}/collect",
        json={
            "collector_id": "DRIVER-01",
            "actual_weight_tonnes": 0.75,
        },
    )
    assert dup_res.status_code == 409
    assert "cannot record collection" in dup_res.json()["message"].lower()
    assert "collected" in dup_res.json()["message"].lower()


def test_cd_hash_verification_v2_canonical(client: TestClient) -> None:
    """Fix 2 & 3: Test that complete_processing issues a canonical v2 hash and GET /verify-hash validates it."""
    # 1. Create rubble report
    create_res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Airport Expressway Demolition",
            "material_category": "broken_concrete",
            "description": "Culvert rubble",
            "latitude": 13.198,
            "longitude": 77.706,
            "address": "Devanahalli Expressway",
            "user_volume_m3": 3.0,
        },
    )
    assert create_res.status_code == 201
    report_id = create_res.json()["data"]["id"]
    estimated_wt = create_res.json()["data"]["estimated_weight_tonnes"]

    # 2. Collect
    collect_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/collect",
        json={"collector_id": "DRIVER-CD-07", "actual_weight_tonnes": estimated_wt},
    )
    assert collect_res.status_code == 200

    # 3. Facility receipt
    receipt_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/receive-facility",
        json={
            "facility_name": "Bangalore North C&D Recycling Center",
            "received_weight_tonnes": 4.5,
            "weighbridge_ticket_id": "WB-2026-9901",
        },
    )
    assert receipt_res.status_code == 200

    # 4. Complete processing
    proc_res = client.post(
        f"/api/v1/cd-waste/reports/{report_id}/complete-processing",
        json={
            "output_material_type": "manufactured_sand",
            "output_tonnes": 4.1,
            "processing_evidence": "Wash plant run #WP-44; fineness modulus 2.6.",
        },
    )
    assert proc_res.status_code == 200
    assert proc_res.json()["data"]["status"] == "processing_completed"

    # Get stored hash via disposal record
    disp_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/disposal-record")
    assert disp_res.status_code == 200
    stored_hash = disp_res.json()["data"]["integrity_hash"]
    assert stored_hash is not None
    assert len(stored_hash) == 64

    # 5. Verify hash via GET endpoint
    verify_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/verify-hash")
    assert verify_res.status_code == 200
    v_data = verify_res.json()["data"]
    assert v_data["is_valid"] is True
    assert v_data["status"] == "verified"
    assert v_data["hash_format"] == "v2_strengthened"
    assert v_data["stored_hash"] == stored_hash
    assert v_data["computed_hash"] == stored_hash
    assert "canonical v2" in v_data["message"].lower()


def test_cd_hash_verification_v1_legacy_compatibility(client: TestClient) -> None:
    """Fix 2 & 3: Test that legacy v1 SHA-256 seals are preserved and verified as v1_legacy."""
    from tests.conftest import TestingSessionLocal
    from app.models.cd_waste import CDWasteReport
    from app.services.cd_service import CDService
    from app.core.security import generate_sha256_hash
    from datetime import datetime, timezone

    completed_dt = datetime.now(timezone.utc)
    report_id = uuid.uuid4()

    # Generate legacy v1 payload and hash
    v1_payload = CDService.generate_legacy_custody_payload_v1(
        report_id=report_id,
        destination_facility_name="Legacy BBMP Processing Plant",
        facility_received_weight_tonnes=6.00,
        output_material_type="recycled_aggregate_40mm",
        output_tonnes=5.70,
        completed_at=completed_dt,
        force_utc_tz=True,
    )
    v1_hash = generate_sha256_hash(v1_payload)

    # Insert historical record directly with legacy v1 hash into test DB
    with TestingSessionLocal() as session:
        legacy_report = CDWasteReport(
            id=report_id,
            project_name="Historical Flyover Rubble",
            material_category="broken_concrete",
            description="Demolished ramp section",
            latitude=12.95,
            longitude=77.58,
            address="Lalbagh Road",
            estimated_volume_m3=4.0,
            bulk_density_tonnes_m3=1.5,
            estimated_weight_tonnes=6.0,
            status="processing_completed",
            destination_facility_name="Legacy BBMP Processing Plant",
            facility_received_weight_tonnes=6.00,
            processing_status="completed",
            processing_completed_at=completed_dt,
            processed_output_type="recycled_aggregate_40mm",
            processed_output_tonnes=5.70,
            processing_evidence="Historical crushing log batch #88",
            integrity_hash=v1_hash,
        )
        session.add(legacy_report)
        session.commit()

    # Verify via endpoint
    verify_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/verify-hash")
    assert verify_res.status_code == 200
    v_data = verify_res.json()["data"]
    assert v_data["is_valid"] is True
    assert v_data["status"] == "verified"
    assert v_data["hash_format"] == "v1_legacy"
    assert v_data["stored_hash"] == v1_hash
    assert v_data["computed_hash"] == v1_hash
    assert "legacy v1" in v_data["message"].lower()


def test_cd_hash_verification_tamper_detection(client: TestClient) -> None:
    """Fix 3: Test that tampering with record values after sealing causes hash verification failure."""
    from tests.conftest import TestingSessionLocal
    from app.models.cd_waste import CDWasteReport

    # 1. Complete a report legitimately
    res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Tamper Test Foundation",
            "material_category": "broken_concrete",
            "description": "Foundation slabs",
            "latitude": 12.98,
            "longitude": 77.60,
            "address": "MG Road",
            "user_volume_m3": 2.0,
        },
    )
    report_id = res.json()["data"]["id"]

    client.post(f"/api/v1/cd-waste/reports/{report_id}/collect", json={"collector_id": "DRIVER-T1"})
    client.post(
        f"/api/v1/cd-waste/reports/{report_id}/receive-facility",
        json={"facility_name": "Tamper Test Yard", "received_weight_tonnes": 3.0},
    )
    client.post(
        f"/api/v1/cd-waste/reports/{report_id}/complete-processing",
        json={"output_material_type": "aggregate", "output_tonnes": 2.9, "processing_evidence": "Log-T1"},
    )

    # Verify it is initially valid
    init_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/verify-hash")
    assert init_res.json()["data"]["is_valid"] is True

    # 2. Tamper with a field directly in the database
    with TestingSessionLocal() as session:
        record = session.get(CDWasteReport, uuid.UUID(report_id))
        record.destination_facility_name = "Unauthorized Ghost Yard"
        session.commit()

    # 3. Verify mismatch is detected
    tamper_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/verify-hash")
    assert tamper_res.status_code == 200
    t_data = tamper_res.json()["data"]
    assert t_data["is_valid"] is False
    assert t_data["status"] == "mismatch"
    assert t_data["hash_format"] is None
    assert "mismatch" in t_data["message"].lower() or "altered" in t_data["message"].lower()


def test_cd_hash_verification_unsealed_and_unknown_id(client: TestClient) -> None:
    """Fix 3: Test that unsealed reports return status='unsealed' and unknown IDs return 404."""
    # 1. Unsealed report
    create_res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "In-Progress Rubble Excavation",
            "material_category": "soil_excavation",
            "description": "Basement excavation",
            "latitude": 12.92,
            "longitude": 77.65,
            "address": "Bellandur Gate",
            "user_volume_m3": 5.0,
        },
    )
    report_id = create_res.json()["data"]["id"]

    unsealed_res = client.get(f"/api/v1/cd-waste/reports/{report_id}/verify-hash")
    assert unsealed_res.status_code == 200
    u_data = unsealed_res.json()["data"]
    assert u_data["is_valid"] is False
    assert u_data["status"] == "unsealed"
    assert u_data["stored_hash"] is None
    assert u_data["computed_hash"] is None
    assert "not completed" in u_data["message"].lower()

    # 2. Unknown ID returns 404 Not Found
    unknown_id = uuid.uuid4()
    not_found_res = client.get(f"/api/v1/cd-waste/reports/{unknown_id}/verify-hash")
    assert not_found_res.status_code == 404
    assert "not found" in not_found_res.json()["message"].lower()


def test_cd_waste_reports_combined_filtering(client: TestClient) -> None:
    """Fix 4: Verify combined category and status filtering on GET /cd-waste/reports."""
    tag = uuid.uuid4().hex[:6]
    # Create 3 reports with distinct category/status combinations
    r1 = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": f"Filter Test Concrete Reported {tag}",
            "material_category": "broken_concrete",
            "description": "Concrete reported",
            "latitude": 12.90,
            "longitude": 77.50,
            "address": "Filter Test St",
            "user_volume_m3": 1.0,
            "request_pickup": False,  # status: reported
        },
    ).json()["data"]

    r2 = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": f"Filter Test Concrete Requested {tag}",
            "material_category": "broken_concrete",
            "description": "Concrete pickup requested",
            "latitude": 12.90,
            "longitude": 77.50,
            "address": "Filter Test St",
            "user_volume_m3": 1.0,
            "request_pickup": True,  # status: pickup_requested
        },
    ).json()["data"]

    r3 = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": f"Filter Test Bricks Reported {tag}",
            "material_category": "brick_masonry",
            "description": "Bricks reported",
            "latitude": 12.90,
            "longitude": 77.50,
            "address": "Filter Test St",
            "user_volume_m3": 1.0,
            "request_pickup": False,  # status: reported
        },
    ).json()["data"]

    # Filter by both category=broken_concrete AND status=reported
    res_both = client.get("/api/v1/cd-waste/reports?category=broken_concrete&status=reported")
    assert res_both.status_code == 200
    ids_both = [r["id"] for r in res_both.json()["data"]]
    assert r1["id"] in ids_both
    assert r2["id"] not in ids_both  # different status
    assert r3["id"] not in ids_both  # different category

    # Filter by category=broken_concrete AND status=pickup_requested
    res_req = client.get("/api/v1/cd-waste/reports?category=broken_concrete&status=pickup_requested")
    assert res_req.status_code == 200
    ids_req = [r["id"] for r in res_req.json()["data"]]
    assert r2["id"] in ids_req
    assert r1["id"] not in ids_req


def test_cd_waste_report_custom_density_override(client: TestClient) -> None:
    """Fix 4: Verify custom_density_tonnes_m3 overrides standard bulk density and correctly calculates mass."""
    # Standard bulk density for broken_concrete is 1.5 tonnes/m3
    # We supply a custom density of 2.45 tonnes/m3 (e.g. heavily reinforced rebar-dense concrete)
    custom_density = 2.45
    volume = 8.0
    expected_tonnes = round(volume * custom_density, 2)  # 19.60 tonnes
    expected_kg = round(expected_tonnes * 1000.0, 2)     # 19600.0 kg

    res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Heavy Reinforced Pier Debris",
            "material_category": "broken_concrete",
            "description": "High-density steel-reinforced concrete piers",
            "latitude": 12.93,
            "longitude": 77.62,
            "address": "Koramangala Metro Yard",
            "user_volume_m3": volume,
            "custom_density_tonnes_m3": custom_density,
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["bulk_density_tonnes_m3"] == custom_density
    assert data["estimated_weight_tonnes"] == expected_tonnes
    assert data["estimated_weight_kg"] == expected_kg


def test_cd_cancellation_unsupported_guard(client: TestClient) -> None:
    """Documentation and test: verify cancellation is currently unsupported for C&D waste reports.

    No cancellation route exists, preventing unauthorized cancellations or state transitions.
    """
    create_res = client.post(
        "/api/v1/cd-waste/reports",
        json={
            "project_name": "Active Road Rubble",
            "material_category": "broken_concrete",
            "description": "Road rubble",
            "latitude": 12.8123,
            "longitude": 77.4123,
            "address": "Rajajinagar",
            "user_volume_m3": 1.0,
        },
    )
    report_id = create_res.json()["data"]["id"]

    # Attempting to call non-existent cancellation endpoint returns 404 or 405
    cancel_res = client.post(f"/api/v1/cd-waste/reports/{report_id}/cancel")
    assert cancel_res.status_code in [404, 405]

    # Verify report status remains 'reported'
    rep_res = client.get(f"/api/v1/cd-waste/reports/{report_id}")
    assert rep_res.status_code == 200
    assert rep_res.json()["data"]["status"] == "reported"

