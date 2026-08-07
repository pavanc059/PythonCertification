"""
Tests for the penny stock alert system (stockiq/news/alerts/penny_alerts.py).

Covers:
- detect_momentum_threshold   (unit + property)
- detect_high_priority_gain   (unit + property — Property 52)
- detect_pump_dump_warning    (unit + property)
- detect_insider_activity_alert (unit)

Property 52: high-priority alert fires iff intraday gain > 100%.

**Validates: Requirements 11.11, 11.20**
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from stockiq.news.penny.scanner import PennyStock, RiskMetrics
from stockiq.news.alerts.penny_alerts import (
    detect_momentum_threshold,
    detect_high_priority_gain,
    detect_pump_dump_warning,
    detect_insider_activity_alert,
    HIGH_PRIORITY_GAIN_THRESHOLD,
    PUMP_DUMP_SUSPICION_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_penny(
    ticker: str = "TEST",
    price: float = 1.00,
    price_change_pct: float = 0.0,
    volume: int = 100_000,
    avg_volume: int = 50_000,
    momentum_score: float | None = None,
    catalyst: str | None = None,
) -> PennyStock:
    """Build a PennyStock with sensible defaults."""
    vol_ratio = volume / avg_volume if avg_volume > 0 else 0.0
    return PennyStock(
        ticker=ticker,
        price=Decimal(str(price)),
        price_change_pct=price_change_pct,
        volume=volume,
        avg_volume=avg_volume,
        volume_ratio=vol_ratio,
        market_cap=5_000_000,
        sector="Technology",
        momentum_score=momentum_score,
        catalyst=catalyst,
    )


# ---------------------------------------------------------------------------
# detect_momentum_threshold — unit tests
# ---------------------------------------------------------------------------

class TestDetectMomentumThreshold:
    """Unit tests for detect_momentum_threshold."""

    def test_fires_when_score_above_threshold(self):
        stock = make_penny(momentum_score=75.0)
        assert detect_momentum_threshold(stock, threshold=70.0) is True

    def test_fires_when_score_equals_threshold(self):
        """Boundary: score exactly at threshold should trigger."""
        stock = make_penny(momentum_score=70.0)
        assert detect_momentum_threshold(stock, threshold=70.0) is True

    def test_does_not_fire_when_score_below_threshold(self):
        stock = make_penny(momentum_score=69.9)
        assert detect_momentum_threshold(stock, threshold=70.0) is False

    def test_returns_false_when_momentum_score_is_none(self):
        """No score computed yet → no alert."""
        stock = make_penny(momentum_score=None)
        assert detect_momentum_threshold(stock, threshold=0.0) is False

    def test_zero_threshold_fires_for_any_nonnegative_score(self):
        stock = make_penny(momentum_score=0.01)
        assert detect_momentum_threshold(stock, threshold=0.0) is True

    def test_threshold_100_fires_only_at_max(self):
        stock_max = make_penny(momentum_score=100.0)
        stock_below = make_penny(momentum_score=99.9)
        assert detect_momentum_threshold(stock_max, threshold=100.0) is True
        assert detect_momentum_threshold(stock_below, threshold=100.0) is False

    def test_returns_bool(self):
        stock = make_penny(momentum_score=50.0)
        result = detect_momentum_threshold(stock, threshold=40.0)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# detect_high_priority_gain — unit tests (Property 52)
# ---------------------------------------------------------------------------

class TestDetectHighPriorityGain:
    """
    Unit tests for detect_high_priority_gain.

    Property 52: alert fires iff price_change_pct > 100%.
    **Validates: Requirements 11.20**
    """

    def test_fires_for_gain_above_100_pct(self):
        stock = make_penny(price_change_pct=100.1)
        assert detect_high_priority_gain(stock) is True

    def test_fires_for_exactly_200_pct_gain(self):
        stock = make_penny(price_change_pct=200.0)
        assert detect_high_priority_gain(stock) is True

    def test_does_not_fire_for_exactly_100_pct_gain(self):
        """Boundary: 100% is NOT strictly greater than 100% — no alert."""
        stock = make_penny(price_change_pct=100.0)
        assert detect_high_priority_gain(stock) is False

    def test_does_not_fire_for_99_pct_gain(self):
        stock = make_penny(price_change_pct=99.0)
        assert detect_high_priority_gain(stock) is False

    def test_does_not_fire_for_zero_gain(self):
        stock = make_penny(price_change_pct=0.0)
        assert detect_high_priority_gain(stock) is False

    def test_does_not_fire_for_negative_change(self):
        stock = make_penny(price_change_pct=-50.0)
        assert detect_high_priority_gain(stock) is False

    def test_returns_bool(self):
        stock = make_penny(price_change_pct=150.0)
        assert isinstance(detect_high_priority_gain(stock), bool)

    def test_threshold_constant_is_100(self):
        """Confirms the module constant matches the spec."""
        assert HIGH_PRIORITY_GAIN_THRESHOLD == 100.0


# ---------------------------------------------------------------------------
# Property 52 — property-based test
# ---------------------------------------------------------------------------

@given(gain=st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=300)
def test_property_52_high_priority_gain_threshold(gain: float):
    """
    **Property 52**: detect_high_priority_gain returns True iff
    price_change_pct > 100.0 for all finite gain values.

    **Validates: Requirements 11.20**
    """
    # PennyStock price must be <= $5 — price is irrelevant here, just use 1.00
    stock = make_penny(price_change_pct=gain)
    result = detect_high_priority_gain(stock)
    if gain > 100.0:
        assert result is True, f"Expected True for gain={gain}, got False"
    else:
        assert result is False, f"Expected False for gain={gain}, got True"


# ---------------------------------------------------------------------------
# detect_pump_dump_warning — unit tests
# ---------------------------------------------------------------------------

class TestDetectPumpDumpWarning:
    """Unit tests for detect_pump_dump_warning."""

    def test_fires_for_score_above_0_7(self):
        stock = make_penny()
        assert detect_pump_dump_warning(stock, suspicion_score=0.71) is True

    def test_fires_for_score_of_1_0(self):
        stock = make_penny()
        assert detect_pump_dump_warning(stock, suspicion_score=1.0) is True

    def test_does_not_fire_for_exactly_0_7(self):
        """Boundary: 0.7 is NOT strictly greater — no alert."""
        stock = make_penny()
        assert detect_pump_dump_warning(stock, suspicion_score=0.7) is False

    def test_does_not_fire_for_score_below_0_7(self):
        stock = make_penny()
        assert detect_pump_dump_warning(stock, suspicion_score=0.5) is False

    def test_does_not_fire_for_zero_score(self):
        stock = make_penny()
        assert detect_pump_dump_warning(stock, suspicion_score=0.0) is False

    def test_raises_for_negative_score(self):
        stock = make_penny()
        with pytest.raises(ValueError, match="suspicion_score"):
            detect_pump_dump_warning(stock, suspicion_score=-0.1)

    def test_raises_for_score_above_1(self):
        stock = make_penny()
        with pytest.raises(ValueError, match="suspicion_score"):
            detect_pump_dump_warning(stock, suspicion_score=1.01)

    def test_threshold_constant_is_0_7(self):
        assert PUMP_DUMP_SUSPICION_THRESHOLD == 0.7

    def test_returns_bool(self):
        stock = make_penny()
        result = detect_pump_dump_warning(stock, suspicion_score=0.5)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# detect_pump_dump_warning — property-based test
# ---------------------------------------------------------------------------

@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=300)
def test_pump_dump_warning_threshold_property(score: float):
    """
    For any suspicion_score in [0, 1], the warning fires iff score > 0.7.
    """
    stock = make_penny()
    result = detect_pump_dump_warning(stock, suspicion_score=score)
    if score > PUMP_DUMP_SUSPICION_THRESHOLD:
        assert result is True, f"Expected True for score={score}"
    else:
        assert result is False, f"Expected False for score={score}"


# ---------------------------------------------------------------------------
# detect_insider_activity_alert — unit tests
# ---------------------------------------------------------------------------

class TestDetectInsiderActivityAlert:
    """Unit tests for detect_insider_activity_alert."""

    def _make_activity(
        self,
        recent_buys: int = 0,
        recent_sells: int = 0,
        net_activity: str = "neutral",
        suspicious: bool = False,
    ):
        """Build a mock InsiderActivity object."""
        from stockiq.news.penny.risk import InsiderActivity
        return InsiderActivity(
            ticker="TST",
            recent_buys=recent_buys,
            recent_sells=recent_sells,
            net_activity=net_activity,
            suspicious=suspicious,
        )

    def test_fires_when_suspicious_flag_is_true(self):
        activity = self._make_activity(suspicious=True)
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            return_value=activity,
        ):
            assert detect_insider_activity_alert("TST") is True

    def test_fires_for_significant_buying(self):
        activity = self._make_activity(
            recent_buys=5, net_activity="buying", suspicious=False
        )
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            return_value=activity,
        ):
            assert detect_insider_activity_alert("TST") is True

    def test_fires_for_significant_selling(self):
        activity = self._make_activity(
            recent_sells=4, net_activity="selling", suspicious=False
        )
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            return_value=activity,
        ):
            assert detect_insider_activity_alert("TST") is True

    def test_does_not_fire_for_insufficient_buying(self):
        """Less than 3 buys with net_activity='buying' → no alert."""
        activity = self._make_activity(
            recent_buys=2, net_activity="buying", suspicious=False
        )
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            return_value=activity,
        ):
            assert detect_insider_activity_alert("TST") is False

    def test_does_not_fire_for_neutral_activity(self):
        activity = self._make_activity(
            recent_buys=10, recent_sells=10, net_activity="neutral", suspicious=False
        )
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            return_value=activity,
        ):
            assert detect_insider_activity_alert("TST") is False

    def test_returns_false_when_risk_unavailable(self):
        """If RISK_AVAILABLE is False the function degrades gracefully → False."""
        with patch(
            "stockiq.news.alerts.penny_alerts.RISK_AVAILABLE",
            False,
        ):
            assert detect_insider_activity_alert("ANY") is False

    def test_returns_false_on_unexpected_exception(self):
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            side_effect=RuntimeError("db down"),
        ):
            assert detect_insider_activity_alert("ERR") is False

    def test_returns_bool(self):
        activity = self._make_activity()
        with patch(
            "stockiq.news.alerts.penny_alerts.PumpDumpDetector.check_insider_activity",
            return_value=activity,
        ):
            result = detect_insider_activity_alert("TST")
            assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Integration: combined scenario
# ---------------------------------------------------------------------------

class TestCombinedAlertScenario:
    """
    Verify that multiple alert functions can be composed for a single stock
    with extreme characteristics.
    """

    def test_all_alerts_fire_for_extreme_pump_and_dump_stock(self):
        """A stock with 150% gain, momentum=95, suspicion=0.9 → all alerts fire."""
        stock = make_penny(
            ticker="PUMP",
            price_change_pct=150.0,
            momentum_score=95.0,
        )
        assert detect_high_priority_gain(stock) is True          # Property 52
        assert detect_momentum_threshold(stock, 90.0) is True    # Req 11.11
        assert detect_pump_dump_warning(stock, 0.9) is True      # Req 11.14

    def test_normal_stock_no_alerts_fire(self):
        """A low-momentum, small-gain stock should trigger no alerts."""
        stock = make_penny(
            ticker="CALM",
            price_change_pct=5.0,
            momentum_score=20.0,
        )
        assert detect_high_priority_gain(stock) is False
        assert detect_momentum_threshold(stock, 70.0) is False
        assert detect_pump_dump_warning(stock, 0.2) is False


# ---------------------------------------------------------------------------
# Module import smoke test
# ---------------------------------------------------------------------------

def test_module_imports_cleanly():
    """All four functions are importable from the alerts package."""
    from stockiq.news.alerts import (
        detect_momentum_threshold,
        detect_high_priority_gain,
        detect_pump_dump_warning,
        detect_insider_activity_alert,
    )
    assert callable(detect_momentum_threshold)
    assert callable(detect_high_priority_gain)
    assert callable(detect_pump_dump_warning)
    assert callable(detect_insider_activity_alert)
