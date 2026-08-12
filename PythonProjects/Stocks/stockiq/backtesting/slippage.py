"""
Slippage Models

Models for simulating realistic slippage in order execution
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional
import pandas as pd


class SlippageModel(ABC):
    """Abstract base class for slippage models"""
    
    @abstractmethod
    def calculate_slippage(self, price: Decimal, quantity: int, 
                          volume: int, side: str) -> Decimal:
        """
        Calculate slippage for an order
        
        Args:
            price: Execution price before slippage
            quantity: Order quantity
            volume: Current market volume
            side: 'buy' or 'sell'
            
        Returns:
            Slippage amount (positive value)
        """
        pass


class FixedSlippageModel(SlippageModel):
    """
    Fixed slippage model - constant slippage per share
    
    Example: $0.01 per share
    """
    
    def __init__(self, slippage_per_share: Decimal = Decimal('0.01')):
        """
        Args:
            slippage_per_share: Fixed slippage amount per share
        """
        if slippage_per_share < 0:
            raise ValueError(f"Slippage per share must be non-negative, got {slippage_per_share}")
        self.slippage_per_share = slippage_per_share
    
    def calculate_slippage(self, price: Decimal, quantity: int, 
                          volume: int, side: str) -> Decimal:
        """Calculate fixed slippage"""
        return self.slippage_per_share * Decimal(quantity)


class PercentageSlippageModel(SlippageModel):
    """
    Percentage slippage model - slippage as percentage of price
    
    Example: 0.1% of price per order
    """
    
    def __init__(self, slippage_pct: Decimal = Decimal('0.001')):
        """
        Args:
            slippage_pct: Slippage percentage (e.g., 0.001 = 0.1%)
        """
        if slippage_pct < 0:
            raise ValueError(f"Slippage percentage must be non-negative, got {slippage_pct}")
        if slippage_pct > 1:
            raise ValueError(f"Slippage percentage must be <= 1, got {slippage_pct}")
        self.slippage_pct = slippage_pct
    
    def calculate_slippage(self, price: Decimal, quantity: int, 
                          volume: int, side: str) -> Decimal:
        """Calculate percentage-based slippage"""
        order_value = price * Decimal(quantity)
        return order_value * self.slippage_pct


class VolumeSlippageModel(SlippageModel):
    """
    Volume-based slippage model - slippage increases with order size relative to volume
    
    More realistic model that accounts for market impact:
    - Small orders (<1% of volume): minimal slippage
    - Medium orders (1-5% of volume): moderate slippage
    - Large orders (>5% of volume): high slippage
    """
    
    def __init__(self, base_slippage_pct: Decimal = Decimal('0.0005'),
                 volume_impact_factor: Decimal = Decimal('0.1')):
        """
        Args:
            base_slippage_pct: Base slippage percentage (e.g., 0.0005 = 0.05%)
            volume_impact_factor: Multiplier for volume impact (higher = more impact)
        """
        if base_slippage_pct < 0:
            raise ValueError(f"Base slippage must be non-negative, got {base_slippage_pct}")
        if volume_impact_factor < 0:
            raise ValueError(f"Volume impact factor must be non-negative, got {volume_impact_factor}")
        
        self.base_slippage_pct = base_slippage_pct
        self.volume_impact_factor = volume_impact_factor
    
    def calculate_slippage(self, price: Decimal, quantity: int, 
                          volume: int, side: str) -> Decimal:
        """Calculate volume-based slippage with market impact"""
        if volume <= 0:
            # No volume data, use high slippage as conservative estimate
            volume = quantity
        
        # Calculate order size as fraction of volume
        volume_fraction = Decimal(quantity) / Decimal(volume)
        
        # Slippage increases with square root of volume fraction (market impact model)
        # This reflects the nonlinear impact of large orders
        impact_multiplier = Decimal(1) + (volume_fraction ** Decimal('0.5')) * self.volume_impact_factor
        
        # Calculate total slippage
        order_value = price * Decimal(quantity)
        slippage_pct = self.base_slippage_pct * impact_multiplier
        
        return order_value * slippage_pct


class BidAskSlippageModel(SlippageModel):
    """
    Bid-ask spread slippage model - uses actual bid-ask spread
    
    Most realistic model when bid-ask data is available
    """
    
    def __init__(self, spread_fraction: Decimal = Decimal('0.5')):
        """
        Args:
            spread_fraction: Fraction of spread to use as slippage (0.5 = half spread)
        """
        if spread_fraction < 0 or spread_fraction > 1:
            raise ValueError(f"Spread fraction must be in [0, 1], got {spread_fraction}")
        self.spread_fraction = spread_fraction
    
    def calculate_slippage_with_spread(self, bid: Decimal, ask: Decimal, 
                                      quantity: int, side: str) -> Decimal:
        """
        Calculate slippage using bid-ask spread
        
        Args:
            bid: Bid price
            ask: Ask price
            quantity: Order quantity
            side: 'buy' or 'sell'
            
        Returns:
            Slippage amount
        """
        spread = ask - bid
        if spread < 0:
            raise ValueError(f"Ask must be >= bid, got bid={bid}, ask={ask}")
        
        # Use fraction of spread as slippage
        slippage_per_share = spread * self.spread_fraction
        return slippage_per_share * Decimal(quantity)
    
    def calculate_slippage(self, price: Decimal, quantity: int, 
                          volume: int, side: str) -> Decimal:
        """
        Fallback calculation when bid-ask not available
        Estimates spread as percentage of price
        """
        # Estimate spread as 0.1% of price for liquid stocks
        estimated_spread = price * Decimal('0.001')
        slippage_per_share = estimated_spread * self.spread_fraction
        return slippage_per_share * Decimal(quantity)
