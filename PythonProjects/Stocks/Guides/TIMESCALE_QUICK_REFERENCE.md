# TimescaleDB Continuous Aggregates - Quick Reference

## Query API

### Get OHLCV Data

```python
from stockiq.infrastructure.timescale import get_ohlcv_data
from datetime import datetime, timedelta

# 5 years of daily data
end_time = datetime.now()
start_time = end_time - timedelta(days=5*365)
df = get_ohlcv_data('AAPL', start_time, end_time, '1d')
```

### Get Latest Data

```python
from stockiq.infrastructure.timescale import get_latest_ohlcv

# Last 100 days
df = get_latest_ohlcv('AAPL', '1d', limit=100)

# Last 50 hours
df = get_latest_ohlcv('TSLA', '1h', limit=50)
```

### Multi-Ticker Queries

```python
from stockiq.infrastructure.timescale import get_ohlcv_data_multi_ticker

tickers = ['AAPL', 'MSFT', 'GOOGL']
data = get_ohlcv_data_multi_ticker(tickers, start_time, end_time, '1d')

# Returns: {'AAPL': df, 'MSFT': df, 'GOOGL': df}
```

### Get Statistics

```python
from stockiq.infrastructure.timescale import get_aggregate_statistics

stats = get_aggregate_statistics('1d')
print(f"Total rows: {stats['total_rows']}")
print(f"Stocks: {stats['num_stocks']}")
print(f"Date range: {stats['earliest_data']} to {stats['latest_data']}")
```

### Manual Refresh

```python
from stockiq.infrastructure.timescale import refresh_continuous_aggregate

# Refresh daily aggregate (useful after bulk import)
refresh_continuous_aggregate('1d')
```

### Benchmark Performance

```python
from stockiq.infrastructure.timescale import benchmark_query_performance

results = benchmark_query_performance('AAPL')
for interval, result in results.items():
    print(f"{interval}: {result['elapsed_ms']:.1f}ms")
```

## Supported Intervals

| Interval | Aliases | Refresh | Use Case |
|----------|---------|---------|----------|
| `1m` or `1min` | | Every 5 min | Real-time |
| `5m` or `5min` | | Every 15 min | Intraday |
| `1h` or `1hour` | | Hourly | Day trading |
| `1d`, `1day`, `daily` | | Daily | Long-term |

## DataFrame Columns

All queries return DataFrames with these columns:

- `timestamp` - Time bucket start
- `open` - Opening price (first in bucket)
- `high` - Highest price in bucket
- `low` - Lowest price in bucket
- `close` - Closing price (last in bucket)
- `volume` - Total volume in bucket
- `num_trades` - Number of trades in bucket

## Performance Guidelines

### Choose the Right Interval

- **Need second-by-second?** → Query raw `price_data` table
- **Need minute precision?** → Use `1m` aggregate
- **Need hourly charts?** → Use `1h` aggregate
- **Need daily analysis?** → Use `1d` aggregate (fastest!)

### Query Optimization

✅ **DO:**
- Use coarsest interval that meets your needs
- Limit time ranges to what you need
- Cache results for frequently-used queries

❌ **DON'T:**
- Query `price_data` for aggregated data
- Use finer intervals than necessary
- Query unbounded time ranges

### Expected Performance

| Interval | 5-Year Query | Typical Use |
|----------|-------------|-------------|
| `1d` | ~50ms | Historical analysis, backtesting |
| `1h` | ~120ms | Medium-term analysis |
| `5m` | ~180ms | Short-term trading |
| `1m` | ~250ms | Real-time monitoring |

## Maintenance

### Check Aggregate Health

```python
from stockiq.infrastructure.timescale import get_aggregate_statistics
from datetime import datetime, timedelta

stats = get_aggregate_statistics('1d')
if stats['latest_data'] < datetime.now() - timedelta(days=2):
    print("⚠️ Aggregate is stale!")
```

### Manual Refresh (if needed)

```bash
python -c "from stockiq.infrastructure.timescale import refresh_continuous_aggregate; refresh_continuous_aggregate('1d')"
```

### Verify Performance

```bash
python scripts/verify_aggregate_performance.py
```

## Common Patterns

### Historical Analysis

```python
# Get 1 year of data
df = get_ohlcv_data('AAPL', start_time, end_time, '1d')

# Calculate returns
df['return'] = df['close'].pct_change()

# Moving averages
df['sma_20'] = df['close'].rolling(20).mean()
```

### Intraday Analysis

```python
# Today's 5-minute bars
from datetime import datetime, time

today = datetime.now().date()
start = datetime.combine(today, time(9, 30))
end = datetime.combine(today, time(16, 0))

df = get_ohlcv_data('TSLA', start, end, '5m')
```

### Correlation Analysis

```python
# Get data for multiple stocks
data = get_ohlcv_data_multi_ticker(
    ['AAPL', 'MSFT', 'GOOGL'], 
    start_time, 
    end_time, 
    '1d'
)

# Calculate correlation
returns = {ticker: df['close'].pct_change() for ticker, df in data.items()}
corr = pd.DataFrame(returns).corr()
```

## Troubleshooting

### "View not found" Error

Run the migration:
```bash
python scripts/migrate_continuous_aggregates.py
```

### Slow Queries

1. Check you're using appropriate interval
2. Verify indexes exist: `SELECT * FROM pg_indexes WHERE tablename LIKE 'price_data_%';`
3. Check aggregate freshness with `get_aggregate_statistics()`

### Stale Data

Manually refresh:
```python
from stockiq.infrastructure.timescale import refresh_continuous_aggregate
refresh_continuous_aggregate('1d')
```

## Database Views

Direct SQL access (if needed):

```sql
-- Query 1-day aggregate
SELECT * FROM price_data_1day
WHERE stock_id = (SELECT id FROM stocks WHERE ticker = 'AAPL')
AND bucket >= NOW() - INTERVAL '1 year'
ORDER BY bucket DESC;

-- Query 1-hour aggregate  
SELECT * FROM price_data_1hour
WHERE stock_id = (SELECT id FROM stocks WHERE ticker = 'TSLA')
AND bucket >= NOW() - INTERVAL '7 days'
ORDER BY bucket DESC;
```

## References

- Full documentation: `TASK_COMPLETION_TIMESCALEDB_CONTINUOUS_AGGREGATES.md`
- Implementation: `stockiq/infrastructure/timescale.py`
- Tests: `tests/test_timescale_aggregates.py`
- Migration: `scripts/migrate_continuous_aggregates.py`
