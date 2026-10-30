"""EcoPass Household Identity and EcoCredits Ledger ORM Models."""

from typing import Optional
import uuid
import sqlalchemy as sa
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class EcoPassAccount(Base, UUIDMixin, TimestampMixin):
    """Household or establishment EcoPass circular identity."""

    __tablename__ = "ecopass_accounts"

    ecopass_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    household_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ward_number: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    balance_ecocredits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class EcoCreditTransaction(Base, UUIDMixin, TimestampMixin):
    """Immutable audit ledger record for EcoCredit disbursements and redemptions."""

    __tablename__ = "ecocredit_transactions"

    ecopass_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("ecopass_accounts.ecopass_id"),
        index=True,
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
