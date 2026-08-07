"""
Daily Market Brief Dashboard

Provides an integrated daily dashboard combining:
- Top 10 gainers and losers (side-by-side)
- 5 most important news stories with sentiment indicators
- Daily predictions for watchlist stocks with confidence scores

Layout: 3-column (left: top movers, center: news, right: predictions)

Requirements implemented:
- Requirement 4.1: "Daily Market Brief" as default landing page
- Requirement 4.2: Top 10 gainers/losers side-by-side
- Requirement 4.3: 5 most important news stories with sentiment
- Requirement 4.4: Daily predictions with confidence scores
- Requirement 4.12: Dashboard loads within 2 seconds (via caching)
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Streamlit / Plotly – graceful degradation when not installed
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available – dashboard will not render")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available – charts will not render")

# ---------------------------------------------------------------------------
# Internal imports – each wrapped so the dashboard degrades gracefully
# ---------------------------------------------------------------------------
try:
    from stockiq.data.models import TopMover, EnrichedNewsArticle, NewsCategory
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False

try:
    from stockiq.data.collectors.market import MarketDataCollector
    MARKET_COLLECTOR_AVAILABLE = True
except ImportError:
    MARKET_COLLECTOR_AVAILABLE = False

try:
    from stockiq.data.processors.movers import TopMoversCalculator
    MOVERS_AVAILABLE = True
except ImportError:
    MOVERS_AVAILABLE = False

try:
    from stockiq.data.collectors.news import NewsCollector
    NEWS_COLLECTOR_AVAILABLE = True
except ImportError:
    NEWS_COLLECTOR_AVAILABLE = False

try:
    from stockiq.models.ensemble.predictor import Prediction
    from stockiq.core.prediction_log import PredictionLogger
    PREDICTION_AVAILABLE = True
except ImportError:
    PREDICTION_AVAILABLE = False

try:
    from stockiq.infrastructure.cache import get_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOP_MOVERS_LIMIT = 10       # gainers + losers each
NEWS_DISPLAY_LIMIT = 5      # top news stories shown
DASHBOARD_CACHE_TTL = 300   # 5 min cache – keeps load time < 2 s

# Sentiment colour thresholds
_SENTIMENT_POS_THRESHOLD = 0.15
_SENTIMENT_NEG_THRESHOLD = -0.15

# Category badge colours
_CATEGORY_COLOURS: Dict[str, str] = {
    "Strong Buy":  "#00c853",
    "Buy":         "#69f0ae",
    "Hold":        "#ffd740",
    "Sell":        "#ff6d00",
    "Strong Sell": "#d50000",
}

# ---------------------------------------------------------------------------
# Demo / mock data (used when live data sources are unavailable)
# ---------------------------------------------------------------------------

def _demo_gainers() -> List[Dict[str, Any]]:
    """Return sample gainer rows for UI development / offline use."""
    return [
        {"ticker": "NVDA", "name": "NVIDIA Corp", "price_change_pct": 8.42,
         "current_price": 875.30, "volume": 45_200_000, "avg_volume": 32_000_000,
         "sector": "Technology", "has_unusual_volume": True},
        {"ticker": "META", "name": "Meta Platforms", "price_change_pct": 5.91,
         "current_price": 512.70, "volume": 22_100_000, "avg_volume": 18_000_000,
         "sector": "Technology", "has_unusual_volume": False},
        {"ticker": "AMD",  "name": "Advanced Micro Devices", "price_change_pct": 4.75,
         "current_price": 164.50, "volume": 61_000_000, "avg_volume": 48_000_000,
         "sector": "Technology", "has_unusual_volume": False},
        {"ticker": "AMZN", "name": "Amazon.com Inc", "price_change_pct": 3.60,
         "current_price": 186.20, "volume": 35_000_000, "avg_volume": 30_000_000,
         "sector": "Consumer Cyclical", "has_unusual_volume": False},
        {"ticker": "TSLA", "name": "Tesla Inc", "price_change_pct": 3.10,
         "current_price": 242.80, "volume": 110_000_000, "avg_volume": 95_000_000,
         "sector": "Consumer Cyclical", "has_unusual_volume": False},
        {"ticker": "MSFT", "name": "Microsoft Corp", "price_change_pct": 2.85,
         "current_price": 421.60, "volume": 18_000_000, "avg_volume": 22_000_000,
         "sector": "Technology", "has_unusual_volume": False},
        {"ticker": "GOOGL","name": "Alphabet Inc", "price_change_pct": 2.43,
         "current_price": 169.90, "volume": 20_000_000, "avg_volume": 25_000_000,
         "sector": "Communication Services", "has_unusual_volume": False},
        {"ticker": "AAPL", "name": "Apple Inc", "price_change_pct": 1.97,
         "current_price": 196.30, "volume": 52_000_000, "avg_volume": 55_000_000,
         "sector": "Technology", "has_unusual_volume": False},
        {"ticker": "JPM",  "name": "JPMorgan Chase", "price_change_pct": 1.62,
         "current_price": 210.40, "volume": 8_000_000, "avg_volume": 9_000_000,
         "sector": "Financial Services", "has_unusual_volume": False},
        {"ticker": "V",    "name": "Visa Inc", "price_change_pct": 1.28,
         "current_price": 282.10, "volume": 5_500_000, "avg_volume": 6_000_000,
         "sector": "Financial Services", "has_unusual_volume": False},
    ]


def _demo_losers() -> List[Dict[str, Any]]:
    """Return sample loser rows for UI development / offline use."""
    return [
        {"ticker": "INTC", "name": "Intel Corp", "price_change_pct": -7.30,
         "current_price": 31.20, "volume": 55_000_000, "avg_volume": 42_000_000,
         "sector": "Technology", "has_unusual_volume": True},
        {"ticker": "PFE",  "name": "Pfizer Inc", "price_change_pct": -5.82,
         "current_price": 27.45, "volume": 30_000_000, "avg_volume": 22_000_000,
         "sector": "Healthcare", "has_unusual_volume": True},
        {"ticker": "CVS",  "name": "CVS Health Corp", "price_change_pct": -4.51,
         "current_price": 53.10, "volume": 12_000_000, "avg_volume": 9_000_000,
         "sector": "Healthcare", "has_unusual_volume": False},
        {"ticker": "WBA",  "name": "Walgreens Boots Alliance", "price_change_pct": -3.95,
         "current_price": 15.70, "volume": 9_000_000, "avg_volume": 8_000_000,
         "sector": "Healthcare", "has_unusual_volume": False},
        {"ticker": "MPW",  "name": "Medical Properties Trust", "price_change_pct": -3.40,
         "current_price": 4.85, "volume": 11_000_000, "avg_volume": 10_000_000,
         "sector": "Real Estate", "has_unusual_volume": False},
        {"ticker": "T",    "name": "AT&T Inc", "price_change_pct": -2.87,
         "current_price": 17.35, "volume": 40_000_000, "avg_volume": 38_000_000,
         "sector": "Communication Services", "has_unusual_volume": False},
        {"ticker": "VZ",   "name": "Verizon Communications", "price_change_pct": -2.34,
         "current_price": 39.20, "volume": 18_000_000, "avg_volume": 17_000_000,
         "sector": "Communication Services", "has_unusual_volume": False},
        {"ticker": "WMT",  "name": "Walmart Inc", "price_change_pct": -1.90,
         "current_price": 68.80, "volume": 8_500_000, "avg_volume": 9_000_000,
         "sector": "Consumer Defensive", "has_unusual_volume": False},
        {"ticker": "KO",   "name": "Coca-Cola Co", "price_change_pct": -1.45,
         "current_price": 59.40, "volume": 13_000_000, "avg_volume": 14_000_000,
         "sector": "Consumer Defensive", "has_unusual_volume": False},
        {"ticker": "MO",   "name": "Altria Group Inc", "price_change_pct": -1.12,
         "current_price": 42.60, "volume": 7_000_000, "avg_volume": 7_500_000,
         "sector": "Consumer Defensive", "has_unusual_volume": False},
    ]


def _demo_news() -> List[Dict[str, Any]]:
    """Return sample news items for UI development / offline use."""
    now = datetime.utcnow()
    return [
        {"title": "Fed Signals Rate Cut Possible in Q3 as Inflation Cools",
         "source": "Reuters", "published_at": now - timedelta(minutes=15),
         "sentiment": 0.62, "category": "economic", "is_breaking": True,
         "summary": "Federal Reserve officials indicated a rate reduction may be appropriate "
                    "in the third quarter as recent CPI data showed inflation easing toward "
                    "the 2% target. Markets rallied on the news.",
         "tickers": ["SPY", "QQQ"], "url": "#"},
        {"title": "NVIDIA Beats Q1 Estimates; Data-Centre Revenue Surges 427%",
         "source": "Bloomberg", "published_at": now - timedelta(hours=1),
         "sentiment": 0.85, "category": "earnings", "is_breaking": False,
         "summary": "NVIDIA reported Q1 earnings of $6.12 per share, smashing consensus of "
                    "$5.59. Data-centre revenue of $22.6 billion surged 427% year-over-year, "
                    "driven by AI chip demand.",
         "tickers": ["NVDA"], "url": "#"},
        {"title": "Intel Cuts Guidance Amid Foundry Transition Delays",
         "source": "WSJ", "published_at": now - timedelta(hours=2),
         "sentiment": -0.74, "category": "earnings", "is_breaking": False,
         "summary": "Intel lowered its full-year revenue guidance citing delays in its "
                    "18A process node and slower-than-expected foundry customer wins. "
                    "Shares fell sharply in pre-market trading.",
         "tickers": ["INTC"], "url": "#"},
        {"title": "Amazon Expands AWS Healthcare Cloud with $3.9B Acquisition",
         "source": "CNBC", "published_at": now - timedelta(hours=3),
         "sentiment": 0.48, "category": "M&A", "is_breaking": False,
         "summary": "Amazon Web Services announced the acquisition of a leading healthcare "
                    "data platform for $3.9 billion, expanding its position in the rapidly "
                    "growing cloud-based medical records market.",
         "tickers": ["AMZN"], "url": "#"},
        {"title": "SEC Approves New Crypto Custody Rules for Registered Advisers",
         "source": "FT", "published_at": now - timedelta(hours=4),
         "sentiment": -0.12, "category": "regulatory", "is_breaking": False,
         "summary": "The SEC finalized rules requiring registered investment advisers to use "
                    "qualified custodians for crypto assets, with an 18-month compliance "
                    "window. Industry groups called the rules overly prescriptive.",
         "tickers": ["COIN", "BTC-USD"], "url": "#"},
    ]


def _demo_predictions() -> List[Dict[str, Any]]:
    """Return sample predictions for UI development / offline use."""
    return [
        {"ticker": "AAPL", "category": "Buy",        "confidence": 74.5,
         "value": 0.022,  "lower_bound": 0.008,  "upper_bound": 0.036,
         "low_confidence": False},
        {"ticker": "MSFT", "category": "Strong Buy", "confidence": 81.2,
         "value": 0.031,  "lower_bound": 0.019,  "upper_bound": 0.043,
         "low_confidence": False},
        {"ticker": "GOOGL","category": "Hold",       "confidence": 55.1,
         "value": 0.004,  "lower_bound": -0.012, "upper_bound": 0.020,
         "low_confidence": True},
        {"ticker": "TSLA", "category": "Sell",       "confidence": 68.0,
         "value": -0.025, "lower_bound": -0.041, "upper_bound": -0.009,
         "low_confidence": False},
        {"ticker": "AMZN", "category": "Buy",        "confidence": 72.8,
         "value": 0.019,  "lower_bound": 0.005,  "upper_bound": 0.033,
         "low_confidence": False},
        {"ticker": "NVDA", "category": "Strong Buy", "confidence": 88.3,
         "value": 0.047,  "lower_bound": 0.031,  "upper_bound": 0.063,
         "low_confidence": False},
        {"ticker": "META", "category": "Buy",        "confidence": 77.4,
         "value": 0.028,  "lower_bound": 0.012,  "upper_bound": 0.044,
         "low_confidence": False},
        {"ticker": "JPM",  "category": "Hold",       "confidence": 61.9,
         "value": 0.007,  "lower_bound": -0.005, "upper_bound": 0.019,
         "low_confidence": False},
    ]


# ---------------------------------------------------------------------------
# Data-fetch helpers (with caching and graceful fallback to demo data)
# ---------------------------------------------------------------------------

def _cache_get(key: str) -> Optional[Any]:
    """Attempt a Redis cache read; return None on any failure."""
    if not CACHE_AVAILABLE:
        return None
    try:
        cache = get_cache()
        return cache.get(key)
    except Exception:
        return None


def _cache_set(key: str, value: Any, ttl: int = DASHBOARD_CACHE_TTL) -> None:
    """Attempt a Redis cache write; silently swallow errors."""
    if not CACHE_AVAILABLE:
        return
    try:
        cache = get_cache()
        cache.set(key, value, ttl=ttl)
    except Exception:
        pass


def _fetch_top_movers() -> tuple[List[Dict], List[Dict]]:
    """
    Return (gainers, losers) as lists of plain dicts.

    Tries live data first (MarketDataCollector → TopMoversCalculator),
    falls back to demo data when any dependency is unavailable or errors.
    """
    cache_key = f"dashboard:top_movers:{date.today().isoformat()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached.get("gainers", []), cached.get("losers", [])

    if not MARKET_COLLECTOR_AVAILABLE or not MOVERS_AVAILABLE:
        return _demo_gainers(), _demo_losers()

    try:
        collector = MarketDataCollector()
        calculator = TopMoversCalculator()

        # Build a universe of tickers (S&P 500 proxy).  A production system
        # would load these from the database; here we use a capped list so the
        # dashboard stays responsive.
        from stockiq.data.tickers import get_sp500_tickers  # type: ignore
        tickers = get_sp500_tickers()[:100]

        # One consolidated quote per ticker → real price change (trend) and
        # volume ("purchases") in a single call each.
        stocks_data = collector.get_bulk_daily_quotes(tickers)

        if not stocks_data:
            return _demo_gainers(), _demo_losers()

        gainers = calculator.identify_top_gainers(stocks_data, limit=TOP_MOVERS_LIMIT)
        losers  = calculator.identify_top_losers(stocks_data,  limit=TOP_MOVERS_LIMIT)

        def _mover_to_dict(m: "TopMover") -> Dict:
            return {
                "ticker": m.ticker,
                "name": m.name,
                "price_change_pct": m.price_change_pct,
                "current_price": float(m.current_price),
                "volume": m.volume,
                "avg_volume": m.avg_volume,
                "sector": m.sector,
                "has_unusual_volume": m.has_unusual_volume(),
            }

        g_dicts = [_mover_to_dict(g) for g in gainers]
        l_dicts = [_mover_to_dict(l) for l in losers]
        _cache_set(cache_key, {"gainers": g_dicts, "losers": l_dicts})
        return g_dicts, l_dicts

    except Exception as exc:
        logger.warning("fetch_top_movers_failed: %s – using demo data", exc)
        return _demo_gainers(), _demo_losers()


def _fetch_top_news(limit: int = NEWS_DISPLAY_LIMIT) -> List[Dict[str, Any]]:
    """
    Return top news articles as plain dicts.

    Ranked by |sentiment| * recency weighting.  Falls back to demo data.
    """
    cache_key = f"dashboard:top_news:{date.today().isoformat()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached[:limit]

    if not NEWS_COLLECTOR_AVAILABLE:
        return _demo_news()[:limit]

    try:
        collector = NewsCollector()
        articles = collector.collect_latest_news(limit=50)

        def _article_score(a: "EnrichedNewsArticle") -> float:
            """Rank by sentiment magnitude * recency (decay over 24h)."""
            age_h = (datetime.utcnow() - a.published_at).total_seconds() / 3600
            sentiment = abs(a.sentiment.overall) if a.sentiment else 0.0
            recency = max(0.0, 1.0 - age_h / 24.0)
            breaking_bonus = 0.3 if a.is_breaking() else 0.0
            return sentiment * recency + breaking_bonus

        articles_sorted = sorted(articles, key=_article_score, reverse=True)

        result = []
        for a in articles_sorted[:limit]:
            result.append({
                "title": a.title,
                "source": a.source,
                "published_at": a.published_at,
                "sentiment": a.sentiment.overall if a.sentiment else 0.0,
                "category": a.category.value if a.category else "general",
                "is_breaking": a.is_breaking(),
                "summary": a.summary or a.content[:200],
                "tickers": a.tickers,
                "url": a.url,
            })

        _cache_set(cache_key, result)
        return result

    except Exception as exc:
        logger.warning("fetch_top_news_failed: %s – using demo data", exc)
        return _demo_news()[:limit]


def _demo_predictions_labeled() -> List[Dict[str, Any]]:
    """Demo predictions flagged as sample data so the UI can label them."""
    return [{**d, "is_sample": True} for d in _demo_predictions()]


# Module-level cache so the trained model is loaded at most once per process.
_PREDICTOR_INSTANCE: Any = None
_PREDICTOR_LOADED: bool = False


def _get_predictor() -> Any:
    """
    Load the trained EnsemblePredictor from cache (once per process).

    Returns the predictor instance, or None when no trained model is available.
    """
    global _PREDICTOR_INSTANCE, _PREDICTOR_LOADED
    if _PREDICTOR_LOADED:
        return _PREDICTOR_INSTANCE

    _PREDICTOR_LOADED = True
    if not PREDICTION_AVAILABLE:
        return None

    try:
        from stockiq.models.ensemble.predictor import EnsemblePredictor
        _PREDICTOR_INSTANCE = EnsemblePredictor.load_from_cache()
        if _PREDICTOR_INSTANCE is None:
            logger.info("no_trained_model_cached – predictions will use sample data")
    except Exception as exc:
        logger.warning("predictor_load_failed: %s", exc)
        _PREDICTOR_INSTANCE = None

    return _PREDICTOR_INSTANCE


def _reset_predictor_cache() -> None:
    """Force the next prediction call to reload the model (e.g. after training)."""
    global _PREDICTOR_INSTANCE, _PREDICTOR_LOADED
    _PREDICTOR_INSTANCE = None
    _PREDICTOR_LOADED = False


def _real_prediction(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Generate a real next-day return prediction for a ticker using the trained
    ensemble model and live feature data.

    Returns a display-ready dict (is_sample=False) or None when a real
    prediction cannot be produced (no model, missing features, etc.).
    """
    predictor = _get_predictor()
    if predictor is None or not getattr(predictor, "is_trained", False):
        return None

    try:
        from stockiq.models.features import create_feature_matrix

        X = create_feature_matrix(ticker)
        if X is None or X.empty:
            return None

        # Align to the exact features the model was trained on, newest row only.
        feature_names = list(getattr(predictor, "feature_names", []) or [])
        if feature_names:
            missing = [c for c in feature_names if c not in X.columns]
            if missing:
                logger.warning(
                    "feature_mismatch for %s, missing=%s", ticker, missing[:5]
                )
                return None
            X_latest = X[feature_names].tail(1)
        else:
            X_latest = X.tail(1)

        preds = predictor.predict(X_latest)
        if not preds:
            return None

        p = preds[0]
        return {
            "ticker": ticker,
            "category": p.category,
            "confidence": round(float(p.confidence), 1),
            "value": float(p.value),
            "lower_bound": float(p.lower_bound),
            "upper_bound": float(p.upper_bound),
            "low_confidence": bool(p.low_confidence),
            "is_sample": False,
        }
    except Exception as exc:
        logger.warning("real_prediction_failed for %s: %s", ticker, exc)
        return None


