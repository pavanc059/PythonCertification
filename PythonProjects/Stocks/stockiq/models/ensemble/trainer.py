"""
Training orchestration for the ensemble prediction model.

Builds a combined feature matrix across a set of tickers, fits the
EnsemblePredictor, and caches the trained model in Redis so the Daily Market
Brief dashboard can serve live predictions.

The same entry point (`train_and_cache_ensemble`) is used by both the CLI
training script (`train_model.py`) and the dashboard "Train model" button.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Columns produced by create_feature_matrix that are targets / not features.
_TARGET_COLUMNS = {"target_return", "target_direction"}

# Default training universe – a small, liquid set keeps training fast while
# still producing a usable model.  Callers can override this.
DEFAULT_TRAINING_TICKERS: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "MA", "HD", "CAT", "DE", "BA", "GE",
]


@dataclass
class TrainingResult:
    """Outcome of a training run."""
    success: bool
    samples: int = 0
    features: int = 0
    tickers_used: List[str] = field(default_factory=list)
    tickers_failed: List[str] = field(default_factory=list)
    training_score: Optional[float] = None
    message: str = ""


def train_and_cache_ensemble(
    tickers: Optional[List[str]] = None,
    lookback_days: int = 365,
    n_estimators: int = 100,
    max_depth: int = 10,
) -> TrainingResult:
    """
    Train the ensemble predictor on real market data and cache it in Redis.

    Args:
        tickers: Universe to train on (defaults to DEFAULT_TRAINING_TICKERS).
        lookback_days: Days of history per ticker used for features/targets.
        n_estimators: Trees per base model.
        max_depth: Maximum tree depth per base model.

    Returns:
        TrainingResult describing the outcome.
    """
    # Imported lazily so importing this module never forces heavy ML deps.
    try:
        import numpy as np
        import pandas as pd
        from stockiq.models.features import create_feature_matrix
        from stockiq.models.ensemble.predictor import EnsemblePredictor
    except Exception as exc:  # pragma: no cover - dependency guard
        return TrainingResult(
            success=False,
            message=f"Required ML dependencies unavailable: {exc}",
        )

    universe = tickers or DEFAULT_TRAINING_TICKERS

    frames: List["pd.DataFrame"] = []
    used: List[str] = []
    failed: List[str] = []

    for ticker in universe:
        try:
            df = create_feature_matrix(ticker, lookback_days=lookback_days)
            if df is not None and not df.empty:
                frames.append(df)
                used.append(ticker)
            else:
                failed.append(ticker)
        except Exception as exc:
            logger.warning("feature_matrix_failed ticker=%s error=%s", ticker, exc)
            failed.append(ticker)

    if not frames:
        return TrainingResult(
            success=False,
            tickers_failed=failed,
            message="No feature data could be built for any ticker.",
        )

    # Align on the columns common to every ticker (fundamental columns can
    # differ), preserving the column order from the first frame.
    common_cols = [c for c in frames[0].columns if all(c in f.columns for f in frames)]
    frames = [f[common_cols] for f in frames]

    data = pd.concat(frames, axis=0)

    # Targets: next-day return.  Drop rows where the target is undefined.
    data = data.dropna(subset=["target_return"])

    # Features: numeric columns excluding the target columns.
    feature_cols = [
        c for c in data.columns
        if c not in _TARGET_COLUMNS and pd.api.types.is_numeric_dtype(data[c])
    ]

    X = data[feature_cols].replace([np.inf, -np.inf], np.nan)
    y = data["target_return"]

    # Drop rows that still contain NaNs in any feature.
    mask = X.notna().all(axis=1)
    X, y = X[mask], y[mask]

    if X.empty or len(X) < 30:
        return TrainingResult(
            success=False,
            samples=len(X),
            features=len(feature_cols),
            tickers_used=used,
            tickers_failed=failed,
            message=(
                f"Not enough clean training samples ({len(X)}). "
                "Try more tickers or a longer lookback."
            ),
        )

    try:
        predictor = EnsemblePredictor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            cache_models=True,  # caches to Redis key model:ensemble:predictor
        )
        predictor.train(X, y)
    except Exception as exc:
        logger.error("ensemble_training_failed error=%s", exc)
        return TrainingResult(
            success=False,
            samples=len(X),
            features=len(feature_cols),
            tickers_used=used,
            tickers_failed=failed,
            message=f"Training failed: {exc}",
        )

    return TrainingResult(
        success=True,
        samples=len(X),
        features=len(feature_cols),
        tickers_used=used,
        tickers_failed=failed,
        training_score=predictor.training_score,
        message=(
            f"Trained on {len(X)} samples across {len(used)} tickers "
            f"({len(feature_cols)} features). Model cached."
        ),
    )
