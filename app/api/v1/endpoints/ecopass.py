"""EcoPass Household Identity and EcoCredits Ledger REST Endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.ecopass import (
    EcoCreditTransactionResponse,
    EcoPassCreate,
    EcoPassResponse,
)
from app.services.ecopass_service import EcoPassService

router = APIRouter(prefix="/ecopass", tags=["Pillar 1 & 2: Household EcoPass & EcoCredits"])


@router.post(
    "",
    response_model=APIResponse[EcoPassResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Household EcoPass",
    description="Provision a circular citizen identity card for tracking waste diversion and receiving EcoCredits.",
)
def register_ecopass(
    account_in: EcoPassCreate,
    db: Session = Depends(get_db),
) -> APIResponse[EcoPassResponse]:
    """Register household EcoPass account."""
    account = EcoPassService.register_account(db, account_in)
    return APIResponse[EcoPassResponse](
        success=True,
        message=f"EcoPass identity '{account.ecopass_id}' provisioned successfully.",
        data=EcoPassResponse.model_validate(account),
    )


@router.get(
    "/{ecopass_id}",
    response_model=APIResponse[EcoPassResponse],
    status_code=status.HTTP_200_OK,
    summary="Get EcoPass Account & Balance",
    description="Retrieve household EcoPass profile, current EcoCredit balance, and ward data.",
)
def get_ecopass_account(
    ecopass_id: str,
    db: Session = Depends(get_db),
) -> APIResponse[EcoPassResponse]:
    """Get EcoPass account details."""
    account = EcoPassService.get_account(db, ecopass_id)
    return APIResponse[EcoPassResponse](
        success=True,
        message="EcoPass account retrieved.",
        data=EcoPassResponse.model_validate(account),
    )


@router.get(
    "/{ecopass_id}/transactions",
    response_model=APIResponse[List[EcoCreditTransactionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get EcoCredit Ledger History",
    description="Fetch immutable transaction audit history for EcoCredits earned from verified pickups and circular donations.",
)
def get_ecopass_transactions(
    ecopass_id: str,
    db: Session = Depends(get_db),
) -> APIResponse[List[EcoCreditTransactionResponse]]:
    """Retrieve audit ledger transactions."""
    txs = EcoPassService.get_transactions(db, ecopass_id)
    return APIResponse[List[EcoCreditTransactionResponse]](
        success=True,
        message=f"Retrieved {len(txs)} ledger transactions.",
        data=[EcoCreditTransactionResponse.model_validate(t) for t in txs],
    )
