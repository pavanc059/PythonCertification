"""
Walk-Forward Optimization

Implements walk-forward optimization with out-of-sample testing to prevent overfitting
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Callable, Any, Optional
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

from .engine import BacktestEngine, BacktestConfig
from .performance import PerformanceMetrics


@dataclass
class OptimizationWindow:
    """
    Represents a single optimization window
    """
    window_id: int
    in_sample_start: datetime
    in_sample_end: datetime
    out_sample_start: datetime
    out_sample_end: datetime
    
    @property
    def in_sample_period(self) -> Tuple[datetime, datetime]:
        """Get in-sample period"""
        return (self.in_sample_start, self.in_sample_end)
    
    @property
    def out_sample_period(self) -> Tuple[datetime, datetime]:
        """Get out-of-sample period"""
        return (self.out_sample_start, self.out_sample_end)


@dataclass
class OptimizationResult:
    """
    Result of parameter optimization for one window
    """
    window: OptimizationWindow
    best_params: Dict[str, Any]
    in_sample_metrics: PerformanceMetrics
    out_sample_metrics: PerformanceMetrics
    all_param_results: List[Dict[str, Any]]


@dataclass
class WalkForwardResult:
    """
    Complete walk-forward optimization result
    """
    window_results: List[OptimizationResult]
    combined_out_sample_metrics: PerformanceMetrics
    parameter_stability: Dict[str, float]  # Std dev of each parameter across windows
    
    def get_average_params(self) -> Dict[str, Any]:
        """Get average parameter values across all windows"""
        if not self.window_results:
            return {}
        
        param_values = {}
        for result in self.window_results:
            for param_name, param_value in result.best_params.items():
                if param_name not in param_values:
                    param_values[param_name] = []
                param_values[param_name].append(param_value)
        
        # Calculate average
        avg_params = {}
        for param_name, values in param_values.items():
            if isinstance(values[0], (int, float)):
                avg_params[param_name] = np.mean(values)
            else:
                # For non-numeric parameters, use most common value
                avg_params[param_name] = max(set(values), key=values.count)
        
        return avg_params


class WalkForwardOptimizer:
    """
    Walk-forward optimization engine
    
    Divides historical data into overlapping windows:
    - In-sample (IS): Used for parameter optimization
    - Out-of-sample (OOS): Used for validation
    
    Process:
    1. Optimize parameters on IS data
    2. Test optimized parameters on OOS data
    3. Move window forward and repeat
    4. Combine OOS results for overall performance
    
    This prevents overfitting by ensuring parameters are tested on unseen data.
    """
    
    def __init__(self, config: BacktestConfig,
                 in_sample_days: int = 252,  # 1 year
                 out_sample_days: int = 63,  # 3 months
                 step_days: int = 63,  # Move forward 3 months each time
                 n_jobs: int = 1):
        """
        Args:
            config: Backtest configuration
            in_sample_days: Number of days for in-sample optimization
            out_sample_days: Number of days for out-of-sample testing
            step_days: Number of days to move forward each window
            n_jobs: Number of parallel jobs for optimization (-1 = all CPUs)
        """
        self.config = config
        self.in_sample_days = in_sample_days
        self.out_sample_days = out_sample_days
        self.step_days = step_days
        self.n_jobs = n_jobs
    
    def create_windows(self, start_date: datetime, end_date: datetime) -> List[OptimizationWindow]:
        """
        Create optimization windows
        
        Args:
            start_date: Start date of historical data
            end_date: End date of historical data
            
        Returns:
            List of OptimizationWindow objects
        """
        windows = []
        window_id = 0
        
        current_start = start_date
        
        while True:
            is_start = current_start
            is_end = is_start + timedelta(days=self.in_sample_days)
            
            oos_start = is_end + timedelta(days=1)
            oos_end = oos_start + timedelta(days=self.out_sample_days)
            
            # Check if we have enough data
            if oos_end > end_date:
                break
            
            window = OptimizationWindow(
                window_id=window_id,
                in_sample_start=is_start,
                in_sample_end=is_end,
                out_sample_start=oos_start,
                out_sample_end=oos_end
            )
            windows.append(window)
            
            # Move forward
            current_start += timedelta(days=self.step_days)
            window_id += 1
        
        return windows
    
    def optimize(self, 
                 market_data: pd.DataFrame,
                 strategy_func: Callable,
                 param_grid: Dict[str, List[Any]],
                 optimization_metric: str = 'sharpe_ratio') -> WalkForwardResult:
        """
        Run walk-forward optimization
        
        Args:
            market_data: Historical market data
            strategy_func: Strategy function that takes (timestamp, market_data, params)
            param_grid: Dictionary of parameter names to list of values
                       Example: {'sma_period': [20, 50, 100], 'rsi_threshold': [30, 40, 50]}
            optimization_metric: Metric to optimize ('sharpe_ratio', 'total_return', etc.)
            
        Returns:
            WalkForwardResult with optimization results
        """
        # Create windows
        start_date = market_data['timestamp'].min()
        end_date = market_data['timestamp'].max()
        windows = self.create_windows(start_date, end_date)
        
        print(f"Created {len(windows)} optimization windows")
        print(f"In-sample: {self.in_sample_days} days, Out-sample: {self.out_sample_days} days")
        print(f"Step: {self.step_days} days\n")
        
        # Optimize each window
        window_results = []
        for i, window in enumerate(windows):
            print(f"Optimizing window {i+1}/{len(windows)}...")
            result = self._optimize_window(
                window,
                market_data,
                strategy_func,
                param_grid,
                optimization_metric
            )
            window_results.append(result)
            
            print(f"  Best params: {result.best_params}")
            print(f"  IS {optimization_metric}: {getattr(result.in_sample_metrics, optimization_metric):.4f}")
            print(f"  OOS {optimization_metric}: {getattr(result.out_sample_metrics, optimization_metric):.4f}\n")
        
        # Combine out-of-sample results
        combined_oos_metrics = self._combine_oos_metrics(window_results)
        
        # Calculate parameter stability
        param_stability = self._calculate_param_stability(window_results)
        
        return WalkForwardResult(
            window_results=window_results,
            combined_out_sample_metrics=combined_oos_metrics,
            parameter_stability=param_stability
        )
    
    def _optimize_window(self,
                        window: OptimizationWindow,
                        market_data: pd.DataFrame,
                        strategy_func: Callable,
                        param_grid: Dict[str, List[Any]],
                        optimization_metric: str) -> OptimizationResult:
        """Optimize parameters for a single window"""
        
        # Filter data for in-sample period
        is_data = market_data[
            (market_data['timestamp'] >= window.in_sample_start) &
            (market_data['timestamp'] <= window.in_sample_end)
        ]
        
        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(param_grid)
        
        print(f"  Testing {len(param_combinations)} parameter combinations...")
        
        # Test each parameter combination
        results = []
        for params in param_combinations:
            # Create strategy with these parameters
            def parameterized_strategy(timestamp, data):
                return strategy_func(timestamp, data, params)
            
            # Run backtest
            engine = BacktestEngine(self.config)
            metrics = engine.run(is_data, parameterized_strategy)
            
            results.append({
                'params': params,
                'metrics': metrics,
                'optimization_value': getattr(metrics, optimization_metric)
            })
        
        # Find best parameters
        best_result = max(results, key=lambda x: x['optimization_value'])
        best_params = best_result['params']
        in_sample_metrics = best_result['metrics']
        
        # Test best parameters on out-of-sample data
        oos_data = market_data[
            (market_data['timestamp'] >= window.out_sample_start) &
            (market_data['timestamp'] <= window.out_sample_end)
        ]
        
        def best_strategy(timestamp, data):
            return strategy_func(timestamp, data, best_params)
        
        engine = BacktestEngine(self.config)
        out_sample_metrics = engine.run(oos_data, best_strategy)
        
        return OptimizationResult(
            window=window,
            best_params=best_params,
            in_sample_metrics=in_sample_metrics,
            out_sample_metrics=out_sample_metrics,
            all_param_results=results
        )
    
    def _generate_param_combinations(self, param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """Generate all combinations of parameters"""
        if not param_grid:
            return [{}]
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        # Generate Cartesian product
        from itertools import product
        combinations = []
        for values in product(*param_values):
            combination = dict(zip(param_names, values))
            combinations.append(combination)
        
        return combinations
    
    def _combine_oos_metrics(self, window_results: List[OptimizationResult]) -> PerformanceMetrics:
        """
        Combine out-of-sample metrics from all windows
        
        This represents the true performance of the walk-forward strategy
        """
        if not window_results:
            return PerformanceMetrics._empty_metrics()
        
        # Collect all OOS trades
        all_trades = []
        for result in window_results:
            # Note: We would need to extract trades from the backtest engine
            # For now, we'll aggregate the metrics
            pass
        
        # For now, return average metrics
        # In production, we would re-run a combined backtest with switching parameters
        total_return = np.mean([r.out_sample_metrics.total_return for r in window_results])
        sharpe = np.mean([r.out_sample_metrics.sharpe_ratio for r in window_results])
        max_dd = np.mean([r.out_sample_metrics.max_drawdown for r in window_results])
        win_rate = np.mean([r.out_sample_metrics.win_rate for r in window_results])
        
        # Create combined metrics (simplified)
        from decimal import Decimal
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=np.mean([r.out_sample_metrics.annualized_return for r in window_results]),
            cumulative_return=total_return,
            max_drawdown=max_dd,
            max_drawdown_duration_days=int(np.mean([r.out_sample_metrics.max_drawdown_duration_days for r in window_results])),
            sharpe_ratio=sharpe,
            sortino_ratio=np.mean([r.out_sample_metrics.sortino_ratio for r in window_results]),
            calmar_ratio=np.mean([r.out_sample_metrics.calmar_ratio for r in window_results]),
            total_trades=sum([r.out_sample_metrics.total_trades for r in window_results]),
            winning_trades=sum([r.out_sample_metrics.winning_trades for r in window_results]),
            losing_trades=sum([r.out_sample_metrics.losing_trades for r in window_results]),
            win_rate=win_rate,
            avg_win=np.mean([r.out_sample_metrics.avg_win for r in window_results]),
            avg_loss=np.mean([r.out_sample_metrics.avg_loss for r in window_results]),
            avg_win_loss_ratio=np.mean([r.out_sample_metrics.avg_win_loss_ratio for r in window_results]),
            largest_win=max([r.out_sample_metrics.largest_win for r in window_results]),
            largest_loss=min([r.out_sample_metrics.largest_loss for r in window_results]),
            best_day=max([r.out_sample_metrics.best_day for r in window_results]),
            worst_day=min([r.out_sample_metrics.worst_day for r in window_results]),
            avg_daily_return=np.mean([r.out_sample_metrics.avg_daily_return for r in window_results]),
            daily_volatility=np.mean([r.out_sample_metrics.daily_volatility for r in window_results]),
            total_commission=Decimal(str(sum([float(r.out_sample_metrics.total_commission) for r in window_results]))),
            total_slippage=Decimal(str(sum([float(r.out_sample_metrics.total_slippage) for r in window_results]))),
            avg_time_in_market=np.mean([r.out_sample_metrics.avg_time_in_market for r in window_results]),
            value_at_risk_95=np.mean([r.out_sample_metrics.value_at_risk_95 for r in window_results]),
            conditional_var_95=np.mean([r.out_sample_metrics.conditional_var_95 for r in window_results])
        )
    
    def _calculate_param_stability(self, window_results: List[OptimizationResult]) -> Dict[str, float]:
        """
        Calculate stability of parameters across windows
        
        Lower standard deviation = more stable parameters
        """
        if not window_results:
            return {}
        
        param_values = {}
        for result in window_results:
            for param_name, param_value in result.best_params.items():
                if param_name not in param_values:
                    param_values[param_name] = []
                if isinstance(param_value, (int, float)):
                    param_values[param_name].append(param_value)
        
        # Calculate standard deviation for each parameter
        stability = {}
        for param_name, values in param_values.items():
            if values:
                stability[param_name] = float(np.std(values))
        
        return stability


def grid_search(engine: BacktestEngine,
                market_data: pd.DataFrame,
                strategy_func: Callable,
                param_grid: Dict[str, List[Any]],
                optimization_metric: str = 'sharpe_ratio') -> Dict[str, Any]:
    """
    Simple grid search optimization (no walk-forward)
    
    Args:
        engine: BacktestEngine instance
        market_data: Historical market data
        strategy_func: Strategy function
        param_grid: Parameter grid
        optimization_metric: Metric to optimize
        
    Returns:
        Best parameters and metrics
    """
    from itertools import product
    
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    
    best_value = float('-inf')
    best_params = None
    best_metrics = None
    
    for values in product(*param_values):
        params = dict(zip(param_names, values))
        
        def parameterized_strategy(timestamp, data):
            return strategy_func(timestamp, data, params)
        
        metrics = engine.run(market_data, parameterized_strategy)
        value = getattr(metrics, optimization_metric)
        
        if value > best_value:
            best_value = value
            best_params = params
            best_metrics = metrics
    
    return {
        'best_params': best_params,
        'best_value': best_value,
        'metrics': best_metrics
    }
