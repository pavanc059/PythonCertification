"""
Redis cache management for high-performance data access.

This module implements Requirements 22.1-22.4:
- Redis 7.0+ with connection pooling (Req 22.1)
- Sub-second latency caching (Req 22.2)
- Automatic TTL management (Req 22.3)
- Pub/sub support for real-time updates (Req 22.4)
"""

import json
import pickle
from typing import Any, Optional, List, Dict, Callable
from datetime import timedelta
import redis
from redis.connection import ConnectionPool
from redis.sentinel import Sentinel
import structlog

from .config import get_settings

logger = structlog.get_logger(__name__)

# Global Redis client and connection pool
_redis_client = None
_connection_pool = None
_sentinel_client = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with connection pooling.
    
    Supports two modes:
    1. Direct connection (development)
    2. Sentinel connection (production HA)
    
    Returns:
        Redis client instance with connection pooling
    """
    global _redis_client, _connection_pool, _sentinel_client
    
    if _redis_client is None:
        settings = get_settings()
        
        # Check if Sentinel mode is enabled
        if settings.redis_sentinel_hosts:
            logger.info("initializing_redis_sentinel_client")
            _redis_client = _create_sentinel_client(settings)
        else:
            logger.info("initializing_redis_direct_client")
            _redis_client = _create_direct_client(settings)
        
        # Test connection
        try:
            _redis_client.ping()
            info = _redis_client.info('server')
            logger.info(
                "redis_connection_established",
                redis_version=info.get('redis_version', 'unknown'),
                mode='sentinel' if settings.redis_sentinel_hosts else 'direct',
                max_connections=settings.redis_max_connections
            )
        except redis.ConnectionError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    return _redis_client


def _create_direct_client(settings) -> redis.Redis:
    """Create Redis client with direct connection (development)."""
    global _connection_pool
    
    # Parse password from URL or use separate config
    connection_kwargs = {
        'max_connections': settings.redis_max_connections,
        'decode_responses': False,  # We handle encoding/decoding
        'socket_keepalive': settings.redis_socket_keepalive,
        'socket_connect_timeout': settings.redis_socket_connect_timeout,
        'health_check_interval': settings.redis_health_check_interval,
    }
    
    # Add password if specified
    if settings.redis_password:
        connection_kwargs['password'] = settings.redis_password
    
    # Create connection pool with enhanced settings
    _connection_pool = ConnectionPool.from_url(
        settings.redis_url,
        **connection_kwargs
    )
    
    return redis.Redis(connection_pool=_connection_pool)


def _create_sentinel_client(settings) -> redis.Redis:
    """Create Redis client with Sentinel connection (production HA)."""
    global _sentinel_client
    
    # Parse sentinel hosts (format: "host1:port1,host2:port2,host3:port3")
    sentinel_hosts = []
    for host_port in settings.redis_sentinel_hosts.split(','):
        host, port = host_port.strip().split(':')
        sentinel_hosts.append((host, int(port)))
    
    logger.info(
        "connecting_to_redis_sentinel",
        sentinel_hosts=sentinel_hosts,
        master_name=settings.redis_sentinel_master
    )
    
    # Create Sentinel instance
    sentinel_kwargs = {
        'socket_timeout': settings.redis_sentinel_socket_timeout,
        'socket_keepalive': settings.redis_socket_keepalive,
    }
    
    # Add password if specified
    if settings.redis_password:
        sentinel_kwargs['password'] = settings.redis_password
    
    _sentinel_client = Sentinel(
        sentinel_hosts,
        **sentinel_kwargs
    )
    
    # Get master connection for read/write
    master = _sentinel_client.master_for(
        settings.redis_sentinel_master,
        socket_timeout=settings.redis_socket_connect_timeout,
        password=settings.redis_password,
        decode_responses=False,
        max_connections=settings.redis_max_connections,
        health_check_interval=settings.redis_health_check_interval,
    )
    
    return master


def get_redis_slave() -> Optional[redis.Redis]:
    """
    Get Redis slave connection for read-only operations (Sentinel mode only).
    
    In Sentinel mode, this returns a connection to a replica for reads,
    reducing load on the master. Falls back to master if not in Sentinel mode.
    
    Returns:
        Redis slave client or None if not in Sentinel mode
    """
    global _sentinel_client
    
    settings = get_settings()
    
    if _sentinel_client and settings.redis_sentinel_hosts:
        return _sentinel_client.slave_for(
            settings.redis_sentinel_master,
            socket_timeout=settings.redis_socket_connect_timeout,
            password=settings.redis_password,
            decode_responses=False,
        )
    
    # Not in Sentinel mode, return None (use master for reads)
    return None


class CacheKeyPatterns:
    """Cache key patterns for different data types."""
    
    # Price data keys
    PRICE_LATEST = "price:{ticker}:latest"
    PRICE_HISTORY = "price:{ticker}:history:{timeframe}"
    PRICE_INTRADAY = "price:{ticker}:intraday:{date}"
    
    # News keys
    NEWS_LATEST = "news:latest:{limit}"
    NEWS_TICKER = "news:ticker:{ticker}:{hours}"
    NEWS_ARTICLE = "news:article:{article_id}"
    NEWS_BREAKING = "news:breaking"
    
    # Sentiment keys
    SENTIMENT_TICKER = "sentiment:{ticker}:latest"
    SENTIMENT_MARKET = "sentiment:market:latest"
    SENTIMENT_ARTICLE = "sentiment:article:{article_id}"
    
    # Prediction keys
    PREDICTION_TICKER = "prediction:{ticker}:{date}"
    PREDICTIONS_DAILY = "predictions:daily:{date}"
    PREDICTION_ACCURACY = "prediction:accuracy:{ticker}"
    
    # Top movers keys
    MOVERS_GAINERS = "movers:gainers:{date}"
    MOVERS_LOSERS = "movers:losers:{date}"
    MOVERS_UNUSUAL_VOLUME = "movers:unusual_volume:{date}"
    
    # Penny stock keys
    PENNY_MOVERS = "penny:movers:{date}"
    PENNY_MOMENTUM = "penny:momentum:{ticker}"
    PENNY_RISK = "penny:risk:{ticker}"
    PENNY_TOP = "penny:top:{date}:{limit}"
    
    # Market overview keys
    MARKET_INDICES = "market:indices:latest"
    MARKET_SECTORS = "market:sectors:{date}"
    MARKET_SENTIMENT_GAUGE = "market:sentiment:gauge"
    
    # User keys
    USER_WATCHLIST = "user:{user_id}:watchlist"
    USER_ALERTS = "user:{user_id}:alerts"
    USER_PREFERENCES = "user:{user_id}:preferences"
    
    @staticmethod
    def format_key(pattern: str, **kwargs) -> str:
        """Format a cache key pattern with values."""
        return pattern.format(**kwargs)


class CacheTTL:
    """
    Time-to-live (TTL) values for different cache key patterns.
    
    TTL values are in seconds and are aligned with Requirements 22.1-22.4:
    - Current prices: 30 seconds (Req 22.2)
    - Technical indicators: 5 minutes (Req 22.3)
    - Fundamental data: 24 hours (Req 22.4)
    - News sentiment: 15 minutes (Req 22.5)
    """
    
    # Price data TTLs
    # Real-time price data - 30 seconds for sub-minute freshness (Req 22.2)
    PRICE_LATEST = 30
    
    # Historical price data - 5 minutes (technical indicators use this) (Req 22.3)
    PRICE_HISTORY = 300
    
    # Intraday historical data - 5 minutes
    PRICE_INTRADAY = 300
    
    # News data TTLs
    # Latest news feed - 1 hour (60 minutes) for general news browsing
    NEWS_LATEST = 3600
    
    # Ticker-specific news - 1 hour (news doesn't change that frequently)
    NEWS_TICKER = 3600
    TICKER_NEWS = 3600  # Alias for NEWS_TICKER to match pattern "news:ticker:{ticker}:{hours}"
    
    # Individual news article - 24 hours (articles don't change once published)
    NEWS_ARTICLE = 86400
    
    # Breaking news feed - 5 minutes (high refresh rate for breaking news)
    NEWS_BREAKING = 300
    
    # Sentiment data TTLs
    # Ticker sentiment - 15 minutes (Req 22.5)
    SENTIMENT_TICKER = 900
    
    # Market-wide sentiment - 15 minutes
    SENTIMENT_MARKET = 900
    
    # Article sentiment - 1 hour (sentiment analysis results are stable)
    SENTIMENT_ARTICLE = 3600
    
    # Prediction data TTLs
    # Ticker-specific prediction - 24 hours (predictions are daily)
    PREDICTION_TICKER = 86400
    
    # Daily predictions list - 24 hours (generated once per day)
    PREDICTIONS_DAILY = 86400
    
    # Prediction accuracy metrics - 1 hour (updated periodically)
    PREDICTION_ACCURACY = 3600
    
    # Top movers TTLs
    # Gainers/losers lists - 5 minutes during market hours for freshness
    MOVERS_GAINERS = 300
    MOVERS_LOSERS = 300
    
    # Unusual volume - 5 minutes (high volatility requires frequent updates)
    MOVERS_UNUSUAL_VOLUME = 300
    
    # Penny stock TTLs
    # Penny stock movers - 2 minutes (high volatility requires very frequent updates)
    PENNY_MOVERS = 120
    
    # Penny stock momentum score - 2 minutes (momentum changes rapidly)
    PENNY_MOMENTUM = 120
    
    # Penny stock risk metrics - 5 minutes (risk metrics less volatile)
    PENNY_RISK = 300
    
    # Top penny stocks list - 2 minutes
    PENNY_TOP = 120
    
    # Market overview TTLs
    # Market indices - 30 seconds (real-time market overview) (Req 22.2)
    MARKET_INDICES = 30
    
    # Sector performance - 5 minutes (technical indicator level)
    MARKET_SECTORS = 300
    
    # Market sentiment gauge - 15 minutes (sentiment update rate)
    MARKET_SENTIMENT_GAUGE = 900
    
    # User data TTLs
    # User watchlist - 5 minutes (balance between freshness and performance)
    USER_WATCHLIST = 300
    
    # User alerts - 1 minute (alerts should be near real-time)
    USER_ALERTS = 60
    
    # User preferences - 1 hour (preferences change infrequently)
    USER_PREFERENCES = 3600
    
    @classmethod
    def get_ttl(cls, cache_key_pattern: str) -> int:
        """
        Get TTL for a cache key pattern.
        
        Args:
            cache_key_pattern: Cache key pattern or formatted key 
                              (e.g., "price:{ticker}:latest" or "price:AAPL:latest")
        
        Returns:
            TTL in seconds, or 300 (5 minutes) as default
        """
        # Normalize the key to match our constant naming
        # e.g., "price:AAPL:latest" or "price:{ticker}:latest" -> "PRICE_LATEST"
        parts = cache_key_pattern.split(':')
        
        if len(parts) == 0:
            logger.warning("ttl_not_found", pattern=cache_key_pattern, using_default=300)
            return 300
        
        # Build potential constant name from parts
        # Filter out placeholder parts (e.g., {ticker}, {date}) and numeric parts
        filtered_parts = [
            part.upper() for part in parts 
            if not part.startswith('{') and not part.isdigit()
        ]
        
        # Try different combinations
        constant_candidates = []
        
        if filtered_parts:
            # Try all filtered parts joined (e.g., NEWS_LATEST)
            constant_candidates.append('_'.join(filtered_parts))
            
            # Try first and last (e.g., PRICE_LATEST from price:AAPL:latest)
            if len(filtered_parts) >= 2:
                constant_candidates.append(f"{filtered_parts[0]}_{filtered_parts[-1]}")
            
            # Try just the first part
            constant_candidates.append(filtered_parts[0])
        
        # Look for matching TTL constant
        for candidate in constant_candidates:
            if hasattr(cls, candidate):
                return getattr(cls, candidate)
        
        # Default TTL: 5 minutes
        logger.warning("ttl_not_found", pattern=cache_key_pattern, using_default=300)
        return 300
    
    @classmethod
    def get_all_ttls(cls) -> Dict[str, int]:
        """
        Get all TTL values as a dictionary.
        
        Returns:
            Dictionary mapping TTL constant names to their values in seconds
        """
        ttls = {}
        for attr_name in dir(cls):
            if not attr_name.startswith('_') and attr_name.isupper():
                ttls[attr_name] = getattr(cls, attr_name)
        return ttls


class RedisCache:
    """Redis cache operations wrapper."""
    
    def __init__(self):
        self.client = get_redis_client()
        self.slave = get_redis_slave()  # For read operations in Sentinel mode
        self.settings = get_settings()
        self.pubsub = None
    
    def _get_read_client(self) -> redis.Redis:
        """Get client for read operations (uses slave if available)."""
        return self.slave if self.slave else self.client
    
    def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """
        Get value from cache.
        
        Uses read replica if available (Sentinel mode) to reduce master load.
        
        Args:
            key: Cache key
            deserialize: Whether to deserialize the value (pickle)
        
        Returns:
            Cached value or None if not found
        """
        try:
            read_client = self._get_read_client()
            value = read_client.get(key)
            
            if value is None:
                logger.debug("cache_miss", key=key)
                return None
            
            logger.debug("cache_hit", key=key)
            
            if deserialize:
                return pickle.loads(value)
            return value
            
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = no expiration)
            serialize: Whether to serialize the value (pickle)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if serialize:
                value = pickle.dumps(value)
            
            if ttl:
                self.client.setex(key, ttl, value)
            else:
                self.client.set(key, value)
            
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))
            return False
    
    def set_with_pattern_ttl(
        self,
        key: str,
        value: Any,
        pattern: Optional[str] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set value in cache using automatic TTL from CacheTTL based on key pattern.
        
        Args:
            key: Cache key (formatted, e.g., "price:AAPL:latest")
            value: Value to cache
            pattern: Optional cache key pattern (e.g., CacheKeyPatterns.PRICE_LATEST).
                    If not provided, TTL will be inferred from the key.
            serialize: Whether to serialize the value (pickle)
        
        Returns:
            True if successful, False otherwise
        
        Example:
            cache.set_with_pattern_ttl("price:AAPL:latest", price_data)
            # Uses CacheTTL.PRICE_LATEST (30 seconds)
        """
        # Get TTL from pattern or infer from key
        if pattern:
            ttl = CacheTTL.get_ttl(pattern)
        else:
            ttl = CacheTTL.get_ttl(key)
        
        return self.set(key, value, ttl=ttl, serialize=serialize)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            result = self.client.delete(key)
            logger.debug("cache_delete", key=key, deleted=result)
            return result > 0
        except Exception as e:
            logger.error("cache_delete_failed", key=key, error=str(e))
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "price:*")
        
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info("cache_pattern_delete", pattern=pattern, deleted=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.error("cache_pattern_delete_failed", pattern=pattern, error=str(e))
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error("cache_exists_failed", key=key, error=str(e))
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key."""
        try:
            return self.client.expire(key, ttl)
        except Exception as e:
            logger.error("cache_expire_failed", key=key, error=str(e))
            return False
    
    def ttl(self, key: str) -> int:
        """Get remaining TTL for a key in seconds."""
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error("cache_ttl_failed", key=key, error=str(e))
            return -1
    
    def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache."""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("cache_get_json_failed", key=key, error=str(e))
            return None
    
    def set_json(self, key: str, value: Dict, ttl: Optional[int] = None) -> bool:
        """Set JSON value in cache."""
        try:
            json_value = json.dumps(value)
            if ttl:
                self.client.setex(key, ttl, json_value)
            else:
                self.client.set(key, json_value)
            return True
        except Exception as e:
            logger.error("cache_set_json_failed", key=key, error=str(e))
            return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error("cache_increment_failed", key=key, error=str(e))
            return 0
    
    def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        try:
            return self.client.decrby(key, amount)
        except Exception as e:
            logger.error("cache_decrement_failed", key=key, error=str(e))
            return 0
    
    def get_list(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list from cache."""
        try:
            values = self.client.lrange(key, start, end)
            return [pickle.loads(v) for v in values]
        except Exception as e:
            logger.error("cache_get_list_failed", key=key, error=str(e))
            return []
    
    def push_list(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Push value to list (right push)."""
        try:
            serialized = pickle.dumps(value)
            self.client.rpush(key, serialized)
            if ttl:
                self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error("cache_push_list_failed", key=key, error=str(e))
            return False
    
    def get_set(self, key: str) -> set:
        """Get set from cache."""
        try:
            values = self.client.smembers(key)
            return {pickle.loads(v) for v in values}
        except Exception as e:
            logger.error("cache_get_set_failed", key=key, error=str(e))
            return set()
    
    def add_to_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Add value to set."""
        try:
            serialized = pickle.dumps(value)
            self.client.sadd(key, serialized)
            if ttl:
                self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error("cache_add_to_set_failed", key=key, error=str(e))
            return False
    
    def flush_all(self) -> bool:
        """Flush all keys from cache. USE WITH CAUTION!"""
        try:
            self.client.flushall()
            logger.warning("cache_flushed_all")
            return True
        except Exception as e:
            logger.error("cache_flush_failed", error=str(e))
            return False
    
    def get_info(self) -> Dict:
        """Get Redis server info."""
        try:
            return self.client.info()
        except Exception as e:
            logger.error("cache_info_failed", error=str(e))
            return {}
    
    def ping(self) -> bool:
        """Ping Redis server."""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error("cache_ping_failed", error=str(e))
            return False
    
    # ==================== PUB/SUB OPERATIONS ====================
    
    def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to a Redis pub/sub channel.
        
        Args:
            channel: Channel name (e.g., "price_updates", "news_alerts")
            message: Message to publish (will be serialized)
        
        Returns:
            Number of subscribers that received the message
        """
        try:
            serialized = pickle.dumps(message)
            subscribers = self.client.publish(channel, serialized)
            logger.debug("pubsub_publish", channel=channel, subscribers=subscribers)
            return subscribers
        except Exception as e:
            logger.error("pubsub_publish_failed", channel=channel, error=str(e))
            return 0
    
    def subscribe(self, channels: List[str], callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to Redis pub/sub channels and handle messages.
        
        This is a blocking operation that listens for messages.
        Use in a separate thread or async task.
        
        Args:
            channels: List of channel names to subscribe to
            callback: Function to call with (channel, message) when message received
        
        Example:
            def handle_price_update(channel, message):
                print(f"Price update on {channel}: {message}")
            
            cache.subscribe(["price_updates"], handle_price_update)
        """
        try:
            if not self.pubsub:
                self.pubsub = self.client.pubsub()
            
            # Subscribe to channels
            self.pubsub.subscribe(*channels)
            logger.info("pubsub_subscribed", channels=channels)
            
            # Listen for messages
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = pickle.loads(message['data'])
                    callback(channel, data)
                    
        except Exception as e:
            logger.error("pubsub_subscribe_failed", channels=channels, error=str(e))
    
    def unsubscribe(self, channels: Optional[List[str]] = None) -> None:
        """
        Unsubscribe from pub/sub channels.
        
        Args:
            channels: List of channels to unsubscribe from, or None for all
        """
        try:
            if self.pubsub:
                if channels:
                    self.pubsub.unsubscribe(*channels)
                else:
                    self.pubsub.unsubscribe()
                logger.info("pubsub_unsubscribed", channels=channels or "all")
        except Exception as e:
            logger.error("pubsub_unsubscribe_failed", error=str(e))
    
    def psubscribe(self, patterns: List[str], callback: Callable[[str, Any], None]) -> None:
        """
        Subscribe to Redis pub/sub channels using patterns.
        
        Args:
            patterns: List of channel patterns (e.g., ["price:*", "news:ticker:*"])
            callback: Function to call with (channel, message) when message received
        
        Example:
            def handle_all_prices(channel, message):
                ticker = channel.split(':')[1]
                print(f"Price update for {ticker}: {message}")
            
            cache.psubscribe(["price:*"], handle_all_prices)
        """
        try:
            if not self.pubsub:
                self.pubsub = self.client.pubsub()
            
            # Subscribe to patterns
            self.pubsub.psubscribe(*patterns)
            logger.info("pubsub_psubscribed", patterns=patterns)
            
            # Listen for messages
            for message in self.pubsub.listen():
                if message['type'] == 'pmessage':
                    channel = message['channel'].decode('utf-8')
                    data = pickle.loads(message['data'])
                    callback(channel, data)
                    
        except Exception as e:
            logger.error("pubsub_psubscribe_failed", patterns=patterns, error=str(e))
    
    def get_pubsub_channels(self, pattern: str = '*') -> List[str]:
        """
        Get list of active pub/sub channels matching pattern.
        
        Args:
            pattern: Channel pattern (default: all channels)
        
        Returns:
            List of active channel names
        """
        try:
            channels = self.client.pubsub_channels(pattern)
            return [ch.decode('utf-8') for ch in channels]
        except Exception as e:
            logger.error("pubsub_channels_failed", pattern=pattern, error=str(e))
            return []
    
    def get_pubsub_numsub(self, channels: List[str]) -> Dict[str, int]:
        """
        Get number of subscribers for each channel.
        
        Args:
            channels: List of channel names
        
        Returns:
            Dictionary mapping channel names to subscriber counts
        """
        try:
            result = self.client.pubsub_numsub(*channels)
            return {
                ch.decode('utf-8'): count 
                for ch, count in zip(channels, result[1::2])
            }
        except Exception as e:
            logger.error("pubsub_numsub_failed", channels=channels, error=str(e))
            return {}
    
    # ==================== CONNECTION POOL STATS ====================
    
    def get_pool_stats(self) -> Dict[str, int]:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary with pool metrics (created, in_use, available)
        """
        try:
            pool = self.client.connection_pool
            return {
                'max_connections': pool.max_connections,
                'created_connections': len(pool._created_connections) if hasattr(pool, '_created_connections') else 0,
                'available_connections': len(pool._available_connections) if hasattr(pool, '_available_connections') else 0,
                'in_use_connections': len(pool._in_use_connections) if hasattr(pool, '_in_use_connections') else 0,
            }
        except Exception as e:
            logger.error("pool_stats_failed", error=str(e))
            return {}


# Global cache instance
_cache = None


def get_cache() -> RedisCache:
    """Get the global cache instance."""
    global _cache
    
    if _cache is None:
        _cache = RedisCache()
    
    return _cache


def close_cache():
    """Close Redis connection and cleanup resources."""
    global _redis_client, _connection_pool, _cache, _sentinel_client
    
    if _redis_client is not None:
        logger.info("closing_redis_connection")
        
        # Close pub/sub if active
        if _cache and _cache.pubsub:
            _cache.pubsub.close()
        
        # Close main connection
        _redis_client.close()
        
        # Disconnect pool
        if _connection_pool:
            _connection_pool.disconnect()
        
        # Reset globals
        _redis_client = None
        _connection_pool = None
        _cache = None
        _sentinel_client = None
        
        logger.info("redis_connection_closed")
