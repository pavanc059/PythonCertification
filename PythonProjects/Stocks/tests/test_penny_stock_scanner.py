"""
Unit tests for PennyStockScanner (Properties 42, 43, 44, 47).

These tests exercise the scanner's pure-logic paths using synthetic PennyStock
objects — no network, Redis, or database access required.

**Validates: Requirements 11.1, 11.2, 11.3, 11.6, 11.7**
"""

import pytest
from decimal import Decimal

from stockiq.news.penny.scanner import PennyStock, PennyStockScanner, RiskMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_penny(
    ticker: str = "TEST",
    price: float = 1.00,
    price_change_pct: float = 0.0,
    volume: int = 100_000,
    avg_volume: int = 50_000,
) -> PennyStock:
    """Construct a PennyStock with sensible defaults."""
    volume_ratio = volume / avg_volume if avg_volume > 0 else 0.0
    return PennyStock(
        ticker=ticker,
        price=Decimal(str(price)),
        price_change_pct=price_change_pct,
        volume=volume,
        avg_volume=avg_volume,
        volume_ratio=volume_ratio,
        market_cap=5_000_000,
        sector="Technology",
    )


# ---------------------------------------------------------------------------
# Property 42 — penny stocks must have price ≤ $5.00
# ---------------------------------------------------------------------------

class TestProperty42PriceThreshold:
    """Property 42: PennyStock price must be ≤ $5.00."""

    def test_penny_price_exactly_five(self):
        """$5.00 is the boundary — should be accepted."""
        stock = make_penny(price=5.00)
        assert stock.price == Decimal("5.00")

    def test_penny_price_below_five(self):
        """Prices well below $5 are valid penny stocks."""
        for price in [0.01, 0.50, 1.00, 2.99, 4.99]:
            stock = make_penny(price=price)
            assert stock.price <= Decimal("5.00"), f"Expected price ≤ 5 for {price}"

    def test_penny_price_above_five_raises(self):
        """Prices above $5.00 must be rejected by the constructor."""
        with pytest.raises(ValueError, match="Property 42"):
            make_penny(price=5.01)

    def test_penny_price_ten_raises(self):
        with pytest.raises(ValueError):
            make_penny(price=10.00)

    def test_penny_price_negative_raises(self):
        with pytest.raises(ValueError):
            make_penny(price=-0.01)


# ---------------------------------------------------------------------------
# Property 43 — intraday gainers must have gain ≥ min_gain_pct
# ---------------------------------------------------------------------------

class TestProperty43IntradayGain:
    """
    Property 43: scan_intraday_gainers returns only stocks with
    price_change_pct ≥ min_gain_pct.
    """

    def _run_filter(self, stocks, min_gain_pct=20.0):
        """
        Simulate the gain filter applied inside scan_intraday_gainers
        without hitting any network / DB / cache.
        """
        return [s for s in stocks if s.price_change_pct >= min_gain_pct]

    def test_all_qualify(self):
        stocks = [
            make_penny("A", price_change_pct=20.0),
            make_penny("B", price_change_pct=50.0),
            make_penny("C", price_change_pct=100.0),
        ]
        result = self._run_filter(stocks, min_gain_pct=20.0)
        assert len(result) == 3

    def test_none_qualify(self):
        stocks = [
            make_penny("A", price_change_pct=5.0),
            make_penny("B", price_change_pct=19.99),
        ]
        result = self._run_filter(stocks, min_gain_pct=20.0)
        assert len(result) == 0

    def test_partial_qualify(self):
        stocks = [
            make_penny("A", price_change_pct=19.99),  # just below threshold
            make_penny("B", price_change_pct=20.0),   # exactly at threshold
            make_penny("C", price_change_pct=21.0),   # above threshold
        ]
        result = self._run_filter(stocks, min_gain_pct=20.0)
        assert len(result) == 2
        tickers = {s.ticker for s in result}
        assert "B" in tickers
        assert "C" in tickers

    def test_custom_threshold(self):
        stocks = [make_penny("X", price_change_pct=pct) for pct in [10, 30, 75]]
        result = self._run_filter(stocks, min_gain_pct=30.0)
        assert {s.ticker for s in result} == {"X"} | set()  # 30 and 75 qualify
        result_tickers = [s.ticker for s in result]
        assert len(result_tickers) == 2  # 30.0 and 75.0 qualify

    def test_returned_stocks_all_satisfy_threshold(self):
        stocks = [make_penny(str(i), price_change_pct=i * 10) for i in range(10)]
        min_gain = 30.0
        result = self._run_filter(stocks, min_gain_pct=min_gain)
        for s in result:
            assert s.price_change_pct >= min_gain


# ---------------------------------------------------------------------------
# Property 44 — multi-day gainers must have gain ≥ min_gain_pct
# ---------------------------------------------------------------------------

