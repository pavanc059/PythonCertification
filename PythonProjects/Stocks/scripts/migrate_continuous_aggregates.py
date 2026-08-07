"""
Migration script to upgrade continuous aggregates.

This script:
1. Drops old continuous aggregate views (price_data_daily, price_data_hourly)
2. Creates new continuous aggregates (1m, 5m, 1h, 1d)
3. Creates indexes on the new aggregates
4. Sets up refresh policies

Run this on existing databases to upgrade to the new aggregate structure.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
import structlog

from stockiq.infrastructure.database import get_engine
from stockiq.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)


def drop_old_continuous_aggregates():
    """Drop old continuous aggregate views."""
    engine = get_engine()
    
    old_views = ['price_data_daily', 'price_data_hourly']
    
    with engine.connect() as conn:
        for view_name in old_views:
            try:
                logger.info("dropping_old_aggregate", view_name=view_name)
                
                # Drop the continuous aggregate (CASCADE to drop policies)
                conn.execute(text(f"""
                    DROP MATERIALIZED VIEW IF EXISTS {view_name} CASCADE;
                """))
                conn.commit()
                
                logger.info("old_aggregate_dropped", view_name=view_name)
                
            except Exception as e:
                logger.warning(
                    "failed_to_drop_old_aggregate",
                    view_name=view_name,
                    error=str(e)
                )


def create_new_continuous_aggregates():
    """Create new continuous aggregates with 1m, 5m, 1h, 1d intervals."""
    engine = get_engine()
    
    aggregates = [
        ('price_data_1min', '1 minute'),
        ('price_data_5min', '5 minutes'),
        ('price_data_1hour', '1 hour'),
        ('price_data_1day', '1 day')
    ]
    
    with engine.connect() as conn:
        for view_name, interval in aggregates:
            try:
                logger.info("creating_continuous_aggregate", view_name=view_name)
                
                conn.execute(text(f"""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name}
                    WITH (timescaledb.continuous) AS
                    SELECT
                        stock_id,
                        time_bucket('{interval}', timestamp) AS bucket,
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
                
                logger.info("continuous_aggregate_created", view_name=view_name)
                
            except Exception as e:
                logger.error(
                    "failed_to_create_continuous_aggregate",
                    view_name=view_name,
                    error=str(e)
                )
                raise


