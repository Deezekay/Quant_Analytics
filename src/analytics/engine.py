"""
Analytics Engine - Orchestrator for all quantitative computations.

This module coordinates all analytics components (statistics, regression,
stationarity, correlation) and provides a unified interface with caching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ..storage.database import DatabaseManager
from ..config import (
    ANALYTICS_UPDATE_INTERVAL,
    CACHE_TTL_STATS,
    CACHE_TTL_REGRESSION,
    CACHE_TTL_ADF,
    CACHE_TTL_CORRELATION,
    DEFAULT_SYMBOL_PAIRS,
)
from .statistics import StatisticsCalculator
from .regression import RegressionAnalyzer
from .stationarity import StationarityAnalyzer
from .correlation import CorrelationAnalyzer

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Centralized analytics engine orchestrator.
    
    Coordinates all analytics modules and provides:
    - Unified API for accessing analytics
    - TTL-based caching to reduce computation overhead
    - Background update tasks for pre-computation
    - Error handling and graceful degradation
    """
    
    def __init__(self, db: DatabaseManager):
        """
        Initialize analytics engine.
        
        Args:
            db: Database manager instance
        """
        self.db = db
        
        # Initialize sub-analyzers
        self.stats_calc = StatisticsCalculator(db)
        self.regression = RegressionAnalyzer(db)
        self.stationarity = StationarityAnalyzer(db)
        self.correlation = CorrelationAnalyzer(db)
        
        # Cache storage: {cache_key: result}
        self._cache: Dict[str, Any] = {}
        
        # Cache timestamps: {cache_key: datetime}
        self._cache_time: Dict[str, datetime] = {}
        
        logger.info("Analytics engine initialized")
    
    def _get_cache_key(self, category: str, *args) -> str:
        """Generate cache key from category and arguments."""
        return f"{category}:{'_'.join(str(arg) for arg in args)}"
    
    def _is_cache_valid(self, cache_key: str, ttl: float) -> bool:
        """Check if cached value is still valid (within TTL)."""
        if cache_key not in self._cache_time:
            return False
        
        age = (datetime.now() - self._cache_time[cache_key]).total_seconds()
        return age < ttl
    
    def _get_cached(self, cache_key: str, ttl: float) -> Optional[Any]:
        """Get cached value if valid, otherwise None."""
        if not self._is_cache_valid(cache_key, ttl):
            return None
        
        return self._cache.get(cache_key)
    
    def _set_cache(self, cache_key: str, value: Any) -> None:
        """Store value in cache with current timestamp."""
        self._cache[cache_key] = value
        self._cache_time[cache_key] = datetime.now()
    
    async def get_symbol_analytics(
        self,
        symbol: str,
        interval: str = '1m',
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get all analytics for a single symbol.
        
        Returns price statistics, volume statistics, and latest update time.
        Results are cached with CACHE_TTL_STATS TTL.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Time interval ('1m', '5m', etc.)
            force_refresh: If True, bypass cache and recompute
        
        Returns:
            Dictionary containing:
            {
                'stats': PriceStats object,
                'volume_stats': VolumeStats object,
                'last_update': datetime
            }
            
            Or None if computation fails
        """
        try:
            cache_key = self._get_cache_key('symbol_analytics', symbol, interval)
            
            # Check cache (unless force_refresh)
            if not force_refresh:
                cached = self._get_cached(cache_key, CACHE_TTL_STATS)
                if cached:
                    logger.debug(f"Cache hit: symbol analytics for {symbol}")
                    return cached
            
            # Compute fresh analytics
            logger.debug(f"Computing fresh symbol analytics for {symbol}")
            
            stats = await self.stats_calc.compute_price_stats(symbol, interval)
            volume_stats = await self.stats_calc.compute_volume_stats(symbol, interval)
            
            if not stats and not volume_stats:
                logger.warning(f"No analytics available for {symbol}")
                return None
            
            result = {
                'stats': stats,
                'volume_stats': volume_stats,
                'last_update': datetime.now()
            }
            
            # Cache result
            self._set_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get symbol analytics for {symbol}: {e}")
            return None
    
    async def get_pairs_analytics(
        self,
        symbol_x: str,
        symbol_y: str,
        interval: str = '1m',
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete pairs trading analytics.
        
        Computes:
        1. OLS regression (hedge ratio, R²)
        2. Spread (residuals)
        3. Z-score of spread
        4. ADF test on spread (stationarity)
        5. Rolling correlation
        
        Results are cached with CACHE_TTL_REGRESSION TTL.
        
        Args:
            symbol_x: First symbol (independent variable)
            symbol_y: Second symbol (dependent variable)
            interval: Time interval
            force_refresh: If True, bypass cache
        
        Returns:
            Dictionary containing:
            {
                'regression': RegressionResult,
                'spread': List[float],
                'z_score': List[float],
                'adf_test': ADFTestResult,
                'correlation': CorrelationResult,
                'last_update': datetime
            }
            
            Or None if insufficient data or computation fails
        """
        try:
            cache_key = self._get_cache_key('pairs_analytics', symbol_x, symbol_y, interval)
            
            # Check cache
            if not force_refresh:
                cached = self._get_cached(cache_key, CACHE_TTL_REGRESSION)
                if cached:
                    logger.debug(f"Cache hit: pairs analytics for {symbol_x}-{symbol_y}")
                    return cached
            
            # Compute fresh analytics
            logger.info(f"Computing fresh pairs analytics: {symbol_x}-{symbol_y}")
            
            # Step 1: OLS Regression
            regression_result = await self.regression.compute_ols_hedge_ratio(
                symbol_x, symbol_y, interval
            )
            
            if not regression_result:
                logger.warning(f"No regression result for {symbol_x}-{symbol_y}")
                return None
            
            # Step 2: Compute spread using hedge ratio
            spread = await self.regression.compute_spread(
                symbol_x, symbol_y, regression_result.hedge_ratio, interval
            )
            
            if not spread or len(spread) < 20:
                logger.warning(f"Insufficient spread data for {symbol_x}-{symbol_y}")
                return None
            
            # Step 3: Z-score of spread
            z_scores = await self.stats_calc.compute_zscore(spread, window=20)
            
            # Step 4: ADF test on spread (is it stationary?)
            adf_result = await self.stationarity.adf_test_on_values(
                spread,
                label=f"{symbol_x}-{symbol_y} spread"
            )
            
            # Step 5: Rolling correlation
            corr_result = await self.correlation.compute_rolling_correlation(
                symbol_x, symbol_y, interval
            )
            
            # Build result
            result = {
                'regression': regression_result,
                'spread': spread,
                'z_score': z_scores,
                'adf_test': adf_result,
                'correlation': corr_result,
                'last_update': datetime.now()
            }
            
            # Cache result
            self._set_cache(cache_key, result)
            
            logger.info(
                f"Pairs analytics computed: {symbol_x}-{symbol_y} | "
                f"hedge_ratio={regression_result.hedge_ratio:.6f}, "
                f"R²={regression_result.r_squared:.4f}, "
                f"stationary={adf_result.is_stationary if adf_result else 'N/A'}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get pairs analytics {symbol_x}-{symbol_y}: {e}")
            return None
    
    async def update_all_analytics(self) -> None:
        """
        Update analytics for all configured symbols and pairs.
        
        Called by background task to pre-populate cache.
        """
        try:
            logger.info("Starting analytics update cycle")
            
            # Get symbols from config (currently BTCUSDT, ETHUSDT)
            from ..config import SYMBOLS
            
            # Update single-symbol analytics
            for symbol in SYMBOLS:
                await self.get_symbol_analytics(symbol, interval='1m', force_refresh=True)
            
            # Update pairs analytics
            for symbol_x, symbol_y in DEFAULT_SYMBOL_PAIRS:
                await self.get_pairs_analytics(symbol_x, symbol_y, interval='1m', force_refresh=True)
            
            logger.info("Analytics update cycle complete")
            
        except Exception as e:
            logger.error(f"Error in analytics update cycle: {e}")
    
    async def update_analytics_loop(self, interval_seconds: int = ANALYTICS_UPDATE_INTERVAL) -> None:
        """
        Background task to periodically update analytics.
        
        Runs continuously, updating cache every 'interval_seconds'.
        Should be started as an async task in main.py.
        
        Args:
            interval_seconds: Delay between update cycles
        """
        logger.info(f"Starting analytics update loop (interval: {interval_seconds}s)")
        
        # Wait for initial data to accumulate
        await asyncio.sleep(60)  # Wait 1 minute for data
        logger.info("Initial data collection period complete, starting analytics updates")
        
        while True:
            try:
                await self.update_all_analytics()
            except Exception as e:
                logger.error(f"Analytics update loop error: {e}")
            
            await asyncio.sleep(interval_seconds)
