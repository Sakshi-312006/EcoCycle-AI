"""Pillar 5: Voice Accessibility and Localized Rules Schemas."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LanguageCodeEnum(str, Enum):
    """Supported Indian regional and official languages."""

    EN = "en"   # English
    HI = "hi"   # Hindi
    KN = "kn"   # Kannada
    TA = "ta"   # Tamil
    TE = "te"   # Telugu
    MR = "mr"   # Marathi


class SupportedLanguage(BaseModel):
    """Metadata for a supported regional Indian or official language."""

    code: LanguageCodeEnum
    name: str = Field(..., description="English language name (e.g. Hindi)")
    local_name: str = Field(..., description="Native script name (e.g. हिंदी)")
    bcp47_tag: str = Field(..., description="BCP-47 speech locale tag (e.g. hi-IN)")
    is_fully_supported: bool = Field(True, description="True if complete UI translations exist")


class StreamInstructionItem(BaseModel):
    """Instructions and visual accessibility metadata for a specific waste stream."""

    stream: str
    stream_name_localized: str
    allowed_items: List[str]
    disallowed_items: List[str]
    handling_advice: str
    color_hex: Optional[str] = Field(None, description="Accessible high-contrast HEX color")
    color_name: Optional[str] = Field(None, description="Color name in localized text")
    icon_symbol: Optional[str] = Field(None, description="Visual symbol name (e.g. leaf, bottle, medical, alert)")
    audio_prompt_text: Optional[str] = Field(None, description="Concise text optimized for text-to-speech audio guidance")


class LocalizedInstructionResponse(BaseModel):
    """Localized segregation guidance for citizen app and voice prompts."""

    language_code: str
    language_name: str
    general_guideline: str
    streams: Dict[str, StreamInstructionItem]


class UIBundleResponse(BaseModel):
    """Complete localized bundle containing UI strings, button labels, and stream guidance."""

    language_code: str
    language_name: str
    bcp47_tag: str
    ui_strings: Dict[str, str]
    streams: Dict[str, StreamInstructionItem]


class BhashiniIntegrationStatus(BaseModel):
    """Diagnostic interface reporting status of MeitY Bhashini API pipeline."""

    provider: str = "MeitY Bhashini"
    status: str = Field(..., description="connected | unconfigured | offline")
    configured_credentials: bool = Field(..., description="True if credentials present in .env")
    message: str = Field(..., description="Operational status message")
    supported_services: List[str] = Field(
        default=["ASR (Automated Speech Recognition)", "NMT (Neural Machine Translation)", "TTS (Text to Speech)"],
        description="Planned voice interface pipelines",
    )
    disclaimer: str = Field(
        default="EcoCycle AI maintains an open interface for Bhashini APIs. Active live inference requires valid MeitY credentials in .env.",
        description="Integrity disclaimer",
    )
