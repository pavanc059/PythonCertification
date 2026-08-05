"""
Pydantic schemas for the portfolio API endpoints.

Requirements: R2.1–R2.8, R7.3
"""

from typing import List, Optional

from pydantic import BaseModel


class BenchmarkComparison(BaseModel):
    benchmark_ticker: str = "SPY"
    benchmark_return_pct: Optional[float]
    portfolio_return_pct: float
    alpha: Optional[float]
    performance: str  # "outperforming" | "underperforming" | "matching"


class PortfolioSummaryResponse(BaseModel):
    # Account
    account_id: str
    cash: float
    portfolio_value: float
    total_value: float
    buying_power: float
    initial_cash: float = 100000.0

    # P&L
    total_return: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    day_pnl: float = 0.0

    # Performance metrics
    win_rate: float
    num_trades: int
    num_winning_trades: int
    num_losing_trades: int
    avg_win: float
    avg_loss: float

    # Benchmark
    benchmark: Optional[BenchmarkComparison]


class PositionDetail(BaseModel):
    ticker: str
    quantity: int
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    cost_basis: float
    day_change_pct: Optional[float] = None  # % change today (from yfinance)


class ClosedTradeRecord(BaseModel):
    ticker: str
    quantity: int
    avg_entry_price: float
    exit_price: float
    entry_time: str
    exit_time: str
    realized_pnl: float
    realized_pnl_pct: float


class EquitySnapshot(BaseModel):
    date: str
    total_value: float


class PortfolioHistoryResponse(BaseModel):
    closed_trades: List[ClosedTradeRecord]
    equity_snapshots: List[EquitySnapshot]
    total_realized_pnl: float
