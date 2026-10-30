"""API v1 Router aggregator.

Mounts version 1 domain routes across all Five Pillars of EcoCycle AI.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth_otp import router as auth_otp_router
from app.api.v1.endpoints.cd_waste import router as cd_waste_router
from app.api.v1.endpoints.circular import router as circular_router
from app.api.v1.endpoints.ecopass import router as ecopass_router
from app.api.v1.endpoints.fleet import router as fleet_router
from app.api.v1.endpoints.garbage_piles import router as garbage_piles_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.municipal import router as municipal_router
from app.api.v1.endpoints.pickups import router as pickups_router
from app.api.v1.endpoints.user_settings import router as user_settings_router
from app.api.v1.endpoints.voice import router as voice_router
from app.api.v1.endpoints.waste import router as waste_router

api_v1_router = APIRouter()

# Core diagnostic and health checks
api_v1_router.include_router(health_router)

# Authentication & OTP verification (demo prototype mode)
api_v1_router.include_router(auth_otp_router)

# User preferences & accessibility settings
api_v1_router.include_router(user_settings_router)

# Pillar 1: Four-stream waste segregation & doorstep collection
api_v1_router.include_router(waste_router)
api_v1_router.include_router(ecopass_router)

# Pillar 2: Pickup operations & EcoProof verification
api_v1_router.include_router(pickups_router)

# Pillar 3: Construction and demolition waste estimation & management
api_v1_router.include_router(cd_waste_router)

# Pillar 4: Circular recovery, material reuse, resale, donations & recycling
api_v1_router.include_router(circular_router)

# Pillar 4: Garbage-pile detection, smart collection routing & verified cleanliness
api_v1_router.include_router(garbage_piles_router)

# Pillar 5: Fleet logistics, voice accessibility & municipal governance
api_v1_router.include_router(fleet_router)
api_v1_router.include_router(municipal_router)
api_v1_router.include_router(voice_router)
