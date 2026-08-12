# Redis Quick Reference

Quick reference for Redis operations in StockIQ.

## Connection Configuration

```bash
# Development (direct connection)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Production with password
REDIS_URL=redis://:your_password@redis-host:6379/0
REDIS_PASSWORD=your_password

# Production with Sentinel (HA)
REDIS_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
REDIS_SENTINEL_MASTER=stockiq-master
REDIS_PASSWORD=your_password
```

## Usage Examples

### Basic Cache Operations

```python
from stockiq.infrastructure.cache import get_cache, CacheKeyPatterns

cache = get_cache()

# Set with automatic TTL based on pattern
key = CacheKeyPatterns.format_key(
    CacheKeyPatterns.PRICE_LATEST,
    ticker="AAPL"
)
cache.set_with_pattern_ttl(key, price_data)

# Get from cache
price = cache.get(key)

# Check if exists
if cache.exists(key):
    print("Cache hit!")

# Delete
cache.delete(key)
```

### Pub/Sub for Real-Time Updates

```python
# Publish price update
cache.publish("price_updates", {
    "ticker": "AAPL",
    "price": 150.25,
    "timestamp": "2024-01-15T10:30:00Z"
})

# Subscribe to updates (in separate thread/process)
def handle_update(channel, message):
    print(f"Received on {channel}: {message}")

cache.subscribe(["price_updates"], handle_update)
```

### Cache Key Patterns

| Pattern | TTL | Usage |
|---------|-----|-------|
| `price:{ticker}:latest` | 30s | Current price |
| `news:ticker:{ticker}:{hours}` | 1hr | Ticker news |
| `sentiment:{ticker}:latest` | 15min | Sentiment score |
| `prediction:{ticker}:{date}` | 24hr | Daily prediction |
| `movers:gainers:{date}` | 5min | Top gainers |
| `penny:momentum:{ticker}` | 2min | Penny stock momentum |

## Docker Commands

```bash
# Start Redis
docker-compose up -d redis

# Check Redis status
docker exec -it stockiq-redis redis-cli ping

# Monitor Redis commands
docker exec -it stockiq-redis redis-cli MONITOR

# Check memory usage
docker exec -it stockiq-redis redis-cli info memory

# Flush cache (WARNING: deletes all data)
docker exec -it stockiq-redis redis-cli FLUSHALL
```

## Performance Tips

1. **Use connection pooling** (already configured)
2. **Set appropriate TTLs** (use pattern-based TTLs)
3. **Use pipelines for bulk operations** (reduces round trips)
4. **Monitor memory usage** (set alerts at 80%)
5. **Use read replicas** (Sentinel mode for high availability)

## Troubleshooting

```bash
# Check Redis is running
docker ps | grep redis

# View Redis logs
docker logs stockiq-redis

# Test connection
python scripts/test_redis_setup.py

# Check slow queries
docker exec -it stockiq-redis redis-cli SLOWLOG GET 10
```

## See Also

- **Full Guide:** `REDIS_SETUP_GUIDE.md`
- **Cache Keys:** `CACHE_KEY_PATTERNS.md`
- **Configuration:** `stockiq/infrastructure/config.py`
- **Implementation:** `stockiq/infrastructure/cache.py`
