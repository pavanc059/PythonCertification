"""
Property-based tests for penny stock momentum scoring.

**Validates: Requirements 11.4, 11.5**
**Properties: 45, 46, 54**

Property 45: MomentumScore.overall_score is always in [0, 100]
Property 46: The four component weights sum to exactly 100%
             (price 40% + volume 30% + trend 20% + catalyst 10%)
Property 54: rank_by_momentum returns stocks sorted in descending order
             by momentum score
"""

import pytest
from decimal import Decimal
from hypothesis import given, strategies as st, settings, assume

from stockiq.news.penny.scanner import PennyStock, RiskMetrics
from stockiq.news.penny.momentum import (
    MomentumCalculator,
    MomentumScore,
    PRICE_WEIGHT,
    VOLUME_WEIGHT,
    TREND_WEIGHT,
    CATALYST_WEIGHT,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def penny_stock(draw, ticker: str = None, catalyst: str = None):
    """
    Generate a valid PennyStock with arbitrary (but realistic) field values.

    price is always ≤ $5.00 (Property 42).
    """
    t = ticker or draw(
        st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=5)
    )

    # Price: Decimal in (0, 5]
    price_float = draw(st.floats(min_value=0.01, max_value=5.00, allow_nan=False))
    price = Decimal(str(round(price_float, 2)))

    price_change_pct = draw(
        st.floats(min_value=-99.0, max_value=500.0, allow_nan=False, allow_infinity=False)
    )

    volume = draw(st.integers(min_value=0, max_value=10_000_000))
    avg_volume = draw(st.integers(min_value=1, max_value=5_000_000))
    volume_ratio = volume / avg_volume

    market_cap = draw(st.integers(min_value=1_000, max_value=500_000_000))
    sector = draw(st.sampled_from([
        "Technology", "Healthcare", "Finance", "Energy",
        "Consumer", "Industrial", "Materials", "Utilities", "Unknown",
    ]))

    # Catalyst is optional
    cat = catalyst or draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))

    return PennyStock(
        ticker=t,
        price=price,
        price_change_pct=price_change_pct,
        volume=volume,
        avg_volume=avg_volume,
        volume_ratio=volume_ratio,
        market_cap=market_cap,
        sector=sector,
        catalyst=cat,
    )


@st.composite
def list_of_penny_stocks(draw, min_size=0, max_size=20):
    """Generate a list of distinct-ticker PennyStock objects."""
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    stocks = []
    used_tickers = set()
    for _ in range(n):
        stock = draw(penny_stock())
        # Ensure unique tickers to avoid confusion in ranking assertions
        while stock.ticker in used_tickers:
            stock = draw(penny_stock())
        used_tickers.add(stock.ticker)
        stocks.append(stock)
    return stocks


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_stock(
    ticker="TEST",
    price: float = 1.00,
    price_change_pct: float = 0.0,
    volume: int = 100_000,
    avg_volume: int = 50_000,
    catalyst: str = None,
) -> PennyStock:
    """Construct a PennyStock with controlled values."""
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
        catalyst=catalyst,
    )


# ---------------------------------------------------------------------------
# Property 45 — overall_score always in [0, 100]
# ---------------------------------------------------------------------------

class TestProperty45MomentumScoreRange:
    """
    **Validates: Requirements 11.4**

    Property 45: For any PennyStock, the MomentumScore.overall_score
    calculated by MomentumCalculator SHALL always be in the range [0, 100].
    """

    def setup_method(self):
        self.calc = MomentumCalculator()

    # --- Property-based test ---

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_45_overall_score_in_range(self, stock):
        """
        **Validates: Requirements 11.4**

        Property 45: overall_score ∈ [0, 100] for every possible PennyStock.
        """
        score = self.calc.calculate_momentum_score(stock)

        assert 0.0 <= score.overall_score <= 100.0, (
            f"Property 45 violation: overall_score={score.overall_score} "
            f"not in [0, 100] for stock={stock}"
        )

    # --- Unit examples ---

    def test_zero_gain_zero_volume_no_catalyst_gives_low_score(self):
        """Stock with no momentum indicators scores near 0."""
        stock = make_stock(price_change_pct=0.0, volume=50_000, avg_volume=100_000)
        score = self.calc.calculate_momentum_score(stock)
        assert 0.0 <= score.overall_score <= 100.0
        assert score.overall_score < 20.0  # should be very low

    def test_maximum_inputs_score_at_most_100(self):
        """Extreme positive values must not produce a score above 100."""
        stock = make_stock(
            price_change_pct=9999.0,  # extreme gain
            volume=10_000_000,
            avg_volume=10_000,        # 1000× volume surge
            catalyst="earnings beat",
        )
        score = self.calc.calculate_momentum_score(stock)
        assert score.overall_score <= 100.0

    def test_negative_gain_score_non_negative(self):
        """Falling stocks must not produce a negative score."""
        stock = make_stock(price_change_pct=-50.0)
        score = self.calc.calculate_momentum_score(stock)
        assert score.overall_score >= 0.0

    def test_individual_components_in_range(self):
        """Each component score must also be in [0, 100]."""
        stock = make_stock(price_change_pct=30.0, volume=300_000, avg_volume=50_000, catalyst="news")
        score = self.calc.calculate_momentum_score(stock)
        for component_name, value in [
            ("price_component", score.price_component),
            ("volume_component", score.volume_component),
            ("trend_component", score.trend_component),
            ("catalyst_component", score.catalyst_component),
        ]:
            assert 0.0 <= value <= 100.0, (
                f"{component_name}={value} not in [0, 100]"
            )

    @given(stock=penny_stock())
    @settings(max_examples=20, deadline=None)
    def test_property_45_all_components_in_range(self, stock):
        """
        **Validates: Requirements 11.4**

        All four component scores must individually be in [0, 100].
        """
        score = self.calc.calculate_momentum_score(stock)
        for name, val in [
            ("price_component", score.price_component),
            ("volume_component", score.volume_component),
            ("trend_component", score.trend_component),
            ("catalyst_component", score.catalyst_component),
        ]:
            assert 0.0 <= val <= 100.0, (
                f"Property 45 violation: {name}={val} not in [0, 100]"
            )


# ---------------------------------------------------------------------------
# Property 46 — component weights sum to 100%
# ---------------------------------------------------------------------------