def _fetch_predictions(watchlist: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Return prediction dicts for watchlist stocks.

    Uses the trained EnsemblePredictor with live feature data when available.
    Falls back to clearly-labelled sample data when no trained model exists.
    """
    tickers = watchlist or [d["ticker"] for d in _demo_predictions()]

    results: List[Dict[str, Any]] = []
    for ticker in tickers:
        pred = _real_prediction(ticker)
        if pred:
            results.append(pred)

    if results:
        return results

    # No real predictions available – show sample data, honestly labelled.
    return _demo_predictions_labeled()


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _sentiment_badge(score: float) -> str:
    """Return a coloured emoji badge for a sentiment score."""
    if score > _SENTIMENT_POS_THRESHOLD:
        return "🟢"
    if score < _SENTIMENT_NEG_THRESHOLD:
        return "🔴"
    return "🟡"


def _sentiment_label(score: float) -> str:
    if score > _SENTIMENT_POS_THRESHOLD:
        return f"Positive ({score:+.2f})"
    if score < _SENTIMENT_NEG_THRESHOLD:
        return f"Negative ({score:+.2f})"
    return f"Neutral ({score:+.2f})"


def _category_colour(category: str) -> str:
    return _CATEGORY_COLOURS.get(category, "#9e9e9e")


def _pct_colour(pct: float) -> str:
    return "#00c853" if pct >= 0 else "#d50000"


def _fmt_volume(v: int) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.0f}K"
    return str(v)


def _fmt_price(p: float) -> str:
    return f"${p:,.2f}"


def _fmt_pct(p: float) -> str:
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"


def _time_ago(dt: datetime) -> str:
    delta = datetime.utcnow() - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return dt.strftime("%b %d")


def _confidence_colour(conf: float) -> str:
    if conf >= 75:
        return "#00c853"
    if conf >= 60:
        return "#ffd740"
    return "#ff6d00"


def _return_pct(value: float) -> str:
    pct = value * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"


def _trend_arrow(pct: float) -> str:
    """Return an up/down/flat arrow emoji based on the price-change trend."""
    if pct > 0:
        return "🔼"
    if pct < 0:
        return "🔽"
    return "➖"


# ---------------------------------------------------------------------------
# Section: Top Movers
# ---------------------------------------------------------------------------

def _fetch_ticker_quote(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single ticker's daily quote (real data, demo fallback).

    Returns a dict with ticker, name, current_price, price_change_pct, volume,
    etc. — or None when the symbol cannot be resolved.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return None

    if MARKET_COLLECTOR_AVAILABLE:
        try:
            collector = MarketDataCollector()
            quote = collector.get_daily_quote(ticker)
            if quote:
                return quote
        except Exception as exc:
            logger.warning("ticker_quote_failed for %s: %s", ticker, exc)

    # Fallback: look the ticker up in the demo movers.
    for stock in _demo_gainers() + _demo_losers():
        if stock.get("ticker") == ticker:
            return stock
    return None


def _get_ticker_news(ticker: str) -> List[Dict[str, Any]]:
    """Fetch news for a specific ticker."""
    cache_key = f"ticker_news:{ticker}:{date.today().isoformat()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    
    if not NEWS_COLLECTOR_AVAILABLE:
        # Return demo news filtered for ticker
        all_news = _demo_news()
        return [n for n in all_news if ticker in n.get("tickers", [])][:3]
    
    try:
        collector = NewsCollector()
        articles = collector.collect_ticker_news(ticker, hours=24)
        
        result = []
        for a in articles[:3]:  # Top 3 news items
            result.append({
                "title": a.title,
                "source": a.source,
                "published_at": a.published_at,
                "sentiment": a.sentiment.overall if a.sentiment else 0.0,
                "summary": a.summary or a.content[:200],
                "url": a.url,
            })
        
        _cache_set(cache_key, result, ttl=600)  # 10 min cache
        return result
    except Exception:
        return []


def _get_ticker_prediction(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch prediction for a specific ticker (real model, sample fallback)."""
    cache_key = f"ticker_prediction:{ticker}:{date.today().isoformat()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Try a real prediction from the trained ensemble model first.
    pred = _real_prediction(ticker)

    if pred is None:
        # Honest fallback: sample data, clearly flagged.
        demo_preds = _demo_predictions()
        match = next((p for p in demo_preds if p["ticker"] == ticker), None)
        pred = {**match, "is_sample": True} if match else None

    if pred:
        _cache_set(cache_key, pred, ttl=3600)  # 1 hour cache

    return pred


def _render_ticker_details(ticker: str, name: str, is_gainer: bool):
    """Render detailed ticker information in an expander."""
    st.markdown("---")
    
    # Get news and prediction
    news_items = _get_ticker_news(ticker)
    prediction = _get_ticker_prediction(ticker)
    
    # News explanation section
    st.markdown("#### 📰 Why is it moving?")
    
    if news_items:
        for news in news_items:
            sentiment = news.get("sentiment", 0.0)
            badge = _sentiment_badge(sentiment)
            title = news.get("title", "")
            source = news.get("source", "")
            summary = news.get("summary", "")
            published = news.get("published_at", datetime.utcnow())
            
            st.markdown(f"{badge} **{title}**")
            st.caption(f"{source} · {_time_ago(published)}")
            if summary:
                st.markdown(f"*{summary}*")
            st.markdown("")
    else:
        direction = "up" if is_gainer else "down"
        st.info(f"No specific news found. The movement may be due to general market sentiment or technical factors pushing {ticker} {direction}.")
    
    # Prediction section
    st.markdown("#### 🔮 Prediction")
    
    if prediction:
        if prediction.get("is_sample"):
            st.caption("⚠️ Sample prediction — train the ensemble model for live forecasts.")
        category = prediction.get("category", "Hold")
        confidence = prediction.get("confidence", 0.0)
        value = prediction.get("value", 0.0)
        lower_bound = prediction.get("lower_bound", 0.0)
        upper_bound = prediction.get("upper_bound", 0.0)
        
        cat_colour = _category_colour(category)
        conf_colour = _confidence_colour(confidence)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Signal",
                category,
                help="AI-generated trading signal"
            )
        with col2:
            st.metric(
                "Confidence",
                f"{confidence:.1f}%",
                help="Model confidence in this prediction"
            )
        with col3:
            st.metric(
                "Expected Return",
                _return_pct(value),
                help="Predicted next-day return"
            )
        
        # Confidence bar
        st.progress(confidence / 100, text=f"Confidence: {confidence:.1f}%")
        
        # Range
        st.markdown(
            f"**Predicted Range:** {_return_pct(lower_bound)} to {_return_pct(upper_bound)}"
        )
        
        # Recommendation
        if category in ["Strong Buy", "Buy"]:
            st.success(f"💡 **{category}** - Model suggests upside potential")
        elif category in ["Strong Sell", "Sell"]:
            st.error(f"⚠️ **{category}** - Model suggests downside risk")
        else:
            st.info(f"➡️ **{category}** - Model suggests waiting for clearer signal")
        
        if confidence < 60:
            st.warning("⚠️ Low confidence - Use caution with this prediction")
    else:
        st.info("No prediction available for this ticker at this time.")


