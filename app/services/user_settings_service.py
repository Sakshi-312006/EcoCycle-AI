"""User settings preference management service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_settings import UserSettings
from app.schemas.user_settings import UserSettingsUpdate


class UserSettingsService:
    """Service managing prototype user and household preferences."""

    @classmethod
    def get_or_create_settings(cls, db: Session, user_id: str) -> UserSettings:
        """Fetch existing user settings or initialize default preferences for the user."""
        clean_user_id = user_id.strip()
        settings_record = db.execute(
            select(UserSettings).where(UserSettings.user_id == clean_user_id)
        ).scalar_one_or_none()

        if not settings_record:
            settings_record = UserSettings(
                user_id=clean_user_id,
                language="en",
                notifications_enabled=True,
                notification_preference="push",
                theme="system",
                accessibility_high_contrast=False,
                accessibility_large_text=False,
            )
            db.add(settings_record)
            db.commit()
            db.refresh(settings_record)

        return settings_record

    @classmethod
    def update_settings(cls, db: Session, user_id: str, update_in: UserSettingsUpdate) -> UserSettings:
        """Update existing user preferences or initialize with overrides."""
        settings_record = cls.get_or_create_settings(db, user_id)

        if update_in.language is not None:
            settings_record.language = update_in.language.value
        if update_in.notifications_enabled is not None:
            settings_record.notifications_enabled = update_in.notifications_enabled
        if update_in.notification_preference is not None:
            settings_record.notification_preference = update_in.notification_preference.value
        if update_in.theme is not None:
            settings_record.theme = update_in.theme.value
        if update_in.accessibility_high_contrast is not None:
            settings_record.accessibility_high_contrast = update_in.accessibility_high_contrast
        if update_in.accessibility_large_text is not None:
            settings_record.accessibility_large_text = update_in.accessibility_large_text

        db.commit()
        db.refresh(settings_record)
        return settings_record

