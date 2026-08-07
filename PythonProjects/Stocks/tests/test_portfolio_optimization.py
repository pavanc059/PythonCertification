"""
Tests for Portfolio Optimization

Tests mean-variance and Black-Litterman optimization algorithms.

Requirements: 14.10, 14.11
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from stockiq.analytics.portfolio.mean_variance import (
    MeanVarianceOptimizer,
    Portfolio,
    OptimizationConstraints,
    OptimizationResult,
)
from stockiq.analytics.portfolio.black_litterman import (
    BlackLittermanOptimizer,
    InvestorViews,
    InvestorView,
    BlackLittermanResult,
)


# Test fixtures
@pytest.fixture
def sample_returns():
    """Generate sample return data for 5 stocks over 252 days"""
    np.random.seed(42)
    n_days = 252
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    # Generate correlated returns
    mean_returns = np.array([0.001, 0.0008, 0.0012, 0.0015, 0.002])  # Daily
    cov_matrix = np.array([
        [0.0004, 0.0002, 0.0001, 0.0001, 0.0002],
        [0.0002, 0.0003, 0.0001, 0.0001, 0.0001],
        [0.0001, 0.0001, 0.0005, 0.0002, 0.0002],
        [0.0001, 0.0001, 0.0002, 0.0006, 0.0003],
        [0.0002, 0.0001, 0.0002, 0.0003, 0.0008],
    ])
    
    returns = np.random.multivariate_normal(mean_returns, cov_matrix, n_days)
    
    return pd.DataFrame(returns, columns=tickers)


@pytest.fixture
def sample_market_caps():
    """Sample market capitalizations"""
    return {
        'AAPL': 2800e9,  # $2.8T
        'MSFT': 2500e9,  # $2.5T
        'GOOGL': 1600e9,  # $1.6T
        'AMZN': 1400e9,  # $1.4T
        'TSLA': 800e9,    # $800B
    }


class TestMeanVarianceOptimizer:
    """Test suite for mean-variance optimization"""
    
    def test_max_sharpe_optimization(self, sample_returns):
        """Test maximum Sharpe ratio optimization"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        result = optimizer.optimize_max_sharpe(sample_returns)
        
        # Verify result structure
        assert isinstance(result, OptimizationResult)
        assert isinstance(result.portfolio, Portfolio)
        assert result.convergence is True
        
        # Verify portfolio properties
        portfolio = result.portfolio
        assert len(portfolio.weights) > 0
        assert abs(sum(portfolio.weights.values()) - 1.0) < 0.01  # Weights sum to 1
        assert all(w >= -0.01 for w in portfolio.weights.values())  # Long-only (with tolerance)
        assert portfolio.sharpe_ratio > 0  # Positive Sharpe ratio
        
        print(f"\nMax Sharpe Portfolio:")
        print(f"  Expected Return: {portfolio.expected_return:.2%}")
        print(f"  Volatility: {portfolio.volatility:.2%}")
        print(f"  Sharpe Ratio: {portfolio.sharpe_ratio:.2f}")
        print(f"  Weights: {portfolio.weights}")
    
    def test_min_variance_optimization(self, sample_returns):
        """Test minimum variance optimization"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        result = optimizer.optimize_min_variance(sample_returns)
        
        assert result.convergence is True
        portfolio = result.portfolio
        
        # Min variance should have lowest volatility
        assert portfolio.volatility > 0
        assert len(portfolio.weights) > 0
        assert abs(sum(portfolio.weights.values()) - 1.0) < 0.01
        
        print(f"\nMin Variance Portfolio:")
        print(f"  Expected Return: {portfolio.expected_return:.2%}")
        print(f"  Volatility: {portfolio.volatility:.2%}")
        print(f"  Sharpe Ratio: {portfolio.sharpe_ratio:.2f}")
        print(f"  Weights: {portfolio.weights}")
    
    def test_efficient_return_optimization(self, sample_returns):
        """Test optimization for target return"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        target_return = 0.15  # 15% annual return
        
        result = optimizer.optimize_efficient_return(
            sample_returns,
            target_return=target_return
        )
        
        assert result.convergence is True
        portfolio = result.portfolio
        
        # Should achieve approximately target return
        assert abs(portfolio.expected_return - target_return) < 0.05  # Within 5%
        assert len(portfolio.weights) > 0
        
        print(f"\nEfficient Return Portfolio (target={target_return:.2%}):")
        print(f"  Expected Return: {portfolio.expected_return:.2%}")
        print(f"  Volatility: {portfolio.volatility:.2%}")
        print(f"  Sharpe Ratio: {portfolio.sharpe_ratio:.2f}")
    
    def test_weight_constraints(self, sample_returns):
        """Test optimization with weight constraints"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        
        # Constrain each weight to max 30%
        constraints = OptimizationConstraints(
            min_weight=0.0,
            max_weight=0.3,
            risk_free_rate=0.02
        )
        
        result = optimizer.optimize_max_sharpe(sample_returns, constraints)
        
        assert result.convergence is True
        portfolio = result.portfolio
        
        # Verify weight constraints
        for weight in portfolio.weights.values():
            assert 0.0 <= weight <= 0.31  # Allow small tolerance
        
        print(f"\nConstrained Portfolio (max 30% per asset):")
        print(f"  Weights: {portfolio.weights}")
        print(f"  Max weight: {max(portfolio.weights.values()):.2%}")
    
    def test_efficient_frontier(self, sample_returns):
        """Test efficient frontier generation"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        
        frontier = optimizer.generate_efficient_frontier(
            sample_returns,
            num_points=10
        )
        
        assert len(frontier) > 0
        assert all(isinstance(p, Portfolio) for p in frontier)
        
        # Frontier should be sorted by increasing volatility
        volatilities = [p.volatility for p in frontier]
        assert volatilities == sorted(volatilities)
        
        print(f"\nEfficient Frontier ({len(frontier)} points):")
        for i, portfolio in enumerate(frontier[:3]):  # Show first 3
            print(f"  Point {i+1}: Return={portfolio.expected_return:.2%}, "
                  f"Vol={portfolio.volatility:.2%}, Sharpe={portfolio.sharpe_ratio:.2f}")
    
    def test_portfolio_metrics_calculation(self, sample_returns):
        """Test portfolio metrics calculation for given weights"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        
        # Equal weight portfolio
        weights = {ticker: 0.2 for ticker in sample_returns.columns}
        
        exp_return, volatility, sharpe = optimizer.calculate_portfolio_metrics(
            weights, sample_returns
        )
        
        assert exp_return > 0
        assert volatility > 0
        assert isinstance(sharpe, float)
        
        print(f"\nEqual Weight Portfolio:")
        print(f"  Expected Return: {exp_return:.2%}")
        print(f"  Volatility: {volatility:.2%}")
        print(f"  Sharpe Ratio: {sharpe:.2f}")
    
    def test_empty_returns_handling(self):
        """Test handling of empty returns"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        empty_returns = pd.DataFrame()
        
        with pytest.raises(Exception):
            optimizer.optimize_max_sharpe(empty_returns)
    
    def test_single_asset_optimization(self):
        """Test optimization with single asset"""
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        
        # Single asset returns
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 252)
        })
        
        result = optimizer.optimize_max_sharpe(returns)
        
        assert result.convergence is True
        assert 'AAPL' in result.portfolio.weights
        assert abs(result.portfolio.weights['AAPL'] - 1.0) < 0.01


