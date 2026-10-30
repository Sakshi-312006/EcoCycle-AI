"""Pillar 3: Circular Material Recovery, Upcycling, and Community Reuse Service."""

from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.circular import CircularListing
from app.models.pickup import PickupRequest
from app.models.waste import WasteReport
from app.schemas.circular import (
    CircularClaimRequest,
    CircularListingCreate,
    CircularMaterialGuidanceRequest,
    CircularPickupDetailResponse,
    CircularPickupRequest,
    CircularPickupResponse,
    CircularStreamTypeEnum,
    DestinationTypeEnum,
    MaterialGuidanceItem,
    PackagingCategoryEnum,
    PackagingConditionEnum,
    ResaleCompleteRequest,
    RigidMaterialCategoryEnum,
)
from app.services.ecopass_service import EcoPassService


# ---------------------------------------------------------------------------
# Authoritative Circular Material Catalog & Recovery Matrix
# ---------------------------------------------------------------------------

CIRCULAR_MATERIALS: Dict[str, MaterialGuidanceItem] = {
    "pet": MaterialGuidanceItem(
        category_key="pet",
        name="PET Bottles & Clear Food Jars",
        stream_type=CircularStreamTypeEnum.STREAM_3A_RIGID,
        spi_resin_code="SPI #1 (PET / PETE)",
        packaging_condition=None,
        accepted_items=[
            "Clear drinking water bottles",
            "Carbonated beverage and soda bottles",
            "Transparent fruit juice and squash bottles",
            "Clear transparent cooking oil containers",
            "Transparent food storage jars with resin mark #1",
        ],
        rejected_items=[
            "Opaque or colored milk/shampoo bottles (classified as HDPE #2)",
            "Lubricating motor oil bottles or pesticide bottles",
            "Multilayer foil pouches (Stream 3B)",
            "Heavily burnt, degraded, or bio-contaminated plastics",
        ],
        preparation_requirements=[
            "Empty all liquid contents completely",
            "Rinse with clean water to remove sweet or sticky beverage residue",
            "Crush or flatten bottle vertically/horizontally to minimize collection bin volume",
            "Remove external non-recyclable pump tops if present (simple screw caps can remain)",
            "Keep dry and completely segregated from wet organic garbage",
        ],
        examples=[
            "Bisleri 1L drinking water bottle",
            "Coca-Cola / Pepsi 500ml beverage bottle",
            "Real Fruit Juice transparent bottle",
            "Saffola clear cooking oil container",
        ],
        intended_destination="Registered Mechanical PET Recycler (Bottle-to-Bottle Recycling & Polyester Staple Fiber Spinning)",
        destination_type=DestinationTypeEnum.MECHANICAL_RECYCLING,
        credit_eligible=True,
        handling_instructions="Store clean and crushed in a dedicated dry-recyclables bag. Hand over during doorstep collection or drop off at the municipal dry waste collection centre (DWCC).",
    ),
    "hdpe": MaterialGuidanceItem(
        category_key="hdpe",
        name="HDPE Rigid Bottles, Jugs & Containers",
        stream_type=CircularStreamTypeEnum.STREAM_3A_RIGID,
        spi_resin_code="SPI #2 (HDPE)",
        packaging_condition=None,
        accepted_items=[
            "Rigid milk, buttermilk, and curd jugs",
            "Shampoo, conditioner, and body wash bottles",
            "Liquid laundry detergent and fabric softener containers",
            "Solid plastic buckets, basins, and tubs",
            "Cosmetic cream and lotion jars with HDPE resin mark",
        ],
        rejected_items=[
            "Mechanical pump dispensers containing internal steel springs (remove before handover)",
            "Flexible single-layer or multilayer milk pouches (classified under Stream 3B)",
            "Hazardous agrochemical, pesticide, or toxic solvent drums",
            "Contaminated biomedical containers",
        ],
        preparation_requirements=[
            "Drain all detergent, shampoo, or liquid soap contents completely",
            "Rinse thoroughly with water to eliminate residual suds and scum",
            "Unscrew and discard mechanical trigger/pump heads into non-recyclable disposal",
            "Air dry inverted before placing into the collection bin",
        ],
        examples=[
            "Amul / Mother Dairy rigid milk bottle",
            "Head & Shoulders shampoo bottle",
            "Surf Excel liquid detergent jug",
            "Clean Asian Paints plastic bucket",
        ],
        intended_destination="Mechanical HDPE Recycler (Extrusion Pelletization for Industrial Crates & Non-Pressure Agricultural Pipes)",
        destination_type=DestinationTypeEnum.MECHANICAL_RECYCLING,
        credit_eligible=True,
        handling_instructions="Rinse clean and remove pump tops. HDPE is a premium polymer with high secondary extrusion demand.",
    ),
    "aluminium_cans": MaterialGuidanceItem(
        category_key="aluminium_cans",
        name="Aluminium Beverage Cans & Clean Food Tins",
        stream_type=CircularStreamTypeEnum.STREAM_3A_RIGID,
        spi_resin_code="ALU (#41 Aluminium)",
        packaging_condition=None,
        accepted_items=[
            "Aluminium soda, carbonated drink, and energy drink cans",
            "Clean aluminium foil food takeaway trays and containers",
            "Clean steel / tin-plated canned vegetable and fruit tins",
            "Clean metal crown bottle caps and jar lids",
        ],
        rejected_items=[
            "Pressurized aerosol insecticide/spray cans with propellant still inside (Hazardous)",
            "Paint tins coated with wet or toxic oil-based paint residues",
            "Lead-acid battery components or electronic scrap",
            "Food tins containing decaying, moldy meat or fish remains",
        ],
        preparation_requirements=[
            "Pour out any remaining liquid or beverage",
            "Rinse thoroughly with water to prevent attracting insects and odors",
            "Lightly crush beverage cans to reduce transport bulk",
            "Ensure metal edges are pushed inward safely to prevent injury to sanitation workers",
        ],
        examples=[
            "Red Bull 250ml can",
            "Thums Up / Diet Coke 330ml can",
            "Clean aluminium biryani takeaway tray",
            "Nestle Milkmaid tin (washed and clean)",
        ],
        intended_destination="Secondary Aluminium Smelting Unit & Secondary Foundry (Closed-Loop Can-to-Can Remelting)",
        destination_type=DestinationTypeEnum.MECHANICAL_RECYCLING,
        credit_eligible=True,
        handling_instructions="Aluminium retains 95% energy savings in secondary remelting compared to primary bauxite smelting. Rinse, crush, and hand over.",
    ),
    "other_rigid": MaterialGuidanceItem(
        category_key="other_rigid",
        name="Other Rigid Plastics (PP #5) & Scrap Metals",
        stream_type=CircularStreamTypeEnum.STREAM_3A_RIGID,
        spi_resin_code="SPI #5 (PP) & Scrap Metal",
        packaging_condition=None,
        accepted_items=[
            "Polypropylene takeaway containers and microwaveable lids (PP #5)",
            "Curd, yogurt, and ice cream rigid plastic tubs (clean)",
            "Rigid plastic storage crates and broken plastic stools",
            "Clean household brass, copper, aluminium, or mild steel offcuts",
        ],
        rejected_items=[
            "Expanded polystyrene foam / thermocol (non-recyclable packaging)",
            "PVC pipes and construction masonry (Pillar 2 C&D Waste)",
            "Medical sharps or broken mercury thermometers",
        ],
        preparation_requirements=[
            "Wipe off visible food grease, oils, or organic residues",
            "Rinse with water and let dry",
            "Bundle metal scrap safely to prevent sharp puncture injuries",
        ],
        examples=[
            "Epigamia Greek yogurt cup",
            "Haldiram sweet plastic box (PP #5)",
            "Broken plastic laundry stool",
            "Clean brass plumbing fixture offcut",
        ],
        intended_destination="Registered Material Recovery Facility (MRF) Secondary Mechanical Recycler & Scrap Aggregator",
        destination_type=DestinationTypeEnum.MECHANICAL_RECYCLING,
        credit_eligible=True,
        handling_instructions="Segregate by resin code where marked. Ensure items are clean, unsoiled, and safely boxed or bundled.",
    ),
    "clean_wrapper": MaterialGuidanceItem(
        category_key="clean_wrapper",
        name="Clean & Dry Flexible Wrappers (Upcycling Stream)",
        stream_type=CircularStreamTypeEnum.STREAM_3B_FLEXIBLE,
        spi_resin_code="SPI #7 (Clean MLP / Monolayer)",
        packaging_condition=PackagingConditionEnum.CLEAN_DRY,
        accepted_items=[
            "Clean, dry biscuit and cookie wrappers",
            "Clean confectionery, chocolate, and candy packaging",
            "Clean e-commerce courier bags and bubble wrap",
            "Rinsed and thoroughly dried snack bags with zero oily residue",
            "Clean monolayer polyethylene grocery wrappers and bread bags",
        ],
        rejected_items=[
            "Oily, greasy, or curry-stained packaging wrappers",
            "Wrappers with attached food crumbs, dried gravy, or mold",
            "Pesticide, fertilizer, or agrochemical flexible sachets",
            "Dirty, unwashed milk packets",
        ],
        preparation_requirements=[
            "Shake out all loose food crumbs and crumbs completely",
            "Wipe clean with a cloth or rinse and dry completely before storing",
            "Flatten wrappers and bundle multiple items into a single clean envelope or pouch",
            "Keep strictly dry and separate from any moist kitchen waste",
        ],
        examples=[
            "Parle-G / Britannia biscuit wrapper (dry)",
            "Cadbury Dairy Milk wrapper (clean)",
            "Amazon / Flipkart plastic mailer bag (clean)",
            "Clean bubble wrap cushioning rolls",
        ],
        intended_destination="Artisan Upcycling Studio (Hand-Woven Bags, Pouches & Planters) & Eco-Board Compressed Architectural Panel Manufacturer",
        destination_type=DestinationTypeEnum.ARTISAN_UPCYCLING,
        credit_eligible=True,
        handling_instructions="High-value stream for circular community upcycling! Clean wrappers are hand-woven by artisan collectives into bags or heat-compressed into timber-substitute eco-boards. NEVER send to cement kilns or incinerators when clean and dry.",
    ),
    "contaminated_packaging": MaterialGuidanceItem(
        category_key="contaminated_packaging",
        name="Dirty, Oily, or Contaminated Multilayer Packaging",
        stream_type=CircularStreamTypeEnum.STREAM_3B_FLEXIBLE,
        spi_resin_code="SPI #7 (Contaminated Multilayer Plastic)",
        packaging_condition=PackagingConditionEnum.DIRTY_CONTAMINATED,
        accepted_items=[
            "Oily potato chip pouches with greasy inner metallized film",
            "Greasy masala and spice mix packaging sachets",
            "Pickle and cooking oil pouches with unremovable residues",
            "Meat, dairy, and fish flexible packaging film",
            "Food delivery wrappers soiled with butter, oil, or gravies",
        ],
        rejected_items=[
            "Clean dry wrappers (route to Artisan Upcycling to preserve material value)",
            "Biodegradable / compostable PLA films (route to Organic Composting)",
            "Hazardous biomedical bandages or infectious wraps",
        ],
        preparation_requirements=[
            "Squeeze out any remaining liquids, sauces, or pastes",
            "Do NOT mix with clean dry recyclables (prevents contaminating clean paper and rigid plastics)",
            "Fold tightly and pack in designated non-recyclable discard bag",
        ],
        examples=[
            "Lay's Magic Masala greasy chips pouch",
            "Mother's Recipe pickle pouch with oil residue",
            "Maggi Tastemaker seasoning sachet",
            "Soiled food delivery butter-paper wrapper",
        ],
        intended_destination="Authorized Industrial Co-Processing (Cement Kiln High-Temperature Energy Recovery) & Polymer-Modified Bitumen Road Construction",
        destination_type=DestinationTypeEnum.INDUSTRIAL_RECOVERY,
        credit_eligible=True,
        handling_instructions="Due to oil/food contamination, mechanical recycling and artisan upcycling are not viable. Under CPCB Guidelines, this material is safely co-processed in high-temperature cement kilns (>1400°C) with zero slag, or shredded for polymer-modified bitumen road paving (IRC:SP:98-2020). If industrial recovery is unavailable in the ward, route to Controlled Municipal Solid Waste Processing (RDF).",
    ),
}


