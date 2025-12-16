"""
Database management for crypto analytics platform.

This module provides async database operations with SQLite,
including tick storage, OHLC persistence, and batch insert optimization.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite

from ..ingestion.binance_websocket import TradeData
from ..analytics.models import OHLCData
from ..config import TICK_BATCH_SIZE, TICK_BATCH_TIMEOUT

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Async SQLite database manager with batch insert optimization.
    
    Manages the lifecycle of database connections, provides CRUD operations
    for ticks and OHLC data, and implements batch insert buffering for
    high-throughput write performance.
    
    Attributes:
        db_path: Path to SQLite database file
        conn: Active database connection (None when closed)
        tick_buffer: In-memory buffer for batching tick inserts
        last_flush: Timestamp of last batch flush
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file (created if doesn't exist)
        """
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        self.tick_buffer: List[TradeData] = []
        self.last_flush: datetime = datetime.now()
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """
        Initialize database connection and create schema.
        
        Creates tables and indexes if they don't exist.
        Safe to call multiple times (idempotent).
        """
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            
            # Enable WAL mode for better concurrent access
            await self.conn.execute("PRAGMA journal_mode=WAL")
            
            # Create tables
            await self._create_tables()
            
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """Create database schema (tables and indexes)."""
        
        # Ticks table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                size REAL NOT NULL
            )
        """)
        
        # Indexes for ticks
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticks_symbol_timestamp 
            ON ticks(symbol, timestamp DESC)
        """)
        
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticks_symbol_id 
            ON ticks(symbol, id DESC)
        """)
        
        # OHLC table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlc (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                trade_count INTEGER NOT NULL,
                PRIMARY KEY (symbol, interval, timestamp)
            )
        """)
        
        # Index for OHLC
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_interval_timestamp 
            ON ohlc(symbol, interval, timestamp DESC)
        """)
        
        await self.conn.commit()
    
    async def insert_tick(self, tick: TradeData) -> None:
        """
        Insert tick with batch optimization.
        
        Ticks are buffered in memory and flushed when:
        - Buffer reaches TICK_BATCH_SIZE (e.g., 100 ticks), OR
        - TICK_BATCH_TIMEOUT seconds have elapsed (e.g., 1.0 second)
        
        This provides ~100x performance improvement over individual inserts.
        
        Args:
            tick: Trade data to insert
        """
        self.tick_buffer.append(tick)
        
        # Check flush conditions
        buffer_full = len(self.tick_buffer) >= TICK_BATCH_SIZE
        time_elapsed = (datetime.now() - self.last_flush).total_seconds()
        timeout_reached = time_elapsed >= TICK_BATCH_TIMEOUT
        
        if buffer_full or timeout_reached:
            await self._flush_ticks()
    
    async def _flush_ticks(self) -> None:
        """Flush buffered ticks to database in a single transaction."""
        if not self.tick_buffer:
            return
        
        try:
            # Prepare batch data
            batch_data = [
                (tick.symbol, tick.timestamp.isoformat(), tick.price, tick.size)
                for tick in self.tick_buffer
            ]
            
            # Batch insert
            await self.conn.executemany(
                "INSERT INTO ticks (symbol, timestamp, price, size) VALUES (?, ?, ?, ?)",
                batch_data
            )
            await self.conn.commit()
            
            logger.debug(f"Flushed {len(self.tick_buffer)} ticks to database")
            
            # Clear buffer
            self.tick_buffer.clear()
            self.last_flush = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to flush ticks: {e}")
            # Don't clear buffer on error - will retry on next flush
    
    async def insert_ohlc(self, symbol: str, interval: str, ohlc: OHLCData) -> None:
        """
        Insert OHLC bar into database.
        
        Uses INSERT OR REPLACE to handle duplicate intervals
        (prevents errors if resampler processes same interval twice).
        
        Args:
            symbol: Trading symbol
            interval: Time interval (e.g., '1s', '1m')
            ohlc: OHLC data to insert
        """
        try:
            await self.conn.execute(
                """
                INSERT OR REPLACE INTO ohlc 
                (symbol, interval, timestamp, open, high, low, close, volume, trade_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    interval,
                    ohlc.timestamp.isoformat(),
                    ohlc.open,
                    ohlc.high,
                    ohlc.low,
                    ohlc.close,
                    ohlc.volume,
                    ohlc.trade_count
                )
            )
            await self.conn.commit()
            
            logger.debug(f"Inserted OHLC: {symbol} {interval} @ {ohlc.timestamp}")
            
        except Exception as e:
            logger.error(f"Failed to insert OHLC: {e}")
    
    async def get_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: Optional[int] = None
    ) -> List[TradeData]:
        """
        Query ticks by symbol and time range.
        
        Args:
            symbol: Trading symbol to query
            start: Start of time range (inclusive)
            end: End of time range (inclusive)
            limit: Maximum number of ticks to return (optional)
        
        Returns:
            List of TradeData objects, ordered by timestamp ascending
        """
        try:
            query = """
                SELECT symbol, timestamp, price, size
                FROM ticks
                WHERE symbol = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            async with self.conn.execute(
                query,
                (symbol, start.isoformat(), end.isoformat())
            ) as cursor:
                rows = await cursor.fetchall()
            
            # Convert to TradeData objects
            ticks = [
                TradeData(
                    symbol=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    price=row[2],
                    size=row[3]
                )
                for row in rows
            ]
            
            return ticks
            
        except Exception as e:
            logger.error(f"Failed to query ticks: {e}")
            return []
    
    async def get_ohlc(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: Optional[int] = None
    ) -> List[OHLCData]:
        """
        Query OHLC bars by symbol, interval, and time range.
        
        Args:
            symbol: Trading symbol to query
            interval: Time interval (e.g., '1s', '1m', '5m')
            start: Start of time range (inclusive)
            end: End of time range (inclusive)
            limit: Maximum number of bars to return (optional)
        
        Returns:
            List of OHLCData objects, ordered by timestamp ascending
        """
        try:
            query = """
                SELECT symbol, interval, timestamp, open, high, low, close, volume, trade_count
                FROM ohlc
                WHERE symbol = ? AND interval = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            async with self.conn.execute(
                query,
                (symbol, interval, start.isoformat(), end.isoformat())
            ) as cursor:
                rows = await cursor.fetchall()
            
            # Convert to OHLCData objects
            bars = [
                OHLCData(
                    symbol=row[0],
                    interval=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    open=row[3],
                    high=row[4],
                    low=row[5],
                    close=row[6],
                    volume=row[7],
                    trade_count=row[8]
                )
                for row in rows
            ]
            
            return bars
            
        except Exception as e:
            logger.error(f"Failed to query OHLC: {e}")
            return []
    
    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the most recent tick price for a symbol.
        
        Optimized query using the idx_ticks_symbol_id index.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Latest price, or None if no ticks exist
        """
        try:
            async with self.conn.execute(
                "SELECT price FROM ticks WHERE symbol = ? ORDER BY id DESC LIMIT 1",
                (symbol,)
            ) as cursor:
                row = await cursor.fetchone()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Failed to get latest price: {e}")
            return None
    
    async def close(self) -> None:
        """
        Close database connection.
        
        Flushes any remaining buffered ticks before closing.
        """
        try:
            # Flush remaining ticks
            await self._flush_ticks()
            
            # Close connection
            if self.conn:
                await self.conn.close()
                logger.info("Database connection closed")
                
        except Exception as e:
            logger.error(f"Error closing database: {e}")
