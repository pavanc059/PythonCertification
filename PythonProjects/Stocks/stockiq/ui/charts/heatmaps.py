"""
Heatmap Visualizations

Interactive heatmaps for:
- Sector performance visualization
- Correlation matrices

Requirement 18.9: Heat maps for sector performance visualization
Requirement 18.10: Correlation matrices as interactive heat maps
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

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
    import plotly.express as px
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


def fetch_sector_performance(
    sector_etfs: Optional[Dict[str, str]] = None,
    period: str = "1d",
) -> pd.DataFrame:
    """
    Fetch sector ETF performance data.
    
    Args:
        sector_etfs: Dictionary mapping ticker symbols to sector names
        period: Time period for performance calculation
    
    Returns:
        DataFrame with sector performance data
    """
    if sector_etfs is None:
        # Default SPDR sector ETFs
        sector_etfs = {
            "XLK": "Technology",
            "XLV": "Healthcare",
            "XLF": "Financials",
            "XLE": "Energy",
            "XLI": "Industrials",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLU": "Utilities",
            "XLRE": "Real Estate",
            "XLB": "Materials",
            "XLC": "Communication Services",
        }
    
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available - using demo data")
        return _demo_sector_data(sector_etfs)
    
    try:
        tickers = list(sector_etfs.keys())
        data = yf.download(
            tickers,
            period="2d",
            interval="1d",
            progress=False,
            threads=True,
        )
        
        performance = []
        for ticker, sector in sector_etfs.items():
            try:
                if hasattr(data["Close"], "columns"):
                    closes = data["Close"][ticker].dropna()
                else:
                    closes = data["Close"].dropna()
                
                if len(closes) >= 2:
                    pct_change = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100
                    performance.append({
                        "ticker": ticker,
                        "sector": sector,
                        "change_pct": pct_change,
                        "price": closes.iloc[-1],
                    })
            except Exception as exc:
                logger.debug(f"Failed to process {ticker}: {exc}")
        
        return pd.DataFrame(performance)
    
    except Exception as exc:
        logger.error(f"Failed to fetch sector performance: {exc}")
        return _demo_sector_data(sector_etfs)


def _demo_sector_data(sector_etfs: Dict[str, str]) -> pd.DataFrame:
    """Generate demo sector performance data."""
    np.random.seed(42)
    data = []
    for ticker, sector in sector_etfs.items():
        data.append({
            "ticker": ticker,
            "sector": sector,
            "change_pct": np.random.randn() * 1.5,
            "price": np.random.uniform(50, 150),
        })
    return pd.DataFrame(data)


def render_sector_heatmap(
    sector_etfs: Optional[Dict[str, str]] = None,
    period: str = "1d",
    height: int = 400,
) -> None:
    """
    Render an interactive sector performance heatmap.
    
    Displays sector ETF performance as a color-coded treemap where:
    - Size represents relative market weight
    - Color represents performance (green=positive, red=negative)
    
    Args:
        sector_etfs: Dictionary mapping ticker symbols to sector names
        period: Time period for performance calculation
        height: Chart height in pixels
    
    Requirement 18.9: Heat maps for sector performance visualization
    """
    if not STREAMLIT_AVAILABLE or not PLOTLY_AVAILABLE:
        logger.error("Required libraries not available")
        return
    
    # Fetch sector data
    df = fetch_sector_performance(sector_etfs, period)
    
    if df.empty:
        st.error("Unable to fetch sector performance data")
        return
    
    # Create treemap
    fig = go.Figure(go.Treemap(
        labels=[f"{row['sector']}<br>{row['change_pct']:+.2f}%" for _, row in df.iterrows()],
        parents=[""] * len(df),
        values=[1] * len(df),  # Equal size boxes
        customdata=df[["ticker", "change_pct", "price"]].values,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Ticker: %{customdata[0]}<br>"
            "Change: %{customdata[1]:.2f}%<br>"
            "Price: $%{customdata[2]:.2f}<extra></extra>"
        ),
        marker=dict(
            colors=df["change_pct"],
            colorscale=[
                [0.0, "#d50000"],    # Deep red (most negative)
                [0.35, "#ff6d00"],   # Orange
                [0.45, "#424242"],   # Dark grey (neutral)
                [0.55, "#424242"],
                [0.65, "#69f0ae"],   # Light green
                [1.0, "#00c853"],    # Deep green (most positive)
            ],
            cmid=0,
            showscale=True,
            colorbar=dict(
                title=dict(text="% Change", side="right"),
                tickformat="+.1f",
                thickness=15,
                len=0.8,
            ),
        ),
        textfont=dict(size=14, color="white"),
        tiling=dict(packing="squarify"),
    ))
    
    # Ensure symmetric color scale
    max_abs = df["change_pct"].abs().max() or 1.0
    fig.data[0].marker.cmin = -max_abs
    fig.data[0].marker.cmax = max_abs
    
    fig.update_layout(
        title=dict(
            text="Sector Performance Heatmap",
            font=dict(size=18, color="#cccccc"),
        ),
        height=height,
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#cccccc"),
        margin=dict(l=0, r=0, t=50, b=0),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def calculate_correlation_matrix(
    tickers: List[str],
    period: str = "1y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Calculate correlation matrix for a list of tickers.
    
    Args:
        tickers: List of stock symbols
        period: Time period for correlation calculation
        interval: Data interval
    
    Returns:
        DataFrame containing correlation matrix
    """
    if not YFINANCE_AVAILABLE:
        logger.warning("yfinance not available - using demo data")
        return _demo_correlation_matrix(tickers)
    
    try:
        # Download price data
        data = yf.download(
            tickers,
            period=period,
            interval=interval,
            progress=False,
            threads=True,
        )
        
        if data.empty:
            return _demo_correlation_matrix(tickers)
        
        # Extract closing prices
        if isinstance(data.columns, pd.MultiIndex):
            closes = data["Close"]
        else:
            closes = data[["Close"]]
        
        # Calculate returns
        returns = closes.pct_change().dropna()
        
        # Calculate correlation matrix
        corr_matrix = returns.corr()
        
        return corr_matrix
    
    except Exception as exc:
        logger.error(f"Failed to calculate correlation matrix: {exc}")
        return _demo_correlation_matrix(tickers)


