"""
Drawing Tools Module

Support for adding drawing tools to charts including:
- Trendlines
- Horizontal lines
- Fibonacci retracements

Requirement 18.2: Drawing tools including trendlines, horizontal lines, and Fibonacci retracements
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DrawingTool:
    """Base class for all drawing tools."""
    
    type: str
    color: str = "#ffeb3b"
    width: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert drawing tool to dictionary for chart rendering."""
        raise NotImplementedError


@dataclass
class TrendLine:
    """
    Trendline connecting two points on a chart.
    
    Attributes:
        x0: Starting x-coordinate (datetime)
        y0: Starting y-coordinate (price)
        x1: Ending x-coordinate (datetime)
        y1: Ending y-coordinate (price)
        color: Line color
        width: Line width
    """
    
    x0: datetime
    y0: float
    x1: datetime
    y1: float
    type: str = "trendline"
    color: str = "#ffeb3b"
    width: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Plotly shape."""
        return {
            "type": "trendline",
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "color": self.color,
            "width": self.width,
        }
    
    def calculate_price_at_date(self, date: datetime) -> float:
        """
        Calculate the price on the trendline at a given date.
        
        Args:
            date: Date to calculate price for
        
        Returns:
            Price on the trendline at the given date
        """
        # Convert dates to timestamps for calculation
        t0 = self.x0.timestamp()
        t1 = self.x1.timestamp()
        t = date.timestamp()
        
        # Linear interpolation
        if t1 == t0:
            return self.y0
        
        slope = (self.y1 - self.y0) / (t1 - t0)
        price = self.y0 + slope * (t - t0)
        
        return price


@dataclass
class HorizontalLine:
    """
    Horizontal line at a specific price level.
    
    Attributes:
        y: Price level for the horizontal line
        label: Optional label for the line
        color: Line color
        width: Line width
        dash: Line style ("solid", "dash", "dot", "dashdot")
    """
    
    y: float
    type: str = "horizontal"
    label: Optional[str] = None
    color: str = "#ff9800"
    width: int = 2
    dash: str = "dash"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Plotly shape."""
        return {
            "type": "horizontal",
            "y": self.y,
            "label": self.label,
            "color": self.color,
            "width": self.width,
            "dash": self.dash,
        }


