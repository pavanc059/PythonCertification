"""
StockIQ - Streamlit Web Application Entry Point

This is the main entry point for the Streamlit web interface.
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from stockiq.infrastructure.config import get_settings
from stockiq.infrastructure.database import get_engine
from stockiq.infrastructure.cache import get_cache

# Page configuration
st.set_page_config(
    page_title="StockIQ - Institutional-Grade Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

def check_infrastructure():
    """Check if infrastructure is ready."""
    try:
        # Check database connection
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Check Redis connection
        cache = get_cache()
        cache.ping()
        
        return True
    except Exception as e:
        st.error(f"Infrastructure check failed: {e}")
        return False

def main():
    """Main application entry point."""
    
    # Check infrastructure
    if not check_infrastructure():
        st.error("⚠️ Infrastructure not ready. Please check database and Redis connections.")
        st.info("Run `docker-compose up -d` to start all services.")
        return
    
    # Sidebar
    st.sidebar.title("📈 StockIQ")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        [
            "🏠 Home",
            "📊 Daily Market Brief",
            "💰 Penny Stocks",
            "📰 News Feed",
            "🔮 Predictions",
            "⚠️ Alerts",
            "📋 Watchlist",
            "⚙️ Settings",
        ]
    )
    
    # Main content
    st.title("StockIQ - Institutional-Grade Stock Analyzer")
    
    if page == "🏠 Home":
        show_home()
    elif page == "📊 Daily Market Brief":
        show_daily_brief()
    elif page == "💰 Penny Stocks":
        show_penny_stocks()
    elif page == "📰 News Feed":
        show_news_feed()
    elif page == "🔮 Predictions":
        show_predictions()
    elif page == "⚠️ Alerts":
        show_alerts()
    elif page == "📋 Watchlist":
        show_watchlist()
    elif page == "⚙️ Settings":
        show_settings()

def show_home():
    """Show home page."""
    st.header("Welcome to StockIQ")
    
    st.markdown("""
    ## 🚀 Phase 0: Daily Intelligence System
    
    StockIQ is an institutional-grade stock analysis platform providing:
    
    - **📊 Daily Top Movers**: Real-time identification of top gainers/losers
    - **📰 News Analyzer**: NLP-powered news processing with sentiment scoring
    - **🔮 Daily Predictions**: AI-powered next-day price forecasts
    - **💰 Penny Stock Dashboard**: Momentum tracking for penny stocks
    - **⚠️ Real-Time Alerts**: Instant notifications for market-moving events
    - **📈 Integrated Dashboard**: Complete market overview in one place
    
    ### 🏗️ Current Status
    
    **Phase 0.1: Infrastructure Foundation** - ✅ Complete
    - Database setup with TimescaleDB
    - Redis cache implementation
    - Docker containerization
    
    **Next Steps:**
    - Implement data collection pipeline
    - Build news analysis system
    - Create ML prediction engine
    - Develop penny stock analyzer
    
    ### 📚 Quick Links
    
    - [Documentation](https://github.com/yourusername/stockiq)
    - [API Reference](https://github.com/yourusername/stockiq/wiki)
    - [GitHub Repository](https://github.com/yourusername/stockiq)
    """)
    
    # System status
    st.markdown("---")
    st.subheader("System Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Database", "✅ Connected", "PostgreSQL + TimescaleDB")
    
    with col2:
        st.metric("Cache", "✅ Connected", "Redis 7.0")
    
    with col3:
        st.metric("Workers", "⏳ Pending", "Celery")

def show_daily_brief():
    """Show daily market brief with live data."""
    st.header("📊 Daily Market Brief")
    st.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
    
    # Add refresh button
    col_refresh, col_spacer = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    # Import with error handling
    try:
        from stockiq.ui.dashboards.daily_brief import render_daily_brief_dashboard
        render_daily_brief_dashboard()
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.info("Showing demo data...")

def show_penny_stocks():
    """Show penny stocks dashboard."""
    from stockiq.ui.dashboards.penny_stocks import (
        render_penny_stock_table,
        render_penny_stock_charts,
        render_penny_stock_metrics,
        render_sector_distribution,
        get_refresh_interval_seconds,
    )
    
    st.header("💰 Penny Stock Momentum Dashboard")
    
    # Auto-refresh notice
    refresh_interval = get_refresh_interval_seconds()
    st.info(f"🔄 Dashboard auto-refreshes every {refresh_interval} seconds during market hours")
    st.markdown("---")
    
    # Main content
    render_penny_stock_table()
    st.markdown("---")
    render_penny_stock_charts()
    st.markdown("---")
    render_penny_stock_metrics()
    st.markdown("---")
    render_sector_distribution()

def show_news_feed():
    """Show news feed."""
    st.header("📰 Real-Time News Feed")
    st.info("🚧 Coming soon in Phase 0.3 - News Analysis & Sentiment")

def show_predictions():
    """Show predictions."""
    st.header("🔮 Daily Stock Predictions")
    st.info("🚧 Coming soon in Phase 0.4 - ML Prediction Engine")

def show_alerts():
    """Show alerts."""
    st.header("⚠️ Alerts")
    st.info("🚧 Coming soon in Phase 0.6 - Alert System")

def show_watchlist():
    """Show watchlist."""
    st.header("📋 Watchlist")
    st.info("🚧 Coming soon - Watchlist Management")

def show_settings():
    """Show settings."""
    st.header("⚙️ Settings")
    
    settings = get_settings()
    
    st.subheader("Configuration")
    
    st.text(f"Environment: {settings.app_env}")
    st.text(f"Debug Mode: {settings.debug}")
    st.text(f"Log Level: {settings.log_level}")
    
    st.subheader("Feature Flags")
    
    st.checkbox("Real-Time Streaming", value=settings.enable_real_time_streaming, disabled=True)
    st.checkbox("Deep Learning", value=settings.enable_deep_learning, disabled=True)
    st.checkbox("Alternative Data", value=settings.enable_alternative_data, disabled=True)

if __name__ == "__main__":
    main()
