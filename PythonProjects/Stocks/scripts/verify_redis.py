"""
Redis verification script for institutional-upgrade Phase 0.1.2.

This script verifies that Redis 7.0+ is properly configured and accessible
for caching and pub/sub functionality.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
import structlog
from stockiq.infrastructure.config import get_settings
from stockiq.infrastructure.cache import get_redis_client, get_cache, CacheKeyPatterns

logger = structlog.get_logger(__name__)


def verify_redis_connection():
    """Verify basic Redis connection."""
    print("\n=== Verifying Redis Connection ===")
    
    try:
        settings = get_settings()
        client = get_redis_client()
        
        # Test ping
        result = client.ping()
        print(f"✓ Redis PING successful: {result}")
        
        # Get Redis info
        info = client.info()
        redis_version = info.get('redis_version', 'unknown')
        print(f"✓ Redis version: {redis_version}")
        
        # Verify version is 7.0+
        major_version = int(redis_version.split('.')[0])
        if major_version >= 7:
            print(f"✓ Redis version {redis_version} meets requirement (7.0+)")
        else:
            print(f"✗ Redis version {redis_version} does not meet requirement (7.0+)")
            return False
        
        # Check memory configuration
        maxmemory = info.get('maxmemory', 0)
        maxmemory_policy = info.get('maxmemory_policy', 'unknown')
        print(f"✓ Max memory: {maxmemory / (1024*1024):.0f} MB")
        print(f"✓ Max memory policy: {maxmemory_policy}")
        
        # Check persistence
        aof_enabled = info.get('aof_enabled', 0)
        rdb_last_save_time = info.get('rdb_last_save_time', 0)
        print(f"✓ AOF persistence: {'enabled' if aof_enabled else 'disabled'}")
        print(f"✓ RDB persistence: {'enabled' if rdb_last_save_time > 0 else 'disabled'}")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"✗ Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def verify_cache_operations():
    """Verify cache operations."""
    print("\n=== Verifying Cache Operations ===")
    
    try:
        cache = get_cache()
        
        # Test basic set/get
        test_key = "test:verification:basic"
        test_value = {"message": "Redis cache working", "number": 42}
        
        cache.set_json(test_key, test_value, ttl=60)
        print(f"✓ Cache SET successful: {test_key}")
        
        retrieved = cache.get_json(test_key)
        if retrieved == test_value:
            print(f"✓ Cache GET successful: {retrieved}")
        else:
            print(f"✗ Cache GET mismatch: expected {test_value}, got {retrieved}")
            return False
        
        # Test TTL
        ttl = cache.ttl(test_key)
        if ttl > 0:
            print(f"✓ Cache TTL working: {ttl} seconds remaining")
        else:
            print(f"✗ Cache TTL not working: {ttl}")
            return False
        
        # Test exists
        if cache.exists(test_key):
            print(f"✓ Cache EXISTS working")
        else:
            print(f"✗ Cache EXISTS not working")
            return False
        
        # Test delete
        cache.delete(test_key)
        if not cache.exists(test_key):
            print(f"✓ Cache DELETE working")
        else:
            print(f"✗ Cache DELETE not working")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Cache operations failed: {e}")
        return False


def verify_cache_key_patterns():
    """Verify cache key patterns are properly defined."""
    print("\n=== Verifying Cache Key Patterns ===")
    
    try:
        # Test price keys
        price_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_LATEST,
            ticker="AAPL"
        )
        print(f"✓ Price latest key: {price_key}")
        
        # Test news keys
        news_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.NEWS_TICKER,
            ticker="AAPL",
            hours=24
        )
        print(f"✓ News ticker key: {news_key}")
        
        # Test sentiment keys
        sentiment_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.SENTIMENT_TICKER,
            ticker="AAPL"
        )
        print(f"✓ Sentiment ticker key: {sentiment_key}")
        
        # Test prediction keys
        prediction_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PREDICTION_TICKER,
            ticker="AAPL",
            date="2024-01-15"
        )
        print(f"✓ Prediction ticker key: {prediction_key}")
        
        # Test penny stock keys
        penny_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PENNY_MOMENTUM,
            ticker="XYZ"
        )
        print(f"✓ Penny stock momentum key: {penny_key}")
        
        # Test movers keys
        movers_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.MOVERS_GAINERS,
            date="2024-01-15"
        )
        print(f"✓ Top movers gainers key: {movers_key}")
        
        print("✓ All cache key patterns verified")
        return True
        
    except Exception as e:
        print(f"✗ Cache key pattern verification failed: {e}")
        return False


def verify_pub_sub():
    """Verify Redis pub/sub functionality."""
    print("\n=== Verifying Pub/Sub Functionality ===")
    
    try:
        client = get_redis_client()
        
        # Create subscriber
        pubsub = client.pubsub()
        test_channel = "test:verification:channel"
        test_message = "Hello from pub/sub"
        
        # Subscribe
        pubsub.subscribe(test_channel)
        print(f"✓ Subscribed to channel: {test_channel}")
        
        # Publish
        client.publish(test_channel, test_message)
        print(f"✓ Published message: {test_message}")
        
        # Receive (skip subscription confirmation message)
        message = pubsub.get_message()  # Subscription confirmation
        message = pubsub.get_message()  # Actual message
        
        if message and message['type'] == 'message':
            received_data = message['data'].decode('utf-8')
            if received_data == test_message:
                print(f"✓ Received message: {received_data}")
            else:
                print(f"✗ Message mismatch: expected '{test_message}', got '{received_data}'")
                return False
        else:
            print(f"✗ No message received or wrong type")
            return False
        
        # Cleanup
        pubsub.unsubscribe(test_channel)
        pubsub.close()
        print(f"✓ Pub/Sub verification successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Pub/Sub verification failed: {e}")
        return False


def verify_celery_broker():
    """Verify Redis is accessible as Celery broker."""
    print("\n=== Verifying Celery Broker Connection ===")
    
    try:
        settings = get_settings()
        
        # Connect to Celery broker (Redis DB 1)
        broker_client = redis.from_url(settings.celery_broker_url)
        result = broker_client.ping()
        print(f"✓ Celery broker PING successful: {result}")
        
        # Connect to Celery result backend (Redis DB 2)
        backend_client = redis.from_url(settings.celery_result_backend)
        result = backend_client.ping()
        print(f"✓ Celery result backend PING successful: {result}")
        
        broker_client.close()
        backend_client.close()
        
        return True
        
    except redis.ConnectionError as e:
        print(f"✗ Celery Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """Run all Redis verifications."""
    print("=" * 60)
    print("Redis 7.0+ Verification for Institutional Upgrade")
    print("Phase 0.1.2 - Redis Cache Setup")
    print("=" * 60)
    
    results = []
    
    # Run verifications
    results.append(("Connection", verify_redis_connection()))
    results.append(("Cache Operations", verify_cache_operations()))
    results.append(("Cache Key Patterns", verify_cache_key_patterns()))
    results.append(("Pub/Sub", verify_pub_sub()))
    results.append(("Celery Broker", verify_celery_broker()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ ALL VERIFICATIONS PASSED")
        print("\nRedis 7.0+ is properly configured and ready for:")
        print("  - Caching (price data, news, sentiment, predictions)")
        print("  - Pub/sub messaging (real-time data distribution)")
        print("  - Celery task queue backend")
        return 0
    else:
        print("\n✗ SOME VERIFICATIONS FAILED")
        print("\nPlease check the errors above and fix configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