@dataclass
class FibonacciRetracement:
    """
    Fibonacci retracement levels between a high and low point.
    
    Standard Fibonacci levels:
    - 0.0% (High)
    - 23.6%
    - 38.2%
    - 50.0%
    - 61.8%
    - 78.6%
    - 100.0% (Low)
    
    Attributes:
        high: High price point
        low: Low price point
        x_start: Starting x-coordinate (datetime)
        x_end: Ending x-coordinate (datetime)
        show_labels: Whether to show level labels
    """
    
    high: float
    low: float
    x_start: datetime
    x_end: datetime
    type: str = "fibonacci"
    color: str = "#ffeb3b"
    width: int = 2
    show_labels: bool = True
    
    # Fibonacci levels and their colors
    LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    LEVEL_COLORS = [
        "#f44336",  # 0% - Red
        "#ff9800",  # 23.6% - Orange
        "#ffeb3b",  # 38.2% - Yellow
        "#4caf50",  # 50% - Green
        "#2196f3",  # 61.8% - Blue
        "#9c27b0",  # 78.6% - Purple
        "#795548",  # 100% - Brown
    ]
    
    def calculate_levels(self) -> Dict[float, float]:
        """
        Calculate price levels for each Fibonacci ratio.
        
        Returns:
            Dictionary mapping Fibonacci ratios to price levels
        """
        price_range = self.high - self.low
        levels = {}
        
        for ratio in self.LEVELS:
            price = self.high - (price_range * ratio)
            levels[ratio] = price
        
        return levels
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for chart rendering."""
        return {
            "type": "fibonacci",
            "high": self.high,
            "low": self.low,
            "x_start": self.x_start,
            "x_end": self.x_end,
            "show_labels": self.show_labels,
            "levels": self.calculate_levels(),
        }
    
    def get_level_configs(self) -> List[Dict[str, Any]]:
        """
        Get configuration for each Fibonacci level for rendering.
        
        Returns:
            List of dictionaries with level configurations
        """
        levels = self.calculate_levels()
        configs = []
        
        for (ratio, price), color in zip(levels.items(), self.LEVEL_COLORS):
            label = f"{ratio * 100:.1f}%" if self.show_labels else None
            configs.append({
                "price": price,
                "label": label,
                "color": color,
                "ratio": ratio,
            })
        
        return configs


def add_trendline(
    x0: datetime,
    y0: float,
    x1: datetime,
    y1: float,
    color: str = "#ffeb3b",
    width: int = 2,
) -> TrendLine:
    """
    Create a trendline drawing tool.
    
    Args:
        x0: Starting datetime
        y0: Starting price
        x1: Ending datetime
        y1: Ending price
        color: Line color (default yellow)
        width: Line width in pixels
    
    Returns:
        TrendLine object
    """
    return TrendLine(
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        color=color,
        width=width,
    )


def add_horizontal_line(
    y: float,
    label: Optional[str] = None,
    color: str = "#ff9800",
    width: int = 2,
    dash: str = "dash",
) -> HorizontalLine:
    """
    Create a horizontal line drawing tool.
    
    Args:
        y: Price level for the line
        label: Optional text label
        color: Line color (default orange)
        width: Line width in pixels
        dash: Line style ("solid", "dash", "dot", "dashdot")
    
    Returns:
        HorizontalLine object
    """
    return HorizontalLine(
        y=y,
        label=label,
        color=color,
        width=width,
        dash=dash,
    )


def add_fibonacci_retracement(
    high: float,
    low: float,
    x_start: datetime,
    x_end: datetime,
    show_labels: bool = True,
) -> FibonacciRetracement:
    """
    Create a Fibonacci retracement drawing tool.
    
    Args:
        high: High price point
        low: Low price point
        x_start: Starting datetime for retracement range
        x_end: Ending datetime for retracement range
        show_labels: Whether to display level labels
    
    Returns:
        FibonacciRetracement object
    """
    return FibonacciRetracement(
        high=high,
        low=low,
        x_start=x_start,
        x_end=x_end,
        show_labels=show_labels,
    )


def calculate_support_resistance_levels(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    num_levels: int = 3,
    window: int = 20,
) -> Dict[str, List[float]]:
    """
    Automatically identify support and resistance levels.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        num_levels: Number of support/resistance levels to identify
        window: Lookback window for local extrema
    
    Returns:
        Dictionary with 'support' and 'resistance' lists of price levels
    """
    try:
        import pandas as pd
        import numpy as np
        
        # Find local maxima (resistance) and minima (support)
        rolling_max = high.rolling(window=window, center=True).max()
        rolling_min = low.rolling(window=window, center=True).min()
        
        # Resistance: local maxima where high equals rolling max
        resistance_points = high[high == rolling_max].dropna()
        
        # Support: local minima where low equals rolling min
        support_points = low[low == rolling_min].dropna()
        
        # Cluster nearby levels using simple rounding
        def cluster_levels(levels: pd.Series, num_clusters: int) -> List[float]:
            if len(levels) == 0:
                return []
            
            # Use percentile-based clustering
            percentiles = np.linspace(0, 100, num_clusters + 2)[1:-1]
            clusters = [np.percentile(levels, p) for p in percentiles]
            
            return sorted(clusters)
        
        resistance_levels = cluster_levels(resistance_points, num_levels)
        support_levels = cluster_levels(support_points, num_levels)
        
        return {
            "resistance": resistance_levels,
            "support": support_levels,
        }
    
    except Exception as exc:
        logger.error(f"Failed to calculate support/resistance levels: {exc}")
        return {"resistance": [], "support": []}


# Import pandas for support/resistance calculation
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available - support/resistance calculation disabled")
