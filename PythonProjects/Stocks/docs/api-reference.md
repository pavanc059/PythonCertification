# API Reference

**Version:** 2.0  
**Last Updated:** 2024

This document provides a comprehensive reference for all public interfaces in the StockIQ platform.

## Table of Contents

- [Core Module](#core-module)
- [Data Module](#data-module)
- [Models Module](#models-module)
- [News Module](#news-module)
- [Analytics Module](#analytics-module)
- [Backtesting Module](#backtesting-module)
- [Trading Module](#trading-module)
- [UI Module](#ui-module)
- [Infrastructure Module](#infrastructure-module)

---

## Core Module

### `stockiq.core.validation`

Data validation and quality assurance utilities.

#### `ValidationResult`

**Class:** `ValidationResult`

Represents the result of a validation operation.

**Attributes:**
- `is_valid` (bool): Whether validation passed
- `errors` (List[str]): List of validation errors
- `warnings` (List[str]): List of validation warnings

**Example:**
```python
from stockiq.core.validation import validate_ticker

result = validate_ticker("AAPL")
if result.is_valid:
    print("Valid ticker")
else:
    print(f"Errors: {result.errors}")
```

#### `validate_ticker()`

**Function:** `validate_ticker(ticker: str) -> ValidationResult`

Validates a stock ticker symbol.

**Parameters:**
- `ticker` (str): Stock ticker symbol to validate

**Returns:**
- `ValidationResult`: Validation result with errors/warnings

**Raises:**
- `ValueError`: If ticker is empty or None


### `stockiq.core.prediction_log`

Tracks and manages prediction performance.

#### `PredictionLog`

**Class:** `PredictionLog`

Manages prediction logging and performance tracking.

**Methods:**

##### `log_prediction()`

**Method:** `log_prediction(ticker: str, prediction: float, confidence: float, timestamp: datetime) -> str`

Logs a new prediction.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `prediction` (float): Predicted price or direction
- `confidence` (float): Confidence score (0-1)
- `timestamp` (datetime): Prediction timestamp

**Returns:**
- `str`: Prediction ID

**Example:**
```python
from stockiq.core.prediction_log import PredictionLog
from datetime import datetime

log = PredictionLog()
pred_id = log.log_prediction(
    ticker="AAPL",
    prediction=175.50,
    confidence=0.85,
    timestamp=datetime.now()
)
```

##### `get_accuracy()`

**Method:** `get_accuracy(ticker: Optional[str] = None, days: int = 30) -> float`

Calculates prediction accuracy.

**Parameters:**
- `ticker` (Optional[str]): Ticker to filter by (None for all)
- `days` (int): Number of days to look back

**Returns:**
- `float`: Accuracy percentage (0-100)

---

## Data Module

### `stockiq.data.collectors.market`

Market data collection from multiple sources.


#### `MarketDataCollector`

**Class:** `MarketDataCollector`

Collects real-time and historical market data.

**Methods:**

##### `get_realtime_price()`

**Method:** `get_realtime_price(ticker: str) -> Price`

Gets current market price for a ticker.

**Parameters:**
- `ticker` (str): Stock ticker symbol

**Returns:**
- `Price`: Current price data

**Raises:**
- `DataCollectionError`: If data retrieval fails
- `RateLimitError`: If rate limit is exceeded

**Example:**
```python
from stockiq.data.collectors.market import MarketDataCollector

collector = MarketDataCollector()
price = collector.get_realtime_price("AAPL")
print(f"Current price: ${price.price}")
```

##### `get_historical_data()`

**Method:** `get_historical_data(ticker: str, start: date, end: date, interval: str = '1d') -> DataFrame`

Gets historical OHLCV data.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `start` (date): Start date
- `end` (date): End date  
- `interval` (str): Data interval ('1d', '1h', '5m', etc.)

**Returns:**
- `DataFrame`: Historical OHLCV data with columns ['open', 'high', 'low', 'close', 'volume']

**Example:**
```python
from datetime import date, timedelta

end_date = date.today()
start_date = end_date - timedelta(days=365)

data = collector.get_historical_data("AAPL", start_date, end_date)
print(data.head())
```


##### `stream_realtime_data()`

**Method:** `async stream_realtime_data(tickers: List[str]) -> AsyncIterator[Price]`

Streams real-time price updates via WebSocket.

**Parameters:**
- `tickers` (List[str]): List of ticker symbols to stream

**Yields:**
- `Price`: Real-time price updates

**Example:**
```python
import asyncio

async def monitor_prices():
    collector = MarketDataCollector()
    async for price in collector.stream_realtime_data(["AAPL", "TSLA", "MSFT"]):
        print(f"{price.ticker}: ${price.price}")

asyncio.run(monitor_prices())
```

### `stockiq.data.collectors.news`

News data collection and aggregation.

#### `NewsCollector`

**Class:** `NewsCollector`

Aggregates financial news from multiple sources.

**Methods:**

##### `collect_latest_news()`

**Method:** `collect_latest_news(limit: int = 100, sources: Optional[List[str]] = None) -> List[NewsArticle]`

Collects latest financial news.

**Parameters:**
- `limit` (int): Maximum number of articles to return
- `sources` (Optional[List[str]]): Filter by news sources

**Returns:**
- `List[NewsArticle]`: List of news articles

**Example:**
```python
from stockiq.data.collectors.news import NewsCollector

collector = NewsCollector()
news = collector.collect_latest_news(limit=10)
for article in news:
    print(f"{article.title} - {article.source}")
```


##### `collect_ticker_news()`

**Method:** `collect_ticker_news(ticker: str, hours: int = 24) -> List[NewsArticle]`

Collects news mentioning a specific ticker.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `hours` (int): Hours to look back

**Returns:**
- `List[NewsArticle]`: News articles mentioning the ticker

---

## Models Module

### `stockiq.models.ensemble.predictor`

Ensemble ML prediction models.

#### `EnsemblePredictor`

**Class:** `EnsemblePredictor`

Combines multiple ML models using stacking for improved predictions.

**Methods:**

##### `train()`

**Method:** `train(X: DataFrame, y: Series, validation_split: float = 0.2) -> None`

Trains all base models and meta-learner.

**Parameters:**
- `X` (DataFrame): Feature matrix
- `y` (Series): Target variable
- `validation_split` (float): Validation data proportion

**Example:**
```python
from stockiq.models.ensemble.predictor import EnsemblePredictor

predictor = EnsemblePredictor()
predictor.train(X_train, y_train)
```

##### `predict()`

**Method:** `predict(X: DataFrame) -> Prediction`

Generates ensemble prediction with confidence intervals.

**Parameters:**
- `X` (DataFrame): Feature matrix

**Returns:**
- `Prediction`: Prediction with confidence and explanation


### `stockiq.models.features`

Feature engineering for ML models.

#### `FeatureEngineer`

**Class:** `FeatureEngineer`

Creates technical indicators and derived features.

**Methods:**

##### `add_technical_indicators()`

**Method:** `add_technical_indicators(data: DataFrame) -> DataFrame`

Adds 20+ technical indicators to price data.

**Parameters:**
- `data` (DataFrame): OHLCV data

**Returns:**
- `DataFrame`: Data with technical indicators added

**Indicators Added:**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
- OBV (On-Balance Volume)
- Stochastic Oscillator
- And 14 more...

**Example:**
```python
from stockiq.models.features import FeatureEngineer

engineer = FeatureEngineer()
data_with_features = engineer.add_technical_indicators(ohlcv_data)
```

---

## News Module

### `stockiq.news.nlp.sentiment`

Sentiment analysis for financial news.

#### `SentimentAnalyzer`

**Class:** `SentimentAnalyzer`

Analyzes news sentiment using VADER and FinBERT.

**Methods:**

##### `analyze_sentiment()`

**Method:** `analyze_sentiment(text: str) -> SentimentScore`

Calculates sentiment score for text.

**Parameters:**
- `text` (str): Text to analyze

**Returns:**
- `SentimentScore`: Sentiment score with confidence

**Example:**
```python
from stockiq.news.nlp.sentiment import SentimentAnalyzer

analyzer = SentimentAnalyzer()
score = analyzer.analyze_sentiment("Apple reports record earnings")
print(f"Sentiment: {score.overall} (confidence: {score.confidence})")
```


### `stockiq.news.penny.scanner`

Penny stock scanner for sudden gains.

#### `PennyStockScanner`

**Class:** `PennyStockScanner`

Scans for penny stocks with sudden gains and momentum.

**Methods:**

##### `scan_intraday_gainers()`

**Method:** `scan_intraday_gainers(min_gain_pct: float = 20.0) -> List[PennyStock]`

Identifies penny stocks with intraday gains.

**Parameters:**
- `min_gain_pct` (float): Minimum gain percentage threshold

**Returns:**
- `List[PennyStock]`: List of penny stocks matching criteria

**Example:**
```python
from stockiq.news.penny.scanner import PennyStockScanner

scanner = PennyStockScanner()
gainers = scanner.scan_intraday_gainers(min_gain_pct=25.0)
for stock in gainers:
    print(f"{stock.ticker}: +{stock.price_change_pct}%")
```

---

## Analytics Module

### `stockiq.analytics.risk.analyzer`

Risk metrics and VaR calculations.

#### `RiskAnalyzer`

**Class:** `RiskAnalyzer`

Calculates comprehensive risk metrics.

**Methods:**

##### `calculate_var()`

**Method:** `calculate_var(returns: Series, confidence: float = 0.95, method: str = 'historical') -> float`

Calculates Value at Risk (VaR).

**Parameters:**
- `returns` (Series): Historical returns
- `confidence` (float): Confidence level (0.95 or 0.99)
- `method` (str): Calculation method ('historical', 'parametric', 'monte_carlo')

**Returns:**
- `float`: VaR as a positive number (e.g., 0.02 = 2% loss)

**Example:**
```python
from stockiq.analytics.risk.analyzer import RiskAnalyzer

analyzer = RiskAnalyzer()
var_95 = analyzer.calculate_var(returns, confidence=0.95)
print(f"95% VaR: {var_95 * 100:.2f}%")
```


### `stockiq.analytics.options.greeks`

Options Greeks calculations.

#### `OptionsAnalyzer`

**Class:** `OptionsAnalyzer`

Calculates options Greeks and implied volatility.

**Methods:**

##### `calculate_greeks()`

**Method:** `calculate_greeks(option_type: str, S: float, K: float, T: float, r: float, sigma: float) -> Greeks`

Calculates options Greeks.

**Parameters:**
- `option_type` (str): 'call' or 'put'
- `S` (float): Current stock price
- `K` (float): Strike price
- `T` (float): Time to expiration (years)
- `r` (float): Risk-free rate
- `sigma` (float): Volatility

**Returns:**
- `Greeks`: Object with delta, gamma, theta, vega, rho

**Example:**
```python
from stockiq.analytics.options.greeks import OptionsAnalyzer

analyzer = OptionsAnalyzer()
greeks = analyzer.calculate_greeks('call', S=100, K=105, T=0.25, r=0.05, sigma=0.3)
print(f"Delta: {greeks.delta:.4f}")
```

---

## Backtesting Module

### `stockiq.backtesting.engine`

Backtesting engine for strategy simulation.

#### `BacktestEngine`

**Class:** `BacktestEngine`

Simulates trading strategies with realistic execution.

**Methods:**

##### `run()`

**Method:** `run(strategy: Strategy, data: DataFrame, initial_capital: float = 100000) -> BacktestResult`

Runs a backtest simulation.

**Parameters:**
- `strategy` (Strategy): Trading strategy to test
- `data` (DataFrame): Historical price data
- `initial_capital` (float): Starting capital

**Returns:**
- `BacktestResult`: Performance metrics and equity curve

**Example:**
```python
from stockiq.backtesting.engine import BacktestEngine
from stockiq.backtesting.strategies import MomentumStrategy

engine = BacktestEngine()
strategy = MomentumStrategy(lookback=20)
result = engine.run(strategy, historical_data, initial_capital=100000)
print(f"Total Return: {result.total_return * 100:.2f}%")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```


---

## Trading Module

### `stockiq.trading.account`

Paper trading account management.

#### `TradingAccount`

**Class:** `TradingAccount`

Manages paper trading account with virtual cash.

**Methods:**

##### `place_order()`

**Method:** `place_order(ticker: str, quantity: int, order_type: str, side: str, limit_price: Optional[float] = None) -> Order`

Places a paper trading order.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `quantity` (int): Number of shares
- `order_type` (str): 'market', 'limit', 'stop', 'stop_limit'
- `side` (str): 'buy' or 'sell'
- `limit_price` (Optional[float]): Limit price for limit orders

**Returns:**
- `Order`: Placed order object

**Example:**
```python
from stockiq.trading.account import TradingAccount

account = TradingAccount(initial_capital=100000)
order = account.place_order(
    ticker="AAPL",
    quantity=10,
    order_type="limit",
    side="buy",
    limit_price=175.00
)
print(f"Order placed: {order.order_id}")
```

---

## Infrastructure Module

### `stockiq.infrastructure.cache`

Redis caching layer.

#### `CacheManager`

**Class:** `CacheManager`

Manages Redis cache operations.

**Methods:**

##### `get()`

**Method:** `get(key: str) -> Optional[Any]`

Retrieves value from cache.

**Parameters:**
- `key` (str): Cache key

**Returns:**
- `Optional[Any]`: Cached value or None if not found

##### `set()`

**Method:** `set(key: str, value: Any, ttl: int = 3600) -> bool`

Stores value in cache.

**Parameters:**
- `key` (str): Cache key
- `value` (Any): Value to cache
- `ttl` (int): Time to live in seconds

**Returns:**
- `bool`: True if successful

**Example:**
```python
from stockiq.infrastructure.cache import CacheManager

cache = CacheManager()
cache.set("AAPL:price", 175.50, ttl=60)
price = cache.get("AAPL:price")
```


### `stockiq.infrastructure.database`

Database connection and query utilities.

#### `Database`

**Class:** `Database`

PostgreSQL/TimescaleDB database interface.

**Methods:**

##### `execute_query()`

**Method:** `execute_query(query: str, params: Optional[Dict] = None) -> DataFrame`

Executes SQL query and returns results as DataFrame.

**Parameters:**
- `query` (str): SQL query
- `params` (Optional[Dict]): Query parameters

**Returns:**
- `DataFrame`: Query results

**Example:**
```python
from stockiq.infrastructure.database import Database

db = Database()
result = db.execute_query(
    "SELECT * FROM prices WHERE ticker = :ticker AND date >= :start_date",
    params={"ticker": "AAPL", "start_date": "2024-01-01"}
)
```

---

## Data Models

### Common Data Structures

#### `Price`

**Dataclass:** `Price`

Represents a stock price at a point in time.

**Attributes:**
- `ticker` (str): Stock ticker symbol
- `timestamp` (datetime): Price timestamp
- `price` (Decimal): Current price
- `volume` (int): Trading volume
- `bid` (Optional[Decimal]): Bid price
- `ask` (Optional[Decimal]): Ask price

#### `NewsArticle`

**Dataclass:** `NewsArticle`

Represents a financial news article.

**Attributes:**
- `id` (str): Article ID
- `title` (str): Article title
- `content` (str): Article content
- `source` (str): News source
- `published_at` (datetime): Publication timestamp
- `url` (str): Article URL
- `tickers` (List[str]): Mentioned tickers
- `category` (NewsCategory): Article category


#### `SentimentScore`

**Dataclass:** `SentimentScore`

Sentiment analysis result.

**Attributes:**
- `overall` (float): Overall sentiment (-1 to +1)
- `vader_score` (float): VADER sentiment score
- `finbert_score` (float): FinBERT sentiment score
- `confidence` (float): Confidence level (0-1)

#### `Prediction`

**Dataclass:** `Prediction`

ML model prediction result.

**Attributes:**
- `ticker` (str): Stock ticker
- `timestamp` (datetime): Prediction timestamp
- `prediction_type` (str): 'price', 'direction', 'return'
- `value` (float): Predicted value
- `confidence` (float): Confidence score (0-1)
- `lower_bound` (float): Lower confidence interval
- `upper_bound` (float): Upper confidence interval
- `features_importance` (Dict[str, float]): Feature contributions

---

## Error Handling

### Exception Classes

All StockIQ exceptions inherit from `StockIQException`.

#### `DataCollectionError`

**Exception:** `DataCollectionError`

Raised when data collection fails.

**Usage:**
```python
try:
    data = collector.get_realtime_price("INVALID")
except DataCollectionError as e:
    print(f"Failed to collect data: {e}")
```

#### `RateLimitError`

**Exception:** `RateLimitError`

Raised when API rate limit is exceeded.

**Attributes:**
- `retry_after` (int): Seconds until retry is allowed

#### `ValidationError`

**Exception:** `ValidationError`

Raised when input validation fails.

#### `ModelError`

**Exception:** `ModelError`

Raised when ML model operations fail.

---

## Configuration

### Environment Variables

Key environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | Required |
| `NEWSAPI_KEY` | NewsAPI.org API key | Required |
| `FINNHUB_API_KEY` | Finnhub.io API key | Required |
| `ALPHAVANTAGE_API_KEY` | Alpha Vantage API key | Optional |
| `LOG_LEVEL` | Logging level | INFO |
| `CACHE_TTL_DEFAULT` | Default cache TTL (seconds) | 3600 |

---

## Rate Limits

### API Rate Limits

| Service | Limit | Period |
|---------|-------|--------|
| Market Data (yfinance) | 2000 requests | Per hour |
| NewsAPI | 1000 requests | Per day |
| Finnhub | 60 requests | Per minute |
| Alpha Vantage | 5 requests | Per minute |

### Internal Rate Limits

The platform implements automatic rate limiting and retries with exponential backoff.

---

*For detailed examples and tutorials, see the [User Guide](user-guide.md) and [Developer Guide](developer-guide.md).*
