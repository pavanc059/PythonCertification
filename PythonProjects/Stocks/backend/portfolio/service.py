"""
PortfolioService — enriched portfolio view with live P&L analytics.

Wraps TradingService and adds:
- Live price refresh from yfinance for all open positions
- Accurate unrealized P&L and market value recalculation
- Day P&L (today's change based on previous close)
- Equity snapshots seeded from order history when no daily snapshots exist
- Win-rate and trade statistics via PerformanceMetrics.calculate()
- Benchmark comparison against SPY

Requirements: R2.1–R2.8, R7.3
"""

import os
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

import logging
from sqlalchemy.orm import Session
from trading.service import TradingService
from stockiq.trading.portfolio import PerformanceMetrics

logger = logging.getLogger(__name__)


def _fetch_live_prices(tickers: list[str]) -> Dict[str, dict]:
    """
    Fetch live price + previous-close for a list of tickers in one yfinance call.
    Returns {ticker: {price, prev_close, day_change_pct}} or {} on failure.
    """
    if not tickers:
        return {}
    try:
        import yfinance as yf
        data = {}
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                fi = t.fast_info
                price = fi.last_price
                prev = fi.previous_close or price
                if price and prev and prev != 0:
                    day_pct = round((price - prev) / prev * 100, 4)
                else:
                    day_pct = 0.0
                data[ticker] = {
                    "price": float(price) if price else None,
                    "prev_close": float(prev) if prev else None,
                    "day_change_pct": day_pct,
                }
            except Exception as exc:
                logger.debug("price fetch failed for %s: %s", ticker, exc)
        return data
    except Exception as exc:
        logger.warning("yfinance bulk price fetch failed: %s", exc)
        return {}


