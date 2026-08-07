"""
Tests for customizable dashboard system.

Tests coverage:
- Dashboard layout creation and management
- Widget configuration
- Storage persistence
- Multiple layouts per user
- Widget type availability (15+ types)
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from stockiq.ui.dashboards.custom import (
    WidgetType, WidgetConfig, DashboardLayout,
    DashboardStorage, DashboardManager
)


# ---------------------------------------------------------------------------
# Test WidgetConfig
# ---------------------------------------------------------------------------

def test_widget_config_creation():
    """Test creating a widget configuration."""
    widget = WidgetConfig(
        id="test-widget-1",
        type=WidgetType.PRICE_CHART,
        title="AAPL Price Chart",
        x=0,
        y=0,
        w=6,
        h=4,
        settings={"ticker": "AAPL", "timeframe": "1d"}
    )
    
    assert widget.id == "test-widget-1"
    assert widget.type == WidgetType.PRICE_CHART
    assert widget.title == "AAPL Price Chart"
    assert widget.x == 0
    assert widget.y == 0
    assert widget.w == 6
    assert widget.h == 4
    assert widget.settings["ticker"] == "AAPL"


def test_widget_config_serialization():
    """Test widget configuration serialization to/from dict."""
    widget = WidgetConfig(
        id="test-widget-2",
        type=WidgetType.NEWS_FEED,
        title="Latest News",
        x=6,
        y=0,
        w=6,
        h=4,
        settings={"limit": 5}
    )
    
    # Serialize
    widget_dict = widget.to_dict()
    assert widget_dict["id"] == "test-widget-2"
    assert widget_dict["type"] == "news_feed"
    assert widget_dict["settings"]["limit"] == 5
    
    # Deserialize
    restored = WidgetConfig.from_dict(widget_dict)
    assert restored.id == widget.id
    assert restored.type == widget.type
    assert restored.title == widget.title
    assert restored.settings == widget.settings


# ---------------------------------------------------------------------------
# Test DashboardLayout
# ---------------------------------------------------------------------------

def test_dashboard_layout_creation():
    """Test creating a dashboard layout."""
    widgets = [
        WidgetConfig("w1", WidgetType.MARKET_INDICES, "Indices", 0, 0, 12, 2, {}),
        WidgetConfig("w2", WidgetType.TOP_MOVERS, "Movers", 0, 2, 6, 4, {}),
        WidgetConfig("w3", WidgetType.NEWS_FEED, "News", 6, 2, 6, 4, {})
    ]
    
    layout = DashboardLayout(
        id="layout-1",
        name="Market Overview",
        description="Comprehensive market monitoring",
        widgets=widgets,
        is_default=True
    )
    
    assert layout.id == "layout-1"
    assert layout.name == "Market Overview"
    assert len(layout.widgets) == 3
    assert layout.is_default is True


def test_dashboard_layout_serialization():
    """Test dashboard layout serialization to/from dict."""
    widgets = [
        WidgetConfig("w1", WidgetType.WATCHLIST, "My Watchlist", 0, 0, 6, 4, {})
    ]
    
    layout = DashboardLayout(
        id="layout-2",
        name="Trading Desk",
        description="Active trading dashboard",
        widgets=widgets,
        is_default=False,
        created_at=datetime(2025, 1, 1, 12, 0, 0)
    )
    
    # Serialize
    layout_dict = layout.to_dict()
    assert layout_dict["id"] == "layout-2"
    assert layout_dict["name"] == "Trading Desk"
    assert len(layout_dict["widgets"]) == 1
    
    # Deserialize
    restored = DashboardLayout.from_dict(layout_dict)
    assert restored.id == layout.id
    assert restored.name == layout.name
    assert len(restored.widgets) == 1
    assert restored.widgets[0].type == WidgetType.WATCHLIST


# ---------------------------------------------------------------------------
# Test DashboardStorage
# ---------------------------------------------------------------------------

def test_dashboard_storage_save_and_load():
    """Test saving and loading dashboard layouts."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = DashboardStorage(temp_path)
        
        # Create a layout
        layout = DashboardLayout(
            id="test-layout",
            name="Test Dashboard",
            description="Testing storage",
            widgets=[
                WidgetConfig("w1", WidgetType.ALERTS, "Alerts", 0, 0, 4, 3, {})
            ]
        )
        
        # Save
        success = storage.save_layout(layout, user_id="test_user")
        assert success is True
        
        # Load
        layouts = storage.load_layouts(user_id="test_user")
        assert len(layouts) == 1
        assert layouts[0].id == "test-layout"
        assert layouts[0].name == "Test Dashboard"
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_dashboard_storage_multiple_layouts():
    """Test storing multiple layouts for same user."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = DashboardStorage(temp_path)
        
        layout1 = DashboardLayout(
            id="layout-1", name="Layout 1", description="First", widgets=[]
        )
        layout2 = DashboardLayout(
            id="layout-2", name="Layout 2", description="Second", widgets=[]
        )
        
        storage.save_layout(layout1, user_id="user1")
        storage.save_layout(layout2, user_id="user1")
        
        layouts = storage.load_layouts(user_id="user1")
        assert len(layouts) == 2
        assert {l.id for l in layouts} == {"layout-1", "layout-2"}
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_dashboard_storage_delete_layout():
    """Test deleting a dashboard layout."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = DashboardStorage(temp_path)
        
        layout = DashboardLayout(
            id="to-delete", name="Delete Me", description="", widgets=[]
        )
        storage.save_layout(layout, user_id="test_user")
        
        # Verify it exists
        layouts = storage.load_layouts(user_id="test_user")
        assert len(layouts) == 1
        
        # Delete it
        success = storage.delete_layout("to-delete", user_id="test_user")
        assert success is True
        
        # Verify it's gone
        layouts = storage.load_layouts(user_id="test_user")
        assert len(layouts) == 0
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test DashboardManager
# ---------------------------------------------------------------------------

