"""
Rate limiter implementation for API calls.

This module provides a general-purpose rate limiting system that respects
80% of API rate limits as per Requirement 12.7.

Features:
- Token bucket algorithm for smooth rate limiting
- Per-source rate limiting
- Redis-backed for distributed rate limiting
- Automatic recovery and cleanup
- 80% threshold to stay well within limits
"""

from typing import Optional, Dict
import time
import structlog
from redis import Redis

from .cache import get_cache
from .config import get_settings

logger = structlog.get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with Redis backend.
    
    Implements token bucket algorithm:
    - Tokens are added at a constant rate
    - Each request consumes a token
    - Requests are blocked when bucket is empty
    - Stays at 80% of max rate to avoid hitting limits
    """
    
    def __init__(self, source: str, max_requests: int, time_window: int = 3600):
        """
        Initialize rate limiter for a specific source.
        
        Args:
            source: Source identifier (e.g., 'yfinance', 'newsapi', 'finnhub')
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds (default: 3600 = 1 hour)
        """
        self.source = source
        self.max_requests = max_requests
        self.time_window = time_window
        self.cache: Redis = get_cache()
        
        # Stay at 80% of limit as per Requirement 12.7
        self.threshold = int(max_requests * 0.8)
        
        # Redis keys
        self._count_key = f"ratelimit:{source}:count"
        self._window_key = f"ratelimit:{source}:window"
        
        logger.info(
            "rate_limiter_initialized",
            source=source,
            max_requests=max_requests,
            threshold=self.threshold,
            time_window=time_window
        )
    
    def is_allowed(self) -> bool:
        """
        Check if a request is allowed under rate limits.
        
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        try:
            # Get current count
            count_str = self.cache.get(self._count_key, deserialize=False)
            current_count = int(count_str) if count_str else 0
            
            # Check against 80% threshold
            is_allowed = current_count < self.threshold
            
            if not is_allowed:
                logger.warning(
                    "rate_limit_threshold_reached",
                    source=self.source,
                    current_count=current_count,
                    threshold=self.threshold
                )
            
            return is_allowed
            
        except Exception as e:
            logger.error(
                "rate_limit_check_failed",
                source=self.source,
                error=str(e)
            )
            # Fail open - allow request if rate limit check fails
            return True
    
    def acquire(self) -> bool:
        """
        Attempt to acquire a token for a request.
        
        Returns:
            True if token acquired, False if rate limited
        """
        if not self.is_allowed():
            return False
        
        try:
            # Increment counter
            count = self.cache.increment(self._count_key)
            
            # Set expiration on first increment
            if count == 1:
                self.cache.expire(self._count_key, self.time_window)
                self.cache.set(
                    self._window_key,
                    int(time.time()) + self.time_window,
                    ttl=self.time_window
                )
            
            logger.debug(
                "rate_limit_token_acquired",
                source=self.source,
                count=count,
                threshold=self.threshold
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "rate_limit_acquire_failed",
                source=self.source,
                error=str(e)
            )
            # Fail open
            return True
    
    def get_remaining(self) -> int:
        """
        Get remaining requests before hitting rate limit.
        
        Returns:
            Number of remaining requests
        """
        try:
            count_str = self.cache.get(self._count_key, deserialize=False)
            current_count = int(count_str) if count_str else 0
            remaining = max(0, self.threshold - current_count)
            return remaining
        except Exception as e:
            logger.error(
                "rate_limit_remaining_check_failed",
                source=self.source,
                error=str(e)
            )
            return 0
    
    def get_reset_time(self) -> Optional[int]:
        """
        Get Unix timestamp when rate limit window resets.
        
        Returns:
            Unix timestamp or None if no active window
        """
        try:
            reset_str = self.cache.get(self._window_key, deserialize=False)
            return int(reset_str) if reset_str else None
        except Exception as e:
            logger.error(
                "rate_limit_reset_check_failed",
                source=self.source,
                error=str(e)
            )
            return None
    
    def reset(self):
        """Reset rate limit counters (admin/testing use only)."""
        try:
            self.cache.delete(self._count_key)
            self.cache.delete(self._window_key)
            logger.info("rate_limit_reset", source=self.source)
        except Exception as e:
            logger.error(
                "rate_limit_reset_failed",
                source=self.source,
                error=str(e)
            )