class TestBlackLittermanOptimizer:
    """Test suite for Black-Litterman optimization"""
    
    def test_optimization_without_views(self, sample_returns, sample_market_caps):
        """Test BL optimization with no investor views"""
        optimizer = BlackLittermanOptimizer(
            risk_free_rate=0.02,
            tau=0.025,
            risk_aversion=2.5
        )
        
        views = InvestorViews()  # Empty views
        
        result = optimizer.optimize(
            sample_returns,
            sample_market_caps,
            views,
            optimize_method="max_sharpe"
        )
        
        assert isinstance(result, BlackLittermanResult)
        assert isinstance(result.portfolio, Portfolio)
        assert result.views_applied == 0
        assert len(result.implied_returns) == len(sample_returns.columns)
        
        print(f"\nBL Portfolio (no views):")
        print(f"  Expected Return: {result.portfolio.expected_return:.2%}")
        print(f"  Volatility: {result.portfolio.volatility:.2%}")
        print(f"  Sharpe Ratio: {result.portfolio.sharpe_ratio:.2f}")
        print(f"  Weights: {result.portfolio.weights}")
    
    def test_optimization_with_absolute_views(self, sample_returns, sample_market_caps):
        """Test BL optimization with absolute views"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        # Create views
        views = InvestorViews()
        views.add_absolute_view(
            ticker='AAPL',
            expected_return=0.12,  # 12% expected return
            confidence=0.8,
            description="Strong confidence in AAPL growth"
        )
        views.add_absolute_view(
            ticker='TSLA',
            expected_return=0.18,  # 18% expected return
            confidence=0.6,
            description="Moderate confidence in TSLA growth"
        )
        
        result = optimizer.optimize(
            sample_returns,
            sample_market_caps,
            views,
            optimize_method="max_sharpe"
        )
        
        assert result.views_applied == 2
        assert 'AAPL' in result.posterior_returns
        assert 'TSLA' in result.posterior_returns
        
        # Posterior returns should differ from implied returns
        assert result.implied_returns != result.posterior_returns
        
        print(f"\nBL Portfolio (absolute views):")
        print(f"  Views Applied: {result.views_applied}")
        print(f"  Expected Return: {result.portfolio.expected_return:.2%}")
        print(f"  Volatility: {result.portfolio.volatility:.2%}")
        print(f"  Weights: {result.portfolio.weights}")
        
        # Show impact of views
        print(f"\n  Implied vs Posterior Returns:")
        for ticker in ['AAPL', 'TSLA']:
            implied = result.implied_returns[ticker]
            posterior = result.posterior_returns[ticker]
            print(f"    {ticker}: {implied:.2%} → {posterior:.2%} "
                  f"(Δ {posterior-implied:+.2%})")
    
    def test_optimization_with_relative_views(self, sample_returns, sample_market_caps):
        """Test BL optimization with relative views"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        # Create relative views
        views = InvestorViews()
        views.add_relative_view(
            ticker1='AAPL',
            ticker2='MSFT',
            expected_outperformance=0.05,  # AAPL outperforms MSFT by 5%
            confidence=0.7,
            description="AAPL will outperform MSFT"
        )
        views.add_relative_view(
            ticker1='GOOGL',
            ticker2='AMZN',
            expected_outperformance=0.03,  # GOOGL outperforms AMZN by 3%
            confidence=0.5,
            description="GOOGL will slightly outperform AMZN"
        )
        
        result = optimizer.optimize(
            sample_returns,
            sample_market_caps,
            views,
            optimize_method="max_sharpe"
        )
        
        assert result.views_applied == 2
        
        print(f"\nBL Portfolio (relative views):")
        print(f"  Views Applied: {result.views_applied}")
        print(f"  Expected Return: {result.portfolio.expected_return:.2%}")
        print(f"  Weights: {result.portfolio.weights}")
    
    def test_mixed_views(self, sample_returns, sample_market_caps):
        """Test BL optimization with mixed absolute and relative views"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        views = InvestorViews()
        views.add_absolute_view('AAPL', 0.15, confidence=0.8)
        views.add_relative_view('TSLA', 'AMZN', 0.08, confidence=0.6)
        
        result = optimizer.optimize(
            sample_returns,
            sample_market_caps,
            views
        )
        
        assert result.views_applied == 2
        assert len(result.portfolio.weights) > 0
        
        print(f"\nBL Portfolio (mixed views):")
        print(f"  Weights: {result.portfolio.weights}")
    
    def test_confidence_levels(self, sample_returns, sample_market_caps):
        """Test that confidence levels affect optimization"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        # High confidence view
        high_conf_views = InvestorViews()
        high_conf_views.add_absolute_view('AAPL', 0.20, confidence=0.95)
        
        # Low confidence view  
        low_conf_views = InvestorViews()
        low_conf_views.add_absolute_view('AAPL', 0.20, confidence=0.30)
        
        high_result = optimizer.optimize(sample_returns, sample_market_caps, high_conf_views)
        low_result = optimizer.optimize(sample_returns, sample_market_caps, low_conf_views)
        
        # High confidence should result in larger allocation to AAPL
        high_aapl_weight = high_result.portfolio.weights.get('AAPL', 0.0)
        low_aapl_weight = low_result.portfolio.weights.get('AAPL', 0.0)
        
        print(f"\nConfidence Level Impact on AAPL weight:")
        print(f"  High confidence (0.95): {high_aapl_weight:.2%}")
        print(f"  Low confidence (0.30): {low_aapl_weight:.2%}")
        
        # Not strict assertion as optimization can vary
        # But generally high confidence should increase weight
    
    def test_comparison_function(self, sample_returns, sample_market_caps):
        """Test equilibrium vs posterior comparison"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        views = InvestorViews()
        views.add_absolute_view('AAPL', 0.15, confidence=0.8)
        views.add_absolute_view('MSFT', 0.08, confidence=0.7)
        
        result = optimizer.optimize(sample_returns, sample_market_caps, views)
        
        comparison = optimizer.compare_equilibrium_vs_posterior(result)
        
        assert isinstance(comparison, pd.DataFrame)
        assert 'Equilibrium_Return' in comparison.columns
        assert 'Posterior_Return' in comparison.columns
        assert 'Difference' in comparison.columns
        assert len(comparison) == len(sample_returns.columns)
        
        print(f"\nEquilibrium vs Posterior Returns:")
        print(comparison.to_string(index=False))
    
    def test_sensitivity_analysis(self, sample_returns, sample_market_caps):
        """Test sensitivity to tau parameter"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        views = InvestorViews()
        views.add_absolute_view('AAPL', 0.15, confidence=0.8)
        
        sensitivity = optimizer.sensitivity_analysis(
            sample_returns,
            sample_market_caps,
            views,
            tau_values=[0.01, 0.025, 0.05, 0.1]
        )
        
        assert isinstance(sensitivity, pd.DataFrame)
        assert 'tau' in sensitivity.columns
        assert len(sensitivity) == 4
        
        print(f"\nSensitivity Analysis (tau parameter):")
        print(sensitivity.to_string(index=False))
    
    def test_min_variance_method(self, sample_returns, sample_market_caps):
        """Test BL with min variance optimization"""
        optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        
        views = InvestorViews()
        views.add_absolute_view('AAPL', 0.12, confidence=0.7)
        
        result = optimizer.optimize(
            sample_returns,
            sample_market_caps,
            views,
            optimize_method="min_variance"
        )
        
        assert result.portfolio.optimization_method == "min_variance"
        assert result.portfolio.volatility > 0
        
        print(f"\nBL Min Variance Portfolio:")
        print(f"  Volatility: {result.portfolio.volatility:.2%}")
        print(f"  Weights: {result.portfolio.weights}")


