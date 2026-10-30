"""User settings and preference schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
from pydantic import BaseModel, Field


class SupportedLanguageEnum(str, Enum):
    """Supported UI and voice guidance languages."""

    EN = "en"
    KN = "kn"
    HI = "hi"
    TA = "ta"
    TE = "te"


class NotificationPreferenceEnum(str, Enum):
    """Notification delivery channels."""

    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"
    NONE = "none"


class ThemeEnum(str, Enum):
    """Visual UI themes."""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class UserSettingsUpdate(BaseModel):
    """Update payload for user preferences."""

    language: Optional[SupportedLanguageEnum] = Field(None, description="Preferred language (en, kn, hi, ta, te)")
    notifications_enabled: Optional[bool] = Field(None, description="Enable or disable operational alerts")
    notification_preference: Optional[NotificationPreferenceEnum] = Field(None, description="Preferred channel: push | sms | email | none")
    theme: Optional[ThemeEnum] = Field(None, description="Visual theme: light | dark | system")
    accessibility_high_contrast: Optional[bool] = Field(None, description="High-contrast accessibility mode")
    accessibility_large_text: Optional[bool] = Field(None, description="Enlarged font accessibility mode")


class UserSettingsResponse(BaseModel):
    """Complete user settings response."""

    id: uuid.UUID
    user_id: str
    language: str
    notifications_enabled: bool
    notification_preference: str
    theme: str
    accessibility_high_contrast: bool
    accessibility_large_text: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

