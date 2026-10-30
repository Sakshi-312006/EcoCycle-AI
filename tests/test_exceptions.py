"""Tests for error handling, exception translations, and security hashing."""

from starlette.testclient import TestClient
from app.core.exceptions import AppException, EntityNotFoundException
from app.core.security import generate_sha256_hash, verify_sha256_hash


def test_404_not_found_envelope(client: TestClient) -> None:
    """Ensure non-existent routes return standard ErrorResponse envelope with HTTP 404."""
    response = client.get("/api/v1/non-existent-route-12345")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "ENDPOINT_NOT_FOUND"
    assert "timestamp" in data
    assert "message" in data


def test_405_method_not_allowed_envelope(client: TestClient) -> None:
    """Ensure invalid HTTP methods return standard ErrorResponse envelope with HTTP 405."""
    response = client.post("/api/v1/health/live")
    assert response.status_code == 405
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "METHOD_NOT_ALLOWED"


def test_sha256_integrity_helpers() -> None:
    """Test SHA-256 integrity generation and validation for EcoProof receipts."""
    payload = "ward-12:collector-99:household-4501:stream-organic:weight-4.2kg"
    digest = generate_sha256_hash(payload, salt="test-salt")
    assert isinstance(digest, str)
    assert len(digest) == 64

    # Verification should succeed for identical payload
    assert verify_sha256_hash(payload, digest, salt="test-salt") is True

    # Verification should fail for tampered payload
    tampered_payload = payload.replace("4.2kg", "0.2kg")
    assert verify_sha256_hash(tampered_payload, digest, salt="test-salt") is False


def test_custom_exception_properties() -> None:
    """Test custom exception construction and defaults."""
    exc = EntityNotFoundException("EcoPass", "EP-1002")
    assert exc.status_code == 404
    assert exc.error_code == "RESOURCE_NOT_FOUND"
    assert "EcoPass" in exc.message
    assert exc.details == [{"entity": "EcoPass", "identifier": "EP-1002"}]