def render_stock_search_section() -> None:
    """
    Render a stock search box that shows full details for any ticker.

    On submit, displays the ticker's trend (up/down arrow), price/volume,
    the "why it's moving" news explanation, and the prediction — the same
    detail view used for top movers.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render stock search section")
        return

    st.subheader("🔍 Search a Stock")
    st.caption("Enter a ticker to see its trend, the news behind it, and a prediction")

    with st.form("stock_search_form", clear_on_submit=False):
        col_in, col_btn = st.columns([4, 1])
        with col_in:
            query = st.text_input(
                "Ticker symbol",
                placeholder="e.g. AAPL, TSLA, NVDA",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Search", use_container_width=True)

    if not (submitted and query):
        return

    ticker = query.strip().upper()
    with st.spinner(f"Fetching {ticker}…"):
        quote = _fetch_ticker_quote(ticker)

    if not quote:
        st.error(
            f"Couldn't find data for '{ticker}'. Check the symbol and try again."
        )
        return

    pct   = quote.get("price_change_pct", 0.0)
    name  = quote.get("name", ticker)
    price = quote.get("current_price", 0.0)
    vol   = quote.get("volume", 0)
    arrow = _trend_arrow(pct)
    colour = "#00c853" if pct >= 0 else "#d50000"

    st.markdown(f"### {ticker} {arrow} {name}")
    st.markdown(
        f"**Current Price:** {_fmt_price(price)} | "
        f"**Change:** <span style='color:{colour};font-weight:bold'>{_fmt_pct(pct)}</span> | "
        f"**Volume:** {_fmt_volume(vol)}",
        unsafe_allow_html=True,
    )

    # Reuse the shared detail view (news + prediction).
    _render_ticker_details(ticker, name, is_gainer=(pct >= 0))


def render_top_movers_section() -> None:
    """
    Render the Top Movers section with clickable tickers.

    Displays top 10 gainers and top 10 losers side-by-side using st.columns.
    When a ticker is clicked, shows news explanation and prediction.
    
    Requirement 4.2: Top 10 gainers/losers in side-by-side layout.
    Enhancement: Interactive ticker cards with news and predictions on click.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render top movers section")
        return

    st.subheader("📈 Top Movers")
    st.caption("Click any ticker to see why it's moving and get predictions")

    gainers, losers = _fetch_top_movers()

    col_gain, col_lose = st.columns(2)

    with col_gain:
        st.markdown("### 🟢 Top 10 Gainers")
        for i, stock in enumerate(gainers[:TOP_MOVERS_LIMIT], start=1):
            pct = stock.get("price_change_pct", 0.0)
            ticker = stock.get("ticker", "N/A")
            name   = stock.get("name", "")
            price  = stock.get("current_price", 0.0)
            vol    = stock.get("volume", 0)
            avg_vol= stock.get("avg_volume", 0)
            unusual = stock.get("has_unusual_volume", False)

            vol_badge = " 🔥" if unusual else ""
            
            # Use expander for each ticker to make it clickable
            with st.expander(
                f"**{i}. {ticker}** {_trend_arrow(pct)} {_fmt_pct(pct)}  ·  Vol {_fmt_volume(vol)}{vol_badge}",
                expanded=False
            ):
                # Ticker header
                st.markdown(f"### {ticker} {_trend_arrow(pct)} {name}")
                st.markdown(
                    f"**Current Price:** {_fmt_price(price)} | "
                    f"**Change:** <span style='color:#00c853;font-weight:bold'>{_fmt_pct(pct)}</span> | "
                    f"**Volume:** {_fmt_volume(vol)}",
                    unsafe_allow_html=True
                )
                
                # Show details
                _render_ticker_details(ticker, name, is_gainer=True)

    with col_lose:
        st.markdown("### 🔴 Top 10 Losers")
        for i, stock in enumerate(losers[:TOP_MOVERS_LIMIT], start=1):
            pct = stock.get("price_change_pct", 0.0)
            ticker = stock.get("ticker", "N/A")
            name   = stock.get("name", "")
            price  = stock.get("current_price", 0.0)
            vol    = stock.get("volume", 0)
            unusual = stock.get("has_unusual_volume", False)

            vol_badge = " 🔥" if unusual else ""
            
            # Use expander for each ticker to make it clickable
            with st.expander(
                f"**{i}. {ticker}** {_trend_arrow(pct)} {_fmt_pct(pct)}  ·  Vol {_fmt_volume(vol)}{vol_badge}",
                expanded=False
            ):
                # Ticker header
                st.markdown(f"### {ticker} {_trend_arrow(pct)} {name}")
                st.markdown(
                    f"**Current Price:** {_fmt_price(price)} | "
                    f"**Change:** <span style='color:#d50000;font-weight:bold'>{_fmt_pct(pct)}</span> | "
                    f"**Volume:** {_fmt_volume(vol)}",
                    unsafe_allow_html=True
                )
                
                # Show details
                _render_ticker_details(ticker, name, is_gainer=False)


