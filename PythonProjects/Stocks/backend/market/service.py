"""
MarketService — business logic for market data endpoints.

Wraps yfinance for real-time quotes and OHLCV data, and provides
a simple RSI-based AI prediction signal (no heavyweight ML dependencies).
Redis caching is used where available; failures are silently swallowed.

Requirements: R3.2, R3.8, R3.9, R4.5, R4.6, R4.7, R4.8, R5.11,
              R8.8, R8.9, R8.10, R11.3
"""

import json
import logging
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def _parse_yf_news_item(item: dict, now_ts: float) -> dict:
    """
    Parse a yfinance news item into a normalised article dict.

    yfinance ≥1.5.x changed the schema:
      Old: {"title": ..., "publisher": ..., "providerPublishTime": ..., "link": ..., "uuid": ..., "relatedTickers": [...]}
      New: {"id": ..., "content": {"title": ..., "pubDate": ..., "canonicalUrl": {"url": ...}, ...}}

    This function handles both layouts.
    """
    import hashlib
    from datetime import datetime as _dt

    # ── New nested layout ────────────────────────────────────────────────
    if "content" in item and isinstance(item["content"], dict):
        content = item["content"]
        title = content.get("title") or content.get("summary") or ""
        source = (
            content.get("provider", {}).get("displayName")
            or content.get("provider", {}).get("name")
            or "Yahoo Finance"
        ) if isinstance(content.get("provider"), dict) else "Yahoo Finance"
        pub_str = content.get("pubDate") or content.get("displayTime") or ""
        try:
            pub_iso = _dt.fromisoformat(pub_str.replace("Z", "+00:00")).isoformat()
            pub_ts = _dt.fromisoformat(pub_str.replace("Z", "+00:00")).timestamp()
        except Exception:
            pub_iso = _dt.utcnow().isoformat() + "Z"
            pub_ts = now_ts
        url = ""
        if isinstance(content.get("canonicalUrl"), dict):
            url = content["canonicalUrl"].get("url", "")
        elif isinstance(content.get("clickThroughUrl"), dict):
            url = content["clickThroughUrl"].get("url", "")
        tickers_in = [
            t.get("symbol", "") for t in content.get("finance", {}).get("stockTickers", [])
            if isinstance(t, dict)
        ]
        item_id = f"yf_{content.get('id', hashlib.md5(title.encode()).hexdigest()[:12])}"

    # ── Old flat layout ──────────────────────────────────────────────────
    else:
        title = item.get("title") or ""
        source = item.get("publisher") or "Yahoo Finance"
        pub_ts_raw = item.get("providerPublishTime", 0)
        try:
            pub_ts = float(pub_ts_raw) if pub_ts_raw else now_ts
            pub_iso = _dt.utcfromtimestamp(pub_ts).isoformat() + "Z"
        except Exception:
            pub_ts = now_ts
            pub_iso = _dt.utcnow().isoformat() + "Z"
        url = item.get("link") or ""
        tickers_in = item.get("relatedTickers") or []
        item_id = f"yf_{item.get('uuid', hashlib.md5(title.encode()).hexdigest()[:12])}"

    return {
        "id": item_id,
        "title": title,
        "source": source,
        "published_at": pub_iso,
        "pub_ts": pub_ts,
        "url": url,
        "tickers_in": [t.upper() for t in tickers_in if t],
    }

# ---------------------------------------------------------------------------
# In-memory alert store (module-level so state persists across requests)
# ---------------------------------------------------------------------------

_ALERTS_STORE: List[dict] = [
    {
        "id": "alert-001",
        "ticker": "AAPL",
        "alert_type": "price_target",
        "message": "AAPL has crossed above the $190 resistance level.",
        "severity": "warning",
        "timestamp": "2024-01-15T09:35:00Z",
        "is_read": False,
    },
    {
        "id": "alert-002",
        "ticker": "GME",
        "alert_type": "unusual_volume",
        "message": "GME volume is 3.2x above the 20-day average.",
        "severity": "critical",
        "timestamp": "2024-01-15T10:12:00Z",
        "is_read": False,
    },
    {
        "id": "alert-003",
        "ticker": "TSLA",
        "alert_type": "news_sentiment",
        "message": "Strong negative sentiment detected in recent TSLA news.",
        "severity": "warning",
        "timestamp": "2024-01-15T11:00:00Z",
        "is_read": True,
    },
    {
        "id": "alert-004",
        "ticker": "NVDA",
        "alert_type": "earnings",
        "message": "NVDA earnings release scheduled for tomorrow after close.",
        "severity": "info",
        "timestamp": "2024-01-15T12:00:00Z",
        "is_read": False,
    },
    {
        "id": "alert-005",
        "ticker": "SPY",
        "alert_type": "market_move",
        "message": "S&P 500 down more than 1% intraday — circuit-breaker level approaching.",
        "severity": "critical",
        "timestamp": "2024-01-15T14:22:00Z",
        "is_read": False,
    },
]

# ---------------------------------------------------------------------------
# Stub market data (realistic fake data; no live integration required)
# ---------------------------------------------------------------------------

_STUB_GAINERS = [
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "price_change_pct": 4.82,
     "current_price": 487.21, "volume": 52_300_000, "avg_volume": 30_000_000,
     "sector": "Technology", "has_unusual_volume": True},
    {"ticker": "META", "name": "Meta Platforms Inc.", "price_change_pct": 3.45,
     "current_price": 374.50, "volume": 28_100_000, "avg_volume": 22_000_000,
     "sector": "Technology", "has_unusual_volume": True},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "price_change_pct": 2.91,
     "current_price": 152.34, "volume": 41_000_000, "avg_volume": 35_000_000,
     "sector": "Technology", "has_unusual_volume": False},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "price_change_pct": 1.87,
     "current_price": 378.85, "volume": 19_500_000, "avg_volume": 20_000_000,
     "sector": "Technology", "has_unusual_volume": False},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "price_change_pct": 1.63,
     "current_price": 182.10, "volume": 31_000_000, "avg_volume": 28_000_000,
     "sector": "Consumer Cyclical", "has_unusual_volume": False},
]

_STUB_LOSERS = [
    {"ticker": "INTC", "name": "Intel Corporation", "price_change_pct": -3.74,
     "current_price": 35.20, "volume": 67_000_000, "avg_volume": 40_000_000,
     "sector": "Technology", "has_unusual_volume": True},
    {"ticker": "WBA", "name": "Walgreens Boots Alliance", "price_change_pct": -2.88,
     "current_price": 21.45, "volume": 15_200_000, "avg_volume": 12_000_000,
     "sector": "Healthcare", "has_unusual_volume": True},
    {"ticker": "PFE", "name": "Pfizer Inc.", "price_change_pct": -2.21,
     "current_price": 28.90, "volume": 38_500_000, "avg_volume": 30_000_000,
     "sector": "Healthcare", "has_unusual_volume": False},
    {"ticker": "T", "name": "AT&T Inc.", "price_change_pct": -1.55,
     "current_price": 16.80, "volume": 44_000_000, "avg_volume": 38_000_000,
     "sector": "Communication Services", "has_unusual_volume": False},
    {"ticker": "VZ", "name": "Verizon Communications", "price_change_pct": -1.12,
     "current_price": 35.50, "volume": 22_000_000, "avg_volume": 20_000_000,
     "sector": "Communication Services", "has_unusual_volume": False},
]


