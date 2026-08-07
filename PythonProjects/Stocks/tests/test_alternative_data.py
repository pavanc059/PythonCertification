"""
Unit tests for alternative data collectors.

Tests cover:
- SECFilingParser: SEC EDGAR filing retrieval and parsing
- EarningsCallProcessor: NLP processing of earnings transcripts
- InsiderTradingTracker: Form 4 tracking and 90-day metrics

Requirements tested:
- Requirement 15.1-15.2: SEC filing parsing
- Requirement 15.3-15.4: Earnings call NLP processing
- Requirement 15.5-15.6: Insider trading tracking and 90-day ratios
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from stockiq.data.collectors.alternative import (
    SECFilingParser,
    EarningsCallProcessor,
    InsiderTradingTracker,
    FilingType,
    SECFiling,
    EarningsCall,
    InsiderTransaction,
    InsiderMetrics
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_cache():
    """Mock cache for testing."""
    cache = Mock()
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    cache.increment.return_value = 1
    cache.expire.return_value = True
    cache.client = Mock()
    cache.client.sismember.return_value = False
    cache.client.sadd.return_value = True
    return cache


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.sec_user_agent = 'StockIQ/1.0 (test@example.com)'
    settings.newsapi_key = None
    settings.finnhub_api_key = None
    settings.alphavantage_api_key = None
    return settings


@pytest.fixture
def sec_parser(mock_cache, mock_settings):
    """Create SECFilingParser instance with mocked dependencies."""
    with patch('stockiq.data.collectors.alternative.get_cache', return_value=mock_cache):
        with patch('stockiq.data.collectors.alternative.get_settings', return_value=mock_settings):
            parser = SECFilingParser()
            return parser


@pytest.fixture
def earnings_processor(mock_cache, mock_settings):
    """Create EarningsCallProcessor instance with mocked dependencies."""
    with patch('stockiq.data.collectors.alternative.get_cache', return_value=mock_cache):
        with patch('stockiq.data.collectors.alternative.get_settings', return_value=mock_settings):
            processor = EarningsCallProcessor()
            return processor


@pytest.fixture
def insider_tracker(mock_cache, mock_settings):
    """Create InsiderTradingTracker instance with mocked dependencies."""
    with patch('stockiq.data.collectors.alternative.get_cache', return_value=mock_cache):
        with patch('stockiq.data.collectors.alternative.get_settings', return_value=mock_settings):
            tracker = InsiderTradingTracker()
            return tracker


@pytest.fixture
def sample_sec_response():
    """Sample SEC EDGAR RSS/Atom response."""
    return """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>10-K - Annual Report</title>
            <updated>2024-03-01T10:00:00Z</updated>
            <link rel="alternate" href="https://www.sec.gov/Archives/edgar/data/320193/000032019324000006/aapl-20231230.htm"/>
        </entry>
    </feed>"""


@pytest.fixture
def sample_filing_html():
    """Sample SEC filing HTML content."""
    return """
    <html>
        <body>
            <h2>Management's Discussion and Analysis</h2>
            <p>Revenue grew 15% year over year driven by strong product sales...</p>
            
            <table>
                <tr><th>Item</th><th>2023</th><th>2022</th></tr>
                <tr><td>Revenue</td><td>$394,328</td><td>$365,817</td></tr>
                <tr><td>Net Income</td><td>$96,995</td><td>$94,680</td></tr>
            </table>
        </body>
    </html>
    """


@pytest.fixture
def sample_earnings_transcript():
    """Sample earnings call transcript."""
    return """
    Good afternoon, and welcome to the Q4 2023 earnings call.
    
    We're pleased to report record revenue of $119.5 billion, up 2% year over year.
    iPhone revenue grew to $69.7 billion, representing 58% of total revenue.
    Services revenue reached a new all-time high of $23.1 billion.
    
    Looking ahead, we expect continued growth in our Services segment.
    We're optimistic about innovation in AI and machine learning.
    Our guidance for Q1 2024 is revenue between $119-124 billion.
    
    We remain focused on delivering exceptional value to customers.
    """


@pytest.fixture
def sample_form4_xml():
    """Sample Form 4 XML content."""
    return """
    <ownershipDocument>
        <reportingOwner>
            <rptOwnerName>Cook, Timothy D.</rptOwnerName>
            <officerTitle>Chief Executive Officer</officerTitle>
            <isDirector>0</isDirector>
            <isOfficer>1</isOfficer>
        </reportingOwner>
        <nonDerivativeTransaction>
            <securityTitle>
                <value>Common Stock</value>
            </securityTitle>
            <transactionDate>
                <value>2024-03-15</value>
            </transactionDate>
            <transactionCode>S</transactionCode>
            <transactionShares>
                <value>223842</value>
            </transactionShares>
            <transactionPricePerShare>
                <value>175.50</value>
            </transactionPricePerShare>
        </nonDerivativeTransaction>
    </ownershipDocument>
    """


# ============================================================================
# SECFilingParser Tests
# ============================================================================

class TestSECFilingParser:
    """Tests for SEC filing parser."""
    
    def test_initialization(self, sec_parser):
        """Test parser initialization."""
        assert sec_parser.base_url == "https://www.sec.gov"
        assert sec_parser._min_request_interval == 0.1  # 10 req/sec
        assert 'User-Agent' in sec_parser.headers
    
    def test_rate_limiting(self, sec_parser):
        """Test rate limiting enforcement."""
        import time
        
        start_time = time.time()
        sec_parser._rate_limit()
        sec_parser._rate_limit()
        elapsed = time.time() - start_time
        
        # Should enforce at least 100ms between requests
        assert elapsed >= 0.1
    
    @patch('requests.get')
    def test_get_company_filings_success(self, mock_get, sec_parser, sample_sec_response, sample_filing_html):
        """Test successful filing retrieval (Requirement 15.1)."""
        # Mock RSS feed response
        mock_feed_response = Mock()
        mock_feed_response.content = sample_sec_response.encode()
        mock_feed_response.raise_for_status = Mock()
        
        # Mock filing content response
        mock_content_response = Mock()
        mock_content_response.text = sample_filing_html
        mock_content_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_feed_response, mock_content_response]
        
        # Clear cache for test
        sec_parser.cache.delete("sec:filings:ticker=AAPL:type=10-K:count=1")
        
        filings = sec_parser.get_company_filings(
            ticker="AAPL",
            filing_type=FilingType.FORM_10K,
            count=1
        )
        
        assert len(filings) > 0
        assert isinstance(filings[0], SECFiling)
        assert filings[0].ticker == "AAPL"
        assert filings[0].filing_type == FilingType.FORM_10K
    
    def test_extract_financial_tables(self, sec_parser, sample_filing_html):
        """Test financial table extraction (Requirement 15.2)."""
        tables = sec_parser._extract_financial_tables(sample_filing_html)
        
        assert len(tables) > 0
        assert 'headers' in tables[0]
        assert 'rows' in tables[0]
        assert 'Item' in tables[0]['headers']
    
    def test_extract_mda_section(self, sec_parser, sample_filing_html):
        """Test MD&A section extraction (Requirement 15.2)."""
        mda = sec_parser._extract_mda_section(sample_filing_html)
        
        assert mda is not None
        assert len(mda) > 50
        assert 'Revenue grew' in mda or 'revenue' in mda.lower()
    
    def test_parse_html_table(self, sec_parser):
        """Test HTML table parsing."""
        html = """
        <table>
            <tr><th>Col1</th><th>Col2</th></tr>
            <tr><td>Value1</td><td>Value2</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        result = sec_parser._parse_html_table(table)
        
        assert result is not None
        assert result['headers'] == ['Col1', 'Col2']
        assert result['rows'][0] == ['Value1', 'Value2']