class PortfolioService:
    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.trading_service = TradingService(db=db, user_id=user_id)

    # ------------------------------------------------------------------
    # GET /portfolio/summary
    # ------------------------------------------------------------------

    def get_summary(self) -> dict:
        account = self.trading_service.account
        account_db = self.trading_service.account_db
        summary = self.trading_service.get_account_summary()

        # Refresh live prices and recalculate portfolio value
        tickers = list(account.portfolio.positions.keys())
        live = _fetch_live_prices(tickers)

        portfolio_value = Decimal("0")
        unrealized_pnl = Decimal("0")
        day_pnl = Decimal("0")

        for ticker, pos in account.portfolio.positions.items():
            info = live.get(ticker, {})
            live_price = info.get("price")
            prev_close = info.get("prev_close")

            if live_price:
                current = Decimal(str(live_price))
            else:
                current = pos.current_price

            market_val = current * pos.quantity
            cost = pos.avg_entry_price * pos.quantity
            portfolio_value += market_val
            unrealized_pnl += market_val - cost

            if prev_close:
                prev = Decimal(str(prev_close))
                day_pnl += (current - prev) * pos.quantity

        total_value = account.cash + portfolio_value
        initial_cash = Decimal(str(account_db.initial_cash))
        total_return = total_value - initial_cash
        total_return_pct = float(total_return / initial_cash * 100) if initial_cash else 0.0

        closed_trades = account.portfolio.closed_positions
        realized_pnl = account.portfolio.get_realized_pnl()

        metrics = PerformanceMetrics.calculate(
            initial_capital=initial_cash,
            current_value=total_value,
            previous_value=total_value - day_pnl,  # yesterday's value
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            closed_trades=closed_trades,
            benchmark_ticker="SPY",
        )

        benchmark = None
        if metrics.benchmark_return_pct is not None:
            alpha = metrics.alpha or 0.0
            perf = "outperforming" if alpha > 0.02 else "underperforming" if alpha < -0.02 else "matching"
            benchmark = {
                "benchmark_ticker": "SPY",
                "benchmark_return_pct": metrics.benchmark_return_pct,
                "portfolio_return_pct": total_return_pct,
                "alpha": alpha,
                "performance": perf,
            }

        return {
            "account_id": summary["account_id"],
            "cash": float(account.cash),
            "portfolio_value": float(portfolio_value),
            "total_value": float(total_value),
            "buying_power": float(account.cash),
            "initial_cash": float(initial_cash),
            "total_return": float(total_return),
            "total_return_pct": total_return_pct,
            "realized_pnl": float(realized_pnl),
            "unrealized_pnl": float(unrealized_pnl),
            "day_pnl": float(day_pnl),
            "win_rate": metrics.win_rate,
            "num_trades": metrics.num_trades,
            "num_winning_trades": metrics.num_winning_trades,
            "num_losing_trades": metrics.num_losing_trades,
            "avg_win": float(metrics.avg_win),
            "avg_loss": float(metrics.avg_loss),
            "benchmark": benchmark,
        }

    # ------------------------------------------------------------------
    # GET /portfolio/positions
    # ------------------------------------------------------------------

    def get_positions(self) -> list:
        account = self.trading_service.account
        tickers = list(account.portfolio.positions.keys())
        live = _fetch_live_prices(tickers)

        result = []
        for ticker, pos in account.portfolio.positions.items():
            info = live.get(ticker, {})
            live_price = info.get("price")

            current = Decimal(str(live_price)) if live_price else pos.current_price
            market_val = current * pos.quantity
            cost = pos.avg_entry_price * pos.quantity
            upnl = market_val - cost
            upnl_pct = float(upnl / cost * 100) if cost else 0.0

            result.append({
                "ticker": ticker,
                "quantity": pos.quantity,
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(current),
                "market_value": float(market_val),
                "unrealized_pnl": float(upnl),
                "unrealized_pnl_pct": upnl_pct,
                "cost_basis": float(cost),
                "day_change_pct": info.get("day_change_pct"),
            })

        return result

    # ------------------------------------------------------------------
    # GET /portfolio/history
    # ------------------------------------------------------------------

    def get_history(self) -> dict:
        account = self.trading_service.account
        account_db = self.trading_service.account_db

        closed_trades = []
        for trade in account.portfolio.closed_positions:
            entry_time = trade["entry_time"]
            exit_time = trade["exit_time"]
            closed_trades.append({
                "ticker": trade["ticker"],
                "quantity": trade["quantity"],
                "avg_entry_price": float(str(trade["avg_entry_price"])),
                "exit_price": float(str(trade["exit_price"])),
                "entry_time": entry_time.isoformat() if hasattr(entry_time, "isoformat") else str(entry_time),
                "exit_time": exit_time.isoformat() if hasattr(exit_time, "isoformat") else str(exit_time),
                "realized_pnl": float(str(trade["realized_pnl"])),
                "realized_pnl_pct": float(trade["realized_pnl_pct"]),
            })

        # Build equity snapshots from daily_snapshots if available,
        # otherwise seed from order fill dates + always include today.
        snapshots = []
        if account.portfolio.daily_snapshots:
            for snap in account.portfolio.daily_snapshots:
                snap_date = snap["date"]
                date_str = snap_date.isoformat() if hasattr(snap_date, "isoformat") else str(snap_date)
                snap_total = float(str(snap["total_value"])) + float(str(account_db.cash))
                snapshots.append({"date": date_str, "total_value": snap_total})
        else:
            # Seed equity curve from order fill history
            from trading.models import PaperOrderDB
            orders = (
                self.db.query(PaperOrderDB)
                .filter_by(account_id=account_db.id)
                .filter(PaperOrderDB.status == "filled")
                .order_by(PaperOrderDB.filled_at)
                .all()
            )

            running_cash = float(account_db.initial_cash)
            seen_dates: set = set()
            for o in orders:
                if not o.filled_at:
                    continue
                d = o.filled_at.date().isoformat()
                if d in seen_dates:
                    continue
                seen_dates.add(d)
                qty = o.filled_quantity or o.quantity
                price = float(o.filled_price or o.limit_price or 0)
                if o.side == "buy":
                    running_cash -= qty * price
                else:
                    running_cash += qty * price
                snapshots.append({"date": d, "total_value": running_cash})

        # Always append today's live value
        tickers = list(account.portfolio.positions.keys())
        live = _fetch_live_prices(tickers)
        today_portfolio = sum(
            float((Decimal(str(live[t]["price"])) if live.get(t, {}).get("price") else pos.current_price) * pos.quantity)
            for t, pos in account.portfolio.positions.items()
        )
        today_total = float(account_db.cash) + today_portfolio
        today_str = date.today().isoformat()
        if not snapshots or snapshots[-1]["date"] != today_str:
            snapshots.append({"date": today_str, "total_value": today_total})
        else:
            snapshots[-1]["total_value"] = today_total

        return {
            "closed_trades": closed_trades,
            "equity_snapshots": snapshots,
            "total_realized_pnl": float(str(account.portfolio.get_realized_pnl())),
        }
