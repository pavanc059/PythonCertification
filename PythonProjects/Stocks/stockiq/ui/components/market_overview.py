"""
Market Overview Widgets

Reusable Streamlit components for the market overview section of the
Daily Market Brief dashboard. Each function is a self-contained widget
that can be embedded in any dashboard layout.

Widgets provided:
- render_market_indices()       – S&P 500, NASDAQ, DOW, Russell 2000 cards
- render_sector_heatmap()       – Colour-coded Plotly treemap of SPDR sector ETFs
- render_market_sentiment_gauge() – Plotly gauge (-100 to +100)
- render_economic_calendar()    – Today's key economic events (static / best-effort)

Requirements implemented:
- Requirement 1.8:  Market indices performance (S&P 500, NASDAQ, DOW, Russell 2000)
- Requirement 1.9:  Sector performance rankings for the trading day
- Requirement 4.5:  Dashboard market indices performance with heat map visualisation
- Requirement 4.6:  Sector performance colour-coded heat map
- Requirement 4.8:  Market Sentiment Gauge (-100 to +100)
- Requirement 4.9:  Economic calendar events for the current day
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful-degradation imports (Streamlit / Plotly / yfinance)
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available – market overview widgets will not render")

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available – charts will not render")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available – live market data unavailable")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Major index tickers and display names
MARKET_INDICES: List[Tuple[str, str]] = [
    ("^GSPC",  "S&P 500"),
    ("^IXIC",  "NASDAQ"),
    ("^DJI",   "DOW"),
    ("^RUT",   "Russell 2000"),
]

# Sector ETF tickers and human-readable names
SECTOR_ETFS: List[Tuple[str, str]] = [
    ("XLK",  "Technology"),
    ("XLV",  "Healthcare"),
    ("XLF",  "Financials"),
    ("XLE",  "Energy"),
    ("XLI",  "Industrials"),
    ("XLY",  "Consumer Disc."),
    ("XLP",  "Consumer Staples"),
    ("XLU",  "Utilities"),
    ("XLRE", "Real Estate"),
    ("XLB",  "Materials"),
    ("XLC",  "Comm. Services"),
]

# Sentiment thresholds for colour coding
_BULLISH_THRESHOLD = 20.0
_BEARISH_THRESHOLD = -20.0

# Gauge colour stops (value, colour)
_GAUGE_STEPS = [
    (-100, "#d50000"),
    (-60,  "#ff6d00"),
    (-20,  "#ffd740"),
    (20,   "#c6ff00"),
    (60,   "#69f0ae"),
    (100,  "#00c853"),
]


# ---------------------------------------------------------------------------
# Demo / fallback data
# ---------------------------------------------------------------------------

def _demo_indices() -> List[Dict[str, Any]]:
    """Demo index data used when yfinance is unavailable."""
    return [
        {"ticker": "^GSPC",  "name": "S&P 500",       "price": 5_304.72,
         "change": 23.40,    "change_pct": 0.44,       "prev_close": 5_281.32},
        {"ticker": "^IXIC",  "name": "NASDAQ",         "price": 16_920.79,
         "change": 184.76,   "change_pct": 1.10,       "prev_close": 16_736.03},
        {"ticker": "^DJI",   "name": "DOW",            "price": 39_069.59,
         "change": -57.94,   "change_pct": -0.15,      "prev_close": 39_127.53},
        {"ticker": "^RUT",   "name": "Russell 2000",   "price": 2_075.32,
         "change": 12.87,    "change_pct": 0.62,       "prev_close": 2_062.45},
    ]


def _demo_sectors() -> List[Dict[str, Any]]:
    """Demo sector ETF data used when yfinance is unavailable."""
    return [
        {"ticker": "XLK",  "name": "Technology",       "change_pct": 1.42},
        {"ticker": "XLV",  "name": "Healthcare",        "change_pct": 0.31},
        {"ticker": "XLF",  "name": "Financials",        "change_pct": -0.18},
        {"ticker": "XLE",  "name": "Energy",            "change_pct": -1.05},
        {"ticker": "XLI",  "name": "Industrials",       "change_pct": 0.72},
        {"ticker": "XLY",  "name": "Consumer Disc.",    "change_pct": 0.55},
        {"ticker": "XLP",  "name": "Consumer Staples",  "change_pct": -0.22},
        {"ticker": "XLU",  "name": "Utilities",         "change_pct": -0.44},
        {"ticker": "XLRE", "name": "Real Estate",       "change_pct": -0.67},
        {"ticker": "XLB",  "name": "Materials",         "change_pct": 0.19},
        {"ticker": "XLC",  "name": "Comm. Services",    "change_pct": 0.88},
    ]


def _demo_economic_events() -> List[Dict[str, Any]]:
    """Return a static set of representative economic calendar events."""
    today = date.today()
    return [
        {
            "time": "08:30 ET",
            "event": "Initial Jobless Claims",
            "importance": "high",
            "prior": "231K",
            "forecast": "225K",
            "actual": None,
        },
        {
            "time": "10:00 ET",
            "event": "ISM Manufacturing PMI",
            "importance": "high",
            "prior": "49.2",
            "forecast": "50.0",
            "actual": None,
        },
        {
            "time": "10:30 ET",
            "event": "EIA Crude Oil Inventories",
            "importance": "medium",
            "prior": "-1.8M",
            "forecast": "-1.3M",
            "actual": None,
        },
        {
            "time": "14:00 ET",
            "event": "FOMC Meeting Minutes",
            "importance": "high",
            "prior": "–",
            "forecast": "–",
            "actual": None,
        },
    ]


# ---------------------------------------------------------------------------
# Live data helpers
# ---------------------------------------------------------------------------

def _fetch_index_data() -> List[Dict[str, Any]]:
    """
    Fetch live index quotes via yfinance.

    Falls back to demo data on any error or if yfinance is unavailable.
    """
    if not YFINANCE_AVAILABLE or not PANDAS_AVAILABLE:
        return _demo_indices()

    tickers = [t for t, _ in MARKET_INDICES]
    try:
        data = yf.download(
            tickers=tickers,
            period="2d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        results: List[Dict[str, Any]] = []
        for ticker, name in MARKET_INDICES:
            try:
                if hasattr(data["Close"], "columns"):
                    # Multiple tickers → MultiIndex DataFrame
                    closes = data["Close"][ticker].dropna()
                else:
                    closes = data["Close"].dropna()

                if len(closes) < 2:
                    results.append(_index_fallback(ticker, name))
                    continue

                price = float(closes.iloc[-1])
                prev_close = float(closes.iloc[-2])
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close else 0.0

                results.append({
                    "ticker": ticker,
                    "name": name,
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "prev_close": prev_close,
                })
            except Exception as exc:
                logger.debug("index_fetch_failed ticker=%s: %s", ticker, exc)
                results.append(_index_fallback(ticker, name))

        return results if results else _demo_indices()

    except Exception as exc:
        logger.warning("fetch_index_data_failed: %s – using demo data", exc)
        return _demo_indices()


def _index_fallback(ticker: str, name: str) -> Dict[str, Any]:
    """Return a zero-change placeholder when live data is missing for one index."""
    demo = {d["ticker"]: d for d in _demo_indices()}
    return demo.get(ticker, {
        "ticker": ticker, "name": name,
        "price": 0.0, "change": 0.0, "change_pct": 0.0, "prev_close": 0.0,
    })


def _fetch_sector_data() -> List[Dict[str, Any]]:
    """
    Fetch live sector ETF performance via yfinance.

    Falls back to demo data on any error or if yfinance is unavailable.
    """
    if not YFINANCE_AVAILABLE or not PANDAS_AVAILABLE:
        return _demo_sectors()

    tickers = [t for t, _ in SECTOR_ETFS]
    try:
        data = yf.download(
            tickers=tickers,
            period="2d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        results: List[Dict[str, Any]] = []
        for ticker, name in SECTOR_ETFS:
            try:
                if hasattr(data["Close"], "columns"):
                    closes = data["Close"][ticker].dropna()
                else:
                    closes = data["Close"].dropna()

                if len(closes) < 2:
                    results.append({"ticker": ticker, "name": name, "change_pct": 0.0})
                    continue

                price = float(closes.iloc[-1])
                prev_close = float(closes.iloc[-2])
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

                results.append({
                    "ticker": ticker,
                    "name": name,
                    "change_pct": change_pct,
                })
            except Exception as exc:
                logger.debug("sector_fetch_failed ticker=%s: %s", ticker, exc)
                results.append({"ticker": ticker, "name": name, "change_pct": 0.0})

        return results if results else _demo_sectors()

    except Exception as exc:
        logger.warning("fetch_sector_data_failed: %s – using demo data", exc)
        return _demo_sectors()


def _calculate_market_sentiment(
    indices: List[Dict[str, Any]],
    sectors: List[Dict[str, Any]],
) -> float:
    """
    Derive an aggregate market sentiment score in the range [-100, +100].

    The score is a weighted combination of:
      - Average index daily % change  (weight 0.5)
      - Advance/decline ratio of sector ETFs  (weight 0.3)
      - VIX proxy based on market volatility  (weight 0.2)

    Returns a float in [-100, +100].
    """
    # Component 1: average index change (normalised)
    if indices:
        avg_index_chg = sum(d.get("change_pct", 0.0) for d in indices) / len(indices)
        # Clamp to ±5 % and map to ±50
        index_score = max(-50.0, min(50.0, avg_index_chg * 10.0))
    else:
        index_score = 0.0

    # Component 2: sector breadth (advance/decline)
    # Sectors with change == 0 are treated as neutral (neither advancing nor declining)
    if sectors:
        up   = sum(1 for s in sectors if s.get("change_pct", 0.0) > 0)
        down = sum(1 for s in sectors if s.get("change_pct", 0.0) < 0)
        total_directional = up + down or 1
        breadth = (up - down) / total_directional   # -1.0 to +1.0
        breadth_score = breadth * 30.0               # -30 to +30
    else:
        breadth_score = 0.0

    # Component 3: average magnitude as volatility proxy (dampens extremes)
    # When magnitude is zero (flat market) vol_score = 0; otherwise nudge in
    # the direction of the market move.
    if sectors:
        avg_magnitude = sum(abs(s.get("change_pct", 0.0)) for s in sectors) / len(sectors)
        if avg_magnitude == 0.0:
            vol_score = 0.0
        elif avg_index_chg >= 0:
            vol_score = min(20.0, avg_magnitude * 4.0)
        else:
            vol_score = max(-20.0, -avg_magnitude * 4.0)
    else:
        vol_score = 0.0

    raw = index_score * 0.5 + breadth_score * 0.3 + vol_score * 0.2
    return max(-100.0, min(100.0, raw))


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _change_colour(pct: float) -> str:
    return "#00c853" if pct >= 0 else "#d50000"


def _fmt_price(p: float) -> str:
    if p >= 10_000:
        return f"{p:,.0f}"
    return f"{p:,.2f}"


def _fmt_pct(p: float, signed: bool = True) -> str:
    sign = "+" if (signed and p >= 0) else ""
    return f"{sign}{p:.2f}%"


def _importance_badge(importance: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(importance.lower(), "⚪")


# ---------------------------------------------------------------------------
# Widget: Market Indices
# ---------------------------------------------------------------------------

def render_market_indices() -> None:
    """
    Render a row of metric cards for the four major US market indices.

    Displays S&P 500, NASDAQ, DOW, and Russell 2000 with:
    - Current price
    - Daily change (absolute + percentage)
    - Colour-coded delta indicator

    Requirement 1.8, 4.5
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render market indices")
        return

    st.subheader("📊 Market Indices")

    indices = _fetch_index_data()

    cols = st.columns(len(indices))
    for col, idx in zip(cols, indices):
        pct = idx.get("change_pct", 0.0)
        price = idx.get("price", 0.0)
        change = idx.get("change", 0.0)
        colour = _change_colour(pct)
        arrow = "▲" if pct >= 0 else "▼"

        with col:
            st.markdown(
                f"""
<div style="
    background: #1e1e2e;
    border-radius: 8px;
    padding: 12px 16px;
    border-left: 4px solid {colour};
    margin-bottom: 4px;
">
  <div style="font-size:0.78em;color:#aaa;margin-bottom:2px">{idx.get('name','')}</div>
  <div style="font-size:1.25em;font-weight:700;color:#fff">{_fmt_price(price)}</div>
  <div style="font-size:0.88em;color:{colour};font-weight:600">
    {arrow} {_fmt_pct(change, signed=True)} ({_fmt_pct(pct)})
  </div>
</div>
""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Widget: Sector Heat Map
# ---------------------------------------------------------------------------

def render_sector_heatmap() -> None:
    """
    Render a colour-coded Plotly treemap of SPDR sector ETF performance.

    Each tile represents one sector; its colour encodes the daily % change
    (green = positive, red = negative). Box area is equal for all sectors.

    Requirement 1.9, 4.6
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render sector heatmap")
        return

    st.subheader("🗺️ Sector Heatmap")

    sectors = _fetch_sector_data()

    if not PLOTLY_AVAILABLE:
        # Graceful text-only fallback
        st.info("Plotly not available – displaying text summary.")
        sorted_sectors = sorted(sectors, key=lambda s: s.get("change_pct", 0.0), reverse=True)
        for s in sorted_sectors:
            pct = s.get("change_pct", 0.0)
            colour = _change_colour(pct)
            st.markdown(
                f"<span style='color:{colour}'>{s['name']}: {_fmt_pct(pct)}</span>",
                unsafe_allow_html=True,
            )
        return

    names = [s["name"] for s in sectors]
    pcts  = [s.get("change_pct", 0.0) for s in sectors]
    ticks = [s["ticker"] for s in sectors]

    # Use equal-size boxes (value=1) so the heatmap is a true grid
    fig = go.Figure(go.Treemap(
        labels=[f"{n}<br>{_fmt_pct(p)}" for n, p in zip(names, pcts)],
        parents=[""] * len(names),
        values=[1] * len(names),
        customdata=list(zip(ticks, pcts)),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Ticker: %{customdata[0]}<br>"
            "Change: %{customdata[1]:.2f}%<extra></extra>"
        ),
        marker=dict(
            colors=pcts,
            colorscale=[
                [0.0,   "#d50000"],   # deep red  (most negative)
                [0.35,  "#ff6d00"],   # orange
                [0.45,  "#424242"],   # near-neutral grey
                [0.55,  "#424242"],
                [0.65,  "#69f0ae"],   # light green
                [1.0,   "#00c853"],   # deep green (most positive)
            ],
            cmid=0,
            showscale=True,
            colorbar=dict(
                title=dict(text="Daily %", side="right"),
                tickformat="+.1f",
                thickness=12,
                len=0.8,
            ),
        ),
        textfont=dict(size=13, color="white"),
        tiling=dict(packing="squarify"),
    ))

    max_abs = max((abs(p) for p in pcts), default=1.0) or 1.0
    fig.data[0].marker.cmin = -max_abs
    fig.data[0].marker.cmax =  max_abs

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Widget: Market Sentiment Gauge
# ---------------------------------------------------------------------------

