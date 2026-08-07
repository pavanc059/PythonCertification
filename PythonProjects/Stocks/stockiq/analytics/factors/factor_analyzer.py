"""
Factor Analysis Implementation

Provides Fama-French 5-factor model analysis, factor exposures calculation,
and cointegration testing for pairs trading strategies.

Requirements: 14.6, 14.7, 14.9
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
import warnings

# Suppress statsmodels warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='statsmodels')


@dataclass
class FactorExposures:
    """
    Factor exposures (betas) for a security or portfolio.
    
    Attributes:
        ticker: Security ticker
        market: Market factor exposure (Mkt-RF)
        smb: Size factor exposure (Small Minus Big)
        hml: Value factor exposure (High Minus Low)
        rmw: Profitability factor exposure (Robust Minus Weak)
        cma: Investment factor exposure (Conservative Minus Aggressive)
        momentum: Momentum factor exposure (optional)
        quality: Quality factor exposure (optional)
        alpha: Intercept (alpha) from regression
        r_squared: Model R-squared
        period_start: Start date of analysis period
        period_end: End date of analysis period
    """
    ticker: str
    market: float
    smb: float
    hml: float
    rmw: float
    cma: float
    momentum: Optional[float] = None
    quality: Optional[float] = None
    alpha: float = 0.0
    r_squared: float = 0.0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for easy serialization."""
        return {
            'ticker': self.ticker,
            'market': self.market,
            'smb': self.smb,
            'hml': self.hml,
            'rmw': self.rmw,
            'cma': self.cma,
            'momentum': self.momentum if self.momentum is not None else 0.0,
            'quality': self.quality if self.quality is not None else 0.0,
            'alpha': self.alpha,
            'r_squared': self.r_squared,
        }


@dataclass
class FactorReturns:
    """
    Factor-attributed returns decomposition.
    
    Attributes:
        total_return: Total portfolio return
        market_contribution: Return attributed to market factor
        smb_contribution: Return attributed to size factor
        hml_contribution: Return attributed to value factor
        rmw_contribution: Return attributed to profitability factor
        cma_contribution: Return attributed to investment factor
        momentum_contribution: Return attributed to momentum factor
        quality_contribution: Return attributed to quality factor
        alpha_contribution: Return attributed to alpha (unexplained)
        residual: Unexplained return
    """
    total_return: float
    market_contribution: float
    smb_contribution: float
    hml_contribution: float
    rmw_contribution: float
    cma_contribution: float
    momentum_contribution: float = 0.0
    quality_contribution: float = 0.0
    alpha_contribution: float = 0.0
    residual: float = 0.0


@dataclass
class CointegrationResult:
    """
    Cointegration test results for pairs trading.
    
    Attributes:
        ticker1: First security ticker
        ticker2: Second security ticker
        is_cointegrated: Whether the pair is cointegrated
        test_method: Test method used ('engle_granger' or 'johansen')
        test_statistic: Test statistic value
        p_value: P-value of the test
        critical_value: Critical value at 5% significance
        hedge_ratio: Optimal hedge ratio (beta from regression)
        half_life: Half-life of mean reversion in days
        spread_mean: Mean of the spread
        spread_std: Standard deviation of the spread
        adf_statistic: ADF test statistic for spread stationarity
        adf_p_value: ADF test p-value
    """
    ticker1: str
    ticker2: str
    is_cointegrated: bool
    test_method: str
    test_statistic: float
    p_value: float
    critical_value: float
    hedge_ratio: float
    half_life: Optional[float] = None
    spread_mean: float = 0.0
    spread_std: float = 0.0
    adf_statistic: Optional[float] = None
    adf_p_value: Optional[float] = None


