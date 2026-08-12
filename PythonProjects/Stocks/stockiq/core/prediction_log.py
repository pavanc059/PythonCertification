"""
Prediction Tracking and Performance Logging

Implements prediction lifecycle management: storing predictions, measuring
directional accuracy, generating market outlook, and computing performance
metrics with Sharpe ratio.

Requirements implemented:
- Requirement 3.8: Track prediction accuracy and display historical performance metrics
- Requirement 3.9: Adjust prediction models when accuracy drops below 55% (trigger alert)
- Requirement 3.11: Generate market outlook (bullish/neutral/bearish)
- Requirement 6.1: Store all daily predictions with timestamps

Properties validated:
- Property 17: calculate_accuracy returns float in [0.0, 1.0] (directional accuracy)
- Property 18: calculate_market_outlook returns exactly 'bullish', 'bearish', or 'neutral'
"""

import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

import structlog

from stockiq.infrastructure.database import get_db_context
from stockiq.infrastructure.models import Alert, AlertType, DailyPrediction, PredictionCategory, Stock
from stockiq.models.ensemble.predictor import Prediction

logger = structlog.get_logger(__name__)

# Threshold constants
_ACCURACY_RETRAINING_THRESHOLD = 0.55   # Requirement 3.9
_OUTLOOK_MAJORITY_THRESHOLD = 0.60      # 60% majority for bullish/bearish
_ANNUALISE_FACTOR = math.sqrt(252)      # Trading days in a year

# Positive / negative category sets for market outlook (Property 18)
_POSITIVE_CATEGORIES = {"Strong Buy", "Buy"}
_NEGATIVE_CATEGORIES = {"Strong Sell", "Sell"}


