"""Pillar 3: Circular Material Recovery, Upcycling, MRF Routing, Resale & Donation Tests."""

import io
import uuid
from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# Stream 3C & Resale Existing Tests (Preserved)
# ---------------------------------------------------------------------------


def test_create_resale_and_donation_listings(client: TestClient) -> None:
    """Test publishing resale and community donation listings."""
    # 1. Resale item
    resale_res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "resale",
            "title": "Solid Teak Study Table",
            "description": "Sturdy 4x2 foot study desk, minor scratch on drawer",
            "category": "furniture",
            "condition": "good",
            "price_inr": 2500.0,
            "donor_or_seller_name": "Ananya Roy",
        },
    )
    assert resale_res.status_code == 201
    resale = resale_res.json()["data"]
    assert resale["listing_type"] == "resale"
    assert resale["price_inr"] == 2500.0
    assert resale["status"] == "available"

    # 2. Donation item
    donation_res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "CBSE Class 10 & 12 Science Textbooks",
            "description": "Full set of physics and chemistry books in good shape",
            "category": "books",
            "condition": "like_new",
            "price_inr": 0.0,
            "donor_or_seller_name": "Vikram Patel",
            "beneficiary_ngo_name": "Community Children Library",
        },
    )
    assert donation_res.status_code == 201
    donation = donation_res.json()["data"]
    assert donation["listing_type"] == "donation"
    assert donation["price_inr"] is None
    assert donation["is_free"] is True


def test_claim_donation_awards_circular_credits(client: TestClient) -> None:
    """Ensure claiming a donation awards 50 circular diversion EcoCredits to the registered donor."""
    # 1. Register donor EcoPass
    donor_res = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Kulkarni Family",
            "ward_number": "55",
            "address": "12 Malleshwaram 7th Cross",
        },
    )
    donor_pass_id = donor_res.json()["data"]["ecopass_id"]

    # 2. Post item with donor EcoPass
    listing_res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Working Ceiling Fan",
            "description": "3-blade electric fan in functional condition",
            "category": "appliances",
            "condition": "good",
            "price_inr": 0.0,
            "donor_or_seller_name": "Kulkarni",
            "ecopass_id": donor_pass_id,
        },
    )
    listing_id = listing_res.json()["data"]["id"]

    # 3. Recipient claims the item
    claim_res = client.post(
        f"/api/v1/circular/listings/{listing_id}/claim",
        json={
            "claimer_name": "Shelter Home Volunteer",
            "notes": "Collected for youth shelter dorm",
        },
    )
    assert claim_res.status_code == 200
    assert claim_res.json()["data"]["status"] == "completed"

    # 4. Verify 50 EcoCredits credited to donor's EcoPass
    donor_check = client.get(f"/api/v1/ecopass/{donor_pass_id}")
    assert donor_check.status_code == 200
    assert donor_check.json()["data"]["balance_ecocredits"] == 50


def test_filter_circular_listings(client: TestClient) -> None:
    """Test filtering listings by category and listing_type."""
    res = client.get("/api/v1/circular/listings?category=books&listing_type=donation")
    assert res.status_code == 200
    items = res.json()["data"]
    assert all(i["category"] == "books" and i["listing_type"] == "donation" for i in items)


# ---------------------------------------------------------------------------
# Stream 3A: Rigid Plastics & Metals Tests
# ---------------------------------------------------------------------------


