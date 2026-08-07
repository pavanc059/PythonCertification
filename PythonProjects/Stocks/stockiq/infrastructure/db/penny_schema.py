"""
SQLAlchemy ORM models for penny stock tables.

Tables defined here:
    PennyStockMomentum  — daily momentum scores and price/volume metrics
    PennyStockRiskMetrics — daily liquidity, volatility, and spread metrics
    PennyStockAlert     — threshold-triggered alerts for penny stocks

Column names intentionally match the design-doc dataclass fields so
that application code requires no mapping layer:
    - momentum_score, price_change_pct, volume_ratio  (momentum table)
    - liquidity_risk, volatility_risk, spread_pct      (risk table)
    - ticker, alert_type, threshold, triggered_at      (alerts table)

Requirements: 11.1–11.20 (Penny Stock Momentum Dashboard)
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Date,
    Float,
    Index,
    Integer,
    Numeric,
    BigInteger,
    String,
    Text,
    UniqueConstraint,
)

from ..database import Base


# ---------------------------------------------------------------------------
# PennyStockMomentum
# ---------------------------------------------------------------------------

class PennyStockMomentum(Base):
    """
    Daily momentum snapshot for a penny stock.

    One row per (ticker, date) pair; the UNIQUE constraint enforces
    idempotent upserts from the Celery tasks.

    Core columns (per task spec):
        ticker          — stock symbol (VARCHAR 10)
        date            — trading date (DATE)
        momentum_score  — composite score 0–100 (FLOAT)
        price_change_pct — percentage price change (FLOAT)
        volume_ratio    — current_volume / avg_volume (FLOAT, ≥ 0)
    """

    __tablename__ = "penny_stock_momentum"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # ---- Core task-spec columns ----
    ticker = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    momentum_score = Column(Float, nullable=False)   # 0–100
    price_change_pct = Column(Float, nullable=False)
    volume_ratio = Column(Float, nullable=False)     # ≥ 0

    # ---- Extended momentum breakdown ----
    price_component = Column(Float)      # 40% weight
    volume_component = Column(Float)     # 30% weight
    trend_component = Column(Float)      # 20% weight
    catalyst_component = Column(Float)   # 10% weight

    # ---- Additional context ----
    price = Column(Numeric(10, 4))       # must be ≤ $5.00
    volume = Column(BigInteger)
    avg_volume = Column(BigInteger)
    catalyst = Column(String(500))
    rank = Column(Integer)               # rank within the day's top list

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ---- Constraints ----
    __table_args__ = (
        # Idempotency
        UniqueConstraint("ticker", "date", name="uq_psm_ticker_date"),
        # Business-rule guards
        CheckConstraint(
            "momentum_score >= 0 AND momentum_score <= 100",
            name="chk_psm_momentum_range",
        ),
        CheckConstraint(
            "volume_ratio >= 0",
            name="chk_psm_volume_ratio",
        ),
        CheckConstraint(
            "price IS NULL OR price <= 5.0",
            name="chk_psm_penny_price",
        ),
        # Indexes on ticker and date (query performance requirement)
        Index("idx_psm_ticker", "ticker"),
        Index("idx_psm_date", "date"),
        Index("idx_psm_ticker_date", "ticker", "date"),
        Index("idx_psm_date_rank", "date", "rank"),
        Index("idx_psm_date_momentum_score", "date", "momentum_score"),
    )


# ---------------------------------------------------------------------------
# PennyStockRiskMetrics
# ---------------------------------------------------------------------------

class PennyStockRiskMetrics(Base):
    """
    Daily risk metrics for a penny stock.

    One row per (ticker, date); the UNIQUE constraint enforces idempotent
    upserts from the Celery tasks.

    Core columns (per task spec):
        ticker          — stock symbol (VARCHAR 10)
        date            — trading date (DATE)
        liquidity_risk  — 0–1 float; higher = more risky
        volatility_risk — 0–1 float; higher = more risky
        spread_pct      — bid-ask spread as % of mid-price (≥ 0)

    Note: the column is named ``spread_pct`` (not ``spread_percentage``) to
    match the task specification and the ``RiskMetrics`` dataclass field name
    used in stockiq.news.penny.scanner.
    """

    __tablename__ = "penny_stock_risk_metrics"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # ---- Core task-spec columns ----
    ticker = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    liquidity_risk = Column(Float, nullable=False)   # 0–1
    volatility_risk = Column(Float, nullable=False)  # 0–1
    spread_pct = Column(Float, nullable=False)        # ≥ 0

    # ---- Extended risk classification ----
    overall_risk = Column(String(20))    # 'low', 'medium', 'high', 'extreme'
    suspicion_score = Column(Float)      # 0–1, pump-dump indicator
    recommendation = Column(String(20))  # 'safe', 'caution', 'avoid'

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ---- Constraints ----
    __table_args__ = (
        # Idempotency
        UniqueConstraint("ticker", "date", name="uq_psrm_ticker_date"),
        # Business-rule guards
        CheckConstraint(
            "liquidity_risk >= 0 AND liquidity_risk <= 1",
            name="chk_psrm_liquidity",
        ),
        CheckConstraint(
            "volatility_risk >= 0 AND volatility_risk <= 1",
            name="chk_psrm_volatility",
        ),
        CheckConstraint(
            "spread_pct >= 0",
            name="chk_psrm_spread",
        ),
        CheckConstraint(
            "overall_risk IS NULL OR overall_risk IN ('low', 'medium', 'high', 'extreme')",
            name="chk_psrm_overall_risk",
        ),
        CheckConstraint(
            "suspicion_score IS NULL OR (suspicion_score >= 0 AND suspicion_score <= 1)",
            name="chk_psrm_suspicion",
        ),
        CheckConstraint(
            "recommendation IS NULL OR recommendation IN ('safe', 'caution', 'avoid')",
            name="chk_psrm_recommendation",
        ),
        # Indexes on ticker and date (query performance requirement)
        Index("idx_psrm_ticker", "ticker"),
        Index("idx_psrm_date", "date"),
        Index("idx_psrm_ticker_date", "ticker", "date"),
        Index("idx_psrm_date_overall_risk", "date", "overall_risk"),
    )


# ---------------------------------------------------------------------------
# PennyStockAlert
# ---------------------------------------------------------------------------

class PennyStockAlert(Base):
    """
    Threshold-triggered alert for a penny stock.

    Scoped exclusively to penny-stock alert types.  Uses ``triggered_at``
    as the primary temporal column (the equivalent of ``date`` in the other
    penny tables).

    Core columns (per task spec):
        ticker       — stock symbol (VARCHAR 10)
        alert_type   — type of alert (VARCHAR 50)
        threshold    — the value that was crossed (FLOAT)
        triggered_at — when the threshold was crossed (TIMESTAMP)
    """

    __tablename__ = "penny_stock_alerts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # ---- Core task-spec columns ----
    ticker = Column(String(10), nullable=False)
    alert_type = Column(String(50), nullable=False)
    threshold = Column(Float, nullable=False)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ---- Additional context ----
    current_value = Column(Float)   # actual value that triggered the alert
    message = Column(Text)          # human-readable description
    priority = Column(Integer, default=1)   # 1=low, 2=medium, 3=high
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ---- Constraints ----
    __table_args__ = (
        CheckConstraint(
            "priority BETWEEN 1 AND 3",
            name="chk_psa_priority",
        ),
        # Indexes on ticker and date-equivalent (triggered_at)
        Index("idx_psa_ticker", "ticker"),
        Index("idx_psa_triggered_at", "triggered_at"),
        Index("idx_psa_ticker_triggered_at", "ticker", "triggered_at"),
        Index("idx_psa_alert_type", "alert_type"),
    )
