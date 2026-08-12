# Cache Key Patterns and TTL Configuration

This document defines all cache key patterns and their associated Time-To-Live (TTL) values for the StockIQ platform's Redis caching layer.

## Overview

The caching strategy is designed to balance data freshness with system performance according to Requirements 22.1-22.5 of the institutional-upgrade specification.

## Cache Key Patterns

All cache key patterns are defined in `stockiq/infrastructure/cache.py` in the `CacheKeyPatterns` class.

### Price Data

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `price:{ticker}:latest` | `price:AAPL:latest` | 30s | Current/real-time price |
| `price:{ticker}:history:{timeframe}` | `price:AAPL:history:1d` | 5min | Historical OHLCV data |
| `price:{ticker}:intraday:{date}` | `price:AAPL:intraday:2024-01-15` | 5min | Intraday historical data |

### News Data

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `news:latest:{limit}` | `news:latest:100` | 1hr | Latest news feed |
| `news:ticker:{ticker}:{hours}` | `news:ticker:TSLA:24` | 1hr | Ticker-specific news |
| `news:article:{article_id}` | `news:article:abc123` | 24hr | Individual article (immutable) |
| `news:breaking` | `news:breaking` | 5min | Breaking news feed |

### Sentiment Data

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `sentiment:{ticker}:latest` | `sentiment:AAPL:latest` | 15min | Ticker sentiment score |
| `sentiment:market:latest` | `sentiment:market:latest` | 15min | Market-wide sentiment |
| `sentiment:article:{article_id}` | `sentiment:article:abc123` | 1hr | Article sentiment (stable) |

### Prediction Data

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `prediction:{ticker}:{date}` | `prediction:NVDA:2024-01-15` | 24hr | Daily prediction per ticker |
| `predictions:daily:{date}` | `predictions:daily:2024-01-15` | 24hr | All daily predictions |
| `prediction:accuracy:{ticker}` | `prediction:accuracy:AAPL` | 1hr | Prediction accuracy metrics |

### Top Movers

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `movers:gainers:{date}` | `movers:gainers:2024-01-15` | 5min | Top gaining stocks |
| `movers:losers:{date}` | `movers:losers:2024-01-15` | 5min | Top losing stocks |
| `movers:unusual_volume:{date}` | `movers:unusual_volume:2024-01-15` | 5min | Unusual volume stocks |

### Penny Stocks

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `penny:movers:{date}` | `penny:movers:2024-01-15` | 2min | Penny stock movers |
| `penny:momentum:{ticker}` | `penny:momentum:XYZ` | 2min | Penny stock momentum score |
| `penny:risk:{ticker}` | `penny:risk:XYZ` | 5min | Penny stock risk metrics |
| `penny:top:{date}:{limit}` | `penny:top:2024-01-15:20` | 2min | Top penny stocks list |

### Market Overview

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `market:indices:latest` | `market:indices:latest` | 30s | Market indices (S&P, NASDAQ, etc.) |
| `market:sectors:{date}` | `market:sectors:2024-01-15` | 5min | Sector performance |
| `market:sentiment:gauge` | `market:sentiment:gauge` | 15min | Market sentiment gauge |

### User Data

| Pattern | Example | TTL | Description |
|---------|---------|-----|-------------|
| `user:{user_id}:watchlist` | `user:123:watchlist` | 5min | User watchlist |
| `user:{user_id}:alerts` | `user:123:alerts` | 1min | User alerts (near real-time) |
| `user:{user_id}:preferences` | `user:123:preferences` | 1hr | User preferences |

## TTL Values

### Standard TTL Values

- **30 seconds**: Real-time data (prices, indices) - Requirement 22.2
- **2 minutes**: High-volatility penny stocks
- **5 minutes**: Technical indicators, movers - Requirement 22.3
- **15 minutes**: Sentiment analysis - Requirement 22.5
- **1 hour**: News articles, user alerts
- **24 hours**: Predictions, fundamental data - Requirement 22.4

### TTL Rationale

1. **Real-time Data (30s)**: Current prices and indices require sub-minute freshness for real-time trading decisions
2. **Penny Stocks (2min)**: High volatility requires more frequent updates than standard stocks
3. **Technical Data (5min)**: Balance between data freshness and API rate limits
4. **Sentiment Data (15min)**: Sentiment doesn't change as rapidly as prices
5. **News Articles (1-24hr)**: Published content is immutable; longer cache for efficiency
6. **Predictions (24hr)**: Daily predictions are generated once per day

## Usage Examples

### Basic Cache Operations

```python
from stockiq.infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL

cache = get_cache()

# Store price with automatic TTL
key = CacheKeyPatterns.format_key(
    CacheKeyPatterns.PRICE_LATEST, 
    ticker="AAPL"
)
cache.set_with_pattern_ttl(key, price_data)

# Retrieve price
price = cache.get(key)
```

### Manual TTL Control

```python
# Store with explicit TTL
cache.set(
    "price:AAPL:latest", 
    price_data, 
    ttl=CacheTTL.PRICE_LATEST
)

# Get TTL for a pattern
ttl = CacheTTL.get_ttl("price:AAPL:latest")  # Returns 30
```

### Pattern-Based Operations

```python
# Delete all price caches
cache.delete_pattern("price:*")

# Delete all news caches for a specific ticker
cache.delete_pattern("news:ticker:AAPL:*")
```

## Requirements Compliance

This cache key pattern and TTL configuration complies with the following requirements from the institutional-upgrade specification:

- **Requirement 22.1**: Redis for in-memory data caching ✓
- **Requirement 22.2**: Current stock prices with 30-second TTL ✓
- **Requirement 22.3**: Technical indicators with 5-minute TTL ✓
- **Requirement 22.4**: Fundamental data with 24-hour TTL ✓
- **Requirement 22.5**: News sentiment with 15-minute TTL ✓
- **Requirement 22.9**: Cache key namespacing for different data types ✓

## Testing

All cache key patterns and TTL values are validated by comprehensive tests in `tests/test_cache_keys.py`:

```bash
pytest tests/test_cache_keys.py -v
```

## Configuration

TTL values can be overridden via environment variables in production if needed:

```env
PRICE_CACHE_TTL=300  # 5 minutes (for testing)
NEWS_CACHE_TTL=3600  # 1 hour
PREDICTION_CACHE_TTL=86400  # 24 hours
```

However, the default values defined in `CacheTTL` class are optimized for production use and should not be changed without careful consideration of performance and data freshness tradeoffs.