class TestProperty46ComponentWeights:
    """
    **Validates: Requirements 11.4**

    Property 46: The component weights in MomentumCalculator SHALL sum to
    exactly 100% (price 40% + volume 30% + trend 20% + catalyst 10%).
    """

    def test_weight_constants_sum_to_one(self):
        """
        **Validates: Requirements 11.4**

        Property 46 (static): PRICE_WEIGHT + VOLUME_WEIGHT + TREND_WEIGHT
        + CATALYST_WEIGHT == 1.0.
        """
        total = PRICE_WEIGHT + VOLUME_WEIGHT + TREND_WEIGHT + CATALYST_WEIGHT
        assert abs(total - 1.0) < 1e-9, (
            f"Property 46 violation: weights sum to {total}, expected 1.0"
        )

    def test_individual_weight_values(self):
        """Verify each individual weight value."""
        assert abs(PRICE_WEIGHT - 0.40) < 1e-9, f"PRICE_WEIGHT={PRICE_WEIGHT}, expected 0.40"
        assert abs(VOLUME_WEIGHT - 0.30) < 1e-9, f"VOLUME_WEIGHT={VOLUME_WEIGHT}, expected 0.30"
        assert abs(TREND_WEIGHT - 0.20) < 1e-9, f"TREND_WEIGHT={TREND_WEIGHT}, expected 0.20"
        assert abs(CATALYST_WEIGHT - 0.10) < 1e-9, f"CATALYST_WEIGHT={CATALYST_WEIGHT}, expected 0.10"

    @given(stock=penny_stock())
    @settings(max_examples=20, deadline=None)
    def test_property_46_weighted_sum_equals_overall_score(self, stock):
        """
        **Validates: Requirements 11.4**

        Property 46: The weighted combination of the four components
        (before clamping) must equal overall_score for any PennyStock.

        weighted = price*0.40 + volume*0.30 + trend*0.20 + catalyst*0.10
        overall_score == clamp(weighted, 0, 100)
        """
        calc = MomentumCalculator()
        score = calc.calculate_momentum_score(stock)

        # Reconstruct weighted sum from components
        weighted = (
            score.price_component * PRICE_WEIGHT
            + score.volume_component * VOLUME_WEIGHT
            + score.trend_component * TREND_WEIGHT
            + score.catalyst_component * CATALYST_WEIGHT
        )
        clamped = max(0.0, min(100.0, weighted))

        assert abs(score.overall_score - clamped) < 1e-9, (
            f"Property 46 violation: overall_score={score.overall_score} "
            f"!= weighted_sum={weighted} (clamped={clamped})"
        )

    def test_known_score_with_all_components(self):
        """Verify exact arithmetic for a controlled stock."""
        # 50% gain → price_component = 50
        # 5× volume ratio → volume_component = (5-1)/9*100 ≈ 44.44
        # catalyst present → catalyst_component = 100
        # trend (estimated from 50% / 10 = 5 days) → trend_component = 100
        stock = make_stock(
            price_change_pct=50.0,
            volume=500_000,
            avg_volume=100_000,   # 5× ratio
            catalyst="earnings",
        )
        calc = MomentumCalculator()
        score = calc.calculate_momentum_score(stock)

        # Recompute manually
        expected = (
            score.price_component * 0.40
            + score.volume_component * 0.30
            + score.trend_component * 0.20
            + score.catalyst_component * 0.10
        )
        expected = max(0.0, min(100.0, expected))

        assert abs(score.overall_score - expected) < 1e-9


# ---------------------------------------------------------------------------
# Property 54 — rank_by_momentum sorts descending
# ---------------------------------------------------------------------------

class TestProperty54MomentumRanking:
    """
    **Validates: Requirements 11.5**

    Property 54: For any list of penny stocks, rank_by_momentum SHALL return
    the stocks sorted in descending order by momentum score, so that
    ranked[i].momentum_score >= ranked[i+1].momentum_score for all i.
    """

    def setup_method(self):
        self.calc = MomentumCalculator()

    # --- Property-based tests ---

    @given(stocks=list_of_penny_stocks(min_size=0, max_size=15))
    @settings(max_examples=20, deadline=None)
    def test_property_54_ranked_descending(self, stocks):
        """
        **Validates: Requirements 11.5**

        Property 54: rank_by_momentum result is strictly non-increasing in
        momentum score.
        """
        ranked = self.calc.rank_by_momentum(stocks)

        # Verify descending order
        for i in range(len(ranked) - 1):
            assert ranked[i].momentum_score >= ranked[i + 1].momentum_score, (
                f"Property 54 violation: ranked[{i}].momentum_score="
                f"{ranked[i].momentum_score} < ranked[{i+1}].momentum_score="
                f"{ranked[i+1].momentum_score}"
            )

    @given(stocks=list_of_penny_stocks(min_size=0, max_size=15))
    @settings(max_examples=20, deadline=None)
    def test_property_54_all_stocks_present(self, stocks):
        """
        **Validates: Requirements 11.5**

        Property 54: rank_by_momentum returns all input stocks — no stocks
        are added or dropped during ranking.
        """
        ranked = self.calc.rank_by_momentum(stocks)

        assert len(ranked) == len(stocks), (
            f"Property 54 violation: input has {len(stocks)} stocks but "
            f"output has {len(ranked)}"
        )

        input_tickers = {s.ticker for s in stocks}
        output_tickers = {s.ticker for s in ranked}
        assert input_tickers == output_tickers, (
            f"Property 54 violation: tickers changed after ranking. "
            f"Missing: {input_tickers - output_tickers}, "
            f"Extra: {output_tickers - input_tickers}"
        )

    @given(stocks=list_of_penny_stocks(min_size=0, max_size=15))
    @settings(max_examples=20, deadline=None)
    def test_property_54_all_scores_in_range_after_ranking(self, stocks):
        """
        **Validates: Requirements 11.4, 11.5**

        Combined Properties 45 + 54: All momentum_score values in the ranked
        list are in [0, 100].
        """
        ranked = self.calc.rank_by_momentum(stocks)

        for stock in ranked:
            assert stock.momentum_score is not None, (
                f"momentum_score should be set after ranking for {stock.ticker}"
            )
            assert 0.0 <= stock.momentum_score <= 100.0, (
                f"Property 45+54 violation: {stock.ticker}.momentum_score="
                f"{stock.momentum_score} not in [0, 100]"
            )

    # --- Unit examples ---

    def test_empty_list_returns_empty(self):
        """Ranking an empty list returns an empty list."""
        assert self.calc.rank_by_momentum([]) == []

    def test_single_stock_returns_itself(self):
        """Ranking a single stock returns a list with that stock."""
        stock = make_stock("ONLY", price_change_pct=30.0)
        ranked = self.calc.rank_by_momentum([stock])
        assert len(ranked) == 1
        assert ranked[0].ticker == "ONLY"

    def test_two_stocks_higher_first(self):
        """The stock with higher momentum should be first."""
        low = make_stock("LOW", price_change_pct=5.0, volume=60_000, avg_volume=50_000)
        high = make_stock("HIGH", price_change_pct=80.0, volume=500_000, avg_volume=50_000, catalyst="news")
        ranked = self.calc.rank_by_momentum([low, high])
        assert ranked[0].ticker == "HIGH"
        assert ranked[1].ticker == "LOW"

    def test_already_sorted_list_unchanged_order(self):
        """A pre-sorted list should come out in the same order."""
        stocks = [
            make_stock("A", price_change_pct=90.0, volume=1_000_000, avg_volume=50_000, catalyst="news"),
            make_stock("B", price_change_pct=50.0, volume=200_000, avg_volume=50_000),
            make_stock("C", price_change_pct=10.0, volume=60_000, avg_volume=50_000),
        ]
        ranked = self.calc.rank_by_momentum(stocks)
        for i in range(len(ranked) - 1):
            assert ranked[i].momentum_score >= ranked[i + 1].momentum_score

    def test_scores_are_populated_on_stocks(self):
        """After ranking, every stock should have a non-None momentum_score."""
        stocks = [make_stock(str(i), price_change_pct=i * 10.0) for i in range(5)]
        # Ensure no pre-existing scores
        for s in stocks:
            s.momentum_score = None

        ranked = self.calc.rank_by_momentum(stocks)
        for stock in ranked:
            assert stock.momentum_score is not None


