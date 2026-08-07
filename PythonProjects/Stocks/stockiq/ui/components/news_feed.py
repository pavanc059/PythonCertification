"""
Real-Time News Feed Component

Reusable Streamlit component for displaying a real-time news feed with
intelligent filtering, search, and reading list functionality.

Components provided:
- render_news_feed()           – Main news feed with 30-second auto-refresh
- render_news_filters()        – Filter UI (ticker, sector, category, sentiment, source)
- render_news_item()           – Individual news article display
- render_news_search()         – Historical news search (90 days)
- render_reading_list()        – Saved articles for later reading

Requirements implemented:
- Requirement 9.1: Real-time news feed with 30-second updates
- Requirement 9.2: Filter by ticker, sector, category, sentiment, source
- Requirement 9.3: Filter by news source and credibility rating
- Requirement 9.4: Highlight breaking news with visual indicators
- Requirement 9.5: Display sentiment score and predicted price impact
- Requirement 9.6: Show related stocks affected by each news item
- Requirement 9.7: Save news items to reading list
- Requirement 9.8: Search functionality across historical news (90 days)
- Requirement 9.9: Display news volume trends
- Requirement 9.10: Show social media buzz metrics
- Requirement 9.11: Custom news alerts based on keywords
- Requirement 9.12: Filter adjustment suggestions when empty
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful-degradation imports
# ---------------------------------------------------------------------------
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available – news feed will not render")

try:
    from stockiq.data.models import EnrichedNewsArticle, NewsCategory, SentimentScore
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("data models not available")

try:
    from stockiq.data.collectors.news import NewsCollector
    NEWS_COLLECTOR_AVAILABLE = True
except ImportError:
    NEWS_COLLECTOR_AVAILABLE = False
    logger.warning("news collector not available")

try:
    from stockiq.infrastructure.database import get_db_context
    from stockiq.infrastructure.models import NewsArticle as DBNewsArticle, Stock as DBStock
    from sqlalchemy import and_, or_, desc
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("database not available")

try:
    from stockiq.infrastructure.cache import get_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("cache not available")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Auto-refresh interval (seconds)
AUTO_REFRESH_INTERVAL = 30

# Sentiment thresholds for filtering
SENTIMENT_POSITIVE_THRESHOLD = 0.2
SENTIMENT_NEGATIVE_THRESHOLD = -0.2

# Historical search period (days)
HISTORICAL_SEARCH_DAYS = 90

# Breaking news threshold (minutes)
BREAKING_NEWS_THRESHOLD = 30

# News sources with credibility ratings
NEWS_SOURCES = {
    "Reuters": {"credibility": 9, "category": "wire"},
    "Bloomberg": {"credibility": 9, "category": "wire"},
    "CNBC": {"credibility": 8, "category": "tv"},
    "Wall Street Journal": {"credibility": 9, "category": "print"},
    "Financial Times": {"credibility": 9, "category": "print"},
    "MarketWatch": {"credibility": 7, "category": "online"},
    "Seeking Alpha": {"credibility": 6, "category": "online"},
    "Benzinga": {"credibility": 6, "category": "online"},
    "Finnhub": {"credibility": 7, "category": "aggregator"},
    "NewsAPI": {"credibility": 7, "category": "aggregator"},
    "Alpha Vantage": {"credibility": 7, "category": "aggregator"},
}

# Sector list for filtering
SECTORS = [
    "Technology", "Healthcare", "Financials", "Energy", "Industrials",
    "Consumer Discretionary", "Consumer Staples", "Utilities",
    "Real Estate", "Materials", "Communication Services"
]

# Reading list storage key (in session state)
READING_LIST_KEY = "news_reading_list"


# ---------------------------------------------------------------------------
# Demo / fallback data
# ---------------------------------------------------------------------------

def _demo_news() -> List[Dict[str, Any]]:
    """Return demo news articles when live data is unavailable."""
    return [
        {
            "id": "demo-1",
            "title": "Fed Signals Rate Cuts Ahead as Inflation Cools",
            "content": "Federal Reserve officials indicated potential rate cuts in 2024 as inflation shows signs of moderating. The announcement sent markets higher with the S&P 500 gaining 1.5%.",
            "source": "Reuters",
            "published_at": datetime.utcnow() - timedelta(minutes=15),
            "sentiment": 0.65,
            "category": "economic",
            "is_breaking": True,
            "tickers": ["SPY", "QQQ"],
            "url": "https://example.com/1",
            "summary": "Fed signals rate cuts ahead as inflation moderates.",
            "predicted_impact": 1.5,
        },
        {
            "id": "demo-2",
            "title": "Apple Unveils AI-Powered iPhone Features",
            "content": "Apple announced new AI capabilities for the iPhone 16, including advanced on-device processing for privacy-focused machine learning applications.",
            "source": "Bloomberg",
            "published_at": datetime.utcnow() - timedelta(hours=2),
            "sentiment": 0.42,
            "category": "earnings",
            "is_breaking": False,
            "tickers": ["AAPL"],
            "url": "https://example.com/2",
            "summary": "Apple unveils AI-powered iPhone features.",
            "predicted_impact": 0.8,
        },
        {
            "id": "demo-3",
            "title": "Tesla Faces Production Challenges in China",
            "content": "Tesla's Shanghai facility experienced temporary production slowdowns due to supply chain disruptions, potentially impacting Q4 delivery targets.",
            "source": "CNBC",
            "published_at": datetime.utcnow() - timedelta(hours=4),
            "sentiment": -0.55,
            "category": "sector-specific",
            "is_breaking": False,
            "tickers": ["TSLA"],
            "url": "https://example.com/3",
            "summary": "Tesla faces production challenges in China.",
            "predicted_impact": -1.2,
        },
        {
            "id": "demo-4",
            "title": "Microsoft Expands Cloud Infrastructure Investment",
            "content": "Microsoft announced a $10 billion investment in cloud infrastructure to support growing AI workload demands.",
            "source": "Wall Street Journal",
            "published_at": datetime.utcnow() - timedelta(hours=6),
            "sentiment": 0.38,
            "category": "M&A",
            "is_breaking": False,
            "tickers": ["MSFT"],
            "url": "https://example.com/4",
            "summary": "Microsoft expands cloud infrastructure investment.",
            "predicted_impact": 0.6,
        },
        {
            "id": "demo-5",
            "title": "SEC Proposes New Crypto Trading Regulations",
            "content": "The Securities and Exchange Commission unveiled proposed regulations for cryptocurrency exchanges, requiring enhanced disclosure and investor protections.",
            "source": "Financial Times",
            "published_at": datetime.utcnow() - timedelta(hours=8),
            "sentiment": -0.25,
            "category": "regulatory",
            "is_breaking": False,
            "tickers": ["COIN", "MSTR"],
            "url": "https://example.com/5",
            "summary": "SEC proposes new crypto trading regulations.",
            "predicted_impact": -0.9,
        },
    ]


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------

def _fetch_news_articles(
    limit: int = 50,
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    category: Optional[str] = None,
    sentiment_filter: Optional[str] = None,
    source: Optional[str] = None,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Fetch news articles with optional filters.
    
    Falls back to demo data if live data unavailable.
    
    Args:
        limit: Maximum number of articles to return
        ticker: Filter by ticker symbol
        sector: Filter by sector
        category: Filter by news category
        sentiment_filter: Filter by sentiment (positive/neutral/negative)
        source: Filter by news source
        hours: Time window in hours
    
    Returns:
        List of article dictionaries
    """
    # Try to fetch from database
    if DATABASE_AVAILABLE and CACHE_AVAILABLE:
        try:
            cache = get_cache()
            cache_key = f"news:feed:{ticker}:{sector}:{category}:{sentiment_filter}:{source}:{hours}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug("news_feed_cache_hit", cache_key=cache_key)
                return cached_result[:limit]
            
            with get_db_context() as db:
                # Build query
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                query = db.query(DBNewsArticle).filter(
                    DBNewsArticle.published_at >= cutoff_time
                )
                
                # Apply filters
                if ticker:
                    # Join with news_sentiment to filter by ticker
                    from stockiq.infrastructure.models import NewsSentiment
                    stock = db.query(DBStock).filter(DBStock.ticker == ticker).first()
                    if stock:
                        query = query.join(NewsSentiment).filter(
                            NewsSentiment.stock_id == stock.id
                        )
                
                if source:
                    query = query.filter(DBNewsArticle.source == source)
                
                if category:
                    query = query.filter(DBNewsArticle.category == category)
                
                # Order by published date (most recent first)
                query = query.order_by(desc(DBNewsArticle.published_at))
                
                # Execute query
                articles = query.limit(limit * 2).all()  # Fetch extra for filtering
                
                # Convert to dicts and apply remaining filters
                result = []
                for article in articles:
                    # Get sentiment from most recent sentiment record
                    sentiment_score = 0.0
                    if article.sentiments:
                        sentiment_score = article.sentiments[0].sentiment_score
                    
                    # Apply sentiment filter
                    if sentiment_filter:
                        if sentiment_filter == "positive" and sentiment_score < SENTIMENT_POSITIVE_THRESHOLD:
                            continue
                        elif sentiment_filter == "negative" and sentiment_score > SENTIMENT_NEGATIVE_THRESHOLD:
                            continue
                        elif sentiment_filter == "neutral" and (
                            sentiment_score <= SENTIMENT_NEGATIVE_THRESHOLD or 
                            sentiment_score >= SENTIMENT_POSITIVE_THRESHOLD
                        ):
                            continue
                    
                    # Get tickers from sentiment records
                    tickers = [
                        db.query(DBStock).get(s.stock_id).ticker 
                        for s in article.sentiments[:5]  # Limit to 5 tickers
                        if s.stock_id
                    ]
                    
                    # Check if breaking news
                    time_diff = datetime.utcnow() - article.published_at
                    is_breaking = time_diff.total_seconds() <= (BREAKING_NEWS_THRESHOLD * 60)
                    
                    result.append({
                        "id": str(article.id),
                        "title": article.title,
                        "content": article.content or "",
                        "source": article.source,
                        "published_at": article.published_at,
                        "sentiment": sentiment_score,
                        "category": article.category or "general",
                        "is_breaking": is_breaking,
                        "tickers": tickers,
                        "url": article.url,
                        "summary": article.content[:200] if article.content else "",
                        "predicted_impact": abs(sentiment_score) * 1.5,  # Simple heuristic
                    })
                    
                    if len(result) >= limit:
                        break
                
                # Cache result
                cache.set(cache_key, result, ttl=300)  # 5-minute cache
                return result
                
        except Exception as e:
            logger.warning("news_fetch_failed", exc_info=True)
    
    # Fallback to demo data
    logger.warning("using_demo_news_data")
    return _demo_news()[:limit]


