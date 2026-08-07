# Analytics Module

Institutional-grade financial analytics for the StockIQ platform.

## Overview

The analytics module provides advanced quantitative analysis tools used by institutional traders and analysts. This includes options Greeks, risk metrics, factor analysis, and portfolio optimization.

## Modules

### Options Analytics (`stockiq.analytics.options`)

Comprehensive options analysis using the Black-Scholes-Merton model.

**Key Features:**
- **Greeks Calculation**: Delta, Gamma, Theta, Vega, Rho
- **Implied Volatility**: Reverse-engineer volatility from market prices
- **Volatility Surfaces**: 2D IV grids across strikes and expirations
- **Dividend Support**: Full support for dividend-paying stocks

**Usage Example:**

```python
from datetime import date, timedelta
from stockiq.analytics.options.greeks import OptionsAnalyzer, OptionContract

# Initialize analyzer
analyzer = OptionsAnalyzer()

# Create option contract
option = OptionContract(
    ticker='AAPL',
    strike=150.0,
    expiration=date.today() + timedelta(days=30),
    option_type='call',
    underlying_price=155.0,
    risk_free_rate=0.05,
    dividend_yield=0.005,
    market_price=7.50
)

# Calculate Greeks
greeks = analyzer.calculate_greeks(option, volatility=0.25)
print(f"Delta: {greeks.delta:.4f}")
print(f"Gamma: {greeks.gamma:.4f}")
print(f"Theta: {greeks.theta:.4f}")
print(f"Vega: {greeks.vega:.4f}")
print(f"Rho: {greeks.rho:.4f}")

# Calculate implied volatility
iv = analyzer.calculate_implied_volatility(option)
print(f"Implied Volatility: {iv:.2%}")

# Generate volatility surface (from options chain)
surface = analyzer.generate_volatility_surface('AAPL', options_chain)
print(f"Surface shape: {surface.implied_vols.shape}")
```

### Risk Analytics (`stockiq.analytics.risk`) - Coming Soon

Risk measurement and management tools.

**Planned Features:**
- Value at Risk (VaR) calculation
- Conditional Value at Risk (CVaR)
- Risk ratios (Sharpe, Sortino, Calmar)
- Stress testing and scenario analysis

### Factor Analysis (`stockiq.analytics.factors`) - Coming Soon

Multi-factor models for return attribution and risk analysis.

**Planned Features:**
- Fama-French 5-factor model
- Momentum, quality, and value factor exposures
- Custom factor construction
- Factor return decomposition

### Portfolio Optimization (`stockiq.analytics.portfolio`) ✅

Modern portfolio theory optimization algorithms.

**Implemented Features:**
- **Mean-Variance Optimization**: Markowitz optimization using quadratic programming
  - Maximum Sharpe ratio portfolios
  - Minimum variance portfolios
  - Efficient frontier generation
  - Customizable constraints (weight limits, target returns)
- **Black-Litterman Model**: Combines market equilibrium with investor views
  - Absolute views (e.g., "AAPL will return 15%")
  - Relative views (e.g., "AAPL will outperform MSFT by 5%")
  - Confidence-weighted Bayesian updating
  - Sensitivity analysis on uncertainty parameters

**Usage Example:**

```python
from stockiq.analytics.portfolio.mean_variance import MeanVarianceOptimizer
from stockiq.analytics.portfolio.black_litterman import (
    BlackLittermanOptimizer,
    InvestorViews,
)

# Mean-Variance Optimization
mv_optimizer = MeanVarianceOptimizer(risk_free_rate=0.02)

# Maximize Sharpe ratio
result = mv_optimizer.optimize_max_sharpe(returns_df)
print(f"Optimal weights: {result.portfolio.weights}")
print(f"Expected return: {result.portfolio.expected_return:.2%}")
print(f"Sharpe ratio: {result.portfolio.sharpe_ratio:.2f}")

# Generate efficient frontier
frontier = mv_optimizer.generate_efficient_frontier(returns_df, num_points=50)

# Black-Litterman Optimization
bl_optimizer = BlackLittermanOptimizer(risk_free_rate=0.02)

# Add investor views
views = InvestorViews()
views.add_absolute_view('AAPL', expected_return=0.15, confidence=0.8)
views.add_relative_view('TSLA', 'AMZN', expected_outperformance=0.05, confidence=0.6)

# Optimize with views
bl_result = bl_optimizer.optimize(returns_df, market_caps, views)
print(f"BL weights: {bl_result.portfolio.weights}")

# Compare equilibrium vs posterior returns
comparison = bl_optimizer.compare_equilibrium_vs_posterior(bl_result)
print(comparison)
```

