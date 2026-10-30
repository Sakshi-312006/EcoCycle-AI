"""Pillar 1: Waste Management business service."""

from typing import List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFoundException, ValidationException
from app.models.ecopass import EcoPassAccount
from app.models.waste import WasteReport
from app.schemas.waste import WasteReportCreate, WasteReportUpdate


class WasteService:
    """Service handling doorstep waste report lifecycle."""

    @staticmethod
    def create_report(db: Session, report_in: WasteReportCreate) -> WasteReport:
        """Create a new waste collection report."""
        verified_ecopass_id: Optional[str] = None
        if report_in.ecopass_id:
            account = db.execute(
                select(EcoPassAccount).where(EcoPassAccount.ecopass_id == report_in.ecopass_id)
            ).scalar_one_or_none()
            if not account:
                raise EntityNotFoundException("EcoPassAccount", report_in.ecopass_id)
            verified_ecopass_id = account.ecopass_id

        report = WasteReport(
            category=report_in.category.value,
            description=report_in.description,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            address=report_in.address,
            ward_number=report_in.ward_number,
            ecopass_id=verified_ecopass_id,
            image_url=report_in.image_url,
            estimated_weight_kg=report_in.estimated_weight_kg,
            status="reported",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def get_report_by_id(db: Session, report_id: uuid.UUID) -> WasteReport:
        """Fetch report by UUID; raises 404 if not found."""
        report = db.execute(select(WasteReport).where(WasteReport.id == report_id)).scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("WasteReport", str(report_id))
        return report

    @staticmethod
    def list_reports(
        db: Session,
        category: Optional[str] = None,
        status: Optional[str] = None,
        ward_number: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WasteReport]:
        """List reports with optional stream, status, and ward filters."""
        query = select(WasteReport).order_by(desc(WasteReport.created_at))
        if category:
            query = query.where(WasteReport.category == category)
        if status:
            query = query.where(WasteReport.status == status)
        if ward_number:
            query = query.where(WasteReport.ward_number == ward_number)

        query = query.limit(limit).offset(offset)
        return list(db.execute(query).scalars().all())

    @staticmethod
    def update_report(db: Session, report_id: uuid.UUID, update_in: WasteReportUpdate) -> WasteReport:
        """Update report status or metadata."""
        report = WasteService.get_report_by_id(db, report_id)
        if update_in.status:
            report.status = update_in.status.value
        if update_in.estimated_weight_kg is not None:
            report.estimated_weight_kg = update_in.estimated_weight_kg
        if update_in.address is not None:
            report.address = update_in.address

        db.commit()
        db.refresh(report)
        return report