def test_stream_3a_rigid_plastics_and_metals_guidance_and_manual_selection(client: TestClient) -> None:
    """Test Stream 3A material catalog, manual selection, preparation requirements, and destinations."""
    # 1. Fetch Stream 3A catalog
    res = client.get("/api/v1/circular/materials/guidance?stream_type=stream_3a_rigid")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_categories"] == 4
    categories = {m["category_key"]: m for m in data["materials"]}

    # Verify all four required rigid streams exist
    assert "pet" in categories
    assert "hdpe" in categories
    assert "aluminium_cans" in categories
    assert "other_rigid" in categories

    # Verify PET guidance
    pet = categories["pet"]
    assert "Bottle-to-Bottle" in pet["intended_destination"]
    assert pet["destination_type"] == "mechanical_recycling"
    assert any("Bisleri" in ex for ex in pet["examples"])
    assert any("Crush" in prep for prep in pet["preparation_requirements"])
    assert pet["spi_resin_code"] == "SPI #1 (PET / PETE)"

    # Verify HDPE guidance
    hdpe = categories["hdpe"]
    assert "Pelletization" in hdpe["intended_destination"]
    assert any("shampoo" in ex.lower() for ex in hdpe["examples"])
    assert any("pump" in prep.lower() for prep in hdpe["preparation_requirements"])

    # Verify Aluminium Cans guidance
    alu = categories["aluminium_cans"]
    assert "Smelting" in alu["intended_destination"]
    assert any("Red Bull" in ex for ex in alu["examples"])

    # Verify Other Rigid guidance (PP #5 & Scrap Metals)
    other = categories["other_rigid"]
    assert "MRF" in other["intended_destination"]
    assert other["destination_type"] == "mechanical_recycling"

    # 2. Test targeted POST evaluation without requiring any AI classification model
    eval_res = client.post(
        "/api/v1/circular/materials/guidance",
        json={"stream_type": "stream_3a_rigid", "material_category": "hdpe"},
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()["data"]
    assert eval_data["category_key"] == "hdpe"
    assert eval_data["credit_eligible"] is True


def test_stream_3a_optional_pickup_and_verified_credits(client: TestClient) -> None:
    """Verify Stream 3A image upload, optional pickup creation, destination tracking, and verified collection crediting."""
    # 1. Upload waste image via Circular image upload endpoint
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x55" * 150
    upload_res = client.post(
        "/api/v1/circular/upload-image",
        files={"file": ("bottles.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert upload_res.status_code == 201
    image_url = upload_res.json()["data"]["file_url"]

    # 2. Register household EcoPass
    pass_res = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Mehta Residence",
            "ward_number": "150",
            "address": "45 Bellandur Lake Road",
        },
    )
    ecopass_id = pass_res.json()["data"]["ecopass_id"]

    # 3. Schedule optional pickup for Aluminium Cans
    pickup_res = client.post(
        "/api/v1/circular/materials/request-pickup",
        json={
            "stream_type": "stream_3a_rigid",
            "material_category": "aluminium_cans",
            "image_url": image_url,
            "description": "Bag of rinsed and crushed beverage cans",
            "latitude": 12.9352,
            "longitude": 77.6744,
            "address": "45 Bellandur Lake Road",
            "ward_number": "150",
            "ecopass_id": ecopass_id,
            "estimated_weight_kg": 3.0,
        },
    )
    assert pickup_res.status_code == 201
    pickup_data = pickup_res.json()["data"]
    pickup_id = pickup_data["pickup_id"]
    report_id = pickup_data["report_id"]
    assert pickup_data["status"] == "scheduled"
    assert "Aluminium" in pickup_data["intended_destination"]
    assert pickup_data["image_url"] == image_url

    # 4. Verify that credits are NOT awarded upon initial pickup creation
    balance_check_1 = client.get(f"/api/v1/ecopass/{ecopass_id}")
    assert balance_check_1.json()["data"]["balance_ecocredits"] == 0

    # 5. Check tracking details before verification
    tracking_1 = client.get(f"/api/v1/circular/materials/pickups/{pickup_id}")
    assert tracking_1.status_code == 200
    track_data_1 = tracking_1.json()["data"]
    assert track_data_1["collection_verified"] is False
    assert track_data_1["status"] == "scheduled"
    assert track_data_1["ecocredits_awarded"] == 0

    # 6. Physical collection occurs: Collector verifies collection with actual weight (3.5 kg)
    verify_res = client.post(
        f"/api/v1/pickups/{pickup_id}/verify",
        json={
            "actual_weight_kg": 3.5,
            "stream_confirmed": "dry_recyclable",
            "collector_signature_id": "COL-BANGALORE-102",
            "notes": "Verified clean crushed aluminium beverage cans",
        },
    )
    assert verify_res.status_code == 201
    verification = verify_res.json()["data"]
    assert verification["ecocredits_awarded"] == 35  # 10 credits / kg
    assert verification["actual_weight_kg"] == 3.5
    assert len(verification["integrity_hash"]) == 64

    # 7. Verify EcoCredits are now credited to generator's EcoPass ledger
    balance_check_2 = client.get(f"/api/v1/ecopass/{ecopass_id}")
    assert balance_check_2.json()["data"]["balance_ecocredits"] == 35

    # 8. Verify duplicate verification is prevented
    duplicate_res = client.post(
        f"/api/v1/pickups/{pickup_id}/verify",
        json={
            "actual_weight_kg": 3.5,
            "stream_confirmed": "dry_recyclable",
            "collector_signature_id": "COL-BANGALORE-102",
        },
    )
    assert duplicate_res.status_code == 422
    assert "already been verified" in duplicate_res.json()["message"]

    # 9. Verify tracking details reflect completed and verified collection
    tracking_2 = client.get(f"/api/v1/circular/materials/pickups/{pickup_id}")
    assert tracking_2.status_code == 200
    track_data_2 = tracking_2.json()["data"]
    assert track_data_2["collection_verified"] is True
    assert track_data_2["status"] == "completed"
    assert track_data_2["verified_weight_kg"] == 3.5
    assert track_data_2["ecocredits_awarded"] == 35
    assert "Secondary Aluminium Smelting" in track_data_2["intended_destination"]


# ---------------------------------------------------------------------------
# Stream 3B: Flexible & Multilayer Packaging Tests
# ---------------------------------------------------------------------------


def test_stream_3b_clean_wrapper_upcycling_vs_contaminated_industrial_recovery(client: TestClient) -> None:
    """Verify Stream 3B condition guidance: clean wrappers route to artisan upcycling, contaminated to industrial recovery."""
    # 1. Clean, Dry Wrappers Guidance Evaluation
    clean_eval = client.post(
        "/api/v1/circular/materials/guidance",
        json={
            "stream_type": "stream_3b_flexible",
            "packaging_condition": "clean_dry",
        },
    )
    assert clean_eval.status_code == 200
    clean_data = clean_eval.json()["data"]
    assert clean_data["category_key"] == "clean_wrapper"
    assert clean_data["destination_type"] == "artisan_upcycling"
    assert "Artisan Upcycling Studio" in clean_data["intended_destination"]
    assert "NEVER send to cement kilns" in clean_data["handling_instructions"]

    # 2. Dirty, Contaminated Packaging Guidance Evaluation
    dirty_eval = client.post(
        "/api/v1/circular/materials/guidance",
        json={
            "stream_type": "stream_3b_flexible",
            "packaging_condition": "dirty_contaminated",
        },
    )
    assert dirty_eval.status_code == 200
    dirty_data = dirty_eval.json()["data"]
    assert dirty_data["category_key"] == "contaminated_packaging"
    assert dirty_data["destination_type"] == "industrial_recovery"
    assert "Cement Kiln" in dirty_data["intended_destination"]
    assert "Bitumen Road" in dirty_data["intended_destination"]

    # 3. Register EcoPass for Stream 3B collection
    pass_res = client.post(
        "/api/v1/ecopass",
        json={
            "household_name": "Rao Family",
            "ward_number": "88",
            "address": "14 Indiranagar Double Road",
        },
    )
    ecopass_id = pass_res.json()["data"]["ecopass_id"]

    # 4. Request Pickup for Clean Wrappers -> Verify routing to Artisan Upcycling
    clean_pickup = client.post(
        "/api/v1/circular/materials/request-pickup",
        json={
            "stream_type": "stream_3b_flexible",
            "material_category": "clean_wrapper",
            "packaging_condition": "clean_dry",
            "description": "50 bundled dry Parle-G and biscuit wrappers",
            "latitude": 12.9784,
            "longitude": 77.6408,
            "address": "14 Indiranagar Double Road",
            "ward_number": "88",
            "ecopass_id": ecopass_id,
            "estimated_weight_kg": 1.2,
        },
    )
    assert clean_pickup.status_code == 201
    clean_p_data = clean_pickup.json()["data"]
    assert "Artisan Upcycling Studio" in clean_p_data["intended_destination"]
    assert clean_p_data["destination_type"] == "artisan_upcycling"
    clean_pickup_id = clean_p_data["pickup_id"]

    # 5. Verify physical collection and credit award for clean wrapper pickup
    verify_clean = client.post(
        f"/api/v1/pickups/{clean_pickup_id}/verify",
        json={
            "actual_weight_kg": 1.5,
            "stream_confirmed": "dry_recyclable",
            "collector_signature_id": "COL-INDIRA-09",
            "notes": "Bundle of clean, dry wrappers received for artisan upcycling center",
        },
    )
    assert verify_clean.status_code == 201
    # 1.5 kg -> max(10, int(1.5 * 10)) = 15 credits
    assert verify_clean.json()["data"]["ecocredits_awarded"] == 15

    # Generator balance updated
    gen_balance = client.get(f"/api/v1/ecopass/{ecopass_id}")
    assert gen_balance.json()["data"]["balance_ecocredits"] == 15

    # 6. Request Pickup for Contaminated Packaging -> Verify routing to Industrial Co-Processing
    dirty_pickup = client.post(
        "/api/v1/circular/materials/request-pickup",
        json={
            "stream_type": "stream_3b_flexible",
            "material_category": "contaminated_packaging",
            "packaging_condition": "dirty_contaminated",
            "description": "Greasy potato chips and pickle pouches",
            "latitude": 12.9784,
            "longitude": 77.6408,
            "address": "14 Indiranagar Double Road",
            "ward_number": "88",
            "ecopass_id": ecopass_id,
            "estimated_weight_kg": 2.0,
        },
    )
    assert dirty_pickup.status_code == 201
    dirty_p_data = dirty_pickup.json()["data"]
    assert "Industrial Co-Processing" in dirty_p_data["intended_destination"]
    assert dirty_p_data["destination_type"] == "industrial_recovery"


# ---------------------------------------------------------------------------
# Stream 3C & Resale Dedicated Workflow Tests
# ---------------------------------------------------------------------------


def test_resale_marketplace_complete_sale_workflow(client: TestClient) -> None:
    """Test full secondhand resale lifecycle: listing, pricing, querying, and completion."""
    # 1. Create Resale Listing
    res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "resale",
            "title": "Ergonomic Mesh Office Chair",
            "description": "Adjustable armrests, lumbar support, minor cosmetic wear on base",
            "category": "furniture",
            "condition": "good",
            "price_inr": 3500.0,
            "donor_or_seller_name": "Deepak Joshi",
        },
    )
    assert res.status_code == 201
    listing = res.json()["data"]
    listing_id = listing["id"]
    assert listing["listing_type"] == "resale"
    assert listing["price_inr"] == 3500.0
    assert listing["status"] == "available"

    # 2. Retrieve listing details
    get_res = client.get(f"/api/v1/circular/listings/{listing_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["title"] == "Ergonomic Mesh Office Chair"

    # 3. Complete Resale Transaction
    complete_res = client.post(
        f"/api/v1/circular/listings/{listing_id}/complete-sale",
        json={
            "buyer_name": "Rohan Deshmukh",
            "transaction_notes": "Paid via UPI, picked up in person",
        },
    )
    assert complete_res.status_code == 200
    completed_listing = complete_res.json()["data"]
    assert completed_listing["status"] == "completed"

    # 4. Prevent duplicate completion
    dup_res = client.post(
        f"/api/v1/circular/listings/{listing_id}/complete-sale",
        json={
            "buyer_name": "Another Buyer",
        },
    )
    assert dup_res.status_code == 422
    assert "cannot be completed" in dup_res.json()["message"]


def test_stream_3c_duplicate_claim_prevention(client: TestClient) -> None:
    """Ensure completed donation items cannot be claimed again."""
    # 1. Create donation
    res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Wooden Kids Toy Set",
            "description": "Educational stacking blocks in great shape",
            "category": "other",
            "condition": "like_new",
            "price_inr": 0.0,
            "donor_or_seller_name": "Nisha",
        },
    )
    listing_id = res.json()["data"]["id"]

    # 2. Claim first time
    claim_1 = client.post(
        f"/api/v1/circular/listings/{listing_id}/claim",
        json={"claimer_name": "Daycare Volunteer"},
    )
    assert claim_1.status_code == 200
    assert claim_1.json()["data"]["status"] == "completed"

    # 3. Claim second time -> Must be rejected with 422
    claim_2 = client.post(
        f"/api/v1/circular/listings/{listing_id}/claim",
        json={"claimer_name": "Second Volunteer"},
    )
    assert claim_2.status_code == 422
    assert "cannot be claimed" in claim_2.json()["message"]


