"""
SQLAlchemy ORM model for the ``watchlist_items`` table.

Requirements: R3.1, R3.3, R3.4, R3.7, R7.4
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class WatchlistItem(Base):
    """
    Persistent watchlist entry for a user.

    A user can add the same ticker to multiple named lists, but the same
    ticker cannot appear twice within the same list (enforced via unique
    constraint on user_id + ticker + list_name).
    """

    __tablename__ = "watchlist_items"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        # FK enforced in migration; avoiding a runtime import of auth.models
        # here so that the model can be imported standalone without triggering
        # a circular-import chain.
        nullable=False,
    )
    ticker = Column(String, nullable=False)
    list_name = Column(String, nullable=False, default="Default")
    # Optional price alert threshold (R3.7)
    alert_price = Column(Numeric(18, 6), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        # Same ticker may appear in different lists but not twice in one list.
        UniqueConstraint(
            "user_id",
            "ticker",
            "list_name",
            name="uq_watchlist_user_ticker_list",
        ),
        # Extra index on user_id for fast per-user queries.
        Index("ix_watchlist_items_user_id", "user_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WatchlistItem user={self.user_id} ticker={self.ticker!r}"
            f" list={self.list_name!r}>"
        )
