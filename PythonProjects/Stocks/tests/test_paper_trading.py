"""
Comprehensive tests for paper trading system.

Tests Requirements 16.7-16.10:
- Virtual cash accounts (16.7)
- Real-time price execution (16.8)
- Daily P&L tracking (16.9)
- Benchmark comparison (16.10)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from stockiq.trading import (
    PaperTradingAccount,
    AccountConfig,
    MarketOrder,
    LimitOrder,
    StopLossOrder,
    StopLimitOrder,
    OrderSide,
    OrderStatus,
    Portfolio,
    Position,
    PerformanceMetrics
)


# ==================== ACCOUNT TESTS ====================

class TestPaperTradingAccount:
    """Test paper trading account functionality"""
    
    def test_account_creation(self):
        """Test account creation with default config"""
        account = PaperTradingAccount("test_account_1")
        
        assert account.account_id == "test_account_1"
        assert account.cash == Decimal('100000')
        assert account.initial_cash == Decimal('100000')
        assert len(account.pending_orders) == 0
        assert len(account.completed_orders) == 0
    
    def test_account_creation_with_custom_config(self):
        """Test account creation with custom configuration"""
        config = AccountConfig(
            initial_cash=Decimal('50000'),
            slippage_pct=0.002,
            commission_per_share=Decimal('0.01')
        )
        account = PaperTradingAccount("test_account_2", config)
        
        assert account.cash == Decimal('50000')
        assert account.config.slippage_pct == 0.002
        assert account.config.commission_per_share == Decimal('0.01')
    
    def test_account_summary(self):
        """Test account summary generation"""
        account = PaperTradingAccount("test_account_3")
        summary = account.get_account_summary()
        
        assert summary['account_id'] == "test_account_3"
        assert summary['cash'] == Decimal('100000')
        assert summary['total_value'] == Decimal('100000')
        assert summary['num_positions'] == 0
        assert summary['total_return'] == Decimal('0')
        assert summary['total_return_pct'] == 0.0
    
    def test_buying_power_without_margin(self):
        """Test buying power calculation without margin"""
        account = PaperTradingAccount("test_account_4")
        
        assert account.get_buying_power() == Decimal('100000')
    
    def test_buying_power_with_margin(self):
        """Test buying power calculation with margin"""
        config = AccountConfig(
            initial_cash=Decimal('100000'),
            allow_margin=True,
            margin_multiplier=Decimal('2')
        )
        account = PaperTradingAccount("test_account_5", config)
        
        assert account.get_buying_power() == Decimal('200000')
    
    def test_account_reset(self):
        """Test account reset functionality"""
        account = PaperTradingAccount("test_account_6")
        
        # Modify account state
        account.cash = Decimal('50000')
        account.portfolio.add_position('AAPL', 100, Decimal('150'), datetime.utcnow())
        
        # Reset account
        account.reset()
        
        assert account.cash == account.initial_cash
        assert len(account.portfolio.positions) == 0
        assert len(account.pending_orders) == 0
        assert len(account.completed_orders) == 0


# ==================== ORDER TESTS ====================

class TestOrders:
    """Test order types and execution logic"""
    
    def test_market_order_should_execute(self):
        """Test market order always executes"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        
        assert order.should_execute(
            current_price=Decimal('150'),
            bid=Decimal('149.95'),
            ask=Decimal('150.05')
        )
    
    def test_market_order_buy_execution_price(self):
        """Test market buy order executes at ask"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        
        exec_price = order.get_execution_price(
            current_price=Decimal('150'),
            bid=Decimal('149.95'),
            ask=Decimal('150.05')
        )
        
        assert exec_price == Decimal('150.05')
    
    def test_market_order_sell_execution_price(self):
        """Test market sell order executes at bid"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.SELL, quantity=100)
        
        exec_price = order.get_execution_price(
            current_price=Decimal('150'),
            bid=Decimal('149.95'),
            ask=Decimal('150.05')
        )
        
        assert exec_price == Decimal('149.95')
    
    def test_limit_buy_order_execution_conditions(self):
        """Test limit buy order execution conditions"""
        order = LimitOrder(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            limit_price=Decimal('150')
        )
        
        # Should execute when ask <= limit
        assert order.should_execute(
            current_price=Decimal('149'),
            bid=Decimal('148.95'),
            ask=Decimal('149.05')
        )
        
        # Should not execute when ask > limit
        assert not order.should_execute(
            current_price=Decimal('151'),
            bid=Decimal('150.95'),
            ask=Decimal('151.05')
        )
    
    def test_limit_sell_order_execution_conditions(self):
        """Test limit sell order execution conditions"""
        order = LimitOrder(
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            limit_price=Decimal('150')
        )
        
        # Should execute when bid >= limit
        assert order.should_execute(
            current_price=Decimal('151'),
            bid=Decimal('150.95'),
            ask=Decimal('151.05')
        )
        
        # Should not execute when bid < limit
        assert not order.should_execute(
            current_price=Decimal('149'),
            bid=Decimal('148.95'),
            ask=Decimal('149.05')
        )
    
    def test_stop_loss_buy_order(self):
        """Test stop-loss buy order (buy stop)"""
        order = StopLossOrder(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            stop_price=Decimal('150')
        )
        
        # Should not trigger below stop
        assert not order.should_execute(
            current_price=Decimal('149'),
            bid=Decimal('148.95'),
            ask=Decimal('149.05')
        )
        
        # Should trigger at or above stop
        assert order.should_execute(
            current_price=Decimal('150'),
            bid=Decimal('149.95'),
            ask=Decimal('150.05')
        )
    
    def test_stop_loss_sell_order(self):
        """Test stop-loss sell order (sell stop)"""
        order = StopLossOrder(
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=Decimal('150')
        )
        
        # Should not trigger above stop
        assert not order.should_execute(
            current_price=Decimal('151'),
            bid=Decimal('150.95'),
            ask=Decimal('151.05')
        )
        
        # Should trigger at or below stop
        assert order.should_execute(
            current_price=Decimal('150'),
            bid=Decimal('149.95'),
            ask=Decimal('150.05')
        )
    
    def test_stop_limit_order_triggering(self):
        """Test stop-limit order trigger and execution"""
        order = StopLimitOrder(
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            stop_price=Decimal('150'),
            limit_price=Decimal('149')
        )
        
        # Should not execute above stop
        assert not order.should_execute(
            current_price=Decimal('151'),
            bid=Decimal('150.95'),
            ask=Decimal('151.05')
        )
        
        # Should trigger at stop but not execute if limit not met
        assert not order.should_execute(
            current_price=Decimal('150'),
            bid=Decimal('148.50'),  # Below limit
            ask=Decimal('150.05')
        )
        
        # Should execute when both stop and limit conditions met
        assert order.should_execute(
            current_price=Decimal('149.50'),
            bid=Decimal('149.50'),  # At limit
            ask=Decimal('149.55')
        )
    
    def test_order_fill(self):
        """Test order fill functionality"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        
        order.fill(
            price=Decimal('150'),
            quantity=100,
            timestamp=datetime.utcnow(),
            commission=Decimal('1'),
            slippage=Decimal('0.50')
        )
        
        assert order.status == OrderStatus.FILLED
        assert order.filled_price == Decimal('150')
        assert order.filled_quantity == 100
        assert order.commission == Decimal('1')
        assert order.slippage == Decimal('0.50')
    
    def test_order_partial_fill(self):
        """Test partial order fill"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        
        order.fill(
            price=Decimal('150'),
            quantity=50,  # Partial fill
            timestamp=datetime.utcnow()
        )
        
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == 50
    
    def test_order_cancel(self):
        """Test order cancellation"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        
        order.cancel()
        
        assert order.status == OrderStatus.CANCELLED
    
    def test_order_reject(self):
        """Test order rejection"""
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        
        order.reject()
        
        assert order.status == OrderStatus.REJECTED


# ==================== PORTFOLIO TESTS ====================

class TestPortfolio:
    """Test portfolio tracking and management"""
    
    def test_portfolio_creation(self):
        """Test portfolio initialization"""
        portfolio = Portfolio()
        
        assert len(portfolio.positions) == 0
        assert len(portfolio.closed_positions) == 0
        assert portfolio.get_total_value() == Decimal('0')
    
    def test_add_new_position(self):
        """Test adding a new position"""
        portfolio = Portfolio()
        
        portfolio.add_position(
            ticker="AAPL",
            quantity=100,
            price=Decimal('150'),
            timestamp=datetime.utcnow()
        )
        
        assert len(portfolio.positions) == 1
        position = portfolio.get_position("AAPL")
        assert position.quantity == 100
        assert position.avg_entry_price == Decimal('150')
    
    def test_add_to_existing_position(self):
        """Test adding to an existing position (averaging)"""
        portfolio = Portfolio()
        
        # First purchase
        portfolio.add_position(
            ticker="AAPL",
            quantity=100,
            price=Decimal('150'),
            timestamp=datetime.utcnow()
        )
        
        # Second purchase at different price
        portfolio.add_position(
            ticker="AAPL",
            quantity=100,
            price=Decimal('160'),
            timestamp=datetime.utcnow()
        )
        
        position = portfolio.get_position("AAPL")
        assert position.quantity == 200
        # Average price should be (150*100 + 160*100) / 200 = 155
        assert position.avg_entry_price == Decimal('155')
    
    def test_reduce_position(self):
        """Test reducing a position"""
        portfolio = Portfolio()
        
        portfolio.add_position(
            ticker="AAPL",
            quantity=100,
            price=Decimal('150'),
            timestamp=datetime.utcnow()
        )
        
        # Sell half
        realized_pnl = portfolio.reduce_position(
            ticker="AAPL",
            quantity=50,
            price=Decimal('160'),
            timestamp=datetime.utcnow()
        )
        
        position = portfolio.get_position("AAPL")
        assert position.quantity == 50
        assert realized_pnl == Decimal('500')  # (160 - 150) * 50
        assert len(portfolio.closed_positions) == 1
    
    def test_close_entire_position(self):
        """Test closing an entire position"""
        portfolio = Portfolio()
        
        portfolio.add_position(
            ticker="AAPL",
            quantity=100,
            price=Decimal('150'),
            timestamp=datetime.utcnow()
        )
        
        # Sell all
        realized_pnl = portfolio.reduce_position(
            ticker="AAPL",
            quantity=100,
            price=Decimal('160'),
            timestamp=datetime.utcnow()
        )
        
        assert portfolio.get_position("AAPL") is None
        assert realized_pnl == Decimal('1000')  # (160 - 150) * 100
        assert len(portfolio.closed_positions) == 1
    
    def test_position_market_value(self):
        """Test position market value calculation"""
        position = Position(
            ticker="AAPL",
            quantity=100,
            avg_entry_price=Decimal('150'),
            current_price=Decimal('160'),
            entry_time=datetime.utcnow()
        )
        
        assert position.market_value == Decimal('16000')  # 100 * 160
    
    def test_position_unrealized_pnl(self):
        """Test unrealized P&L calculation"""
        position = Position(
            ticker="AAPL",
            quantity=100,
            avg_entry_price=Decimal('150'),
            current_price=Decimal('160'),
            entry_time=datetime.utcnow()
        )
        
        assert position.unrealized_pnl == Decimal('1000')  # (160 - 150) * 100
        assert position.unrealized_pnl_pct == pytest.approx(0.0666, rel=0.01)
    
    def test_portfolio_total_value(self):
        """Test portfolio total value calculation"""
        portfolio = Portfolio()
        
        portfolio.add_position("AAPL", 100, Decimal('150'), datetime.utcnow())
        portfolio.add_position("GOOGL", 50, Decimal('2800'), datetime.utcnow())
        
        # Update prices
        portfolio.update_prices({
            'AAPL': Decimal('160'),
            'GOOGL': Decimal('2850')
        })
        
        # Total value = 100*160 + 50*2850 = 16000 + 142500 = 158500
        assert portfolio.get_total_value() == Decimal('158500')
    
    def test_portfolio_unrealized_pnl(self):
        """Test portfolio unrealized P&L"""
        portfolio = Portfolio()
        
        portfolio.add_position("AAPL", 100, Decimal('150'), datetime.utcnow())
        portfolio.add_position("GOOGL", 50, Decimal('2800'), datetime.utcnow())
        
        # Update prices
        portfolio.update_prices({
            'AAPL': Decimal('160'),
            'GOOGL': Decimal('2750')
        })
        
        # AAPL unrealized: (160 - 150) * 100 = 1000
        # GOOGL unrealized: (2750 - 2800) * 50 = -2500
        # Total unrealized: 1000 - 2500 = -1500
        assert portfolio.get_unrealized_pnl() == Decimal('-1500')
    
    def test_portfolio_realized_pnl(self):
        """Test portfolio realized P&L"""
        portfolio = Portfolio()
        
        portfolio.add_position("AAPL", 100, Decimal('150'), datetime.utcnow())
        portfolio.reduce_position("AAPL", 100, Decimal('160'), datetime.utcnow())
        
        portfolio.add_position("GOOGL", 50, Decimal('2800'), datetime.utcnow())
        portfolio.reduce_position("GOOGL", 50, Decimal('2750'), datetime.utcnow())
        
        # AAPL realized: (160 - 150) * 100 = 1000
        # GOOGL realized: (2750 - 2800) * 50 = -2500
        # Total realized: 1000 - 2500 = -1500
        assert portfolio.get_realized_pnl() == Decimal('-1500')
    
    def test_daily_snapshot(self):
        """Test daily portfolio snapshot"""
        portfolio = Portfolio()
        
        portfolio.add_position("AAPL", 100, Decimal('150'), datetime.utcnow())
        
        # Update prices with mock data
        portfolio.update_prices({'AAPL': Decimal('160')})
        
        # Take snapshot without updating prices (already updated)
        snapshot = portfolio.take_daily_snapshot(skip_price_update=True)
        
        assert snapshot['total_value'] == Decimal('16000')
        assert snapshot['unrealized_pnl'] == Decimal('1000')
        assert snapshot['num_positions'] == 1
        assert len(snapshot['positions']) == 1


# ==================== PERFORMANCE METRICS TESTS ====================

class TestPerformanceMetrics:
    """Test performance calculation and benchmark comparison"""
    
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation"""
        closed_trades = [
            {
                'ticker': 'AAPL',
                'realized_pnl': Decimal('1000'),
                'realized_pnl_pct': 0.1
            },
            {
                'ticker': 'GOOGL',
                'realized_pnl': Decimal('-500'),
                'realized_pnl_pct': -0.05
            },
            {
                'ticker': 'MSFT',
                'realized_pnl': Decimal('800'),
                'realized_pnl_pct': 0.08
            }
        ]
        
        metrics = PerformanceMetrics.calculate(
            initial_capital=Decimal('100000'),
            current_value=Decimal('105000'),
            previous_value=Decimal('104000'),
            realized_pnl=Decimal('1300'),
            unrealized_pnl=Decimal('3700'),
            closed_trades=closed_trades,
            benchmark_ticker="SPY"
        )
        
        assert metrics.total_return == Decimal('5000')
        assert metrics.total_return_pct == 0.05
        assert metrics.daily_pnl == Decimal('1000')
        assert metrics.daily_pnl_pct == pytest.approx(0.0096, rel=0.01)
        assert metrics.num_trades == 3
        assert metrics.num_winning_trades == 2
        assert metrics.num_losing_trades == 1
        assert metrics.win_rate == pytest.approx(0.6666, rel=0.01)
    
    def test_win_rate_calculation(self):
        """Test win rate calculation"""
        closed_trades = [
            {'realized_pnl': Decimal('100')},
            {'realized_pnl': Decimal('200')},
            {'realized_pnl': Decimal('-50')},
            {'realized_pnl': Decimal('150')},
        ]
        
        metrics = PerformanceMetrics.calculate(
            initial_capital=Decimal('100000'),
            current_value=Decimal('100400'),
            previous_value=Decimal('100300'),
            realized_pnl=Decimal('400'),
            unrealized_pnl=Decimal('0'),
            closed_trades=closed_trades
        )
        
        assert metrics.win_rate == 0.75  # 3 out of 4 trades won
    
    def test_avg_win_loss_calculation(self):
        """Test average win/loss calculation"""
        closed_trades = [
            {'realized_pnl': Decimal('100')},
            {'realized_pnl': Decimal('200')},
            {'realized_pnl': Decimal('-50')},
            {'realized_pnl': Decimal('-30')},
        ]
        
        metrics = PerformanceMetrics.calculate(
            initial_capital=Decimal('100000'),
            current_value=Decimal('100220'),
            previous_value=Decimal('100200'),
            realized_pnl=Decimal('220'),
            unrealized_pnl=Decimal('0'),
            closed_trades=closed_trades
        )
        
        assert metrics.avg_win == Decimal('150')  # (100 + 200) / 2
        assert metrics.avg_loss == Decimal('-40')  # (-50 + -30) / 2


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests for complete trading workflows"""
    
    def test_complete_buy_sell_workflow(self):
        """Test complete workflow: account creation -> buy -> sell"""
        # Create account
        config = AccountConfig(
            initial_cash=Decimal('100000'),
            commission_per_share=Decimal('0'),
            slippage_pct=0
        )
        account = PaperTradingAccount("integration_test", config)
        
        # Mock market data
        market_data = {
            'price': Decimal('150'),
            'bid': Decimal('149.95'),
            'ask': Decimal('150.05'),
            'timestamp': datetime.utcnow()
        }
        
        # Place buy order
        buy_order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=100)
        account.executor.execute_order(buy_order, market_data)
        account._process_filled_order(buy_order)
        
        # Verify position created
        position = account.portfolio.get_position("AAPL")
        assert position is not None
        assert position.quantity == 100
        
        # Verify cash decreased
        expected_cash = Decimal('100000') - (Decimal('150.05') * 100)
        assert account.cash == expected_cash
        
        # Update market price
        market_data['price'] = Decimal('160')
        market_data['bid'] = Decimal('159.95')
        market_data['ask'] = Decimal('160.05')
        
        # Place sell order
        sell_order = MarketOrder(ticker="AAPL", side=OrderSide.SELL, quantity=100)
        account.executor.execute_order(sell_order, market_data)
        account._process_filled_order(sell_order)
        
        # Verify position closed
        assert account.portfolio.get_position("AAPL") is None
        
        # Verify profit realized
        proceeds = Decimal('159.95') * 100
        expected_final_cash = expected_cash + proceeds
        assert account.cash == expected_final_cash
    
    def test_insufficient_funds_rejection(self):
        """Test order rejection due to insufficient funds"""
        config = AccountConfig(initial_cash=Decimal('10000'))
        account = PaperTradingAccount("test_insufficient", config)
        
        # Try to buy too many shares
        market_data = {
            'price': Decimal('150'),
            'bid': Decimal('149.95'),
            'ask': Decimal('150.05'),
            'timestamp': datetime.utcnow()
        }
        
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=1000)
        account.executor.execute_order(order, market_data)
        
        # Order should be rejected
        account._process_filled_order(order)
        assert order.status == OrderStatus.REJECTED
    
    def test_insufficient_shares_rejection(self):
        """Test order rejection due to insufficient shares"""
        account = PaperTradingAccount("test_insufficient_shares")
        
        # Try to sell shares we don't have
        order = MarketOrder(ticker="AAPL", side=OrderSide.SELL, quantity=100)
        result = account.place_order(order)
        
        assert result['status'] == 'rejected'
        assert 'Insufficient shares' in result['reason']
    
    def test_multiple_positions_management(self):
        """Test managing multiple positions simultaneously"""
        account = PaperTradingAccount("test_multi_positions")
        
        # Mock market data for multiple tickers
        tickers_data = {
            'AAPL': {'price': Decimal('150'), 'bid': Decimal('149.95'), 'ask': Decimal('150.05')},
            'GOOGL': {'price': Decimal('2800'), 'bid': Decimal('2799'), 'ask': Decimal('2801')},
            'MSFT': {'price': Decimal('350'), 'bid': Decimal('349.95'), 'ask': Decimal('350.05')}
        }
        
        # Buy multiple positions
        for ticker, data in tickers_data.items():
            order = MarketOrder(ticker=ticker, side=OrderSide.BUY, quantity=10)
            market_data = {**data, 'timestamp': datetime.utcnow()}
            account.executor.execute_order(order, market_data)
            account._process_filled_order(order)
        
        # Verify all positions created
        assert len(account.portfolio.positions) == 3
        assert account.portfolio.get_position('AAPL') is not None
        assert account.portfolio.get_position('GOOGL') is not None
        assert account.portfolio.get_position('MSFT') is not None
    
    def test_limit_order_pending_then_filled(self):
        """Test limit order that starts pending and later fills"""
        account = PaperTradingAccount("test_limit_pending")
        
        # Place limit buy order above current market price
        order = LimitOrder(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            limit_price=Decimal('145')
        )
        
        # Current market price is 150, order should be pending
        market_data = {
            'price': Decimal('150'),
            'bid': Decimal('149.95'),
            'ask': Decimal('150.05'),
            'timestamp': datetime.utcnow()
        }
        
        result = account.place_order(order)
        assert result['status'] == 'pending'
        assert len(account.pending_orders) == 1
        
        # Market price drops, order should now fill
        market_data = {
            'price': Decimal('144'),
            'bid': Decimal('143.95'),
            'ask': Decimal('144.05'),
            'timestamp': datetime.utcnow()
        }
        
        # Manually execute pending orders (would be done by periodic check)
        for pending_order in account.pending_orders:
            account.executor.execute_order(pending_order, market_data)
            if pending_order.status == OrderStatus.FILLED:
                account._process_filled_order(pending_order)
        
        # Remove filled orders from pending
        account.pending_orders = [o for o in account.pending_orders if o.status == OrderStatus.PENDING]
        
        assert len(account.pending_orders) == 0
        assert account.portfolio.get_position('AAPL') is not None


# ==================== EDGE CASES ====================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_zero_quantity_order(self):
        """Test order with zero quantity"""
        account = PaperTradingAccount("test_zero_qty")
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=0)
        result = account.place_order(order)
        
        assert result['status'] == 'rejected'
    
    def test_negative_quantity_order(self):
        """Test order with negative quantity"""
        account = PaperTradingAccount("test_neg_qty")
        order = MarketOrder(ticker="AAPL", side=OrderSide.BUY, quantity=-100)
        result = account.place_order(order)
        
        assert result['status'] == 'rejected'
    
    def test_position_with_zero_cost_basis(self):
        """Test position unrealized P&L with zero cost basis"""
        position = Position(
            ticker="FREE",
            quantity=100,
            avg_entry_price=Decimal('0'),
            current_price=Decimal('10'),
            entry_time=datetime.utcnow()
        )
        
        # Should not crash with division by zero
        assert position.unrealized_pnl_pct == 0.0
    
    def test_order_cancel(self):
        """Test canceling a pending order"""
        account = PaperTradingAccount("test_cancel")
        
        # Place limit order that won't fill immediately
        order = LimitOrder(
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            limit_price=Decimal('100')
        )
        
        market_data = {
            'price': Decimal('150'),
            'bid': Decimal('149.95'),
            'ask': Decimal('150.05'),
            'timestamp': datetime.utcnow()
        }
        
        result = account.place_order(order)
        assert result['status'] == 'pending'
        
        # Cancel the order
        cancelled = account.cancel_order(order.order_id)
        assert cancelled
        assert len(account.pending_orders) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
