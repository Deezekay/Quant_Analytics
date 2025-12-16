"""
Binance Futures WebSocket client for real-time trade data ingestion.

This module provides an async WebSocket client that:
- Connects to Binance Futures trade streams
- Normalizes incoming trade events
- Handles auto-reconnection with exponential backoff
- Manages thread-safe buffering of trade data
- Provides graceful shutdown capabilities
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import websockets
from websockets.exceptions import WebSocketException

from ..config import (
    BUFFER_SIZE,
    PING_INTERVAL,
    PING_TIMEOUT,
    RECONNECT_DELAY_BASE,
    RECONNECT_MAX_DELAY,
    WEBSOCKET_URL,
)

logger = logging.getLogger(__name__)


@dataclass
class TradeData:
    """
    Normalized trade data structure.
    
    Attributes:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        timestamp: Trade execution timestamp
        price: Trade price
        size: Trade quantity/size
    """
    symbol: str
    timestamp: datetime
    price: float
    size: float

    def __str__(self) -> str:
        """Format trade data for console display."""
        return (
            f"{self.symbol} | "
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} | "
            f"${self.price:,.2f} | "
            f"{self.size:.6f}"
        )


class BinanceWebSocketClient:
    """
    Async WebSocket client for Binance Futures trade streams.
    
    This client manages multiple concurrent WebSocket connections,
    one per trading symbol, with automatic reconnection and error handling.
    
    Attributes:
        symbols: List of trading symbols to monitor
        queues: Dictionary mapping symbols to their data queues
        tasks: Active asyncio tasks for each symbol
        running: Flag indicating if client is active
        tick_counts: Counter for received ticks per symbol
    """

    def __init__(self, symbols: list[str]):
        """
        Initialize the WebSocket client.
        
        Args:
            symbols: List of trading symbols to monitor (e.g., ["btcusdt", "ethusdt"])
        """
        self.symbols = [s.lower() for s in symbols]
        self.queues: Dict[str, asyncio.Queue] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.tick_counts: Dict[str, int] = {symbol: 0 for symbol in self.symbols}
        
        # Initialize queues for each symbol
        for symbol in self.symbols:
            self.queues[symbol] = asyncio.Queue(maxsize=BUFFER_SIZE)

    async def _connect_and_consume(self, symbol: str) -> None:
        """
        Connect to WebSocket for a symbol and consume messages.
        
        Implements auto-reconnection with exponential backoff.
        
        Args:
            symbol: Trading symbol to connect to
        """
        url = WEBSOCKET_URL.format(symbol=symbol)
        retry_delay = RECONNECT_DELAY_BASE
        
        while self.running:
            try:
                logger.info(f"Connecting to {symbol.upper()}...")
                
                async with websockets.connect(
                    url,
                    ping_interval=PING_INTERVAL,
                    ping_timeout=PING_TIMEOUT,
                ) as websocket:
                    logger.info(f"Connected to {symbol.upper()}")
                    retry_delay = RECONNECT_DELAY_BASE  # Reset backoff on success
                    
                    # Consume messages while connected
                    async for message in websocket:
                        if not self.running:
                            break
                            
                        try:
                            await self._handle_message(symbol, message)
                        except Exception as e:
                            logger.error(f"Error handling message for {symbol.upper()}: {e}")
                            
            except WebSocketException as e:
                if self.running:
                    logger.error(f"WebSocket error for {symbol.upper()}: {e}")
                    logger.info(f"Reconnecting in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    
                    # Exponential backoff
                    retry_delay = min(retry_delay * 2, RECONNECT_MAX_DELAY)
                else:
                    break
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Unexpected error for {symbol.upper()}: {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    break
        
        logger.info(f"Disconnected from {symbol.upper()}")

    async def _handle_message(self, symbol: str, message: str) -> None:
        """
        Parse and normalize incoming WebSocket message.
        
        Binance trade event format:
        {
            "e": "trade",
            "s": "BTCUSDT",
            "T": 1702742400000,  # Trade time (ms)
            "p": "43250.50",      # Price
            "q": "0.125"          # Quantity
        }
        
        Args:
            symbol: Trading symbol
            message: Raw WebSocket message
        """
        try:
            data = json.loads(message)
            
            # Validate message structure
            if data.get("e") != "trade":
                return
            
            # Normalize data
            trade = TradeData(
                symbol=data["s"],
                timestamp=datetime.fromtimestamp(data["T"] / 1000.0),
                price=float(data["p"]),
                size=float(data["q"])
            )
            
            # Add to queue (non-blocking, will drop if full)
            try:
                self.queues[symbol].put_nowait(trade)
                self.tick_counts[symbol] += 1
            except asyncio.QueueFull:
                logger.warning(f"Queue full for {symbol.upper()}, dropping tick")
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse message for {symbol.upper()}: {e}")

    async def start(self) -> None:
        """
        Start WebSocket connections for all configured symbols.
        
        Creates an async task for each symbol's WebSocket connection.
        """
        self.running = True
        
        for symbol in self.symbols:
            task = asyncio.create_task(self._connect_and_consume(symbol))
            self.tasks[symbol] = task
        
        logger.info(f"Started WebSocket client for {len(self.symbols)} symbols")

    async def stop(self) -> None:
        """
        Gracefully stop all WebSocket connections.
        
        Cancels all active tasks and waits for cleanup.
        """
        logger.info("Shutting down WebSocket client...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks.values():
            task.cancel()
        
        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        logger.info("WebSocket client stopped")

    async def get_next_tick(self, symbol: str, timeout: Optional[float] = None) -> Optional[TradeData]:
        """
        Get the next trade tick for a symbol.
        
        Args:
            symbol: Trading symbol
            timeout: Maximum time to wait for a tick (None = wait forever)
            
        Returns:
            TradeData object or None if timeout
        """
        try:
            return await asyncio.wait_for(
                self.queues[symbol].get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    def get_tick_counts(self) -> Dict[str, int]:
        """
        Get the number of ticks received per symbol.
        
        Returns:
            Dictionary mapping symbols to tick counts
        """
        return self.tick_counts.copy()
