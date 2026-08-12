"""
Auth router — /auth/* endpoints.

Endpoints
---------
POST /auth/register    — create a new account, return tokens
POST /auth/login       — authenticate, return tokens
POST /auth/logout      — clear refresh-token cookie
POST /auth/refresh     — exchange refresh cookie for new access token
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy.orm import Session

from auth.models import User
from auth.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
from auth.service import (

    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from config import settings
from dependencies import get_current_user, get_db

router = APIRouter()

# ---------------------------------------------------------------------------
# Cookie name constant
# ---------------------------------------------------------------------------
REFRESH_COOKIE = "refresh_token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tokens(user: User) -> tuple[str, str]:
    """Return ``(access_token, refresh_token)`` for *user*."""
    claims = {"sub": str(user.id), "email": user.email}
    access = create_access_token(
        claims,
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh = create_refresh_token(
        claims,
        timedelta(days=settings.refresh_token_expire_days),
    )
    return access, refresh


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Write the refresh token as an HTTP-only, SameSite=lax cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set to True behind HTTPS in production
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _token_response(user: User, access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserRegister,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create a new user account and return JWT tokens."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered.",
        )

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-create paper trading account with $100K starting balance (R4.1)
    from trading.models import PaperTradingAccountDB
    from decimal import Decimal as _Decimal

    existing_account = (
        db.query(PaperTradingAccountDB).filter_by(user_id=user.id).first()
    )
    if not existing_account:
        trading_account = PaperTradingAccountDB(
            user_id=user.id,
            cash=_Decimal("100000"),
            initial_cash=_Decimal("100000"),
        )
        db.add(trading_account)
        db.commit()

    access, refresh = _make_tokens(user)
    _set_refresh_cookie(response, refresh)
    # Log registration activity
    try:
        from activity.logger import log_event
        from datetime import datetime as _dt
        log_event(db, user_id=user.id, category="auth", event_type="register",
                  description=f"New account created for {user.email}",
                  metadata={"email": user.email, "ts": _dt.utcnow().isoformat()})
    except Exception:
        pass
    return _token_response(user, access)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email + password and return JWT tokens."""
    user = db.query(User).filter(User.email == body.email).first()
    # Use the same error message whether email or password is wrong
    # to avoid leaking which part is incorrect (R1.1, R1.7).
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials.",
    )
    if not user:
        raise invalid
    if not verify_password(body.password, user.hashed_password):
        raise invalid
    if not user.is_active:
        raise invalid

    access, refresh = _make_tokens(user)
    _set_refresh_cookie(response, refresh)
    # Update last_login_at and log activity
    try:
        from datetime import datetime as _dt
        user.last_login_at = _dt.utcnow()
        db.commit()
        from activity.logger import log_event
        log_event(db, user_id=user.id, category="auth", event_type="login",
                  description=f"Logged in",
                  metadata={"email": user.email, "ts": _dt.utcnow().isoformat()})
    except Exception:
        pass
    return _token_response(user, access)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Clear the refresh-token cookie, ending the session."""
    response.delete_cookie(key=REFRESH_COOKIE, path="/")
    return {"message": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh-token cookie for a new access token."""
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing.",
        )

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token.",
    )
    try:
        token_data = decode_token(
            refresh_token,
            settings.secret_key + "_refresh",
        )
    except JWTError:
        raise credentials_exc

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        raise credentials_exc

    # Issue a new access token; refresh token stays the same (no rotation).
    claims = {"sub": str(user.id), "email": user.email}
    from datetime import timedelta as _td
    new_access = create_access_token(
        claims,
        _td(minutes=settings.access_token_expire_minutes),
    )
    return _token_response(user, new_access)