class FactorAnalyzer:
    """
    Institutional-grade factor analysis engine.
    
    Implements:
    - Fama-French 5-factor model (Requirement 14.6)
    - Momentum, quality, and value factor exposures (Requirement 14.7)
    - Cointegration testing using Engle-Granger and Johansen methods (Requirement 14.9)
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize FactorAnalyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate for excess return calculations (default: 2%)
        """
        self.risk_free_rate = risk_free_rate
        self.daily_rf_rate = risk_free_rate / 252  # Convert annual to daily
        
    def calculate_factor_exposures(
        self,
        returns: pd.Series,
        factor_returns: pd.DataFrame,
        ticker: str = "Portfolio"
    ) -> FactorExposures:
        """
        Calculate Fama-French 5-factor exposures using regression.
        
        Requirement 14.6: Fama-French 5-factor model analysis
        Requirement 14.7: Calculate factor exposures
        
        Args:
            returns: Security or portfolio daily returns
            factor_returns: DataFrame with columns ['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA']
            ticker: Security ticker or portfolio name
            
        Returns:
            FactorExposures object with factor betas and statistics
        """
        # Align returns with factor returns
        aligned = pd.concat([returns, factor_returns], axis=1, join='inner')
        aligned = aligned.dropna()
        
        if len(aligned) < 60:  # Minimum 60 days for reliable regression
            raise ValueError(f"Insufficient data: {len(aligned)} days (minimum 60 required)")
        
        y = aligned.iloc[:, 0].values  # Security returns
        X = aligned[['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA']].values
        
        # Add intercept
        X = np.column_stack([np.ones(len(X)), X])
        
        # OLS regression: y = alpha + beta1*Mkt-RF + beta2*SMB + beta3*HML + beta4*RMW + beta5*CMA
        betas, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
        
        # Calculate R-squared
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        ss_res = np.sum(residuals) if len(residuals) > 0 else np.sum((y - X @ betas) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # Extract factor exposures
        alpha = betas[0]
        market_beta = betas[1]
        smb_beta = betas[2]
        hml_beta = betas[3]
        rmw_beta = betas[4]
        cma_beta = betas[5]
        
        # Calculate momentum and quality if possible
        momentum_beta = None
        quality_beta = None
        
        if 'MOM' in factor_returns.columns:
            momentum_beta = self._calculate_single_factor_exposure(returns, factor_returns['MOM'])
            
        if 'QMJ' in factor_returns.columns:
            quality_beta = self._calculate_single_factor_exposure(returns, factor_returns['QMJ'])
        
        return FactorExposures(
            ticker=ticker,
            market=market_beta,
            smb=smb_beta,
            hml=hml_beta,
            rmw=rmw_beta,
            cma=cma_beta,
            momentum=momentum_beta,
            quality=quality_beta,
            alpha=alpha,
            r_squared=r_squared,
            period_start=aligned.index[0] if hasattr(aligned.index[0], 'date') else None,
            period_end=aligned.index[-1] if hasattr(aligned.index[-1], 'date') else None,
        )
    
    def _calculate_single_factor_exposure(
        self,
        returns: pd.Series,
        factor: pd.Series
    ) -> float:
        """
        Calculate exposure to a single factor using simple regression.
        
        Args:
            returns: Security returns
            factor: Factor returns
            
        Returns:
            Factor beta (exposure)
        """
        aligned = pd.concat([returns, factor], axis=1, join='inner').dropna()
        
        if len(aligned) < 30:
            return 0.0
        
        y = aligned.iloc[:, 0].values
        X = aligned.iloc[:, 1].values
        
        # Simple linear regression
        X_with_intercept = np.column_stack([np.ones(len(X)), X])
        betas, _, _, _ = np.linalg.lstsq(X_with_intercept, y, rcond=None)
        
        return betas[1]  # Return slope (beta)
    
    def calculate_factor_returns(
        self,
        exposures: FactorExposures,
        factor_returns: pd.DataFrame,
        period: str = "1M"
    ) -> FactorReturns:
        """
        Decompose portfolio returns into factor contributions.
        
        Requirement 14.6: Factor return attribution
        
        Args:
            exposures: FactorExposures from calculate_factor_exposures()
            factor_returns: DataFrame with factor returns
            period: Period for return calculation ('1M', '3M', '1Y')
            
        Returns:
            FactorReturns with attribution to each factor
        """
        # Determine period
        if period == "1M":
            days = 21
        elif period == "3M":
            days = 63
        elif period == "1Y":
            days = 252
        else:
            days = 21
        
        # Get recent factor returns
        recent_factors = factor_returns.tail(days)
        
        if len(recent_factors) == 0:
            raise ValueError("No factor return data available")
        
        # Calculate cumulative factor returns
        mkt_return = recent_factors['Mkt-RF'].sum() if 'Mkt-RF' in recent_factors.columns else 0.0
        smb_return = recent_factors['SMB'].sum() if 'SMB' in recent_factors.columns else 0.0
        hml_return = recent_factors['HML'].sum() if 'HML' in recent_factors.columns else 0.0
        rmw_return = recent_factors['RMW'].sum() if 'RMW' in recent_factors.columns else 0.0
        cma_return = recent_factors['CMA'].sum() if 'CMA' in recent_factors.columns else 0.0
        mom_return = recent_factors['MOM'].sum() if 'MOM' in recent_factors.columns else 0.0
        qmj_return = recent_factors['QMJ'].sum() if 'QMJ' in recent_factors.columns else 0.0
        
        # Calculate factor contributions (beta * factor_return)
        market_contrib = exposures.market * mkt_return
        smb_contrib = exposures.smb * smb_return
        hml_contrib = exposures.hml * hml_return
        rmw_contrib = exposures.rmw * rmw_return
        cma_contrib = exposures.cma * cma_return
        mom_contrib = exposures.momentum * mom_return if exposures.momentum else 0.0
        qmj_contrib = exposures.quality * qmj_return if exposures.quality else 0.0
        alpha_contrib = exposures.alpha * days
        
        # Total return is sum of all contributions
        total_return = (
            market_contrib + smb_contrib + hml_contrib + 
            rmw_contrib + cma_contrib + mom_contrib + qmj_contrib + alpha_contrib
        )
        
        return FactorReturns(
            total_return=total_return,
            market_contribution=market_contrib,
            smb_contribution=smb_contrib,
            hml_contribution=hml_contrib,
            rmw_contribution=rmw_contrib,
            cma_contribution=cma_contrib,
            momentum_contribution=mom_contrib,
            quality_contribution=qmj_contrib,
            alpha_contribution=alpha_contrib,
            residual=0.0,
        )
    
    def test_cointegration_engle_granger(
        self,
        prices1: pd.Series,
        prices2: pd.Series,
        ticker1: str,
        ticker2: str,
        significance_level: float = 0.05
    ) -> CointegrationResult:
        """
        Test for cointegration using Engle-Granger two-step method.
        
        Requirement 14.9: Engle-Granger cointegration test
        
        Args:
            prices1: Price series for first security
            prices2: Price series for second security
            ticker1: Ticker for first security
            ticker2: Ticker for second security
            significance_level: Significance level for test (default: 0.05)
            
        Returns:
            CointegrationResult with test statistics and hedge ratio
        """
        # Align price series
        aligned = pd.concat([prices1, prices2], axis=1, join='inner').dropna()
        
        if len(aligned) < 50:
            raise ValueError(f"Insufficient data: {len(aligned)} days (minimum 50 required)")
        
        y = aligned.iloc[:, 0].values
        x = aligned.iloc[:, 1].values
        
        # Step 1: OLS regression to find hedge ratio
        X_with_intercept = np.column_stack([np.ones(len(x)), x])
        betas, _, _, _ = np.linalg.lstsq(X_with_intercept, y, rcond=None)
        hedge_ratio = betas[1]
        
        # Calculate spread
        spread = y - hedge_ratio * x - betas[0]
        
        # Step 2: Test spread for stationarity using ADF test
        adf_result = adfuller(spread, maxlag=1, regression='c', autolag='AIC')
        adf_stat = adf_result[0]
        adf_pval = adf_result[1]
        
        # Engle-Granger critical values (more stringent than standard ADF)
        # For 5% significance: -3.34 (approximate)
        critical_value_5pct = -3.34
        
        # Cointegrated if ADF statistic < critical value (more negative)
        is_cointegrated = bool(adf_stat < critical_value_5pct and adf_pval < significance_level)
        
        # Calculate half-life of mean reversion
        half_life = self._calculate_half_life(spread)
        
        # Calculate spread statistics
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        return CointegrationResult(
            ticker1=ticker1,
            ticker2=ticker2,
            is_cointegrated=is_cointegrated,
            test_method='engle_granger',
            test_statistic=adf_stat,
            p_value=adf_pval,
            critical_value=critical_value_5pct,
            hedge_ratio=hedge_ratio,
            half_life=half_life,
            spread_mean=spread_mean,
            spread_std=spread_std,
            adf_statistic=adf_stat,
            adf_p_value=adf_pval,
        )
    
    def test_cointegration_johansen(
        self,
        prices1: pd.Series,
        prices2: pd.Series,
        ticker1: str,
        ticker2: str,
        significance_level: int = 1  # 0=90%, 1=95%, 2=99%
    ) -> CointegrationResult:
        """
        Test for cointegration using Johansen test.
        
        Requirement 14.9: Johansen cointegration test
        
        Args:
            prices1: Price series for first security
            prices2: Price series for second security
            ticker1: Ticker for first security
            ticker2: Ticker for second security
            significance_level: Significance level index (0=90%, 1=95%, 2=99%)
            
        Returns:
            CointegrationResult with test statistics
        """
        # Align price series
        aligned = pd.concat([prices1, prices2], axis=1, join='inner').dropna()
        
        if len(aligned) < 50:
            raise ValueError(f"Insufficient data: {len(aligned)} days (minimum 50 required)")
        
        # Johansen test requires DataFrame
        data = aligned.values
        
        # Run Johansen test
        # det_order: -1=no deterministic term, 0=constant, 1=constant+trend
        result = coint_johansen(data, det_order=0, k_ar_diff=1)
        
        # Extract trace statistic and critical value
        trace_stat = result.trace_stat[0]  # First eigenvalue trace statistic
        critical_value = result.trace_stat_crit_vals[0, significance_level]
        
        # Cointegrated if trace statistic > critical value
        is_cointegrated = bool(trace_stat > critical_value)
        
        # Extract eigenvector for hedge ratio
        # First eigenvector gives cointegrating relationship
        eigenvector = result.evec[:, 0]
        hedge_ratio = -eigenvector[1] / eigenvector[0]
        
        # Calculate spread using hedge ratio
        y = aligned.iloc[:, 0].values
        x = aligned.iloc[:, 1].values
        spread = y + hedge_ratio * x  # Note: eigenvector already includes sign
        
        # Calculate spread statistics
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        # Calculate half-life
        half_life = self._calculate_half_life(spread)
        
        # ADF test on spread
        adf_result = adfuller(spread, maxlag=1, regression='c', autolag='AIC')
        adf_stat = adf_result[0]
        adf_pval = adf_result[1]
        
        return CointegrationResult(
            ticker1=ticker1,
            ticker2=ticker2,
            is_cointegrated=is_cointegrated,
            test_method='johansen',
            test_statistic=trace_stat,
            p_value=0.0,  # Johansen test doesn't provide p-value directly
            critical_value=critical_value,
            hedge_ratio=hedge_ratio,
            half_life=half_life,
            spread_mean=spread_mean,
            spread_std=spread_std,
            adf_statistic=adf_stat,
            adf_p_value=adf_pval,
        )
    
    def _calculate_half_life(self, spread: np.ndarray) -> Optional[float]:
        """
        Calculate half-life of mean reversion for a spread.
        
        Uses AR(1) model: spread(t) = a + b*spread(t-1) + e(t)
        Half-life = -log(2) / log(b)
        
        Args:
            spread: Spread time series
            
        Returns:
            Half-life in days, or None if calculation fails
        """
        try:
            # Fit AR(1) model
            spread_lag = spread[:-1]
            spread_current = spread[1:]
            
            X = np.column_stack([np.ones(len(spread_lag)), spread_lag])
            betas, _, _, _ = np.linalg.lstsq(X, spread_current, rcond=None)
            
            b = betas[1]  # AR(1) coefficient
            
            # Half-life calculation
            if 0 < b < 1:
                half_life = -np.log(2) / np.log(b)
                return half_life
            else:
                return None
                
        except Exception:
            return None
    
    def generate_synthetic_factor_returns(
        self,
        start_date: datetime,
        end_date: datetime,
        include_momentum: bool = True,
        include_quality: bool = True
    ) -> pd.DataFrame:
        """
        Generate synthetic Fama-French factor returns for testing/demo purposes.
        
        In production, this should be replaced with actual factor data from
        Kenneth French's data library or similar sources.
        
        Args:
            start_date: Start date for factor returns
            end_date: End date for factor returns
            include_momentum: Include momentum factor
            include_quality: Include quality factor
            
        Returns:
            DataFrame with factor returns indexed by date
        """
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
        n_days = len(dates)
        
        # Generate synthetic factor returns
        # Using realistic means and volatilities based on historical data
        np.random.seed(42)  # For reproducibility
        
        factor_data = {
            'Mkt-RF': np.random.normal(0.0003, 0.01, n_days),  # Market premium
            'SMB': np.random.normal(0.0001, 0.003, n_days),    # Size factor
            'HML': np.random.normal(0.0001, 0.004, n_days),    # Value factor
            'RMW': np.random.normal(0.0001, 0.003, n_days),    # Profitability
            'CMA': np.random.normal(0.0001, 0.002, n_days),    # Investment
        }
        
        if include_momentum:
            factor_data['MOM'] = np.random.normal(0.0002, 0.005, n_days)
            
        if include_quality:
            factor_data['QMJ'] = np.random.normal(0.0001, 0.003, n_days)
        
        df = pd.DataFrame(factor_data, index=dates)
        
        return df
    
    def calculate_momentum_exposure(
        self,
        prices: pd.Series,
        lookback_period: int = 252
    ) -> float:
        """
        Calculate momentum factor exposure.
        
        Requirement 14.7: Momentum factor exposure
        
        Args:
            prices: Price series
            lookback_period: Lookback period in days (default: 252 = 1 year)
            
        Returns:
            Momentum score (cumulative return over lookback period)
        """
        if len(prices) < lookback_period:
            lookback_period = len(prices)
        
        if lookback_period < 2:
            return 0.0
        
        # Calculate cumulative return
        start_price = prices.iloc[-lookback_period]
        end_price = prices.iloc[-1]
        
        momentum = (end_price - start_price) / start_price
        
        return momentum
    
    def calculate_quality_exposure(
        self,
        financials: Dict[str, float]
    ) -> float:
        """
        Calculate quality factor exposure based on financial metrics.
        
        Requirement 14.7: Quality factor exposure
        
        Quality is typically measured by:
        - Profitability (ROE, ROA, Gross Profit/Assets)
        - Growth (stable earnings growth)
        - Safety (low leverage, low volatility)
        
        Args:
            financials: Dictionary with financial metrics
                Required keys: 'roe', 'roa', 'debt_to_equity', 'earnings_stability'
                
        Returns:
            Quality score (normalized, higher is better quality)
        """
        # Extract metrics with defaults
        roe = financials.get('roe', 0.0)
        roa = financials.get('roa', 0.0)
        debt_to_equity = financials.get('debt_to_equity', 1.0)
        earnings_stability = financials.get('earnings_stability', 0.0)
        
        # Normalize metrics (simple scoring)
        # ROE: >15% is good
        roe_score = min(roe / 0.15, 1.0) if roe > 0 else 0.0
        
        # ROA: >5% is good
        roa_score = min(roa / 0.05, 1.0) if roa > 0 else 0.0
        
        # Debt/Equity: <1.0 is good
        leverage_score = max(1.0 - debt_to_equity, 0.0)
        
        # Earnings stability: 0-1 scale, higher is better
        stability_score = max(0.0, min(earnings_stability, 1.0))
        
        # Composite quality score (equal weights)
        quality_score = (roe_score + roa_score + leverage_score + stability_score) / 4.0
        
        return quality_score
    
    def calculate_value_exposure(
        self,
        price: float,
        book_value_per_share: float,
        earnings_per_share: float
    ) -> float:
        """
        Calculate value factor exposure based on valuation ratios.
        
        Requirement 14.7: Value factor exposure (related to HML factor)
        
        Args:
            price: Current stock price
            book_value_per_share: Book value per share
            earnings_per_share: Earnings per share (TTM)
            
        Returns:
            Value score (higher = more value-oriented, lower = more growth-oriented)
        """
        if price <= 0:
            return 0.0
        
        # Price-to-Book ratio (lower is more value)
        pb_ratio = price / book_value_per_share if book_value_per_share > 0 else 999.0
        
        # Price-to-Earnings ratio (lower is more value)
        pe_ratio = price / earnings_per_share if earnings_per_share > 0 else 999.0
        
        # Normalize (invert so higher score = more value)
        # Typical P/B for value stocks: 0.5-1.5, growth stocks: 3-10+
        # Typical P/E for value stocks: 5-15, growth stocks: 25-50+
        
        pb_score = max(0.0, 1.0 - (pb_ratio - 1.0) / 5.0)  # 1.0 at P/B=1, 0.0 at P/B=6
        pe_score = max(0.0, 1.0 - (pe_ratio - 10.0) / 40.0)  # 1.0 at P/E=10, 0.0 at P/E=50
        
        # Composite value score
        value_score = (pb_score + pe_score) / 2.0
        
        return value_score