def test_circular_material_pickup_validation_errors(client: TestClient) -> None:
    """Ensure invalid categories or contradictory conditions are properly rejected."""
    # Invalid category for Stream 3A Rigid
    invalid_3a = client.post(
        "/api/v1/circular/materials/request-pickup",
        json={
            "stream_type": "stream_3a_rigid",
            "material_category": "plastic_straws_invalid",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert invalid_3a.status_code == 422
    assert "Invalid material category" in invalid_3a.json()["message"]

    # Unknown category evaluation
    eval_invalid = client.post(
        "/api/v1/circular/materials/guidance",
        json={"stream_type": "stream_3a_rigid", "material_category": "unknown_material"},
    )
    assert eval_invalid.status_code == 422
    assert "Unknown material category" in eval_invalid.json()["message"]


# ---------------------------------------------------------------------------
# Donation and Resale Photo, Category, Condition, and Pricing Tests
# ---------------------------------------------------------------------------


def test_resale_listing_with_photo_category_condition_and_price(client: TestClient) -> None:
    """Verify resale listing creation with uploaded photo, valid category, condition, description, and price."""
    # 1. Upload photo of resale item
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x44" * 120
    upload_res = client.post(
        "/api/v1/circular/upload-image",
        files={"file": ("toy_set.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
    )
    assert upload_res.status_code == 201
    image_url = upload_res.json()["data"]["file_url"]

    # 2. Publish resale item
    resale_res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "resale",
            "title": "LEGO Technic Space Shuttle",
            "description": "Complete 1200-piece building set with original manual, no missing bricks",
            "category": "toys",
            "condition": "like_new",
            "price_inr": 2800.0,
            "donor_or_seller_name": "Siddharth Verma",
            "image_url": image_url,
        },
    )
    assert resale_res.status_code == 201
    resale = resale_res.json()["data"]
    listing_id = resale["id"]
    assert resale["listing_type"] == "resale"
    assert resale["category"] == "toys"
    assert resale["condition"] == "like_new"
    assert resale["price_inr"] == 2800.0
    assert resale["is_free"] is False
    assert resale["image_url"] == image_url
    assert resale["status"] == "available"

    # 3. Retrieve listing and verify stored image and price
    get_res = client.get(f"/api/v1/circular/listings/{listing_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()["data"]
    assert retrieved["image_url"] == image_url
    assert retrieved["price_inr"] == 2800.0
    assert retrieved["is_free"] is False


def test_donation_listing_with_photo_no_selling_price(client: TestClient) -> None:
    """Verify donation listing creation with uploaded photo, clothes category, and no selling price required or displayed."""
    # 1. Upload photo
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4" + b"\x00" * 50
    upload_res = client.post(
        "/api/v1/circular/upload-image",
        files={"file": ("sweaters.png", io.BytesIO(fake_png), "image/png")},
    )
    assert upload_res.status_code == 201
    image_url = upload_res.json()["data"]["file_url"]

    # 2. Publish donation without selling price
    donation_res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Winter Woolen Jackets (Ages 7-10)",
            "description": "Two warm insulated winter coats, clean and freshly washed, no tears",
            "category": "clothes",
            "condition": "good",
            "donor_or_seller_name": "Pooja Hegde",
            "image_url": image_url,
        },
    )
    assert donation_res.status_code == 201
    donation = donation_res.json()["data"]
    listing_id = donation["id"]
    assert donation["listing_type"] == "donation"
    assert donation["category"] == "clothes"
    assert donation["condition"] == "good"
    assert donation["price_inr"] is None
    assert donation["is_free"] is True
    assert donation["image_url"] == image_url

    # 3. Retrieve and ensure donation remains free with no price displayed
    get_res = client.get(f"/api/v1/circular/listings/{listing_id}")
    assert get_res.status_code == 200
    data = get_res.json()["data"]
    assert data["price_inr"] is None
    assert data["is_free"] is True
    assert data["image_url"] == image_url


def test_resale_price_validation_zero_negative_and_missing(client: TestClient) -> None:
    """Ensure resale listings strictly require an asking price greater than 0."""
    base_payload = {
        "listing_type": "resale",
        "title": "Handmade Wooden Bookshelf",
        "description": "Three tier pine bookshelf in fair condition",
        "category": "furniture",
        "condition": "fair",
        "donor_or_seller_name": "Arjun",
    }

    # Zero price rejected
    zero_res = client.post("/api/v1/circular/listings", json={**base_payload, "price_inr": 0.0})
    assert zero_res.status_code == 422
    assert any("greater than" in d.get("message", "").lower() for d in zero_res.json().get("details", []))

    # Negative price rejected
    neg_res = client.post("/api/v1/circular/listings", json={**base_payload, "price_inr": -50.0})
    assert neg_res.status_code == 422
    assert any("greater than" in d.get("message", "").lower() for d in neg_res.json().get("details", []))

    # Missing price rejected
    missing_res = client.post("/api/v1/circular/listings", json=base_payload)
    assert missing_res.status_code == 422
    assert any("greater than" in d.get("message", "").lower() for d in missing_res.json().get("details", []))


def test_donation_rejects_positive_price(client: TestClient) -> None:
    """Ensure donation items must be free and reject any asking price greater than 0."""
    res = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Children Math Puzzles",
            "description": "Cardboard puzzle set, clean and complete",
            "category": "toys",
            "condition": "good",
            "price_inr": 150.0,  # Positive price invalid for donation
            "donor_or_seller_name": "Kavita",
        },
    )
    assert res.status_code == 422
    assert any("free" in d.get("message", "").lower() for d in res.json().get("details", []))


