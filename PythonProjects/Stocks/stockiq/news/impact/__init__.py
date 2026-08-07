"""
News impact analysis module.

This module analyzes the correlation between news sentiment and price movements
to measure news impact effectiveness.

Modules:
- correlation: News-price correlation analysis
- decay: Impact decay curves over time
- beta: News sensitivity (news beta) calculation
"""

from .correlation import (
    NewsImpactAnalyzer,
    ImpactAnalysis,
    PriceImpact,
    calculate_sentiment_correlation,
    calculate_news_beta,
)

__all__ = [
    "NewsImpactAnalyzer",
    "ImpactAnalysis",
    "PriceImpact",
    "calculate_sentiment_correlation",
    "calculate_news_beta",
]
