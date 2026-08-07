"""Pydantic schemas for the auto-trade / backtest API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class RiskParams(BaseModel):
    position_size_pct: float = Field(default=0.10, gt=0, le=1)
    stop_loss_pct: float = Field(default=0.02, gt=0, lt=1)
    take_profit_pct: float = Field(default=0.04, gt=0, lt=5)
    daily_loss_limit_pct: float = Field(default=0.03, gt=0, lt=1)
    max_positions: int = Field(default=5, ge=1, le=50)
    max_trades_per_day: int = Field(default=10, ge=1, le=200)
    min_confidence: float = Field(default=55.0, ge=0, le=100)


class BacktestRequest(BaseModel):
    ticker: str
    strategy: str = "momentum"          # momentum | mean_reversion | ma_crossover
    period: str = "1y"                  # yfinance period
    interval: str = "1d"                # yfinance interval
    initial_capital: float = Field(default=100_000.0, gt=0)
    risk: RiskParams = RiskParams()


class TradeRecord(BaseModel):
    ticker: str
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    quantity: int
    realized_pnl: float
    realized_pnl_pct: float
    exit_reason: str


class EquityPoint(BaseModel):
    date: str
    equity: float


class BacktestResponse(BaseModel):
    ticker: str
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return: float
    total_return_pct: float
    num_trades: int
    num_winning: int
    num_losing: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    trades: List[TradeRecord]
    equity_curve: List[EquityPoint]


class StrategyInfo(BaseModel):
    name: str
    display_name: str
    min_bars: int


class StrategyListResponse(BaseModel):
    strategies: List[StrategyInfo]


# ------------------------------------------------------------------
# Bot CRUD schemas
# ------------------------------------------------------------------

class CreateBotRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    ticker: str
    strategy: str
    risk: RiskParams = RiskParams()
    enabled: bool = True


class UpdateBotRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    ticker: Optional[str] = None
    strategy: Optional[str] = None
    risk: Optional[RiskParams] = None
    enabled: Optional[bool] = None


class BotResponse(BaseModel):
    id: str
    name: str
    ticker: str
    strategy: str
    enabled: bool
    risk: RiskParams
    last_run_at: Optional[str]
    last_signal: Optional[str]
    last_error: Optional[str]
    total_trades: int
    winning_trades: int
    total_pnl: float
    created_at: str
    updated_at: str


class BotLogResponse(BaseModel):
    id: str
    timestamp: str
    ticker: str
    price: Optional[float]
    signal_type: str
    signal_confidence: Optional[float]
    signal_reason: Optional[str]
    action_taken: str
    order_id: Optional[str]
    details: Optional[str]
