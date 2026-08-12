# Database Quick Reference

Quick reference guide for common database operations with PostgreSQL + TimescaleDB.

## Connection

### Connect to Database

```powershell
# Using Docker
docker exec -it stockiq-timescaledb psql -U stockiq -d stockiq

# Using psql (if installed locally)
psql -h localhost -p 5432 -U stockiq -d stockiq
```

### Connection String

```
postgresql://stockiq:your_password@localhost:5432/stockiq
```

## Common psql Commands

```sql
-- List all databases
\l

-- List all tables
\dt

-- Describe table structure
\d table_name

-- List all indexes
\di

-- List all views
\dv

-- Show table sizes
\dt+

-- Execute SQL from file
\i /path/to/file.sql

-- Toggle expanded display (better for wide tables)
\x

-- Show query execution time
\timing

-- Quit psql
\q
```

## Database Information

### Check TimescaleDB Version

```sql
SELECT * FROM pg_extension WHERE extname = 'timescaledb';
```

### List All Hypertables

```sql
SELECT * FROM timescaledb_information.hypertables;
```

### Get Hypertable Details

```sql
SELECT * FROM get_hypertable_info();
```

### View Database Statistics

```sql
SELECT * FROM database_stats;
```

### View Table Sizes

```sql
SELECT * FROM table_sizes;
```

### View Index Usage

```sql
SELECT * FROM index_usage;
```

## Table Operations

### List All Tables

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

### Count Rows in Table

```sql
SELECT COUNT(*) FROM stocks;
SELECT COUNT(*) FROM price_data;
SELECT COUNT(*) FROM news_articles;
```

### View Recent Data

```sql
-- Recent price data
SELECT s.ticker, p.timestamp, p.close, p.volume
FROM price_data p
JOIN stocks s ON p.stock_id = s.id
ORDER BY p.timestamp DESC
LIMIT 10;

-- Recent news articles
SELECT title, source, published_at, category
FROM news_articles
ORDER BY published_at DESC
LIMIT 10;

-- Recent predictions
SELECT s.ticker, dp.prediction_date, dp.predicted_price, dp.confidence, dp.category
FROM daily_predictions dp
JOIN stocks s ON dp.stock_id = s.id
ORDER BY dp.prediction_date DESC
LIMIT 10;
```

## Stock Queries

### Find Stock by Ticker

```sql
SELECT * FROM stocks WHERE ticker = 'AAPL';
```

### List All Stocks by Sector

```sql
SELECT sector, COUNT(*) as stock_count
FROM stocks
GROUP BY sector
ORDER BY stock_count DESC;
```

### Find Penny Stocks

```sql
SELECT ticker, name, sector
FROM stocks
WHERE is_penny_stock = true
ORDER BY ticker;
```

## Price Data Queries

### Get Latest Price for Stock

```sql
SELECT s.ticker, p.timestamp, p.close, p.volume
FROM price_data p
JOIN stocks s ON p.stock_id = s.id
WHERE s.ticker = 'AAPL'
ORDER BY p.timestamp DESC
LIMIT 1;
```

### Get Price History

```sql
SELECT timestamp, open, high, low, close, volume
FROM price_data p
JOIN stocks s ON p.stock_id = s.id
WHERE s.ticker = 'AAPL'
  AND timestamp >= NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;
```

### Calculate Daily Returns

```sql
SELECT 
    timestamp::date as date,
    close,
    LAG(close) OVER (ORDER BY timestamp) as prev_close,
    ROUND(((close - LAG(close) OVER (ORDER BY timestamp)) / LAG(close) OVER (ORDER BY timestamp) * 100)::numeric, 2) as return_pct
FROM price_data p
JOIN stocks s ON p.stock_id = s.id
WHERE s.ticker = 'AAPL'
  AND timestamp >= NOW() - INTERVAL '30 days'
ORDER BY timestamp;
```

## TimescaleDB Specific Queries

### Time Bucket Aggregation (Daily OHLCV)

```sql
SELECT 
    time_bucket('1 day', timestamp) AS day,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM price_data p
JOIN stocks s ON p.stock_id = s.id
WHERE s.ticker = 'AAPL'
  AND timestamp >= NOW() - INTERVAL '90 days'
GROUP BY day
ORDER BY day DESC;
```

