"""
Chart Export Module

Functions for exporting charts to various formats:
- PNG: Raster image format
- SVG: Vector graphics format
- PDF: Portable document format

Requirement 18.12: Export charts to PNG, SVG, and PDF formats
"""

from __future__ import annotations

import logging
import io
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Graceful imports
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly not available")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - PNG export may be limited")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available - PDF export disabled")


def export_chart_png(
    fig: go.Figure,
    filename: Union[str, Path],
    width: int = 1400,
    height: int = 800,
    scale: int = 2,
) -> bool:
    """
    Export a Plotly figure to PNG format.
    
    Args:
        fig: Plotly Figure object to export
        filename: Output filename (with or without .png extension)
        width: Image width in pixels
        height: Image height in pixels
        scale: Image scale factor for higher resolution
    
    Returns:
        True if export successful, False otherwise
    
    Requirement 18.12: PNG export support
    """
    if not PLOTLY_AVAILABLE:
        logger.error("plotly not available - cannot export PNG")
        return False
    
    try:
        # Ensure .png extension
        filename = Path(filename)
        if filename.suffix.lower() != ".png":
            filename = filename.with_suffix(".png")
        
        # Export using kaleido (plotly's static image export engine)
        fig.write_image(
            str(filename),
            format="png",
            width=width,
            height=height,
            scale=scale,
        )
        
        logger.info(f"Chart exported to PNG: {filename}")
        return True
    
    except Exception as exc:
        logger.error(f"Failed to export PNG: {exc}")
        return False


def export_chart_svg(
    fig: go.Figure,
    filename: Union[str, Path],
    width: int = 1400,
    height: int = 800,
) -> bool:
    """
    Export a Plotly figure to SVG format (vector graphics).
    
    SVG format is resolution-independent and ideal for presentations
    and publications that require scalable graphics.
    
    Args:
        fig: Plotly Figure object to export
        filename: Output filename (with or without .svg extension)
        width: Image width in pixels
        height: Image height in pixels
    
    Returns:
        True if export successful, False otherwise
    
    Requirement 18.12: SVG export support
    """
    if not PLOTLY_AVAILABLE:
        logger.error("plotly not available - cannot export SVG")
        return False
    
    try:
        # Ensure .svg extension
        filename = Path(filename)
        if filename.suffix.lower() != ".svg":
            filename = filename.with_suffix(".svg")
        
        # Export to SVG
        fig.write_image(
            str(filename),
            format="svg",
            width=width,
            height=height,
        )
        
        logger.info(f"Chart exported to SVG: {filename}")
        return True
    
    except Exception as exc:
        logger.error(f"Failed to export SVG: {exc}")
        return False


def export_chart_pdf(
    fig: go.Figure,
    filename: Union[str, Path],
    width: int = 1400,
    height: int = 800,
    title: Optional[str] = None,
    pagesize: str = "letter",
) -> bool:
    """
    Export a Plotly figure to PDF format.
    
    The chart is first rendered as PNG, then embedded in a PDF document.
    Additional metadata and titles can be included.
    
    Args:
        fig: Plotly Figure object to export
        filename: Output filename (with or without .pdf extension)
        width: Chart width in pixels
        height: Chart height in pixels
        title: Optional title to add above the chart
        pagesize: Page size ("letter" or "A4")
    
    Returns:
        True if export successful, False otherwise
    
    Requirement 18.12: PDF export support
    """
    if not PLOTLY_AVAILABLE:
        logger.error("plotly not available - cannot export PDF")
        return False
    
    if not REPORTLAB_AVAILABLE:
        logger.warning("reportlab not available - using fallback PDF export")
        return _export_pdf_fallback(fig, filename, width, height)
    
    try:
        # Ensure .pdf extension
        filename = Path(filename)
        if filename.suffix.lower() != ".pdf":
            filename = filename.with_suffix(".pdf")
        
        # First export to PNG in memory
        img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
        
        # Create PDF
        page_size = letter if pagesize.lower() == "letter" else A4
        c = canvas.Canvas(str(filename), pagesize=page_size)
        page_width, page_height = page_size
        
        # Add title if provided
        y_position = page_height - 50
        if title:
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y_position, title)
            y_position -= 30
        
        # Calculate image dimensions to fit page with margins
        margin = 50
        available_width = page_width - 2 * margin
        available_height = y_position - margin
        
        # Maintain aspect ratio
        aspect_ratio = width / height
        if available_width / aspect_ratio <= available_height:
            img_width = available_width
            img_height = available_width / aspect_ratio
        else:
            img_height = available_height
            img_width = available_height * aspect_ratio
        
        # Center image horizontally
        x_position = (page_width - img_width) / 2
        y_position = y_position - img_height
        
        # Draw image
        img_reader = ImageReader(io.BytesIO(img_bytes))
        c.drawImage(
            img_reader,
            x_position,
            y_position,
            width=img_width,
            height=img_height,
        )
        
        # Add metadata
        c.setTitle(title or "Chart Export")
        c.setAuthor("Stock Analyzer")
        c.setSubject("Financial Chart")
        
        # Save PDF
        c.save()
        
        logger.info(f"Chart exported to PDF: {filename}")
        return True
    
    except Exception as exc:
        logger.error(f"Failed to export PDF: {exc}")
        return False


