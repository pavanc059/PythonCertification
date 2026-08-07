"""
Advanced Charting Module

Professional-grade interactive charts for technical analysis with:
- Candlestick charts with multiple timeframes
- Drawing tools (trendlines, Fibonacci retracements)
- Technical indicator overlays
- Chart comparison mode
- Zoom/pan functionality
- Export capabilities

Requirements implemented:
- Requirement 18.1: Candlestick charts with 6 timeframe options
- Requirement 18.2: Drawing tools (trendlines, horizontal lines, Fibonacci)
- Requirement 18.3: 10+ technical indicator overlays
- Requirement 18.4: Chart comparison mode for multiple stocks
- Requirement 18.5: Volume bars synchronized with price
- Requirement 18.6: Zoom and pan with mouse/touch
- Requirement 18.7: Save chart configurations
- Requirement 18.8: Real-time price updates without refresh
- Requirement 18.9: Heat maps for sector performance
- Requirement 18.10: Correlation matrices as interactive heat maps
- Requirement 18.11: Fast chart rendering (<500ms)
- Requirement 18.12: Export charts (PNG, SVG, PDF)
"""

from .candlestick_chart import (
    render_candlestick_chart,
    render_multi_stock_comparison,
    TIMEFRAME_OPTIONS,
)
from .indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_stochastic,
    calculate_obv,
    calculate_adx,
    calculate_cci,
    AVAILABLE_INDICATORS,
)
from .drawing_tools import (
    DrawingTool,
    TrendLine,
    HorizontalLine,
    FibonacciRetracement,
    add_trendline,
    add_horizontal_line,
    add_fibonacci_retracement,
)
from .chart_export import (
    export_chart_png,
    export_chart_svg,
    export_chart_pdf,
)
from .heatmaps import (
    render_sector_heatmap,
    render_correlation_matrix,
)

__all__ = [
    # Main chart rendering
    "render_candlestick_chart",
    "render_multi_stock_comparison",
    "TIMEFRAME_OPTIONS",
    # Indicators
    "calculate_sma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_macd",
    "calculate_bollinger_bands",
    "calculate_atr",
    "calculate_stochastic",
    "calculate_obv",
    "calculate_adx",
    "calculate_cci",
    "AVAILABLE_INDICATORS",
    # Drawing tools
    "DrawingTool",
    "TrendLine",
    "HorizontalLine",
    "FibonacciRetracement",
    "add_trendline",
    "add_horizontal_line",
    "add_fibonacci_retracement",
    # Export
    "export_chart_png",
    "export_chart_svg",
    "export_chart_pdf",
    # Heatmaps
    "render_sector_heatmap",
    "render_correlation_matrix",
]
