"""
Backtesting Engine Module

This module provides professional-grade backtesting capabilities for trading strategies,
including realistic market simulation, multiple order types, and comprehensive performance metrics.
"""

from .engine import BacktestEngine, BacktestConfig, Position
from .orders import Order, OrderType, OrderStatus, OrderSide, MarketOrder, LimitOrder, StopLossOrder, StopLimitOrder
from .slippage import SlippageModel, FixedSlippageModel, VolumeSlippageModel, PercentageSlippageModel, BidAskSlippageModel
from .commission import (
    CommissionModel, FixedCommissionModel, PercentageCommissionModel, 
    TieredCommissionModel, ZeroCommissionModel, PerShareCommissionModel,
    InteractiveBrokersCommissionModel, TradeStationCommissionModel
)
from .performance import PerformanceMetrics, EquityCurve, DrawdownAnalyzer, Trade
from .optimization import WalkForwardOptimizer, OptimizationWindow, OptimizationResult, WalkForwardResult

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'Position',
    'Order',
    'OrderType',
    'OrderStatus',
    'OrderSide',
    'MarketOrder',
    'LimitOrder',
    'StopLossOrder',
    'StopLimitOrder',
    'SlippageModel',
    'FixedSlippageModel',
    'VolumeSlippageModel',
    'PercentageSlippageModel',
    'BidAskSlippageModel',
    'CommissionModel',
    'FixedCommissionModel',
    'PercentageCommissionModel',
    'PerShareCommissionModel',
    'TieredCommissionModel',
    'ZeroCommissionModel',
    'InteractiveBrokersCommissionModel',
    'TradeStationCommissionModel',
    'PerformanceMetrics',
    'EquityCurve',
    'DrawdownAnalyzer',
    'Trade',
    'WalkForwardOptimizer',
    'OptimizationWindow',
    'OptimizationResult',
    'WalkForwardResult',
]
