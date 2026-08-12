"""
Pydantic v2 request/response schemas for the watchlist endpoints.

Requirements: R3.1, R3.3, R3.4, R3.7
"""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class WatchlistItemResponse(BaseModel):
    """Serialised view of a single watchlist entry returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    ticker: str
    list_name: str
    alert_price: Optional[float] = None
    created_at: str


class WatchlistListResponse(BaseModel):
    """Summary of a named watchlist with its item count."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    item_count: int


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AddWatchlistItemRequest(BaseModel):
    """Payload for POST /watchlist/add."""

    ticker: str
    list_name: str = "Default"
    alert_price: Optional[float] = None

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_non_empty_uppercase(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("ticker must not be empty")
        return stripped

    @field_validator("list_name")
    @classmethod
    def list_name_must_be_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("list_name must not be empty")
        return stripped


class WatchlistListCreate(BaseModel):
    """Payload for POST /watchlist/lists."""

    name: str

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be empty")
        # Allow alphanumerics, spaces, hyphens, and underscores only.
        if not re.match(r"^[\w\s\-]+$", stripped):
            raise ValueError(
                "name may only contain letters, digits, spaces, hyphens, and underscores"
            )
        return stripped