# ---------------------------------------------------------------------------
# Section: News
# ---------------------------------------------------------------------------

def render_news_section() -> None:
    """
    Render the News section.

    Displays 5 most important news stories with colour-coded sentiment
    indicators (🟢 positive, 🔴 negative, 🟡 neutral).
    Requirement 4.3: 5 most important news stories with sentiment.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render news section")
        return

    st.subheader("📰 Market News")

    articles = _fetch_top_news(limit=NEWS_DISPLAY_LIMIT)

    if not articles:
        st.info("No news articles available at this time.")
        return

    for article in articles:
        sentiment = article.get("sentiment", 0.0)
        badge     = _sentiment_badge(sentiment)
        label     = _sentiment_label(sentiment)
        title     = article.get("title", "Untitled")
        source    = article.get("source", "Unknown")
        published = article.get("published_at", datetime.utcnow())
        summary   = article.get("summary", "")
        tickers   = article.get("tickers", [])
        url       = article.get("url", "#")
        category  = article.get("category", "general")
        is_breaking = article.get("is_breaking", False)

        breaking_tag = "🚨 **BREAKING** " if is_breaking else ""

        with st.container():
            st.markdown(
                f"{breaking_tag}{badge} **{title}**",
                unsafe_allow_html=False,
            )

            meta_col, sent_col = st.columns([3, 1])
            with meta_col:
                ticker_str = "  ·  ".join(tickers) if tickers else ""
                ticker_display = f"  ·  `{ticker_str}`" if ticker_str else ""
                st.markdown(
                    f"<span style='font-size:0.8em;color:#aaa'>"
                    f"{source}  ·  {_time_ago(published)}  ·  "
                    f"<em>{category}</em>{ticker_display}"
                    f"</span>",
                    unsafe_allow_html=True,
                )
            with sent_col:
                if sentiment > _SENTIMENT_POS_THRESHOLD:
                    sent_colour = "#00c853"
                elif sentiment < _SENTIMENT_NEG_THRESHOLD:
                    sent_colour = "#d50000"
                else:
                    sent_colour = "#9e9e9e"
                st.markdown(
                    f"<span style='color:{sent_colour};font-size:0.85em'>"
                    f"{label}</span>",
                    unsafe_allow_html=True,
                )

            if summary:
                st.markdown(
                    f"<span style='font-size:0.88em'>{summary}</span>",
                    unsafe_allow_html=True,
                )

            if url and url != "#":
                st.markdown(f"[Read more →]({url})")

            st.divider()


# ---------------------------------------------------------------------------
# Section: Predictions
# ---------------------------------------------------------------------------

def _render_train_model_button() -> None:
    """Render a button that trains and caches the ensemble model on demand."""
    if st.button("🛠️ Train prediction model", help="Fetches live data and trains the ensemble model (~1 min)"):
        try:
            from stockiq.models.ensemble.trainer import train_and_cache_ensemble
        except Exception as exc:
            st.error(f"Training unavailable: {exc}")
            return

        with st.spinner("Training ensemble model on live market data…"):
            result = train_and_cache_ensemble()

        if result.success:
            _reset_predictor_cache()
            # Clear cached sample predictions so live ones are fetched next run.
            _cache_clear_predictions()
            st.success(result.message)
            st.rerun()
        else:
            st.error(result.message)


def _cache_clear_predictions() -> None:
    """Best-effort clear of cached per-ticker prediction entries for today."""
    if not CACHE_AVAILABLE:
        return
    try:
        cache = get_cache()
        today = date.today().isoformat()
        for d in _demo_predictions():
            try:
                cache.delete(f"ticker_prediction:{d['ticker']}:{today}")
            except Exception:
                pass
    except Exception:
        pass


def render_predictions_section() -> None:
    """
    Render the Predictions section.

    Shows daily predictions for watchlist stocks with confidence scores
    displayed as Streamlit progress bars.
    Requirement 4.4: Daily predictions with confidence scores.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render predictions section")
        return

    st.subheader("🔮 Daily Predictions")

    predictions = _fetch_predictions()

    if not predictions:
        st.info("No predictions available at this time.")
        return

    if any(p.get("is_sample") for p in predictions):
        st.caption(
            "⚠️ Showing **sample** predictions — no trained model is available yet. "
            "Train the ensemble model to see live forecasts."
        )
        _render_train_model_button()

    for pred in predictions:
        ticker      = pred.get("ticker", "N/A")
        category    = pred.get("category", "Hold")
        confidence  = pred.get("confidence", 0.0)   # 0-100
        value       = pred.get("value", 0.0)         # expected return as fraction
        low_conf    = pred.get("low_confidence", confidence < 60)
        lower_bound = pred.get("lower_bound", 0.0)
        upper_bound = pred.get("upper_bound", 0.0)

        cat_colour  = _category_colour(category)
        conf_colour = _confidence_colour(confidence)

        header_col, badge_col = st.columns([2, 1])
        with header_col:
            low_flag = " ⚠️ low confidence" if low_conf else ""
            st.markdown(
                f"**{ticker}**"
                f"<span style='font-size:0.8em;color:#aaa'>{low_flag}</span>",
                unsafe_allow_html=True,
            )
        with badge_col:
            st.markdown(
                f"<span style='background:{cat_colour};color:#fff;"
                f"padding:2px 8px;border-radius:4px;font-size:0.82em'>"
                f"{category}</span>",
                unsafe_allow_html=True,
            )

        # Confidence progress bar
        st.progress(
            int(confidence),
            text=f"Confidence: {confidence:.1f}%",
        )

        # Expected return + range
        ret_str = _return_pct(value)
        rng_str = f"[{_return_pct(lower_bound)}, {_return_pct(upper_bound)}]"
        st.markdown(
            f"<span style='font-size:0.82em;color:{_pct_colour(value)}'>"
            f"Expected: **{ret_str}**  "
            f"<span style='color:#aaa'>Range {rng_str}</span>"
            f"</span>",
            unsafe_allow_html=True,
        )

        st.markdown("")   # small spacer


