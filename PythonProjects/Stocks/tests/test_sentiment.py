"""
Unit tests for SentimentAnalyzer.

Tests cover:
- VADER sentiment analysis
- FinBERT sentiment analysis
- Combined sentiment scoring
- Confidence calculation
- Caching functionality
- Database storage
- Property 9: Sentiment score range validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from stockiq.news.nlp.sentiment import (
    SentimentAnalyzer,
    SentimentScore,
    get_sentiment_analyzer
)


class TestSentimentScore:
    """Test SentimentScore dataclass."""
    
    def test_sentiment_score_creation(self):
        """Test creating a sentiment score."""
        score = SentimentScore(
            overall=0.5,
            vader_score=0.6,
            finbert_score=0.4,
            confidence=0.8
        )
        
        assert score.overall == 0.5
        assert score.vader_score == 0.6
        assert score.finbert_score == 0.4
        assert score.confidence == 0.8
    
    def test_sentiment_score_range_clamping_positive(self):
        """Test Property 9: Scores > 1.0 are clamped to 1.0."""
        score = SentimentScore(
            overall=1.5,
            vader_score=2.0,
            finbert_score=1.2,
            confidence=1.5
        )
        
        # All scores should be clamped to valid range
        assert score.overall == 1.0
        assert score.vader_score == 1.0
        assert score.finbert_score == 1.0
        assert score.confidence == 1.0
    
    def test_sentiment_score_range_clamping_negative(self):
        """Test Property 9: Scores < -1.0 are clamped to -1.0."""
        score = SentimentScore(
            overall=-1.5,
            vader_score=-2.0,
            finbert_score=-1.2,
            confidence=-0.5
        )
        
        # Sentiment scores should be clamped to -1.0, confidence to 0.0
        assert score.overall == -1.0
        assert score.vader_score == -1.0
        assert score.finbert_score == -1.0
        assert score.confidence == 0.0
    
    def test_sentiment_score_to_dict(self):
        """Test converting sentiment score to dictionary."""
        score = SentimentScore(
            overall=0.5,
            vader_score=0.6,
            finbert_score=0.4,
            confidence=0.8
        )
        
        result = score.to_dict()
        
        assert result == {
            'overall': 0.5,
            'vader_score': 0.6,
            'finbert_score': 0.4,
            'confidence': 0.8
        }


class TestSentimentAnalyzer:
    """Test SentimentAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a sentiment analyzer instance."""
        return SentimentAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test sentiment analyzer initializes correctly."""
        assert analyzer.vader is not None
        assert analyzer.cache is not None
    
    def test_analyze_with_vader_positive(self, analyzer):
        """Test VADER analysis with positive text."""
        text = "This stock is performing excellently with great returns!"
        score = analyzer.analyze_with_vader(text)
        
        # Should be positive
        assert score > 0
        # Should be in valid range (Property 9)
        assert -1.0 <= score <= 1.0
    
    def test_analyze_with_vader_negative(self, analyzer):
        """Test VADER analysis with negative text."""
        text = "This stock is terrible and losing money badly."
        score = analyzer.analyze_with_vader(text)
        
        # Should be negative
        assert score < 0
        # Should be in valid range (Property 9)
        assert -1.0 <= score <= 1.0
    
    def test_analyze_with_vader_neutral(self, analyzer):
        """Test VADER analysis with neutral text."""
        text = "The stock price is at 100 dollars."
        score = analyzer.analyze_with_vader(text)
        
        # Should be close to neutral
        assert -0.2 <= score <= 0.2
        # Should be in valid range (Property 9)
        assert -1.0 <= score <= 1.0
    
    def test_analyze_with_vader_empty_text(self, analyzer):
        """Test VADER analysis with empty text."""
        score = analyzer.analyze_with_vader("")
        assert score == 0.0
        
        score = analyzer.analyze_with_vader("   ")
        assert score == 0.0
    
    def test_analyze_with_finbert_positive(self, analyzer):
        """Test FinBERT analysis with positive financial text."""
        if analyzer.finbert_model is None:
            pytest.skip("FinBERT model not available")
        
        text = "The company reported strong earnings growth and increased revenue."
        score = analyzer.analyze_with_finbert(text)
        
        # Should be positive
        assert score > 0
        # Should be in valid range (Property 9)
        assert -1.0 <= score <= 1.0
    
    def test_analyze_with_finbert_negative(self, analyzer):
        """Test FinBERT analysis with negative financial text."""
        if analyzer.finbert_model is None:
            pytest.skip("FinBERT model not available")
        
        text = "The company faces bankruptcy and massive losses."
        score = analyzer.analyze_with_finbert(text)
        
        # Should be negative
        assert score < 0
        # Should be in valid range (Property 9)
        assert -1.0 <= score <= 1.0
    
    def test_analyze_with_finbert_empty_text(self, analyzer):
        """Test FinBERT analysis with empty text."""
        score = analyzer.analyze_with_finbert("")
        assert score == 0.0
        
        score = analyzer.analyze_with_finbert("   ")
        assert score == 0.0
    
    def test_calculate_confidence_high_agreement(self, analyzer):
        """Test confidence calculation with high model agreement."""
        # Both models agree (both positive, similar magnitude)
        confidence = analyzer._calculate_confidence(0.8, 0.7)
        
        # Should have high confidence (>0.7)
        assert confidence > 0.7
        assert 0.0 <= confidence <= 1.0
    
    def test_calculate_confidence_low_agreement(self, analyzer):
        """Test confidence calculation with low model agreement."""
        # Models disagree (one positive, one negative)
        confidence = analyzer._calculate_confidence(0.8, -0.6)
        
        # Should have low confidence (<0.5)
        assert confidence < 0.5
        assert 0.0 <= confidence <= 1.0
    
    def test_calculate_confidence_one_model_only(self, analyzer):
        """Test confidence calculation with only one model available."""
        # Only VADER available (FinBERT = 0)
        confidence = analyzer._calculate_confidence(0.8, 0.0)
        
        # Should have medium confidence (0.5)
        assert confidence == 0.5
    
    def test_calculate_confidence_no_models(self, analyzer):
        """Test confidence calculation with no models available."""
        confidence = analyzer._calculate_confidence(0.0, 0.0)
        
        # Should have no confidence
        assert confidence == 0.0
    
    def test_analyze_sentiment_positive(self, analyzer):
        """Test combined sentiment analysis with positive text."""
        text = "Apple reports record-breaking quarterly earnings with strong iPhone sales!"
        
        sentiment = analyzer.analyze_sentiment(text)
        
        # Should return SentimentScore
        assert isinstance(sentiment, SentimentScore)
        
        # Overall score should be positive
        assert sentiment.overall > 0
        
        # All scores should be in valid range (Property 9)
        assert -1.0 <= sentiment.overall <= 1.0
        assert -1.0 <= sentiment.vader_score <= 1.0
        assert -1.0 <= sentiment.finbert_score <= 1.0
        assert 0.0 <= sentiment.confidence <= 1.0
    
    def test_analyze_sentiment_negative(self, analyzer):
        """Test combined sentiment analysis with negative text."""
        text = "Company announces massive layoffs and bankruptcy fears."
        
        sentiment = analyzer.analyze_sentiment(text)
        
        # Overall score should be negative
        assert sentiment.overall < 0
        
        # All scores should be in valid range (Property 9)
        assert -1.0 <= sentiment.overall <= 1.0
        assert -1.0 <= sentiment.vader_score <= 1.0
        assert -1.0 <= sentiment.finbert_score <= 1.0
        assert 0.0 <= sentiment.confidence <= 1.0
    
    def test_analyze_sentiment_caching(self, analyzer):
        """Test sentiment analysis uses caching."""
        text = "This is a test article for caching."
        
        # First call should compute
        sentiment1 = analyzer.analyze_sentiment(text)
        
        # Second call should use cache (mock to verify)
        with patch.object(analyzer, 'analyze_with_vader') as mock_vader:
            sentiment2 = analyzer.analyze_sentiment(text)
            
            # VADER should not be called (result from cache)
            mock_vader.assert_not_called()
        
        # Results should be identical
        assert sentiment1.overall == sentiment2.overall
        assert sentiment1.vader_score == sentiment2.vader_score
    
    @patch('stockiq.news.nlp.sentiment.get_db_context')
    def test_store_sentiment(self, mock_db_context, analyzer):
        """Test storing sentiment in database."""
        # Mock database session
        mock_db = MagicMock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        sentiment = SentimentScore(
            overall=0.5,
            vader_score=0.6,
            finbert_score=0.4,
            confidence=0.8
        )
        
        result = analyzer.store_sentiment(
            article_db_id=1,
            stock_db_id=2,
            sentiment=sentiment,
            entities={'companies': ['Apple']}
        )
        
        # Should succeed
        assert result is True
        
        # Should have added record to database
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('stockiq.news.nlp.sentiment.get_db_context')
    def test_store_sentiment_error(self, mock_db_context, analyzer):
        """Test storing sentiment handles errors gracefully."""
        # Mock database session to raise error
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Database error")
        mock_db_context.return_value.__enter__.return_value = mock_db
        
        sentiment = SentimentScore(
            overall=0.5,
            vader_score=0.6,
            finbert_score=0.4,
            confidence=0.8
        )
        
        result = analyzer.store_sentiment(
            article_db_id=1,
            stock_db_id=2,
            sentiment=sentiment
        )
        
        # Should return False on error
        assert result is False
    
    def test_analyze_article_with_caching(self, analyzer):
        """Test analyzing article uses caching."""
        article_id = "test-article-123"
        text = "Apple announces new product launch."
        
        # First call should compute and cache
        sentiment1 = analyzer.analyze_article(article_id, text, use_cache=True)
        
        # Second call should use cache
        with patch.object(analyzer, 'analyze_sentiment') as mock_analyze:
            sentiment2 = analyzer.analyze_article(article_id, text, use_cache=True)
            
            # analyze_sentiment should not be called
            mock_analyze.assert_not_called()
    
    def test_analyze_article_without_caching(self, analyzer):
        """Test analyzing article without caching."""
        article_id = "test-article-456"
        text = "Tesla reports delivery numbers."
        
        # Both calls should compute
        sentiment1 = analyzer.analyze_article(article_id, text, use_cache=False)
        sentiment2 = analyzer.analyze_article(article_id, text, use_cache=False)
        
        # Results should still be similar
        assert abs(sentiment1.overall - sentiment2.overall) < 0.1


