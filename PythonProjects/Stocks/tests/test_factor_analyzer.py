"""
Test suite for Factor Analyzer

Tests Fama-French 5-factor model, factor exposures, and cointegration testing.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from stockiq.analytics.factors import (
    FactorAnalyzer,
    FactorExposures,
    FactorReturns,
    CointegrationResult,
)


class TestFactorAnalyzer:
    """Test suite for FactorAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create FactorAnalyzer instance."""
        return FactorAnalyzer(risk_free_rate=0.02)
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample security returns."""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        returns = pd.Series(
            np.random.normal(0.001, 0.02, len(dates)),
            index=dates,
            name='AAPL'
        )
        return returns
    
    @pytest.fixture
    def sample_factor_returns(self):
        """Generate sample Fama-French factor returns."""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        
        factor_data = {
            'Mkt-RF': np.random.normal(0.0003, 0.01, len(dates)),
            'SMB': np.random.normal(0.0001, 0.003, len(dates)),
            'HML': np.random.normal(0.0001, 0.004, len(dates)),
            'RMW': np.random.normal(0.0001, 0.003, len(dates)),
            'CMA': np.random.normal(0.0001, 0.002, len(dates)),
            'MOM': np.random.normal(0.0002, 0.005, len(dates)),
            'QMJ': np.random.normal(0.0001, 0.003, len(dates)),
        }
        
        return pd.DataFrame(factor_data, index=dates)
    
    @pytest.fixture
    def cointegrated_prices(self):
        """Generate cointegrated price series for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        
        # Generate cointegrated series
        # price1 = base + noise1
        # price2 = 2 * base + noise2
        # They share common stochastic trend (base)
        
        base = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
        noise1 = np.random.normal(0, 2, len(dates))
        noise2 = np.random.normal(0, 2, len(dates))
        
        price1 = base + noise1
        price2 = 2 * base + noise2
        
        series1 = pd.Series(price1, index=dates, name='TICKER1')
        series2 = pd.Series(price2, index=dates, name='TICKER2')
        
        return series1, series2
    
    @pytest.fixture
    def non_cointegrated_prices(self):
        """Generate non-cointegrated price series for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        
        # Generate independent random walks
        price1 = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
        price2 = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
        
        series1 = pd.Series(price1, index=dates, name='TICKER1')
        series2 = pd.Series(price2, index=dates, name='TICKER2')
        
        return series1, series2
    
    # Test Factor Exposures Calculation
    
    def test_calculate_factor_exposures_basic(self, analyzer, sample_returns, sample_factor_returns):
        """Test basic factor exposure calculation."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns,
            ticker='AAPL'
        )
        
        assert isinstance(exposures, FactorExposures)
        assert exposures.ticker == 'AAPL'
        assert isinstance(exposures.market, float)
        assert isinstance(exposures.smb, float)
        assert isinstance(exposures.hml, float)
        assert isinstance(exposures.rmw, float)
        assert isinstance(exposures.cma, float)
        assert isinstance(exposures.alpha, float)
        assert 0.0 <= exposures.r_squared <= 1.0
    
    def test_calculate_factor_exposures_with_momentum(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor exposure calculation includes momentum."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns,
            ticker='AAPL'
        )
        
        assert exposures.momentum is not None
        assert isinstance(exposures.momentum, float)
    
    def test_calculate_factor_exposures_with_quality(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor exposure calculation includes quality."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns,
            ticker='AAPL'
        )
        
        assert exposures.quality is not None
        assert isinstance(exposures.quality, float)
    
    def test_calculate_factor_exposures_insufficient_data(self, analyzer):
        """Test error handling with insufficient data."""
        # Only 30 days of data
        dates = pd.date_range(start='2023-01-01', end='2023-01-30', freq='B')
        returns = pd.Series(np.random.normal(0.001, 0.02, len(dates)), index=dates)
        
        factor_data = {
            'Mkt-RF': np.random.normal(0.0003, 0.01, len(dates)),
            'SMB': np.random.normal(0.0001, 0.003, len(dates)),
            'HML': np.random.normal(0.0001, 0.004, len(dates)),
            'RMW': np.random.normal(0.0001, 0.003, len(dates)),
            'CMA': np.random.normal(0.0001, 0.002, len(dates)),
        }
        factor_returns = pd.DataFrame(factor_data, index=dates)
        
        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.calculate_factor_exposures(returns, factor_returns)
    
    def test_factor_exposures_to_dict(self, analyzer, sample_returns, sample_factor_returns):
        """Test FactorExposures to_dict method."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns
        )
        
        exposure_dict = exposures.to_dict()
        
        assert isinstance(exposure_dict, dict)
        assert 'ticker' in exposure_dict
        assert 'market' in exposure_dict
        assert 'smb' in exposure_dict
        assert 'hml' in exposure_dict
        assert 'rmw' in exposure_dict
        assert 'cma' in exposure_dict
        assert 'momentum' in exposure_dict
        assert 'quality' in exposure_dict
        assert 'alpha' in exposure_dict
        assert 'r_squared' in exposure_dict
    
    # Test Factor Returns Calculation
    
    def test_calculate_factor_returns_1m(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor return attribution for 1 month period."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns,
            ticker='AAPL'
        )
        
        factor_returns = analyzer.calculate_factor_returns(
            exposures,
            sample_factor_returns,
            period='1M'
        )
        
        assert isinstance(factor_returns, FactorReturns)
        assert isinstance(factor_returns.total_return, float)
        assert isinstance(factor_returns.market_contribution, float)
        assert isinstance(factor_returns.smb_contribution, float)
        assert isinstance(factor_returns.hml_contribution, float)
        assert isinstance(factor_returns.rmw_contribution, float)
        assert isinstance(factor_returns.cma_contribution, float)
    
    def test_calculate_factor_returns_3m(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor return attribution for 3 month period."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns
        )
        
        factor_returns = analyzer.calculate_factor_returns(
            exposures,
            sample_factor_returns,
            period='3M'
        )
        
        assert isinstance(factor_returns, FactorReturns)
        # 3M should have larger absolute contributions than 1M
        assert factor_returns.total_return != 0.0
    
    def test_calculate_factor_returns_1y(self, analyzer, sample_returns, sample_factor_returns):
        """Test factor return attribution for 1 year period."""
        exposures = analyzer.calculate_factor_exposures(
            sample_returns,
            sample_factor_returns
        )
        
        factor_returns = analyzer.calculate_factor_returns(
            exposures,
            sample_factor_returns,
            period='1Y'
        )
        
        assert isinstance(factor_returns, FactorReturns)
        assert factor_returns.total_return != 0.0
    
    # Test Cointegration - Engle-Granger
    
    def test_cointegration_engle_granger_cointegrated(self, analyzer, cointegrated_prices):
        """Test Engle-Granger cointegration test on cointegrated series."""
        price1, price2 = cointegrated_prices
        
        result = analyzer.test_cointegration_engle_granger(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        assert isinstance(result, CointegrationResult)
        assert result.ticker1 == 'TICKER1'
        assert result.ticker2 == 'TICKER2'
        assert result.test_method == 'engle_granger'
        assert isinstance(result.is_cointegrated, bool)
        assert isinstance(result.hedge_ratio, float)
        assert isinstance(result.test_statistic, float)
        assert isinstance(result.p_value, float)
        assert isinstance(result.adf_statistic, float)
        assert isinstance(result.adf_p_value, float)
    
    def test_cointegration_engle_granger_non_cointegrated(self, analyzer, non_cointegrated_prices):
        """Test Engle-Granger cointegration test on non-cointegrated series."""
        price1, price2 = non_cointegrated_prices
        
        result = analyzer.test_cointegration_engle_granger(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        assert isinstance(result, CointegrationResult)
        # Independent random walks should not be cointegrated
        assert result.is_cointegrated == False
    
    def test_cointegration_engle_granger_hedge_ratio(self, analyzer, cointegrated_prices):
        """Test hedge ratio calculation in Engle-Granger test."""
        price1, price2 = cointegrated_prices
        
        result = analyzer.test_cointegration_engle_granger(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        # Hedge ratio should be approximately 0.5 (since price2 = 2 * base, but we're regressing price1 on price2)
        # So price1 = hedge_ratio * price2 => base = hedge_ratio * 2*base => hedge_ratio ≈ 0.5
        assert 0.3 < result.hedge_ratio < 0.7
    
    def test_cointegration_engle_granger_spread_stats(self, analyzer, cointegrated_prices):
        """Test spread statistics in Engle-Granger test."""
        price1, price2 = cointegrated_prices
        
        result = analyzer.test_cointegration_engle_granger(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        assert isinstance(result.spread_mean, float)
        assert isinstance(result.spread_std, float)
        assert result.spread_std > 0
    
    def test_cointegration_engle_granger_half_life(self, analyzer, cointegrated_prices):
        """Test half-life calculation in Engle-Granger test."""
        price1, price2 = cointegrated_prices
        
        result = analyzer.test_cointegration_engle_granger(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        # Half-life should be positive for mean-reverting spread
        if result.half_life is not None:
            assert result.half_life > 0
    
    def test_cointegration_engle_granger_insufficient_data(self, analyzer):
        """Test error handling with insufficient data."""
        dates = pd.date_range(start='2023-01-01', end='2023-01-30', freq='B')
        price1 = pd.Series(np.random.randn(len(dates)) + 100, index=dates)
        price2 = pd.Series(np.random.randn(len(dates)) + 100, index=dates)
        
        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.test_cointegration_engle_granger(
                price1,
                price2,
                ticker1='A',
                ticker2='B'
            )
    
    # Test Cointegration - Johansen
    
    def test_cointegration_johansen_cointegrated(self, analyzer, cointegrated_prices):
        """Test Johansen cointegration test on cointegrated series."""
        price1, price2 = cointegrated_prices
        
        result = analyzer.test_cointegration_johansen(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        assert isinstance(result, CointegrationResult)
        assert result.ticker1 == 'TICKER1'
        assert result.ticker2 == 'TICKER2'
        assert result.test_method == 'johansen'
        assert isinstance(result.is_cointegrated, bool)
        assert isinstance(result.hedge_ratio, float)
        assert isinstance(result.test_statistic, float)
    
    def test_cointegration_johansen_non_cointegrated(self, analyzer, non_cointegrated_prices):
        """Test Johansen cointegration test on non-cointegrated series."""
        price1, price2 = non_cointegrated_prices
        
        result = analyzer.test_cointegration_johansen(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        assert isinstance(result, CointegrationResult)
        # Independent random walks should not be cointegrated
        assert result.is_cointegrated == False
    
    def test_cointegration_johansen_spread_stats(self, analyzer, cointegrated_prices):
        """Test spread statistics in Johansen test."""
        price1, price2 = cointegrated_prices
        
        result = analyzer.test_cointegration_johansen(
            price1,
            price2,
            ticker1='TICKER1',
            ticker2='TICKER2'
        )
        
        assert isinstance(result.spread_mean, float)
        assert isinstance(result.spread_std, float)
        assert result.spread_std > 0
    
    def test_cointegration_johansen_insufficient_data(self, analyzer):
        """Test error handling with insufficient data."""
        dates = pd.date_range(start='2023-01-01', end='2023-01-30', freq='B')
        price1 = pd.Series(np.random.randn(len(dates)) + 100, index=dates)
        price2 = pd.Series(np.random.randn(len(dates)) + 100, index=dates)
        
        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.test_cointegration_johansen(
                price1,
                price2,
                ticker1='A',
                ticker2='B'
            )
    
    # Test Momentum Exposure
    
    def test_calculate_momentum_exposure_positive(self, analyzer):
        """Test momentum exposure calculation with upward trend."""
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        # Upward trending prices
        prices = pd.Series(np.linspace(100, 150, len(dates)), index=dates)
        
        momentum = analyzer.calculate_momentum_exposure(prices, lookback_period=252)
        
        assert isinstance(momentum, float)
        assert momentum > 0  # Upward trend should have positive momentum
    
    def test_calculate_momentum_exposure_negative(self, analyzer):
        """Test momentum exposure calculation with downward trend."""
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        # Downward trending prices
        prices = pd.Series(np.linspace(150, 100, len(dates)), index=dates)
        
        momentum = analyzer.calculate_momentum_exposure(prices, lookback_period=252)
        
        assert isinstance(momentum, float)
        assert momentum < 0  # Downward trend should have negative momentum
    
    def test_calculate_momentum_exposure_insufficient_data(self, analyzer):
        """Test momentum exposure with insufficient data."""
        dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='B')
        prices = pd.Series(np.linspace(100, 110, len(dates)), index=dates)
        
        # Should handle short series gracefully
        momentum = analyzer.calculate_momentum_exposure(prices, lookback_period=252)
        
        assert isinstance(momentum, float)
    
    # Test Quality Exposure
    
    def test_calculate_quality_exposure_high_quality(self, analyzer):
        """Test quality exposure with high-quality metrics."""
        financials = {
            'roe': 0.20,  # 20% ROE
            'roa': 0.08,  # 8% ROA
            'debt_to_equity': 0.3,  # Low leverage
            'earnings_stability': 0.9,  # High stability
        }
        
        quality = analyzer.calculate_quality_exposure(financials)
        
        assert isinstance(quality, float)
        assert 0.0 <= quality <= 1.0
        assert quality > 0.7  # Should be high quality score
    
    def test_calculate_quality_exposure_low_quality(self, analyzer):
        """Test quality exposure with low-quality metrics."""
        financials = {
            'roe': 0.05,  # 5% ROE
            'roa': 0.01,  # 1% ROA
            'debt_to_equity': 2.5,  # High leverage
            'earnings_stability': 0.2,  # Low stability
        }
        
        quality = analyzer.calculate_quality_exposure(financials)
        
        assert isinstance(quality, float)
        assert 0.0 <= quality <= 1.0
        assert quality < 0.4  # Should be low quality score
    
    def test_calculate_quality_exposure_missing_data(self, analyzer):
        """Test quality exposure with missing metrics."""
        financials = {}
        
        quality = analyzer.calculate_quality_exposure(financials)
        
        assert isinstance(quality, float)
        assert 0.0 <= quality <= 1.0
    
    # Test Value Exposure
    
    def test_calculate_value_exposure_value_stock(self, analyzer):
        """Test value exposure for value stock."""
        price = 50.0
        book_value = 45.0  # P/B = 1.11
        earnings = 5.0  # P/E = 10
        
        value = analyzer.calculate_value_exposure(price, book_value, earnings)
        
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0
        assert value > 0.5  # Should be value-oriented
    
    def test_calculate_value_exposure_growth_stock(self, analyzer):
        """Test value exposure for growth stock."""
        price = 100.0
        book_value = 10.0  # P/B = 10
        earnings = 2.0  # P/E = 50
        
        value = analyzer.calculate_value_exposure(price, book_value, earnings)
        
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0
        assert value < 0.3  # Should be growth-oriented (low value score)
    
    def test_calculate_value_exposure_invalid_price(self, analyzer):
        """Test value exposure with invalid price."""
        value = analyzer.calculate_value_exposure(0.0, 50.0, 5.0)
        
        assert value == 0.0
    
    # Test Synthetic Factor Generation
    
    def test_generate_synthetic_factor_returns(self, analyzer):
        """Test synthetic factor return generation."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        factors = analyzer.generate_synthetic_factor_returns(
            start_date,
            end_date,
            include_momentum=True,
            include_quality=True
        )
        
        assert isinstance(factors, pd.DataFrame)
        assert 'Mkt-RF' in factors.columns
        assert 'SMB' in factors.columns
        assert 'HML' in factors.columns
        assert 'RMW' in factors.columns
        assert 'CMA' in factors.columns
        assert 'MOM' in factors.columns
        assert 'QMJ' in factors.columns
        assert len(factors) > 200  # Should have ~252 business days
    
    def test_generate_synthetic_factor_returns_no_momentum(self, analyzer):
        """Test synthetic factor generation without momentum."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        factors = analyzer.generate_synthetic_factor_returns(
            start_date,
            end_date,
            include_momentum=False,
            include_quality=True
        )
        
        assert 'MOM' not in factors.columns
        assert 'QMJ' in factors.columns
    
    def test_generate_synthetic_factor_returns_no_quality(self, analyzer):
        """Test synthetic factor generation without quality."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        factors = analyzer.generate_synthetic_factor_returns(
            start_date,
            end_date,
            include_momentum=True,
            include_quality=False
        )
        
        assert 'MOM' in factors.columns
        assert 'QMJ' not in factors.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
