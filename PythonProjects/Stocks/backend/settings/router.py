"""
Settings API router.

Endpoints
---------
GET  /settings  — returns current app settings and feature flags
PATCH /settings  — partially updates feature flags

All endpoints require a valid JWT Bearer token.

Requirements: 12.6, 12.7
"""

from fastapi import APIRouter, Depends

from auth.models import User
from dependencies import get_current_user
from settings.schemas import AppSettingsResponse, FeatureFlagsPatch
from settings.service import get_settings, patch_settings

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /settings
# ---------------------------------------------------------------------------


@router.get("", response_model=AppSettingsResponse)
async def read_settings(
    current_user: User = Depends(get_current_user),
) -> AppSettingsResponse:
    """
    Return current application settings (env vars) and feature flags.

    Requires JWT Bearer authentication.
    """
    return get_settings()


# ---------------------------------------------------------------------------
# PATCH /settings
# ---------------------------------------------------------------------------


@router.patch("", response_model=AppSettingsResponse)
async def update_settings(
    patch: FeatureFlagsPatch,
    current_user: User = Depends(get_current_user),
) -> AppSettingsResponse:
    """
    Partially update feature flags.  Only non-null fields in the request
    body are applied; omitted fields retain their current values.

    Requires JWT Bearer authentication.
    """
    return patch_settings(patch)
