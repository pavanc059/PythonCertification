"""
Mean-Variance Portfolio Optimization

Implements Markowitz mean-variance optimization using quadratic programming.
Finds the portfolio weights that maximize expected return for a given level of risk,
or minimize risk for a given level of expected return.

Requirements: 14.10
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import warnings


@dataclass
class Portfolio:
    """Optimized portfolio representation"""
    tickers: List[str]
    weights: Dict[str, float]  # Ticker -> weight
    expected_return: float  # Annualized expected return
    volatility: float  # Annualized portfolio volatility (std dev)
    sharpe_ratio: float  # Risk-adjusted return
    optimization_method: str  # "max_sharpe", "min_variance", "efficient_return"


@dataclass
class OptimizationConstraints:
    """Portfolio optimization constraints"""
    min_weight: float = 0.0  # Minimum weight per asset (0.0 = no short selling)
    max_weight: float = 1.0  # Maximum weight per asset
    target_return: Optional[float] = None  # Target return for efficient frontier
    target_volatility: Optional[float] = None  # Target volatility
    risk_free_rate: float = 0.02  # Annual risk-free rate (2%)
    allow_short: bool = False  # Allow short positions (negative weights)
    sector_limits: Optional[Dict[str, Tuple[float, float]]] = None  # Sector -> (min, max)


@dataclass
class OptimizationResult:
    """Complete optimization result with diagnostics"""
    portfolio: Portfolio
    convergence: bool  # Whether optimization converged
    iterations: int  # Number of iterations
    objective_value: float  # Final objective function value
    frontier_points: Optional[List[Portfolio]] = None  # Efficient frontier portfolios


class MeanVarianceOptimizer:
    """
    Mean-Variance Portfolio Optimizer using Markowitz framework.
    
    Implements quadratic programming to find optimal portfolio weights that:
    1. Maximize Sharpe ratio (risk-adjusted return)
    2. Minimize portfolio variance
    3. Target specific return or volatility levels
    
    Key assumptions:
    - Returns are normally distributed
    - Investors are risk-averse and prefer higher returns
    - Historical returns and covariances predict future behavior
    
    Requirements: 14.10 - Mean-variance optimization using quadratic programming
    """
    
    TRADING_DAYS_PER_YEAR = 252
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize optimizer.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def optimize_max_sharpe(
        self,
        returns: pd.DataFrame,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Find portfolio that maximizes Sharpe ratio.
        
        Sharpe ratio = (Expected Return - Risk-Free Rate) / Volatility
        
        This is the most commonly used optimization objective as it balances
        return and risk in a single metric.
        
        Args:
            returns: DataFrame with daily returns (rows=dates, cols=tickers)
            constraints: Optimization constraints
        
        Returns:
            OptimizationResult with maximum Sharpe portfolio
            
        Requirement: 14.10 - Mean-variance optimization
        """
        if constraints is None:
            constraints = OptimizationConstraints(risk_free_rate=self.risk_free_rate)
        
        # Calculate expected returns and covariance
        expected_returns = self._calculate_expected_returns(returns)
        cov_matrix = self._calculate_covariance(returns)
        
        n_assets = len(returns.columns)
        tickers = list(returns.columns)
        
        # Initial guess: equal weights
        initial_weights = np.array([1.0 / n_assets] * n_assets)
        
        # Objective: Negative Sharpe ratio (minimize negative = maximize positive)
        def objective(weights):
            port_return = np.dot(weights, expected_returns)
            port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            if port_volatility < 1e-10:
                return -1e6  # Avoid division by zero
            
            sharpe = (port_return - constraints.risk_free_rate) / port_volatility
            return -sharpe  # Negative because we're minimizing
        
        # Constraints and bounds
        scipy_constraints, bounds = self._build_constraints(
            n_assets, constraints, expected_returns, cov_matrix
        )
        
        # Run optimization
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=scipy_constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        # Build portfolio
        optimal_weights = result.x
        portfolio = self._create_portfolio(
            tickers,
            optimal_weights,
            expected_returns,
            cov_matrix,
            constraints.risk_free_rate,
            "max_sharpe"
        )
        
        return OptimizationResult(
            portfolio=portfolio,
            convergence=result.success,
            iterations=result.nit,
            objective_value=-result.fun  # Convert back to positive Sharpe
        )
    
    def optimize_min_variance(
        self,
        returns: pd.DataFrame,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Find minimum variance portfolio (lowest risk).
        
        This portfolio has the lowest volatility regardless of expected return.
        Useful for highly risk-averse investors.
        
        Args:
            returns: DataFrame with daily returns (rows=dates, cols=tickers)
            constraints: Optimization constraints
        
        Returns:
            OptimizationResult with minimum variance portfolio
            
        Requirement: 14.10 - Mean-variance optimization
        """
        if constraints is None:
            constraints = OptimizationConstraints(risk_free_rate=self.risk_free_rate)
        
        # Calculate expected returns and covariance
        expected_returns = self._calculate_expected_returns(returns)
        cov_matrix = self._calculate_covariance(returns)
        
        n_assets = len(returns.columns)
        tickers = list(returns.columns)
        
        # Initial guess: equal weights
        initial_weights = np.array([1.0 / n_assets] * n_assets)
        
        # Objective: Portfolio variance
        def objective(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))
        
        # Constraints and bounds
        scipy_constraints, bounds = self._build_constraints(
            n_assets, constraints, expected_returns, cov_matrix
        )
        
        # Run optimization
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=scipy_constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        # Build portfolio
        optimal_weights = result.x
        portfolio = self._create_portfolio(
            tickers,
            optimal_weights,
            expected_returns,
            cov_matrix,
            constraints.risk_free_rate,
            "min_variance"
        )
        
        return OptimizationResult(
            portfolio=portfolio,
            convergence=result.success,
            iterations=result.nit,
            objective_value=result.fun  # Portfolio variance
        )
    
    def optimize_efficient_return(
        self,
        returns: pd.DataFrame,
        target_return: float,
        constraints: Optional[OptimizationConstraints] = None
    ) -> OptimizationResult:
        """
        Find portfolio with minimum variance for a target return.
        
        This finds a point on the efficient frontier with a specific return level.
        
        Args:
            returns: DataFrame with daily returns (rows=dates, cols=tickers)
            target_return: Target annualized return (e.g., 0.10 for 10%)
            constraints: Optimization constraints
        
        Returns:
            OptimizationResult with efficient portfolio
            
        Requirement: 14.10 - Mean-variance optimization
        """
        if constraints is None:
            constraints = OptimizationConstraints(risk_free_rate=self.risk_free_rate)
        
        constraints.target_return = target_return
        
        # Calculate expected returns and covariance
        expected_returns = self._calculate_expected_returns(returns)
        cov_matrix = self._calculate_covariance(returns)
        
        n_assets = len(returns.columns)
        tickers = list(returns.columns)
        
        # Initial guess: equal weights
        initial_weights = np.array([1.0 / n_assets] * n_assets)
        
        # Objective: Portfolio variance
        def objective(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))
        
        # Constraints and bounds (includes target return constraint)
        scipy_constraints, bounds = self._build_constraints(
            n_assets, constraints, expected_returns, cov_matrix
        )
        
        # Run optimization
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=scipy_constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        # Build portfolio
        optimal_weights = result.x
        portfolio = self._create_portfolio(
            tickers,
            optimal_weights,
            expected_returns,
            cov_matrix,
            constraints.risk_free_rate,
            "efficient_return"
        )
        
        return OptimizationResult(
            portfolio=portfolio,
            convergence=result.success,
            iterations=result.nit,
            objective_value=result.fun  # Portfolio variance
        )
    
    def generate_efficient_frontier(
        self,
        returns: pd.DataFrame,
        num_points: int = 50,
        constraints: Optional[OptimizationConstraints] = None
    ) -> List[Portfolio]:
        """
        Generate efficient frontier portfolios.
        
        The efficient frontier shows the best possible portfolios for each
        risk level (minimum variance for each return level).
        
        Args:
            returns: DataFrame with daily returns (rows=dates, cols=tickers)
            num_points: Number of frontier points to generate
            constraints: Optimization constraints
        
        Returns:
            List of efficient portfolios ordered by increasing risk
            
        Requirement: 14.10 - Mean-variance optimization
        """
        if constraints is None:
            constraints = OptimizationConstraints(risk_free_rate=self.risk_free_rate)
        
        # Calculate expected returns
        expected_returns = self._calculate_expected_returns(returns)
        
        # Find min and max return bounds
        min_return = expected_returns.min()
        max_return = expected_returns.max()
        
        # Generate target returns along the frontier
        target_returns = np.linspace(min_return, max_return, num_points)
        
        frontier_portfolios = []
        
        for target_ret in target_returns:
            try:
                result = self.optimize_efficient_return(
                    returns,
                    target_ret,
                    constraints
                )
                
                if result.convergence:
                    frontier_portfolios.append(result.portfolio)
            except Exception as e:
                warnings.warn(f"Failed to optimize for return {target_ret:.4f}: {e}")
                continue
        
        # Sort by volatility (ascending)
        frontier_portfolios.sort(key=lambda p: p.volatility)
        
        return frontier_portfolios
    
    def _calculate_expected_returns(self, returns: pd.DataFrame) -> np.ndarray:
        """
        Calculate annualized expected returns from historical data.
        
        Args:
            returns: DataFrame with daily returns
        
        Returns:
            Array of annualized expected returns
        """
        # Mean daily return * trading days per year
        expected_returns = returns.mean() * self.TRADING_DAYS_PER_YEAR
        return expected_returns.values
    
    def _calculate_covariance(self, returns: pd.DataFrame) -> np.ndarray:
        """
        Calculate annualized covariance matrix from historical data.
        
        Args:
            returns: DataFrame with daily returns
        
        Returns:
            Covariance matrix (annualized)
        """
        # Daily covariance * trading days per year
        cov_matrix = returns.cov() * self.TRADING_DAYS_PER_YEAR
        return cov_matrix.values
    
    def _build_constraints(
        self,
        n_assets: int,
        constraints: OptimizationConstraints,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray
    ) -> Tuple[List[Dict], List[Tuple[float, float]]]:
        """
        Build scipy optimization constraints and bounds.
        
        Args:
            n_assets: Number of assets
            constraints: User-defined constraints
            expected_returns: Array of expected returns
            cov_matrix: Covariance matrix
        
        Returns:
            Tuple of (scipy_constraints, bounds)
        """
        scipy_constraints = []
        
        # Constraint 1: Weights must sum to 1
        scipy_constraints.append({
            'type': 'eq',
            'fun': lambda w: np.sum(w) - 1.0
        })
        
        # Constraint 2: Target return (if specified)
        if constraints.target_return is not None:
            scipy_constraints.append({
                'type': 'eq',
                'fun': lambda w: np.dot(w, expected_returns) - constraints.target_return
            })
        
        # Constraint 3: Target volatility (if specified)
        if constraints.target_volatility is not None:
            scipy_constraints.append({
                'type': 'eq',
                'fun': lambda w: np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))) - constraints.target_volatility
            })
        
        # Bounds: Weight limits per asset
        if constraints.allow_short:
            # Allow short positions (negative weights)
            bounds = [(constraints.min_weight, constraints.max_weight)] * n_assets
        else:
            # Long-only (no short selling)
            bounds = [(max(0.0, constraints.min_weight), constraints.max_weight)] * n_assets
        
        return scipy_constraints, bounds
    
    def _create_portfolio(
        self,
        tickers: List[str],
        weights: np.ndarray,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_free_rate: float,
        method: str
    ) -> Portfolio:
        """
        Create Portfolio object from optimization result.
        
        Args:
            tickers: List of ticker symbols
            weights: Optimal weights
            expected_returns: Array of expected returns
            cov_matrix: Covariance matrix
            risk_free_rate: Risk-free rate
            method: Optimization method used
        
        Returns:
            Portfolio object
        """
        # Round very small weights to zero for cleaner output
        weights = np.where(np.abs(weights) < 1e-6, 0.0, weights)
        
        # Normalize to ensure weights sum to 1.0
        weights = weights / np.sum(weights)
        
        # Calculate portfolio metrics
        port_return = np.dot(weights, expected_returns)
        port_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Calculate Sharpe ratio
        if port_volatility > 1e-10:
            sharpe_ratio = (port_return - risk_free_rate) / port_volatility
        else:
            sharpe_ratio = 0.0
        
        # Create weight dictionary
        weight_dict = {
            ticker: float(weight)
            for ticker, weight in zip(tickers, weights)
            if abs(weight) > 1e-6  # Only include non-zero weights
        }
        
        return Portfolio(
            tickers=tickers,
            weights=weight_dict,
            expected_return=float(port_return),
            volatility=float(port_volatility),
            sharpe_ratio=float(sharpe_ratio),
            optimization_method=method
        )
    
    def calculate_portfolio_metrics(
        self,
        weights: Dict[str, float],
        returns: pd.DataFrame
    ) -> Tuple[float, float, float]:
        """
        Calculate metrics for a given portfolio.
        
        Args:
            weights: Dict of ticker -> weight
            returns: DataFrame with daily returns
        
        Returns:
            Tuple of (expected_return, volatility, sharpe_ratio)
        """
        # Align weights with returns columns
        tickers = list(returns.columns)
        weight_array = np.array([weights.get(ticker, 0.0) for ticker in tickers])
        
        # Normalize weights
        weight_array = weight_array / np.sum(weight_array)
        
        # Calculate metrics
        expected_returns = self._calculate_expected_returns(returns)
        cov_matrix = self._calculate_covariance(returns)
        
        port_return = np.dot(weight_array, expected_returns)
        port_volatility = np.sqrt(np.dot(weight_array.T, np.dot(cov_matrix, weight_array)))
        
        if port_volatility > 1e-10:
            sharpe_ratio = (port_return - self.risk_free_rate) / port_volatility
        else:
            sharpe_ratio = 0.0
        
        return float(port_return), float(port_volatility), float(sharpe_ratio)
