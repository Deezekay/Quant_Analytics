"""
Analytics module for quantitative analysis.

This module provides real-time analytics, time-series resampling,
and statistical computations for crypto trading.
"""

from .models import (
    OHLCData,
    PriceStats,
    VolumeStats,
    RegressionResult,
    ADFTestResult,
    CorrelationResult
)

__all__ = [
    "OHLCData",
    "PriceStats",
    "VolumeStats",
    "RegressionResult",
    "ADFTestResult",
    "CorrelationResult"
]

# Note: Import analyzers and engine directly to avoid circular imports:
# from src.analytics.statistics import StatisticsCalculator
# from src.analytics.regression import RegressionAnalyzer
# from src.analytics.stationarity import StationarityAnalyzer
# from src.analytics.correlation import CorrelationAnalyzer
# from src.analytics.resampler import TickResampler
# from src.analytics.engine import AnalyticsEngine
