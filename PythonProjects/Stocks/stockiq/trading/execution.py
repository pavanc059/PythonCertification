"""
Simulated order execution using real-time market prices.

Implements Requirement 16.8: Execute simulated trades using real-time market prices
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional, Tuple
import yfinance as yf
import structlog

from .orders import Order, OrderSide, OrderStatus

logger = structlog.get_logger(__name__)


class OrderExecutor:
    """
    Executes paper trading orders using real-time market prices from yfinance
    
    Features:
    - Real-time price fetching
    - Realistic slippage simulation
    - Commission calculation
    - Bid-ask spread estimation
    """
    
    def __init__(
        self,
        slippage_pct: float = 0.001,  # 0.1% default slippage
        commission_per_share: Decimal = Decimal('0'),  # Zero commission (like Robinhood)
        commission_min: Decimal = Decimal('0'),
        use_bid_ask_spread: bool = True,
        spread_pct: float = 0.001  # 0.1% default spread (half-spread each side)
    ):
        """
        Initialize order executor
        
        Args:
            slippage_pct: Slippage percentage (0.001 = 0.1%)
            commission_per_share: Commission per share
            commission_min: Minimum commission per trade
            use_bid_ask_spread: Whether to simulate bid-ask spread
            spread_pct: Bid-ask spread percentage (half-spread each side)
        """
        self.slippage_pct = slippage_pct
        self.commission_per_share = commission_per_share
        self.commission_min = commission_min
        self.use_bid_ask_spread = use_bid_ask_spread
        self.spread_pct = spread_pct
    
    def fetch_real_time_price(self, ticker: str) -> Optional[Dict[str, Decimal]]:
        """
        Fetch real-time market price from yfinance
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with 'price', 'bid', 'ask' or None if error
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get current price
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if current_price is None:
                logger.error("price_fetch_failed", ticker=ticker, reason="no_price_data")
                return None
            
            current_price = Decimal(str(current_price))
            
            # Get bid/ask if available
            bid = info.get('bid')
            ask = info.get('ask')
            
            if self.use_bid_ask_spread and bid and ask:
                bid = Decimal(str(bid))
                ask = Decimal(str(ask))
            else:
                # Estimate bid/ask from current price and spread
                half_spread = current_price * Decimal(str(self.spread_pct))
                bid = current_price - half_spread
                ask = current_price + half_spread
            
            logger.info(
                "price_fetched",
                ticker=ticker,
                price=float(current_price),
                bid=float(bid),
                ask=float(ask)
            )
            
            return {
                'price': current_price,
                'bid': bid,
                'ask': ask,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("price_fetch_failed", ticker=ticker, error=str(e))
            return None
    
    def calculate_slippage(
        self,
        price: Decimal,
        quantity: int,
        side: OrderSide
    ) -> Decimal:
        """
        Calculate slippage for order
        
        Slippage increases with order size and is asymmetric:
        - Buy orders: slippage increases price
        - Sell orders: slippage decreases price
        
        Args:
            price: Execution price
            quantity: Order quantity
            side: Order side (buy/sell)
            
        Returns:
            Slippage amount (always positive)
        """
        # Base slippage
        base_slippage = price * Decimal(str(self.slippage_pct))
        
        # Scale slippage by quantity (larger orders have more slippage)
        # Use logarithmic scaling to avoid excessive slippage
        import math
        quantity_factor = Decimal(str(1 + 0.1 * math.log10(max(1, quantity / 100))))
        
        total_slippage = base_slippage * quantity_factor * Decimal(quantity)
        
        return total_slippage
    
    def calculate_commission(self, price: Decimal, quantity: int) -> Decimal:
        """
        Calculate commission for order
        
        Args:
            price: Execution price
            quantity: Order quantity
            
        Returns:
            Commission amount
        """
        commission = self.commission_per_share * Decimal(quantity)
        return max(commission, self.commission_min)
    
    def execute_order(
        self,
        order: Order,
        market_data: Optional[Dict[str, Decimal]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute a paper trading order
        
        Args:
            order: Order to execute
            market_data: Optional pre-fetched market data (for testing/replay)
            
        Returns:
            Tuple of (success, error_message)
        """
        # Fetch real-time price if not provided
        if market_data is None:
            market_data = self.fetch_real_time_price(order.ticker)
            if market_data is None:
                order.reject()
                return False, f"Failed to fetch price for {order.ticker}"
        
        current_price = market_data['price']
        bid = market_data['bid']
        ask = market_data['ask']
        
        # Check if order should execute
        if not order.should_execute(current_price, bid, ask):
            return False, "Order conditions not met"
        
        # Get execution price
        execution_price = order.get_execution_price(current_price, bid, ask)
        
        # Calculate slippage
        slippage = self.calculate_slippage(execution_price, order.quantity, order.side)
        
        # Apply slippage to execution price
        if order.side == OrderSide.BUY:
            execution_price += slippage / Decimal(order.quantity)
        else:
            execution_price -= slippage / Decimal(order.quantity)
        
        # Calculate commission
        commission = self.calculate_commission(execution_price, order.quantity)
        
        # Fill order
        order.fill(
            price=execution_price,
            quantity=order.quantity,
            timestamp=market_data.get('timestamp', datetime.utcnow()),
            commission=commission,
            slippage=slippage
        )
        
        logger.info(
            "order_executed",
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            execution_price=float(execution_price),
            commission=float(commission),
            slippage=float(slippage)
        )
        
        return True, None
