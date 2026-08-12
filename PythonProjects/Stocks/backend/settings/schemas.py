"""
Pydantic schemas for the settings endpoints.

Requirements: 12.6, 12.7
"""

from typing import Optional

from pydantic import BaseModel


class FeatureFlags(BaseModel):
    real_time_streaming: bool
    deep_learning: bool
    alternative_data: bool


class AppSettingsResponse(BaseModel):
    app_env: str
    api_version: str
    log_level: str
    feature_flags: FeatureFlags


class FeatureFlagsPatch(BaseModel):
    real_time_streaming: Optional[bool] = None
    deep_learning: Optional[bool] = None
    alternative_data: Optional[bool] = None
