# Feature Engineering Module

**Status:** ✅ Implemented and Tested  
**Phase:** 0.4.1 - Feature Engineering  
**Requirements:** 3.6, 13.1-13.3

## Overview

The feature engineering module (`stockiq/models/features.py`) provides comprehensive feature calculation capabilities for the ML pipeline, including technical indicators, fundamental metrics, and sentiment features.

## Features Implemented

### Technical Indicators (29 features)

1. **Trend Indicators**
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence) with signal and histogram
   - Moving Averages: SMA 20, 50, 200
   - Exponential Moving Averages: EMA 12, 26

2. **Volatility Indicators**
   - Bollinger Bands (upper, middle, lower, width)
   - ATR (Average True Range)
   - Price volatility (20-day rolling standard deviation)

3. **Volume Indicators**
   - OBV (On-Balance Volume)
   - Volume moving average (20-day)
   - Volume ratio (current vs. average)

4. **Momentum Indicators**
   - Momentum (10-day price change)
   - Rate of Change (10-day percentage change)
   - Daily returns

5. **Derived Features**
   - Price position relative to SMAs (20, 50, 200)
   - Bollinger Band position
   - Price range and percentage range
   - Price-to-moving-average ratios

### Fundamental Features (22 features)

- **Valuation Ratios:** P/E, Forward P/E, P/B, P/S, PEG
- **Profitability Metrics:** ROE, ROA, Profit Margin, Operating Margin
- **Financial Health:** Debt-to-Equity, Current Ratio, Quick Ratio
- **Growth Metrics:** Revenue Growth, Earnings Growth
- **Dividend Metrics:** Dividend Yield, Payout Ratio
- **Market Metrics:** Market Cap, Enterprise Value, Beta, Book Value

### Sentiment Features (8 features - Placeholder)

- Average Sentiment Score
- Sentiment Trend
- News Volume
- Positive/Negative Ratios
- Sentiment Volatility
- Bullish/Bearish Mentions

**Note:** Sentiment features currently return placeholder values and will be integrated with the News Analyzer module (`stockiq.news`) in a later phase.

## API Reference

### Main Functions

#### `create_feature_matrix(ticker, lookback_days=90)`

Creates a comprehensive feature matrix combining all feature types.

**Parameters:**
- `ticker` (str): Stock ticker symbol (e.g., 'AAPL')
- `lookback_days` (int): Number of days of historical data (default: 90)

**Returns:**
- DataFrame with complete feature matrix (technical + fundamental + sentiment)

**Example:**
```python
from stockiq.models.features import create_feature_matrix

features = create_feature_matrix('AAPL', lookback_days=90)
print(features.shape)  # (90, 66)
print(features.columns)
```

#### `calculate_technical_features(price_data)`

Calculates all technical indicators from OHLCV data.

**Parameters:**
- `price_data` (DataFrame): DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']

**Returns:**
- DataFrame with original data plus 29 technical features

**Example:**
```python
import yfinance as yf
from stockiq.models.features import calculate_technical_features

# Get price data
stock = yf.Ticker('AAPL')
price_data = stock.history(period='1y')

# Calculate technical features
features = calculate_technical_features(price_data)
```

#### `calculate_fundamental_features(ticker)`

Extracts fundamental metrics from company financial data.

**Parameters:**
- `ticker` (str): Stock ticker symbol

**Returns:**
- Dictionary with 22 fundamental features

**Example:**
```python
from stockiq.models.features import calculate_fundamental_features

fundamentals = calculate_fundamental_features('MSFT')
print(f"P/E Ratio: {fundamentals['pe_ratio']:.2f}")
print(f"ROE: {fundamentals['roe']*100:.2f}%")
```

#### `calculate_sentiment_features(ticker, hours=24)`

Calculates sentiment features (placeholder implementation).

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `hours` (int): Number of hours to look back (default: 24)

**Returns:**
- Dictionary with 8 sentiment features

#### `create_feature_matrices(tickers, lookback_days=90)`

Batch processing for multiple tickers.

