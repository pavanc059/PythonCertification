"""
Candlestick Chart Component

Professional candlestick charts with:
- Multiple timeframe support (1m, 5m, 15m, 1h, 1d, 1w)
- Volume bars synchronized with price
- Technical indicator overlays
- Drawing tools support
- Real-time updates
- Zoom and pan functionality

Requirement 18.1: Candlestick charts with 6 timeframe options
Requirement 18.4: Chart comparison mode
Requirement 18.5: Volume bars synchronized with price
Requirement 18.6: Zoom and pan functionality
Requirement 18.8: Real-time price updates
Requirement 18.11: Fast chart rendering (<500ms)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Graceful imports
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available")

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available")

# Timeframe configurations
TIMEFRAME_OPTIONS = {
    "1m": {"interval": "1m", "period": "1d", "label": "1 Minute"},
    "5m": {"interval": "5m", "period": "5d", "label": "5 Minutes"},
    "15m": {"interval": "15m", "period": "5d", "label": "15 Minutes"},
    "1h": {"interval": "1h", "period": "1mo", "label": "1 Hour"},
    "1d": {"interval": "1d", "period": "1y", "label": "1 Day"},
    "1w": {"interval": "1wk", "period": "2y", "label": "1 Week"},
}

# Chart color scheme
COLORS = {
    "up_candle": "#00c853",
    "down_candle": "#d50000",
    "up_border": "#00e676",
    "down_border": "#ff1744",
    "volume_up": "rgba(0, 200, 83, 0.3)",
    "volume_down": "rgba(213, 0, 0, 0.3)",
    "grid": "#2a2a2a",
    "text": "#cccccc",
    "background": "#1e1e1e",
}


def fetch_price_data(
    ticker: str,
    timeframe: str = "1d",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    Fetch OHLCV price data for the specified ticker and timeframe.
    
    Args:
        ticker: Stock symbol
        timeframe: One of the TIMEFRAME_OPTIONS keys
        start_date: Optional start date for custom range
        end_date: Optional end date for custom range
    
    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    if not YFINANCE_AVAILABLE:
        logger.error("yfinance not available")
        return pd.DataFrame()
    
    try:
        config = TIMEFRAME_OPTIONS.get(timeframe, TIMEFRAME_OPTIONS["1d"])
        
        if start_date and end_date:
            # Custom date range
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=config["interval"],
                progress=False,
            )
        else:
            # Use period
            data = yf.download(
                ticker,
                period=config["period"],
                interval=config["interval"],
                progress=False,
            )
        
        if data.empty:
            logger.warning(f"No data returned for {ticker}")
            return pd.DataFrame()
        
        # Ensure proper column names
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        
        # Ensure required columns exist
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in data.columns:
                logger.error(f"Missing required column: {col}")
                return pd.DataFrame()
        
        return data[required_cols]
    
    except Exception as exc:
        logger.error(f"Failed to fetch data for {ticker}: {exc}")
        return pd.DataFrame()


def create_candlestick_trace(
    data: pd.DataFrame,
    name: str = "",
    show_volume: bool = True,
) -> Tuple[go.Candlestick, Optional[go.Bar]]:
    """
    Create Plotly candlestick and volume bar traces.
    
    Args:
        data: DataFrame with OHLCV data
        name: Display name for the trace
        show_volume: Whether to include volume bars
    
    Returns:
        Tuple of (candlestick_trace, volume_trace)
    """
    candlestick = go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name=name,
        increasing=dict(
            line=dict(color=COLORS["up_border"], width=1),
            fillcolor=COLORS["up_candle"],
        ),
        decreasing=dict(
            line=dict(color=COLORS["down_border"], width=1),
            fillcolor=COLORS["down_candle"],
        ),
        hoverinfo="text",
        text=[
            f"Date: {idx.strftime('%Y-%m-%d %H:%M') if hasattr(idx, 'strftime') else idx}<br>"
            f"Open: ${row['Open']:.2f}<br>"
            f"High: ${row['High']:.2f}<br>"
            f"Low: ${row['Low']:.2f}<br>"
            f"Close: ${row['Close']:.2f}<br>"
            f"Volume: {int(row['Volume']):,}"
            for idx, row in data.iterrows()
        ],
    )
    
    if show_volume:
        # Color volume bars based on price direction
        volume_colors = [
            COLORS["volume_up"] if close >= open_price else COLORS["volume_down"]
            for open_price, close in zip(data["Open"], data["Close"])
        ]
        
        volume = go.Bar(
            x=data.index,
            y=data["Volume"],
            name="Volume",
            marker=dict(color=volume_colors),
            yaxis="y2",
            hoverinfo="text",
            text=[
                f"Volume: {int(vol):,}" for vol in data["Volume"]
            ],
        )
        return candlestick, volume
    
    return candlestick, None


def render_candlestick_chart(
    ticker: str,
    timeframe: str = "1d",
    indicators: Optional[List[str]] = None,
    height: int = 600,
    show_volume: bool = True,
    drawing_tools: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Render an interactive candlestick chart with technical indicators.
    
    Args:
        ticker: Stock symbol to chart
        timeframe: One of TIMEFRAME_OPTIONS keys
        indicators: List of indicator names to overlay
        height: Chart height in pixels
        show_volume: Whether to show volume bars
        drawing_tools: List of drawing tool configurations
    
    Requirements:
        - 18.1: Multiple timeframe support
        - 18.3: Technical indicator overlays
        - 18.5: Volume bars
        - 18.6: Zoom and pan
        - 18.11: Fast rendering
    """
    if not STREAMLIT_AVAILABLE or not PLOTLY_AVAILABLE:
        logger.error("Required libraries not available")
        return
    
    # Fetch data
    data = fetch_price_data(ticker, timeframe)
    
    if data.empty:
        st.error(f"Unable to fetch data for {ticker}")
        return
    
    # Create subplot layout
    row_heights = [0.7, 0.3] if show_volume else [1.0]
    rows = 2 if show_volume else 1
    
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        specs=[[{"secondary_y": False}]] * rows,
    )
    
    # Add candlestick trace
    candlestick, volume = create_candlestick_trace(data, name=ticker, show_volume=show_volume)
    fig.add_trace(candlestick, row=1, col=1)
    
    # Add volume if enabled
    if show_volume and volume:
        fig.add_trace(volume, row=2, col=1)
    
    # Add technical indicators
    if indicators:
        from .indicators import (
            calculate_sma,
            calculate_ema,
            calculate_rsi,
            calculate_macd,
            calculate_bollinger_bands,
        )
        
        for indicator in indicators:
            if indicator.startswith("SMA"):
                period = int(indicator.split("_")[1]) if "_" in indicator else 20
                sma = calculate_sma(data["Close"], period)
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=sma,
                        name=f"SMA({period})",
                        line=dict(width=1.5),
                    ),
                    row=1,
                    col=1,
                )
            
            elif indicator.startswith("EMA"):
                period = int(indicator.split("_")[1]) if "_" in indicator else 20
                ema = calculate_ema(data["Close"], period)
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=ema,
                        name=f"EMA({period})",
                        line=dict(width=1.5, dash="dash"),
                    ),
                    row=1,
                    col=1,
                )
            
            elif indicator == "BB":
                upper, middle, lower = calculate_bollinger_bands(data["Close"])
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=upper,
                        name="BB Upper",
                        line=dict(width=1, color="rgba(100, 100, 255, 0.5)"),
                    ),
                    row=1,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=middle,
                        name="BB Middle",
                        line=dict(width=1, color="rgba(100, 100, 255, 0.8)"),
                    ),
                    row=1,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=lower,
                        name="BB Lower",
                        line=dict(width=1, color="rgba(100, 100, 255, 0.5)"),
                        fill="tonexty",
                        fillcolor="rgba(100, 100, 255, 0.1)",
                    ),
                    row=1,
                    col=1,
                )
    
    # Add drawing tools
    if drawing_tools:
        for tool in drawing_tools:
            if tool["type"] == "trendline":
                fig.add_shape(
                    type="line",
                    x0=tool["x0"],
                    y0=tool["y0"],
                    x1=tool["x1"],
                    y1=tool["y1"],
                    line=dict(color=tool.get("color", "#ffeb3b"), width=2),
                    row=1,
                    col=1,
                )
            
            elif tool["type"] == "horizontal":
                fig.add_hline(
                    y=tool["y"],
                    line=dict(color=tool.get("color", "#ff9800"), width=2, dash="dash"),
                    row=1,
                    col=1,
                )
            
            elif tool["type"] == "fibonacci":
                # Add Fibonacci retracement levels
                high = tool["high"]
                low = tool["low"]
                levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
                colors = ["#f44336", "#ff9800", "#ffeb3b", "#4caf50", "#2196f3", "#9c27b0", "#795548"]
                
                for level, color in zip(levels, colors):
                    price = high - (high - low) * level
                    fig.add_hline(
                        y=price,
                        line=dict(color=color, width=1, dash="dot"),
                        annotation=dict(text=f"{level:.1%}", font=dict(color=color, size=10)),
                        row=1,
                        col=1,
                    )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f"{ticker} - {TIMEFRAME_OPTIONS[timeframe]['label']}",
            font=dict(size=20, color=COLORS["text"]),
        ),
        xaxis=dict(
            rangeslider=dict(visible=False),
            type="date",
            gridcolor=COLORS["grid"],
            showgrid=True,
        ),
        yaxis=dict(
            title="Price ($)",
            gridcolor=COLORS["grid"],
            showgrid=True,
        ),
        hovermode="x unified",
        height=height,
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=60, r=20, t=80, b=60),
    )
    
    if show_volume:
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    # Enable drag and zoom
    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "modeBarButtonsToAdd": ["drawline", "drawopenpath", "eraseshape"],
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"{ticker}_{timeframe}_{datetime.now().strftime('%Y%m%d')}",
            "height": 800,
            "width": 1400,
            "scale": 2,
        },
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)


