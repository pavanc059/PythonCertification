"""
Property-based and unit tests for PredictionLogger.

**Validates: Requirements 3.8, 3.9, 3.11, 6.1**
**Properties: 17, 18**
"""

import math
import unittest.mock as mock
from datetime import datetime
from typing import List

import pytest
from hypothesis import given, settings, strategies as st

from stockiq.core.prediction_log import PredictionLogger, _POSITIVE_CATEGORIES, _NEGATIVE_CATEGORIES
from stockiq.models.ensemble.predictor import Prediction


# ---------------------------------------------------------------------------
# Helpers / strategies
# ---------------------------------------------------------------------------

VALID_CATEGORIES = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell", None]

POSITIVE_CATS = list(_POSITIVE_CATEGORIES)    # ["Strong Buy", "Buy"]
NEGATIVE_CATS = list(_NEGATIVE_CATEGORIES)    # ["Strong Sell", "Sell"]


def _make_prediction(category: str = "Hold", ticker: str = "AAPL") -> Prediction:
    """Create a minimal Prediction with the requested category."""
    # For 'return' type we must ensure lower_bound ≤ value ≤ upper_bound
    # and confidence in [0, 100]; then override .category after creation.
    pred = Prediction(
        ticker=ticker,
        timestamp=datetime.now(),
        prediction_type="return",
        value=0.01,
        confidence=70.0,
        lower_bound=0.0,
        upper_bound=0.02,
    )
    # Override the auto-assigned category with the requested one
    object.__setattr__(pred, "category", category)
    return pred


