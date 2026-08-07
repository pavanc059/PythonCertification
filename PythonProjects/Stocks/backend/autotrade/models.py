"""
SQLAlchemy models for the auto-trade engine.

AutoTradeBotDB stores the configuration for each user's trading bot:
strategy, ticker, risk parameters, enabled state, and running statistics.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Float, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class AutoTradeBotDB(Base):
    """
    A user's auto-trade bot configuration and running statistics.
    
    Each bot watches a single ticker and executes one strategy with a fixed
    risk profile. Users can enable/disable bots at will. The Celery beat task
    runs all enabled bots every 5 minutes during market hours.
    """
    __tablename__ = "autotrade_bots"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Bot config
    name = Column(String(100), nullable=False)  # user-chosen display name
    ticker = Column(String(10), nullable=False)
    strategy = Column(String(50), nullable=False)  # "momentum" | "mean_reversion" | "ma_crossover"
    enabled = Column(Boolean, nullable=False, default=True)

    # Risk config (stored as individual columns for queryability)
    position_size_pct = Column(Float, nullable=False, default=0.10)
    stop_loss_pct = Column(Float, nullable=False, default=0.02)
    take_profit_pct = Column(Float, nullable=False, default=0.04)
    daily_loss_limit_pct = Column(Float, nullable=False, default=0.03)
    max_positions = Column(Integer, nullable=False, default=5)
    max_trades_per_day = Column(Integer, nullable=False, default=10)
    min_confidence = Column(Float, nullable=False, default=55.0)

    # Execution state
    last_run_at = Column(DateTime, nullable=True)
    last_signal = Column(String(10), nullable=True)  # "BUY" | "SELL" | "HOLD"
    last_error = Column(Text, nullable=True)

    # Running statistics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    total_pnl = Column(Float, nullable=False, default=0.0)  # cumulative realized P&L

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    user = relationship("User", back_populates="autotrade_bots")

    __table_args__ = (
        Index("ix_autotrade_bots_user_id", "user_id"),
        Index("ix_autotrade_bots_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        return (
            f"<AutoTradeBotDB id={self.id} user_id={self.user_id} "
            f"name='{self.name}' ticker={self.ticker} strategy={self.strategy} "
            f"enabled={self.enabled}>"
        )


class AutoTradeLogDB(Base):
    """
    Audit log for auto-trade bot executions.
    
    Every time a bot runs (every 5 minutes), we log the signal, decision,
    and any order placed. This provides a full audit trail for debugging
    and compliance.
    """
    __tablename__ = "autotrade_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    bot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("autotrade_bots.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    ticker = Column(String(10), nullable=False)
    price = Column(Float, nullable=True)  # current price at evaluation
    signal_type = Column(String(10), nullable=False)  # "BUY" | "SELL" | "HOLD"
    signal_confidence = Column(Float, nullable=True)
    signal_reason = Column(Text, nullable=True)
    action_taken = Column(String(20), nullable=False)  # "order_placed" | "risk_blocked" | "no_action" | "error"
    order_id = Column(String, nullable=True)  # paper order ID if placed
    details = Column(Text, nullable=True)  # JSON or human-readable detail

    __table_args__ = (
        Index("ix_autotrade_logs_bot_id", "bot_id"),
        Index("ix_autotrade_logs_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<AutoTradeLogDB bot_id={self.bot_id} ticker={self.ticker} "
            f"signal={self.signal_type} action={self.action_taken}>"
        )
