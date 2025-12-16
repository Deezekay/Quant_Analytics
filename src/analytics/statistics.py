"""
Statistical calculations for price and volume data.

This module provides descriptive statistics, z-score calculations,
and other statistical measures for quantitative trading analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd

from ..storage.database import DatabaseManager
from ..config import (
    DEFAULT_ROLLING_WINDOW,
    MIN_DATA_POINTS_STATS,
    ZSCORE_WINDOW,
)
from .models import PriceStats, VolumeStats

logger = logging.getLogger(__name__)


class StatisticsCalculator:
    """
    Calculator for descriptive statistics on price and volume data.
    
    Computes rolling statistics from OHLC bars stored in the database.
    All methods are async and query the database for fresh data.
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize statistics calculator.
        
        Args:
            db: Database manager instance
        """
        self.db = db
    
    async def compute_price_stats(
        self,
        symbol: str,
        interval: str = '1m',
        window: int = DEFAULT_ROLLING_WINDOW
    ) -> Optional[PriceStats]:
        """
        Compute rolling price statistics from OHLC close prices.
        
        Math:
        - mean = Σ(price_i) / n
        - std = sqrt(Σ(price_i - mean)² / (n-1))  [sample std]
        - change_pct = ((last - first) / first) × 100
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Time interval ('1s', '1m', '5m')
            window: Number of bars to analyze
        
        Returns:
            PriceStats object or None if insufficient data
        """
        try:
            # Get last N OHLC bars
            end = datetime.now()
            start = end - timedelta(hours=24)  # Look back 24 hours
            
            bars = await self.db.get_ohlc(symbol, interval, start, end, limit=window)
            
            if len(bars) < MIN_DATA_POINTS_STATS:
                logger.warning(
                    f"Insufficient data for price stats: {len(bars)} bars "
                    f"(min: {MIN_DATA_POINTS_STATS})"
                )
                return None
            
            # Extract close prices
            prices = np.array([bar.close for bar in bars])
            
            # Compute statistics
            mean_price = float(np.mean(prices))
            std_price = float(np.std(prices, ddof=1))  # Sample std
            min_price = float(np.min(prices))
            max_price = float(np.max(prices))
            current_price = float(prices[-1])
            
            # Percent change from first to last
            change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100 if prices[0] != 0 else 0.0
            
            result = PriceStats(
                symbol=symbol,
                interval=interval,
                window_size=len(bars),
                mean=mean_price,
                std=std_price,
                min=min_price,
                max=max_price,
                current=current_price,
                change_pct=change_pct,
                timestamp=datetime.now()
            )
            
            logger.debug(
                f"Price stats for {symbol}: mean=${mean_price:.2f}, "
                f"std=${std_price:.2f}, change={change_pct:+.2f}%"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to compute price stats for {symbol}: {e}")
            return None
    
    async def compute_volume_stats(
        self,
        symbol: str,
        interval: str = '1m',
        window: int = DEFAULT_ROLLING_WINDOW
    ) -> Optional[VolumeStats]:
        """
        Compute volume statistics from OHLC bars.
        
        Args:
            symbol: Trading symbol
            interval: Time interval
            window: Number of bars to analyze
        
        Returns:
            VolumeStats object or None if insufficient data
        """
        try:
            # Get last N OHLC bars
            end = datetime.now()
            start = end - timedelta(hours=24)
            
            bars = await self.db.get_ohlc(symbol, interval, start, end, limit=window)
            
            if len(bars) < MIN_DATA_POINTS_STATS:
                logger.warning(
                    f"Insufficient data for volume stats: {len(bars)} bars "
                    f"(min: {MIN_DATA_POINTS_STATS})"
                )
                return None
            
            # Extract volumes
            volumes = np.array([bar.volume for bar in bars])
            
            # Compute statistics
            mean_vol = float(np.mean(volumes))
            std_vol = float(np.std(volumes, ddof=1))
            total_vol = float(np.sum(volumes))
            
            result = VolumeStats(
                symbol=symbol,
                interval=interval,
                window_size=len(bars),
                mean_volume=mean_vol,
                std_volume=std_vol,
                total_volume=total_vol,
                timestamp=datetime.now()
            )
            
            logger.debug(
                f"Volume stats for {symbol}: mean={mean_vol:.6f}, "
                f"total={total_vol:.6f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to compute volume stats for {symbol}: {e}")
            return None
    
    async def compute_zscore(
        self,
        values: List[float],
        window: int = ZSCORE_WINDOW
    ) -> List[float]:
        """
        Compute rolling z-score for a list of values.
        
        Z-score formula: z_i = (value_i - μ_window) / σ_window
        
        Where:
        - μ_window = rolling mean over window
        - σ_window = rolling standard deviation over window
        
        Use case: Identify when values deviate from normal
        - z > 2: Value is 2 standard deviations above mean (overbought)
        - z < -2: Value is 2 standard deviations below mean (oversold)
        - |z| < 1: Within normal range
        
        Args:
            values: List of values (e.g., spread prices)
            window: Rolling window size for mean/std calculation
        
        Returns:
            List of z-scores (same length as input, with NaN for early values)
        
        Example:
            >>> values = [100, 102, 98, 105, 95, 110, 90]
            >>> z_scores = await calc.compute_zscore(values, window=3)
            >>> # First 2 values will be NaN (not enough data)
            >>> # z_scores[2] onwards will have z-score values
        """
        try:
            if len(values) < window:
                logger.warning(
                    f"Insufficient data for z-score: {len(values)} values "
                    f"(window: {window})"
                )
                return [np.nan] * len(values)
            
            # Convert to pandas Series for efficient rolling operations
            series = pd.Series(values)
            
            # Compute rolling mean and std
            rolling_mean = series.rolling(window=window).mean()
            rolling_std = series.rolling(window=window).std(ddof=1)
            
            # Compute z-score
            z_scores = (series - rolling_mean) / rolling_std
            
            # Convert back to list, handling NaN
            result = z_scores.tolist()
            
            logger.debug(
                f"Computed {len([z for z in result if not np.isnan(z)])} "
                f"z-scores from {len(values)} values"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to compute z-score: {e}")
            return [np.nan] * len(values)
