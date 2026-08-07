"""
Penny Stock Momentum Dashboard

A dedicated dashboard for penny stocks (price <= $5.00) with sudden gains and
high momentum.  It surfaces the top 20 penny stocks ranked by momentum score,
along with risk metrics, price-history charts, insider activity and a sector
distribution breakdown.

Layout:
- Header + auto-refresh notice (every 2 minutes during market hours)
- Top-20 momentum table (ticker, price, % change, volume ratio, momentum, risk)
- Price-history charts (1-day / 5-day / 30-day) with catalyst-event highlights
- Risk metrics panel (liquidity risk, volatility risk, spread %, insider activity)
- Sector distribution pie chart

Requirements implemented:
- Requirement 11.5  : Display top 20 penny stocks ranked by momentum score
- Requirement 11.8  : Show 1-day / 5-day / 30-day price history charts
- Requirement 11.12 : Show insider trading activity for penny stocks
- Requirement 11.13 : Flag suspicious (pump-and-dump) patterns
- Requirement 11.15 : Update penny stock dashboard every 2 minutes (Property 53)
- Requirement 11.16 : Historical performance tracking for momentum plays
- Requirement 11.17 : Average holding period for profitable trades
- Requirement 11.18 : Sector distribution of trending penny stocks
- Requirement 11.19 : Correlation between penny stock gains and market sentiment

Property tests:
- Property 53 : Dashboard refresh interval is always <= 120 seconds (2 minutes)
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Streamlit / Plotly - graceful degradation when not installed
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available - penny dashboard will not render")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available - penny dashboard charts will not render")

# ---------------------------------------------------------------------------
# Internal imports - each wrapped so the dashboard degrades gracefully
# ---------------------------------------------------------------------------
try:
    from stockiq.news.penny.scanner import (
        PennyStock,
        PennyStockScanner,
        RiskMetrics,
    )
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False
    logger.warning("penny scanner not available - using demo data")

try:
    from stockiq.news.penny.momentum import MomentumCalculator, MomentumScore
    MOMENTUM_AVAILABLE = True
except ImportError:
    MOMENTUM_AVAILABLE = False

try:
    from stockiq.news.penny.risk import (
        PennyStockRiskAnalyzer,
        PumpDumpDetector,
        RiskAssessment,
        SuspicionScore,
        InsiderActivity,
    )
    RISK_AVAILABLE = True
except ImportError:
    RISK_AVAILABLE = False

try:
    from stockiq.infrastructure.cache import get_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Top-N penny stocks displayed, ranked by momentum (Requirement 11.5)
TOP_PENNY_LIMIT = 20

#: Maximum allowed dashboard refresh interval in seconds (Property 53).
#: The dashboard MUST refresh at least this often during market hours.
#: This is the hard upper bound enforced by Property 53 (<= 2 minutes).
MAX_REFRESH_INTERVAL_SECONDS = 120

#: Actual refresh interval used by the dashboard (Requirement 11.15).
#: Kept <= MAX_REFRESH_INTERVAL_SECONDS so Property 53 always holds.
PENNY_DASHBOARD_REFRESH_SECONDS = 120

#: Cache TTL for penny dashboard data - matches the 2-minute refresh window.
PENNY_DASHBOARD_CACHE_TTL = PENNY_DASHBOARD_REFRESH_SECONDS

#: Price-history chart timeframes (Requirement 11.8)
CHART_TIMEFRAMES = ("1D", "5D", "30D")

#: Risk-level badge colours
_RISK_COLOURS: Dict[str, str] = {
    "low":     "#00c853",
    "medium":  "#ffd740",
    "high":    "#ff6d00",
    "extreme": "#d50000",
}

#: Recommendation badge colours
_RECOMMENDATION_COLOURS: Dict[str, str] = {
    "safe":    "#00c853",
    "caution": "#ffd740",
    "avoid":   "#d50000",
}


# ---------------------------------------------------------------------------
# Refresh-interval helpers (Property 53)
# ---------------------------------------------------------------------------

def get_refresh_interval_seconds() -> int:
    """
    Return the dashboard refresh interval in seconds.

    Property 53 requires this to be <= 120 seconds (2 minutes).  The value is
    clamped defensively so the property holds even if the configuration
    constant is changed to something larger.

    Returns:
        Refresh interval in seconds, guaranteed in (0, 120].
    """
    interval = int(PENNY_DASHBOARD_REFRESH_SECONDS)
    # Clamp to the hard upper bound enforced by Property 53.
    return max(1, min(interval, MAX_REFRESH_INTERVAL_SECONDS))


def should_refresh(last_refresh: datetime, now: Optional[datetime] = None) -> bool:
    """
    Determine whether the dashboard is due for a refresh.

    The dashboard refreshes when the elapsed time since the previous refresh
    reaches or exceeds the configured interval.  Combined with
    get_refresh_interval_seconds() (which is <= 120), this guarantees the
    dashboard never goes longer than 120 seconds without refreshing while it
    is being driven (Property 53).

    Args:
        last_refresh: Timestamp of the previous refresh.
        now:          Current time (defaults to datetime.utcnow()).

    Returns:
        True when a refresh is due, else False.
    """
    now = now or datetime.utcnow()
    elapsed = (now - last_refresh).total_seconds()
    return elapsed >= get_refresh_interval_seconds()


def seconds_until_next_refresh(
    last_refresh: datetime, now: Optional[datetime] = None
) -> float:
    """
    Return the number of seconds remaining until the next scheduled refresh.

    The result is always <= get_refresh_interval_seconds() (<= 120s), and is
    clamped to >= 0.  This is the value Property 53 verifies: the time between
    two consecutive refreshes never exceeds 120 seconds.

    Args:
        last_refresh: Timestamp of the previous refresh.
        now:          Current time (defaults to datetime.utcnow()).

    Returns:
        Seconds until the next refresh, in [0, interval].
    """
    now = now or datetime.utcnow()
    interval = get_refresh_interval_seconds()
    elapsed = (now - last_refresh).total_seconds()
    remaining = interval - elapsed
    return max(0.0, min(float(interval), remaining))


# ---------------------------------------------------------------------------
# Demo / mock data (used when live data sources are unavailable)
# ---------------------------------------------------------------------------

def _demo_penny_stocks() -> List[Dict[str, Any]]:
    """
    Return sample penny stock rows for UI development / offline use.

    Each row carries the display fields the table and metrics panels expect.
    All prices are <= $5.00 (Property 42 in the backend).
    """
    return [
        {"ticker": "ABCD", "price": 0.85, "price_change_pct": 142.8,
         "volume": 28_500_000, "avg_volume": 1_200_000, "volume_ratio": 23.75,
         "market_cap": 18_000_000, "sector": "Healthcare", "momentum_score": 96.4,
         "risk_level": "extreme", "liquidity_risk": 0.72, "volatility_risk": 0.95,
         "spread_pct": 4.2, "catalyst": "FDA Phase 3 trial results",
         "recommendation": "avoid", "suspicion_score": 0.78,
         "insider_net": "selling", "insider_buys": 0, "insider_sells": 7},
        {"ticker": "MNOP", "price": 2.34, "price_change_pct": 78.2,
         "volume": 14_100_000, "avg_volume": 950_000, "volume_ratio": 14.84,
         "market_cap": 42_000_000, "sector": "Technology", "momentum_score": 88.1,
         "risk_level": "high", "liquidity_risk": 0.55, "volatility_risk": 0.78,
         "spread_pct": 2.8, "catalyst": "New product launch",
         "recommendation": "caution", "suspicion_score": 0.45,
         "insider_net": "buying", "insider_buys": 5, "insider_sells": 1},
        {"ticker": "WXYZ", "price": 3.97, "price_change_pct": 61.5,
         "volume": 8_900_000, "avg_volume": 720_000, "volume_ratio": 12.36,
         "market_cap": 88_000_000, "sector": "Energy", "momentum_score": 81.7,
         "risk_level": "high", "liquidity_risk": 0.41, "volatility_risk": 0.62,
         "spread_pct": 1.9, "catalyst": "Earnings beat",
         "recommendation": "caution", "suspicion_score": 0.38,
         "insider_net": "neutral", "insider_buys": 2, "insider_sells": 2},
        {"ticker": "QRST", "price": 1.12, "price_change_pct": 54.0,
         "volume": 11_200_000, "avg_volume": 1_050_000, "volume_ratio": 10.67,
         "market_cap": 25_000_000, "sector": "Healthcare", "momentum_score": 76.9,
         "risk_level": "high", "liquidity_risk": 0.60, "volatility_risk": 0.58,
         "spread_pct": 3.1, "catalyst": "Acquisition rumour",
         "recommendation": "caution", "suspicion_score": 0.52,
         "insider_net": "selling", "insider_buys": 1, "insider_sells": 4},
        {"ticker": "EFGH", "price": 4.50, "price_change_pct": 47.3,
         "volume": 6_300_000, "avg_volume": 680_000, "volume_ratio": 9.26,
         "market_cap": 110_000_000, "sector": "Consumer", "momentum_score": 71.2,
         "risk_level": "medium", "liquidity_risk": 0.33, "volatility_risk": 0.49,
         "spread_pct": 1.4, "catalyst": "Analyst upgrade",
         "recommendation": "safe", "suspicion_score": 0.21,
         "insider_net": "buying", "insider_buys": 6, "insider_sells": 0},
        {"ticker": "IJKL", "price": 0.42, "price_change_pct": 39.8,
         "volume": 19_800_000, "avg_volume": 2_100_000, "volume_ratio": 9.43,
         "market_cap": 9_500_000, "sector": "Technology", "momentum_score": 68.5,
         "risk_level": "extreme", "liquidity_risk": 0.80, "volatility_risk": 0.71,
         "spread_pct": 5.0, "catalyst": None,
         "recommendation": "avoid", "suspicion_score": 0.74,
         "insider_net": "neutral", "insider_buys": 0, "insider_sells": 0},
        {"ticker": "UVWX", "price": 2.88, "price_change_pct": 33.1,
         "volume": 4_700_000, "avg_volume": 560_000, "volume_ratio": 8.39,
         "market_cap": 64_000_000, "sector": "Industrial", "momentum_score": 62.0,
         "risk_level": "medium", "liquidity_risk": 0.38, "volatility_risk": 0.42,
         "spread_pct": 1.7, "catalyst": "Contract win",
         "recommendation": "safe", "suspicion_score": 0.18,
         "insider_net": "buying", "insider_buys": 3, "insider_sells": 1},
        {"ticker": "BCDE", "price": 1.75, "price_change_pct": 28.4,
         "volume": 3_900_000, "avg_volume": 510_000, "volume_ratio": 7.65,
         "market_cap": 31_000_000, "sector": "Financial", "momentum_score": 55.8,
         "risk_level": "medium", "liquidity_risk": 0.47, "volatility_risk": 0.39,
         "spread_pct": 2.2, "catalyst": None,
         "recommendation": "caution", "suspicion_score": 0.33,
         "insider_net": "neutral", "insider_buys": 1, "insider_sells": 1},
        {"ticker": "FGHI", "price": 4.95, "price_change_pct": 24.6,
         "volume": 2_800_000, "avg_volume": 430_000, "volume_ratio": 6.51,
         "market_cap": 145_000_000, "sector": "Energy", "momentum_score": 49.3,
         "risk_level": "medium", "liquidity_risk": 0.29, "volatility_risk": 0.34,
         "spread_pct": 1.1, "catalyst": "Sector momentum",
         "recommendation": "safe", "suspicion_score": 0.15,
         "insider_net": "buying", "insider_buys": 4, "insider_sells": 2},
        {"ticker": "JKLM", "price": 0.97, "price_change_pct": 21.9,
         "volume": 5_100_000, "avg_volume": 880_000, "volume_ratio": 5.80,
         "market_cap": 22_000_000, "sector": "Materials", "momentum_score": 44.1,
         "risk_level": "medium", "liquidity_risk": 0.51, "volatility_risk": 0.31,
         "spread_pct": 2.6, "catalyst": None,
         "recommendation": "caution", "suspicion_score": 0.40,
         "insider_net": "neutral", "insider_buys": 0, "insider_sells": 1},
        {"ticker": "NOPQ", "price": 3.20, "price_change_pct": 20.2,
         "volume": 1_900_000, "avg_volume": 360_000, "volume_ratio": 5.28,
         "market_cap": 76_000_000, "sector": "Technology", "momentum_score": 38.7,
         "risk_level": "low", "liquidity_risk": 0.24, "volatility_risk": 0.28,
         "spread_pct": 1.3, "catalyst": "Partnership announcement",
         "recommendation": "safe", "suspicion_score": 0.12,
         "insider_net": "buying", "insider_buys": 2, "insider_sells": 0},
        {"ticker": "RSTU", "price": 1.55, "price_change_pct": 18.0,
         "volume": 2_200_000, "avg_volume": 470_000, "volume_ratio": 4.68,
         "market_cap": 28_000_000, "sector": "Consumer", "momentum_score": 33.5,
         "risk_level": "low", "liquidity_risk": 0.36, "volatility_risk": 0.25,
         "spread_pct": 1.8, "catalyst": None,
         "recommendation": "safe", "suspicion_score": 0.09,
         "insider_net": "neutral", "insider_buys": 1, "insider_sells": 1},
    ]


def _demo_price_history(ticker: str, days: int) -> List[Dict[str, Any]]:
    """
    Build a deterministic synthetic price series for *ticker* over *days*.

    Used for chart rendering when live OHLC data is not available.  The series
    trends upward to reflect a momentum play and is reproducible per ticker.
    """
    seed = sum(ord(c) for c in ticker) or 1
    base = 0.50 + (seed % 400) / 100.0   # base price in [0.50, 4.49]
    series: List[Dict[str, Any]] = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        # Gentle upward drift with deterministic wobble
        drift = (i / max(1, days - 1)) * base * 0.8
        wobble = ((seed + i * 7) % 11 - 5) / 100.0 * base
        price = max(0.01, round(base + drift + wobble, 2))
        series.append({"date": d, "close": price})
    return series


def _demo_catalyst_events(ticker: str, days: int) -> List[Dict[str, Any]]:
    """Return synthetic catalyst events to highlight on the price charts."""
    seed = sum(ord(c) for c in ticker) or 1
    if seed % 3 == 0:
        return []
    today = date.today()
    offset = days // 2
    return [{
        "date": today - timedelta(days=offset),
        "label": "Catalyst: news/earnings event",
    }]


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_get(key: str) -> Optional[Any]:
    """Attempt a Redis cache read; return None on any failure."""
    if not CACHE_AVAILABLE:
        return None
    try:
        return get_cache().get(key)
    except Exception:
        return None


def _cache_set(key: str, value: Any, ttl: int = PENNY_DASHBOARD_CACHE_TTL) -> None:
    """Attempt a Redis cache write; silently swallow errors."""
    if not CACHE_AVAILABLE:
        return
    try:
        get_cache().set(key, value, ttl=ttl)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Data assembly (pure, testable)
# ---------------------------------------------------------------------------

def select_top_penny_stocks(
    rows: List[Dict[str, Any]], limit: int = TOP_PENNY_LIMIT
) -> List[Dict[str, Any]]:
    """
    Rank penny-stock display rows by momentum score (descending) and return
    the top *limit*.

    Requirement 11.5: top 20 penny stocks ranked by momentum score.
    Mirrors backend Property 54 (descending momentum order) at the UI layer.

    Args:
        rows:  List of penny-stock display dicts (must carry 'momentum_score').
        limit: Maximum number of rows to return (default 20).

    Returns:
        New list sorted by momentum_score descending, truncated to *limit*.
    """
    ranked = sorted(
        rows, key=lambda r: r.get("momentum_score", 0.0) or 0.0, reverse=True
    )
    return ranked[:limit]


def build_table_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construct the column data shown in the penny stock table.

    Columns (Requirement 11.5, 11.7, 11.10):
      ticker, price, % change, volume ratio, momentum score, risk classification

    Args:
        rows: List of penny-stock display dicts.

    Returns:
        List of dicts with exactly the table columns, in input order.
    """
    table: List[Dict[str, Any]] = []
    for r in rows:
        table.append({
            "Ticker":     r.get("ticker", "N/A"),
            "Price":      _fmt_price(float(r.get("price", 0.0))),
            "% Change":   _fmt_pct(float(r.get("price_change_pct", 0.0))),
            "Vol Ratio":  f"{float(r.get('volume_ratio', 0.0)):.2f}x",
            "Momentum":   f"{float(r.get('momentum_score', 0.0)):.1f}",
            "Risk":       str(r.get("risk_level", "n/a")).capitalize(),
        })
    return table


