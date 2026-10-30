"""EcoPass Household Identity and EcoCredits Ledger Schemas."""

from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field, field_validator


class EcoPassCreate(BaseModel):
    """Schema for registering a new household or building EcoPass."""

    household_name: str = Field(..., min_length=2, max_length=100, description="Family or establishment name")
    ward_number: str = Field(..., min_length=1, max_length=50, description="Municipal ward number")
    address: str = Field(..., min_length=5, max_length=255, description="Full residential address")

    @field_validator("household_name", "ward_number", "address", mode="before")
    @classmethod
    def trim_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v


class EcoCreditTransactionResponse(BaseModel):
    """Schema for an individual ledger transaction."""

    id: uuid.UUID
    ecopass_id: str
    amount: int
    transaction_type: str
    reference_id: Optional[str]
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class EcoPassResponse(BaseModel):
    """Schema for household EcoPass profile and balance."""

    id: uuid.UUID
    ecopass_id: str
    household_name: str
    ward_number: str
    address: str
    balance_ecocredits: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
