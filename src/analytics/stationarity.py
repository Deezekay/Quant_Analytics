"""
Stationarity testing for time series analysis.

This module provides Augmented Dickey-Fuller (ADF) testing to determine
if a time series is stationary - a critical requirement for mean-reversion
trading strategies.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
from statsmodels.tsa.stattools import adfuller

from ..storage.database import DatabaseManager
from ..config import MIN_DATA_POINTS_ADF
from .models import ADFTestResult

logger = logging.getLogger(__name__)


class StationarityAnalyzer:
    """
    Stationarity analyzer using Augmented Dickey-Fuller test.
    
    Tests whether a time series is stationary (mean-reverting) or
    non-stationary (has a unit root, random walk).
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize stationarity analyzer.
        
        Args:
            db: Database manager instance
        """
        self.db = db
    
    async def adf_test(
        self,
        symbol: str,
        interval: str = '1m',
        window: int = MIN_DATA_POINTS_ADF * 2
    ) -> Optional[ADFTestResult]:
        """
        Perform Augmented Dickey-Fuller test on price series.
        
        Mathematical Background:
        -----------------------
        ADF tests the null hypothesis H₀: series has a unit root (non-stationary)
        
        Test equation: ΔY_t = α + β·Y_{t-1} + Σ(γ_i·ΔY_{t-i}) + ε_t
        
        Where:
        - ΔY_t = Y_t - Y_{t-1} (first difference)
        - β is the coefficient of interest
        - Test statistic τ = β / SE(β)
        
        Decision Rule:
        - If p-value < 0.05: Reject H₀ → Series IS stationary ✅
        - If p-value ≥ 0.05: Cannot reject H₀ → Series may be non-stationary
        
        Or using critical values:
        - If test_stat < critical_value_5%: Stationary
        - If test_stat > critical_value_5%: Non-stationary
        
        Trading Significance:
        --------------------
        - Stationary series: Mean-reverting → suitable for pairs trading
        - Non-stationary series: Random walk → NOT suitable for mean reversion
        
        Args:
            symbol: Trading symbol to test
            interval: Time interval
            window: Number of bars (min 50 for statistical power)
        
        Returns:
            ADFTestResult or None if insufficient data
        """
        try:
            # Get OHLC data
            end = datetime.now()
            start = end - timedelta(hours=24)
            
            bars = await self.db.get_ohlc(symbol, interval, start, end, limit=window)
            
            if len(bars) < MIN_DATA_POINTS_ADF:
                logger.warning(
                    f"Insufficient data for ADF test: {len(bars)} bars "
                    f"(min: {MIN_DATA_POINTS_ADF})"
                )
                return None
            
            # Extract close prices
            prices = np.array([bar.close for bar in bars])
            
            # Perform ADF test
            result = adfuller(prices, autolag='AIC')
            test_statistic, p_value, _, _, critical_values, _ = result
            
            # Determine stationarity
            is_stationary = p_value < 0.05
            
            # Generate interpretation
            interpretation = self._generate_interpretation(
                symbol, test_statistic, p_value, critical_values, is_stationary
            )
            
            adf_result = ADFTestResult(
                symbol=symbol,
                test_statistic=test_statistic,
                p_value=p_value,
                critical_values={k: float(v) for k, v in critical_values.items()},
                is_stationary=is_stationary,
                interpretation=interpretation,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"ADF test {symbol}: p={p_value:.4f}, "
                f"stationary={is_stationary}, n={len(prices)}"
            )
            
            return adf_result
            
        except Exception as e:
            logger.error(f"Failed to perform ADF test on {symbol}: {e}")
            return None
    
    async def adf_test_on_values(
        self,
        values: List[float],
        label: str = "spread"
    ) -> Optional[ADFTestResult]:
        """
        Perform ADF test on arbitrary values (e.g., spread).
        
        Use case: Test if trading spread is stationary
        
        Args:
            values: List of values to test
            label: Description for logging/reporting
        
        Returns:
            ADFTestResult or None if insufficient data
        """
        try:
            if len(values) < MIN_DATA_POINTS_ADF:
                logger.warning(
                    f"Insufficient data for ADF test on {label}: {len(values)} values "
                    f"(min: {MIN_DATA_POINTS_ADF})"
                )
                return None
            
            # Remove NaN values
            clean_values = [v for v in values if not np.isnan(v)]
            
            if len(clean_values) < MIN_DATA_POINTS_ADF:
                logger.warning(f"Insufficient non-NaN values for ADF test: {len(clean_values)}")
                return None
            
            # Perform ADF test
            result = adfuller(clean_values, autolag='AIC')
            test_statistic, p_value, _, _, critical_values, _ = result
            
            is_stationary = p_value < 0.05
            
            interpretation = self._generate_interpretation(
                label, test_statistic, p_value, critical_values, is_stationary
            )
            
            adf_result = ADFTestResult(
                symbol=label,
                test_statistic=test_statistic,
                p_value=p_value,
                critical_values={k: float(v) for k, v in critical_values.items()},
                is_stationary=is_stationary,
                interpretation=interpretation,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"ADF test on {label}: p={p_value:.4f}, "
                f"stationary={is_stationary}, n={len(clean_values)}"
            )
            
            return adf_result
            
        except Exception as e:
            logger.error(f"Failed to perform ADF test on values: {e}")
            return None
    
    def _generate_interpretation(
        self,
        label: str,
        test_stat: float,
        p_value: float,
        critical_values: dict,
        is_stationary: bool
    ) -> str:
        """Generate human-readable interpretation of ADF test."""
        
        if is_stationary:
            interpretation = (
                f"{label} is STATIONARY (p-value: {p_value:.4f} < 0.05). "
                f"The series exhibits mean-reversion, suitable for pairs trading. "
                f"Test statistic ({test_stat:.4f}) is below the 5% critical value "
                f"({critical_values.get('5%', 'N/A'):.4f})."
            )
        else:
            interpretation = (
                f"{label} is NON-STATIONARY (p-value: {p_value:.4f} ≥ 0.05). "
                f"The series may have a unit root (random walk). "
                f"Not recommended for mean-reversion strategies. "
                f"Consider: (1) differencing the series, (2) using a different pair, "
                f"or (3) increasing the sample size."
            )
        
        return interpretation
