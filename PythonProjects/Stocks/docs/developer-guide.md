# Developer Guide

**Version:** 2.0  
**Last Updated:** 2024

This guide is for developers who want to contribute to StockIQ, extend its functionality, or understand its architecture.

## Table of Contents

- [Project Structure](#project-structure)
- [Development Environment Setup](#development-environment-setup)
- [Code Architecture](#code-architecture)
- [Adding New Data Sources](#adding-new-data-sources)
- [Creating Custom ML Models](#creating-custom-ml-models)
- [Extending the UI](#extending-the-ui)
- [Database Schema](#database-schema)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)
- [Contributing Guidelines](#contributing-guidelines)
- [Release Process](#release-process)

---

## Project Structure

```
stockiq/
├── core/                      # Core business logic
│   ├── __init__.py
│   ├── prediction_log.py     # Prediction tracking
│   └── validation.py         # Data validation
├── data/                      # Data collection
│   ├── collectors/
│   │   ├── market.py         # Market data collection
│   │   ├── news.py           # News collection
│   │   └── fundamentals.py   # Fundamental data
│   ├── processors/
│   │   ├── validator.py      # Data validation
│   │   ├── normalizer.py     # Data normalization
│   │   └── enricher.py       # Data enrichment
│   ├── streams/
│   │   ├── websocket.py      # WebSocket streaming
│   │   └── distributor.py    # Data distribution
│   ├── models.py             # Data models
│   └── tickers.py            # Ticker management
├── models/                    # Machine learning
│   ├── ensemble/
│   │   └── predictor.py      # Ensemble models
│   ├── deep/
│   │   ├── lstm.py           # LSTM networks
│   │   └── transformer.py    # Transformer models
│   ├── rl/
│   │   ├── environment.py    # RL trading environment
│   │   └── agents.py         # RL agents
│   ├── sentiment/
│   │   └── analyzer.py       # Sentiment analysis
│   ├── features.py           # Feature engineering
│   └── preprocessing.py      # Data preprocessing
├── news/                      # News analysis
│   ├── nlp/
│   │   ├── sentiment.py      # Sentiment analysis
│   │   ├── entities.py       # Entity extraction
│   │   ├── summarization.py  # Text summarization
│   │   └── categorization.py # News categorization
│   ├── impact/
│   │   ├── correlation.py    # News-price correlation
│   │   └── decay.py          # Impact decay analysis
│   ├── alerts/
│   │   ├── detector.py       # Alert detection
│   │   ├── prioritizer.py    # Alert prioritization
│   │   └── notifier.py       # Alert delivery
│   └── penny/
│       ├── scanner.py        # Penny stock scanner
│       ├── momentum.py       # Momentum calculation
│       └── risk.py           # Risk assessment
├── analytics/                 # Financial analytics
│   ├── options/
│   │   └── greeks.py         # Options Greeks
│   ├── risk/
│   │   └── analyzer.py       # Risk metrics
│   ├── factors/
│   │   └── analyzer.py       # Factor analysis
│   └── portfolio/
│       └── optimizer.py      # Portfolio optimization
├── backtesting/               # Backtesting engine
│   ├── engine.py             # Backtest engine
│   ├── orders.py             # Order types
│   ├── slippage.py           # Slippage models
│   └── performance.py        # Performance metrics
├── trading/                   # Paper trading
│   ├── account.py            # Trading account
│   ├── execution.py          # Order execution
│   └── portfolio.py          # Portfolio management
├── ui/                        # User interface
│   ├── dashboards/
│   │   ├── daily_brief.py    # Daily brief dashboard
│   │   └── penny_stocks.py   # Penny stock dashboard
│   ├── components/
│   │   ├── charts.py         # Chart components
│   │   └── tables.py         # Table components
│   └── screeners/
│       └── builder.py        # Screener builder
└── infrastructure/            # Infrastructure
    ├── database.py           # Database interface
    ├── cache.py              # Redis cache
    ├── tasks.py              # Celery tasks
    ├── security.py           # Security utilities
    └── config.py             # Configuration
```


---

## Development Environment Setup

### Prerequisites

- Python 3.8 or higher (3.12 recommended)
- PostgreSQL 14+ with TimescaleDB extension
- Redis 7.0+
- Git 2.30+
- VS Code or PyCharm (recommended)

### Step-by-Step Setup

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/stockiq.git
cd stockiq
```

2. **Create virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# spaCy language model
python -m spacy download en_core_web_sm

# FinBERT tokenizer
python download_finbert_tokenizer.py
```

4. **Set up environment variables**

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
DATABASE_URL=postgresql://stockiq:password@localhost:5432/stockiq
REDIS_URL=redis://localhost:6379/0
NEWSAPI_KEY=your_key
FINNHUB_API_KEY=your_key
LOG_LEVEL=DEBUG
```

5. **Start infrastructure services**

```bash
# Start PostgreSQL and Redis
docker-compose up -d timescaledb redis

# Or start locally if you have them installed
pg_ctl start
redis-server
```

6. **Initialize database**

```bash
python scripts/init_db.py
```

7. **Start Celery worker (in separate terminal)**

```bash
celery -A stockiq.infrastructure.tasks worker --loglevel=info
```

8. **Start Celery Beat (in separate terminal)**

```bash
celery -A stockiq.infrastructure.tasks beat --loglevel=info
```

9. **Run the application**

```bash
# Web interface
streamlit run app.py

# CLI
python stock_analyzer.py AAPL
```

### IDE Configuration

#### VS Code

Install recommended extensions:
- Python
- Pylance
- Python Test Explorer
- Python Docstring Generator
- GitLens

**Settings (.vscode/settings.json):**

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.rulers": [88],
    "editor.tabSize": 4
  }
}
```


---

## Code Architecture

### Design Patterns

#### 1. Layered Architecture

The application follows strict layering:

```
Presentation (UI) → Application (Core) → Domain (Data/Models/News) → Infrastructure (DB/Cache)
```

**Rules:**
- Higher layers can depend on lower layers
- Lower layers cannot depend on higher layers
- Each layer has single responsibility

#### 2. Dependency Injection

Services receive dependencies via constructor:

```python
class NewsCollector:
    def __init__(self, cache: CacheManager, db: Database):
        self.cache = cache
        self.db = db
```

#### 3. Repository Pattern

Data access abstracted behind repositories:

```python
class PriceRepository:
    def __init__(self, db: Database):
        self.db = db
    
    def get_latest_price(self, ticker: str) -> Price:
        # Database query logic
        pass
    
    def save_price(self, price: Price) -> None:
        # Save logic
        pass
```

#### 4. Factory Pattern

Complex object creation handled by factories:

```python
class CollectorFactory:
    @staticmethod
    def create_collector(source: str) -> DataCollector:
        if source == "market":
            return MarketDataCollector()
        elif source == "news":
            return NewsCollector()
        # ...
```

#### 5. Strategy Pattern

Algorithms encapsulated as strategies:

```python
class SlippageStrategy(ABC):
    @abstractmethod
    def calculate_slippage(self, order: Order) -> float:
        pass

class FixedSlippage(SlippageStrategy):
    def calculate_slippage(self, order: Order) -> float:
        return order.quantity * 0.001  # 0.1%
```

### Key Architectural Principles

**1. Separation of Concerns**
- Data collection separate from analysis
- Business logic separate from UI
- Infrastructure separate from domain logic

**2. Single Responsibility**
- Each class has one primary responsibility
- Functions do one thing well
- Modules are cohesive

**3. Dependency Inversion**
- Depend on abstractions, not implementations
- Use interfaces/protocols for dependencies
- Enable testing and flexibility

**4. DRY (Don't Repeat Yourself)**
- Common logic extracted to utilities
- Code reuse through composition
- Consistent patterns across codebase

**5. Error Handling**
- Explicit error handling at boundaries
- Custom exceptions for domain errors
- Graceful degradation when possible


---

## Adding New Data Sources

### Step 1: Create Collector Class

**File:** `stockiq/data/collectors/my_source.py`

```python
from typing import List, Optional
from datetime import datetime
import requests
from stockiq.data.models import Price, NewsArticle
from stockiq.infrastructure.rate_limiter import RateLimiter
from stockiq.infrastructure.cache import CacheManager

class MySourceCollector:
    """Collects data from MySource API"""
    
    def __init__(
        self,
        api_key: str,
        cache: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        self.api_key = api_key
        self.cache = cache or CacheManager()
        self.rate_limiter = rate_limiter or RateLimiter(
            max_requests=100,
            time_window=60  # per minute
        )
        self.base_url = "https://api.mysource.com/v1"
    
    def get_latest_price(self, ticker: str) -> Price:
        """Get current price for ticker"""
        # Check cache first
        cache_key = f"price:{ticker}"
        cached = self.cache.get(cache_key)
        if cached:
            return Price(**cached)
        
        # Rate limit
        self.rate_limiter.acquire()
        
        # API call
        response = requests.get(
            f"{self.base_url}/quote/{ticker}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        response.raise_for_status()
        data = response.json()
        
        # Parse response
        price = Price(
            ticker=ticker,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            price=float(data["price"]),
            volume=int(data["volume"]),
            bid=float(data.get("bid")),
            ask=float(data.get("ask"))
        )
        
        # Cache result
        self.cache.set(cache_key, price.dict(), ttl=60)
        
        return price
```

### Step 2: Add Configuration

**File:** `stockiq/infrastructure/config.py`

```python
class Config:
    # ... existing config ...
    
    # MySource configuration
    MYSOURCE_API_KEY = os.getenv("MYSOURCE_API_KEY")
    MYSOURCE_RATE_LIMIT = int(os.getenv("MYSOURCE_RATE_LIMIT", "100"))
```

### Step 3: Register in Factory

**File:** `stockiq/data/collectors/__init__.py`

```python
from .my_source import MySourceCollector

class CollectorFactory:
    @staticmethod
    def create_collector(source: str):
        if source == "my_source":
            return MySourceCollector(
                api_key=Config.MYSOURCE_API_KEY
            )
        # ... existing collectors ...
```

### Step 4: Add Tests

**File:** `tests/test_my_source_collector.py`

```python
import pytest
from stockiq.data.collectors.my_source import MySourceCollector

@pytest.fixture
def collector():
    return MySourceCollector(api_key="test_key")

def test_get_latest_price(collector):
    price = collector.get_latest_price("AAPL")
    assert price.ticker == "AAPL"
    assert price.price > 0
    assert price.volume > 0
```

### Step 5: Update Documentation

Add to `docs/api-reference.md`:

```markdown
### `stockiq.data.collectors.my_source`

MySource data collection.

#### `MySourceCollector`

Collects data from MySource API.
...
```


---

## Creating Custom ML Models

### Step 1: Define Model Class

**File:** `stockiq/models/custom/my_model.py`

```python
from typing import Dict, List
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from stockiq.models.preprocessing import DataPreprocessor
from stockiq.models.features import FeatureEngineer

class MyCustomModel(BaseEstimator):
    """Custom ML model for stock prediction"""
    
    def __init__(
        self,
        lookback_period: int = 60,
        prediction_horizon: int = 1,
        feature_engineer: FeatureEngineer = None
    ):
        self.lookback_period = lookback_period
        self.prediction_horizon = prediction_horizon
        self.feature_engineer = feature_engineer or FeatureEngineer()
        self.model = None
    
    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'MyCustomModel':
        """Train the model"""
        # Feature engineering
        X_features = self.feature_engineer.add_technical_indicators(X)
        X_features = self.feature_engineer.add_lag_features(
            X_features,
            lags=self.lookback_period
        )
        
        # Your model training logic here
        # self.model = YourModel()
        # self.model.fit(X_features, y)
        
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions"""
        X_features = self.feature_engineer.add_technical_indicators(X)
        X_features = self.feature_engineer.add_lag_features(
            X_features,
            lags=self.lookback_period
        )
        
        predictions = self.model.predict(X_features)
        return predictions
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Generate prediction probabilities"""
        if hasattr(self.model, 'predict_proba'):
            X_features = self.feature_engineer.add_technical_indicators(X)
            return self.model.predict_proba(X_features)
        else:
            raise NotImplementedError("Model doesn't support probability predictions")
```

### Step 2: Add to Ensemble

**File:** `stockiq/models/ensemble/predictor.py`

```python
from stockiq.models.custom.my_model import MyCustomModel

class EnsemblePredictor:
    def __init__(self):
        self.base_models = [
            RandomForestModel(),
            XGBoostModel(),
            MyCustomModel(),  # Add your model
        ]
        self.meta_learner = None
```

### Step 3: Add Configuration

```python
# In config
ML_MODELS = {
    "ensemble": ["rf", "xgb", "my_model"],
    "my_model_params": {
        "lookback_period": 60,
        "prediction_horizon": 1
    }
}
```

### Step 4: Write Tests

**File:** `tests/test_my_custom_model.py`

```python
import pytest
import pandas as pd
from stockiq.models.custom.my_model import MyCustomModel

@pytest.fixture
def sample_data():
    # Create sample OHLCV data
    dates = pd.date_range('2020-01-01', periods=100)
    data = pd.DataFrame({
        'date': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 100)
    })
    return data

def test_model_training(sample_data):
    model = MyCustomModel()
    X = sample_data[['open', 'high', 'low', 'close', 'volume']]
    y = sample_data['close'].shift(-1).dropna()
    X = X[:-1]
    
    model.fit(X, y)
    assert model.model is not None

def test_model_prediction(sample_data):
    model = MyCustomModel()
    X = sample_data[['open', 'high', 'low', 'close', 'volume']][:-10]
    y = sample_data['close'].shift(-1)[:-10].dropna()
    X = X[:-1]
    
    model.fit(X, y)
    
    X_test = sample_data[['open', 'high', 'low', 'close', 'volume']][-10:]
    predictions = model.predict(X_test)
    
    assert len(predictions) == 10
    assert all(predictions > 0)  # Prices should be positive
```


---

## Extending the UI

### Adding a New Dashboard Page

**File:** `stockiq/ui/dashboards/my_dashboard.py`

```python
import streamlit as st
import plotly.graph_objects as go
from stockiq.data.collectors.market import MarketDataCollector
from stockiq.ui.components.charts import create_candlestick_chart

def render_my_dashboard():
    """Render custom dashboard page"""
    st.title("My Custom Dashboard")
    
    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        selected_tickers = st.multiselect(
            "Select Tickers",
            ["AAPL", "TSLA", "MSFT", "GOOGL"],
            default=["AAPL"]
        )
        timeframe = st.selectbox(
            "Timeframe",
            ["1D", "1W", "1M", "3M", "1Y"],
            index=2
        )
    
    # Main content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Price Chart")
        if selected_tickers:
            collector = MarketDataCollector()
            data = collector.get_historical_data(
                selected_tickers[0],
                start_date=get_start_date(timeframe),
                end_date=date.today()
            )
            chart = create_candlestick_chart(data)
            st.plotly_chart(chart, use_container_width=True)
    
    with col2:
        st.subheader("Statistics")
        if selected_tickers:
            for ticker in selected_tickers:
                price = collector.get_realtime_price(ticker)
                st.metric(
                    label=ticker,
                    value=f"${price.price:.2f}",
                    delta=f"{price.change_pct:.2f}%"
                )
```

### Register Dashboard in Main App

**File:** `app.py`

```python
from stockiq.ui.dashboards.my_dashboard import render_my_dashboard

# Navigation
page = st.sidebar.selectbox(
    "Navigate",
    [
        "Daily Brief",
        "Markets",
        "My Dashboard",  # Add your dashboard
        # ... other pages
    ]
)

# Route to page
if page == "My Dashboard":
    render_my_dashboard()
```

### Creating Reusable Components

**File:** `stockiq/ui/components/my_component.py`

```python
import streamlit as st
import plotly.graph_objects as go

def render_price_card(ticker: str, price: float, change_pct: float):
    """Reusable price card component"""
    color = "green" if change_pct > 0 else "red"
    arrow = "↑" if change_pct > 0 else "↓"
    
    st.markdown(f"""
    <div style="
        padding: 20px;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
        <h3 style="margin: 0;">{ticker}</h3>
        <h2 style="margin: 10px 0;">${price:.2f}</h2>
        <p style="margin: 0; color: {color};">
            {arrow} {abs(change_pct):.2f}%
        </p>
    </div>
    """, unsafe_allow_html=True)

def create_custom_chart(data):
    """Create custom Plotly chart"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data['date'],
        y=data['close'],
        mode='lines',
        name='Price',
        line=dict(color='#667eea', width=2)
    ))
    
    fig.update_layout(
        template='plotly_dark',
        hovermode='x unified',
        showlegend=True,
        height=400
    )
    
    return fig
```


---

## Database Schema

### Core Tables

#### prices

Stores historical and real-time price data (TimescaleDB hypertable).

```sql
CREATE TABLE prices (
    id BIGSERIAL,
    ticker VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(12, 4),
    high NUMERIC(12, 4),
    low NUMERIC(12, 4),
    close NUMERIC(12, 4) NOT NULL,
    volume BIGINT,
    PRIMARY KEY (ticker, timestamp)
);

-- Convert to hypertable
SELECT create_hypertable('prices', 'timestamp');

-- Indexes
CREATE INDEX idx_prices_ticker ON prices (ticker, timestamp DESC);
CREATE INDEX idx_prices_timestamp ON prices (timestamp DESC);
```

#### news_articles

Stores news articles with sentiment analysis.

```sql
CREATE TABLE news_articles (
    id VARCHAR(255) PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    source VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL,
    url TEXT,
    category VARCHAR(50),
    sentiment_overall NUMERIC(5, 4),
    sentiment_vader NUMERIC(5, 4),
    sentiment_finbert NUMERIC(5, 4),
    sentiment_confidence NUMERIC(5, 4),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_news_published ON news_articles (published_at DESC);
CREATE INDEX idx_news_sentiment ON news_articles (sentiment_overall);
```

#### predictions

Stores ML predictions and their outcomes.

```sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    prediction_timestamp TIMESTAMPTZ NOT NULL,
    prediction_type VARCHAR(20),  -- 'price', 'direction', 'return'
    predicted_value NUMERIC(12, 4),
    confidence NUMERIC(5, 4),
    lower_bound NUMERIC(12, 4),
    upper_bound NUMERIC(12, 4),
    model_version VARCHAR(50),
    actual_value NUMERIC(12, 4),
    is_correct BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_predictions_ticker ON predictions (ticker, prediction_timestamp DESC);
CREATE INDEX idx_predictions_accuracy ON predictions (is_correct) WHERE is_correct IS NOT NULL;
```

### Continuous Aggregates

Precomputed aggregations for performance.

```sql
-- Hourly price aggregates
CREATE MATERIALIZED VIEW prices_hourly
WITH (timescaledb.continuous) AS
SELECT
    ticker,
    time_bucket('1 hour', timestamp) AS hour,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM prices
GROUP BY ticker, hour;

-- Daily aggregates
CREATE MATERIALIZED VIEW prices_daily
WITH (timescaledb.continuous) AS
SELECT
    ticker,
    time_bucket('1 day', timestamp) AS day,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM prices
GROUP BY ticker, day;
```

### Adding a New Table

```python
# In migrations/add_my_table.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MyTable(Base):
    __tablename__ = 'my_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default='NOW()')

# Create table
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
```


---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_collectors.py
│   ├── test_models.py
│   └── test_analytics.py
├── integration/             # Integration tests
│   ├── test_data_pipeline.py
│   └── test_ml_pipeline.py
├── properties/              # Property-based tests
│   ├── test_feature_engineering.py
│   └── test_risk_metrics.py
└── conftest.py             # Pytest fixtures
```

### Unit Testing

**Example:** `tests/unit/test_market_collector.py`

```python
import pytest
from unittest.mock import Mock, patch
from stockiq.data.collectors.market import MarketDataCollector
from stockiq.data.models import Price

@pytest.fixture
def collector():
    cache = Mock()
    rate_limiter = Mock()
    return MarketDataCollector(cache=cache, rate_limiter=rate_limiter)

def test_get_realtime_price_from_cache(collector):
    """Test that cached prices are returned"""
    cached_price = {
        "ticker": "AAPL",
        "price": 175.50,
        "timestamp": "2024-01-15T10:30:00Z"
    }
    collector.cache.get.return_value = cached_price
    
    price = collector.get_realtime_price("AAPL")
    
    assert price.ticker == "AAPL"
    assert price.price == 175.50
    collector.cache.get.assert_called_once()

@patch('requests.get')
def test_get_realtime_price_api_call(mock_get, collector):
    """Test API call when cache misses"""
    collector.cache.get.return_value = None
    mock_get.return_value.json.return_value = {
        "ticker": "AAPL",
        "price": 175.50,
        "timestamp": "2024-01-15T10:30:00Z",
        "volume": 1000000
    }
    
    price = collector.get_realtime_price("AAPL")
    
    assert price.ticker == "AAPL"
    assert price.price == 175.50
    collector.rate_limiter.acquire.assert_called_once()
    mock_get.assert_called_once()
```

### Integration Testing

**Example:** `tests/integration/test_data_pipeline.py`

```python
import pytest
from datetime import datetime, timedelta
from stockiq.data.collectors.market import MarketDataCollector
from stockiq.infrastructure.database import Database
from stockiq.infrastructure.cache import CacheManager

@pytest.fixture
def setup_infrastructure():
    db = Database()
    cache = CacheManager()
    return db, cache

def test_price_collection_pipeline(setup_infrastructure):
    """Test end-to-end price collection and storage"""
    db, cache = setup_infrastructure
    collector = MarketDataCollector(cache=cache)
    
    # Collect price
    price = collector.get_realtime_price("AAPL")
    
    # Store in database
    db.execute_query(
        """
        INSERT INTO prices (ticker, timestamp, close, volume)
        VALUES (:ticker, :timestamp, :close, :volume)
        """,
        params={
            "ticker": price.ticker,
            "timestamp": price.timestamp,
            "close": price.price,
            "volume": price.volume
        }
    )
    
    # Verify storage
    result = db.execute_query(
        "SELECT * FROM prices WHERE ticker = :ticker ORDER BY timestamp DESC LIMIT 1",
        params={"ticker": "AAPL"}
    )
    
    assert len(result) == 1
    assert result.iloc[0]["ticker"] == "AAPL"
    assert result.iloc[0]["close"] == price.price
```


### Property-Based Testing

Using Hypothesis for property-based tests.

**Example:** `tests/properties/test_risk_metrics.py`

```python
import pytest
from hypothesis import given, strategies as st
import numpy as np
from stockiq.analytics.risk.analyzer import RiskAnalyzer

@given(
    returns=st.lists(
        st.floats(min_value=-0.1, max_value=0.1),
        min_size=100,
        max_size=500
    )
)
def test_var_is_positive(returns):
    """VaR should always be a positive number"""
    analyzer = RiskAnalyzer()
    var = analyzer.calculate_var(pd.Series(returns))
    assert var >= 0

@given(
    returns=st.lists(
        st.floats(min_value=-0.1, max_value=0.1),
        min_size=100,
        max_size=500
    )
)
def test_cvar_greater_than_var(returns):
    """CVaR should always be greater than or equal to VaR"""
    analyzer = RiskAnalyzer()
    var = analyzer.calculate_var(pd.Series(returns))
    cvar = analyzer.calculate_cvar(pd.Series(returns))
    assert cvar >= var
```

### Test Coverage

Aim for >80% code coverage:

```bash
# Run tests with coverage
pytest --cov=stockiq --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html
```

---

## Code Style

### Python Style Guide

Follow PEP 8 with these specifics:

**Line Length:** 88 characters (Black default)

**Imports:**
```python
# Standard library
import os
from datetime import datetime, timedelta

# Third-party
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# Local
from stockiq.data.models import Price
from stockiq.infrastructure.cache import CacheManager
```

**Type Hints:**
```python
from typing import List, Optional, Dict, Any

def process_prices(
    prices: List[Price],
    cache: Optional[CacheManager] = None
) -> Dict[str, Any]:
    """Process list of prices and return statistics"""
    ...
```

**Docstrings (Google Style):**
```python
def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        prices: Series of closing prices
        period: RSI period (default: 14)
        
    Returns:
        Series of RSI values (0-100)
        
    Raises:
        ValueError: If period < 2 or prices is empty
        
    Example:
        >>> prices = pd.Series([100, 102, 101, 103, 105])
        >>> rsi = calculate_rsi(prices)
    """
    if period < 2:
        raise ValueError("Period must be >= 2")
    ...
```

### Code Formatting

Use Black for automatic formatting:

```bash
# Format single file
black stockiq/data/collectors/market.py

# Format entire project
black stockiq/ tests/

# Check without modifying
black --check stockiq/
```

### Linting

Use flake8 for linting:

```bash
# Run flake8
flake8 stockiq/ tests/

# With configuration (.flake8)
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv
```

### Type Checking

Use mypy for type checking:

```bash
# Run mypy
mypy stockiq/

# Configuration (mypy.ini)
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```


---

## Contributing Guidelines

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork:**
   ```bash
   git clone https://github.com/yourusername/stockiq.git
   cd stockiq
   ```
3. **Create a feature branch:**
   ```bash
   git checkout -b feature/my-new-feature
   ```

### Development Workflow

1. **Make your changes**
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation

2. **Run tests:**
   ```bash
   pytest
   ```

3. **Check code quality:**
   ```bash
   black stockiq/ tests/
   flake8 stockiq/ tests/
   mypy stockiq/
   ```

4. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

   **Commit Message Format:**
   ```
   <type>: <description>
   
   [optional body]
   
   [optional footer]
   ```
   
   **Types:**
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation changes
   - `style`: Code style changes (formatting)
   - `refactor`: Code refactoring
   - `test`: Adding or updating tests
   - `chore`: Maintenance tasks

5. **Push to your fork:**
   ```bash
   git push origin feature/my-new-feature
   ```

6. **Create Pull Request** on GitHub

### Pull Request Guidelines

**PR Title Format:**
```
[Type] Brief description
```

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- List key changes
- Made to the codebase

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] No new warnings
```

### Code Review Process

1. **Automated Checks:**
   - Tests must pass
   - Code coverage >= 80%
   - Linting must pass
   - Type checking must pass

2. **Manual Review:**
   - At least 1 approval required
   - Address all review comments
   - Keep PR scope focused

3. **Merge:**
   - Squash and merge preferred
   - Delete branch after merge

### Reporting Bugs

Use GitHub Issues with this template:

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: 
- Python version:
- StockIQ version:

## Logs
Paste relevant logs

## Screenshots
Add if applicable
```

### Feature Requests

```markdown
## Feature Description
Clear description of proposed feature

## Use Case
Who would benefit and how?

## Proposed Solution
How could this be implemented?

## Alternatives Considered
Other approaches considered

## Additional Context
Any other relevant information
```


---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 2.1.0)
- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes

### Release Checklist

1. **Update Version Number**
   ```python
   # stockiq/__init__.py
   __version__ = "2.1.0"
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [2.1.0] - 2024-01-15
   
   ### Added
   - New penny stock dashboard
   - Real-time WebSocket streaming
   
   ### Changed
   - Improved prediction accuracy
   - Updated UI components
   
   ### Fixed
   - Fixed cache invalidation bug
   - Corrected VaR calculation
   ```

3. **Run Full Test Suite**
   ```bash
   pytest tests/ --cov=stockiq
   pytest tests/integration/
   pytest tests/properties/
   ```

4. **Build Documentation**
   ```bash
   # Update all documentation
   # Generate API docs if using sphinx
   ```

5. **Create Git Tag**
   ```bash
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin v2.1.0
   ```

6. **Build Docker Images**
   ```bash
   docker build -t stockiq:2.1.0 .
   docker build -t stockiq:latest .
   ```

7. **Push to Container Registry**
   ```bash
   docker tag stockiq:2.1.0 ghcr.io/yourusername/stockiq:2.1.0
   docker push ghcr.io/yourusername/stockiq:2.1.0
   docker push ghcr.io/yourusername/stockiq:latest
   ```

8. **Create GitHub Release**
   - Go to GitHub → Releases → New Release
   - Select tag v2.1.0
   - Add release notes from CHANGELOG
   - Attach any binaries if applicable

9. **Announce Release**
   - Update README with new version
   - Post announcement in discussions
   - Notify users via mailing list (if applicable)

### Hotfix Process

For critical bugs in production:

1. **Create hotfix branch from main:**
   ```bash
   git checkout main
   git checkout -b hotfix/critical-bug
   ```

2. **Make fix and test thoroughly**

3. **Bump PATCH version:**
   ```python
   __version__ = "2.1.1"
   ```

4. **Fast-track merge to main**

5. **Release immediately**

---

## Additional Resources

### Documentation
- [API Reference](api-reference.md)
- [User Guide](user-guide.md)
- [Deployment Guide](deployment-guide.md)

### External Resources
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Redis Documentation](https://redis.io/documentation)
- [Celery Documentation](https://docs.celeryproject.org/)

### Community
- **GitHub:** https://github.com/yourusername/stockiq
- **Discussions:** https://github.com/yourusername/stockiq/discussions
- **Issues:** https://github.com/yourusername/stockiq/issues
- **Wiki:** https://github.com/yourusername/stockiq/wiki

### Getting Help

If you need help:
1. Check this documentation
2. Search existing GitHub issues
3. Ask in GitHub Discussions
4. Open a new issue with details

---

## Appendix: Common Tasks

### Adding a Celery Task

```python
# In stockiq/infrastructure/tasks.py
from celery import shared_task

@shared_task(name="my_custom_task")
def my_custom_task(param1: str, param2: int):
    """Custom background task"""
    # Task logic here
    return result

# Schedule in beat schedule
celery_app.conf.beat_schedule = {
    'my-task': {
        'task': 'my_custom_task',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
        'args': ('arg1', 123)
    }
}
```

### Adding a Cache Key Pattern

```python
# In stockiq/infrastructure/cache.py
class CacheKeys:
    PRICE = "price:{ticker}"
    NEWS = "news:{ticker}:{hours}"
    PREDICTION = "prediction:{ticker}:{date}"
    CUSTOM = "custom:{param1}:{param2}"

# Usage
cache.set(CacheKeys.PRICE.format(ticker="AAPL"), price_data, ttl=60)
```

### Adding a Database Migration

```bash
# Create migration file
alembic revision -m "add_my_table"

# Edit migration file in alembic/versions/
# Add upgrade() and downgrade() logic

# Run migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

*Thank you for contributing to StockIQ! Your contributions help make this platform better for everyone.*
