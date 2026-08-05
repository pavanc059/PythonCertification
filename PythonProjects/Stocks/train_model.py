#!/usr/bin/env python
"""
Train and cache the ensemble prediction model.

Builds real feature data from yfinance for a set of tickers, trains the
RandomForest + GradientBoosting + XGBoost ensemble, and caches it in Redis so
the Daily Market Brief dashboard serves live predictions.

Usage:
    python train_model.py
    python train_model.py --tickers AAPL MSFT NVDA --lookback 365
    python train_model.py --tickers AAPL MSFT --estimators 200 --max-depth 12
"""

import argparse
import logging
import sys

from stockiq.models.ensemble.trainer import (
    DEFAULT_TRAINING_TICKERS,
    train_and_cache_ensemble,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the ensemble prediction model.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=DEFAULT_TRAINING_TICKERS,
        help="Tickers to train on (default: a small liquid universe).",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=365,
        help="Days of history per ticker (default: 365).",
    )
    parser.add_argument(
        "--estimators",
        type=int,
        default=100,
        help="Trees per base model (default: 100).",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="Maximum tree depth (default: 10).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    print(f"Training on {len(args.tickers)} tickers, lookback={args.lookback} days...")
    print("This fetches live market data and may take a minute.\n")

    result = train_and_cache_ensemble(
        tickers=args.tickers,
        lookback_days=args.lookback,
        n_estimators=args.estimators,
        max_depth=args.max_depth,
    )

    if result.success:
        print("[OK] Training complete - model cached.")
        print(f"   Samples:        {result.samples}")
        print(f"   Features:       {result.features}")
        print(f"   Tickers used:   {', '.join(result.tickers_used)}")
        if result.tickers_failed:
            print(f"   Tickers skipped: {', '.join(result.tickers_failed)}")
        if result.training_score is not None:
            print(f"   Training R^2:   {result.training_score:.4f}")
        print("\nThe Daily Market Brief will now show live predictions.")
        return 0

    print("[FAILED] Training did not complete.")
    print(f"   {result.message}")
    if result.tickers_failed:
        print(f"   Tickers skipped: {', '.join(result.tickers_failed)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