def test_listing_invalid_and_fabricated_image_handling(client: TestClient) -> None:
    """Ensure fabricated URLs, path traversal, and invalid image formats are rejected."""
    base_listing = {
        "listing_type": "donation",
        "title": "Vintage Wall Clock",
        "description": "Functional pendulum wall clock with bronze trim",
        "category": "appliances",
        "condition": "good",
        "donor_or_seller_name": "Sunil",
    }

    # 1. Non-existent / fabricated URL
    fake_res = client.post(
        "/api/v1/circular/listings",
        json={**base_listing, "image_url": "/static/uploads/fabricated_ghost_photo_9999.jpg"},
    )
    assert fake_res.status_code == 422
    assert "fabricated" in fake_res.json()["message"].lower()

    # 2. Unsupported extension
    ext_res = client.post(
        "/api/v1/circular/listings",
        json={**base_listing, "image_url": "/static/uploads/malicious_script.exe"},
    )
    assert ext_res.status_code == 422
    assert "unsupported" in ext_res.json()["message"].lower()

    # 3. Path traversal attempt
    traversal_res = client.post(
        "/api/v1/circular/listings",
        json={**base_listing, "image_url": "/static/uploads/../../etc/passwd"},
    )
    assert traversal_res.status_code == 422
    assert "path traversal" in traversal_res.json()["message"].lower()


