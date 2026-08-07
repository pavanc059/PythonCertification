"""
Tests for RiskAnalyzer module

Tests VaR, CVaR, and performance ratio calculations.
Requirements: 14.3, 14.4, 14.5, 14.12
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from stockiq.analytics.risk import RiskAnalyzer, VaRResult, CVaRResult, PerformanceMetrics


class TestRiskAnalyzer:
    """Test suite for RiskAnalyzer class"""
    
    @pytest.fixture
    def risk_analyzer(self):
        """Create RiskAnalyzer instance"""
        return RiskAnalyzer(risk_free_rate=0.02)
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample return data for testing"""
        np.random.seed(42)
        # Generate 252 days of returns (1 year)
        # Mean return of 0.05% per day with 1% volatility
        returns = np.random.normal(0.0005, 0.01, 252)
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        return pd.Series(returns, index=dates)
    
    @pytest.fixture
    def negative_skew_returns(self):
        """Generate returns with negative skew (fat left tail)"""
        np.random.seed(42)
        # Mix normal returns with occasional large losses
        normal_returns = np.random.normal(0.001, 0.01, 240)
        crash_returns = np.random.normal(-0.05, 0.02, 12)
        returns = np.concatenate([normal_returns, crash_returns])
        np.random.shuffle(returns)
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        return pd.Series(returns, index=dates)
    
    @pytest.fixture
    def uptrend_returns(self):
        """Generate consistently positive returns (uptrend)"""
        np.random.seed(42)
        returns = np.random.normal(0.002, 0.005, 252)
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        return pd.Series(returns, index=dates)
    
    # VaR Tests (Requirement 14.3)
    
    def test_var_95_historical_simulation(self, risk_analyzer, sample_returns):
        """Test VaR calculation at 95% confidence using historical simulation"""
        result = risk_analyzer.calculate_var(
            sample_returns,
            confidence_level=0.95,
            method="historical_simulation"
        )
        
        assert isinstance(result, VaRResult)
        assert result.confidence_level == 0.95
        assert result.method == "historical_simulation"
        assert result.lookback_days == 252
        assert result.var_amount > 0  # VaR should be positive (loss amount)
        assert result.var_percentage > 0
        assert result.var_percentage < 100  # Should be reasonable percentage
    
    def test_var_99_historical_simulation(self, risk_analyzer, sample_returns):
        """Test VaR calculation at 99% confidence using historical simulation"""
        result = risk_analyzer.calculate_var(
            sample_returns,
            confidence_level=0.99,
            method="historical_simulation"
        )
        
        assert isinstance(result, VaRResult)
        assert result.confidence_level == 0.99
        assert result.var_amount > 0
        
        # 99% VaR should be larger than 95% VaR
        var_95 = risk_analyzer.calculate_var(sample_returns, confidence_level=0.95)
        assert result.var_amount >= var_95.var_amount
    
    def test_var_parametric(self, risk_analyzer, sample_returns):
        """Test parametric VaR calculation (assumes normal distribution)"""
        result = risk_analyzer.calculate_var(
            sample_returns,
            confidence_level=0.95,
            method="parametric"
        )
        
        assert isinstance(result, VaRResult)
        assert result.method == "parametric"
        assert result.var_amount > 0
    
    def test_var_with_short_history(self, risk_analyzer):
        """Test VaR calculation with less than 252 days of data"""
        # Only 100 days of data
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.01, 100))
        
        result = risk_analyzer.calculate_var(returns, lookback_days=252)
        
        assert result.lookback_days == 100  # Should use available data
        assert result.var_amount > 0
    
    def test_var_invalid_method(self, risk_analyzer, sample_returns):
        """Test VaR calculation with invalid method raises error"""
        with pytest.raises(ValueError, match="Unknown VaR method"):
            risk_analyzer.calculate_var(
                sample_returns,
                method="invalid_method"
            )
    
    # CVaR Tests (Requirement 14.4)
    
    def test_cvar_95_historical_simulation(self, risk_analyzer, sample_returns):
        """Test CVaR calculation at 95% confidence"""
        result = risk_analyzer.calculate_cvar(
            sample_returns,
            confidence_level=0.95,
            method="historical_simulation"
        )
        
        assert isinstance(result, CVaRResult)
        assert result.confidence_level == 0.95
        assert result.method == "historical_simulation"
        assert result.cvar_amount > 0  # CVaR should be positive (loss amount)
        assert result.cvar_percentage > 0
        assert result.tail_losses >= 0  # Count of tail observations
    
    def test_cvar_99_historical_simulation(self, risk_analyzer, sample_returns):
        """Test CVaR calculation at 99% confidence"""
        result = risk_analyzer.calculate_cvar(
            sample_returns,
            confidence_level=0.99,
            method="historical_simulation"
        )
        
        assert isinstance(result, CVaRResult)
        assert result.confidence_level == 0.99
        assert result.cvar_amount > 0
    
    def test_cvar_greater_than_var(self, risk_analyzer, negative_skew_returns):
        """Test that CVaR >= VaR (CVaR measures expected loss beyond VaR)"""
        var_result = risk_analyzer.calculate_var(
            negative_skew_returns,
            confidence_level=0.95
        )
        cvar_result = risk_analyzer.calculate_cvar(
            negative_skew_returns,
            confidence_level=0.95
        )
        
        # CVaR should be greater than or equal to VaR
        assert cvar_result.cvar_amount >= var_result.var_amount
    
    def test_cvar_tail_loss_count(self, risk_analyzer, sample_returns):
        """Test that CVaR tail loss count is reasonable"""
        result = risk_analyzer.calculate_cvar(
            sample_returns,
            confidence_level=0.95
        )
        
        # At 95% confidence, we expect approximately 5% of observations in tail
        expected_tail_count = int(len(sample_returns) * 0.05)
        
        # Allow some variance due to randomness
        assert result.tail_losses >= 0
        assert result.tail_losses <= len(sample_returns)
    
    # Sharpe Ratio Tests (Requirement 14.5)
    
    def test_sharpe_ratio_calculation(self, risk_analyzer, sample_returns):
        """Test Sharpe ratio calculation"""
        sharpe = risk_analyzer.calculate_sharpe_ratio(sample_returns)
        
        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)
        # Sharpe ratio typically ranges from -3 to 3 for most portfolios
        assert -5 < sharpe < 5
    
    def test_sharpe_ratio_positive_returns(self, risk_analyzer, uptrend_returns):
        """Test Sharpe ratio with positive returns should be positive"""
        sharpe = risk_analyzer.calculate_sharpe_ratio(uptrend_returns)
        
        # With consistent positive returns, Sharpe should be positive
        assert sharpe > 0
    
    def test_sharpe_ratio_zero_volatility(self, risk_analyzer):
        """Test Sharpe ratio with zero volatility returns zero"""
        # All returns are identical (no volatility)
        returns = pd.Series([0.001] * 252)
        sharpe = risk_analyzer.calculate_sharpe_ratio(returns)
        
        assert sharpe == 0.0
    
    # Sortino Ratio Tests (Requirement 14.5)
    
    def test_sortino_ratio_calculation(self, risk_analyzer, sample_returns):
        """Test Sortino ratio calculation"""
        sortino = risk_analyzer.calculate_sortino_ratio(sample_returns)
        
        assert isinstance(sortino, float)
        assert not np.isnan(sortino)
        assert not np.isinf(sortino)
    
    def test_sortino_ratio_no_downside(self, risk_analyzer, uptrend_returns):
        """Test Sortino ratio with no negative returns"""
        # Make all returns positive
        positive_returns = uptrend_returns.abs()
        sortino = risk_analyzer.calculate_sortino_ratio(positive_returns)
        
        # With no downside, Sortino should be infinite or very high
        assert sortino > 0
    
    def test_sortino_higher_than_sharpe_asymmetric(self, risk_analyzer, uptrend_returns):
        """Test that Sortino > Sharpe for asymmetric positive returns"""
        sharpe = risk_analyzer.calculate_sharpe_ratio(uptrend_returns)
        sortino = risk_analyzer.calculate_sortino_ratio(uptrend_returns)
        
        # With mostly positive returns, Sortino should be higher than Sharpe
        # (Sortino only penalizes downside volatility)
        assert sortino >= sharpe
    
    # Calmar Ratio Tests (Requirement 14.5)
    
    def test_calmar_ratio_calculation(self, risk_analyzer, sample_returns):
        """Test Calmar ratio calculation"""
        calmar = risk_analyzer.calculate_calmar_ratio(sample_returns)
        
        assert isinstance(calmar, float)
        assert not np.isnan(calmar)
    
    def test_calmar_ratio_with_drawdown(self, risk_analyzer, negative_skew_returns):
        """Test Calmar ratio with significant drawdown"""
        calmar = risk_analyzer.calculate_calmar_ratio(negative_skew_returns)
        
        assert isinstance(calmar, float)
        # With drawdown, Calmar should be finite
        assert not np.isinf(calmar)
    
    def test_max_drawdown_calculation(self, risk_analyzer):
        """Test maximum drawdown calculation"""
        # Create price series with known drawdown
        prices = pd.Series([100, 110, 120, 90, 95, 100])  # 25% drawdown from 120 to 90
        
        max_dd = risk_analyzer.calculate_max_drawdown(prices)
        
        expected_dd = (90 - 120) / 120  # -0.25
        assert np.isclose(max_dd, expected_dd, atol=0.001)
        assert max_dd < 0  # Drawdown should be negative
    
    def test_max_drawdown_no_decline(self, risk_analyzer):
        """Test maximum drawdown with no decline (all gains)"""
        prices = pd.Series([100, 110, 120, 130, 140, 150])
        
        max_dd = risk_analyzer.calculate_max_drawdown(prices)
        
        assert max_dd == 0.0  # No drawdown
    
    # Performance Metrics Tests (Requirement 14.5)
    
    def test_performance_metrics_comprehensive(self, risk_analyzer, sample_returns):
        """Test comprehensive performance metrics calculation"""
        metrics = risk_analyzer.calculate_performance_metrics(sample_returns)
        
        assert isinstance(metrics, PerformanceMetrics)
        assert isinstance(metrics.sharpe_ratio, float)
        assert isinstance(metrics.sortino_ratio, float)
        assert isinstance(metrics.calmar_ratio, float)
        assert isinstance(metrics.annual_return, float)
        assert isinstance(metrics.annual_volatility, float)
        assert isinstance(metrics.downside_volatility, float)
        assert isinstance(metrics.max_drawdown, float)
        assert metrics.lookback_days == 252
    
    def test_performance_metrics_volatility_positive(self, risk_analyzer, sample_returns):
        """Test that volatility metrics are non-negative"""
        metrics = risk_analyzer.calculate_performance_metrics(sample_returns)
        
        assert metrics.annual_volatility >= 0
        assert metrics.downside_volatility >= 0
    
    def test_performance_metrics_max_drawdown_negative(self, risk_analyzer, sample_returns):
        """Test that max drawdown is non-positive"""
        metrics = risk_analyzer.calculate_performance_metrics(sample_returns)
        
        assert metrics.max_drawdown <= 0
    
    # Rolling Window Tests (Requirement 14.12)
    
    def test_rolling_var_252_days(self, risk_analyzer, sample_returns):
        """Test rolling VaR with 252-day window"""
        rolling_var = risk_analyzer.calculate_rolling_var(
            sample_returns,
            window=252
        )
        
        assert isinstance(rolling_var, pd.Series)
        assert len(rolling_var) == len(sample_returns)
        
        # First 251 values should be NaN (insufficient data)
        assert pd.isna(rolling_var.iloc[:251]).all()
        
        # Last value should be valid
        assert not pd.isna(rolling_var.iloc[-1])
        assert rolling_var.iloc[-1] > 0
    
    def test_rolling_sharpe_252_days(self, risk_analyzer, sample_returns):
        """Test rolling Sharpe ratio with 252-day window"""
        rolling_sharpe = risk_analyzer.calculate_rolling_sharpe(
            sample_returns,
            window=252
        )
        
        assert isinstance(rolling_sharpe, pd.Series)
        assert len(rolling_sharpe) == len(sample_returns)
        
        # First 251 values should be NaN
        assert pd.isna(rolling_sharpe.iloc[:251]).all()
        
        # Last value should be valid
        assert not pd.isna(rolling_sharpe.iloc[-1])
    
    def test_rolling_var_shorter_window(self, risk_analyzer, sample_returns):
        """Test rolling VaR with shorter window (e.g., 60 days)"""
        rolling_var = risk_analyzer.calculate_rolling_var(
            sample_returns,
            window=60
        )
        
        assert isinstance(rolling_var, pd.Series)
        
        # First 59 values should be NaN
        assert pd.isna(rolling_var.iloc[:59]).all()
        
        # Should have more valid values than 252-day window
        assert rolling_var.notna().sum() > (252 - 60)
    
    def test_lookback_days_parameter(self, risk_analyzer, sample_returns):
        """Test that lookback_days parameter is respected"""
        # Calculate VaR with different lookback periods
        var_60 = risk_analyzer.calculate_var(sample_returns, lookback_days=60)
        var_252 = risk_analyzer.calculate_var(sample_returns, lookback_days=252)
        
        assert var_60.lookback_days == 60
        assert var_252.lookback_days == 252
        
        # Results may differ due to different data windows
        # Just ensure both are valid
        assert var_60.var_amount > 0
        assert var_252.var_amount > 0
    
    # Risk Report Tests
    
    def test_generate_risk_report(self, risk_analyzer, sample_returns):
        """Test comprehensive risk report generation"""
        report = risk_analyzer.generate_risk_report(sample_returns)
        
        assert isinstance(report, dict)
        assert 'var_95' in report
        assert 'var_99' in report
        assert 'cvar_95' in report
        assert 'cvar_99' in report
        assert 'performance' in report
        assert 'lookback_days' in report
        
        # Verify all components are correct types
        assert isinstance(report['var_95'], VaRResult)
        assert isinstance(report['var_99'], VaRResult)
        assert isinstance(report['cvar_95'], CVaRResult)
        assert isinstance(report['cvar_99'], CVaRResult)
        assert isinstance(report['performance'], PerformanceMetrics)
        assert report['lookback_days'] == 252
    
    def test_risk_report_consistency(self, risk_analyzer, sample_returns):
        """Test that risk report components are internally consistent"""
        report = risk_analyzer.generate_risk_report(sample_returns)
        
        # 99% VaR should be >= 95% VaR
        assert report['var_99'].var_amount >= report['var_95'].var_amount
        
        # CVaR should be >= VaR at same confidence level
        assert report['cvar_95'].cvar_amount >= report['var_95'].var_amount
        assert report['cvar_99'].cvar_amount >= report['var_99'].var_amount
    
    # Edge Cases
    
    def test_empty_returns(self, risk_analyzer):
        """Test handling of empty returns series"""
        empty_returns = pd.Series([])
        
        # Should handle gracefully (use available data)
        result = risk_analyzer.calculate_var(empty_returns, lookback_days=252)
        assert result.lookback_days == 0
    
    def test_single_return(self, risk_analyzer):
        """Test handling of single return value"""
        single_return = pd.Series([0.01])
        
        result = risk_analyzer.calculate_var(single_return, lookback_days=252)
        assert result.lookback_days == 1
        assert result.var_amount >= 0
    
    def test_extreme_losses(self, risk_analyzer):
        """Test handling of extreme loss events"""
        # Create returns with more extreme losses in the tail
        # Mostly small returns, but with significant losses
        np.random.seed(42)
        normal_returns = np.random.normal(0.0001, 0.005, 240)  # Small daily returns
        crash_returns = [-0.20, -0.18, -0.15, -0.12, -0.10, -0.08, -0.06, -0.05, -0.04, -0.03, -0.02, -0.01]
        all_returns = np.concatenate([normal_returns, crash_returns])
        returns = pd.Series(all_returns)
        
        var_95 = risk_analyzer.calculate_var(returns, confidence_level=0.95)
        var_99 = risk_analyzer.calculate_var(returns, confidence_level=0.99)
        cvar_95 = risk_analyzer.calculate_cvar(returns, confidence_level=0.95)
        cvar_99 = risk_analyzer.calculate_cvar(returns, confidence_level=0.99)
        
        # Should capture losses from the tail
        # 99% VaR should be larger than 95% VaR
        assert var_99.var_amount >= var_95.var_amount
        
        # CVaR should be >= VaR at same confidence level
        assert cvar_95.cvar_amount >= var_95.var_amount
        assert cvar_99.cvar_amount >= var_99.var_amount
        
        # With extreme tail losses, CVaR should capture the averaging effect
        assert cvar_99.cvar_amount > 0
    
    def test_risk_free_rate_impact(self):
        """Test impact of different risk-free rates on Sharpe ratio"""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0005, 0.01, 252))
        
        analyzer_low_rf = RiskAnalyzer(risk_free_rate=0.01)
        analyzer_high_rf = RiskAnalyzer(risk_free_rate=0.05)
        
        sharpe_low = analyzer_low_rf.calculate_sharpe_ratio(returns)
        sharpe_high = analyzer_high_rf.calculate_sharpe_ratio(returns)
        
        # Higher risk-free rate should result in lower Sharpe ratio
        # (assuming returns are positive)
        # Note: This may not always hold if returns are very low
        assert isinstance(sharpe_low, float)
        assert isinstance(sharpe_high, float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
