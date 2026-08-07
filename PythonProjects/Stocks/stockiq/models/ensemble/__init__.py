"""
Ensemble ML models for stock prediction.

This module implements Requirements 3.1-3.12, 13.3-13.4:
- Ensemble stacking with RandomForest, GradientBoosting, and XGBoost
- Prediction confidence scoring (0-100 range)
- Prediction category assignment (Strong Buy, Buy, Hold, Sell, Strong Sell)
- Uncertainty quantification with prediction bounds
- Low-confidence flagging (<60%)
- SHAP feature importance
- Redis model caching (24-hour TTL)
"""

from .predictor import EnsemblePredictor, Prediction

__all__ = ['EnsemblePredictor', 'Prediction']
