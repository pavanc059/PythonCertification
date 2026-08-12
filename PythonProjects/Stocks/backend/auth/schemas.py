"""
Pydantic v2 request / response schemas for the auth module.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    """Body expected by POST /auth/register."""

    email: EmailStr
    name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be empty.")
        return v


class UserLogin(BaseModel):
    """Body expected by POST /auth/login."""

    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    """Public user representation returned inside token responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    is_active: bool
    role: str
    theme_preference: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Returned after successful login or registration."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Internal schemas
# ---------------------------------------------------------------------------


class TokenData(BaseModel):
    """Decoded JWT payload used inside the application."""

    user_id: UUID
    email: str
