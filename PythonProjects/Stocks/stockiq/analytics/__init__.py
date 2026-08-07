"""
Analytics Module

Provides institutional-grade financial analytics including:
- Options Greeks and implied volatility analysis
- Risk metrics (VaR, CVaR, ratios)
- Factor analysis (Fama-French, momentum, quality, value)
- Portfolio optimization (mean-variance, Black-Litterman)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .options.greeks import OptionsAnalyzer, Greeks, VolatilitySurface
    from .factors.factor_analyzer import (
        FactorAnalyzer,
        FactorExposures,
        FactorReturns,
        CointegrationResult,
    )
    from .portfolio.mean_variance import (
        MeanVarianceOptimizer,
        Portfolio,
        OptimizationConstraints,
        OptimizationResult,
    )
    from .portfolio.black_litterman import (
        BlackLittermanOptimizer,
        InvestorViews,
        InvestorView,
        BlackLittermanResult,
    )

__all__ = [
    'OptionsAnalyzer',
    'Greeks',
    'VolatilitySurface',
    'FactorAnalyzer',
    'FactorExposures',
    'FactorReturns',
    'CointegrationResult',
    'MeanVarianceOptimizer',
    'Portfolio',
    'OptimizationConstraints',
    'OptimizationResult',
    'BlackLittermanOptimizer',
    'InvestorViews',
    'InvestorView',
    'BlackLittermanResult',
]
