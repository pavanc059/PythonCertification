"""
Advanced Charting Demo

Demonstrates all features of the stockiq.ui.charts module including:
- Candlestick charts with multiple timeframes
- Technical indicator overlays
- Drawing tools (trendlines, Fibonacci)
- Multi-stock comparison
- Chart export
- Heatmaps

Run with: streamlit run examples/advanced_charting_demo.py
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

# Import charting components
from stockiq.ui.charts import (
    render_candlestick_chart,
    render_multi_stock_comparison,
    TIMEFRAME_OPTIONS,
    AVAILABLE_INDICATORS,
    add_trendline,
    add_horizontal_line,
    add_fibonacci_retracement,
    render_sector_heatmap,
    render_correlation_matrix,
    render_correlation_network,
)

st.set_page_config(
    page_title="Advanced Charting Demo",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Advanced Charting Demo")
st.markdown("---")

# Sidebar configuration
st.sidebar.header("Chart Configuration")

demo_mode = st.sidebar.selectbox(
    "Demo Mode",
    [
        "Candlestick Chart",
        "Technical Indicators",
        "Drawing Tools",
        "Multi-Stock Comparison",
        "Sector Heatmap",
        "Correlation Matrix",
        "Correlation Network",
    ]
)

# ============================================================================
# Demo 1: Candlestick Chart
# ============================================================================

if demo_mode == "Candlestick Chart":
    st.header("Candlestick Chart with Volume")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ticker = st.text_input("Ticker Symbol", value="AAPL")
    
    with col2:
        timeframe = st.selectbox(
            "Timeframe",
            options=list(TIMEFRAME_OPTIONS.keys()),
            format_func=lambda x: TIMEFRAME_OPTIONS[x]["label"]
        )
    
    with col3:
        show_volume = st.checkbox("Show Volume", value=True)
    
    st.markdown("---")
    
    with st.spinner(f"Loading {ticker} data..."):
        render_candlestick_chart(
            ticker=ticker,
            timeframe=timeframe,
            indicators=None,
            height=600,
            show_volume=show_volume,
        )
    
    st.info(f"💡 Use mouse to zoom and pan. Double-click to reset view.")

# ============================================================================
# Demo 2: Technical Indicators
# ============================================================================

elif demo_mode == "Technical Indicators":
    st.header("Technical Indicators Overlay")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.text_input("Ticker Symbol", value="AAPL")
        timeframe = st.selectbox(
            "Timeframe",
            options=list(TIMEFRAME_OPTIONS.keys()),
            format_func=lambda x: TIMEFRAME_OPTIONS[x]["label"]
        )
    
    with col2:
        indicators = st.multiselect(
            "Select Indicators (max 5)",
            options=AVAILABLE_INDICATORS,
            default=["SMA_20", "SMA_50", "BB"],
            max_selections=5,
        )
    
    st.markdown("---")
    
    with st.spinner(f"Loading {ticker} with indicators..."):
        render_candlestick_chart(
            ticker=ticker,
            timeframe=timeframe,
            indicators=indicators,
            height=700,
            show_volume=True,
        )
    
    # Indicator legend
    st.subheader("Available Indicators")
    indicator_info = {
        "SMA_20/50/200": "Simple Moving Average",
        "EMA_12/26/50": "Exponential Moving Average",
        "BB": "Bollinger Bands (20-period, 2-std)",
        "RSI": "Relative Strength Index (14-period)",
        "MACD": "Moving Average Convergence Divergence",
        "ATR": "Average True Range",
        "Stochastic": "Stochastic Oscillator",
        "OBV": "On-Balance Volume",
        "ADX": "Average Directional Index",
        "CCI": "Commodity Channel Index",
    }
    
    cols = st.columns(2)
    for i, (name, desc) in enumerate(indicator_info.items()):
        with cols[i % 2]:
            st.markdown(f"**{name}**: {desc}")

# ============================================================================
# Demo 3: Drawing Tools
# ============================================================================

elif demo_mode == "Drawing Tools":
    st.header("Drawing Tools")
    
    ticker = st.text_input("Ticker Symbol", value="AAPL")
    timeframe = st.selectbox(
        "Timeframe",
        options=["1d", "1w"],
        format_func=lambda x: TIMEFRAME_OPTIONS[x]["label"]
    )
    
    st.markdown("---")
    
    # Example drawing tools
    st.subheader("Example: Support/Resistance Lines")
    
    # Create sample drawing tools
    drawing_tools = []
    
    # Horizontal lines at key levels
    if st.checkbox("Show Support/Resistance Lines", value=True):
        drawing_tools.append({
            "type": "horizontal",
            "y": 175.0,
            "color": "#00c853",
            "label": "Support"
        })
        drawing_tools.append({
            "type": "horizontal",
            "y": 185.0,
            "color": "#d50000",
            "label": "Resistance"
        })
    
    # Trendline
    if st.checkbox("Show Trendline", value=False):
        x0 = datetime.now() - timedelta(days=90)
        x1 = datetime.now()
        drawing_tools.append({
            "type": "trendline",
            "x0": x0,
            "y0": 160.0,
            "x1": x1,
            "y1": 185.0,
            "color": "#ffeb3b"
        })
    
    # Fibonacci retracement
    if st.checkbox("Show Fibonacci Retracement", value=False):
        drawing_tools.append({
            "type": "fibonacci",
            "high": 195.0,
            "low": 165.0,
        })
    
    with st.spinner(f"Loading {ticker} with drawing tools..."):
        render_candlestick_chart(
            ticker=ticker,
            timeframe=timeframe,
            indicators=["SMA_50"],
            height=700,
            show_volume=True,
            drawing_tools=drawing_tools if drawing_tools else None,
        )
    
    st.info("💡 Drawing tools shown are examples. Interactive drawing coming in future update.")

# ============================================================================
# Demo 4: Multi-Stock Comparison
# ============================================================================

elif demo_mode == "Multi-Stock Comparison":
    st.header("Multi-Stock Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tickers_input = st.text_input(
            "Ticker Symbols (comma-separated)",
            value="AAPL, MSFT, GOOGL, TSLA, NVDA"
        )
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
    
    with col2:
        timeframe = st.selectbox(
            "Timeframe",
            options=["1d", "1w"],
            format_func=lambda x: TIMEFRAME_OPTIONS[x]["label"]
        )
        normalize = st.checkbox("Normalize to % Change", value=True)
    
    st.markdown("---")
    
    with st.spinner(f"Comparing {len(tickers)} stocks..."):
        render_multi_stock_comparison(
            tickers=tickers,
            timeframe=timeframe,
            normalize=normalize,
            height=600,
        )
    
    st.info(f"💡 Comparing {', '.join(tickers)} on the same chart.")

# ============================================================================
# Demo 5: Sector Heatmap
# ============================================================================

elif demo_mode == "Sector Heatmap":
    st.header("Sector Performance Heatmap")
    
    st.markdown("""
    Visualizes daily performance of SPDR sector ETFs as a color-coded treemap.
    - **Green**: Positive performance
    - **Red**: Negative performance
    - **Intensity**: Magnitude of change
    """)
    
    st.markdown("---")
    
    with st.spinner("Loading sector performance..."):
        render_sector_heatmap(height=500)
    
    st.subheader("SPDR Sector ETFs")
    sectors = {
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
    
    cols = st.columns(3)
    for i, (ticker, name) in enumerate(sectors.items()):
        with cols[i % 3]:
            st.markdown(f"**{ticker}**: {name}")

# ============================================================================
# Demo 6: Correlation Matrix
# ============================================================================

elif demo_mode == "Correlation Matrix":
    st.header("Stock Correlation Matrix")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tickers_input = st.text_input(
            "Ticker Symbols (comma-separated)",
            value="AAPL, MSFT, GOOGL, TSLA, NVDA, AMZN"
        )
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
    
    with col2:
        period = st.selectbox(
            "Time Period",
            options=["1mo", "3mo", "6mo", "1y", "2y"],
            index=3
        )
        show_values = st.checkbox("Show Correlation Values", value=True)
    
    st.markdown("---")
    
    with st.spinner(f"Calculating correlations for {len(tickers)} stocks..."):
        render_correlation_matrix(
            tickers=tickers,
            period=period,
            height=600,
            show_values=show_values,
        )
    
    st.info("""
    💡 **Interpretation**:
    - **+1.0**: Perfect positive correlation (move together)
    - **0.0**: No correlation
    - **-1.0**: Perfect negative correlation (move opposite)
    """)

# ============================================================================
# Demo 7: Correlation Network
# ============================================================================

elif demo_mode == "Correlation Network":
    st.header("Stock Correlation Network")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tickers_input = st.text_input(
            "Ticker Symbols (comma-separated)",
            value="AAPL, MSFT, GOOGL, TSLA, NVDA, AMZN, META, NFLX"
        )
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
    
    with col2:
        period = st.selectbox(
            "Time Period",
            options=["1mo", "3mo", "6mo", "1y", "2y"],
            index=3
        )
        threshold = st.slider("Correlation Threshold", 0.0, 1.0, 0.5, 0.05)
    
    st.markdown("---")
    
    with st.spinner(f"Building correlation network..."):
        render_correlation_network(
            tickers=tickers,
            period=period,
            threshold=threshold,
            height=600,
        )
    
    st.info(f"""
    💡 **Network Graph**:
    - **Nodes**: Stock symbols
    - **Green edges**: Positive correlation > {threshold}
    - **Red edges**: Negative correlation < -{threshold}
    - **Edge thickness**: Correlation strength
    """)

# ============================================================================
# Footer
# ============================================================================

st.markdown("---")
st.caption("Advanced Charting Module | Stock Analyzer v2.0")
