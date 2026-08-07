"""
Unit tests for News Feed UI component.

Tests the news feed rendering functions including filters,
article display, search, and reading list functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Test data structures
def test_demo_news_data():
    """Test that demo news data is properly structured."""
    from stockiq.ui.components.news_feed import _demo_news
    
    articles = _demo_news()
    
    # Should have at least 5 demo articles
    assert len(articles) >= 5
    
    # Each article should have required fields
    for article in articles:
        assert "id" in article
        assert "title" in article
        assert "content" in article
        assert "source" in article
        assert "published_at" in article
        assert "sentiment" in article
        assert "category" in article
        assert "is_breaking" in article
        assert "tickers" in article
        assert "url" in article
        assert "summary" in article
        assert "predicted_impact" in article


def test_sentiment_badge():
    """Test sentiment badge generation."""
    from stockiq.ui.components.news_feed import _sentiment_badge
    
    # Positive sentiment
    assert _sentiment_badge(0.5) == "🟢"
    
    # Negative sentiment
    assert _sentiment_badge(-0.5) == "🔴"
    
    # Neutral sentiment
    assert _sentiment_badge(0.0) == "🟡"
    assert _sentiment_badge(0.1) == "🟡"


def test_sentiment_label():
    """Test sentiment label generation."""
    from stockiq.ui.components.news_feed import _sentiment_label
    
    # Positive sentiment
    assert _sentiment_label(0.5) == "Positive"
    
    # Negative sentiment
    assert _sentiment_label(-0.5) == "Negative"
    
    # Neutral sentiment
    assert _sentiment_label(0.0) == "Neutral"


def test_sentiment_color():
    """Test sentiment color code generation."""
    from stockiq.ui.components.news_feed import _sentiment_color
    
    # Positive sentiment (green)
    assert _sentiment_color(0.5) == "#00c853"
    
    # Negative sentiment (red)
    assert _sentiment_color(-0.5) == "#d50000"
    
    # Neutral sentiment (yellow)
    assert _sentiment_color(0.0) == "#ffd740"


def test_format_time_ago():
    """Test time ago formatting."""
    from stockiq.ui.components.news_feed import _format_time_ago
    
    now = datetime.utcnow()
    
    # Just now
    assert _format_time_ago(now) == "Just now"
    
    # Minutes ago
    time_5m = now - timedelta(minutes=5)
    assert _format_time_ago(time_5m) == "5m ago"
    
    # Hours ago
    time_3h = now - timedelta(hours=3)
    assert _format_time_ago(time_3h) == "3h ago"
    
    # Days ago
    time_2d = now - timedelta(days=2)
    assert _format_time_ago(time_2d) == "2d ago"


def test_source_credibility():
    """Test news source credibility ratings."""
    from stockiq.ui.components.news_feed import _get_source_credibility
    
    # High credibility sources
    assert _get_source_credibility("Reuters") == 9
    assert _get_source_credibility("Bloomberg") == 9
    assert _get_source_credibility("Wall Street Journal") == 9
    
    # Medium credibility sources
    assert _get_source_credibility("CNBC") == 8
    assert _get_source_credibility("MarketWatch") == 7
    
    # Lower credibility sources
    assert _get_source_credibility("Seeking Alpha") == 6
    
    # Unknown source (default)
    assert _get_source_credibility("Unknown Source") == 5


def test_credibility_badge():
    """Test credibility badge generation."""
    from stockiq.ui.components.news_feed import _credibility_badge
    
    # High credibility (8-10)
    assert _credibility_badge(9) == "⭐⭐⭐"
    assert _credibility_badge(8) == "⭐⭐⭐"
    
    # Medium credibility (6-7)
    assert _credibility_badge(7) == "⭐⭐"
    assert _credibility_badge(6) == "⭐⭐"
    
    # Low credibility (1-5)
    assert _credibility_badge(5) == "⭐"
    assert _credibility_badge(3) == "⭐"


def test_reading_list_operations():
    """Test reading list add/remove/check operations."""
    from stockiq.ui.components.news_feed import (
        _add_to_reading_list,
        _remove_from_reading_list,
        _is_in_reading_list,
        _init_reading_list,
        READING_LIST_KEY
    )
    
    # Mock streamlit session state
    mock_session_state = {}
    
    with patch('stockiq.ui.components.news_feed.st') as mock_st:
        mock_st.session_state = mock_session_state
        
        # Initialize reading list
        _init_reading_list()
        assert READING_LIST_KEY in mock_session_state
        assert mock_session_state[READING_LIST_KEY] == []
        
        # Add article
        test_article = {
            "id": "test-1",
            "title": "Test Article",
            "content": "Test content"
        }
        _add_to_reading_list("test-1", test_article)
        assert len(mock_session_state[READING_LIST_KEY]) == 1
        assert _is_in_reading_list("test-1")
        
        # Try to add duplicate (should not add)
        _add_to_reading_list("test-1", test_article)
        assert len(mock_session_state[READING_LIST_KEY]) == 1
        
        # Remove article
        _remove_from_reading_list("test-1")
        assert len(mock_session_state[READING_LIST_KEY]) == 0
        assert not _is_in_reading_list("test-1")


def test_fetch_news_articles_fallback():
    """Test news fetching falls back to demo data when database unavailable."""
    from stockiq.ui.components.news_feed import _fetch_news_articles
    
    # Without database, should return demo data
    articles = _fetch_news_articles(limit=10)
    
    # Should have some articles (demo data)
    assert len(articles) > 0
    assert len(articles) <= 10
    
    # Articles should have required structure
    for article in articles:
        assert "id" in article
        assert "title" in article
        assert "sentiment" in article


def test_search_historical_news_no_database():
    """Test historical search returns empty when database unavailable."""
    from stockiq.ui.components.news_feed import _search_historical_news
    
    # Mock DATABASE_AVAILABLE to False
    with patch('stockiq.ui.components.news_feed.DATABASE_AVAILABLE', False):
        results = _search_historical_news("test query")
        assert results == []


def test_breaking_news_threshold():
    """Test breaking news detection based on 30-minute threshold."""
    from stockiq.ui.components.news_feed import BREAKING_NEWS_THRESHOLD
    
    # Breaking news threshold should be 30 minutes
    assert BREAKING_NEWS_THRESHOLD == 30


def test_auto_refresh_interval():
    """Test auto-refresh interval is 30 seconds as per requirements."""
    from stockiq.ui.components.news_feed import AUTO_REFRESH_INTERVAL
    
    # Auto-refresh should be 30 seconds (Requirement 9.1)
    assert AUTO_REFRESH_INTERVAL == 30


def test_historical_search_period():
    """Test historical search period is 90 days as per requirements."""
    from stockiq.ui.components.news_feed import HISTORICAL_SEARCH_DAYS
    
    # Historical search should cover 90 days (Requirement 9.8)
    assert HISTORICAL_SEARCH_DAYS == 90


def test_sentiment_thresholds():
    """Test sentiment thresholds for filtering."""
    from stockiq.ui.components.news_feed import (
        SENTIMENT_POSITIVE_THRESHOLD,
        SENTIMENT_NEGATIVE_THRESHOLD
    )
    
    # Positive threshold should be > 0
    assert SENTIMENT_POSITIVE_THRESHOLD > 0
    assert SENTIMENT_POSITIVE_THRESHOLD == 0.2
    
    # Negative threshold should be < 0
    assert SENTIMENT_NEGATIVE_THRESHOLD < 0
    assert SENTIMENT_NEGATIVE_THRESHOLD == -0.2


def test_news_sources_list():
    """Test news sources have proper metadata."""
    from stockiq.ui.components.news_feed import NEWS_SOURCES
    
    # Should have multiple sources
    assert len(NEWS_SOURCES) >= 10
    
    # Each source should have credibility and category
    for source, metadata in NEWS_SOURCES.items():
        assert "credibility" in metadata
        assert "category" in metadata
        assert 1 <= metadata["credibility"] <= 10
        assert metadata["category"] in ["wire", "tv", "print", "online", "aggregator"]


def test_sectors_list():
    """Test sectors list for filtering."""
    from stockiq.ui.components.news_feed import SECTORS
    
    # Should have all major sectors
    assert len(SECTORS) == 11
    assert "Technology" in SECTORS
    assert "Healthcare" in SECTORS
    assert "Financials" in SECTORS
    assert "Energy" in SECTORS


@patch('stockiq.ui.components.news_feed.STREAMLIT_AVAILABLE', False)
def test_render_functions_without_streamlit():
    """Test that render functions handle missing Streamlit gracefully."""
    from stockiq.ui.components.news_feed import (
        render_news_feed,
        render_news_filters,
        render_news_item,
        render_news_search,
        render_reading_list
    )
    
    # Should not crash when Streamlit unavailable
    render_news_feed()
    
    result = render_news_filters()
    assert result == {}
    
    test_article = {
        "id": "test-1",
        "title": "Test",
        "source": "Test Source",
        "published_at": datetime.utcnow(),
        "sentiment": 0.5,
        "is_breaking": False,
        "tickers": ["AAPL"],
        "url": "https://example.com",
        "summary": "Test summary",
        "predicted_impact": 1.0
    }
    render_news_item(test_article)
    
    render_news_search()
    render_reading_list()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
