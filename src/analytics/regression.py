"""
Regression analysis for pairs trading.

This module provides OLS (Ordinary Least Squares) regression for computing
hedge ratios and spreads between correlated trading pairs.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
from scipy import stats

from ..storage.database import DatabaseManager
from ..config import DEFAULT_ROLLING_WINDOW, MIN_DATA_POINTS_REGRESSION
from .models import RegressionResult

logger = logging.getLogger(__name__)


class RegressionAnalyzer:
    """
    OLS regression analyzer for pairs trading.
    
    Computes hedge ratios, spreads, and regression statistics for
    identifying trading opportunities in correlated pairs.
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize regression analyzer.
        
        Args:
            db: Database manager instance
        """
        self.db = db
    
    async def compute_ols_hedge_ratio(
        self,
        symbol_x: str,
        symbol_y: str,
        interval: str = '1m',
        window: int = DEFAULT_ROLLING_WINDOW
    ) -> Optional[RegressionResult]:
        """
        Compute OLS regression on LOG RETURNS: r_Y = α + β·r_X + ε
        
        Mathematical Background:
        -----------------------
        This uses LOG RETURNS (industry standard) instead of raw prices:
        - Scale invariance (BTC ~$86k vs ETH ~$3k doesn't matter)
        - Numerical stability (avoids division by near-zero)
        - Additive property (log returns compose properly)
        - Approximately normal distribution
        
        Log return calculation:
        r_t = log(P_t / P_{t-1}) = log(P_t) - log(P_{t-1})
        
        Formulas:
        β (hedge_ratio) = Cov(r_X, r_Y) / Var(r_X)
        α (intercept) = mean(r_Y) - β·mean(r_X)
        R² = 1 - (SS_residual / SS_total)
        
        Trading Interpretation:
        ----------------------
        If β = 1.12:
        - When BTC log-returns +1%, ETH log-returns +1.12%
        - BTC and ETH move together with 1.12× sensitivity
        
        If R² = 0.85:
        - 85% of ETH return variance explained by BTC returns
        - Strong relationship, suitable for pairs trading
        
        Sanity Gates (Professional Standard):
        ------------------------------------
        Regression is SUPPRESSED if:
        - |β| > 3.0 (unrealistic leverage)
        - R² < 0.3 (weak relationship)
        - std_err > |β| (unstable estimate)
        
        Args:
            symbol_x: Independent variable (e.g., "BTCUSDT")
            symbol_y: Dependent variable (e.g., "ETHUSDT")
            interval: Time interval for OHLC data
            window: Number of bars to use
        
        Returns:
            RegressionResult or None if insufficient/invalid data
        """
        try:
            # Get OHLC data for both symbols
            end = datetime.now()
            start = end - timedelta(hours=24)
            
            bars_x = await self.db.get_ohlc(symbol_x, interval, start, end, limit=window * 2)
            bars_y = await self.db.get_ohlc(symbol_y, interval, start, end, limit=window * 2)
            
            if len(bars_x) < MIN_DATA_POINTS_REGRESSION or len(bars_y) < MIN_DATA_POINTS_REGRESSION:
                logger.warning(
                    f"Insufficient data for regression: X={len(bars_x)}, Y={len(bars_y)} "
                    f"(min: {MIN_DATA_POINTS_REGRESSION})"
                )
                return None
            
            # ============================================================
            # CRITICAL: Strict timestamp alignment
            # ============================================================
            timestamps_x = {bar.timestamp: bar.close for bar in bars_x}
            timestamps_y = {bar.timestamp: bar.close for bar in bars_y}
            
            common_timestamps = sorted(set(timestamps_x.keys()) & set(timestamps_y.keys()))
            
            if len(common_timestamps) < MIN_DATA_POINTS_REGRESSION + 1:
                logger.warning(
                    f"Insufficient aligned data: {len(common_timestamps)} timestamps "
                    f"(min: {MIN_DATA_POINTS_REGRESSION + 1})"
                )
                return None
            
            # Take last N aligned points
            common_timestamps = common_timestamps[-window:]
            
            # Extract aligned prices - STRICT synchronization
            prices_x = np.array([timestamps_x[ts] for ts in common_timestamps])
            prices_y = np.array([timestamps_y[ts] for ts in common_timestamps])
            
            # Validation: Same length, no NaN/Inf
            assert len(prices_x) == len(prices_y), "Price arrays must be same length"
            if not (np.all(np.isfinite(prices_x)) and np.all(np.isfinite(prices_y))):
                logger.error("Non-finite prices detected, aborting regression")
                return None
            
            # ============================================================
            # INDUSTRY FIX: Use LOG RETURNS (not percentage returns)
            # ============================================================
            # Log returns: r_t = log(P_t) - log(P_{t-1})
            log_prices_x = np.log(prices_x)
            log_prices_y = np.log(prices_y)
            
            returns_x = np.diff(log_prices_x)
            returns_y = np.diff(log_prices_y)
            
            # Validation: Check for NaN/Inf after log
            valid_mask = np.isfinite(returns_x) & np.isfinite(returns_y)
            returns_x_clean = returns_x[valid_mask]
            returns_y_clean = returns_y[valid_mask]
            
            if len(returns_x_clean) < MIN_DATA_POINTS_REGRESSION:
                logger.warning(
                    f"Insufficient valid returns after filtering: {len(returns_x_clean)} "
                    f"(removed {len(returns_x) - len(returns_x_clean)} invalid points)"
                )
                return None
            
            # Check for near-zero variance (causes unstable regression)
            if np.std(returns_x_clean) < 1e-8 or np.std(returns_y_clean) < 1e-8:
                logger.warning("Near-zero return variance detected, regression unstable")
                return None
            
            # Perform OLS regression on LOG RETURNS
            # Direction: r_Y = α + β·r_X (Y depends on X)
            slope, intercept, r_value, p_value, std_err = stats.linregress(returns_x_clean, returns_y_clean)
            
            # R-squared
            r_squared = r_value ** 2
            
            # ============================================================
            # SANITY GATES (Professional Standard)
            # ============================================================
            # Gate 1: Beta must be realistic
            if abs(slope) > 3.0:
                logger.warning(
                    f"Beta unrealistic: β={slope:.2f} (|β| > 3.0). "
                    f"Likely data misalignment or numerical issue. Suppressing regression."
                )
                return None
            
            # Gate 2: R² must show meaningful relationship
            if r_squared < 0.3:
                logger.warning(
                    f"R² too low: {r_squared:.4f} (< 0.3). "
                    f"Weak relationship, not suitable for pairs trading. Suppressing regression."
                )
                return None
            
            # Gate 3: Standard error must be reasonable
            if std_err > abs(slope):
                logger.warning(
                    f"Standard error too large: σ(β)={std_err:.4f} > |β|={abs(slope):.4f}. "
                    f"Estimate is unstable. Suppressing regression."
                )
                return None
            
            # Compute residuals (log return spread)
            predicted_y = intercept + slope * returns_x_clean
            residuals = (returns_y_clean - predicted_y).tolist()
            
            result = RegressionResult(
                symbol_x=symbol_x,
                symbol_y=symbol_y,
                interval=interval,
                hedge_ratio=slope,         # Beta (return sensitivity)
                intercept=intercept,        # Should be near zero
                r_squared=r_squared,        # Should be 0.3-0.9
                std_error=std_err,          # Should be < |beta|
                residuals=residuals,        # Log return spread
                timestamp=datetime.now()
            )
            
            logger.info(
                f"✅ Log-returns regression {symbol_x}->{symbol_y}: "
                f"β={slope:.4f}, R²={r_squared:.4f}, σ(β)={std_err:.4f}, n={len(returns_x_clean)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to compute log-returns regression {symbol_x}->{symbol_y}: {e}")
            return None
    
    async def compute_spread(
        self,
        symbol_x: str,
        symbol_y: str,
        hedge_ratio: float,
        interval: str = '1m',
        window: int = DEFAULT_ROLLING_WINDOW
    ) -> List[float]:
        """
        Compute log-return spread: spread = r_Y - β·r_X
        
        The spread represents the regression residual on LOG RETURNS and is used
        for mean-reversion trading strategies.
        
        Trading Logic:
        --------------
        - If z-score(spread) > 2: Short the spread (r_Y > expected)
        - If z-score(spread) < -2: Long the spread (r_Y < expected)
        - Profit when spread reverts to mean
        
        Note: This uses LOG RETURNS, consistent with the regression methodology.
        
        Args:
            symbol_x: First symbol
            symbol_y: Second symbol
            hedge_ratio: Beta from log-returns regression
            interval: Time interval
            window: Number of bars
        
        Returns:
            List of log-return spread values
        """
        try:
            # Get aligned prices (same logic as regression)
            end = datetime.now()
            start = end - timedelta(hours=24)
            
            bars_x = await self.db.get_ohlc(symbol_x, interval, start, end, limit=window * 2)
            bars_y = await self.db.get_ohlc(symbol_y, interval, start, end, limit=window * 2)
            
            if not bars_x or not bars_y:
                logger.warning(f"No data for spread calculation: {symbol_x}, {symbol_y}")
                return []
            
            # Strict timestamp alignment
            timestamps_x = {bar.timestamp: bar.close for bar in bars_x}
            timestamps_y = {bar.timestamp: bar.close for bar in bars_y}
            
            common_timestamps = sorted(set(timestamps_x.keys()) & set(timestamps_y.keys()))
            common_timestamps = common_timestamps[-window:]
            
            if len(common_timestamps) < 2:
                return []
            
            # Extract aligned prices
            prices_x = np.array([timestamps_x[ts] for ts in common_timestamps])
            prices_y = np.array([timestamps_y[ts] for ts in common_timestamps])
            
            # Calculate LOG returns (consistent with regression)
            log_prices_x = np.log(prices_x)
            log_prices_y = np.log(prices_y)
            
            returns_x = np.diff(log_prices_x)
            returns_y = np.diff(log_prices_y)
            
            # Compute log-return spread: spread = r_Y - β·r_X
            spreads = []
            for i in range(len(returns_x)):
                if np.isfinite(returns_x[i]) and np.isfinite(returns_y[i]):
                    spread = returns_y[i] - (hedge_ratio * returns_x[i])
                    spreads.append(spread)
            
            logger.debug(f"Computed {len(spreads)} log-return spread values for {symbol_x}-{symbol_y}")
            
            return spreads
            
        except Exception as e:
            logger.error(f"Failed to compute log-return spread: {e}")
            return []
