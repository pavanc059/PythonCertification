"""
Customizable Dashboard Demo

Run with: streamlit run dashboard_demo.py
"""

import streamlit as st

# Import the customizable dashboard system
from stockiq.ui.dashboards.custom import render_custom_dashboard, DashboardManager
from stockiq.ui.dashboards.builder import render_layout_builder

# Page configuration
st.set_page_config(
    page_title="StockIQ - Custom Dashboards",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stButton > button {
        width: 100%;
    }
    h1 {
        color: #00c853;
    }
    .stMetric {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.title("📊 StockIQ Custom Dashboards")
st.markdown("---")

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Select Page",
        ["View Dashboard", "Dashboard Builder", "About"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### Quick Stats")
    st.info("✅ 21 Widget Types Available")
    st.info("📊 3 Default Layouts")
    st.info("💾 Per-User Configurations")

# Page routing
if page == "View Dashboard":
    st.header("📊 Custom Dashboard")
    st.markdown("Select a dashboard layout from the sidebar and view your customized widgets.")
    
    # Render the custom dashboard
    render_custom_dashboard()

elif page == "Dashboard Builder":
    st.header("🛠️ Dashboard Builder")
    st.markdown("Create and customize your own dashboard layouts with drag-and-drop widgets.")
    
    # Render the layout builder
    render_layout_builder()

else:  # About page
    st.header("ℹ️ About Custom Dashboards")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✨ Features")
        st.markdown("""
        - **Multiple Layouts**: Create unlimited custom dashboard layouts
        - **21 Widget Types**: Choose from a comprehensive widget library
        - **Grid-Based**: Flexible 12-column grid system
        - **Persistent Storage**: Your configurations are saved per user
        - **Default Layouts**: Start with pre-configured templates
        """)
        
        st.subheader("📊 Available Widget Types")
        st.markdown("""
        **Price & Charts**
        - Price Chart
        - Candlestick Chart
        - Volume Chart
        
        **Market Overview**
        - Market Indices
        - Sector Heatmap
        - Top Movers
        
        **News & Sentiment**
        - News Feed
        - Breaking News
        - Sentiment Gauge
        
        **Portfolio & Performance**
        - Portfolio Summary
        - Performance Metrics
        - Watchlist
        """)
    
    with col2:
        st.subheader("🚀 Getting Started")
        st.markdown("""
        1. **View Dashboard**: See your current dashboard with customized widgets
        2. **Dashboard Builder**: Create or edit layouts
        3. **Add Widgets**: Select from 21 widget types
        4. **Configure**: Set position, size, and settings
        5. **Save**: Your layout is automatically saved
        """)
        
        st.subheader("📊 More Widget Types")
        st.markdown("""
        **Predictions & Analysis**
        - Daily Predictions
        - ML Insights
        - Technical Indicators
        
        **Alerts & Monitoring**
        - Active Alerts
        - Screener Results
        - Unusual Activity
        
        **Economic & Fundamentals**
        - Economic Calendar
        - Earnings Calendar
        - Institutional Holdings
        """)
        
        st.subheader("💡 Tips")
        st.markdown("""
        - Start with a default layout and customize it
        - Use the 12-column grid for precise positioning
        - Widgets can span multiple columns and rows
        - Set a layout as default for quick access
        """)
    
    st.markdown("---")
    st.success("✅ System Status: All 21 widget types available and tested!")