def _export_pdf_fallback(
    fig: go.Figure,
    filename: Union[str, Path],
    width: int,
    height: int,
) -> bool:
    """
    Fallback PDF export using Plotly's built-in PDF writer.
    
    This is less flexible than the reportlab version but doesn't
    require additional dependencies.
    """
    try:
        filename = Path(filename)
        if filename.suffix.lower() != ".pdf":
            filename = filename.with_suffix(".pdf")
        
        fig.write_image(
            str(filename),
            format="pdf",
            width=width,
            height=height,
        )
        
        logger.info(f"Chart exported to PDF (fallback): {filename}")
        return True
    
    except Exception as exc:
        logger.error(f"Failed to export PDF (fallback): {exc}")
        return False


def export_chart_html(
    fig: go.Figure,
    filename: Union[str, Path],
    include_plotlyjs: Union[bool, str] = "cdn",
    config: Optional[dict] = None,
) -> bool:
    """
    Export a Plotly figure to interactive HTML format.
    
    While not in the requirements, HTML export is useful for
    sharing interactive charts via web or email.
    
    Args:
        fig: Plotly Figure object to export
        filename: Output filename (with or without .html extension)
        include_plotlyjs: How to include plotly.js ("cdn", True, False)
        config: Optional plotly config dictionary
    
    Returns:
        True if export successful, False otherwise
    """
    if not PLOTLY_AVAILABLE:
        logger.error("plotly not available - cannot export HTML")
        return False
    
    try:
        filename = Path(filename)
        if filename.suffix.lower() != ".html":
            filename = filename.with_suffix(".html")
        
        fig.write_html(
            str(filename),
            include_plotlyjs=include_plotlyjs,
            config=config,
        )
        
        logger.info(f"Chart exported to HTML: {filename}")
        return True
    
    except Exception as exc:
        logger.error(f"Failed to export HTML: {exc}")
        return False


def get_export_formats() -> list[str]:
    """
    Get list of available export formats based on installed dependencies.
    
    Returns:
        List of available format strings
    """
    formats = []
    
    if PLOTLY_AVAILABLE:
        formats.extend(["png", "svg", "html"])
        
        if REPORTLAB_AVAILABLE:
            formats.append("pdf")
    
    return formats


def export_chart(
    fig: go.Figure,
    filename: Union[str, Path],
    format: str = "png",
    **kwargs,
) -> bool:
    """
    Export a chart to the specified format.
    
    This is a convenience function that routes to the appropriate
    format-specific export function.
    
    Args:
        fig: Plotly Figure object to export
        filename: Output filename
        format: Export format ("png", "svg", "pdf", "html")
        **kwargs: Additional arguments passed to format-specific function
    
    Returns:
        True if export successful, False otherwise
    """
    format = format.lower()
    
    if format == "png":
        return export_chart_png(fig, filename, **kwargs)
    elif format == "svg":
        return export_chart_svg(fig, filename, **kwargs)
    elif format == "pdf":
        return export_chart_pdf(fig, filename, **kwargs)
    elif format == "html":
        return export_chart_html(fig, filename, **kwargs)
    else:
        logger.error(f"Unsupported export format: {format}")
        return False
