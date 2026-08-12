"""
TradingService — bridges FastAPI ↔ in-memory trading engine ↔ PostgreSQL.

Responsibilities
----------------
- Load (hydrate) a user's PaperTradingAccount from the database on construction.
- Persist every order, position change, and cash balance update back to the DB.
- Expose a clean interface to the FastAPI trading router (Task 4).

Requirements: R4.1, R4.3, R7.8
"""

import os
import sys

# Ensure the app root is on sys.path so `stockiq` package is importable
_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from trading.models import PaperOrderDB, PaperPositionDB, PaperTradingAccountDB

# --- existing stockiq trading engine ---
from stockiq.trading.account import AccountConfig, PaperTradingAccount
from stockiq.trading.orders import (
    LimitOrder,
    MarketOrder,
    OrderSide,
    StopLimitOrder,
    StopLossOrder,
)
from stockiq.trading.portfolio import Position


class TradingService:
    """
    Service layer that owns all paper-trading persistence logic.

    Usage
    -----
    Instantiate once per request inside a FastAPI route that depends on
    ``get_db`` and ``get_current_user``.

        service = TradingService(db=db, user_id=current_user.id)
        summary = service.get_account_summary()
    """

    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.account_db: PaperTradingAccountDB = self._get_or_create_account_db()
        self.account: PaperTradingAccount = self._hydrate_account()

    # ------------------------------------------------------------------
    # Internal: DB ↔ in-memory hydration
    # ------------------------------------------------------------------

    def _get_or_create_account_db(self) -> PaperTradingAccountDB:
        """Return the user's DB account row, creating it if it doesn't exist (R4.1)."""
        account = (
            self.db.query(PaperTradingAccountDB)
            .filter_by(user_id=self.user_id)
            .first()
        )
        if not account:
            account = PaperTradingAccountDB(
                user_id=self.user_id,
                cash=Decimal("100000"),
                initial_cash=Decimal("100000"),
            )
            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
        return account

    def _hydrate_account(self) -> PaperTradingAccount:
        """
        Rebuild an in-memory PaperTradingAccount from the current DB state (R4.3).

        Positions and pending orders are restored so the engine can
        continue processing them correctly.
        """
        account = PaperTradingAccount(
            account_id=str(self.account_db.id),
            config=AccountConfig(
                initial_cash=Decimal(str(self.account_db.initial_cash))
            ),
        )
        # Override the cash that AccountConfig resets to initial_cash
        account.cash = Decimal(str(self.account_db.cash))

        # Restore open positions
        for pos_db in self.account_db.positions:
            account.portfolio.positions[pos_db.ticker] = Position(
                ticker=pos_db.ticker,
                quantity=pos_db.quantity,
                avg_entry_price=Decimal(str(pos_db.avg_entry_price)),
                current_price=Decimal(str(pos_db.current_price)),
                entry_time=pos_db.entry_time,
            )

        # Restore pending limit/stop orders (market orders are never pending)
        for ord_db in self.account_db.orders:
            if ord_db.status == "pending":
                order = self._db_to_domain_order(ord_db)
                if order is not None:
                    account.pending_orders.append(order)

        return account

    def _db_to_domain_order(self, ord_db: PaperOrderDB):
        """Convert a DB order row back to a domain Order object, or None for market orders."""
        side = OrderSide(ord_db.side)

        if ord_db.order_type == "market":
            # Market orders are always filled immediately; they never stay pending.
            return None
        elif ord_db.order_type == "limit":
            o = LimitOrder(
                ticker=ord_db.ticker,
                side=side,
                quantity=ord_db.quantity,
                limit_price=Decimal(str(ord_db.limit_price or 0)),
            )
        elif ord_db.order_type == "stop_loss":
            o = StopLossOrder(
                ticker=ord_db.ticker,
                side=side,
                quantity=ord_db.quantity,
                stop_price=Decimal(str(ord_db.stop_price or 0)),
            )
        elif ord_db.order_type == "stop_limit":
            o = StopLimitOrder(
                ticker=ord_db.ticker,
                side=side,
                quantity=ord_db.quantity,
                stop_price=Decimal(str(ord_db.stop_price or 0)),
                limit_price=Decimal(str(ord_db.limit_price or 0)),
            )
        else:
            return None

        # Restore the original domain order_id so cancel/update works correctly
        o.order_id = ord_db.order_id
        return o

    # ------------------------------------------------------------------
    # Internal: DB write helpers
    # ------------------------------------------------------------------

    def _persist_order(self, order) -> None:
        """Insert or update the DB row for a domain order."""
        existing = (
            self.db.query(PaperOrderDB).filter_by(order_id=order.order_id).first()
        )
        if existing:
            existing.status = order.status.value
            existing.filled_price = order.filled_price
            existing.filled_quantity = order.filled_quantity
            existing.filled_at = order.filled_at
            existing.commission = order.commission
            existing.slippage = order.slippage
        else:
            self.db.add(
                PaperOrderDB(
                    account_id=self.account_db.id,
                    order_id=order.order_id,
                    ticker=order.ticker,
                    side=order.side.value,
                    order_type=order.order_type.value,
                    quantity=order.quantity,
                    limit_price=getattr(order, "limit_price", None),
                    stop_price=getattr(order, "stop_price", None),
                    status=order.status.value,
                    filled_price=order.filled_price,
                    filled_quantity=order.filled_quantity,
                    commission=order.commission,
                    slippage=order.slippage,
                    created_at=order.created_at,
                    filled_at=order.filled_at,
                )
            )
        self.db.commit()

    def _sync_positions(self) -> None:
        """
        Replace all DB position rows for this account with the current
        in-memory portfolio state (delete-then-insert is correct and simple).
        """
        self.db.query(PaperPositionDB).filter_by(
            account_id=self.account_db.id
        ).delete()
        for ticker, pos in self.account.portfolio.positions.items():
            self.db.add(
                PaperPositionDB(
                    account_id=self.account_db.id,
                    ticker=ticker,
                    quantity=pos.quantity,
                    avg_entry_price=pos.avg_entry_price,
                    current_price=pos.current_price,
                    entry_time=pos.entry_time,
                )
            )
        self.db.commit()

    def _sync_account_cash(self) -> None:
        """Persist the in-memory cash balance back to the DB row."""
        self.account_db.cash = self.account.cash
        self.db.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_order(
        self,
        ticker: str,
        side: str,
        order_type: str,
        quantity: int,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> dict:
        """
        Place an order through the engine and persist all side-effects.

        Returns a dict matching the domain order result (status, order_id, …).
        """
        order_side = OrderSide(side)

        if order_type == "market":
            order = MarketOrder(ticker=ticker, side=order_side, quantity=quantity)
        elif order_type == "limit":
            order = LimitOrder(
                ticker=ticker,
                side=order_side,
                quantity=quantity,
                limit_price=Decimal(str(limit_price or 0)),
            )
        elif order_type == "stop_loss":
            order = StopLossOrder(
                ticker=ticker,
                side=order_side,
                quantity=quantity,
                stop_price=Decimal(str(stop_price or 0)),
            )
        elif order_type == "stop_limit":
            order = StopLimitOrder(
                ticker=ticker,
                side=order_side,
                quantity=quantity,
                stop_price=Decimal(str(stop_price or 0)),
                limit_price=Decimal(str(limit_price or 0)),
            )
        else:
            return {"status": "rejected", "reason": f"Unknown order type: {order_type}"}

        result = self.account.place_order(order)
        self._persist_order(order)
        self._sync_positions()
        self._sync_account_cash()
        return result

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order in both the engine and the DB.

        Returns True if the order was found and cancelled.
        """
        success = self.account.cancel_order(order_id)
        if success:
            ord_db = (
                self.db.query(PaperOrderDB).filter_by(order_id=order_id).first()
            )
            if ord_db:
                ord_db.status = "cancelled"
                self.db.commit()
        return success

    def reset_account(self) -> None:
        """
        Reset the paper trading account to its initial $100 K balance.

        Wipes all positions and orders from both the engine and the DB (R4.2).
        """
        self.account.reset()
        self.account_db.cash = self.account_db.initial_cash
        self.db.query(PaperPositionDB).filter_by(
            account_id=self.account_db.id
        ).delete()
        self.db.query(PaperOrderDB).filter_by(
            account_id=self.account_db.id
        ).delete()
        self.db.commit()

    def get_account_summary(self) -> dict:
        """Return a JSON-serialisable account summary."""
        summary = self.account.get_account_summary()
        return {
            "account_id": str(self.account_db.id),
            "cash": float(summary["cash"]),
            "portfolio_value": float(summary["portfolio_value"]),
            "total_value": float(summary["total_value"]),
            "buying_power": float(summary["buying_power"]),
            "total_return": float(summary["total_return"]),
            "total_return_pct": summary["total_return_pct"],
            "num_positions": summary["num_positions"],
            "num_pending_orders": summary["num_pending_orders"],
            "created_at": summary["created_at"].isoformat(),
        }

    def get_positions(self) -> List[dict]:
        """Return all open positions as a list of dicts."""
        return [
            {
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "market_value": float(pos.market_value),
                "unrealized_pnl": float(pos.unrealized_pnl),
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "cost_basis": float(pos.cost_basis),
            }
            for pos in self.account.portfolio.positions.values()
        ]

    def get_orders(self) -> List[dict]:
        """Return all orders (newest first) from the DB."""
        orders = (
            self.db.query(PaperOrderDB)
            .filter_by(account_id=self.account_db.id)
            .order_by(PaperOrderDB.created_at.desc())
            .all()
        )
        return [
            {
                "order_id": o.order_id,
                "ticker": o.ticker,
                "side": o.side,
                "order_type": o.order_type,
                "quantity": o.quantity,
                "limit_price": float(o.limit_price) if o.limit_price is not None else None,
                "stop_price": float(o.stop_price) if o.stop_price is not None else None,
                "status": o.status,
                "filled_price": float(o.filled_price) if o.filled_price is not None else None,
                "filled_quantity": o.filled_quantity,
                "commission": float(o.commission),
                "slippage": float(o.slippage),
                "created_at": o.created_at.isoformat(),
                "filled_at": o.filled_at.isoformat() if o.filled_at else None,
            }
            for o in orders
        ]
