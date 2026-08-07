"""
Tests for rate limiter implementation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from stockiq.infrastructure.rate_limiter import (
    RateLimiter,
    RateLimiterManager,
    get_rate_limiter,
    get_rate_limiter_manager,
)


class MockCache:
    """Mock Redis cache for testing."""
    
    def __init__(self):
        self.data = {}
        self.expiry = {}
    
    def get(self, key, deserialize=True):
        if key not in self.data:
            return None
        # Check expiry
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data[key]
    
    def set(self, key, value, ttl=None):
        self.data[key] = value
        if ttl:
            self.expiry[key] = time.time() + ttl
    
    def increment(self, key):
        current = self.get(key, deserialize=False)
        if current is None:
            self.data[key] = "1"
            return 1
        new_value = int(current) + 1
        self.data[key] = str(new_value)
        return new_value
    
    def expire(self, key, ttl):
        if key in self.data:
            self.expiry[key] = time.time() + ttl
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
        if key in self.expiry:
            del self.expiry[key]


@pytest.fixture
def mock_cache():
    """Provide mock cache."""
    return MockCache()


@pytest.fixture
def mock_settings():
    """Provide mock settings."""
    settings = Mock()
    settings.yfinance_rate_limit = 2000
    settings.newsapi_rate_limit = 100
    settings.finnhub_rate_limit = 60
    settings.alphavantage_rate_limit = 5
    return settings


@pytest.fixture
def rate_limiter(mock_cache):
    """Provide rate limiter instance."""
    with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
        limiter = RateLimiter(source='test', max_requests=100, time_window=3600)
        return limiter


class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        assert rate_limiter.source == 'test'
        assert rate_limiter.max_requests == 100
        assert rate_limiter.time_window == 3600
        assert rate_limiter.threshold == 80  # 80% of 100
    
    def test_is_allowed_initially(self, rate_limiter):
        """Test that requests are allowed initially."""
        assert rate_limiter.is_allowed() is True
    
    def test_acquire_increments_counter(self, rate_limiter, mock_cache):
        """Test that acquire increments the counter."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
            assert rate_limiter.acquire() is True
            assert mock_cache.get(rate_limiter._count_key, deserialize=False) == "1"
    
    def test_acquire_sets_expiration(self, rate_limiter, mock_cache):
        """Test that acquire sets expiration on first call."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
            rate_limiter.acquire()
            assert rate_limiter._count_key in mock_cache.expiry
    
    def test_rate_limit_threshold(self, rate_limiter, mock_cache):
        """Test that rate limit is enforced at 80% threshold."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
            # Acquire tokens up to threshold
            for i in range(80):
                assert rate_limiter.acquire() is True
            
            # Next acquire should fail (at threshold)
            assert rate_limiter.acquire() is False
    
    def test_get_remaining(self, rate_limiter, mock_cache):
        """Test getting remaining requests."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
            # Initially, should have threshold remaining
            assert rate_limiter.get_remaining() == 80
            
            # After 10 requests
            for i in range(10):
                rate_limiter.acquire()
            
            assert rate_limiter.get_remaining() == 70
    
    def test_get_reset_time(self, rate_limiter, mock_cache):
        """Test getting reset time."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
            # Initially None
            assert rate_limiter.get_reset_time() is None
            
            # After first acquire, should have reset time
            rate_limiter.acquire()
            reset_time = rate_limiter.get_reset_time()
            assert reset_time is not None
            assert reset_time > time.time()
    
    def test_reset(self, rate_limiter, mock_cache):
        """Test resetting rate limit counters."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
            # Acquire some tokens
            for i in range(10):
                rate_limiter.acquire()
            
            # Reset
            rate_limiter.reset()
            
            # Should be able to acquire again
            assert rate_limiter.get_remaining() == 80
            assert rate_limiter.acquire() is True
    
    def test_fail_open_on_error(self, rate_limiter):
        """Test that limiter fails open on cache errors."""
        with patch('stockiq.infrastructure.rate_limiter.get_cache') as mock_get_cache:
            mock_get_cache.return_value.get.side_effect = Exception("Cache error")
            
            # Should allow request even with cache error
            assert rate_limiter.is_allowed() is True
            assert rate_limiter.acquire() is True


class TestRateLimiterManager:
    """Test RateLimiterManager class."""
    
    def test_initialization(self, mock_settings, mock_cache):
        """Test manager initialization."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                assert 'yfinance' in manager._limiters
                assert 'newsapi' in manager._limiters
                assert 'finnhub' in manager._limiters
                assert 'alphavantage' in manager._limiters
    
    def test_get_limiter(self, mock_settings, mock_cache):
        """Test getting limiter by source."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                limiter = manager.get_limiter('yfinance')
                assert limiter is not None
                assert limiter.source == 'yfinance'
    
    def test_get_limiter_unknown_source(self, mock_settings, mock_cache):
        """Test getting limiter for unknown source."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                limiter = manager.get_limiter('unknown')
                assert limiter is None
    
    def test_is_allowed(self, mock_settings, mock_cache):
        """Test checking if request is allowed."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                # Initially allowed
                assert manager.is_allowed('yfinance') is True
    
    def test_acquire(self, mock_settings, mock_cache):
        """Test acquiring token."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                # Should be able to acquire
                assert manager.acquire('yfinance') is True
    
    def test_get_status(self, mock_settings, mock_cache):
        """Test getting rate limit status."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                status = manager.get_status('yfinance')
                assert status['source'] == 'yfinance'
                assert status['max_requests'] == 2000
                assert status['threshold'] == 1600  # 80% of 2000
                assert 'remaining' in status
                assert 'reset_time' in status
    
    def test_get_all_status(self, mock_settings, mock_cache):
        """Test getting status for all sources."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager = RateLimiterManager()
                
                all_status = manager.get_all_status()
                assert 'yfinance' in all_status
                assert 'newsapi' in all_status
                assert 'finnhub' in all_status
                assert 'alphavantage' in all_status


