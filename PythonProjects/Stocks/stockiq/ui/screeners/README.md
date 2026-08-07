# Stock Screener System

A powerful, high-performance stock screening system with 26+ filter criteria, logical operators, persistent storage, and automated scheduling.

## Features

- **26+ Filter Criteria** across 9 categories (price, volume, technical, fundamental, sentiment, etc.)
- **Logical Operators**: AND, OR, NOT for complex boolean logic
- **Sub-5-Second Performance** across 5,000+ stocks using vectorized operations
- **Persistent Storage**: Save and reuse custom screeners
- **Automated Scheduling**: Schedule screeners to run at specific times
- **Pre-Built Screeners**: Value, Growth, Momentum, Dividend, Penny Stock templates
- **Fluent Builder API**: Intuitive screener construction

## Quick Start

### Basic Usage

```python
from stockiq.ui.screeners import ScreenerEngine
import pandas as pd

# Create engine with data source
def get_stock_data():
    # Return DataFrame with stock data
    return pd.DataFrame({...})

engine = ScreenerEngine(data_source=get_stock_data)

# Build and execute a screener
results = (engine.builder()
    .where("market_cap").greater_than(1_000_000_000)
    .and_where("pe_ratio").less_than(20)
    .and_where("dividend_yield").greater_than(2)
    .execute())

print(f"Found {len(results)} matching stocks")
```

### Save and Reuse

```python
# Build a screener
screener = (engine.builder()
    .with_name("Value Stocks")
    .with_description("Low P/E, high dividend stocks")
    .where("pe_ratio").less_than(15)
    .and_where("dividend_yield").greater_than(3)
    .build())

# Save it
engine.save_screener(screener)

# Load and execute later
saved_screener = engine.load_screener("Value Stocks")
results = engine.execute(saved_screener)
```

### Schedule Automatic Execution

```python
# Save a screener first
engine.save_screener(screener, name="Daily Growth Stocks")

# Schedule it for 8:00 AM on weekdays
schedule_id = engine.schedule_screener(
    screener_name="Daily Growth Stocks",
    schedule_time="08:00",
    frequency="weekdays",
    notify_on_results=True,
    result_limit=50
)

# Start the scheduler
engine.start_scheduler()

# Scheduler runs in background, checking every minute
```

### Use Pre-Built Screeners

```python
# Quick screen with pre-built screener
results = engine.quick_screen("value", limit=50)

# Available pre-built screeners
prebuilt = engine.list_prebuilt()
# ['value', 'growth', 'momentum', 'dividend', 'penny']
```

## Available Filter Criteria

### Price & Volume (5 criteria)
- `price` — Current stock price
- `price_change_pct` — Percentage price change
- `volume` — Current trading volume
- `avg_volume` — Average daily volume (30-day)
- `volume_ratio` — Current/Average volume

### Technical Indicators (4 criteria)
- `rsi` — Relative Strength Index (14)
- `macd_signal` — MACD signal (bullish/bearish)
- `sma_20` — Price vs 20-day SMA
- `sma_50` — Price vs 50-day SMA

### Fundamental Metrics (5 criteria)
- `market_cap` — Market capitalization
- `pe_ratio` — Price-to-Earnings ratio
- `pb_ratio` — Price-to-Book ratio
- `dividend_yield` — Dividend yield percentage
- `debt_to_equity` — Debt-to-Equity ratio

### Growth Metrics (2 criteria)
- `revenue_growth` — Year-over-year revenue growth
- `earnings_growth` — Year-over-year earnings growth

### Sentiment (2 criteria)
- `sentiment_score` — Overall sentiment (-1 to +1)
- `analyst_rating` — Analyst consensus rating

### Market (3 criteria)
- `sector` — Stock sector
- `industry` — Stock industry
- `exchange` — Stock exchange (NYSE, NASDAQ, etc.)

### Performance (3 criteria)
- `return_1w` — 1-week percentage return
- `return_1m` — 1-month percentage return
- `return_ytd` — Year-to-date percentage return

### Risk (2 criteria)
- `beta` — Stock beta (market correlation)
- `volatility` — 30-day volatility percentage

## Comparison Operators

- `equals(value)` / `not_equals(value)`
- `greater_than(value)` / `greater_than_or_equal(value)`
- `less_than(value)` / `less_than_or_equal(value)`
- `between(min, max)` — Range queries
- `in_list([values])` / `not_in_list([values])` — List membership
- `contains(text)` / `not_contains(text)` — String matching

## Logical Operators

### AND Logic (default)
```python
# All conditions must be true
screener = (builder
    .where("price").greater_than(50)
    .and_where("volume").greater_than(1_000_000)
    .and_where("rsi").less_than(70)
    .build())
```

### OR Logic
```python
# Any condition can be true
screener = (builder
    .with_operator(FilterOperator.OR)
    .where("sector").equals("Technology")
    .or_where("sector").equals("Healthcare")
    .build())
```

### NOT Logic
```python
# Negate a condition
screener = (builder
    .where("sector").not_in_list(["Finance", "Energy"])
    .build())
```

## Advanced Examples

### Complex Multi-Condition Screener
```python
screener = (engine.builder()
    .with_name("Quality Growth")
    .with_description("High-quality growth stocks")
    .where("market_cap").greater_than(10_000_000_000)
    .and_where("revenue_growth").greater_than(15)
    .and_where("earnings_growth").greater_than(10)
    .and_where("pe_ratio").between(15, 30)
    .and_where("debt_to_equity").less_than(1)
    .and_where("rsi").between(40, 70)
    .and_where("sentiment_score").greater_than(0)
    .build())

results = engine.execute(screener, limit=100)
```

