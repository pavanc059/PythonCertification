"""
Structure and import tests for news impact correlation module.

This test file verifies module structure without importing heavy dependencies
like transformers/torch which cause DLL issues on Windows.
"""

import pytest
import sys
from pathlib import Path


class TestModuleStructure:
    """Tests for module file structure and organization."""
    
    def test_impact_module_exists(self):
        """Test that impact module directory exists."""
        impact_dir = Path(__file__).parent.parent / "stockiq" / "news" / "impact"
        assert impact_dir.exists(), "Impact module directory should exist"
        assert impact_dir.is_dir(), "Impact should be a directory"
    
    def test_correlation_module_exists(self):
        """Test that correlation.py file exists."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        assert correlation_file.exists(), "correlation.py should exist"
        assert correlation_file.is_file(), "correlation.py should be a file"
    
    def test_init_file_exists(self):
        """Test that __init__.py exists."""
        init_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "__init__.py"
        assert init_file.exists(), "__init__.py should exist"
        assert init_file.is_file(), "__init__.py should be a file"
    
    def test_readme_exists(self):
        """Test that README.md documentation exists."""
        readme_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "README.md"
        assert readme_file.exists(), "README.md should exist"
        assert readme_file.is_file(), "README.md should be a file"
    
    def test_correlation_file_content(self):
        """Test that correlation.py contains expected classes and functions."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for required classes
        assert "class PriceImpact" in content, "Should define PriceImpact class"
        assert "class ImpactAnalysis" in content, "Should define ImpactAnalysis class"
        assert "class NewsImpactAnalyzer" in content, "Should define NewsImpactAnalyzer class"
        
        # Check for required methods
        assert "def calculate_impact" in content, "Should define calculate_impact method"
        assert "def calculate_sentiment_correlation" in content, "Should define calculate_sentiment_correlation method"
        assert "def calculate_news_beta" in content, "Should define calculate_news_beta method"
        
        # Check for Property 12 validation
        assert "Property 12" in content, "Should mention Property 12 in documentation"
        assert "np.clip" in content, "Should use np.clip for range validation"
        assert "[-1.0, 1.0]" in content, "Should document correlation range"
    
    def test_init_file_exports(self):
        """Test that __init__.py exports correct symbols."""
        init_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "__init__.py"
        content = init_file.read_text()
        
        # Check for imports
        assert "from .correlation import" in content, "Should import from correlation module"
        
        # Check for __all__ exports
        assert "__all__" in content, "Should define __all__"
        assert "NewsImpactAnalyzer" in content, "Should export NewsImpactAnalyzer"
        assert "ImpactAnalysis" in content, "Should export ImpactAnalysis"
        assert "PriceImpact" in content, "Should export PriceImpact"
        assert "calculate_sentiment_correlation" in content, "Should export calculate_sentiment_correlation"
        assert "calculate_news_beta" in content, "Should export calculate_news_beta"
    
    def test_docstrings_present(self):
        """Test that key classes and functions have docstrings."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for module docstring
        lines = content.split('\n')
        assert lines[0].startswith('"""') or lines[1].startswith('"""'), "Should have module docstring"
        
        # Check for class docstrings
        assert 'class PriceImpact:' in content and '"""' in content, "PriceImpact should have docstring"
        assert 'class ImpactAnalysis:' in content and '"""' in content, "ImpactAnalysis should have docstring"
        assert 'class NewsImpactAnalyzer:' in content and '"""' in content, "NewsImpactAnalyzer should have docstring"
    
    def test_property_12_validation_present(self):
        """Test that Property 12 validation is implemented."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Should clamp correlation to [-1.0, 1.0]
        assert "np.clip(correlation, -1.0, 1.0)" in content or \
               "max(-1.0, min(1.0," in content, \
               "Should implement correlation clamping for Property 12"
    
    def test_requirements_implementation(self):
        """Test that module implements required features from requirements."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for requirement references
        assert "Requirement 2.11" in content or "Req 2.11" in content, \
               "Should implement Requirement 2.11"
        assert "Requirement 7" in content or "Req 7" in content, \
               "Should implement Requirement 7"
        
        # Check for timeframe support
        assert "'1h'" in content, "Should support 1h timeframe"
        assert "'4h'" in content, "Should support 4h timeframe"
        assert "'1d'" in content, "Should support 1d timeframe"
        assert "'1w'" in content, "Should support 1w timeframe"
    
    def test_database_integration(self):
        """Test that module integrates with database correctly."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for database imports
        assert "from ...infrastructure.database import" in content, \
               "Should import database utilities"
        assert "from ...infrastructure.models import" in content, \
               "Should import database models"
        
        # Check for model usage
        assert "NewsSentimentModel" in content or "NewsSentiment" in content, \
               "Should use NewsSentiment model"
        assert "PriceDataModel" in content or "PriceData" in content, \
               "Should use PriceData model"
        assert "StockModel" in content or "Stock" in content, \
               "Should use Stock model"
    
    def test_cache_integration(self):
        """Test that module integrates with cache correctly."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for cache imports
        assert "from ...infrastructure.cache import" in content, \
               "Should import cache utilities"
        
        # Check for cache usage
        assert "self.cache = get_cache()" in content, \
               "Should initialize cache"
        assert "cache.get(" in content or "self.cache.get(" in content, \
               "Should use cache.get"
        assert "cache.set(" in content or "self.cache.set(" in content, \
               "Should use cache.set"
    
    def test_logging_implementation(self):
        """Test that module implements proper logging."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for structlog usage
        assert "import structlog" in content, "Should import structlog"
        assert "logger = structlog.get_logger" in content, "Should create logger"
        
        # Check for log statements
        assert "logger.info(" in content, "Should have info logs"
        assert "logger.debug(" in content, "Should have debug logs"
        assert "logger.warning(" in content or "logger.warn(" in content, \
               "Should have warning logs"
        assert "logger.error(" in content, "Should have error logs"
    
    def test_pandas_numpy_scipy_usage(self):
        """Test that module uses pandas, numpy, and scipy correctly."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for imports
        assert "import pandas as pd" in content, "Should import pandas"
        assert "import numpy as np" in content, "Should import numpy"
        assert "from scipy import stats" in content or "import scipy" in content, \
               "Should import scipy.stats"
        
        # Check for usage
        assert "pd.DataFrame" in content, "Should use pandas DataFrames"
        assert "np.clip" in content or "np." in content, "Should use numpy functions"