### Time Bucket Aggregation (Hourly)

```sql
SELECT 
    time_bucket('1 hour', timestamp) AS hour,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM price_data p
JOIN stocks s ON p.stock_id = s.id
WHERE s.ticker = 'AAPL'
  AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour DESC;
```

### Check Chunk Information

```sql
SELECT 
    chunk_name,
    range_start,
    range_end,
    pg_size_pretty(total_bytes) as size
FROM timescaledb_information.chunks
WHERE hypertable_name = 'price_data'
ORDER BY range_start DESC;
```

## News and Sentiment Queries

### Recent News with Sentiment

```sql
SELECT 
    na.title,
    na.source,
    na.published_at,
    na.category,
    s.ticker,
    ns.sentiment_score,
    ns.confidence
FROM news_articles na
JOIN news_sentiment ns ON na.id = ns.article_id
JOIN stocks s ON ns.stock_id = s.id
WHERE s.ticker = 'AAPL'
ORDER BY na.published_at DESC
LIMIT 10;
```

### Average Sentiment by Stock

```sql
SELECT 
    s.ticker,
    COUNT(*) as article_count,
    ROUND(AVG(ns.sentiment_score)::numeric, 3) as avg_sentiment,
    ROUND(AVG(ns.confidence)::numeric, 3) as avg_confidence
FROM news_sentiment ns
JOIN stocks s ON ns.stock_id = s.id
WHERE ns.created_at >= NOW() - INTERVAL '7 days'
GROUP BY s.ticker
ORDER BY avg_sentiment DESC;
```

### Breaking News

```sql
SELECT title, source, published_at, category
FROM news_articles
WHERE is_breaking = true
  AND published_at >= NOW() - INTERVAL '24 hours'
ORDER BY published_at DESC;
```

## Prediction Queries

### Recent Predictions with Accuracy

```sql
SELECT 
    s.ticker,
    dp.prediction_date,
    dp.predicted_price,
    dp.actual_price,
    dp.confidence,
    dp.category,
    dp.is_accurate
FROM daily_predictions dp
JOIN stocks s ON dp.stock_id = s.id
WHERE dp.actual_price IS NOT NULL
ORDER BY dp.prediction_date DESC
LIMIT 20;
```

### Prediction Accuracy by Stock

```sql
SELECT 
    s.ticker,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN dp.is_accurate THEN 1 ELSE 0 END) as accurate_predictions,
    ROUND(100.0 * SUM(CASE WHEN dp.is_accurate THEN 1 ELSE 0 END) / COUNT(*)::numeric, 2) as accuracy_pct
FROM daily_predictions dp
JOIN stocks s ON dp.stock_id = s.id
WHERE dp.actual_price IS NOT NULL
GROUP BY s.ticker
HAVING COUNT(*) >= 10
ORDER BY accuracy_pct DESC;
```

## Top Movers Queries

### Today's Top Gainers

```sql
SELECT 
    s.ticker,
    s.name,
    tm.price_change_pct,
    tm.volume,
    tm.volume_ratio,
    tm.has_unusual_volume
FROM top_movers tm
JOIN stocks s ON tm.stock_id = s.id
WHERE tm.date = CURRENT_DATE
  AND tm.is_gainer = true
ORDER BY tm.rank;
```

### Today's Top Losers

```sql
SELECT 
    s.ticker,
    s.name,
    tm.price_change_pct,
    tm.volume,
    tm.volume_ratio
FROM top_movers tm
JOIN stocks s ON tm.stock_id = s.id
WHERE tm.date = CURRENT_DATE
  AND tm.is_gainer = false
ORDER BY tm.rank;
```

## Penny Stock Queries

### Top Penny Stocks by Momentum

```sql
SELECT 
    ticker,
    price,
    price_change_pct,
    volume_ratio,
    momentum_score,
    catalyst
FROM penny_stock_momentum
WHERE date = CURRENT_DATE
ORDER BY rank
LIMIT 20;
```

### Penny Stocks with High Risk