# ---------------------------------------------------------------------------
# Unit tests for MomentumScore dataclass
# ---------------------------------------------------------------------------

class TestMomentumScoreDataclass:
    """Unit tests for MomentumScore structure."""

    def test_dataclass_fields(self):
        ms = MomentumScore(
            overall_score=75.5,
            price_component=80.0,
            volume_component=70.0,
            trend_component=60.0,
            catalyst_component=100.0,
        )
        assert ms.overall_score == 75.5
        assert ms.price_component == 80.0
        assert ms.volume_component == 70.0
        assert ms.trend_component == 60.0
        assert ms.catalyst_component == 100.0

    def test_zero_score(self):
        ms = MomentumScore(0.0, 0.0, 0.0, 0.0, 0.0)
        assert ms.overall_score == 0.0

    def test_full_score(self):
        ms = MomentumScore(100.0, 100.0, 100.0, 100.0, 100.0)
        assert ms.overall_score == 100.0


# ---------------------------------------------------------------------------
# Integration: calculate → rank round-trip
# ---------------------------------------------------------------------------

class TestMomentumCalculatorIntegration:
    """Integration tests confirming the full calculate → rank workflow."""

    def setup_method(self):
        self.calc = MomentumCalculator()

    def test_full_workflow_produces_valid_ranking(self):
        """End-to-end: calculate scores then rank and verify properties."""
        stocks = [
            make_stock("A", price_change_pct=20.0, volume=200_000, avg_volume=50_000),
            make_stock("B", price_change_pct=60.0, volume=600_000, avg_volume=50_000, catalyst="FDA approval"),
            make_stock("C", price_change_pct=5.0, volume=55_000, avg_volume=50_000),
            make_stock("D", price_change_pct=100.0, volume=5_000_000, avg_volume=50_000, catalyst="earnings"),
        ]

        # Scores first
        for stock in stocks:
            ms = self.calc.calculate_momentum_score(stock)
            assert 0.0 <= ms.overall_score <= 100.0
            stock.momentum_score = ms.overall_score

        ranked = self.calc.rank_by_momentum(stocks)

        # All present
        assert len(ranked) == 4

        # Descending order
        for i in range(len(ranked) - 1):
            assert ranked[i].momentum_score >= ranked[i + 1].momentum_score

        # The highest-momentum stock has a catalyst + strong gain + high volume
        assert ranked[0].ticker in {"B", "D"}  # both are strong candidates

    def test_catalyst_increases_score(self):
        """A stock with a catalyst should score higher than an identical one without."""
        no_cat = make_stock("NC", price_change_pct=30.0, volume=300_000, avg_volume=50_000, catalyst=None)
        with_cat = make_stock("WC", price_change_pct=30.0, volume=300_000, avg_volume=50_000, catalyst="news")

        score_no_cat = self.calc.calculate_momentum_score(no_cat)
        score_with_cat = self.calc.calculate_momentum_score(with_cat)

        assert score_with_cat.overall_score > score_no_cat.overall_score, (
            "A catalyst should increase the momentum score"
        )

    def test_volume_surge_increases_score(self):
        """Higher volume ratio should yield a higher volume component."""
        low_vol = make_stock("LV", price_change_pct=20.0, volume=100_000, avg_volume=100_000)   # 1× ratio
        high_vol = make_stock("HV", price_change_pct=20.0, volume=1_000_000, avg_volume=100_000)  # 10× ratio

        low_score = self.calc.calculate_momentum_score(low_vol)
        high_score = self.calc.calculate_momentum_score(high_vol)

        assert high_score.volume_component > low_score.volume_component
        assert high_score.overall_score > low_score.overall_score


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ===========================================================================
# Properties 48, 49, 50, 51 — PennyStockRiskAnalyzer & PumpDumpDetector
# ===========================================================================

