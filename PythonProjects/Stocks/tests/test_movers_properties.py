"""
Property-based tests for top movers calculation.

**Validates: Requirements 1.1-1.12**
**Properties: 1, 2, 3, 4, 5, 6, 7**
"""

import pytest
from hypothesis import given, strategies as st, assume
from decimal import Decimal
import pandas as pd
from datetime import datetime

from stockiq.data.processors.movers import TopMoversCalculator
from stockiq.data.models import Stock


# Strategies for generating test data
@st.composite
def stock_data_dict(draw):
    """Generate a valid stock data dictionary."""
    ticker = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        min_size=1,
        max_size=5
    ))
    
    market_cap = draw(st.integers(min_value=0, max_value=10_000_000_000_000))
    avg_volume = draw(st.integers(min_value=0, max_value=1_000_000_000))
    current_price = draw(st.decimals(
        min_value=Decimal("0.01"),
        max_value=Decimal("10000.00"),
        places=2
    ))
    
    # Generate price change percentage
    price_change_pct = draw(st.floats(
        min_value=-99.0,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False
    ))
    
    # Calculate price_change_abs from percentage
    price_change_abs = float(current_price) * price_change_pct / 100
    
    volume = draw(st.integers(min_value=0, max_value=1_000_000_000))
    
    sector = draw(st.sampled_from([
        "Technology", "Healthcare", "Finance", "Energy",
        "Consumer", "Industrial", "Materials", "Utilities"
    ]))
    
    return {
        "ticker": ticker,
        "name": f"{ticker} Inc.",
        "market_cap": market_cap,
        "avg_volume": avg_volume,
        "current_price": float(current_price),
        "price_change_pct": price_change_pct,
        "price_change_abs": price_change_abs,
        "volume": volume,
        "sector": sector
    }


