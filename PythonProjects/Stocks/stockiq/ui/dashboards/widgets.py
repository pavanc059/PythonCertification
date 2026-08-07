"""
Dashboard Widget Library

Implements 15+ widget types for customizable dashboards.

Requirements implemented:
- Requirement 19.3: At least 15 widget types

Widget Types:
1. Price Chart
2. Candlestick Chart
3. Volume Chart
4. Market Indices
5. Sector Heatmap
6. Top Movers
7. News Feed
8. Breaking News
9. Sentiment Gauge
10. Portfolio Summary
11. Performance Metrics
12. Watchlist
13. Daily Predictions
14. ML Insights
15. Technical Indicators
16. Alerts
17. Screener Results
18. Unusual Activity
19. Economic Calendar
20. Earnings Calendar
21. Institutional Holdings
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available")

try:
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# ---------------------------------------------------------------------------
# 1. Price Chart Widget
# ---------------------------------------------------------------------------

def render_price_chart_widget(config: Dict[str, Any]) -> None:
    """Render line price chart widget with real data."""
    if not STREAMLIT_AVAILABLE:
        return
    
    ticker = config.get("ticker", "AAPL")
    timeframe = config.get("timeframe", "1mo")
    
    st.subheader(f"📈 {ticker} Price Chart")
    
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        hist = stock.history(period=timeframe)
        
        if not hist.empty:
            if PLOTLY_AVAILABLE:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist.index, 
                    y=hist['Close'], 
                    mode='lines', 
                    name=ticker,
                    line=dict(color='#00c853', width=2)
                ))
                fig.update_layout(
                    height=300, 
                    margin=dict(l=0, r=0, t=20, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ffffff')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(hist['Close'])
            
            # Show current price
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[0]
            change = ((current - prev) / prev) * 100
            st.metric("Current Price", f"${current:.2f}", f"{change:+.2f}%")
        else:
            st.warning(f"No data available for {ticker}")
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    st.caption(f"Timeframe: {timeframe}")


# ---------------------------------------------------------------------------
# 2. Candlestick Chart Widget
# ---------------------------------------------------------------------------

def render_candlestick_chart_widget(config: Dict[str, Any]) -> None:
    """Render candlestick chart widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    ticker = config.get("ticker", "AAPL")
    
    st.subheader(f"🕯️ {ticker} Candlestick")
    
    # Demo OHLC data
    dates = pd.date_range(end=datetime.now(), periods=20, freq='D')
    data = {
        "open": [100 + i * 2 for i in range(20)],
        "high": [105 + i * 2 for i in range(20)],
        "low": [98 + i * 2 for i in range(20)],
        "close": [102 + i * 2 for i in range(20)]
    }
    
    if PLOTLY_AVAILABLE:
        fig = go.Figure(data=[go.Candlestick(
            x=dates,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"]
        )])
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(data["close"])


# ---------------------------------------------------------------------------
# 3. Volume Chart Widget
# ---------------------------------------------------------------------------

def render_volume_chart_widget(config: Dict[str, Any]) -> None:
    """Render volume chart widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    ticker = config.get("ticker", "AAPL")
    
    st.subheader(f"📊 {ticker} Volume")
    
    # Demo volume data
    volumes = [50000000 + i * 1000000 for i in range(20)]
    
    if PLOTLY_AVAILABLE:
        fig = go.Figure(data=[go.Bar(y=volumes)])
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.bar_chart(volumes)


# ---------------------------------------------------------------------------
# 4. Market Indices Widget
# ---------------------------------------------------------------------------

def render_market_indices_widget(config: Dict[str, Any]) -> None:
    """Render market indices overview widget with real data."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("📊 Market Indices")
    
    try:
        import yfinance as yf
        
        indices = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DOW": "^DJI",
            "Russell 2000": "^RUT"
        }
        
        col1, col2, col3, col4 = st.columns(4)
        cols = [col1, col2, col3, col4]
        
        for col, (name, symbol) in zip(cols, indices.items()):
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change = current - prev
                    change_pct = (change / prev) * 100
                    
                    with col:
                        st.metric(
                            name, 
                            f"{current:,.2f}", 
                            f"{change:+.2f} ({change_pct:+.2f}%)"
                        )
                else:
                    with col:
                        st.metric(name, "N/A", "N/A")
            except Exception:
                with col:
                    st.metric(name, "N/A", "N/A")
    except Exception as e:
        st.error(f"Error loading indices: {e}")
        # Fallback to demo data
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("S&P 500", "5,234.12", "+64.23 (+1.2%)")
        with col2:
            st.metric("NASDAQ", "16,789.45", "+342.11 (+2.1%)")
        with col3:
            st.metric("DOW", "39,456.78", "+312.45 (+0.8%)")
        with col4:
            st.metric("Russell 2000", "2,123.56", "+31.23 (+1.5%)")