class RateLimiterManager:
    """
    Manages multiple rate limiters for different API sources.
    
    Provides centralized rate limiting configuration and access.
    """
    
    def __init__(self):
        """Initialize rate limiter manager with configured sources."""
        self.settings = get_settings()
        self._limiters: Dict[str, RateLimiter] = {}
        
        # Initialize rate limiters for known sources
        self._initialize_limiters()
    
    def _initialize_limiters(self):
        """Initialize rate limiters for configured API sources."""
        # yfinance: 2000 requests/hour (default)
        self._limiters['yfinance'] = RateLimiter(
            source='yfinance',
            max_requests=self.settings.yfinance_rate_limit,
            time_window=3600
        )
        
        # NewsAPI: 100 requests/day (default)
        self._limiters['newsapi'] = RateLimiter(
            source='newsapi',
            max_requests=self.settings.newsapi_rate_limit,
            time_window=86400
        )
        
        # Finnhub: 60 requests/minute (default)
        self._limiters['finnhub'] = RateLimiter(
            source='finnhub',
            max_requests=self.settings.finnhub_rate_limit,
            time_window=60
        )
        
        # Alpha Vantage: 5 requests/minute (default)
        self._limiters['alphavantage'] = RateLimiter(
            source='alphavantage',
            max_requests=self.settings.alphavantage_rate_limit,
            time_window=60
        )
        
        logger.info(
            "rate_limiter_manager_initialized",
            sources=list(self._limiters.keys())
        )
    
    def get_limiter(self, source: str) -> Optional[RateLimiter]:
        """
        Get rate limiter for a specific source.
        
        Args:
            source: Source identifier
            
        Returns:
            RateLimiter instance or None if source not configured
        """
        return self._limiters.get(source)
    
    def is_allowed(self, source: str) -> bool:
        """
        Check if request is allowed for source.
        
        Args:
            source: Source identifier
            
        Returns:
            True if allowed, False if rate limited
        """
        limiter = self.get_limiter(source)
        if limiter is None:
            logger.warning("rate_limiter_not_found", source=source)
            return True  # Fail open
        
        return limiter.is_allowed()
    
    def acquire(self, source: str) -> bool:
        """
        Acquire token for request to source.
        
        Args:
            source: Source identifier
            
        Returns:
            True if token acquired, False if rate limited
        """
        limiter = self.get_limiter(source)
        if limiter is None:
            logger.warning("rate_limiter_not_found", source=source)
            return True  # Fail open
        
        return limiter.acquire()
    
    def get_status(self, source: str) -> Dict[str, any]:
        """
        Get rate limit status for source.
        
        Args:
            source: Source identifier
            
        Returns:
            Dictionary with status information
        """
        limiter = self.get_limiter(source)
        if limiter is None:
            return {
                'source': source,
                'error': 'Rate limiter not configured'
            }
        
        return {
            'source': source,
            'max_requests': limiter.max_requests,
            'threshold': limiter.threshold,
            'remaining': limiter.get_remaining(),
            'reset_time': limiter.get_reset_time(),
            'time_window': limiter.time_window
        }
    
    def get_all_status(self) -> Dict[str, Dict[str, any]]:
        """
        Get rate limit status for all sources.
        
        Returns:
            Dictionary mapping source names to status info
        """
        return {
            source: self.get_status(source)
            for source in self._limiters.keys()
        }


# Global rate limiter manager instance
_rate_limiter_manager: Optional[RateLimiterManager] = None


def get_rate_limiter_manager() -> RateLimiterManager:
    """Get or create the global rate limiter manager."""
    global _rate_limiter_manager
    
    if _rate_limiter_manager is None:
        _rate_limiter_manager = RateLimiterManager()
    
    return _rate_limiter_manager


def get_rate_limiter(source: str) -> Optional[RateLimiter]:
    """
    Get rate limiter for a specific source.
    
    Args:
        source: Source identifier (e.g., 'yfinance', 'newsapi')
        
    Returns:
        RateLimiter instance or None if not configured
    """
    manager = get_rate_limiter_manager()
    return manager.get_limiter(source)