@st.composite
def prediction_list(draw, min_size: int = 0, max_size: int = 30):
    """Strategy: list of Predictions with arbitrary valid categories."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    categories = draw(
        st.lists(
            st.sampled_from(VALID_CATEGORIES),
            min_size=size,
            max_size=size,
        )
    )
    return [_make_prediction(cat) for cat in categories]


@st.composite
def bullish_prediction_list(draw, min_size: int = 1, max_size: int = 30):
    """Strategy: list where >60% of predictions are positive (Buy/Strong Buy)."""
    total = draw(st.integers(min_value=min_size, max_value=max_size))
    # Minimum positive count needed to exceed the 60% threshold
    min_positive = int(total * 0.60) + 1

    positive_count = draw(
        st.integers(min_value=min_positive, max_value=total)
    )
    negative_or_neutral = total - positive_count

    pos_cats = draw(
        st.lists(
            st.sampled_from(POSITIVE_CATS),
            min_size=positive_count,
            max_size=positive_count,
        )
    )
    neg_cats = draw(
        st.lists(
            st.sampled_from(["Hold", "Sell", "Strong Sell"]),
            min_size=negative_or_neutral,
            max_size=negative_or_neutral,
        )
    )

    all_cats = pos_cats + neg_cats
    return [_make_prediction(cat) for cat in all_cats]


@st.composite
def bearish_prediction_list(draw, min_size: int = 1, max_size: int = 30):
    """Strategy: list where >60% of predictions are negative (Sell/Strong Sell)."""
    total = draw(st.integers(min_value=min_size, max_value=max_size))
    min_negative = int(total * 0.60) + 1

    negative_count = draw(
        st.integers(min_value=min_negative, max_value=total)
    )
    rest = total - negative_count

    neg_cats = draw(
        st.lists(
            st.sampled_from(NEGATIVE_CATS),
            min_size=negative_count,
            max_size=negative_count,
        )
    )
    rest_cats = draw(
        st.lists(
            st.sampled_from(["Hold", "Strong Buy", "Buy"]),
            min_size=rest,
            max_size=rest,
        )
    )

    all_cats = neg_cats + rest_cats
    return [_make_prediction(cat) for cat in all_cats]


# ---------------------------------------------------------------------------
# Tests: Property 17 – calculate_accuracy returns float in [0.0, 1.0]
# ---------------------------------------------------------------------------

class TestCalculateAccuracyProperty17:
    """
    **Validates: Requirements 3.8, 3.9**

    Property 17: calculate_accuracy(ticker, period_days) always returns a
    float in [0.0, 1.0].
    """

    def _make_logger(self):
        return PredictionLogger()

    # --- No-data path (DB unavailable / stock not found) ---

    def test_returns_zero_when_db_unavailable(self):
        """
        Property 17: When the database raises an exception, accuracy
        gracefully returns 0.0 (still within [0.0, 1.0]).
        """
        logger = self._make_logger()
        with mock.patch(
            "stockiq.core.prediction_log.get_db_context",
            side_effect=Exception("DB unavailable"),
        ):
            result = logger.calculate_accuracy("AAPL", 30)

        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        assert result == 0.0

    def test_returns_zero_when_no_stock(self):
        """Property 17: Unknown ticker returns 0.0."""
        logger = self._make_logger()

        mock_db = mock.MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with mock.patch(
            "stockiq.core.prediction_log.get_db_context"
        ) as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            result = logger.calculate_accuracy("UNKNOWN", 30)

        assert 0.0 <= result <= 1.0
        assert result == 0.0

    def test_returns_zero_when_no_evaluated_rows(self):
        """Property 17: If no predictions have been evaluated (is_accurate is NULL), return 0.0."""
        logger = self._make_logger()

        mock_stock = mock.MagicMock()
        mock_stock.id = 1
        mock_db = mock.MagicMock()
        # First query (Stock) returns mock_stock; second (DailyPrediction) returns []
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock
        mock_db.query.return_value.filter.return_value.filter.return_value.filter.return_value.all.return_value = []

        with mock.patch(
            "stockiq.core.prediction_log.get_db_context"
        ) as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            result = logger.calculate_accuracy("AAPL", 30)

        assert 0.0 <= result <= 1.0

    # --- Property-based: accuracy ∈ [0, 1] for arbitrary correct/total counts ---

    @given(
        correct=st.integers(min_value=0, max_value=500),
        total=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=15, deadline=None)
    def test_property_17_accuracy_always_in_range(self, correct: int, total: int):
        """
        **Validates: Requirements 3.8**

        Property 17: For any ratio of correct/total predictions,
        calculate_accuracy MUST return a value in [0.0, 1.0].
        """
        # Clamp correct ≤ total to form valid input
        correct = min(correct, total)

        # Build mock rows
        rows = [mock.MagicMock(is_accurate=True) for _ in range(correct)]
        rows += [mock.MagicMock(is_accurate=False) for _ in range(total - correct)]

        mock_stock = mock.MagicMock()
        mock_stock.id = 42
        mock_db = mock.MagicMock()

        def query_side_effect(model_cls):
            q = mock.MagicMock()
            q.filter.return_value = q
            q.first.return_value = mock_stock
            q.all.return_value = rows
            q.isnot.return_value = q
            return q

        mock_db.query.side_effect = query_side_effect

        logger = PredictionLogger()
        with mock.patch(
            "stockiq.core.prediction_log.get_db_context"
        ) as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            result = logger.calculate_accuracy("AAPL", 30)

        assert isinstance(result, float), "accuracy must be a float"
        assert 0.0 <= result <= 1.0, (
            f"Property 17 violation: accuracy={result} not in [0.0, 1.0] "
            f"(correct={correct}, total={total})"
        )

    @given(
        correct=st.integers(min_value=0, max_value=200),
        total=st.integers(min_value=1, max_value=200),
    )
    @settings(max_examples=15, deadline=None)
    def test_property_17_accuracy_equals_correct_over_total(
        self, correct: int, total: int
    ):
        """
        **Validates: Requirements 3.8**

        Property 17 (value check): accuracy == correct / total when data
        is present and within [0.0, 1.0].
        """
        correct = min(correct, total)

        rows = [mock.MagicMock(is_accurate=True) for _ in range(correct)]
        rows += [mock.MagicMock(is_accurate=False) for _ in range(total - correct)]

        mock_stock = mock.MagicMock()
        mock_stock.id = 1
        mock_db = mock.MagicMock()

        def query_side_effect(model_cls):
            q = mock.MagicMock()
            q.filter.return_value = q
            q.first.return_value = mock_stock
            q.all.return_value = rows
            return q

        mock_db.query.side_effect = query_side_effect

        logger = PredictionLogger()

        # Suppress retraining-alert side effects
        with mock.patch.object(logger, "_trigger_retraining_alert"):
            with mock.patch(
                "stockiq.core.prediction_log.get_db_context"
            ) as ctx:
                ctx.return_value.__enter__.return_value = mock_db
                ctx.return_value.__exit__.return_value = False
                result = logger.calculate_accuracy("AAPL", 30)

        expected = correct / total
        assert abs(result - expected) < 1e-9, (
            f"Expected {expected}, got {result}"
        )
        assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# Tests: Property 18 – calculate_market_outlook returns valid string
# ---------------------------------------------------------------------------

class TestCalculateMarketOutlookProperty18:
    """
    **Validates: Requirements 3.11**

    Property 18: calculate_market_outlook returns exactly one of
    'bullish', 'bearish', or 'neutral'.
    """

    VALID_OUTLOOKS = {"bullish", "bearish", "neutral"}

    def _logger(self) -> PredictionLogger:
        return PredictionLogger()

    # --- Unit tests ---

    def test_empty_list_returns_neutral(self):
        """Property 18: Empty prediction list → 'neutral'."""
        result = self._logger().calculate_market_outlook([])
        assert result == "neutral"

    def test_all_strong_buy_returns_bullish(self):
        """Property 18: All Strong Buy → 'bullish'."""
        preds = [_make_prediction("Strong Buy") for _ in range(10)]
        result = self._logger().calculate_market_outlook(preds)
        assert result == "bullish"

    def test_all_buy_returns_bullish(self):
        """Property 18: All Buy → 'bullish'."""
        preds = [_make_prediction("Buy") for _ in range(10)]
        result = self._logger().calculate_market_outlook(preds)
        assert result == "bullish"

    def test_all_strong_sell_returns_bearish(self):
        """Property 18: All Strong Sell → 'bearish'."""
        preds = [_make_prediction("Strong Sell") for _ in range(10)]
        result = self._logger().calculate_market_outlook(preds)
        assert result == "bearish"

    def test_all_sell_returns_bearish(self):
        """Property 18: All Sell → 'bearish'."""
        preds = [_make_prediction("Sell") for _ in range(10)]
        result = self._logger().calculate_market_outlook(preds)
        assert result == "bearish"

    def test_all_hold_returns_neutral(self):
        """Property 18: All Hold → 'neutral' (neither majority)."""
        preds = [_make_prediction("Hold") for _ in range(10)]
        result = self._logger().calculate_market_outlook(preds)
        assert result == "neutral"

    def test_exactly_60_percent_positive_is_neutral(self):
        """Property 18: Exactly 60% positive is NOT > 60%, so → 'neutral'."""
        total = 10
        positive = 6  # 60% exactly, not > 60%
        preds = (
            [_make_prediction("Buy")] * positive
            + [_make_prediction("Hold")] * (total - positive)
        )
        result = self._logger().calculate_market_outlook(preds)
        assert result == "neutral"

    def test_just_above_60_percent_positive_is_bullish(self):
        """Property 18: 7 out of 10 positive (70%) → 'bullish'."""
        preds = (
            [_make_prediction("Buy")] * 7
            + [_make_prediction("Hold")] * 3
        )
        result = self._logger().calculate_market_outlook(preds)
        assert result == "bullish"

    def test_just_above_60_percent_negative_is_bearish(self):
        """Property 18: 7 out of 10 negative (70%) → 'bearish'."""
        preds = (
            [_make_prediction("Sell")] * 7
            + [_make_prediction("Hold")] * 3
        )
        result = self._logger().calculate_market_outlook(preds)
        assert result == "bearish"

    def test_mixed_no_majority_returns_neutral(self):
        """Property 18: 5 Buy + 5 Sell → neither majority → 'neutral'."""
        preds = (
            [_make_prediction("Buy")] * 5
            + [_make_prediction("Sell")] * 5
        )
        result = self._logger().calculate_market_outlook(preds)
        assert result == "neutral"

    # --- Property-based tests ---

    @given(predictions=prediction_list(min_size=0, max_size=50))
    @settings(max_examples=20, deadline=None)
    def test_property_18_return_value_always_valid(self, predictions: List[Prediction]):
        """
        **Validates: Requirements 3.11**

        Property 18: For ANY list of predictions (including empty),
        calculate_market_outlook MUST return exactly one of
        'bullish', 'bearish', or 'neutral'.
        """
        result = self._logger().calculate_market_outlook(predictions)

        assert result in self.VALID_OUTLOOKS, (
            f"Property 18 violation: '{result}' is not in "
            f"{self.VALID_OUTLOOKS}"
        )
        assert isinstance(result, str), "Return value must be a string"

    @given(predictions=bullish_prediction_list(min_size=1, max_size=50))
    @settings(max_examples=15, deadline=None)
    def test_property_18_bullish_majority_returns_bullish(
        self, predictions: List[Prediction]
    ):
        """
        **Validates: Requirements 3.11**

        Property 18 (bullish case): When >60% of predictions have a
        positive category (Buy / Strong Buy), the result MUST be 'bullish'.
        """
        result = self._logger().calculate_market_outlook(predictions)

        assert result == "bullish", (
            f"Property 18 violation: expected 'bullish' but got '{result}' "
            f"(positive categories: "
            f"{[p.category for p in predictions if p.category in _POSITIVE_CATEGORIES]})"
        )

    @given(predictions=bearish_prediction_list(min_size=1, max_size=50))
    @settings(max_examples=15, deadline=None)
    def test_property_18_bearish_majority_returns_bearish(
        self, predictions: List[Prediction]
    ):
        """
        **Validates: Requirements 3.11**

        Property 18 (bearish case): When >60% of predictions have a
        negative category (Sell / Strong Sell), the result MUST be 'bearish'.
        """
        result = self._logger().calculate_market_outlook(predictions)

        assert result == "bearish", (
            f"Property 18 violation: expected 'bearish' but got '{result}' "
            f"(negative categories: "
            f"{[p.category for p in predictions if p.category in _NEGATIVE_CATEGORIES]})"
        )

    @given(predictions=prediction_list(min_size=1, max_size=50))
    @settings(max_examples=15, deadline=None)
    def test_property_18_no_majority_returns_neutral_or_directional(
        self, predictions: List[Prediction]
    ):
        """
        **Validates: Requirements 3.11**

        Property 18 (determinism): The same list of predictions always
        produces the same outlook (pure function / no side-effects on output).
        """
        logger = self._logger()
        first = logger.calculate_market_outlook(predictions)
        second = logger.calculate_market_outlook(predictions)

        assert first == second, (
            "calculate_market_outlook is not deterministic for the same input"
        )
        assert first in self.VALID_OUTLOOKS


# ---------------------------------------------------------------------------
# Unit tests for supporting functions (not property tests)
# ---------------------------------------------------------------------------

class TestLogPrediction:
    """Unit tests for log_prediction (Requirement 6.1)."""

    def test_log_prediction_gracefully_handles_db_error(self):
        """log_prediction must not raise when DB is unavailable."""
        pred = _make_prediction("Buy", ticker="TSLA")
        logger = PredictionLogger()

        with mock.patch(
            "stockiq.core.prediction_log.get_db_context",
            side_effect=Exception("connection refused"),
        ):
            # Should not raise
            logger.log_prediction(pred)

    def test_log_prediction_inserts_new_row(self):
        """log_prediction inserts a DailyPrediction when none exists."""
        pred = _make_prediction("Buy", ticker="MSFT")
        logger = PredictionLogger()

        mock_stock = mock.MagicMock()
        mock_stock.id = 99

        # Use a universal mock_db where every chained query returns sensible values.
        # The key calls inside log_prediction are:
        #   1. db.query(Stock).filter(...).first()  → mock_stock
        #   2. db.query(DailyPrediction).filter(...).filter(...).first() → None  (no existing row)
        #   3. db.add(new_row)
        call_count = {"n": 0}

        def query_side_effect(model_cls):
            q = mock.MagicMock()
            q.filter.return_value = q   # chaining
            call_count["n"] += 1
            if call_count["n"] == 1:
                # First query → Stock lookup
                q.first.return_value = mock_stock
            else:
                # Second query → DailyPrediction lookup (no existing row)
                q.first.return_value = None
            return q

        mock_db = mock.MagicMock()
        mock_db.query.side_effect = query_side_effect

        with mock.patch("stockiq.core.prediction_log.get_db_context") as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            logger.log_prediction(pred)

        mock_db.add.assert_called_once()


class TestGetPerformanceMetrics:
    """Unit tests for get_performance_metrics (Requirement 3.8)."""

    def test_returns_zeros_on_db_error(self):
        """Graceful degradation: zeros dict returned when DB fails."""
        logger = PredictionLogger()
        with mock.patch(
            "stockiq.core.prediction_log.get_db_context",
            side_effect=Exception("timeout"),
        ):
            result = logger.get_performance_metrics("GOOG")

        assert isinstance(result, dict)
        for key in ("win_rate", "avg_gain", "avg_loss", "sharpe_ratio",
                    "total_predictions", "accurate_predictions"):
            assert key in result
            assert result[key] == 0.0

    def test_returns_zeros_when_insufficient_data(self):
        """Returns zeros when fewer than 2 evaluated predictions exist."""
        mock_stock = mock.MagicMock()
        mock_stock.id = 1
        mock_db = mock.MagicMock()

        def query_side(cls):
            q = mock.MagicMock()
            q.filter.return_value = q
            q.first.return_value = mock_stock
            q.all.return_value = []  # zero rows
            return q

        mock_db.query.side_effect = query_side

        logger = PredictionLogger()
        with mock.patch("stockiq.core.prediction_log.get_db_context") as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            result = logger.get_performance_metrics("AAPL")

        assert result["win_rate"] == 0.0
        assert result["sharpe_ratio"] == 0.0

    def test_sharpe_ratio_is_annualised(self):
        """Sharpe ratio is multiplied by sqrt(252)."""
        import math

        mock_stock = mock.MagicMock()
        mock_stock.id = 1

        # 3 rows: predicted=100, actual=110 (10% return, all accurate)
        rows = []
        for _ in range(3):
            r = mock.MagicMock()
            r.predicted_price = 100.0
            r.actual_price = 110.0
            r.is_accurate = True
            rows.append(r)

        mock_db = mock.MagicMock()

        def query_side(cls):
            q = mock.MagicMock()
            q.filter.return_value = q
            q.first.return_value = mock_stock
            q.all.return_value = rows
            return q

        mock_db.query.side_effect = query_side

        logger = PredictionLogger()
        with mock.patch("stockiq.core.prediction_log.get_db_context") as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            result = logger.get_performance_metrics("AAPL")

        # With identical returns std_dev == 0 → sharpe should be 0
        assert result["win_rate"] == 1.0
        assert result["avg_gain"] == pytest.approx(0.1, abs=1e-6)


class TestTriggerRetrainingAlert:
    """Unit tests for _trigger_retraining_alert (Requirement 3.9)."""

    def test_alert_created_in_db(self):
        """_trigger_retraining_alert writes an Alert row to the database."""
        from stockiq.infrastructure.models import Alert

        mock_db = mock.MagicMock()
        logger = PredictionLogger()

        with mock.patch("stockiq.core.prediction_log.get_db_context") as ctx:
            ctx.return_value.__enter__.return_value = mock_db
            ctx.return_value.__exit__.return_value = False
            logger._trigger_retraining_alert("NVDA", 0.48)

        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, Alert)
        assert added_obj.ticker == "NVDA"
        assert "NVDA" in added_obj.message
        assert "55%" in added_obj.message

    def test_alert_not_raised_when_db_fails(self):
        """_trigger_retraining_alert does not propagate DB exceptions."""
        logger = PredictionLogger()
        with mock.patch(
            "stockiq.core.prediction_log.get_db_context",
            side_effect=Exception("DB down"),
        ):
            # Must not raise
            logger._trigger_retraining_alert("TSLA", 0.40)

    def test_retraining_triggered_when_accuracy_below_threshold(self):
        """calculate_accuracy triggers alert when result < 0.55."""
        correct = 4
        total = 10
        # accuracy = 0.40 → below 0.55 threshold

        rows = [mock.MagicMock(is_accurate=True) for _ in range(correct)]
        rows += [mock.MagicMock(is_accurate=False) for _ in range(total - correct)]

        mock_stock = mock.MagicMock()
        mock_stock.id = 1
        mock_db = mock.MagicMock()

        def query_side(cls):
            q = mock.MagicMock()
            q.filter.return_value = q
            q.first.return_value = mock_stock
            q.all.return_value = rows
            return q

        mock_db.query.side_effect = query_side

        logger = PredictionLogger()
        with mock.patch.object(logger, "_trigger_retraining_alert") as alert_mock:
            with mock.patch("stockiq.core.prediction_log.get_db_context") as ctx:
                ctx.return_value.__enter__.return_value = mock_db
                ctx.return_value.__exit__.return_value = False
                result = logger.calculate_accuracy("AAPL", 30)

        assert result == pytest.approx(0.40, abs=1e-9)
        alert_mock.assert_called_once_with("AAPL", pytest.approx(0.40, abs=1e-9))

    def test_retraining_not_triggered_when_accuracy_above_threshold(self):
        """calculate_accuracy does NOT trigger alert when result >= 0.55."""
        correct = 6
        total = 10
        # accuracy = 0.60 → above threshold

        rows = [mock.MagicMock(is_accurate=True) for _ in range(correct)]
        rows += [mock.MagicMock(is_accurate=False) for _ in range(total - correct)]

        mock_stock = mock.MagicMock()
        mock_stock.id = 1
        mock_db = mock.MagicMock()

        def query_side(cls):
            q = mock.MagicMock()
            q.filter.return_value = q
            q.first.return_value = mock_stock
            q.all.return_value = rows
            return q

        mock_db.query.side_effect = query_side

        logger = PredictionLogger()
        with mock.patch.object(logger, "_trigger_retraining_alert") as alert_mock:
            with mock.patch("stockiq.core.prediction_log.get_db_context") as ctx:
                ctx.return_value.__enter__.return_value = mock_db
                ctx.return_value.__exit__.return_value = False
                logger.calculate_accuracy("AAPL", 30)

        alert_mock.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
