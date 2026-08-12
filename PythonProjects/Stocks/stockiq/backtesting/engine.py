"""
Backtest Engine

Main backtesting engine with realistic market simulation
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
import pandas as pd
import numpy as np
from collections import defaultdict

from .orders import Order, OrderSide, OrderStatus, MarketOrder, LimitOrder, StopLossOrder, StopLimitOrder
from .slippage import SlippageModel, PercentageSlippageModel
from .commission import CommissionModel, ZeroCommissionModel
from .performance import PerformanceMetrics, EquityCurve, Trade


@dataclass
class Position:
    """Represents a position in the portfolio"""
    ticker: str
    quantity: int
    avg_entry_price: Decimal
    current_price: Decimal
    entry_time: datetime
    
    @property
    def market_value(self) -> Decimal:
        """Current market value of position"""
        return self.current_price * Decimal(abs(self.quantity))
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Unrealized profit/loss"""
        if self.quantity > 0:  # Long position
            return (self.current_price - self.avg_entry_price) * Decimal(self.quantity)
        else:  # Short position
            return (self.avg_entry_price - self.current_price) * Decimal(abs(self.quantity))
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized profit/loss percentage"""
        if self.avg_entry_price == 0:
            return 0.0
        return float(self.unrealized_pnl / (self.avg_entry_price * Decimal(abs(self.quantity))))


@dataclass
class BacktestConfig:
    """Configuration for backtest"""
    initial_capital: Decimal = Decimal('100000')
    slippage_model: SlippageModel = field(default_factory=lambda: PercentageSlippageModel())
    commission_model: CommissionModel = field(default_factory=lambda: ZeroCommissionModel())
    allow_short_selling: bool = False
    margin_requirement: Decimal = Decimal('0.5')  # 50% margin for shorts
    prevent_look_ahead_bias: bool = True  # Prevent using future data


class BacktestEngine:
    """
    Professional-grade backtesting engine
    
    Features:
    - Realistic order execution with slippage and commissions
    - Multiple order types (market, limit, stop-loss, stop-limit)
    - Bid-ask spread simulation
    - Look-ahead bias prevention
    - Comprehensive performance metrics
    """
    
    def __init__(self, config: BacktestConfig):
        """
        Args:
            config: Backtest configuration
        """
        self.config = config
        
        # Portfolio state
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.pending_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        self.closed_trades: List[Trade] = []
        
        # Equity tracking
        self.equity_curve = EquityCurve(config.initial_capital)
        
        # Current simulation time
        self.current_time: Optional[datetime] = None
        
        # Market data cache (for current bar)
        self.current_market_data: Dict[str, Dict] = {}
        
        # Strategy callback
        self.strategy_func: Optional[Callable] = None
    
    def set_strategy(self, strategy_func: Callable[[datetime, Dict], List[Order]]) -> None:
        """
        Set trading strategy function
        
        Args:
            strategy_func: Function that takes (timestamp, market_data) and returns list of orders
        """
        self.strategy_func = strategy_func
    
    def run(self, market_data: pd.DataFrame, 
            strategy_func: Optional[Callable] = None) -> PerformanceMetrics:
        """
        Run backtest on historical data
        
        Args:
            market_data: DataFrame with columns: ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']
                        Can also include 'bid', 'ask' for more realistic spread simulation
            strategy_func: Optional strategy function (overrides set_strategy)
            
        Returns:
            PerformanceMetrics object
        """
        if strategy_func:
            self.strategy_func = strategy_func
        
        if self.strategy_func is None:
            raise ValueError("Strategy function must be set before running backtest")
        
        # Validate market data
        required_cols = ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in market_data.columns:
                raise ValueError(f"Market data missing required column: {col}")
        
        # Sort by timestamp to prevent look-ahead bias
        market_data = market_data.sort_values('timestamp')
        
        # Group by timestamp for bar-by-bar simulation
        grouped = market_data.groupby('timestamp')
        
        for timestamp, bar_data in grouped:
            self._simulate_bar(timestamp, bar_data)
        
        # Close all positions at end
        self._close_all_positions(market_data['timestamp'].max())
        
        # Calculate performance metrics
        metrics = PerformanceMetrics.calculate(
            self.equity_curve,
            self.closed_trades,
            self.config.initial_capital
        )
        
        return metrics
    
    def _simulate_bar(self, timestamp: datetime, bar_data: pd.DataFrame) -> None:
        """
        Simulate one time bar
        
        Args:
            timestamp: Current timestamp
            bar_data: Market data for all tickers at this timestamp
        """
        self.current_time = timestamp
        
        # Update market data cache
        self.current_market_data = {}
        for _, row in bar_data.iterrows():
            ticker = row['ticker']
            self.current_market_data[ticker] = {
                'open': Decimal(str(row['open'])),
                'high': Decimal(str(row['high'])),
                'low': Decimal(str(row['low'])),
                'close': Decimal(str(row['close'])),
                'volume': int(row['volume']),
                'bid': Decimal(str(row.get('bid', row['close']))),
                'ask': Decimal(str(row.get('ask', row['close']))),
            }
        
        # Update position values with current prices
        self._update_positions()
        
        # Process pending orders (check if they should execute)
        self._process_pending_orders()
        
        # Call strategy to generate new orders
        if self.config.prevent_look_ahead_bias:
            # Strategy can only see data up to current bar's open
            # Use previous close as "current" price for strategy
            strategy_data = self._get_strategy_data()
        else:
            strategy_data = self.current_market_data
        
        new_orders = self.strategy_func(timestamp, strategy_data)
        
        # Add new orders to pending
        for order in new_orders:
            self._submit_order(order)
        
        # Record equity curve point
        self._record_equity_point()
    
    def _get_strategy_data(self) -> Dict[str, Dict]:
        """
        Get market data available to strategy (prevent look-ahead bias)
        
        Returns data at bar open, not bar close
        """
        strategy_data = {}
        for ticker, data in self.current_market_data.items():
            # Strategy sees open price, not close
            strategy_data[ticker] = {
                'price': data['open'],
                'bid': data['open'],  # Simplified
                'ask': data['open'],
                'volume': data['volume']
            }
        return strategy_data
    
    def _update_positions(self) -> None:
        """Update position values with current market prices"""
        for ticker, position in self.positions.items():
            if ticker in self.current_market_data:
                # Use close price for position valuation
                position.current_price = self.current_market_data[ticker]['close']
    
    def _process_pending_orders(self) -> None:
        """Process pending orders and execute if conditions are met"""
        orders_to_remove = []
        
        for order in self.pending_orders:
            if order.ticker not in self.current_market_data:
                continue
            
            market_data = self.current_market_data[order.ticker]
            
            # Check if order should execute
            if order.should_execute(
                market_data['close'],
                market_data['bid'],
                market_data['ask']
            ):
                # Execute order
                success = self._execute_order(order, market_data)
                if success:
                    orders_to_remove.append(order)
        
        # Remove executed orders
        for order in orders_to_remove:
            self.pending_orders.remove(order)
            self.completed_orders.append(order)
    
    def _submit_order(self, order: Order) -> None:
        """Submit a new order"""
        # Validate order
        if order.quantity <= 0:
            order.reject()
            return
        
        # Check if short selling is allowed
        if order.side == OrderSide.SELL:
            current_position = self.positions.get(order.ticker)
            if current_position is None or current_position.quantity < order.quantity:
                if not self.config.allow_short_selling:
                    order.reject()
                    return
        
        # Add to pending orders
        self.pending_orders.append(order)
    
    def _execute_order(self, order: Order, market_data: Dict) -> bool:
        """
        Execute an order
        
        Args:
            order: Order to execute
            market_data: Current market data
            
        Returns:
            True if execution successful, False otherwise
        """
        # Get execution price
        execution_price = order.get_execution_price(
            market_data['close'],
            market_data['bid'],
            market_data['ask']
        )
        
        # Calculate slippage
        slippage = self.config.slippage_model.calculate_slippage(
            execution_price,
            order.quantity,
            market_data['volume'],
            'buy' if order.side == OrderSide.BUY else 'sell'
        )
        
        # Apply slippage to execution price
        if order.side == OrderSide.BUY:
            execution_price += slippage / Decimal(order.quantity)
        else:
            execution_price -= slippage / Decimal(order.quantity)
        
        # Calculate commission
        commission = self.config.commission_model.calculate_commission(
            execution_price,
            order.quantity,
            'buy' if order.side == OrderSide.BUY else 'sell'
        )
        
        # Calculate total cost
        total_cost = execution_price * Decimal(order.quantity) + commission
        
        # Check if sufficient capital
        if order.side == OrderSide.BUY:
            if total_cost > self.cash:
                order.reject()
                return False
        
        # Execute trade
        if order.side == OrderSide.BUY:
            self._open_or_add_position(order.ticker, order.quantity, execution_price, self.current_time)
            self.cash -= total_cost
        else:
            self._reduce_or_close_position(order.ticker, order.quantity, execution_price, self.current_time)
            proceeds = execution_price * Decimal(order.quantity) - commission
            self.cash += proceeds
        
        # Fill order
        order.fill(execution_price, order.quantity, self.current_time, commission, slippage)
        
        return True
    
    def _open_or_add_position(self, ticker: str, quantity: int, price: Decimal, 
                             timestamp: datetime) -> None:
        """Open new position or add to existing"""
        if ticker in self.positions:
            # Add to existing position
            position = self.positions[ticker]
            total_quantity = position.quantity + quantity
            total_cost = (position.avg_entry_price * Decimal(position.quantity) + 
                         price * Decimal(quantity))
            position.avg_entry_price = total_cost / Decimal(total_quantity)
            position.quantity = total_quantity
        else:
            # Open new position
            self.positions[ticker] = Position(
                ticker=ticker,
                quantity=quantity,
                avg_entry_price=price,
                current_price=price,
                entry_time=timestamp
            )
    
    def _reduce_or_close_position(self, ticker: str, quantity: int, price: Decimal,
                                  timestamp: datetime) -> None:
        """Reduce or close position and record trade"""
        if ticker not in self.positions:
            # Short selling (if allowed)
            if self.config.allow_short_selling:
                self.positions[ticker] = Position(
                    ticker=ticker,
                    quantity=-quantity,
                    avg_entry_price=price,
                    current_price=price,
                    entry_time=timestamp
                )
            return
        
        position = self.positions[ticker]
        
        if quantity >= position.quantity:
            # Close entire position
            pnl = (price - position.avg_entry_price) * Decimal(position.quantity)
            pnl_pct = float(pnl / (position.avg_entry_price * Decimal(position.quantity)))
            
            # Record trade
            trade = Trade(
                ticker=ticker,
                entry_time=position.entry_time,
                exit_time=timestamp,
                entry_price=position.avg_entry_price,
                exit_price=price,
                quantity=position.quantity,
                side='long',
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=Decimal('0'),  # Commission already deducted from cash
                slippage=Decimal('0')  # Slippage already applied to price
            )
            self.closed_trades.append(trade)
            
            # Remove position
            del self.positions[ticker]
        else:
            # Reduce position
            pnl = (price - position.avg_entry_price) * Decimal(quantity)
            pnl_pct = float(pnl / (position.avg_entry_price * Decimal(quantity)))
            
            # Record partial trade
            trade = Trade(
                ticker=ticker,
                entry_time=position.entry_time,
                exit_time=timestamp,
                entry_price=position.avg_entry_price,
                exit_price=price,
                quantity=quantity,
                side='long',
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=Decimal('0'),
                slippage=Decimal('0')
            )
            self.closed_trades.append(trade)
            
            # Reduce position quantity
            position.quantity -= quantity
    
    def _close_all_positions(self, timestamp: datetime) -> None:
        """Close all open positions at end of backtest"""
        for ticker, position in list(self.positions.items()):
            if ticker in self.current_market_data:
                exit_price = self.current_market_data[ticker]['close']
                self._reduce_or_close_position(ticker, position.quantity, exit_price, timestamp)
    
    def _record_equity_point(self) -> None:
        """Record current equity for equity curve"""
        position_value = sum([p.market_value for p in self.positions.values()])
        total_equity = self.cash + position_value
        
        self.equity_curve.add_point(
            self.current_time,
            total_equity,
            self.cash,
            position_value
        )
    
    def get_current_equity(self) -> Decimal:
        """Get current total equity"""
        position_value = sum([p.market_value for p in self.positions.values()])
        return self.cash + position_value
    
    def get_positions(self) -> Dict[str, Position]:
        """Get current positions"""
        return self.positions.copy()
    
    def get_trades(self) -> List[Trade]:
        """Get all closed trades"""
        return self.closed_trades.copy()
    
    def get_equity_curve(self) -> EquityCurve:
        """Get equity curve"""
        return self.equity_curve
