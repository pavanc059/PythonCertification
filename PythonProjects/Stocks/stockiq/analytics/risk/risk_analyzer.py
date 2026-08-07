"""
Risk Analytics Module

This module provides institutional-grade risk metrics including:
- Value at Risk (VaR) at 95% and 99% confidence levels
- Conditional Value at Risk (CVaR) for tail risk assessment
- Performance ratios: Sharpe, Sortino, Calmar

Requirements: 14.3, 14.4, 14.5, 14.12
"""

from dataclasses import dataclass
from typing import Optional, Dict
import numpy as np
import pandas as pd
from decimal import Decimal


@dataclass
class VaRResult:
    """Value at Risk calculation result"""
    confidence_level: float  # e.g., 0.95 or 0.99
    var_amount: float  # VaR in currency units
    var_percentage: float  # VaR as percentage of portfolio value
    method: str  # "historical_simulation", "parametric", "monte_carlo"
    lookback_days: int


@dataclass
class CVaRResult:
    """Conditional Value at Risk calculation result"""
    confidence_level: float  # e.g., 0.95 or 0.99
    cvar_amount: float  # CVaR in currency units
    cvar_percentage: float  # CVaR as percentage of portfolio value
    method: str
    lookback_days: int
    tail_losses: int  # Number of observations beyond VaR


@dataclass
class PerformanceMetrics:
    """Performance ratio metrics"""
    sharpe_ratio: float  # Risk-adjusted return using total volatility
    sortino_ratio: float  # Risk-adjusted return using downside volatility
    calmar_ratio: float  # Return over maximum drawdown
    annual_return: float
    annual_volatility: float
    downside_volatility: float
    max_drawdown: float
    lookback_days: int


