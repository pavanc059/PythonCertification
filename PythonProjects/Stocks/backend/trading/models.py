"""
SQLAlchemy ORM models for paper trading persistence.

Tables
------
paper_trading_accounts  — one account per user, holds cash balance
paper_positions         — open positions for an account
paper_orders            — all orders (pending, filled, cancelled, rejected)
real_trade_audit_log    — immutable audit log for real-money confirmation events

Requirements: R4.1, R4.3, R7.8, R7.1, R7.3
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class PaperTradingAccountDB(Base):
    """One paper trading account per user, created on registration."""

    __tablename__ = "paper_trading_accounts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # Virtual cash balance — starts at $100,000 (R4.1)
    cash = Column(Numeric(18, 6), nullable=False, default=100000)
    initial_cash = Column(Numeric(18, 6), nullable=False, default=100000)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    positions = relationship(
        "PaperPositionDB",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="select",
    )
    orders = relationship(
        "PaperOrderDB",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaperTradingAccountDB id={self.id} user_id={self.user_id} cash={self.cash}>"


class PaperPositionDB(Base):
    """Open positions within a paper trading account."""

    __tablename__ = "paper_positions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("paper_trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticker = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Numeric(18, 6), nullable=False)
    current_price = Column(Numeric(18, 6), nullable=False)
    entry_time = Column(DateTime, nullable=False)
    last_updated = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    account = relationship("PaperTradingAccountDB", back_populates="positions")

    __table_args__ = (
        Index("ix_paper_positions_account_id", "account_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PaperPositionDB ticker={self.ticker} qty={self.quantity} "
            f"account_id={self.account_id}>"
        )


class PaperOrderDB(Base):
    """All orders placed within a paper trading account."""

    __tablename__ = "paper_orders"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("paper_trading_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    # order_id is the UUID string from the domain Order object
    order_id = Column(String, nullable=False, unique=True)
    ticker = Column(String, nullable=False)
    # "buy" | "sell"
    side = Column(String, nullable=False)
    # "market" | "limit" | "stop_loss" | "stop_limit"
    order_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    limit_price = Column(Numeric(18, 6), nullable=True)
    stop_price = Column(Numeric(18, 6), nullable=True)
    # "pending" | "filled" | "cancelled" | "rejected"
    status = Column(String, nullable=False)
    filled_price = Column(Numeric(18, 6), nullable=True)
    filled_quantity = Column(Integer, nullable=False, default=0)
    commission = Column(Numeric(18, 6), nullable=False, default=0)
    slippage = Column(Numeric(18, 6), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)

    account = relationship("PaperTradingAccountDB", back_populates="orders")

    __table_args__ = (
        Index("ix_paper_orders_account_id", "account_id"),
        Index("ix_paper_orders_ticker", "ticker"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PaperOrderDB order_id={self.order_id} ticker={self.ticker} "
            f"side={self.side} status={self.status}>"
        )


class RealTradeAuditLog(Base):
    """Immutable audit log for real-money trade confirmation events.

    Rows are insert-only — no update or delete methods are provided.
    The user_id FK uses ondelete="RESTRICT" to preserve audit evidence
    even if a user account is deleted.

    Requirements: R7.1, R7.3
    """

    __tablename__ = "real_trade_audit_log"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ticker = Column(String(10), nullable=False)
    # "buy" | "sell"
    side = Column(String(4), nullable=False)
    order_type = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    limit_price = Column(Numeric(18, 6), nullable=True)
    stop_price = Column(Numeric(18, 6), nullable=True)
    # The exact string the user typed — preserved as audit evidence
    confirmation_text = Column(Text, nullable=False)
    # "confirmed" | "rejected" | "expired"
    outcome = Column(String(10), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_rtaudit_user_created", "user_id", "created_at"),
        Index("ix_rtaudit_ticker", "ticker"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RealTradeAuditLog id={self.id} ticker={self.ticker} "
            f"side={self.side} outcome={self.outcome}>"
        )
