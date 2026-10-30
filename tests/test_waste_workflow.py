"""Tests for the Complete Pillar 1 Waste Identification and Handling Workflow.

Verifies:
1. Image upload validation (format, magic bytes, size limits, traversal resistance, static retrieval)
2. Vision AI classification interface (categories, confidence thresholding, safe fallback, missing weights)
3. Specific handling guidance (Fruit scraps, Lemon/chilli, Diaper, Bandages - minor vs infectious)
4. Home handling vs pickup decision outcomes (HOME_HANDLING_RECOMMENDED, COLLECTION_APPROPRIATE, SPECIAL_HANDLING_REQUIRED)
5. Zero DB record creation on guidance-only journeys
6. Atomic WasteReport + PickupRequest creation only after explicit citizen confirmation
7. Duplicate submission prevention
8. Multilingual regional language guidance support
"""

import io
import uuid
import pytest
from starlette.testclient import TestClient

from app.models.pickup import PickupRequest
from app.models.waste import WasteReport


# ---------------------------------------------------------------------------
# 1. Image Upload Tests
# ---------------------------------------------------------------------------


def test_image_upload_success_jpeg_and_png(client: TestClient):
    """Test successful image upload for valid JPEG and PNG binary payloads."""
    # Valid JPEG header \xff\xd8\xff followed by dummy bytes
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xaa" * 200
    response = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("photo.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "file_url" in data["data"]
    file_url = data["data"]["file_url"]
    assert file_url.startswith("/static/uploads/")
    assert file_url.endswith(".jpg")
    assert data["data"]["size_bytes"] == len(jpeg_bytes)

    # Verify static file is readable via HTTP
    static_resp = client.get(file_url)
    assert static_resp.status_code == 200
    assert static_resp.content == jpeg_bytes

    # Valid PNG header \x89PNG\r\n\x1a\n
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\xbb" * 200
    png_resp = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("photo.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert png_resp.status_code == 201
    assert png_resp.json()["data"]["file_url"].endswith(".png")


def test_image_upload_rejects_empty_file(client: TestClient):
    """Test that zero-byte files are rejected."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("empty.jpg", empty_file, "image/jpeg")},
    )
    assert response.status_code == 422
    assert "empty" in response.json()["message"].lower()


def test_image_upload_rejects_invalid_format_and_corrupt_signature(client: TestClient):
    """Test rejection of unsupported MIME types and mismatched magic bytes."""
    # 1. Plain text file
    txt_file = io.BytesIO(b"this is plain text not an image")
    resp1 = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("notes.txt", txt_file, "text/plain")},
    )
    assert resp1.status_code == 422
    assert "unsupported file type" in resp1.json()["message"].lower()

    # 2. Corrupt file claiming to be JPEG but containing random text
    corrupt_jpeg = io.BytesIO(b"FAKE_DATA_NOT_A_JPEG")
    resp2 = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("fake.jpg", corrupt_jpeg, "image/jpeg")},
    )
    assert resp2.status_code == 422
    assert "header does not match" in resp2.json()["message"].lower()


def test_image_upload_rejects_oversized_file(client: TestClient):
    """Test that files exceeding MAX_UPLOAD_SIZE_BYTES (5 MB) are rejected."""
    # 5.2 MB payload with valid JPEG header
    oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (5242880 + 1024)
    response = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("huge.jpg", io.BytesIO(oversized_bytes), "image/jpeg")},
    )
    assert response.status_code == 422
    assert "exceeds maximum allowed limit" in response.json()["message"].lower()


def test_image_upload_path_traversal_prevention(client: TestClient):
    """Verify that malicious directory traversal filenames are ignored and stored safely."""
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x11" * 100
    malicious_filename = "../../../etc/passwd.jpg"
    response = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": (malicious_filename, io.BytesIO(jpeg_bytes), "image/jpeg")},
    )
    assert response.status_code == 201
    stored_name = response.json()["data"]["filename"]
    # The stored filename must be a clean hex UUID, not the traversal string
    assert ".." not in stored_name
    assert "/" not in stored_name
    assert "\\" not in stored_name


# ---------------------------------------------------------------------------
# 2. AI Waste Classification Tests
# ---------------------------------------------------------------------------


def test_waste_classification_supported_category_and_item(client: TestClient):
    """Test classification for recognized waste items across statutory streams."""
    # Test Fruit scraps
    resp_fruit = client.post(
        "/api/v1/waste-reports/classify-image",
        json={"image_url": "/static/uploads/fruit_scraps.jpg", "user_hint": "raw fruit scraps"},
    )
    assert resp_fruit.status_code == 200
    data_fruit = resp_fruit.json()["data"]
    assert data_fruit["predicted_category"] == "wet_organic"
    assert data_fruit["item_prediction"] == "raw_fruit_scraps"
    assert data_fruit["confidence"] >= 0.70
    assert data_fruit["requires_confirmation"] is False
    assert data_fruit["suggested_action"] == "proceed_to_guidance"

    # Test Diaper
    resp_diaper = client.post(
        "/api/v1/waste-reports/classify-image",
        json={"image_url": "/static/uploads/diaper.jpg", "user_hint": "used diaper"},
    )
    assert resp_diaper.status_code == 200
    data_diaper = resp_diaper.json()["data"]
    assert data_diaper["predicted_category"] == "sanitary"
    assert data_diaper["item_prediction"] == "used_diapers"
    assert data_diaper["confidence"] >= 0.70


def test_waste_classification_low_confidence_fallback(client: TestClient):
    """Test that low-confidence classification triggers the safe fallback."""
    resp = client.post(
        "/api/v1/waste-reports/classify-image",
        json={"image_url": "/static/uploads/blurry_photo.jpg", "user_hint": "low_confidence ambiguous object"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["confidence"] < 0.70
    assert data["requires_confirmation"] is True
    assert data["fallback_triggered"] is True
    assert data["suggested_action"] == "confirm_category"


def test_waste_classification_missing_weights_honest_reporting(client: TestClient):
    """Test that when weights are uninstalled and image is unrecognized, service honestly reports status."""
    resp = client.post(
        "/api/v1/waste-reports/classify-image",
        json={"image_url": "/static/uploads/generic_sample_999.jpg"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["requires_confirmation"] is True
    assert data["fallback_triggered"] is True
    assert data["model_info"]["architecture"].startswith("MobileNetV3")
    assert "dataset_requirements" in data["model_info"]


# ---------------------------------------------------------------------------
# 3. Handling Guidance & Decision Engine Tests
# ---------------------------------------------------------------------------


def test_guidance_example_a_fruit_scraps(client: TestClient):
    """Verify Example A: Raw fruit scraps recommends home composting without pickup option."""
    resp = client.post(
        "/api/v1/waste-reports/guidance",
        json={
            "category": "wet_organic",
            "item": "raw_fruit_scraps",
            "language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["action_outcome"] == "HOME_HANDLING_RECOMMENDED"
    assert data["home_handling_suitable"] is True
    assert data["collection_recommended"] is False
    assert data["pickup_available"] is False
    # Verify scientific ratio guidance
    assert "2:1 to 3:1" in data["scientific_guidance"]
    assert "25:1 to 30:1" in data["scientific_guidance"]
    # Verify statutory reference
    assert "Solid Waste Management" in data["statutory_guidance"]
    assert "Rule 4(1)(a)" in data["statutory_reference"]
    # Verify allowed actions do not include ordinary request_pickup
    assert "request_pickup" not in data["allowed_next_actions"]
    assert "exit_to_home" in data["allowed_next_actions"]


def test_guidance_example_b_lemon_peels_and_chillies(client: TestClient):
    """Verify Example B: Lemon peels and chillies provides nuanced vermicomposting cautions."""
    resp = client.post(
        "/api/v1/waste-reports/guidance",
        json={
            "category": "wet_organic",
            "item": "citrus_chilli_scraps",
            "language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["action_outcome"] == "HOME_HANDLING_RECOMMENDED"
    assert data["pickup_available"] is False
    # Verify cautious vermicomposting guidance
    assert "vermicomposting" in data["scientific_guidance"].lower()
    assert "Eisenia fetida" in data["scientific_guidance"]
    assert "d-limonene" in data["scientific_guidance"] or "acid" in data["scientific_guidance"].lower()


def test_guidance_example_c_used_diapers(client: TestClient):
    """Verify Example C: Used diapers recommends sanitary collection with pickup available."""
    resp = client.post(
        "/api/v1/waste-reports/guidance",
        json={
            "category": "sanitary",
            "item": "used_diapers",
            "language": "en",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["action_outcome"] == "COLLECTION_APPROPRIATE"
    assert data["home_handling_suitable"] is False
    assert data["collection_recommended"] is True
    assert data["pickup_available"] is True
    assert "request_pickup" in data["allowed_next_actions"]
    assert "Rule 4(1)(b)" in data["statutory_reference"]


def test_guidance_example_d_medical_bandages_infectious_vs_minor(client: TestClient):
    """Verify Example D: Infectious bandages block ordinary collection while minor bandages allow it."""
    # Case D1: Potentially infectious medical bandage
    resp_infectious = client.post(
        "/api/v1/waste-reports/guidance",
        json={
            "category": "sanitary",
            "item": "medical_bandages",
            "is_potentially_infectious": True,
            "language": "en",
        },
    )
    assert resp_infectious.status_code == 200
    data_inf = resp_infectious.json()["data"]
    assert data_inf["action_outcome"] == "SPECIAL_HANDLING_REQUIRED"
    assert data_inf["pickup_available"] is False
    assert "Bio-Medical Waste Management Rules, 2016" in data_inf["statutory_guidance"]
    assert "CBWTF" in data_inf["statutory_guidance"]
    assert "request_pickup" not in data_inf["allowed_next_actions"]

    # Case D2: Minor household bandage
    resp_minor = client.post(
        "/api/v1/waste-reports/guidance",
        json={
            "category": "sanitary",
            "item": "medical_bandages",
            "is_potentially_infectious": False,
            "language": "en",
        },
    )
    assert resp_minor.status_code == 200
    data_minor = resp_minor.json()["data"]
    assert data_minor["action_outcome"] == "COLLECTION_APPROPRIATE"
    assert data_minor["pickup_available"] is True
    assert "request_pickup" in data_minor["allowed_next_actions"]


def test_guidance_multilingual_support(client: TestClient):
    """Verify localized guidance across all 6 supported regional languages."""
    languages = ["en", "hi", "kn", "ta", "te", "mr"]
    for lang in languages:
        resp = client.post(
            "/api/v1/waste-reports/guidance",
            json={
                "category": "wet_organic",
                "item": "raw_fruit_scraps",
                "language": lang,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["language"] == lang
        assert len(resp.json()["data"]["title"]) > 0


# ---------------------------------------------------------------------------
# 4. User Journey & Pickup Confirmation Tests
# ---------------------------------------------------------------------------


def test_guidance_only_journey_creates_no_database_records(client: TestClient, db_session_fixture):
    """Verify that a citizen learning about waste handling creates ZERO database records."""
    count_reports_before = len(db_session_fixture.query(WasteReport).all())
    count_pickups_before = len(db_session_fixture.query(PickupRequest).all())

    # Citizen classifies image
    client.post(
        "/api/v1/waste-reports/classify-image",
        json={"image_url": "/static/uploads/fruit.jpg", "user_hint": "fruit_scraps"},
    )
    # Citizen reads guidance
    client.post(
        "/api/v1/waste-reports/guidance",
        json={"category": "wet_organic", "item": "raw_fruit_scraps"},
    )
    # Citizen exits back to home screen without requesting pickup
    count_reports_after = len(db_session_fixture.query(WasteReport).all())
    count_pickups_after = len(db_session_fixture.query(PickupRequest).all())

    assert count_reports_after == count_reports_before
    assert count_pickups_after == count_pickups_before


def test_explicit_pickup_submission_creates_report_and_pickup(client: TestClient):
    """Verify atomic WasteReport and PickupRequest creation ONLY upon explicit confirmation."""
    unique_url = f"/static/uploads/pickup_test_{uuid.uuid4().hex[:8]}.jpg"
    payload = {
        "confirmed_category": "dry_recyclable",
        "item": "plastic_bottle",
        "image_url": unique_url,
        "description": "Clean sorted plastic bottles ready for doorstep recycling",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "42 MG Road, Ward 110",
        "ward_number": "Ward-110",
        "estimated_weight_kg": 3.5,
    }

    response = client.post("/api/v1/waste-reports/request-pickup", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]
    assert "report_id" in data
    assert "pickup_id" in data
    assert data["category"] == "dry_recyclable"
    assert data["status"] == "scheduled"

    # Verify pickup request is queryable via existing pickup API
    pickup_resp = client.get(f"/api/v1/pickups/{data['pickup_id']}")
    assert pickup_resp.status_code == 200
    assert pickup_resp.json()["data"]["report_id"] == data["report_id"]


def test_explicit_pickup_blocks_prohibited_infectious_biomedical(client: TestClient):
    """Verify that attempting to request doorstep pickup for infectious waste is strictly blocked."""
    payload = {
        "confirmed_category": "sanitary",
        "item": "medical_bandages",
        "description": "Infectious blood-soaked dressings from patient care",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }

    response = client.post("/api/v1/waste-reports/request-pickup", json=payload)
    assert response.status_code == 422
    assert "doorstep pickup is prohibited" in response.json()["message"].lower()


def test_pickup_submission_duplicate_prevention(client: TestClient):
    """Verify that rapid duplicate submissions return existing request rather than creating duplicates."""
    unique_image = f"/static/uploads/duplicate_guard_{uuid.uuid4().hex[:8]}.jpg"
    payload = {
        "confirmed_category": "sanitary",
        "item": "used_diapers",
        "image_url": unique_image,
        "description": "Wrapped sanitary diaper bundle",
        "latitude": 12.9720,
        "longitude": 77.5950,
        "ward_number": "Ward-110",
    }

    # First submission
    resp1 = client.post("/api/v1/waste-reports/request-pickup", json=payload)
    assert resp1.status_code == 201
    report_id_1 = resp1.json()["data"]["report_id"]
    pickup_id_1 = resp1.json()["data"]["pickup_id"]

    # Second submission with identical image_url within 5 minutes
    resp2 = client.post("/api/v1/waste-reports/request-pickup", json=payload)
    assert resp2.status_code == 201
    data2 = resp2.json()["data"]
    assert data2["report_id"] == report_id_1
    assert data2["pickup_id"] == pickup_id_1
    assert "duplicate submission prevented" in data2["message"].lower()


# ---------------------------------------------------------------------------
# 5. Four-Category Exhaustive Guidance & Manual Confirmation Tests
# ---------------------------------------------------------------------------


def test_guidance_for_all_four_categories_generic(client: TestClient):
    """Verify correct guidance and routing for all 4 statutory categories without specific items."""
    # 1. wet_organic
    resp_wet = client.post("/api/v1/waste-reports/guidance", json={"category": "wet_organic", "language": "en"})
    assert resp_wet.status_code == 200
    assert resp_wet.json()["data"]["category"] == "wet_organic"
    assert resp_wet.json()["data"]["collection_recommended"] is True
    assert resp_wet.json()["data"]["pickup_available"] is True

    # 2. dry_recyclable
    resp_dry = client.post("/api/v1/waste-reports/guidance", json={"category": "dry_recyclable", "language": "en"})
    assert resp_dry.status_code == 200
    assert resp_dry.json()["data"]["category"] == "dry_recyclable"
    assert resp_dry.json()["data"]["action_outcome"] == "COLLECTION_APPROPRIATE"
    assert resp_dry.json()["data"]["pickup_available"] is True

    # 3. sanitary
    resp_san = client.post("/api/v1/waste-reports/guidance", json={"category": "sanitary", "language": "en"})
    assert resp_san.status_code == 200
    assert resp_san.json()["data"]["category"] == "sanitary"
    assert resp_san.json()["data"]["action_outcome"] == "COLLECTION_APPROPRIATE"
    assert resp_san.json()["data"]["pickup_available"] is True
    assert "red cross" not in resp_san.json()["data"]["scientific_guidance"].lower()
    assert "red cross" not in resp_san.json()["data"]["statutory_guidance"].lower()

    # 4. hazardous
    resp_haz = client.post("/api/v1/waste-reports/guidance", json={"category": "hazardous", "language": "en"})
    assert resp_haz.status_code == 200
    assert resp_haz.json()["data"]["category"] == "hazardous"
    assert resp_haz.json()["data"]["action_outcome"] == "SPECIAL_HANDLING_REQUIRED"
    assert resp_haz.json()["data"]["pickup_available"] is False
    assert resp_haz.json()["data"]["specialized_disposal_required"] is True


def test_manual_category_selection_and_confirmation(client: TestClient):
    """Verify citizen manual selection bypasses model uncertainty without fabricating AI claims."""
    payload = {
        "image_url": "/static/uploads/unclear_sample.jpg",
        "confirmed_category": "hazardous",
        "user_hint": "lead acid car battery",
    }
    response = client.post("/api/v1/waste-reports/classify-image", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["predicted_category"] == "hazardous"
    assert data["is_manual_selection"] is True
    assert data["requires_confirmation"] is False
    assert data["fallback_triggered"] is False
    assert data["suggested_action"] == "proceed_to_guidance"
    assert "manually confirmed" in data["message"].lower()


def test_unsupported_or_ambiguous_waste_item_safe_fallback(client: TestClient):
    """Verify that unrecognized items trigger safe manual confirmation."""
    payload = {
        "image_url": "/static/uploads/mystery_gear.jpg",
        "user_hint": "unknown mysterious component",
    }
    response = client.post("/api/v1/waste-reports/classify-image", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["requires_confirmation"] is True
    assert data["fallback_triggered"] is True
    assert data["suggested_action"] == "confirm_category"


def test_real_pytorch_model_inference_on_disk_image(client: TestClient):
    """Verify real MobileNetV3-Small tensor forward pass on actual uploaded image file."""
    # Generate a real valid JPEG image using PIL
    from PIL import Image as PILImage
    buf = io.BytesIO()
    test_img = PILImage.new("RGB", (128, 128), color=(30, 150, 40))
    test_img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    upload_resp = client.post(
        "/api/v1/waste-reports/upload-image",
        files={"file": ("test_tensor.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
    )
    assert upload_resp.status_code == 201
    file_url = upload_resp.json()["data"]["file_url"]

    # Request classification of this real on-disk image
    classify_resp = client.post(
        "/api/v1/waste-reports/classify-image",
        json={"image_url": file_url},
    )
    assert classify_resp.status_code == 200
    data = classify_resp.json()["data"]
    # Check that model executed and returned genuine model info
    assert "architecture" in data["model_info"]
    assert data["model_info"]["architecture"].startswith("MobileNetV3")
    # Confidence must be a valid float between 0.0 and 1.0
    assert 0.0 <= data["confidence"] <= 1.0

