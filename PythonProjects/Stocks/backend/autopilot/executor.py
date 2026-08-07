"""
AutoPilotExecutor — the core execution loop for one AutoPilot config.

Called every ~5 minutes during market hours by the Celery task. For a single
config (penny or regular) it:

  1. Rolls the trading day (resets daily counters at a new session).
  2. Recomputes today's realized P&L from closed trades.
  3. MONITORS open positions → take-profit / stop-loss exits.
  4. Enforces the two circuit breakers:
       - target hit  → lock gains, stop opening new positions
       - loss limit  → halt for the day
  5. If still trading: scans for candidates, runs the LLM gate, and opens new
     positions sized so their combined take-profit covers the *remaining*
     daily target — respecting max concurrent positions and capital budget.

Position sizing intuition
-------------------------
To net ``remaining_target`` dollars at a per-trade take-profit of ``tp_pct``,
a position needs allocation ≈ remaining_target / tp_pct. That allocation is
capped by ``max_position_size_pct * capital`` and by available cash.

force_flat(config_id) closes every open position — used at the end of the day
(no overnight risk) and whenever the user disables the config.

All monetary movement goes through the paper TradingService. Nothing here
touches real money.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from trading.service import TradingService
from autopilot.models import AutoPilotConfigDB, AutoPilotTradeDB
from autopilot.providers import get_provider
from autopilot.scanner import CandidateScanner, ScanFilters, Candidate
from autopilot.llm import LLMPredictionGate

logger = logging.getLogger(__name__)


class AutoPilotExecutor:
    """Executes one AutoPilot config's trading logic."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def run(self, config_id: UUID) -> dict:
        """
        Run one execution cycle for a config. Never raises — errors are logged
        to the config row so a single bad config can't break the beat task.
        """
        config = self.db.query(AutoPilotConfigDB).filter_by(id=config_id).first()
        if not config:
            return {"error": "config not found"}
        if not config.enabled:
            return {"skipped": "disabled"}

        try:
            return self._run(config)
        except Exception as exc:
            logger.exception("AutoPilot run failed for %s: %s", config_id, exc)
            config.last_error = str(exc)
            config.last_run_at = datetime.utcnow()
            self.db.commit()
            return {"error": str(exc)}

    def force_flat(self, config_id: UUID, reason: str = "force_flat") -> dict:
        """Close every open position for a config (end-of-day / disable)."""
        config = self.db.query(AutoPilotConfigDB).filter_by(id=config_id).first()
        if not config:
            return {"error": "config not found"}

        trading = TradingService(self.db, config.user_id)
        provider = get_provider(config.data_provider)
        open_trades = self._open_trades(config)

        closed = 0
        for trade in open_trades:
            price = self._current_price(provider, trading, trade.ticker)
            if self._close_trade(config, trading, trade, price, reason):
                closed += 1

        config.status = "closed"
        config.last_run_at = datetime.utcnow()
        self.db.commit()
        logger.info("AutoPilot force_flat %s: closed %d positions (%s)",
                    config_id, closed, reason)
        return {"closed": closed, "reason": reason}

    # ------------------------------------------------------------------
    # Core cycle
    # ------------------------------------------------------------------

    def _run(self, config: AutoPilotConfigDB) -> dict:
        today = datetime.utcnow().date()
        self._roll_day(config, today)

        trading = TradingService(self.db, config.user_id)
        provider = get_provider(config.data_provider)

        # 1. Monitor open positions first (may realize P&L / free capital)
        exits = self._monitor_open_positions(config, trading, provider)

        # 2. Recompute realized P&L today from closed trades
        config.realized_pnl_today = self._realized_pnl_today(config, today)

        # 3. Circuit breakers
        if config.realized_pnl_today >= config.daily_profit_target:
            config.target_hit = True
            config.status = "target_hit"
            config.last_run_at = datetime.utcnow()
            self.db.commit()
            logger.info("AutoPilot %s TARGET HIT: $%.2f >= $%.2f",
                        config.id, config.realized_pnl_today, config.daily_profit_target)
            return {"status": "target_hit", "pnl": config.realized_pnl_today, "exits": exits}

        if config.realized_pnl_today <= -abs(config.daily_loss_limit):
            config.halted = True
            config.status = "halted"
            # Also flatten everything so a bad day can't get worse
            self.force_flat(config.id, reason="loss_limit")
            logger.warning("AutoPilot %s HALTED: $%.2f <= -$%.2f",
                           config.id, config.realized_pnl_today, config.daily_loss_limit)
            return {"status": "halted", "pnl": config.realized_pnl_today, "exits": exits}

        # 4. Open new positions toward the remaining target
        config.status = "trading"
        entries = self._open_new_positions(config, trading, provider, today)

        config.last_run_at = datetime.utcnow()
        config.last_error = None
        self.db.commit()
        return {
            "status": config.status,
            "pnl": config.realized_pnl_today,
            "exits": exits,
            "entries": entries,
        }

    # ------------------------------------------------------------------
    # Monitoring open positions
    # ------------------------------------------------------------------

    def _monitor_open_positions(
        self,
        config: AutoPilotConfigDB,
        trading: TradingService,
        provider,
    ) -> int:
        """Close positions that hit their take-profit or stop-loss."""
        closed = 0
        for trade in self._open_trades(config):
            price = self._current_price(provider, trading, trade.ticker)
            if price is None:
                continue

            if price >= trade.take_profit_price:
                if self._close_trade(config, trading, trade, price, "take_profit"):
                    closed += 1
            elif price <= trade.stop_price:
                if self._close_trade(config, trading, trade, price, "stop_loss"):
                    closed += 1
        return closed

    # ------------------------------------------------------------------
    # Opening new positions
    # ------------------------------------------------------------------

    def _open_new_positions(
        self,
        config: AutoPilotConfigDB,
        trading: TradingService,
        provider,
        today: date,
    ) -> int:
        open_trades = self._open_trades(config)
        slots = config.max_concurrent_positions - len(open_trades)
        if slots <= 0:
            return 0

        remaining_target = max(config.daily_profit_target - config.realized_pnl_today, 0.0)
        if remaining_target <= 0:
            return 0

        # Scan for candidates
        config.status = "scanning"
        self.db.commit()
        scanner = CandidateScanner(provider)
        filters = ScanFilters(
            market_type=config.market_type,
            min_price=config.min_price,
            max_price=config.max_price,
            min_change_pct=config.min_change_pct,
            min_volume_ratio=config.min_volume_ratio,
            max_candidates=config.max_candidates,
        )
        candidates = scanner.scan(filters)
        if not candidates:
            return 0

        # Skip tickers we already hold
        held = {t.ticker for t in open_trades}
        candidates = [c for c in candidates if c.ticker not in held]

        # LLM gate
        gate = LLMPredictionGate() if config.use_llm else None

        account = trading.get_account_summary()
        cash = account["cash"]

        entries = 0
        for cand in candidates:
            if slots <= 0:
                break

            verdict = None
            if gate is not None:
                verdict = gate.predict_intraday_profit(
                    cand, config.take_profit_pct * 100, config.market_type
                )
                if verdict.confidence < config.llm_min_confidence:
                    logger.info("AutoPilot skip %s: LLM conf %.0f < %.0f",
                                cand.ticker, verdict.confidence, config.llm_min_confidence)
                    continue
                if not verdict.will_hit_target:
                    logger.info("AutoPilot skip %s: LLM says won't hit target", cand.ticker)
                    continue

            # Position sizing toward remaining target
            qty, alloc = self._size_position(config, cand.price, remaining_target, cash)
            if qty < 1:
                continue

            trade = self._open_trade(config, trading, cand, qty, verdict, today)
            if trade is not None:
                entries += 1
                slots -= 1
                cash -= alloc
                # Reduce remaining target by this position's take-profit potential
                remaining_target -= alloc * config.take_profit_pct

        return entries

    def _size_position(
        self,
        config: AutoPilotConfigDB,
        price: float,
        remaining_target: float,
        cash: float,
    ) -> tuple[int, float]:
        """
        Return (quantity, allocation$) for a new position.

        Allocation targets remaining_target / take_profit_pct, capped by the
        per-position budget and available cash.
        """
        if price <= 0 or config.take_profit_pct <= 0:
            return 0, 0.0

        target_alloc = remaining_target / config.take_profit_pct
        max_alloc = config.capital * config.max_position_size_pct
        alloc = min(target_alloc, max_alloc, cash)
        if alloc < price:
            return 0, 0.0

        qty = int(alloc // price)
        return qty, qty * price

    # ------------------------------------------------------------------
    # Trade open / close helpers
    # ------------------------------------------------------------------

    def _open_trade(
        self,
        config: AutoPilotConfigDB,
        trading: TradingService,
        cand: Candidate,
        qty: int,
        verdict,
        today: date,
    ) -> Optional[AutoPilotTradeDB]:
        result = trading.place_order(
            ticker=cand.ticker, side="buy", order_type="market", quantity=qty,
        )
        if result.get("status") != "filled":
            logger.info("AutoPilot entry rejected for %s: %s",
                        cand.ticker, result.get("reason"))
            return None

        fill = float(result.get("filled_price") or cand.price)
        stop = round(fill * (1 - config.stop_loss_pct), 4)
        tp = round(fill * (1 + config.take_profit_pct), 4)

        reason = f"momentum {cand.momentum_score:.0f}, {cand.change_pct:+.1f}%, vol {cand.volume_ratio:.1f}x"
        if verdict is not None:
            reason += f" | LLM {verdict.confidence:.0f}%: {verdict.reasoning}"

        trade = AutoPilotTradeDB(
            config_id=config.id,
            user_id=config.user_id,
            market_type=config.market_type,
            ticker=cand.ticker,
            trading_day=today,
            entry_time=datetime.utcnow(),
            entry_price=fill,
            quantity=qty,
            stop_price=stop,
            take_profit_price=tp,
            momentum_score=cand.momentum_score,
            llm_confidence=(verdict.confidence if verdict is not None else None),
            entry_reason=reason,
            entry_order_id=result.get("order_id"),
            status="open",
        )
        self.db.add(trade)
        config.trades_today += 1
        self.db.commit()
        logger.info("AutoPilot OPEN %s x%d @ $%.4f (stop $%.4f, tp $%.4f)",
                    cand.ticker, qty, fill, stop, tp)
        return trade

    def _close_trade(
        self,
        config: AutoPilotConfigDB,
        trading: TradingService,
        trade: AutoPilotTradeDB,
        price: Optional[float],
        reason: str,
    ) -> bool:
        result = trading.place_order(
            ticker=trade.ticker, side="sell", order_type="market", quantity=trade.quantity,
        )
        if result.get("status") != "filled":
            logger.warning("AutoPilot exit rejected for %s: %s",
                           trade.ticker, result.get("reason"))
            return False

        fill = float(result.get("filled_price") or price or trade.entry_price)
        pnl = (fill - trade.entry_price) * trade.quantity
        pnl_pct = ((fill - trade.entry_price) / trade.entry_price * 100) if trade.entry_price else 0.0

        trade.status = "closed"
        trade.exit_time = datetime.utcnow()
        trade.exit_price = fill
        trade.exit_reason = reason
        trade.exit_order_id = result.get("order_id")
        trade.realized_pnl = round(pnl, 2)
        trade.realized_pnl_pct = round(pnl_pct, 2)
        self.db.commit()
        logger.info("AutoPilot CLOSE %s x%d @ $%.4f — %s, P&L $%.2f",
                    trade.ticker, trade.quantity, fill, reason, pnl)
        return True

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _roll_day(self, config: AutoPilotConfigDB, today: date) -> None:
        """Reset daily counters when the calendar day advances."""
        if config.trading_day != today:
            config.trading_day = today
            config.realized_pnl_today = 0.0
            config.trades_today = 0
            config.target_hit = False
            config.halted = False
            config.status = "idle"
            self.db.commit()

    def _realized_pnl_today(self, config: AutoPilotConfigDB, today: date) -> float:
        rows = (
            self.db.query(AutoPilotTradeDB)
            .filter_by(config_id=config.id, trading_day=today, status="closed")
            .all()
        )
        return round(sum(t.realized_pnl or 0.0 for t in rows), 2)

    def _open_trades(self, config: AutoPilotConfigDB) -> List[AutoPilotTradeDB]:
        return (
            self.db.query(AutoPilotTradeDB)
            .filter_by(config_id=config.id, status="open")
            .all()
        )

    @staticmethod
    def _current_price(provider, trading: TradingService, ticker: str) -> Optional[float]:
        """Prefer the paper position's marked price; fall back to a fresh quote."""
        for pos in trading.get_positions():
            if pos["ticker"] == ticker and pos.get("current_price"):
                return float(pos["current_price"])
        quote = provider.get_quote(ticker)
        return quote.price if quote else None