# ============================================================================
# EarningsCallProcessor Tests
# ============================================================================

class TestEarningsCallProcessor:
    """Tests for earnings call processor."""
    
    def test_initialization(self, earnings_processor):
        """Test processor initialization."""
        assert earnings_processor.settings is not None
        assert earnings_processor.cache is not None
    
    def test_process_transcript_basic(self, earnings_processor, sample_earnings_transcript):
        """Test basic transcript processing (Requirement 15.3)."""
        # Clear cache
        earnings_processor.cache.delete("earnings:processed:ticker=AAPL:quarter=Q4 2023")
        
        call = earnings_processor.process_transcript(
            ticker="AAPL",
            transcript=sample_earnings_transcript,
            call_date=date(2024, 1, 15),
            quarter="Q4 2023"
        )
        
        assert isinstance(call, EarningsCall)
        assert call.ticker == "AAPL"
        assert call.quarter == "Q4 2023"
        assert call.transcript == sample_earnings_transcript
    
    def test_extract_key_topics(self, earnings_processor, sample_earnings_transcript):
        """Test topic extraction (Requirement 15.4)."""
        topics = earnings_processor._extract_key_topics(sample_earnings_transcript)
        
        assert isinstance(topics, list)
        assert len(topics) > 0
        # Should extract business-related topics
        assert any('revenue' in topic.lower() for topic in topics)
    
    def test_extract_topics_simple_fallback(self, earnings_processor, sample_earnings_transcript):
        """Test fallback topic extraction when spaCy unavailable."""
        topics = earnings_processor._extract_topics_simple(sample_earnings_transcript, 5)
        
        assert isinstance(topics, list)
        assert 'revenue' in topics or 'growth' in topics
    
    def test_extract_guidance(self, earnings_processor, sample_earnings_transcript):
        """Test guidance extraction."""
        guidance = earnings_processor._extract_guidance(sample_earnings_transcript)
        
        # Sample transcript contains guidance
        if guidance:
            assert len(guidance) > 20
            assert 'guidance' in guidance.lower() or 'expect' in guidance.lower()
    
    @patch('stockiq.data.collectors.alternative.TRANSFORMERS_AVAILABLE', True)
    def test_analyze_sentiment_with_transformers(self, earnings_processor):
        """Test sentiment analysis when transformers available (Requirement 15.4)."""
        # Mock sentiment analyzer
        mock_analyzer = Mock()
        mock_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.95}]
        earnings_processor.sentiment_analyzer = mock_analyzer
        
        sentiment = earnings_processor._analyze_sentiment("Great quarter with strong growth")
        
        assert sentiment is not None
        assert -1 <= sentiment <= 1
    
    def test_analyze_sentiment_without_transformers(self, earnings_processor):
        """Test graceful degradation when transformers unavailable."""
        earnings_processor.sentiment_analyzer = None
        
        sentiment = earnings_processor._analyze_sentiment("Great quarter")
        
        assert sentiment is None  # Should return None gracefully

