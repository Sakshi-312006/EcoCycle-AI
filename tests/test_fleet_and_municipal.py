"""Pillar 5: Fleet Prioritization, Municipal Dashboard, and Voice API tests."""

from starlette.testclient import TestClient


def test_fleet_priority_queue(client: TestClient) -> None:
    """Ensure hazardous waste reports are ranked with highest priority over inert streams."""
    # 1. Create a dry recyclable report
    dry_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "dry_recyclable",
            "description": "Clean cardboard boxes",
            "latitude": 12.92,
            "longitude": 77.60,
            "estimated_weight_kg": 2.0,
        },
    )
    dry_id = dry_res.json()["data"]["id"]
    client.post("/api/v1/pickups", json={"report_id": dry_id})

    # 2. Create a hazardous waste report
    haz_res = client.post(
        "/api/v1/waste-reports",
        json={
            "category": "hazardous",
            "description": "Chemical solvents and leaky lead battery",
            "latitude": 12.93,
            "longitude": 77.61,
            "estimated_weight_kg": 10.0,
        },
    )
    haz_id = haz_res.json()["data"]["id"]
    client.post("/api/v1/pickups", json={"report_id": haz_id})

    # 3. Retrieve priority queue
    queue_res = client.get("/api/v1/fleet/priority-queue")
    assert queue_res.status_code == 200
    queue = queue_res.json()["data"]
    assert queue["total_pending_pickups"] >= 2
    items = queue["items"]

    # First item should be the hazardous stream due to risk weight (100 pts)
    assert items[0]["category"] == "hazardous"
    assert items[0]["priority_tier"] in ["URGENT", "HIGH"]
    assert items[0]["priority_score"] > items[-1]["priority_score"]
    assert "stream_risk_points" in items[0]["scoring_breakdown"]


def test_municipal_dashboard_stats(client: TestClient) -> None:
    """Test dashboard compilation from active database rows."""
    res = client.get("/api/v1/municipal/dashboard")
    assert res.status_code == 200
    stats = res.json()["data"]
    assert "total_waste_reports" in stats
    assert stats["total_waste_reports"] > 0
    assert "reports_by_stream" in stats
    assert "total_verified_collections" in stats
    assert "total_waste_verified_kg" in stats
    assert "total_ecocredits_circulating" in stats
    assert "total_ecopass_households" in stats
    assert "ward_coverage" in stats


def test_voice_instructions_regional(client: TestClient) -> None:
    """Test localized segregation rules in English, Hindi, and Kannada."""
    # English
    en_res = client.get("/api/v1/voice/instructions?lang=en")
    assert en_res.status_code == 200
    en_data = en_res.json()["data"]
    assert en_data["language_code"] == "en"
    assert "wet_organic" in en_data["streams"]
    assert "Green" in en_data["streams"]["wet_organic"]["stream_name_localized"]

    # Hindi
    hi_res = client.get("/api/v1/voice/instructions?lang=hi")
    assert hi_res.status_code == 200
    hi_data = hi_res.json()["data"]
    assert hi_data["language_code"] == "hi"
    assert "कचरा" in hi_data["general_guideline"]
    assert "गीला जैविक कचरा" in hi_data["streams"]["wet_organic"]["stream_name_localized"]

    # Kannada
    kn_res = client.get("/api/v1/voice/instructions?lang=kn")
    assert kn_res.status_code == 200
    kn_data = kn_res.json()["data"]
    assert kn_data["language_code"] == "kn"
    assert "ತ್ಯಾಜ್ಯ" in kn_data["general_guideline"]


def test_bhashini_status_unconfigured(client: TestClient) -> None:
    """Verify Bhashini integration interface reports unconfigured cleanly without fake claims."""
    res = client.get("/api/v1/voice/bhashini/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["provider"] == "MeitY Bhashini"
    assert data["status"] in ["unconfigured", "configured_untested"]
    assert "credentials" in data["message"]
