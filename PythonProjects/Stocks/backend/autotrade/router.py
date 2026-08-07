"""
Auto-trade / backtest API router.

Endpoints
---------
GET  /autotrade/strategies       — list available strategies
POST /autotrade/backtest         — run a backtest over historical data

POST   /autotrade/bots           — create a new auto-trade bot
GET    /autotrade/bots           — list user's bots
GET    /autotrade/bots/{id}      — get bot details
PATCH  /autotrade/bots/{id}      — update bot config or toggle enabled
DELETE /autotrade/bots/{id}      — delete a bot
GET    /autotrade/bots/{id}/logs — get bot execution logs

All endpoints require a valid JWT Bearer token.

NOTE: Backtesting never places orders. Live auto-trading places paper orders
only — real-money execution is not implemented.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.models import User
from dependencies import get_current_user, get_db
from config import settings

from autotrade.schemas import (
    BacktestRequest,
    BacktestResponse,
    StrategyListResponse,
    CreateBotRequest,
    UpdateBotRequest,
    BotResponse,
    BotLogResponse,
)
from autotrade.strategies import get_strategy, list_strategies, Bar
from autotrade.risk import RiskConfig
from autotrade.backtest import Backtester
from autotrade.service import BotService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/strategies", response_model=StrategyListResponse)
async def get_strategies(current_user: User = Depends(get_current_user)):
    """List the available auto-trade strategies and their metadata."""
    return {"strategies": list_strategies()}


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    body: BacktestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Run a strategy backtest over historical OHLCV data for a ticker.

    Fetches history from yfinance, replays the chosen strategy bar-by-bar
    through the risk manager, and returns full performance metrics plus an
    equity curve. Never places orders.
    """
    ticker = body.ticker.upper().strip()

    # Validate strategy
    try:
        strategy = get_strategy(body.strategy)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Fetch historical data via yfinance
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        hist = t.history(period=body.period, interval=body.interval)
    except Exception as exc:
        logger.warning("yfinance history fetch failed for %s: %s", ticker, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch price history for {ticker}.",
        )

    if hist is None or hist.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical data found for '{ticker}'.",
        )

    # Convert to Bar objects
    bars: list[Bar] = []
    for ts, row in hist.iterrows():
        try:
            bars.append(Bar(
                timestamp=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            ))
        except (ValueError, KeyError, TypeError):
            continue

    if len(bars) < strategy.min_bars:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Not enough data: {len(bars)} bars, strategy needs "
                f"{strategy.min_bars}. Try a longer period."
            ),
        )

    # Build risk config and run
    risk_config = RiskConfig(
        position_size_pct=body.risk.position_size_pct,
        stop_loss_pct=body.risk.stop_loss_pct,
        take_profit_pct=body.risk.take_profit_pct,
        daily_loss_limit_pct=body.risk.daily_loss_limit_pct,
        max_positions=body.risk.max_positions,
        max_trades_per_day=body.risk.max_trades_per_day,
        min_confidence=body.risk.min_confidence,
    )

    backtester = Backtester(strategy, risk_config, initial_capital=body.initial_capital)
    result = backtester.run(ticker, bars)

    return result.__dict__


# ------------------------------------------------------------------
# Bot CRUD
# ------------------------------------------------------------------

@router.post("/bots", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(
    body: CreateBotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new auto-trade bot."""
    # Validate strategy
    try:
        get_strategy(body.strategy)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    service = BotService(db, current_user.id)
    risk_config = RiskConfig(
        position_size_pct=body.risk.position_size_pct,
        stop_loss_pct=body.risk.stop_loss_pct,
        take_profit_pct=body.risk.take_profit_pct,
        daily_loss_limit_pct=body.risk.daily_loss_limit_pct,
        max_positions=body.risk.max_positions,
        max_trades_per_day=body.risk.max_trades_per_day,
        min_confidence=body.risk.min_confidence,
    )
    bot = service.create_bot(
        name=body.name,
        ticker=body.ticker,
        strategy=body.strategy,
        risk=risk_config,
        enabled=body.enabled,
    )
    return _bot_to_dict(bot)


@router.get("/bots", response_model=list[BotResponse])
async def list_bots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all auto-trade bots for the current user."""
    service = BotService(db, current_user.id)
    bots = service.list_bots()
    return [_bot_to_dict(b) for b in bots]


@router.get("/bots/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details for a specific bot."""
    service = BotService(db, current_user.id)
    bot = service.get_bot(bot_id)
    return _bot_to_dict(bot)


@router.patch("/bots/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: UUID,
    body: UpdateBotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a bot's configuration or toggle enabled state."""
    service = BotService(db, current_user.id)

    # Validate strategy if provided
    if body.strategy is not None:
        try:
            get_strategy(body.strategy)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    risk_config = None
    if body.risk is not None:
        risk_config = RiskConfig(
            position_size_pct=body.risk.position_size_pct,
            stop_loss_pct=body.risk.stop_loss_pct,
            take_profit_pct=body.risk.take_profit_pct,
            daily_loss_limit_pct=body.risk.daily_loss_limit_pct,
            max_positions=body.risk.max_positions,
            max_trades_per_day=body.risk.max_trades_per_day,
            min_confidence=body.risk.min_confidence,
        )

    bot = service.update_bot(
        bot_id,
        name=body.name,
        ticker=body.ticker,
        strategy=body.strategy,
        enabled=body.enabled,
        risk=risk_config,
    )
    return _bot_to_dict(bot)


@router.delete("/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a bot and all its logs."""
    service = BotService(db, current_user.id)
    service.delete_bot(bot_id)


@router.get("/bots/{bot_id}/logs", response_model=list[BotLogResponse])
async def get_bot_logs(
    bot_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get execution logs for a bot (newest first)."""
    service = BotService(db, current_user.id)
    logs = service.get_logs(bot_id, limit=limit)
    return [
        {
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat(),
            "ticker": log.ticker,
            "price": log.price,
            "signal_type": log.signal_type,
            "signal_confidence": log.signal_confidence,
            "signal_reason": log.signal_reason,
            "action_taken": log.action_taken,
            "order_id": log.order_id,
            "details": log.details,
        }
        for log in logs
    ]


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _bot_to_dict(bot) -> dict:
    """Convert AutoTradeBotDB to dict for response."""
    return {
        "id": str(bot.id),
        "name": bot.name,
        "ticker": bot.ticker,
        "strategy": bot.strategy,
        "enabled": bot.enabled,
        "risk": {
            "position_size_pct": bot.position_size_pct,
            "stop_loss_pct": bot.stop_loss_pct,
            "take_profit_pct": bot.take_profit_pct,
            "daily_loss_limit_pct": bot.daily_loss_limit_pct,
            "max_positions": bot.max_positions,
            "max_trades_per_day": bot.max_trades_per_day,
            "min_confidence": bot.min_confidence,
        },
        "last_run_at": bot.last_run_at.isoformat() if bot.last_run_at else None,
        "last_signal": bot.last_signal,
        "last_error": bot.last_error,
        "total_trades": bot.total_trades,
        "winning_trades": bot.winning_trades,
        "total_pnl": bot.total_pnl,
        "created_at": bot.created_at.isoformat(),
        "updated_at": bot.updated_at.isoformat(),
    }
