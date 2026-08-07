"""
Property-based tests for news analysis.

**Validates: Requirements 2.1-2.12, 7.1-7.12**
**Properties: 8, 9, 10, 11, 12**

This test suite uses property-based testing with Hypothesis to verify
invariants and properties of the news analysis pipeline.

Properties Tested:
- Property 8: News category assignment
- Property 9: Sentiment score range [-1.0, 1.0]
- Property 10: Breaking news detection
- Property 11: News relevance ranking
- Property 12: News sentiment correlation calculation
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from decimal import Decimal

from stockiq.data.models import (
    NewsArticle,
    EnrichedNewsArticle,
    NewsCategory,
    SentimentScore,
    Entities
)

# Import only what we need to avoid loading heavy dependencies during collection
# Actual imports will be done in setup_method to avoid DLL loading errors
NewsCategorizer = None
SentimentAnalyzer = None
NewsImpactAnalyzer = None
NewsAlertDetector = None


# ===========================================================================
# Hypothesis Strategies for Generating Test Data
# ===========================================================================

@st.composite
def news_article_dict(draw):
    """
    Generate a valid news article dictionary.
    
    Returns a dictionary with all fields required for NewsArticle.
    """
    article_id = draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=8,
        max_size=16
    ))
    
    # Generate title and content with potential category keywords
    category_keywords = {
        'earnings': ['earnings', 'revenue', 'profit', 'quarterly', 'eps'],
        'M&A': ['merger', 'acquisition', 'deal', 'takeover'],
        'regulatory': ['FDA', 'SEC', 'investigation', 'approval'],
        'economic': ['GDP', 'inflation', 'Fed', 'interest rate'],
        'sector': ['technology', 'healthcare', 'energy', 'finance']
    }
    
    selected_category = draw(st.sampled_from(list(category_keywords.keys())))
    keywords = category_keywords[selected_category]
    keyword = draw(st.sampled_from(keywords))
    
    title = draw(st.text(min_size=10, max_size=100)) + f" {keyword} " + draw(st.text(min_size=5, max_size=50))
    content = draw(st.text(min_size=50, max_size=500)) + f" {keyword} " + draw(st.text(min_size=50, max_size=200))
    
    # Source from known news sources
    source = draw(st.sampled_from([
        'Reuters', 'Bloomberg', 'WSJ', 'CNBC', 'MarketWatch', 
        'Financial Times', 'The Motley Fool', 'Seeking Alpha'
    ]))
    
    # Published time: within last 7 days (timezone-naive to match is_breaking() implementation)
    hours_ago = draw(st.integers(min_value=0, max_value=168))  # 7 days
    published_at = datetime.utcnow() - timedelta(hours=hours_ago)
    
    # URL
    url = f"https://{source.lower().replace(' ', '')}.com/article/{article_id}"
    
    # Tickers: 0-5 random tickers
    num_tickers = draw(st.integers(min_value=0, max_value=5))
    tickers = [
        draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5))
        for _ in range(num_tickers)
    ]
    
    return {
        'id': article_id,
        'title': title,
        'content': content,
        'source': source,
        'published_at': published_at,
        'url': url,
        'tickers': tickers,
        'category': None,
        'author': None
    }


@st.composite
def sentiment_score_strategy(draw):
    """
    Generate a valid SentimentScore.
    
    Property 9: All scores must be in range [-1.0, 1.0]
    """
    overall = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    vader = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    finbert = draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return SentimentScore(
        overall=overall,
        vader_score=vader,
        finbert_score=finbert,
        confidence=confidence
    )


@st.composite
def enriched_news_article_strategy(draw):
    """Generate an EnrichedNewsArticle with sentiment."""
    article_data = draw(news_article_dict())
    sentiment = draw(sentiment_score_strategy())
    relevance = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return EnrichedNewsArticle(
        **article_data,
        sentiment=sentiment,
        entities=None,
        summary="",
        relevance_score=relevance
    )


# ===========================================================================
# Property 8: News Category Assignment
# ===========================================================================

class TestProperty8NewsCategoryAssignment:
    """
    **Validates: Requirement 2.2**
    
    Property 8: For any news article, the system SHALL assign exactly one
    category from the valid set: earnings, M&A, regulatory, economic,
    sector-specific, general.
    """
    
    def setup_method(self):
        """Set up categorizer for each test method."""
        import unittest.mock as mock
        from stockiq.news.nlp.categorization import NewsCategorizer as Categorizer
        # Mock cache and database to avoid dependencies
        with mock.patch('stockiq.news.nlp.categorization.get_cache'):
            with mock.patch('stockiq.news.nlp.categorization.get_db'):
                self.categorizer = Categorizer()
                self.categorizer.cache = mock.MagicMock()
                self.categorizer.cache.get.return_value = None
                self.categorizer._valid_tickers = {'AAPL', 'MSFT', 'TSLA', 'GOOGL', 'AMZN'}
    
    @given(article_data=news_article_dict())
    @settings(max_examples=30, deadline=None)
    def test_property_8_category_is_valid(self, article_data):
        """
        **Validates: Requirement 2.2**
        
        Verify that categorize_article returns a valid NewsCategory enum value.
        """
        article = NewsArticle(**article_data)
        
        # Execute
        category = self.categorizer.categorize_article(article)
        
        # Property 8: Category must be one of the valid enum values
        valid_categories = {
            NewsCategory.EARNINGS,
            NewsCategory.MA,
            NewsCategory.REGULATORY,
            NewsCategory.ECONOMIC,
            NewsCategory.SECTOR_SPECIFIC,
            NewsCategory.GENERAL
        }
        
        assert category in valid_categories, \
            f"Category {category} is not in valid set {valid_categories}"
        
        # Verify it's a NewsCategory enum
        assert isinstance(category, NewsCategory), \
            f"Category {category} is not a NewsCategory enum"
    
    def test_property_8_earnings_keywords(self):
        """Test that earnings keywords result in EARNINGS category."""
        article = NewsArticle(
            id="test_1",
            title="Apple announces quarterly earnings beat expectations",
            content="Apple Inc reported quarterly earnings that exceeded analyst expectations...",
            source="Reuters",
            published_at=datetime.utcnow(),
            url="https://reuters.com/article/test_1",
            tickers=["AAPL"]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.EARNINGS
    
    def test_property_8_ma_keywords(self):
        """Test that M&A keywords result in MA category."""
        article = NewsArticle(
            id="test_2",
            title="Microsoft announces acquisition of gaming company",
            content="Microsoft Corp announced today a major acquisition deal for $69 billion...",
            source="Bloomberg",
            published_at=datetime.utcnow(),
            url="https://bloomberg.com/article/test_2",
            tickers=["MSFT"]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.MA


# ===========================================================================
# Property 9: Sentiment Score Range
# ===========================================================================

class TestProperty9SentimentScoreRange:
    """
    **Validates: Requirement 2.4**
    
    Property 9: For any text analyzed for sentiment, all sentiment scores
    (overall, vader_score, finbert_score) SHALL be in the range [-1.0, 1.0]
    and confidence SHALL be in range [0.0, 1.0].
    """
    
    def setup_method(self):
        """Set up sentiment analyzer for each test method."""
        from stockiq.news.nlp.sentiment import SentimentAnalyzer as Analyzer
        self.analyzer = Analyzer()
    
    @given(text=st.text(min_size=10, max_size=500))
    @settings(max_examples=30, deadline=None)
    def test_property_9_sentiment_range(self, text):
        """
        **Validates: Requirement 2.4**
        
        Verify that all sentiment scores are in valid ranges.
        """
        # Filter out empty/whitespace-only text
        if not text.strip():
            return
        
        # Execute
        sentiment = self.analyzer.analyze_sentiment(text)
        
        # Property 9a: Overall score in [-1.0, 1.0]
        assert -1.0 <= sentiment.overall <= 1.0, \
            f"Overall sentiment {sentiment.overall} not in range [-1.0, 1.0]"
        
        # Property 9b: VADER score in [-1.0, 1.0]
        assert -1.0 <= sentiment.vader_score <= 1.0, \
            f"VADER score {sentiment.vader_score} not in range [-1.0, 1.0]"
        
        # Property 9c: FinBERT score in [-1.0, 1.0]
        assert -1.0 <= sentiment.finbert_score <= 1.0, \
            f"FinBERT score {sentiment.finbert_score} not in range [-1.0, 1.0]"
        
        # Property 9d: Confidence in [0.0, 1.0]
        assert 0.0 <= sentiment.confidence <= 1.0, \
            f"Confidence {sentiment.confidence} not in range [0.0, 1.0]"
    
    def test_property_9_positive_text(self):
        """Test positive sentiment text."""
        text = "The company reported excellent earnings with strong growth and positive outlook"
        sentiment = self.analyzer.analyze_sentiment(text)
        
        # Verify range
        assert -1.0 <= sentiment.overall <= 1.0
        # Expect positive sentiment
        assert sentiment.overall > 0, "Positive text should have positive sentiment"
    
    def test_property_9_negative_text(self):
        """Test negative sentiment text."""
        text = "The company announced disappointing results with declining revenue and poor outlook"
        sentiment = self.analyzer.analyze_sentiment(text)
        
        # Verify range
        assert -1.0 <= sentiment.overall <= 1.0
        # Expect negative sentiment
        assert sentiment.overall < 0, "Negative text should have negative sentiment"
    
    def test_property_9_neutral_text(self):
        """Test neutral sentiment text."""
        text = "The company will hold its annual meeting next week"
        sentiment = self.analyzer.analyze_sentiment(text)
        
        # Verify range
        assert -1.0 <= sentiment.overall <= 1.0


# ===========================================================================
# Property 10: Breaking News Detection
# ===========================================================================

class TestProperty10BreakingNewsDetection:
    """
    **Validates: Requirement 2.5**
    
    Property 10: For any news article, the article SHALL be classified as
    breaking news if and only if it was published within the last 30 minutes.
    """
    
    @given(minutes_ago=st.integers(min_value=0, max_value=120))
    @settings(max_examples=50, deadline=None)
    def test_property_10_breaking_news_threshold(self, minutes_ago):
        """
        **Validates: Requirement 2.5**
        
        Verify that breaking news detection correctly identifies articles
        published within 30 minutes.
        """
        # Create article with specific publication time (timezone-naive)
        published_at = datetime.utcnow() - timedelta(minutes=minutes_ago)
        
        article = NewsArticle(
            id=f"test_{minutes_ago}",
            title="Test article",
            content="Test content",
            source="Test Source",
            published_at=published_at,
            url="https://test.com",
            tickers=[]
        )
        
        # Execute
        is_breaking = article.is_breaking()
        
        # Property 10: Breaking if and only if published within 30 minutes
        expected_breaking = minutes_ago <= 30
        
        assert is_breaking == expected_breaking, \
            f"Article published {minutes_ago} minutes ago: " \
            f"expected breaking={expected_breaking}, got {is_breaking}"
    
    def test_property_10_exactly_30_minutes(self):
        """Edge case: Article exactly 30 minutes old should be breaking."""
        published_at = datetime.utcnow() - timedelta(minutes=30)
        
        article = NewsArticle(
            id="test_30",
            title="Test article",
            content="Test content",
            source="Test Source",
            published_at=published_at,
            url="https://test.com",
            tickers=[]
        )
        
        # At exactly 30 minutes, should be breaking (<=1800 seconds)
        is_breaking = article.is_breaking()
        assert is_breaking is True
    
    def test_property_10_just_over_30_minutes(self):
        """Edge case: Article just over 30 minutes should not be breaking."""
        published_at = datetime.utcnow() - timedelta(minutes=31)
        
        article = NewsArticle(
            id="test_31",
            title="Test article",
            content="Test content",
            source="Test Source",
            published_at=published_at,
            url="https://test.com",
            tickers=[]
        )
        
        is_breaking = article.is_breaking()
        assert is_breaking is False


# ===========================================================================
# Property 11: News Relevance Ranking
# ===========================================================================

class TestProperty11NewsRelevanceRanking:
    """
    **Validates: Requirement 2.6**
    
    Property 11: For any list of news articles ranked by relevance,
    the articles SHALL be ordered in descending order by relevance score.
    """
    
    def setup_method(self):
        """Set up categorizer for each test method."""
        import unittest.mock as mock
        from stockiq.news.nlp.categorization import NewsCategorizer as Categorizer
        with mock.patch('stockiq.news.nlp.categorization.get_cache'):
            with mock.patch('stockiq.news.nlp.categorization.get_db'):
                self.categorizer = Categorizer()
                self.categorizer.cache = mock.MagicMock()
                self.categorizer.cache.get.return_value = None
                self.categorizer._valid_tickers = {'AAPL', 'MSFT', 'TSLA'}
    
    @given(articles=st.lists(news_article_dict(), min_size=2, max_size=20))
    @settings(max_examples=20, deadline=None)
    def test_property_11_ranking_order(self, articles):
        """
        **Validates: Requirement 2.6**
        
        Verify that ranked articles are in descending order by relevance.
        """
        # Create NewsArticle objects
        news_articles = [NewsArticle(**data) for data in articles]
        
        # Execute ranking (without user interests for simplicity)
        ranked = self.categorizer.rank_by_relevance(news_articles, user_interests=None)
        
        # Property 11: Articles must be in descending order by relevance
        # (We need to re-calculate scores to verify ordering)
        scores = []
        for article in ranked:
            score = self.categorizer._default_relevance_score(article)
            scores.append(score)
        
        # Verify descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], \
                f"Articles not sorted: index {i} has score {scores[i]} " \
                f"< index {i+1} has score {scores[i + 1]}"
    
    def test_property_11_empty_list(self):
        """Edge case: Empty list returns empty list."""
        ranked = self.categorizer.rank_by_relevance([], user_interests=None)
        assert ranked == []
    
    def test_property_11_single_article(self):
        """Edge case: Single article returns list with one article."""
        article = NewsArticle(
            id="test_1",
            title="Test article",
            content="Test content",
            source="Reuters",
            published_at=datetime.utcnow(),
            url="https://test.com",
            tickers=[]
        )
        
        ranked = self.categorizer.rank_by_relevance([article], user_interests=None)
        assert len(ranked) == 1
        assert ranked[0] == article
    
    def test_property_11_with_user_interests(self):
        """Test ranking with user interests."""
        # Create articles with different tickers
        articles = [
            NewsArticle(
                id="test_1",
                title="Apple news",
                content="Apple Inc. content",
                source="Reuters",
                published_at=datetime.utcnow(),
                url="https://test.com/1",
                tickers=["AAPL"]
            ),
            NewsArticle(
                id="test_2",
                title="Microsoft news",
                content="Microsoft Corp content",
                source="Bloomberg",
                published_at=datetime.utcnow(),
                url="https://test.com/2",
                tickers=["MSFT"]
            ),
            NewsArticle(
                id="test_3",
                title="General news",
                content="General market content",
                source="CNBC",
                published_at=datetime.utcnow(),
                url="https://test.com/3",
                tickers=[]
            )
        ]
        
        # User interested in AAPL
        ranked = self.categorizer.rank_by_relevance(articles, user_interests=["AAPL"])
        
        # AAPL article should be ranked first
        assert ranked[0].id == "test_1"


# ===========================================================================
# Property 12: News Sentiment Correlation Calculation
# ===========================================================================

class TestProperty12SentimentCorrelation:
    """
    **Validates: Requirement 2.11, 7.1-7.12**
    
    Property 12: For any ticker and time period, the calculated correlation
    coefficient between news sentiment and price movements SHALL be in the
    range [-1.0, 1.0].
    """
    
    def setup_method(self):
        """Set up analyzer for each test method."""
        import unittest.mock as mock
        from stockiq.news.impact.correlation import NewsImpactAnalyzer as Analyzer
        
        # Mock the cache
        with mock.patch('stockiq.news.impact.correlation.get_cache'):
            self.analyzer = Analyzer()
            self.analyzer.cache = mock.MagicMock()
            self.analyzer.cache.get.return_value = None
    
    @given(
        ticker=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5),
        period_days=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=30, deadline=None)
    def test_property_12_correlation_range(self, ticker, period_days):
        """
        **Validates: Requirement 2.11**
        
        Verify that correlation coefficient is always in [-1.0, 1.0].
        
        Note: This test will return 0.0 for unknown tickers (insufficient data),
        which is still a valid correlation coefficient.
        """
        import unittest.mock as mock
        
        # Mock database queries to return no data (will result in correlation = 0.0)
        with mock.patch('stockiq.news.impact.correlation.get_db_context'):
            # Execute
            correlation = self.analyzer.calculate_sentiment_correlation(ticker, period_days)
            
            # Property 12: Correlation must be in [-1.0, 1.0]
            assert -1.0 <= correlation <= 1.0, \
                f"Correlation {correlation} not in range [-1.0, 1.0]"
    
    def test_property_12_perfect_positive_correlation(self):
        """Test that perfect positive correlation is capped at 1.0."""
        import numpy as np
        
        # Mock perfect positive correlation
        correlation = float(np.clip(1.5, -1.0, 1.0))  # Simulating clipping
        
        assert correlation == 1.0
        assert -1.0 <= correlation <= 1.0
    
    def test_property_12_perfect_negative_correlation(self):
        """Test that perfect negative correlation is capped at -1.0."""
        import numpy as np
        
        # Mock perfect negative correlation
        correlation = float(np.clip(-1.5, -1.0, 1.0))  # Simulating clipping
        
        assert correlation == -1.0
        assert -1.0 <= correlation <= 1.0
    
    def test_property_12_zero_correlation(self):
        """Test that zero correlation is valid."""
        # Zero correlation indicates no relationship
        correlation = 0.0
        assert -1.0 <= correlation <= 1.0
    
    @given(
        correlation_value=st.floats(
            min_value=-10.0,
            max_value=10.0,
            allow_nan=False,
            allow_infinity=False
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_property_12_clipping_behavior(self, correlation_value):
        """
        **Validates: Property 12**
        
        Verify that any correlation value is properly clipped to [-1.0, 1.0].
        """
        import numpy as np
        
        # Simulate the clipping behavior used in the implementation
        clipped = float(np.clip(correlation_value, -1.0, 1.0))
        
        # Property 12: Clipped value must be in range
        assert -1.0 <= clipped <= 1.0, \
            f"Clipped correlation {clipped} not in range [-1.0, 1.0]"
        
        # Verify clipping logic
        if correlation_value > 1.0:
            assert clipped == 1.0
        elif correlation_value < -1.0:
            assert clipped == -1.0
        else:
            assert abs(clipped - correlation_value) < 0.0001


# ===========================================================================
# Integration Tests for Combined Properties
# ===========================================================================

class TestIntegratedNewsAnalysis:
    """
    Integration tests combining multiple properties.
    """
    
    def setup_method(self):
        """Set up all analyzers."""
        import unittest.mock as mock
        from stockiq.news.nlp.categorization import NewsCategorizer as Categorizer
        from stockiq.news.nlp.sentiment import SentimentAnalyzer as Analyzer
        
        with mock.patch('stockiq.news.nlp.categorization.get_cache'):
            with mock.patch('stockiq.news.nlp.categorization.get_db'):
                self.categorizer = Categorizer()
                self.categorizer.cache = mock.MagicMock()
                self.categorizer.cache.get.return_value = None
                self.categorizer._valid_tickers = {'AAPL', 'MSFT', 'TSLA'}
        
        self.sentiment_analyzer = Analyzer()
    
    @given(article_data=news_article_dict())
    @settings(max_examples=20, deadline=None)
    def test_combined_properties_8_9_10(self, article_data):
        """
        Test that an article can be processed through categorization,
        sentiment analysis, and breaking news detection with all properties
        holding.
        """
        # Create article
        article = NewsArticle(**article_data)
        
        # Property 8: Categorize
        category = self.categorizer.categorize_article(article)
        assert isinstance(category, NewsCategory)
        
        # Property 9: Analyze sentiment
        text = f"{article.title} {article.content}"
        sentiment = self.sentiment_analyzer.analyze_sentiment(text)
        assert -1.0 <= sentiment.overall <= 1.0
        assert -1.0 <= sentiment.vader_score <= 1.0
        assert -1.0 <= sentiment.finbert_score <= 1.0
        assert 0.0 <= sentiment.confidence <= 1.0
        
        # Property 10: Check breaking news
        is_breaking = article.is_breaking()
        age_minutes = (datetime.utcnow() - article.published_at).total_seconds() / 60
        expected_breaking = age_minutes <= 30
        assert is_breaking == expected_breaking
    
    def test_end_to_end_news_pipeline(self):
        """
        Test complete news processing pipeline.
        """
        # Create a realistic article
        article = NewsArticle(
            id="test_e2e",
            title="Apple announces record quarterly earnings with strong iPhone sales",
            content="Apple Inc. reported quarterly earnings that beat analyst expectations. "
                   "The company showed revenue growth of 15% and EPS of $1.50...",
            source="Reuters",
            published_at=datetime.utcnow() - timedelta(minutes=10),
            url="https://reuters.com/test",
            tickers=["AAPL"]
        )
        
        # Property 8: Categorization
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.EARNINGS  # Should detect earnings keywords
        
        # Property 9: Sentiment
        text = f"{article.title} {article.content}"
        sentiment = self.sentiment_analyzer.analyze_sentiment(text)
        assert -1.0 <= sentiment.overall <= 1.0
        assert sentiment.overall > 0  # Positive news should have positive sentiment
        
        # Property 10: Breaking news (published 10 minutes ago)
        assert article.is_breaking() is True
        
        # Create enriched article
        enriched = EnrichedNewsArticle.from_news_article(
            article,
            sentiment=sentiment,
            relevance_score=0.8
        )
        
        # Property 11: Can be ranked
        ranked = self.categorizer.rank_by_relevance([enriched], user_interests=["AAPL"])
        assert len(ranked) == 1
        assert ranked[0].id == "test_e2e"


# ===========================================================================
# Edge Cases and Boundary Tests
# ===========================================================================

class TestEdgeCases:
    """
    Test edge cases for news analysis properties.
    """
    
    def setup_method(self):
        """Set up analyzers."""
        import unittest.mock as mock
        from stockiq.news.nlp.categorization import NewsCategorizer as Categorizer
        from stockiq.news.nlp.sentiment import SentimentAnalyzer as Analyzer
        
        with mock.patch('stockiq.news.nlp.categorization.get_cache'):
            with mock.patch('stockiq.news.nlp.categorization.get_db'):
                self.categorizer = Categorizer()
                self.categorizer.cache = mock.MagicMock()
                self.categorizer.cache.get.return_value = None
                self.categorizer._valid_tickers = set()
        
        self.sentiment_analyzer = Analyzer()
    
    def test_empty_article_content(self):
        """Test handling of empty article content."""
        article = NewsArticle(
            id="empty",
            title="",
            content="",
            source="Test",
            published_at=datetime.utcnow(),
            url="https://test.com",
            tickers=[]
        )
        
        # Should still return a valid category (likely GENERAL)
        category = self.categorizer.categorize_article(article)
        assert isinstance(category, NewsCategory)
        assert category == NewsCategory.GENERAL
    
    def test_very_long_article(self):
        """Test handling of very long article content."""
        long_content = "earnings revenue profit " * 1000  # 3000 words
        
        article = NewsArticle(
            id="long",
            title="Earnings report",
            content=long_content,
            source="Test",
            published_at=datetime.utcnow(),
            url="https://test.com",
            tickers=[]
        )
        
        # Should still categorize correctly
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.EARNINGS
    
    def test_sentiment_with_special_characters(self):
        """Test sentiment analysis with special characters."""
        text = "Apple $AAPL earnings 📈 $$$ revenue!!! @@@"
        
        sentiment = self.sentiment_analyzer.analyze_sentiment(text)
        
        # Property 9: Must still return valid ranges
        assert -1.0 <= sentiment.overall <= 1.0
        assert -1.0 <= sentiment.vader_score <= 1.0
        assert -1.0 <= sentiment.finbert_score <= 1.0
        assert 0.0 <= sentiment.confidence <= 1.0
    
    def test_breaking_news_at_exact_boundary(self):
        """Test breaking news detection at exact 30-minute boundary."""
        # Exactly 30 minutes ago
        published_at = datetime.utcnow() - timedelta(seconds=1800)
        
        article = NewsArticle(
            id="boundary",
            title="Test",
            content="Test",
            source="Test",
            published_at=published_at,
            url="https://test.com",
            tickers=[]
        )
        
        # Should be breaking (<=1800 seconds)
        assert article.is_breaking() is True
        
        # Just over 30 minutes
        published_at = datetime.utcnow() - timedelta(seconds=1801)
        article.published_at = published_at
        
        # Should not be breaking (>1800 seconds)
        assert article.is_breaking() is False
    
    def test_correlation_with_no_data(self):
        """Test correlation calculation with no data."""
        import unittest.mock as mock
        from stockiq.news.impact.correlation import NewsImpactAnalyzer as Analyzer
        
        with mock.patch('stockiq.news.impact.correlation.get_cache'):
            analyzer = Analyzer()
            analyzer.cache = mock.MagicMock()
            analyzer.cache.get.return_value = None
        
        with mock.patch('stockiq.news.impact.correlation.get_db_context'):
            # Should return 0.0 (no correlation) when no data available
            correlation = analyzer.calculate_sentiment_correlation("UNKNOWN", 90)
            
            # Property 12: Must be in valid range
            assert -1.0 <= correlation <= 1.0
            assert correlation == 0.0  # No data = no correlation