# ============================================================================
# InsiderTradingTracker Tests
# ============================================================================

class TestInsiderTradingTracker:
    """Tests for insider trading tracker."""
    
    def test_initialization(self, insider_tracker):
        """Test tracker initialization."""
        assert insider_tracker.base_url == "https://www.sec.gov"
        assert insider_tracker._min_request_interval == 0.1
        assert 'User-Agent' in insider_tracker.headers
    
    def test_rate_limiting(self, insider_tracker):
        """Test rate limiting enforcement."""
        import time
        
        start_time = time.time()
        insider_tracker._rate_limit()
        insider_tracker._rate_limit()
        elapsed = time.time() - start_time
        
        # Should enforce at least 100ms between requests
        assert elapsed >= 0.1
    
    @patch('requests.get')
    def test_get_insider_transactions_success(self, mock_get, insider_tracker):
        """Test insider transaction retrieval (Requirement 15.5)."""
        # Mock Form 4 feed response
        mock_feed = Mock()
        mock_feed.content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <link rel="alternate" href="https://www.sec.gov/form4"/>
            </entry>
        </feed>"""
        mock_feed.raise_for_status = Mock()
        
        # Mock Form 4 content
        mock_content = Mock()
        mock_content.content = b"<ownershipDocument></ownershipDocument>"
        mock_content.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_feed, mock_content]
        
        # Clear cache
        insider_tracker.cache.delete("insider:transactions:ticker=AAPL:start=all:end=all")
        
        transactions = insider_tracker.get_insider_transactions(ticker="AAPL", count=1)
        
        assert isinstance(transactions, list)
    
    def test_parse_transaction_element(self, insider_tracker, sample_form4_xml):
        """Test Form 4 transaction parsing (Requirement 15.5)."""
        soup = BeautifulSoup(sample_form4_xml, 'html.parser')
        trans_elem = soup.find('nonDerivativeTransaction')
        
        transaction = insider_tracker._parse_transaction_element(
            trans_elem=trans_elem,
            ticker="AAPL",
            insider_name="Cook, Timothy D.",
            insider_role="CEO"
        )
        
        assert transaction is not None
        assert isinstance(transaction, InsiderTransaction)
        assert transaction.ticker == "AAPL"
        assert transaction.insider_name == "Cook, Timothy D."
        assert transaction.transaction_type == 'sell'  # Code 'S'
        assert transaction.shares == 223842
        assert transaction.price_per_share == Decimal('175.50')
    
    def test_extract_insider_name(self, insider_tracker, sample_form4_xml):
        """Test insider name extraction."""
        soup = BeautifulSoup(sample_form4_xml, 'html.parser')
        name = insider_tracker._extract_insider_name(soup)
        
        assert name == "Cook, Timothy D."
    
    def test_extract_insider_role(self, insider_tracker, sample_form4_xml):
        """Test insider role extraction."""
        soup = BeautifulSoup(sample_form4_xml, 'html.parser')
        role = insider_tracker._extract_insider_role(soup)
        
        assert role == "Chief Executive Officer"
    
    def test_filter_by_date_range(self, insider_tracker):
        """Test date range filtering."""
        transactions = [
            InsiderTransaction(
                ticker="AAPL",
                transaction_date=date(2024, 1, 15),
                insider_name="Insider 1",
                insider_role="CEO",
                transaction_type="buy",
                shares=1000
            ),
            InsiderTransaction(
                ticker="AAPL",
                transaction_date=date(2024, 2, 15),
                insider_name="Insider 2",
                insider_role="CFO",
                transaction_type="sell",
                shares=500
            ),
            InsiderTransaction(
                ticker="AAPL",
                transaction_date=date(2024, 3, 15),
                insider_name="Insider 3",
                insider_role="CTO",
                transaction_type="buy",
                shares=750
            )
        ]
        
        filtered = insider_tracker._filter_by_date_range(
            transactions,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 28)
        )
        
        assert len(filtered) == 1
        assert filtered[0].transaction_date == date(2024, 2, 15)
    
    def test_calculate_90day_metrics(self, insider_tracker):
        """Test 90-day metrics calculation (Requirement 15.6)."""
        # Create sample transactions
        sample_transactions = [
            InsiderTransaction(
                ticker="AAPL",
                transaction_date=date.today() - timedelta(days=30),
                insider_name="Insider 1",
                insider_role="CEO",
                transaction_type="buy",
                shares=10000,
                price_per_share=Decimal("150.00"),
                total_value=Decimal("1500000")
            ),
            InsiderTransaction(
                ticker="AAPL",
                transaction_date=date.today() - timedelta(days=20),
                insider_name="Insider 2",
                insider_role="CFO",
                transaction_type="sell",
                shares=5000,
                price_per_share=Decimal("155.00"),
                total_value=Decimal("775000")
            ),
            InsiderTransaction(
                ticker="AAPL",
                transaction_date=date.today() - timedelta(days=10),
                insider_name="Insider 3",
                insider_role="CTO",
                transaction_type="buy",
                shares=3000,
                price_per_share=Decimal("160.00"),
                total_value=Decimal("480000")
            )
        ]
        
        # Mock get_insider_transactions
        with patch.object(
            insider_tracker,
            'get_insider_transactions',
            return_value=sample_transactions
        ):
            metrics = insider_tracker.calculate_90day_metrics(ticker="AAPL")
        
        assert isinstance(metrics, InsiderMetrics)
        assert metrics.ticker == "AAPL"
        assert metrics.total_buy_transactions == 2
        assert metrics.total_sell_transactions == 1
        assert metrics.total_buy_shares == 13000
        assert metrics.total_sell_shares == 5000
        assert metrics.total_buy_value == Decimal("1980000")
        assert metrics.total_sell_value == Decimal("775000")
        
        # Check buy/sell ratio: buy_shares / (buy_shares + sell_shares)
        expected_ratio = 13000 / (13000 + 5000)
        assert abs(metrics.buy_sell_ratio - expected_ratio) < 0.001
    
    def test_calculate_90day_metrics_no_transactions(self, insider_tracker):
        """Test metrics calculation with no transactions."""
        with patch.object(
            insider_tracker,
            'get_insider_transactions',
            return_value=[]
        ):
            metrics = insider_tracker.calculate_90day_metrics(ticker="AAPL")
        
        assert metrics.total_buy_transactions == 0
        assert metrics.total_sell_transactions == 0
        assert metrics.buy_sell_ratio == 0.0


# ============================================================================
# Data Model Tests
# ============================================================================

class TestDataModels:
    """Tests for data model classes."""
    
    def test_sec_filing_model(self):
        """Test SECFiling data model."""
        filing = SECFiling(
            ticker="AAPL",
            filing_type=FilingType.FORM_10K,
            filing_date=date(2024, 3, 1),
            url="https://www.sec.gov/example",
            accession_number="0000320193-24-000006",
            content="<html>Filing content</html>",
            financial_tables=[{'headers': ['A', 'B'], 'rows': [['1', '2']]}],
            md_section="Management discussion content"
        )
        
        assert filing.ticker == "AAPL"
        assert filing.filing_type == FilingType.FORM_10K
        assert filing.accession_number == "0000320193-24-000006"
        assert len(filing.financial_tables) == 1
        assert filing.md_section is not None
    
    def test_earnings_call_model(self):
        """Test EarningsCall data model."""
        call = EarningsCall(
            ticker="AAPL",
            call_date=date(2024, 1, 15),
            quarter="Q4 2023",
            transcript="Earnings call transcript...",
            sentiment_score=0.75,
            key_topics=["revenue", "growth", "innovation"],
            company_guidance="Q1 2024 revenue guidance..."
        )
        
        assert call.ticker == "AAPL"
        assert call.quarter == "Q4 2023"
        assert call.sentiment_score == 0.75
        assert len(call.key_topics) == 3
    
    def test_insider_transaction_model(self):
        """Test InsiderTransaction data model."""
        transaction = InsiderTransaction(
            ticker="AAPL",
            transaction_date=date(2024, 3, 15),
            insider_name="Cook, Timothy D.",
            insider_role="CEO",
            transaction_type="sell",
            shares=223842,
            price_per_share=Decimal("175.50"),
            total_value=Decimal("39284271.00")
        )
        
        assert transaction.ticker == "AAPL"
        assert transaction.insider_name == "Cook, Timothy D."
        assert transaction.transaction_type == "sell"
        assert transaction.shares == 223842
    
    def test_insider_metrics_model(self):
        """Test InsiderMetrics data model."""
        metrics = InsiderMetrics(
            ticker="AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            total_buy_transactions=5,
            total_sell_transactions=3,
            total_buy_shares=50000,
            total_sell_shares=30000,
            total_buy_value=Decimal("7500000"),
            total_sell_value=Decimal("4500000"),
            buy_sell_ratio=0.625
        )
        
        assert metrics.ticker == "AAPL"
        assert metrics.total_buy_transactions == 5
        assert metrics.total_sell_transactions == 3
        assert metrics.buy_sell_ratio == 0.625


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for alternative data collectors."""
    
    def test_filing_types_enum(self):
        """Test FilingType enum."""
        assert FilingType.FORM_10K.value == "10-K"
        assert FilingType.FORM_10Q.value == "10-Q"
        assert FilingType.FORM_8K.value == "8-K"
        assert FilingType.FORM_4.value == "4"
    
    def test_graceful_degradation_nlp(self, earnings_processor):
        """Test graceful degradation when NLP dependencies unavailable."""
        # Should not raise exception even if transformers/spacy unavailable
        call = earnings_processor.process_transcript(
            ticker="AAPL",
            transcript="Sample transcript",
            call_date=date(2024, 1, 15),
            quarter="Q4 2023"
        )
        
        assert isinstance(call, EarningsCall)
        assert call.transcript == "Sample transcript"
