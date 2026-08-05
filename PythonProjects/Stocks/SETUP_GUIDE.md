# Setup Guide - Phase 0.1.1 Complete! ✅

## What We've Built

**PHASE_0.1.1: Database Setup** is now complete with:

1. ✅ **Database Connection Management** (`stockiq/infrastructure/database.py`)
   - SQLAlchemy engine with connection pooling
   - Session management with context managers
   - Automatic connection health checks

2. ✅ **ORM Models** (`stockiq/infrastructure/models.py`)
   - 11 database tables with proper relationships
   - TimescaleDB hypertable support for time-series data
   - Comprehensive constraints and indexes
   - Tables created:
     - `stocks` - Stock information
     - `price_data` - Time-series price data (hypertable)
     - `news_articles` - News articles
     - `news_sentiment` - Sentiment analysis results
     - `daily_predictions` - ML predictions
     - `top_movers` - Daily gainers/losers
     - `penny_stock_momentum` - Penny stock tracking
     - `penny_stock_risk_metrics` - Risk analysis
     - `alerts` - User alerts
     - `user_watchlists` - User watchlists

3. ✅ **Initialization Scripts** (`scripts/`)
   - `init_db.py` - Full database setup with TimescaleDB
   - `manage_db.py` - Database management utility

## Quick Start

### 1. Install Dependencies

```bash
cd d:\workspace\projects\Stocks

# Activate virtual environment
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL with TimescaleDB

**Option A: Docker (Recommended)**
```bash
# Start PostgreSQL with TimescaleDB
docker run -d ^
  --name timescaledb ^
  -p 5432:5432 ^
  -e POSTGRES_PASSWORD=password ^
  -e POSTGRES_DB=stockiq ^
  timescale/timescaledb:latest-pg14

# Verify it's running
docker ps
```

**Option B: Native Installation**
1. Install PostgreSQL 14+ from https://www.postgresql.org/download/windows/
2. Install TimescaleDB from https://docs.timescale.com/install/latest/self-hosted/installation-windows/
3. Create database:
```sql
CREATE DATABASE stockiq;
```

### 3. Configure Environment

```bash
# Copy environment template
copy .env.example .env

# Edit .env file
notepad .env
```

**Minimum required settings:**
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/stockiq
REDIS_URL=redis://localhost:6379/0
```

### 4. Initialize Database

```bash
# Run initialization script
python scripts/init_db.py
```

**Expected output:**
```
✅ Database initialization completed successfully!

Next steps:
1. Verify tables: psql -d stockiq -c '\dt'
2. Check hypertables: psql -d stockiq -c 'SELECT * FROM timescaledb_information.hypertables;'
3. Start implementing Phase 0.1.2 - Redis Cache Setup
```

### 5. Verify Installation

```bash
# Check database status
python scripts/manage_db.py status
```

**Expected output:**
```
============================================================
DATABASE STATUS
============================================================

Database URL: localhost:5432/stockiq

1. Connection Status:
   ✅ Connected successfully

2. TimescaleDB Extension:
   ✅ TimescaleDB installed

3. Tables:
   Found 11 tables:
   - alerts
   - daily_predictions
   - news_articles
   - news_sentiment
   - penny_stock_momentum
   - penny_stock_risk_metrics
   - price_data
   - stocks
   - top_movers
   - user_watchlists

4. Row Counts:
   alerts: 0
   daily_predictions: 0
   news_articles: 0
   news_sentiment: 0
   penny_stock_momentum: 0
   penny_stock_risk_metrics: 0
   price_data: 0
   stocks: 10
   top_movers: 0
   user_watchlists: 0
============================================================
```

## Database Management Commands

```bash
# Initialize database (create all tables)
python scripts/manage_db.py init

# Check database status
python scripts/manage_db.py status

# Drop all tables (CAUTION!)
python scripts/manage_db.py drop

# Reset database (drop and recreate)
python scripts/manage_db.py reset
```

## Database Schema Overview

### Core Tables

**stocks** - Stock information
- ticker, name, sector, industry
- market_cap, avg_volume
- is_penny_stock flag

**price_data** (TimescaleDB Hypertable)
- OHLCV data with timestamps
- Optimized for time-series queries
- Automatic partitioning by time

**news_articles** - News content
- title, content, summary
- source, published_at
- category, relevance_score

**news_sentiment** - Sentiment analysis
- Links articles to stocks
- VADER and FinBERT scores
- Confidence and entities

### Prediction & Analysis Tables

**daily_predictions** - ML predictions
- predicted_price, confidence
- lower_bound, upper_bound
- category (Strong Buy to Strong Sell)
- factors (JSON)

**top_movers** - Daily gainers/losers
- price_change_pct, volume_ratio
- is_gainer flag
- rank (1-20)

### Penny Stock Tables

**penny_stock_momentum** - Momentum tracking
- momentum_score (0-100)
- Components: price, volume, trend, catalyst
- rank by momentum

**penny_stock_risk_metrics** - Risk analysis
- liquidity_risk, volatility_risk
- spread_percentage
- overall_risk (low/medium/high/extreme)
- suspicion_score (pump-dump detection)

### User Tables

**alerts** - User alerts
- alert_type, threshold
- is_triggered, priority
- message

**user_watchlists** - Watchlists
- name, description
- tickers (JSON array)

## TimescaleDB Features

### Hypertables
- `price_data` is converted to a hypertable
- Automatic time-based partitioning
- Optimized for time-series queries

### Continuous Aggregates
- `price_data_daily` - Daily OHLCV rollups
- `price_data_hourly` - Hourly OHLCV rollups
- Auto-refresh policies configured

### Performance Benefits
- Fast queries on large time-series datasets
- Efficient compression
- Automatic data retention policies (can be configured)

## Troubleshooting

### Connection Failed
```bash
# Check if PostgreSQL is running
docker ps  # If using Docker

# Test connection
psql -h localhost -U postgres -d stockiq
```

### TimescaleDB Not Installed
```bash
# If using Docker, ensure you're using timescale/timescaledb image
docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb:latest-pg14

# If native installation, install TimescaleDB extension
# https://docs.timescale.com/install/latest/self-hosted/
```

### Tables Already Exist
```bash
# Reset database
python scripts/manage_db.py reset
```

## Next Steps

**Phase 0.1.2: Redis Cache Setup** (1 day)

Create `stockiq/infrastructure/cache.py` with:
- Redis connection management
- Cache key patterns
- TTL management
- Cache operations (get, set, delete, exists)

**Reference:** See `d:\workspace\projects\.kiro\specs\institutional-upgrade\tasks.md` for detailed task breakdown.

## Testing the Database

You can test the database with Python:

```python
from stockiq.infrastructure.database import get_db_context
from stockiq.infrastructure.models import Stock

# Query stocks
with get_db_context() as db:
    stocks = db.query(Stock).all()
    for stock in stocks:
        print(f"{stock.ticker}: {stock.name}")
```

## Database Backup

```bash
# Backup database
pg_dump -h localhost -U postgres stockiq > backup.sql

# Restore database
psql -h localhost -U postgres stockiq < backup.sql
```

---

**Status:** ✅ Phase 0.1.1 Complete
**Next:** Phase 0.1.2 - Redis Cache Setup
**Duration:** 2 days completed, 1 day remaining in Phase 0.1
