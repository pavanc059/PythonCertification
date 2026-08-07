"""
Commission Models

Models for calculating trading commissions and fees
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Tuple


class CommissionModel(ABC):
    """Abstract base class for commission models"""
    
    @abstractmethod
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """
        Calculate commission for a trade
        
        Args:
            price: Execution price
            quantity: Order quantity
            side: 'buy' or 'sell'
            
        Returns:
            Commission amount (positive value)
        """
        pass


class FixedCommissionModel(CommissionModel):
    """
    Fixed commission per trade
    
    Example: $1.00 per trade (common for modern brokers like Robinhood, Webull)
    """
    
    def __init__(self, commission_per_trade: Decimal = Decimal('1.00')):
        """
        Args:
            commission_per_trade: Fixed commission amount per trade
        """
        if commission_per_trade < 0:
            raise ValueError(f"Commission must be non-negative, got {commission_per_trade}")
        self.commission_per_trade = commission_per_trade
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """Calculate fixed commission"""
        return self.commission_per_trade


class PerShareCommissionModel(CommissionModel):
    """
    Commission per share with optional minimum
    
    Example: $0.005 per share, $1.00 minimum (common for discount brokers)
    """
    
    def __init__(self, commission_per_share: Decimal = Decimal('0.005'),
                 minimum_commission: Decimal = Decimal('1.00')):
        """
        Args:
            commission_per_share: Commission per share
            minimum_commission: Minimum commission per trade
        """
        if commission_per_share < 0:
            raise ValueError(f"Commission per share must be non-negative, got {commission_per_share}")
        if minimum_commission < 0:
            raise ValueError(f"Minimum commission must be non-negative, got {minimum_commission}")
        
        self.commission_per_share = commission_per_share
        self.minimum_commission = minimum_commission
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """Calculate per-share commission with minimum"""
        commission = self.commission_per_share * Decimal(quantity)
        return max(commission, self.minimum_commission)


class PercentageCommissionModel(CommissionModel):
    """
    Commission as percentage of trade value
    
    Example: 0.1% of trade value (common for full-service brokers)
    """
    
    def __init__(self, commission_pct: Decimal = Decimal('0.001'),
                 minimum_commission: Decimal = Decimal('1.00')):
        """
        Args:
            commission_pct: Commission percentage (e.g., 0.001 = 0.1%)
            minimum_commission: Minimum commission per trade
        """
        if commission_pct < 0:
            raise ValueError(f"Commission percentage must be non-negative, got {commission_pct}")
        if commission_pct > 1:
            raise ValueError(f"Commission percentage must be <= 1, got {commission_pct}")
        if minimum_commission < 0:
            raise ValueError(f"Minimum commission must be non-negative, got {minimum_commission}")
        
        self.commission_pct = commission_pct
        self.minimum_commission = minimum_commission
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """Calculate percentage-based commission"""
        trade_value = price * Decimal(quantity)
        commission = trade_value * self.commission_pct
        return max(commission, self.minimum_commission)


class TieredCommissionModel(CommissionModel):
    """
    Tiered commission based on trade value
    
    Example:
    - $0-10,000: 0.1%
    - $10,000-50,000: 0.08%
    - $50,000+: 0.05%
    """
    
    def __init__(self, tiers: List[Tuple[Decimal, Decimal]], 
                 minimum_commission: Decimal = Decimal('1.00')):
        """
        Args:
            tiers: List of (threshold, commission_pct) tuples, sorted by threshold
                   Example: [(10000, 0.001), (50000, 0.0008), (float('inf'), 0.0005)]
            minimum_commission: Minimum commission per trade
        """
        if not tiers:
            raise ValueError("Tiers list cannot be empty")
        
        # Validate tiers are sorted
        for i in range(len(tiers) - 1):
            if tiers[i][0] >= tiers[i + 1][0]:
                raise ValueError("Tiers must be sorted by threshold in ascending order")
        
        # Validate commission percentages
        for threshold, pct in tiers:
            if pct < 0 or pct > 1:
                raise ValueError(f"Commission percentage must be in [0, 1], got {pct}")
        
        if minimum_commission < 0:
            raise ValueError(f"Minimum commission must be non-negative, got {minimum_commission}")
        
        self.tiers = tiers
        self.minimum_commission = minimum_commission
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """Calculate tiered commission"""
        trade_value = price * Decimal(quantity)
        
        # Find applicable tier
        commission_pct = self.tiers[-1][1]  # Default to highest tier
        for threshold, pct in self.tiers:
            if trade_value < threshold:
                commission_pct = pct
                break
        
        commission = trade_value * commission_pct
        return max(commission, self.minimum_commission)


class InteractiveBrokersCommissionModel(CommissionModel):
    """
    Interactive Brokers commission model (IBKR Lite)
    
    - US stocks: $0 commission
    - Options: $0.65 per contract
    """
    
    def __init__(self):
        """Initialize IBKR commission model"""
        pass
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """IBKR Lite has zero commission for stocks"""
        return Decimal('0')


class TradeStationCommissionModel(CommissionModel):
    """
    TradeStation commission model
    
    - $0 per trade for stocks and ETFs
    - Plus $0.60 per options contract
    """
    
    def __init__(self, base_commission: Decimal = Decimal('0')):
        """
        Args:
            base_commission: Base commission per trade
        """
        self.base_commission = base_commission
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """Calculate TradeStation commission"""
        return self.base_commission


class ZeroCommissionModel(CommissionModel):
    """
    Zero commission model (e.g., Robinhood, Webull, most modern brokers)
    """
    
    def __init__(self):
        """Initialize zero commission model"""
        pass
    
    def calculate_commission(self, price: Decimal, quantity: int, side: str) -> Decimal:
        """Zero commission"""
        return Decimal('0')
