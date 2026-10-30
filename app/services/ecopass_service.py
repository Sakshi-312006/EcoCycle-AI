"""EcoPass Identity and EcoCredits Ledger Service."""

from typing import List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.ecopass import EcoCreditTransaction, EcoPassAccount
from app.schemas.ecopass import EcoPassCreate


class EcoPassService:
    """Service managing household circular identity and credit ledgers."""

    @staticmethod
    def register_account(db: Session, data_in: EcoPassCreate) -> EcoPassAccount:
        """Register a new household EcoPass."""
        ecopass_id = f"ECOPASS-W{data_in.ward_number}-{uuid.uuid4().hex[:6].upper()}"

        account = EcoPassAccount(
            ecopass_id=ecopass_id,
            household_name=data_in.household_name,
            ward_number=data_in.ward_number,
            address=data_in.address,
            balance_ecocredits=0,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    @staticmethod
    def get_account(db: Session, ecopass_id: str) -> EcoPassAccount:
        """Retrieve EcoPass account by ID."""
        account = db.execute(
            select(EcoPassAccount).where(EcoPassAccount.ecopass_id == ecopass_id)
        ).scalar_one_or_none()
        if not account:
            raise EntityNotFoundException("EcoPassAccount", ecopass_id)
        return account

    @staticmethod
    def award_credits(
        db: Session,
        ecopass_id: str,
        amount: int,
        transaction_type: str,
        reference_id: Optional[str],
        description: str,
    ) -> EcoCreditTransaction:
        """Credit or debit EcoCredits and record an immutable ledger entry."""
        account = db.execute(
            select(EcoPassAccount).where(EcoPassAccount.ecopass_id == ecopass_id)
        ).scalar_one_or_none()

        if account:
            account.balance_ecocredits += amount

        tx = EcoCreditTransaction(
            ecopass_id=ecopass_id,
            amount=amount,
            transaction_type=transaction_type,
            reference_id=reference_id,
            description=description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def get_transactions(db: Session, ecopass_id: str) -> List[EcoCreditTransaction]:
        """Fetch audit trail of credit transactions for an account."""
        # Ensure account exists
        EcoPassService.get_account(db, ecopass_id)
        return list(
            db.execute(
                select(EcoCreditTransaction)
                .where(EcoCreditTransaction.ecopass_id == ecopass_id)
                .order_by(desc(EcoCreditTransaction.created_at))
            )
            .scalars()
            .all()
        )
