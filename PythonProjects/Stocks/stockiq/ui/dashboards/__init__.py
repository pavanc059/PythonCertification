"""
Dashboard modules for StockIQ web interface.

Modules:
- daily_brief.py: Daily Market Brief - default landing page
- penny_stocks.py: Penny Stock Momentum dashboard
- custom.py: Customizable dashboard system with multiple layouts
- widgets.py: Widget library (15+ widget types)
- builder.py: Dashboard layout builder UI
"""

from .daily_brief import render_daily_dashboard
from .penny_stocks import render_penny_dashboard
from .custom import render_custom_dashboard, get_available_widget_types
from .builder import render_layout_builder

__all__ = [
    "render_daily_dashboard",
    "render_penny_dashboard",
    "render_custom_dashboard",
    "get_available_widget_types",
    "render_layout_builder"
]
