"""
Tests for news summarization functionality.
"""

import pytest
from datetime import datetime
from stockiq.news.nlp.summarization import NewsSummarizer, KeyFacts
from stockiq.data.models import NewsArticle


class TestNewsSummarizer:
    """Test suite for NewsSummarizer class."""
    
    @pytest.fixture
    def summarizer(self):
        """Create summarizer instance."""
        return NewsSummarizer()
    
    @pytest.fixture
    def sample_article(self):
        """Create sample news article."""
        return NewsArticle(
            id="test_001",
            title="Apple Stock Rises 15% on Strong Earnings",
            content=(
                "Apple Inc. reported quarterly earnings that exceeded analyst expectations, "
                "sending shares up 15% to $125.50 in after-hours trading on January 15, 2024. "
                "The company posted revenue of $95.3 billion, representing a 12% increase year-over-year. "
                "CEO Tim Cook highlighted strong iPhone sales which grew 18% in the quarter. "
                "The services segment also performed well, generating $23.1 billion in revenue. "
                "Analysts praised the results and several raised their price targets for the stock. "
                "The company also announced a new $90 billion share buyback program. "
                "Looking ahead, management provided optimistic guidance for the next quarter."
            ),
            source="Test Source",
            published_at=datetime.utcnow(),
            url="https://example.com/test",
            tickers=["AAPL"]
        )
    
    def test_extractive_summarization_basic(self, summarizer):
        """Test basic extractive summarization."""
        text = (
            "This is the first sentence with some content here today. "
            "This is the second sentence with more detailed information about the situation. "
            "This is the third sentence with additional context for readers. "
            "This is the fourth sentence with additional information about the market. "
            "This is the fifth sentence with final thoughts and analysis."
        )
        
        summary = summarizer.summarize_extractive(text, sentences=2)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        # Summary should be shorter than or equal to original text
        assert len(summary) <= len(text)
    
    def test_extractive_summarization_article(self, summarizer, sample_article):
        """Test extractive summarization on article."""
        full_text = f"{sample_article.title}. {sample_article.content}"
        summary = summarizer.summarize_extractive(full_text, sentences=3)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < len(full_text)
        # Summary should contain at least one complete sentence
        assert '.' in summary
    
    def test_extractive_summarization_short_text(self, summarizer):
        """Test summarization with text shorter than requested sentences."""
        text = "This is a short text."
        summary = summarizer.summarize_extractive(text, sentences=5)
        
        # Should return original text or part of it
        assert isinstance(summary, str)
        assert len(summary) > 0
    
    def test_extractive_summarization_empty(self, summarizer):
        """Test summarization with empty text."""
        summary = summarizer.summarize_extractive("", sentences=3)
        
        assert summary == ""
    
    def test_extract_key_facts_prices(self, summarizer, sample_article):
        """Test extraction of price information."""
        facts = summarizer.extract_key_facts(sample_article.content)
        
        assert isinstance(facts, KeyFacts)
        assert len(facts.prices) > 0
        
        # Should extract $125.50
        price_values = [p['value'] for p in facts.prices]
        assert any(abs(v - 125.50) < 0.01 for v in price_values)
    
    def test_extract_key_facts_percentages(self, summarizer, sample_article):
        """Test extraction of percentage information."""
        facts = summarizer.extract_key_facts(sample_article.content)
        
        assert isinstance(facts, KeyFacts)
        assert len(facts.percentages) > 0
        
        # Should extract 15%, 12%, 18%
        percentage_values = [p['value'] for p in facts.percentages]
        assert 15.0 in percentage_values
    
    def test_extract_key_facts_dates(self, summarizer, sample_article):
        """Test extraction of date information."""
        facts = summarizer.extract_key_facts(sample_article.content)
        
        assert isinstance(facts, KeyFacts)
        assert len(facts.dates) > 0
        
        # Should extract "January 15, 2024"
        date_values = [d['value'] for d in facts.dates]
        assert any('January' in v and '2024' in v for v in date_values)
    
    def test_extract_key_facts_numbers(self, summarizer, sample_article):
        """Test extraction of other numerical information."""
        facts = summarizer.extract_key_facts(sample_article.content)
        
        assert isinstance(facts, KeyFacts)
        # Should extract revenue in billions
        assert len(facts.numbers) > 0 or len(facts.prices) > 0
    
    def test_extract_key_facts_empty(self, summarizer):
        """Test fact extraction with empty text."""
        facts = summarizer.extract_key_facts("")
        
        assert isinstance(facts, KeyFacts)
        assert len(facts.prices) == 0
        assert len(facts.percentages) == 0
        assert len(facts.dates) == 0
        assert len(facts.numbers) == 0
    
    def test_generate_daily_summary_multiple_articles(self, summarizer, sample_article):
        """Test daily summary generation from multiple articles."""
        articles = [sample_article]
        
        summary = summarizer.generate_daily_summary(articles)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        # Should mention key themes
        assert any(word in summary.lower() for word in ['market', 'stock', 'earnings'])
    
    def test_generate_daily_summary_empty(self, summarizer):
        """Test daily summary with no articles."""
        summary = summarizer.generate_daily_summary([])
        
        assert isinstance(summary, str)
        assert "No news available" in summary
    
    def test_summarize_article_complete(self, summarizer, sample_article):
        """Test complete article summarization."""
        result = summarizer.summarize_article(
            sample_article,
            sentences=2,
            include_facts=True
        )
        
        assert isinstance(result, dict)
        assert 'article_id' in result
        assert 'summary' in result
        assert 'facts' in result
        assert result['article_id'] == sample_article.id
        assert len(result['summary']) > 0
        assert isinstance(result['facts'], dict)
    
    def test_summarize_article_without_facts(self, summarizer, sample_article):
        """Test article summarization without facts."""
        result = summarizer.summarize_article(
            sample_article,
            sentences=3,
            include_facts=False
        )
        
        assert isinstance(result, dict)
        assert 'summary' in result
        assert 'facts' not in result
    
    def test_tokenize_sentences(self, summarizer):
        """Test sentence tokenization."""
        text = (
            "Apple Inc. reported strong quarterly earnings today. "
            "The company significantly beat analyst expectations across revenue and profit. "
            "Shares rose by double digits in after-hours trading."
        )
        
        sentences = summarizer._tokenize_sentences(text)
        
        assert isinstance(sentences, list)
        # Should handle abbreviations like "Inc."
        assert len(sentences) >= 2
    
    def test_textrank_algorithm(self, summarizer):
        """Test TextRank scoring."""
        similarity_matrix = [
            [0.0, 0.5, 0.3],
            [0.5, 0.0, 0.7],
            [0.3, 0.7, 0.0]
        ]
        
        scores = summarizer._textrank(similarity_matrix)
        
        assert isinstance(scores, list)
        assert len(scores) == 3
        assert all(s > 0 for s in scores)
        # Scores should be different (not all equal)
        assert len(set(scores)) > 1
    
    def test_sentence_similarity(self, summarizer):
        """Test sentence similarity calculation."""
        sent1 = "Apple reported strong earnings today"
        sent2 = "Apple announced great earnings results"
        sent3 = "Tesla delivered new vehicles"
        
        # Similar sentences
        sim_12 = summarizer._calculate_sentence_similarity(sent1, sent2)
        # Different sentences
        sim_13 = summarizer._calculate_sentence_similarity(sent1, sent3)
        
        assert 0.0 <= sim_12 <= 1.0
        assert 0.0 <= sim_13 <= 1.0
        # Similar sentences should have higher score
        assert sim_12 > sim_13
    
    def test_price_extraction_with_multipliers(self, summarizer):
        """Test price extraction with billion/million multipliers."""
        text = "Company raised $5 billion in funding and earned $200 million in revenue."
        
        facts = summarizer.extract_key_facts(text)
        
        price_values = [p['value'] for p in facts.prices]
        # Should convert to actual values
        assert any(v >= 1_000_000_000 for v in price_values)  # 5 billion
        assert any(v >= 100_000_000 for v in price_values)    # 200 million
    
    def test_keyfacts_to_dict_from_dict(self):
        """Test KeyFacts serialization."""
        facts = KeyFacts(
            prices=[{'value': 100.0, 'currency': 'USD', 'context': 'test'}],
            percentages=[{'value': 15.0, 'context': 'test'}],
            dates=[{'value': 'January 1, 2024', 'context': 'test'}],
            numbers=[{'value': 1000, 'unit': 'shares', 'context': 'test'}]
        )
        
        # Serialize
        data = facts.to_dict()
        assert isinstance(data, dict)
        assert 'prices' in data
        
        # Deserialize
        restored = KeyFacts.from_dict(data)
        assert len(restored.prices) == len(facts.prices)
        assert len(restored.percentages) == len(facts.percentages)
        assert len(restored.dates) == len(facts.dates)
        assert len(restored.numbers) == len(facts.numbers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
