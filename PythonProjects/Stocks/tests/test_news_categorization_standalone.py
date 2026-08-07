"""
Standalone tests for news categorization (no Redis/DB required).

Tests the core categorization logic without external dependencies.
"""

import re
from datetime import datetime, timedelta
from stockiq.data.models import NewsArticle, NewsCategory


def test_category_keyword_matching():
    """Test that category keywords are correctly defined."""
    from stockiq.news.nlp.categorization import CATEGORY_KEYWORDS
    
    # Verify all categories have keywords defined
    assert NewsCategory.EARNINGS in CATEGORY_KEYWORDS
    assert NewsCategory.MA in CATEGORY_KEYWORDS
    assert NewsCategory.REGULATORY in CATEGORY_KEYWORDS
    assert NewsCategory.ECONOMIC in CATEGORY_KEYWORDS
    assert NewsCategory.SECTOR_SPECIFIC in CATEGORY_KEYWORDS
    
    # Verify keywords are sets
    for category, keywords in CATEGORY_KEYWORDS.items():
        assert isinstance(keywords, set)
        assert len(keywords) > 0
    
    # Verify some key earnings keywords
    earnings_keywords = CATEGORY_KEYWORDS[NewsCategory.EARNINGS]
    assert 'earnings' in earnings_keywords
    assert 'revenue' in earnings_keywords
    assert 'eps' in earnings_keywords
    
    print("✓ Category keywords are properly defined")


def test_ticker_regex_patterns():
    """Test ticker extraction regex patterns."""
    from stockiq.news.nlp.categorization import TICKER_PATTERNS
    
    # Test $TICKER format
    pattern_dollar = re.compile(TICKER_PATTERNS[0], re.IGNORECASE)
    assert pattern_dollar.search("Apple ($AAPL) rose today")
    assert pattern_dollar.search("Buy $TSLA now")
    
    # Test exchange format
    pattern_exchange = re.compile(TICKER_PATTERNS[1], re.IGNORECASE)
    assert pattern_exchange.search("Tesla (NASDAQ:TSLA) announced")
    assert pattern_exchange.search("Microsoft (NYSE:MSFT) reports")
    
    # Test contextual format
    pattern_contextual = re.compile(TICKER_PATTERNS[2], re.IGNORECASE)
    assert pattern_contextual.search("AAPL stock")
    assert pattern_contextual.search("TSLA shares")
    
    print("✓ Ticker regex patterns work correctly")


def test_categorization_result_dataclass():
    """Test CategorizationResult dataclass."""
    from stockiq.news.nlp.categorization import CategorizationResult
    
    result = CategorizationResult(
        category=NewsCategory.EARNINGS,
        confidence=0.85,
        matched_keywords=['earnings', 'revenue', 'profit']
    )
    
    assert result.category == NewsCategory.EARNINGS
    assert result.confidence == 0.85
    assert len(result.matched_keywords) == 3
    
    print("✓ CategorizationResult dataclass works")


def test_relevance_score_dataclass():
    """Test RelevanceScore dataclass."""
    from stockiq.news.nlp.categorization import RelevanceScore
    
    score = RelevanceScore(
        score=0.75,
        factors={'ticker_overlap': 0.4, 'category_match': 0.3, 'recency': 0.05}
    )
    
    assert score.score == 0.75
    assert 'ticker_overlap' in score.factors
    assert score.factors['ticker_overlap'] == 0.4
    
    print("✓ RelevanceScore dataclass works")


def test_news_article_is_breaking():
    """Test NewsArticle.is_breaking() method."""
    # Recent article (5 minutes ago) - should be breaking
    recent_article = NewsArticle(
        id="test_1",
        title="Breaking News",
        content="Content",
        source="Reuters",
        published_at=datetime.utcnow() - timedelta(minutes=5),
        url="http://example.com/1",
        tickers=[]
    )
    assert recent_article.is_breaking() == True
    
    # Old article (2 hours ago) - should not be breaking
    old_article = NewsArticle(
        id="test_2",
        title="Old News",
        content="Content",
        source="Reuters",
        published_at=datetime.utcnow() - timedelta(hours=2),
        url="http://example.com/2",
        tickers=[]
    )
    assert old_article.is_breaking() == False
    
    print("✓ NewsArticle.is_breaking() works correctly")


def test_news_category_enum():
    """Test NewsCategory enum values."""
    assert NewsCategory.EARNINGS.value == "earnings"
    assert NewsCategory.MA.value == "M&A"
    assert NewsCategory.REGULATORY.value == "regulatory"
    assert NewsCategory.ECONOMIC.value == "economic"
    assert NewsCategory.SECTOR_SPECIFIC.value == "sector-specific"
    assert NewsCategory.GENERAL.value == "general"
    
    print("✓ NewsCategory enum is correctly defined")


def test_keyword_matching_logic():
    """Test the keyword matching logic manually."""
    from stockiq.news.nlp.categorization import CATEGORY_KEYWORDS
    
    # Test earnings article
    earnings_text = "Apple reported quarterly earnings of $1.52 per share, beating expectations."
    earnings_keywords = CATEGORY_KEYWORDS[NewsCategory.EARNINGS]
    
    matches = []
    for keyword in earnings_keywords:
        if keyword in earnings_text.lower():
            matches.append(keyword)
    
    assert len(matches) > 0
    assert 'earnings' in matches
    
    # Test M&A article
    ma_text = "Microsoft announces acquisition of gaming company in $68 billion deal."
    ma_keywords = CATEGORY_KEYWORDS[NewsCategory.MA]
    
    matches = []
    for keyword in ma_keywords:
        if keyword in ma_text.lower():
            matches.append(keyword)
    
    assert len(matches) > 0
    assert 'acquisition' in matches or 'deal' in matches
    
    print("✓ Keyword matching logic works correctly")


if __name__ == "__main__":
    print("\nRunning standalone categorization tests (no Redis/DB required)...\n")
    
    test_category_keyword_matching()
    test_ticker_regex_patterns()
    test_categorization_result_dataclass()
    test_relevance_score_dataclass()
    test_news_article_is_breaking()
    test_news_category_enum()
    test_keyword_matching_logic()
    
    print("\n✅ All standalone tests passed!\n")