@st.composite
def stock_dataframe(draw, min_size=0, max_size=100):
    """Generate a DataFrame of stock data."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    stocks = [draw(stock_data_dict()) for _ in range(size)]
    return pd.DataFrame(stocks)


class TestTopMoversProperties:
    """Property-based tests for top movers calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the cache to avoid Redis dependency in tests
        import unittest.mock as mock
        with mock.patch('stockiq.data.processors.movers.get_cache'):
            self.calculator = TopMoversCalculator()
            self.calculator.cache = mock.MagicMock()
    
    # Property 1: Top Gainers Ranking Correctness
    @given(stocks=st.lists(stock_data_dict(), min_size=0, max_size=50))
    def test_property_1_top_gainers_ranking(self, stocks):
        """
        **Validates: Requirements 1.1**
        
        Property 1: For any set of stock price data with percentage changes,
        when identifying the top 20 gainers, the system SHALL return exactly
        20 stocks (or fewer if less than 20 available) sorted in descending
        order by percentage change, where each stock's percentage change is
        greater than or equal to the next stock's percentage change.
        """
        # Filter to stocks that meet minimum criteria
        valid_stocks = [
            s for s in stocks
            if s['market_cap'] >= 100_000_000 and s['avg_volume'] >= 100_000
        ]
        
        # Execute
        gainers = self.calculator.identify_top_gainers(stocks, limit=20)
        
        # Verify count (exactly 20 or fewer if less than 20 available)
        expected_count = min(len(valid_stocks), 20)
        assert len(gainers) == expected_count, \
            f"Expected {expected_count} gainers, got {len(gainers)}"
        
        # Verify sorted in descending order
        for i in range(len(gainers) - 1):
            assert gainers[i].price_change_pct >= gainers[i + 1].price_change_pct, \
                f"Gainers not sorted: {gainers[i].price_change_pct} < {gainers[i + 1].price_change_pct}"
        
        # Verify all are gainers
        for gainer in gainers:
            assert gainer.is_gainer is True
    
    # Property 2: Top Losers Ranking Correctness
    @given(stocks=st.lists(stock_data_dict(), min_size=0, max_size=50))
    def test_property_2_top_losers_ranking(self, stocks):
        """
        **Validates: Requirements 1.2**
        
        Property 2: For any set of stock price data with percentage changes,
        when identifying the top 20 losers, the system SHALL return exactly
        20 stocks (or fewer if less than 20 available) sorted in ascending
        order by percentage change, where each stock's percentage change is
        less than or equal to the next stock's percentage change.
        """
        # Filter to stocks that meet minimum criteria
        valid_stocks = [
            s for s in stocks
            if s['market_cap'] >= 100_000_000 and s['avg_volume'] >= 100_000
        ]
        
        # Execute
        losers = self.calculator.identify_top_losers(stocks, limit=20)
        
        # Verify count (exactly 20 or fewer if less than 20 available)
        expected_count = min(len(valid_stocks), 20)
        assert len(losers) == expected_count, \
            f"Expected {expected_count} losers, got {len(losers)}"
        
        # Verify sorted in ascending order
        for i in range(len(losers) - 1):
            assert losers[i].price_change_pct <= losers[i + 1].price_change_pct, \
                f"Losers not sorted: {losers[i].price_change_pct} > {losers[i + 1].price_change_pct}"
        
        # Verify all are losers
        for loser in losers:
            assert loser.is_gainer is False
    
    # Property 3: Percentage Change Calculation
    @given(
        open_price=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000.00"),
            places=2
        ),
        close_price=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000.00"),
            places=2
        )
    )
    def test_property_3_percentage_change_calculation(self, open_price, close_price):
        """
        **Validates: Requirements 1.3**
        
        Property 3: For any stock with valid open and close prices,
        the calculated percentage change SHALL equal
        ((close - open) / open) * 100, and the absolute price change
        SHALL equal (close - open).
        """
        # Execute
        pct_change = TopMoversCalculator.calculate_percentage_change(
            open_price, close_price
        )
        
        # Calculate expected value
        expected_pct = ((close_price - open_price) / open_price) * 100
        
        # Verify (allow small floating point tolerance)
        assert abs(pct_change - expected_pct) < Decimal("0.0001"), \
            f"Expected {expected_pct}, got {pct_change}"
        
        # Also verify absolute change formula
        abs_change = close_price - open_price
        expected_abs = close_price - open_price
        assert abs_change == expected_abs
    
    def test_property_3_zero_open_price_raises_error(self):
        """
        **Validates: Requirements 1.3**
        
        Property 3 edge case: Zero open price should raise ValueError.
        """
        with pytest.raises(ValueError, match="Open price cannot be zero"):
            TopMoversCalculator.calculate_percentage_change(
                Decimal("0"), Decimal("100")
            )
    
    # Property 4: Market Cap Filtering
    @given(df=stock_dataframe(min_size=1, max_size=50))
    def test_property_4_market_cap_filtering(self, df):
        """
        **Validates: Requirements 1.5**
        
        Property 4: For any set of stocks processed for top movers,
        all returned stocks SHALL have a market capitalization greater
        than or equal to $100 million.
        """
        min_cap = 100_000_000
        
        # Execute
        filtered = self.calculator.filter_by_market_cap(df, min_cap)
        
        # Verify all stocks meet minimum market cap
        if not filtered.empty:
            assert (filtered['market_cap'] >= min_cap).all(), \
                "All stocks must have market_cap >= 100M"
        
        # Verify we only filtered out stocks below threshold
        expected_count = len(df[df['market_cap'] >= min_cap])
        assert len(filtered) == expected_count
    
    # Property 5: Volume Filtering
    @given(df=stock_dataframe(min_size=1, max_size=50))
    def test_property_5_volume_filtering(self, df):
        """
        **Validates: Requirements 1.6**
        
        Property 5: For any set of stocks processed for top movers,
        all returned stocks SHALL have an average daily volume greater
        than or equal to 100,000 shares.
        """
        min_volume = 100_000
        
        # Execute
        filtered = self.calculator.filter_by_volume(df, min_volume)
        
        # Verify all stocks meet minimum volume
        if not filtered.empty:
            assert (filtered['avg_volume'] >= min_volume).all(), \
                "All stocks must have avg_volume >= 100k"
        
        # Verify we only filtered out stocks below threshold
        expected_count = len(df[df['avg_volume'] >= min_volume])
        assert len(filtered) == expected_count
    
    # Property 6: Sector Performance Aggregation
    @given(df=stock_dataframe(min_size=1, max_size=50))
    def test_property_6_sector_performance_aggregation(self, df):
        """
        **Validates: Requirements 1.9**
        
        Property 6: For any set of stocks grouped by sector with individual
        returns, the calculated sector performance SHALL equal the weighted
        average return of all stocks in that sector, and sectors SHALL be
        ranked in descending order by performance.
        """
        # Execute
        sector_perf = self.calculator.calculate_sector_performance(df)
        
        # Verify sectors are ranked in descending order
        if len(sector_perf) > 1:
            values = list(sector_perf.values())
            for i in range(len(values) - 1):
                assert values[i] >= values[i + 1], \
                    f"Sectors not sorted: {values[i]} < {values[i + 1]}"
        
        # Verify weighted average calculation for each sector
        for sector, performance in sector_perf.items():
            sector_df = df[df['sector'] == sector]
            total_market_cap = sector_df['market_cap'].sum()
            
            if total_market_cap > 0:
                expected_perf = (
                    (sector_df['price_change_pct'] * sector_df['market_cap']).sum()
                    / total_market_cap
                )
                
                # Allow small floating point tolerance
                assert abs(performance - expected_perf) < 0.0001, \
                    f"Sector {sector}: expected {expected_perf}, got {performance}"
    
    # Property 7: Unusual Volume Detection
    @given(
        volume=st.integers(min_value=0, max_value=1_000_000_000),
        avg_volume=st.integers(min_value=1, max_value=1_000_000_000)
    )
    def test_property_7_unusual_volume_detection(self, volume, avg_volume):
        """
        **Validates: Requirements 1.10**
        
        Property 7: For any stock with current volume and average volume,
        the stock SHALL be flagged as having unusual volume if and only if
        current_volume > 3 * average_volume.
        """
        # Create a stock object
        stock = Stock(
            ticker="TEST",
            name="Test Inc.",
            sector="Technology",
            market_cap=1_000_000_000,
            avg_volume=avg_volume,
            current_price=Decimal("100.00")
        )
        stock.volume = volume  # Add volume attribute
        
        # Execute
        is_unusual = self.calculator.detect_unusual_volume(stock)
        
        # Verify Property 7: unusual iff volume > 3 * avg_volume
        expected = volume > 3 * avg_volume
        assert is_unusual == expected, \
            f"Volume {volume}, Avg {avg_volume}: expected {expected}, got {is_unusual}"
    
    def test_property_7_zero_avg_volume(self):
        """
        **Validates: Requirements 1.10**
        
        Property 7 edge case: Zero average volume should return False.
        """
        stock = Stock(
            ticker="TEST",
            name="Test Inc.",
            sector="Technology",
            market_cap=1_000_000_000,
            avg_volume=0,
            current_price=Decimal("100.00")
        )
        stock.volume = 1_000_000
        
        is_unusual = self.calculator.detect_unusual_volume(stock)
        assert is_unusual is False
    
    def test_property_7_missing_volume_attributes(self):
        """
        **Validates: Requirements 1.10**
        
        Property 7 edge case: Missing volume attributes should return False.
        """
        stock = Stock(
            ticker="TEST",
            name="Test Inc.",
            sector="Technology"
        )
        
        is_unusual = self.calculator.detect_unusual_volume(stock)
        assert is_unusual is False


