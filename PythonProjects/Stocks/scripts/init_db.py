"""
Database initialization script.

This script:
1. Creates all database tables
2. Sets up TimescaleDB hypertables
3. Creates indexes
4. Creates continuous aggregates for performance
5. Creates penny stock tables (penny_stock_momentum, penny_stock_risk_metrics,
   penny_stock_alerts) via the dedicated migration file
"""

import sys
import os

# Add parent directory to path to import stockiq
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
import structlog

from stockiq.infrastructure.database import get_engine, init_db
from stockiq.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)


def create_timescaledb_extension():
    """Create TimescaleDB extension if it doesn't exist."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            logger.info("creating_timescaledb_extension")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            conn.commit()
            logger.info("timescaledb_extension_created")
        except Exception as e:
            logger.error("failed_to_create_timescaledb_extension", error=str(e))
            raise


def create_hypertables():
    """Convert price_data table to TimescaleDB hypertable."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            # Check if hypertable already exists
            result = conn.execute(text("""
                SELECT * FROM timescaledb_information.hypertables 
                WHERE hypertable_name = 'price_data';
            """))
            
            if result.rowcount == 0:
                logger.info("creating_price_data_hypertable")
                conn.execute(text("""
                    SELECT create_hypertable(
                        'price_data',
                        'timestamp',
                        chunk_time_interval => INTERVAL '1 month',
                        if_not_exists => TRUE
                    );
                """))
                conn.commit()
                logger.info("price_data_hypertable_created")
            else:
                logger.info("price_data_hypertable_already_exists")
                
        except Exception as e:
            logger.error("failed_to_create_hypertable", error=str(e))
            raise


def create_continuous_aggregates():
    """
    Create continuous aggregates for pre-computed OHLCV rollups.
    
    Creates 1-minute, 5-minute, 1-hour, and 1-day aggregates to achieve
    sub-200ms query performance for 5-year time spans (Requirement 12.5).
    """
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            # 1-minute OHLCV aggregate (finest granularity)
            logger.info("creating_1min_ohlcv_aggregate")
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_1min
                WITH (timescaledb.continuous) AS
                SELECT
                    stock_id,
                    time_bucket('1 minute', timestamp) AS bucket,
                    first(open, timestamp) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    last(close, timestamp) AS close,
                    sum(volume) AS volume,
                    count(*) AS num_trades
                FROM price_data
                GROUP BY stock_id, bucket
                WITH NO DATA;
            """))
            conn.commit()
            logger.info("1min_ohlcv_aggregate_created")
            
            # 5-minute OHLCV aggregate
            logger.info("creating_5min_ohlcv_aggregate")
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_5min
                WITH (timescaledb.continuous) AS
                SELECT
                    stock_id,
                    time_bucket('5 minutes', timestamp) AS bucket,
                    first(open, timestamp) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    last(close, timestamp) AS close,
                    sum(volume) AS volume,
                    count(*) AS num_trades
                FROM price_data
                GROUP BY stock_id, bucket
                WITH NO DATA;
            """))
            conn.commit()
            logger.info("5min_ohlcv_aggregate_created")
            
            # 1-hour OHLCV aggregate
            logger.info("creating_hourly_ohlcv_aggregate")
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_1hour
                WITH (timescaledb.continuous) AS
                SELECT
                    stock_id,
                    time_bucket('1 hour', timestamp) AS bucket,
                    first(open, timestamp) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    last(close, timestamp) AS close,
                    sum(volume) AS volume,
                    count(*) AS num_trades
                FROM price_data
                GROUP BY stock_id, bucket
                WITH NO DATA;
            """))
            conn.commit()
            logger.info("hourly_ohlcv_aggregate_created")
            
            # 1-day OHLCV aggregate
            logger.info("creating_daily_ohlcv_aggregate")
            conn.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_1day
                WITH (timescaledb.continuous) AS
                SELECT
                    stock_id,
                    time_bucket('1 day', timestamp) AS bucket,
                    first(open, timestamp) AS open,
                    max(high) AS high,
                    min(low) AS low,
                    last(close, timestamp) AS close,
                    sum(volume) AS volume,
                    count(*) AS num_trades
                FROM price_data
                GROUP BY stock_id, bucket
                WITH NO DATA;
            """))
            conn.commit()
            logger.info("daily_ohlcv_aggregate_created")
            
            # Create indexes on continuous aggregates for optimal query performance
            logger.info("creating_continuous_aggregate_indexes")
            
            # Indexes for 1-minute aggregate
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_price_data_1min_stock_bucket 
                ON price_data_1min (stock_id, bucket DESC);
            """))
            
            # Indexes for 5-minute aggregate
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_price_data_5min_stock_bucket 
                ON price_data_5min (stock_id, bucket DESC);
            """))
            
            # Indexes for 1-hour aggregate
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_price_data_1hour_stock_bucket 
                ON price_data_1hour (stock_id, bucket DESC);
            """))
            
            # Indexes for 1-day aggregate
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_price_data_1day_stock_bucket 
                ON price_data_1day (stock_id, bucket DESC);
            """))
            
            conn.commit()
            logger.info("continuous_aggregate_indexes_created")
            
            # Add refresh policies for each aggregate
            logger.info("adding_refresh_policies")
            
            # Refresh 1-minute aggregate every 5 minutes (near real-time)
            conn.execute(text("""
                SELECT add_continuous_aggregate_policy('price_data_1min',
                    start_offset => INTERVAL '1 hour',
                    end_offset => INTERVAL '1 minute',
                    schedule_interval => INTERVAL '5 minutes',
                    if_not_exists => TRUE
                );
            """))
            
            # Refresh 5-minute aggregate every 15 minutes
            conn.execute(text("""
                SELECT add_continuous_aggregate_policy('price_data_5min',
                    start_offset => INTERVAL '3 hours',
                    end_offset => INTERVAL '5 minutes',
                    schedule_interval => INTERVAL '15 minutes',
                    if_not_exists => TRUE
                );
            """))
            
            # Refresh 1-hour aggregate every hour
            conn.execute(text("""
                SELECT add_continuous_aggregate_policy('price_data_1hour',
                    start_offset => INTERVAL '12 hours',
                    end_offset => INTERVAL '1 hour',
                    schedule_interval => INTERVAL '1 hour',
                    if_not_exists => TRUE
                );
            """))
            
            # Refresh 1-day aggregate once per day
            conn.execute(text("""
                SELECT add_continuous_aggregate_policy('price_data_1day',
                    start_offset => INTERVAL '7 days',
                    end_offset => INTERVAL '1 day',
                    schedule_interval => INTERVAL '1 day',
                    if_not_exists => TRUE
                );
            """))
            
            conn.commit()
            logger.info("refresh_policies_added")
            
        except Exception as e:
            logger.error("failed_to_create_continuous_aggregates", error=str(e))
            # Don't raise - continuous aggregates are optional optimization
            logger.warning("continuing_without_continuous_aggregates")