def test_listing_missing_and_invalid_required_fields(client: TestClient) -> None:
    """Validate mandatory fields: title, description, category, and condition."""
    # Missing title
    res_no_title = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "description": "Valid description with plenty of characters",
            "category": "books",
            "condition": "good",
            "donor_or_seller_name": "User",
        },
    )
    assert res_no_title.status_code == 422

    # Whitespace-only title
    res_ws_title = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "   ",
            "description": "Valid description with plenty of characters",
            "category": "books",
            "condition": "good",
            "donor_or_seller_name": "User",
        },
    )
    assert res_ws_title.status_code == 422

    # Short description
    res_short_desc = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Valid Title",
            "description": "Bad",
            "category": "books",
            "condition": "good",
            "donor_or_seller_name": "User",
        },
    )
    assert res_short_desc.status_code == 422

    # Invalid category
    res_bad_cat = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Valid Title",
            "description": "Valid description with plenty of characters",
            "category": "unsupported_space_junk",
            "condition": "good",
            "donor_or_seller_name": "User",
        },
    )
    assert res_bad_cat.status_code == 422

    # Invalid condition
    res_bad_cond = client.post(
        "/api/v1/circular/listings",
        json={
            "listing_type": "donation",
            "title": "Valid Title",
            "description": "Valid description with plenty of characters",
            "category": "books",
            "condition": "totally_broken_junk",
            "donor_or_seller_name": "User",
        },
    )
    assert res_bad_cond.status_code == 422


