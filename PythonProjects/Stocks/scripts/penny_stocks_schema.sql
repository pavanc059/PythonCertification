-- =============================================================================
-- Penny Stock Schema Migration
-- =============================================================================
-- Creates the three penny stock tables and their supporting indexes.
--
-- Tables:
--   penny_stock_momentum     — momentum scores and price/volume metrics
--   penny_stock_risk_metrics — liquidity, volatility, and spread metrics
--   penny_stock_alerts       — threshold-based alerts for penny stocks
--
-- Requirements: 11.1-11.20 (Penny Stock Momentum Dashboard)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. penny_stock_momentum
-- -----------------------------------------------------------------------------
-- Stores a daily snapshot of momentum scoring for each penny stock
-- (price ≤ $5.00).  One row per (ticker, date) pair is the expected pattern;
-- a UNIQUE constraint enforces idempotent upserts.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS penny_stock_momentum (
    id                  SERIAL          PRIMARY KEY,
    ticker              VARCHAR(10)     NOT NULL,
    date                DATE            NOT NULL,

    -- Core metrics required by the task spec
    momentum_score      FLOAT           NOT NULL
        CONSTRAINT chk_psm_momentum_range CHECK (momentum_score >= 0 AND momentum_score <= 100),
    price_change_pct    FLOAT           NOT NULL,
    volume_ratio        FLOAT           NOT NULL
        CONSTRAINT chk_psm_volume_ratio CHECK (volume_ratio >= 0),

    -- Extended momentum components (weights sum to 100%)
    price_component     FLOAT,
    volume_component    FLOAT,
    trend_component     FLOAT,
    catalyst_component  FLOAT,

    -- Additional context
    price               NUMERIC(10, 4)
        CONSTRAINT chk_psm_penny_price CHECK (price IS NULL OR price <= 5.0),
    volume              BIGINT,
    avg_volume          BIGINT,
    catalyst            VARCHAR(500),
    rank                INTEGER,

    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- Idempotency: one record per (ticker, date)
    CONSTRAINT uq_psm_ticker_date UNIQUE (ticker, date)
);

-- Indexes on ticker and date for query performance (Requirement: index on ticker and date)
CREATE INDEX IF NOT EXISTS idx_psm_ticker
    ON penny_stock_momentum (ticker);

CREATE INDEX IF NOT EXISTS idx_psm_date
    ON penny_stock_momentum (date);

CREATE INDEX IF NOT EXISTS idx_psm_ticker_date
    ON penny_stock_momentum (ticker, date);

-- Support for ranking queries (e.g. top 20 by momentum on a given date)
CREATE INDEX IF NOT EXISTS idx_psm_date_rank
    ON penny_stock_momentum (date, rank);

CREATE INDEX IF NOT EXISTS idx_psm_date_momentum_score
    ON penny_stock_momentum (date, momentum_score DESC);


-- -----------------------------------------------------------------------------
-- 2. penny_stock_risk_metrics
-- -----------------------------------------------------------------------------
-- Stores daily risk metrics for penny stocks.  Column names deliberately
-- match the design-doc dataclass fields (spread_pct, liquidity_risk,
-- volatility_risk) so application code needs no mapping layer.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS penny_stock_risk_metrics (
    id                  SERIAL          PRIMARY KEY,
    ticker              VARCHAR(10)     NOT NULL,
    date                DATE            NOT NULL,

    -- Core metrics required by the task spec
    liquidity_risk      FLOAT           NOT NULL
        CONSTRAINT chk_psrm_liquidity CHECK (liquidity_risk >= 0 AND liquidity_risk <= 1),
    volatility_risk     FLOAT           NOT NULL
        CONSTRAINT chk_psrm_volatility CHECK (volatility_risk >= 0 AND volatility_risk <= 1),
    spread_pct          FLOAT           NOT NULL
        CONSTRAINT chk_psrm_spread CHECK (spread_pct >= 0),

    -- Overall classification and pump-dump indicators
    overall_risk        VARCHAR(20)
        CONSTRAINT chk_psrm_overall_risk CHECK (
            overall_risk IS NULL OR overall_risk IN ('low', 'medium', 'high', 'extreme')
        ),
    suspicion_score     FLOAT
        CONSTRAINT chk_psrm_suspicion CHECK (
            suspicion_score IS NULL OR (suspicion_score >= 0 AND suspicion_score <= 1)
        ),
    recommendation      VARCHAR(20)
        CONSTRAINT chk_psrm_recommendation CHECK (
            recommendation IS NULL OR recommendation IN ('safe', 'caution', 'avoid')
        ),

    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- Idempotency: one record per (ticker, date)
    CONSTRAINT uq_psrm_ticker_date UNIQUE (ticker, date)
);

-- Indexes on ticker and date (Requirement: index on ticker and date)
CREATE INDEX IF NOT EXISTS idx_psrm_ticker
    ON penny_stock_risk_metrics (ticker);

CREATE INDEX IF NOT EXISTS idx_psrm_date
    ON penny_stock_risk_metrics (date);

CREATE INDEX IF NOT EXISTS idx_psrm_ticker_date
    ON penny_stock_risk_metrics (ticker, date);

-- Support filtering by risk level
CREATE INDEX IF NOT EXISTS idx_psrm_date_overall_risk
    ON penny_stock_risk_metrics (date, overall_risk);


-- -----------------------------------------------------------------------------
-- 3. penny_stock_alerts
-- -----------------------------------------------------------------------------
-- Records threshold-crossing events for penny stocks.  Unlike the general
-- `alerts` table, this table is scoped to penny-stock-specific alert types
-- and is intentionally denormalized (stores ticker directly rather than a
-- FK to `stocks`) to remain functional even before the stocks table is
-- populated.
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS penny_stock_alerts (
    id              SERIAL          PRIMARY KEY,
    ticker          VARCHAR(10)     NOT NULL,
    alert_type      VARCHAR(50)     NOT NULL,
    threshold       FLOAT           NOT NULL,
    triggered_at    TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- Additional context
    current_value   FLOAT,              -- actual value that crossed the threshold
    message         TEXT,               -- human-readable description
    priority        INTEGER DEFAULT 1   -- 1=low, 2=medium, 3=high
        CONSTRAINT chk_psa_priority CHECK (priority BETWEEN 1 AND 3),
    is_read         BOOLEAN DEFAULT FALSE,

    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

-- Indexes on ticker (Requirement: index on ticker and date)
-- penny_stock_alerts uses triggered_at instead of a separate date column
CREATE INDEX IF NOT EXISTS idx_psa_ticker
    ON penny_stock_alerts (ticker);

CREATE INDEX IF NOT EXISTS idx_psa_triggered_at
    ON penny_stock_alerts (triggered_at);

CREATE INDEX IF NOT EXISTS idx_psa_ticker_triggered_at
    ON penny_stock_alerts (ticker, triggered_at);

CREATE INDEX IF NOT EXISTS idx_psa_alert_type
    ON penny_stock_alerts (alert_type);


-- =============================================================================
-- Verification queries (run manually to confirm the migration)
-- =============================================================================
-- SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'public'
--     AND table_name IN ('penny_stock_momentum', 'penny_stock_risk_metrics', 'penny_stock_alerts');
--
-- SELECT indexname, tablename FROM pg_indexes
--   WHERE tablename IN ('penny_stock_momentum', 'penny_stock_risk_metrics', 'penny_stock_alerts')
--   ORDER BY tablename, indexname;
-- =============================================================================
