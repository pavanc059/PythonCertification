# Task Completion: Implement FactorAnalyzer in `stockiq/analytics/factors/`

**Status:** Completed ✅  
**Date:** 2025-06-19

## Task Overview

Implemented institutional-grade factor analysis engine with Fama-French 5-factor model, momentum/quality/value factor exposures, and cointegration testing for pairs trading strategies.

## Files Created

1. **`stockiq/analytics/factors/__init__.py`** — Module initialization with exports
2. **`stockiq/analytics/factors/factor_analyzer.py`** — Full implementation of FactorAnalyzer class (700+ lines)
3. **`tests/test_factor_analyzer.py`** — Comprehensive test suite with 30 test cases

## Files Modified

1. **`stockiq/analytics/__init__.py`** — Added factor analysis exports to analytics module
2. **`requirements.txt`** — Added statsmodels>=0.14.0 dependency for cointegration testing

## What Was Implemented

### 1. Fama-French 5-Factor Model (Requirement 14.6)

- **`calculate_factor_exposures()`**: OLS regression to calculate factor betas
  - Market factor (Mkt-RF): Market risk premium exposure
  - SMB (Small Minus Big): Size factor exposure
  - HML (High Minus Low): Value factor exposure  
  - RMW (Robust Minus Weak): Profitability factor exposure
  - CMA (Conservative Minus Aggressive): Investment factor exposure
  - Alpha: Intercept term (risk-adjusted excess return)
  - R-squared: Model fit quality

- **`calculate_factor_returns()`**: Factor return attribution
  - Decomposes portfolio returns into contributions from each factor
  - Supports 1M, 3M, and 1Y periods
  - Calculates factor contributions: beta × factor_return

- **`generate_synthetic_factor_returns()`**: Synthetic factor data for testing/demo
  - Generates realistic factor returns based on historical distributions
  - Useful for development and testing without external data sources

### 2. Factor Exposures (Requirement 14.7)

- **`calculate_momentum_exposure()`**: Momentum factor analysis
  - Calculates cumulative return over lookback period (default: 252 days)
  - Positive values indicate upward momentum, negative indicate downward momentum

- **`calculate_quality_exposure()`**: Quality factor scoring
  - Composite score based on:
    - Profitability: ROE and ROA metrics
    - Financial safety: Debt-to-equity ratio
    - Earnings stability: Volatility of earnings
  - Returns normalized score [0, 1], higher = better quality

- **`calculate_value_exposure()`**: Value factor scoring
  - Based on valuation ratios:
    - Price-to-Book ratio (P/B)
    - Price-to-Earnings ratio (P/E)
  - Returns score [0, 1], higher = more value-oriented (vs. growth)

### 3. Cointegration Testing (Requirement 14.9)

- **`test_cointegration_engle_granger()`**: Engle-Granger two-step method
  - Step 1: OLS regression to find hedge ratio
  - Step 2: ADF test on spread for stationarity
  - Returns: is_cointegrated, hedge_ratio, spread statistics, half-life of mean reversion
  - Use case: Identify pairs trading opportunities

- **`test_cointegration_johansen()`**: Johansen multivariate test
  - Tests for cointegration using trace statistic
  - Extracts cointegrating vector (hedge ratio) from eigenvector
  - More powerful than Engle-Granger for multiple time series
  - Returns: is_cointegrated, hedge_ratio, spread statistics

- **`_calculate_half_life()`**: Mean reversion speed
  - Fits AR(1) model to spread
  - Calculates half-life: time for spread to revert halfway to mean
  - Useful for pairs trading position sizing and timing

### 4. Data Classes

- **`FactorExposures`**: Factor beta coefficients with metadata
- **`FactorReturns`**: Factor-attributed return decomposition
- **`CointegrationResult`**: Complete cointegration test results

## Tests Written

**File:** `tests/test_factor_analyzer.py`  
**Total Tests:** 30/30 passed ✅

### Test Coverage:

1. **Factor Exposures (8 tests)**
   - Basic factor exposure calculation
   - Momentum and quality factor inclusion
   - Insufficient data error handling
   - to_dict() serialization

2. **Factor Returns (3 tests)**
   - 1-month, 3-month, and 1-year period calculations
   - Factor contribution decomposition

3. **Cointegration - Engle-Granger (6 tests)**
   - Cointegrated series detection
   - Non-cointegrated series rejection
   - Hedge ratio calculation accuracy
   - Spread statistics (mean, std)
   - Half-life calculation
   - Insufficient data error handling

4. **Cointegration - Johansen (4 tests)**
   - Cointegrated series detection
   - Non-cointegrated series rejection
   - Spread statistics
   - Insufficient data error handling

5. **Momentum Exposure (3 tests)**
   - Positive momentum (upward trend)
   - Negative momentum (downward trend)
   - Insufficient data handling

