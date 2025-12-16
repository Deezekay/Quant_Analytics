"""
Correlation analysis for cryptocurrency pairs.

This module provides Pearson correlation calculations for measuring
the relationship strength between trading pairs.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from ..storage.database import DatabaseManager
from ..config import CORRELATION_WINDOW, MIN_DATA_POINTS_CORRELATION
from .models import CorrelationResult

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Pearson correlation analyzer for symbol pairs.
    
    Computes rolling correlation to monitor relationship strength
    over time between correlated trading pairs.
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize correlation analyzer.
        
        Args:
            db: Database manager instance
        """
        self.db = db
    
    async def compute_rolling_correlation(
        self,
        symbol_x: str,
        symbol_y: str,
        interval: str = '1m',
        window: int = CORRELATION_WINDOW,
        lookback: int = 1440  # 1 day of 1m bars
    ) -> Optional[CorrelationResult]:
        """
        Compute rolling Pearson correlation between two symbols.
        
        Mathematical Background:
        -----------------------
        Pearson correlation coefficient:
        
        r = Cov(X,Y) / (σ_X · σ_Y)
        
        where:
        - Cov(X,Y) = Σ((X_i - X̄)(Y_i - Ȳ)) / n
        - σ_X = sqrt(Σ(X_i - X̄)² / n)
        
        Range: r ∈ [-1, 1]
        
        Interpretation:
        --------------
        r → +1: Strong positive correlation (move together)
        r → 0:  No linear relationship
        r → -1: Strong negative correlation (move opposite)
        
        Trading Use Cases:
        -----------------
        - High correlation (r > 0.8): Good candidates for pairs trading
        - Declining correlation: Relationship weakening, exit positions
        - Negative correlation: Hedging opportunities
        
        Args:
            symbol_x: First symbol
            symbol_y: Second symbol
            interval: Time interval for OHLC data
            window: Rolling window for correlation (e.g., 60 bars)
            lookback: How far back to compute history (e.g., 1440 = 1 day)
        
        Returns:
            CorrelationResult with latest value and full history
        """
        try:
            # Get OHLC data
            end = datetime.now()
            start = end - timedelta(hours=48)  # Extra buffer
            
            bars_x = await self.db.get_ohlc(symbol_x, interval, start, end, limit=lookback * 2)
            bars_y = await self.db.get_ohlc(symbol_y, interval, start, end, limit=lookback * 2)
            
            if len(bars_x) < MIN_DATA_POINTS_CORRELATION or len(bars_y) < MIN_DATA_POINTS_CORRELATION:
                logger.warning(
                    f"Insufficient data for correlation: X={len(bars_x)}, Y={len(bars_y)} "
                    f"(min: {MIN_DATA_POINTS_CORRELATION})"
                )
                return None
            
            # Align timestamps
            timestamps_x = {bar.timestamp: bar.close for bar in bars_x}
            timestamps_y = {bar.timestamp: bar.close for bar in bars_y}
            
            common_timestamps = sorted(set(timestamps_x.keys()) & set(timestamps_y.keys()))
            
            if len(common_timestamps) < window:
                logger.warning(
                    f"Insufficient aligned data for correlation: {len(common_timestamps)} "
                    f"(window: {window})"
                )
                return None
            
            # Take last 'lookback' aligned points
            common_timestamps = common_timestamps[-lookback:]
            
            # Create aligned price series
            prices_x = np.array([timestamps_x[ts] for ts in common_timestamps])
            prices_y = np.array([timestamps_y[ts] for ts in common_timestamps])
            
            # Compute rolling correlation using pandas
            df = pd.DataFrame({
                'timestamp': common_timestamps,
                'x': prices_x,
                'y': prices_y
            })
            
            # Rolling correlation
            rolling_corr = df['x'].rolling(window=window).corr(df['y'])
            
            # Build correlation history (timestamp, correlation)
            correlation_history: List[Tuple[datetime, float]] = []
            for i, (ts, corr) in enumerate(zip(common_timestamps, rolling_corr)):
                if not np.isnan(corr):
                    correlation_history.append((ts, float(corr)))
            
            # Latest correlation
            latest_corr = correlation_history[-1][1] if correlation_history else 0.0
            
            result = CorrelationResult(
                symbol_x=symbol_x,
                symbol_y=symbol_y,
                interval=interval,
                correlation=latest_corr,
                rolling_window=window,
                correlation_history=correlation_history,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"Correlation {symbol_x}-{symbol_y}: r={latest_corr:.4f}, "
                f"history={len(correlation_history)} points"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Failed to compute rolling correlation {symbol_x}-{symbol_y}: {e}"
            )
            return None
    
    async def compute_correlation_matrix(
        self,
        symbols: List[str],
        interval: str = '1m',
        window: int = CORRELATION_WINDOW
    ) -> Optional[pd.DataFrame]:
        """
        Compute pairwise correlation matrix for multiple symbols.
        
        Returns a correlation matrix suitable for heatmap visualization:
        
                BTCUSDT  ETHUSDT  BNBUSDT
        BTCUSDT    1.00     0.98     0.85
        ETHUSDT    0.98     1.00     0.82
        BNBUSDT    0.85     0.82     1.00
        
        Args:
            symbols: List of symbols to analyze
            interval: Time interval
            window: Rolling window for correlation
        
        Returns:
            pandas DataFrame with correlation matrix, or None if error
        """
        try:
            # Get OHLC data for all symbols
            end = datetime.now()
            start = end - timedelta(hours=24)
            
            price_data = {}
            all_timestamps = set()
            
            for symbol in symbols:
                bars = await self.db.get_ohlc(symbol, interval, start, end, limit=window * 2)
                if len(bars) < window:
                    logger.warning(f"Insufficient data for {symbol} in correlation matrix")
                    continue
                
                price_data[symbol] = {bar.timestamp: bar.close for bar in bars}
                all_timestamps.update(price_data[symbol].keys())
            
            if len(price_data) < 2:
                logger.warning("Need at least 2 symbols with sufficient data")
                return None
            
            # Find common timestamps
            common_timestamps = sorted(all_timestamps)
            
            for symbol in list(price_data.keys()):
                # Remove timestamps not present in this symbol
                price_data[symbol] = {
                    ts: price_data[symbol][ts]
                    for ts in common_timestamps
                    if ts in price_data[symbol]
                }
            
            # Build DataFrame
            df_dict = {}
            for symbol in symbols:
                if symbol in price_data:
                    timestamps = sorted(price_data[symbol].keys())[-window:]
                    df_dict[symbol] = [price_data[symbol][ts] for ts in timestamps]
            
            if not df_dict:
                return None
            
            df = pd.DataFrame(df_dict)
            
            # Compute correlation matrix
            corr_matrix = df.corr()
            
            logger.info(f"Computed correlation matrix for {len(symbols)} symbols")
            
            return corr_matrix
            
        except Exception as e:
            logger.error(f"Failed to compute correlation matrix: {e}")
            return None
