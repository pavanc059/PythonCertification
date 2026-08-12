"""
ActivityService — query helpers for the activity feed and admin view.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from activity.models import ActivityLogDB


class ActivityService:
    """Query the activity log for a single user or all users (admin)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # User feed
    # ------------------------------------------------------------------

    def get_user_feed(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[ActivityLogDB]:
        q = (
            self.db.query(ActivityLogDB)
            .filter(ActivityLogDB.user_id == user_id)
        )
        if category:
            q = q.filter(ActivityLogDB.category == category)
        return (
            q.order_by(ActivityLogDB.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_user_feed(self, user_id: UUID, *, category: Optional[str] = None) -> int:
        q = self.db.query(ActivityLogDB).filter(ActivityLogDB.user_id == user_id)
        if category:
            q = q.filter(ActivityLogDB.category == category)
        return q.count()

    # ------------------------------------------------------------------
    # Admin feed (all users)
    # ------------------------------------------------------------------

    def get_all_feed(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[UUID] = None,
        category: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[ActivityLogDB]:
        q = self.db.query(ActivityLogDB)
        if user_id:
            q = q.filter(ActivityLogDB.user_id == user_id)
        if category:
            q = q.filter(ActivityLogDB.category == category)
        if event_type:
            q = q.filter(ActivityLogDB.event_type == event_type)
        return (
            q.order_by(ActivityLogDB.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_all_feed(
        self,
        *,
        user_id: Optional[UUID] = None,
        category: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        q = self.db.query(ActivityLogDB)
        if user_id:
            q = q.filter(ActivityLogDB.user_id == user_id)
        if category:
            q = q.filter(ActivityLogDB.category == category)
        if event_type:
            q = q.filter(ActivityLogDB.event_type == event_type)
        return q.count()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def to_dict(e: ActivityLogDB) -> dict:
        return {
            "id": str(e.id),
            "user_id": str(e.user_id),
            "category": e.category,
            "event_type": e.event_type,
            "description": e.description,
            "metadata": e.event_data or {},
            "created_at": e.created_at.isoformat() + "Z",
        }
