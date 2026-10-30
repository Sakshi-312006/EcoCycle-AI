"""Pillar 2: Pickup and EcoProof Verification Service."""

import base64
from datetime import datetime, timezone
import io
from typing import List, Optional
import uuid
import qrcode
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import EntityNotFoundException, ValidationException
from app.core.security import generate_sha256_hash
from app.models.pickup import PickupRequest, VerificationRecord
from app.models.waste import WasteReport
from app.schemas.pickup import (
    CollectionVerificationCreate,
    PickupCreate,
    PickupQRCodeResponse,
    PickupStatusUpdate,
    PickupVerificationStatusResponse,
)
from app.services.ecopass_service import EcoPassService


class PickupService:
    """Service handling pickup dispatch and EcoProof cryptographic verification."""

    @staticmethod
    def create_pickup(db: Session, pickup_in: PickupCreate) -> PickupRequest:
        """Schedule a collection pickup for a logged waste report."""
        report = db.execute(select(WasteReport).where(WasteReport.id == pickup_in.report_id)).scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("WasteReport", str(pickup_in.report_id))

        pickup = PickupRequest(
            report_id=pickup_in.report_id,
            collector_id=pickup_in.collector_id,
            collector_name=pickup_in.collector_name,
            vehicle_id=pickup_in.vehicle_id,
            scheduled_time=pickup_in.scheduled_time,
            status="scheduled",
        )
        report.status = "assigned"
        db.add(pickup)
        db.commit()
        db.refresh(pickup)
        return pickup

    @staticmethod
    def get_pickup_by_id(db: Session, pickup_id: uuid.UUID) -> PickupRequest:
        """Fetch pickup with verification relationship."""
        pickup = db.execute(
            select(PickupRequest)
            .options(joinedload(PickupRequest.verification))
            .where(PickupRequest.id == pickup_id)
        ).scalar_one_or_none()
        if not pickup:
            raise EntityNotFoundException("PickupRequest", str(pickup_id))
        return pickup

    @staticmethod
    def list_pickups(
        db: Session,
        status: Optional[str] = None,
        collector_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PickupRequest]:
        """List pickups with optional filters."""
        query = select(PickupRequest).options(joinedload(PickupRequest.verification)).order_by(desc(PickupRequest.created_at))
        if status:
            query = query.where(PickupRequest.status == status)
        if collector_id:
            query = query.where(PickupRequest.collector_id == collector_id)
        return list(db.execute(query.limit(limit).offset(offset)).scalars().unique().all())

    @staticmethod
    def update_status(db: Session, pickup_id: uuid.UUID, update_in: PickupStatusUpdate) -> PickupRequest:
        """Transition pickup status."""
        pickup = PickupService.get_pickup_by_id(db, pickup_id)
        pickup.status = update_in.status.value
        db.commit()
        db.refresh(pickup)
        return pickup

    @staticmethod
    def verify_collection(
        db: Session,
        pickup_id: uuid.UUID,
        verify_in: CollectionVerificationCreate,
    ) -> VerificationRecord:
        """Issue an EcoProof collection receipt with SHA-256 integrity digest."""
        pickup = PickupService.get_pickup_by_id(db, pickup_id)

        # Check if already verified
        existing_verification = db.execute(
            select(VerificationRecord).where(VerificationRecord.pickup_id == pickup_id)
        ).scalar_one_or_none()
        if existing_verification:
            raise ValidationException("This pickup has already been verified and issued an EcoProof receipt.")

        verified_at = datetime.now(timezone.utc)

        # Generate cryptographic SHA-256 digest of verified payload
        hash_payload = (
            f"pickup:{pickup.id}|"
            f"weight_kg:{verify_in.actual_weight_kg:.2f}|"
            f"stream:{verify_in.stream_confirmed}|"
            f"collector:{verify_in.collector_signature_id}|"
            f"timestamp:{verified_at.isoformat()}"
        )
        integrity_hash = generate_sha256_hash(hash_payload)

        # EcoCredits: 10 credits per kg verified (minimum 10)
        credits_awarded = max(10, int(verify_in.actual_weight_kg * 10))

        record = VerificationRecord(
            pickup_id=pickup.id,
            verified_at=verified_at,
            actual_weight_kg=verify_in.actual_weight_kg,
            stream_confirmed=verify_in.stream_confirmed,
            collector_signature_id=verify_in.collector_signature_id,
            notes=verify_in.notes,
            integrity_hash=integrity_hash,
            ecocredits_awarded=credits_awarded,
        )
        db.add(record)

        # Update parent pickup and waste report states
        pickup.status = "completed"

        report = db.execute(
            select(WasteReport).where(WasteReport.id == pickup.report_id)
        ).scalar_one_or_none()
        if report:
            report.status = "verified"
            # If household EcoPass is registered, disburse EcoCredits to their ledger
            if report.ecopass_id:
                EcoPassService.award_credits(
                    db=db,
                    ecopass_id=report.ecopass_id,
                    amount=credits_awarded,
                    transaction_type="pickup_reward",
                    reference_id=str(pickup.id),
                    description=f"EcoProof verified: {verify_in.actual_weight_kg}kg of {verify_in.stream_confirmed} collected",
                )

        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def generate_qr_code(
        cls,
        db: Session,
        pickup_id: uuid.UUID,
        base_url: str = "http://127.0.0.1:8000",
    ) -> PickupQRCodeResponse:
        """Generate a verification QR code encoding the public backend verification URL.

        Encodes only the stable verification URL without PII, secrets, or OTPs.
        """
        pickup = cls.get_pickup_by_id(db, pickup_id)

        # Stable public verification URL
        verification_url = f"{base_url.rstrip('/')}/api/v1/pickups/{pickup.id}/verify-receipt"

        # Generate QR code PNG in-memory
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        b64_png = base64.b64encode(buf.getvalue()).decode("ascii")
        data_url = f"data:image/png;base64,{b64_png}"

        is_verified = pickup.verification is not None
        integrity_hash = pickup.verification.integrity_hash if is_verified else None

        return PickupQRCodeResponse(
            pickup_id=pickup.id,
            verification_url=verification_url,
            qr_code_data_url=data_url,
            is_verified=is_verified,
            status=pickup.status,
            integrity_hash=integrity_hash,
        )

    @classmethod
    def verify_receipt_hash(cls, db: Session, pickup_id: uuid.UUID) -> PickupVerificationStatusResponse:
        """Validate cryptographic SHA-256 seal of the EcoProof pickup verification receipt.

        Read-only verification that does not mutate records.
        """
        pickup = cls.get_pickup_by_id(db, pickup_id)

        if not pickup.verification:
            return PickupVerificationStatusResponse(
                pickup_id=pickup.id,
                is_valid=False,
                status="unverified",
                message="Pickup has not been verified with an EcoProof receipt.",
            )

        ver = pickup.verification
        verified_at = ver.verified_at
        if verified_at.tzinfo is None:
            dt_utc = verified_at.replace(tzinfo=timezone.utc)
        else:
            dt_utc = verified_at.astimezone(timezone.utc)

        # Compute candidate SHA-256 hash using UTC ISO timestamp
        payload = (
            f"pickup:{pickup.id}|"
            f"weight_kg:{ver.actual_weight_kg:.2f}|"
            f"stream:{ver.stream_confirmed}|"
            f"collector:{ver.collector_signature_id}|"
            f"timestamp:{dt_utc.isoformat()}"
        )
        computed = generate_sha256_hash(payload)

        # Also check naive ISO timestamp in case SQLite stripped tzinfo on storage
        payload_naive = (
            f"pickup:{pickup.id}|"
            f"weight_kg:{ver.actual_weight_kg:.2f}|"
            f"stream:{ver.stream_confirmed}|"
            f"collector:{ver.collector_signature_id}|"
            f"timestamp:{verified_at.replace(tzinfo=None).isoformat()}"
        )
        computed_naive = generate_sha256_hash(payload_naive)

        stored = ver.integrity_hash
        if stored in [computed, computed_naive]:
            return PickupVerificationStatusResponse(
                pickup_id=pickup.id,
                is_valid=True,
                status="verified",
                verified_at=ver.verified_at,
                actual_weight_kg=ver.actual_weight_kg,
                stream_confirmed=ver.stream_confirmed,
                collector_signature_id=ver.collector_signature_id,
                stored_hash=stored,
                computed_hash=stored,
                ecocredits_awarded=ver.ecocredits_awarded,
                message="EcoProof collection receipt verified successfully against SHA-256 integrity digest.",
            )

        return PickupVerificationStatusResponse(
            pickup_id=pickup.id,
            is_valid=False,
            status="mismatch",
            verified_at=ver.verified_at,
            actual_weight_kg=ver.actual_weight_kg,
            stream_confirmed=ver.stream_confirmed,
            collector_signature_id=ver.collector_signature_id,
            stored_hash=stored,
            computed_hash=computed,
            ecocredits_awarded=ver.ecocredits_awarded,
            message="Cryptographic digest mismatch. Verification record appears altered or tampered with.",
        )
