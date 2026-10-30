"""OTP authentication and contact verification endpoints."""

from fastapi import APIRouter, status

from app.schemas.common import APIResponse
from app.schemas.otp import OTPRequestPayload, OTPRequestResponse, OTPVerifyPayload, OTPVerifyResponse
from app.services.otp_service import OTPService

router = APIRouter(prefix="/auth/otp", tags=["Authentication & OTP Verification"])


@router.post(
    "/request",
    response_model=APIResponse[OTPRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Request Verification OTP",
    description="Requests a 6-digit OTP for citizen or driver mobile verification. Operates in demo mode with rate throttling.",
)
def request_otp(
    payload: OTPRequestPayload,
) -> APIResponse[OTPRequestResponse]:
    """Request a prototype verification OTP."""
    result = OTPService.request_otp(payload)
    return APIResponse[OTPRequestResponse](
        success=True,
        message=result.message,
        data=result,
    )


@router.post(
    "/verify",
    response_model=APIResponse[OTPVerifyResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify OTP Code",
    description="Validates a candidate 6-digit OTP code against the hashed session record with TTL and attempt limits.",
)
def verify_otp(
    payload: OTPVerifyPayload,
) -> APIResponse[OTPVerifyResponse]:
    """Verify submitted OTP code."""
    result = OTPService.verify_otp(payload)
    return APIResponse[OTPVerifyResponse](
        success=True,
        message=result.message,
        data=result,
    )

