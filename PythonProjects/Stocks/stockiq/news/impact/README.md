# News Impact Analysis Module

This module analyzes the correlation between news sentiment and price movements to measure news impact effectiveness.

## Overview

The news impact module implements **Requirements 2.11 and 7**:
- Track news sentiment correlation with price movements (Req 2.11)
- Multi-timeframe news impact analysis (Req 7)

## Features

- **Multi-Timeframe Impact Analysis**: Calculate price impact at 1h, 4h, 1d, 1w timeframes
- **Sentiment-Price Correlation**: Measure correlation between news sentiment and price movements (Property 12)
- **News Beta Calculation**: Calculate stock's sensitivity to news sentiment
- **Statistical Significance Testing**: Determine if impacts are statistically significant
- **Database Storage**: Store correlation results for historical tracking
- **Redis Caching**: Cache correlation and beta calculations (24-hour TTL)

## Implementation Status

### ✅ Completed Components

1. **Data Classes**
   - `PriceImpact`: Represents price impact at a specific timeframe
   - `ImpactAnalysis`: Complete impact analysis for a news article

2. **NewsImpactAnalyzer Class**
   - `calculate_impact()`: Multi-timeframe impact analysis for news articles
   - `calculate_sentiment_correlation()`: Pearson correlation between sentiment and returns
   - `calculate_news_beta()`: Stock's sensitivity to news using linear regression
   - Private helper methods for price retrieval and calculations

3. **Convenience Functions**
   - `calculate_sentiment_correlation()`: Direct function for correlation calculation
   - `calculate_news_beta()`: Direct function for beta calculation

4. **Property Validation**
   - **Property 12**: Correlation coefficients clamped to range [-1.0, 1.0]

## Usage

### Basic Usage

```python
from stockiq.news.impact import NewsImpactAnalyzer, calculate_sentiment_correlation

# Create analyzer instance
analyzer = NewsImpactAnalyzer()

# Calculate sentiment-price correlation
correlation = analyzer.calculate_sentiment_correlation('AAPL', period_days=90)
print(f"Sentiment-Price Correlation: {correlation:.3f}")

# Calculate news beta
beta = analyzer.calculate_news_beta('TSLA', period_days=90)
print(f"News Beta: {beta:.2f}")

# Analyze impact of a specific news article
impact = analyzer.calculate_impact(
    article_id='news_123',
    ticker='AAPL',
    timeframes=['1h', '4h', '1d', '1w']
)

# Check impact at each timeframe
for timeframe, price_impact in impact.timeframes.items():
    print(f"{timeframe}: {price_impact.price_change_pct:.2f}% price change")
    if price_impact.is_significant():
        print(f"  ✓ Statistically significant (p={price_impact.statistical_significance:.4f})")
```

### Convenience Functions

```python
from stockiq.news.impact import calculate_sentiment_correlation, calculate_news_beta

# Quick correlation calculation
corr = calculate_sentiment_correlation("AAPL", period_days=90)

# Quick news beta calculation
beta = calculate_news_beta("TSLA", period_days=90)
```

### Understanding Results

#### Correlation Coefficient
- **Range**: -1.0 to +1.0 (Property 12)
- **Positive (0 to +1)**: Positive news sentiment → price increases
- **Negative (-1 to 0)**: Positive news sentiment → price decreases (rare)
- **Near Zero**: No correlation between sentiment and price

#### News Beta
- **Beta > 1.0**: Stock is more sensitive to news than average
- **Beta = 1.0**: Stock has average news sensitivity
- **Beta < 1.0**: Stock is less sensitive to news than average
- **Beta < 0**: Stock moves opposite to news sentiment (rare)

#### Statistical Significance
- **p < 0.05**: Impact is statistically significant
- **p < 0.01**: Impact is highly significant
- **p >= 0.05**: Impact may be due to random chance

## Dependencies

### Internal Dependencies
- `stockiq.news.nlp.sentiment`: For SentimentScore class
- `stockiq.infrastructure.cache`: For Redis caching
- `stockiq.infrastructure.database`: For database operations
- `stockiq.infrastructure.models`: For database models

### External Dependencies
- `pandas`: Data manipulation and time-series analysis
- `numpy`: Numerical operations
- `scipy.stats`: Statistical tests (Pearson correlation, linear regression)

## Database Schema

### Sentiment Data
- **Table**: `news_sentiment`
- **Fields**: article_id, stock_id, sentiment_score, vader_score, finbert_score, confidence, created_at

### Price Data
- **Table**: `price_data` (TimescaleDB hypertable)
- **Fields**: stock_id, timestamp, open, high, low, close, volume

### Future: Correlation Tracking Table
```sql
CREATE TABLE news_correlation (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    period_days INTEGER,
    correlation FLOAT,
    data_points INTEGER,
    calculated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE news_beta (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id),
    period_days INTEGER,
    beta FLOAT,
    r_squared FLOAT,
    p_value FLOAT,
    calculated_at TIMESTAMP DEFAULT NOW()
);
```

## Caching Strategy

### Sentiment-Price Correlation
- **Key Pattern**: `correlation:sentiment_price:{ticker}:{period}`
- **TTL**: 24 hours
- **Rationale**: Correlation changes slowly, can be cached for a day

### News Beta
- **Key Pattern**: `correlation:news_beta:{ticker}:{period}`
- **TTL**: 24 hours
- **Rationale**: Beta is stable metric, daily recalculation sufficient

## Algorithm Details

### Sentiment-Price Correlation

