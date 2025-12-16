"""
Analytics data models for quantitative trading.

This module defines data structures for time-series resampling,
OHLC (candlestick) bars, and analytics results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple


@dataclass
class OHLCData:
    """
    OHLC (Open-High-Low-Close) candlestick bar data.
    
    Represents aggregated trade data over a specific time interval.
    Used for charting, technical analysis, and pattern recognition.
    
    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        interval: Time interval of the bar (e.g., "1s", "1m", "5m")
        timestamp: Start of the interval bucket
        open: First trade price in the interval
        high: Highest trade price in the interval
        low: Lowest trade price in the interval
        close: Last trade price in the interval
        volume: Total trading volume (sum of trade sizes)
        trade_count: Number of individual trades in the interval
    
    Example:
        >>> ohlc = OHLCData(
        ...     symbol="BTCUSDT",
        ...     interval="1m",
        ...     timestamp=datetime(2025, 12, 16, 12, 18, 0),
        ...     open=86384.0,
        ...     high=86390.5,
        ...     low=86380.0,
        ...     close=86385.0,
        ...     volume=2.5,
        ...     trade_count=47
        ... )
    """
    
    symbol: str
    interval: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int
    
    def __str__(self) -> str:
        """Format OHLC data for console display."""
        return (
            f"{self.symbol} {self.interval} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"O: ${self.open:,.2f} | H: ${self.high:,.2f} | "
            f"L: ${self.low:,.2f} | C: ${self.close:,.2f} | "
            f"V: {self.volume:.6f} | Trades: {self.trade_count}"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trade_count": self.trade_count
        }


@dataclass
class PriceStats:
    """
    Descriptive statistics for price data.
    
    Attributes:
        symbol: Trading symbol
        interval: Time interval of underlying OHLC data
        window_size: Number of bars used in calculation
        mean: Average price
        std: Standard deviation
        min: Minimum price
        max: Maximum price
        current: Latest price
        change_pct: Percentage change from first to last price
        timestamp: When statistics were computed
    """
    symbol: str
    interval: str
    window_size: int
    mean: float
    std: float
    min: float
    max: float
    current: float
    change_pct: float
    timestamp: datetime


@dataclass
class VolumeStats:
    """
    Descriptive statistics for volume data.
    
    Attributes:
        symbol: Trading symbol
        interval: Time interval of underlying OHLC data
        window_size: Number of bars used
        mean_volume: Average volume per bar
        std_volume: Standard deviation of volume
        total_volume: Sum of all volume
        timestamp: When statistics were computed
    """
    symbol: str
    interval: str
    window_size: int
    mean_volume: float
    std_volume: float
    total_volume: float
    timestamp: datetime


@dataclass
class RegressionResult:
    """
    Results from OLS (Ordinary Least Squares) regression for pairs trading.
    
    Models relationship: Y = intercept + hedge_ratio * X + error
    
    Attributes:
        symbol_x: Independent variable symbol (e.g., "BTCUSDT")
        symbol_y: Dependent variable symbol (e.g., "ETHUSDT")
        interval: Time interval of underlying data
        hedge_ratio: Beta coefficient (slope) - how much Y moves per unit of X
        intercept: Alpha coefficient (y-intercept)
        r_squared: R² goodness of fit [0, 1] - proportion of variance explained
        std_error: Standard error of the regression
        residuals: Regression residuals (spread values)
        timestamp: When regression was computed
    """
    symbol_x: str
    symbol_y: str
    interval: str
    hedge_ratio: float
    intercept: float
    r_squared: float
    std_error: float
    residuals: List[float]
    timestamp: datetime


@dataclass
class ADFTestResult:
    """
    Results from Augmented Dickey-Fuller stationarity test.
    
    Tests null hypothesis: time series has unit root (non-stationary)
    
    Attributes:
        symbol: Symbol tested (or description if testing spread)
        test_statistic: ADF test statistic
        p_value: Probability value - reject null if < 0.05
        critical_values: Critical values at 1%, 5%, 10% significance levels
        is_stationary: True if p_value < 0.05 (reject null hypothesis)
        interpretation: Human-readable result explanation
        timestamp: When test was performed
    """
    symbol: str
    test_statistic: float
    p_value: float
    critical_values: Dict[str, float]
    is_stationary: bool
    interpretation: str
    timestamp: datetime


@dataclass
class CorrelationResult:
    """
    Rolling correlation analysis between two symbols.
    
    Attributes:
        symbol_x: First symbol
        symbol_y: Second symbol
        interval: Time interval of underlying data
        correlation: Latest Pearson correlation coefficient [-1, 1]
        rolling_window: Window size for correlation calculation
        correlation_history: Time series of (timestamp, correlation) tuples
        timestamp: When analysis was performed
    """
    symbol_x: str
    symbol_y: str
    interval: str
    correlation: float
    rolling_window: int
    correlation_history: List[Tuple[datetime, float]]
    timestamp: datetime