# ---------------------------------------------------------------------------
# Primary render entry point
# ---------------------------------------------------------------------------

def render_daily_dashboard() -> None:
    """
    Render the Daily Market Brief dashboard.

    This is the default landing page for the StockIQ web interface.
    Layout: 3 columns — left (top movers), centre (news), right (predictions).

    Requirement 4.1  : Default landing page
    Requirement 4.2  : Top 10 gainers/losers side-by-side
    Requirement 4.3  : 5 most important news stories with sentiment
    Requirement 4.4  : Daily predictions with confidence scores
    Requirement 4.12 : Loads within 2 seconds (backed by Redis cache / demo data)
    """
    if not STREAMLIT_AVAILABLE:
        logger.error(
            "streamlit not available – render_daily_dashboard() called outside "
            "a Streamlit context; nothing will be rendered."
        )
        return

    # Page header
    today_str = datetime.utcnow().strftime("%A, %B %d, %Y")
    st.title("📊 Daily Market Brief")
    st.caption(f"As of {today_str} UTC  ·  Data refreshes every 5 minutes")
    st.divider()

    # Stock search – full details for any ticker on demand.
    render_stock_search_section()
    st.divider()

    # 3-column layout
    left_col, centre_col, right_col = st.columns([1.4, 1.8, 1.3])

    with left_col:
        render_top_movers_section()

    with centre_col:
        render_news_section()

    with right_col:
        render_predictions_section()


# ---------------------------------------------------------------------------
# Public aliases
# ---------------------------------------------------------------------------
# `app.py` imports the dashboard under this name; keep both available so
# either entry point works.
render_daily_brief_dashboard = render_daily_dashboard