def test_create_listing_with_photo_multipart_endpoint(client: TestClient) -> None:
    """Test atomic single-request multipart listing creation with photo upload."""
    fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x88" * 100
    res = client.post(
        "/api/v1/circular/listings/with-photo",
        files={"file": ("desk_fan.jpg", io.BytesIO(fake_jpeg), "image/jpeg")},
        data={
            "listing_type": "resale",
            "title": "Portable High-Speed Table Fan",
            "description": "Compact 12-inch 3-speed oscillating fan, perfect working order",
            "category": "appliances",
            "condition": "good",
            "price_inr": "850.0",
            "donor_or_seller_name": "Meera Sen",
        },
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["title"] == "Portable High-Speed Table Fan"
    assert data["category"] == "appliances"
    assert data["price_inr"] == 850.0
    assert data["image_url"].startswith("/static/uploads/")


def test_existing_database_resale_record_intact() -> None:
    """Verify that existing database records in data/ecocycle_dev.db remain intact."""
    import sqlite3

    con = sqlite3.connect("data/ecocycle_dev.db")
    cur = con.cursor()
    cur.execute(
        "SELECT id, listing_type, title, price_inr, status, image_url FROM circular_listings WHERE title = 'Wooden Study Table';"
    )
    row = cur.fetchone()
    con.close()

    assert row is not None
    assert row[1] == "resale"
    assert row[2] == "Wooden Study Table"
    assert row[3] == 1500.0
    assert row[4] == "completed"
    assert row[5] is None