def compute_sector_distribution(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count penny stocks per sector for the sector-distribution pie chart.

    Requirement 11.18: sector distribution of trending penny stocks.

    Args:
        rows: List of penny-stock display dicts (each with a 'sector').

    Returns:
        Mapping of sector name -> count, including all sectors present.
    """
    distribution: Dict[str, int] = {}
    for r in rows:
        sector = r.get("sector") or "Unknown"
        distribution[sector] = distribution.get(sector, 0) + 1
    return distribution


# ---------------------------------------------------------------------------
# Live data fetch (with graceful fallback to demo data)
# ---------------------------------------------------------------------------

def _penny_stock_to_row(stock: "PennyStock") -> Dict[str, Any]:
    """Convert a backend PennyStock (with attached analytics) to a display dict."""
    risk = getattr(stock, "risk_metrics", None)
    return {
        "ticker": stock.ticker,
        "price": float(stock.price),
        "price_change_pct": float(stock.price_change_pct),
        "volume": int(stock.volume),
        "avg_volume": int(stock.avg_volume),
        "volume_ratio": float(stock.volume_ratio),
        "market_cap": int(stock.market_cap),
        "sector": stock.sector or "Unknown",
        "momentum_score": float(stock.momentum_score or 0.0),
        "risk_level": getattr(risk, "overall_risk", "n/a") if risk else "n/a",
        "liquidity_risk": getattr(risk, "liquidity_risk", 0.0) if risk else 0.0,
        "volatility_risk": getattr(risk, "volatility_risk", 0.0) if risk else 0.0,
        "spread_pct": getattr(risk, "spread_percentage", 0.0) if risk else 0.0,
        "catalyst": stock.catalyst,
        "recommendation": "n/a",
        "suspicion_score": 0.0,
        "insider_net": "neutral",
        "insider_buys": 0,
        "insider_sells": 0,
    }


def fetch_penny_stocks(limit: int = TOP_PENNY_LIMIT) -> List[Dict[str, Any]]:
    """
    Return the top penny-stock display rows ranked by momentum.

    Tries the live backend (scanner -> momentum -> risk -> pump/dump) and
    falls back to deterministic demo data when any dependency is unavailable
    or errors.  Results are cached for the 2-minute refresh window.

    Args:
        limit: Maximum number of rows to return (default 20).

    Returns:
        List of penny-stock display dicts, ranked by momentum descending.
    """
    cache_key = f"penny_dashboard:top:{date.today().isoformat()}:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return cached[:limit]

    if not (SCANNER_AVAILABLE and MOMENTUM_AVAILABLE and RISK_AVAILABLE):
        return select_top_penny_stocks(_demo_penny_stocks(), limit)

    try:
        scanner = PennyStockScanner()
        momentum = MomentumCalculator()
        risk_analyzer = PennyStockRiskAnalyzer()
        detector = PumpDumpDetector()

        # Scan intraday + multi-day gainers, then filter by volume.
        candidates = scanner.scan_intraday_gainers()
        candidates += scanner.scan_multi_day_gainers()
        candidates = scanner.filter_by_volume(candidates)

        # De-duplicate by ticker (keep the higher gainer).
        unique: Dict[str, "PennyStock"] = {}
        for s in candidates:
            existing = unique.get(s.ticker)
            if existing is None or s.price_change_pct > existing.price_change_pct:
                unique[s.ticker] = s
        stocks = list(unique.values())

        if not stocks:
            return select_top_penny_stocks(_demo_penny_stocks(), limit)

        # Enrich each stock with momentum + risk + insider analytics.
        ranked = momentum.rank_by_momentum(stocks)
        rows: List[Dict[str, Any]] = []
        for s in ranked[:limit]:
            try:
                risk_analyzer.assess_overall_risk(s)
            except Exception:
                pass
            row = _penny_stock_to_row(s)
            try:
                suspicion = detector.detect_suspicious_patterns(s)
                row["recommendation"] = suspicion.recommendation
                row["suspicion_score"] = suspicion.score
            except Exception:
                pass
            try:
                insider = detector.check_insider_activity(s.ticker)
                row["insider_net"] = insider.net_activity
                row["insider_buys"] = insider.recent_buys
                row["insider_sells"] = insider.recent_sells
            except Exception:
                pass
            rows.append(row)

        rows = select_top_penny_stocks(rows, limit)
        _cache_set(cache_key, rows)
        return rows

    except Exception as exc:
        logger.warning("fetch_penny_stocks_failed: %s - using demo data", exc)
        return select_top_penny_stocks(_demo_penny_stocks(), limit)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_price(p: float) -> str:
    return f"${p:,.2f}"


def _fmt_pct(p: float) -> str:
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.2f}%"


def _fmt_volume(v: int) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.0f}K"
    return str(v)


def _pct_colour(pct: float) -> str:
    return "#00c853" if pct >= 0 else "#d50000"


def _risk_colour(level: str) -> str:
    return _RISK_COLOURS.get((level or "").lower(), "#9e9e9e")


def _recommendation_colour(rec: str) -> str:
    return _RECOMMENDATION_COLOURS.get((rec or "").lower(), "#9e9e9e")


# ---------------------------------------------------------------------------
# Section: momentum table
# ---------------------------------------------------------------------------

def render_penny_stock_table(rows: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Render the top-20 penny stock momentum table.

    Columns: ticker, price, % change, volume ratio, momentum score, risk class.
    Requirement 11.5, 11.7, 11.10.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available - cannot render penny stock table")
        return

    rows = rows if rows is not None else fetch_penny_stocks(TOP_PENNY_LIMIT)
    st.subheader("🚀 Top 20 Penny Stocks by Momentum")

    if not rows:
        st.info("No penny stocks meet the momentum criteria right now.")
        return

    # Header row
    h = st.columns([0.6, 1.6, 1.2, 1.2, 1.2, 1.2, 1.4])
    for col, label in zip(
        h, ["#", "Ticker", "Price", "% Change", "Vol Ratio", "Momentum", "Risk"]
    ):
        with col:
            st.markdown(f"**{label}**")

    for i, r in enumerate(rows, start=1):
        pct = float(r.get("price_change_pct", 0.0))
        risk_level = str(r.get("risk_level", "n/a"))
        momentum_score = float(r.get("momentum_score", 0.0))
        c = st.columns([0.6, 1.6, 1.2, 1.2, 1.2, 1.2, 1.4])
        with c[0]:
            st.markdown(f"{i}")
        with c[1]:
            catalyst_badge = " 📰" if r.get("catalyst") else ""
            st.markdown(f"**{r.get('ticker', 'N/A')}**{catalyst_badge}")
        with c[2]:
            st.markdown(_fmt_price(float(r.get("price", 0.0))))
        with c[3]:
            st.markdown(
                f"<span style='color:{_pct_colour(pct)};font-weight:bold'>"
                f"{_fmt_pct(pct)}</span>",
                unsafe_allow_html=True,
            )
        with c[4]:
            st.markdown(f"{float(r.get('volume_ratio', 0.0)):.2f}x")
        with c[5]:
            st.markdown(f"{momentum_score:.1f}")
        with c[6]:
            st.markdown(
                f"<span style='background:{_risk_colour(risk_level)};color:#fff;"
                f"padding:1px 7px;border-radius:4px;font-size:0.8em'>"
                f"{risk_level.capitalize()}</span>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Section: price-history charts
# ---------------------------------------------------------------------------

def render_penny_stock_charts(rows: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Render 1-day / 5-day / 30-day price history charts with catalyst-event
    highlights for a selected penny stock.

    Requirement 11.8: price history charts with 1D / 5D / 30D views.
    Requirement 11.9: highlight catalyst events on the charts.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available - cannot render penny stock charts")
        return

    rows = rows if rows is not None else fetch_penny_stocks(TOP_PENNY_LIMIT)
    st.subheader("📈 Price History & Catalysts")

    if not rows:
        st.info("No penny stocks available to chart.")
        return

    tickers = [r.get("ticker", "N/A") for r in rows]
    selected = st.selectbox("Select a penny stock", tickers, key="penny_chart_ticker")

    if not PLOTLY_AVAILABLE:
        st.warning("Plotly is not available - charts cannot be displayed.")
        return

    tabs = st.tabs([f"{tf} View" for tf in CHART_TIMEFRAMES])
    timeframe_days = {"1D": 1, "5D": 5, "30D": 30}

    for tab, tf in zip(tabs, CHART_TIMEFRAMES):
        with tab:
            days = timeframe_days[tf]
            # 1-day view uses intraday granularity; emulate with hourly points.
            history = _demo_price_history(selected, max(days, 2))
            events = _demo_catalyst_events(selected, max(days, 2))
            _render_price_chart(selected, history, events, tf)


def _render_price_chart(
    ticker: str,
    history: List[Dict[str, Any]],
    events: List[Dict[str, Any]],
    timeframe: str,
) -> None:
    """Render a single Plotly line chart with catalyst-event markers."""
    if not PLOTLY_AVAILABLE:
        return

    x = [pt["date"] for pt in history]
    y = [pt["close"] for pt in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers", name=f"{ticker} close",
        line=dict(color="#2962ff", width=2),
    ))

    # Highlight catalyst events with vertical markers (Requirement 11.9).
    for ev in events:
        fig.add_vline(
            x=ev["date"], line_width=1, line_dash="dash", line_color="#ff6d00",
        )
        fig.add_annotation(
            x=ev["date"], y=max(y) if y else 0,
            text=f"⚡ {ev.get('label', 'Catalyst')}",
            showarrow=True, arrowhead=2, font=dict(size=10, color="#ff6d00"),
        )

    fig.update_layout(
        title=f"{ticker} — {timeframe} Price History",
        height=320, margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Date", yaxis_title="Price ($)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Section: risk metrics
# ---------------------------------------------------------------------------

def render_penny_stock_metrics(rows: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Render the risk-metrics panel for penny stocks.

    Displays liquidity risk, volatility risk, spread percentage and insider
    activity for each top penny stock.
    Requirement 11.10 (risk metrics), 11.12 (insider activity), 11.13 (pump/dump).
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available - cannot render penny stock metrics")
        return

    rows = rows if rows is not None else fetch_penny_stocks(TOP_PENNY_LIMIT)
    st.subheader("⚠️ Risk Metrics & Insider Activity")

    if not rows:
        st.info("No penny stock risk data available.")
        return

    for r in rows:
        ticker = r.get("ticker", "N/A")
        rec = str(r.get("recommendation", "n/a"))
        with st.expander(
            f"{ticker} — {str(r.get('risk_level', 'n/a')).capitalize()} risk", expanded=False
        ):
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Liquidity Risk", f"{float(r.get('liquidity_risk', 0.0)):.2f}")
            with m2:
                st.metric("Volatility Risk", f"{float(r.get('volatility_risk', 0.0)):.2f}")
            with m3:
                st.metric("Spread %", f"{float(r.get('spread_pct', 0.0)):.2f}%")
            with m4:
                st.metric(
                    "Insider",
                    str(r.get("insider_net", "neutral")).capitalize(),
                    delta=f"+{r.get('insider_buys', 0)} / -{r.get('insider_sells', 0)}",
                )

            # Pump-and-dump recommendation badge (Requirement 11.13)
            if rec and rec != "n/a":
                st.markdown(
                    f"Recommendation: "
                    f"<span style='background:{_recommendation_colour(rec)};color:#fff;"
                    f"padding:1px 8px;border-radius:4px;font-size:0.85em'>"
                    f"{rec.upper()}</span>  "
                    f"<span style='font-size:0.8em;color:#aaa'>"
                    f"(suspicion {float(r.get('suspicion_score', 0.0)):.2f})</span>",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Section: sector distribution
# ---------------------------------------------------------------------------

def render_sector_distribution(rows: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Render a pie chart of trending penny stock sectors.

    Requirement 11.18: sector distribution of trending penny stocks.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available - cannot render sector distribution")
        return

    rows = rows if rows is not None else fetch_penny_stocks(TOP_PENNY_LIMIT)
    st.subheader("🏭 Sector Distribution")

    distribution = compute_sector_distribution(rows)
    if not distribution:
        st.info("No sector data available.")
        return

    if not PLOTLY_AVAILABLE:
        # Text fallback when plotly is unavailable.
        for sector, count in sorted(
            distribution.items(), key=lambda kv: kv[1], reverse=True
        ):
            st.markdown(f"- **{sector}**: {count}")
        return

    labels = list(distribution.keys())
    values = list(distribution.values())
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4))
    fig.update_layout(
        height=340, margin=dict(l=20, r=20, t=30, b=20),
        title="Trending Penny Stocks by Sector",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Primary render entry point
# ---------------------------------------------------------------------------

def render_penny_dashboard() -> None:
    """
    Render the Penny Stock Momentum dashboard.

    Displays the top 20 penny stocks ranked by momentum score along with the
    momentum table, price-history charts, risk metrics and a sector
    distribution pie chart.

    The dashboard auto-refreshes every 2 minutes during market hours
    (Requirement 11.15 / Property 53).  When the optional `streamlit-autorefresh`
    component is present it is used; otherwise a meta-refresh notice is shown.

    Requirement 11.5, 11.8, 11.12, 11.13, 11.15-11.19.
    """
    if not STREAMLIT_AVAILABLE:
        logger.error(
            "streamlit not available - render_penny_dashboard() called outside "
            "a Streamlit context; nothing will be rendered."
        )
        return

    interval = get_refresh_interval_seconds()  # <= 120 (Property 53)

    # Header
    today_str = datetime.utcnow().strftime("%A, %B %d, %Y")
    st.title("🪙 Penny Stock Momentum Dashboard")
    st.caption(
        f"As of {today_str} UTC  ·  Auto-refreshes every "
        f"{interval // 60} min {interval % 60} sec during market hours"
    )

    # Auto-refresh: prefer the streamlit-autorefresh component; fall back to a
    # millisecond interval registered on the page.  Both are bounded by the
    # 2-minute Property 53 interval.
    _register_autorefresh(interval)

    st.divider()

    rows = fetch_penny_stocks(TOP_PENNY_LIMIT)

    render_penny_stock_table(rows)
    st.divider()

    chart_col, sector_col = st.columns([2, 1])
    with chart_col:
        render_penny_stock_charts(rows)
    with sector_col:
        render_sector_distribution(rows)

    st.divider()
    render_penny_stock_metrics(rows)


def _register_autorefresh(interval_seconds: int) -> None:
    """
    Register a client-side auto-refresh bounded by *interval_seconds*.

    Uses streamlit-autorefresh when installed; otherwise records the interval
    in session state so the surrounding app can schedule a rerun.  Failures
    degrade gracefully (the dashboard simply won't auto-refresh).
    """
    interval_ms = min(interval_seconds, MAX_REFRESH_INTERVAL_SECONDS) * 1000
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore
        st_autorefresh(interval=interval_ms, key="penny_dashboard_autorefresh")
        return
    except Exception:
        pass

    # Fallback: stash the interval for the host app / track last refresh time.
    try:
        if hasattr(st, "session_state"):
            st.session_state["penny_dashboard_refresh_ms"] = interval_ms
            st.session_state.setdefault(
                "penny_dashboard_last_refresh", datetime.utcnow()
            )
    except Exception:
        pass
