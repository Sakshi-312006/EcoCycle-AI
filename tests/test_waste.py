"""Pillar 1: Waste Management API test suite."""

import uuid
from starlette.testclient import TestClient


def test_create_waste_report_success(client: TestClient) -> None:
    """Test successful creation of a doorstep waste report."""
    payload = {
        "category": "wet_organic",
        "description": "Kitchen vegetable scraps and coffee grounds",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "142 MG Road, Ward 84",
        "ward_number": "84",
        "estimated_weight_kg": 3.5,
    }
    response = client.post("/api/v1/waste-reports", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    report = data["data"]
    assert report["category"] == "wet_organic"
    assert report["status"] == "reported"
    assert report["ward_number"] == "84"
    assert report["estimated_weight_kg"] == 3.5
    assert "id" in report


def test_create_waste_report_all_four_streams(client: TestClient) -> None:
    """Verify that all four statutory streams are accepted and validated."""
    streams = ["wet_organic", "dry_recyclable", "sanitary", "hazardous"]
    for stream in streams:
        payload = {
            "category": stream,
            "description": f"Testing stream {stream}",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "ward_number": "12",
        }
        response = client.post("/api/v1/waste-reports", json=payload)
        assert response.status_code == 201
        assert response.json()["data"]["category"] == stream


def test_create_waste_report_validation_errors(client: TestClient) -> None:
    """Ensure invalid latitude/longitude or unknown category triggers HTTP 422 standard envelope."""
    # Invalid latitude > 90
    invalid_coords = {
        "category": "dry_recyclable",
        "description": "Packaging cartons",
        "latitude": 150.0,
        "longitude": 77.0,
    }
    response = client.post("/api/v1/waste-reports", json=invalid_coords)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "VALIDATION_ERROR"
    assert len(data["details"]) > 0

    # Invalid category
    invalid_cat = {
        "category": "e_waste_unsupported",
        "description": "Old cables",
        "latitude": 12.9,
        "longitude": 77.5,
    }
    res_cat = client.post("/api/v1/waste-reports", json=invalid_cat)
    assert res_cat.status_code == 422


def test_list_waste_reports_and_filters(client: TestClient) -> None:
    """Test filtering reports by stream category and ward."""
    # Seed specific report
    client.post(
        "/api/v1/waste-reports",
        json={
            "category": "hazardous",
            "description": "Discarded car battery",
            "latitude": 12.92,
            "longitude": 77.61,
            "ward_number": "99",
        },
    )
    # Query with category=hazardous
    response = client.get("/api/v1/waste-reports?category=hazardous")
    assert response.status_code == 200
    reports = response.json()["data"]
    assert len(reports) >= 1
    assert all(r["category"] == "hazardous" for r in reports)

    # Query with ward=99
    res_ward = client.get("/api/v1/waste-reports?ward=99")
    assert res_ward.status_code == 200
    assert any(r["ward_number"] == "99" for r in res_ward.json()["data"])


def test_get_waste_report_not_found(client: TestClient) -> None:
    """Test 404 for non-existent UUID."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/waste-reports/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "RESOURCE_NOT_FOUND"


def test_update_waste_report(client: TestClient) -> None:
    """Test updating report status."""
    create_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Newspaper bundle",
            "latitude": 12.95,
            "longitude": 77.58,
        },
    )
    report_id = create_res.json()["data"]["id"]

    patch_res = client.patch(
        f"/api/v1/waste-reports/{report_id}",
        json={"status": "collected", "estimated_weight_kg": 6.2},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()["data"]
    assert updated["status"] == "collected"
    assert updated["estimated_weight_kg"] == 6.2


def test_waste_report_weight_kg_payload_mapping(client: TestClient) -> None:
    """weight_kg in payload should map to estimated_weight_kg when valid."""
    res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Kitchen waste",
            "latitude": 12.97,
            "longitude": 77.59,
            "weight_kg": 4.5,
        },
    )
    assert res.status_code == 201
    assert res.json()["data"]["estimated_weight_kg"] == 4.5


def test_waste_report_negative_weight_rejected(client: TestClient) -> None:
    """Negative values for weight_kg or estimated_weight_kg must return HTTP 422."""
    res_weight = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Kitchen waste",
            "latitude": 12.97,
            "longitude": 77.59,
            "weight_kg": -2.0,
        },
    )
    assert res_weight.status_code == 422
    assert res_weight.json()["error_code"] == "VALIDATION_ERROR"

    res_est = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Kitchen waste",
            "latitude": 12.97,
            "longitude": 77.59,
            "estimated_weight_kg": -5.0,
        },
    )
    assert res_est.status_code == 422
    assert res_est.json()["error_code"] == "VALIDATION_ERROR"


def test_waste_report_weight_upper_bound_rejected(client: TestClient) -> None:
    """Values exceeding 1000.0 kg must return HTTP 422."""
    res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Scrap metal",
            "latitude": 12.97,
            "longitude": 77.59,
            "weight_kg": 1000.1,
        },
    )
    assert res.status_code == 422


def test_waste_report_weight_optional_omitted(client: TestClient) -> None:
    """When weight is omitted, estimated_weight_kg must remain null (no default invented)."""
    res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Sorted plastic bottles",
            "latitude": 12.97,
            "longitude": 77.59,
        },
    )
    assert res.status_code == 201
    assert res.json()["data"]["estimated_weight_kg"] is None


def test_waste_report_conflicting_and_matching_weights(client: TestClient) -> None:
    """Conflicting weights trigger 422; matching weights succeed."""
    res_conflict = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "sanitary",
            "description": "Sanitary napkins safely wrapped",
            "latitude": 12.97,
            "longitude": 77.59,
            "weight_kg": 2.5,
            "estimated_weight_kg": 5.0,
        },
    )
    assert res_conflict.status_code == 422
    assert "Conflicting values" in str(res_conflict.json()["details"])

    res_matching = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "sanitary",
            "description": "Sanitary napkins safely wrapped",
            "latitude": 12.97,
            "longitude": 77.59,
            "weight_kg": 2.5,
            "estimated_weight_kg": 2.5,
        },
    )
    assert res_matching.status_code == 201
    assert res_matching.json()["data"]["estimated_weight_kg"] == 2.5


def test_waste_report_ecopass_validation(client: TestClient) -> None:
    """Unknown ecopass_id returns 404; blank stores None; existing persists."""
    # Unknown ecopass_id
    res_unknown = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Vegetable peels",
            "latitude": 12.97,
            "longitude": 77.59,
            "ecopass_id": "ECO-UNKNOWN-99999",
        },
    )
    assert res_unknown.status_code == 404
    assert res_unknown.json()["error_code"] == "RESOURCE_NOT_FOUND"

    # Whitespace-only ecopass_id stores None
    res_blank = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Vegetable peels",
            "latitude": 12.97,
            "longitude": 77.59,
            "ecopass_id": "   ",
        },
    )
    assert res_blank.status_code == 201
    assert res_blank.json()["data"]["ecopass_id"] is None

    # Valid ecopass_id with surrounding whitespace trimmed
    pass_res = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Verma Family",
            "ward_number": "55",
            "address": "Flat 303, Sunrise Apts, Ward 55",
        },
    )
    assert pass_res.status_code == 201
    valid_id = pass_res.json()["data"]["ecopass_id"]

    res_valid = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Kitchen waste",
            "latitude": 12.97,
            "longitude": 77.59,
            "ecopass_id": f"  {valid_id}  ",
        },
    )
    assert res_valid.status_code == 201
    assert res_valid.json()["data"]["ecopass_id"] == valid_id


def test_waste_report_patch_preserves_negative_weight_rejection(client: TestClient) -> None:
    """PATCH on /api/v1/waste-reports/{id} continues to reject negative estimated_weight_kg with 422."""
    create_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Aluminum cans",
            "latitude": 12.95,
            "longitude": 77.58,
        },
    )
    report_id = create_res.json()["data"]["id"]

    patch_res = client.patch(
        f"/api/v1/waste-reports/{report_id}",
        json={"estimated_weight_kg": -1.5},
    )
    assert patch_res.status_code == 422
    assert patch_res.json()["error_code"] == "VALIDATION_ERROR"

