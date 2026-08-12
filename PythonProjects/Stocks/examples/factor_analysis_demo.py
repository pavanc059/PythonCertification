"""
Factor Analysis Demonstration

Shows how to use the FactorAnalyzer for:
1. Fama-French 5-factor model analysis
2. Momentum, quality, and value factor exposures
3. Cointegration testing for pairs trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from stockiq.analytics.factors import FactorAnalyzer

def demo_factor_exposures():
    """Demonstrate factor exposure calculation."""
    print("=" * 80)
    print("DEMO 1: Fama-French 5-Factor Exposures")
    print("=" * 80)
    
    # Initialize analyzer
    analyzer = FactorAnalyzer(risk_free_rate=0.02)
    
    # Generate synthetic data
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    # Generate factor returns
    factor_returns = analyzer.generate_synthetic_factor_returns(
        start_date, 
        end_date,
        include_momentum=True,
        include_quality=True
    )
    
    # Generate synthetic security returns with known exposures
    # Let's create a "growth stock" with high market beta, negative value (HML)
    np.random.seed(42)
    market_beta = 1.3
    smb_beta = -0.5  # Large cap
    hml_beta = -0.8  # Growth (low value)
    rmw_beta = 0.2   # Medium profitability
    cma_beta = -0.3  # Aggressive investment
    
    security_returns = (
        0.0001 +  # Small alpha
        market_beta * factor_returns['Mkt-RF'] +
        smb_beta * factor_returns['SMB'] +
        hml_beta * factor_returns['HML'] +
        rmw_beta * factor_returns['RMW'] +
        cma_beta * factor_returns['CMA'] +
        np.random.normal(0, 0.01, len(factor_returns))  # Idiosyncratic risk
    )
    security_returns.name = 'TECH_STOCK'
    
    # Calculate factor exposures
    exposures = analyzer.calculate_factor_exposures(
        security_returns,
        factor_returns,
        ticker='TECH_STOCK'
    )
    
    print(f"\n📊 Factor Exposures for TECH_STOCK:")
    print(f"   Market (β):        {exposures.market:>7.3f}  (Expected: ~1.30)")
    print(f"   Size (SMB):        {exposures.smb:>7.3f}  (Expected: ~-0.50, Large cap)")
    print(f"   Value (HML):       {exposures.hml:>7.3f}  (Expected: ~-0.80, Growth)")
    print(f"   Profitability:     {exposures.rmw:>7.3f}  (Expected: ~0.20)")
    print(f"   Investment (CMA):  {exposures.cma:>7.3f}  (Expected: ~-0.30)")
    print(f"   Momentum (MOM):    {exposures.momentum:>7.3f}")
    print(f"   Quality (QMJ):     {exposures.quality:>7.3f}")
    print(f"   Alpha:             {exposures.alpha:>7.5f}  (Excess return)")
    print(f"   R-squared:         {exposures.r_squared:>7.1%}  (Model fit)")
    
    # Calculate factor returns
    factor_contribution = analyzer.calculate_factor_returns(
        exposures,
        factor_returns,
        period='1M'
    )
    
    print(f"\n📈 1-Month Factor Return Attribution:")
    print(f"   Total Return:      {factor_contribution.total_return:>7.2%}")
    print(f"   Market:            {factor_contribution.market_contribution:>7.2%}")
    print(f"   Size:              {factor_contribution.smb_contribution:>7.2%}")
    print(f"   Value:             {factor_contribution.hml_contribution:>7.2%}")
    print(f"   Profitability:     {factor_contribution.rmw_contribution:>7.2%}")
    print(f"   Investment:        {factor_contribution.cma_contribution:>7.2%}")
    print(f"   Alpha:             {factor_contribution.alpha_contribution:>7.2%}")
    
    print("\n✅ Interpretation:")
    print("   • High market beta (>1.0): Stock amplifies market movements")
    print("   • Negative HML: Growth stock (trades at high P/B, P/E)")
    print("   • Negative SMB: Large-cap stock")
    print("   • R-squared shows % of variance explained by factors")


def demo_momentum_quality_value():
    """Demonstrate momentum, quality, and value factor calculations."""
    print("\n" + "=" * 80)
    print("DEMO 2: Momentum, Quality, and Value Exposures")
    print("=" * 80)
    
    analyzer = FactorAnalyzer()
    
    # Momentum example
    print("\n📊 Momentum Analysis:")
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
    
    # Upward trending stock
    uptrend_prices = pd.Series(np.linspace(100, 150, len(dates)), index=dates)
    momentum_up = analyzer.calculate_momentum_exposure(uptrend_prices, lookback_period=252)
    
    # Downward trending stock
    downtrend_prices = pd.Series(np.linspace(150, 100, len(dates)), index=dates)
    momentum_down = analyzer.calculate_momentum_exposure(downtrend_prices, lookback_period=252)
    
    print(f"   Strong Uptrend:    {momentum_up:>7.1%}  (Positive momentum)")
    print(f"   Strong Downtrend:  {momentum_down:>7.1%}  (Negative momentum)")
    
    # Quality example
    print("\n📊 Quality Factor Analysis:")
    
    high_quality = {
        'roe': 0.22,  # 22% ROE
        'roa': 0.10,  # 10% ROA
        'debt_to_equity': 0.2,  # Low leverage
        'earnings_stability': 0.95,  # Very stable
    }
    quality_score_high = analyzer.calculate_quality_exposure(high_quality)
    
    low_quality = {
        'roe': 0.03,  # 3% ROE
        'roa': 0.01,  # 1% ROA
        'debt_to_equity': 3.0,  # High leverage
        'earnings_stability': 0.3,  # Unstable
    }
    quality_score_low = analyzer.calculate_quality_exposure(low_quality)
    
    print(f"   High Quality Stock:  {quality_score_high:>5.1%}")
    print(f"     • ROE: 22%, ROA: 10%, Debt/Equity: 0.2")
    print(f"   Low Quality Stock:   {quality_score_low:>5.1%}")
    print(f"     • ROE: 3%, ROA: 1%, Debt/Equity: 3.0")
    
    # Value example
    print("\n📊 Value vs Growth Analysis:")
    
    value_score = analyzer.calculate_value_exposure(
        price=50.0,
        book_value_per_share=45.0,  # P/B = 1.11
        earnings_per_share=5.0       # P/E = 10
    )
    
    growth_score = analyzer.calculate_value_exposure(
        price=100.0,
        book_value_per_share=10.0,   # P/B = 10
        earnings_per_share=2.0        # P/E = 50
    )
    
    print(f"   Value Stock:         {value_score:>5.1%}  (P/B=1.1, P/E=10)")
    print(f"   Growth Stock:        {growth_score:>5.1%}  (P/B=10, P/E=50)")
    
    print("\n✅ Interpretation:")
    print("   • Momentum > 0: Price trending up (buy momentum)")
    print("   • Quality > 0.7: Strong profitability and stability")
    print("   • Value > 0.5: Trading at reasonable valuations")


def demo_cointegration():
    """Demonstrate cointegration testing for pairs trading."""
    print("\n" + "=" * 80)
    print("DEMO 3: Cointegration Testing (Pairs Trading)")
    print("=" * 80)
    
    analyzer = FactorAnalyzer()
    
    # Generate cointegrated price series
    print("\n📊 Testing Cointegrated Pair:")
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
    
    # Create cointegrated series (share common stochastic trend)
    common_trend = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
    noise1 = np.random.normal(0, 2, len(dates))
    noise2 = np.random.normal(0, 2, len(dates))
    
    price1 = common_trend + noise1
    price2 = 2 * common_trend + noise2  # Related by factor of 2
    
    series1 = pd.Series(price1, index=dates, name='STOCK_A')
    series2 = pd.Series(price2, index=dates, name='STOCK_B')
    
    # Test with Engle-Granger
    result_eg = analyzer.test_cointegration_engle_granger(
        series1, series2, 
        ticker1='STOCK_A', 
        ticker2='STOCK_B'
    )
    
    print(f"   Method: Engle-Granger")
    print(f"   Cointegrated:        {'✅ YES' if result_eg.is_cointegrated else '❌ NO'}")
    print(f"   Test Statistic:      {result_eg.test_statistic:>7.3f}")
    print(f"   Critical Value (5%): {result_eg.critical_value:>7.3f}")
    print(f"   P-value:             {result_eg.p_value:>7.5f}")
    print(f"   Hedge Ratio:         {result_eg.hedge_ratio:>7.3f}")
    print(f"   Half-Life:           {result_eg.half_life:>7.1f} days" if result_eg.half_life else "   Half-Life:           N/A")
    print(f"   Spread Std Dev:      {result_eg.spread_std:>7.3f}")
    
    # Test with Johansen
    result_jh = analyzer.test_cointegration_johansen(
        series1, series2,
        ticker1='STOCK_A',
        ticker2='STOCK_B'
    )
    
    print(f"\n   Method: Johansen")
    print(f"   Cointegrated:        {'✅ YES' if result_jh.is_cointegrated else '❌ NO'}")
    print(f"   Trace Statistic:     {result_jh.test_statistic:>7.3f}")
    print(f"   Critical Value (5%): {result_jh.critical_value:>7.3f}")
    print(f"   Hedge Ratio:         {result_jh.hedge_ratio:>7.3f}")
    
    # Test non-cointegrated pair
    print("\n📊 Testing Non-Cointegrated Pair:")
    price3 = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
    price4 = np.cumsum(np.random.normal(0, 1, len(dates))) + 100
    
    series3 = pd.Series(price3, index=dates, name='STOCK_C')
    series4 = pd.Series(price4, index=dates, name='STOCK_D')
    
    result_no_coint = analyzer.test_cointegration_engle_granger(
        series3, series4,
        ticker1='STOCK_C',
        ticker2='STOCK_D'
    )
    
    print(f"   Method: Engle-Granger")
    print(f"   Cointegrated:        {'✅ YES' if result_no_coint.is_cointegrated else '❌ NO'}")
    print(f"   Test Statistic:      {result_no_coint.test_statistic:>7.3f}")
    print(f"   P-value:             {result_no_coint.p_value:>7.5f}")
    
    print("\n✅ Interpretation:")
    print("   • Cointegrated pairs: Mean-reverting spread (pairs trading opportunity)")
    print("   • Hedge ratio: Position size ratio (e.g., 0.5 means short 1:long 2)")
    print("   • Half-life < 30 days: Good for short-term pairs trading")
    print("   • Half-life > 100 days: Too slow for practical trading")


if __name__ == '__main__':
    print("\n" + "🔬" * 40)
    print("FACTOR ANALYSIS DEMONSTRATIONS")
    print("🔬" * 40)
    
    try:
        demo_factor_exposures()
        demo_momentum_quality_value()
        demo_cointegration()
        
        print("\n" + "=" * 80)
        print("✅ All demonstrations completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
