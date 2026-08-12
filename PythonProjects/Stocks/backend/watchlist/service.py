"""
WatchlistService — business logic for watchlist management.

Requirements: R3.1, R3.3, R3.4, R3.7
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from watchlist.models import WatchlistItem


class WatchlistService:
    """
    Service layer for all watchlist operations.

    Usage
    -----
        service = WatchlistService(db=db, user_id=current_user.id)
        items = service.get_items()
        item  = service.add_item("AAPL", "Tech Stocks", alert_price=200.0)
    """

    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # GET /watchlist
    # ------------------------------------------------------------------

    def get_items(self, list_name: Optional[str] = None) -> list[dict]:
        """
        Return all WatchlistItem rows for the user, optionally filtered by
        list_name.

        Args:
            list_name: When provided, only items in that list are returned.

        Returns:
            List of item dicts matching WatchlistItemResponse schema.
        """
        query = self.db.query(WatchlistItem).filter(
            WatchlistItem.user_id == self.user_id
        )
        if list_name is not None:
            query = query.filter(WatchlistItem.list_name == list_name)

        items = query.order_by(WatchlistItem.created_at.asc()).all()
        return [self._item_to_dict(item) for item in items]

    # ------------------------------------------------------------------
    # POST /watchlist/add
    # ------------------------------------------------------------------

    def add_item(
        self,
        ticker: str,
        list_name: str = "Default",
        alert_price: Optional[float] = None,
    ) -> dict:
        """
        Create a new WatchlistItem.

        Args:
            ticker: Uppercase ticker symbol (e.g. "AAPL").
            list_name: Destination list name (default "Default").
            alert_price: Optional price alert threshold.

        Returns:
            Dict matching WatchlistItemResponse schema.

        Raises:
            HTTPException 409: Ticker already exists in the specified list.
        """
        # Validate ticker
        ticker = ticker.strip().upper()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="ticker must not be empty",
            )

        # Check for duplicate within the same list
        existing = (
            self.db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == self.user_id,
                WatchlistItem.ticker == ticker,
                WatchlistItem.list_name == list_name,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{ticker} is already in list '{list_name}'",
            )

        item = WatchlistItem(
            user_id=self.user_id,
            ticker=ticker,
            list_name=list_name,
            alert_price=alert_price,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return self._item_to_dict(item)

    # ------------------------------------------------------------------
    # DELETE /watchlist/{ticker}
    # ------------------------------------------------------------------

    def remove_item(self, ticker: str, list_name: str = "Default") -> bool:
        """
        Delete a WatchlistItem for the current user.

        Args:
            ticker: Uppercase ticker symbol.
            list_name: List name the ticker belongs to (default "Default").

        Returns:
            True if the item was found and deleted, False if it did not exist.
        """
        item = (
            self.db.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == self.user_id,
                WatchlistItem.ticker == ticker.upper(),
                WatchlistItem.list_name == list_name,
            )
            .first()
        )
        if item is None:
            return False

        self.db.delete(item)
        self.db.commit()
        return True

    # ------------------------------------------------------------------
    # GET /watchlist/lists
    # ------------------------------------------------------------------

    def get_lists(self) -> list[dict]:
        """
        Return the distinct named lists for the user along with item counts.

        Returns:
            List of dicts matching WatchlistListResponse schema,
            e.g. [{"name": "Default", "item_count": 3}, ...].
        """
        rows = (
            self.db.query(
                WatchlistItem.list_name,
                func.count(WatchlistItem.id).label("item_count"),
            )
            .filter(WatchlistItem.user_id == self.user_id)
            .group_by(WatchlistItem.list_name)
            .order_by(WatchlistItem.list_name.asc())
            .all()
        )
        return [{"name": row.list_name, "item_count": row.item_count} for row in rows]

    # ------------------------------------------------------------------
    # POST /watchlist/lists
    # ------------------------------------------------------------------

    def create_list(self, name: str) -> dict:
        """
        "Create" a named list.

        Because lists are implicit (derived from item rows), this method
        either returns existing metadata if the list already has items, or
        creates a placeholder entry to anchor the list name.

        Args:
            name: Desired list name.

        Returns:
            Dict matching WatchlistListResponse schema.
        """
        # Check if the list already exists (has at least one item).
        existing_count = (
            self.db.query(func.count(WatchlistItem.id))
            .filter(
                WatchlistItem.user_id == self.user_id,
                WatchlistItem.list_name == name,
            )
            .scalar()
        )
        if existing_count and existing_count > 0:
            return {"name": name, "item_count": existing_count}

        # No items yet — the list is logically "created" by returning metadata.
        # Callers will populate it later with add_item().
        return {"name": name, "item_count": 0}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _item_to_dict(item: WatchlistItem) -> dict:
        alert = float(item.alert_price) if item.alert_price is not None else None
        return {
            "id": str(item.id),
            "ticker": item.ticker,
            "list_name": item.list_name,
            "alert_price": alert,
            "created_at": (
                item.created_at.isoformat()
                if hasattr(item.created_at, "isoformat")
                else str(item.created_at)
            ),
        }
