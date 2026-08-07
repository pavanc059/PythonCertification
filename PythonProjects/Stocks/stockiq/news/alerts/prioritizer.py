"""
Alert Prioritizer.

Assigns integer priority scores to news alerts and groups related alerts
by ticker within a 1-hour window to prevent notification spam.

Requirements: 5.7, 5.8, 5.10, 5.12
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from stockiq.news.alerts.detector import AlertType, NewsAlert

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority constants
# Breaking news > earnings > M&A > regulatory > general
# Higher integer = more urgent.
# ---------------------------------------------------------------------------

#: Base priority scores per alert type (before adjustments).
_BASE_PRIORITY: Dict[AlertType, int] = {
    AlertType.BREAKING_NEWS: 100,
    AlertType.EARNINGS:      80,
    AlertType.MA:            60,
    AlertType.REGULATORY:    40,
    AlertType.SENTIMENT_CHANGE: 30,
    AlertType.GENERAL:       20,
}

#: Sentinel for alert types not explicitly listed (treated as GENERAL).
_DEFAULT_BASE_PRIORITY = _BASE_PRIORITY[AlertType.GENERAL]

#: Maximum bonus that sentiment magnitude and predicted impact can contribute.
_MAX_SENTIMENT_BONUS = 10
_MAX_IMPACT_BONUS = 10

#: Time window used to group alerts for the same ticker.
_GROUP_WINDOW = timedelta(hours=1)


# ---------------------------------------------------------------------------
# AlertGroup dataclass
# ---------------------------------------------------------------------------


@dataclass
class AlertGroup:
    """
    A collection of related alerts for the same ticker within a 1-hour window.

    Attributes:
        ticker:       The stock ticker all alerts in this group share.
        alerts:       Ordered list of alerts (earliest first).
        highest_priority: Pre-computed maximum priority across all alerts.
    """

    ticker: str
    alerts: List[NewsAlert] = field(default_factory=list)
    highest_priority: int = 0

    def add(self, alert: NewsAlert, priority: int) -> None:
        """Append *alert* to the group and update *highest_priority*."""
        self.alerts.append(alert)
        if priority > self.highest_priority:
            self.highest_priority = priority

    @property
    def count(self) -> int:
        """Number of alerts in this group."""
        return len(self.alerts)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def calculate_priority(alert: NewsAlert) -> int:
    """
    Return an integer priority score for *alert*.

    Higher values indicate greater urgency.  The score is composed of:

    1. **Base score** — determined by :class:`AlertType`:
       - BREAKING_NEWS:   100
       - EARNINGS:         80
       - M&A:              60
       - REGULATORY:       40
       - SENTIMENT_CHANGE: 30
       - GENERAL:          20

    2. **Sentiment magnitude bonus** (0–10):
       Proportional to ``|alert.sentiment_score|`` (capped at 1.0).
       A score of ±1.0 gives the full +10 bonus.

    3. **Predicted impact bonus** (0–10):
       Proportional to ``|alert.predicted_impact|`` (capped at 1.0).
       Only applied when *predicted_impact* is not ``None``.

    Args:
        alert: The :class:`~stockiq.news.alerts.detector.NewsAlert` to score.

    Returns:
        Integer priority ≥ 0.  A higher score means the alert is more urgent.

    **Validates: Requirements 5.7, 5.12**
    """
    base = _BASE_PRIORITY.get(alert.alert_type, _DEFAULT_BASE_PRIORITY)

    # Sentiment magnitude bonus: 0–10 based on |sentiment_score| in [0, 1]
    sentiment_mag = min(abs(alert.sentiment_score), 1.0)
    sentiment_bonus = round(sentiment_mag * _MAX_SENTIMENT_BONUS)

    # Predicted impact bonus: 0–10 based on |predicted_impact| in [0, 1]
    impact_bonus = 0
    if alert.predicted_impact is not None:
        impact_mag = min(abs(alert.predicted_impact), 1.0)
        impact_bonus = round(impact_mag * _MAX_IMPACT_BONUS)

    total = base + sentiment_bonus + impact_bonus
    logger.debug(
        "calculate_priority ticker=%s type=%s base=%d sentiment_bonus=%d "
        "impact_bonus=%d total=%d",
        alert.ticker,
        alert.alert_type,
        base,
        sentiment_bonus,
        impact_bonus,
        total,
    )
    return total


def group_related_alerts(alerts: List[NewsAlert]) -> List[AlertGroup]:
    """
    Group *alerts* by ticker within a 1-hour sliding window.

    Alerts for the same ticker that were triggered within 60 minutes of the
    **earliest** alert in an existing group are merged into that group.
    This prevents notification spam when multiple news items arrive at
    once for the same stock (Requirement 5.10).

    Algorithm:
    1. Sort *alerts* chronologically by ``triggered_at``.
    2. For each alert, find an open group whose ticker matches and whose
       earliest alert falls within 1 hour of the current alert.
    3. If no matching group exists, start a new one.
    4. Return groups sorted by descending ``highest_priority``.

    Args:
        alerts: Flat list of :class:`~stockiq.news.alerts.detector.NewsAlert`
                objects to group.  May be empty.

    Returns:
        List of :class:`AlertGroup` objects, each representing a set of
        related alerts.  Groups are ordered from highest to lowest priority
        so callers can deliver the most important notifications first.

    **Validates: Requirements 5.10, 5.12**
    """
    if not alerts:
        return []

    # Sort chronologically so we can use a stable "window start" per group.
    sorted_alerts = sorted(alerts, key=lambda a: _alert_time(a))

    # ticker → list of groups (a ticker may span multiple non-overlapping windows)
    groups_by_ticker: Dict[str, List[AlertGroup]] = {}

    for alert in sorted_alerts:
        ticker = alert.ticker.upper()
        priority = calculate_priority(alert)
        alert_time = _alert_time(alert)

        placed = False
        if ticker in groups_by_ticker:
            # Try to fit into an existing group for this ticker.
            for group in groups_by_ticker[ticker]:
                window_start = _alert_time(group.alerts[0])
                if alert_time - window_start <= _GROUP_WINDOW:
                    group.add(alert, priority)
                    placed = True
                    break

        if not placed:
            # Start a new group for this ticker.
            new_group = AlertGroup(ticker=ticker)
            new_group.add(alert, priority)
            groups_by_ticker.setdefault(ticker, []).append(new_group)

    # Flatten all groups and sort by descending highest_priority.
    all_groups: List[AlertGroup] = [
        g for gs in groups_by_ticker.values() for g in gs
    ]
    all_groups.sort(key=lambda g: g.highest_priority, reverse=True)
    return all_groups


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _alert_time(alert: NewsAlert) -> datetime:
    """
    Return a timezone-aware UTC datetime for *alert.triggered_at*.

    Handles naive datetimes by assuming UTC.
    """
    ts = alert.triggered_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts
