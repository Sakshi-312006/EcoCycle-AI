"""OTP authentication and contact verification service.

Implements demo prototype OTP handling:
- In-memory hashed storage (SHA-256 + salt; never stored plaintext).
- 5-minute TTL expiration.
- 3-attempt maximum before invalidation.
- 60-second resend throttling.
- Gated demo-mode response (never exposed in production).
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from threading import Lock
from typing import Dict, Optional
import uuid

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.schemas.otp import OTPRequestPayload, OTPRequestResponse, OTPVerifyPayload, OTPVerifyResponse


class _StoredOTPEntry:
    """Internal memory entry storing hashed OTP and lifecycle state."""

    def __init__(self, phone_number: str, hashed_otp: str, salt: str, expires_at: datetime):
        self.phone_number = phone_number
        self.hashed_otp = hashed_otp
        self.salt = salt
        self.expires_at = expires_at
        self.attempts_remaining = 3
        self.last_requested_at = datetime.now(timezone.utc)
        self.is_consumed = False


class OTPService:
    """Service managing prototype OTP generation, rate limits, and verification."""

    _store: Dict[str, _StoredOTPEntry] = {}
    _lock = Lock()

    OTP_EXPIRATION_SECONDS = 300       # 5 minutes
    RESEND_COOLDOWN_SECONDS = 60       # 1 minute
    MAX_ATTEMPTS = 3

    @classmethod
    def _hash_otp(cls, otp: str, salt: str) -> str:
        """Hash OTP with salt using SHA-256."""
        return hashlib.sha256(f"{otp}:{salt}".encode("utf-8")).hexdigest()

    @classmethod
    def request_otp(cls, payload: OTPRequestPayload) -> OTPRequestResponse:
        """Generate and store a new hashed OTP enforcing resend throttling."""
        phone = payload.phone_number
        now = datetime.now(timezone.utc)

        with cls._lock:
            # 1. Enforce resend cooldown across active sessions for this phone
            existing = [entry for entry in cls._store.values() if entry.phone_number == phone and not entry.is_consumed]
            if existing:
                latest = max(existing, key=lambda e: e.last_requested_at)
                elapsed = (now - latest.last_requested_at).total_seconds()
                if elapsed < cls.RESEND_COOLDOWN_SECONDS:
                    wait_sec = int(cls.RESEND_COOLDOWN_SECONDS - elapsed)
                    raise ValidationException(
                        f"Resend throttled. Please wait {wait_sec} seconds before requesting a new OTP.",
                        details=[{"phone_number": phone, "retry_after_seconds": wait_sec}],
                    )

            # 2. Generate cryptographically strong 6-digit numeric code
            otp_digits = f"{secrets.randbelow(900000) + 100000}"
            salt = secrets.token_hex(16)
            hashed = cls._hash_otp(otp_digits, salt)

            session_id = f"otp_sess_{uuid.uuid4().hex}"
            expires_at = now + timedelta(seconds=cls.OTP_EXPIRATION_SECONDS)

            cls._store[session_id] = _StoredOTPEntry(
                phone_number=phone,
                hashed_otp=hashed,
                salt=salt,
                expires_at=expires_at,
            )

        # 3. Expose demo OTP only in development / debug mode
        demo_otp = None
        if settings.DEBUG or settings.ENVIRONMENT == "development":
            demo_otp = otp_digits

        return OTPRequestResponse(
            phone_number=phone,
            session_id=session_id,
            delivery_mode="demo",
            expires_in_seconds=cls.OTP_EXPIRATION_SECONDS,
            resend_available_in_seconds=cls.RESEND_COOLDOWN_SECONDS,
            message="Demo mode active: No SMS gateway configured. Demo OTP generated for prototype testing.",
            demo_otp=demo_otp,
        )

    @classmethod
    def verify_otp(cls, payload: OTPVerifyPayload) -> OTPVerifyResponse:
        """Verify candidate OTP against stored hash, enforcing TTL and max attempt limits."""
        session_id = payload.session_id
        phone = payload.phone_number
        candidate_code = payload.otp_code
        now = datetime.now(timezone.utc)

        with cls._lock:
            entry = cls._store.get(session_id)
            if not entry or entry.phone_number != phone:
                raise ValidationException(
                    "Invalid OTP session. Please request a new verification code.",
                    details=[{"field": "session_id", "message": "Session not found or phone mismatch"}],
                )

            if entry.is_consumed:
                raise ValidationException(
                    "This OTP has already been used and cannot be reused.",
                    details=[{"field": "otp_code", "message": "OTP consumed"}],
                )

            # Check expiration
            if now > entry.expires_at:
                raise ValidationException(
                    "OTP has expired. Please request a new verification code.",
                    details=[{"field": "otp_code", "message": "Expired code"}],
                )

            # Check attempts remaining
            if entry.attempts_remaining <= 0:
                raise ValidationException(
                    "Maximum verification attempts exceeded. This OTP has been invalidated.",
                    details=[{"field": "otp_code", "message": "Attempt limit reached"}],
                )

            # Validate hash
            candidate_hash = cls._hash_otp(candidate_code, entry.salt)
            if not secrets.compare_digest(candidate_hash, entry.hashed_otp):
                entry.attempts_remaining -= 1
                remaining = entry.attempts_remaining
                if remaining <= 0:
                    raise ValidationException(
                        "Incorrect OTP. Maximum verification attempts exceeded. Code invalidated.",
                        details=[{"attempts_remaining": 0}],
                    )
                raise ValidationException(
                    f"Incorrect OTP. You have {remaining} attempt(s) remaining.",
                    details=[{"attempts_remaining": remaining}],
                )

            # Success: consume OTP so it cannot be replayed
            entry.is_consumed = True

            # Generate lightweight verification receipt proof
            proof = hashlib.sha256(f"{phone}:{session_id}:{entry.salt}".encode()).hexdigest()[:32]
            verification_token = f"proof_verified_{proof}"

        return OTPVerifyResponse(
            phone_number=phone,
            is_verified=True,
            verification_token=verification_token,
            message="Mobile number successfully verified.",
        )

    @classmethod
    def reset_store_for_testing(cls) -> None:
        """Utility for test suites to clear in-memory OTP cache."""
        with cls._lock:
            cls._store.clear()

