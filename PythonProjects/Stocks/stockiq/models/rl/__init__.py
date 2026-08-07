"""
Reinforcement Learning Module for Portfolio Optimization

This module provides RL agents and trading environments for portfolio optimization.
Uses Stable-Baselines3 for PPO, A2C, and SAC agents.
"""

# Graceful degradation for RL dependencies
try:
    from .environment import TradingEnvironment, PortfolioState
    from .rewards import RewardCalculator, RewardMetrics
    
    RL_ENVIRONMENT_AVAILABLE = True
except ImportError as e:
    RL_ENVIRONMENT_AVAILABLE = False
    _import_error = str(e)

try:
    from .agents import RLPortfolioOptimizer
    
    RL_AGENTS_AVAILABLE = True
except ImportError as e:
    RL_AGENTS_AVAILABLE = False
    _agents_import_error = str(e)

__all__ = [
    "TradingEnvironment",
    "PortfolioState",
    "RLPortfolioOptimizer",
    "RewardCalculator",
    "RewardMetrics",
    "RL_ENVIRONMENT_AVAILABLE",
    "RL_AGENTS_AVAILABLE",
]
