"""
SQLAlchemy ORM models for all database tables.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Text, Boolean,
    ForeignKey, Index, CheckConstraint, Numeric, BigInteger, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from .database import Base


# Enums
class NewsCategory(str, enum.Enum):
    """News article categories."""
    EARNINGS = "earnings"
    MA = "M&A"
    REGULATORY = "regulatory"
    ECONOMIC = "economic"
    SECTOR_SPECIFIC = "sector-specific"
    GENERAL = "general"


class PredictionCategory(str, enum.Enum):
    """Prediction categories."""
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


class RiskLevel(str, enum.Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class AlertType(str, enum.Enum):
    """Alert types."""
    PRICE_THRESHOLD = "price_threshold"
    NEWS_SENTIMENT = "news_sentiment"
    EARNINGS = "earnings"
    MA = "M&A"
    REGULATORY = "regulatory"
    UNUSUAL_VOLUME = "unusual_volume"
    MOMENTUM_THRESHOLD = "momentum_threshold"
    PUMP_DUMP_WARNING = "pump_dump_warning"


# Models
class Stock(Base):
    """Stock information table."""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(BigInteger)  # Market cap in dollars
    avg_volume = Column(BigInteger)  # Average daily volume
    is_penny_stock = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    price_data = relationship("PriceData", back_populates="stock", cascade="all, delete-orphan")
    news_sentiment = relationship("NewsSentiment", back_populates="stock", cascade="all, delete-orphan")
    predictions = relationship("DailyPrediction", back_populates="stock", cascade="all, delete-orphan")
    top_movers = relationship("TopMover", back_populates="stock", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_stocks_sector", "sector"),
        Index("idx_stocks_market_cap", "market_cap"),
        Index("idx_stocks_penny", "is_penny_stock"),
    )


class PriceData(Base):
    """
    Time-series price data table (TimescaleDB hypertable).
    This will be converted to a hypertable in the init script.
    
    Note: For TimescaleDB hypertables, the partitioning column (timestamp)
    must be part of the primary key. We use a composite primary key (id, timestamp).
    """
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, primary_key=True)
    open = Column(Numeric(10, 2), nullable=False)
    high = Column(Numeric(10, 2), nullable=False)
    low = Column(Numeric(10, 2), nullable=False)
    close = Column(Numeric(10, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    adjusted_close = Column(Numeric(10, 2))
    
    # Relationships
    stock = relationship("Stock", back_populates="price_data")
    
    __table_args__ = (
        Index("idx_price_data_stock_timestamp", "stock_id", "timestamp"),
        CheckConstraint("high >= open", name="check_high_gte_open"),
        CheckConstraint("high >= close", name="check_high_gte_close"),
        CheckConstraint("low <= open", name="check_low_lte_open"),
        CheckConstraint("low <= close", name="check_low_lte_close"),
        CheckConstraint("volume >= 0", name="check_volume_non_negative"),
    )


class NewsArticle(Base):
    """News articles table."""
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    source = Column(String(100), nullable=False, index=True)
    author = Column(String(255))
    published_at = Column(DateTime, nullable=False, index=True)
    url = Column(String(1000))
    category = Column(SQLEnum(NewsCategory), index=True)
    relevance_score = Column(Float)
    is_breaking = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sentiment = relationship("NewsSentiment", back_populates="article", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_news_published_at", "published_at"),
        Index("idx_news_category", "category"),
        Index("idx_news_breaking", "is_breaking"),
    )


class NewsSentiment(Base):
    """News sentiment analysis results."""
    __tablename__ = "news_sentiment"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    sentiment_score = Column(Float, nullable=False)  # -1 to +1
    vader_score = Column(Float)
    finbert_score = Column(Float)
    confidence = Column(Float)
    entities = Column(JSONB)  # Store extracted entities as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("NewsArticle", back_populates="sentiment")
    stock = relationship("Stock", back_populates="news_sentiment")
    
    __table_args__ = (
        Index("idx_sentiment_article_stock", "article_id", "stock_id"),
        Index("idx_sentiment_score", "sentiment_score"),
        CheckConstraint("sentiment_score >= -1.0 AND sentiment_score <= 1.0", name="check_sentiment_range"),
    )


class DailyPrediction(Base):
    """Daily stock predictions."""
    __tablename__ = "daily_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    prediction_date = Column(Date, nullable=False, index=True)
    predicted_price = Column(Numeric(10, 2), nullable=False)
    confidence = Column(Float, nullable=False)  # 0-100
    lower_bound = Column(Numeric(10, 2))
    upper_bound = Column(Numeric(10, 2))
    category = Column(SQLEnum(PredictionCategory))
    factors = Column(JSONB)  # Store prediction factors as JSON
    model_version = Column(String(50))
    actual_price = Column(Numeric(10, 2))  # Filled in after the day
    is_accurate = Column(Boolean)  # True if prediction direction was correct
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="predictions")
    
    __table_args__ = (
        Index("idx_predictions_stock_date", "stock_id", "prediction_date"),
        Index("idx_predictions_date", "prediction_date"),
        Index("idx_predictions_confidence", "confidence"),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="check_confidence_range"),
        CheckConstraint("lower_bound <= predicted_price", name="check_lower_bound"),
        CheckConstraint("predicted_price <= upper_bound", name="check_upper_bound"),
    )


class TopMover(Base):
    """Daily top movers (gainers and losers)."""
    __tablename__ = "top_movers"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    price_change_pct = Column(Float, nullable=False)
    price_change_abs = Column(Numeric(10, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    volume_ratio = Column(Float)  # current_volume / avg_volume
    is_gainer = Column(Boolean, nullable=False, index=True)
    rank = Column(Integer)  # 1-20
    has_unusual_volume = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="top_movers")
    
    __table_args__ = (
        Index("idx_movers_date_gainer", "date", "is_gainer"),
        Index("idx_movers_date_rank", "date", "rank"),
    )


class PennyStockMomentum(Base):
    """Penny stock momentum tracking."""
    __tablename__ = "penny_stock_momentum"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    price = Column(Numeric(10, 4), nullable=False)
    price_change_pct = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    avg_volume = Column(BigInteger, nullable=False)
    volume_ratio = Column(Float, nullable=False)
    momentum_score = Column(Float, nullable=False)  # 0-100
    price_component = Column(Float)
    volume_component = Column(Float)
    trend_component = Column(Float)
    catalyst_component = Column(Float)
    catalyst = Column(String(500))
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_penny_momentum_date_rank", "date", "rank"),
        Index("idx_penny_momentum_score", "momentum_score"),
        CheckConstraint("price <= 5.0", name="check_penny_price"),
        CheckConstraint("momentum_score >= 0 AND momentum_score <= 100", name="check_momentum_range"),
        CheckConstraint("volume_ratio >= 1.0", name="check_volume_ratio"),
    )


class PennyStockRiskMetrics(Base):
    """Penny stock risk metrics."""
    __tablename__ = "penny_stock_risk_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    liquidity_risk = Column(Float, nullable=False)  # 0-1
    volatility_risk = Column(Float, nullable=False)  # 0-1
    spread_percentage = Column(Float, nullable=False)
    overall_risk = Column(SQLEnum(RiskLevel), nullable=False)
    suspicion_score = Column(Float)  # 0-1, pump-dump indicator
    suspicion_indicators = Column(JSONB)
    recommendation = Column(String(20))  # 'safe', 'caution', 'avoid'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_penny_risk_date_ticker", "date", "ticker"),
        Index("idx_penny_risk_level", "overall_risk"),
        CheckConstraint("liquidity_risk >= 0 AND liquidity_risk <= 1", name="check_liquidity_risk_range"),
        CheckConstraint("volatility_risk >= 0 AND volatility_risk <= 1", name="check_volatility_risk_range"),
        CheckConstraint("spread_percentage >= 0", name="check_spread_non_negative"),
    )


class Alert(Base):
    """User alerts."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)  # Will add user table later
    ticker = Column(String(10), nullable=False, index=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    threshold = Column(Float)
    is_triggered = Column(Boolean, default=False, index=True)
    triggered_at = Column(DateTime)
    message = Column(Text)
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_alerts_user_ticker", "user_id", "ticker"),
        Index("idx_alerts_triggered", "is_triggered"),
        Index("idx_alerts_priority", "priority"),
    )


