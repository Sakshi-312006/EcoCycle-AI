"""Pillar 5: Municipal Governance and Circular Dashboard Schemas."""

from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field


class StreamStatistics(BaseModel):
    """Breakdown of reports and diversion per waste stream."""

    wet_organic: int = 0
    dry_recyclable: int = 0
    sanitary: int = 0
    hazardous: int = 0


class PickupStatistics(BaseModel):
    """Breakdown of pickup lifecycle counts."""

    scheduled: int = 0
    in_progress: int = 0
    completed: int = 0
    cancelled: int = 0


class MunicipalDashboardStats(BaseModel):
    """Aggregated operational metrics computed directly from stored records."""

    total_waste_reports: int = Field(..., description="Cumulative count of logged reports")
    reports_by_stream: StreamStatistics = Field(..., description="Report distribution across four streams")
    total_pickups: int = Field(..., description="Total pickup requests")
    pickups_by_status: PickupStatistics = Field(..., description="Status breakdown of pickups")
    total_verified_collections: int = Field(..., description="Number of collections with EcoProof receipts")
    total_waste_verified_kg: float = Field(..., description="Cumulative verified waste collected in kg")
    total_cd_estimates_logged: int = Field(..., description="Number of C&D volume estimates calculated")
    total_cd_materials_listed: int = Field(..., description="Available reusable construction material listings")
    total_circular_items_listed: int = Field(..., description="Total circular reuse and donation listings")
    total_circular_items_diverted: int = Field(..., description="Items marked claimed or completed")
    total_ecocredits_circulating: int = Field(..., description="Total EcoCredits awarded in ledger")
    total_ecopass_households: int = Field(..., description="Registered household EcoPass accounts")
    ward_coverage: Dict[str, int] = Field(default_factory=dict, description="Active reports distributed by municipal ward")
    timestamp: datetime = Field(..., description="Dashboard computation timestamp")