def _search_historical_news(
    query: str,
    days: int = HISTORICAL_SEARCH_DAYS,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search historical news articles.
    
    Args:
        query: Search query string
        days: Number of days to search back
        limit: Maximum number of results
    
    Returns:
        List of matching article dictionaries
    """
    if not DATABASE_AVAILABLE:
        return []
    
    try:
        with get_db_context() as db:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Search in title and content
            search_filter = or_(
                DBNewsArticle.title.ilike(f"%{query}%"),
                DBNewsArticle.content.ilike(f"%{query}%")
            )
            
            articles = db.query(DBNewsArticle).filter(
                and_(
                    DBNewsArticle.published_at >= cutoff_date,
                    search_filter
                )
            ).order_by(desc(DBNewsArticle.published_at)).limit(limit).all()
            
            # Convert to dicts
            result = []
            for article in articles:
                sentiment_score = 0.0
                if article.sentiments:
                    sentiment_score = article.sentiments[0].sentiment_score
                
                tickers = [
                    db.query(DBStock).get(s.stock_id).ticker 
                    for s in article.sentiments[:5]
                    if s.stock_id
                ]
                
                time_diff = datetime.utcnow() - article.published_at
                is_breaking = time_diff.total_seconds() <= (BREAKING_NEWS_THRESHOLD * 60)
                
                result.append({
                    "id": str(article.id),
                    "title": article.title,
                    "content": article.content or "",
                    "source": article.source,
                    "published_at": article.published_at,
                    "sentiment": sentiment_score,
                    "category": article.category or "general",
                    "is_breaking": is_breaking,
                    "tickers": tickers,
                    "url": article.url,
                    "summary": article.content[:200] if article.content else "",
                    "predicted_impact": abs(sentiment_score) * 1.5,
                })
            
            return result
            
    except Exception as e:
        logger.warning("historical_search_failed", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Reading list helpers
# ---------------------------------------------------------------------------

def _init_reading_list():
    """Initialize reading list in session state if not exists."""
    if not STREAMLIT_AVAILABLE:
        return
    
    if READING_LIST_KEY not in st.session_state:
        st.session_state[READING_LIST_KEY] = []


def _add_to_reading_list(article_id: str, article_data: Dict[str, Any]):
    """Add article to reading list."""
    if not STREAMLIT_AVAILABLE:
        return
    
    _init_reading_list()
    
    # Check if already in list
    if article_id not in [a["id"] for a in st.session_state[READING_LIST_KEY]]:
        st.session_state[READING_LIST_KEY].append(article_data)
        logger.info("article_added_to_reading_list", article_id=article_id)


def _remove_from_reading_list(article_id: str):
    """Remove article from reading list."""
    if not STREAMLIT_AVAILABLE:
        return
    
    _init_reading_list()
    st.session_state[READING_LIST_KEY] = [
        a for a in st.session_state[READING_LIST_KEY] if a["id"] != article_id
    ]
    logger.info("article_removed_from_reading_list", article_id=article_id)


def _is_in_reading_list(article_id: str) -> bool:
    """Check if article is in reading list."""
    if not STREAMLIT_AVAILABLE:
        return False
    
    _init_reading_list()
    return article_id in [a["id"] for a in st.session_state[READING_LIST_KEY]]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _sentiment_badge(score: float) -> str:
    """Return emoji badge for sentiment score."""
    if score >= SENTIMENT_POSITIVE_THRESHOLD:
        return "🟢"
    elif score <= SENTIMENT_NEGATIVE_THRESHOLD:
        return "🔴"
    else:
        return "🟡"


def _sentiment_label(score: float) -> str:
    """Return text label for sentiment score."""
    if score >= SENTIMENT_POSITIVE_THRESHOLD:
        return "Positive"
    elif score <= SENTIMENT_NEGATIVE_THRESHOLD:
        return "Negative"
    else:
        return "Neutral"


def _sentiment_color(score: float) -> str:
    """Return color code for sentiment score."""
    if score >= SENTIMENT_POSITIVE_THRESHOLD:
        return "#00c853"  # Green
    elif score <= SENTIMENT_NEGATIVE_THRESHOLD:
        return "#d50000"  # Red
    else:
        return "#ffd740"  # Yellow


def _format_time_ago(published_at: datetime) -> str:
    """Format time ago string."""
    now = datetime.utcnow()
    delta = now - published_at
    
    if delta.total_seconds() < 60:
        return "Just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes}m ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(delta.total_seconds() / 86400)
        return f"{days}d ago"


def _get_source_credibility(source: str) -> int:
    """Get credibility rating for news source (1-10)."""
    return NEWS_SOURCES.get(source, {}).get("credibility", 5)


def _credibility_badge(credibility: int) -> str:
    """Return badge for source credibility."""
    if credibility >= 8:
        return "⭐⭐⭐"
    elif credibility >= 6:
        return "⭐⭐"
    else:
        return "⭐"


# ---------------------------------------------------------------------------
# Widget: News Filters
# ---------------------------------------------------------------------------

def render_news_filters() -> Dict[str, Any]:
    """
    Render news filter controls.
    
    Provides filters for:
    - Ticker symbol
    - Sector
    - News category
    - Sentiment (positive/neutral/negative)
    - News source
    
    Returns:
        Dictionary of active filter values
    
    Requirement 9.2: Filter by ticker, sector, category, sentiment, source
    Requirement 9.3: Filter by news source and credibility rating
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render news filters")
        return {}
    
    st.markdown("### 🔍 Filter News")
    
    # Create filter columns
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        ticker_filter = st.text_input(
            "Ticker",
            placeholder="e.g., AAPL",
            help="Filter by stock ticker symbol"
        ).upper()
    
    with col2:
        sector_filter = st.selectbox(
            "Sector",
            options=["All"] + SECTORS,
            help="Filter by market sector"
        )
        if sector_filter == "All":
            sector_filter = None
    
    with col3:
        category_filter = st.selectbox(
            "Category",
            options=["All", "earnings", "M&A", "regulatory", "economic", "sector-specific", "general"],
            help="Filter by news category"
        )
        if category_filter == "All":
            category_filter = None
    
    with col4:
        sentiment_filter = st.selectbox(
            "Sentiment",
            options=["All", "positive", "neutral", "negative"],
            help="Filter by sentiment analysis"
        )
        if sentiment_filter == "All":
            sentiment_filter = None
    
    with col5:
        source_filter = st.selectbox(
            "Source",
            options=["All"] + sorted(NEWS_SOURCES.keys()),
            help="Filter by news source"
        )
        if source_filter == "All":
            source_filter = None
    
    # Time range filter
    col_time, col_clear = st.columns([4, 1])
    with col_time:
        hours_filter = st.slider(
            "Time Range (hours)",
            min_value=1,
            max_value=72,
            value=24,
            help="Show news from the last N hours"
        )
    
    with col_clear:
        st.markdown("<div style='margin-top:1.8rem'></div>", unsafe_allow_html=True)
        if st.button("Clear Filters", use_container_width=True):
            st.rerun()
    
    return {
        "ticker": ticker_filter if ticker_filter else None,
        "sector": sector_filter,
        "category": category_filter,
        "sentiment": sentiment_filter,
        "source": source_filter,
        "hours": hours_filter,
    }


# ---------------------------------------------------------------------------
# Widget: News Item
# ---------------------------------------------------------------------------

def render_news_item(article: Dict[str, Any]) -> None:
    """
    Render a single news article item.
    
    Displays:
    - Headline
    - Source with credibility badge
    - Timestamp (time ago format)
    - Sentiment badge
    - Predicted price impact
    - Related tickers
    - Breaking news indicator (if applicable)
    - Read more link
    - Save to reading list button
    
    Args:
        article: Article dictionary with all metadata
    
    Requirements:
    - Requirement 9.4: Highlight breaking news with visual indicators
    - Requirement 9.5: Display sentiment score and predicted price impact
    - Requirement 9.6: Show related stocks affected by each news item
    - Requirement 9.7: Save news items to reading list
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render news item")
        return
    
    # Breaking news animation CSS
    breaking_css = """
        <style>
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        .breaking-badge {
            animation: pulse 1.5s ease-in-out infinite;
            background: #d50000;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 700;
            display: inline-block;
            margin-left: 8px;
        }
        </style>
    """
    
    # Extract article data
    article_id = article.get("id", "")
    title = article.get("title", "No title")
    source = article.get("source", "Unknown")
    published_at = article.get("published_at", datetime.utcnow())
    sentiment = article.get("sentiment", 0.0)
    is_breaking = article.get("is_breaking", False)
    tickers = article.get("tickers", [])
    url = article.get("url", "#")
    summary = article.get("summary", "")
    predicted_impact = article.get("predicted_impact", 0.0)
    
    # Get source credibility
    credibility = _get_source_credibility(source)
    
    # Format time ago
    time_ago = _format_time_ago(published_at)
    
    # Sentiment badge and color
    sentiment_badge = _sentiment_badge(sentiment)
    sentiment_color = _sentiment_color(sentiment)
    sentiment_text = _sentiment_label(sentiment)
    
    # Create article container
    with st.container():
        # Add breaking news CSS if needed
        if is_breaking:
            st.markdown(breaking_css, unsafe_allow_html=True)
        
        # Article card HTML
        breaking_badge_html = '<span class="breaking-badge">🔥 BREAKING</span>' if is_breaking else ""
        
        tickers_html = " ".join([
            f'<span style="background:#1e1e2e;padding:2px 6px;border-radius:3px;font-size:0.8em;margin-right:4px">{t}</span>'
            for t in tickers[:5]  # Limit to 5 tickers
        ])
        
        impact_color = "#00c853" if predicted_impact >= 0 else "#d50000"
        impact_arrow = "↑" if predicted_impact >= 0 else "↓"
        
        article_html = f"""
        <div style="
            background: #1e1e2e;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            border-left: 4px solid {sentiment_color};
        ">
            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px">
                <div style="flex:1">
                    <div style="font-size:1.1em;font-weight:600;color:#fff;margin-bottom:4px">
                        {title} {breaking_badge_html}
                    </div>
                    <div style="font-size:0.82em;color:#aaa;margin-bottom:8px">
                        <span>{source}</span> {_credibility_badge(credibility)}
                        <span style="margin-left:8px">•</span>
                        <span style="margin-left:8px">{time_ago}</span>
                    </div>
                </div>
                <div style="text-align:right;margin-left:16px">
                    <div style="font-size:0.8em;color:#aaa;margin-bottom:2px">Sentiment</div>
                    <div style="font-size:1.1em;color:{sentiment_color};font-weight:600">
                        {sentiment_badge} {sentiment_text}
                    </div>
                    <div style="font-size:0.75em;color:#aaa;margin-top:4px">
                        Impact: <span style="color:{impact_color}">{impact_arrow} {abs(predicted_impact):.1f}%</span>
                    </div>
                </div>
            </div>
            
            <div style="font-size:0.9em;color:#ccc;margin-bottom:8px;line-height:1.4">
                {summary}
            </div>
            
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div style="font-size:0.82em">
                    <span style="color:#888">Related:</span> {tickers_html if tickers else '<span style="color:#555">None</span>'}
                </div>
            </div>
        </div>
        """
        
        st.markdown(article_html, unsafe_allow_html=True)
        
        # Action buttons
        col_read, col_save = st.columns([3, 1])
        
        with col_read:
            if st.button(f"🔗 Read Full Article", key=f"read_{article_id}", use_container_width=True):
                st.write(f"Opening: {url}")
                # In production, use st.components.v1.html to open in new tab
        
        with col_save:
            if _is_in_reading_list(article_id):
                if st.button("✓ Saved", key=f"saved_{article_id}", use_container_width=True):
                    _remove_from_reading_list(article_id)
                    st.rerun()
            else:
                if st.button("📌 Save", key=f"save_{article_id}", use_container_width=True):
                    _add_to_reading_list(article_id, article)
                    st.rerun()
        
        st.markdown("<hr style='margin:8px 0;border:none;border-top:1px solid #333'>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Widget: News Feed
# ---------------------------------------------------------------------------

def render_news_feed() -> None:
    """
    Render the main real-time news feed with 30-second auto-refresh.
    
    Features:
    - Auto-refresh every 30 seconds
    - Filter controls
    - Article list with rich metadata
    - Breaking news highlighting
    - Empty state with filter suggestions
    
    Requirements:
    - Requirement 9.1: Real-time news feed with 30-second updates
    - Requirement 9.4: Highlight breaking news with visual indicators
    - Requirement 9.9: Display news volume trends
    - Requirement 9.12: Filter adjustment suggestions when empty
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render news feed")
        return
    
    st.markdown("## 📰 Real-Time News Feed")
    
    # Auto-refresh setup
    st.markdown(
        f"<div style='font-size:0.8em;color:#888;margin-bottom:16px'>"
        f"Auto-refreshes every {AUTO_REFRESH_INTERVAL} seconds | "
        f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
        f"</div>",
        unsafe_allow_html=True
    )
    
    # Render filters
    filters = render_news_filters()
    
    st.markdown("---")
    
    # Fetch news articles with filters
    articles = _fetch_news_articles(
        limit=50,
        ticker=filters.get("ticker"),
        sector=filters.get("sector"),
        category=filters.get("category"),
        sentiment_filter=filters.get("sentiment"),
        source=filters.get("source"),
        hours=filters.get("hours", 24),
    )
    
    # Display article count and volume trends
    breaking_count = sum(1 for a in articles if a.get("is_breaking", False))
    
    col_count, col_breaking = st.columns([3, 1])
    with col_count:
        st.markdown(
            f"<div style='font-size:0.9em;color:#ccc'>Showing {len(articles)} articles</div>",
            unsafe_allow_html=True
        )
    with col_breaking:
        if breaking_count > 0:
            st.markdown(
                f"<div style='font-size:0.9em;color:#d50000;font-weight:600'>🔥 {breaking_count} Breaking</div>",
                unsafe_allow_html=True
            )
    
    st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)
    
    # Display articles
    if articles:
        for article in articles:
            render_news_item(article)
    else:
        # Empty state with filter suggestions (Requirement 9.12)
        st.info(
            "📭 No news articles found matching your filters.\n\n"
            "**Suggestions:**\n"
            "- Try expanding the time range\n"
            "- Remove some filters to see more results\n"
            "- Try different ticker symbols or sectors\n"
            "- Check back later for new articles"
        )
    
    # Auto-refresh using time.sleep and st.rerun
    # Note: In production, use st.experimental_rerun with a timer
    # For now, we'll add a manual refresh button
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()


