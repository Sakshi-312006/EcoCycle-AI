"""OTP authentication and contact verification schemas."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OTPRequestPayload(BaseModel):
    """Payload to request a verification OTP."""

    phone_number: str = Field(..., min_length=10, max_length=20, description="Citizen or driver mobile phone number")
    purpose: str = Field("login", max_length=50, description="Verification purpose: login | doorstep_verification | ecopass_link")

    @field_validator("phone_number")
    @classmethod
    def clean_phone_number(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if len(cleaned) < 10:
            raise ValueError("Phone number must have at least 10 digits.")
        return cleaned


class OTPRequestResponse(BaseModel):
    """Response returned upon requesting an OTP."""

    phone_number: str
    session_id: str = Field(..., description="Unique session tracking ID for this OTP request")
    delivery_mode: str = Field("demo", description="demo | sms_gateway")
    expires_in_seconds: int = Field(300, description="OTP lifetime in seconds")
    resend_available_in_seconds: int = Field(60, description="Cooldown seconds before next request is permitted")
    message: str = Field(..., description="Operational status notice")
    demo_otp: Optional[str] = Field(
        None,
        description="Demo-mode OTP returned exclusively during local development / testing. Stripped in production.",
    )
    disclaimer: str = Field(
        default="Demo OTP mode active. No external SMS gateway is configured. Demo OTP is only exposed in development mode.",
        description="Delivery and testing notice",
    )


class OTPVerifyPayload(BaseModel):
    """Payload to verify an issued OTP."""

    phone_number: str = Field(..., min_length=10, max_length=20)
    session_id: str = Field(..., min_length=10, max_length=100)
    otp_code: str = Field(..., min_length=4, max_length=10, description="Numeric OTP code")

    @field_validator("phone_number")
    @classmethod
    def clean_phone_number(cls, v: str) -> str:
        return v.strip().replace(" ", "").replace("-", "")

    @field_validator("otp_code")
    @classmethod
    def clean_otp_code(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.isdigit():
            raise ValueError("OTP code must be strictly numeric digits.")
        return cleaned


class OTPVerifyResponse(BaseModel):
    """Result of OTP verification."""

    phone_number: str
    is_verified: bool = Field(..., description="True if OTP matches, has not expired, and attempt limit not exceeded")
    verification_token: Optional[str] = Field(None, description="Cryptographic verification proof receipt")
    message: str = Field(..., description="Verification result message")