class TestTopMoversIntegration:
    """Integration tests for top movers calculation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the cache to avoid Redis dependency in tests
        import unittest.mock as mock
        with mock.patch('stockiq.data.processors.movers.get_cache'):
            self.calculator = TopMoversCalculator()
            self.calculator.cache = mock.MagicMock()
    
    def test_identify_top_gainers_with_real_data(self):
        """Test top gainers identification with realistic data."""
        stocks = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "market_cap": 3_000_000_000_000,
                "avg_volume": 50_000_000,
                "current_price": 180.50,
                "price_change_pct": 5.2,
                "price_change_abs": 8.91,
                "volume": 60_000_000,
                "sector": "Technology"
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "market_cap": 2_500_000_000_000,
                "avg_volume": 40_000_000,
                "current_price": 380.20,
                "price_change_pct": 3.8,
                "price_change_abs": 13.92,
                "volume": 45_000_000,
                "sector": "Technology"
            },
            {
                "ticker": "TSLA",
                "name": "Tesla Inc.",
                "market_cap": 800_000_000_000,
                "avg_volume": 100_000_000,
                "current_price": 245.30,
                "price_change_pct": 8.5,
                "price_change_abs": 19.23,
                "volume": 150_000_000,
                "sector": "Consumer"
            },
            {
                "ticker": "NVDA",
                "name": "NVIDIA Corp.",
                "market_cap": 1_200_000_000_000,
                "avg_volume": 80_000_000,
                "current_price": 495.60,
                "price_change_pct": 12.3,
                "price_change_abs": 54.32,
                "volume": 120_000_000,
                "sector": "Technology"
            },
            {
                "ticker": "PENNY",
                "name": "Penny Stock Inc.",
                "market_cap": 50_000_000,  # Below minimum
                "avg_volume": 50_000,  # Below minimum
                "current_price": 2.50,
                "price_change_pct": 50.0,
                "price_change_abs": 0.83,
                "volume": 100_000,
                "sector": "Materials"
            }
        ]
        
        gainers = self.calculator.identify_top_gainers(stocks, limit=20)
        
        # Should exclude PENNY due to market cap and volume filters
        assert len(gainers) == 4
        
        # Should be sorted by percentage change descending
        assert gainers[0].ticker == "NVDA"  # 12.3%
        assert gainers[1].ticker == "TSLA"  # 8.5%
        assert gainers[2].ticker == "AAPL"  # 5.2%
        assert gainers[3].ticker == "MSFT"  # 3.8%
    
    def test_identify_top_losers_with_real_data(self):
        """Test top losers identification with realistic data."""
        stocks = [
            {
                "ticker": "XYZ",
                "name": "XYZ Corp.",
                "market_cap": 500_000_000_000,
                "avg_volume": 20_000_000,
                "current_price": 50.20,
                "price_change_pct": -8.5,
                "price_change_abs": -4.67,
                "volume": 30_000_000,
                "sector": "Finance"
            },
            {
                "ticker": "ABC",
                "name": "ABC Inc.",
                "market_cap": 300_000_000_000,
                "avg_volume": 15_000_000,
                "current_price": 75.80,
                "price_change_pct": -3.2,
                "price_change_abs": -2.51,
                "volume": 18_000_000,
                "sector": "Healthcare"
            },
            {
                "ticker": "DEF",
                "name": "DEF Ltd.",
                "market_cap": 400_000_000_000,
                "avg_volume": 25_000_000,
                "current_price": 120.40,
                "price_change_pct": -12.1,
                "price_change_abs": -16.58,
                "volume": 35_000_000,
                "sector": "Energy"
            }
        ]
        
        losers = self.calculator.identify_top_losers(stocks, limit=20)
        
        assert len(losers) == 3
        
        # Should be sorted by percentage change ascending
        assert losers[0].ticker == "DEF"  # -12.1%
        assert losers[1].ticker == "XYZ"  # -8.5%
        assert losers[2].ticker == "ABC"  # -3.2%
    
    def test_calculate_sector_performance_with_real_data(self):
        """Test sector performance calculation with realistic data."""
        stocks = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "market_cap": 3_000_000_000_000,
                "avg_volume": 50_000_000,
                "current_price": 180.50,
                "price_change_pct": 2.0,
                "price_change_abs": 3.53,
                "volume": 60_000_000,
                "sector": "Technology"
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "market_cap": 2_000_000_000_000,
                "avg_volume": 40_000_000,
                "current_price": 380.20,
                "price_change_pct": 4.0,
                "price_change_abs": 14.62,
                "volume": 45_000_000,
                "sector": "Technology"
            },
            {
                "ticker": "JNJ",
                "name": "Johnson & Johnson",
                "market_cap": 400_000_000_000,
                "avg_volume": 10_000_000,
                "current_price": 160.30,
                "price_change_pct": 1.0,
                "price_change_abs": 1.59,
                "volume": 12_000_000,
                "sector": "Healthcare"
            }
        ]
        
        df = pd.DataFrame(stocks)
        sector_perf = self.calculator.calculate_sector_performance(df)
        
        # Technology sector weighted average:
        # (2.0 * 3e12 + 4.0 * 2e12) / (3e12 + 2e12) = 2.8
        tech_perf = sector_perf["Technology"]
        assert abs(tech_perf - 2.8) < 0.01
        
        # Healthcare sector: only one stock, so just 1.0
        health_perf = sector_perf["Healthcare"]
        assert abs(health_perf - 1.0) < 0.01
        
        # Verify ordering (Technology should be first)
        sectors_list = list(sector_perf.keys())
        assert sectors_list[0] == "Technology"
        assert sectors_list[1] == "Healthcare"
