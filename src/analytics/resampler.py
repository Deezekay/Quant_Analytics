"""
Time-series resampling for tick data to OHLC bars.

This module converts high-frequency tick data into OHLC (candlestick) bars
at various time intervals (1s, 1m, 5m, etc.) for charting and analysis.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from ..ingestion.binance_websocket import TradeData
from ..storage.database import DatabaseManager
from .models import OHLCData

logger = logging.getLogger(__name__)


class TickResampler:
    """
    Real-time tick-to-OHLC resampler with interval boundary handling.
    
    Buffers incoming ticks by time interval buckets, computes OHLC bars
    when intervals complete, and persists to database.
    
    Key challenge: Determining when an interval is "complete"
    - We can't know an interval is done until we see a tick from the NEXT interval
    - Example: 12:18:57 bar completes when we see a tick at 12:18:58
    
    Attributes:
        db: Database manager instance
        intervals: List of time intervals to generate (e.g., ['1s', '1m', '5m'])
        buffers: Nested dict structure {symbol: {interval: {bucket_start: [ticks]}}}
    """
    
    def __init__(self, db: DatabaseManager, intervals: List[str]):
        """
        Initialize resampler.
        
        Args:
            db: Database manager for persisting OHLC bars
            intervals: List of intervals to generate (e.g., ['1s', '1m', '5m'])
        """
        self.db = db
        self.intervals = intervals
        
        # Buffer structure: {symbol: {interval: {bucket_start: [ticks]}}}
        # Example: {'BTCUSDT': {'1s': {datetime(...): [tick1, tick2, ...]}}}
        self.buffers: Dict[str, Dict[str, Dict[datetime, List[TradeData]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
    
    def get_interval_bucket(self, timestamp: datetime, interval: str) -> datetime:
        """
        Calculate the start of the interval bucket for a given timestamp.
        
        Critical for aligning ticks to correct OHLC bars.
        
        Args:
            timestamp: Tick timestamp
            interval: Interval string ('1s', '1m', '5m', '15m', '1h')
        
        Returns:
            Start of the interval bucket (rounded down)
        
        Examples:
            >>> ts = datetime(2025, 12, 16, 12, 18, 57, 486000)
            >>> get_interval_bucket(ts, '1s')
            datetime(2025, 12, 16, 12, 18, 57, 0)  # 12:18:57.000
            
            >>> get_interval_bucket(ts, '1m')
            datetime(2025, 12, 16, 12, 18, 0, 0)   # 12:18:00.000
            
            >>> get_interval_bucket(ts, '5m')
            datetime(2025, 12, 16, 12, 15, 0, 0)   # 12:15:00.000 (not 12:18!)
        """
        if interval == '1s':
            # Round down to nearest second
            return timestamp.replace(microsecond=0)
        
        elif interval == '1m':
            # Round down to nearest minute
            return timestamp.replace(second=0, microsecond=0)
        
        elif interval == '5m':
            # Round down to nearest 5-minute mark (0, 5, 10, 15, ...)
            minute = (timestamp.minute // 5) * 5
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        
        elif interval == '15m':
            # Round down to nearest 15-minute mark (0, 15, 30, 45)
            minute = (timestamp.minute // 15) * 15
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        
        elif interval == '1h':
            # Round down to nearest hour
            return timestamp.replace(minute=0, second=0, microsecond=0)
        
        else:
            raise ValueError(f"Unsupported interval: {interval}")
    
    async def process_tick(self, tick: TradeData) -> None:
        """
        Process incoming tick: persist to DB and update OHLC buffers.
        
        Flow:
        1. Save tick to database (batched)
        2. For each interval (1s, 1m, 5m):
           a. Determine which bucket this tick belongs to
           b. Add tick to that bucket's buffer
           c. Check if any PREVIOUS buckets are now complete
           d. If complete, compute OHLC and save to DB
        
        Args:
            tick: Incoming trade data
        """
        try:
            # 1. Persist tick to database (uses batch optimization)
            await self.db.insert_tick(tick)
            
            # 2. Process for each interval
            for interval in self.intervals:
                await self._process_tick_for_interval(tick, interval)
                
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    async def _process_tick_for_interval(self, tick: TradeData, interval: str) -> None:
        """
        Process tick for a specific interval.
        
        Args:
            tick: Incoming trade data
            interval: Time interval to process (e.g., '1s')
        """
        # Determine which bucket this tick belongs to
        bucket_start = self.get_interval_bucket(tick.timestamp, interval)
        
        # Add tick to buffer
        self.buffers[tick.symbol][interval][bucket_start].append(tick)
        
        # Check if we can finalize any completed buckets
        await self._finalize_completed_buckets(tick.symbol, interval, tick.timestamp)
    
    async def _finalize_completed_buckets(
        self,
        symbol: str,
        interval: str,
        current_time: datetime
    ) -> None:
        """
        Finalize and persist any OHLC bars that are now complete.
        
        A bucket is "complete" when we receive a tick from a NEWER bucket.
        
        Example:
            Current time: 12:18:58.234
            Current 1s bucket: 12:18:58.000
            
            Buffered buckets:
              12:18:55.000 ← Complete (older than current) → Finalize!
              12:18:56.000 ← Complete (older than current) → Finalize!
              12:18:57.000 ← Complete (older than current) → Finalize!
              12:18:58.000 ← ACTIVE (current bucket) → Keep buffering
        
        Args:
            symbol: Trading symbol
            interval: Time interval
            current_time: Timestamp of the current tick
        """
        current_bucket = self.get_interval_bucket(current_time, interval)
        
        # Get all buffered buckets for this symbol/interval
        symbol_interval_buffers = self.buffers[symbol][interval]
        
        # Find buckets that are older than current bucket (i.e., complete)
        completed_buckets = [
            bucket_start
            for bucket_start in symbol_interval_buffers.keys()
            if bucket_start < current_bucket
        ]
        
        # Finalize each completed bucket
        for bucket_start in completed_buckets:
            ticks = symbol_interval_buffers[bucket_start]
            
            # Compute OHLC from ticks
            ohlc = self._compute_ohlc(ticks, symbol, interval, bucket_start)
            
            if ohlc:  # Skip empty intervals
                # Persist to database
                await self.db.insert_ohlc(symbol, interval, ohlc)
                
                logger.info(
                    f"Finalized {interval} bar: {symbol} @ {bucket_start.strftime('%H:%M:%S')} "
                    f"(O: ${ohlc.open:.2f}, H: ${ohlc.high:.2f}, L: ${ohlc.low:.2f}, C: ${ohlc.close:.2f}, "
                    f"V: {ohlc.volume:.6f}, Trades: {ohlc.trade_count})"
                )
            
            # Remove from buffer (free memory)
            del symbol_interval_buffers[bucket_start]
    
    def _compute_ohlc(
        self,
        ticks: List[TradeData],
        symbol: str,
        interval: str,
        bucket_start: datetime
    ) -> OHLCData:
        """
        Compute OHLC bar from a list of ticks.
        
        OHLC definition:
        - Open: First tick's price
        - High: Maximum tick price
        - Low: Minimum tick price
        - Close: Last tick's price
        - Volume: Sum of tick sizes
        - Trade count: Number of ticks
        
        Args:
            ticks: List of trade data in the interval
            symbol: Trading symbol
            interval: Time interval
            bucket_start: Start of the interval bucket
        
        Returns:
            OHLCData object, or None if no ticks
        """
        if not ticks:
            return None  # Skip empty intervals
        
        # Sort ticks by timestamp (should already be sorted, but be safe)
        sorted_ticks = sorted(ticks, key=lambda t: t.timestamp)
        
        # Extract prices for min/max calculation
        prices = [tick.price for tick in sorted_ticks]
        
        return OHLCData(
            symbol=symbol,
            interval=interval,
            timestamp=bucket_start,
            open=sorted_ticks[0].price,      # First tick
            high=max(prices),                # Highest price
            low=min(prices),                 # Lowest price
            close=sorted_ticks[-1].price,    # Last tick
            volume=sum(tick.size for tick in sorted_ticks),
            trade_count=len(sorted_ticks)
        )
    
    async def flush_remaining(self) -> None:
        """
        Flush all remaining buffered intervals on shutdown.
        
        Called during graceful shutdown to ensure no data loss.
        Finalizes all buckets regardless of whether they're "complete".
        """
        logger.info("Flushing remaining OHLC buffers...")
        
        for symbol in self.buffers:
            for interval in self.buffers[symbol]:
                for bucket_start, ticks in list(self.buffers[symbol][interval].items()):
                    ohlc = self._compute_ohlc(ticks, symbol, interval, bucket_start)
                    
                    if ohlc:
                        await self.db.insert_ohlc(symbol, interval, ohlc)
                        logger.info(f"Flushed final {interval} bar: {symbol} @ {bucket_start}")
        
        logger.info("OHLC buffer flush complete")
