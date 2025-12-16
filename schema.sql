-- Crypto Analytics Platform - Database Schema
-- SQLite implementation for Phase 2
-- Migration path to PostgreSQL provided in comments

-- ============================================================================
-- TICKS TABLE - Raw trade data from WebSocket streams
-- ============================================================================

CREATE TABLE IF NOT EXISTS ticks (
    -- Auto-incrementing primary key (ensures monotonic ordering)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Trading symbol (e.g., 'BTCUSDT', 'ETHUSDT')
    symbol TEXT NOT NULL,
    
    -- Trade timestamp in ISO 8601 format
    -- Example: '2025-12-16T12:18:57.486000'
    -- Note: SQLite stores as TEXT, PostgreSQL uses TIMESTAMPTZ
    timestamp TEXT NOT NULL,
    
    -- Trade price (SQLite REAL = 8-byte float)
    -- Note: PostgreSQL uses NUMERIC(20,8) for exact decimal representation
    price REAL NOT NULL,
    
    -- Trade quantity/size
    size REAL NOT NULL
);

-- Index for time-range queries (most common access pattern)
-- Optimizes queries like: WHERE symbol = ? AND timestamp BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_timestamp 
ON ticks(symbol, timestamp DESC);

-- Index for latest price queries
-- Optimizes queries like: WHERE symbol = ? ORDER BY id DESC LIMIT 1
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_id 
ON ticks(symbol, id DESC);

-- ============================================================================
-- OHLC TABLE - Resampled candlestick/bar data
-- ============================================================================

CREATE TABLE IF NOT EXISTS ohlc (
    -- Trading symbol
    symbol TEXT NOT NULL,
    
    -- Time interval ('1s', '1m', '5m', '15m', '1h', etc.)
    interval TEXT NOT NULL,
    
    -- Start of the interval bucket (ISO 8601 format)
    -- Example: For 1m interval, '2025-12-16T12:18:00.000000'
    timestamp TEXT NOT NULL,
    
    -- OHLC prices
    open REAL NOT NULL,      -- First trade price in interval
    high REAL NOT NULL,      -- Highest trade price in interval
    low REAL NOT NULL,       -- Lowest trade price in interval
    close REAL NOT NULL,     -- Last trade price in interval
    
    -- Volume (sum of all trade sizes in interval)
    volume REAL NOT NULL,
    
    -- Number of trades in interval
    trade_count INTEGER NOT NULL,
    
    -- Composite primary key (prevents duplicate bars)
    PRIMARY KEY (symbol, interval, timestamp)
);

-- Index for time-range queries on OHLC data
-- Optimizes charting queries: WHERE symbol = ? AND interval = ? AND timestamp BETWEEN ? AND ?
CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_interval_timestamp 
ON ohlc(symbol, interval, timestamp DESC);

-- ============================================================================
-- POSTGRESQL MIGRATION REFERENCE
-- ============================================================================

-- When migrating to PostgreSQL, use this schema:
--
-- CREATE TABLE ticks (
--     id SERIAL PRIMARY KEY,
--     symbol VARCHAR(20) NOT NULL,
--     timestamp TIMESTAMPTZ NOT NULL,
--     price NUMERIC(20, 8) NOT NULL,
--     size NUMERIC(20, 8) NOT NULL
-- );
-- 
-- CREATE INDEX idx_ticks_symbol_timestamp 
-- ON ticks(symbol, timestamp DESC);
-- 
-- CREATE INDEX idx_ticks_symbol_id 
-- ON ticks(symbol, id DESC);
--
-- CREATE TABLE ohlc (
--     symbol VARCHAR(20) NOT NULL,
--     interval VARCHAR(10) NOT NULL,
--     timestamp TIMESTAMPTZ NOT NULL,
--     open NUMERIC(20, 8) NOT NULL,
--     high NUMERIC(20, 8) NOT NULL,
--     low NUMERIC(20, 8) NOT NULL,
--     close NUMERIC(20, 8) NOT NULL,
--     volume NUMERIC(20, 8) NOT NULL,
--     trade_count INTEGER NOT NULL,
--     PRIMARY KEY (symbol, interval, timestamp)
-- );
--
-- CREATE INDEX idx_ohlc_symbol_interval_timestamp 
-- ON ohlc(symbol, interval, timestamp DESC);

-- ============================================================================
-- TIMESCALEDB ENHANCEMENT (Future Phase 4)
-- ============================================================================

-- After PostgreSQL migration, convert to TimescaleDB hypertables:
--
-- SELECT create_hypertable('ticks', 'timestamp', chunk_time_interval => INTERVAL '1 day');
-- SELECT create_hypertable('ohlc', 'timestamp', chunk_time_interval => INTERVAL '7 days');
--
-- Enable compression (reduces storage by 90%+):
-- ALTER TABLE ticks SET (timescaledb.compress);
-- SELECT add_compression_policy('ticks', INTERVAL '7 days');
--
-- Create continuous aggregates for pre-computed metrics:
-- CREATE MATERIALIZED VIEW vwap_1m WITH (timescaledb.continuous) AS
-- SELECT time_bucket('1 minute', timestamp) AS bucket,
--        symbol,
--        SUM(price * size) / SUM(size) AS vwap
-- FROM ticks
-- GROUP BY bucket, symbol;
