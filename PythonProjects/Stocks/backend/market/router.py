"""
Market data API router.

Endpoints
---------
GET  /market/quote/{ticker}                       — real-time quote (R3.2, R7.6)
GET  /market/chart/{ticker}?period=1d&interval=5m — OHLCV candlestick data (R3.9, R7.6)
GET  /market/predict/{ticker}                     — AI prediction with technical signals (R3.8, R7.6, R11.3)
GET  /market/movers                               — top gainers and losers (R4.1)
GET  /market/news                                 — paginated market news (R4.2)
GET  /market/news/{ticker}                        — ticker-specific news (R4.3, R11.1)
GET  /market/predictions                          — ensemble predictions (R4.4)
GET  /market/penny-stocks                         — penny stock momentum list (R5.11)
GET  /market/snapshot                             — market index snapshot (R10.5)
GET  /market/alerts                               — active alerts (R8.8)
DELETE /market/alerts/{id}                        — dismiss an alert (R8.9)
POST /market/alerts/read-all                      — mark all alerts read (R8.10)

All endpoints require a valid JWT Bearer token (R7.7).

Requirements: R3.2, R3.8, R3.9, R4.1–R4.8, R5.11, R7.6, R8.8–R8.10, R10.5, R11.1, R11.3
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth.models import User
from config import settings
from dependencies import get_current_user, get_db
from sqlalchemy.orm import Session
from market.schemas import (
    AlertItem,
    ChartResponse,
    EarningsResponse,
    EnsemblePrediction,
    InstitutionalResponse,
    MarketSnapshot,
    MoversResponse,
    NewsItem,
    PennyStockItem,
    PredictionResponse,
    QuoteResponse,
)
from market.service import MarketService, WebullMarketService
from state import get_webull_client

router = APIRouter()

# ---------------------------------------------------------------------------
# Valid parameter values
# ---------------------------------------------------------------------------

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "1y"}
VALID_INTERVALS = {"1m", "5m", "15m", "1h", "1d"}


# ---------------------------------------------------------------------------
# Dependency — shared MarketService instance per request
# ---------------------------------------------------------------------------


def get_market_service() -> WebullMarketService:
    """Provide a WebullMarketService instance configured for the active data source.

    - ``"webull"``: uses the WebullClient singleton stored in state.
    - ``"yfinance"``: uses WebullMarketService with no Webull client (yfinance fallback).
    - ``"stub"``: uses WebullMarketService with no Webull client (stub data).

    WebullMarketService supports all three modes, so it is always returned
    regardless of the configured source.

    Requirements: 13.1, 13.2, 13.3
    """
    source = settings.market_data_source

    if source == "webull":
        return WebullMarketService(
            redis_url=settings.redis_url,
            webull_client=get_webull_client(),
            data_source="webull",
        )
    elif source == "yfinance":
        return WebullMarketService(
            redis_url=settings.redis_url,
            webull_client=None,
            data_source="yfinance",
        )
    else:
        # "stub" or any unrecognised value
        return WebullMarketService(
            redis_url=settings.redis_url,
            webull_client=None,
            data_source="stub",
        )


# ---------------------------------------------------------------------------
# GET /market/quote/{ticker}
# ---------------------------------------------------------------------------


@router.get("/quote/{ticker}", response_model=QuoteResponse)
async def get_quote(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Fetch a real-time quote for the given ticker symbol.

    Returns price, dollar/percent change, volume, day range,
    52-week range, and market cap.  Results are cached in Redis
    for 30 seconds to reduce yfinance load.

    Raises:
        404 — Ticker not found or price unavailable.
    """
    return service.get_quote(ticker.upper())


# ---------------------------------------------------------------------------
# GET /market/chart/{ticker}
# ---------------------------------------------------------------------------


