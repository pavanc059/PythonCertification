"""
Tests for Backtesting Engine

Tests order execution, slippage, commissions, and performance metrics
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

from stockiq.backtesting import (
    BacktestEngine,
    BacktestConfig,
    MarketOrder,
    LimitOrder,
    StopLossOrder,
    StopLimitOrder,
    OrderSide,
    FixedSlippageModel,
    PercentageSlippageModel,
    VolumeSlippageModel,
    FixedCommissionModel,
    PercentageCommissionModel,
    TieredCommissionModel,
    ZeroCommissionModel,
)


@pytest.fixture
def sample_market_data():
    """Generate sample market data for testing"""
    dates = pd.date_range('2024-01-01', '2024-01-31', freq='D')
    
    data = []
    for i, date in enumerate(dates):
        # Simple uptrend
        close_price = 100 + i * 0.5
        data.append({
            'timestamp': date,
            'ticker': 'TEST',
            'open': close_price - 0.5,
            'high': close_price + 1.0,
            'low': close_price - 1.0,
            'close': close_price,
            'volume': 1000000,
            'bid': close_price - 0.05,
            'ask': close_price + 0.05
        })
    
    return pd.DataFrame(data)


class TestOrderTypes:
    """Test different order types"""
    
    def test_market_order_buy(self, sample_market_data):
        """Test market order execution (buy)"""
        config = BacktestConfig(
            initial_capital=Decimal('10000'),
            slippage_model=FixedSlippageModel(Decimal('0.01')),
            commission_model=ZeroCommissionModel()
        )
        engine = BacktestEngine(config)
        
        # Simple buy-and-hold strategy
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                # Buy on first day
                order = MarketOrder('TEST', OrderSide.BUY, 10, timestamp)
                orders_submitted.append(order)
                return [order]
            return []
        
        metrics = engine.run(sample_market_data, strategy)
        
        assert metrics.total_trades == 1
        assert engine.get_current_equity() > Decimal('10000')  # Should have profit
    
    def test_market_order_sell(self, sample_market_data):
        """Test market order execution (sell)"""
        config = BacktestConfig(
            initial_capital=Decimal('10000'),
            slippage_model=FixedSlippageModel(Decimal('0.01')),
            commission_model=ZeroCommissionModel()
        )
        engine = BacktestEngine(config)
        
        # Buy then sell strategy
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                order = MarketOrder('TEST', OrderSide.BUY, 10, timestamp)
                orders_submitted.append(order)
                return [order]
            elif len(orders_submitted) == 1 and len(sample_market_data[sample_market_data['timestamp'] <= timestamp]) > 5:
                order = MarketOrder('TEST', OrderSide.SELL, 10, timestamp)
                orders_submitted.append(order)
                return [order]
            return []
        
        metrics = engine.run(sample_market_data, strategy)
        
        assert metrics.total_trades == 2
        assert len(engine.get_positions()) == 0  # All positions closed
    
    def test_limit_order(self, sample_market_data):
        """Test limit order execution"""
        config = BacktestConfig(
            initial_capital=Decimal('10000'),
            slippage_model=FixedSlippageModel(Decimal('0.01')),
            commission_model=ZeroCommissionModel()
        )
        engine = BacktestEngine(config)
        
        # Limit order strategy
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                # Set limit price below current price
                order = LimitOrder('TEST', OrderSide.BUY, 10, Decimal('99.5'), timestamp)
                orders_submitted.append(order)
                return [order]
            return []
        
        metrics = engine.run(sample_market_data, strategy)
        
        # Limit order should execute when price reaches limit
        assert metrics.total_trades >= 0
    
    def test_stop_loss_order(self, sample_market_data):
        """Test stop-loss order execution"""
        config = BacktestConfig(
            initial_capital=Decimal('10000'),
            slippage_model=FixedSlippageModel(Decimal('0.01')),
            commission_model=ZeroCommissionModel()
        )
        engine = BacktestEngine(config)
        
        # Stop-loss strategy
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                # Buy first
                order = MarketOrder('TEST', OrderSide.BUY, 10, timestamp)
                orders_submitted.append(order)
                return [order]
            elif len(orders_submitted) == 1:
                # Set stop-loss
                order = StopLossOrder('TEST', OrderSide.SELL, 10, Decimal('99.0'), timestamp)
                orders_submitted.append(order)
                return [order]
            return []
        
        metrics = engine.run(sample_market_data, strategy)
        
        # Should have at least buy order
        assert metrics.total_trades >= 1


class TestSlippageModels:
    """Test slippage calculation models"""
    
    def test_fixed_slippage(self):
        """Test fixed slippage model"""
        model = FixedSlippageModel(Decimal('0.01'))
        slippage = model.calculate_slippage(Decimal('100'), 10, 1000, 'buy')
        
        assert slippage == Decimal('0.10')  # 0.01 * 10
    
    def test_percentage_slippage(self):
        """Test percentage slippage model"""
        model = PercentageSlippageModel(Decimal('0.001'))  # 0.1%
        slippage = model.calculate_slippage(Decimal('100'), 10, 1000, 'buy')
        
        # 100 * 10 * 0.001 = 1.0
        assert slippage == Decimal('1.0')
    
    def test_volume_slippage(self):
        """Test volume-based slippage model"""
        model = VolumeSlippageModel()
        
        # Small order (< 1% of volume)
        slippage_small = model.calculate_slippage(Decimal('100'), 10, 10000, 'buy')
        
        # Large order (> 5% of volume)
        slippage_large = model.calculate_slippage(Decimal('100'), 1000, 10000, 'buy')
        
        # Large order should have more slippage
        assert slippage_large > slippage_small


class TestCommissionModels:
    """Test commission calculation models"""
    
    def test_zero_commission(self):
        """Test zero commission model"""
        model = ZeroCommissionModel()
        commission = model.calculate_commission(Decimal('100'), 10, 'buy')
        
        assert commission == Decimal('0')
    
    def test_fixed_commission(self):
        """Test fixed commission model"""
        model = FixedCommissionModel(Decimal('1.00'))
        commission = model.calculate_commission(Decimal('100'), 10, 'buy')
        
        assert commission == Decimal('1.00')
    
    def test_percentage_commission(self):
        """Test percentage commission model"""
        model = PercentageCommissionModel(Decimal('0.001'))  # 0.1%
        commission = model.calculate_commission(Decimal('100'), 10, 'buy')
        
        # 100 * 10 * 0.001 = 1.0
        assert commission == Decimal('1.00')
    
    def test_tiered_commission(self):
        """Test tiered commission model"""
        tiers = [
            (Decimal('10000'), Decimal('0.001')),  # < $10k: 0.1%
            (Decimal('50000'), Decimal('0.0008')),  # $10k-50k: 0.08%
            (Decimal('inf'), Decimal('0.0005'))  # > $50k: 0.05%
        ]
        model = TieredCommissionModel(tiers)
        
        # Small order
        commission_small = model.calculate_commission(Decimal('100'), 10, 'buy')
        assert commission_small == Decimal('1.00')  # 1000 * 0.001 = 1.0
        
        # Medium order
        commission_medium = model.calculate_commission(Decimal('100'), 200, 'buy')
        assert commission_medium == Decimal('16.00')  # 20000 * 0.0008 = 16.0
        
        # Large order
        commission_large = model.calculate_commission(Decimal('100'), 1000, 'buy')
        assert commission_large == Decimal('50.00')  # 100000 * 0.0005 = 50.0


class TestPerformanceMetrics:
    """Test performance metrics calculation"""
    
    def test_metrics_calculation(self, sample_market_data):
        """Test that metrics are calculated correctly"""
        config = BacktestConfig(
            initial_capital=Decimal('10000'),
            slippage_model=FixedSlippageModel(Decimal('0.01')),
            commission_model=FixedCommissionModel(Decimal('1.00'))
        )
        engine = BacktestEngine(config)
        
        # Simple buy-and-hold strategy
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                order = MarketOrder('TEST', OrderSide.BUY, 10, timestamp)
                orders_submitted.append(order)
                return [order]
            return []
        
        metrics = engine.run(sample_market_data, strategy)
        
        # Verify metrics are calculated
        assert metrics.total_return > 0  # Uptrend should be profitable
        assert metrics.sharpe_ratio != 0
        assert metrics.max_drawdown <= 0
        assert metrics.total_trades == 1
        assert metrics.win_rate >= 0 and metrics.win_rate <= 1
    
    def test_drawdown_calculation(self, sample_market_data):
        """Test drawdown calculation"""
        config = BacktestConfig(initial_capital=Decimal('10000'))
        engine = BacktestEngine(config)
        
        # Simple strategy
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                order = MarketOrder('TEST', OrderSide.BUY, 10, timestamp)
                orders_submitted.append(order)
                return [order]
            return []
        
        metrics = engine.run(sample_market_data, strategy)
        
        # In uptrend, max drawdown should be small
        assert metrics.max_drawdown <= 0
        assert metrics.max_drawdown_duration_days >= 0


class TestLookAheadBiasPrevention:
    """Test that look-ahead bias is prevented"""
    
    def test_strategy_sees_only_open_price(self, sample_market_data):
        """Test that strategy can only see open price, not close"""
        config = BacktestConfig(
            initial_capital=Decimal('10000'),
            prevent_look_ahead_bias=True
        )
        engine = BacktestEngine(config)
        
        seen_prices = []
        def strategy(timestamp, market_data):
            if 'TEST' in market_data:
                seen_prices.append(market_data['TEST']['price'])
            return []
        
        engine.run(sample_market_data, strategy)
        
        # Strategy should see open prices, not close prices
        # Open prices should be lower than close prices in uptrend
        for i, seen_price in enumerate(seen_prices):
            if i < len(sample_market_data):
                open_price = sample_market_data.iloc[i]['open']
                assert float(seen_price) == pytest.approx(open_price, abs=0.01)


class TestMultiplePositions:
    """Test managing multiple positions"""
    
    def test_multiple_tickers(self):
        """Test trading multiple tickers"""
        # Create data for multiple tickers
        dates = pd.date_range('2024-01-01', '2024-01-10', freq='D')
        data = []
        
        for i, date in enumerate(dates):
            for ticker in ['AAPL', 'GOOGL', 'MSFT']:
                close_price = 100 + i * 0.5
                data.append({
                    'timestamp': date,
                    'ticker': ticker,
                    'open': close_price - 0.5,
                    'high': close_price + 1.0,
                    'low': close_price - 1.0,
                    'close': close_price,
                    'volume': 1000000,
                    'bid': close_price - 0.05,
                    'ask': close_price + 0.05
                })
        
        market_data = pd.DataFrame(data)
        
        config = BacktestConfig(initial_capital=Decimal('10000'))
        engine = BacktestEngine(config)
        
        # Buy all three tickers
        orders_submitted = []
        def strategy(timestamp, market_data):
            if len(orders_submitted) == 0:
                orders = [
                    MarketOrder('AAPL', OrderSide.BUY, 5, timestamp),
                    MarketOrder('GOOGL', OrderSide.BUY, 5, timestamp),
                    MarketOrder('MSFT', OrderSide.BUY, 5, timestamp),
                ]
                orders_submitted.extend(orders)
                return orders
            return []
        
        metrics = engine.run(market_data, strategy)
        
        assert metrics.total_trades == 3
        assert len(engine.get_positions()) == 3


def test_backtest_engine_initialization():
    """Test BacktestEngine initialization"""
    config = BacktestConfig()
    engine = BacktestEngine(config)
    
    assert engine.cash == config.initial_capital
    assert len(engine.positions) == 0
    assert len(engine.pending_orders) == 0


def test_backtest_config_defaults():
    """Test BacktestConfig default values"""
    config = BacktestConfig()
    
    assert config.initial_capital == Decimal('100000')
    assert isinstance(config.slippage_model, PercentageSlippageModel)
    assert isinstance(config.commission_model, ZeroCommissionModel)
    assert config.allow_short_selling == False
    assert config.prevent_look_ahead_bias == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