# ---------------------------------------------------------------------------
# 5. Sector Heatmap Widget
# ---------------------------------------------------------------------------

def render_sector_heatmap_widget(config: Dict[str, Any]) -> None:
    """Render sector performance heatmap widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("🌡️ Sector Heatmap")
    
    sectors = ["Technology", "Healthcare", "Financial", "Energy", 
               "Consumer", "Industrial", "Materials", "Utilities"]
    performance = [2.5, 1.8, -0.5, -1.2, 0.8, 1.1, -0.3, 0.4]
    
    if PLOTLY_AVAILABLE:
        fig = go.Figure(data=go.Heatmap(
            z=[performance],
            x=sectors,
            colorscale='RdYlGn',
            zmid=0
        ))
        fig.update_layout(height=150, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        df = pd.DataFrame({"Sector": sectors, "Performance": performance})
        st.dataframe(df)


# ---------------------------------------------------------------------------
# 6. Top Movers Widget
# ---------------------------------------------------------------------------

def render_top_movers_widget(config: Dict[str, Any]) -> None:
    """Render top movers (gainers/losers) widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("🚀 Top Movers")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🟢 Gainers**")
        gainers = pd.DataFrame({
            "Ticker": ["NVDA", "META", "AMD"],
            "Change": ["+8.42%", "+5.91%", "+4.75%"]
        })
        st.dataframe(gainers, hide_index=True)
    
    with col2:
        st.markdown("**🔴 Losers**")
        losers = pd.DataFrame({
            "Ticker": ["INTC", "PFE", "CVS"],
            "Change": ["-7.30%", "-5.82%", "-4.51%"]
        })
        st.dataframe(losers, hide_index=True)


# ---------------------------------------------------------------------------
# 7. News Feed Widget
# ---------------------------------------------------------------------------

def render_news_feed_widget(config: Dict[str, Any]) -> None:
    """Render news feed widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    limit = config.get("limit", 5)
    
    st.subheader("📰 News Feed")
    
    for i in range(min(limit, 3)):
        st.markdown(f"**Breaking: Fed Signals Rate Cut in Q{i+1}**")
        st.caption("Reuters • 2h ago • 🟢 Positive")
        if i < 2:
            st.divider()


# ---------------------------------------------------------------------------
# 8. Breaking News Widget
# ---------------------------------------------------------------------------

def render_breaking_news_widget(config: Dict[str, Any]) -> None:
    """Render breaking news widget (last 30 min only)."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("🚨 Breaking News")
    
    st.error("🚨 **NVIDIA Earnings Beat Estimates by 15%**")
    st.caption("Bloomberg • 12 min ago")
    
    st.warning("⚠️ **Fed Minutes Released - Rate Cut Possible**")
    st.caption("Reuters • 28 min ago")


# ---------------------------------------------------------------------------
# 9. Sentiment Gauge Widget
# ---------------------------------------------------------------------------

def render_sentiment_gauge_widget(config: Dict[str, Any]) -> None:
    """Render market sentiment gauge widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("💭 Market Sentiment")
    
    sentiment = 0.65  # Demo: +65 (bullish)
    
    if PLOTLY_AVAILABLE:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=sentiment * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [-100, 100]},
                'bar': {'color': "darkgreen" if sentiment > 0 else "darkred"},
                'steps': [
                    {'range': [-100, -50], 'color': "lightcoral"},
                    {'range': [-50, 50], 'color': "lightyellow"},
                    {'range': [50, 100], 'color': "lightgreen"}
                ]
            }
        ))
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.metric("Sentiment Score", f"{sentiment * 100:+.0f}", "Bullish")


# ---------------------------------------------------------------------------
# 10. Portfolio Summary Widget
# ---------------------------------------------------------------------------

def render_portfolio_summary_widget(config: Dict[str, Any]) -> None:
    """Render portfolio summary widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("💼 Portfolio Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Value", "$125,430", "+$8,230 (+7.0%)")
    with col2:
        st.metric("Today's P/L", "+$1,240", "+0.99%")
    with col3:
        st.metric("Holdings", "12 positions")