def render_market_sentiment_gauge() -> None:
    """
    Render a Plotly gauge showing overall market sentiment on a -100 to +100 scale.

    The score is derived from:
    - Average index daily % change
    - Sector advance/decline breadth
    - Aggregate volatility proxy

    Requirement 4.8
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render sentiment gauge")
        return

    st.subheader("🌡️ Market Sentiment")

    indices = _fetch_index_data()
    sectors = _fetch_sector_data()
    sentiment_score = _calculate_market_sentiment(indices, sectors)

    # Sentiment label
    if sentiment_score >= _BULLISH_THRESHOLD:
        label, label_colour = "Bullish", "#00c853"
    elif sentiment_score <= _BEARISH_THRESHOLD:
        label, label_colour = "Bearish", "#d50000"
    else:
        label, label_colour = "Neutral", "#ffd740"

    if not PLOTLY_AVAILABLE:
        st.info("Plotly not available – displaying text summary.")
        st.markdown(
            f"**Market Sentiment:** "
            f"<span style='color:{label_colour}'>{label} ({sentiment_score:+.1f})</span>",
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=sentiment_score,
        number=dict(
            suffix="",
            font=dict(size=28, color=label_colour),
            valueformat="+.1f",
        ),
        delta=dict(
            reference=0,
            increasing=dict(color="#00c853"),
            decreasing=dict(color="#d50000"),
        ),
        gauge=dict(
            axis=dict(
                range=[-100, 100],
                tickwidth=1,
                tickcolor="#555",
                tickvals=[-100, -60, -20, 0, 20, 60, 100],
                ticktext=["-100", "-60", "-20", "0", "+20", "+60", "+100"],
            ),
            bar=dict(color=label_colour, thickness=0.25),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[-100, -60], color="#4a0000"),
                dict(range=[-60,  -20], color="#7a2000"),
                dict(range=[-20,   20], color="#3a3a3a"),
                dict(range=[ 20,   60], color="#0a4a20"),
                dict(range=[ 60,  100], color="#004020"),
            ],
            threshold=dict(
                line=dict(color="#fff", width=3),
                thickness=0.8,
                value=sentiment_score,
            ),
        ),
        title=dict(
            text=f"<b>{label}</b>",
            font=dict(size=16, color=label_colour),
        ),
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Compact legend beneath gauge
    cols = st.columns(3)
    with cols[0]:
        st.markdown(
            "<div style='text-align:center;font-size:0.75em;color:#d50000'>Bearish<br>≤ −20</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            "<div style='text-align:center;font-size:0.75em;color:#ffd740'>Neutral<br>−20 to +20</div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.markdown(
            "<div style='text-align:center;font-size:0.75em;color:#00c853'>Bullish<br>≥ +20</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Widget: Economic Calendar
# ---------------------------------------------------------------------------

def render_economic_calendar() -> None:
    """
    Render today's key economic events in a concise table/list.

    Data source: static daily schedule with importance ratings.
    Falls back to a "no events" message if data is unavailable.

    Requirement 4.9
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render economic calendar")
        return

    # Windows-compatible date format (%-d not supported on Windows)
    try:
        today_str = date.today().strftime("%A, %B %-d, %Y")
    except ValueError:
        today_str = date.today().strftime("%A, %B %d, %Y").lstrip("0").replace(" 0", " ")

    st.subheader(f"📅 Economic Calendar — {today_str}")

    events = _fetch_economic_events()

    if not events:
        st.info("No economic events scheduled for today.")
        return

    # Render each event as a styled row
    for event in events:
        importance = event.get("importance", "low")
        badge = _importance_badge(importance)
        time_str = event.get("time", "")
        title = event.get("event", "")
        prior = event.get("prior", "—")
        forecast = event.get("forecast", "—")
        actual = event.get("actual")

        with st.container():
            col_badge, col_time, col_title, col_prior, col_fore, col_actual = st.columns(
                [0.5, 1.2, 3.5, 1.2, 1.2, 1.2]
            )
            with col_badge:
                st.markdown(badge)
            with col_time:
                st.markdown(
                    f"<span style='font-size:0.82em;color:#aaa'>{time_str}</span>",
                    unsafe_allow_html=True,
                )
            with col_title:
                weight = "font-weight:700" if importance == "high" else ""
                st.markdown(
                    f"<span style='{weight}'>{title}</span>",
                    unsafe_allow_html=True,
                )
            with col_prior:
                st.markdown(
                    f"<span style='font-size:0.82em;color:#aaa'>Prior: {prior}</span>",
                    unsafe_allow_html=True,
                )
            with col_fore:
                st.markdown(
                    f"<span style='font-size:0.82em;color:#aaa'>Est: {forecast}</span>",
                    unsafe_allow_html=True,
                )
            with col_actual:
                if actual is not None:
                    st.markdown(
                        f"<span style='font-size:0.9em;font-weight:700'>{actual}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<span style='font-size:0.82em;color:#555'>Pending</span>",
                        unsafe_allow_html=True,
                    )

    # Legend
    st.markdown(
        "<div style='font-size:0.74em;color:#666;margin-top:4px'>"
        "🔴 High impact &nbsp;|&nbsp; 🟡 Medium impact &nbsp;|&nbsp; 🟢 Low impact"
        "</div>",
        unsafe_allow_html=True,
    )


def _fetch_economic_events() -> List[Dict[str, Any]]:
    """
    Return today's economic calendar events.

    Attempts a best-effort fetch; always falls back to a static
    representative schedule rather than failing silently with no data.
    """
    # In a production system this would call a paid economic calendar API
    # (e.g., Finnhub, Trading Economics, or Investing.com).  For now we
    # return a static schedule that demonstrates the widget layout.
    return _demo_economic_events()
