"""Pydantic schemas for the AutoPilot API."""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class AutoPilotConfigUpdate(BaseModel):
    """Editable AutoPilot settings. All fields optional for partial updates."""
    enabled: Optional[bool] = None

    capital: Optional[float] = Field(None, gt=0)
    daily_profit_target: Optional[float] = Field(None, gt=0)
    daily_loss_limit: Optional[float] = Field(None, gt=0)

    max_concurrent_positions: Optional[int] = Field(None, ge=1, le=20)
    max_position_size_pct: Optional[float] = Field(None, gt=0, le=1)
    take_profit_pct: Optional[float] = Field(None, gt=0, le=1)
    stop_loss_pct: Optional[float] = Field(None, gt=0, le=1)

    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, gt=0)
    min_change_pct: Optional[float] = Field(None, ge=0)
    min_volume_ratio: Optional[float] = Field(None, ge=0)
    max_candidates: Optional[int] = Field(None, ge=1, le=100)

    use_llm: Optional[bool] = None
    llm_min_confidence: Optional[float] = Field(None, ge=0, le=100)

    force_flat_minutes_before_close: Optional[int] = Field(None, ge=0, le=120)
    data_provider: Optional[str] = None


class AutoPilotConfigResponse(BaseModel):
    id: str
    market_type: str
    enabled: bool

    capital: float
    daily_profit_target: float
    daily_loss_limit: float

    max_concurrent_positions: int
    max_position_size_pct: float
    take_profit_pct: float
    stop_loss_pct: float

    min_price: float
    max_price: float
    min_change_pct: float
    min_volume_ratio: float
    max_candidates: int

    use_llm: bool
    llm_min_confidence: float

    force_flat_minutes_before_close: int
    data_provider: Optional[str]

    # live state
    trading_day: Optional[str]
    realized_pnl_today: float
    trades_today: int
    target_hit: bool
    halted: bool
    status: str
    last_run_at: Optional[str]
    last_error: Optional[str]

    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Status (progress vs target)
# ---------------------------------------------------------------------------

class AutoPilotStatusResponse(BaseModel):
    market_type: str
    enabled: bool
    status: str
    capital: float
    daily_profit_target: float
    realized_pnl_today: float
    progress_pct: float          # realized / target * 100 (clamped 0–100+)
    target_hit: bool
    halted: bool
    trades_today: int
    open_positions: int
    last_run_at: Optional[str]


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class AutoPilotTradeResponse(BaseModel):
    id: str
    market_type: str
    ticker: str
    trading_day: str
    entry_time: str
    entry_price: float
    quantity: int
    stop_price: float
    take_profit_price: float
    momentum_score: Optional[float]
    llm_confidence: Optional[float]
    entry_reason: Optional[str]
    status: str
    exit_time: Optional[str]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    realized_pnl: Optional[float]
    realized_pnl_pct: Optional[float]


# ---------------------------------------------------------------------------
# Daily reports
# ---------------------------------------------------------------------------

class AutoPilotReportResponse(BaseModel):
    id: str
    market_type: str
    trading_day: str
    capital: float
    daily_profit_target: float
    realized_pnl: float
    target_met: bool
    return_pct: float
    num_trades: int
    num_winning: int
    num_losing: int
    win_rate: float
    best_trade_pnl: Optional[float]
    worst_trade_pnl: Optional[float]
    summary: Optional[str]


class ProvidersResponse(BaseModel):
    providers: List[str]
    active: str
