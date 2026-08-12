"""
GET /activity          — current user's activity feed (paginated)
GET /activity/count    — total count for badge/pagination
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.models import User
from dependencies import get_current_user, get_db
from activity.service import ActivityService

router = APIRouter()


@router.get("")
async def get_activity(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's personal activity feed, newest first."""
    svc = ActivityService(db)
    items = svc.get_user_feed(current_user.id, limit=limit, offset=offset, category=category)
    total = svc.count_user_feed(current_user.id, category=category)
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [svc.to_dict(e) for e in items],
    }
