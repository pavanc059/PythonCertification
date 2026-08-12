"""
Admin-only API.

GET    /admin/users                — list all users + stats
PATCH  /admin/users/{id}/role     — promote / demote
GET    /admin/activity            — activity feed across all users (paginated)
GET    /admin/stats               — platform-wide totals

All endpoints require role == "admin".
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.models import User
from dependencies import get_current_user, get_db
from activity.service import ActivityService

router = APIRouter()


# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency — raises 403 if the caller is not an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return all users with role, last login, and trade count."""
    from sqlalchemy import func
    from trading.models import PaperOrderDB, PaperTradingAccountDB

    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(func.count(User.id)).scalar()

    result = []
    for u in users:
        # Trade count from paper orders
        account = db.query(PaperTradingAccountDB).filter_by(user_id=u.id).first()
        trade_count = 0
        if account:
            trade_count = db.query(func.count(PaperOrderDB.id)).filter_by(
                account_id=account.id, status="filled"
            ).scalar() or 0

        result.append({
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() + "Z",
            "last_login_at": u.last_login_at.isoformat() + "Z" if u.last_login_at else None,
            "trade_count": trade_count,
        })

    return {"total": total, "offset": offset, "limit": limit, "users": result}


class RolePatch(BaseModel):
    role: str  # "user" | "admin"


@router.patch("/users/{user_id}/role")
async def set_user_role(
    user_id: UUID,
    body: RolePatch,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Promote or demote a user. Admins cannot demote themselves."""
    if body.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'admin'.")
    if user_id == current_admin.id and body.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot demote yourself.")

    target = db.query(User).filter_by(id=user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    target.role = body.role
    db.commit()
    return {"id": str(target.id), "email": target.email, "role": target.role}


# ---------------------------------------------------------------------------
# Activity feed (global)
# ---------------------------------------------------------------------------

@router.get("/activity")
async def admin_activity(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Return activity log across all users, paginated and filterable."""
    svc = ActivityService(db)
    uid = UUID(user_id) if user_id else None
    items = svc.get_all_feed(
        limit=limit, offset=offset,
        user_id=uid, category=category, event_type=event_type,
    )
    total = svc.count_all_feed(user_id=uid, category=category, event_type=event_type)

    # Enrich each entry with user email for display
    from sqlalchemy.orm import joinedload
    user_cache: dict[str, str] = {}

    def _email(uid_str: str) -> str:
        if uid_str not in user_cache:
            u = db.query(User).filter_by(id=uid_str).first()
            user_cache[uid_str] = u.email if u else uid_str
        return user_cache[uid_str]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {**svc.to_dict(e), "user_email": _email(str(e.user_id))}
            for e in items
        ],
    }


# ---------------------------------------------------------------------------
# Platform stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def platform_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """High-level platform metrics for the admin dashboard."""
    from sqlalchemy import func
    from trading.models import PaperOrderDB, PaperTradingAccountDB
    from autotrade.models import AutoTradeBotDB
    from autopilot.models import AutoPilotConfigDB
    from activity.models import ActivityLogDB

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter_by(is_active=True).scalar() or 0
    admin_users = db.query(func.count(User.id)).filter_by(role="admin").scalar() or 0
    total_orders = db.query(func.count(PaperOrderDB.id)).scalar() or 0
    filled_orders = db.query(func.count(PaperOrderDB.id)).filter_by(status="filled").scalar() or 0
    active_bots = db.query(func.count(AutoTradeBotDB.id)).filter_by(enabled=True).scalar() or 0
    active_autopilots = db.query(func.count(AutoPilotConfigDB.id)).filter_by(enabled=True).scalar() or 0
    total_events = db.query(func.count(ActivityLogDB.id)).scalar() or 0

    return {
        "users": {"total": total_users, "active": active_users, "admins": admin_users},
        "orders": {"total": total_orders, "filled": filled_orders},
        "automation": {"active_bots": active_bots, "active_autopilots": active_autopilots},
        "activity": {"total_events": total_events},
    }
