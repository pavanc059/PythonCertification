"""
Service layer for auto-trade bot CRUD operations.

BotService owns all persistence logic for bot configuration and logs.
The executor (executor.py) and Celery task use this service to load bots,
update stats, and write audit logs.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from autotrade.models import AutoTradeBotDB, AutoTradeLogDB
from autotrade.risk import RiskConfig


class BotService:
    """Service for managing auto-trade bots."""

    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_bot(
        self,
        *,
        name: str,
        ticker: str,
        strategy: str,
        risk: RiskConfig,
        enabled: bool = True,
    ) -> AutoTradeBotDB:
        """Create a new auto-trade bot for the current user."""
        bot = AutoTradeBotDB(
            user_id=self.user_id,
            name=name,
            ticker=ticker.upper().strip(),
            strategy=strategy,
            enabled=enabled,
            position_size_pct=risk.position_size_pct,
            stop_loss_pct=risk.stop_loss_pct,
            take_profit_pct=risk.take_profit_pct,
            daily_loss_limit_pct=risk.daily_loss_limit_pct,
            max_positions=risk.max_positions,
            max_trades_per_day=risk.max_trades_per_day,
            min_confidence=risk.min_confidence,
        )
        self.db.add(bot)
        self.db.commit()
        self.db.refresh(bot)
        return bot

    def list_bots(self) -> List[AutoTradeBotDB]:
        """Return all bots for the current user (newest first)."""
        return (
            self.db.query(AutoTradeBotDB)
            .filter_by(user_id=self.user_id)
            .order_by(AutoTradeBotDB.created_at.desc())
            .all()
        )

    def get_bot(self, bot_id: UUID) -> AutoTradeBotDB:
        """
        Fetch a bot by ID, ensuring it belongs to the current user.
        
        Raises:
            HTTPException 404: Bot not found or does not belong to user.
        """
        bot = (
            self.db.query(AutoTradeBotDB)
            .filter_by(id=bot_id, user_id=self.user_id)
            .first()
        )
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot '{bot_id}' not found.",
            )
        return bot

    def update_bot(
        self,
        bot_id: UUID,
        *,
        name: Optional[str] = None,
        ticker: Optional[str] = None,
        strategy: Optional[str] = None,
        enabled: Optional[bool] = None,
        risk: Optional[RiskConfig] = None,
    ) -> AutoTradeBotDB:
        """Update a bot's configuration."""
        bot = self.get_bot(bot_id)

        if name is not None:
            bot.name = name
        if ticker is not None:
            bot.ticker = ticker.upper().strip()
        if strategy is not None:
            bot.strategy = strategy
        if enabled is not None:
            bot.enabled = enabled
        if risk is not None:
            bot.position_size_pct = risk.position_size_pct
            bot.stop_loss_pct = risk.stop_loss_pct
            bot.take_profit_pct = risk.take_profit_pct
            bot.daily_loss_limit_pct = risk.daily_loss_limit_pct
            bot.max_positions = risk.max_positions
            bot.max_trades_per_day = risk.max_trades_per_day
            bot.min_confidence = risk.min_confidence

        self.db.commit()
        self.db.refresh(bot)
        return bot

    def delete_bot(self, bot_id: UUID) -> None:
        """Delete a bot and all its logs."""
        bot = self.get_bot(bot_id)
        self.db.delete(bot)
        self.db.commit()

    # ------------------------------------------------------------------
    # Execution state updates (called by executor)
    # ------------------------------------------------------------------

    def record_run(
        self,
        bot_id: UUID,
        *,
        signal: str,
        error: Optional[str] = None,
    ) -> None:
        """Update bot's last_run_at and last_signal after a run."""
        bot = self.get_bot(bot_id)
        bot.last_run_at = datetime.utcnow()
        bot.last_signal = signal
        bot.last_error = error
        self.db.commit()

    def record_trade(
        self,
        bot_id: UUID,
        *,
        pnl: float,
        is_win: bool,
    ) -> None:
        """Increment trade counters when a bot closes a position."""
        bot = self.get_bot(bot_id)
        bot.total_trades += 1
        if is_win:
            bot.winning_trades += 1
        bot.total_pnl += pnl
        self.db.commit()

    # ------------------------------------------------------------------
    # Audit logs
    # ------------------------------------------------------------------

    def log_execution(
        self,
        bot_id: UUID,
        *,
        ticker: str,
        price: Optional[float],
        signal_type: str,
        signal_confidence: Optional[float],
        signal_reason: Optional[str],
        action_taken: str,
        order_id: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Write an audit log entry for a bot execution."""
        log = AutoTradeLogDB(
            bot_id=bot_id,
            user_id=self.user_id,
            ticker=ticker,
            price=price,
            signal_type=signal_type,
            signal_confidence=signal_confidence,
            signal_reason=signal_reason,
            action_taken=action_taken,
            order_id=order_id,
            details=details,
        )
        self.db.add(log)
        self.db.commit()

    def get_logs(
        self,
        bot_id: UUID,
        limit: int = 100,
    ) -> List[AutoTradeLogDB]:
        """Return recent execution logs for a bot (newest first)."""
        # Verify ownership
        self.get_bot(bot_id)
        return (
            self.db.query(AutoTradeLogDB)
            .filter_by(bot_id=bot_id)
            .order_by(AutoTradeLogDB.timestamp.desc())
            .limit(limit)
            .all()
        )


# ------------------------------------------------------------------
# Global helpers for Celery task (no user_id required)
# ------------------------------------------------------------------

def get_all_enabled_bots(db: Session) -> List[AutoTradeBotDB]:
    """Return all enabled bots across all users (for Celery task)."""
    return db.query(AutoTradeBotDB).filter_by(enabled=True).all()


def get_bot_by_id_global(db: Session, bot_id: UUID) -> Optional[AutoTradeBotDB]:
    """Fetch a bot by ID without user_id check (for Celery task)."""
    return db.query(AutoTradeBotDB).filter_by(id=bot_id).first()
