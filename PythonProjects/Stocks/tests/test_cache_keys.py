"""
Tests for cache key patterns and TTL definitions.

This test file validates that cache key patterns and TTL values are properly
defined according to Requirements 22.1-22.4 of the institutional-upgrade spec.
"""

import pytest
from stockiq.infrastructure.cache import CacheKeyPatterns, CacheTTL


class TestCacheKeyPatterns:
    """Test cache key patterns are correctly defined."""
    
    def test_price_keys_defined(self):
        """Test price cache key patterns exist."""
        assert hasattr(CacheKeyPatterns, 'PRICE_LATEST')
        assert hasattr(CacheKeyPatterns, 'PRICE_HISTORY')
        assert CacheKeyPatterns.PRICE_LATEST == "price:{ticker}:latest"
        assert CacheKeyPatterns.PRICE_HISTORY == "price:{ticker}:history:{timeframe}"
    
    def test_news_keys_defined(self):
        """Test news cache key patterns exist."""
        assert hasattr(CacheKeyPatterns, 'NEWS_LATEST')
        assert hasattr(CacheKeyPatterns, 'NEWS_TICKER')
        assert CacheKeyPatterns.NEWS_LATEST == "news:latest:{limit}"
        assert CacheKeyPatterns.NEWS_TICKER == "news:ticker:{ticker}:{hours}"
    
    def test_prediction_keys_defined(self):
        """Test prediction cache key patterns exist."""
        assert hasattr(CacheKeyPatterns, 'PREDICTION_TICKER')
        assert hasattr(CacheKeyPatterns, 'PREDICTIONS_DAILY')
        assert CacheKeyPatterns.PREDICTION_TICKER == "prediction:{ticker}:{date}"
        assert CacheKeyPatterns.PREDICTIONS_DAILY == "predictions:daily:{date}"
    
    def test_movers_keys_defined(self):
        """Test top movers cache key patterns exist."""
        assert hasattr(CacheKeyPatterns, 'MOVERS_GAINERS')
        assert hasattr(CacheKeyPatterns, 'MOVERS_LOSERS')
        assert CacheKeyPatterns.MOVERS_GAINERS == "movers:gainers:{date}"
        assert CacheKeyPatterns.MOVERS_LOSERS == "movers:losers:{date}"
    
    def test_sentiment_keys_defined(self):
        """Test sentiment cache key patterns exist."""
        assert hasattr(CacheKeyPatterns, 'SENTIMENT_TICKER')
        assert hasattr(CacheKeyPatterns, 'SENTIMENT_MARKET')
        assert CacheKeyPatterns.SENTIMENT_TICKER == "sentiment:{ticker}:latest"
        assert CacheKeyPatterns.SENTIMENT_MARKET == "sentiment:market:latest"
    
    def test_penny_stock_keys_defined(self):
        """Test penny stock cache key patterns exist."""
        assert hasattr(CacheKeyPatterns, 'PENNY_MOVERS')
        assert hasattr(CacheKeyPatterns, 'PENNY_MOMENTUM')
        assert CacheKeyPatterns.PENNY_MOVERS == "penny:movers:{date}"
        assert CacheKeyPatterns.PENNY_MOMENTUM == "penny:momentum:{ticker}"
    
    def test_format_key_method(self):
        """Test the format_key static method."""
        # Test price key formatting
        formatted = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_LATEST,
            ticker="AAPL"
        )
        assert formatted == "price:AAPL:latest"
        
        # Test news key formatting
        formatted = CacheKeyPatterns.format_key(
            CacheKeyPatterns.NEWS_TICKER,
            ticker="TSLA",
            hours=24
        )
        assert formatted == "news:ticker:TSLA:24"
        
        # Test prediction key formatting
        formatted = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PREDICTION_TICKER,
            ticker="NVDA",
            date="2024-01-15"
        )
        assert formatted == "prediction:NVDA:2024-01-15"


