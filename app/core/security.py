"""Security utilities and cryptographic verification helpers.

Provides integrity verification (SHA-256 for EcoProof & telemetry),
basic token/hash helpers, and scaffolding for the upcoming authentication module.
"""

import hashlib
import hmac
from typing import Optional
from app.core.config import settings


def generate_sha256_hash(payload: str, salt: Optional[str] = None) -> str:
    """Generate SHA-256 hex digest for a payload, optionally HMAC-salted.

    Used across EcoCycle AI for:
    - Pillar 1: EcoProof digital verification receipt hashing
    - Pillar 4: Telemetry payload tamper-evidence
    - Pillar 5: Municipal audit log integrity chains
    """
    effective_salt = salt or settings.ECOPROOF_SALT
    if effective_salt:
        return hmac.new(
            key=effective_salt.encode("utf-8"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_sha256_hash(payload: str, expected_hash: str, salt: Optional[str] = None) -> bool:
    """Verify integrity of a payload against an expected SHA-256 digest."""
    computed = generate_sha256_hash(payload, salt)
    return hmac.compare_digest(computed.lower(), expected_hash.lower())
