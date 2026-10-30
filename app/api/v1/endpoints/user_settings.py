"""User settings and preference endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import APIResponse
from app.schemas.user_settings import UserSettingsResponse, UserSettingsUpdate
from app.services.user_settings_service import UserSettingsService

router = APIRouter(prefix="/user-settings", tags=["User Preferences & Settings"])


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Settings",
    description="Retrieve preferences for a user or EcoPass account. Returns defaults if not previously configured.",
)
def get_user_settings(
    user_id: str,
    db: Session = Depends(get_db),
) -> APIResponse[UserSettingsResponse]:
    """Retrieve user preferences."""
    settings = UserSettingsService.get_or_create_settings(db, user_id)
    return APIResponse[UserSettingsResponse](
        success=True,
        message="User settings retrieved successfully.",
        data=UserSettingsResponse.model_validate(settings),
    )


@router.put(
    "/{user_id}",
    response_model=APIResponse[UserSettingsResponse],
    status_code=status.HTTP_200_OK,
    summary="Update User Settings",
    description="Update user preferences such as language, notifications, theme, and accessibility.",
)
def update_user_settings(
    user_id: str,
    update_in: UserSettingsUpdate,
    db: Session = Depends(get_db),
) -> APIResponse[UserSettingsResponse]:
    """Update user preferences."""
    settings = UserSettingsService.update_settings(db, user_id, update_in)
    return APIResponse[UserSettingsResponse](
        success=True,
        message="User settings updated successfully.",
        data=UserSettingsResponse.model_validate(settings),
    )

