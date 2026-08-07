"""
Penny stock alert system.

Detects momentum, extreme gain, pump-dump, and insider-activity conditions
that should trigger alerts for penny stocks.

Requirements: 11.11, 11.20
Property Tests: Property 52 — high-priority alert when intraday gain > 100%

Functions:
    detect_momentum_threshold(stock, threshold)  → bool
    detect_high_priority_gain(stock)             → bool  (Property 52)
    detect_pump_dump_warning(stock, suspicion_score) → bool
    detect_insider_activity_alert(ticker)        → bool
"""

from __future__ import annotations

import logging
from typing import Optional

from ..penny.scanner import PennyStock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional integration with existing risk / pump-dump infrastructure
# ---------------------------------------------------------------------------

try:
    from ..penny.risk import PumpDumpDetector, InsiderActivity
    RISK_AVAILABLE = True
except Exception:  # pragma: no cover
    RISK_AVAILABLE = False
    logger.warning("Penny risk module not available — insider/pump-dump detection degraded")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

#: Intraday gain that triggers a HIGH-PRIORITY alert (Property 52, Req 11.20)
HIGH_PRIORITY_GAIN_THRESHOLD: float = 100.0

#: Suspicion score threshold that triggers a pump-dump warning (Req 11.14)
PUMP_DUMP_SUSPICION_THRESHOLD: float = 0.7

#: Minimum net insider transactions to be considered "significant"
SIGNIFICANT_INSIDER_TRANSACTIONS: int = 3


# ---------------------------------------------------------------------------
# Public alert functions
# ---------------------------------------------------------------------------


def detect_momentum_threshold(stock: PennyStock, threshold: float) -> bool:
    """
    Return True when the stock's momentum score crosses (≥) *threshold*.

    Requirement 11.11 — alerts when penny stocks cross momentum thresholds.

    The function checks ``stock.momentum_score`` directly.  If the stock has
    no pre-computed momentum score (``None``), the function returns ``False``
    because the score has not yet been calculated.

    Args:
        stock:     PennyStock with an optional momentum_score attribute.
        threshold: Score value (0–100) above which an alert should fire.

    Returns:
        True if stock.momentum_score is not None and ≥ threshold, else False.

    Example::

        stock = PennyStock(..., momentum_score=75.0, ...)
        detect_momentum_threshold(stock, threshold=70.0)  # → True
        detect_momentum_threshold(stock, threshold=80.0)  # → False
    """
    if stock.momentum_score is None:
        logger.debug(
            "detect_momentum_threshold: %s has no momentum_score — skipping",
            stock.ticker,
        )
        return False

    triggered = stock.momentum_score >= threshold
    if triggered:
        logger.info(
            "ALERT momentum_threshold ticker=%s score=%.2f threshold=%.2f",
            stock.ticker, stock.momentum_score, threshold,
        )
    return triggered


def detect_high_priority_gain(stock: PennyStock) -> bool:
    """
    Return True when the stock's intraday gain exceeds 100%.

    **Property 52** — Trigger high-priority alert when intraday gain > 100%.
    **Requirement 11.20** — WHEN penny stock gains exceed 100% intraday, THE
    System SHALL send high-priority alerts.

    The check is ``stock.price_change_pct > 100.0`` (strictly greater than,
    not ≥).

    Args:
        stock: PennyStock with a price_change_pct value.

    Returns:
        True if the intraday gain is strictly greater than 100 %.

    **Validates: Requirements 11.20**
    Property 52: high-priority alert threshold (> 100% intraday)
    """
    triggered = stock.price_change_pct > HIGH_PRIORITY_GAIN_THRESHOLD
    if triggered:
        logger.warning(
            "HIGH-PRIORITY ALERT intraday gain > 100%% ticker=%s gain=%.2f%%",
            stock.ticker, stock.price_change_pct,
        )
    return triggered


def detect_pump_dump_warning(stock: PennyStock, suspicion_score: float) -> bool:
    """
    Return True when *suspicion_score* exceeds the pump-dump threshold (> 0.7).

    Requirement 11.14 — flag penny stocks with suspicious patterns.

    The caller is responsible for computing the *suspicion_score* (typically
    via ``PumpDumpDetector.detect_suspicious_patterns``).  This function is a
    pure threshold check so it can be tested and used without the full
    risk-analysis pipeline.

    Args:
        stock:            PennyStock being evaluated (used for logging only).
        suspicion_score:  Float in [0, 1]; higher = more suspicious.

    Returns:
        True if suspicion_score > PUMP_DUMP_SUSPICION_THRESHOLD (0.7).

    Raises:
        ValueError: if suspicion_score is outside [0, 1].
    """
    if not (0.0 <= suspicion_score <= 1.0):
        raise ValueError(
            f"suspicion_score must be in [0, 1], got {suspicion_score!r}"
        )

    triggered = suspicion_score > PUMP_DUMP_SUSPICION_THRESHOLD
    if triggered:
        logger.warning(
            "PUMP-DUMP WARNING ticker=%s suspicion_score=%.3f",
            stock.ticker, suspicion_score,
        )
    return triggered


def detect_insider_activity_alert(ticker: str) -> bool:
    """
    Return True when significant insider buying or selling is detected for
    *ticker*.

    Requirement 11.13 — show insider trading activity for penny stocks with
    sudden gains.

    The function uses ``PumpDumpDetector.check_insider_activity`` when the
    risk module is available, and degrades gracefully (returns False) when it
    is not.

    "Significant" activity is defined as:
    - ``InsiderActivity.suspicious`` is True, **or**
    - ``InsiderActivity.net_activity`` is ``'buying'`` or ``'selling'`` **and**
      the dominant side has at least ``SIGNIFICANT_INSIDER_TRANSACTIONS``
      (3) transactions.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        True if significant insider activity is detected, else False.
    """
    if not RISK_AVAILABLE:
        logger.debug(
            "detect_insider_activity_alert: risk module unavailable — "
            "returning False for %s",
            ticker,
        )
        return False

    try:
        detector = PumpDumpDetector()
        activity: InsiderActivity = detector.check_insider_activity(ticker)

        # Primary flag: the detector itself marked it suspicious
        if activity.suspicious:
            logger.warning(
                "INSIDER ALERT (suspicious flag) ticker=%s buys=%d sells=%d",
                ticker, activity.recent_buys, activity.recent_sells,
            )
            return True

        # Secondary flag: significant net directional activity
        if activity.net_activity == "buying":
            significant = activity.recent_buys >= SIGNIFICANT_INSIDER_TRANSACTIONS
        elif activity.net_activity == "selling":
            significant = activity.recent_sells >= SIGNIFICANT_INSIDER_TRANSACTIONS
        else:
            significant = False

        if significant:
            logger.info(
                "INSIDER ALERT (%s) ticker=%s buys=%d sells=%d",
                activity.net_activity, ticker,
                activity.recent_buys, activity.recent_sells,
            )
        return significant

    except Exception as exc:
        logger.warning(
            "detect_insider_activity_alert: unexpected error for %s: %s",
            ticker, exc,
        )
        return False