**Parameters:**
- `tickers` (list): List of stock ticker symbols
- `lookback_days` (int): Number of days of historical data

**Returns:**
- Dictionary mapping ticker to feature DataFrame

**Example:**
```python
from stockiq.models.features import create_feature_matrices

tickers = ['AAPL', 'GOOGL', 'MSFT']
features_dict = create_feature_matrices(tickers, lookback_days=90)

for ticker, features in features_dict.items():
    print(f"{ticker}: {features.shape}")
```

### Individual Indicator Functions

- `calculate_rsi(prices, period=14)` - RSI calculation
- `calculate_macd(prices, fast=12, slow=26, signal=9)` - MACD calculation
- `calculate_bollinger_bands(prices, period=20, std_dev=2.0)` - Bollinger Bands
- `calculate_atr(high, low, close, period=14)` - Average True Range
- `calculate_obv(close, volume)` - On-Balance Volume

## Data Handling

### Missing Value Strategy

1. **Technical Indicators:** Forward fill followed by backward fill
2. **Fundamental Features:** Forward fill (values don't change frequently)
3. **Sentiment Features:** Default values (0.0 for placeholders)

### Target Variables

The feature matrix includes two target variables for ML training:
- `target_return`: Next-day return percentage
- `target_direction`: Binary classification (1 = up, 0 = down)

## Testing

Comprehensive test suite with 23 tests covering:
- Individual technical indicator calculations
- Complete feature matrix creation
- Fundamental feature extraction
- Edge cases and error handling
- Data quality validation

**Run tests:**
```bash
cd Stocks
python -m pytest tests/test_features.py -v
```

## Example Usage

See `examples/feature_engineering_demo.py` for comprehensive demonstrations:

```bash
cd Stocks
python examples/feature_engineering_demo.py
```

## Integration Points

The feature engineering module is designed to integrate with:

1. **ML Prediction Models** (`stockiq.models.predictor`)
   - LSTM neural networks
   - Transformer models
   - Ensemble methods

2. **Backtesting Engine** (`stockiq.backtesting`)
   - Strategy simulation with historical features

3. **Real-Time Analysis Pipeline**
   - Streaming feature calculation
   - WebSocket integration

4. **Paper Trading System** (`stockiq.trading`)
   - Live feature calculation for trading decisions

5. **News Analyzer** (`stockiq.news`) - Future Integration
   - Sentiment feature calculation
   - News impact analysis

## Performance Considerations

- **Feature Calculation Time:** ~1-2 seconds for 90 days of data per stock
- **Memory Usage:** Efficient with pandas operations
- **Caching:** Future integration with Redis for computed features
- **Batch Processing:** Use `create_feature_matrices()` for multiple stocks

## Future Enhancements

1. **Sentiment Integration**
   - Connect with News Analyzer module
   - Real-time sentiment updates
   - Historical sentiment tracking

2. **Advanced Technical Indicators**
   - Ichimoku Cloud
   - Keltner Channels
   - Supertrend

3. **Alternative Data Features**
   - Insider trading indicators
   - Options flow metrics
   - Social media sentiment

4. **Performance Optimization**
   - Parallel processing for batch operations
   - Incremental feature updates
   - Feature caching with Redis

## Dependencies

- **pandas** (≥1.5.0): Data manipulation
- **numpy** (≥1.24.0): Numerical computing
- **yfinance** (≥0.2.18): Market data retrieval

## Validation

✅ All 23 unit tests passing  
✅ No linting errors or warnings  
✅ Integration tested with real market data  
✅ Example demos working correctly  
✅ Documentation complete  

## Related Documentation

- [Design Document](../../.kiro/specs/institutional-upgrade/design.md)
- [Requirements](../../.kiro/specs/institutional-upgrade/requirements.md)
- [Implementation Status](IMPLEMENTATION_STATUS.md)

---

**Last Updated:** June 17, 2026  
**Module Location:** `stockiq/models/features.py`  
**Test Location:** `tests/test_features.py`  
**Demo Location:** `examples/feature_engineering_demo.py`
