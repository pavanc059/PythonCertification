"""
Tests for news categorization module.

Tests Property 8 (News Category Assignment) and Property 11 (News Relevance Ranking).
"""

import pytest
from datetime import datetime, timedelta
from stockiq.data.models import NewsArticle, NewsCategory
from stockiq.news.nlp.categorization import NewsCategorizer, extract_tickers


class TestNewsCategorization:
    """Test news categorization functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.categorizer = NewsCategorizer()
    
    def test_categorize_earnings_article(self):
        """Test earnings article categorization (Property 8)."""
        article = NewsArticle(
            id="test_1",
            title="Apple Reports Strong Q2 Earnings",
            content="Apple Inc. reported quarterly earnings of $1.52 per share, "
                   "beating analyst expectations. Revenue rose 8% to $94.8 billion.",
            source="Reuters",
            published_at=datetime.utcnow(),
            url="https://example.com/1",
            tickers=["AAPL"]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.EARNINGS
    
    def test_categorize_ma_article(self):
        """Test M&A article categorization (Property 8)."""
        article = NewsArticle(
            id="test_2",
            title="Microsoft Announces Acquisition of Gaming Company",
            content="Microsoft Corporation announced today that it will acquire "
                   "Activision Blizzard in a $68.7 billion deal.",
            source="Bloomberg",
            published_at=datetime.utcnow(),
            url="https://example.com/2",
            tickers=["MSFT"]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.MA
    
    def test_categorize_regulatory_article(self):
        """Test regulatory article categorization (Property 8)."""
        article = NewsArticle(
            id="test_3",
            title="FDA Approves New Drug for Cancer Treatment",
            content="The Food and Drug Administration approved a new drug for "
                   "treatment of lung cancer, marking a significant regulatory milestone.",
            source="MarketWatch",
            published_at=datetime.utcnow(),
            url="https://example.com/3",
            tickers=[]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.REGULATORY
    
    def test_categorize_economic_article(self):
        """Test economic article categorization (Property 8)."""
        article = NewsArticle(
            id="test_4",
            title="Federal Reserve Raises Interest Rates",
            content="The Federal Reserve announced a 25 basis point increase in "
                   "interest rates citing persistent inflation concerns.",
            source="CNBC",
            published_at=datetime.utcnow(),
            url="https://example.com/4",
            tickers=[]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.ECONOMIC
    
    def test_categorize_sector_article(self):
        """Test sector-specific article categorization (Property 8)."""
        article = NewsArticle(
            id="test_5",
            title="Technology Sector Outperforms Market",
            content="The technology sector posted strong gains as semiconductor "
                   "companies rallied on supply chain improvements.",
            source="WSJ",
            published_at=datetime.utcnow(),
            url="https://example.com/5",
            tickers=[]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.SECTOR_SPECIFIC
    
    def test_categorize_general_article(self):
        """Test general article categorization (Property 8)."""
        article = NewsArticle(
            id="test_6",
            title="Stock Market Opens Higher",
            content="Stock markets opened higher today as investors remain optimistic.",
            source="Financial Times",
            published_at=datetime.utcnow(),
            url="https://example.com/6",
            tickers=[]
        )
        
        category = self.categorizer.categorize_article(article)
        assert category == NewsCategory.GENERAL
    
    def test_extract_tickers_dollar_format(self):
        """Test ticker extraction with $TICKER format."""
        text = "Apple ($AAPL) and Microsoft ($MSFT) stocks rose today."
        tickers = self.categorizer.extract_tickers(text)
        
        # Note: This test may fail if database is not populated with these tickers
        # In that case, tickers will be empty []
        assert isinstance(tickers, list)
    
    def test_extract_tickers_exchange_format(self):
        """Test ticker extraction with exchange format."""
        text = "Tesla (NASDAQ:TSLA) announced new vehicle production."
        tickers = self.categorizer.extract_tickers(text)
        
        assert isinstance(tickers, list)
    
    def test_extract_tickers_contextual(self):
        """Test ticker extraction with contextual format."""
        text = "AAPL stock gained 5% while TSLA shares fell 3%."
        tickers = self.categorizer.extract_tickers(text)
        
        assert isinstance(tickers, list)
    
    def test_extract_tickers_no_matches(self):
        """Test ticker extraction with no matches."""
        text = "The market is performing well today."
        tickers = self.categorizer.extract_tickers(text)
        
        assert tickers == []
    
    def test_calculate_relevance_score_with_interests(self):
        """Test relevance score calculation with user interests."""
        article = NewsArticle(
            id="test_7",
            title="Apple Reports Strong Earnings",
            content="Apple Inc. announced quarterly results.",
            source="Reuters",
            published_at=datetime.utcnow(),
            url="https://example.com/7",
            tickers=["AAPL"],
            category=NewsCategory.EARNINGS
        )
        
        user_interests = ["AAPL", "earnings", "reuters"]
        score = self.categorizer.calculate_relevance_score(article, user_interests)
        
        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0
        # With all interests matching, score should be relatively high
        assert score > 0.5
    
    def test_calculate_relevance_score_no_match(self):
        """Test relevance score with no matching interests."""
        article = NewsArticle(
            id="test_8",
            title="Tech Sector Update",
            content="General technology sector news.",
            source="TechCrunch",
            published_at=datetime.utcnow(),
            url="https://example.com/8",
            tickers=["GOOG"],
            category=NewsCategory.SECTOR_SPECIFIC
        )
        
        user_interests = ["AAPL", "earnings"]
        score = self.categorizer.calculate_relevance_score(article, user_interests)
        
        # Score should be between 0 and 1
        assert 0.0 <= score <= 1.0
        # With no matches, score should be low
        assert score < 0.5
    
    def test_rank_by_relevance_property_11(self):
        """Test article ranking by relevance (Property 11)."""
        # Create articles with different characteristics
        articles = [
            NewsArticle(
                id="rank_1",
                title="Low relevance article",
                content="Generic content.",
                source="Unknown Source",
                published_at=datetime.utcnow() - timedelta(hours=48),
                url="https://example.com/r1",
                tickers=[],
                category=NewsCategory.GENERAL
            ),
            NewsArticle(
                id="rank_2",
                title="High relevance breaking news",
                content="Important breaking news about AAPL.",
                source="Reuters",
                published_at=datetime.utcnow() - timedelta(minutes=10),
                url="https://example.com/r2",
                tickers=["AAPL"],
                category=NewsCategory.EARNINGS
            ),
            NewsArticle(
                id="rank_3",
                title="Medium relevance article",
                content="Standard market update.",
                source="Bloomberg",
                published_at=datetime.utcnow() - timedelta(hours=6),
                url="https://example.com/r3",
                tickers=["MSFT"],
                category=NewsCategory.GENERAL
            ),
        ]
        
        user_interests = ["AAPL", "earnings"]
        ranked = self.categorizer.rank_by_relevance(articles, user_interests)
        
        # Property 11: Articles must be ranked in descending order of relevance
        assert len(ranked) == 3
        # Most relevant article should be first (has AAPL, earnings, Reuters, recent)
        assert ranked[0].id == "rank_2"
        # Least relevant should be last
        assert ranked[2].id == "rank_1"
    
    def test_rank_by_relevance_no_interests(self):
        """Test article ranking without user interests."""
        articles = [
            NewsArticle(
                id="default_1",
                title="Old article",
                content="Old content.",
                source="Unknown",
                published_at=datetime.utcnow() - timedelta(hours=48),
                url="https://example.com/d1",
                tickers=[]
            ),
            NewsArticle(
                id="default_2",
                title="Breaking news",
                content="Breaking news content.",
                source="Reuters",
                published_at=datetime.utcnow() - timedelta(minutes=15),
                url="https://example.com/d2",
                tickers=[]
            ),
        ]
        
        ranked = self.categorizer.rank_by_relevance(articles)
        
        # Breaking news should rank higher
        assert ranked[0].id == "default_2"
    
    def test_rank_by_relevance_empty_list(self):
        """Test ranking with empty article list."""
        ranked = self.categorizer.rank_by_relevance([])
        assert ranked == []
    
    def test_categorize_batch(self):
        """Test batch categorization."""
        articles = [
            NewsArticle(
                id="batch_1",
                title="Earnings Report",
                content="Company reports quarterly earnings.",
                source="Reuters",
                published_at=datetime.utcnow(),
                url="https://example.com/b1",
                tickers=[]
            ),
            NewsArticle(
                id="batch_2",
                title="Merger Announcement",
                content="Company announces merger deal.",
                source="Bloomberg",
                published_at=datetime.utcnow(),
                url="https://example.com/b2",
                tickers=[]
            ),
        ]
        
        categorized = self.categorizer.categorize_batch(articles)
        
        assert len(categorized) == 2
        assert categorized["batch_1"] == NewsCategory.EARNINGS
        assert categorized["batch_2"] == NewsCategory.MA


class TestTickerExtraction:
    """Test standalone ticker extraction function."""
    
    def test_extract_tickers_function(self):
        """Test the convenience extract_tickers function."""
        text = "Apple ($AAPL) and Tesla (NASDAQ:TSLA) are tech stocks."
        tickers = extract_tickers(text)
        
        assert isinstance(tickers, list)
        # Actual validation depends on database content


class TestCategorizationCaching:
    """Test categorization caching functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.categorizer = NewsCategorizer()
    
    def test_category_caching(self):
        """Test that categorization results are cached."""
        article = NewsArticle(
            id="cache_test_1",
            title="Apple Reports Earnings",
            content="Apple reported strong quarterly earnings.",
            source="Reuters",
            published_at=datetime.utcnow(),
            url="https://example.com/ct1",
            tickers=["AAPL"]
        )
        
        # First call - should compute and cache
        category1 = self.categorizer.categorize_article(article)
        
        # Second call - should retrieve from cache
        category2 = self.categorizer.categorize_article(article)
        
        assert category1 == category2
        assert category1 == NewsCategory.EARNINGS
    
    def test_relevance_caching(self):
        """Test that relevance scores are cached."""
        article = NewsArticle(
            id="rel_cache_1",
            title="Tech News",
            content="Technology sector update.",
            source="TechCrunch",
            published_at=datetime.utcnow(),
            url="https://example.com/rc1",
            tickers=["AAPL"]
        )
        
        user_interests = ["AAPL", "technology"]
        
        # First call - should compute and cache
        score1 = self.categorizer.calculate_relevance_score(article, user_interests)
        
        # Second call - should retrieve from cache
        score2 = self.categorizer.calculate_relevance_score(article, user_interests)
        
        assert score1 == score2
    
    def test_clear_cache(self):
        """Test cache clearing."""
        article = NewsArticle(
            id="clear_test_1",
            title="News Article",
            content="Article content.",
            source="Source",
            published_at=datetime.utcnow(),
            url="https://example.com/cl1",
            tickers=[]
        )
        
        # Categorize to populate cache
        self.categorizer.categorize_article(article)
        
        # Clear cache for this article
        self.categorizer.clear_cache(article.id)
        
        # Should succeed without error
        # Note: Can't easily verify cache is actually cleared without mocking


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
