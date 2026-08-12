"""
Settings service — reads application configuration from environment variables
and manages in-memory feature flags.

Requirements: 12.6, 12.7
"""

import os

from settings.schemas import AppSettingsResponse, FeatureFlags, FeatureFlagsPatch

# ---------------------------------------------------------------------------
# In-memory feature flags store (defaults all to False)
# ---------------------------------------------------------------------------

_feature_flags: dict = {
    "real_time_streaming": False,
    "deep_learning": False,
    "alternative_data": False,
}


def get_settings() -> AppSettingsResponse:
    """
    Build an AppSettingsResponse from environment variables and the in-memory
    feature flags dict.

    Environment variables read:
        APP_ENV      — defaults to "development"
        API_VERSION  — defaults to "1.0.0"
        LOG_LEVEL    — defaults to "INFO"
    """
    return AppSettingsResponse(
        app_env=os.getenv("APP_ENV", "development"),
        api_version=os.getenv("API_VERSION", "1.0.0"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        feature_flags=FeatureFlags(**_feature_flags),
    )


def get_flag(key: str) -> bool:
    """Read a single feature flag by key. Never raises — returns False on unknown keys."""
    return bool(_feature_flags.get(key, False))
    """
    Merge non-None fields from *patch* into the in-memory feature flags dict
    and return the updated AppSettingsResponse.
    """
    global _feature_flags

    patch_data = patch.model_dump(exclude_none=True)
    _feature_flags.update(patch_data)

    return get_settings()
