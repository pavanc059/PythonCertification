"""
Auth service: password hashing and JWT creation / validation.

All JWT operations live here so that both the router and ``dependencies.py``
can call them without circular imports.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt as _bcrypt
from jose import JWTError, jwt

from auth.schemas import TokenData

# ---------------------------------------------------------------------------
# Password hashing (using bcrypt directly — avoids passlib/bcrypt 4.x compat)
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    hashed = _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches the stored *hashed* password."""
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

ALGORITHM = "HS256"


def _build_payload(data: dict, expires_delta: timedelta) -> dict:
    """Return a copy of *data* with an ``exp`` claim appended."""
    payload = data.copy()
    expire = datetime.now(tz=timezone.utc) + expires_delta
    payload["exp"] = expire
    return payload


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """
    Encode a short-lived JWT access token.

    Args:
        data: Claims to embed (should include ``sub`` and ``email``).
        expires_delta: Token lifetime.

    Returns:
        Encoded JWT string.
    """
    payload = _build_payload(data, expires_delta)
    return jwt.encode(payload, _get_secret(), algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta) -> str:
    """
    Encode a long-lived JWT refresh token.

    Args:
        data: Claims to embed (should include ``sub`` and ``email``).
        expires_delta: Token lifetime.

    Returns:
        Encoded JWT string.
    """
    payload = _build_payload(data, expires_delta)
    return jwt.encode(payload, _get_refresh_secret(), algorithm=ALGORITHM)


def decode_token(token: str, secret_key: str, algorithm: str = ALGORITHM) -> TokenData:
    """
    Decode and validate a JWT, returning a :class:`TokenData` instance.

    Args:
        token: Raw JWT string.
        secret_key: Secret used to verify the signature.
        algorithm: Signing algorithm (default ``HS256``).

    Returns:
        Parsed :class:`TokenData`.

    Raises:
        :class:`jose.JWTError`: If the token is invalid or expired.
    """
    payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    sub: str | None = payload.get("sub")
    email: str | None = payload.get("email")
    if sub is None or email is None:
        raise JWTError("Token payload missing required fields.")
    return TokenData(user_id=UUID(sub), email=email)


# ---------------------------------------------------------------------------
# Internal helpers — lazy imports avoid circular deps at module load time
# ---------------------------------------------------------------------------


def _get_secret() -> str:
    from config import settings  # local import to avoid top-level circular dep
    return settings.secret_key


def _get_refresh_secret() -> str:
    """
    Use a separate derived secret for refresh tokens so that a leaked
    access secret does not automatically compromise refresh tokens.
    """
    from config import settings
    return settings.secret_key + "_refresh"