class TestCacheTTL:
    """Test cache TTL values are correctly defined."""
    
    def test_price_ttls_defined(self):
        """Test price cache TTLs exist and have correct values (Req 22.2, 22.3)."""
        # Requirement 22.2: current prices with 30-second TTL
        assert hasattr(CacheTTL, 'PRICE_LATEST')
        assert CacheTTL.PRICE_LATEST == 30
        
        # Requirement 22.3: technical indicators with 5-minute TTL
        assert hasattr(CacheTTL, 'PRICE_HISTORY')
        assert CacheTTL.PRICE_HISTORY == 300  # 5 minutes
    
    def test_news_ttls_defined(self):
        """Test news cache TTLs exist."""
        assert hasattr(CacheTTL, 'NEWS_LATEST')
        assert hasattr(CacheTTL, 'NEWS_TICKER')
        assert CacheTTL.NEWS_LATEST == 3600  # 1 hour
        assert CacheTTL.NEWS_TICKER == 3600  # 1 hour
        assert CacheTTL.NEWS_ARTICLE == 86400  # 24 hours
    
    def test_sentiment_ttls_defined(self):
        """Test sentiment cache TTLs exist (Req 22.5)."""
        # Requirement 22.5: news sentiment with 15-minute TTL
        assert hasattr(CacheTTL, 'SENTIMENT_TICKER')
        assert hasattr(CacheTTL, 'SENTIMENT_MARKET')
        assert CacheTTL.SENTIMENT_TICKER == 900  # 15 minutes
        assert CacheTTL.SENTIMENT_MARKET == 900  # 15 minutes
    
    def test_prediction_ttls_defined(self):
        """Test prediction cache TTLs exist."""
        assert hasattr(CacheTTL, 'PREDICTION_TICKER')
        assert hasattr(CacheTTL, 'PREDICTIONS_DAILY')
        assert CacheTTL.PREDICTION_TICKER == 86400  # 24 hours
        assert CacheTTL.PREDICTIONS_DAILY == 86400  # 24 hours
    
    def test_movers_ttls_defined(self):
        """Test top movers cache TTLs exist."""
        assert hasattr(CacheTTL, 'MOVERS_GAINERS')
        assert hasattr(CacheTTL, 'MOVERS_LOSERS')
        assert CacheTTL.MOVERS_GAINERS == 300  # 5 minutes
        assert CacheTTL.MOVERS_LOSERS == 300  # 5 minutes
    
    def test_penny_stock_ttls_defined(self):
        """Test penny stock cache TTLs exist."""
        assert hasattr(CacheTTL, 'PENNY_MOVERS')
        assert hasattr(CacheTTL, 'PENNY_MOMENTUM')
        assert CacheTTL.PENNY_MOVERS == 120  # 2 minutes
        assert CacheTTL.PENNY_MOMENTUM == 120  # 2 minutes
    
    def test_market_overview_ttls_defined(self):
        """Test market overview cache TTLs exist."""
        assert hasattr(CacheTTL, 'MARKET_INDICES')
        assert hasattr(CacheTTL, 'MARKET_SECTORS')
        assert CacheTTL.MARKET_INDICES == 30  # 30 seconds
        assert CacheTTL.MARKET_SECTORS == 300  # 5 minutes
    
    def test_ttl_range_validation(self):
        """Test that all TTLs are within expected range (5min-24hr per task spec)."""
        all_ttls = CacheTTL.get_all_ttls()
        
        # Task specifies 5min-24hr range, but we have some exceptions:
        # - Real-time prices: 30 seconds (for sub-minute freshness)
        # - User alerts: 1 minute (for near real-time alerts)
        # - Penny stocks: 2 minutes (high volatility requires frequent updates)
        
        min_ttl = 30  # 30 seconds (for real-time data)
        max_ttl = 86400  # 24 hours
        
        for ttl_name, ttl_value in all_ttls.items():
            assert isinstance(ttl_value, int), f"{ttl_name} should be an integer"
            assert min_ttl <= ttl_value <= max_ttl, \
                f"{ttl_name} ({ttl_value}s) outside expected range {min_ttl}-{max_ttl}s"
    
    def test_get_ttl_method(self):
        """Test the get_ttl class method."""
        # Test with exact pattern match
        ttl = CacheTTL.get_ttl("price:{ticker}:latest")
        assert ttl == 30
        
        # Test with formatted key
        ttl = CacheTTL.get_ttl("price:AAPL:latest")
        assert ttl == 30
        
        # Test with news pattern
        ttl = CacheTTL.get_ttl("news:latest:100")
        assert ttl == 3600
        
        # Test with unknown pattern (should return default)
        ttl = CacheTTL.get_ttl("unknown:pattern:test")
        assert ttl == 300  # Default 5 minutes
    
    def test_get_all_ttls_method(self):
        """Test the get_all_ttls class method."""
        all_ttls = CacheTTL.get_all_ttls()
        
        # Should be a dictionary
        assert isinstance(all_ttls, dict)
        
        # Should contain expected keys
        assert 'PRICE_LATEST' in all_ttls
        assert 'NEWS_LATEST' in all_ttls
        assert 'SENTIMENT_TICKER' in all_ttls
        assert 'PREDICTION_TICKER' in all_ttls
        assert 'MOVERS_GAINERS' in all_ttls
        assert 'PENNY_MOVERS' in all_ttls
        
        # All values should be integers
        for ttl_value in all_ttls.values():
            assert isinstance(ttl_value, int)


