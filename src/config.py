"""
Configuration management for the crypto analytics platform.

This module centralizes all configuration parameters including:
- Trading symbols to monitor
- WebSocket connection settings
- Buffer and performance tuning
- Logging configuration
"""

from typing import List, Tuple

# ============================================================================
# TRADING SYMBOLS
# ============================================================================

# List of symbols to track (Binance Futures format)
# Easily extensible - add more symbols as needed
SYMBOLS: List[str] = [
    "btcusdt",
    "ethusdt",
]

# ============================================================================
# WEBSOCKET CONFIGURATION
# ============================================================================

# Binance Futures WebSocket URL template
# Format: wss://fstream.binance.com/ws/{symbol}@trade
WEBSOCKET_URL: str = "wss://fstream.binance.com/ws/{symbol}@trade"

# ============================================================================
# BUFFER CONFIGURATION
# ============================================================================

# Maximum number of ticks to buffer per symbol before blocking
# Adjust based on processing speed and memory constraints
BUFFER_SIZE: int = 1000

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

# Base delay for exponential backoff on reconnection (seconds)
RECONNECT_DELAY_BASE: float = 1.0

# Maximum delay between reconnection attempts (seconds)
RECONNECT_MAX_DELAY: float = 8.0

# Ping interval to keep connection alive (seconds)
PING_INTERVAL: float = 20.0

# Ping timeout before considering connection dead (seconds)
PING_TIMEOUT: float = 10.0

# ============================================================================
# MONITORING
# ============================================================================

# Interval for printing status updates (seconds)
STATUS_UPDATE_INTERVAL: int = 10

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log format with timestamp
LOG_FORMAT: str = "[%(asctime)s] %(levelname)s: %(message)s"

# Timestamp format (with milliseconds)
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Default log level
LOG_LEVEL: str = "INFO"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database type (future: 'postgresql', 'timescaledb')
DATABASE_TYPE: str = "sqlite"

# SQLite database file path
DATABASE_PATH: str = "data/crypto_analytics.db"

# Batch insert optimization
TICK_BATCH_SIZE: int = 100          # Flush after N ticks
TICK_BATCH_TIMEOUT: float = 1.0     # Flush after N seconds (whichever comes first)

# ============================================================================
# RESAMPLING CONFIGURATION
# ============================================================================

# OHLC intervals to generate
RESAMPLE_INTERVALS: List[str] = ["1s", "1m", "5m"]

# ============================================================================
# ANALYTICS CONFIGURATION
# ============================================================================

# Update interval for background analytics (seconds)
ANALYTICS_UPDATE_INTERVAL: int = 5

# Default rolling windows for various metrics
DEFAULT_ROLLING_WINDOW: int = 60        # General purpose (60 bars)
CORRELATION_WINDOW: int = 60            # Correlation calculation
ZSCORE_WINDOW: int = 20                 # Z-score normalization

# Minimum data requirements for analytics
MIN_DATA_POINTS_STATS: int = 10         # Basic statistics
MIN_DATA_POINTS_REGRESSION: int = 30    # OLS regression
MIN_DATA_POINTS_ADF: int = 50           # ADF stationarity test
MIN_DATA_POINTS_CORRELATION: int = 20   # Correlation analysis

# Cache TTL (time-to-live) in seconds
CACHE_TTL_STATS: float = 5.0            # Price/volume statistics
CACHE_TTL_REGRESSION: float = 10.0      # Regression results
CACHE_TTL_ADF: float = 60.0             # ADF test (expensive)
CACHE_TTL_CORRELATION: float = 10.0     # Correlation metrics

# Pairs trading configuration
DEFAULT_SYMBOL_PAIRS: List[Tuple[str, str]] = [
    ("BTCUSDT", "ETHUSDT"),
    # Add more pairs as needed
]

# ============================================================================
# FLASK API CONFIGURATION (Phase 4)
# ============================================================================

# Flask server settings
FLASK_HOST: str = "127.0.0.1"
FLASK_PORT: int = 5000
FLASK_DEBUG: bool = True

# ============================================================================
# DASH DASHBOARD CONFIGURATION (Phase 4)
# ============================================================================

# Dash server settings
DASH_HOST: str = "127.0.0.1"
DASH_PORT: int = 8050
DASH_DEBUG: bool = True

# Dashboard update interval (milliseconds)
DASHBOARD_UPDATE_INTERVAL: int = 5000  # 5 seconds