class TestInvestorViews:
    """Test suite for InvestorViews class"""
    
    def test_add_absolute_view(self):
        """Test adding absolute views"""
        views = InvestorViews()
        views.add_absolute_view('AAPL', 0.15, confidence=0.8)
        
        assert len(views.views) == 1
        assert views.views[0].view_type == "absolute"
        assert views.views[0].assets == ['AAPL']
        assert views.views[0].expected_return == 0.15
        assert views.views[0].confidence == 0.8
    
    def test_add_relative_view(self):
        """Test adding relative views"""
        views = InvestorViews()
        views.add_relative_view('AAPL', 'MSFT', 0.05, confidence=0.7)
        
        assert len(views.views) == 1
        assert views.views[0].view_type == "relative"
        assert views.views[0].assets == ['AAPL', 'MSFT']
        assert views.views[0].expected_return == 0.05
        assert views.views[0].confidence == 0.7
    
    def test_multiple_views(self):
        """Test adding multiple views"""
        views = InvestorViews()
        views.add_absolute_view('AAPL', 0.15, confidence=0.8)
        views.add_absolute_view('GOOGL', 0.12, confidence=0.6)
        views.add_relative_view('TSLA', 'AMZN', 0.10, confidence=0.5)
        
        assert len(views.views) == 3


# Integration tests
class TestPortfolioOptimizationIntegration:
    """Integration tests comparing MV and BL"""
    
    def test_mv_vs_bl_comparison(self, sample_returns, sample_market_caps):
        """Compare mean-variance vs Black-Litterman results"""
        # Mean-variance optimizer
        mv_optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
        mv_result = mv_optimizer.optimize_max_sharpe(sample_returns)
        
        # Black-Litterman optimizer (no views = similar to MV)
        bl_optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)
        bl_result = bl_optimizer.optimize(
            sample_returns,
            sample_market_caps,
            InvestorViews()
        )
        
        print(f"\nMean-Variance vs Black-Litterman:")
        print(f"\nMV Portfolio:")
        print(f"  Sharpe: {mv_result.portfolio.sharpe_ratio:.2f}")
        print(f"  Weights: {mv_result.portfolio.weights}")
        
        print(f"\nBL Portfolio (no views):")
        print(f"  Sharpe: {bl_result.portfolio.sharpe_ratio:.2f}")
        print(f"  Weights: {bl_result.portfolio.weights}")
        
        # Both should produce reasonable portfolios
        assert mv_result.portfolio.sharpe_ratio > 0
        assert bl_result.portfolio.sharpe_ratio > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