class TestGlobalFunctions:
    """Test global helper functions."""
    
    def test_get_rate_limiter_manager(self, mock_settings, mock_cache):
        """Test getting global rate limiter manager."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                manager1 = get_rate_limiter_manager()
                manager2 = get_rate_limiter_manager()
                
                # Should return same instance
                assert manager1 is manager2
    
    def test_get_rate_limiter(self, mock_settings, mock_cache):
        """Test getting rate limiter for source."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                limiter = get_rate_limiter('yfinance')
                
                assert limiter is not None
                assert limiter.source == 'yfinance'


class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""
    
    def test_80_percent_threshold_compliance(self, mock_settings, mock_cache):
        """Test that rate limiter stays at 80% of max as per Requirement 12.7."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                # Create limiter with max 100 requests
                limiter = RateLimiter(source='test', max_requests=100, time_window=3600)
                
                # Should allow 80 requests (80% of 100)
                successful_requests = 0
                for i in range(100):
                    if limiter.acquire():
                        successful_requests += 1
                
                # Should have acquired exactly 80 tokens (80% threshold)
                assert successful_requests == 80
    
    def test_distributed_rate_limiting(self, mock_settings, mock_cache):
        """Test that multiple limiter instances share state via Redis."""
        with patch('stockiq.infrastructure.rate_limiter.get_settings', return_value=mock_settings):
            with patch('stockiq.infrastructure.rate_limiter.get_cache', return_value=mock_cache):
                # Create two limiter instances for same source
                limiter1 = RateLimiter(source='shared', max_requests=100, time_window=3600)
                limiter2 = RateLimiter(source='shared', max_requests=100, time_window=3600)
                
                # Acquire 40 from limiter1
                for i in range(40):
                    limiter1.acquire()
                
                # Acquire 40 from limiter2
                for i in range(40):
                    limiter2.acquire()
                
                # Both should see the same remaining count (0)
                assert limiter1.get_remaining() == 0
                assert limiter2.get_remaining() == 0
                
                # Next acquire should fail for both
                assert limiter1.acquire() is False
                assert limiter2.acquire() is False
