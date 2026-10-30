"""Schemas package containing common request/response envelopes and domain DTOs."""

from app.schemas.cd_waste import (
    ALLOWED_CD_MATERIAL_STATUSES,
    CDEstimateRequest,
    CDEstimateResponse,
    CDMaterialCategoryEnum,
    CDMaterialConditionEnum,
    CDMaterialCreate,
    CDMaterialDensityEnum,
    CDMaterialResponse,
    CDMaterialStatusEnum,
)
from app.schemas.circular import (
    CircularClaimRequest,
    CircularConditionEnum,
    CircularItemCategoryEnum,
    CircularListingCreate,
    CircularListingResponse,
    CircularListingTypeEnum,
)
from app.schemas.common import APIResponse, ErrorResponse, PaginationParams
from app.schemas.ecopass import (
    EcoCreditTransactionResponse,
    EcoPassCreate,
    EcoPassResponse,
)
from app.schemas.fleet import FleetPriorityQueueResponse, PrioritizedPickupItem
from app.schemas.health import (
    DatabaseHealthData,
    HealthSummaryData,
    LivenessData,
    ReadinessData,
)
from app.schemas.municipal import (
    MunicipalDashboardStats,
    PickupStatistics,
    StreamStatistics,
)
from app.schemas.pickup import (
    CollectionVerificationCreate,
    PickupCreate,
    PickupResponse,
    PickupStatusEnum,
    PickupStatusUpdate,
    VerificationResponse,
)
from app.schemas.voice import (
    BhashiniIntegrationStatus,
    LanguageCodeEnum,
    LocalizedInstructionResponse,
    StreamInstructionItem,
    SupportedLanguage,
    UIBundleResponse,
)
from app.schemas.waste import (
    WasteReportCreate,
    WasteReportResponse,
    WasteReportStatusEnum,
    WasteReportUpdate,
    WasteStreamEnum,
)
from app.schemas.waste_workflow import (
    ActionOutcomeEnum,
    HandlingGuidanceRequest,
    HandlingGuidanceResponse,
    ImageUploadResponse,
    PickupSubmissionRequest,
    PickupSubmissionResponse,
    WasteClassificationRequest,
    WasteClassificationResponse,
)

__all__ = [
    "APIResponse",
    "ErrorResponse",
    "PaginationParams",
    "DatabaseHealthData",
    "HealthSummaryData",
    "LivenessData",
    "ReadinessData",
    # Waste
    "WasteStreamEnum",
    "WasteReportStatusEnum",
    "WasteReportCreate",
    "WasteReportUpdate",
    "WasteReportResponse",
    # Waste Workflow
    "ActionOutcomeEnum",
    "ImageUploadResponse",
    "WasteClassificationRequest",
    "WasteClassificationResponse",
    "HandlingGuidanceRequest",
    "HandlingGuidanceResponse",
    "PickupSubmissionRequest",
    "PickupSubmissionResponse",
    # Pickup
    "PickupStatusEnum",
    "PickupCreate",
    "PickupStatusUpdate",
    "CollectionVerificationCreate",
    "VerificationResponse",
    "PickupResponse",
    # EcoPass
    "EcoPassCreate",
    "EcoPassResponse",
    "EcoCreditTransactionResponse",
    # C&D
    "CDMaterialDensityEnum",
    "CDEstimateRequest",
    "CDEstimateResponse",
    "CDMaterialCategoryEnum",
    "CDMaterialConditionEnum",
    "CDMaterialStatusEnum",
    "ALLOWED_CD_MATERIAL_STATUSES",
    "CDMaterialCreate",
    "CDMaterialResponse",
    # Circular
    "CircularListingTypeEnum",
    "CircularItemCategoryEnum",
    "CircularConditionEnum",
    "CircularListingCreate",
    "CircularClaimRequest",
    "CircularListingResponse",
    # Fleet
    "PrioritizedPickupItem",
    "FleetPriorityQueueResponse",
    # Municipal
    "StreamStatistics",
    "PickupStatistics",
    "MunicipalDashboardStats",
    # Voice
    "LanguageCodeEnum",
    "StreamInstructionItem",
    "LocalizedInstructionResponse",
    "SupportedLanguage",
    "UIBundleResponse",
    "BhashiniIntegrationStatus",
]
