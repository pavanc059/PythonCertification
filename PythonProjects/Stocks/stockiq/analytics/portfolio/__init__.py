"""
Portfolio Optimization Module

Provides institutional-grade portfolio optimization algorithms including:
- Mean-variance optimization (Markowitz)
- Black-Litterman model with investor views
- Constraint-based optimization

Requirements: 14.10, 14.11
"""

# Runtime imports for actual usage
from .mean_variance import (
    MeanVarianceOptimizer,
    Portfolio,
    OptimizationConstraints,
    OptimizationResult,
)
from .black_litterman import (
    BlackLittermanOptimizer,
    InvestorViews,
    InvestorView,
    BlackLittermanResult,
)

__all__ = [
    'MeanVarianceOptimizer',
    'Portfolio',
    'OptimizationConstraints',
    'OptimizationResult',
    'BlackLittermanOptimizer',
    'InvestorViews',
    'InvestorView',
    'BlackLittermanResult',
]
