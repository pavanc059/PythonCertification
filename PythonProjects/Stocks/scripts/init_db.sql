-- Database initialization SQL script
-- This script is automatically executed when the PostgreSQL container starts
-- It creates the TimescaleDB extension and performs initial setup

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create a function to check if TimescaleDB is properly installed
CREATE OR REPLACE FUNCTION check_timescaledb_version()
RETURNS TEXT AS $$
DECLARE
    version TEXT;
BEGIN
    SELECT extversion INTO version
    FROM pg_extension
    WHERE extname = 'timescaledb';
    
    IF version IS NULL THEN
        RETURN 'TimescaleDB not installed';
    ELSE
        RETURN 'TimescaleDB version: ' || version;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Log TimescaleDB version
DO $$
DECLARE
    version_info TEXT;
BEGIN
    version_info := check_timescaledb_version();
    RAISE NOTICE '%', version_info;
END $$;

-- Create a function to safely create hypertable
CREATE OR REPLACE FUNCTION create_hypertable_safe(
    table_name TEXT,
    time_column TEXT,
    chunk_interval INTERVAL DEFAULT '1 month'
)
RETURNS VOID AS $$
BEGIN
    -- Check if table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = $1
    ) THEN
        RAISE NOTICE 'Table % does not exist yet, skipping hypertable creation', $1;
        RETURN;
    END IF;
    
    -- Check if already a hypertable
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables 
        WHERE hypertable_name = $1
    ) THEN
        RAISE NOTICE 'Table % is already a hypertable', $1;
        RETURN;
    END IF;
    
    -- Create hypertable
    PERFORM create_hypertable($1, $2, chunk_time_interval => $3, if_not_exists => TRUE);
    RAISE NOTICE 'Created hypertable for table %', $1;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Could not create hypertable for %: %', $1, SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE stockiq TO stockiq;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stockiq;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stockiq;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO stockiq;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO stockiq;

-- Configure PostgreSQL for better performance with time-series data
-- These settings are optimized for TimescaleDB workloads

-- Increase shared_buffers for better caching (25% of RAM is recommended)
-- Note: This requires PostgreSQL restart to take effect
-- ALTER SYSTEM SET shared_buffers = '256MB';

-- Increase work_mem for complex queries
-- ALTER SYSTEM SET work_mem = '16MB';

-- Increase maintenance_work_mem for faster index creation
-- ALTER SYSTEM SET maintenance_work_mem = '128MB';

-- Enable parallel query execution
-- ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
-- ALTER SYSTEM SET max_parallel_workers = 8;

-- Optimize for time-series queries
-- ALTER SYSTEM SET random_page_cost = 1.1;
-- ALTER SYSTEM SET effective_cache_size = '1GB';

-- Log slow queries for monitoring
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries taking > 1 second

-- Enable query statistics
ALTER SYSTEM SET track_activities = on;
ALTER SYSTEM SET track_counts = on;
ALTER SYSTEM SET track_io_timing = on;

-- Reload configuration
SELECT pg_reload_conf();

-- Create a monitoring view for database statistics
CREATE OR REPLACE VIEW database_stats AS
SELECT
    datname AS database_name,
    numbackends AS active_connections,
    xact_commit AS transactions_committed,
    xact_rollback AS transactions_rolled_back,
    blks_read AS blocks_read_from_disk,
    blks_hit AS blocks_read_from_cache,
    CASE 
        WHEN (blks_read + blks_hit) > 0 
        THEN ROUND(100.0 * blks_hit / (blks_read + blks_hit), 2)
        ELSE 0
    END AS cache_hit_ratio,
    tup_returned AS rows_returned,
    tup_fetched AS rows_fetched,
    tup_inserted AS rows_inserted,
    tup_updated AS rows_updated,
    tup_deleted AS rows_deleted,
    conflicts AS conflicts,
    temp_files AS temp_files_created,
    temp_bytes AS temp_bytes_written,
    deadlocks,
    stats_reset AS stats_reset_time
FROM pg_stat_database
WHERE datname = 'stockiq';

-- Create a view for table sizes
CREATE OR REPLACE VIEW table_sizes AS
SELECT
    schemaname AS schema_name,
    tablename AS table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    pg_total_relation_size(schemaname||'.'||tablename) AS total_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Create a view for index usage statistics
CREATE OR REPLACE VIEW index_usage AS
SELECT
    schemaname AS schema_name,
    tablename AS table_name,
    indexname AS index_name,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Create a function to get hypertable information
CREATE OR REPLACE FUNCTION get_hypertable_info()
RETURNS TABLE (
    hypertable_name TEXT,
    num_chunks BIGINT,
    total_size TEXT,
    compression_enabled BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.hypertable_name::TEXT,
        COUNT(c.chunk_id) AS num_chunks,
        pg_size_pretty(SUM(pg_total_relation_size(format('%I.%I', c.chunk_schema, c.chunk_name)))) AS total_size,
        h.compression_state > 0 AS compression_enabled
    FROM timescaledb_information.hypertables h
    LEFT JOIN timescaledb_information.chunks c ON h.hypertable_name = c.hypertable_name
    GROUP BY h.hypertable_name, h.compression_state;
END;
$$ LANGUAGE plpgsql;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE '=================================================';
    RAISE NOTICE 'Database initialization completed successfully';
    RAISE NOTICE 'TimescaleDB extension: ENABLED';
    RAISE NOTICE 'Monitoring views: CREATED';
    RAISE NOTICE 'Helper functions: CREATED';
    RAISE NOTICE '=================================================';
END $$;
