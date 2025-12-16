"""
Storage module for persisting market data.

This module handles database connections and data persistence
for the crypto analytics platform.
"""

from .database import DatabaseManager

__all__ = ["DatabaseManager"]