class RiskAnalyzer:
    """
    Institutional-grade risk analytics engine.
    
    Provides:
    - Value at Risk (VaR) at multiple confidence levels
    - Conditional Value at Risk (CVaR) for tail risk
    - Performance ratios (Sharpe, Sortino, Calmar)
    - Rolling window analysis
    
    Requirements: 14.3, 14.4, 14.5, 14.12
    """
    
    DEFAULT_WINDOW = 252  # 252 trading days = 1 year
    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.02  # 2% annual risk-free rate (configurable)
    
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE):
        """
        Initialize risk analyzer.
        
        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical_simulation",
        lookback_days: int = DEFAULT_WINDOW
    ) -> VaRResult:
        """
        Calculate Value at Risk (VaR) - maximum expected loss at given confidence level.
        
        VaR answers: "What is the maximum loss we expect over the next period,
        with X% confidence?"
        
        Args:
            returns: Series of daily returns
            confidence_level: Confidence level (0.95 or 0.99)
            method: Calculation method ("historical_simulation", "parametric")
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            VaRResult with VaR amount and percentage
            
        Requirement: 14.3 - VaR at 95% and 99% confidence levels
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        if len(returns) < lookback_days:
            lookback_days = len(returns)
        
        # Handle empty returns
        if len(returns) == 0:
            return VaRResult(
                confidence_level=confidence_level,
                var_amount=0.0,
                var_percentage=0.0,
                method=method,
                lookback_days=0
            )
        
        # Use most recent data within lookback window
        recent_returns = returns.tail(lookback_days)
        
        if method == "historical_simulation":
            # Historical simulation: use empirical distribution
            var_percentage = np.percentile(recent_returns, (1 - confidence_level) * 100)
            # VaR is expressed as positive loss, so if worst loss is negative, flip it
            var_amount = abs(var_percentage)
        
        elif method == "parametric":
            # Parametric VaR: assumes normal distribution
            mean_return = recent_returns.mean()
            std_return = recent_returns.std()
            
            # Z-score for confidence level (1.645 for 95%, 2.326 for 99%)
            from scipy import stats
            z_score = stats.norm.ppf(confidence_level)
            
            var_percentage = -(mean_return - z_score * std_return)
            var_amount = abs(var_percentage)
        
        else:
            raise ValueError(f"Unknown VaR method: {method}")
        
        return VaRResult(
            confidence_level=confidence_level,
            var_amount=float(var_amount),
            var_percentage=float(var_amount * 100),  # Convert to percentage
            method=method,
            lookback_days=lookback_days
        )
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical_simulation",
        lookback_days: int = DEFAULT_WINDOW
    ) -> CVaRResult:
        """
        Calculate Conditional Value at Risk (CVaR) - expected loss in the tail.
        
        CVaR (also called Expected Shortfall) answers: "If we exceed VaR,
        what is the average loss we can expect?"
        
        CVaR provides better tail risk assessment than VaR alone.
        
        Args:
            returns: Series of daily returns
            confidence_level: Confidence level (0.95 or 0.99)
            method: Calculation method ("historical_simulation")
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            CVaRResult with CVaR amount and tail statistics
            
        Requirement: 14.4 - CVaR for tail risk assessment
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        if len(returns) < lookback_days:
            lookback_days = len(returns)
        
        # Handle empty returns
        if len(returns) == 0:
            return CVaRResult(
                confidence_level=confidence_level,
                cvar_amount=0.0,
                cvar_percentage=0.0,
                method=method,
                lookback_days=0,
                tail_losses=0
            )
        
        # Use most recent data within lookback window
        recent_returns = returns.tail(lookback_days)
        
        if method == "historical_simulation":
            # Calculate VaR threshold (worst losses are at the low percentile)
            var_threshold = np.percentile(recent_returns, (1 - confidence_level) * 100)
            
            # CVaR is the average of all losses beyond VaR (worse than VaR threshold)
            tail_losses = recent_returns[recent_returns <= var_threshold]
            cvar_value = abs(tail_losses.mean()) if len(tail_losses) > 0 else abs(var_threshold)
            
            tail_count = len(tail_losses)
        
        else:
            raise ValueError(f"Unknown CVaR method: {method}")
        
        return CVaRResult(
            confidence_level=confidence_level,
            cvar_amount=float(cvar_value),
            cvar_percentage=float(cvar_value * 100),  # Convert to percentage
            method=method,
            lookback_days=lookback_days,
            tail_losses=tail_count
        )
    
    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        lookback_days: int = DEFAULT_WINDOW
    ) -> float:
        """
        Calculate Sharpe Ratio - risk-adjusted return using total volatility.
        
        Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility
        
        Higher Sharpe ratio indicates better risk-adjusted performance.
        Typical values: <1 (poor), 1-2 (good), >2 (excellent)
        
        Args:
            returns: Series of daily returns
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            Annualized Sharpe ratio
            
        Requirement: 14.5 - Sharpe ratio for performance evaluation
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        if len(returns) < lookback_days:
            lookback_days = len(returns)
        
        recent_returns = returns.tail(lookback_days)
        
        # Annualize return and volatility
        mean_return = recent_returns.mean() * self.TRADING_DAYS_PER_YEAR
        volatility = recent_returns.std(ddof=1) * np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        # Handle zero or very small volatility
        if volatility < 1e-10:
            return 0.0
        
        sharpe = (mean_return - self.risk_free_rate) / volatility
        return float(sharpe)
    
    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        lookback_days: int = DEFAULT_WINDOW
    ) -> float:
        """
        Calculate Sortino Ratio - risk-adjusted return using downside volatility.
        
        Sortino Ratio = (Portfolio Return - Risk-Free Rate) / Downside Volatility
        
        Similar to Sharpe but only penalizes downside volatility, not upside.
        Preferred over Sharpe when returns are asymmetric.
        
        Args:
            returns: Series of daily returns
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            Annualized Sortino ratio
            
        Requirement: 14.5 - Sortino ratio for performance evaluation
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        if len(returns) < lookback_days:
            lookback_days = len(returns)
        
        recent_returns = returns.tail(lookback_days)
        
        # Annualize return
        mean_return = recent_returns.mean() * self.TRADING_DAYS_PER_YEAR
        
        # Calculate downside volatility (only negative returns)
        negative_returns = recent_returns[recent_returns < 0]
        
        if len(negative_returns) == 0:
            return float('inf')  # No downside risk
        
        downside_volatility = negative_returns.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        if downside_volatility == 0:
            return 0.0
        
        sortino = (mean_return - self.risk_free_rate) / downside_volatility
        return float(sortino)
    
    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """
        Calculate maximum drawdown - largest peak-to-trough decline.
        
        Max Drawdown = (Trough - Peak) / Peak
        
        Args:
            prices: Series of portfolio values or prices
        
        Returns:
            Maximum drawdown as decimal (e.g., -0.25 for 25% drawdown)
        """
        # Calculate cumulative maximum (running peak)
        cummax = prices.cummax()
        
        # Calculate drawdown at each point
        drawdown = (prices - cummax) / cummax
        
        # Maximum drawdown is the minimum value (most negative)
        max_dd = drawdown.min()
        
        return float(max_dd)
    
    def calculate_calmar_ratio(
        self,
        returns: pd.Series,
        lookback_days: int = DEFAULT_WINDOW
    ) -> float:
        """
        Calculate Calmar Ratio - return over maximum drawdown.
        
        Calmar Ratio = Annualized Return / |Maximum Drawdown|
        
        Measures return relative to worst-case drawdown.
        Higher values indicate better risk-adjusted returns.
        
        Args:
            returns: Series of daily returns
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            Calmar ratio
            
        Requirement: 14.5 - Calmar ratio for performance evaluation
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        if len(returns) < lookback_days:
            lookback_days = len(returns)
        
        recent_returns = returns.tail(lookback_days)
        
        # Calculate annualized return
        mean_return = recent_returns.mean() * self.TRADING_DAYS_PER_YEAR
        
        # Calculate cumulative returns to get price series
        cumulative_returns = (1 + recent_returns).cumprod()
        
        # Calculate maximum drawdown
        max_dd = self.calculate_max_drawdown(cumulative_returns)
        
        if max_dd == 0:
            return float('inf')  # No drawdown
        
        calmar = mean_return / abs(max_dd)
        return float(calmar)
    
    def calculate_performance_metrics(
        self,
        returns: pd.Series,
        lookback_days: int = DEFAULT_WINDOW
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.
        
        Combines all risk-adjusted performance measures:
        - Sharpe ratio
        - Sortino ratio
        - Calmar ratio
        - Volatility metrics
        - Maximum drawdown
        
        Args:
            returns: Series of daily returns
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            PerformanceMetrics with all ratios and statistics
            
        Requirements: 14.5, 14.12
        """
        if len(returns) < lookback_days:
            lookback_days = len(returns)
        
        recent_returns = returns.tail(lookback_days)
        
        # Calculate annualized metrics
        annual_return = recent_returns.mean() * self.TRADING_DAYS_PER_YEAR
        annual_volatility = recent_returns.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)
        
        # Calculate downside volatility
        negative_returns = recent_returns[recent_returns < 0]
        downside_volatility = (
            negative_returns.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)
            if len(negative_returns) > 0 else 0.0
        )
        
        # Calculate maximum drawdown
        cumulative_returns = (1 + recent_returns).cumprod()
        max_drawdown = self.calculate_max_drawdown(cumulative_returns)
        
        # Calculate ratios
        sharpe = self.calculate_sharpe_ratio(recent_returns, lookback_days)
        sortino = self.calculate_sortino_ratio(recent_returns, lookback_days)
        calmar = self.calculate_calmar_ratio(recent_returns, lookback_days)
        
        return PerformanceMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            annual_return=float(annual_return),
            annual_volatility=float(annual_volatility),
            downside_volatility=float(downside_volatility),
            max_drawdown=float(max_drawdown),
            lookback_days=lookback_days
        )
    
    def calculate_rolling_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        window: int = DEFAULT_WINDOW
    ) -> pd.Series:
        """
        Calculate rolling Value at Risk over time.
        
        Args:
            returns: Series of daily returns
            confidence_level: Confidence level (0.95 or 0.99)
            window: Rolling window size (default 252 days)
        
        Returns:
            Series of VaR values over time
            
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        def calc_var(window_returns):
            if len(window_returns) < window:
                return np.nan
            # VaR is the percentile at the loss tail, expressed as positive loss
            return abs(np.percentile(window_returns, (1 - confidence_level) * 100))
        
        rolling_var = returns.rolling(window=window).apply(calc_var, raw=True)
        return rolling_var
    
    def calculate_rolling_sharpe(
        self,
        returns: pd.Series,
        window: int = DEFAULT_WINDOW
    ) -> pd.Series:
        """
        Calculate rolling Sharpe ratio over time.
        
        Args:
            returns: Series of daily returns
            window: Rolling window size (default 252 days)
        
        Returns:
            Series of Sharpe ratios over time
            
        Requirement: 14.12 - Rolling windows of 252 trading days
        """
        def calc_sharpe(window_returns):
            if len(window_returns) < window:
                return np.nan
            mean_ret = window_returns.mean() * self.TRADING_DAYS_PER_YEAR
            vol = window_returns.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)
            if vol == 0:
                return 0.0
            return (mean_ret - self.risk_free_rate) / vol
        
        rolling_sharpe = returns.rolling(window=window).apply(calc_sharpe, raw=True)
        return rolling_sharpe
    
    def generate_risk_report(
        self,
        returns: pd.Series,
        lookback_days: int = DEFAULT_WINDOW
    ) -> Dict:
        """
        Generate comprehensive risk report with all metrics.
        
        Args:
            returns: Series of daily returns
            lookback_days: Rolling window size (default 252 days)
        
        Returns:
            Dictionary with all risk metrics
        """
        # VaR at multiple confidence levels
        var_95 = self.calculate_var(returns, confidence_level=0.95, lookback_days=lookback_days)
        var_99 = self.calculate_var(returns, confidence_level=0.99, lookback_days=lookback_days)
        
        # CVaR at multiple confidence levels
        cvar_95 = self.calculate_cvar(returns, confidence_level=0.95, lookback_days=lookback_days)
        cvar_99 = self.calculate_cvar(returns, confidence_level=0.99, lookback_days=lookback_days)
        
        # Performance metrics
        performance = self.calculate_performance_metrics(returns, lookback_days=lookback_days)
        
        return {
            'var_95': var_95,
            'var_99': var_99,
            'cvar_95': cvar_95,
            'cvar_99': cvar_99,
            'performance': performance,
            'lookback_days': lookback_days
        }