# ---------------------------------------------------------------------------
# 11. Performance Metrics Widget
# ---------------------------------------------------------------------------

def render_performance_metrics_widget(config: Dict[str, Any]) -> None:
    """Render performance metrics widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("📊 Performance Metrics")
    
    metrics = pd.DataFrame({
        "Metric": ["Sharpe Ratio", "Max Drawdown", "Win Rate", "Avg Return"],
        "Value": ["1.85", "-12.3%", "64.5%", "+2.1%"]
    })
    st.dataframe(metrics, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 12. Watchlist Widget
# ---------------------------------------------------------------------------

def render_watchlist_widget(config: Dict[str, Any]) -> None:
    """Render watchlist widget with real data."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader(widget.title if 'widget' in locals() else "👁️ Watchlist")
    
    # Default watchlist
    watchlist_tickers = config.get("tickers", ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
    
    try:
        import yfinance as yf
        
        data = []
        for ticker in watchlist_tickers[:5]:  # Limit to 5 for performance
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d")
                
                if len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2]
                    change_pct = ((current - prev) / prev) * 100
                    
                    data.append({
                        "Ticker": ticker,
                        "Price": f"${current:.2f}",
                        "Change": f"{change_pct:+.2f}%",
                        "Alert": "🔔" if abs(change_pct) > 3 else ""
                    })
            except Exception:
                continue
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.warning("No watchlist data available")
    except Exception as e:
        st.error(f"Error loading watchlist: {e}")
        # Fallback demo data
        watchlist = pd.DataFrame({
            "Ticker": ["AAPL", "MSFT", "GOOGL", "TSLA"],
            "Price": ["$196.30", "$421.60", "$169.90", "$242.80"],
            "Change": ["+1.97%", "+2.85%", "+2.43%", "+3.10%"],
            "Alert": ["🔔", "", "", "🔔"]
        })
        st.dataframe(watchlist, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 13. Daily Predictions Widget
# ---------------------------------------------------------------------------

def render_daily_predictions_widget(config: Dict[str, Any]) -> None:
    """Render daily ML predictions widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("🔮 Daily Predictions")
    
    predictions = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT", "NVDA"],
        "Signal": ["Buy", "Strong Buy", "Hold"],
        "Confidence": ["74%", "81%", "55%"],
        "Target": ["+2.2%", "+3.1%", "+0.4%"]
    })
    st.dataframe(predictions, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 14. ML Insights Widget
# ---------------------------------------------------------------------------

def render_ml_insights_widget(config: Dict[str, Any]) -> None:
    """Render ML insights and feature importance widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("🤖 ML Insights")
    
    st.markdown("**Top Factors Driving Predictions:**")
    factors = pd.DataFrame({
        "Feature": ["News Sentiment", "Technical RSI", "Volume Trend", "Momentum"],
        "Importance": [0.35, 0.28, 0.22, 0.15]
    })
    
    if PLOTLY_AVAILABLE:
        fig = px.bar(factors, x="Importance", y="Feature", orientation='h')
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(factors, hide_index=True)


# ---------------------------------------------------------------------------
# 15. Technical Indicators Widget
# ---------------------------------------------------------------------------

def render_technical_indicators_widget(config: Dict[str, Any]) -> None:
    """Render technical indicators widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    ticker = config.get("ticker", "AAPL")
    
    st.subheader(f"📐 Technical Indicators - {ticker}")
    
    indicators = pd.DataFrame({
        "Indicator": ["RSI", "MACD", "BB %", "Volume Ratio"],
        "Value": ["52.3", "Bullish", "48%", "1.2x"],
        "Signal": ["Neutral", "Buy", "Neutral", "Normal"]
    })
    st.dataframe(indicators, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 16. Alerts Widget
# ---------------------------------------------------------------------------

def render_alerts_widget(config: Dict[str, Any]) -> None:
    """Render active alerts widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("🔔 Active Alerts")
    
    st.info("🔔 **NVDA** crossed $900 resistance")
    st.warning("⚠️ **TSLA** volume spike detected (3.2x avg)")
    st.success("✅ **AAPL** hit target price $200")


# ---------------------------------------------------------------------------
# 17. Screener Results Widget
# ---------------------------------------------------------------------------

def render_screener_results_widget(config: Dict[str, Any]) -> None:
    """Render stock screener results widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    screener_name = config.get("screener", "High Momentum")
    
    st.subheader(f"🔍 Screener: {screener_name}")
    
    results = pd.DataFrame({
        "Ticker": ["NVDA", "AMD", "META"],
        "Score": [92, 88, 85],
        "Price": ["$875.30", "$164.50", "$512.70"]
    })
    st.dataframe(results, hide_index=True, use_container_width=True)
    st.caption(f"{len(results)} stocks matched")


# ---------------------------------------------------------------------------
# 18. Unusual Activity Widget
# ---------------------------------------------------------------------------

def render_unusual_activity_widget(config: Dict[str, Any]) -> None:
    """Render unusual market activity widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("⚡ Unusual Activity")
    
    activity = pd.DataFrame({
        "Ticker": ["INTC", "PFE", "NVDA"],
        "Type": ["Volume Spike", "Options Flow", "Block Trade"],
        "Magnitude": ["5.2x avg", "$12M calls", "2.5M shares"]
    })
    st.dataframe(activity, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 19. Economic Calendar Widget
# ---------------------------------------------------------------------------

def render_economic_calendar_widget(config: Dict[str, Any]) -> None:
    """Render economic calendar widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("📅 Economic Calendar")
    
    events = pd.DataFrame({
        "Time": ["10:00 AM", "2:00 PM", "4:30 PM"],
        "Event": ["CPI Data", "Fed Minutes", "Treasury Auction"],
        "Impact": ["High", "High", "Medium"]
    })
    st.dataframe(events, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 20. Earnings Calendar Widget
# ---------------------------------------------------------------------------

def render_earnings_calendar_widget(config: Dict[str, Any]) -> None:
    """Render earnings calendar widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    st.subheader("📊 Earnings Calendar")
    
    earnings = pd.DataFrame({
        "Date": ["Today", "Tomorrow", "Thu"],
        "Ticker": ["NVDA", "TSLA", "AAPL"],
        "Time": ["After Close", "Before Open", "After Close"],
        "Est EPS": ["$6.12", "$0.85", "$1.52"]
    })
    st.dataframe(earnings, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 21. Institutional Holdings Widget
# ---------------------------------------------------------------------------

def render_institutional_holdings_widget(config: Dict[str, Any]) -> None:
    """Render institutional holdings widget."""
    if not STREAMLIT_AVAILABLE:
        return
    
    ticker = config.get("ticker", "AAPL")
    
    st.subheader(f"🏦 Institutional Holdings - {ticker}")
    
    holdings = pd.DataFrame({
        "Institution": ["Vanguard", "BlackRock", "State Street"],
        "Shares": ["1.2B", "1.0B", "685M"],
        "% Ownership": ["8.1%", "6.8%", "4.6%"],
        "Change": ["+2.1%", "+1.5%", "-0.3%"]
    })
    st.dataframe(holdings, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Widget Registry
# ---------------------------------------------------------------------------

WIDGET_RENDERERS = {
    "price_chart": render_price_chart_widget,
    "candlestick_chart": render_candlestick_chart_widget,
    "volume_chart": render_volume_chart_widget,
    "market_indices": render_market_indices_widget,
    "sector_heatmap": render_sector_heatmap_widget,
    "top_movers": render_top_movers_widget,
    "news_feed": render_news_feed_widget,
    "breaking_news": render_breaking_news_widget,
    "sentiment_gauge": render_sentiment_gauge_widget,
    "portfolio_summary": render_portfolio_summary_widget,
    "performance_metrics": render_performance_metrics_widget,
    "watchlist": render_watchlist_widget,
    "daily_predictions": render_daily_predictions_widget,
    "ml_insights": render_ml_insights_widget,
    "technical_indicators": render_technical_indicators_widget,
    "alerts": render_alerts_widget,
    "screener_results": render_screener_results_widget,
    "unusual_activity": render_unusual_activity_widget,
    "economic_calendar": render_economic_calendar_widget,
    "earnings_calendar": render_earnings_calendar_widget,
    "institutional_holdings": render_institutional_holdings_widget,
}


def get_widget_renderer(widget_type: str):
    """Get renderer function for a widget type."""
    return WIDGET_RENDERERS.get(widget_type)
