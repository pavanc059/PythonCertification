"""
Tests for Walk-Forward Optimization

Tests parameter optimization and out-of-sample validation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

from stockiq.backtesting import (
    BacktestEngine,
    BacktestConfig,
    WalkForwardOptimizer,
    MarketOrder,
    OrderSide,
)


@pytest.fixture
def long_market_data():
    """Generate longer market data for walk-forward testing"""
    # Generate 2 years of data
    dates = pd.date_range('2022-01-01', '2023-12-31', freq='D')
    
    data = []
    for i, date in enumerate(dates):
        # Add some volatility
        price = 100 + i * 0.1 + np.random.randn() * 2
        data.append({
            'timestamp': date,
            'ticker': 'TEST',
            'open': price - 0.5,
            'high': price + 1.0,
            'low': price - 1.0,
            'close': price,
            'volume': 1000000,
            'bid': price - 0.05,
            'ask': price + 0.05
        })
    
    return pd.DataFrame(data)


class TestWalkForwardOptimizer:
    """Test walk-forward optimization"""
    
    def test_window_creation(self, long_market_data):
        """Test creation of optimization windows"""
        config = BacktestConfig(initial_capital=Decimal('10000'))
        optimizer = WalkForwardOptimizer(
            config=config,
            in_sample_days=252,  # 1 year
            out_sample_days=63,  # 3 months
            step_days=63  # Move forward 3 months
        )
        
        start_date = long_market_data['timestamp'].min()
        end_date = long_market_data['timestamp'].max()
        
        windows = optimizer.create_windows(start_date, end_date)
        
        assert len(windows) > 0
        
        # Check window structure
        for window in windows:
            assert window.in_sample_start < window.in_sample_end
            assert window.out_sample_start > window.in_sample_end
            assert window.out_sample_end > window.out_sample_start
    
    def test_simple_optimization(self, long_market_data):
        """Test simple parameter optimization"""
        config = BacktestConfig(initial_capital=Decimal('10000'))
        optimizer = WalkForwardOptimizer(
            config=config,
            in_sample_days=252,
            out_sample_days=63,
            step_days=126  # Larger step for faster test
        )
        
        # Simple moving average crossover strategy
        def sma_strategy(timestamp, market_data, params):
            # This is a simplified strategy for testing
            # In practice, you'd track SMA history
            return []
        
        # Parameter grid
        param_grid = {
            'short_period': [10, 20],
            'long_period': [50, 100]
        }
        
        # Run optimization (this will take a while)
        result = optimizer.optimize(
            market_data=long_market_data,
            strategy_func=sma_strategy,
            param_grid=param_grid,
            optimization_metric='sharpe_ratio'
        )
        
        assert len(result.window_results) > 0
        assert result.combined_out_sample_metrics is not None
        assert result.parameter_stability is not None
    
    def test_parameter_stability(self, long_market_data):
        """Test parameter stability calculation"""
        config = BacktestConfig(initial_capital=Decimal('10000'))
        optimizer = WalkForwardOptimizer(
            config=config,
            in_sample_days=180,
            out_sample_days=60,
            step_days=60
        )
        
        # Simple strategy
        def simple_strategy(timestamp, market_data, params):
            return []
        
        param_grid = {
            'threshold': [0.5, 1.0, 1.5]
        }
        
        result = optimizer.optimize(
            market_data=long_market_data,
            strategy_func=simple_strategy,
            param_grid=param_grid
        )
        
        # Check parameter stability
        assert 'threshold' in result.parameter_stability
        assert result.parameter_stability['threshold'] >= 0


class TestGridSearch:
    """Test simple grid search optimization"""
    
    def test_grid_search(self, long_market_data):
        """Test grid search finds best parameters"""
        from stockiq.backtesting.optimization import grid_search
        
        config = BacktestConfig(initial_capital=Decimal('10000'))
        engine = BacktestEngine(config)
        
        # Simple strategy with parameters
        def parameterized_strategy(timestamp, market_data, params):
            # Dummy strategy that doesn't actually use params
            return []
        
        param_grid = {
            'param1': [1, 2, 3],
            'param2': [10, 20, 30]
        }
        
        # Use subset of data for speed
        subset_data = long_market_data.head(100)
        
        result = grid_search(
            engine=engine,
            market_data=subset_data,
            strategy_func=parameterized_strategy,
            param_grid=param_grid,
            optimization_metric='sharpe_ratio'
        )
        
        assert 'best_params' in result
        assert 'best_value' in result
        assert 'metrics' in result
        assert 'param1' in result['best_params']
        assert 'param2' in result['best_params']


class TestOptimizationMetrics:
    """Test optimization with different metrics"""
    
    def test_optimize_sharpe_ratio(self, long_market_data):
        """Test optimizing for Sharpe ratio"""
        config = BacktestConfig(initial_capital=Decimal('10000'))
        engine = BacktestEngine(config)
        
        # Buy and hold strategy
        def buy_hold_strategy(timestamp, market_data):
            # Only buy on first day
            if timestamp == long_market_data['timestamp'].min():
                return [MarketOrder('TEST', OrderSide.BUY, 10, timestamp)]
            return []
        
        subset_data = long_market_data.head(100)
        metrics = engine.run(subset_data, buy_hold_strategy)
        
        # Sharpe ratio should be calculated
        assert hasattr(metrics, 'sharpe_ratio')
    
    def test_optimize_total_return(self, long_market_data):
        """Test optimizing for total return"""
        config = BacktestConfig(initial_capital=Decimal('10000'))
        engine = BacktestEngine(config)
        
        def buy_hold_strategy(timestamp, market_data):
            if timestamp == long_market_data['timestamp'].min():
                return [MarketOrder('TEST', OrderSide.BUY, 10, timestamp)]
            return []
        
        subset_data = long_market_data.head(100)
        metrics = engine.run(subset_data, buy_hold_strategy)
        
        # Total return should be calculated
        assert hasattr(metrics, 'total_return')


def test_optimization_window_structure():
    """Test OptimizationWindow dataclass"""
    from stockiq.backtesting.optimization import OptimizationWindow
    
    window = OptimizationWindow(
        window_id=0,
        in_sample_start=datetime(2024, 1, 1),
        in_sample_end=datetime(2024, 6, 30),
        out_sample_start=datetime(2024, 7, 1),
        out_sample_end=datetime(2024, 9, 30)
    )
    
    assert window.window_id == 0
    assert window.in_sample_period == (datetime(2024, 1, 1), datetime(2024, 6, 30))
    assert window.out_sample_period == (datetime(2024, 7, 1), datetime(2024, 9, 30))


def test_walk_forward_result_average_params():
    """Test WalkForwardResult average parameter calculation"""
    from stockiq.backtesting.optimization import WalkForwardResult, OptimizationResult, OptimizationWindow
    from stockiq.backtesting.performance import PerformanceMetrics
    
    # Create mock window results
    window1 = OptimizationWindow(
        window_id=0,
        in_sample_start=datetime(2024, 1, 1),
        in_sample_end=datetime(2024, 6, 30),
        out_sample_start=datetime(2024, 7, 1),
        out_sample_end=datetime(2024, 9, 30)
    )
    
    result1 = OptimizationResult(
        window=window1,
        best_params={'param1': 10, 'param2': 20},
        in_sample_metrics=PerformanceMetrics._empty_metrics(),
        out_sample_metrics=PerformanceMetrics._empty_metrics(),
        all_param_results=[]
    )
    
    window2 = OptimizationWindow(
        window_id=1,
        in_sample_start=datetime(2024, 4, 1),
        in_sample_end=datetime(2024, 9, 30),
        out_sample_start=datetime(2024, 10, 1),
        out_sample_end=datetime(2024, 12, 31)
    )
    
    result2 = OptimizationResult(
        window=window2,
        best_params={'param1': 20, 'param2': 30},
        in_sample_metrics=PerformanceMetrics._empty_metrics(),
        out_sample_metrics=PerformanceMetrics._empty_metrics(),
        all_param_results=[]
    )
    
    wf_result = WalkForwardResult(
        window_results=[result1, result2],
        combined_out_sample_metrics=PerformanceMetrics._empty_metrics(),
        parameter_stability={}
    )
    
    avg_params = wf_result.get_average_params()
    
    assert avg_params['param1'] == 15.0  # (10 + 20) / 2
    assert avg_params['param2'] == 25.0  # (20 + 30) / 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
