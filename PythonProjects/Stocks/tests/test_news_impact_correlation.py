"""
Unit tests for news impact correlation analysis.

Tests for stockiq.news.impact.correlation module covering:
- Property 12: Correlation coefficients in range [-1.0, 1.0]
- Impact analysis calculations
- News beta calculations
- Cache behavior
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from stockiq.news.impact.correlation import (
    NewsImpactAnalyzer,
    PriceImpact,
    ImpactAnalysis,
    calculate_sentiment_correlation,
    calculate_news_beta,
)


class TestPriceImpact:
    """Tests for PriceImpact dataclass."""
    
    def test_price_impact_creation(self):
        """Test creating a PriceImpact object."""
        impact = PriceImpact(
            timeframe='1h',
            price_change_pct=2.5,
            volume_change_pct=150.0,
            statistical_significance=0.01
        )
        
        assert impact.timeframe == '1h'
        assert impact.price_change_pct == 2.5
        assert impact.volume_change_pct == 150.0
        assert impact.statistical_significance == 0.01
    
    def test_is_significant(self):
        """Test statistical significance check."""
        # Significant impact
        significant = PriceImpact('1h', 2.5, 150.0, 0.01)
        assert significant.is_significant(alpha=0.05) is True
        
        # Not significant impact
        not_significant = PriceImpact('1h', 0.5, 20.0, 0.10)
        assert not_significant.is_significant(alpha=0.05) is False
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        impact = PriceImpact('1d', 5.0, 200.0, 0.001)
        result = impact.to_dict()
        
        assert result['timeframe'] == '1d'
        assert result['price_change_pct'] == 5.0
        assert result['volume_change_pct'] == 200.0
        assert result['statistical_significance'] == 0.001


class TestImpactAnalysis:
    """Tests for ImpactAnalysis dataclass."""
    
    def test_impact_analysis_creation(self):
        """Test creating an ImpactAnalysis object."""
        analysis = ImpactAnalysis(
            ticker='AAPL',
            article_id='news_123'
        )
        
        assert analysis.ticker == 'AAPL'
        assert analysis.article_id == 'news_123'
        assert isinstance(analysis.timeframes, dict)
        assert len(analysis.timeframes) == 0
    
    def test_impact_analysis_with_timeframes(self):
        """Test ImpactAnalysis with timeframe data."""
        impact_1h = PriceImpact('1h', 2.5, 150.0, 0.01)
        impact_1d = PriceImpact('1d', 5.0, 200.0, 0.001)
        
        analysis = ImpactAnalysis(
            ticker='AAPL',
            article_id='news_123',
            timeframes={
                '1h': impact_1h,
                '1d': impact_1d,
            }
        )
        
        assert len(analysis.timeframes) == 2
        assert '1h' in analysis.timeframes
        assert '1d' in analysis.timeframes
        assert analysis.timeframes['1h'].price_change_pct == 2.5
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        impact = PriceImpact('1h', 2.5, 150.0, 0.01)
        analysis = ImpactAnalysis(
            ticker='AAPL',
            article_id='news_123',
            timeframes={'1h': impact}
        )
        
        result = analysis.to_dict()
        
        assert result['ticker'] == 'AAPL'
        assert result['article_id'] == 'news_123'
        assert '1h' in result['timeframes']
        assert result['timeframes']['1h']['price_change_pct'] == 2.5


class TestNewsImpactAnalyzer:
    """Tests for NewsImpactAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a NewsImpactAnalyzer instance."""
        return NewsImpactAnalyzer()
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        assert analyzer.cache is not None
        assert analyzer.TIMEFRAME_HOURS == {
            '1h': 1,
            '4h': 4,
            '1d': 24,
            '1w': 168,
        }
    
    def test_timeframe_hours_mapping(self, analyzer):
        """Test timeframe to hours conversion."""
        assert analyzer.TIMEFRAME_HOURS['1h'] == 1
        assert analyzer.TIMEFRAME_HOURS['4h'] == 4
        assert analyzer.TIMEFRAME_HOURS['1d'] == 24
        assert analyzer.TIMEFRAME_HOURS['1w'] == 168
    
    @patch('stockiq.news.impact.correlation.get_db_context')
    def test_calculate_impact_stock_not_found(self, mock_db, analyzer):
        """Test calculate_impact when stock not found."""
        # Mock database to return None for stock query
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.return_value.__enter__.return_value = mock_session
        
        result = analyzer.calculate_impact('news_123', 'INVALID', ['1h'])
        
        assert result.ticker == 'INVALID'
        assert result.article_id == 'news_123'
        assert len(result.timeframes) == 0
    
    @patch('stockiq.news.impact.correlation.get_db_context')
    def test_calculate_sentiment_correlation_property_12(self, mock_db, analyzer):
        """
        Test that correlation coefficient is in range [-1.0, 1.0].
        
        **Validates: Property 12**
        """
        # Mock database with sample data
        mock_session = MagicMock()
        
        # Mock stock
        mock_stock = Mock()
        mock_stock.id = 1
        mock_stock.ticker = 'AAPL'
        
        # Mock sentiment records
        mock_sentiments = []
        base_date = datetime.utcnow() - timedelta(days=30)
        for i in range(30):
            sentiment = Mock()
            sentiment.stock_id = 1
            sentiment.created_at = base_date + timedelta(days=i)
            sentiment.sentiment_score = 0.5 + (i % 10) * 0.05  # Varying sentiment
            mock_sentiments.append(sentiment)
        
        # Mock price records
        mock_prices = []
        for i in range(30):
            price = Mock()
            price.stock_id = 1
            price.timestamp = base_date + timedelta(days=i)
            price.close = Decimal('150.0') + Decimal(str(i * 0.5))  # Rising price
            mock_prices.append(price)
        
        # Setup query mocks
        def query_side_effect(model):
            mock_query = MagicMock()
            if 'Stock' in str(model):
                mock_query.filter.return_value.first.return_value = mock_stock
            elif 'NewsSentiment' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = mock_sentiments
            elif 'PriceData' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_prices
            return mock_query
        
        mock_session.query.side_effect = query_side_effect
        mock_db.return_value.__enter__.return_value = mock_session
        
        # Calculate correlation
        correlation = analyzer.calculate_sentiment_correlation('AAPL', period_days=30)
        
        # Property 12: Correlation must be in range [-1.0, 1.0]
        assert -1.0 <= correlation <= 1.0, f"Correlation {correlation} is not in range [-1.0, 1.0]"
    
    @patch('stockiq.news.impact.correlation.get_db_context')
    def test_calculate_sentiment_correlation_insufficient_data(self, mock_db, analyzer):
        """Test correlation calculation with insufficient data."""
        # Mock database with insufficient data
        mock_session = MagicMock()
        
        mock_stock = Mock()
        mock_stock.id = 1
        
        # Return only 1 sentiment record (need at least 2)
        mock_sentiments = [Mock()]
        
        def query_side_effect(model):
            mock_query = MagicMock()
            if 'Stock' in str(model):
                mock_query.filter.return_value.first.return_value = mock_stock
            elif 'NewsSentiment' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = mock_sentiments
            return mock_query
        
        mock_session.query.side_effect = query_side_effect
        mock_db.return_value.__enter__.return_value = mock_session
        
        correlation = analyzer.calculate_sentiment_correlation('AAPL')
        
        # Should return 0.0 when insufficient data
        assert correlation == 0.0
    
    @patch('stockiq.news.impact.correlation.get_db_context')
    def test_calculate_news_beta(self, mock_db, analyzer):
        """Test news beta calculation."""
        # Mock database with sample data
        mock_session = MagicMock()
        
        mock_stock = Mock()
        mock_stock.id = 1
        
        # Generate correlated sentiment and price data
        base_date = datetime.utcnow() - timedelta(days=30)
        mock_sentiments = []
        mock_prices = []
        
        for i in range(30):
            sentiment = Mock()
            sentiment.stock_id = 1
            sentiment.created_at = base_date + timedelta(days=i)
            sentiment.sentiment_score = 0.5 + (i % 10) * 0.05
            mock_sentiments.append(sentiment)
            
            price = Mock()
            price.stock_id = 1
            price.timestamp = base_date + timedelta(days=i)
            price.close = Decimal('150.0') + Decimal(str(i * 0.5))
            mock_prices.append(price)
        
        def query_side_effect(model):
            mock_query = MagicMock()
            if 'Stock' in str(model):
                mock_query.filter.return_value.first.return_value = mock_stock
            elif 'NewsSentiment' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = mock_sentiments
            elif 'PriceData' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_prices
            return mock_query
        
        mock_session.query.side_effect = query_side_effect
        mock_db.return_value.__enter__.return_value = mock_session
        
        beta = analyzer.calculate_news_beta('AAPL', period_days=30)
        
        # Beta should be a valid number
        assert isinstance(beta, float)
        assert not np.isnan(beta)
    
    @patch('stockiq.news.impact.correlation.get_db_context')
    def test_calculate_news_beta_insufficient_data(self, mock_db, analyzer):
        """Test news beta with insufficient data returns default."""
        mock_session = MagicMock()
        
        mock_stock = Mock()
        mock_stock.id = 1
        
        # Return too few records
        mock_sentiments = [Mock() for _ in range(5)]  # Need at least 10
        
        def query_side_effect(model):
            mock_query = MagicMock()
            if 'Stock' in str(model):
                mock_query.filter.return_value.first.return_value = mock_stock
            elif 'NewsSentiment' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = mock_sentiments
            return mock_query
        
        mock_session.query.side_effect = query_side_effect
        mock_db.return_value.__enter__.return_value = mock_session
        
        beta = analyzer.calculate_news_beta('AAPL')
        
        # Should return default value of 1.0
        assert beta == 1.0


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @patch('stockiq.news.impact.correlation.NewsImpactAnalyzer')
    def test_calculate_sentiment_correlation_function(self, mock_analyzer_class):
        """Test calculate_sentiment_correlation convenience function."""
        mock_analyzer = Mock()
        mock_analyzer.calculate_sentiment_correlation.return_value = 0.5
        mock_analyzer_class.return_value = mock_analyzer
        
        result = calculate_sentiment_correlation('AAPL', period_days=90)
        
        assert result == 0.5
        mock_analyzer.calculate_sentiment_correlation.assert_called_once_with('AAPL', 90)
    
    @patch('stockiq.news.impact.correlation.NewsImpactAnalyzer')
    def test_calculate_news_beta_function(self, mock_analyzer_class):
        """Test calculate_news_beta convenience function."""
        mock_analyzer = Mock()
        mock_analyzer.calculate_news_beta.return_value = 1.2
        mock_analyzer_class.return_value = mock_analyzer
        
        result = calculate_news_beta('TSLA', period_days=60)
        
        assert result == 1.2
        mock_analyzer.calculate_news_beta.assert_called_once_with('TSLA', 60)


class TestPropertyValidation:
    """Tests specifically for property validation."""
    
    @patch('stockiq.news.impact.correlation.get_db_context')
    def test_property_12_correlation_range_edge_cases(self, mock_db):
        """
        Test Property 12 with edge cases that could produce out-of-range values.
        
        **Validates: Property 12**
        """
        analyzer = NewsImpactAnalyzer()
        
        # Test with perfect positive correlation data
        mock_session = MagicMock()
        mock_stock = Mock()
        mock_stock.id = 1
        
        base_date = datetime.utcnow() - timedelta(days=10)
        
        # Create perfectly correlated data (should give correlation = 1.0)
        mock_sentiments = []
        mock_prices = []
        for i in range(10):
            sentiment = Mock()
            sentiment.stock_id = 1
            sentiment.created_at = base_date + timedelta(days=i)
            sentiment.sentiment_score = float(i) / 10.0  # 0.0 to 0.9
            mock_sentiments.append(sentiment)
            
            price = Mock()
            price.stock_id = 1
            price.timestamp = base_date + timedelta(days=i)
            price.close = Decimal(str(100 + i * 10))  # Perfect correlation
            mock_prices.append(price)
        
        def query_side_effect(model):
            mock_query = MagicMock()
            if 'Stock' in str(model):
                mock_query.filter.return_value.first.return_value = mock_stock
            elif 'NewsSentiment' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = mock_sentiments
            elif 'PriceData' in str(model):
                mock_query.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = mock_prices
            return mock_query
        
        mock_session.query.side_effect = query_side_effect
        mock_db.return_value.__enter__.return_value = mock_session
        
        correlation = analyzer.calculate_sentiment_correlation('AAPL', period_days=10)
        
        # Property 12: Must be in range [-1.0, 1.0]
        assert -1.0 <= correlation <= 1.0
        # Should be close to 1.0 for perfect positive correlation
        assert correlation > 0.8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