class UserWatchlist(Base):
    """User watchlists."""
    __tablename__ = "user_watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    tickers = Column(JSONB, nullable=False)  # List of ticker symbols
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_watchlist_user", "user_id"),
    )


# Paper Trading Models

class PaperTradingAccountModel(Base):
    """Paper trading accounts."""
    __tablename__ = "paper_trading_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    initial_cash = Column(Numeric(15, 2), nullable=False)
    current_cash = Column(Numeric(15, 2), nullable=False)
    total_value = Column(Numeric(15, 2), nullable=False)
    slippage_pct = Column(Float, default=0.001)
    commission_per_share = Column(Numeric(10, 4), default=0)
    allow_margin = Column(Boolean, default=False)
    margin_multiplier = Column(Numeric(5, 2), default=1.0)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("PaperTradingOrder", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("PaperTradingPosition", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship("PaperTradingTransaction", back_populates="account", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_paper_account_user", "user_id"),
        Index("idx_paper_account_active", "is_active"),
    )


class OrderTypeEnum(str, enum.Enum):
    """Paper trading order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"


class OrderSideEnum(str, enum.Enum):
    """Paper trading order side."""
    BUY = "buy"
    SELL = "sell"


class OrderStatusEnum(str, enum.Enum):
    """Paper trading order status."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PaperTradingOrder(Base):
    """Paper trading orders."""
    __tablename__ = "paper_trading_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("paper_trading_accounts.id"), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    order_type = Column(SQLEnum(OrderTypeEnum), nullable=False)
    side = Column(SQLEnum(OrderSideEnum), nullable=False)
    quantity = Column(Integer, nullable=False)
    limit_price = Column(Numeric(10, 2))
    stop_price = Column(Numeric(10, 2))
    status = Column(SQLEnum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING, index=True)
    filled_price = Column(Numeric(10, 2))
    filled_quantity = Column(Integer, default=0)
    commission = Column(Numeric(10, 2), default=0)
    slippage = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    filled_at = Column(DateTime)
    
    # Relationships
    account = relationship("PaperTradingAccountModel", back_populates="orders")
    
    __table_args__ = (
        Index("idx_paper_order_account_status", "account_id", "status"),
        Index("idx_paper_order_ticker", "ticker"),
        CheckConstraint("quantity > 0", name="check_order_quantity_positive"),
    )


class PaperTradingPosition(Base):
    """Paper trading positions."""
    __tablename__ = "paper_trading_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("paper_trading_accounts.id"), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Numeric(10, 2), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=False)
    market_value = Column(Numeric(15, 2), nullable=False)
    unrealized_pnl = Column(Numeric(15, 2), nullable=False)
    unrealized_pnl_pct = Column(Float, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("PaperTradingAccountModel", back_populates="positions")
    
    __table_args__ = (
        Index("idx_paper_position_account_ticker", "account_id", "ticker", unique=True),
        CheckConstraint("quantity > 0", name="check_position_quantity_positive"),
    )


class TransactionTypeEnum(str, enum.Enum):
    """Paper trading transaction types."""
    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class PaperTradingTransaction(Base):
    """Paper trading transaction history."""
    __tablename__ = "paper_trading_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("paper_trading_accounts.id"), nullable=False)
    transaction_type = Column(SQLEnum(TransactionTypeEnum), nullable=False)
    ticker = Column(String(10), index=True)
    quantity = Column(Integer)
    price = Column(Numeric(10, 2))
    amount = Column(Numeric(15, 2), nullable=False)  # Cash amount (positive or negative)
    commission = Column(Numeric(10, 2), default=0)
    slippage = Column(Numeric(10, 2), default=0)
    balance_after = Column(Numeric(15, 2), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    account = relationship("PaperTradingAccountModel", back_populates="transactions")
    
    __table_args__ = (
        Index("idx_paper_transaction_account_date", "account_id", "created_at"),
        Index("idx_paper_transaction_ticker", "ticker"),
    )


class PaperTradingPerformance(Base):
    """Daily paper trading performance snapshots."""
    __tablename__ = "paper_trading_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("paper_trading_accounts.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    total_value = Column(Numeric(15, 2), nullable=False)
    cash = Column(Numeric(15, 2), nullable=False)
    portfolio_value = Column(Numeric(15, 2), nullable=False)
    daily_pnl = Column(Numeric(15, 2), nullable=False)
    daily_pnl_pct = Column(Float, nullable=False)
    total_return = Column(Numeric(15, 2), nullable=False)
    total_return_pct = Column(Float, nullable=False)
    realized_pnl = Column(Numeric(15, 2), default=0)
    unrealized_pnl = Column(Numeric(15, 2), default=0)
    num_positions = Column(Integer, default=0)
    num_trades = Column(Integer, default=0)
    benchmark_return_pct = Column(Float)  # e.g., SPY return
    alpha = Column(Float)  # Excess return vs benchmark
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_paper_performance_account_date", "account_id", "date", unique=True),
        Index("idx_paper_performance_date", "date"),
    )
