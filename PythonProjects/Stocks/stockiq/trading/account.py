"""
Virtual account management for paper trading.

Implements Requirement 16.7: Virtual cash accounts with real-time price execution
"""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
import structlog

from .orders import Order, OrderSide, OrderStatus
from .execution import OrderExecutor
from .portfolio import Portfolio, Position

logger = structlog.get_logger(__name__)


@dataclass
class AccountConfig:
    """Configuration for paper trading account"""
    initial_cash: Decimal = Decimal('100000')  # $100,000 default
    slippage_pct: float = 0.001  # 0.1% slippage
    commission_per_share: Decimal = Decimal('0')  # Zero commission
    commission_min: Decimal = Decimal('0')
    use_bid_ask_spread: bool = True
    spread_pct: float = 0.001  # 0.1% spread
    allow_margin: bool = False
    margin_multiplier: Decimal = Decimal('1')  # 1x = no margin, 2x = 2:1 leverage


class PaperTradingAccount:
    """
    Virtual trading account with paper money
    
    Features:
    - Virtual cash balance management
    - Order placement and execution
    - Position tracking
    - Portfolio performance monitoring
    - Realistic trade simulation
    
    Implements Requirements 16.7-16.8:
    - Virtual cash accounts (16.7)
    - Real-time price execution (16.8)
    """
    
    def __init__(self, account_id: str, config: Optional[AccountConfig] = None):
        """
        Initialize paper trading account
        
        Args:
            account_id: Unique account identifier
            config: Account configuration
        """
        self.account_id = account_id
        self.config = config or AccountConfig()
        
        # Account state
        self.cash = self.config.initial_cash
        self.initial_cash = self.config.initial_cash
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()
        
        # Orders
        self.pending_orders: List[Order] = []
        self.completed_orders: List[Order] = []
        
        # Portfolio
        self.portfolio = Portfolio()
        
        # Execution engine
        self.executor = OrderExecutor(
            slippage_pct=self.config.slippage_pct,
            commission_per_share=self.config.commission_per_share,
            commission_min=self.config.commission_min,
            use_bid_ask_spread=self.config.use_bid_ask_spread,
            spread_pct=self.config.spread_pct
        )
        
        logger.info(
            "account_created",
            account_id=account_id,
            initial_cash=float(self.initial_cash)
        )
    
    def place_order(self, order: Order) -> Dict:
        """
        Place a trading order
        
        Args:
            order: Order to place
            
        Returns:
            Order confirmation dictionary
        """
        # Validate order
        if order.quantity <= 0:
            order.reject()
            logger.warning("order_rejected", order_id=order.order_id, reason="invalid_quantity")
            return {
                'status': 'rejected',
                'order_id': order.order_id,
                'reason': 'Invalid quantity'
            }
        
        # Check if selling - must have position
        if order.side == OrderSide.SELL:
            position = self.portfolio.get_position(order.ticker)
            if position is None or position.quantity < order.quantity:
                order.reject()
                logger.warning(
                    "order_rejected",
                    order_id=order.order_id,
                    reason="insufficient_shares",
                    ticker=order.ticker,
                    required=order.quantity,
                    available=position.quantity if position else 0
                )
                return {
                    'status': 'rejected',
                    'order_id': order.order_id,
                    'reason': 'Insufficient shares'
                }
        
        # Try to execute order immediately (if market order)
        success, error = self.executor.execute_order(order)
        
        if success:
            # Order executed
            self._process_filled_order(order)
            self.completed_orders.append(order)
            
            logger.info(
                "order_filled",
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side.value,
                quantity=order.quantity,
                price=float(order.filled_price) if order.filled_price else None
            )
            
            return {
                'status': 'filled',
                'order_id': order.order_id,
                'filled_price': order.filled_price,
                'filled_quantity': order.filled_quantity,
                'commission': order.commission,
                'slippage': order.slippage
            }
        else:
            # Order pending (limit/stop orders)
            if order.status == OrderStatus.REJECTED:
                logger.warning("order_rejected", order_id=order.order_id, reason=error)
                return {
                    'status': 'rejected',
                    'order_id': order.order_id,
                    'reason': error
                }
            else:
                self.pending_orders.append(order)
                logger.info("order_pending", order_id=order.order_id, ticker=order.ticker)
                return {
                    'status': 'pending',
                    'order_id': order.order_id
                }
    
    def _process_filled_order(self, order: Order) -> None:
        """
        Process a filled order and update account state
        
        Args:
            order: Filled order
        """
        if order.side == OrderSide.BUY:
            # Buy order - decrease cash, add position
            total_cost = order.filled_price * Decimal(order.filled_quantity) + order.commission
            
            if total_cost > self.cash:
                # Insufficient funds - this shouldn't happen after validation
                order.reject()
                logger.error(
                    "insufficient_funds",
                    order_id=order.order_id,
                    required=float(total_cost),
                    available=float(self.cash)
                )
                return
            
            self.cash -= total_cost
            self.portfolio.add_position(
                ticker=order.ticker,
                quantity=order.filled_quantity,
                price=order.filled_price,
                timestamp=order.filled_at
            )
            
        else:
            # Sell order - increase cash, reduce position
            proceeds = order.filled_price * Decimal(order.filled_quantity) - order.commission
            self.cash += proceeds
            self.portfolio.reduce_position(
                ticker=order.ticker,
                quantity=order.filled_quantity,
                price=order.filled_price,
                timestamp=order.filled_at
            )
        
        self.last_updated = datetime.utcnow()
    
    def process_pending_orders(self) -> List[Dict]:
        """
        Process pending orders (check if they should execute)
        
        Returns:
            List of order confirmations for newly filled orders
        """
        filled_orders = []
        orders_to_remove = []
        
        for order in self.pending_orders:
            success, error = self.executor.execute_order(order)
            
            if success:
                self._process_filled_order(order)
                self.completed_orders.append(order)
                orders_to_remove.append(order)
                
                filled_orders.append({
                    'status': 'filled',
                    'order_id': order.order_id,
                    'filled_price': order.filled_price,
                    'filled_quantity': order.filled_quantity,
                    'commission': order.commission,
                    'slippage': order.slippage
                })
        
        # Remove filled orders from pending
        for order in orders_to_remove:
            self.pending_orders.remove(order)
        
        return filled_orders
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if order was cancelled, False otherwise
        """
        for order in self.pending_orders:
            if order.order_id == order_id:
                order.cancel()
                self.pending_orders.remove(order)
                self.completed_orders.append(order)
                
                logger.info("order_cancelled", order_id=order_id)
                return True
        
        return False
    
    def get_portfolio(self) -> Portfolio:
        """
        Get current portfolio
        
        Returns:
            Portfolio object with current positions
        """
        return self.portfolio
    
    def get_account_value(self) -> Decimal:
        """
        Get total account value (cash + positions)
        
        Returns:
            Total account value
        """
        portfolio_value = self.portfolio.get_total_value()
        return self.cash + portfolio_value
    
    def get_buying_power(self) -> Decimal:
        """
        Get available buying power
        
        Returns:
            Available cash for new purchases (including margin if enabled)
        """
        if self.config.allow_margin:
            return self.cash * self.config.margin_multiplier
        else:
            return self.cash
    
    def get_account_summary(self) -> Dict:
        """
        Get account summary
        
        Returns:
            Dictionary with account details
        """
        account_value = self.get_account_value()
        portfolio_value = self.portfolio.get_total_value()
        
        return {
            'account_id': self.account_id,
            'cash': self.cash,
            'portfolio_value': portfolio_value,
            'total_value': account_value,
            'buying_power': self.get_buying_power(),
            'num_positions': len(self.portfolio.positions),
            'num_pending_orders': len(self.pending_orders),
            'num_completed_orders': len(self.completed_orders),
            'total_return': account_value - self.initial_cash,
            'total_return_pct': float((account_value - self.initial_cash) / self.initial_cash) if self.initial_cash > 0 else 0.0,
            'created_at': self.created_at,
            'last_updated': self.last_updated
        }
    
    def reset(self) -> None:
        """Reset account to initial state"""
        self.cash = self.initial_cash
        self.pending_orders = []
        self.completed_orders = []
        self.portfolio = Portfolio()
        self.last_updated = datetime.utcnow()
        
        logger.info("account_reset", account_id=self.account_id)
