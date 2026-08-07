"""
Order management for paper trading.

Supports multiple order types:
- Market orders: Execute immediately at current market price
- Limit orders: Execute only at specified price or better
- Stop-loss orders: Trigger market order when price reaches stop price
- Stop-limit orders: Trigger limit order when price reaches stop price
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
import uuid


class OrderType(str, Enum):
    """Order type enum"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enum"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enum"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Order:
    """
    Base order class
    
    Attributes:
        order_id: Unique order identifier
        ticker: Stock ticker symbol
        side: Buy or sell
        quantity: Number of shares
        order_type: Type of order
        status: Current order status
        created_at: Order creation timestamp
        filled_at: Order fill timestamp
        filled_price: Price at which order was filled
        filled_quantity: Number of shares filled
        commission: Commission paid
        slippage: Slippage incurred
    """
    ticker: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    filled_price: Optional[Decimal] = None
    filled_quantity: int = 0
    commission: Decimal = Decimal('0')
    slippage: Decimal = Decimal('0')
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """
        Check if order should execute based on current market conditions
        
        Args:
            current_price: Current market price
            bid: Current bid price
            ask: Current ask price
            
        Returns:
            True if order should execute
        """
        raise NotImplementedError("Subclasses must implement should_execute")
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """
        Get execution price for this order
        
        Args:
            current_price: Current market price
            bid: Current bid price
            ask: Current ask price
            
        Returns:
            Execution price
        """
        raise NotImplementedError("Subclasses must implement get_execution_price")
    
    def fill(self, price: Decimal, quantity: int, timestamp: datetime, 
             commission: Decimal = Decimal('0'), slippage: Decimal = Decimal('0')) -> None:
        """
        Fill the order
        
        Args:
            price: Fill price
            quantity: Quantity filled
            timestamp: Fill timestamp
            commission: Commission paid
            slippage: Slippage incurred
        """
        self.filled_price = price
        self.filled_quantity = quantity
        self.filled_at = timestamp
        self.commission = commission
        self.slippage = slippage
        
        if quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def cancel(self) -> None:
        """Cancel the order"""
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.CANCELLED
    
    def reject(self) -> None:
        """Reject the order"""
        self.status = OrderStatus.REJECTED
    
    def expire(self) -> None:
        """Expire the order"""
        self.status = OrderStatus.EXPIRED


@dataclass
class MarketOrder(Order):
    """
    Market order - executes immediately at current market price
    
    Market orders always execute (assuming liquidity).
    Buy orders execute at ask price, sell orders at bid price.
    """
    order_type: OrderType = field(default=OrderType.MARKET, init=False)
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """Market orders always execute immediately"""
        return True
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """
        Get execution price based on bid-ask spread
        
        Buys execute at ask, sells execute at bid
        """
        if self.side == OrderSide.BUY:
            return ask
        else:
            return bid


@dataclass
class LimitOrder(Order):
    """
    Limit order - executes only at specified price or better
    
    Buy limit: executes when ask <= limit_price
    Sell limit: executes when bid >= limit_price
    """
    limit_price: Decimal = Decimal('0')
    order_type: OrderType = field(default=OrderType.LIMIT, init=False)
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """
        Check if limit order should execute
        
        Buy limit: ask <= limit_price
        Sell limit: bid >= limit_price
        """
        if self.side == OrderSide.BUY:
            return ask <= self.limit_price
        else:
            return bid >= self.limit_price
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """
        Get execution price for limit order
        
        Executes at limit price or better
        """
        if self.side == OrderSide.BUY:
            return min(ask, self.limit_price)
        else:
            return max(bid, self.limit_price)


@dataclass
class StopLossOrder(Order):
    """
    Stop-loss order - triggers market order when price reaches stop price
    
    Buy stop: triggers when price >= stop_price
    Sell stop: triggers when price <= stop_price
    """
    stop_price: Decimal = Decimal('0')
    order_type: OrderType = field(default=OrderType.STOP_LOSS, init=False)
    triggered: bool = False
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """
        Check if stop order should trigger
        
        Buy stop: current_price >= stop_price
        Sell stop: current_price <= stop_price
        """
        if not self.triggered:
            if self.side == OrderSide.BUY:
                self.triggered = current_price >= self.stop_price
            else:
                self.triggered = current_price <= self.stop_price
        
        return self.triggered
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """
        Get execution price for stop order
        
        Once triggered, executes as market order
        """
        if self.side == OrderSide.BUY:
            return ask
        else:
            return bid


@dataclass
class StopLimitOrder(Order):
    """
    Stop-limit order - triggers limit order when price reaches stop price
    
    Buy stop-limit: triggers when price >= stop_price, then executes as limit order
    Sell stop-limit: triggers when price <= stop_price, then executes as limit order
    """
    stop_price: Decimal = Decimal('0')
    limit_price: Decimal = Decimal('0')
    order_type: OrderType = field(default=OrderType.STOP_LIMIT, init=False)
    triggered: bool = False
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """
        Check if stop-limit order should trigger and execute
        
        First checks if stop is triggered, then checks if limit conditions are met
        """
        # Check if stop triggered
        if not self.triggered:
            if self.side == OrderSide.BUY:
                self.triggered = current_price >= self.stop_price
            else:
                self.triggered = current_price <= self.stop_price
        
        # If triggered, check limit conditions
        if self.triggered:
            if self.side == OrderSide.BUY:
                return ask <= self.limit_price
            else:
                return bid >= self.limit_price
        
        return False
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """
        Get execution price for stop-limit order
        
        Once triggered, executes as limit order
        """
        if self.side == OrderSide.BUY:
            return min(ask, self.limit_price)
        else:
            return max(bid, self.limit_price)