def create_additional_indexes():
    """Create additional performance indexes."""
    engine = get_engine()
    
    with engine.connect() as conn:
        try:
            logger.info("creating_additional_indexes")
            
            # Composite index for common queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_price_data_stock_timestamp_desc 
                ON price_data (stock_id, timestamp DESC);
            """))
            
            # Index for news sentiment queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_news_sentiment_stock_created 
                ON news_sentiment (stock_id, created_at DESC);
            """))
            
            # Index for prediction queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_predictions_stock_date_desc 
                ON daily_predictions (stock_id, prediction_date DESC);
            """))
            
            conn.commit()
            logger.info("additional_indexes_created")
            
        except Exception as e:
            logger.error("failed_to_create_additional_indexes", error=str(e))
            # Don't raise - indexes are optional optimization
            logger.warning("continuing_without_additional_indexes")


def run_penny_stocks_migration():
    """
    Execute the penny_stocks_schema.sql migration.

    Creates the three penny stock tables and their indexes if they don't
    already exist:
      - penny_stock_momentum
      - penny_stock_risk_metrics
      - penny_stock_alerts

    The migration file lives at scripts/penny_stocks_schema.sql and uses
    CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS, making it
    safe to run multiple times.
    """
    sql_path = os.path.join(os.path.dirname(__file__), "penny_stocks_schema.sql")
    if not os.path.exists(sql_path):
        logger.warning("penny_stocks_schema.sql not found, skipping migration", path=sql_path)
        return

    with open(sql_path, "r", encoding="utf-8") as fh:
        migration_sql = fh.read()

    engine = get_engine()
    with engine.connect() as conn:
        try:
            logger.info("running_penny_stocks_migration")
            conn.execute(text(migration_sql))
            conn.commit()
            logger.info("penny_stocks_migration_completed")
        except Exception as exc:
            logger.error("penny_stocks_migration_failed", error=str(exc))
            raise


def insert_sample_data():
    """Insert sample stock data for testing."""
    from stockiq.infrastructure.database import get_db_context
    from stockiq.infrastructure.models import Stock
    
    sample_stocks = [
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
        {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "industry": "Software"},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "industry": "Internet Services"},
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "industry": "Internet Retail"},
        {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical", "industry": "Auto Manufacturers"},
        {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "industry": "Semiconductors"},
        {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "industry": "Internet Services"},
        {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial", "industry": "Banks"},
        {"ticker": "V", "name": "Visa Inc.", "sector": "Financial", "industry": "Credit Services"},
        {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer Defensive", "industry": "Discount Stores"},
    ]
    
    try:
        with get_db_context() as db:
            logger.info("inserting_sample_stocks")
            
            for stock_data in sample_stocks:
                # Check if stock already exists
                existing = db.query(Stock).filter(Stock.ticker == stock_data["ticker"]).first()
                if not existing:
                    stock = Stock(**stock_data)
                    db.add(stock)
            
            db.commit()
            logger.info("sample_stocks_inserted", count=len(sample_stocks))
            
    except Exception as e:
        logger.error("failed_to_insert_sample_data", error=str(e))
        # Don't raise - sample data is optional


def main():
    """Main initialization function."""
    settings = get_settings()
    
    logger.info(
        "starting_database_initialization",
        database_url=settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url
    )
    
    try:
        # Step 1: Create TimescaleDB extension
        create_timescaledb_extension()
        
        # Step 2: Create all tables
        logger.info("creating_database_tables")
        init_db()
        logger.info("database_tables_created")
        
        # Step 3: Create hypertables
        create_hypertables()
        
        # Step 4: Create continuous aggregates
        create_continuous_aggregates()
        
        # Step 5: Create additional indexes
        create_additional_indexes()

        # Step 6: Run penny stocks schema migration
        run_penny_stocks_migration()

        # Step 7: Insert sample data
        insert_sample_data()
        
        logger.info("database_initialization_completed_successfully")
        print("\n✅ Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Verify tables: psql -d stockiq -c '\\dt'")
        print("2. Check hypertables: psql -d stockiq -c 'SELECT * FROM timescaledb_information.hypertables;'")
        print("3. Start implementing Phase 0.1.2 - Redis Cache Setup")
        
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        print(f"\n❌ Database initialization failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Ensure TimescaleDB extension is installed")
        print("3. Check database credentials in .env file")
        print("4. Verify database 'stockiq' exists")
        sys.exit(1)


if __name__ == "__main__":
    main()