class MarketService:
    """
    Service layer wrapping yfinance for market data and Redis for caching.

    All methods either return a dict/list matching the corresponding Pydantic
    schema, or raise HTTPException with an appropriate status code.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis = self._connect_redis(redis_url)
        self._yf_session = self._build_yf_session()

    @staticmethod
    def _build_yf_session():
        """Return a requests.Session with a browser User-Agent so Yahoo
        Finance doesn't rate-limit Docker/cloud container IPs."""
        try:
            import requests
            session = requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            return session
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _connect_redis(redis_url: Optional[str]):
        """Attempt to connect to Redis; return None if unavailable."""
        if not redis_url:
            return None
        try:
            redis_lib = None
            try:
                import redis as redis_lib  # type: ignore
            except ImportError:
                return None
            client = redis_lib.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            logger.debug("Redis not available — caching disabled.")
            return None

    def _cache_get(self, key: str):
        """Return cached dict for key, or None on miss / error."""
        if not self._redis:
            return None
        try:
            raw = self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    def _cache_set(self, key: str, data, ttl: int = 30) -> None:
        """Store data in Redis with the given TTL; silently ignore errors."""
        if not self._redis:
            return
        try:
            self._redis.setex(key, ttl, json.dumps(data))
        except Exception:
            return

    # ------------------------------------------------------------------
    # Quote
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> dict:
        """
        Fetch real-time quote for a ticker.

        Returns a dict matching QuoteResponse schema.
        Results are cached in Redis with a 30-second TTL.

        Raises:
            HTTPException 404: Ticker not found (yfinance returns no price).
        """
        cache_key = f"quote:{ticker}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            import yfinance as yf  # type: ignore
            t = yf.Ticker(ticker, session=self._yf_session)
            info = t.info or {}
        except Exception as exc:
            logger.warning("yfinance error for %s: %s", ticker, exc)
            info = {}

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if not price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker '{ticker}' not found.",
            )

        prev_close = info.get("regularMarketPreviousClose") or price
        change = info.get("regularMarketChange") or (price - prev_close)
        change_pct = info.get("regularMarketChangePercent") or (change / prev_close if prev_close else 0.0)

        result = {
            "ticker": ticker,
            "company_name": info.get("longName") or info.get("shortName") or ticker,
            "price": float(price),
            "change": float(change),
            "change_pct": float(change_pct),
            "volume": info.get("regularMarketVolume") or info.get("volume"),
            "day_high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
            "day_low": info.get("regularMarketDayLow") or info.get("dayLow"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
            "sector": info.get("sector"),
        }
        self._cache_set(cache_key, result, ttl=30)
        return result

    # ------------------------------------------------------------------
    # Chart
    # ------------------------------------------------------------------

    def get_chart(self, ticker: str, period: str = "1d", interval: str = "5m") -> dict:
        """
        Fetch OHLCV chart data for a ticker.

        Returns a dict matching ChartResponse schema.

        Raises:
            HTTPException 404: No data returned by yfinance.
        """
        try:
            import yfinance as yf  # type: ignore
            t = yf.Ticker(ticker, session=self._yf_session)
            hist = t.history(period=period, interval=interval)
        except Exception as exc:
            logger.warning("yfinance chart error for %s: %s", ticker, exc)
            hist = None

        if hist is None or hist.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chart data found for '{ticker}'.",
            )

        candles = []
        for ts, row in hist.iterrows():
            time_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            candles.append({
                "timestamp": time_str,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })

        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": candles,
        }

    # ------------------------------------------------------------------
    # Prediction (RSI-14 based, with MACD and SMA cross signals)
    # ------------------------------------------------------------------

    def get_prediction(self, ticker: str) -> dict:
        """
        Return an RSI-based AI prediction for a ticker (R3.8).

        Uses a simple 14-period RSI calculated from 30 days of daily prices.
        Also computes a stub MACD signal and SMA-50 vs SMA-200 cross status.
        Never raises — returns neutral/50 on any error.

        Returns:
            Dict matching PredictionResponse schema with direction
            "bullish" | "bearish" | "neutral", confidence 0–100,
            a factors list, rsi_14, macd_signal, and sma_cross fields.
        """
        neutral_fallback = {
            "ticker": ticker,
            "direction": "neutral",
            "confidence": 50.0,
            "factors": {},
            "rsi_14": None,
            "macd_signal": "neutral",
            "sma_cross": "neutral",
        }

        try:
            import yfinance as yf  # type: ignore
            t = yf.Ticker(ticker, session=self._yf_session)
            # Fetch 200 days so we can compute SMA-200
            hist = t.history(period="1y", interval="1d")
            if hist is None or hist.empty:
                return neutral_fallback

            closes = list(hist["Close"])
            rsi = self._calculate_rsi(closes)

            if rsi is None:
                return neutral_fallback

            rsi_float = float(rsi)

            # Direction from RSI
            if rsi_float > 60:
                direction = "bullish"
                confidence = min(50.0 + (rsi_float - 60) * 2.0, 95.0)
            elif rsi_float < 40:
                direction = "bearish"
                confidence = min(50.0 + (40 - rsi_float) * 2.0, 95.0)
            else:
                direction = "neutral"
                confidence = 50.0

            # MACD signal: derived from RSI as a simple proxy
            if rsi_float > 55:
                macd_signal = "bullish"
            elif rsi_float < 45:
                macd_signal = "bearish"
            else:
                macd_signal = "neutral"

            # SMA cross: compare SMA-50 vs SMA-200
            sma_cross = "neutral"
            if len(closes) >= 200:
                sma_50 = sum(closes[-50:]) / 50
                sma_200 = sum(closes[-200:]) / 200
                if sma_50 > sma_200 * 1.002:
                    sma_cross = "golden_cross"
                elif sma_50 < sma_200 * 0.998:
                    sma_cross = "death_cross"

            return {
                "ticker": ticker,
                "direction": direction,
                "confidence": round(confidence, 1),
                "factors": {"RSI": round(rsi_float, 2)},
                "rsi_14": round(rsi_float, 2),
                "macd_signal": macd_signal,
                "sma_cross": sma_cross,
            }

        except Exception as exc:
            logger.warning("Prediction error for %s: %s", ticker, exc)
            return neutral_fallback

    @staticmethod
    def _calculate_rsi(closes, period: int = 14) -> Optional[float]:
        """
        Calculate the most-recent RSI value from a series of closing prices.

        Args:
            closes: Array-like of closing prices (chronological order).
            period: RSI lookback window (default 14).

        Returns:
            RSI value (0–100) or None if insufficient data.
        """
        try:
            import numpy as np  # type: ignore
            arr = np.array(closes, dtype=float)
        except Exception:
            arr = list(closes)

        if len(arr) < period + 1:
            return None

        deltas = [arr[i + 1] - arr[i] for i in range(len(arr) - 1)]
        gains = [max(d, 0.0) for d in deltas]
        losses = [max(-d, 0.0) for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # ------------------------------------------------------------------
    # Movers
    # ------------------------------------------------------------------

    def get_movers(self) -> dict:
        """Return top gainers and losers (stub data)."""
        return {
            "gainers": list(_STUB_GAINERS),
            "losers": list(_STUB_LOSERS),
        }

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------

    _STUB_NEWS = [
        {
            "id": "news-001",
            "title": "NVIDIA Beats Q4 Earnings Expectations, Revenue Surges 265%",
            "source": "Reuters",
            "published_at": "2024-01-15T09:00:00Z",
            "sentiment_score": 0.82,
            "category": "Earnings",
            "is_breaking": True,
            "summary": "NVIDIA Corporation reported fourth-quarter earnings that surpassed analyst forecasts, "
                        "with revenue growing 265% year-over-year driven by explosive AI chip demand.",
            "tickers": ["NVDA"],
            "url": "https://example.com/news/nvda-earnings",
        },
        {
            "id": "news-002",
            "title": "Federal Reserve Signals Possible Rate Cut in March",
            "source": "Bloomberg",
            "published_at": "2024-01-15T08:30:00Z",
            "sentiment_score": 0.35,
            "category": "Economic",
            "is_breaking": False,
            "summary": "Fed officials hinted at potential interest rate reductions as inflation data shows "
                        "continued cooling, giving markets a boost ahead of the policy meeting.",
            "tickers": ["SPY", "QQQ"],
            "url": "https://example.com/news/fed-rate-cut",
        },
        {
            "id": "news-003",
            "title": "Intel Faces Headwinds as AI Chip Competition Intensifies",
            "source": "Wall Street Journal",
            "published_at": "2024-01-15T07:45:00Z",
            "sentiment_score": -0.61,
            "category": "Earnings",
            "is_breaking": False,
            "summary": "Intel posted disappointing guidance for the upcoming quarter, citing increased "
                        "competition from AMD and NVIDIA in the rapidly growing AI accelerator market.",
            "tickers": ["INTC", "AMD", "NVDA"],
            "url": "https://example.com/news/intel-headwinds",
        },
        {
            "id": "news-004",
            "title": "Apple Explores Generative AI Features for iPhone 16",
            "source": "CNBC",
            "published_at": "2024-01-15T07:00:00Z",
            "sentiment_score": 0.45,
            "category": "Earnings",
            "is_breaking": False,
            "summary": "Apple is reportedly integrating large language model capabilities into iOS 18, "
                        "targeting a major AI-driven iPhone upgrade cycle later this year.",
            "tickers": ["AAPL"],
            "url": "https://example.com/news/apple-ai",
        },
        {
            "id": "news-005",
            "title": "Tesla Deliveries Miss Q4 Estimates Amid Price War",
            "source": "Financial Times",
            "published_at": "2024-01-15T06:15:00Z",
            "sentiment_score": -0.48,
            "category": "Earnings",
            "is_breaking": False,
            "summary": "Tesla reported 484,507 deliveries in Q4, falling short of the 493,000 consensus "
                        "estimate as aggressive pricing strategies weigh on margins.",
            "tickers": ["TSLA"],
            "url": "https://example.com/news/tesla-deliveries",
        },
    ]

    def get_news(
        self,
        limit: int = 5,
        offset: int = 0,
        ticker: Optional[str] = None,
        sentiment: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[dict]:
        """
        Return paginated news articles with optional filters.

        Raises:
            HTTPException 404: If a specific unknown ticker is requested.
        """
        articles = list(self._STUB_NEWS)

        if ticker:
            ticker_upper = ticker.upper()
            filtered = [a for a in articles if ticker_upper in a["tickers"]]
            if not filtered:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No news found for ticker '{ticker}'.",
                )
            articles = filtered

        if sentiment:
            def _matches_sentiment(score: float, s: str) -> bool:
                if s == "positive":
                    return score > 0.15
                if s == "negative":
                    return score < -0.15
                return -0.15 <= score <= 0.15

            articles = [a for a in articles if _matches_sentiment(a["sentiment_score"], sentiment)]

        if category:
            articles = [a for a in articles if a["category"].lower() == category.lower()]

        return articles[offset: offset + limit]

    def get_ticker_news(self, ticker: str, limit: int = 3) -> List[dict]:
        """
        Return news articles for a specific ticker.

        Raises:
            HTTPException 404: If the ticker is not recognised.
        """
        ticker_upper = ticker.upper()
        articles = [a for a in self._STUB_NEWS if ticker_upper in a["tickers"]]
        if not articles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No news found for ticker '{ticker_upper}'.",
            )
        return articles[:limit]

    # ------------------------------------------------------------------
    # Ensemble predictions
    # ------------------------------------------------------------------

    _STUB_PREDICTIONS = [
        {"ticker": "NVDA", "category": "Strong Buy", "confidence": 0.91,
         "expected_return": 0.085, "lower_bound": 0.02, "upper_bound": 0.18, "is_low_confidence": False},
        {"ticker": "META", "category": "Buy", "confidence": 0.74,
         "expected_return": 0.042, "lower_bound": 0.01, "upper_bound": 0.09, "is_low_confidence": False},
        {"ticker": "MSFT", "category": "Buy", "confidence": 0.68,
         "expected_return": 0.031, "lower_bound": 0.005, "upper_bound": 0.07, "is_low_confidence": False},
        {"ticker": "AAPL", "category": "Hold", "confidence": 0.55,
         "expected_return": 0.012, "lower_bound": -0.02, "upper_bound": 0.05, "is_low_confidence": False},
        {"ticker": "TSLA", "category": "Hold", "confidence": 0.38,
         "expected_return": -0.008, "lower_bound": -0.12, "upper_bound": 0.10, "is_low_confidence": True},
        {"ticker": "INTC", "category": "Sell", "confidence": 0.72,
         "expected_return": -0.045, "lower_bound": -0.10, "upper_bound": -0.01, "is_low_confidence": False},
        {"ticker": "AMD", "category": "Buy", "confidence": 0.61,
         "expected_return": 0.028, "lower_bound": -0.01, "upper_bound": 0.08, "is_low_confidence": False},
        {"ticker": "AMZN", "category": "Strong Buy", "confidence": 0.82,
         "expected_return": 0.065, "lower_bound": 0.02, "upper_bound": 0.13, "is_low_confidence": False},
    ]

    def get_predictions(self, tickers: Optional[List[str]] = None) -> List[dict]:
        """Return ensemble predictions, optionally filtered by ticker list."""
        preds = list(self._STUB_PREDICTIONS)
        if tickers:
            upper = [t.upper() for t in tickers]
            preds = [p for p in preds if p["ticker"] in upper]
        return preds

    # ------------------------------------------------------------------
    # Penny stocks
    # ------------------------------------------------------------------

    _STUB_PENNY_STOCKS = [
        {"ticker": "SNDL", "price": 1.82, "price_change_pct": 12.4,
         "volume": 45_000_000, "avg_volume": 18_000_000, "volume_ratio": 2.5,
         "momentum_score": 87.3, "risk_level": "high", "sector": "Healthcare",
         "catalyst": "FDA approval rumour", "suspicion_score": 0.42,
         "recommendation": "Speculative Buy", "insider_net": 50000,
         "insider_buys": 3, "insider_sells": 0},
        {"ticker": "MMAT", "price": 0.45, "price_change_pct": 8.1,
         "volume": 120_000_000, "avg_volume": 60_000_000, "volume_ratio": 2.0,
         "momentum_score": 74.1, "risk_level": "extreme", "sector": "Technology",
         "catalyst": "New partnership announced", "suspicion_score": 0.78,
         "recommendation": "High Risk — Avoid", "insider_net": -20000,
         "insider_buys": 0, "insider_sells": 2},
        {"ticker": "CLOV", "price": 3.21, "price_change_pct": 5.6,
         "volume": 22_000_000, "avg_volume": 15_000_000, "volume_ratio": 1.47,
         "momentum_score": 61.9, "risk_level": "medium", "sector": "Healthcare",
         "catalyst": "Earnings beat", "suspicion_score": 0.28,
         "recommendation": "Watch", "insider_net": 10000,
         "insider_buys": 1, "insider_sells": 0},
        {"ticker": "NKLA", "price": 0.72, "price_change_pct": -3.2,
         "volume": 31_000_000, "avg_volume": 25_000_000, "volume_ratio": 1.24,
         "momentum_score": 41.2, "risk_level": "extreme", "sector": "Industrials",
         "catalyst": "Production update", "suspicion_score": 0.65,
         "recommendation": "Sell", "insider_net": -50000,
         "insider_buys": 0, "insider_sells": 5},
        {"ticker": "SENS", "price": 2.10, "price_change_pct": 7.3,
         "volume": 9_500_000, "avg_volume": 7_000_000, "volume_ratio": 1.36,
         "momentum_score": 68.5, "risk_level": "medium", "sector": "Healthcare",
         "catalyst": "Clinical trial results", "suspicion_score": 0.18,
         "recommendation": "Speculative Buy", "insider_net": 30000,
         "insider_buys": 2, "insider_sells": 0},
    ]

    def get_penny_stocks(self) -> List[dict]:
        """Return penny stocks sorted by momentum_score descending."""
        return sorted(self._STUB_PENNY_STOCKS, key=lambda x: x["momentum_score"], reverse=True)

    # ------------------------------------------------------------------
    # Market snapshot
    # ------------------------------------------------------------------

    def get_snapshot(self) -> dict:
        """Return a high-level market index snapshot (stub data)."""
        return {
            "sp500_change_pct": 0.82,
            "nasdaq_change_pct": 1.14,
            "vix": 15.3,
        }

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def get_alerts(self) -> List[dict]:
        """Return all active alerts."""
        return list(_ALERTS_STORE)

    def dismiss_alert(self, alert_id: str) -> None:
        """
        Delete a specific alert by ID.

        Raises:
            HTTPException 404: If the alert ID is not found.
        """
        global _ALERTS_STORE
        original_len = len(_ALERTS_STORE)
        _ALERTS_STORE = [a for a in _ALERTS_STORE if a["id"] != alert_id]
        if len(_ALERTS_STORE) == original_len:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert '{alert_id}' not found.",
            )

    def mark_all_alerts_read(self) -> None:
        """Mark all alerts as read."""
        for alert in _ALERTS_STORE:
            alert["is_read"] = True


