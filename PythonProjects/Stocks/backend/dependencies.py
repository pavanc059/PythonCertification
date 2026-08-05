"""
Shared FastAPI dependency functions.

- get_db: database session (re-exported from database.py)
- oauth2_scheme: OAuth2 bearer token extractor
- get_current_user: JWT-protected user resolver
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

# Re-export get_db so routes only need to import from this module.
from database import get_db as get_db  # noqa: F401 (re-export)

# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Current-user resolver
# ---------------------------------------------------------------------------


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Resolve the authenticated user from the JWT bearer token.

    Decodes the token, looks up the user in the database, and ensures the
    account is active.  Raises HTTP 401 on any validation failure.

    Args:
        token: Bearer token extracted from the Authorization header.
        db: Active SQLAlchemy session.

    Returns:
        The authenticated :class:`auth.models.User` instance.

    Raises:
        HTTPException 401: Token is invalid, expired, or the user is inactive.
    """
    from auth.models import User
    from auth.service import decode_token
    from config import settings

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = decode_token(token, settings.secret_key)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user
