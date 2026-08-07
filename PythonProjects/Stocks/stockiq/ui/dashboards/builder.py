"""
Dashboard Layout Builder

Provides UI for creating and editing custom dashboard layouts.

Requirements implemented:
- Requirement 19.1: Multiple custom layouts
- Requirement 19.2: Drag-and-drop widget arrangement (grid-based UI)
- Requirement 19.4: Save configurations per user
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logger.warning("streamlit not available")

from .custom import (
    DashboardLayout, WidgetConfig, WidgetType, 
    DashboardManager, DashboardStorage
)


# ---------------------------------------------------------------------------
# Layout Builder UI
# ---------------------------------------------------------------------------

def render_layout_builder(
    layout: Optional[DashboardLayout] = None,
    manager: Optional[DashboardManager] = None
) -> None:
    """
    Render dashboard layout builder UI.
    
    Allows users to:
    - Create new layouts
    - Edit existing layouts
    - Add/remove/configure widgets
    - Adjust widget positions and sizes
    
    Args:
        layout: Existing layout to edit (None for new layout)
        manager: Dashboard manager instance
    """
    if not STREAMLIT_AVAILABLE:
        logger.error("Streamlit not available")
        return
    
    if manager is None:
        manager = DashboardManager()
    
    st.title("🛠️ Dashboard Builder")
    
    # Initialize session state
    if "builder_layout" not in st.session_state:
        if layout:
            st.session_state.builder_layout = layout
        else:
            st.session_state.builder_layout = DashboardLayout(
                id=str(uuid.uuid4()),
                name="New Dashboard",
                description="",
                widgets=[]
            )
    
    current_layout = st.session_state.builder_layout
    
    # Layout metadata form
    with st.form("layout_metadata"):
        st.subheader("Layout Settings")
        
        name = st.text_input("Dashboard Name", value=current_layout.name)
        description = st.text_area("Description", value=current_layout.description)
        is_default = st.checkbox("Set as default layout", value=current_layout.is_default)
        
        if st.form_submit_button("Save Layout Settings"):
            current_layout.name = name
            current_layout.description = description
            current_layout.is_default = is_default
            st.success("Layout settings updated")
    
    st.divider()
    
    # Widget management
    st.subheader("Widgets")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Current Widgets")
        
        if not current_layout.widgets:
            st.info("No widgets added yet. Use the panel on the right to add widgets.")
        else:
            for i, widget in enumerate(current_layout.widgets):
                with st.expander(f"{widget.title} ({widget.type.value})"):
                    st.write(f"**Position:** Row {widget.y}, Column {widget.x}")
                    st.write(f"**Size:** {widget.w} cols × {widget.h} rows")
                    
                    # Widget configuration
                    new_title = st.text_input(f"Title###{widget.id}", value=widget.title)
                    
                    col_x, col_y = st.columns(2)
                    with col_x:
                        new_x = st.number_input(f"Column (X)###{widget.id}", 
                                               min_value=0, max_value=11, value=widget.x)
                    with col_y:
                        new_y = st.number_input(f"Row (Y)###{widget.id}", 
                                               min_value=0, max_value=20, value=widget.y)
                    
                    col_w, col_h = st.columns(2)
                    with col_w:
                        new_w = st.number_input(f"Width###{widget.id}", 
                                               min_value=1, max_value=12, value=widget.w)
                    with col_h:
                        new_h = st.number_input(f"Height###{widget.id}", 
                                               min_value=1, max_value=12, value=widget.h)
                    
                    col_update, col_delete = st.columns(2)
                    with col_update:
                        if st.button(f"Update###{widget.id}"):
                            widget.title = new_title
                            widget.x = new_x
                            widget.y = new_y
                            widget.w = new_w
                            widget.h = new_h
                            st.success("Widget updated")
                            st.rerun()
                    
                    with col_delete:
                        if st.button(f"Delete###{widget.id}", type="secondary"):
                            current_layout.widgets.pop(i)
                            st.success("Widget deleted")
                            st.rerun()
    
    with col2:
        st.markdown("### Add Widget")
        
        with st.form("add_widget"):
            widget_type_options = [wt.value for wt in WidgetType]
            selected_type = st.selectbox("Widget Type", widget_type_options)
            
            widget_title = st.text_input("Widget Title", value=selected_type.replace("_", " ").title())
            
            st.markdown("**Position & Size**")
            col_x, col_y = st.columns(2)
            with col_x:
                x_pos = st.number_input("Column (X)", min_value=0, max_value=11, value=0)
            with col_y:
                y_pos = st.number_input("Row (Y)", min_value=0, max_value=20, value=0)
            
            col_w, col_h = st.columns(2)
            with col_w:
                width = st.number_input("Width", min_value=1, max_value=12, value=6)
            with col_h:
                height = st.number_input("Height", min_value=1, max_value=12, value=4)
            
            if st.form_submit_button("Add Widget"):
                new_widget = WidgetConfig(
                    id=str(uuid.uuid4()),
                    type=WidgetType(selected_type),
                    title=widget_title,
                    x=x_pos,
                    y=y_pos,
                    w=width,
                    h=height,
                    settings={}
                )
                current_layout.widgets.append(new_widget)
                st.success(f"Added {widget_title}")
                st.rerun()
    
    st.divider()
    
    # Save and preview actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Dashboard", type="primary"):
            if manager.save_layout(current_layout):
                st.success(f"Dashboard '{current_layout.name}' saved successfully!")
            else:
                st.error("Failed to save dashboard")
    
    with col2:
        if st.button("👁️ Preview Dashboard"):
            st.session_state.preview_layout = current_layout.id
            st.info("Preview mode activated - check main dashboard view")
    
    with col3:
        if st.button("🔄 Reset"):
            del st.session_state.builder_layout
            st.rerun()
    
    # Grid visualization
    st.divider()
    st.subheader("Layout Preview (12-Column Grid)")
    
    _render_grid_preview(current_layout)


def _render_grid_preview(layout: DashboardLayout) -> None:
    """Render a visual grid preview of the layout."""
    if not STREAMLIT_AVAILABLE:
        return
    
    # Create a simple grid visualization
    st.markdown("""
    <style>
    .grid-preview {
        display: grid;
        grid-template-columns: repeat(12, 1fr);
        gap: 4px;
        margin: 10px 0;
    }
    .grid-cell {
        aspect-ratio: 1;
        border: 1px solid #ddd;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7em;
        background: #f5f5f5;
    }
    .widget-cell {
        background: #4CAF50;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Show widget positions as text (simplified version)
    if layout.widgets:
        st.markdown("**Widget Positions:**")
        for widget in layout.widgets:
            st.text(f"• {widget.title}: Row {widget.y}, Col {widget.x}, Size {widget.w}×{widget.h}")
    else:
        st.info("No widgets to display")
