"""
Auto-trade bot executor.

BotExecutor.run_bot(bot_id) is the single entry point called by the Celery
beat task. It:
1. Fetches the latest OHLCV bars for the bot's ticker
2. Evaluates the strategy (BUY / SELL / HOLD signal)
3. Checks the risk manager gates
4. Places paper orders via TradingService if approved
5. Logs everything to AutoTradeLogDB

This runs synchronously within the Celery worker thread. Failures are logged
but never crash the entire beat task — one bot failing won't stop others.
"""

import logging
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from autotrade.models import AutoTradeBotDB
from autotrade.strategies import get_strategy, Bar, SignalType
from autotrade.risk import RiskConfig, RiskManager
from autotrade.service import BotService, get_bot_by_id_global
from trading.service import TradingService

logger = logging.getLogger(__name__)


class BotExecutor:
    """Executes a single auto-trade bot's logic."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def run_bot(self, bot_id: UUID) -> None:
        """
        Execute one bot's strategy and place paper orders if signaled.
        
        This is the top-level entry point called by the Celery task.
        All exceptions are caught and logged — never crash the task.
        """
        bot = get_bot_by_id_global(self.db, bot_id)
        if not bot:
            logger.warning("Bot %s not found, skipping.", bot_id)
            return

        if not bot.enabled:
            logger.debug("Bot %s (%s) is disabled, skipping.", bot_id, bot.name)
            return

        bot_service = BotService(self.db, bot.user_id)
        trading_service = TradingService(self.db, bot.user_id)

        try:
            self._execute(bot, bot_service, trading_service)
        except Exception as exc:
            logger.exception("Bot %s (%s) execution failed: %s", bot_id, bot.name, exc)
            bot_service.record_run(bot_id, signal="HOLD", error=str(exc))
            bot_service.log_execution(
                bot_id,
                ticker=bot.ticker,
                price=None,
                signal_type="HOLD",
                signal_confidence=None,
                signal_reason=None,
                action_taken="error",
                details=f"Exception: {exc}",
            )

    def _execute(
        self,
        bot: AutoTradeBotDB,
        bot_service: BotService,
        trading_service: TradingService,
    ) -> None:
        """
        Internal execution logic. Raises on errors so the outer handler can log them.
        
        Flow:
        1. Fetch latest bars (yfinance, 60 days daily for sufficient history)
        2. Build strategy + risk manager from bot config
        3. Evaluate strategy → signal
        4. Log signal
        5. If BUY and no position: try to enter via risk manager + TradingService
        6. If SELL and have position: close via TradingService
        7. Update bot.last_run_at + last_signal
        """
        import yfinance as yf

        ticker = bot.ticker
        logger.info("Running bot %s (%s) for %s", bot.id, bot.name, ticker)

        # 1. Fetch bars
        t = yf.Ticker(ticker)
        hist = t.history(period="60d", interval="1d")
        if hist is None or hist.empty:
            raise ValueError(f"No historical data for {ticker}")

        bars: list[Bar] = []
        for ts, row in hist.iterrows():
            try:
                bars.append(Bar(
                    timestamp=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                ))
            except (ValueError, KeyError, TypeError):
                continue

        if not bars:
            raise ValueError(f"No valid bars for {ticker}")

        current_price = bars[-1].close

        # 2. Build strategy + risk manager
        strategy = get_strategy(bot.strategy)
        risk_config = RiskConfig(
            position_size_pct=bot.position_size_pct,
            stop_loss_pct=bot.stop_loss_pct,
            take_profit_pct=bot.take_profit_pct,
            daily_loss_limit_pct=bot.daily_loss_limit_pct,
            max_positions=bot.max_positions,
            max_trades_per_day=bot.max_trades_per_day,
            min_confidence=bot.min_confidence,
        )
        risk_manager = RiskManager(risk_config)

        # Check if we have a position in this ticker
        positions = trading_service.get_positions()
        has_position = any(p["ticker"] == ticker for p in positions)

        # 3. Evaluate strategy
        if len(bars) < strategy.min_bars:
            raise ValueError(
                f"Not enough bars: {len(bars)}, strategy needs {strategy.min_bars}"
            )

        signal = strategy.evaluate(bars, has_position)

        logger.info(
            "Bot %s signal: %s (conf=%.1f) — %s",
            bot.id, signal.type, signal.confidence, signal.reason
        )

        # 4. Log signal
        bot_service.log_execution(
            bot.id,
            ticker=ticker,
            price=current_price,
            signal_type=signal.type.value,
            signal_confidence=signal.confidence,
            signal_reason=signal.reason,
            action_taken="no_action",  # will be overwritten if we place an order
        )

        # 5. Act on signal
        action_taken = "no_action"
        order_id = None
        details = None

        if signal.type == SignalType.BUY and not has_position:
            # Attempt entry
            account = trading_service.get_account_summary()
            equity = account["total_value"]
            cash = account["cash"]

            decision = risk_manager.evaluate_entry(
                today=datetime.utcnow().date(),
                equity=equity,
                cash=cash,
                price=current_price,
                confidence=signal.confidence,
                open_positions=len([p for p in positions if p["ticker"] != ticker]),
            )

            if decision.approved:
                result = trading_service.place_order(
                    ticker=ticker,
                    side="buy",
                    order_type="market",
                    quantity=decision.quantity,
                )
                if result["status"] == "filled":
                    action_taken = "order_placed"
                    order_id = result.get("order_id")
                    details = f"BUY {decision.quantity} shares @ ${current_price:.2f}"
                    risk_manager.record_trade_open()
                    logger.info("Bot %s placed BUY order: %s", bot.id, order_id)
                else:
                    action_taken = "order_rejected"
                    details = result.get("reason", "Unknown rejection")
            else:
                action_taken = "risk_blocked"
                details = decision.reason

        elif signal.type == SignalType.SELL and has_position:
            # Close position
            pos = next((p for p in positions if p["ticker"] == ticker), None)
            if pos:
                result = trading_service.place_order(
                    ticker=ticker,
                    side="sell",
                    order_type="market",
                    quantity=pos["quantity"],
                )
                if result["status"] == "filled":
                    action_taken = "order_placed"
                    order_id = result.get("order_id")
                    pnl = pos["unrealized_pnl"]
                    details = f"SELL {pos['quantity']} shares @ ${current_price:.2f}, P&L=${pnl:.2f}"
                    # Update bot stats
                    bot_service.record_trade(bot.id, pnl=pnl, is_win=(pnl >= 0))
                    risk_manager.record_trade_close(pnl)
                    logger.info("Bot %s placed SELL order: %s", bot.id, order_id)
                else:
                    action_taken = "order_rejected"
                    details = result.get("reason", "Unknown rejection")

        # 6. Update log with action
        if action_taken != "no_action":
            # Overwrite the earlier log entry with the actual action
            logs = bot_service.get_logs(bot.id, limit=1)
            if logs:
                last_log = logs[0]
                last_log.action_taken = action_taken
                last_log.order_id = order_id
                last_log.details = details
                self.db.commit()

        # 7. Update bot state
        bot_service.record_run(bot.id, signal=signal.type.value, error=None)
        logger.info("Bot %s run complete: %s", bot.id, action_taken)
