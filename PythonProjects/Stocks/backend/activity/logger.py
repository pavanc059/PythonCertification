"""
log_event() — fire-and-forget activity logger.

Call this from anywhere that performs a meaningful user action.
Never raises — a logging failure must never break the caller.

Usage:
    from activity.logger import log_event
    log_event(db, user_id=user.id, category="trading", event_type="order_filled",
              description=f"Bought 10 AAPL @ $193.42",
              metadata={"ticker": "AAPL", "side": "buy", "qty": 10, "price": 193.42})
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from activity.models import ActivityLogDB

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known categories and event types (for documentation / UI filtering)
# ---------------------------------------------------------------------------
#
# category="auth"        event_type: login | logout | register | password_change
# category="trading"     event_type: order_placed | order_filled | order_cancelled
#                                    order_rejected | position_opened | position_closed
# category="autotrade"   event_type: bot_signal | bot_order_placed | bot_order_blocked
#                                    bot_enabled | bot_disabled | bot_error
# category="autopilot"   event_type: ap_entry | ap_exit | ap_target_hit | ap_halted
#                                    ap_force_flat | ap_enabled | ap_disabled | ap_report
# category="watchlist"   event_type: ticker_added | ticker_removed
# category="portfolio"   event_type: portfolio_snapshot
# category="system"      event_type: api_error | task_error
# ---------------------------------------------------------------------------


def log_event(
    db: Session,
    *,
    user_id: UUID,
    category: str,
    event_type: str,
    description: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Persist one activity log entry.

    This is synchronous and commits immediately.  Failures are caught and
    logged to stderr so the caller is never affected.
    """
    try:
        entry = ActivityLogDB(
            user_id=user_id,
            category=category,
            event_type=event_type,
            description=description,
            event_data=metadata or {},
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        logger.warning("activity log write failed (user=%s type=%s): %s", user_id, event_type, exc)
        try:
            db.rollback()
        except Exception:
            pass
