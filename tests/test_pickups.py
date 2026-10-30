"""Pillar 2: Pickups, EcoProof Verification, and EcoCredits tests."""

import uuid
from starlette.testclient import TestClient


def test_create_and_update_pickup_status(client: TestClient) -> None:
    """Test scheduling and status update of a pickup request."""
    # 1. Create a waste report
    report_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Cardboard boxes",
            "latitude": 12.91,
            "longitude": 77.63,
            "ward_number": "45",
        },
    )
    report_id = report_res.json()["data"]["id"]

    # 2. Schedule pickup
    pickup_res = client.post(
        "/api/v1/pickups",
        json={
            "report_id": report_id,
            "collector_id": "COL-04",
            "collector_name": "Ramesh Kumar",
            "vehicle_id": "KA-01-EA-1002",
        },
    )
    assert pickup_res.status_code == 201
    pickup = pickup_res.json()["data"]
    assert pickup["status"] == "scheduled"
    pickup_id = pickup["id"]

    # 3. Transition to in_progress
    patch_res = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={"status": "in_progress"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "in_progress"


def test_verify_collection_and_ecoproof_receipt(client: TestClient) -> None:
    """Verify collection, test SHA-256 integrity hash generation, and EcoCredits disbursement."""
    # 1. Provision an EcoPass account
    pass_res = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Sharma Residence",
            "ward_number": "101",
            "address": "402 Green Haven Apts, Ward 101",
        },
    )
    assert pass_res.status_code == 201
    ecopass = pass_res.json()["data"]
    ecopass_id = ecopass["ecopass_id"]
    assert ecopass["balance_ecocredits"] == 0

    # 2. Create waste report tied to this EcoPass
    report_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Segregated organic compostable scraps",
            "latitude": 12.93,
            "longitude": 77.62,
            "ward_number": "101",
            "ecopass_id": ecopass_id,
        },
    )
    report_id = report_res.json()["data"]["id"]

    # 3. Schedule pickup
    pickup_res = client.post(
        "/api/v1/pickups",
        json={
            "report_id": report_id,
            "collector_name": "Suresh",
        },
    )
    pickup_id = pickup_res.json()["data"]["id"]

    # 4. Verify collection (5.5 kg)
    verify_res = client.post(
        f"/api/v1/pickups/{pickup_id}/verify",
        json={
            "actual_weight_kg": 5.5,
            "stream_confirmed": "wet_organic",
            "collector_signature_id": "STAFF-902",
            "notes": "Proper segregation confirmed",
        },
    )
    assert verify_res.status_code == 201
    receipt = verify_res.json()["data"]
    assert receipt["actual_weight_kg"] == 5.5
    assert len(receipt["integrity_hash"]) == 64  # SHA-256 hex string
    assert receipt["ecocredits_awarded"] == 55   # 5.5 kg * 10 = 55 credits
    assert "SHA-256 provides record tamper-detection" in receipt["hash_explanation"]

    # 5. Confirm household EcoPass received the awarded credits
    pass_check = client.get(f"/api/v1/ecopass/{ecopass_id}")
    assert pass_check.status_code == 200
    assert pass_check.json()["data"]["balance_ecocredits"] == 55

    # 6. Check ledger transaction history
    tx_res = client.get(f"/api/v1/ecopass/{ecopass_id}/transactions")
    assert tx_res.status_code == 200
    txs = tx_res.json()["data"]
    assert len(txs) == 1
    assert txs[0]["amount"] == 55
    assert txs[0]["transaction_type"] == "pickup_reward"


def test_duplicate_verification_prevention(client: TestClient) -> None:
    """Ensure verifying the same pickup twice is rejected with HTTP 422."""
    report_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "sanitary",
            "description": "Sanitary waste properly wrapped",
            "latitude": 12.94,
            "longitude": 77.60,
        },
    )
    report_id = report_res.json()["data"]["id"]
    pickup_res = client.post("/api/v1/pickups", json={"report_id": report_id})
    pickup_id = pickup_res.json()["data"]["id"]

    # First verification succeeds
    res1 = client.post(
        f"/api/v1/pickups/{pickup_id}/verify",
        json={
            "actual_weight_kg": 2.0,
            "stream_confirmed": "sanitary",
            "collector_signature_id": "STAFF-11",
        },
    )
    assert res1.status_code == 201

    # Second verification fails
    res2 = client.post(
        f"/api/v1/pickups/{pickup_id}/verify",
        json={
            "actual_weight_kg": 2.0,
            "stream_confirmed": "sanitary",
            "collector_signature_id": "STAFF-11",
        },
    )
    assert res2.status_code == 422
    assert "already been verified" in res2.json()["message"]


def test_ecopass_registration_whitespace_only_rejected(client: TestClient) -> None:
    """Whitespace-only household_name, ward_number, or address must be rejected with HTTP 422."""
    # Whitespace-only household_name
    res_hh = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "    ",
            "ward_number": "12",
            "address": "123 Main Street, Ward 12",
        },
    )
    assert res_hh.status_code == 422
    assert res_hh.json()["error_code"] == "VALIDATION_ERROR"

    # Whitespace-only ward_number
    res_ward = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Patel Household",
            "ward_number": "   ",
            "address": "123 Main Street, Ward 12",
        },
    )
    assert res_ward.status_code == 422
    assert res_ward.json()["error_code"] == "VALIDATION_ERROR"

    # Whitespace-only address
    res_addr = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Patel Household",
            "ward_number": "12",
            "address": "     ",
        },
    )
    assert res_addr.status_code == 422
    assert res_addr.json()["error_code"] == "VALIDATION_ERROR"


def test_ecopass_registration_trims_whitespace(client: TestClient) -> None:
    """Leading and trailing whitespace must be trimmed and stored clean."""
    res = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "  Mukherjee Family  ",
            "ward_number": " 77 ",
            "address": "  Flat 2B, Harmony Residency, Ward 77  ",
        },
    )
    assert res.status_code == 201
    account = res.json()["data"]
    assert account["household_name"] == "Mukherjee Family"
    assert account["ward_number"] == "77"
    assert account["address"] == "Flat 2B, Harmony Residency, Ward 77"


def test_ecopass_registration_length_limits(client: TestClient) -> None:
    """Household name < 2 chars and address < 5 chars must be rejected."""
    # household_name length 1 (< 2)
    res_hh = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": " M ",
            "ward_number": "12",
            "address": "123 Main Street, Ward 12",
        },
    )
    assert res_hh.status_code == 422

    # address length 4 (< 5)
    res_addr = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Mukherjee",
            "ward_number": "12",
            "address": " Rd ",
        },
    )
    assert res_addr.status_code == 422