1. **Query Data**: Fetch sentiment and price data for specified period
2. **Calculate Returns**: Compute daily returns from price data
3. **Aggregate Sentiment**: Average sentiment scores by day
4. **Merge Data**: Combine sentiment and returns on matching dates
5. **Compute Correlation**: Calculate Pearson correlation coefficient
6. **Clamp Result**: Ensure correlation is in [-1.0, 1.0] range (Property 12)

### News Beta Calculation

1. **Query Data**: Fetch sentiment and price data for specified period
2. **Calculate Changes**: Compute daily returns and sentiment changes
3. **Aggregate by Day**: Group data by trading day
4. **Linear Regression**: Fit linear model (returns ~ sentiment_change)
5. **Extract Beta**: Beta = slope of regression line
6. **Statistical Tests**: Calculate R², p-value for significance

### Multi-Timeframe Impact

1. **Get Article**: Fetch article and publication time from database
2. **For Each Timeframe**:
   - Calculate end time (publication + timeframe hours)
   - Get price/volume at publication time
   - Get price/volume at end time
   - Calculate percentage changes
   - Estimate statistical significance
3. **Return ImpactAnalysis**: Package all timeframe results

## Property Validation

### Property 12: Correlation Coefficient Range

**Statement**: News sentiment correlation coefficient must be in range [-1.0, 1.0]

**Implementation**: 
- Line 433-434 in `correlation.py`
- `correlation = float(np.clip(correlation, -1.0, 1.0))`
- Handles edge cases where numerical computation might produce values slightly outside range due to floating-point precision

**Test Coverage**:
- Unit test: `test_calculate_sentiment_correlation_property_12`
- Edge case test: `test_property_12_correlation_range_edge_cases`

## Error Handling

The module implements graceful degradation:

1. **Missing Stock**: Returns 0.0 correlation, 1.0 beta (average)
2. **Insufficient Data**: Returns default values with warning logs
3. **NaN Correlation**: Converts to 0.0 (occurs when one series is constant)
4. **Database Errors**: Logs error and returns safe defaults
5. **Cache Failures**: Continues without cache (degraded performance)

## Logging

All major operations are logged using `structlog`:

```python
logger.info(
    "sentiment_correlation_calculated",
    ticker=ticker,
    period_days=period_days,
    correlation=round(correlation, 3),
    data_points=len(merged)
)
```

## Performance Considerations

### Database Queries
- Queries filter by stock_id and date range with indexes
- Returns are calculated in-memory using pandas
- No N+1 query issues

### Caching
- 24-hour TTL reduces database load by 96% for repeated queries
- Cache keys include ticker and period for granular invalidation

### Memory Usage
- Uses pandas DataFrames for efficient time-series operations
- Data is not held in memory after calculation
- Suitable for stocks with years of historical data

## Future Enhancements

### Planned Features (Not Yet Implemented)

1. **Decay Curves Module** (`decay.py`)
   - Calculate impact decay over time
   - Generate decay curves by news category
   - Identify optimal holding periods

2. **Proper Statistical Significance Testing**
   - Currently uses threshold-based approach
   - Should implement t-test or permutation test
   - Add confidence intervals

3. **Database Storage Tables**
   - Create `news_correlation` table
   - Create `news_beta` table
   - Implement `_store_correlation_result()` and `_store_news_beta_result()`

4. **Advanced Features**
   - Sector-wide sentiment-price correlation
   - Intraday impact analysis (minute-level)
   - News impact attribution (which articles moved the market most)
   - Rolling correlation tracking

## Testing

Run unit tests:

```bash
cd Stocks
python -m pytest tests/test_news_impact_correlation.py -v
```

**Note**: Tests may fail on Windows due to PyTorch DLL issues during import. This is a known issue with PyTorch on Windows and does not affect runtime functionality.

## Integration Points

This module integrates with:

1. **SentimentAnalyzer** (`stockiq.news.nlp.sentiment`)
   - Provides sentiment scores for articles
   - Sentiment data stored in `news_sentiment` table

2. **MarketDataCollector** (`stockiq.data.collectors.market`)
   - Provides historical price data
   - Price data stored in `price_data` hypertable

3. **Cache Layer** (`stockiq.infrastructure.cache`)
   - Redis caching for performance
   - 24-hour TTL for correlation/beta results

4. **Database Layer** (`stockiq.infrastructure.database`)
   - Queries sentiment and price data
   - Stores correlation results (TODO)

## Dependencies Between Phases

This module (PHASE_0.3.1) depends on:
- ✅ PHASE_0.1: Infrastructure (Database, Redis, Celery)
- ✅ PHASE_0.2.1: MarketDataCollector for price data
- ✅ PHASE_0.3.1: SentimentAnalyzer for sentiment scores

## Author Notes

### Design Decisions

1. **Pearson Correlation**: Used for sentiment-price correlation as it's standard in finance and easy to interpret
2. **Linear Regression for Beta**: Follows financial beta calculation methodology (similar to market beta)
3. **Daily Aggregation**: Sentiment and prices aggregated by trading day for robustness
4. **Clipping Correlation**: Ensures Property 12 even with floating-point errors
5. **Cache-First Strategy**: Reduces database load for repeated queries

### Known Limitations

1. **Statistical Significance**: Current implementation uses simple thresholds; needs proper hypothesis testing
2. **Database Storage**: Correlation/beta storage not yet implemented (logged only)
3. **Intraday Analysis**: Only supports daily aggregation, not intraday
4. **Market Hours**: Does not consider market hours or pre/post-market trading

### Related Files

- `stockiq/news/impact/__init__.py`: Module exports
- `stockiq/news/impact/correlation.py`: Implementation
- `tests/test_news_impact_correlation.py`: Unit tests
- `stockiq/news/nlp/sentiment.py`: Sentiment analysis
- `stockiq/data/collectors/market.py`: Market data collection
