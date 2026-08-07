"""
Factor Analysis Module

Provides institutional-grade factor analysis including:
- Fama-French 5-factor model
- Momentum, quality, and value factor exposures
- Cointegration testing for pairs trading
"""

from .factor_analyzer import (
    FactorAnalyzer,
    FactorExposures,
    FactorReturns,
    CointegrationResult,
)

__all__ = [
    'FactorAnalyzer',
    'FactorExposures',
    'FactorReturns',
    'CointegrationResult',
]
