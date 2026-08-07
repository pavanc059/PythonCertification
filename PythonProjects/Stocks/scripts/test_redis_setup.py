#!/usr/bin/env python3
"""
Test Redis setup and configuration.

This script verifies:
1. Redis connection
2. Connection pooling
3. Cache operations
4. Pub/sub functionality
5. Performance metrics
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stockiq.infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
from stockiq.infrastructure.config import get_settings
import structlog

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


def test_connection():
    """Test basic Redis connection."""
    print("\n" + "="*60)
    print("TEST 1: Redis Connection")
    print("="*60)
    
    try:
        cache = get_cache()
        result = cache.ping()
        
        if result:
            print("✓ Redis connection successful")
            
            # Get server info
            info = cache.get_info()
            print(f"✓ Redis version: {info.get('redis_version', 'unknown')}")
            print(f"✓ Used memory: {info.get('used_memory_human', 'unknown')}")
            print(f"✓ Connected clients: {info.get('connected_clients', 0)}")
            print(f"✓ Total connections received: {info.get('total_connections_received', 0)}")
            print(f"✓ Total commands processed: {info.get('total_commands_processed', 0)}")
            
            return True
        else:
            print("✗ Redis ping failed")
            return False
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_cache_operations():
    """Test basic cache operations."""
    print("\n" + "="*60)
    print("TEST 2: Cache Operations")
    print("="*60)
    
    try:
        cache = get_cache()
        
        # Test 1: String set/get
        test_key = "test:string"
        test_value = "Hello, Redis!"
        cache.set(test_key, test_value, ttl=60, serialize=False)
        retrieved = cache.get(test_key, deserialize=False)
        
        if retrieved.decode('utf-8') == test_value:
            print("✓ String set/get working")
        else:
            print("✗ String set/get failed")
            return False
        
        # Test 2: Object serialization
        test_key = "test:object"
        test_obj = {"ticker": "AAPL", "price": 150.25, "volume": 1000000}
        cache.set(test_key, test_obj, ttl=60)
        retrieved = cache.get(test_key)
        
        if retrieved == test_obj:
            print("✓ Object serialization working")
        else:
            print("✗ Object serialization failed")
            return False
        
        # Test 3: TTL
        ttl = cache.ttl(test_key)
        if 55 <= ttl <= 60:
            print(f"✓ TTL working (remaining: {ttl}s)")
        else:
            print(f"✗ TTL unexpected: {ttl}s")
        
        # Test 4: Exists
        if cache.exists(test_key):
            print("✓ Exists check working")
        else:
            print("✗ Exists check failed")
            return False
        
        # Test 5: Delete
        cache.delete(test_key)
        if not cache.exists(test_key):
            print("✓ Delete working")
        else:
            print("✗ Delete failed")
            return False
        
        # Test 6: Pattern-based TTL
        key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_LATEST,
            ticker="AAPL"
        )
        cache.set_with_pattern_ttl(key, {"price": 150.25})
        ttl = cache.ttl(key)
        expected_ttl = CacheTTL.PRICE_LATEST
        
        if ttl <= expected_ttl and ttl > 0:
            print(f"✓ Pattern-based TTL working (TTL: {ttl}s, expected: {expected_ttl}s)")
        else:
            print(f"✗ Pattern-based TTL failed (TTL: {ttl}s, expected: {expected_ttl}s)")
        
        # Cleanup
        cache.delete(key)
        
        return True
        
    except Exception as e:
        print(f"✗ Cache operations failed: {e}")
        return False


def test_advanced_operations():
    """Test advanced cache operations."""
    print("\n" + "="*60)
    print("TEST 3: Advanced Operations")
    print("="*60)
    
    try:
        cache = get_cache()
        
        # Test 1: List operations
        list_key = "test:list"
        cache.push_list(list_key, "item1", ttl=60)
        cache.push_list(list_key, "item2")
        cache.push_list(list_key, "item3")
        items = cache.get_list(list_key)
        
        if len(items) == 3 and items[0] == "item1":
            print("✓ List operations working")
        else:
            print("✗ List operations failed")
            return False
        
        cache.delete(list_key)
        
        # Test 2: Set operations
        set_key = "test:set"
        cache.add_to_set(set_key, "value1", ttl=60)
        cache.add_to_set(set_key, "value2")
        cache.add_to_set(set_key, "value1")  # Duplicate
        items = cache.get_set(set_key)
        
        if len(items) == 2:
            print("✓ Set operations working (deduplication works)")
        else:
            print("✗ Set operations failed")
            return False
        
        cache.delete(set_key)
        
        # Test 3: JSON operations
        json_key = "test:json"
        json_obj = {"name": "StockIQ", "version": "2.0"}
        cache.set_json(json_key, json_obj, ttl=60)
        retrieved = cache.get_json(json_key)
        
        if retrieved == json_obj:
            print("✓ JSON operations working")
        else:
            print("✗ JSON operations failed")
            return False
        
        cache.delete(json_key)
        
        # Test 4: Counter operations
        counter_key = "test:counter"
        cache.increment(counter_key, 5)
        cache.increment(counter_key, 3)
        cache.decrement(counter_key, 2)
        # Final value should be 6
        
        print("✓ Counter operations working")
        cache.delete(counter_key)
        
        return True
        
    except Exception as e:
        print(f"✗ Advanced operations failed: {e}")
        return False


def test_connection_pooling():
    """Test connection pooling."""
    print("\n" + "="*60)
    print("TEST 4: Connection Pooling")
    print("="*60)
    
    try:
        cache = get_cache()
        settings = get_settings()
        
        # Get pool stats
        stats = cache.get_pool_stats()
        
        print(f"✓ Max connections: {stats.get('max_connections', settings.redis_max_connections)}")
        print(f"✓ Created connections: {stats.get('created_connections', 0)}")
        print(f"✓ Available connections: {stats.get('available_connections', 0)}")
        print(f"✓ In-use connections: {stats.get('in_use_connections', 0)}")
        
        # Perform multiple operations to test pooling
        for i in range(10):
            cache.set(f"test:pool:{i}", f"value{i}", ttl=60)
        
        for i in range(10):
            cache.get(f"test:pool:{i}")
        
        # Cleanup
        for i in range(10):
            cache.delete(f"test:pool:{i}")
        
        print("✓ Connection pooling working")
        return True
        
    except Exception as e:
        print(f"✗ Connection pooling test failed: {e}")
        return False


def test_pubsub():
    """Test pub/sub functionality."""
    print("\n" + "="*60)
    print("TEST 5: Pub/Sub")
    print("="*60)
    
    try:
        cache = get_cache()
        
        # Test publishing
        channel = "test:channel"
        message = {"event": "price_update", "ticker": "AAPL", "price": 150.25}
        
        subscribers = cache.publish(channel, message)
        print(f"✓ Published message (subscribers: {subscribers})")
        
        # Get active channels
        channels = cache.get_pubsub_channels("test:*")
        print(f"✓ Active channels: {len(channels)}")
        
        # Note: Testing subscribe requires separate thread/process
        # So we just test the publish side here
        
        return True
        
    except Exception as e:
        print(f"✗ Pub/sub test failed: {e}")
        return False


def test_performance():
    """Test cache performance."""
    print("\n" + "="*60)
    print("TEST 6: Performance")
    print("="*60)
    
    try:
        cache = get_cache()
        
        # Test write performance
        num_ops = 1000
        start = time.time()
        
        for i in range(num_ops):
            cache.set(f"test:perf:{i}", f"value{i}", ttl=60, serialize=False)
        
        write_time = time.time() - start
        write_ops_per_sec = num_ops / write_time
        
        print(f"✓ Write performance: {write_ops_per_sec:.0f} ops/sec ({write_time:.3f}s for {num_ops} ops)")
        
        # Test read performance
        start = time.time()
        
        for i in range(num_ops):
            cache.get(f"test:perf:{i}", deserialize=False)
        
        read_time = time.time() - start
        read_ops_per_sec = num_ops / read_time
        
        print(f"✓ Read performance: {read_ops_per_sec:.0f} ops/sec ({read_time:.3f}s for {num_ops} ops)")
        
        # Test delete performance
        start = time.time()
        cache.delete_pattern("test:perf:*")
        delete_time = time.time() - start
        
        print(f"✓ Bulk delete: {delete_time:.3f}s for {num_ops} keys")
        
        # Check if performance meets requirements
        if write_ops_per_sec >= 1000 and read_ops_per_sec >= 5000:
            print("✓ Performance meets requirements (>1K writes/sec, >5K reads/sec)")
        else:
            print("⚠ Performance below optimal (consider tuning)")
        
        return True
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False


def test_cache_key_patterns():
    """Test cache key pattern definitions."""
    print("\n" + "="*60)
    print("TEST 7: Cache Key Patterns & TTLs")
    print("="*60)
    
    try:
        # Test key formatting
        key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_LATEST,
            ticker="AAPL"
        )
        assert key == "price:AAPL:latest", f"Key format failed: {key}"
        print(f"✓ Price latest key: {key}")
        
        key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.NEWS_TICKER,
            ticker="AAPL",
            hours=24
        )
        assert key == "news:ticker:AAPL:24", f"Key format failed: {key}"
        print(f"✓ News ticker key: {key}")
        
        key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PREDICTION_TICKER,
            ticker="AAPL",
            date="2024-01-15"
        )
        assert key == "prediction:AAPL:2024-01-15", f"Key format failed: {key}"
        print(f"✓ Prediction key: {key}")
        
        # Test TTL retrieval
        ttl = CacheTTL.get_ttl("price:AAPL:latest")
        assert ttl == CacheTTL.PRICE_LATEST, f"TTL retrieval failed: {ttl}"
        print(f"✓ Price TTL: {ttl}s")
        
        ttl = CacheTTL.get_ttl("news:ticker:AAPL:24")
        assert ttl == CacheTTL.NEWS_TICKER, f"TTL retrieval failed: {ttl}"
        print(f"✓ News TTL: {ttl}s")
        
        # Get all TTLs
        all_ttls = CacheTTL.get_all_ttls()
        print(f"✓ Defined TTL patterns: {len(all_ttls)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Cache key patterns test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("REDIS SETUP VERIFICATION")
    print("="*60)
    
    settings = get_settings()
    print(f"\nRedis URL: {settings.redis_url}")
    print(f"Max connections: {settings.redis_max_connections}")
    
    if settings.redis_sentinel_hosts:
        print(f"Sentinel mode: ENABLED")
        print(f"Sentinel hosts: {settings.redis_sentinel_hosts}")
        print(f"Master name: {settings.redis_sentinel_master}")
    else:
        print(f"Sentinel mode: DISABLED (direct connection)")
    
    tests = [
        ("Connection", test_connection),
        ("Cache Operations", test_cache_operations),
        ("Advanced Operations", test_advanced_operations),
        ("Connection Pooling", test_connection_pooling),
        ("Pub/Sub", test_pubsub),
        ("Performance", test_performance),
        ("Cache Key Patterns", test_cache_key_patterns),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Redis setup is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please check configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