class TestGetSentimentAnalyzer:
    """Test the global sentiment analyzer instance."""
    
    def test_get_sentiment_analyzer(self):
        """Test getting the global sentiment analyzer."""
        analyzer1 = get_sentiment_analyzer()
        analyzer2 = get_sentiment_analyzer()
        
        # Should return the same instance
        assert analyzer1 is analyzer2
    
    def test_get_sentiment_analyzer_type(self):
        """Test the global analyzer is correct type."""
        analyzer = get_sentiment_analyzer()
        assert isinstance(analyzer, SentimentAnalyzer)


class TestPropertyValidation:
    """Test Property 9: Sentiment score range validation."""
    
    def test_property_9_vader_range(self):
        """Test Property 9: VADER scores are in range [-1.0, 1.0]."""
        analyzer = SentimentAnalyzer()
        
        test_texts = [
            "Excellent performance!",
            "Terrible results.",
            "Neutral statement.",
            "Amazing growth and profits!",
            "Bankruptcy and losses.",
        ]
        
        for text in test_texts:
            score = analyzer.analyze_with_vader(text)
            assert -1.0 <= score <= 1.0, f"VADER score {score} out of range for: {text}"
    
    def test_property_9_finbert_range(self):
        """Test Property 9: FinBERT scores are in range [-1.0, 1.0]."""
        analyzer = SentimentAnalyzer()
        
        if analyzer.finbert_model is None:
            pytest.skip("FinBERT model not available")
        
        test_texts = [
            "Strong quarterly earnings exceed expectations.",
            "Company faces severe financial difficulties.",
            "Price remains stable at current levels.",
            "Revenue growth accelerates significantly.",
            "Major losses reported in recent quarter.",
        ]
        
        for text in test_texts:
            score = analyzer.analyze_with_finbert(text)
            assert -1.0 <= score <= 1.0, f"FinBERT score {score} out of range for: {text}"
    
    def test_property_9_overall_score_range(self):
        """Test Property 9: Overall scores are in range [-1.0, 1.0]."""
        analyzer = SentimentAnalyzer()
        
        test_texts = [
            "Exceptional performance with record profits!",
            "Devastating losses and declining market share.",
            "Standard operating procedures continue.",
            "Innovative products drive strong demand.",
            "Regulatory challenges and compliance issues.",
        ]
        
        for text in test_texts:
            sentiment = analyzer.analyze_sentiment(text)
            assert -1.0 <= sentiment.overall <= 1.0, f"Overall score {sentiment.overall} out of range for: {text}"
            assert -1.0 <= sentiment.vader_score <= 1.0
            assert -1.0 <= sentiment.finbert_score <= 1.0
            assert 0.0 <= sentiment.confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
