"""
Tests for Daily Report Generator.

This module tests Requirements 8.1-8.12:
- Report generation functionality
- All section generators
- Multi-channel delivery
- Content accuracy and formatting
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from stockiq.reports.daily_report import (
    DailyReportGenerator,
    Report,
    ReportSection,
    generate_and_deliver_daily_report
)
from stockiq.infrastructure.models import (
    Stock,
    DailyPrediction,
    TopMover,
    NewsArticle,
    NewsSentiment,
    PredictionCategory,
    NewsCategory
)


class TestReportSection:
    """Test ReportSection data class."""
    
    def test_report_section_creation(self):
        """Test creating a report section."""
        section = ReportSection(
            title="Test Section",
            content="Test content",
            priority=1
        )
        
        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.priority == 1


class TestReport:
    """Test Report data class."""
    
    def test_report_creation(self):
        """Test creating a report."""
        report = Report(
            report_id="test_report_1",
            generation_time=datetime.now(),
            target_date=date.today(),
            sections=[],
            metadata={}
        )
        
        assert report.report_id == "test_report_1"
        assert isinstance(report.generation_time, datetime)
        assert isinstance(report.target_date, date)
        assert len(report.sections) == 0
    
    def test_add_section(self):
        """Test adding sections to a report."""
        report = Report(
            report_id="test_report_1",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        report.add_section("Section 1", "Content 1", priority=1)
        report.add_section("Section 2", "Content 2", priority=2)
        
        assert len(report.sections) == 2
        assert report.sections[0].title == "Section 1"
        assert report.sections[1].title == "Section 2"
    
    def test_to_text(self):
        """Test converting report to text format."""
        report = Report(
            report_id="test_report_1",
            generation_time=datetime(2024, 1, 15, 8, 0, 0),
            target_date=date(2024, 1, 15)
        )
        
        report.add_section("Test Section", "Test content", priority=1)
        
        text = report.to_text()
        
        assert "DAILY MARKET INTELLIGENCE REPORT" in text
        assert "2024-01-15" in text
        assert "Test Section" in text
        assert "Test content" in text
    
    def test_sections_sorted_by_priority(self):
        """Test that sections are sorted by priority in text output."""
        report = Report(
            report_id="test_report_1",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        report.add_section("Low Priority", "Content 3", priority=3)
        report.add_section("High Priority", "Content 1", priority=1)
        report.add_section("Medium Priority", "Content 2", priority=2)
        
        text = report.to_text()
        
        # High priority should appear before low priority
        high_pos = text.index("High Priority")
        medium_pos = text.index("Medium Priority")
        low_pos = text.index("Low Priority")
        
        assert high_pos < medium_pos < low_pos



class TestDailyReportGenerator:
    """Test DailyReportGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create a DailyReportGenerator instance."""
        return DailyReportGenerator()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session
    
    def test_generator_initialization(self, generator):
        """Test generator initializes correctly."""
        assert generator is not None
        assert generator.cache is not None
        assert generator.movers_calculator is not None
        assert generator.summarizer is not None
    
    @patch('stockiq.reports.daily_report.get_db_context')
    def test_generate_daily_report_structure(self, mock_db_context, generator):
        """Test that generate_daily_report creates proper structure."""
        # Mock database context
        mock_session = MagicMock()
        mock_db_context.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        # Generate report
        report = generator.generate_daily_report(user_id=1)
        
        # Verify structure
        assert isinstance(report, Report)
        assert report.report_id is not None
        assert isinstance(report.generation_time, datetime)
        assert isinstance(report.target_date, date)
        assert len(report.sections) > 0
        assert report.metadata['user_id'] == 1
    
    @patch('stockiq.reports.daily_report.get_db_context')
    def test_generate_daily_report_has_all_sections(self, mock_db_context, generator):
        """Test that report includes all required sections."""
        # Mock database
        mock_session = MagicMock()
        mock_db_context.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        report = generator.generate_daily_report(user_id=1)
        
        section_titles = [s.title for s in report.sections]
        
        # Verify all required sections present
        assert "TOP PREDICTIONS" in section_titles
        assert "MARKET OUTLOOK" in section_titles
        assert "KEY NEWS STORIES" in section_titles
        assert "SECTOR ROTATION" in section_titles
        assert "ECONOMIC CALENDAR" in section_titles
        assert "PREDICTION ACCURACY" in section_titles
        assert "RISK WARNINGS" in section_titles
    
    def test_generate_top_predictions_section_no_data(self, generator):
        """Test predictions section with no data."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = []
            
            result = generator.generate_top_predictions_section()
            
            assert "No predictions available" in result
    
    def test_generate_market_outlook_section_bullish(self, generator):
        """Test market outlook with bullish sentiment."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Create mock predictions (70% bullish)
            mock_predictions = []
            for i in range(70):
                pred = Mock()
                pred.category = PredictionCategory.STRONG_BUY
                pred.confidence = 75.0
                mock_predictions.append(pred)
            
            for i in range(30):
                pred = Mock()
                pred.category = PredictionCategory.HOLD
                pred.confidence = 60.0
                mock_predictions.append(pred)
            
            mock_session.query.return_value.filter.return_value.all.return_value = mock_predictions
            
            result = generator.generate_market_outlook_section()
            
            assert "BULLISH" in result
            assert "70.0%" in result
    
    def test_generate_market_outlook_section_bearish(self, generator):
        """Test market outlook with bearish sentiment."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Create mock predictions (70% bearish)
            mock_predictions = []
            for i in range(70):
                pred = Mock()
                pred.category = PredictionCategory.STRONG_SELL
                pred.confidence = 75.0
                mock_predictions.append(pred)
            
            for i in range(30):
                pred = Mock()
                pred.category = PredictionCategory.HOLD
                pred.confidence = 60.0
                mock_predictions.append(pred)
            
            mock_session.query.return_value.filter.return_value.all.return_value = mock_predictions
            
            result = generator.generate_market_outlook_section()
            
            assert "BEARISH" in result
            assert "70.0%" in result
    
    def test_generate_key_news_section_no_data(self, generator):
        """Test news section with no data."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            
            result = generator.generate_key_news_section()
            
            assert "No significant news" in result
    
    def test_generate_accuracy_summary_section_no_data(self, generator):
        """Test accuracy section with no data."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = []
            
            result = generator.generate_accuracy_summary_section()
            
            assert "not yet available" in result
    
    def test_generate_risk_warnings_section_low_confidence(self, generator):
        """Test risk warnings with low confidence predictions."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Create mock low confidence prediction
            stock = Mock()
            stock.ticker = "TEST"
            stock.name = "Test Corp"
            
            pred = Mock()
            pred.confidence = 45.0  # Low confidence
            pred.category = PredictionCategory.BUY
            pred.lower_bound = Decimal("90.0")
            pred.upper_bound = Decimal("110.0")
            pred.predicted_price = Decimal("100.0")
            
            mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [(pred, stock)]
            
            result = generator.generate_risk_warnings_section()
            
            assert "HIGH RISK" in result
            assert "Low confidence" in result
    
    def test_generate_risk_warnings_section_no_warnings(self, generator):
        """Test risk warnings with no high-risk predictions."""
        with patch('stockiq.reports.daily_report.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Create mock high confidence prediction
            stock = Mock()
            stock.ticker = "TEST"
            stock.name = "Test Corp"
            
            pred = Mock()
            pred.confidence = 85.0  # High confidence
            pred.category = PredictionCategory.BUY
            pred.lower_bound = Decimal("98.0")
            pred.upper_bound = Decimal("102.0")
            pred.predicted_price = Decimal("100.0")
            
            mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [(pred, stock)]
            
            result = generator.generate_risk_warnings_section()
            
            assert "No significant risk warnings" in result
    
    def test_deliver_report_invalid_channel(self, generator):
        """Test delivery with invalid channel raises error."""
        report = Report(
            report_id="test",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        with pytest.raises(ValueError, match="Invalid channels"):
            generator.deliver_report(report, user_id=1, channels=['invalid'])
    
    def test_deliver_report_email_channel(self, generator):
        """Test delivery via email channel."""
        report = Report(
            report_id="test",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        # Should not raise error (even if not fully implemented)
        generator.deliver_report(report, user_id=1, channels=['email'])
    
    def test_deliver_report_in_app_channel(self, generator):
        """Test delivery via in-app channel."""
        report = Report(
            report_id="test",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        with patch.object(generator.cache, 'set') as mock_set:
            generator.deliver_report(report, user_id=1, channels=['in_app'])
            
            # Verify cache.set was called
            assert mock_set.called
    
    def test_deliver_report_pdf_channel(self, generator):
        """Test delivery via PDF channel."""
        report = Report(
            report_id="test",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        # Should not raise error
        generator.deliver_report(report, user_id=1, channels=['pdf'])
    
    def test_deliver_report_multiple_channels(self, generator):
        """Test delivery via multiple channels."""
        report = Report(
            report_id="test",
            generation_time=datetime.now(),
            target_date=date.today()
        )
        
        with patch.object(generator.cache, 'set'):
            generator.deliver_report(report, user_id=1, channels=['email', 'in_app', 'pdf'])


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('stockiq.reports.daily_report.DailyReportGenerator')
    def test_generate_and_deliver_daily_report(self, mock_generator_class):
        """Test convenience function for generation and delivery."""
        mock_generator = Mock()
        mock_report = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_daily_report.return_value = mock_report
        
        result = generate_and_deliver_daily_report(user_id=1, channels=['in_app'])
        
        # Verify generator was created
        assert mock_generator_class.called
        
        # Verify report was generated
        mock_generator.generate_daily_report.assert_called_once_with(1)
        
        # Verify report was delivered
        mock_generator.deliver_report.assert_called_once_with(mock_report, 1, ['in_app'])
        
        # Verify report was returned
        assert result == mock_report
    
    @patch('stockiq.reports.daily_report.DailyReportGenerator')
    def test_generate_and_deliver_default_channels(self, mock_generator_class):
        """Test convenience function with default channels."""
        mock_generator = Mock()
        mock_report = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_daily_report.return_value = mock_report
        
        result = generate_and_deliver_daily_report(user_id=1)
        
        # Verify default channel is in_app
        mock_generator.deliver_report.assert_called_once_with(mock_report, 1, ['in_app'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
