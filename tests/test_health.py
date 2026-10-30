"""Tests for root, health, liveness, readiness, and database probe endpoints."""

from starlette.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Test that GET / returns 200 and project metadata envelope."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "EcoCycle AI" in data["message"]
    assert data["data"]["project"] == "EcoCycle AI"
    assert data["data"]["docs_url"] == "/docs"


def test_health_root_endpoint(client: TestClient) -> None:
    """Test root /health alias endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["app_name"] == "EcoCycle AI"
    assert "status" in data["data"]
    assert "database" in data["data"]


def test_api_v1_health_summary(client: TestClient) -> None:
    """Test versioned /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert payload["app_name"] == "EcoCycle AI"
    assert payload["version"] == "0.1.0"
    assert payload["status"] in ["healthy", "degraded"]
    assert payload["uptime_seconds"] >= 0


def test_api_v1_health_liveness(client: TestClient) -> None:
    """Test /api/v1/health/live liveness probe."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


def test_api_v1_health_readiness(client: TestClient) -> None:
    """Test /api/v1/health/ready readiness probe."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ready"
    assert "api_server" in data["data"]["components"]
    assert data["data"]["components"]["api_server"] == "ready"


def test_api_v1_health_db_endpoint(client: TestClient) -> None:
    """Test /api/v1/health/db probe executes safely without unhandled crashes."""
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    # The endpoint should return a structured report even if DB is unconfigured or offline
    assert "data" in data
    db_data = data["data"]
    assert "status" in db_data
    assert "connected" in db_data
    assert isinstance(db_data["connected"], bool)
    assert db_data["status"] in ["connected", "disconnected", "unconfigured"]