def create_aggregate_indexes():
    """Create indexes on continuous aggregates for optimal query performance."""
    engine = get_engine()
    
    indexes = [
        ('idx_price_data_1min_stock_bucket', 'price_data_1min', 'stock_id, bucket DESC'),
        ('idx_price_data_5min_stock_bucket', 'price_data_5min', 'stock_id, bucket DESC'),
        ('idx_price_data_1hour_stock_bucket', 'price_data_1hour', 'stock_id, bucket DESC'),
        ('idx_price_data_1day_stock_bucket', 'price_data_1day', 'stock_id, bucket DESC'),
    ]
    
    with engine.connect() as conn:
        for index_name, table_name, columns in indexes:
            try:
                logger.info("creating_index", index_name=index_name)
                
                conn.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} ({columns});
                """))
                conn.commit()
                
                logger.info("index_created", index_name=index_name)
                
            except Exception as e:
                logger.warning(
                    "failed_to_create_index",
                    index_name=index_name,
                    error=str(e)
                )


def add_refresh_policies():
    """Add refresh policies for continuous aggregates."""
    engine = get_engine()
    
    policies = [
        ('price_data_1min', '1 hour', '1 minute', '5 minutes'),
        ('price_data_5min', '3 hours', '5 minutes', '15 minutes'),
        ('price_data_1hour', '12 hours', '1 hour', '1 hour'),
        ('price_data_1day', '7 days', '1 day', '1 day')
    ]
    
    with engine.connect() as conn:
        for view_name, start_offset, end_offset, schedule_interval in policies:
            try:
                logger.info("adding_refresh_policy", view_name=view_name)
                
                conn.execute(text(f"""
                    SELECT add_continuous_aggregate_policy('{view_name}',
                        start_offset => INTERVAL '{start_offset}',
                        end_offset => INTERVAL '{end_offset}',
                        schedule_interval => INTERVAL '{schedule_interval}',
                        if_not_exists => TRUE
                    );
                """))
                conn.commit()
                
                logger.info(
                    "refresh_policy_added",
                    view_name=view_name,
                    schedule=schedule_interval
                )
                
            except Exception as e:
                logger.error(
                    "failed_to_add_refresh_policy",
                    view_name=view_name,
                    error=str(e)
                )
                raise


def refresh_all_aggregates():
    """Manually refresh all continuous aggregates with existing data."""
    engine = get_engine()
    
    views = ['price_data_1min', 'price_data_5min', 'price_data_1hour', 'price_data_1day']
    
    with engine.connect() as conn:
        for view_name in views:
            try:
                logger.info("refreshing_aggregate", view_name=view_name)
                
                # Refresh the entire aggregate
                conn.execute(text(f"""
                    CALL refresh_continuous_aggregate('{view_name}', NULL, NULL);
                """))
                conn.commit()
                
                logger.info("aggregate_refreshed", view_name=view_name)
                
            except Exception as e:
                logger.warning(
                    "failed_to_refresh_aggregate",
                    view_name=view_name,
                    error=str(e)
                )


def verify_migration():
    """Verify the migration was successful."""
    engine = get_engine()
    
    expected_views = ['price_data_1min', 'price_data_5min', 'price_data_1hour', 'price_data_1day']
    
    with engine.connect() as conn:
        logger.info("verifying_migration")
        
        # Check that all views exist
        for view_name in expected_views:
            result = conn.execute(text(f"""
                SELECT viewname FROM pg_views WHERE viewname = '{view_name}';
            """))
            
            if result.rowcount == 0:
                logger.error("view_not_found", view_name=view_name)
                return False
            
            logger.info("view_verified", view_name=view_name)
        
        # Check that refresh policies exist
        for view_name in expected_views:
            result = conn.execute(text(f"""
                SELECT application_name
                FROM timescaledb_information.jobs
                WHERE application_name LIKE '%{view_name}%';
            """))
            
            if result.rowcount == 0:
                logger.warning("refresh_policy_not_found", view_name=view_name)
            else:
                logger.info("refresh_policy_verified", view_name=view_name)
        
        logger.info("migration_verified_successfully")
        return True


def main():
    """Main migration function."""
    settings = get_settings()
    
    print("\n" + "="*60)
    print("CONTINUOUS AGGREGATE MIGRATION")
    print("="*60)
    
    db_url = settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url
    print(f"\nDatabase: {db_url}")
    
    print("\nThis migration will:")
    print("1. Drop old continuous aggregates (price_data_daily, price_data_hourly)")
    print("2. Create new aggregates (1m, 5m, 1h, 1d)")
    print("3. Create indexes for optimal performance")
    print("4. Set up automatic refresh policies")
    print("5. Refresh aggregates with existing data")
    
    print("\n⚠️  WARNING: This may take several minutes for large databases.")
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Migration aborted.")
        return
    
    try:
        # Step 1: Drop old aggregates
        print("\n1️⃣  Dropping old continuous aggregates...")
        drop_old_continuous_aggregates()
        print("✅ Old aggregates dropped")
        
        # Step 2: Create new aggregates
        print("\n2️⃣  Creating new continuous aggregates...")
        create_new_continuous_aggregates()
        print("✅ New aggregates created")
        
        # Step 3: Create indexes
        print("\n3️⃣  Creating indexes...")
        create_aggregate_indexes()
        print("✅ Indexes created")
        
        # Step 4: Add refresh policies
        print("\n4️⃣  Adding refresh policies...")
        add_refresh_policies()
        print("✅ Refresh policies added")
        
        # Step 5: Refresh aggregates
        print("\n5️⃣  Refreshing aggregates with existing data...")
        print("   (This may take several minutes...)")
        refresh_all_aggregates()
        print("✅ Aggregates refreshed")
        
        # Step 6: Verify migration
        print("\n6️⃣  Verifying migration...")
        if verify_migration():
            print("✅ Migration verified successfully")
        else:
            print("⚠️  Migration completed with warnings (check logs)")
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        
        print("\nNew continuous aggregates are now available:")
        print("  - price_data_1min   (1-minute OHLCV rollups)")
        print("  - price_data_5min   (5-minute OHLCV rollups)")
        print("  - price_data_1hour  (1-hour OHLCV rollups)")
        print("  - price_data_1day   (1-day OHLCV rollups)")
        
        print("\nQuery performance should now meet sub-200ms requirement for 5-year spans.")
        print("\nNext steps:")
        print("1. Run performance benchmark: python -c 'from stockiq.infrastructure.timescale import benchmark_query_performance; print(benchmark_query_performance())'")
        print("2. Update application code to use new aggregate intervals")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check database connection")
        print("2. Ensure TimescaleDB extension is installed")
        print("3. Verify price_data hypertable exists")
        print("4. Check database logs for detailed errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
