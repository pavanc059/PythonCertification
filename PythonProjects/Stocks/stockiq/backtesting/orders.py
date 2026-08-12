"""
Order Types and Management

Supports multiple order types: market, limit, stop-loss, stop-limit
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderType(Enum):
    """Types of orders supported"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order execution status"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """Order side (buy/sell)"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Base order class"""
    ticker: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    created_at: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[Decimal] = None
    filled_at: Optional[datetime] = None
    commission: Decimal = Decimal('0')
    slippage: Decimal = Decimal('0')
    order_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate order parameters"""
        if self.quantity <= 0:
            raise ValueError(f"Order quantity must be positive, got {self.quantity}")
    
    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.status == OrderStatus.FILLED
    
    def is_pending(self) -> bool:
        """Check if order is pending"""
        return self.status == OrderStatus.PENDING
    
    def fill(self, price: Decimal, quantity: int, timestamp: datetime, 
             commission: Decimal, slippage: Decimal) -> None:
        """Fill the order (fully or partially)"""
        if quantity > (self.quantity - self.filled_quantity):
            raise ValueError(
                f"Fill quantity {quantity} exceeds remaining quantity "
                f"{self.quantity - self.filled_quantity}"
            )
        
        self.filled_quantity += quantity
        self.filled_price = price
        self.filled_at = timestamp
        self.commission += commission
        self.slippage += slippage
        
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def cancel(self) -> None:
        """Cancel the order"""
        if self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order with status {self.status}")
        self.status = OrderStatus.CANCELLED
    
    def reject(self) -> None:
        """Reject the order"""
        self.status = OrderStatus.REJECTED


@dataclass
class MarketOrder(Order):
    """
    Market order - executes immediately at current market price
    """
    def __init__(self, ticker: str, side: OrderSide, quantity: int, 
                 created_at: datetime, order_id: Optional[str] = None):
        super().__init__(
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            created_at=created_at,
            order_id=order_id
        )
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """Market orders execute immediately"""
        return True
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """Get execution price for market order"""
        # Use ask for buys, bid for sells
        if self.side == OrderSide.BUY:
            return ask
        else:
            return bid


@dataclass
class LimitOrder(Order):
    """
    Limit order - executes when price reaches limit price
    """
    limit_price: Decimal = field(default=None)
    
    def __init__(self, ticker: str, side: OrderSide, quantity: int, 
                 limit_price: Decimal, created_at: datetime, order_id: Optional[str] = None):
        super().__init__(
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            created_at=created_at,
            order_id=order_id
        )
        self.limit_price = limit_price
        
        if limit_price <= 0:
            raise ValueError(f"Limit price must be positive, got {limit_price}")
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """Check if limit order should execute"""
        if self.side == OrderSide.BUY:
            # Buy limit: execute when ask <= limit price
            return ask <= self.limit_price
        else:
            # Sell limit: execute when bid >= limit price
            return bid >= self.limit_price
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """Get execution price for limit order"""
        # Limit orders execute at limit price or better
        if self.side == OrderSide.BUY:
            return min(ask, self.limit_price)
        else:
            return max(bid, self.limit_price)


@dataclass
class StopLossOrder(Order):
    """
    Stop-loss order - triggers market order when price hits stop price
    """
    stop_price: Decimal = field(default=None)
    triggered: bool = False
    
    def __init__(self, ticker: str, side: OrderSide, quantity: int, 
                 stop_price: Decimal, created_at: datetime, order_id: Optional[str] = None):
        super().__init__(
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP_LOSS,
            created_at=created_at,
            order_id=order_id
        )
        self.stop_price = stop_price
        
        if stop_price <= 0:
            raise ValueError(f"Stop price must be positive, got {stop_price}")
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """Check if stop-loss order should execute"""
        if not self.triggered:
            # Check if stop price is hit
            if self.side == OrderSide.BUY:
                # Buy stop: trigger when price rises above stop price
                self.triggered = current_price >= self.stop_price
            else:
                # Sell stop: trigger when price falls below stop price
                self.triggered = current_price <= self.stop_price
        
        # Once triggered, execute like market order
        return self.triggered
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """Get execution price for stop-loss order"""
        # Execute at market price after trigger
        if self.side == OrderSide.BUY:
            return ask
        else:
            return bid


@dataclass
class StopLimitOrder(Order):
    """
    Stop-limit order - triggers limit order when price hits stop price
    """
    stop_price: Decimal = field(default=None)
    limit_price: Decimal = field(default=None)
    triggered: bool = False
    
    def __init__(self, ticker: str, side: OrderSide, quantity: int, 
                 stop_price: Decimal, limit_price: Decimal, created_at: datetime,
                 order_id: Optional[str] = None):
        super().__init__(
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=OrderType.STOP_LIMIT,
            created_at=created_at,
            order_id=order_id
        )
        self.stop_price = stop_price
        self.limit_price = limit_price
        
        if stop_price <= 0:
            raise ValueError(f"Stop price must be positive, got {stop_price}")
        if limit_price <= 0:
            raise ValueError(f"Limit price must be positive, got {limit_price}")
    
    def should_execute(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> bool:
        """Check if stop-limit order should execute"""
        if not self.triggered:
            # Check if stop price is hit
            if self.side == OrderSide.BUY:
                # Buy stop: trigger when price rises above stop price
                self.triggered = current_price >= self.stop_price
            else:
                # Sell stop: trigger when price falls below stop price
                self.triggered = current_price <= self.stop_price
            
            if not self.triggered:
                return False
        
        # Once triggered, check limit price like limit order
        if self.side == OrderSide.BUY:
            return ask <= self.limit_price
        else:
            return bid >= self.limit_price
    
    def get_execution_price(self, current_price: Decimal, bid: Decimal, ask: Decimal) -> Decimal:
        """Get execution price for stop-limit order"""
        # Execute at limit price or better
        if self.side == OrderSide.BUY:
            return min(ask, self.limit_price)
        else:
            return max(bid, self.limit_price)
