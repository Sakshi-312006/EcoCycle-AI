"""Comprehensive tests for the four remaining prototype features:

1. Overdue indicator (Feature A)
2. QR code & EcoProof verification (Feature B)
3. User settings (Feature C)
4. OTP verification (Feature D)
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from starlette.testclient import TestClient

from app.models.pickup import PickupRequest, VerificationRecord
from app.models.user_settings import UserSettings
from app.models.waste import WasteReport
from app.services.otp_service import OTPService
from tests.conftest import TestingSessionLocal


# ===========================================================================
# Feature A: Overdue Indicator Tests
# ===========================================================================


def test_pickup_overdue_indicator_when_past_scheduled_time(client: TestClient) -> None:
    """Test that a scheduled pickup with past scheduled_time is marked is_overdue=True."""
    # 1. Create waste report
    rep_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Old newspapers and cardboard",
            "latitude": 12.91,
            "longitude": 77.63,
            "ward_number": "150",
        },
    )
    assert rep_res.status_code == 201
    report_id = rep_res.json()["data"]["id"]

    # 2. Create pickup with scheduled_time 2 hours in the past
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    pickup_res = client.post(
        "/api/v1/pickups",
        json={
            "report_id": report_id,
            "collector_id": "COL-01",
            "collector_name": "Ramesh",
            "scheduled_time": past_time.isoformat(),
        },
    )
    assert pickup_res.status_code == 201
    data = pickup_res.json()["data"]
    assert data["status"] == "scheduled"
    assert data["is_overdue"] is True

    # Check GET /pickups/{id} returns is_overdue=True
    get_res = client.get(f"/api/v1/pickups/{data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["is_overdue"] is True


def test_pickup_not_overdue_when_future_scheduled_time(client: TestClient) -> None:
    """Test that a scheduled pickup with future scheduled_time is marked is_overdue=False."""
    rep_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "wet_organic",
            "description": "Compost kitchen greens",
            "latitude": 12.92,
            "longitude": 77.64,
        },
    )
    report_id = rep_res.json()["data"]["id"]

    future_time = datetime.now(timezone.utc) + timedelta(hours=4)
    pickup_res = client.post(
        "/api/v1/pickups",
        json={
            "report_id": report_id,
            "collector_id": "COL-02",
            "scheduled_time": future_time.isoformat(),
        },
    )
    assert pickup_res.status_code == 201
    data = pickup_res.json()["data"]
    assert data["status"] == "scheduled"
    assert data["is_overdue"] is False


def test_pickup_not_overdue_when_completed_or_cancelled(client: TestClient) -> None:
    """Test that completed or cancelled pickups are never marked overdue even if scheduled_time is past."""
    rep_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Glass bottles",
            "latitude": 12.93,
            "longitude": 77.61,
        },
    )
    report_id = rep_res.json()["data"]["id"]

    past_time = datetime.now(timezone.utc) - timedelta(hours=5)
    pickup_res = client.post(
        "/api/v1/pickups",
        json={
            "report_id": report_id,
            "collector_id": "COL-03",
            "scheduled_time": past_time.isoformat(),
        },
    )
    pickup_id = pickup_res.json()["data"]["id"]
    assert pickup_res.json()["data"]["is_overdue"] is True

    # Transition status to cancelled
    cancel_res = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={"status": "cancelled", "notes": "Citizen requested reschedule"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "cancelled"
    assert cancel_res.json()["data"]["is_overdue"] is False

    # Check verified/completed pickup
    rep2 = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Metal tins",
            "latitude": 12.94,
            "longitude": 77.62,
        },
    ).json()["data"]
    pickup2 = client.post(
        "/api/v1/pickups",
        json={
            "report_id": rep2["id"],
            "collector_id": "COL-04",
            "scheduled_time": past_time.isoformat(),
        },
    ).json()["data"]

    # Verify pickup
    client.post(
        f"/api/v1/pickups/{pickup2['id']}/verify",
        json={
            "actual_weight_kg": 5.0,
            "stream_confirmed": "dry_recyclable",
            "collector_signature_id": "STAFF-99",
        },
    )
    p2_res = client.get(f"/api/v1/pickups/{pickup2['id']}")
    assert p2_res.json()["data"]["status"] == "completed"
    assert p2_res.json()["data"]["is_overdue"] is False


def test_pickup_missing_deadline_not_overdue(client: TestClient) -> None:
    """Test that a pickup with no scheduled_time (missing deadline) is marked is_overdue=False."""
    rep_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Mixed paper",
            "latitude": 12.95,
            "longitude": 77.60,
        },
    )
    report_id = rep_res.json()["data"]["id"]

    pickup_res = client.post(
        "/api/v1/pickups",
        json={
            "report_id": report_id,
            "collector_id": "COL-05",
            "scheduled_time": None,  # No deadline
        },
    )
    assert pickup_res.status_code == 201
    data = pickup_res.json()["data"]
    assert data["scheduled_time"] is None
    assert data["is_overdue"] is False


# ===========================================================================
# Feature B: QR Code & Verification Tests
# ===========================================================================


def test_pickup_qr_code_generation(client: TestClient) -> None:
    """Test generating a QR code for a pickup encodes verification URL without PII."""
    rep_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Corrugated boxes",
            "latitude": 12.90,
            "longitude": 77.60,
        },
    )
    pickup_res = client.post(
        "/api/v1/pickups",
        json={"report_id": rep_res.json()["data"]["id"]},
    )
    pickup_id = pickup_res.json()["data"]["id"]

    qr_res = client.get(f"/api/v1/pickups/{pickup_id}/qr")
    assert qr_res.status_code == 200
    qr_data = qr_res.json()["data"]
    assert qr_data["pickup_id"] == pickup_id
    assert f"/api/v1/pickups/{pickup_id}/verify-receipt" in qr_data["verification_url"]
    assert qr_data["qr_code_data_url"].startswith("data:image/png;base64,")
    assert len(qr_data["qr_code_data_url"]) > 100
    assert qr_data["is_verified"] is False
    assert qr_data["status"] == "scheduled"
    assert "QR code encodes a verification URL" in qr_data["disclaimer"]


def test_pickup_verify_receipt_endpoint_lifecycle(client: TestClient) -> None:
    """Test public verification endpoint for unverified, verified, and tampered states."""
    # 1. Create pickup
    rep_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Sorted plastics",
            "latitude": 12.92,
            "longitude": 77.58,
        },
    )
    pickup_res = client.post(
        "/api/v1/pickups",
        json={"report_id": rep_res.json()["data"]["id"]},
    )
    pickup_id = pickup_res.json()["data"]["id"]

    # 2. Check unverified record
    unver_res = client.get(f"/api/v1/pickups/{pickup_id}/verify-receipt")
    assert unver_res.status_code == 200
    u_data = unver_res.json()["data"]
    assert u_data["is_valid"] is False
    assert u_data["status"] == "unverified"
    assert "not been verified" in u_data["message"].lower()

    # 3. Complete verification
    v_post = client.post(
        f"/api/v1/pickups/{pickup_id}/verify",
        json={
            "actual_weight_kg": 12.5,
            "stream_confirmed": "dry_recyclable",
            "collector_signature_id": "DRIVER-44",
            "notes": "Clean high-grade HDPE",
        },
    )
    assert v_post.status_code == 201

    # 4. Check verified record
    ver_res = client.get(f"/api/v1/pickups/{pickup_id}/verify-receipt")
    assert ver_res.status_code == 200
    v_data = ver_res.json()["data"]
    assert v_data["is_valid"] is True
    assert v_data["status"] == "verified"
    assert v_data["actual_weight_kg"] == 12.5
    assert v_data["stream_confirmed"] == "dry_recyclable"
    assert v_data["collector_signature_id"] == "DRIVER-44"
    assert v_data["stored_hash"] == v_data["computed_hash"]
    assert len(v_data["stored_hash"]) == 64

    # Also verify that QR endpoint now marks is_verified=True
    qr_res = client.get(f"/api/v1/pickups/{pickup_id}/qr")
    assert qr_res.status_code == 200
    assert qr_res.json()["data"]["is_verified"] is True
    assert qr_res.json()["data"]["integrity_hash"] == v_data["stored_hash"]

    # 5. Tamper detection: alter the stored hash directly in the database
    with TestingSessionLocal() as session:
        rec = session.get(VerificationRecord, uuid.UUID(v_post.json()["data"]["id"]))
        rec.actual_weight_kg = 99.9  # tampered mass
        session.commit()

    tamper_res = client.get(f"/api/v1/pickups/{pickup_id}/verify-receipt")
    assert tamper_res.status_code == 200
    t_data = tamper_res.json()["data"]
    assert t_data["is_valid"] is False
    assert t_data["status"] == "mismatch"
    assert "mismatch" in t_data["message"].lower() or "altered" in t_data["message"].lower()

    # 6. Unknown pickup ID returns 404
    unknown_res = client.get(f"/api/v1/pickups/{uuid.uuid4()}/verify-receipt")
    assert unknown_res.status_code == 404


# ===========================================================================
# Feature C: User Settings Tests
# ===========================================================================


def test_user_settings_get_defaults_and_update(client: TestClient) -> None:
    """Test retrieving default user settings and updating language, theme, and notifications."""
    test_user_id = f"user_{uuid.uuid4().hex[:8]}"

    # 1. Fetch settings for a new user - returns initialized defaults
    get_res = client.get(f"/api/v1/user-settings/{test_user_id}")
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    assert data["user_id"] == test_user_id
    assert data["language"] == "en"
    assert data["notifications_enabled"] is True
    assert data["notification_preference"] == "push"
    assert data["theme"] == "system"
    assert data["accessibility_high_contrast"] is False
    assert data["accessibility_large_text"] is False

    # 2. Update settings with Kannada language and dark theme
    put_res = client.put(
        f"/api/v1/user-settings/{test_user_id}",
        json={
            "language": "kn",
            "theme": "dark",
            "notification_preference": "sms",
            "accessibility_large_text": True,
        },
    )
    assert put_res.status_code == 200
    updated = put_res.json()["data"]
    assert updated["language"] == "kn"
    assert updated["theme"] == "dark"
    assert updated["notification_preference"] == "sms"
    assert updated["accessibility_large_text"] is True
    assert updated["accessibility_high_contrast"] is False  # untouched

    # 3. Retrieve again to ensure persistence
    get_res2 = client.get(f"/api/v1/user-settings/{test_user_id}")
    assert get_res2.status_code == 200
    persisted = get_res2.json()["data"]
    assert persisted["language"] == "kn"
    assert persisted["theme"] == "dark"


def test_user_settings_validation_invalid_language_and_theme(client: TestClient) -> None:
    """Ensure invalid language or theme choices are rejected with HTTP 422."""
    test_user_id = "user_invalid_test"
    bad_res = client.put(
        f"/api/v1/user-settings/{test_user_id}",
        json={"language": "klingon"},
    )
    assert bad_res.status_code == 422

    bad_theme = client.put(
        f"/api/v1/user-settings/{test_user_id}",
        json={"theme": "neon_cyberpunk"},
    )
    assert bad_theme.status_code == 422


# ===========================================================================
# Feature D: OTP Verification Tests (Demo Mode)
# ===========================================================================


def test_otp_request_and_successful_verification(client: TestClient) -> None:
    """Test standard OTP request, demo OTP reception in development mode, and successful verification."""
    OTPService.reset_store_for_testing()

    phone = "+919876543210"
    req_res = client.post(
        "/api/v1/auth/otp/request",
        json={"phone_number": phone, "purpose": "login"},
    )
    assert req_res.status_code == 200
    req_data = req_res.json()["data"]
    assert req_data["phone_number"] == "+919876543210"
    assert req_data["delivery_mode"] == "demo"
    session_id = req_data["session_id"]
    demo_otp = req_data["demo_otp"]
    assert demo_otp is not None
    assert len(demo_otp) == 6
    assert demo_otp.isdigit()

    # Verify with correct code
    ver_res = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "phone_number": phone,
            "session_id": session_id,
            "otp_code": demo_otp,
        },
    )
    assert ver_res.status_code == 200
    ver_data = ver_res.json()["data"]
    assert ver_data["is_verified"] is True
    assert ver_data["verification_token"].startswith("proof_verified_")

    # Consumed OTP cannot be reused
    replay_res = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "phone_number": phone,
            "session_id": session_id,
            "otp_code": demo_otp,
        },
    )
    assert replay_res.status_code == 422
    assert "already been used" in replay_res.json()["message"].lower()


def test_otp_incorrect_code_and_attempt_limit_exceeded(client: TestClient) -> None:
    """Test that incorrect OTP decrements attempts and exceeds limit on 3rd attempt."""
    OTPService.reset_store_for_testing()

    phone = "+919111222333"
    req_res = client.post(
        "/api/v1/auth/otp/request",
        json={"phone_number": phone},
    )
    session_id = req_res.json()["data"]["session_id"]

    # Attempt 1: wrong code -> 2 attempts remaining
    bad1 = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone_number": phone, "session_id": session_id, "otp_code": "000000"},
    )
    assert bad1.status_code == 422
    assert "2 attempt(s) remaining" in bad1.json()["message"]

    # Attempt 2: wrong code -> 1 attempt remaining
    bad2 = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone_number": phone, "session_id": session_id, "otp_code": "000001"},
    )
    assert bad2.status_code == 422
    assert "1 attempt(s) remaining" in bad2.json()["message"]

    # Attempt 3: wrong code -> attempts exceeded / code invalidated
    bad3 = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone_number": phone, "session_id": session_id, "otp_code": "000002"},
    )
    assert bad3.status_code == 422
    assert "maximum verification attempts exceeded" in bad3.json()["message"].lower()


def test_otp_resend_throttling_cooldown(client: TestClient) -> None:
    """Test that requesting an OTP within 60s cooldown is rejected with throttling error."""
    OTPService.reset_store_for_testing()

    phone = "+919999888877"
    first_req = client.post(
        "/api/v1/auth/otp/request",
        json={"phone_number": phone},
    )
    assert first_req.status_code == 200

    # Immediate second request should be throttled
    second_req = client.post(
        "/api/v1/auth/otp/request",
        json={"phone_number": phone},
    )
    assert second_req.status_code == 422
    assert "resend throttled" in second_req.json()["message"].lower()


def test_otp_expiration(client: TestClient) -> None:
    """Test that expired OTPs cannot be verified."""
    OTPService.reset_store_for_testing()

    phone = "+919888777666"
    req_res = client.post(
        "/api/v1/auth/otp/request",
        json={"phone_number": phone},
    )
    session_id = req_res.json()["data"]["session_id"]
    code = req_res.json()["data"]["demo_otp"]

    # Fast-forward expiration in store
    with OTPService._lock:
        OTPService._store[session_id].expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    ver_res = client.post(
        "/api/v1/auth/otp/verify",
        json={"phone_number": phone, "session_id": session_id, "otp_code": code},
    )
    assert ver_res.status_code == 422
    assert "expired" in ver_res.json()["message"].lower()