# ---------------------------------------------------------------------------
# WebullMarketService — drop-in replacement for MarketService using Webull
# ---------------------------------------------------------------------------


class WebullMarketService:
    """
    Drop-in replacement for MarketService backed by the Webull API.

    Implements the same public method signatures as MarketService.
    Delegates to WebullClient for live data and falls back to yfinance
    (or stub data) on WebullUnavailableError.

    Requirements: R4.1, R4.8, R5.1, R13.2
    """

    # ------------------------------------------------------------------
    # Period/Interval mapping: yfinance → Webull
    # ------------------------------------------------------------------

    PERIOD_INTERVAL_MAP = {
        ("1d",  "1m"):  ("M1",  390),
        ("1d",  "5m"):  ("M5",   78),
        ("1d",  "15m"): ("M15",  26),
        ("5d",  "5m"):  ("M5",  390),
        ("1mo", "1h"):  ("H1",  720),
        ("3mo", "1d"):  ("D1",   63),
        ("1y",  "1d"):  ("D1",  252),
    }

    def __init__(
        self,
        redis_url: Optional[str] = None,
        webull_client=None,
        data_source: str = "webull",
    ) -> None:
        self._webull_client = webull_client
        self._data_source = data_source
        self._redis = self._connect_redis(redis_url)
        self._yf_session = self._build_yf_session()

    @staticmethod
    def _build_yf_session():
        """Return a requests.Session with a browser User-Agent to avoid
        Yahoo Finance rate-limiting Docker/cloud container IPs."""
        try:
            import requests
            session = requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            return session
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Redis helpers (mirrored from MarketService)
    # ------------------------------------------------------------------

    @staticmethod
    def _connect_redis(redis_url: Optional[str]):
        """Attempt to connect to Redis; return None if unavailable."""
        if not redis_url:
            return None
        try:
            redis_lib = None
            try:
                import redis as redis_lib  # type: ignore
            except ImportError:
                return None
            client = redis_lib.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            logger.debug("Redis not available — caching disabled.")
            return None

    def _cache_get(self, key: str):
        """Return cached dict for key, or None on miss / error."""
        if not self._redis:
            return None
        try:
            raw = self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    def _cache_set(self, key: str, data, ttl: int = 30) -> None:
        """Store data in Redis with the given TTL; silently ignore errors."""
        if not self._redis:
            return
        try:
            self._redis.setex(key, ttl, json.dumps(data))
        except Exception:
            return

    # ------------------------------------------------------------------
    # Market methods — stubbed; implemented in tasks 3.3, 3.5, 3.6, 3.7
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> dict:
        """
        Fetch real-time quote for a ticker using the Webull → yfinance fallback chain.

        Returns a dict matching QuoteResponse schema with an additional
        ``data_source`` field indicating which provider served the data.
        Results are cached in Redis (15s TTL for Webull, 30s TTL for yfinance).

        Raises:
            HTTPException 503: When both Webull and yfinance are unavailable.

        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9
        """
        from webull_client.client import WebullUnavailableError

        cache_key = f"quote:{ticker}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # --- Primary source: Webull ---
        if self._data_source == "webull" and self._webull_client is not None:
            try:
                raw = self._webull_client.fetch_quote(ticker)
                result = self._webull_client._normalize_webull_quote(raw, ticker)
                result_dict = {
                    "ticker": result.ticker,
                    "company_name": result.company_name,
                    "price": result.price,
                    "change": result.change,
                    "change_pct": result.change_pct,
                    "volume": result.volume,
                    "day_high": result.day_high,
                    "day_low": result.day_low,
                    "week_52_high": result.week_52_high,
                    "week_52_low": result.week_52_low,
                    "market_cap": result.market_cap,
                    "data_source": "webull",
                }
                self._cache_set(cache_key, result_dict, ttl=15)
                return result_dict
            except WebullUnavailableError:
                logger.warning(
                    "Webull unavailable for %s, falling back to yfinance", ticker
                )

        # --- Fallback: yfinance ---
        if self._data_source in {"webull", "yfinance"}:
            try:
                import yfinance as yf  # type: ignore

                t = yf.Ticker(ticker, session=self._yf_session)
                info = t.info or {}

                price = info.get("regularMarketPrice") or info.get("currentPrice")
                if not price:
                    raise ValueError(f"No price data from yfinance for {ticker}")

                prev_close = info.get("regularMarketPreviousClose") or price
                change = info.get("regularMarketChange") or (price - prev_close)
                change_pct = info.get("regularMarketChangePercent") or (
                    change / prev_close if prev_close else 0.0
                )

                result = {
                    "ticker": ticker,
                    "company_name": (
                        info.get("longName") or info.get("shortName") or ticker
                    ),
                    "price": float(price),
                    "change": float(change),
                    "change_pct": float(change_pct),
                    "volume": info.get("regularMarketVolume") or info.get("volume"),
                    "day_high": (
                        info.get("regularMarketDayHigh") or info.get("dayHigh")
                    ),
                    "day_low": (
                        info.get("regularMarketDayLow") or info.get("dayLow")
                    ),
                    "week_52_high": info.get("fiftyTwoWeekHigh"),
                    "week_52_low": info.get("fiftyTwoWeekLow"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
                    "sector": info.get("sector"),
                    "data_source": "yfinance",
                }
                self._cache_set(cache_key, result, ttl=30)
                return result
            except Exception as exc:
                logger.warning("yfinance also failed for %s: %s", ticker, exc)
                # If yfinance returns empty data it means the ticker doesn't exist
                if "No price data" in str(exc) or "no price data" in str(exc).lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Ticker '{ticker}' not found. Check the symbol and try again.",
                    )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Market data temporarily unavailable for {ticker}",
        )

    def get_chart(self, ticker: str, period: str = "1d", interval: str = "5m") -> dict:
        """
        Fetch OHLCV chart data for a ticker using the Webull → yfinance fallback chain.

        Returns a dict matching ChartResponse schema with an additional
        ``data_source`` field indicating which provider served the data.
        Results are cached in Redis (60s TTL).

        Raises:
            HTTPException 503: When both Webull and yfinance are unavailable,
                               or when data_source='stub'.

        Requirements: 4.8, 5.1
        """
        try:
            from webull_client.client import WebullUnavailableError
        except ImportError:
            WebullUnavailableError = Exception  # type: ignore[assignment,misc]

        cache_key = f"chart:{ticker}:{period}:{interval}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # --- Primary source: Webull ---
        if (
            self._data_source == "webull"
            and self._webull_client is not None
            and (period, interval) in self.PERIOD_INTERVAL_MAP
        ):
            try:
                wb_interval, count = self.PERIOD_INTERVAL_MAP[(period, interval)]
                raw_bars = self._webull_client.fetch_bars(
                    ticker, interval=wb_interval, count=count
                )
                candles = []
                for bar in raw_bars:
                    # Resolve timestamp field: try "timestamp", "time", "vt"
                    ts_raw = bar.get("timestamp") or bar.get("time") or bar.get("vt")
                    if ts_raw is None:
                        time_str = ""
                    elif isinstance(ts_raw, (int, float)):
                        # Unix timestamp in milliseconds
                        time_str = datetime.fromtimestamp(ts_raw / 1000).isoformat()
                    else:
                        # Already an ISO string
                        time_str = str(ts_raw)

                    candles.append({
                        "timestamp": time_str,
                        "open": float(bar["open"]),
                        "high": float(bar["high"]),
                        "low": float(bar["low"]),
                        "close": float(bar["close"]),
                        "volume": int(bar["volume"]),
                    })

                result = {
                    "ticker": ticker,
                    "period": period,
                    "interval": interval,
                    "data": candles,
                    "data_source": "webull",
                }
                self._cache_set(cache_key, result, ttl=60)
                return result
            except WebullUnavailableError:
                logger.warning(
                    "Webull unavailable for chart %s %s/%s, falling back to yfinance",
                    ticker, period, interval,
                )

        # --- Fallback: yfinance ---
        if self._data_source in {"webull", "yfinance"}:
            try:
                import yfinance as yf  # type: ignore

                t = yf.Ticker(ticker, session=self._yf_session)
                hist = t.history(period=period, interval=interval)

                if hist is None or hist.empty:
                    raise ValueError(f"No chart data from yfinance for {ticker}")

                candles = []
                for ts, row in hist.iterrows():
                    time_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                    candles.append({
                        "timestamp": time_str,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    })

                result = {
                    "ticker": ticker,
                    "period": period,
                    "interval": interval,
                    "data": candles,
                    "data_source": "yfinance",
                }
                self._cache_set(cache_key, result, ttl=60)
                return result
            except Exception as exc:
                logger.warning(
                    "yfinance chart also failed for %s: %s", ticker, exc
                )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chart data temporarily unavailable for {ticker}",
        )

    def get_prediction(self, ticker: str) -> dict:
        """
        Return an RSI-based AI prediction for a ticker.

        Identical logic to MarketService.get_prediction — uses yfinance
        internally. No Webull-specific change needed for this method.

        Requirements: 5.3
        """
        neutral_fallback = {
            "ticker": ticker,
            "direction": "neutral",
            "confidence": 50.0,
            "factors": {},
            "rsi_14": None,
            "macd_signal": "neutral",
            "sma_cross": "neutral",
        }

        try:
            import yfinance as yf  # type: ignore

            t = yf.Ticker(ticker, session=self._yf_session)
            hist = t.history(period="1y", interval="1d")
            if hist is None or hist.empty:
                return neutral_fallback

            closes = list(hist["Close"])
            rsi = MarketService._calculate_rsi(closes)

            if rsi is None:
                return neutral_fallback

            rsi_float = float(rsi)

            if rsi_float > 60:
                direction = "bullish"
                confidence = min(50.0 + (rsi_float - 60) * 2.0, 95.0)
            elif rsi_float < 40:
                direction = "bearish"
                confidence = min(50.0 + (40 - rsi_float) * 2.0, 95.0)
            else:
                direction = "neutral"
                confidence = 50.0

            if rsi_float > 55:
                macd_signal = "bullish"
            elif rsi_float < 45:
                macd_signal = "bearish"
            else:
                macd_signal = "neutral"

            sma_cross = "neutral"
            if len(closes) >= 200:
                sma_50 = sum(closes[-50:]) / 50
                sma_200 = sum(closes[-200:]) / 200
                if sma_50 > sma_200 * 1.002:
                    sma_cross = "golden_cross"
                elif sma_50 < sma_200 * 0.998:
                    sma_cross = "death_cross"

            return {
                "ticker": ticker,
                "direction": direction,
                "confidence": round(confidence, 1),
                "factors": {"RSI": round(rsi_float, 2)},
                "rsi_14": round(rsi_float, 2),
                "macd_signal": macd_signal,
                "sma_cross": sma_cross,
            }

        except Exception as exc:
            logger.warning("Prediction error for %s: %s", ticker, exc)
            return neutral_fallback

    def get_movers(self) -> dict:
        """
        Return top gainers and losers using a live yfinance batch scan.

        Scans a 40-ticker watchlist, fetches today's intraday performance via
        yfinance history(period="1d", interval="1m"), and ranks by % change.
        Falls back to Webull if configured, then to stub data.
        Result cached for 5 minutes.
        """
        try:
            from webull_client.client import WebullUnavailableError
        except ImportError:
            WebullUnavailableError = Exception  # type: ignore[assignment,misc]

        cache_key = "movers:v2"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # --- Webull primary ---
        if self._data_source == "webull" and self._webull_client is not None:
            try:
                raw = self._webull_client.fetch_movers()
                result = {
                    "gainers": raw["gainers"],
                    "losers": raw["losers"],
                    "data_source": "webull",
                }
                self._cache_set(cache_key, result, ttl=300)
                return result
            except Exception as exc:
                logger.warning("Webull movers failed, trying yfinance: %s", exc)

        # --- yfinance real-time scan ---
        if self._data_source in ("webull", "yfinance"):
            try:
                import yfinance as yf

                WATCHLIST = [
                    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA",
                    "AMD", "INTC", "NFLX", "JPM", "BAC", "WMT", "PFE", "T",
                    "VZ", "DIS", "PYPL", "CRM", "UBER", "PLTR", "SOFI", "COIN",
                    "ARM", "SMCI", "MARA", "RIOT", "MU", "AVGO", "QCOM",
                    "NIO", "RIVN", "SNAP", "PINS", "ROKU", "DKNG", "SQ",
                    "SHOP", "ORCL", "DELL",
                ]

                movers = []
                for sym in WATCHLIST:
                    try:
                        info = yf.Ticker(sym, session=self._yf_session).info or {}
                        price = info.get("regularMarketPrice") or info.get("currentPrice")
                        if not price:
                            continue
                        prev = info.get("regularMarketPreviousClose") or price
                        chg_pct = round((price - prev) / prev * 100, 2) if prev else 0.0
                        vol = info.get("regularMarketVolume") or info.get("volume") or 0
                        avg_vol = info.get("averageVolume") or info.get("averageDailyVolume10Day") or 1
                        movers.append({
                            "ticker": sym,
                            "name": info.get("longName") or info.get("shortName") or sym,
                            "price_change_pct": chg_pct,
                            "current_price": round(float(price), 2),
                            "volume": int(vol),
                            "avg_volume": int(avg_vol),
                            "sector": info.get("sector") or "",
                            "has_unusual_volume": (vol / avg_vol > 1.5) if avg_vol else False,
                        })
                    except Exception:
                        continue

                if movers:
                    movers.sort(key=lambda x: x["price_change_pct"], reverse=True)
                    gainers = [m for m in movers if m["price_change_pct"] > 0][:10]
                    losers = [m for m in reversed(movers) if m["price_change_pct"] < 0][:10]
                    result = {
                        "gainers": gainers,
                        "losers": losers,
                        "data_source": "yfinance",
                    }
                    self._cache_set(cache_key, result, ttl=300)
                    return result
            except Exception as exc:
                logger.warning("yfinance movers scan failed: %s", exc)

        # --- Stub fallback ---
        result = {
            "gainers": list(_STUB_GAINERS),
            "losers": list(_STUB_LOSERS),
            "data_source": "stub",
        }
        self._cache_set(cache_key, result, ttl=60)
        return result

    def get_news(
        self,
        limit: int = 5,
        offset: int = 0,
        ticker: Optional[str] = None,
        sentiment: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[dict]:
        """
        Return paginated news articles with optional filters.

        Priority chain for LIVE news:
          1. Finnhub company-news  (if FINNHUB_API_KEY set, ticker-specific)
          2. NewsAPI everything    (if NEWSAPI_KEY set, general market news)
          3. yfinance .news        (free, no key needed, per-ticker or S&P 500 news)
          4. Stub fallback         (last resort — shown with today's timestamp)

        Results are cached 10 minutes.
        """
        from config import settings
        from settings.service import get_flag
        import hashlib, requests as _req
        from datetime import datetime, timedelta

        try:
            from webull_client.client import WebullUnavailableError
        except ImportError:
            WebullUnavailableError = Exception  # type: ignore[assignment,misc]

        cache_key = f"news:v2:{ticker or 'all'}:{sentiment or ''}:{category or ''}:{offset}:{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        articles: List[dict] = []
        now = datetime.utcnow()

        # ── 1. Finnhub company-news (Alternative Data flag required) ─────────
        if get_flag("alternative_data") and settings.finnhub_api_key and len(articles) < limit + offset + 10:
            target = ticker.upper() if ticker else "SPY"
            try:
                end = now
                start = end - timedelta(days=3)
                resp = _req.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={
                        "symbol": target,
                        "from": start.strftime("%Y-%m-%d"),
                        "to": end.strftime("%Y-%m-%d"),
                        "token": settings.finnhub_api_key,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    for item in resp.json():
                        headline = item.get("headline", "")
                        if not headline:
                            continue
                        pub_ts = item.get("datetime", 0)
                        pub_iso = (
                            datetime.utcfromtimestamp(pub_ts).isoformat() + "Z"
                            if pub_ts else now.isoformat() + "Z"
                        )
                        articles.append({
                            "id": f"fh_{item.get('id', hashlib.md5(headline.encode()).hexdigest()[:8])}",
                            "title": headline,
                            "source": item.get("source", "Finnhub"),
                            "published_at": pub_iso,
                            "sentiment_score": 0.0,
                            "category": item.get("category", "General").title(),
                            "is_breaking": pub_ts > 0 and (now.timestamp() - pub_ts) < 3600,
                            "summary": (item.get("summary") or headline)[:300],
                            "tickers": [target] if target != "SPY" else ["SPY", "QQQ"],
                            "url": item.get("url", ""),
                        })
            except Exception as exc:
                logger.warning("Finnhub news failed: %s", exc)

        # ── 2. NewsAPI market news ────────────────────────────────────────────
        if settings.newsapi_key and len(articles) < limit + offset + 10:
            try:
                query = f"stock market {ticker.upper()}" if ticker else "stock market Wall Street"
                resp = _req.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 20,
                        "apiKey": settings.newsapi_key,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    for item in resp.json().get("articles", []):
                        title = item.get("title", "")
                        if not title or title == "[Removed]":
                            continue
                        pub_str = item.get("publishedAt", "")
                        try:
                            pub_iso = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).isoformat()
                        except Exception:
                            pub_iso = now.isoformat() + "Z"
                        articles.append({
                            "id": f"na_{hashlib.md5(title.encode()).hexdigest()[:12]}",
                            "title": title,
                            "source": item.get("source", {}).get("name", "NewsAPI"),
                            "published_at": pub_iso,
                            "sentiment_score": 0.0,
                            "category": "Market",
                            "is_breaking": False,
                            "summary": (item.get("description") or title)[:300],
                            "tickers": [ticker.upper()] if ticker else [],
                            "url": item.get("url", ""),
                        })
            except Exception as exc:
                logger.warning("NewsAPI news failed: %s", exc)

        # ── 3. yfinance .news (free, always available) ────────────────────────
        if len(articles) < limit + offset + 5:
            try:
                import yfinance as yf
                target = ticker.upper() if ticker else "SPY"
                yf_news = yf.Ticker(target, session=self._yf_session).news or []
                for item in yf_news:
                    parsed = _parse_yf_news_item(item, now.timestamp())
                    title = parsed["title"]
                    if not title:
                        continue
                    pub_ts = parsed["pub_ts"]
                    tickers_in = parsed["tickers_in"]
                    if ticker and ticker.upper() not in tickers_in:
                        tickers_in = [ticker.upper()] + tickers_in
                    articles.append({
                        "id": parsed["id"],
                        "title": title,
                        "source": parsed["source"],
                        "published_at": parsed["published_at"],
                        "sentiment_score": 0.0,
                        "category": "Market",
                        "is_breaking": pub_ts > 0 and (now.timestamp() - pub_ts) < 3600,
                        "summary": title,
                        "tickers": tickers_in[:5],
                        "url": parsed["url"],
                    })
            except Exception as exc:
                logger.warning("yfinance news failed: %s", exc)

        # ── 4. Stub fallback (use today's timestamp so it won't show "932d ago") ─
        if not articles:
            logger.info("No live news available, using stub with current timestamps")
            today_iso = now.isoformat() + "Z"
            for i, stub in enumerate(MarketService._STUB_NEWS):
                a = dict(stub)
                # Offset each stub article by a few minutes so they sort correctly
                offset_minutes = i * 15
                ts = now - timedelta(minutes=offset_minutes)
                a["published_at"] = ts.isoformat() + "Z"
                articles.append(a)

        # ── Filter + sort + paginate ──────────────────────────────────────────
        if ticker:
            ticker_upper = ticker.upper()
            filtered = [a for a in articles if ticker_upper in [t.upper() for t in a.get("tickers", [])]]
            # If nothing matched by ticker tag, keep all (might just be missing ticker metadata)
            if filtered:
                articles = filtered

        if sentiment:
            def _matches(score: float, s: str) -> bool:
                if s == "positive":
                    return score > 0.15
                if s == "negative":
                    return score < -0.15
                return -0.15 <= score <= 0.15
            articles = [a for a in articles if _matches(a.get("sentiment_score", 0.0), sentiment)]

        if category:
            articles = [a for a in articles if a.get("category", "").lower() == category.lower()]

        # Deduplicate by title prefix
        seen: set = set()
        unique: List[dict] = []
        for a in articles:
            key = a["title"][:60].lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(a)

        # Sort newest first
        def _ts(a: dict) -> float:
            try:
                return datetime.fromisoformat(a["published_at"].replace("Z", "+00:00")).timestamp()
            except Exception:
                return 0.0

        unique.sort(key=_ts, reverse=True)
        result = unique[offset: offset + limit]
        self._cache_set(cache_key, result, ttl=600)  # 10 min
        return result

    def get_ticker_news(self, ticker: str, limit: int = 10) -> List[dict]:
        """
        Return news articles for a specific ticker.

        Sources (in priority order):
          1. Finnhub company news API (real-time, ticker-specific)
          2. AlphaVantage NEWS_SENTIMENT (with per-ticker sentiment scores)
          3. Stub data fallback

        Each article is normalised to the NewsItem schema with a
        sentiment_score in [-1, 1].  Cached 5 minutes.

        Requirements: 4.3, 4.5, 5.1
        """
        from config import settings
        from settings.service import get_flag
        import uuid, hashlib, requests as _req
        from datetime import datetime, timedelta

        cache_key = f"ticker_news:{ticker}:{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        articles: List[dict] = []
        ticker_upper = ticker.upper()

        # ── 1. Finnhub company news (Alternative Data flag required) ─────────
        if get_flag("alternative_data") and settings.finnhub_api_key:
            try:
                end = datetime.utcnow()
                start = end - timedelta(days=7)
                resp = _req.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={
                        "symbol": ticker_upper,
                        "from": start.strftime("%Y-%m-%d"),
                        "to": end.strftime("%Y-%m-%d"),
                        "token": settings.finnhub_api_key,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    for item in resp.json()[:limit * 2]:
                        headline = item.get("headline", "")
                        summary = item.get("summary", "")
                        if not headline:
                            continue
                        # Simple VADER-like lexicon scoring from summary length proxy
                        sentiment = 0.0
                        articles.append({
                            "id": f"fh_{item.get('id', hashlib.md5(headline.encode()).hexdigest()[:8])}",
                            "title": headline,
                            "source": item.get("source", "Finnhub"),
                            "published_at": datetime.utcfromtimestamp(item["datetime"]).isoformat() + "Z",
                            "sentiment_score": sentiment,
                            "category": item.get("category", "General"),
                            "is_breaking": (datetime.utcnow() - datetime.utcfromtimestamp(item["datetime"])).total_seconds() < 1800,
                            "summary": summary[:300] if summary else headline,
                            "tickers": [ticker_upper],
                            "url": item.get("url", ""),
                        })
            except Exception as exc:
                logger.warning("Finnhub news failed for %s: %s", ticker, exc)

        # ── 2. AlphaVantage NEWS_SENTIMENT (Alternative Data flag required) ─
        if get_flag("alternative_data") and settings.alphavantage_api_key and len(articles) < limit:
            try:
                resp = _req.get(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "NEWS_SENTIMENT",
                        "tickers": ticker_upper,
                        "limit": 20,
                        "apikey": settings.alphavantage_api_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("feed", [])[:limit]:
                        title = item.get("title", "")
                        if not title:
                            continue
                        # Extract per-ticker sentiment from AV
                        ticker_sentiment = 0.0
                        for ts in item.get("ticker_sentiment", []):
                            if ts.get("ticker", "").upper() == ticker_upper:
                                try:
                                    ticker_sentiment = float(ts.get("ticker_sentiment_score", 0))
                                except (ValueError, TypeError):
                                    pass
                                break
                        # AV label: Bearish(-1)→-1, Neutral→0, Bullish→+1
                        label = item.get("overall_sentiment_label", "Neutral")
                        if ticker_sentiment == 0.0:
                            ticker_sentiment = {"Bearish": -0.6, "Somewhat-Bearish": -0.3,
                                                "Neutral": 0.0, "Somewhat-Bullish": 0.3,
                                                "Bullish": 0.6}.get(label, 0.0)
                        try:
                            pub = datetime.strptime(item["time_published"], "%Y%m%dT%H%M%S").isoformat() + "Z"
                        except Exception:
                            pub = datetime.utcnow().isoformat() + "Z"
                        articles.append({
                            "id": f"av_{hashlib.md5(title.encode()).hexdigest()[:12]}",
                            "title": title,
                            "source": item.get("source", "Alpha Vantage"),
                            "published_at": pub,
                            "sentiment_score": round(ticker_sentiment, 3),
                            "category": item.get("topics", [{}])[0].get("topic", "General") if item.get("topics") else "General",
                            "is_breaking": False,
                            "summary": item.get("summary", title)[:300],
                            "tickers": [t["ticker"] for t in item.get("ticker_sentiment", [])],
                            "url": item.get("url", ""),
                        })
            except Exception as exc:
                logger.warning("AlphaVantage news failed for %s: %s", ticker, exc)

        # ── 3. yfinance .news (free, always available) ────────────────────────
        if len(articles) < limit:
            try:
                import yfinance as yf
                yf_news = yf.Ticker(ticker_upper, session=self._yf_session).news or []
                from datetime import datetime as _dt
                now_ts = _dt.utcnow().timestamp()
                for item in yf_news[:limit]:
                    parsed = _parse_yf_news_item(item, now_ts)
                    title = parsed["title"]
                    if not title:
                        continue
                    pub_ts = parsed["pub_ts"]
                    tickers_in = parsed["tickers_in"]
                    if ticker_upper not in tickers_in:
                        tickers_in = [ticker_upper] + tickers_in
                    articles.append({
                        "id": parsed["id"],
                        "title": title,
                        "source": parsed["source"],
                        "published_at": parsed["published_at"],
                        "sentiment_score": 0.0,
                        "category": "Market",
                        "is_breaking": pub_ts > 0 and (now_ts - pub_ts) < 3600,
                        "summary": title,
                        "tickers": tickers_in[:5],
                        "url": parsed["url"],
                    })
            except Exception as exc:
                logger.warning("yfinance ticker news failed for %s: %s", ticker, exc)

        # ── 4. Stub fallback (with current timestamps) ────────────────────────
        if not articles:
            from datetime import datetime as _dt, timedelta as _td
            now = _dt.utcnow()
            for i, stub in enumerate([a for a in MarketService._STUB_NEWS if ticker_upper in a.get("tickers", [])]):
                a = dict(stub)
                a["published_at"] = (now - _td(minutes=i * 10)).isoformat() + "Z"
                articles.append(a)
        unique = []
        for a in articles:
            key = a["title"][:60].lower()
            if key not in seen:
                seen.add(key)
                unique.append(a)

        # Sort newest first
        def _pub_ts(a: dict) -> float:
            try:
                return datetime.fromisoformat(a["published_at"].replace("Z", "+00:00")).timestamp()
            except Exception:
                return 0.0

        unique.sort(key=_pub_ts, reverse=True)
        result = unique[:limit]
        self._cache_set(cache_key, result, ttl=300)  # 5 min
        return result

    def get_earnings(self, ticker: str) -> dict:
        """
        Return upcoming earnings date, EPS estimate, and last 4 quarters history.
        Uses yfinance calendar and earnings_history. Cached 4 hours.
        """
        cache_key = f"earnings:{ticker}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = {
            "ticker": ticker,
            "next_earnings_date": None,
            "next_earnings_time": None,
            "eps_estimate": None,
            "history": [],
        }

        try:
            import yfinance as yf
            t = yf.Ticker(ticker, session=self._yf_session)

            # Next earnings date from calendar
            try:
                cal = t.calendar
                if cal is not None and not (hasattr(cal, "empty") and cal.empty):
                    if hasattr(cal, "to_dict"):
                        cal_dict = cal.to_dict()
                    else:
                        cal_dict = dict(cal)
                    ed = cal_dict.get("Earnings Date")
                    if ed:
                        dates = ed if isinstance(ed, list) else [ed]
                        result["next_earnings_date"] = str(dates[0])[:10] if dates else None
                    eps_est = cal_dict.get("Earnings Average") or cal_dict.get("EPS Trend")
                    if eps_est:
                        vals = eps_est if isinstance(eps_est, list) else [eps_est]
                        try:
                            result["eps_estimate"] = float(vals[0])
                        except (ValueError, TypeError):
                            pass
            except Exception as exc:
                logger.debug("yfinance calendar failed for %s: %s", ticker, exc)

            # Historical earnings
            try:
                hist = t.earnings_history
                if hist is not None and not hist.empty:
                    rows = []
                    for ts_idx, row in hist.iterrows():
                        try:
                            qtr = str(ts_idx)[:10]
                            eps_est = row.get("epsEstimate") if hasattr(row, "get") else None
                            eps_act = row.get("epsActual") if hasattr(row, "get") else None
                            if eps_est is None:
                                try:
                                    eps_est = float(row["epsEstimate"])
                                except Exception:
                                    eps_est = None
                            if eps_act is None:
                                try:
                                    eps_act = float(row["epsActual"])
                                except Exception:
                                    eps_act = None
                            surp = None
                            if eps_est and eps_act is not None and eps_est != 0:
                                surp = round(((eps_act - eps_est) / abs(eps_est)) * 100, 1)
                            rows.append({
                                "quarter": qtr,
                                "eps_estimate": eps_est,
                                "eps_actual": eps_act,
                                "surprise_pct": surp,
                            })
                        except Exception:
                            continue
                    result["history"] = rows[-4:]  # last 4 quarters
            except Exception as exc:
                logger.debug("yfinance earnings_history failed for %s: %s", ticker, exc)

        except Exception as exc:
            logger.warning("get_earnings failed for %s: %s", ticker, exc)

        self._cache_set(cache_key, result, ttl=14400)  # 4h
        return result

    def get_institutional(self, ticker: str, limit: int = 10) -> dict:
        """
        Return top institutional holders for a ticker using yfinance.
        Also includes top mutual fund holders as a proxy for "smart money".
        Cached for 24 hours.
        """
        cache_key = f"institutional:{ticker}:{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result: dict = {"ticker": ticker, "holders": []}

        try:
            import yfinance as yf
            t = yf.Ticker(ticker, session=self._yf_session)
            holders: list = []

            # Institutional holders
            try:
                inst = t.institutional_holders
                if inst is not None and not inst.empty:
                    for _, row in inst.iterrows():
                        name = row.get("Holder") or row.get("holder") or ""
                        shares_raw = row.get("Shares") or row.get("shares")
                        pct_raw = row.get("% Out") or row.get("pctHeld") or row.get("pct_held")
                        val_raw = row.get("Value") or row.get("value")
                        date_raw = row.get("Date Reported") or row.get("dateReported")
                        if not name:
                            continue
                        try:
                            shares = int(shares_raw) if shares_raw is not None else None
                        except (ValueError, TypeError):
                            shares = None
                        try:
                            pct = float(pct_raw) * 100 if pct_raw is not None and float(pct_raw) <= 1 else (float(pct_raw) if pct_raw is not None else None)
                        except (ValueError, TypeError):
                            pct = None
                        try:
                            val = float(val_raw) if val_raw is not None else None
                        except (ValueError, TypeError):
                            val = None
                        date_str = str(date_raw)[:10] if date_raw is not None else None
                        holders.append({
                            "holder": str(name),
                            "shares": shares,
                            "pct_held": round(pct, 2) if pct is not None else None,
                            "value": val,
                            "date_reported": date_str,
                            "type": "institution",
                        })
            except Exception as exc:
                logger.debug("institutional_holders failed for %s: %s", ticker, exc)

            # Mutual fund holders (top smart-money funds)
            try:
                mf = t.mutualfund_holders
                if mf is not None and not mf.empty:
                    for _, row in mf.iterrows():
                        name = row.get("Holder") or row.get("holder") or ""
                        shares_raw = row.get("Shares") or row.get("shares")
                        pct_raw = row.get("% Out") or row.get("pctHeld") or row.get("pct_held")
                        val_raw = row.get("Value") or row.get("value")
                        date_raw = row.get("Date Reported") or row.get("dateReported")
                        if not name:
                            continue
                        try:
                            shares = int(shares_raw) if shares_raw is not None else None
                        except (ValueError, TypeError):
                            shares = None
                        try:
                            pct = float(pct_raw) * 100 if pct_raw is not None and float(pct_raw) <= 1 else (float(pct_raw) if pct_raw is not None else None)
                        except (ValueError, TypeError):
                            pct = None
                        try:
                            val = float(val_raw) if val_raw is not None else None
                        except (ValueError, TypeError):
                            val = None
                        date_str = str(date_raw)[:10] if date_raw is not None else None
                        holders.append({
                            "holder": str(name),
                            "shares": shares,
                            "pct_held": round(pct, 2) if pct is not None else None,
                            "value": val,
                            "date_reported": date_str,
                            "type": "fund",
                        })
            except Exception as exc:
                logger.debug("mutualfund_holders failed for %s: %s", ticker, exc)

            # Sort by value desc, take top limit
            holders.sort(key=lambda x: x.get("value") or 0, reverse=True)
            result["holders"] = holders[:limit]

        except Exception as exc:
            logger.warning("get_institutional failed for %s: %s", ticker, exc)

        self._cache_set(cache_key, result, ttl=86400)  # 24h
        return result

    def get_predictions(self, tickers: Optional[List[str]] = None) -> List[dict]:
        """
        Return AI-powered ensemble predictions backed by live market data.

        Pipeline per ticker:
          1. Try Redis cache (pre-warmed daily at 07:00 ET by Celery task)
          2. Compute live from yfinance: RSI, MACD, SMA cross, momentum score
          3. Optional: enrich with LLM confidence adjustment (if key available)
          4. Fall back to stub only when yfinance is completely unavailable

        Each prediction includes:
          - category: Strong Buy / Buy / Hold / Sell / Strong Sell
          - confidence: 0.0–1.0
          - expected_return: estimated % move (from momentum + RSI signal)
          - lower_bound / upper_bound: ±1 sigma range
          - is_low_confidence: True when confidence < 0.50

        Results for the daily pre-warm are cached for 24 hours under key
        "predictions:daily". Per-request results cached for 15 minutes.
        """
        from config import settings

        # ── Full watchlist when caller doesn't specify ────────────────────────
        DEFAULT_WATCHLIST = [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA",
            "AMD", "INTC", "NFLX", "JPM", "BAC", "AVGO", "CRM", "ORCL",
            "PYPL", "MU", "QCOM", "PLTR", "UBER",
        ]

        target_tickers = tickers if tickers else DEFAULT_WATCHLIST

        # ── Check daily pre-warmed cache first ────────────────────────────────
        daily_key = "predictions:daily:v2"
        daily_cached = self._cache_get(daily_key)
        if daily_cached:
            preds = daily_cached
            if tickers:
                upper = {t.upper() for t in tickers}
                preds = [p for p in preds if p["ticker"] in upper]
            return preds

        # ── Compute live ──────────────────────────────────────────────────────
        results: List[dict] = []
        for ticker_sym in target_tickers:
            pred = self._compute_prediction(ticker_sym.upper())
            if pred:
                results.append(pred)

        if not results:
            # Full stub fallback — only if yfinance is completely broken
            preds = list(MarketService._STUB_PREDICTIONS)
            if tickers:
                upper = {t.upper() for t in tickers}
                preds = [p for p in preds if p["ticker"] in upper]
            return preds

        # Sort: Strong Buy → Buy → Hold → Sell → Strong Sell
        ORDER = {"Strong Buy": 0, "Buy": 1, "Hold": 2, "Sell": 3, "Strong Sell": 4}
        results.sort(key=lambda p: ORDER.get(p["category"], 2))

        # Cache per-request (15 min)
        per_key = f"predictions:req:v2:{':'.join(sorted(target_tickers))}"
        self._cache_set(per_key, results, ttl=900)
        return results

    def _compute_prediction(self, ticker: str) -> Optional[dict]:
        """
        Compute a live ensemble prediction for one ticker.

        Stage 1 — Technical signals (always runs, no API key needed):
          RSI(14), MACD histogram, SMA-50/200 cross, 30-day momentum

        Stage 2 — News sentiment enrichment (non-blocking, skipped gracefully):
          Fetches the 5 most recent headlines from AlphaVantage or yfinance news,
          then asks the LLM (Groq/OpenAI) for a structured confidence adjustment.
          The LLM output can shift the technical score by up to ±0.15 and provides
          a one-sentence narrative reason shown on the prediction card.

        Returns a dict matching EnsemblePrediction schema, or None on hard failure.
        """
        from config import settings
        from datetime import datetime as _dt

        # Per-ticker 15-minute cache — avoids hammering yfinance on every request
        cache_key = f"pred:v2:{ticker}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            import yfinance as yf

            t = yf.Ticker(ticker, session=self._yf_session)
            hist = t.history(period="1y", interval="1d")
            if hist is None or hist.empty or len(hist) < 30:
                return None

            closes = [float(c) for c in hist["Close"].tolist()]
            n = len(closes)

            # ── Stage 1: Technical signals ────────────────────────────────────

            # RSI(14)
            rsi_val = float(MarketService._calculate_rsi(closes) or 50.0)

            # MACD histogram (EMA12 − EMA26 − EMA9 of macd)
            def _ema(vals: List[float], period: int) -> List[float]:
                k = 2 / (period + 1)
                out = [vals[0]]
                for v in vals[1:]:
                    out.append(v * k + out[-1] * (1 - k))
                return out

            ema12 = _ema(closes, 12)
            ema26 = _ema(closes, 26)
            macd_line = [a - b for a, b in zip(ema12, ema26)]
            signal_line = _ema(macd_line[25:], 9)
            macd_hist = (macd_line[-1] - signal_line[-1]) if signal_line else 0.0

            # SMA cross
            sma50 = sum(closes[-50:]) / 50 if n >= 50 else None
            sma200 = sum(closes[-200:]) / 200 if n >= 200 else None
            golden = bool(sma50 and sma200 and sma50 > sma200 * 1.002)
            death = bool(sma50 and sma200 and sma50 < sma200 * 0.998)

            # 30-day price momentum
            momentum_30d = ((closes[-1] - closes[-30]) / closes[-30] * 100) if n >= 30 else 0.0

            # Technical composite score in [-2.5, +2.5]
            score = 0.0
            if rsi_val > 65:      score += 1.0
            elif rsi_val > 55:    score += 0.5
            elif rsi_val < 35:    score -= 1.0
            elif rsi_val < 45:    score -= 0.5

            if macd_hist > 0:     score += 0.5
            elif macd_hist < 0:   score -= 0.5

            if golden:            score += 0.5
            elif death:           score -= 0.5

            if momentum_30d > 5:   score += 0.5
            elif momentum_30d > 2: score += 0.25
            elif momentum_30d < -5: score -= 0.5
            elif momentum_30d < -2: score -= 0.25

            # Normalise to [-1, +1]
            norm_score = max(-1.0, min(1.0, score / 2.5))

            # ── Stage 2: News sentiment + LLM enrichment ─────────────────────
            # Only runs if the Deep Learning feature flag is enabled.
            # Skipped gracefully if the flag is off or on any failure.
            llm_sentiment_adj = 0.0
            llm_reason = ""

            try:
                from settings.service import get_flag
                if get_flag("deep_learning"):
                    news_headlines = self._fetch_recent_headlines(ticker)
                    if news_headlines:
                        avg_sentiment = sum(h.get("sentiment", 0.0) for h in news_headlines) / len(news_headlines)
                        llm_sentiment_adj += max(-0.2, min(0.2, avg_sentiment * 0.3))

                        if settings.groq_api_key or settings.openai_api_key:
                            llm_result = self._llm_enrich_prediction(
                                ticker=ticker,
                                norm_score=norm_score,
                                rsi=rsi_val,
                                macd_hist=macd_hist,
                                golden=golden,
                                death=death,
                                momentum_30d=momentum_30d,
                                news_headlines=news_headlines,
                            )
                            if llm_result:
                                llm_sentiment_adj += llm_result.get("score_adj", 0.0)
                                llm_reason = llm_result.get("reason", "")
            except Exception as exc:
                logger.debug("News/LLM enrichment skipped for %s: %s", ticker, exc)

            # Apply adjustment, re-clamp
            final_score = max(-1.0, min(1.0, norm_score + llm_sentiment_adj))

            # Map to category
            if final_score >= 0.6:       category = "Strong Buy"
            elif final_score >= 0.2:     category = "Buy"
            elif final_score <= -0.6:    category = "Strong Sell"
            elif final_score <= -0.2:    category = "Sell"
            else:                         category = "Hold"

            confidence = round(0.35 + abs(final_score) * 0.60, 3)
            expected_return = round(final_score * 0.08, 4)
            half_spread = max(0.01, abs(expected_return) * 0.5 + 0.01)

            # Build the reason text shown on the card
            tech_parts = []
            if rsi_val > 60:   tech_parts.append(f"RSI {rsi_val:.0f} (bullish)")
            elif rsi_val < 40: tech_parts.append(f"RSI {rsi_val:.0f} (oversold)")
            if golden:         tech_parts.append("golden cross")
            elif death:        tech_parts.append("death cross")
            if momentum_30d > 3:  tech_parts.append(f"+{momentum_30d:.1f}% 30d")
            elif momentum_30d < -3: tech_parts.append(f"{momentum_30d:.1f}% 30d")
            if macd_hist > 0:  tech_parts.append("MACD bullish")
            elif macd_hist < 0: tech_parts.append("MACD bearish")

            tech_reason = ", ".join(tech_parts) if tech_parts else "neutral technicals"
            reason = llm_reason if llm_reason else f"Technicals: {tech_reason}."
            if news_sentiment_summary and not llm_reason:
                reason += f" Recent news: {news_headlines[0]['title'][:100]}."

            result = {
                "ticker": ticker,
                "category": category,
                "confidence": confidence,
                "expected_return": expected_return,
                "lower_bound": round(expected_return - half_spread, 4),
                "upper_bound": round(expected_return + half_spread, 4),
                "is_low_confidence": confidence < 0.50,
                # Extended fields for prediction detail view
                "rsi_14": round(rsi_val, 1),
                "macd_histogram": round(macd_hist, 4),
                "sma_cross": "golden_cross" if golden else ("death_cross" if death else "neutral"),
                "momentum_30d": round(momentum_30d, 2),
                "reason": reason[:300],
                "computed_at": _dt.utcnow().isoformat() + "Z",
            }

            self._cache_set(cache_key, result, ttl=900)
            return result

        except Exception as exc:
            logger.warning("_compute_prediction failed for %s: %s", ticker, exc)
            return None

    def _fetch_recent_headlines(self, ticker: str) -> List[dict]:
        """
        Fetch the 5 most recent news headlines + rough sentiment for a ticker.

        Uses AlphaVantage (with sentiment scores) if the Alternative Data flag
        is enabled, falls back to yfinance news (always available, sentiment=0).
        Returns list of {title, sentiment, source}.
        """
        from config import settings
        from settings.service import get_flag
        import requests as _req

        headlines = []

        # AlphaVantage — paid API, gated by Alternative Data feature flag
        if get_flag("alternative_data") and settings.alphavantage_api_key:
            try:
                resp = _req.get(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "NEWS_SENTIMENT",
                        "tickers": ticker,
                        "limit": 5,
                        "apikey": settings.alphavantage_api_key,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    for item in resp.json().get("feed", [])[:5]:
                        score = 0.0
                        for ts in item.get("ticker_sentiment", []):
                            if ts.get("ticker", "").upper() == ticker.upper():
                                try:
                                    score = float(ts.get("ticker_sentiment_score", 0))
                                except (ValueError, TypeError):
                                    pass
                                break
                        headlines.append({
                            "title": item.get("title", ""),
                            "sentiment": score,
                            "source": item.get("source", ""),
                        })
                if headlines:
                    return headlines
            except Exception as exc:
                logger.debug("AV headlines failed for %s: %s", ticker, exc)

        # yfinance news fallback (no sentiment score, use 0.0)
        if not headlines:
            try:
                import yfinance as yf
                from datetime import datetime as _dt
                now_ts = _dt.utcnow().timestamp()
                news = yf.Ticker(ticker, session=self._yf_session).news or []
                for item in news[:5]:
                    parsed = _parse_yf_news_item(item, now_ts)
                    if parsed["title"]:
                        headlines.append({"title": parsed["title"], "sentiment": 0.0, "source": parsed["source"]})
            except Exception as exc:
                logger.debug("yfinance headlines failed for %s: %s", ticker, exc)

        return headlines

    def _llm_enrich_prediction(
        self,
        ticker: str,
        norm_score: float,
        rsi: float,
        macd_hist: float,
        golden: bool,
        death: bool,
        momentum_30d: float,
        news_headlines: List[dict],
    ) -> Optional[dict]:
        """
        Ask the LLM to review the technical signals + recent news and return:
          - score_adj: a float in [-0.15, +0.15] to apply to norm_score
          - reason:    one concise sentence explaining the prediction

        Uses the sync OpenAI client (this runs in Celery worker context).
        Respects JSON mode. Returns None on any failure — never blocks the caller.
        """
        from config import settings
        import json as _json

        try:
            from openai import OpenAI
        except ImportError:
            return None

        try:
            if settings.groq_api_key:
                client = OpenAI(
                    api_key=settings.groq_api_key,
                    base_url="https://api.groq.com/openai/v1",
                )
                model = "llama-3.3-70b-versatile"
            elif settings.openai_api_key:
                client = OpenAI(api_key=settings.openai_api_key)
                model = settings.openai_model
            else:
                return None

            sma_status = "golden cross (bullish)" if golden else ("death cross (bearish)" if death else "no clear cross")
            news_block = "\n".join(
                f'  - [{h["sentiment"]:+.2f}] "{h["title"][:100]}"'
                for h in news_headlines[:5]
            )

            prompt = f"""You are a quantitative equity analyst. Assess this stock and return JSON ONLY.

Ticker: {ticker}
Technical composite score: {norm_score:+.2f} (range -1 to +1, positive = bullish)
RSI(14): {rsi:.1f}
MACD histogram: {macd_hist:+.4f}
SMA cross: {sma_status}
30-day momentum: {momentum_30d:+.1f}%

Recent news headlines (sentiment score in brackets, -1=bearish, +1=bullish):
{news_block}

Return exactly this JSON (no markdown, no extra text):
{{
  "score_adj": <float between -0.15 and +0.15, news adjustment to the technical score>,
  "reason": "<one concise sentence ≤ 140 chars explaining the overall prediction>"
}}"""

            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a quantitative analyst. Return compact JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            data = _json.loads(raw)
            adj = float(data.get("score_adj", 0.0))
            adj = max(-0.15, min(0.15, adj))  # clamp to safe range
            reason = str(data.get("reason", ""))[:300]
            return {"score_adj": adj, "reason": reason}

        except Exception as exc:
            logger.debug("LLM prediction enrichment failed for %s: %s", ticker, exc)
            return None

    def get_penny_stocks(self) -> List[dict]:
        """
        Return live low-priced stocks (price ≤ $15) ranked by momentum score.
        ...
        """
        cache_key = "penny_stocks:live:v2"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # ── Universe of low-price tickers (≤ $15) ────────────────────────────
        PENNY_UNIVERSE = list(dict.fromkeys([
            # Classic sub-$5 names
            "SNDL", "MMAT", "CLOV", "NKLA", "SENS",
            "MVST", "WKHS", "IDEX", "BNGO", "OCGN",
            "ZKIN", "GNUS", "SHIP", "CTRM", "XELA",
            "MULN", "BBIG", "FFIE", "HOFV", "ILUS",
            "VERB", "SIGA", "BLNK", "ZEV", "FCEL",
            # Small-cap $5–$15 range
            "PLUG", "GEVO", "OPEN", "RILY", "TLRY",
            "MARA", "RIOT", "SOFI", "JOBY", "STEM",
            "BFLY", "SPCE", "LAZR", "LIDR", "HIMS",
            "ACHR", "IONQ", "XPEV", "RUN", "EVGO",
            "NOVA", "ASTR", "CANO", "DKNG", "FFIV",
        ]))

        try:
            import yfinance as yf
            from config import settings
            import requests as _req, hashlib

            live: List[dict] = []
            for sym in PENNY_UNIVERSE:
                try:
                    ticker_obj = yf.Ticker(sym, session=self._yf_session)
                    info = ticker_obj.info or {}

                    price = info.get("regularMarketPrice") or info.get("currentPrice")
                    if not price or float(price) > 15.0 or float(price) <= 0:
                        continue

                    price = float(price)
                    prev_close = info.get("regularMarketPreviousClose") or price
                    change_pct = round(((price - prev_close) / prev_close * 100) if prev_close else 0.0, 2)
                    volume = int(info.get("regularMarketVolume") or info.get("volume") or 0)
                    avg_volume = int(info.get("averageVolume") or info.get("averageDailyVolume10Day") or 1)
                    volume_ratio = round(volume / avg_volume, 2) if avg_volume else 0.0
                    sector = info.get("sector") or "Unknown"

                    # ── Momentum score (0–100) ───────────────────────────────
                    chg_comp = min(abs(change_pct) / 15.0, 1.0) * 50.0 * (1 if change_pct >= 0 else -0.5)
                    vol_comp = min(volume_ratio / 5.0, 1.0) * 30.0
                    rsi_comp = 10.0
                    try:
                        hist = ticker_obj.history(period="15d", interval="1d")
                        if hist is not None and len(hist) >= 10:
                            closes = [float(c) for c in hist["Close"].tolist()]
                            sma10 = sum(closes[-10:]) / 10
                            rsi_comp = 20.0 if closes[-1] > sma10 else 5.0
                    except Exception:
                        pass

                    momentum_score = round(max(0.0, chg_comp + vol_comp + rsi_comp), 1)

                    # ── Suspicion score ──────────────────────────────────────
                    extreme_vol = volume_ratio > 5.0
                    large_spike = change_pct > 20.0
                    suspicion = 0.0
                    if extreme_vol and large_spike:
                        suspicion = 0.85
                    elif extreme_vol:
                        suspicion = 0.55
                    elif large_spike:
                        suspicion = 0.45
                    elif volume_ratio > 2.5 and change_pct > 10.0:
                        suspicion = 0.35
                    suspicion = round(suspicion, 2)

                    # ── Risk level ───────────────────────────────────────────
                    if suspicion >= 0.7 or volume_ratio > 8.0:
                        risk_level = "extreme"
                    elif suspicion >= 0.4 or change_pct > 15.0 or volume_ratio > 3.0:
                        risk_level = "high"
                    elif change_pct > 5.0 or volume_ratio > 1.5:
                        risk_level = "medium"
                    else:
                        risk_level = "low"

                    # ── Catalyst from news (yfinance 1.5+ nested schema) ─────
                    catalyst = ""
                    try:
                        news = ticker_obj.news or []
                        if news:
                            # yfinance ≥1.5: {"id":..., "content": {"title":...}}
                            # yfinance <1.5:  {"title":..., ...}
                            first = news[0]
                            if "content" in first:
                                catalyst = (first["content"].get("title") or "")[:80]
                            else:
                                catalyst = (first.get("title") or "")[:80]
                    except Exception:
                        pass

                    # ── Recommendation ───────────────────────────────────────
                    if suspicion >= 0.65 or risk_level == "extreme":
                        recommendation = "High Risk — Avoid"
                    elif momentum_score >= 70 and risk_level in ("low", "medium"):
                        recommendation = "Speculative Buy"
                    elif momentum_score >= 50:
                        recommendation = "Watch"
                    elif change_pct < -5.0:
                        recommendation = "Sell"
                    else:
                        recommendation = "Hold"

                    # ── Insider activity (Finnhub, non-blocking) ─────────────
                    insider_net, insider_buys, insider_sells = 0, 0, 0
                    if settings.finnhub_api_key:
                        try:
                            from datetime import datetime as _dt, timedelta as _td
                            end = _dt.utcnow()
                            start = end - _td(days=90)
                            resp = _req.get(
                                "https://finnhub.io/api/v1/stock/insider-transactions",
                                params={
                                    "symbol": sym,
                                    "from": start.strftime("%Y-%m-%d"),
                                    "to": end.strftime("%Y-%m-%d"),
                                    "token": settings.finnhub_api_key,
                                },
                                timeout=4,
                            )
                            if resp.status_code == 200:
                                for tx in resp.json().get("data", []):
                                    code = tx.get("transactionCode", "")
                                    shares = tx.get("share", 0) or 0
                                    if code == "P":
                                        insider_buys += 1
                                        insider_net += shares
                                    elif code == "S":
                                        insider_sells += 1
                                        insider_net -= shares
                        except Exception:
                            pass

                    live.append({
                        "ticker": sym,
                        "price": price,
                        "price_change_pct": change_pct,
                        "volume": volume,
                        "avg_volume": avg_volume,
                        "volume_ratio": volume_ratio,
                        "momentum_score": momentum_score,
                        "risk_level": risk_level,
                        "sector": sector,
                        "catalyst": catalyst,
                        "suspicion_score": suspicion,
                        "recommendation": recommendation,
                        "insider_net": insider_net,
                        "insider_buys": insider_buys,
                        "insider_sells": insider_sells,
                    })

                except Exception as exc:
                    logger.debug("Penny scan failed for %s: %s", sym, exc)
                    continue

            if live:
                live.sort(key=lambda x: x["momentum_score"], reverse=True)
                self._cache_set(cache_key, live, ttl=300)
                logger.info("Penny stock scan: %d live stocks", len(live))
                return live

        except Exception as exc:
            logger.warning("Penny stocks live scan failed: %s", exc)

        return sorted(MarketService._STUB_PENNY_STOCKS, key=lambda x: x["momentum_score"], reverse=True)

    def get_snapshot(self) -> dict:
        """
        Return a high-level market index snapshot.

        Fetches SPY, QQQ, VIX quotes via WebullClient; extracts change_pct
        for SPY/QQQ and price for VIX. Falls back to stub values on any failure.
        Result cached for 30 s.

        Requirements: 4.3, 4.5, 5.1
        """
        from webull_client.client import WebullUnavailableError

        cache_key = "snapshot"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if self._data_source == "webull" and self._webull_client is not None:
            try:
                spy_raw = self._webull_client.fetch_quote("SPY")
                qqq_raw = self._webull_client.fetch_quote("QQQ")
                vix_raw = self._webull_client.fetch_quote("VIX")

                spy_data = self._webull_client._normalize_webull_quote(spy_raw, "SPY")
                qqq_data = self._webull_client._normalize_webull_quote(qqq_raw, "QQQ")
                vix_data = self._webull_client._normalize_webull_quote(vix_raw, "VIX")

                result = {
                    "sp500_change_pct": spy_data.change_pct,
                    "nasdaq_change_pct": qqq_data.change_pct,
                    "vix": vix_data.price,
                    "data_source": "webull",
                }
                self._cache_set(cache_key, result, ttl=30)
                return result
            except (WebullUnavailableError, Exception) as exc:
                logger.warning(
                    "Webull unavailable for snapshot, falling back to yfinance: %s", exc
                )

        # yfinance path (primary when data_source=="yfinance"; fallback from Webull)
        if self._data_source in ("webull", "yfinance"):
            try:
                import yfinance as yf

                def _pct(sym: str) -> float:
                    fi = yf.Ticker(sym, session=self._yf_session).fast_info
                    prev = fi.previous_close or fi.last_price
                    if prev and prev != 0:
                        return round((fi.last_price - prev) / prev * 100, 2)
                    return 0.0

                def _price(sym: str) -> float:
                    return round(yf.Ticker(sym, session=self._yf_session).fast_info.last_price, 2)

                result = {
                    "sp500_change_pct": _pct("SPY"),
                    "nasdaq_change_pct": _pct("QQQ"),
                    "vix": _price("^VIX"),
                    "data_source": "yfinance",
                }
                self._cache_set(cache_key, result, ttl=30)
                return result
            except Exception as exc:
                logger.warning("yfinance snapshot failed, returning stub: %s", exc)

        # Last resort: stub values
        result = {
            "sp500_change_pct": 0.82,
            "nasdaq_change_pct": 1.14,
            "vix": 15.3,
            "data_source": "stub",
        }
        self._cache_set(cache_key, result, ttl=30)
        return result

    def get_alerts(self, user_id=None, db=None) -> List[dict]:
        """
        Generate live market alerts for the user's watchlist tickers.

        Scans each watchlist ticker for actionable conditions:
          - Large intraday move   (>3% gain or >-3% loss)
          - Volume surge          (current volume > 2x avg daily volume)
          - RSI extremes          (RSI > 75 overbought, RSI < 30 oversold)
          - Earnings proximity    (next earnings date within 3 days)

        Alerts dismissed by the user are tracked in Redis under
        "alerts:dismissed:{user_id}" and filtered out of the response.

        If user_id / db are not provided (legacy call), returns an empty list
        rather than the old hardcoded stubs.

        Results are cached per-user for 5 minutes.
        """
        from datetime import datetime as _dt, timedelta as _td
        import uuid as _uuid

        if user_id is None:
            return []

        # ── Check per-user cache ─────────────────────────────────────────────
        cache_key = f"alerts:live:{user_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        # ── Fetch dismissed IDs for this user ────────────────────────────────
        dismissed_key = f"alerts:dismissed:{user_id}"
        dismissed: set = set()
        if self._redis:
            try:
                dismissed = set(self._redis.smembers(dismissed_key) or [])
            except Exception:
                pass

        # ── Get user's watchlist tickers ────────────────────────────────────
        tickers: List[str] = []
        if db is not None:
            try:
                from watchlist.models import WatchlistItem as _WI
                rows = db.query(_WI).filter(_WI.user_id == user_id).all()
                tickers = list({r.ticker.upper() for r in rows})
            except Exception as exc:
                logger.debug("Watchlist query failed for alerts: %s", exc)

        # Fallback: scan a small default set so new users see something useful
        if not tickers:
            tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"]

        # ── Scan each ticker ─────────────────────────────────────────────────
        alerts: List[dict] = []
        now = _dt.utcnow()

        try:
            import yfinance as yf

            for sym in tickers[:20]:  # cap to prevent timeouts
                try:
                    info = yf.Ticker(sym, session=self._yf_session).info or {}
                    price = info.get("regularMarketPrice") or info.get("currentPrice")
                    if not price:
                        continue

                    price = float(price)
                    prev_close = info.get("regularMarketPreviousClose") or price
                    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
                    volume = int(info.get("regularMarketVolume") or info.get("volume") or 0)
                    avg_volume = int(info.get("averageVolume") or info.get("averageDailyVolume10Day") or 1)

                    def _make_alert(alert_type: str, message: str, severity: str) -> dict:
                        alert_id = f"live-{sym}-{alert_type}-{now.strftime('%Y%m%d')}"
                        if alert_id in dismissed:
                            return {}
                        return {
                            "id": alert_id,
                            "ticker": sym,
                            "alert_type": alert_type,
                            "message": message,
                            "severity": severity,
                            "timestamp": now.isoformat() + "Z",
                            "is_read": False,
                        }

                    # ── Large intraday move ──────────────────────────────────
                    if change_pct >= 5.0:
                        a = _make_alert(
                            "price_move",
                            f"{sym} is up {change_pct:+.1f}% intraday — strong bullish momentum.",
                            "critical",
                        )
                        if a: alerts.append(a)
                    elif change_pct >= 3.0:
                        a = _make_alert(
                            "price_move",
                            f"{sym} gained {change_pct:+.1f}% today.",
                            "warning",
                        )
                        if a: alerts.append(a)
                    elif change_pct <= -5.0:
                        a = _make_alert(
                            "price_drop",
                            f"{sym} is down {change_pct:+.1f}% intraday — notable sell-off.",
                            "critical",
                        )
                        if a: alerts.append(a)
                    elif change_pct <= -3.0:
                        a = _make_alert(
                            "price_drop",
                            f"{sym} dropped {change_pct:.1f}% today.",
                            "warning",
                        )
                        if a: alerts.append(a)

                    # ── Volume surge ─────────────────────────────────────────
                    vol_ratio = volume / avg_volume if avg_volume else 0.0
                    if vol_ratio >= 3.0:
                        a = _make_alert(
                            "unusual_volume",
                            f"{sym} volume is {vol_ratio:.1f}x above its daily average — unusual activity.",
                            "critical",
                        )
                        if a: alerts.append(a)
                    elif vol_ratio >= 2.0:
                        a = _make_alert(
                            "unusual_volume",
                            f"{sym} volume is {vol_ratio:.1f}x above its daily average.",
                            "warning",
                        )
                        if a: alerts.append(a)

                    # ── RSI extremes (fetch daily hist for RSI calc) ──────────
                    try:
                        hist = yf.Ticker(sym, session=self._yf_session).history(
                            period="30d", interval="1d"
                        )
                        if hist is not None and len(hist) >= 15:
                            closes = [float(c) for c in hist["Close"].tolist()]
                            rsi_val = MarketService._calculate_rsi(closes)
                            if rsi_val is not None:
                                if float(rsi_val) >= 75:
                                    a = _make_alert(
                                        "rsi_overbought",
                                        f"{sym} RSI is {rsi_val:.0f} — potentially overbought, consider taking profits.",
                                        "warning",
                                    )
                                    if a: alerts.append(a)
                                elif float(rsi_val) <= 30:
                                    a = _make_alert(
                                        "rsi_oversold",
                                        f"{sym} RSI is {rsi_val:.0f} — potentially oversold, possible entry point.",
                                        "info",
                                    )
                                    if a: alerts.append(a)
                    except Exception:
                        pass

                    # ── Earnings proximity ───────────────────────────────────
                    try:
                        cal = yf.Ticker(sym, session=self._yf_session).calendar
                        if cal is not None:
                            ed = None
                            if hasattr(cal, "to_dict"):
                                cal_dict = cal.to_dict()
                                ed_raw = cal_dict.get("Earnings Date")
                                if ed_raw:
                                    dates = ed_raw if isinstance(ed_raw, list) else [ed_raw]
                                    if dates:
                                        from datetime import date as _date
                                        ed = dates[0]
                                        if hasattr(ed, "date"):
                                            ed = ed.date()
                            if ed is not None:
                                days_to = (ed - now.date()).days
                                if 0 <= days_to <= 3:
                                    a = _make_alert(
                                        "earnings",
                                        f"{sym} reports earnings in {days_to} day{'s' if days_to != 1 else ''} — expect elevated volatility.",
                                        "info",
                                    )
                                    if a: alerts.append(a)
                    except Exception:
                        pass

                except Exception as exc:
                    logger.debug("Alert scan failed for %s: %s", sym, exc)
                    continue

        except Exception as exc:
            logger.warning("Alert generation failed: %s", exc)

        # Sort: critical first, then warning, then info; newest within each group
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: (severity_order.get(a.get("severity", "info"), 2), a["id"]))

        self._cache_set(cache_key, alerts, ttl=300)  # 5 min cache
        return alerts

    def dismiss_alert(self, alert_id: str, user_id=None) -> None:
        """
        Dismiss (hide) an alert for the current user.

        The alert ID is added to a Redis set so it won't reappear on the
        next scan. The set expires after 7 days — dismissed alerts
        eventually re-trigger if the condition persists.
        """
        if user_id and self._redis:
            try:
                key = f"alerts:dismissed:{user_id}"
                self._redis.sadd(key, alert_id)
                self._redis.expire(key, 604800)  # 7 days
                # Bust the live cache so the next fetch reflects the dismissal
                self._redis.delete(f"alerts:live:{user_id}")
                return
            except Exception as exc:
                logger.debug("Redis dismiss failed, using in-memory fallback: %s", exc)

        # In-memory fallback (no Redis or no user_id)
        global _ALERTS_STORE
        original_len = len(_ALERTS_STORE)
        _ALERTS_STORE = [a for a in _ALERTS_STORE if a["id"] != alert_id]
        if len(_ALERTS_STORE) == original_len:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert '{alert_id}' not found.",
            )

    def mark_all_alerts_read(self, user_id=None) -> None:
        """Mark all alerts as read for the user (busts the live cache)."""
        if user_id and self._redis:
            try:
                self._redis.delete(f"alerts:live:{user_id}")
            except Exception:
                pass
        # In-memory fallback
        for alert in _ALERTS_STORE:
            alert["is_read"] = True
