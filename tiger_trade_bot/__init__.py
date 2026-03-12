"""
Tiger Trade Bot - Lightweight trading bot for Tiger Brokers API.

Main Components:
- data: Market data fetching (REST + WebSocket)
- trader: Paper trading engine with order management
- strategies: Trading strategies (gap, MA crossover)
"""

__version__ = "0.1.0"
__author__ = "Code Master"

from .data import TigerDataFetcher, Quote, Bar
from .trader import PaperTrader, OrderSide, OrderType, OrderStatus, Position, OrderRecord
from .strategies import (
    BaseStrategy, GapTradingStrategy, MovingAverageCrossoverStrategy,
    TradeSignal, Signal
)

__all__ = [
    "TigerDataFetcher", "Quote", "Bar",
    "PaperTrader", "OrderSide", "OrderType", "OrderStatus", "Position", "OrderRecord",
    "BaseStrategy", "GapTradingStrategy", "MovingAverageCrossoverStrategy",
    "TradeSignal", "Signal"
]