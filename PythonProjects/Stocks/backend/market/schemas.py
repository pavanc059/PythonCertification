"""
Pydantic v2 request/response schemas for the market data endpoints.

Requirements: R3.2, R3.8, R3.9, R7.6
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Quote response
# ---------------------------------------------------------------------------


class QuoteResponse(BaseModel):
    """Real-time quote data for a single ticker (R3.2)."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    company_name: Optional[str] = None
    price: float
    change: float           # $ change
    change_pct: float       # % change
    volume: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    sector: Optional[str] = None


# ---------------------------------------------------------------------------
# Chart response
# ---------------------------------------------------------------------------


class CandleData(BaseModel):
    """A single OHLCV candle (R3.9)."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: str          # ISO datetime string (matches frontend OHLCV type)
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartResponse(BaseModel):
    """OHLCV candlestick data for a ticker over a given period/interval (R3.9)."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    period: str
    interval: str
    data: List[CandleData]  # matches frontend ChartData.data


# ---------------------------------------------------------------------------
# Prediction response
# ---------------------------------------------------------------------------


class PredictionFactor(BaseModel):
    """A named factor contributing to the AI prediction (R3.8)."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    value: float


class PredictionResponse(BaseModel):
    """AI prediction result for a ticker (R3.8)."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    direction: str          # "bullish" | "bearish" | "neutral"
    confidence: float       # 0–100
    factors: dict           # {factor_name: value} — matches frontend Record<string, number>
    # Technical signals (Requirements: 11.3)
    rsi_14: Optional[float] = None          # RSI-14 value (0–100)
    macd_signal: Optional[str] = None       # "bullish" | "bearish" | "neutral"
    sma_cross: Optional[str] = None         # "golden_cross" | "death_cross" | "neutral"


# ---------------------------------------------------------------------------
# Top Movers
# ---------------------------------------------------------------------------


class TopMover(BaseModel):
    """A single top-gaining or top-losing stock (Requirements: 4.1, 10.5)."""

    ticker: str
    name: str
    price_change_pct: float
    current_price: float
    volume: int
    avg_volume: int
    sector: str
    has_unusual_volume: bool


class MoversResponse(BaseModel):
    """Top gainers and losers response (Requirements: 4.1, 10.5)."""

    gainers: List[TopMover]
    losers: List[TopMover]


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------


class NewsItem(BaseModel):
    """A single news article with sentiment metadata (Requirements: 4.2)."""

    id: str
    title: str
    source: str
    published_at: str       # ISO 8601
    sentiment_score: float  # [-1, 1]
    category: str
    is_breaking: bool
    summary: str
    tickers: List[str]
    url: str


# ---------------------------------------------------------------------------
# Ensemble Predictions
# ---------------------------------------------------------------------------


class EnsemblePrediction(BaseModel):
    """Ensemble ML prediction for a ticker (Requirements: 4.3)."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    ticker: str
    category: str           # 'Strong Buy'|'Buy'|'Hold'|'Sell'|'Strong Sell'
    confidence: float       # [0, 1]
    expected_return: float  # decimal, e.g. 0.035 = +3.5%
    lower_bound: float
    upper_bound: float
    is_low_confidence: bool
    # Enriched fields added by the live prediction engine
    reason: Optional[str] = None          # LLM or technical summary sentence
    rsi_14: Optional[float] = None        # RSI-14 value
    macd_histogram: Optional[float] = None
    sma_cross: Optional[str] = None       # 'golden_cross'|'death_cross'|'neutral'
    momentum_30d: Optional[float] = None  # % price change over 30 days
    computed_at: Optional[str] = None     # ISO datetime of last compute


# ---------------------------------------------------------------------------
# Penny Stocks
# ---------------------------------------------------------------------------


class PennyStockItem(BaseModel):
    """A single penny stock with momentum and risk metrics (Requirements: 5.11)."""

    ticker: str
    price: float
    price_change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float
    momentum_score: float   # [0, 100]
    risk_level: str         # 'low'|'medium'|'high'|'extreme'
    sector: str
    catalyst: str
    suspicion_score: float  # [0, 1]
    recommendation: str
    insider_net: float
    insider_buys: int
    insider_sells: int


# ---------------------------------------------------------------------------
# Market Snapshot
# ---------------------------------------------------------------------------


class MarketSnapshot(BaseModel):
    """High-level market index snapshot (Requirements: 10.5)."""

    sp500_change_pct: float
    nasdaq_change_pct: float
    vix: float


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertItem(BaseModel):
    """A single market alert (Requirements: 8.8)."""

    id: str
    ticker: str
    alert_type: str
    message: str
    severity: str           # 'info'|'warning'|'critical'
    timestamp: str          # ISO 8601
    is_read: bool


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------


class EarningsHistoryItem(BaseModel):
    """A single historical earnings result."""
    quarter: str            # e.g. "2025 Q1"
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    surprise_pct: Optional[float] = None


class EarningsResponse(BaseModel):
    """Upcoming earnings date and history for a ticker."""
    ticker: str
    next_earnings_date: Optional[str] = None   # ISO date string
    next_earnings_time: Optional[str] = None   # "BMO" | "AMC" | "TNS"
    eps_estimate: Optional[float] = None
    history: List[EarningsHistoryItem] = []


# ---------------------------------------------------------------------------
# Institutional holders
# ---------------------------------------------------------------------------


class InstitutionalHolder(BaseModel):
    """A single institutional holder row."""
    holder: str
    shares: Optional[int] = None
    pct_held: Optional[float] = None       # 0–100
    value: Optional[float] = None          # USD market value
    date_reported: Optional[str] = None    # ISO date


class InstitutionalResponse(BaseModel):
    """Top institutional holders for a ticker."""
    ticker: str
    holders: List[InstitutionalHolder] = []
