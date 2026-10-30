"""Pillar 5: Municipal Governance and Circular Dashboard Endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.municipal import MunicipalDashboardStats
from app.services.municipal_service import MunicipalService

router = APIRouter(prefix="/municipal", tags=["Pillar 5: Municipal Operations & Compliance"])


@router.get(
    "/dashboard",
    response_model=APIResponse[MunicipalDashboardStats],
    status_code=status.HTTP_200_OK,
    summary="Get Municipal Governance Dashboard Statistics",
    description="Returns aggregated operational circular metrics computed directly from active database records across all five pillars.",
)
def get_municipal_dashboard(
    db: Session = Depends(get_db),
) -> APIResponse[MunicipalDashboardStats]:
    """Retrieve operational dashboard statistics."""
    stats = MunicipalService.get_dashboard_statistics(db)
    return APIResponse[MunicipalDashboardStats](
        success=True,
        message="Municipal circular metrics compiled from stored records.",
        data=stats,
    )
