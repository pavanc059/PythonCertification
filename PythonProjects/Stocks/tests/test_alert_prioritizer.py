"""
Tests for alert_prioritizer module.

Covers:
- calculate_priority: base scores, sentiment bonus, impact bonus, ordering
- group_related_alerts: grouping by ticker within 1-hour window, multi-window splits,
  sorting by highest_priority, empty input, AlertGroup helpers
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from hypothesis import given, settings
from hypothesis import strategies as st

from stockiq.news.alerts.detector import AlertType, NewsAlert
from stockiq.news.alerts.prioritizer import (
    AlertGroup,
    calculate_priority,
    group_related_alerts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_alert(
    alert_type: AlertType = AlertType.GENERAL,
    ticker: str = "AAPL",
    sentiment_score: float = 0.0,
    predicted_impact: Optional[float] = None,
    triggered_at: Optional[datetime] = None,
) -> NewsAlert:
    if triggered_at is None:
        triggered_at = datetime.now(timezone.utc)
    return NewsAlert(
        alert_type=alert_type,
        ticker=ticker,
        headline="Test headline",
        sentiment_score=sentiment_score,
        predicted_impact=predicted_impact,
        triggered_at=triggered_at,
    )


# ---------------------------------------------------------------------------
# calculate_priority – base scores
# ---------------------------------------------------------------------------


class TestCalculatePriorityBaseScores:
    """Verify base scores reflect the required ordering: BREAKING > EARNINGS > MA > REGULATORY > GENERAL."""

    def test_breaking_news_has_highest_base_score(self):
        breaking = calculate_priority(_make_alert(AlertType.BREAKING_NEWS))
        earnings = calculate_priority(_make_alert(AlertType.EARNINGS))
        assert breaking > earnings

    def test_earnings_higher_than_ma(self):
        earnings = calculate_priority(_make_alert(AlertType.EARNINGS))
        ma = calculate_priority(_make_alert(AlertType.MA))
        assert earnings > ma

    def test_ma_higher_than_regulatory(self):
        ma = calculate_priority(_make_alert(AlertType.MA))
        regulatory = calculate_priority(_make_alert(AlertType.REGULATORY))
        assert ma > regulatory

    def test_regulatory_higher_than_general(self):
        regulatory = calculate_priority(_make_alert(AlertType.REGULATORY))
        general = calculate_priority(_make_alert(AlertType.GENERAL))
        assert regulatory > general

    def test_breaking_news_base_is_100_when_no_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.BREAKING_NEWS))
        assert priority == 100

    def test_general_base_is_20_when_no_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL))
        assert priority == 20

    def test_sentiment_change_base_is_30_when_no_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.SENTIMENT_CHANGE))
        assert priority == 30


# ---------------------------------------------------------------------------
# calculate_priority – sentiment bonus
# ---------------------------------------------------------------------------


class TestCalculatePrioritySentimentBonus:
    """Sentiment magnitude in [0, 1] should contribute 0–10 bonus points."""

    def test_zero_sentiment_gives_no_bonus(self):
        base = calculate_priority(_make_alert(AlertType.GENERAL, sentiment_score=0.0))
        assert base == 20

    def test_maximum_positive_sentiment_gives_10_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, sentiment_score=1.0))
        assert priority == 30  # 20 + 10

    def test_maximum_negative_sentiment_gives_10_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, sentiment_score=-1.0))
        assert priority == 30  # magnitude matters, not sign

    def test_half_sentiment_gives_5_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, sentiment_score=0.5))
        # round(0.5 * 10) = 5
        assert priority == 25

    def test_sentiment_magnitude_capped_at_1(self):
        # Values outside [-1, 1] should be capped
        priority = calculate_priority(_make_alert(AlertType.GENERAL, sentiment_score=2.0))
        assert priority == 30  # capped at 1.0 → max bonus 10


# ---------------------------------------------------------------------------
# calculate_priority – predicted impact bonus
# ---------------------------------------------------------------------------


class TestCalculatePriorityImpactBonus:
    """Predicted impact in [0, 1] should contribute 0–10 bonus points."""

    def test_no_predicted_impact_gives_no_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, predicted_impact=None))
        assert priority == 20

    def test_full_positive_impact_gives_10_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, predicted_impact=1.0))
        assert priority == 30  # 20 + 10

    def test_full_negative_impact_gives_10_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, predicted_impact=-1.0))
        assert priority == 30

    def test_half_impact_gives_5_bonus(self):
        priority = calculate_priority(_make_alert(AlertType.GENERAL, predicted_impact=0.5))
        assert priority == 25

    def test_both_bonuses_stack(self):
        priority = calculate_priority(
            _make_alert(AlertType.GENERAL, sentiment_score=1.0, predicted_impact=1.0)
        )
        assert priority == 40  # 20 + 10 + 10


# ---------------------------------------------------------------------------
# group_related_alerts – basic grouping
# ---------------------------------------------------------------------------


class TestGroupRelatedAlertsBasic:
    def test_empty_list_returns_empty(self):
        assert group_related_alerts([]) == []

    def test_single_alert_returns_one_group(self):
        alert = _make_alert(ticker="AAPL")
        groups = group_related_alerts([alert])
        assert len(groups) == 1
        assert groups[0].ticker == "AAPL"
        assert groups[0].count == 1

    def test_two_alerts_same_ticker_same_window_grouped(self):
        now = datetime.now(timezone.utc)
        a1 = _make_alert(ticker="TSLA", triggered_at=now)
        a2 = _make_alert(ticker="TSLA", triggered_at=now + timedelta(minutes=30))
        groups = group_related_alerts([a1, a2])
        assert len(groups) == 1
        assert groups[0].count == 2

    def test_two_alerts_different_tickers_different_groups(self):
        now = datetime.now(timezone.utc)
        a1 = _make_alert(ticker="AAPL", triggered_at=now)
        a2 = _make_alert(ticker="TSLA", triggered_at=now)
        groups = group_related_alerts([a1, a2])
        assert len(groups) == 2
        tickers = {g.ticker for g in groups}
        assert tickers == {"AAPL", "TSLA"}

    def test_alerts_outside_1_hour_window_get_separate_groups(self):
        now = datetime.now(timezone.utc)
        a1 = _make_alert(ticker="MSFT", triggered_at=now)
        a2 = _make_alert(ticker="MSFT", triggered_at=now + timedelta(hours=1, minutes=1))
        groups = group_related_alerts([a1, a2])
        # The second alert is more than 1 hour after the first
        assert len(groups) == 2

    def test_alerts_exactly_at_1_hour_boundary_are_grouped(self):
        now = datetime.now(timezone.utc)
        a1 = _make_alert(ticker="GOOG", triggered_at=now)
        a2 = _make_alert(ticker="GOOG", triggered_at=now + timedelta(hours=1))
        groups = group_related_alerts([a1, a2])
        # Exactly 1 hour → within window (≤)
        assert len(groups) == 1

    def test_ticker_matching_is_case_insensitive(self):
        now = datetime.now(timezone.utc)
        a1 = _make_alert(ticker="aapl", triggered_at=now)
        a2 = _make_alert(ticker="AAPL", triggered_at=now + timedelta(minutes=10))
        groups = group_related_alerts([a1, a2])
        assert len(groups) == 1


# ---------------------------------------------------------------------------
# group_related_alerts – priority ordering
# ---------------------------------------------------------------------------


class TestGroupRelatedAlertsPriorityOrdering:
    def test_groups_sorted_by_highest_priority_descending(self):
        now = datetime.now(timezone.utc)
        # AAPL gets a low-priority GENERAL alert
        a1 = _make_alert(ticker="AAPL", alert_type=AlertType.GENERAL, triggered_at=now)
        # TSLA gets a high-priority BREAKING_NEWS alert
        a2 = _make_alert(ticker="TSLA", alert_type=AlertType.BREAKING_NEWS, triggered_at=now)
        groups = group_related_alerts([a1, a2])
        assert groups[0].ticker == "TSLA"
        assert groups[1].ticker == "AAPL"

    def test_group_highest_priority_reflects_maximum_alert(self):
        now = datetime.now(timezone.utc)
        a1 = _make_alert(ticker="NVDA", alert_type=AlertType.GENERAL, triggered_at=now)
        a2 = _make_alert(
            ticker="NVDA",
            alert_type=AlertType.EARNINGS,
            triggered_at=now + timedelta(minutes=5),
        )
        groups = group_related_alerts([a1, a2])
        assert len(groups) == 1
        expected_max = calculate_priority(a2)
        assert groups[0].highest_priority == expected_max


# ---------------------------------------------------------------------------
# group_related_alerts – notification spam prevention
# ---------------------------------------------------------------------------


class TestGroupRelatedAlertsSpamPrevention:
    def test_many_same_ticker_alerts_within_window_yield_one_group(self):
        now = datetime.now(timezone.utc)
        alerts = [
            _make_alert(ticker="AMZN", triggered_at=now + timedelta(minutes=i))
            for i in range(10)
        ]
        groups = group_related_alerts(alerts)
        assert len(groups) == 1
        assert groups[0].count == 10

    def test_two_windows_for_same_ticker_yields_two_groups(self):
        now = datetime.now(timezone.utc)
        # First window: 0–55 min
        window1 = [
            _make_alert(ticker="FB", triggered_at=now + timedelta(minutes=i))
            for i in range(0, 56, 10)
        ]
        # Second window: starts at 2h
        window2 = [
            _make_alert(ticker="FB", triggered_at=now + timedelta(hours=2, minutes=i))
            for i in range(0, 30, 10)
        ]
        groups = group_related_alerts(window1 + window2)
        assert len(groups) == 2


# ---------------------------------------------------------------------------
# AlertGroup – helpers
# ---------------------------------------------------------------------------


class TestAlertGroupHelpers:
    def test_count_property(self):
        group = AlertGroup(ticker="X")
        assert group.count == 0
        alert = _make_alert()
        group.add(alert, priority=50)
        assert group.count == 1

    def test_add_updates_highest_priority(self):
        group = AlertGroup(ticker="Y")
        group.add(_make_alert(), priority=30)
        group.add(_make_alert(), priority=80)
        group.add(_make_alert(), priority=50)
        assert group.highest_priority == 80

    def test_initial_highest_priority_is_zero(self):
        group = AlertGroup(ticker="Z")
        assert group.highest_priority == 0


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------


class TestPriorityProperties:
    @given(
        sentiment=st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        impact=st.one_of(
            st.none(),
            st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        ),
    )
    @settings(max_examples=25)
    def test_priority_always_non_negative(self, sentiment, impact):
        """calculate_priority must never return a negative value."""
        alert = _make_alert(sentiment_score=sentiment, predicted_impact=impact)
        assert calculate_priority(alert) >= 0

    @given(
        alert_type=st.sampled_from(list(AlertType)),
    )
    @settings(max_examples=25)
    def test_all_alert_types_return_positive_priority(self, alert_type):
        alert = _make_alert(alert_type=alert_type)
        assert calculate_priority(alert) > 0

    @given(
        n=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=25)
    def test_group_count_never_exceeds_input_count(self, n):
        """Number of groups ≤ number of input alerts."""
        now = datetime.now(timezone.utc)
        alerts = [_make_alert(triggered_at=now + timedelta(minutes=i)) for i in range(n)]
        groups = group_related_alerts(alerts)
        total_in_groups = sum(g.count for g in groups)
        assert total_in_groups == n

    @given(
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=25)
    def test_groups_sorted_descending_by_priority(self, n):
        """Returned groups are ordered from highest to lowest priority."""
        now = datetime.now(timezone.utc)
        # Use varied alert types to get different priorities
        types = list(AlertType)
        alerts = [
            _make_alert(
                alert_type=types[i % len(types)],
                ticker=f"T{i}",
                triggered_at=now + timedelta(minutes=i),
            )
            for i in range(n)
        ]
        groups = group_related_alerts(alerts)
        priorities = [g.highest_priority for g in groups]
        assert priorities == sorted(priorities, reverse=True)