class PredictionLogger:
    """
    Prediction tracking façade.

    Persists predictions to the database, evaluates directional accuracy,
    determines market outlook, and surfaces performance metrics.  All
    public methods degrade gracefully when the database is unavailable.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_prediction(self, prediction: Prediction) -> None:
        """
        Store a prediction in the database with its timestamp.

        Looks up (or creates) the Stock row for ``prediction.ticker``, then
        upserts a DailyPrediction row keyed on (stock_id, prediction_date).

        Requirement 6.1: Store all daily predictions with timestamps.

        Args:
            prediction: The Prediction dataclass to persist.
        """
        try:
            with get_db_context() as db:
                # Resolve Stock row -------------------------------------------
                stock = db.query(Stock).filter(Stock.ticker == prediction.ticker).first()
                if stock is None:
                    stock = Stock(
                        ticker=prediction.ticker,
                        name=prediction.ticker,  # placeholder name
                    )
                    db.add(stock)
                    db.flush()  # populate stock.id before using it below
                    logger.info("stock_created", ticker=prediction.ticker)

                pred_date: date = prediction.timestamp.date()

                # Upsert: check for existing row on (stock_id, prediction_date) --
                existing = (
                    db.query(DailyPrediction)
                    .filter(
                        DailyPrediction.stock_id == stock.id,
                        DailyPrediction.prediction_date == pred_date,
                    )
                    .first()
                )

                # Map optional category string → PredictionCategory enum
                category_enum: Optional[PredictionCategory] = None
                if prediction.category is not None:
                    try:
                        category_enum = PredictionCategory(prediction.category)
                    except ValueError:
                        logger.warning(
                            "unknown_prediction_category",
                            category=prediction.category,
                            ticker=prediction.ticker,
                        )

                if existing is not None:
                    # Update in place
                    existing.predicted_price = prediction.value
                    existing.confidence = prediction.confidence
                    existing.lower_bound = prediction.lower_bound
                    existing.upper_bound = prediction.upper_bound
                    existing.category = category_enum
                    existing.factors = prediction.factors or {}
                    existing.model_version = prediction.model
                    logger.info(
                        "prediction_updated",
                        ticker=prediction.ticker,
                        date=str(pred_date),
                    )
                else:
                    row = DailyPrediction(
                        stock_id=stock.id,
                        prediction_date=pred_date,
                        predicted_price=prediction.value,
                        confidence=prediction.confidence,
                        lower_bound=prediction.lower_bound,
                        upper_bound=prediction.upper_bound,
                        category=category_enum,
                        factors=prediction.factors or {},
                        model_version=prediction.model,
                        created_at=datetime.utcnow(),
                    )
                    db.add(row)
                    logger.info(
                        "prediction_logged",
                        ticker=prediction.ticker,
                        date=str(pred_date),
                    )

        except Exception as exc:
            logger.warning(
                "log_prediction_failed",
                ticker=prediction.ticker,
                error=str(exc),
            )

    def calculate_accuracy(self, ticker: str, period_days: int) -> float:
        """
        Calculate directional prediction accuracy for *ticker* over
        the last *period_days* calendar days.

        Only rows where ``is_accurate`` is not NULL (i.e. the actual outcome
        is known) are included in the calculation.

        Triggers a model-retraining alert when accuracy < 55% (Requirement 3.9).

        Property 17: Return value is always in [0.0, 1.0].

        Args:
            ticker: Stock ticker symbol.
            period_days: Number of calendar days to look back.

        Returns:
            Directional accuracy as a float in [0.0, 1.0].  Returns 0.0 when
            no evaluated predictions exist for the period.
        """
        try:
            cutoff = date.today() - timedelta(days=period_days)

            with get_db_context() as db:
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if stock is None:
                    logger.info("calculate_accuracy_no_stock", ticker=ticker)
                    return 0.0

                rows = (
                    db.query(DailyPrediction)
                    .filter(
                        DailyPrediction.stock_id == stock.id,
                        DailyPrediction.prediction_date >= cutoff,
                        DailyPrediction.is_accurate.isnot(None),
                    )
                    .all()
                )

            total = len(rows)
            if total == 0:
                logger.info(
                    "calculate_accuracy_no_data",
                    ticker=ticker,
                    period_days=period_days,
                )
                return 0.0

            correct = sum(1 for r in rows if r.is_accurate is True)
            accuracy = correct / total

            # Clamp to [0, 1] as a safety net (Property 17)
            accuracy = max(0.0, min(1.0, accuracy))

            logger.info(
                "accuracy_calculated",
                ticker=ticker,
                period_days=period_days,
                accuracy=accuracy,
                total=total,
                correct=correct,
            )

            # Requirement 3.9: Alert when accuracy drops below threshold
            if accuracy < _ACCURACY_RETRAINING_THRESHOLD:
                self._trigger_retraining_alert(ticker, accuracy)

            return accuracy

        except Exception as exc:
            logger.warning(
                "calculate_accuracy_failed",
                ticker=ticker,
                error=str(exc),
            )
            return 0.0

    def calculate_market_outlook(self, predictions: List[Prediction]) -> str:
        """
        Determine overall market outlook from a list of predictions.

        Counts how many predictions carry a positive (Buy/Strong Buy) or
        negative (Sell/Strong Sell) category.  Returns 'bullish' if >60% are
        positive, 'bearish' if >60% are negative, 'neutral' otherwise.

        Property 18: Return value is exactly one of 'bullish', 'bearish',
        or 'neutral'.

        Requirement 3.11: Generate market outlook (bullish/neutral/bearish).

        Args:
            predictions: Iterable of Prediction objects.  May be empty.

        Returns:
            'bullish', 'bearish', or 'neutral'.
        """
        if not predictions:
            return "neutral"

        total = len(predictions)
        positive = sum(
            1 for p in predictions if p.category in _POSITIVE_CATEGORIES
        )
        negative = sum(
            1 for p in predictions if p.category in _NEGATIVE_CATEGORIES
        )

        positive_ratio = positive / total
        negative_ratio = negative / total

        if positive_ratio > _OUTLOOK_MAJORITY_THRESHOLD:
            outlook = "bullish"
        elif negative_ratio > _OUTLOOK_MAJORITY_THRESHOLD:
            outlook = "bearish"
        else:
            outlook = "neutral"

        logger.info(
            "market_outlook_calculated",
            total=total,
            positive=positive,
            negative=negative,
            outlook=outlook,
        )
        return outlook

    def get_performance_metrics(self, ticker: str) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics for all evaluated
        predictions for *ticker*.

        Returns a dictionary with:
        - ``win_rate``: Fraction of correct predictions.
        - ``avg_gain``: Mean return when prediction was correct.
        - ``avg_loss``: Mean return (negative) when prediction was wrong.
        - ``sharpe_ratio``: Annualised Sharpe ratio of prediction returns.
        - ``total_predictions``: Number of evaluated predictions.
        - ``accurate_predictions``: Number of correct predictions.

        All values are 0.0 when insufficient data (<2 rows) is available.

        Requirement 3.8: Track prediction accuracy and display historical
        performance metrics.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Dict with keys: win_rate, avg_gain, avg_loss, sharpe_ratio,
            total_predictions, accurate_predictions.
        """
        zero_metrics: Dict[str, float] = {
            "win_rate": 0.0,
            "avg_gain": 0.0,
            "avg_loss": 0.0,
            "sharpe_ratio": 0.0,
            "total_predictions": 0.0,
            "accurate_predictions": 0.0,
        }

        try:
            with get_db_context() as db:
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if stock is None:
                    return zero_metrics

                rows = (
                    db.query(DailyPrediction)
                    .filter(
                        DailyPrediction.stock_id == stock.id,
                        DailyPrediction.is_accurate.isnot(None),
                        DailyPrediction.actual_price.isnot(None),
                        DailyPrediction.predicted_price.isnot(None),
                    )
                    .all()
                )

            if len(rows) < 2:
                logger.info(
                    "performance_metrics_insufficient_data",
                    ticker=ticker,
                    rows=len(rows),
                )
                return zero_metrics

            total = len(rows)
            accurate_count = sum(1 for r in rows if r.is_accurate is True)
            win_rate = accurate_count / total

            # Compute per-prediction return: (actual - predicted) / predicted
            returns: List[float] = []
            gains: List[float] = []
            losses: List[float] = []

            for row in rows:
                predicted = float(row.predicted_price)
                actual = float(row.actual_price)

                if abs(predicted) < 1e-9:
                    # Avoid division by zero for near-zero predicted prices
                    continue

                ret = (actual - predicted) / predicted
                returns.append(ret)

                if row.is_accurate:
                    gains.append(ret)
                else:
                    losses.append(ret)

            avg_gain = float(sum(gains) / len(gains)) if gains else 0.0
            avg_loss = float(sum(losses) / len(losses)) if losses else 0.0

            # Annualised Sharpe ratio
            sharpe_ratio = 0.0
            if len(returns) >= 2:
                mean_ret = sum(returns) / len(returns)
                variance = sum((r - mean_ret) ** 2 for r in returns) / (
                    len(returns) - 1
                )
                std_ret = math.sqrt(variance)
                if std_ret > 1e-9:
                    sharpe_ratio = (mean_ret / std_ret) * _ANNUALISE_FACTOR

            metrics: Dict[str, float] = {
                "win_rate": win_rate,
                "avg_gain": avg_gain,
                "avg_loss": avg_loss,
                "sharpe_ratio": sharpe_ratio,
                "total_predictions": float(total),
                "accurate_predictions": float(accurate_count),
            }

            logger.info(
                "performance_metrics_calculated",
                ticker=ticker,
                **{k: round(v, 4) for k, v in metrics.items()},
            )
            return metrics

        except Exception as exc:
            logger.warning(
                "get_performance_metrics_failed",
                ticker=ticker,
                error=str(exc),
            )
            return zero_metrics

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _trigger_retraining_alert(self, ticker: str, accuracy: float) -> None:
        """
        Create an Alert row in the database to signal that the model for
        *ticker* should be retrained because accuracy has dropped below the
        55% threshold.

        Requirement 3.9: Adjust prediction models when accuracy drops below 55%.

        Args:
            ticker: Stock ticker symbol.
            accuracy: The current accuracy value (< 0.55).
        """
        message = (
            f"Model retraining required for {ticker}: "
            f"directional accuracy {accuracy:.1%} is below the 55% threshold. "
            "Review feature engineering and re-train the ensemble predictor."
        )

        try:
            with get_db_context() as db:
                alert = Alert(
                    ticker=ticker,
                    alert_type=AlertType.PRICE_THRESHOLD,
                    message=message,
                    priority=3,  # high priority
                    is_triggered=True,
                    triggered_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                )
                db.add(alert)
            logger.warning(
                "retraining_alert_created",
                ticker=ticker,
                accuracy=accuracy,
            )
        except Exception as exc:
            logger.warning(
                "retraining_alert_failed",
                ticker=ticker,
                accuracy=accuracy,
                error=str(exc),
            )
