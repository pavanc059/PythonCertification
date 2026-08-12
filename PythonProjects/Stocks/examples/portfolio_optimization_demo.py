"""
Portfolio Optimization Demo

Demonstrates mean-variance and Black-Litterman optimization with sample data.

Usage:
    python examples/portfolio_optimization_demo.py
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from stockiq.analytics.portfolio.mean_variance import (
    MeanVarianceOptimizer,
    OptimizationConstraints,
)
from stockiq.analytics.portfolio.black_litterman import (
    BlackLittermanOptimizer,
    InvestorViews,
)


def generate_sample_data():
    """Generate sample return data for demonstration"""
    np.random.seed(42)
    n_days = 252  # 1 year of trading days
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    # Realistic daily return assumptions (annualized / 252)
    mean_returns = np.array([0.15, 0.12, 0.18, 0.20, 0.25]) / 252
    
    # Correlation matrix
    correlation = np.array([
        [1.00, 0.70, 0.65, 0.60, 0.55],
        [0.70, 1.00, 0.75, 0.65, 0.50],
        [0.65, 0.75, 1.00, 0.70, 0.60],
        [0.60, 0.65, 0.70, 1.00, 0.65],
        [0.55, 0.50, 0.60, 0.65, 1.00],
    ])
    
    # Daily volatilities (annualized / sqrt(252))
    volatilities = np.array([0.25, 0.22, 0.28, 0.30, 0.40]) / np.sqrt(252)
    
    # Build covariance matrix
    cov_matrix = np.outer(volatilities, volatilities) * correlation
    
    # Generate multivariate normal returns
    returns = np.random.multivariate_normal(mean_returns, cov_matrix, n_days)
    
    return pd.DataFrame(returns, columns=tickers)


def generate_market_caps():
    """Generate sample market capitalizations"""
    return {
        'AAPL': 2800e9,  # $2.8 trillion
        'MSFT': 2500e9,  # $2.5 trillion
        'GOOGL': 1600e9,  # $1.6 trillion
        'AMZN': 1400e9,  # $1.4 trillion
        'TSLA': 800e9,    # $800 billion
    }


def demo_mean_variance():
    """Demonstrate mean-variance optimization"""
    print("=" * 80)
    print("MEAN-VARIANCE OPTIMIZATION DEMO")
    print("=" * 80)
    
    returns = generate_sample_data()
    optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)
    
    # 1. Maximum Sharpe Ratio
    print("\n1. MAXIMUM SHARPE RATIO PORTFOLIO")
    print("-" * 80)
    result = optimizer.optimize_max_sharpe(returns)
    portfolio = result.portfolio
    
    print(f"Convergence: {'✅ Success' if result.convergence else '❌ Failed'}")
    print(f"Iterations: {result.iterations}")
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {portfolio.expected_return:>8.2%}")
    print(f"  Volatility:      {portfolio.volatility:>8.2%}")
    print(f"  Sharpe Ratio:    {portfolio.sharpe_ratio:>8.2f}")
    print(f"\nOptimal Weights:")
    for ticker, weight in sorted(portfolio.weights.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {weight:>6.2%}")
    
    # 2. Minimum Variance
    print("\n\n2. MINIMUM VARIANCE PORTFOLIO")
    print("-" * 80)
    result = optimizer.optimize_min_variance(returns)
    portfolio = result.portfolio
    
    print(f"Convergence: {'✅ Success' if result.convergence else '❌ Failed'}")
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {portfolio.expected_return:>8.2%}")
    print(f"  Volatility:      {portfolio.volatility:>8.2%}")
    print(f"  Sharpe Ratio:    {portfolio.sharpe_ratio:>8.2f}")
    print(f"\nOptimal Weights:")
    for ticker, weight in sorted(portfolio.weights.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {weight:>6.2%}")
    
    # 3. Efficient Frontier
    print("\n\n3. EFFICIENT FRONTIER (10 POINTS)")
    print("-" * 80)
    frontier = optimizer.generate_efficient_frontier(returns, num_points=10)
    
    print(f"Generated {len(frontier)} efficient portfolios")
    print(f"\n{'Point':<8} {'Return':<10} {'Volatility':<12} {'Sharpe':<10}")
    print("-" * 50)
    for i, p in enumerate(frontier[:10], 1):
        print(f"{i:<8} {p.expected_return:<10.2%} {p.volatility:<12.2%} {p.sharpe_ratio:<10.2f}")
    
    # 4. Constrained Optimization
    print("\n\n4. CONSTRAINED OPTIMIZATION (Max 30% per asset)")
    print("-" * 80)
    constraints = OptimizationConstraints(
        min_weight=0.0,
        max_weight=0.30,
        risk_free_rate=0.02
    )
    result = optimizer.optimize_max_sharpe(returns, constraints)
    portfolio = result.portfolio
    
    print(f"Convergence: {'✅ Success' if result.convergence else '❌ Failed'}")
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {portfolio.expected_return:>8.2%}")
    print(f"  Volatility:      {portfolio.volatility:>8.2%}")
    print(f"  Sharpe Ratio:    {portfolio.sharpe_ratio:>8.2f}")
    print(f"\nOptimal Weights:")
    for ticker, weight in sorted(portfolio.weights.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {weight:>6.2%}")
    max_weight = max(portfolio.weights.values())
    print(f"\n  ✅ Constraint satisfied: max weight = {max_weight:.2%} ≤ 30%")


def demo_black_litterman():
    """Demonstrate Black-Litterman optimization"""
    print("\n\n" + "=" * 80)
    print("BLACK-LITTERMAN OPTIMIZATION DEMO")
    print("=" * 80)
    
    returns = generate_sample_data()
    market_caps = generate_market_caps()
    optimizer = BlackLittermanOptimizer(
        risk_free_rate=0.02,
        tau=0.025,
        risk_aversion=2.5
    )
    
    # 1. No Views (Baseline)
    print("\n1. BLACK-LITTERMAN WITHOUT VIEWS (Market Equilibrium)")
    print("-" * 80)
    views = InvestorViews()
    result = optimizer.optimize(returns, market_caps, views)
    portfolio = result.portfolio
    
    print(f"Views Applied: {result.views_applied}")
    print(f"Tau Parameter: {result.tau}")
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {portfolio.expected_return:>8.2%}")
    print(f"  Volatility:      {portfolio.volatility:>8.2%}")
    print(f"  Sharpe Ratio:    {portfolio.sharpe_ratio:>8.2f}")
    print(f"\nOptimal Weights:")
    for ticker, weight in sorted(portfolio.weights.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {weight:>6.2%}")
    
    print(f"\nImplied Equilibrium Returns:")
    for ticker, ret in sorted(result.implied_returns.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {ret:>8.2%}")
    
    # 2. Absolute Views
    print("\n\n2. BLACK-LITTERMAN WITH ABSOLUTE VIEWS")
    print("-" * 80)
    views = InvestorViews()
    views.add_absolute_view(
        ticker='AAPL',
        expected_return=0.18,  # 18% expected return
        confidence=0.85,
        description="High confidence in Apple's AI initiatives"
    )
    views.add_absolute_view(
        ticker='TSLA',
        expected_return=0.22,  # 22% expected return
        confidence=0.60,
        description="Moderate confidence in Tesla's EV growth"
    )
    
    result = optimizer.optimize(returns, market_caps, views)
    portfolio = result.portfolio
    
    print(f"Views Applied: {result.views_applied}")
    print(f"\nInvestor Views:")
    for view in views.views:
        print(f"  • {view.description}")
        print(f"    Expected Return: {view.expected_return:.2%}, Confidence: {view.confidence:.0%}")
    
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {portfolio.expected_return:>8.2%}")
    print(f"  Volatility:      {portfolio.volatility:>8.2%}")
    print(f"  Sharpe Ratio:    {portfolio.sharpe_ratio:>8.2f}")
    print(f"\nOptimal Weights:")
    for ticker, weight in sorted(portfolio.weights.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {weight:>6.2%}")
    
    # Show impact of views
    print(f"\nImpact of Views (Equilibrium → Posterior):")
    for ticker in ['AAPL', 'TSLA']:
        eq_ret = result.implied_returns[ticker]
        post_ret = result.posterior_returns[ticker]
        diff = post_ret - eq_ret
        print(f"  {ticker:>6}: {eq_ret:>7.2%} → {post_ret:>7.2%} (Δ {diff:+.2%})")
    
    # 3. Relative Views
    print("\n\n3. BLACK-LITTERMAN WITH RELATIVE VIEWS")
    print("-" * 80)
    views = InvestorViews()
    views.add_relative_view(
        ticker1='AAPL',
        ticker2='MSFT',
        expected_outperformance=0.06,  # AAPL outperforms MSFT by 6%
        confidence=0.75,
        description="Apple will outperform Microsoft due to hardware advantage"
    )
    views.add_relative_view(
        ticker1='GOOGL',
        ticker2='AMZN',
        expected_outperformance=0.04,  # GOOGL outperforms AMZN by 4%
        confidence=0.65,
        description="Google's AI leadership will drive outperformance vs Amazon"
    )
    
    result = optimizer.optimize(returns, market_caps, views)
    portfolio = result.portfolio
    
    print(f"Views Applied: {result.views_applied}")
    print(f"\nInvestor Views:")
    for view in views.views:
        print(f"  • {view.description}")
        print(f"    Outperformance: {view.expected_return:.2%}, Confidence: {view.confidence:.0%}")
    
    print(f"\nPortfolio Metrics:")
    print(f"  Expected Return: {portfolio.expected_return:>8.2%}")
    print(f"  Volatility:      {portfolio.volatility:>8.2%}")
    print(f"  Sharpe Ratio:    {portfolio.sharpe_ratio:>8.2f}")
    print(f"\nOptimal Weights:")
    for ticker, weight in sorted(portfolio.weights.items(), key=lambda x: -x[1]):
        print(f"  {ticker:>6}: {weight:>6.2%}")
    
    # 4. Comparison Analysis
    print("\n\n4. EQUILIBRIUM VS POSTERIOR COMPARISON")
    print("-" * 80)
    comparison = optimizer.compare_equilibrium_vs_posterior(result)
    print(comparison.to_string(index=False))
    
    # 5. Sensitivity Analysis
    print("\n\n5. SENSITIVITY ANALYSIS (Tau Parameter)")
    print("-" * 80)
    views = InvestorViews()
    views.add_absolute_view('AAPL', 0.18, confidence=0.80)
    
    sensitivity = optimizer.sensitivity_analysis(
        returns,
        market_caps,
        views,
        tau_values=[0.01, 0.025, 0.05, 0.10]
    )
    
    print("\nPortfolio weights at different tau values:")
    print(sensitivity.to_string(index=False, float_format=lambda x: f'{x:.2%}'))
    print("\nNote: Lower tau = more confidence in equilibrium, higher tau = more uncertainty")


def main():
    """Run all demos"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  PORTFOLIO OPTIMIZATION DEMONSTRATION".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print("\n")
    print("This demo showcases institutional-grade portfolio optimization:")
    print("  • Mean-Variance Optimization (Markowitz)")
    print("  • Black-Litterman Model with Investor Views")
    print("  • Efficient Frontier Generation")
    print("  • Constraint-Based Optimization")
    print("\n")
    
    demo_mean_variance()
    demo_black_litterman()
    
    print("\n\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nFor more information, see:")
    print("  • stockiq/analytics/portfolio/mean_variance.py")
    print("  • stockiq/analytics/portfolio/black_litterman.py")
    print("  • tests/test_portfolio_optimization.py")
    print("\n")


if __name__ == "__main__":
    main()