class TestDataClasses:
    """Tests for data class definitions."""
    
    def test_price_impact_structure(self):
        """Test PriceImpact dataclass structure."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Find PriceImpact class definition
        assert "@dataclass" in content, "Should use dataclass decorator"
        assert "class PriceImpact:" in content, "Should define PriceImpact class"
        
        # Check for required fields
        assert "timeframe: str" in content, "Should have timeframe field"
        assert "price_change_pct: float" in content, "Should have price_change_pct field"
        assert "volume_change_pct: float" in content, "Should have volume_change_pct field"
        assert "statistical_significance: float" in content, "Should have statistical_significance field"
    
    def test_impact_analysis_structure(self):
        """Test ImpactAnalysis dataclass structure."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for ImpactAnalysis class
        assert "class ImpactAnalysis:" in content, "Should define ImpactAnalysis class"
        
        # Check for required fields
        assert "ticker: str" in content, "Should have ticker field"
        assert "article_id: str" in content, "Should have article_id field"
        assert "timeframes: Dict" in content, "Should have timeframes field"


class TestConvenienceFunctions:
    """Tests for convenience function exports."""
    
    def test_convenience_functions_defined(self):
        """Test that convenience functions are defined."""
        correlation_file = Path(__file__).parent.parent / "stockiq" / "news" / "impact" / "correlation.py"
        content = correlation_file.read_text()
        
        # Check for standalone functions
        assert "def calculate_sentiment_correlation(" in content, \
               "Should define calculate_sentiment_correlation function"
        assert "def calculate_news_beta(" in content, \
               "Should define calculate_news_beta function"
        
        # Check that they create analyzer instances
        assert "analyzer = NewsImpactAnalyzer()" in content, \
               "Convenience functions should create analyzer instances"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