def render_multi_stock_comparison(
    tickers: List[str],
    timeframe: str = "1d",
    normalize: bool = True,
    height: int = 600,
) -> None:
    """
    Render a comparison chart of multiple stocks on the same plot.
    
    Args:
        tickers: List of stock symbols to compare
        timeframe: One of TIMEFRAME_OPTIONS keys
        normalize: Whether to normalize prices to percentage change
        height: Chart height in pixels
    
    Requirement 18.4: Chart comparison mode for multiple stocks
    """
    if not STREAMLIT_AVAILABLE or not PLOTLY_AVAILABLE:
        logger.error("Required libraries not available")
        return
    
    if not tickers:
        st.warning("No tickers provided for comparison")
        return
    
    fig = go.Figure()
    
    for ticker in tickers:
        data = fetch_price_data(ticker, timeframe)
        
        if data.empty:
            st.warning(f"No data available for {ticker}")
            continue
        
        if normalize:
            # Normalize to percentage change from first value
            prices = (data["Close"] / data["Close"].iloc[0] - 1) * 100
            y_label = "% Change"
        else:
            prices = data["Close"]
            y_label = "Price ($)"
        
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=prices,
                name=ticker,
                mode="lines",
                line=dict(width=2),
                hovertemplate=f"<b>{ticker}</b><br>%{{x}}<br>%{{y:.2f}}<extra></extra>",
            )
        )
    
    fig.update_layout(
        title=dict(
            text=f"Stock Comparison - {TIMEFRAME_OPTIONS[timeframe]['label']}",
            font=dict(size=20, color=COLORS["text"]),
        ),
        xaxis=dict(
            title="Date",
            type="date",
            gridcolor=COLORS["grid"],
            showgrid=True,
        ),
        yaxis=dict(
            title=y_label,
            gridcolor=COLORS["grid"],
            showgrid=True,
        ),
        hovermode="x unified",
        height=height,
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font=dict(color=COLORS["text"]),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=60, r=20, t=80, b=60),
    )
    
    config = {
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"comparison_{datetime.now().strftime('%Y%m%d')}",
            "height": 800,
            "width": 1400,
            "scale": 2,
        },
    }
    
    st.plotly_chart(fig, use_container_width=True, config=config)


def demo_generate_sample_data(ticker: str = "DEMO", days: int = 100) -> pd.DataFrame:
    """
    Generate sample OHLCV data for demonstration purposes.
    
    This is used when yfinance is unavailable or for testing.
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    
    # Generate random walk with trend
    np.random.seed(42)
    returns = np.random.randn(days) * 0.02 + 0.001
    prices = 100 * np.exp(np.cumsum(returns))
    
    # Generate OHLC from close prices
    data = pd.DataFrame(index=dates)
    data["Close"] = prices
    data["Open"] = data["Close"].shift(1).fillna(data["Close"].iloc[0])
    data["High"] = data[["Open", "Close"]].max(axis=1) * (1 + np.random.rand(days) * 0.02)
    data["Low"] = data[["Open", "Close"]].min(axis=1) * (1 - np.random.rand(days) * 0.02)
    data["Volume"] = (np.random.rand(days) * 10000000 + 5000000).astype(int)
    
    return data