```sql
SELECT 
    psm.ticker,
    psm.price,
    psm.momentum_score,
    prm.overall_risk,
    prm.suspicion_score,
    prm.recommendation
FROM penny_stock_momentum psm
JOIN penny_stock_risk_metrics prm ON psm.ticker = prm.ticker AND psm.date = prm.date
WHERE psm.date = CURRENT_DATE
  AND prm.overall_risk IN ('high', 'extreme')
ORDER BY prm.suspicion_score DESC;
```

## Maintenance Operations

### Vacuum Tables

```sql
-- Analyze tables to update statistics
ANALYZE;

-- Vacuum specific table
VACUUM ANALYZE price_data;

-- Full vacuum (requires exclusive lock)
VACUUM FULL price_data;
```

### Reindex

```sql
-- Reindex specific table
REINDEX TABLE price_data;

-- Reindex all tables in database
REINDEX DATABASE stockiq;
```

### Check Table Bloat

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_tuple_pct
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;
```

## Performance Monitoring

### Active Queries

```sql
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    NOW() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE state != 'idle'
  AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;
```

### Slow Queries

```sql
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time,
    stddev_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Cache Hit Ratio

```sql
SELECT 
    'cache hit rate' AS metric,
    ROUND(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0), 2) AS percentage
FROM pg_stat_database;
```

### Lock Information

```sql
SELECT 
    l.locktype,
    l.database,
    l.relation::regclass,
    l.mode,
    l.granted,
    a.usename,
    a.query,
    a.query_start
FROM pg_locks l
JOIN pg_stat_activity a ON l.pid = a.pid
WHERE NOT l.granted
ORDER BY a.query_start;
```

## Backup and Restore

### Backup Database

```powershell
# Backup entire database
docker exec stockiq-timescaledb pg_dump -U stockiq stockiq > backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Backup specific table
docker exec stockiq-timescaledb pg_dump -U stockiq -t price_data stockiq > price_data_backup.sql

# Backup with compression
docker exec stockiq-timescaledb pg_dump -U stockiq stockiq | gzip > backup.sql.gz
```

### Restore Database

```powershell
# Restore from backup
Get-Content backup.sql | docker exec -i stockiq-timescaledb psql -U stockiq stockiq

# Restore from compressed backup
gunzip -c backup.sql.gz | docker exec -i stockiq-timescaledb psql -U stockiq stockiq
```

## Useful Functions

### Get Stock ID by Ticker

```sql
CREATE OR REPLACE FUNCTION get_stock_id(ticker_symbol TEXT)
RETURNS INTEGER AS $$
    SELECT id FROM stocks WHERE ticker = ticker_symbol;
$$ LANGUAGE SQL;

-- Usage
SELECT get_stock_id('AAPL');
```

### Calculate Moving Average

```sql
CREATE OR REPLACE FUNCTION calculate_sma(
    ticker_symbol TEXT,
    period INTEGER DEFAULT 20
)
RETURNS TABLE (
    date DATE,
    close NUMERIC,
    sma NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        timestamp::date,
        p.close,
        ROUND(AVG(p.close) OVER (ORDER BY timestamp ROWS BETWEEN period - 1 PRECEDING AND CURRENT ROW)::numeric, 2) as sma
    FROM price_data p
    JOIN stocks s ON p.stock_id = s.id
    WHERE s.ticker = ticker_symbol
    ORDER BY timestamp DESC;
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT * FROM calculate_sma('AAPL', 20) LIMIT 30;
```

## Tips and Best Practices

1. **Use Indexes**: Ensure frequently queried columns have indexes
2. **Time Buckets**: Use TimescaleDB's `time_bucket()` for time-series aggregations
3. **Continuous Aggregates**: Create materialized views for frequently accessed aggregations
4. **Compression**: Enable compression on older chunks to save space
5. **Retention Policies**: Set up data retention policies to automatically drop old data
6. **Regular Maintenance**: Run VACUUM and ANALYZE regularly
7. **Monitor Performance**: Check cache hit ratio and slow queries regularly
8. **Backup Regularly**: Set up automated backups
9. **Use Prepared Statements**: For better performance in application code
10. **Connection Pooling**: Use pgbouncer or application-level pooling

## Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/14/
- TimescaleDB Documentation: https://docs.timescale.com/
- psql Command Reference: https://www.postgresql.org/docs/14/app-psql.html
- SQL Tutorial: https://www.postgresql.org/docs/14/tutorial.html