@router.get("/chart/{ticker}", response_model=ChartResponse)
async def get_chart(
    ticker: str,
    period: str = "1d",
    interval: str = "5m",
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Fetch OHLCV candlestick data for the given ticker.

    Valid ``period`` values: 1d, 5d, 1mo, 3mo, 1y.
    Valid ``interval`` values: 1m, 5m, 15m, 1h, 1d.

    Raises:
        400 — Invalid period or interval value.
        404 — No data returned for the ticker.
    """
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period '{period}'. Must be one of: {', '.join(sorted(VALID_PERIODS))}.",
        )
    if interval not in VALID_INTERVALS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid interval '{interval}'. Must be one of: {', '.join(sorted(VALID_INTERVALS))}.",
        )

    return service.get_chart(ticker.upper(), period=period, interval=interval)


# ---------------------------------------------------------------------------
# GET /market/predict/{ticker}
# ---------------------------------------------------------------------------


@router.get("/predict/{ticker}", response_model=PredictionResponse)
async def get_prediction(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Return an AI prediction (bullish/bearish/neutral) with technical signals for the given ticker.

    Uses RSI-14 computed from historical daily prices.  Also returns MACD signal
    and SMA-50 vs SMA-200 cross status (Requirements: R11.3).
    Never raises an HTTP error — falls back to neutral / 50% confidence on any failure.
    """
    return service.get_prediction(ticker.upper())


# ---------------------------------------------------------------------------
# GET /market/movers
# ---------------------------------------------------------------------------


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """Return top 10 gainers and top 10 losers (Requirements: R4.1)."""
    return service.get_movers()


# ---------------------------------------------------------------------------
# GET /market/news
# ---------------------------------------------------------------------------


@router.get("/news", response_model=List[NewsItem])
async def get_news(
    limit: int = Query(default=5, ge=1, le=20),
    offset: int = Query(default=0, ge=0),
    ticker: Optional[str] = Query(default=None),
    sentiment: Optional[str] = Query(default=None, pattern="^(positive|neutral|negative)$"),
    category: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Return paginated news articles with optional filters (Requirements: R4.2).

    Raises:
        404 — Unknown ticker supplied.
        422 — ``limit`` outside valid range.
    """
    return service.get_news(
        limit=limit,
        offset=offset,
        ticker=ticker,
        sentiment=sentiment,
        category=category,
    )


# ---------------------------------------------------------------------------
# GET /market/news/{ticker}
# Note: this route MUST be registered BEFORE /market/predictions to avoid
# FastAPI treating "predictions" as a ticker parameter.
# ---------------------------------------------------------------------------


@router.get("/news/{ticker}", response_model=List[NewsItem])
async def get_ticker_news(
    ticker: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Return up to ``limit`` news articles for a specific ticker (Requirements: R4.3, R11.1).

    Sources: Finnhub company news → AlphaVantage NEWS_SENTIMENT → stub fallback.
    Each article carries a sentiment_score in [-1, 1].

    Raises:
        422 — ``limit`` outside valid range.
    """
    return service.get_ticker_news(ticker.upper(), limit=limit)


# ---------------------------------------------------------------------------
# GET /market/earnings/{ticker}
# ---------------------------------------------------------------------------


@router.get("/earnings/{ticker}", response_model=EarningsResponse)
async def get_earnings(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Return upcoming earnings date, EPS estimate, and last 4 quarters of
    earnings history with surprise percentages for the given ticker.

    Data sourced from yfinance calendar and earnings_history.
    Cached for 4 hours — never raises; returns empty fields on failure.
    """
    return service.get_earnings(ticker.upper())


# ---------------------------------------------------------------------------
# GET /market/institutional/{ticker}
# ---------------------------------------------------------------------------


@router.get("/institutional/{ticker}", response_model=InstitutionalResponse)
async def get_institutional(
    ticker: str,
    limit: int = Query(default=10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Return top institutional and mutual-fund holders for a ticker.

    Data sourced from yfinance institutional_holders and mutualfund_holders.
    Sorted by USD market value descending.
    Cached for 24 hours — never raises; returns empty list on failure.
    """
    return service.get_institutional(ticker.upper(), limit=limit)


# ---------------------------------------------------------------------------
# GET /market/predictions
# ---------------------------------------------------------------------------


@router.get("/predictions", response_model=List[EnsemblePrediction])
async def get_predictions(
    tickers: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """
    Return ensemble ML predictions (Requirements: R4.4).

    ``tickers`` is a comma-separated list of up to 50 ticker symbols.
    """
    ticker_list: Optional[List[str]] = None
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:50]
    return service.get_predictions(ticker_list)


# ---------------------------------------------------------------------------
# GET /market/penny-stocks
# ---------------------------------------------------------------------------


@router.get("/penny-stocks", response_model=List[PennyStockItem])
async def get_penny_stocks(
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """Return sub-$5 momentum stocks sorted by momentum_score (Requirements: R5.11)."""
    return service.get_penny_stocks()


# ---------------------------------------------------------------------------
# GET /market/snapshot
# ---------------------------------------------------------------------------


@router.get("/snapshot", response_model=MarketSnapshot)
async def get_snapshot(
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """Return S&P 500, NASDAQ, and VIX snapshot (Requirements: R10.5)."""
    return service.get_snapshot()

# ---------------------------------------------------------------------------
# GET /market/alerts
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=List[AlertItem])
async def get_alerts(
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
    db: Session = Depends(get_db),
):
    """
    Return live market alerts generated from the user's watchlist (R8.8).

    Scans each watchlist ticker for: large price moves (>3%), volume surges
    (>2x avg), RSI extremes, and upcoming earnings. Results are cached 5 min.
    Dismissed alerts are persisted in Redis and excluded from the response.
    """
    return service.get_alerts(user_id=current_user.id, db=db)


# ---------------------------------------------------------------------------
# DELETE /market/alerts/{id}
# ---------------------------------------------------------------------------


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """Dismiss (hide) a specific alert for the current user (R8.9)."""
    service.dismiss_alert(alert_id, user_id=current_user.id)


# ---------------------------------------------------------------------------
# POST /market/alerts/read-all
# ---------------------------------------------------------------------------


@router.post("/alerts/read-all", status_code=status.HTTP_200_OK)
async def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    service: WebullMarketService = Depends(get_market_service),
):
    """Mark all alerts as read (busts the live alerts cache) (R8.10)."""
    service.mark_all_alerts_read(user_id=current_user.id)
    return {"detail": "All alerts marked as read."}
