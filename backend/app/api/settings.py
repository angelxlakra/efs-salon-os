"""Settings API endpoints for salon configuration.

This module provides REST API endpoints for:
- Viewing salon settings
- Updating salon settings (Owner only)
- Resetting to defaults (Owner only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.settings import (
    SalonSettingsResponse,
    SalonSettingsUpdate
)
from app.services.settings_service import SettingsService
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "",
    response_model=SalonSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get salon settings"
)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current salon settings.

    Returns salon configuration including business information,
    contact details, and receipt customization settings.

    **Permissions**: Any authenticated user

    Args:
        db: Database session
        current_user: Authenticated user

    Returns:
        SalonSettingsResponse: Current salon settings

    Raises:
        500: If settings retrieval fails
    """
    settings = SettingsService.get_or_create_settings(db)
    return SalonSettingsResponse.model_validate(settings)


@router.patch(
    "",
    response_model=SalonSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update salon settings"
)
def update_settings(
    updates: SalonSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update salon settings.

    Updates one or more salon configuration fields.
    Only provided fields will be updated.

    **Permissions**: Owner only

    Args:
        updates: Fields to update (all optional)
        db: Database session
        current_user: Authenticated user

    Returns:
        SalonSettingsResponse: Updated salon settings

    Raises:
        403: If user is not owner
        400: If validation fails
    """
    # Check permissions - OWNER ONLY
    if not current_user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can update salon settings"
        )

    try:
        # Convert to dict and filter out None values
        updates_dict = updates.model_dump(exclude_unset=True)

        settings = SettingsService.update_settings(db, updates_dict)
        return SalonSettingsResponse.model_validate(settings)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/reset",
    response_model=SalonSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset settings to defaults"
)
def reset_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset salon settings to default values.

    **Warning**: This will erase all custom salon configuration
    and restore factory defaults.

    **Permissions**: Owner only

    Args:
        db: Database session
        current_user: Authenticated user

    Returns:
        SalonSettingsResponse: Reset settings

    Raises:
        403: If user is not owner
    """
    # Check permissions - OWNER ONLY
    if not current_user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can reset salon settings"
        )

    settings = SettingsService.reset_to_defaults(db)
    return SalonSettingsResponse.model_validate(settings)
