"""Pillar 5: Voice Accessibility and Localized Regional Guidance Endpoints."""

from typing import List
from fastapi import APIRouter, Query, status

from app.schemas.common import APIResponse
from app.schemas.voice import (
    BhashiniIntegrationStatus,
    LanguageCodeEnum,
    LocalizedInstructionResponse,
    SupportedLanguage,
    UIBundleResponse,
)
from app.services.voice_service import VoiceService

router = APIRouter(prefix="/voice", tags=["Pillar 5: Voice Accessibility & Localized Guidance"])


@router.get(
    "/languages",
    response_model=APIResponse[List[SupportedLanguage]],
    status_code=status.HTTP_200_OK,
    summary="List Supported Regional Languages",
    description="Returns metadata for all supported regional Indian and official languages (English, Hindi, Kannada, Tamil, Telugu, Marathi).",
)
def get_supported_languages() -> APIResponse[List[SupportedLanguage]]:
    """Retrieve list of supported languages with BCP-47 speech locale tags."""
    languages = VoiceService.get_supported_languages()
    return APIResponse[List[SupportedLanguage]](
        success=True,
        message=f"Retrieved {len(languages)} supported languages.",
        data=languages,
    )


@router.get(
    "/instructions",
    response_model=APIResponse[LocalizedInstructionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Localized Waste Segregation Instructions",
    description="Returns official segregation guidance for the 4 streams translated into regional Indian languages (English, Hindi, Kannada, Tamil, Telugu, Marathi) for mobile citizen onboarding and future audio prompts.",
)
def get_localized_instructions(
    language: LanguageCodeEnum = Query(LanguageCodeEnum.EN, alias="lang", description="Language: en, hi, kn, ta, te, mr"),
) -> APIResponse[LocalizedInstructionResponse]:
    """Retrieve localized waste handling instructions."""
    instructions = VoiceService.get_instructions(language)
    return APIResponse[LocalizedInstructionResponse](
        success=True,
        message=f"Retrieved localized guidance in {instructions.language_name}.",
        data=instructions,
    )


@router.get(
    "/bundle",
    response_model=APIResponse[UIBundleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Full Localized UI and Guidance Bundle",
    description="Returns full localized bundle including UI strings, button labels, speech hints, and 4-stream visual guidance.",
)
def get_ui_bundle(
    language: LanguageCodeEnum = Query(LanguageCodeEnum.EN, alias="lang", description="Language: en, hi, kn, ta, te, mr"),
) -> APIResponse[UIBundleResponse]:
    """Retrieve complete localized UI bundle."""
    bundle = VoiceService.get_ui_bundle(language)
    return APIResponse[UIBundleResponse](
        success=True,
        message=f"Retrieved UI bundle for {bundle.language_name}.",
        data=bundle,
    )


@router.get(
    "/bhashini/status",
    response_model=APIResponse[BhashiniIntegrationStatus],
    status_code=status.HTTP_200_OK,
    summary="Check MeitY Bhashini Voice Pipeline Interface Status",
    description="Inspects whether MeitY Bhashini API credentials and pipeline endpoints are configured in environment settings. Honestly indicates connection readiness without claiming live synthesis if unconfigured.",
)
def check_bhashini_status() -> APIResponse[BhashiniIntegrationStatus]:
    """Report Bhashini integration interface readiness."""
    status_report = VoiceService.check_bhashini_status()
    return APIResponse[BhashiniIntegrationStatus](
        success=status_report.configured_credentials,
        message=status_report.message,
        data=status_report,
    )