### Sector-Specific Screener
```python
tech_screener = (engine.builder()
    .with_name("Tech Growth")
    .where("sector").equals("Technology")
    .and_where("market_cap").greater_than(5_000_000_000)
    .and_where("revenue_growth").greater_than(20)
    .and_where("beta").less_than(1.5)
    .build())
```

### Penny Stock Screener
```python
penny_screener = (engine.builder()
    .with_name("Penny Momentum")
    .where("price").less_than(5)
    .and_where("price_change_pct").greater_than(10)
    .and_where("volume_ratio").greater_than(2)
    .and_where("avg_volume").greater_than(50_000)
    .build())
```

### Multiple Screeners in Parallel
```python
# Execute multiple screeners at once
screeners = [
    engine.get_prebuilt("value"),
    engine.get_prebuilt("growth"),
    engine.get_prebuilt("momentum")
]

results_dict = engine.execute_batch(screeners)
# Returns: {'Value Stocks': DataFrame, 'Growth Stocks': DataFrame, ...}
```

## Scheduling Options

### Daily Execution
```python
engine.schedule_screener(
    screener_name="Daily Screener",
    schedule_time="08:00",
    frequency="daily"
)
```

### Weekdays Only
```python
engine.schedule_screener(
    screener_name="Weekday Screener",
    schedule_time="09:30",
    frequency="weekdays"
)
```

### Weekly Execution
```python
engine.schedule_screener(
    screener_name="Weekly Screener",
    schedule_time="08:00",
    frequency="weekly"
)
```

### One-Time Execution
```python
engine.schedule_screener(
    screener_name="One-Time Screener",
    schedule_time="15:00",
    frequency="once"
)
```

### With Notifications
```python
# Register callback for notifications
def notify_results(schedule, results):
    print(f"Screener {schedule.screener_name} found {len(results)} stocks")
    # Send email, webhook, etc.

engine.register_notification_callback(notify_results)

# Schedule with notifications
engine.schedule_screener(
    screener_name="Notifying Screener",
    schedule_time="08:00",
    frequency="daily",
    notify_on_results=True,
    notify_channels=["in-app", "email"],
    result_limit=50
)
```

## Performance

The screener system is optimized for high performance:

- **Vectorized operations** using pandas
- **Early exit optimization** for AND logic
- **Condition ordering** by restrictiveness
- **Cache layer** with 5-minute TTL
- **Batch processing** for multiple screeners

### Performance Benchmarks

| Dataset Size | Execution Time | Target |
|-------------|----------------|--------|
| 1,000 stocks | <0.5s | 5s |
| 5,000 stocks | <3s | 5s |
| 10,000 stocks | <5s | 5s |

## Storage

Screeners are stored as JSON files in `~/.stockiq/screeners/`:

```
~/.stockiq/
└── screeners/
    ├── Value_Stocks.json
    ├── Growth_Stocks.json
    └── My_Custom_Screener.json
```

Schedules are stored in `~/.stockiq/schedules/`:

```
~/.stockiq/
└── schedules/
    └── schedules.json
```

## Data Requirements

The screener expects a pandas DataFrame with these columns:

### Required Columns
- `ticker` (str)
- `price` (float)
- `market_cap` (float)
- `volume` (int)
- `avg_volume` (int)

### Optional Columns
Add any criteria you want to filter on:
- `pe_ratio`, `pb_ratio`, `dividend_yield`, etc.
- `rsi`, `macd_signal`, `sma_20`, etc.
- `sector`, `industry`, `exchange`
- `sentiment_score`, `analyst_rating`
- `return_1w`, `return_1m`, `return_ytd`
- `beta`, `volatility`

Missing columns will be skipped during filtering.

## API Reference

### ScreenerEngine

Main entry point for all screener operations.

```python
engine = ScreenerEngine(
    data_source=callable,      # Returns DataFrame with stock data
    storage_dir=str,            # Optional custom storage directory
    schedule_dir=str            # Optional custom schedule directory
)
```

**Methods:**
- `builder()` — Get ScreenerBuilder instance
- `execute(screener, stock_universe, limit)` — Execute a screener
- `save_screener(screener, name, overwrite)` — Save a screener
- `load_screener(name)` — Load a saved screener
- `schedule_screener(name, time, frequency, ...)` — Schedule execution
- `quick_screen(prebuilt_name, limit)` — Execute pre-built screener
- `start_scheduler()` / `stop_scheduler()` — Control scheduler thread

### ScreenerBuilder

Fluent API for building screeners.

```python
builder = ScreenerBuilder()

screener = (builder
    .with_name(name)
    .with_description(description)
    .where(criteria_name).operator(value)
    .and_where(criteria_name).operator(value)
    .build())
```

**Methods:**
- `with_name(name)` — Set screener name
- `with_description(description)` — Set description
- `where(criteria)` — Start new condition
- `and_where(criteria)` — Add AND condition
- `or_where(criteria)` — Add OR condition
- `equals(value)` — Equality comparison
- `greater_than(value)` — Greater than comparison
- `less_than(value)` — Less than comparison
- `between(min, max)` — Range comparison
- `in_list(values)` — List membership
- `build()` — Build CompositeFilter

## Troubleshooting

### Screener returns no results
- Check that data source returns non-empty DataFrame
- Verify column names match criteria names
- Relax filter conditions
- Check for NaN values in data

### Slow execution
- Reduce number of conditions
- Use more restrictive conditions first
- Clear cache: `engine.clear_cache()`
- Check data source performance

### Scheduler not running
- Ensure `engine.start_scheduler()` was called
- Check schedule is enabled
- Verify screener exists in storage
- Check system time matches schedule time

## License

Part of the Universal Stock Analyzer project.
