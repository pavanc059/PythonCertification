"""
SQLAlchemy models for AutoPilot — the portfolio-level automated day-trader.

Three tables:
  - autopilot_config        one row per (user, market_type). Holds capital,
                            daily target, risk parameters, universe filters,
                            the LLM gate, and live daily state.
  - autopilot_trades        every entry/exit AutoPilot makes, with stop/take-
                            profit levels, LLM confidence, and realized P&L.
  - autopilot_daily_reports one row per (config, trading_day) summarising
                            performance versus the daily target.

market_type is either "penny" or "regular" — the two independent sections
the user configures. A user may run both simultaneously.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Date, Boolean, Integer, Float, ForeignKey,
    Index, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class AutoPilotConfigDB(Base):
    """
    A user's AutoPilot configuration for one market segment.

    Exactly one row per (user_id, market_type). The unique constraint enforces
    that a user has at most one penny config and one regular config.
    """
    __tablename__ = "autopilot_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # "penny" | "regular"
    market_type = Column(String(10), nullable=False)

    # Master switch
    enabled = Column(Boolean, nullable=False, default=False)

    # ---- Budget & targets (dollar amounts) ----
    capital = Column(Float, nullable=False, default=10000.0)          # logical budget
    daily_profit_target = Column(Float, nullable=False, default=100.0)  # $ to make/day
    daily_loss_limit = Column(Float, nullable=False, default=200.0)     # $ max daily loss

    # ---- Per-trade risk ----
    max_concurrent_positions = Column(Integer, nullable=False, default=3)
    max_position_size_pct = Column(Float, nullable=False, default=0.34)  # of capital
    take_profit_pct = Column(Float, nullable=False, default=0.03)        # +3% per trade
    stop_loss_pct = Column(Float, nullable=False, default=0.02)          # -2% per trade

    # ---- Universe filters ----
    min_price = Column(Float, nullable=False, default=0.50)
    max_price = Column(Float, nullable=False, default=5.0)   # penny default; regular overrides
    min_change_pct = Column(Float, nullable=False, default=3.0)   # min intraday move to consider
    min_volume_ratio = Column(Float, nullable=False, default=1.5)  # volume surge threshold
    max_candidates = Column(Integer, nullable=False, default=15)   # top-N to evaluate

    # ---- LLM prediction gate ----
    use_llm = Column(Boolean, nullable=False, default=True)
    llm_min_confidence = Column(Float, nullable=False, default=60.0)

    # ---- Day-trading controls ----
    # Minutes before market close (16:00 ET) to force-flat all positions.
    force_flat_minutes_before_close = Column(Integer, nullable=False, default=5)

    # Data provider override (falls back to global settings if null)
    data_provider = Column(String(20), nullable=True)

    # ---- Live daily state (rolled each trading day) ----
    trading_day = Column(Date, nullable=True)
    realized_pnl_today = Column(Float, nullable=False, default=0.0)
    trades_today = Column(Integer, nullable=False, default=0)
    target_hit = Column(Boolean, nullable=False, default=False)
    halted = Column(Boolean, nullable=False, default=False)   # daily loss limit breached
    status = Column(String(20), nullable=False, default="idle")  # idle|scanning|trading|target_hit|halted|closed
    last_run_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="autopilot_configs")
    trades = relationship("AutoPilotTradeDB", back_populates="config", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "market_type", name="uq_autopilot_user_market"),
        Index("ix_autopilot_config_user_id", "user_id"),
        Index("ix_autopilot_config_enabled", "enabled"),
    )

    def __repr__(self) -> str:
        return (
            f"<AutoPilotConfigDB user={self.user_id} market={self.market_type} "
            f"enabled={self.enabled} target=${self.daily_profit_target} status={self.status}>"
        )


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class AutoPilotTradeDB(Base):
    """
    A single AutoPilot trade (one round-trip: open -> close).

    While open, exit_* fields are null and status is "open". On close they are
    populated and status becomes "closed".
    """
    __tablename__ = "autopilot_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    config_id = Column(UUID(as_uuid=True), ForeignKey("autopilot_config.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    market_type = Column(String(10), nullable=False)
    ticker = Column(String(10), nullable=False)
    trading_day = Column(Date, nullable=False)

    # Entry
    entry_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    stop_price = Column(Float, nullable=False)
    take_profit_price = Column(Float, nullable=False)

    # Decision context
    momentum_score = Column(Float, nullable=True)
    llm_confidence = Column(Float, nullable=True)
    entry_reason = Column(Text, nullable=True)
    entry_order_id = Column(String, nullable=True)

    # Exit
    status = Column(String(10), nullable=False, default="open")  # "open" | "closed"
    exit_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_reason = Column(String(20), nullable=True)  # take_profit|stop_loss|force_flat|target_lock|signal
    exit_order_id = Column(String, nullable=True)
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_pct = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    config = relationship("AutoPilotConfigDB", back_populates="trades")

    __table_args__ = (
        Index("ix_autopilot_trades_config_id", "config_id"),
        Index("ix_autopilot_trades_user_id", "user_id"),
        Index("ix_autopilot_trades_status", "status"),
        Index("ix_autopilot_trades_trading_day", "trading_day"),
    )

    def __repr__(self) -> str:
        return (
            f"<AutoPilotTradeDB {self.ticker} qty={self.quantity} "
            f"status={self.status} pnl={self.realized_pnl}>"
        )


# ---------------------------------------------------------------------------
# Daily reports
# ---------------------------------------------------------------------------

class AutoPilotDailyReportDB(Base):
    """End-of-day performance summary for one config on one trading day."""
    __tablename__ = "autopilot_daily_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    config_id = Column(UUID(as_uuid=True), ForeignKey("autopilot_config.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    market_type = Column(String(10), nullable=False)
    trading_day = Column(Date, nullable=False)

    capital = Column(Float, nullable=False)
    daily_profit_target = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    target_met = Column(Boolean, nullable=False, default=False)
    return_pct = Column(Float, nullable=False, default=0.0)  # realized_pnl / capital * 100

    num_trades = Column(Integer, nullable=False, default=0)
    num_winning = Column(Integer, nullable=False, default=0)
    num_losing = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=False, default=0.0)
    best_trade_pnl = Column(Float, nullable=True)
    worst_trade_pnl = Column(Float, nullable=True)

    summary = Column(Text, nullable=True)  # LLM-written narrative
    details = Column(Text, nullable=True)  # JSON blob of per-trade detail

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("config_id", "trading_day", name="uq_autopilot_report_config_day"),
        Index("ix_autopilot_reports_user_id", "user_id"),
        Index("ix_autopilot_reports_trading_day", "trading_day"),
    )

    def __repr__(self) -> str:
        return (
            f"<AutoPilotDailyReportDB {self.market_type} {self.trading_day} "
            f"pnl=${self.realized_pnl:.2f} met={self.target_met}>"
        )