class CircularService:
    """Service handling circular material recovery, donation, resale, and MRF routing."""

    # -----------------------------------------------------------------------
    # Stream 3C & Resale Workflows
    # -----------------------------------------------------------------------

    @staticmethod
    def validate_listing_image_url(image_url: Optional[str]) -> Optional[str]:
        """Validate that provided image URL points to a real, validly uploaded image file."""
        if not image_url:
            return None

        clean_url = image_url.strip()
        if not clean_url:
            return None

        # 1. Reject path traversal and unsafe backslashes
        if ".." in clean_url or "\\" in clean_url:
            raise ValidationException("Path traversal or backslashes detected in image URL.")

        # 2. Reject unsupported extensions
        ext = Path(clean_url).suffix.lower()
        allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
        if ext not in allowed_exts:
            raise ValidationException(
                f"Unsupported image file extension '{ext}'. Allowed extensions: {sorted(list(allowed_exts))}"
            )

        # 3. File existence check under STORAGE_LOCAL_PATH
        if clean_url.startswith("/static/uploads/"):
            filename = clean_url[len("/static/uploads/") :].lstrip("/")
        elif clean_url.startswith("static/uploads/"):
            filename = clean_url[len("static/uploads/") :].lstrip("/")
        else:
            filename = os.path.basename(clean_url)

        target_file = Path(settings.STORAGE_LOCAL_PATH) / filename
        if not target_file.is_file():
            raise ValidationException(
                f"Image file not found at '{clean_url}'. Broken or fabricated image URLs are not permitted."
            )

        # 4. File size validation according to project conventions
        size = target_file.stat().st_size
        if size <= 0:
            raise ValidationException("Image file on server is empty (0 bytes).")
        if size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValidationException(
                f"Image file exceeds maximum permitted size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB."
            )

        return f"/static/uploads/{filename}"

    @staticmethod
    def create_listing(db: Session, listing_in: CircularListingCreate) -> CircularListing:
        """Create a new circular reuse or donation listing."""
        validated_image_url = CircularService.validate_listing_image_url(listing_in.image_url)

        listing = CircularListing(
            listing_type=listing_in.listing_type.value,
            title=listing_in.title,
            description=listing_in.description,
            category=listing_in.category.value,
            condition=listing_in.condition.value,
            price_inr=listing_in.price_inr if listing_in.price_inr is not None else 0.0,
            donor_or_seller_name=listing_in.donor_or_seller_name,
            image_url=validated_image_url,
            ecopass_id=listing_in.ecopass_id,
            beneficiary_ngo_name=listing_in.beneficiary_ngo_name,
            status="available",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def get_listing_by_id(db: Session, listing_id: uuid.UUID) -> CircularListing:
        """Fetch listing by ID."""
        listing = db.execute(select(CircularListing).where(CircularListing.id == listing_id)).scalar_one_or_none()
        if not listing:
            raise EntityNotFoundException("CircularListing", str(listing_id))
        return listing

    @staticmethod
    def list_listings(
        db: Session,
        listing_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CircularListing]:
        """Query circular listings with filters."""
        query = select(CircularListing).order_by(desc(CircularListing.created_at))
        if listing_type:
            query = query.where(CircularListing.listing_type == listing_type)
        if category:
            cat_lower = category.lower()
            if cat_lower in ("clothing", "cloth", "clothes"):
                query = query.where(CircularListing.category.in_(["clothes", "clothing"]))
            elif cat_lower in ("electronic", "electronics"):
                query = query.where(CircularListing.category.in_(["appliances", "electronics"]))
            else:
                query = query.where(CircularListing.category == category)
        if status:
            query = query.where(CircularListing.status == status)

        return list(db.execute(query.limit(limit).offset(offset)).scalars().all())

    @staticmethod
    def claim_listing(db: Session, listing_id: uuid.UUID, claim_in: CircularClaimRequest) -> CircularListing:
        """Claim a donation or finalize recovery of an item for circular recovery."""
        listing = CircularService.get_listing_by_id(db, listing_id)
        if listing.status != "available":
            raise ValidationException(f"Listing is currently '{listing.status}' and cannot be claimed.")

        listing.status = "completed"

        # If donor provided an EcoPass ID, disburse 50 diversion EcoCredits
        if listing.ecopass_id:
            EcoPassService.award_credits(
                db=db,
                ecopass_id=listing.ecopass_id,
                amount=50,
                transaction_type="circular_diversion_reward",
                reference_id=str(listing.id),
                description=f"Circular recovery reward for '{listing.title}' claimed by {claim_in.claimer_name}",
            )

        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def complete_resale(db: Session, listing_id: uuid.UUID, request: ResaleCompleteRequest) -> CircularListing:
        """Finalize a secondhand marketplace resale transaction."""
        listing = CircularService.get_listing_by_id(db, listing_id)
        if listing.status != "available":
            raise ValidationException(f"Resale listing is currently '{listing.status}' and cannot be completed.")
        if listing.listing_type != "resale":
            raise ValidationException("Only listings with type 'resale' can be finalized via resale completion.")

        listing.status = "completed"
        db.commit()
        db.refresh(listing)
        return listing

    # -----------------------------------------------------------------------
    # Stream 3A & Stream 3B: MRF Guidance & Material Routing
    # -----------------------------------------------------------------------

    @staticmethod
    def get_material_catalog(
        stream_type: Optional[CircularStreamTypeEnum] = None,
        condition: Optional[PackagingConditionEnum] = None,
    ) -> List[MaterialGuidanceItem]:
        """Retrieve material catalog filtered by stream or packaging condition."""
        results: List[MaterialGuidanceItem] = []
        for item in CIRCULAR_MATERIALS.values():
            if stream_type and item.stream_type != stream_type:
                continue
            if condition and item.packaging_condition is not None and item.packaging_condition != condition:
                continue
            results.append(item)
        return results

    @staticmethod
    def evaluate_material_guidance(request: CircularMaterialGuidanceRequest) -> MaterialGuidanceItem:
        """Evaluate and return specific guidance for a circular material selection."""
        cat_key = (request.material_category or "").strip().lower()

        # Resolve 3B packaging by condition if category key not directly passed
        if request.stream_type == CircularStreamTypeEnum.STREAM_3B_FLEXIBLE and not cat_key:
            if request.packaging_condition == PackagingConditionEnum.CLEAN_DRY:
                cat_key = "clean_wrapper"
            elif request.packaging_condition == PackagingConditionEnum.DIRTY_CONTAMINATED:
                cat_key = "contaminated_packaging"
            else:
                raise ValidationException(
                    "For Stream 3B flexible packaging, please specify packaging_condition ('clean_dry' or 'dirty_contaminated')."
                )

        if not cat_key:
            raise ValidationException("Material category must be specified (e.g. pet, hdpe, aluminium_cans, clean_wrapper).")

        item = CIRCULAR_MATERIALS.get(cat_key)
        if not item:
            valid_keys = list(CIRCULAR_MATERIALS.keys())
            raise ValidationException(f"Unknown material category '{cat_key}'. Valid categories: {valid_keys}")

        # If stream_type provided, ensure compatibility
        if request.stream_type and item.stream_type != request.stream_type:
            raise ValidationException(
                f"Category '{cat_key}' belongs to stream '{item.stream_type.value}', but '{request.stream_type.value}' was specified."
            )

        return item

    # -----------------------------------------------------------------------
    # Stream 3A & 3B: Optional Pickup Request & Verified Collection Tracking
    # -----------------------------------------------------------------------

    @staticmethod
    def request_circular_pickup(db: Session, request: CircularPickupRequest) -> CircularPickupResponse:
        """Schedule an optional doorstep pickup for sorted circular materials."""
        # Validate stream and material selection
        cat_key = (request.material_category or "").strip().lower()

        if request.stream_type == CircularStreamTypeEnum.STREAM_3A_RIGID:
            valid_3a = ["pet", "hdpe", "aluminium_cans", "other_rigid"]
            if cat_key not in valid_3a:
                raise ValidationException(
                    f"Invalid material category '{cat_key}' for Stream 3A Rigid. Choose from: {valid_3a}"
                )
        elif request.stream_type == CircularStreamTypeEnum.STREAM_3B_FLEXIBLE:
            # Map condition if clean_wrapper or contaminated_packaging not explicitly used
            if cat_key in ["clean_wrapper", "clean_dry_wrappers", "clean_dry"]:
                cat_key = "clean_wrapper"
            elif cat_key in ["contaminated_packaging", "dirty_packaging", "dirty_contaminated"]:
                cat_key = "contaminated_packaging"
            elif request.packaging_condition == PackagingConditionEnum.CLEAN_DRY:
                cat_key = "clean_wrapper"
            elif request.packaging_condition == PackagingConditionEnum.DIRTY_CONTAMINATED:
                cat_key = "contaminated_packaging"
            else:
                raise ValidationException(
                    "For Stream 3B Flexible Packaging, specify condition ('clean_dry' or 'dirty_contaminated') "
                    "or category ('clean_wrapper' or 'contaminated_packaging')."
                )

        material_item = CIRCULAR_MATERIALS.get(cat_key)
        if not material_item:
            raise ValidationException(f"Material category '{cat_key}' could not be resolved.")

        # Determine condition string
        cond_str = (
            request.packaging_condition.value
            if request.packaging_condition
            else (material_item.packaging_condition.value if material_item.packaging_condition else None)
        )

        # Prepare formatted description for municipal and collector context
        dest_tag = f"Dest: {material_item.intended_destination}"
        cond_tag = f"Condition: {cond_str}" if cond_str else "Rigid Segregated"
        combined_desc = (
            f"[Circular {request.stream_type.value.upper()} | {material_item.name} | {cond_tag} | {dest_tag}] "
            f"{request.description or 'Circular material collection request'}"
        )

        # 1. Create statutory WasteReport (under dry_recyclable for SWM 2016 compartment compatibility)
        report = WasteReport(
            category="dry_recyclable",
            description=combined_desc,
            image_url=request.image_url,
            latitude=request.latitude,
            longitude=request.longitude,
            address=request.address,
            ward_number=request.ward_number,
            ecopass_id=request.ecopass_id,
            estimated_weight_kg=request.estimated_weight_kg,
            status="assigned",
        )
        db.add(report)
        db.flush()

        # 2. Create linked PickupRequest
        pickup = PickupRequest(
            report_id=report.id,
            collector_id=request.collector_id,
            collector_name=request.collector_name,
            vehicle_id=request.vehicle_id,
            scheduled_time=request.scheduled_time,
            status="scheduled",
        )
        db.add(pickup)
        db.commit()
        db.refresh(report)
        db.refresh(pickup)

        credit_notice = (
            f"EcoCredits will be awarded to EcoPass '{request.ecopass_id}' only after verified collection handover."
            if request.ecopass_id
            else "No EcoPass ID provided; collection scheduled without credit reward."
        )

        msg = (
            f"Circular pickup scheduled for {material_item.name}. "
            f"Intended destination: {material_item.intended_destination}. {credit_notice}"
        )

        return CircularPickupResponse(
            report_id=report.id,
            pickup_id=pickup.id,
            stream_type=request.stream_type.value,
            material_category=cat_key,
            material_name=material_item.name,
            packaging_condition=cond_str,
            intended_destination=material_item.intended_destination,
            destination_type=material_item.destination_type.value,
            status="scheduled",
            image_url=request.image_url,
            ecopass_id=request.ecopass_id,
            estimated_weight_kg=request.estimated_weight_kg,
            message=msg,
            created_at=pickup.created_at,
        )

    @staticmethod
    def get_circular_pickup_details(db: Session, pickup_id: uuid.UUID) -> CircularPickupDetailResponse:
        """Fetch tracking details, verification status, and destination for a circular pickup."""
        pickup = db.execute(
            select(PickupRequest)
            .options(
                joinedload(PickupRequest.waste_report),
                joinedload(PickupRequest.verification),
            )
            .where(PickupRequest.id == pickup_id)
        ).scalar_one_or_none()

        if not pickup:
            raise EntityNotFoundException("PickupRequest", str(pickup_id))

        report = pickup.waste_report
        desc_text = report.description if report else ""

        # Extract material and destination from description if present
        stream_type = "stream_3a_rigid"
        material_key = "pet"
        material_name = "PET Bottles & Clear Food Jars"
        intended_destination = "Registered Mechanical PET Recycler"
        destination_type = DestinationTypeEnum.MECHANICAL_RECYCLING.value
        packaging_condition = None

        if "STREAM_3B_FLEXIBLE" in desc_text.upper():
            stream_type = "stream_3b_flexible"
            if "CLEAN" in desc_text.upper() or "UPCYCLING" in desc_text.upper():
                material_key = "clean_wrapper"
                packaging_condition = "clean_dry"
                item = CIRCULAR_MATERIALS["clean_wrapper"]
            else:
                material_key = "contaminated_packaging"
                packaging_condition = "dirty_contaminated"
                item = CIRCULAR_MATERIALS["contaminated_packaging"]
            material_name = item.name
            intended_destination = item.intended_destination
            destination_type = item.destination_type.value
        elif "STREAM_3A_RIGID" in desc_text.upper():
            stream_type = "stream_3a_rigid"
            for k in ["hdpe", "aluminium_cans", "other_rigid", "pet"]:
                if k in desc_text.lower() or CIRCULAR_MATERIALS[k].name.lower() in desc_text.lower():
                    material_key = k
                    break
            item = CIRCULAR_MATERIALS.get(material_key, CIRCULAR_MATERIALS["pet"])
            material_name = item.name
            intended_destination = item.intended_destination
            destination_type = item.destination_type.value

        # Verification details
        is_verified = pickup.verification is not None
        verified_weight = pickup.verification.actual_weight_kg if is_verified else None
        credits = pickup.verification.ecocredits_awarded if is_verified else 0
        integrity_hash = pickup.verification.integrity_hash if is_verified else None
        sig_id = pickup.verification.collector_signature_id if is_verified else None
        verified_at = pickup.verification.verified_at if is_verified else None

        return CircularPickupDetailResponse(
            pickup_id=pickup.id,
            report_id=report.id if report else pickup.report_id,
            stream_type=stream_type,
            material_category=material_key,
            material_name=material_name,
            packaging_condition=packaging_condition,
            intended_destination=intended_destination,
            destination_type=destination_type,
            status=pickup.status,
            collection_verified=is_verified,
            verified_weight_kg=verified_weight,
            ecocredits_awarded=credits,
            integrity_hash=integrity_hash,
            collector_signature_id=sig_id,
            verified_at=verified_at,
            ecopass_id=report.ecopass_id if report else None,
            address=report.address if report else None,
            created_at=pickup.created_at,
        )