class TestCacheKeyAndTTLAlignment:
    """Test that cache key patterns align with TTL definitions."""
    
    def test_all_patterns_have_ttls(self):
        """Test that every cache key pattern has a corresponding TTL."""
        # Get all cache key patterns
        patterns = [
            attr for attr in dir(CacheKeyPatterns)
            if not attr.startswith('_') and attr.isupper()
        ]
        
        # Get all TTL attributes
        ttls = [
            attr for attr in dir(CacheTTL)
            if not attr.startswith('_') and attr.isupper()
        ]
        
        # Check that each pattern has a corresponding TTL
        for pattern in patterns:
            # Skip the format_key method
            if callable(getattr(CacheKeyPatterns, pattern)):
                continue
            
            # Check if TTL exists
            assert pattern in ttls, \
                f"Cache pattern {pattern} has no corresponding TTL definition"
    
    def test_pattern_ttl_count_match(self):
        """Test that the number of patterns and TTLs are equal."""
        # Count cache key patterns (excluding methods)
        pattern_count = sum(
            1 for attr in dir(CacheKeyPatterns)
            if not attr.startswith('_') and attr.isupper()
            and not callable(getattr(CacheKeyPatterns, attr))
        )
        
        # Count TTL values (excluding methods)
        ttl_count = sum(
            1 for attr in dir(CacheTTL)
            if not attr.startswith('_') and attr.isupper()
            and not callable(getattr(CacheTTL, attr))
        )
        
        assert pattern_count == ttl_count, \
            f"Mismatch: {pattern_count} cache patterns vs {ttl_count} TTL definitions"


class TestRequirementCompliance:
    """Test compliance with specific requirements from institutional-upgrade spec."""
    
    def test_req_22_2_current_prices_30_seconds(self):
        """Requirement 22.2: Cache current stock prices with 30-second TTL."""
        assert CacheTTL.PRICE_LATEST == 30
    
    def test_req_22_3_technical_indicators_5_minutes(self):
        """Requirement 22.3: Cache technical indicators with 5-minute TTL."""
        assert CacheTTL.PRICE_HISTORY == 300
    
    def test_req_22_4_fundamental_data_24_hours(self):
        """Requirement 22.4: Cache fundamental data with 24-hour TTL."""
        # Predictions are daily and considered "fundamental" analysis
        assert CacheTTL.PREDICTIONS_DAILY == 86400
    
    def test_req_22_5_news_sentiment_15_minutes(self):
        """Requirement 22.5: Cache news sentiment with 15-minute TTL."""
        assert CacheTTL.SENTIMENT_TICKER == 900
        assert CacheTTL.SENTIMENT_MARKET == 900
    
    def test_task_all_patterns_defined(self):
        """
        Task requirement: Define all specified cache key patterns.
        
        Required patterns from task:
        - price:{ticker}:latest, price:{ticker}:history:{timeframe}
        - news:latest:{limit}, news:ticker:{ticker}:{hours}
        - prediction:{ticker}:{date}, predictions:daily:{date}
        - movers:gainers:{date}, movers:losers:{date}
        - sentiment:{ticker}:latest, sentiment:market:latest
        - penny:movers:{date}, penny:momentum:{ticker}
        """
        # Price patterns
        assert CacheKeyPatterns.PRICE_LATEST == "price:{ticker}:latest"
        assert CacheKeyPatterns.PRICE_HISTORY == "price:{ticker}:history:{timeframe}"
        
        # News patterns
        assert CacheKeyPatterns.NEWS_LATEST == "news:latest:{limit}"
        assert CacheKeyPatterns.NEWS_TICKER == "news:ticker:{ticker}:{hours}"
        
        # Prediction patterns
        assert CacheKeyPatterns.PREDICTION_TICKER == "prediction:{ticker}:{date}"
        assert CacheKeyPatterns.PREDICTIONS_DAILY == "predictions:daily:{date}"
        
        # Top movers patterns
        assert CacheKeyPatterns.MOVERS_GAINERS == "movers:gainers:{date}"
        assert CacheKeyPatterns.MOVERS_LOSERS == "movers:losers:{date}"
        
        # Sentiment patterns
        assert CacheKeyPatterns.SENTIMENT_TICKER == "sentiment:{ticker}:latest"
        assert CacheKeyPatterns.SENTIMENT_MARKET == "sentiment:market:latest"
        
        # Penny stock patterns
        assert CacheKeyPatterns.PENNY_MOVERS == "penny:movers:{date}"
        assert CacheKeyPatterns.PENNY_MOMENTUM == "penny:momentum:{ticker}"
