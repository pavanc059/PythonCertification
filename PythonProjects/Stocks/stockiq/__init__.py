"""
StockIQ - Institutional-Grade Stock Analyzer

A comprehensive stock analysis platform providing real-time market intelligence,
AI-powered predictions, and institutional-grade analytics.
"""

__version__ = "2.0.0"
__author__ = "StockIQ Team"

# Eagerly seed sys.modules with subpackages to prevent Streamlit hot-reload race conditions
from . import core as core
from . import data as data
from . import models as models
from . import news as news
from . import ui as ui
from . import infrastructure as infrastructure
from . import analytics as analytics

__all__ = ["core", "data", "models", "news", "ui", "infrastructure", "analytics"]