## Technical Details

### Dependencies

- **numpy**: Array operations and mathematical functions
- **scipy**: Statistical functions and numerical optimization
- **dataclasses**: Type-safe data structures
- **logging**: Error and warning tracking

### Design Principles

1. **Mathematical Rigor**: All calculations verified against academic literature
2. **Numerical Stability**: Robust algorithms that handle edge cases gracefully
3. **Performance**: Efficient numpy operations suitable for real-time use
4. **Type Safety**: Full type hints and dataclass validation
5. **Testability**: Comprehensive test coverage with property-based testing

### Testing

Run all analytics tests:
```bash
pytest tests/test_options_greeks.py -v
```

Run with coverage:
```bash
pytest tests/test_options_greeks.py --cov=stockiq.analytics --cov-report=html
```

### Demo Scripts

Explore the analytics capabilities with interactive demos:
```bash
python examples/options_greeks_demo.py
```

## Architecture

```
stockiq/analytics/
├── __init__.py                 # Module exports
├── README.md                   # This file
├── options/                    # Options analytics
│   ├── __init__.py
│   └── greeks.py              # Greeks and IV calculation
├── risk/                       # Risk metrics (planned)
│   ├── __init__.py
│   ├── var.py
│   ├── cvar.py
│   └── ratios.py
├── factors/                    # Factor analysis (planned)
│   ├── __init__.py
│   ├── fama_french.py
│   ├── momentum.py
│   └── quality.py
└── portfolio/                  # Portfolio optimization (planned)
    ├── __init__.py
    ├── mean_variance.py
    └── black_litterman.py
```

## Requirements Satisfied

### Requirement 14.1: Calculate Options Greeks ✅
- Delta: Rate of change w.r.t. underlying price
- Gamma: Rate of change of delta w.r.t. underlying price
- Theta: Time decay (per-day basis)
- Vega: Sensitivity to volatility (per 1% change)
- Rho: Sensitivity to interest rate (per 1% change)

### Requirement 14.2: Compute Implied Volatility Surfaces ✅
- Brent's method for robust IV calculation
- 2D surfaces across strikes and expirations
- Linear interpolation for missing values
- Validation and error handling

## Future Enhancements

1. **American Options**: Binomial tree or finite difference methods
2. **Higher-Order Greeks**: Vanna, volga, charm, veta
3. **Alternative IV Models**: SABR, SVI, Heston stochastic volatility
4. **Options Strategies**: Pre-built strategy analysis (spreads, straddles)
5. **Real-Time Greeks**: Streaming Greeks via WebSocket
6. **Historical Storage**: TimescaleDB integration for IV history
7. **Visualization**: 3D volatility surface plots
8. **Greeks-Based Hedging**: Delta-neutral portfolio construction

## References

- Black, F., & Scholes, M. (1973). "The Pricing of Options and Corporate Liabilities"
- Merton, R. C. (1973). "Theory of Rational Option Pricing"
- Hull, J. C. (2018). "Options, Futures, and Other Derivatives" (10th ed.)
- Gatheral, J. (2006). "The Volatility Surface: A Practitioner's Guide"

## Support

For questions or issues related to the analytics module:
1. Check the test files for usage examples
2. Run the demo scripts to see the features in action
3. Review the inline documentation in the source code
4. Open an issue on the project repository

## License

This module is part of the StockIQ platform and follows the same license.
