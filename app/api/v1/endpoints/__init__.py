"""V1 Endpoints package."""

from app.api.v1.endpoints.cd_waste import router as cd_waste_router
from app.api.v1.endpoints.circular import router as circular_router
from app.api.v1.endpoints.ecopass import router as ecopass_router
from app.api.v1.endpoints.fleet import router as fleet_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.municipal import router as municipal_router
from app.api.v1.endpoints.pickups import router as pickups_router
from app.api.v1.endpoints.voice import router as voice_router
from app.api.v1.endpoints.waste import router as waste_router

__all__ = [
    "health_router",
    "waste_router",
    "pickups_router",
    "ecopass_router",
    "cd_waste_router",
    "circular_router",
    "fleet_router",
    "municipal_router",
    "voice_router",
]