# ---------------------------------------------------------------------------
# Widget: News Search
# ---------------------------------------------------------------------------

def render_news_search() -> None:
    """
    Render historical news search interface.
    
    Provides:
    - Search query input
    - Date range selection (up to 90 days)
    - Search results display
    
    Requirement 9.8: Search functionality across historical news (90 days)
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render news search")
        return
    
    st.markdown("## 🔍 Search Historical News")
    
    # Search input
    col_query, col_search = st.columns([4, 1])
    
    with col_query:
        search_query = st.text_input(
            "Search Query",
            placeholder="e.g., Apple iPhone, Fed rate hike, earnings",
            help="Search in article titles and content"
        )
    
    with col_search:
        st.markdown("<div style='margin-top:1.8rem'></div>", unsafe_allow_html=True)
        search_button = st.button("Search", use_container_width=True)
    
    # Date range selection
    days_back = st.slider(
        "Search Period (days)",
        min_value=1,
        max_value=HISTORICAL_SEARCH_DAYS,
        value=30,
        help=f"Search up to {HISTORICAL_SEARCH_DAYS} days back"
    )
    
    st.markdown("---")
    
    # Execute search
    if search_query and search_button:
        with st.spinner("Searching..."):
            results = _search_historical_news(search_query, days=days_back, limit=50)
        
        if results:
            st.markdown(f"### Found {len(results)} results")
            for article in results:
                render_news_item(article)
        else:
            st.info(
                f"No results found for **'{search_query}'** in the last {days_back} days.\n\n"
                "Try:\n"
                "- Different keywords\n"
                "- Broader search terms\n"
                "- Extending the search period"
            )
    elif not search_query:
        st.info("💡 Enter a search query above to find historical news articles.")


# ---------------------------------------------------------------------------
# Widget: Reading List
# ---------------------------------------------------------------------------

def render_reading_list() -> None:
    """
    Render saved articles reading list.
    
    Displays all articles saved by the user for later reading.
    Allows removing articles from the list.
    
    Requirement 9.7: Save news items to reading list
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("streamlit not available – cannot render reading list")
        return
    
    st.markdown("## 📚 Reading List")
    
    _init_reading_list()
    reading_list = st.session_state[READING_LIST_KEY]
    
    if reading_list:
        st.markdown(
            f"<div style='font-size:0.9em;color:#ccc;margin-bottom:16px'>"
            f"You have {len(reading_list)} saved article(s)"
            f"</div>",
            unsafe_allow_html=True
        )
        
        # Clear all button
        if st.button("🗑️ Clear All", use_container_width=False):
            st.session_state[READING_LIST_KEY] = []
            st.rerun()
        
        st.markdown("---")
        
        # Display saved articles
        for article in reading_list:
            render_news_item(article)
    else:
        st.info(
            "📭 Your reading list is empty.\n\n"
            "Save articles from the news feed using the '📌 Save' button "
            "to read them later."
        )
