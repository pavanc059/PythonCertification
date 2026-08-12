"""
Performance Metrics and Analysis

Calculate comprehensive performance metrics for backtesting results
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np


@dataclass
class Trade:
    """Represents a completed trade"""
    ticker: str
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: int
    side: str  # 'long' or 'short'
    pnl: Decimal
    pnl_pct: float
    commission: Decimal
    slippage: Decimal


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a backtest"""
    
    # Returns
    total_return: float
    annualized_return: float
    cumulative_return: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_duration_days: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    avg_win_loss_ratio: float
    largest_win: float
    largest_loss: float
    
    # Period metrics
    best_day: float
    worst_day: float
    avg_daily_return: float
    daily_volatility: float
    
    # Exposure
    total_commission: Decimal
    total_slippage: Decimal
    avg_time_in_market: float
    
    # Risk-adjusted
    value_at_risk_95: float  # 95% VaR
    conditional_var_95: float  # 95% CVaR
    
    @classmethod
    def calculate(cls, equity_curve: 'EquityCurve', trades: List[Trade], 
                  initial_capital: Decimal, risk_free_rate: float = 0.02) -> 'PerformanceMetrics':
        """
        Calculate all performance metrics
        
        Args:
            equity_curve: Equity curve with daily values
            trades: List of completed trades
            initial_capital: Initial capital
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            PerformanceMetrics object
        """
        df = equity_curve.to_dataframe()
        
        if len(df) < 2:
            # Not enough data for meaningful metrics
            return cls._empty_metrics()
        
        # Calculate returns
        returns = df['equity'].pct_change().dropna()
        cumulative_returns = (df['equity'] / float(initial_capital)) - 1
        
        total_return = float(cumulative_returns.iloc[-1])
        
        # Annualized return
        trading_days = len(df)
        years = trading_days / 252  # 252 trading days per year
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0.0
        
        # Drawdown analysis
        dd_analyzer = DrawdownAnalyzer(equity_curve)
        max_dd, max_dd_duration = dd_analyzer.get_max_drawdown()
        
        # Risk metrics
        daily_returns = returns.values
        if len(daily_returns) > 1:
            daily_vol = float(np.std(daily_returns))
            annual_vol = daily_vol * np.sqrt(252)
            
            # Sharpe ratio
            if annual_vol > 0:
                excess_return = annualized_return - risk_free_rate
                sharpe = excess_return / annual_vol
            else:
                sharpe = 0.0
            
            # Sortino ratio (downside deviation)
            downside_returns = daily_returns[daily_returns < 0]
            if len(downside_returns) > 0:
                downside_vol = float(np.std(downside_returns))
                downside_annual_vol = downside_vol * np.sqrt(252)
                if downside_annual_vol > 0:
                    sortino = (annualized_return - risk_free_rate) / downside_annual_vol
                else:
                    sortino = 0.0
            else:
                sortino = sharpe  # No downside
            
            # Calmar ratio
            if abs(max_dd) > 0:
                calmar = annualized_return / abs(max_dd)
            else:
                calmar = 0.0
        else:
            daily_vol = 0.0
            sharpe = 0.0
            sortino = 0.0
            calmar = 0.0
        
        # Trade statistics
        if trades:
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl <= 0]
            
            total_trades = len(trades)
            num_wins = len(winning_trades)
            num_losses = len(losing_trades)
            win_rate = num_wins / total_trades if total_trades > 0 else 0.0
            
            avg_win = float(np.mean([float(t.pnl) for t in winning_trades])) if winning_trades else 0.0
            avg_loss = float(np.mean([float(t.pnl) for t in losing_trades])) if losing_trades else 0.0
            
            if avg_loss != 0:
                avg_win_loss_ratio = abs(avg_win / avg_loss)
            else:
                avg_win_loss_ratio = 0.0
            
            largest_win = float(max([t.pnl for t in trades])) if trades else 0.0
            largest_loss = float(min([t.pnl for t in trades])) if trades else 0.0
            
            total_commission = sum([t.commission for t in trades])
            total_slippage = sum([t.slippage for t in trades])
            
            # Average time in market (hours)
            trade_durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in trades]
            avg_time_in_market = float(np.mean(trade_durations))
        else:
            total_trades = 0
            num_wins = 0
            num_losses = 0
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            avg_win_loss_ratio = 0.0
            largest_win = 0.0
            largest_loss = 0.0
            total_commission = Decimal('0')
            total_slippage = Decimal('0')
            avg_time_in_market = 0.0
        
        # Period metrics
        best_day = float(returns.max()) if len(returns) > 0 else 0.0
        worst_day = float(returns.min()) if len(returns) > 0 else 0.0
        avg_daily_return = float(returns.mean()) if len(returns) > 0 else 0.0
        
        # Value at Risk (VaR) and Conditional VaR (CVaR)
        if len(daily_returns) > 0:
            var_95 = float(np.percentile(daily_returns, 5))  # 5th percentile
            cvar_95 = float(np.mean(daily_returns[daily_returns <= var_95]))
        else:
            var_95 = 0.0
            cvar_95 = 0.0
        
        return cls(
            total_return=total_return,
            annualized_return=annualized_return,
            cumulative_return=total_return,
            max_drawdown=max_dd,
            max_drawdown_duration_days=max_dd_duration,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            total_trades=total_trades,
            winning_trades=num_wins,
            losing_trades=num_losses,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_win_loss_ratio=avg_win_loss_ratio,
            largest_win=largest_win,
            largest_loss=largest_loss,
            best_day=best_day,
            worst_day=worst_day,
            avg_daily_return=avg_daily_return,
            daily_volatility=daily_vol,
            total_commission=total_commission,
            total_slippage=total_slippage,
            avg_time_in_market=avg_time_in_market,
            value_at_risk_95=var_95,
            conditional_var_95=cvar_95
        )
    
    @classmethod
    def _empty_metrics(cls) -> 'PerformanceMetrics':
        """Return empty metrics when insufficient data"""
        return cls(
            total_return=0.0, annualized_return=0.0, cumulative_return=0.0,
            max_drawdown=0.0, max_drawdown_duration_days=0,
            sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, avg_win=0.0, avg_loss=0.0, avg_win_loss_ratio=0.0,
            largest_win=0.0, largest_loss=0.0,
            best_day=0.0, worst_day=0.0, avg_daily_return=0.0, daily_volatility=0.0,
            total_commission=Decimal('0'), total_slippage=Decimal('0'),
            avg_time_in_market=0.0, value_at_risk_95=0.0, conditional_var_95=0.0
        )
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for easy display"""
        return {
            'Total Return': f"{self.total_return:.2%}",
            'Annualized Return': f"{self.annualized_return:.2%}",
            'Max Drawdown': f"{self.max_drawdown:.2%}",
            'Max DD Duration (days)': self.max_drawdown_duration_days,
            'Sharpe Ratio': f"{self.sharpe_ratio:.2f}",
            'Sortino Ratio': f"{self.sortino_ratio:.2f}",
            'Calmar Ratio': f"{self.calmar_ratio:.2f}",
            'Total Trades': self.total_trades,
            'Win Rate': f"{self.win_rate:.2%}",
            'Avg Win': f"${self.avg_win:.2f}",
            'Avg Loss': f"${self.avg_loss:.2f}",
            'Win/Loss Ratio': f"{self.avg_win_loss_ratio:.2f}",
            'Largest Win': f"${self.largest_win:.2f}",
            'Largest Loss': f"${self.largest_loss:.2f}",
            'Best Day': f"{self.best_day:.2%}",
            'Worst Day': f"{self.worst_day:.2%}",
            'Avg Daily Return': f"{self.avg_daily_return:.4%}",
            'Daily Volatility': f"{self.daily_volatility:.4%}",
            'Total Commission': f"${self.total_commission:.2f}",
            'Total Slippage': f"${self.total_slippage:.2f}",
            'Avg Time in Market (hours)': f"{self.avg_time_in_market:.1f}",
            'VaR (95%)': f"{self.value_at_risk_95:.2%}",
            'CVaR (95%)': f"{self.conditional_var_95:.2%}",
        }


class EquityCurve:
    """
    Tracks portfolio equity over time
    """
    
    def __init__(self, initial_capital: Decimal):
        """
        Args:
            initial_capital: Starting capital
        """
        self.initial_capital = initial_capital
        self.timestamps: List[datetime] = []
        self.equity_values: List[Decimal] = []
        self.cash_values: List[Decimal] = []
        self.position_values: List[Decimal] = []
    
    def add_point(self, timestamp: datetime, equity: Decimal, 
                  cash: Decimal, position_value: Decimal) -> None:
        """Add a point to the equity curve"""
        self.timestamps.append(timestamp)
        self.equity_values.append(equity)
        self.cash_values.append(cash)
        self.position_values.append(position_value)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert equity curve to DataFrame"""
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'equity': [float(e) for e in self.equity_values],
            'cash': [float(c) for c in self.cash_values],
            'position_value': [float(p) for p in self.position_values]
        }).set_index('timestamp')
    
    def get_current_equity(self) -> Decimal:
        """Get current equity value"""
        if not self.equity_values:
            return self.initial_capital
        return self.equity_values[-1]
    
    def get_return(self) -> float:
        """Get total return"""
        if not self.equity_values:
            return 0.0
        return float((self.equity_values[-1] / self.initial_capital) - 1)


