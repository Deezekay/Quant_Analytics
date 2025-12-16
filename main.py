"""
Main entry point for the crypto analytics platform.

This script:
- Initializes logging
- Creates the WebSocket client
- Starts data ingestion
- Displays live trade data
- Handles graceful shutdown on Ctrl+C
"""

import asyncio
import logging
import signal
from datetime import datetime


from src.config import (
    ANALYTICS_UPDATE_INTERVAL,
    DATABASE_PATH,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    LOG_LEVEL,
    RESAMPLE_INTERVALS,
    STATUS_UPDATE_INTERVAL,
    SYMBOLS,
)
from src.ingestion import BinanceWebSocketClient
from src.storage import DatabaseManager
from src.analytics.resampler import TickResampler  # Direct import to avoid circular dependency
from src.analytics.engine import AnalyticsEngine  # Phase 3: Analytics orchestrator


def setup_logging() -> None:
    """Configure logging with custom format and level."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )


async def resample_and_persist(client: BinanceWebSocketClient, db: DatabaseManager) -> None:
    """
    Consume ticks from WebSocket queues, persist to database, and generate OHLC bars.
    
    This task replaces the display_ticks task from Phase 1.
    It handles:
    - Tick persistence (batched for performance)
    - OHLC bar generation (1s, 1m, 5m intervals)
    - Logging of finalized bars
    
    Args:
        client: WebSocket client instance
        db: Database manager instance
    """
    resampler = TickResampler(db, RESAMPLE_INTERVALS)
    logger = logging.getLogger("TICK")
    
    while True:
        for symbol in client.symbols:
            try:
                tick = await client.get_next_tick(symbol, timeout=0.01)
                if tick:
                    # Log tick to console (Phase 1 behavior preserved)
                    logger.info(str(tick))
                    
                    # Process tick: persist + resample (Phase 2)
                    await resampler.process_tick(tick)
                    
            except Exception as e:
                logging.error(f"Error processing tick for {symbol.upper()}: {e}")
        
        await asyncio.sleep(0.001)


async def print_status(client: BinanceWebSocketClient) -> None:
    """
    Periodically print status updates with tick counts.
    
    Args:
        client: WebSocket client instance
    """
    logger = logging.getLogger(__name__)
    
    while True:
        await asyncio.sleep(STATUS_UPDATE_INTERVAL)
        
        counts = client.get_tick_counts()
        status_parts = [f"{symbol.upper()}: {count} ticks" for symbol, count in counts.items()]
        status = "Status - " + ", ".join(status_parts)
        
        logger.info(status)


async def analytics_update_task(db: DatabaseManager) -> None:
    """
    Background task to periodically compute and cache analytics.
    
    This task runs every ANALYTICS_UPDATE_INTERVAL seconds and pre-computes:
    - Price/volume statistics for all symbols
    - Pairs trading analytics (regression, spread, z-score, ADF, correlation)
    
    Results are cached to provide fast API responses.
    
    Args:
        db: Database manager instance
    """
    logger = logging.getLogger("ANALYTICS")
    logger.info("Starting analytics engine")
    
    engine = AnalyticsEngine(db)
    await engine.update_analytics_loop(interval_seconds=ANALYTICS_UPDATE_INTERVAL)


async def main() -> None:
    """
    Main async entry point.
    
    Initializes database, WebSocket client, starts data ingestion with
    persistence and resampling, and manages graceful shutdown.
    """
    logger = logging.getLogger(__name__)
    
    # Initialize database
    db = DatabaseManager(DATABASE_PATH)
    await db.initialize()
    logger.info("Database ready")
    
    # Create WebSocket client
    client = BinanceWebSocketClient(SYMBOLS)
    
    # Setup shutdown event
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame) -> None:
        """Handle shutdown signals (Ctrl+C, etc.)."""
        logger.info("Shutdown signal received")
        shutdown_event.set()
    
    # Register signal handlers (Windows-compatible)
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start WebSocket client
        await client.start()
        
        # Create tasks for resampling, analytics, and status
        resample_task = asyncio.create_task(resample_and_persist(client, db))
        analytics_task = asyncio.create_task(analytics_update_task(db))  # Phase 3
        status_task = asyncio.create_task(print_status(client))
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Cancel tasks
        resample_task.cancel()
        analytics_task.cancel()
        status_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            resample_task,
            analytics_task,
            status_task,
            return_exceptions=True
        )
        
    finally:
        # Stop WebSocket client
        await client.stop()
        
        # Close database (will flush remaining ticks)
        await db.close()
        
        logger.info("Shutdown complete")


if __name__ == "__main__":
    setup_logging()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Graceful exit (already handled in signal handler)
        pass