def test_dashboard_manager_create_defaults():
    """Test creating default dashboard layouts."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = DashboardStorage(temp_path)
        manager = DashboardManager(storage)
        
        defaults = manager.create_default_layouts()
        
        # Should create at least 3 default layouts
        assert len(defaults) >= 3
        
        # Check first layout (Market Overview)
        market_overview = defaults[0]
        assert market_overview.name == "Market Overview"
        assert market_overview.is_default is True
        assert len(market_overview.widgets) > 0
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_dashboard_manager_get_layouts():
    """Test getting layouts with auto-creation of defaults."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = DashboardStorage(temp_path)
        manager = DashboardManager(storage)
        
        # First call should create defaults
        layouts = manager.get_layouts()
        assert len(layouts) >= 3
        
        # Second call should return same layouts
        layouts2 = manager.get_layouts()
        assert len(layouts2) == len(layouts)
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Test Widget Types (Requirement 19.3: At least 15 widget types)
# ---------------------------------------------------------------------------

def test_widget_types_count():
    """Test that at least 15 widget types are available."""
    widget_types = list(WidgetType)
    
    # Requirement 19.3: At least 15 widget types
    assert len(widget_types) >= 15, f"Expected at least 15 widget types, got {len(widget_types)}"


def test_all_widget_types_have_unique_values():
    """Test that all widget types have unique enum values."""
    values = [wt.value for wt in WidgetType]
    assert len(values) == len(set(values)), "Widget type values must be unique"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_end_to_end_layout_workflow():
    """Test complete workflow: create, save, load, modify, delete."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        storage = DashboardStorage(temp_path)
        manager = DashboardManager(storage)
        
        # 1. Create a new layout
        layout = DashboardLayout(
            id="workflow-test",
            name="Workflow Test",
            description="Testing complete workflow",
            widgets=[
                WidgetConfig("w1", WidgetType.PRICE_CHART, "Chart", 0, 0, 6, 4, {}),
                WidgetConfig("w2", WidgetType.NEWS_FEED, "News", 6, 0, 6, 4, {})
            ]
        )
        
        # 2. Save it
        success = manager.save_layout(layout)
        assert success is True
        
        # 3. Load it back
        loaded = storage.get_layout("workflow-test")
        assert loaded is not None
        assert loaded.name == "Workflow Test"
        assert len(loaded.widgets) == 2
        
        # 4. Modify it
        loaded.widgets.append(
            WidgetConfig("w3", WidgetType.ALERTS, "Alerts", 0, 4, 4, 3, {})
        )
        success = manager.save_layout(loaded)
        assert success is True
        
        # 5. Verify modification
        reloaded = storage.get_layout("workflow-test")
        assert len(reloaded.widgets) == 3
        
        # 6. Delete it
        success = manager.delete_layout("workflow-test")
        assert success is True
        
        # 7. Verify deletion
        deleted = storage.get_layout("workflow-test")
        assert deleted is None
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_widget_renderers_available():
    """Test that widget renderers are available for core types."""
    from stockiq.ui.dashboards.widgets import WIDGET_RENDERERS
    
    # Requirement 19.3: At least 15 widget types with renderers
    assert len(WIDGET_RENDERERS) >= 15, \
        f"Expected at least 15 widget renderers, got {len(WIDGET_RENDERERS)}"
    
    # Check key widget types are present
    essential_types = [
        "price_chart", "market_indices", "news_feed", 
        "watchlist", "alerts", "portfolio_summary"
    ]
    
    for widget_type in essential_types:
        assert widget_type in WIDGET_RENDERERS, \
            f"Essential widget type '{widget_type}' not found in renderers"