class DrawdownAnalyzer:
    """
    Analyzes drawdowns in equity curve
    """
    
    def __init__(self, equity_curve: EquityCurve):
        """
        Args:
            equity_curve: Equity curve to analyze
        """
        self.equity_curve = equity_curve
    
    def calculate_drawdown_series(self) -> pd.Series:
        """
        Calculate drawdown at each point in time
        
        Returns:
            Series of drawdown percentages (negative values)
        """
        df = self.equity_curve.to_dataframe()
        if len(df) == 0:
            return pd.Series()
        
        # Calculate running maximum
        running_max = df['equity'].expanding().max()
        
        # Calculate drawdown
        drawdown = (df['equity'] - running_max) / running_max
        
        return drawdown
    
    def get_max_drawdown(self) -> Tuple[float, int]:
        """
        Get maximum drawdown and its duration
        
        Returns:
            Tuple of (max_drawdown, duration_days)
        """
        drawdown_series = self.calculate_drawdown_series()
        
        if len(drawdown_series) == 0:
            return 0.0, 0
        
        max_dd = float(drawdown_series.min())
        
        # Find duration of max drawdown
        df = self.equity_curve.to_dataframe()
        running_max = df['equity'].expanding().max()
        
        # Find all drawdown periods
        in_drawdown = df['equity'] < running_max
        
        # Calculate duration of longest drawdown period
        max_duration = 0
        current_duration = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_dd, max_duration
    
    def get_drawdown_periods(self) -> List[Dict]:
        """
        Get all drawdown periods
        
        Returns:
            List of dicts with start, end, duration, magnitude
        """
        df = self.equity_curve.to_dataframe()
        if len(df) == 0:
            return []
        
        running_max = df['equity'].expanding().max()
        in_drawdown = df['equity'] < running_max
        
        periods = []
        start_idx = None
        
        for idx, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                # Start of drawdown
                start_idx = idx
            elif not is_dd and start_idx is not None:
                # End of drawdown
                dd_series = df['equity'].iloc[start_idx:idx]
                magnitude = float((dd_series.min() - running_max.iloc[start_idx]) / 
                                 running_max.iloc[start_idx])
                
                periods.append({
                    'start': df.index[start_idx],
                    'end': df.index[idx - 1],
                    'duration_days': idx - start_idx,
                    'magnitude': magnitude
                })
                start_idx = None
        
        # Handle case where drawdown extends to end
        if start_idx is not None:
            dd_series = df['equity'].iloc[start_idx:]
            magnitude = float((dd_series.min() - running_max.iloc[start_idx]) / 
                             running_max.iloc[start_idx])
            
            periods.append({
                'start': df.index[start_idx],
                'end': df.index[-1],
                'duration_days': len(df) - start_idx,
                'magnitude': magnitude
            })
        
        return periods
