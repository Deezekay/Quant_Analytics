"""
Data ingestion module for real-time market data.

This module handles WebSocket connections to cryptocurrency exchanges
and normalizes incoming trade data.
"""

from .binance_websocket import BinanceWebSocketClient, TradeData

__all__ = ["BinanceWebSocketClient", "TradeData"]
