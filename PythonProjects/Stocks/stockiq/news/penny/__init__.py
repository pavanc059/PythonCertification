"""
Penny stock analysis module.

Provides scanning, momentum scoring, risk analysis, and pattern detection
for penny stocks (securities trading below $5.00 per share).
"""

from .scanner import PennyStock, PennyStockScanner, RiskMetrics
from .momentum import MomentumCalculator, MomentumScore
from .risk import (
    PennyStockRiskAnalyzer,
    PumpDumpDetector,
    RiskAssessment,
    SuspicionScore,
    InsiderActivity,
    HIGH_PRIORITY_GAIN_THRESHOLD,
)

__all__ = [
    "PennyStock",
    "PennyStockScanner",
    "RiskMetrics",
    "MomentumCalculator",
    "MomentumScore",
    "PennyStockRiskAnalyzer",
    "PumpDumpDetector",
    "RiskAssessment",
    "SuspicionScore",
    "InsiderActivity",
    "HIGH_PRIORITY_GAIN_THRESHOLD",
]
