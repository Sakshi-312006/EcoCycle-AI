"""User settings and preferences ORM model."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class UserSettings(Base, UUIDMixin, TimestampMixin):
    """User and household application preferences."""

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_preference: Mapped[str] = mapped_column(String(20), default="push", nullable=False)
    theme: Mapped[str] = mapped_column(String(20), default="system", nullable=False)
    accessibility_high_contrast: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accessibility_large_text: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