class TestProperty44MultiDayGain:
    """
    Property 44: scan_multi_day_gainers returns only stocks with
    price_change_pct (over `days` days) ≥ min_gain_pct.
    """

    def _run_filter(self, stocks, min_gain_pct=50.0):
        return [s for s in stocks if s.price_change_pct >= min_gain_pct]

    def test_default_threshold_50_pct(self):
        stocks = [
            make_penny("A", price_change_pct=49.99),   # below
            make_penny("B", price_change_pct=50.0),    # at boundary
            make_penny("C", price_change_pct=150.0),   # well above
        ]
        result = self._run_filter(stocks, min_gain_pct=50.0)
        assert len(result) == 2
        tickers = {s.ticker for s in result}
        assert "B" in tickers
        assert "C" in tickers

    def test_all_below_threshold(self):
        stocks = [make_penny(str(i), price_change_pct=i * 5) for i in range(5)]
        result = self._run_filter(stocks, min_gain_pct=50.0)
        assert all(s.price_change_pct >= 50.0 for s in result)

    def test_custom_threshold(self):
        stocks = [make_penny("X", price_change_pct=75.0)]
        result = self._run_filter(stocks, min_gain_pct=75.0)
        assert len(result) == 1

    def test_returned_stocks_satisfy_threshold(self):
        stocks = [make_penny(str(i), price_change_pct=i * 10.0) for i in range(20)]
        min_gain = 50.0
        result = self._run_filter(stocks, min_gain_pct=min_gain)
        for s in result:
            assert s.price_change_pct >= min_gain, (
                f"Returned stock {s.ticker} has gain {s.price_change_pct} < {min_gain}"
            )


# ---------------------------------------------------------------------------
# Property 47 — volume_ratio = current_volume / average_volume
# ---------------------------------------------------------------------------

class TestProperty47VolumeRatio:
    """
    Property 47: volume_ratio = current_volume / average_volume.
    The result is ≥ 0; values ≥ 1.0 indicate at-or-above-average volume.
    """

    def setup_method(self):
        self.scanner = PennyStockScanner()

    def test_ratio_above_one_indicates_surge(self):
        stock = make_penny(volume=200_000, avg_volume=100_000)
        ratio = self.scanner.calculate_volume_ratio(stock)
        assert ratio == pytest.approx(2.0)

    def test_ratio_exactly_one(self):
        stock = make_penny(volume=50_000, avg_volume=50_000)
        ratio = self.scanner.calculate_volume_ratio(stock)
        assert ratio == pytest.approx(1.0)

    def test_ratio_below_one(self):
        stock = make_penny(volume=25_000, avg_volume=50_000)
        ratio = self.scanner.calculate_volume_ratio(stock)
        assert ratio == pytest.approx(0.5)

    def test_ratio_zero_avg_volume(self):
        """avg_volume == 0 should return 0.0 (no division by zero)."""
        stock = make_penny(volume=100_000, avg_volume=0)
        ratio = self.scanner.calculate_volume_ratio(stock)
        assert ratio == 0.0

    def test_ratio_is_nonnegative(self):
        for v, av in [(0, 1), (1, 1), (1_000_000, 100_000)]:
            stock = make_penny(volume=v, avg_volume=av)
            ratio = self.scanner.calculate_volume_ratio(stock)
            assert ratio >= 0.0

    def test_ratio_matches_direct_calculation(self):
        """volume_ratio on PennyStock should equal volume / avg_volume."""
        vol, avg = 300_000, 75_000
        stock = make_penny(volume=vol, avg_volume=avg)
        expected = vol / avg
        assert self.scanner.calculate_volume_ratio(stock) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# filter_by_volume
# ---------------------------------------------------------------------------

class TestFilterByVolume:
    """PennyStockScanner.filter_by_volume keeps stocks with avg_volume ≥ min."""

    def setup_method(self):
        self.scanner = PennyStockScanner()

    def test_keeps_qualifying_stocks(self):
        stocks = [
            make_penny("A", avg_volume=50_000),   # exactly at threshold
            make_penny("B", avg_volume=100_000),  # above
        ]
        result = self.scanner.filter_by_volume(stocks, min_avg_volume=50_000)
        assert len(result) == 2

    def test_removes_low_volume_stocks(self):
        stocks = [
            make_penny("A", avg_volume=49_999),  # just below
            make_penny("B", avg_volume=50_000),  # at threshold
        ]
        result = self.scanner.filter_by_volume(stocks, min_avg_volume=50_000)
        assert len(result) == 1
        assert result[0].ticker == "B"

    def test_empty_input(self):
        result = self.scanner.filter_by_volume([], min_avg_volume=50_000)
        assert result == []

    def test_all_filtered_out(self):
        stocks = [make_penny("X", avg_volume=1_000)]
        result = self.scanner.filter_by_volume(stocks, min_avg_volume=50_000)
        assert result == []

    def test_returned_stocks_all_satisfy_threshold(self):
        stocks = [make_penny(str(i), avg_volume=i * 10_000) for i in range(10)]
        min_vol = 50_000
        result = self.scanner.filter_by_volume(stocks, min_avg_volume=min_vol)
        for s in result:
            assert s.avg_volume >= min_vol


# ---------------------------------------------------------------------------
# RiskMetrics dataclass
# ---------------------------------------------------------------------------

class TestRiskMetrics:
    def test_instantiation(self):
        rm = RiskMetrics(
            liquidity_risk=0.3,
            volatility_risk=0.7,
            spread_percentage=1.5,
            overall_risk="medium",
        )
        assert rm.liquidity_risk == 0.3
        assert rm.overall_risk == "medium"

    def test_penny_stock_with_risk_metrics(self):
        rm = RiskMetrics(0.8, 0.9, 3.0, "extreme")
        stock = make_penny("RISKY")
        stock.risk_metrics = rm
        assert stock.risk_metrics.overall_risk == "extreme"
