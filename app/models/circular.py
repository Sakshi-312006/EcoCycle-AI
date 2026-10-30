"""Pillar 4: Circular Recovery & NGO Donation ORM Models."""

from typing import Optional
import uuid
import sqlalchemy as sa
from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class CircularListing(Base, UUIDMixin, TimestampMixin):
    """Circular reuse/resale or verified NGO donation item record."""

    __tablename__ = "circular_listings"

    listing_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # 'resale' or 'donation'
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False) # furniture, electronics, clothing, books, etc.
    condition: Mapped[str] = mapped_column(String(50), nullable=False) # like_new, good, fair, needs_repair
    price_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    donor_or_seller_name: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ecopass_id: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    beneficiary_ngo_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="available", index=True, nullable=False)
