"""
Tests for market data collection.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from stockiq.data.models import OHLCV, Price, TopMover
from stockiq.data.collectors.market import MarketDataCollector
from stockiq.data.processors.movers import TopMoversCalculator
from stockiq.data.processors.validator import DataValidator


class TestOHLCVModel:
    """Test OHLCV data model."""
    
    def test_valid_ohlcv(self):
        """Test valid OHLCV data."""
        ohlcv = OHLCV(
            ticker="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("150.00"),
            high=Decimal("155.00"),
            low=Decimal("149.00"),
            close=Decimal("154.00"),
            volume=1000000
        )
        assert ohlcv.ticker == "AAPL"
        assert ohlcv.high >= ohlcv.open
        assert ohlcv.low <= ohlcv.close
    
    def test_property_26_high_gte_open(self):
        """Test Property 26: High >= max(Open, Close)."""
        with pytest.raises(ValueError, match="High.*must be >= max"):
            OHLCV(
                ticker="AAPL",
                timestamp=datetime.utcnow(),
                open=Decimal("150.00"),
                high=Decimal("145.00"),  # Invalid: high < open
                low=Decimal("140.00"),
                close=Decimal("148.00"),
                volume=1000000
            )
    
    def test_property_26_low_lte_close(self):
        """Test Property 26: Low <= min(Open, Close)."""
        with pytest.raises(ValueError, match="Low.*must be <= min"):
            OHLCV(
                ticker="AAPL",
                timestamp=datetime.utcnow(),
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("152.00"),  # Invalid: low > min(open, close)
                close=Decimal("151.00"),
                volume=1000000
            )
    
    def test_property_28_volume_non_negative(self):
        """Test Property 28: Volume >= 0."""
        with pytest.raises(ValueError, match="Volume cannot be negative"):
            OHLCV(
                ticker="AAPL",
                timestamp=datetime.utcnow(),
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("149.00"),
                close=Decimal("154.00"),
                volume=-1000  # Invalid: negative volume
            )
    
    def test_property_3_percentage_change(self):
        """Test Property 3: Percentage change calculation."""
        ohlcv = OHLCV(
            ticker="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("100.00"),
            high=Decimal("110.00"),
            low=Decimal("99.00"),
            close=Decimal("110.00"),
            volume=1000000
        )
        
        pct_change = ohlcv.percentage_change()
        assert pct_change == Decimal("10.00")
    
    def test_property_3_zero_open_price(self):
        """Test Property 3: Zero open price raises error."""
        ohlcv = OHLCV(
            ticker="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("0.00"),
            high=Decimal("10.00"),
            low=Decimal("0.00"),
            close=Decimal("10.00"),
            volume=1000000
        )
        
        with pytest.raises(ValueError, match="Open price cannot be zero"):
            ohlcv.percentage_change()


class TestTopMoversCalculator:
    """Test top movers calculation."""
    
    def test_property_1_top_gainers_sorting(self):
        """Test Property 1: Top gainers sorted descending."""
        stocks_data = [
            {
                'ticker': 'AAPL',
                'name': 'Apple Inc.',
                'price_change_pct': 5.0,
                'price_change_abs': 7.5,
                'current_price': 157.5,
                'volume': 50000000,
                'avg_volume': 40000000,
                'market_cap': 2500000000000,
                'sector': 'Technology'
            },
            {
                'ticker': 'MSFT',
                'name': 'Microsoft',
                'price_change_pct': 3.0,
                'price_change_abs': 9.0,
                'current_price': 309.0,
                'volume': 30000000,
                'avg_volume': 25000000,
                'market_cap': 2300000000000,
                'sector': 'Technology'
            },
            {
                'ticker': 'GOOGL',
                'name': 'Alphabet',
                'price_change_pct': 7.0,
                'price_change_abs': 8.4,
                'current_price': 128.4,
                'volume': 25000000,
                'avg_volume': 20000000,
                'market_cap': 1600000000000,
                'sector': 'Technology'
            }
        ]
        
        calculator = TopMoversCalculator()
        gainers = calculator.identify_top_gainers(stocks_data, limit=20)
        
        # Verify Property 1: sorted in descending order
        assert len(gainers) == 3
        assert gainers[0].ticker == 'GOOGL'  # 7.0%
        assert gainers[1].ticker == 'AAPL'   # 5.0%
        assert gainers[2].ticker == 'MSFT'   # 3.0%
        
        # Verify descending order
        for i in range(len(gainers) - 1):
            assert gainers[i].price_change_pct >= gainers[i + 1].price_change_pct
    
    def test_property_2_top_losers_sorting(self):
        """Test Property 2: Top losers sorted ascending."""
        stocks_data = [
            {
                'ticker': 'AAPL',
                'name': 'Apple Inc.',
                'price_change_pct': -5.0,
                'price_change_abs': -7.5,
                'current_price': 142.5,
                'volume': 50000000,
                'avg_volume': 40000000,
                'market_cap': 2500000000000,
                'sector': 'Technology'
            },
            {
                'ticker': 'MSFT',
                'name': 'Microsoft',
                'price_change_pct': -3.0,
                'price_change_abs': -9.0,
                'current_price': 291.0,
                'volume': 30000000,
                'avg_volume': 25000000,
                'market_cap': 2300000000000,
                'sector': 'Technology'
            },
            {
                'ticker': 'GOOGL',
                'name': 'Alphabet',
                'price_change_pct': -7.0,
                'price_change_abs': -8.4,
                'current_price': 111.6,
                'volume': 25000000,
                'avg_volume': 20000000,
                'market_cap': 1600000000000,
                'sector': 'Technology'
            }
        ]
        
        calculator = TopMoversCalculator()
        losers = calculator.identify_top_losers(stocks_data, limit=20)
        
        # Verify Property 2: sorted in ascending order
        assert len(losers) == 3
        assert losers[0].ticker == 'GOOGL'  # -7.0%
        assert losers[1].ticker == 'AAPL'   # -5.0%
        assert losers[2].ticker == 'MSFT'   # -3.0%
        
        # Verify ascending order
        for i in range(len(losers) - 1):
            assert losers[i].price_change_pct <= losers[i + 1].price_change_pct
    
    def test_property_4_market_cap_filter(self):
        """Test Property 4: Market cap >= $100M."""
        stocks_data = [
            {
                'ticker': 'BIG',
                'name': 'Big Corp',
                'price_change_pct': 10.0,
                'price_change_abs': 5.0,
                'current_price': 55.0,
                'volume': 1000000,
                'avg_volume': 500000,
                'market_cap': 200000000,  # $200M - should be included
                'sector': 'Technology'
            },
            {
                'ticker': 'SMALL',
                'name': 'Small Corp',
                'price_change_pct': 15.0,
                'price_change_abs': 3.0,
                'current_price': 23.0,
                'volume': 500000,
                'avg_volume': 200000,
                'market_cap': 50000000,  # $50M - should be filtered out
                'sector': 'Technology'
            }
        ]
        
        calculator = TopMoversCalculator()
        gainers = calculator.identify_top_gainers(stocks_data, limit=20)
        
        # Only BIG should be included (market cap >= $100M)
        assert len(gainers) == 1
        assert gainers[0].ticker == 'BIG'
    
    def test_property_5_volume_filter(self):
        """Test Property 5: Average volume >= 100k shares."""
        stocks_data = [
            {
                'ticker': 'LIQUID',
                'name': 'Liquid Corp',
                'price_change_pct': 10.0,
                'price_change_abs': 5.0,
                'current_price': 55.0,
                'volume': 1000000,
                'avg_volume': 500000,  # >= 100k - should be included
                'market_cap': 200000000,
                'sector': 'Technology'
            },
            {
                'ticker': 'ILLIQUID',
                'name': 'Illiquid Corp',
                'price_change_pct': 15.0,
                'price_change_abs': 3.0,
                'current_price': 23.0,
                'volume': 50000,
                'avg_volume': 50000,  # < 100k - should be filtered out
                'market_cap': 200000000,
                'sector': 'Technology'
            }
        ]
        
        calculator = TopMoversCalculator()
        gainers = calculator.identify_top_gainers(stocks_data, limit=20)
        
        # Only LIQUID should be included (avg_volume >= 100k)
        assert len(gainers) == 1
        assert gainers[0].ticker == 'LIQUID'
    
    def test_property_7_unusual_volume(self):
        """Test Property 7: Unusual volume detection."""
        mover = TopMover(
            ticker='AAPL',
            name='Apple Inc.',
            price_change_pct=5.0,
            price_change_abs=Decimal("7.5"),
            current_price=Decimal("157.5"),
            volume=120000000,  # 3x average
            avg_volume=40000000,
            market_cap=2500000000000,
            sector='Technology',
            is_gainer=True
        )
        
        # Volume ratio should be 3.0
        assert mover.volume_ratio() == 3.0
        
        # Should be flagged as unusual volume (> 3x)
        assert mover.has_unusual_volume() is True
        
        # Test normal volume
        mover2 = TopMover(
            ticker='MSFT',
            name='Microsoft',
            price_change_pct=3.0,
            price_change_abs=Decimal("9.0"),
            current_price=Decimal("309.0"),
            volume=50000000,  # 2x average
            avg_volume=25000000,
            market_cap=2300000000000,
            sector='Technology',
            is_gainer=True
        )
        
        assert mover2.volume_ratio() == 2.0
        assert mover2.has_unusual_volume() is False


class TestDataValidator:
    """Test data validation."""
    
    def test_property_27_timestamp_ordering(self):
        """Test Property 27: Timestamps in ascending order."""
        now = datetime.utcnow()
        
        # Valid: ascending order
        data_valid = [
            OHLCV(
                ticker="AAPL",
                timestamp=now,
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("149.00"),
                close=Decimal("154.00"),
                volume=1000000
            ),
            OHLCV(
                ticker="AAPL",
                timestamp=now + timedelta(days=1),
                open=Decimal("154.00"),
                high=Decimal("156.00"),
                low=Decimal("153.00"),
                close=Decimal("155.00"),
                volume=1100000
            )
        ]
        
        validator = DataValidator()
        result = validator.validate_price_data(data_valid)
        assert result.is_valid is True
        
        # Invalid: not in ascending order
        data_invalid = [
            OHLCV(
                ticker="AAPL",
                timestamp=now + timedelta(days=1),
                open=Decimal("154.00"),
                high=Decimal("156.00"),
                low=Decimal("153.00"),
                close=Decimal("155.00"),
                volume=1100000
            ),
            OHLCV(
                ticker="AAPL",
                timestamp=now,  # Earlier timestamp
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("149.00"),
                close=Decimal("154.00"),
                volume=1000000
            )
        ]
        
        result = validator.validate_price_data(data_invalid)
        assert result.is_valid is False
        assert any("ascending order" in error for error in result.errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