def _demo_correlation_matrix(tickers: List[str]) -> pd.DataFrame:
    """Generate demo correlation matrix."""
    np.random.seed(42)
    n = len(tickers)
    
    # Generate random correlation matrix
    random_matrix = np.random.randn(n, n)
    corr = np.corrcoef(random_matrix)
    
    return pd.DataFrame(corr, index=tickers, columns=tickers)


def render_correlation_matrix(
    tickers: List[str],
    period: str = "1y",
    height: int = 600,
    show_values: bool = True,
) -> None:
    """
    Render an interactive correlation matrix heatmap.
    
    Displays pairwise correlations between stocks as a color-coded matrix:
    - Red indicates negative correlation
    - Green indicates positive correlation
    - Intensity indicates strength
    
    Args:
        tickers: List of stock symbols to analyze
        period: Time period for correlation calculation
        height: Chart height in pixels
        show_values: Whether to display correlation values on cells
    
    Requirement 18.10: Correlation matrices as interactive heat maps
    """
    if not STREAMLIT_AVAILABLE or not PLOTLY_AVAILABLE:
        logger.error("Required libraries not available")
        return
    
    if not tickers or len(tickers) < 2:
        st.warning("Need at least 2 tickers for correlation analysis")
        return
    
    # Calculate correlation matrix
    corr_matrix = calculate_correlation_matrix(tickers, period)
    
    if corr_matrix.empty:
        st.error("Unable to calculate correlation matrix")
        return
    
    # Create heatmap
    fig = go.Figure(go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.index,
        colorscale=[
            [0.0, "#d50000"],    # Strong negative correlation (-1.0)
            [0.25, "#ff6d00"],   # Weak negative correlation
            [0.5, "#424242"],    # No correlation (0.0)
            [0.75, "#69f0ae"],   # Weak positive correlation
            [1.0, "#00c853"],    # Strong positive correlation (+1.0)
        ],
        zmid=0,
        zmin=-1,
        zmax=1,
        text=corr_matrix.values if show_values else None,
        texttemplate="%{text:.2f}" if show_values else None,
        textfont=dict(size=10, color="white"),
        hovertemplate=(
            "X: %{x}<br>"
            "Y: %{y}<br>"
            "Correlation: %{z:.3f}<extra></extra>"
        ),
        colorbar=dict(
            title="Correlation",
            tickvals=[-1, -0.5, 0, 0.5, 1],
            ticktext=["-1.0", "-0.5", "0.0", "+0.5", "+1.0"],
            thickness=15,
            len=0.8,
        ),
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Correlation Matrix ({period})",
            font=dict(size=18, color="#cccccc"),
        ),
        xaxis=dict(
            tickangle=-45,
            tickfont=dict(size=11),
            side="bottom",
        ),
        yaxis=dict(
            tickfont=dict(size=11),
        ),
        height=height,
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font=dict(color="#cccccc"),
        margin=dict(l=100, r=20, t=80, b=100),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_network(
    tickers: List[str],
    period: str = "1y",
    threshold: float = 0.5,
    height: int = 600,
) -> None:
    """
    Render a network graph of stock correlations.
    
    Stocks are nodes, and edges connect stocks with correlation above
    the threshold. Edge thickness indicates correlation strength.
    
    Args:
        tickers: List of stock symbols
        period: Time period for correlation calculation
        threshold: Minimum correlation to show edge
        height: Chart height in pixels
    """
    if not STREAMLIT_AVAILABLE or not PLOTLY_AVAILABLE:
        logger.error("Required libraries not available")
        return
    
    # Calculate correlation matrix
    corr_matrix = calculate_correlation_matrix(tickers, period)
    
    if corr_matrix.empty:
        st.error("Unable to calculate correlation matrix")
        return
    
    # Generate network layout (simple circular layout)
    n = len(tickers)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x_pos = np.cos(angles)
    y_pos = np.sin(angles)
    
    # Create edges for correlations above threshold
    edge_traces = []
    for i in range(n):
        for j in range(i + 1, n):
            corr = corr_matrix.iloc[i, j]
            if abs(corr) >= threshold:
                # Edge color based on correlation
                color = "#00c853" if corr > 0 else "#d50000"
                width = abs(corr) * 5
                
                edge_trace = go.Scatter(
                    x=[x_pos[i], x_pos[j]],
                    y=[y_pos[i], y_pos[j]],
                    mode="lines",
                    line=dict(color=color, width=width),
                    opacity=abs(corr),
                    hoverinfo="text",
                    text=f"{tickers[i]} - {tickers[j]}: {corr:.3f}",
                    showlegend=False,
                )
                edge_traces.append(edge_trace)
    
    # Create nodes
    node_trace = go.Scatter(
        x=x_pos,
        y=y_pos,
        mode="markers+text",
        marker=dict(
            size=20,
            color="#2196f3",
            line=dict(width=2, color="#ffffff"),
        ),
        text=tickers,
        textposition="top center",
        textfont=dict(size=12, color="#cccccc"),
        hoverinfo="text",
        hovertext=tickers,
        showlegend=False,
    )
    
    # Create figure
    fig = go.Figure(data=edge_traces + [node_trace])
    
    fig.update_layout(
        title=dict(
            text=f"Correlation Network (|r| ≥ {threshold})",
            font=dict(size=18, color="#cccccc"),
        ),
        showlegend=False,
        hovermode="closest",
        height=height,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)