6. **Quality Exposure (3 tests)**
   - High-quality stock metrics
   - Low-quality stock metrics
   - Missing data handling

7. **Value Exposure (3 tests)**
   - Value stock valuation
   - Growth stock valuation
   - Invalid price handling

8. **Synthetic Factor Generation (3 tests)**
   - Full factor generation
   - Selective factor exclusion (momentum, quality)

## Requirements Satisfied

- **Requirement 14.6**: ✅ Fama-French 5-factor model analysis
  - OLS regression for factor exposures
  - Return attribution by factor
  - Alpha calculation (risk-adjusted excess return)

- **Requirement 14.7**: ✅ Momentum, quality, and value factor exposures
  - Momentum: cumulative return over lookback period
  - Quality: composite score from profitability, leverage, stability
  - Value: score from P/B and P/E ratios

- **Requirement 14.9**: ✅ Cointegration testing using Engle-Granger and Johansen tests
  - Both methods implemented and tested
  - Hedge ratio calculation for pairs trading
  - Spread stationarity testing (ADF)
  - Half-life calculation for mean reversion timing

## Technical Details

### Dependencies Added
- **statsmodels>=0.14.0**: Time series analysis and cointegration testing
  - `adfuller`: Augmented Dickey-Fuller test for stationarity
  - `coint_johansen`: Johansen cointegration test

### Key Algorithms

1. **OLS Regression**: NumPy's `lstsq()` for least squares regression
2. **ADF Test**: Statsmodels' `adfuller()` for spread stationarity
3. **Johansen Test**: Statsmodels' `coint_johansen()` for multivariate cointegration
4. **Half-Life Calculation**: AR(1) model fitting with half-life = -log(2) / log(b)

### Performance Considerations

- Minimum data requirements:
  - Factor exposures: 60 days (for reliable regression)
  - Cointegration tests: 50 days (for statistical power)
- All calculations use NumPy vectorization for speed
- Type safety with dataclasses and proper type hints
- Graceful error handling with informative messages

## Integration Points

The FactorAnalyzer can be used by:
- Portfolio optimization module (risk factor decomposition)
- Risk analytics (factor-based VaR)
- Trading strategy module (pairs trading signals)
- Backtesting engine (factor-based strategy evaluation)
- Daily intelligence dashboard (factor exposure display)

## Usage Example

```python
from stockiq.analytics.factors import FactorAnalyzer
import pandas as pd

# Initialize analyzer
analyzer = FactorAnalyzer(risk_free_rate=0.02)

# Calculate factor exposures
returns = pd.Series(...)  # Security returns
factor_returns = pd.DataFrame(...)  # Fama-French factors

exposures = analyzer.calculate_factor_exposures(
    returns, 
    factor_returns, 
    ticker='AAPL'
)

print(f"Market beta: {exposures.market:.2f}")
print(f"Value tilt (HML): {exposures.hml:.2f}")
print(f"Alpha: {exposures.alpha:.4f}")
print(f"R-squared: {exposures.r_squared:.2f}")

# Test cointegration for pairs trading
price1 = pd.Series(...)  # Stock A prices
price2 = pd.Series(...)  # Stock B prices

result = analyzer.test_cointegration_engle_granger(
    price1, 
    price2, 
    ticker1='AAPL', 
    ticker2='MSFT'
)

if result.is_cointegrated:
    print(f"Pair is cointegrated!")
    print(f"Hedge ratio: {result.hedge_ratio:.2f}")
    print(f"Half-life: {result.half_life:.1f} days")
```

## Notes

1. **Production Data Sources**: The implementation includes a synthetic factor generator for testing. In production, factor data should be obtained from:
   - Kenneth French's data library (http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
   - Bloomberg/FactSet APIs
   - Alternative data providers

2. **Factor Model Extensions**: The architecture supports extending beyond Fama-French 5 factors:
   - Momentum factor (MOM) already supported
   - Quality factor (QMJ) already supported
   - Custom factors can be added via `_calculate_single_factor_exposure()`

3. **Cointegration Interpretation**:
   - Engle-Granger: Best for testing pairs (2 securities)
   - Johansen: Can handle multiple securities (portfolios)
   - Half-life < 30 days: Good for pairs trading
   - Half-life > 100 days: Too slow for practical trading

4. **Statistical Significance**: The implementation uses:
   - 5% significance level for cointegration tests
   - Engle-Granger critical value: -3.34 (more stringent than standard ADF)
   - Johansen critical values: from statsmodels lookup tables

## Follow-Up Tasks

- [ ] Integrate with real Fama-French data source
- [ ] Add factor model visualization (factor exposure charts)
- [ ] Implement factor timing strategies
- [ ] Add rolling window factor analysis
- [ ] Create factor-based portfolio construction module
