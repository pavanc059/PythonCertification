"""
Paper trading system for simulated trading with virtual cash.

This module implements Requirements 16.7-16.10:
- Virtual cash accounts with real-time price execution
- Daily P&L tracking and benchmark comparison
"""

from .account import PaperTradingAccount, AccountConfig
from .orders import Order, OrderType, OrderSide, OrderStatus, MarketOrder, LimitOrder, StopLossOrder, StopLimitOrder
from .execution import OrderExecutor
from .portfolio import Portfolio, Position, PerformanceMetrics

__all__ = [
    'PaperTradingAccount',
    'AccountConfig',
    'Order',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'MarketOrder',
    'LimitOrder',
    'StopLossOrder',
    'StopLimitOrder',
    'OrderExecutor',
    'Portfolio',
    'Position',
    'PerformanceMetrics',
]
