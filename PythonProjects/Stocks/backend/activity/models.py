"""
Activity log — immutable audit trail for every meaningful user action.

Every row records one event: a trade placed, a bot decision, an AutoPilot
entry/exit, a login, a watchlist change, etc.  Rows are insert-only.
The admin view queries across all users; the personal activity feed filters
by user_id.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from database import Base


class ActivityLogDB(Base):
    """Immutable audit trail entry."""

    __tablename__ = "activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Category groups events in the UI filter bar
    # "trading" | "autotrade" | "autopilot" | "auth" | "watchlist" | "system"
    category = Column(String(20), nullable=False)

    # Slug used for icons, e.g. "order_filled", "bot_signal", "login"
    event_type = Column(String(50), nullable=False)

    # Human-readable one-liner shown in the feed
    description = Column(Text, nullable=False)

    # Structured payload — ticker, amount, P&L, confidence, etc.
    event_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_activity_log_user_id", "user_id"),
        Index("ix_activity_log_created_at", "created_at"),
        Index("ix_activity_log_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<ActivityLogDB user={self.user_id} type={self.event_type}>"