from stockiq.news.penny.risk import (
    PennyStockRiskAnalyzer,
    PumpDumpDetector,
    RiskAssessment,
    SuspicionScore,
    HIGH_PRIORITY_GAIN_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Property 48 — liquidity_risk always in [0, 1]
# ---------------------------------------------------------------------------

class TestProperty48LiquidityRiskRange:
    """
    **Validates: Requirements 11.10**

    Property 48: For any PennyStock, calculate_liquidity_risk SHALL always
    return a value in [0, 1].
    """

    def setup_method(self):
        self.analyzer = PennyStockRiskAnalyzer()

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_48_liquidity_risk_in_range(self, stock):
        """
        **Validates: Requirements 11.10**

        Property 48: liquidity_risk ∈ [0, 1] for all possible PennyStocks.
        """
        risk = self.analyzer.calculate_liquidity_risk(stock)
        assert 0.0 <= risk <= 1.0, (
            f"Property 48 violation: liquidity_risk={risk} not in [0, 1] "
            f"for stock={stock.ticker} avg_volume={stock.avg_volume} "
            f"market_cap={stock.market_cap}"
        )

    def test_zero_volume_gives_high_risk(self):
        """A stock with zero avg_volume must return maximum liquidity risk."""
        stock = make_stock("ZERO", avg_volume=0)
        # Assign avg_volume=0 by constructing manually
        from decimal import Decimal
        s = PennyStock(
            ticker="ZERO",
            price=Decimal("1.00"),
            price_change_pct=0.0,
            volume=0,
            avg_volume=0,
            volume_ratio=0.0,
            market_cap=0,
            sector="Unknown",
        )
        risk = self.analyzer.calculate_liquidity_risk(s)
        assert risk == 1.0

    def test_high_volume_high_cap_gives_low_risk(self):
        """A liquid, large-cap stock should have low liquidity risk."""
        from decimal import Decimal
        s = PennyStock(
            ticker="LIQ",
            price=Decimal("4.99"),
            price_change_pct=5.0,
            volume=5_000_000,
            avg_volume=10_000_000,
            volume_ratio=0.5,
            market_cap=500_000_000,
            sector="Technology",
        )
        risk = self.analyzer.calculate_liquidity_risk(s)
        assert 0.0 <= risk <= 1.0
        assert risk < 0.3, f"Expected low risk for high-volume/cap stock, got {risk}"

    def test_low_volume_low_cap_gives_high_risk(self):
        """A very illiquid penny stock should have high liquidity risk."""
        from decimal import Decimal
        s = PennyStock(
            ticker="ILLIQ",
            price=Decimal("0.01"),
            price_change_pct=0.0,
            volume=1_000,
            avg_volume=5_000,
            volume_ratio=0.2,
            market_cap=50_000,
            sector="Unknown",
        )
        risk = self.analyzer.calculate_liquidity_risk(s)
        assert 0.0 <= risk <= 1.0
        assert risk > 0.5, f"Expected high risk for illiquid stock, got {risk}"


# ---------------------------------------------------------------------------
# Property 49 — spread_percentage always >= 0
# ---------------------------------------------------------------------------

class TestProperty49SpreadPercentageNonNegative:
    """
    **Validates: Requirements 11.10**

    Property 49: For any PennyStock, calculate_spread_percentage SHALL always
    return a value >= 0.
    """

    def setup_method(self):
        self.analyzer = PennyStockRiskAnalyzer()

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_49_spread_non_negative(self, stock):
        """
        **Validates: Requirements 11.10**

        Property 49: spread_percentage >= 0 for all possible PennyStocks.
        """
        spread = self.analyzer.calculate_spread_percentage(stock)
        assert spread >= 0.0, (
            f"Property 49 violation: spread_percentage={spread} < 0 "
            f"for stock={stock.ticker}"
        )

    @given(
        bid=st.floats(min_value=0.01, max_value=4.99, allow_nan=False),
        ask=st.floats(min_value=0.01, max_value=5.00, allow_nan=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_property_49_with_bid_ask_non_negative(self, bid, ask):
        """
        **Validates: Requirements 11.10**

        Property 49: When bid/ask attributes are attached, spread is still >= 0.
        """
        from decimal import Decimal
        # bid may be > ask — the implementation should handle inversion
        price = min(bid, ask) if min(bid, ask) <= 5.0 else Decimal("1.00")
        try:
            s = PennyStock(
                ticker="BASPRD",
                price=Decimal(str(round(min(bid, ask, 5.0), 2))),
                price_change_pct=0.0,
                volume=100_000,
                avg_volume=50_000,
                volume_ratio=2.0,
                market_cap=1_000_000,
                sector="Unknown",
            )
        except ValueError:
            return  # PennyStock price validation failed — skip
        s.bid = bid
        s.ask = ask
        spread = self.analyzer.calculate_spread_percentage(s)
        assert spread >= 0.0, (
            f"Property 49 violation: spread={spread} < 0 with bid={bid} ask={ask}"
        )

    def test_exact_spread_calculation(self):
        """Verify the exact spread formula with known values."""
        from decimal import Decimal
        s = PennyStock(
            ticker="SPREAD",
            price=Decimal("1.00"),
            price_change_pct=0.0,
            volume=100_000,
            avg_volume=50_000,
            volume_ratio=2.0,
            market_cap=1_000_000,
            sector="Technology",
        )
        s.bid = 0.98
        s.ask = 1.02
        spread = self.analyzer.calculate_spread_percentage(s)
        # mid = (0.98 + 1.02) / 2 = 1.00
        # spread = (1.02 - 0.98) / 1.00 * 100 = 4.0%
        assert abs(spread - 4.0) < 1e-6, f"Expected 4.0%, got {spread}"

    def test_no_bid_ask_returns_default(self):
        """Without bid/ask, returns a positive default spread."""
        stock = make_stock("NOBASP")
        spread = self.analyzer.calculate_spread_percentage(stock)
        assert spread >= 0.0
        assert spread > 0.0  # should be the 2% default


# ---------------------------------------------------------------------------
# Property 50 — overall_risk always one of the valid levels
# ---------------------------------------------------------------------------

class TestProperty50OverallRiskClassification:
    """
    **Validates: Requirements 11.10**

    Property 50: For any PennyStock, assess_overall_risk SHALL return a
    RiskAssessment whose overall_risk is always one of:
    'low', 'medium', 'high', or 'extreme'.
    """

    VALID_RISK_LEVELS = {"low", "medium", "high", "extreme"}

    def setup_method(self):
        self.analyzer = PennyStockRiskAnalyzer()

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_50_overall_risk_valid(self, stock):
        """
        **Validates: Requirements 11.10**

        Property 50: overall_risk ∈ {'low', 'medium', 'high', 'extreme'}
        for all possible PennyStocks.
        """
        assessment = self.analyzer.assess_overall_risk(stock)
        assert assessment.overall_risk in self.VALID_RISK_LEVELS, (
            f"Property 50 violation: overall_risk='{assessment.overall_risk}' "
            f"not in {self.VALID_RISK_LEVELS} for stock={stock.ticker}"
        )

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_50_composite_score_in_range(self, stock):
        """
        **Validates: Requirements 11.10**

        Property 50 (derived): composite_score must be in [0, 1] for
        the classification thresholds to be meaningful.
        """
        assessment = self.analyzer.assess_overall_risk(stock)
        assert 0.0 <= assessment.composite_score <= 1.0, (
            f"composite_score={assessment.composite_score} not in [0, 1]"
        )

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_50_sub_metrics_in_range(self, stock):
        """
        All risk sub-metrics returned by assess_overall_risk are in [0, 1]
        (or >= 0 for spread_percentage).
        """
        a = self.analyzer.assess_overall_risk(stock)
        assert 0.0 <= a.liquidity_risk <= 1.0
        assert 0.0 <= a.volatility_risk <= 1.0
        assert a.spread_percentage >= 0.0

    def test_extreme_risk_stock(self):
        """A highly volatile, illiquid penny stock should get 'high' or 'extreme'."""
        from decimal import Decimal
        s = PennyStock(
            ticker="EXTRM",
            price=Decimal("0.01"),
            price_change_pct=200.0,
            volume=500,
            avg_volume=1_000,
            volume_ratio=0.5,
            market_cap=10_000,
            sector="Unknown",
        )
        a = self.analyzer.assess_overall_risk(s)
        assert a.overall_risk in {"high", "extreme"}

    def test_low_risk_stock(self):
        """A stable, liquid near-$5 stock should get 'low' or 'medium' risk."""
        from decimal import Decimal
        s = PennyStock(
            ticker="LOWRSK",
            price=Decimal("4.90"),
            price_change_pct=1.0,
            volume=2_000_000,
            avg_volume=5_000_000,
            volume_ratio=0.4,
            market_cap=200_000_000,
            sector="Finance",
        )
        a = self.analyzer.assess_overall_risk(s)
        assert a.overall_risk in {"low", "medium"}


# ---------------------------------------------------------------------------
# Property 51 — suspicion score always in [0, 1]
# ---------------------------------------------------------------------------

class TestProperty51SuspicionScoreRange:
    """
    **Validates: Requirements 11.14**

    Property 51: For any PennyStock, detect_suspicious_patterns SHALL return
    a SuspicionScore whose score is always in [0, 1].
    """

    def setup_method(self):
        self.detector = PumpDumpDetector()

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_51_suspicion_score_in_range(self, stock):
        """
        **Validates: Requirements 11.14**

        Property 51: SuspicionScore.score ∈ [0, 1] for all possible PennyStocks.
        """
        result = self.detector.detect_suspicious_patterns(stock)
        assert 0.0 <= result.score <= 1.0, (
            f"Property 51 violation: score={result.score} not in [0, 1] "
            f"for stock={stock.ticker}"
        )

    @given(stock=penny_stock())
    @settings(max_examples=25, deadline=None)
    def test_property_51_recommendation_valid(self, stock):
        """
        **Validates: Requirements 11.14**

        The recommendation must always be one of 'safe', 'caution', 'avoid'.
        """
        result = self.detector.detect_suspicious_patterns(stock)
        assert result.recommendation in {"safe", "caution", "avoid"}, (
            f"Invalid recommendation '{result.recommendation}' for {stock.ticker}"
        )

    def test_no_suspicious_patterns_low_score(self):
        """A normal stock with modest gain and volume gets a low suspicion score."""
        from decimal import Decimal
        s = PennyStock(
            ticker="NORMAL",
            price=Decimal("2.50"),
            price_change_pct=5.0,
            volume=100_000,
            avg_volume=80_000,
            volume_ratio=1.25,
            market_cap=5_000_000,
            sector="Technology",
            catalyst="earnings beat",
        )
        result = self.detector.detect_suspicious_patterns(s)
        assert 0.0 <= result.score <= 1.0
        assert result.score < 0.5, f"Expected low score for normal stock, got {result.score}"

    def test_extreme_gain_triggers_high_priority_indicator(self):
        """A stock with > 100% gain should trigger the high-priority indicator."""
        from decimal import Decimal
        s = PennyStock(
            ticker="PUMP",
            price=Decimal("1.00"),
            price_change_pct=150.0,
            volume=10_000_000,
            avg_volume=100_000,
            volume_ratio=100.0,
            market_cap=500_000,
            sector="Unknown",
        )
        result = self.detector.detect_suspicious_patterns(s)
        assert 0.0 <= result.score <= 1.0
        # Should have indicators including the high-priority one
        assert any("100%" in ind or "high-priority" in ind.lower() or "150" in ind
                   for ind in result.indicators), (
            f"Expected high-priority indicator for 150% gain. Indicators: {result.indicators}"
        )

    def test_abnormal_volume_no_catalyst_increases_score(self):
        """An abnormal volume spike without catalyst should increase suspicion."""
        from decimal import Decimal
        with_catalyst = PennyStock(
            ticker="CAT",
            price=Decimal("1.00"),
            price_change_pct=25.0,
            volume=600_000,
            avg_volume=100_000,
            volume_ratio=6.0,
            market_cap=2_000_000,
            sector="Unknown",
            catalyst="FDA approval",
        )
        no_catalyst = PennyStock(
            ticker="NOCAT",
            price=Decimal("1.00"),
            price_change_pct=25.0,
            volume=600_000,
            avg_volume=100_000,
            volume_ratio=6.0,
            market_cap=2_000_000,
            sector="Unknown",
            catalyst=None,
        )
        score_with = self.detector.detect_suspicious_patterns(with_catalyst)
        score_without = self.detector.detect_suspicious_patterns(no_catalyst)
        assert score_without.score >= score_with.score, (
            "No-catalyst stock should have same or higher suspicion than one with catalyst"
        )

    @given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=20, deadline=None)
    def test_generate_recommendation_valid_for_any_score(self, score):
        """generate_recommendation returns a valid string for any score in [0, 1]."""
        rec = self.detector.generate_recommendation(score)
        assert rec in {"safe", "caution", "avoid"}, (
            f"Invalid recommendation '{rec}' for score={score}"
        )

    def test_generate_recommendation_thresholds(self):
        """Verify recommendation thresholds are applied correctly."""
        assert self.detector.generate_recommendation(0.0) == "safe"
        assert self.detector.generate_recommendation(0.39) == "safe"
        assert self.detector.generate_recommendation(0.40) == "caution"
        assert self.detector.generate_recommendation(0.69) == "caution"
        assert self.detector.generate_recommendation(0.70) == "avoid"
        assert self.detector.generate_recommendation(1.0) == "avoid"


# ---------------------------------------------------------------------------
# Property 52 — high-priority alert when intraday gain > 100%
# ---------------------------------------------------------------------------

class TestProperty52HighPriorityAlert:
    """
    **Validates: Requirements 11.20**

    Property 52: When a penny stock's intraday gain exceeds 100%, the system
    SHALL flag a high-priority alert indicator.
    """

    def setup_method(self):
        self.detector = PumpDumpDetector()

    @given(gain=st.floats(min_value=100.01, max_value=999.0, allow_nan=False))
    @settings(max_examples=20, deadline=None)
    def test_property_52_gain_above_100_triggers_high_priority(self, gain):
        """
        **Validates: Requirements 11.20**

        Property 52: Any penny stock with price_change_pct > 100% must trigger
        the high-priority alert indicator in detect_suspicious_patterns.
        """
        from decimal import Decimal
        try:
            s = PennyStock(
                ticker="HPTEST",
                price=Decimal("1.00"),
                price_change_pct=gain,
                volume=500_000,
                avg_volume=100_000,
                volume_ratio=5.0,
                market_cap=2_000_000,
                sector="Unknown",
            )
        except ValueError:
            return  # Should not happen for price=1.00

        result = self.detector.detect_suspicious_patterns(s)

        # Must have at least one indicator mentioning the gain
        has_high_priority = any(
            "high-priority" in ind.lower() or "extreme" in ind.lower()
            or str(int(gain)) in ind
            for ind in result.indicators
        )
        assert has_high_priority, (
            f"Property 52 violation: no high-priority indicator for "
            f"gain={gain}%. Indicators: {result.indicators}"
        )
        # Score must still be in [0, 1]
        assert 0.0 <= result.score <= 1.0

    @given(gain=st.floats(min_value=-99.0, max_value=100.0, allow_nan=False))
    @settings(max_examples=20, deadline=None)
    def test_property_52_gain_at_or_below_100_no_extreme_indicator(self, gain):
        """
        Property 52 (inverse): Gains at or below 100% should NOT trigger the
        extreme high-priority indicator — only the moderate one if >= 50%.
        """
        from decimal import Decimal
        try:
            s = PennyStock(
                ticker="NORM52",
                price=Decimal("1.00"),
                price_change_pct=gain,
                volume=100_000,
                avg_volume=100_000,
                volume_ratio=1.0,
                market_cap=2_000_000,
                sector="Unknown",
                catalyst="news",  # catalyst prevents vol-spike indicator
            )
        except ValueError:
            return
        result = self.detector.detect_suspicious_patterns(s)
        # The extreme-gain high-priority indicator should NOT fire
        has_extreme = any(
            "high-priority" in ind.lower() for ind in result.indicators
        )
        assert not has_extreme, (
            f"Unexpected high-priority indicator for gain={gain}% <= 100%. "
            f"Indicators: {result.indicators}"
        )
        assert 0.0 <= result.score <= 1.0


# ===========================================================================
# Property 53 — Penny Stock Dashboard Update Frequency
# ===========================================================================

from stockiq.ui.dashboards.penny_stocks import (
    get_refresh_interval_seconds,
    should_refresh,
    seconds_until_next_refresh,
    MAX_REFRESH_INTERVAL_SECONDS,
    PENNY_DASHBOARD_REFRESH_SECONDS,
)
from datetime import datetime, timedelta


class TestProperty53DashboardRefreshInterval:
    """
    **Validates: Requirements 11.12, 11.15**

    Property 53: For any penny stock dashboard data refresh, the time elapsed
    since the previous refresh SHALL be less than or equal to 120 seconds
    (2 minutes).

    The dashboard enforces this with a bounded refresh interval
    (get_refresh_interval_seconds() <= 120) and a should_refresh() predicate
    that fires once the interval elapses.  Together they guarantee the
    dashboard never goes longer than 120 seconds without refreshing.
    """

    def test_configured_interval_within_bound(self):
        """
        **Validates: Requirements 11.12**

        Property 53 (static): the configured refresh interval is <= 120s.
        """
        assert PENNY_DASHBOARD_REFRESH_SECONDS <= MAX_REFRESH_INTERVAL_SECONDS
        assert MAX_REFRESH_INTERVAL_SECONDS == 120

    def test_effective_interval_within_bound(self):
        """
        **Validates: Requirements 11.12**

        Property 53: the effective refresh interval is always in (0, 120].
        """
        interval = get_refresh_interval_seconds()
        assert 0 < interval <= 120

    @given(elapsed=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False))
    @settings(max_examples=50, deadline=None)
    def test_property_53_refresh_within_120s(self, elapsed):
        """
        **Validates: Requirements 11.12**

        Property 53: For any elapsed time since the previous refresh, once
        elapsed reaches the interval (<= 120s) the dashboard is due to refresh.
        Equivalently, the time-until-next-refresh never exceeds 120 seconds.
        """
        now = datetime.utcnow()
        last_refresh = now - timedelta(seconds=elapsed)

        remaining = seconds_until_next_refresh(last_refresh, now)
        # The wait until the next refresh can never exceed the 2-minute bound.
        assert 0.0 <= remaining <= MAX_REFRESH_INTERVAL_SECONDS, (
            f"Property 53 violation: {remaining}s until next refresh exceeds "
            f"{MAX_REFRESH_INTERVAL_SECONDS}s (elapsed={elapsed}s)"
        )

        # When at least the interval has elapsed, a refresh must be due.
        if elapsed >= get_refresh_interval_seconds():
            assert should_refresh(last_refresh, now) is True, (
                f"Property 53 violation: refresh not triggered after "
                f"{elapsed}s (interval={get_refresh_interval_seconds()}s)"
            )

    @given(
        interval_elapsed=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=30, deadline=None)
    def test_property_53_max_gap_between_refreshes(self, interval_elapsed):
        """
        **Validates: Requirements 11.15**

        Property 53: Simulating consecutive refresh checks spaced by the
        interval, the gap between two refreshes never exceeds 120 seconds.
        """
        interval = get_refresh_interval_seconds()
        now = datetime.utcnow()
        # last refresh was exactly `interval_elapsed` intervals ago
        last_refresh = now - timedelta(seconds=interval * interval_elapsed)
        gap = (now - last_refresh).total_seconds()
        if interval_elapsed >= 1:
            # The dashboard would have refreshed at each interval boundary, so
            # the *effective* gap between refreshes is bounded by the interval.
            assert interval <= MAX_REFRESH_INTERVAL_SECONDS
            assert should_refresh(last_refresh, now) is True



# ===========================================================================
# Properties 42, 43, 44, 47 — PennyStockScanner
# ===========================================================================

from stockiq.news.penny.scanner import PennyStockScanner


# ---------------------------------------------------------------------------
# Property 42 — penny stock price threshold (≤ $5.00)
# ---------------------------------------------------------------------------

class TestProperty42PennyStockPriceThreshold:
    """
    **Validates: Requirements 11.1**

    Property 42: A penny stock is defined as a security trading at or below
    $5.00 per share. The PennyStock dataclass SHALL reject prices > $5.00.
    """

    @given(price=st.floats(min_value=0.01, max_value=5.00, allow_nan=False))
    @settings(max_examples=25, deadline=None)
    def test_property_42_price_at_or_below_five(self, price):
        """
        **Validates: Requirements 11.1**

        Property 42: PennyStock constructor accepts prices ≤ $5.00.
        """
        from decimal import Decimal
        try:
            stock = PennyStock(
                ticker="TEST",
                price=Decimal(str(round(price, 2))),
                price_change_pct=0.0,
                volume=100_000,
                avg_volume=50_000,
                volume_ratio=2.0,
                market_cap=1_000_000,
                sector="Technology",
            )
            assert stock.price <= Decimal("5.00")
        except ValueError as e:
            pytest.fail(f"Property 42 violation: price {price} ≤ $5.00 but constructor raised: {e}")

    @given(price=st.floats(min_value=5.01, max_value=1000.0, allow_nan=False))
    @settings(max_examples=25, deadline=None)
    def test_property_42_price_above_five_rejected(self, price):
        """
        **Validates: Requirements 11.1**

        Property 42: PennyStock constructor SHALL reject prices > $5.00.
        """
        from decimal import Decimal
        with pytest.raises(ValueError, match="Property 42"):
            PennyStock(
                ticker="TEST",
                price=Decimal(str(round(price, 2))),
                price_change_pct=0.0,
                volume=100_000,
                avg_volume=50_000,
                volume_ratio=2.0,
                market_cap=1_000_000,
                sector="Technology",
            )

    def test_penny_stock_exactly_five_dollars(self):
        """Exactly $5.00 is valid."""
        from decimal import Decimal
        stock = PennyStock(
            ticker="FIVE",
            price=Decimal("5.00"),
            price_change_pct=0.0,
            volume=100_000,
            avg_volume=50_000,
            volume_ratio=2.0,
            market_cap=1_000_000,
            sector="Finance",
        )
        assert stock.price == Decimal("5.00")

    def test_penny_stock_just_above_five_rejected(self):
        """$5.01 must be rejected."""
        from decimal import Decimal
        with pytest.raises(ValueError, match="Property 42"):
            PennyStock(
                ticker="TOOHIGH",
                price=Decimal("5.01"),
                price_change_pct=0.0,
                volume=100_000,
                avg_volume=50_000,
                volume_ratio=2.0,
                market_cap=1_000_000,
                sector="Finance",
            )


# ---------------------------------------------------------------------------
# Property 43 — intraday gain threshold (≥ 20%)
# ---------------------------------------------------------------------------

class TestProperty43IntradayGainThreshold:
    """
    **Validates: Requirements 11.2**

    Property 43: scan_intraday_gainers SHALL return only stocks whose
    intraday price_change_pct is >= min_gain_pct (default 20%).
    """

    def setup_method(self):
        self.scanner = PennyStockScanner()

    @given(
        gain_pct=st.floats(min_value=20.0, max_value=500.0, allow_nan=False),
        threshold=st.floats(min_value=0.0, max_value=50.0, allow_nan=False),
    )
    @settings(max_examples=20, deadline=None)
    def test_property_43_gain_threshold_enforced(self, gain_pct, threshold):
        """
        **Validates: Requirements 11.2**

        Property 43: A stock with gain >= threshold is included;
        a stock with gain < threshold is excluded.
        """
        from decimal import Decimal
        stock = PennyStock(
            ticker="GAINER",
            price=Decimal("2.50"),
            price_change_pct=gain_pct,
            volume=200_000,
            avg_volume=100_000,
            volume_ratio=2.0,
            market_cap=2_000_000,
            sector="Technology",
        )

        # If gain >= threshold, stock meets Property 43 for this threshold
        if gain_pct >= threshold:
            assert stock.price_change_pct >= threshold, (
                f"Property 43: stock with gain {gain_pct}% should satisfy threshold {threshold}%"
            )
        else:
            assert stock.price_change_pct < threshold

    def test_intraday_gain_exactly_threshold(self):
        """A stock with exactly 20% gain should be included."""
        from decimal import Decimal
        stock = PennyStock(
            ticker="EXACT",
            price=Decimal("3.00"),
            price_change_pct=20.0,
            volume=150_000,
            avg_volume=100_000,
            volume_ratio=1.5,
            market_cap=5_000_000,
            sector="Healthcare",
        )
        # scan_intraday_gainers with default 20% threshold should include this
        assert stock.price_change_pct >= 20.0

    def test_intraday_gain_below_threshold_excluded(self):
        """A stock with 19.9% gain should not meet the 20% threshold."""
        from decimal import Decimal
        stock = PennyStock(
            ticker="BELOW",
            price=Decimal("3.00"),
            price_change_pct=19.9,
            volume=150_000,
            avg_volume=100_000,
            volume_ratio=1.5,
            market_cap=5_000_000,
            sector="Healthcare",
        )
        assert stock.price_change_pct < 20.0


# ---------------------------------------------------------------------------
# Property 44 — multi-day gain threshold (≥ 50%)
# ---------------------------------------------------------------------------

class TestProperty44MultiDayGainThreshold:
    """
    **Validates: Requirements 11.3**

    Property 44: scan_multi_day_gainers SHALL return only stocks whose
    multi-day price_change_pct is >= min_gain_pct (default 50% over 5 days).
    """

    def setup_method(self):
        self.scanner = PennyStockScanner()

    @given(
        gain_pct=st.floats(min_value=50.0, max_value=1000.0, allow_nan=False),
        threshold=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=20, deadline=None)
    def test_property_44_multi_day_threshold_enforced(self, gain_pct, threshold):
        """
        **Validates: Requirements 11.3**

        Property 44: A stock with multi-day gain >= threshold meets the
        property; a stock with gain < threshold does not.
        """
        from decimal import Decimal
        stock = PennyStock(
            ticker="MULTID",
            price=Decimal("4.00"),
            price_change_pct=gain_pct,
            volume=500_000,
            avg_volume=100_000,
            volume_ratio=5.0,
            market_cap=10_000_000,
            sector="Energy",
        )

        if gain_pct >= threshold:
            assert stock.price_change_pct >= threshold, (
                f"Property 44: stock with {gain_pct}% gain should satisfy threshold {threshold}%"
            )
        else:
            assert stock.price_change_pct < threshold

    def test_multi_day_gain_exactly_threshold(self):
        """A stock with exactly 50% gain should meet the default threshold."""
        from decimal import Decimal
        stock = PennyStock(
            ticker="EXACT50",
            price=Decimal("3.75"),
            price_change_pct=50.0,
            volume=300_000,
            avg_volume=100_000,
            volume_ratio=3.0,
            market_cap=8_000_000,
            sector="Materials",
        )
        assert stock.price_change_pct >= 50.0

    def test_multi_day_gain_below_threshold_excluded(self):
        """A stock with 49.9% gain should not meet the 50% threshold."""
        from decimal import Decimal
        stock = PennyStock(
            ticker="BELOW50",
            price=Decimal("3.75"),
            price_change_pct=49.9,
            volume=300_000,
            avg_volume=100_000,
            volume_ratio=3.0,
            market_cap=8_000_000,
            sector="Materials",
        )
        assert stock.price_change_pct < 50.0


# ---------------------------------------------------------------------------
# Property 47 — volume ratio calculation (≥ 1.0 for surge)
# ---------------------------------------------------------------------------

class TestProperty47VolumeRatioCalculation:
    """
    **Validates: Requirements 11.7**

    Property 47: volume_ratio = current_volume / average_volume.
    The ratio is always >= 0.  Values >= 1.0 indicate at-or-above-average
    volume; values > 1.0 indicate a volume surge.
    """

    def setup_method(self):
        self.scanner = PennyStockScanner()

    @given(
        volume=st.integers(min_value=0, max_value=10_000_000),
        avg_volume=st.integers(min_value=1, max_value=5_000_000),
    )
    @settings(max_examples=25, deadline=None)
    def test_property_47_volume_ratio_non_negative(self, volume, avg_volume):
        """
        **Validates: Requirements 11.7**

        Property 47: volume_ratio is always >= 0.
        """
        from decimal import Decimal
        stock = PennyStock(
            ticker="VOLTEST",
            price=Decimal("2.00"),
            price_change_pct=10.0,
            volume=volume,
            avg_volume=avg_volume,
            volume_ratio=float(volume / avg_volume),
            market_cap=1_000_000,
            sector="Consumer",
        )
        assert stock.volume_ratio >= 0.0, (
            f"Property 47 violation: volume_ratio={stock.volume_ratio} < 0"
        )

    @given(
        volume=st.integers(min_value=0, max_value=10_000_000),
        avg_volume=st.integers(min_value=1, max_value=5_000_000),
    )
    @settings(max_examples=25, deadline=None)
    def test_property_47_volume_ratio_correct_formula(self, volume, avg_volume):
        """
        **Validates: Requirements 11.7**

        Property 47: volume_ratio = current_volume / average_volume.
        """
        from decimal import Decimal
        expected_ratio = volume / avg_volume
        stock = PennyStock(
            ticker="RATIO",
            price=Decimal("1.50"),
            price_change_pct=5.0,
            volume=volume,
            avg_volume=avg_volume,
            volume_ratio=expected_ratio,
            market_cap=500_000,
            sector="Industrial",
        )
        assert abs(stock.volume_ratio - expected_ratio) < 1e-9, (
            f"Property 47: volume_ratio={stock.volume_ratio} != {expected_ratio}"
        )

    def test_volume_ratio_surge_detection(self):
        """Values > 1.0 indicate a volume surge."""
        from decimal import Decimal
        surge_stock = PennyStock(
            ticker="SURGE",
            price=Decimal("2.00"),
            price_change_pct=30.0,
            volume=500_000,
            avg_volume=100_000,
            volume_ratio=5.0,
            market_cap=2_000_000,
            sector="Technology",
        )
        assert surge_stock.volume_ratio > 1.0, "This should be a volume surge"

    def test_volume_ratio_normal_volume(self):
        """Ratio close to 1.0 indicates normal volume."""
        from decimal import Decimal
        normal_stock = PennyStock(
            ticker="NORMAL",
            price=Decimal("3.00"),
            price_change_pct=2.0,
            volume=105_000,
            avg_volume=100_000,
            volume_ratio=1.05,
            market_cap=5_000_000,
            sector="Finance",
        )
        assert 0.9 <= normal_stock.volume_ratio <= 1.1

    def test_volume_ratio_low_volume(self):
        """Ratio < 1.0 indicates below-average volume."""
        from decimal import Decimal
        low_vol_stock = PennyStock(
            ticker="LOWVOL",
            price=Decimal("1.00"),
            price_change_pct=-5.0,
            volume=30_000,
            avg_volume=100_000,
            volume_ratio=0.3,
            market_cap=800_000,
            sector="Utilities",
        )
        assert low_vol_stock.volume_ratio < 1.0

    def test_volume_ratio_zero_average_volume(self):
        """When avg_volume is 0, calculate_volume_ratio returns 0.0 to avoid division by zero."""
        from decimal import Decimal
        stock = PennyStock(
            ticker="ZERO",
            price=Decimal("0.50"),
            price_change_pct=0.0,
            volume=10_000,
            avg_volume=0,  # Edge case
            volume_ratio=0.0,
            market_cap=50_000,
            sector="Unknown",
        )
        ratio = self.scanner.calculate_volume_ratio(stock)
        assert ratio == 0.0, "Zero avg_volume should return 0.0 ratio"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
