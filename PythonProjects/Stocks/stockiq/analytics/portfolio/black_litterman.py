"""
Black-Litterman Portfolio Optimization

Implements the Black-Litterman model which combines market equilibrium returns
with investor views to generate optimal portfolio allocations.

The Black-Litterman model solves key problems with mean-variance optimization:
1. Overly concentrated portfolios
2. Unstable allocations from estimation error
3. Counterintuitive corner solutions

Requirements: 14.11
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from .mean_variance import Portfolio, MeanVarianceOptimizer


@dataclass
class InvestorView:
    """Single investor view on asset returns"""
    view_type: str  # "absolute" or "relative"
    assets: List[str]  # Tickers involved in view
    expected_return: float  # Expected return (e.g., 0.05 for 5%)
    confidence: float  # Confidence level 0-1 (0=no confidence, 1=certain)
    description: Optional[str] = None  # Human-readable view description


@dataclass
class InvestorViews:
    """Collection of investor views"""
    views: List[InvestorView] = field(default_factory=list)
    
    def add_absolute_view(
        self,
        ticker: str,
        expected_return: float,
        confidence: float,
        description: Optional[str] = None
    ) -> None:
        """
        Add absolute view on a single asset.
        
        Example: "I believe AAPL will return 8% over the next year"
        
        Args:
            ticker: Asset ticker
            expected_return: Expected return (e.g., 0.08 for 8%)
            confidence: Confidence level 0-1
            description: Human-readable description
        """
        view = InvestorView(
            view_type="absolute",
            assets=[ticker],
            expected_return=expected_return,
            confidence=confidence,
            description=description or f"{ticker} will return {expected_return:.2%}"
        )
        self.views.append(view)
    
    def add_relative_view(
        self,
        ticker1: str,
        ticker2: str,
        expected_outperformance: float,
        confidence: float,
        description: Optional[str] = None
    ) -> None:
        """
        Add relative view between two assets.
        
        Example: "I believe AAPL will outperform MSFT by 3%"
        
        Args:
            ticker1: First asset ticker
            ticker2: Second asset ticker
            expected_outperformance: Expected excess return (e.g., 0.03 for 3%)
            confidence: Confidence level 0-1
            description: Human-readable description
        """
        view = InvestorView(
            view_type="relative",
            assets=[ticker1, ticker2],
            expected_return=expected_outperformance,
            confidence=confidence,
            description=description or f"{ticker1} will outperform {ticker2} by {expected_outperformance:.2%}"
        )
        self.views.append(view)


@dataclass
class BlackLittermanResult:
    """Black-Litterman optimization result"""
    portfolio: Portfolio
    implied_returns: Dict[str, float]  # Market equilibrium returns
    posterior_returns: Dict[str, float]  # Combined returns (equilibrium + views)
    posterior_covariance: np.ndarray  # Posterior covariance matrix
    views_applied: int  # Number of views incorporated
    tau: float  # Uncertainty scaling parameter


class BlackLittermanOptimizer:
    """
    Black-Litterman Portfolio Optimizer.
    
    The Black-Litterman model works in three steps:
    1. Calculate implied equilibrium returns from market capitalization weights
    2. Incorporate investor views using Bayesian updating
    3. Optimize portfolio using posterior returns and covariance
    
    Key advantages over traditional mean-variance:
    - More diversified portfolios
    - Stable allocations despite estimation error
    - Intuitive way to incorporate investor beliefs
    - Handles uncertainty in both market equilibrium and views
    
    Requirements: 14.11 - Black-Litterman optimization with user-specified views
    """
    
    TRADING_DAYS_PER_YEAR = 252
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,
        tau: float = 0.025,
        risk_aversion: float = 2.5
    ):
        """
        Initialize Black-Litterman optimizer.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
            tau: Uncertainty scaling parameter (default 0.025)
                - Smaller tau means more confidence in equilibrium returns
                - Typical range: 0.01 to 0.05
            risk_aversion: Market risk aversion parameter (default 2.5)
                - Higher values indicate more risk-averse market
                - Typical range: 1.0 to 5.0
        """
        self.risk_free_rate = risk_free_rate
        self.tau = tau
        self.risk_aversion = risk_aversion
        self.mv_optimizer = MeanVarianceOptimizer(risk_free_rate=risk_free_rate)
    
    def optimize(
        self,
        returns: pd.DataFrame,
        market_caps: Dict[str, float],
        views: InvestorViews,
        optimize_method: str = "max_sharpe"
    ) -> BlackLittermanResult:
        """
        Optimize portfolio using Black-Litterman model with investor views.
        
        Process:
        1. Calculate implied equilibrium returns from market caps
        2. Build view matrices P (picks) and Q (view returns)
        3. Calculate posterior returns combining equilibrium + views
        4. Optimize portfolio using posterior returns
        
        Args:
            returns: DataFrame with daily returns (rows=dates, cols=tickers)
            market_caps: Dict of ticker -> market capitalization
            views: InvestorViews object with investor beliefs
            optimize_method: "max_sharpe" or "min_variance"
        
        Returns:
            BlackLittermanResult with optimized portfolio and diagnostics
            
        Requirement: 14.11 - Black-Litterman optimization with user-specified views
        """
        tickers = list(returns.columns)
        n_assets = len(tickers)
        
        # Step 1: Calculate implied equilibrium returns (reverse optimization)
        implied_returns = self._calculate_implied_returns(
            returns, market_caps, tickers
        )
        
        # Step 2: Calculate covariance matrix
        cov_matrix = self.mv_optimizer._calculate_covariance(returns)
        
        # Step 3: Build view matrices if views are provided
        if len(views.views) > 0:
            P, Q, Omega = self._build_view_matrices(views, tickers, cov_matrix)
            
            # Step 4: Calculate posterior returns (Bayesian update)
            posterior_returns, posterior_cov = self._calculate_posterior(
                implied_returns, cov_matrix, P, Q, Omega
            )
        else:
            # No views: use equilibrium returns directly
            posterior_returns = implied_returns
            posterior_cov = cov_matrix
        
        # Step 5: Optimize portfolio using posterior returns
        # Create a temporary DataFrame for optimization
        posterior_returns_series = pd.Series(posterior_returns, index=tickers)
        synthetic_returns = self._create_synthetic_returns(
            posterior_returns_series, posterior_cov, len(returns)
        )
        
        # Run mean-variance optimization on synthetic returns
        if optimize_method == "max_sharpe":
            result = self.mv_optimizer.optimize_max_sharpe(synthetic_returns)
        elif optimize_method == "min_variance":
            result = self.mv_optimizer.optimize_min_variance(synthetic_returns)
        else:
            raise ValueError(f"Unknown optimization method: {optimize_method}")
        
        # Build result
        portfolio = result.portfolio
        
        return BlackLittermanResult(
            portfolio=portfolio,
            implied_returns={ticker: float(ret) for ticker, ret in zip(tickers, implied_returns)},
            posterior_returns={ticker: float(ret) for ticker, ret in zip(tickers, posterior_returns)},
            posterior_covariance=posterior_cov,
            views_applied=len(views.views),
            tau=self.tau
        )
    
    def _calculate_implied_returns(
        self,
        returns: pd.DataFrame,
        market_caps: Dict[str, float],
        tickers: List[str]
    ) -> np.ndarray:
        """
        Calculate implied equilibrium returns using reverse optimization.
        
        The implied returns represent the market consensus on expected returns,
        derived from market capitalization weights and historical covariances.
        
        Formula: π = δ * Σ * w_mkt
        where:
        - π = implied excess returns
        - δ = risk aversion coefficient
        - Σ = covariance matrix
        - w_mkt = market capitalization weights
        
        Args:
            returns: DataFrame with daily returns
            market_caps: Dict of ticker -> market cap
            tickers: List of tickers in order
        
        Returns:
            Array of implied equilibrium returns (annualized)
        """
        # Calculate market cap weights
        total_market_cap = sum(market_caps.values())
        mkt_weights = np.array([
            market_caps.get(ticker, 0.0) / total_market_cap
            for ticker in tickers
        ])
        
        # Normalize weights to sum to 1
        mkt_weights = mkt_weights / np.sum(mkt_weights)
        
        # Calculate covariance matrix
        cov_matrix = self.mv_optimizer._calculate_covariance(returns)
        
        # Implied excess returns: π = δ * Σ * w_mkt
        implied_excess_returns = self.risk_aversion * np.dot(cov_matrix, mkt_weights)
        
        # Add risk-free rate to get total returns
        implied_returns = implied_excess_returns + self.risk_free_rate
        
        return implied_returns
    
    def _build_view_matrices(
        self,
        views: InvestorViews,
        tickers: List[str],
        cov_matrix: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Build view matrices P (picks), Q (views), and Ω (uncertainty).
        
        P matrix: Each row represents a view (which assets are involved)
        Q vector: Expected return for each view
        Ω matrix: Uncertainty/confidence in each view
        
        Args:
            views: InvestorViews object
            tickers: List of tickers
            cov_matrix: Covariance matrix
        
        Returns:
            Tuple of (P, Q, Omega)
        """
        n_views = len(views.views)
        n_assets = len(tickers)
        
        # Initialize matrices
        P = np.zeros((n_views, n_assets))
        Q = np.zeros(n_views)
        Omega = np.zeros((n_views, n_views))
        
        ticker_to_idx = {ticker: idx for idx, ticker in enumerate(tickers)}
        
        for i, view in enumerate(views.views):
            # Build Q: expected returns
            Q[i] = view.expected_return
            
            if view.view_type == "absolute":
                # Absolute view: 100% weight on single asset
                ticker = view.assets[0]
                if ticker in ticker_to_idx:
                    P[i, ticker_to_idx[ticker]] = 1.0
                
                # View uncertainty based on asset variance and confidence
                asset_variance = cov_matrix[ticker_to_idx[ticker], ticker_to_idx[ticker]]
                Omega[i, i] = asset_variance * self.tau / view.confidence
            
            elif view.view_type == "relative":
                # Relative view: +1 on first asset, -1 on second asset
                ticker1, ticker2 = view.assets[0], view.assets[1]
                if ticker1 in ticker_to_idx and ticker2 in ticker_to_idx:
                    P[i, ticker_to_idx[ticker1]] = 1.0
                    P[i, ticker_to_idx[ticker2]] = -1.0
                
                # View uncertainty based on portfolio variance of the spread
                idx1, idx2 = ticker_to_idx[ticker1], ticker_to_idx[ticker2]
                spread_variance = (
                    cov_matrix[idx1, idx1] +
                    cov_matrix[idx2, idx2] -
                    2 * cov_matrix[idx1, idx2]
                )
                Omega[i, i] = spread_variance * self.tau / view.confidence
        
        return P, Q, Omega
    
    def _calculate_posterior(
        self,
        implied_returns: np.ndarray,
        cov_matrix: np.ndarray,
        P: np.ndarray,
        Q: np.ndarray,
        Omega: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate posterior returns and covariance using Bayesian update.
        
        Black-Litterman master formula:
        E[R] = [(τΣ)^-1 + P'Ω^-1P]^-1 [(τΣ)^-1π + P'Ω^-1Q]
        
        Combines:
        - Prior: Implied equilibrium returns (π) with uncertainty (τΣ)
        - Views: Investor views (Q) with uncertainty (Ω)
        
        Args:
            implied_returns: Implied equilibrium returns
            cov_matrix: Covariance matrix
            P: Pick matrix (views)
            Q: View returns
            Omega: View uncertainty matrix
        
        Returns:
            Tuple of (posterior_returns, posterior_covariance)
        """
        # Scale covariance by tau (uncertainty in equilibrium)
        tau_sigma = self.tau * cov_matrix
        
        # Calculate inverse matrices
        tau_sigma_inv = np.linalg.inv(tau_sigma)
        omega_inv = np.linalg.inv(Omega)
        
        # Posterior precision matrix: (τΣ)^-1 + P'Ω^-1P
        posterior_precision = tau_sigma_inv + np.dot(np.dot(P.T, omega_inv), P)
        
        # Posterior covariance: inverse of precision
        posterior_cov = np.linalg.inv(posterior_precision)
        
        # Posterior returns: [(τΣ)^-1 + P'Ω^-1P]^-1 [(τΣ)^-1π + P'Ω^-1Q]
        prior_term = np.dot(tau_sigma_inv, implied_returns)
        view_term = np.dot(np.dot(P.T, omega_inv), Q)
        posterior_returns = np.dot(posterior_cov, prior_term + view_term)
        
        return posterior_returns, posterior_cov
    
    def _create_synthetic_returns(
        self,
        expected_returns: pd.Series,
        cov_matrix: np.ndarray,
        n_samples: int
    ) -> pd.DataFrame:
        """
        Create synthetic return samples from posterior distribution.
        
        This allows us to use the standard mean-variance optimizer
        with Black-Litterman posterior returns.
        
        Args:
            expected_returns: Posterior expected returns
            cov_matrix: Posterior covariance matrix
            n_samples: Number of samples to generate
        
        Returns:
            DataFrame of synthetic returns
        """
        # Annualize to daily for consistency
        daily_returns = expected_returns / self.TRADING_DAYS_PER_YEAR
        daily_cov = cov_matrix / self.TRADING_DAYS_PER_YEAR
        
        # Generate multivariate normal samples
        samples = np.random.multivariate_normal(
            daily_returns.values,
            daily_cov,
            size=n_samples
        )
        
        return pd.DataFrame(samples, columns=expected_returns.index)
    
    def compare_equilibrium_vs_posterior(
        self,
        result: BlackLittermanResult
    ) -> pd.DataFrame:
        """
        Compare implied equilibrium returns vs. posterior returns.
        
        Shows how investor views shifted the expected returns.
        
        Args:
            result: BlackLittermanResult from optimization
        
        Returns:
            DataFrame with equilibrium, posterior, and difference
        """
        tickers = list(result.implied_returns.keys())
        
        comparison = pd.DataFrame({
            'Ticker': tickers,
            'Equilibrium_Return': [result.implied_returns[t] for t in tickers],
            'Posterior_Return': [result.posterior_returns[t] for t in tickers],
        })
        
        comparison['Difference'] = (
            comparison['Posterior_Return'] - comparison['Equilibrium_Return']
        )
        
        comparison['Difference_pct'] = (
            comparison['Difference'] / comparison['Equilibrium_Return'].abs() * 100
        )
        
        return comparison.sort_values('Difference', ascending=False)
    
    def sensitivity_analysis(
        self,
        returns: pd.DataFrame,
        market_caps: Dict[str, float],
        views: InvestorViews,
        tau_values: List[float] = None
    ) -> pd.DataFrame:
        """
        Perform sensitivity analysis on tau parameter.
        
        Shows how portfolio allocation changes with different uncertainty levels.
        
        Args:
            returns: DataFrame with daily returns
            market_caps: Dict of ticker -> market cap
            views: InvestorViews object
            tau_values: List of tau values to test (default: [0.01, 0.025, 0.05, 0.1])
        
        Returns:
            DataFrame with portfolio weights for each tau value
        """
        if tau_values is None:
            tau_values = [0.01, 0.025, 0.05, 0.1]
        
        results = []
        
        for tau in tau_values:
            # Temporarily change tau
            original_tau = self.tau
            self.tau = tau
            
            # Optimize
            result = self.optimize(returns, market_caps, views)
            
            # Store weights
            row = {'tau': tau}
            row.update(result.portfolio.weights)
            results.append(row)
            
            # Restore original tau
            self.tau = original_tau
        
        return pd.DataFrame(results).fillna(0.0)
