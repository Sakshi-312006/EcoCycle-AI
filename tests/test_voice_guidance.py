"""Tests for Localized Waste Segregation Guidance and Multilingual UI Bundles."""

from starlette.testclient import TestClient


def test_get_supported_languages(client: TestClient) -> None:
    """Verify list of supported Indian regional and official languages."""
    res = client.get("/api/v1/voice/languages")
    assert res.status_code == 200
    data = res.json()["data"]

    assert len(data) == 6
    codes = [l["code"] for l in data]
    assert set(codes) == {"en", "hi", "kn", "ta", "te", "mr"}

    for lang in data:
        assert lang["name"]
        assert lang["local_name"]
        assert "-IN" in lang["bcp47_tag"]
        assert lang["is_fully_supported"] is True


def test_localized_instructions_all_six_languages(client: TestClient) -> None:
    """Verify that segregation guidelines for all 4 streams exist in all 6 supported languages."""
    supported_langs = ["en", "hi", "kn", "ta", "te", "mr"]
    required_streams = {"wet_organic", "dry_recyclable", "sanitary", "hazardous"}

    for lang in supported_langs:
        res = client.get(f"/api/v1/voice/instructions?lang={lang}")
        assert res.status_code == 200, f"Failed for language: {lang}"
        body = res.json()
        assert body["success"] is True

        data = body["data"]
        assert data["language_code"] == lang
        assert data["language_name"]
        assert len(data["general_guideline"]) > 10

        streams = data["streams"]
        assert set(streams.keys()) == required_streams

        for stream_key, stream_item in streams.items():
            assert stream_item["stream"] == stream_key
            assert stream_item["stream_name_localized"]
            assert len(stream_item["allowed_items"]) >= 2
            assert len(stream_item["disallowed_items"]) >= 1
            assert len(stream_item["handling_advice"]) > 5
            assert stream_item["color_hex"].startswith("#")
            assert stream_item["color_name"]
            assert stream_item["icon_symbol"] in ["leaf", "recycle", "medical", "alert"]
            assert stream_item["audio_prompt_text"]


def test_guidance_bundle_endpoint(client: TestClient) -> None:
    """Verify that full multilingual UI strings and visual stream guidance are returned."""
    res = client.get("/api/v1/voice/bundle?lang=kn")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["language_code"] == "kn"
    assert "ಕನ್ನಡ" in data["language_name"]
    assert data["bcp47_tag"] == "kn-IN"

    # UI strings check
    ui = data["ui_strings"]
    assert "app_title" in ui
    assert "btn_submit" in ui
    assert "field_description" in ui

    # Streams check
    assert "wet_organic" in data["streams"]
    assert "ಹಸಿ ಕಸ" in data["streams"]["wet_organic"]["stream_name_localized"]


def test_voice_bhashini_diagnostic_status(client: TestClient) -> None:
    """Verify that Bhashini probe reports unconfigured honestly when credentials are not in .env."""
    res = client.get("/api/v1/voice/bhashini/status")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["provider"] == "MeitY Bhashini"
    assert data["status"] in ["unconfigured", "configured_untested"]
    assert data["configured_credentials"] is False
    assert "not configured" in data["message"].lower() or "credentials" in data["message"].lower()
    assert "Integrity disclaimer" in data["disclaimer"] or "EcoCycle AI maintains" in data["disclaimer"]
