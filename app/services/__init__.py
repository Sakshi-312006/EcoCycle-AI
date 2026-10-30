"""Services package aggregating business domain services across all Five Pillars."""

from app.services.cd_service import CDService
from app.services.circular_service import CircularService
from app.services.ecopass_service import EcoPassService
from app.services.fleet_service import FleetService
from app.services.health_service import HealthService
from app.services.image_upload_service import ImageUploadService
from app.services.municipal_service import MunicipalService
from app.services.pickup_service import PickupService
from app.services.voice_service import VoiceService
from app.services.waste_classifier_service import WasteClassifierService
from app.services.waste_guidance_service import WasteGuidanceService
from app.services.waste_service import WasteService
from app.services.waste_workflow_service import WasteWorkflowService

__all__ = [
    "HealthService",
    "WasteService",
    "PickupService",
    "EcoPassService",
    "CDService",
    "CircularService",
    "FleetService",
    "MunicipalService",
    "VoiceService",
    "ImageUploadService",
    "WasteClassifierService",
    "WasteGuidanceService",
    "WasteWorkflowService",
]
