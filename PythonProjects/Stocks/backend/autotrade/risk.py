"""
Risk manager for the auto-trade engine.

This is the most important component — it is what separates a trading system
from gambling. Every entry is position-sized, every open trade carries a
stop-loss and take-profit, and the whole system halts when the daily loss
limit is breached.

The RiskManager is pure and stateless with respect to market data; it holds
only configuration and the running daily-loss counter. The backtester and the
live paper-trader both drive it the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class RiskConfig:
    """Risk parameters. All percentages are expressed as decimals (0.02 = 2%)."""

    # Fraction of total equity to allocate to a single new position
    position_size_pct: float = 0.10          # 10% of equity per trade
    # Hard stop-loss below entry
    stop_loss_pct: float = 0.02              # -2%
    # Take-profit above entry
    take_profit_pct: float = 0.04            # +4%
    # Halt all new entries once cumulative daily loss reaches this fraction of equity
    daily_loss_limit_pct: float = 0.03       # -3% of equity in a day
    # Maximum simultaneous open positions
    max_positions: int = 5
    # Maximum new trades opened per day
    max_trades_per_day: int = 10
    # Minimum confidence a signal must carry to act on it
    min_confidence: float = 55.0

    def validate(self) -> None:
        if not (0 < self.position_size_pct <= 1):
            raise ValueError("position_size_pct must be in (0, 1]")
        if not (0 < self.stop_loss_pct < 1):
            raise ValueError("stop_loss_pct must be in (0, 1)")
        if not (0 < self.take_profit_pct < 5):
            raise ValueError("take_profit_pct must be in (0, 5)")
        if self.max_positions < 1:
            raise ValueError("max_positions must be >= 1")


@dataclass
class RiskState:
    """Mutable per-day risk tracking."""
    current_day: Optional[date] = None
    day_start_equity: float = 0.0
    realized_pnl_today: float = 0.0
    trades_today: int = 0

    def roll_day(self, today: date, equity: float) -> None:
        """Reset daily counters when the calendar day advances."""
        if self.current_day != today:
            self.current_day = today
            self.day_start_equity = equity
            self.realized_pnl_today = 0.0
            self.trades_today = 0


@dataclass
class EntryDecision:
    approved: bool
    quantity: int = 0
    stop_price: float = 0.0
    take_profit_price: float = 0.0
    reason: str = ""


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        config.validate()
        self.config = config
        self.state = RiskState()

    # ------------------------------------------------------------------
    # Entry gate
    # ------------------------------------------------------------------

    def evaluate_entry(
        self,
        *,
        today: date,
        equity: float,
        cash: float,
        price: float,
        confidence: float,
        open_positions: int,
    ) -> EntryDecision:
        """
        Decide whether a new BUY may proceed and, if so, at what size.
        Applies every risk gate in order and returns the first blocking reason.
        """
        self.state.roll_day(today, equity)
        c = self.config

        if confidence < c.min_confidence:
            return EntryDecision(False, reason=f"Confidence {confidence:.0f} < min {c.min_confidence:.0f}")

        if open_positions >= c.max_positions:
            return EntryDecision(False, reason=f"Max positions ({c.max_positions}) reached")

        if self.state.trades_today >= c.max_trades_per_day:
            return EntryDecision(False, reason=f"Max trades/day ({c.max_trades_per_day}) reached")

        # Daily loss circuit-breaker
        loss_limit = -abs(c.daily_loss_limit_pct) * self.state.day_start_equity
        if self.state.realized_pnl_today <= loss_limit:
            return EntryDecision(False, reason=(
                f"Daily loss limit hit "
                f"({self.state.realized_pnl_today:.2f} ≤ {loss_limit:.2f})"
            ))

        # Position sizing
        allocation = equity * c.position_size_pct
        allocation = min(allocation, cash)  # never exceed available cash
        if allocation < price:
            return EntryDecision(False, reason="Insufficient cash for one share")

        quantity = int(allocation // price)
        if quantity < 1:
            return EntryDecision(False, reason="Position size rounds to 0 shares")

        stop_price = round(price * (1 - c.stop_loss_pct), 2)
        take_profit_price = round(price * (1 + c.take_profit_pct), 2)

        return EntryDecision(
            approved=True,
            quantity=quantity,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
            reason="Approved",
        )

    # ------------------------------------------------------------------
    # Exit checks for open positions
    # ------------------------------------------------------------------

    def check_stops(self, *, entry_price: float, current_low: float, current_high: float,
                    stop_price: float, take_profit_price: float) -> Optional[str]:
        """
        Check whether an open position should be force-closed this bar.
        Returns "stop_loss", "take_profit", or None. Stop-loss takes priority
        (worst case fills first within a bar).
        """
        if current_low <= stop_price:
            return "stop_loss"
        if current_high >= take_profit_price:
            return "take_profit"
        return None

    # ------------------------------------------------------------------
    # Book-keeping — called whenever a trade closes
    # ------------------------------------------------------------------

    def record_trade_open(self) -> None:
        self.state.trades_today += 1

    def record_trade_close(self, realized_pnl: float) -> None:
        self.state.realized_pnl_today += realized_pnl

    def is_halted(self, equity: float) -> bool:
        """True when the daily loss limit has been breached (no new entries)."""
        loss_limit = -abs(self.config.daily_loss_limit_pct) * self.state.day_start_equity
        return self.state.realized_pnl_today <= loss_limit
