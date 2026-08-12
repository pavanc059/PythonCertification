"""
Alternative data collectors for institutional-grade analysis.

This module implements collectors for alternative data sources:
- SECFilingParser: Parse 10-K, 10-Q, 8-K filings from SEC EDGAR
- EarningsCallProcessor: Process earnings call transcripts with NLP
- InsiderTradingTracker: Track insider trading transactions from Form 4

Requirements implemented:
- Requirement 15.1-15.2: Parse SEC filings and extract financial tables
- Requirement 15.3-15.4: Process earnings call transcripts with NLP
- Requirement 15.5-15.6: Track insider trading with 90-day ratios

Features:
- Rate limiting (10 requests/second for SEC EDGAR)
- Retry logic with exponential backoff
- HTML/XBRL parsing
- NLP sentiment analysis and topic extraction
- Redis caching
- Database persistence
"""

import hashlib
import re
import time
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

import requests
import structlog
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

# Optional NLP dependencies (graceful degradation)
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except (ImportError, OSError) as e:
    # OSError for DLL loading issues on Windows
    TRANSFORMERS_AVAILABLE = False
    pipeline = None

try:
    import spacy
    SPACY_AVAILABLE = True
except (ImportError, OSError) as e:
    SPACY_AVAILABLE = False
    spacy = None

from ...infrastructure.config import get_settings
from ...infrastructure.cache import get_cache, CacheKeyPatterns

logger = structlog.get_logger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class FilingType(Enum):
    """SEC filing types."""
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_4 = "4"
    FORM_DEF14A = "DEF 14A"


@dataclass
class SECFiling:
    """SEC filing document."""
    ticker: str
    filing_type: FilingType
    filing_date: date
    url: str
    accession_number: str
    content: str
    financial_tables: Optional[List[Dict]] = None
    md_section: Optional[str] = None  # Management Discussion & Analysis


@dataclass
class EarningsCall:
    """Earnings call transcript."""
    ticker: str
    call_date: date
    quarter: str
    transcript: str
    sentiment_score: Optional[float] = None
    key_topics: Optional[List[str]] = None
    company_guidance: Optional[str] = None


@dataclass
class InsiderTransaction:
    """Insider trading transaction."""
    ticker: str
    transaction_date: date
    insider_name: str
    insider_role: str
    transaction_type: str  # 'buy' or 'sell'
    shares: int
    price_per_share: Optional[Decimal] = None
    total_value: Optional[Decimal] = None


@dataclass
class InsiderMetrics:
    """Insider trading metrics."""
    ticker: str
    start_date: date
    end_date: date
    total_buy_transactions: int
    total_sell_transactions: int
    total_buy_shares: int
    total_sell_shares: int
    total_buy_value: Decimal
    total_sell_value: Decimal
    buy_sell_ratio: float  # buy_shares / (buy_shares + sell_shares)


# ============================================================================
# SEC Filing Parser
# ============================================================================

class SECFilingParser:
    """
    Parse SEC filings from EDGAR database.
    
    Features:
    - Parse 10-K, 10-Q, and 8-K filings
    - Extract financial tables and MD&A sections
    - Support HTML and XBRL formats
    - Rate limiting (10 requests/second for SEC)
    - Retry logic with exponential backoff
    
    SEC EDGAR API: https://www.sec.gov/edgar/sec-api-documentation
    Rate Limit: 10 requests per second
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.base_url = "https://www.sec.gov"
        self.api_base = f"{self.base_url}/cgi-bin/browse-edgar"
        
        # Rate limiting: 10 requests/second = 100ms between requests
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms
        
        # User agent (required by SEC)
        self.headers = {
            'User-Agent': self.settings.sec_user_agent or 'StockIQ/1.0 (institutional@example.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
    
    def _rate_limit(self):
        """Enforce rate limiting (10 requests/second)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_company_filings(
        self,
        ticker: str,
        filing_type: FilingType,
        count: int = 10
    ) -> List[SECFiling]:
        """
        Get recent filings for a company.
        
        Args:
            ticker: Stock ticker symbol
            filing_type: Type of filing to retrieve
            count: Number of filings to retrieve
        
        Returns:
            List of SECFiling objects
        """
        # Check cache
        cache_key = CacheKeyPatterns.format_key(
            "sec:filings",
            ticker=ticker,
            type=filing_type.value,
            count=count
        )
        
        cached_filings = self.cache.get(cache_key)
        if cached_filings:
            logger.debug("sec_filings_cache_hit", ticker=ticker, filing_type=filing_type.value)
            return cached_filings
        
        try:
            self._rate_limit()
            
            # Search for filings
            params = {
                'action': 'getcompany',
                'CIK': ticker,
                'type': filing_type.value,
                'dateb': '',
                'owner': 'exclude',
                'count': count,
                'output': 'atom'
            }
            
            response = requests.get(
                self.api_base,
                params=params,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            
            # Parse RSS/Atom feed
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')
            
            filings = []
            for entry in entries:
                try:
                    filing = self._parse_filing_entry(entry, ticker, filing_type)
                    if filing:
                        filings.append(filing)
                except Exception as e:
                    logger.warning("filing_parse_error", ticker=ticker, error=str(e))
                    continue
            
            # Cache for 24 hours
            self.cache.set(cache_key, filings, ttl=86400)
            
            logger.info(
                "sec_filings_retrieved",
                ticker=ticker,
                filing_type=filing_type.value,
                count=len(filings)
            )
            
            return filings
            
        except requests.exceptions.RequestException as e:
            logger.error("sec_filing_fetch_failed", ticker=ticker, error=str(e))
            raise
    
    def _parse_filing_entry(
        self,
        entry,
        ticker: str,
        filing_type: FilingType
    ) -> Optional[SECFiling]:
        """Parse a single filing entry from the feed."""
        try:
            # Extract filing details
            title = entry.find('title').text if entry.find('title') else ""
            updated = entry.find('updated').text if entry.find('updated') else ""
            link = entry.find('link', {'rel': 'alternate'})
            
            if not link or not link.get('href'):
                return None
            
            filing_url = link['href']
            
            # Extract accession number from URL or title
            accession_match = re.search(r'(\d{10}-\d{2}-\d{6})', filing_url)
            accession_number = accession_match.group(1) if accession_match else ""
            
            # Parse filing date
            filing_date = datetime.fromisoformat(updated.replace('Z', '+00:00')).date()
            
            # Fetch full filing content
            filing_content = self._fetch_filing_content(filing_url)
            
            # Extract financial tables and MD&A
            financial_tables = self._extract_financial_tables(filing_content)
            md_section = self._extract_mda_section(filing_content)
            
            filing = SECFiling(
                ticker=ticker,
                filing_type=filing_type,
                filing_date=filing_date,
                url=filing_url,
                accession_number=accession_number,
                content=filing_content,
                financial_tables=financial_tables,
                md_section=md_section
            )
            
            return filing
            
        except Exception as e:
            logger.error("filing_entry_parse_error", error=str(e))
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _fetch_filing_content(self, url: str) -> str:
        """Fetch the full filing document content."""
        self._rate_limit()
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error("filing_content_fetch_failed", url=url, error=str(e))
            raise
    
    def _extract_financial_tables(self, html_content: str) -> List[Dict]:
        """
        Extract financial tables from filing HTML.
        
        Returns:
            List of dictionaries containing table data
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            tables = soup.find_all('table')
            
            financial_tables = []
            for table in tables:
                # Look for tables with financial data indicators
                table_text = table.get_text().lower()
                
                financial_keywords = [
                    'revenue', 'income', 'earnings', 'assets', 'liabilities',
                    'equity', 'cash flow', 'balance sheet', 'statement'
                ]
                
                if any(keyword in table_text for keyword in financial_keywords):
                    table_data = self._parse_html_table(table)
                    if table_data:
                        financial_tables.append(table_data)
            
            logger.debug("financial_tables_extracted", count=len(financial_tables))
            return financial_tables
            
        except Exception as e:
            logger.warning("financial_table_extraction_failed", error=str(e))
            return []
    
    def _parse_html_table(self, table) -> Optional[Dict]:
        """Parse HTML table into structured dictionary."""
        try:
            rows = table.find_all('tr')
            if not rows:
                return None
            
            # Extract headers
            headers = []
            first_row = rows[0]
            header_cells = first_row.find_all(['th', 'td'])
            headers = [cell.get_text(strip=True) for cell in header_cells]
            
            # Extract data rows
            data_rows = []
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                if row_data:
                    data_rows.append(row_data)
            
            return {
                'headers': headers,
                'rows': data_rows
            }
            
        except Exception as e:
            logger.warning("table_parse_error", error=str(e))
            return None
    
    def _extract_mda_section(self, html_content: str) -> Optional[str]:
        """
        Extract Management Discussion and Analysis section.
        
        Returns:
            MD&A text content or None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Common MD&A section identifiers
            mda_patterns = [
                r'management[\'"]?s discussion and analysis',
                r'md&a',
                r'item 7',
                r'item 2.*management.*discussion'
            ]
            
            # Search for MD&A section
            for pattern in mda_patterns:
                # Look in headers and text
                mda_header = soup.find(
                    string=re.compile(pattern, re.IGNORECASE)
                )
                
                if mda_header:
                    # Extract text from this section until next major section
                    parent = mda_header.find_parent()
                    if parent:
                        section_text = self._extract_section_text(parent)
                        if section_text and len(section_text) > 100:
                            logger.debug("mda_section_found", length=len(section_text))
                            return section_text
            
            logger.warning("mda_section_not_found")
            return None
            
        except Exception as e:
            logger.warning("mda_extraction_failed", error=str(e))
            return None
    
    def _extract_section_text(self, element, max_length: int = 50000) -> str:
        """Extract text from a section element."""
        try:
            # Get all text within reasonable bounds
            text = element.get_text(separator='\n', strip=True)
            
            # Limit length
            if len(text) > max_length:
                text = text[:max_length]
            
            return text
            
        except Exception:
            return ""

# ============================================================================
# Earnings Call Processor
# ============================================================================

class EarningsCallProcessor:
    """
    Process earnings call transcripts with NLP.
    
    Features:
    - Extract earnings call transcripts
    - Sentiment analysis using transformers (if available)
    - Topic extraction and key phrase identification
    - Company guidance extraction
    
    Note: Requires transformers and spacy for full functionality.
    Gracefully degrades if dependencies are unavailable.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        
        # Initialize NLP models if available
        self.sentiment_analyzer = None
        self.nlp = None
        
        if TRANSFORMERS_AVAILABLE:
            try:
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert"  # Financial sentiment model
                )
                logger.info("sentiment_analyzer_initialized", model="finbert")
            except Exception as e:
                logger.warning("sentiment_analyzer_init_failed", error=str(e))
        else:
            logger.warning("transformers_not_available")
        
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spacy_model_loaded", model="en_core_web_sm")
            except Exception as e:
                logger.warning("spacy_model_load_failed", error=str(e))
        else:
            logger.warning("spacy_not_available")
    
    def process_transcript(
        self,
        ticker: str,
        transcript: str,
        call_date: date,
        quarter: str
    ) -> EarningsCall:
        """
        Process earnings call transcript with NLP analysis.
        
        Args:
            ticker: Stock ticker symbol
            transcript: Full transcript text
            call_date: Date of the earnings call
            quarter: Quarter identifier (e.g., "Q1 2024")
        
        Returns:
            EarningsCall object with sentiment and topics
        """
        # Check cache
        cache_key = CacheKeyPatterns.format_key(
            "earnings:processed",
            ticker=ticker,
            quarter=quarter
        )
        
        cached_call = self.cache.get(cache_key)
        if cached_call:
            logger.debug("processed_transcript_cache_hit", ticker=ticker, quarter=quarter)
            return cached_call
        
        # Extract sentiment
        sentiment_score = self._analyze_sentiment(transcript)
        
        # Extract key topics
        key_topics = self._extract_key_topics(transcript)
        
        # Extract guidance
        company_guidance = self._extract_guidance(transcript)
        
        earnings_call = EarningsCall(
            ticker=ticker,
            call_date=call_date,
            quarter=quarter,
            transcript=transcript,
            sentiment_score=sentiment_score,
            key_topics=key_topics,
            company_guidance=company_guidance
        )
        
        # Cache for 30 days
        self.cache.set(cache_key, earnings_call, ttl=2592000)
        
        logger.info(
            "transcript_processed",
            ticker=ticker,
            quarter=quarter,
            sentiment=sentiment_score,
            topics=len(key_topics) if key_topics else 0
        )
        
        return earnings_call
    
    def _analyze_sentiment(self, text: str) -> Optional[float]:
        """
        Analyze sentiment of transcript text.
        
        Returns:
            Sentiment score from -1 (negative) to 1 (positive), or None
        """
        if not self.sentiment_analyzer:
            logger.debug("sentiment_analyzer_unavailable")
            return None
        
        try:
            # Truncate text if too long (model limit is typically 512 tokens)
            max_length = 2000  # characters
            text_sample = text[:max_length]
            
            result = self.sentiment_analyzer(text_sample)[0]
            
            # Convert to -1 to 1 scale
            label = result['label'].lower()
            score = result['score']
            
            if 'positive' in label:
                sentiment = score
            elif 'negative' in label:
                sentiment = -score
            else:
                sentiment = 0.0
            
            logger.debug("sentiment_analyzed", sentiment=sentiment)
            return sentiment
            
        except Exception as e:
            logger.warning("sentiment_analysis_failed", error=str(e))
            return None
    
    def _extract_key_topics(self, text: str, max_topics: int = 10) -> List[str]:
        """
        Extract key topics from transcript using NLP.
        
        Returns:
            List of key topic strings
        """
        if not self.nlp:
            logger.debug("spacy_unavailable_for_topics")
            return self._extract_topics_simple(text, max_topics)
        
        try:
            # Process text with spaCy
            doc = self.nlp(text[:100000])  # Limit length for performance
            
            # Extract noun chunks as topics
            topics = []
            for chunk in doc.noun_chunks:
                # Filter for relevant business topics
                if len(chunk.text.split()) >= 2 and len(chunk.text) < 50:
                    topics.append(chunk.text.lower().strip())
            
            # Count frequency and get top topics
            from collections import Counter
            topic_counts = Counter(topics)
            top_topics = [topic for topic, _ in topic_counts.most_common(max_topics)]
            
            logger.debug("topics_extracted", count=len(top_topics))
            return top_topics
            
        except Exception as e:
            logger.warning("topic_extraction_failed", error=str(e))
            return self._extract_topics_simple(text, max_topics)
    
    def _extract_topics_simple(self, text: str, max_topics: int) -> List[str]:
        """Fallback topic extraction using keyword matching."""
        business_keywords = [
            'revenue', 'growth', 'margin', 'earnings', 'profit',
            'market share', 'competition', 'innovation', 'product',
            'guidance', 'outlook', 'expansion', 'acquisition',
            'debt', 'cash flow', 'investment', 'strategy'
        ]
        
        topics = []
        text_lower = text.lower()
        
        for keyword in business_keywords:
            if keyword in text_lower:
                topics.append(keyword)
        
        return topics[:max_topics]
    
    def _extract_guidance(self, text: str) -> Optional[str]:
        """
        Extract company guidance section from transcript.
        
        Returns:
            Guidance text or None
        """
        try:
            # Look for guidance keywords
            guidance_patterns = [
                r'guidance.*?(?=\n\n|\. [A-Z])',
                r'outlook.*?(?=\n\n|\. [A-Z])',
                r'expect.*?(?=\n\n|\. [A-Z])',
                r'forecast.*?(?=\n\n|\. [A-Z])'
            ]
            
            for pattern in guidance_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
                if matches:
                    guidance = matches[0]
                    if len(guidance) > 50:
                        logger.debug("guidance_extracted", length=len(guidance))
                        return guidance[:1000]  # Limit length
            
            return None
            
        except Exception as e:
            logger.warning("guidance_extraction_failed", error=str(e))
            return None

# ============================================================================
# Insider Trading Tracker
# ============================================================================

class InsiderTradingTracker:
    """
    Track insider trading transactions from SEC Form 4 filings.
    
    Features:
    - Parse Form 4 filings for insider transactions
    - Track transaction dates, amounts, and insider roles
    - Calculate insider buying/selling ratios over rolling 90-day periods
    - Rate limiting for SEC EDGAR
    
    Requirements:
    - Requirement 15.5: Track insider trading transactions
    - Requirement 15.6: Calculate 90-day buying/selling ratios
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.base_url = "https://www.sec.gov"
        self.api_base = f"{self.base_url}/cgi-bin/browse-edgar"
        
        # Rate limiting: 10 requests/second
        self._last_request_time = 0.0
        self._min_request_interval = 0.1
        
        # User agent (required by SEC)
        self.headers = {
            'User-Agent': self.settings.sec_user_agent or 'StockIQ/1.0 (institutional@example.com)',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
    
    def _rate_limit(self):
        """Enforce rate limiting (10 requests/second)."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_insider_transactions(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        count: int = 100
    ) -> List[InsiderTransaction]:
        """
        Get insider trading transactions for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            count: Maximum number of transactions to retrieve
        
        Returns:
            List of InsiderTransaction objects
        """
        # Check cache
        cache_key = CacheKeyPatterns.format_key(
            "insider:transactions",
            ticker=ticker,
            start=start_date.isoformat() if start_date else "all",
            end=end_date.isoformat() if end_date else "all"
        )
        
        cached_transactions = self.cache.get(cache_key)
        if cached_transactions:
            logger.debug("insider_transactions_cache_hit", ticker=ticker)
            return cached_transactions
        
        try:
            self._rate_limit()
            
            # Search for Form 4 filings
            params = {
                'action': 'getcompany',
                'CIK': ticker,
                'type': '4',
                'dateb': end_date.isoformat() if end_date else '',
                'owner': 'include',
                'count': count,
                'output': 'atom'
            }
            
            response = requests.get(
                self.api_base,
                params=params,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            
            # Parse RSS/Atom feed
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')
            
            transactions = []
            for entry in entries:
                try:
                    transaction_list = self._parse_form4_entry(entry, ticker)
                    transactions.extend(transaction_list)
                except Exception as e:
                    logger.warning("form4_parse_error", ticker=ticker, error=str(e))
                    continue
            
            # Filter by date range if specified
            if start_date or end_date:
                transactions = self._filter_by_date_range(
                    transactions,
                    start_date,
                    end_date
                )
            
            # Cache for 6 hours
            self.cache.set(cache_key, transactions, ttl=21600)
            
            logger.info(
                "insider_transactions_retrieved",
                ticker=ticker,
                count=len(transactions)
            )
            
            return transactions
            
        except requests.exceptions.RequestException as e:
            logger.error("insider_transaction_fetch_failed", ticker=ticker, error=str(e))
            raise
    
    def _parse_form4_entry(
        self,
        entry,
        ticker: str
    ) -> List[InsiderTransaction]:
        """
        Parse Form 4 filing entry to extract transactions.
        
        Returns:
            List of InsiderTransaction objects (multiple transactions per filing)
        """
        try:
            # Get filing URL
            link = entry.find('link', {'rel': 'alternate'})
            if not link or not link.get('href'):
                return []
            
            filing_url = link['href']
            
            # Fetch Form 4 content
            self._rate_limit()
            response = requests.get(filing_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # Parse Form 4 XML/HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract insider information
            insider_name = self._extract_insider_name(soup)
            insider_role = self._extract_insider_role(soup)
            
            # Extract transactions
            transactions = []
            transaction_elements = soup.find_all(['nonDerivativeTransaction', 'derivativeTransaction'])
            
            for trans_elem in transaction_elements:
                transaction = self._parse_transaction_element(
                    trans_elem,
                    ticker,
                    insider_name,
                    insider_role
                )
                if transaction:
                    transactions.append(transaction)
            
            return transactions
            
        except Exception as e:
            logger.warning("form4_entry_parse_error", error=str(e))
            return []
    
    def _extract_insider_name(self, soup) -> str:
        """Extract insider name from Form 4."""
        try:
            # Look for reporting owner name
            name_elem = soup.find('rptOwnerName')
            if name_elem:
                return name_elem.get_text(strip=True)
            
            # Fallback to text search
            name_match = re.search(r'<rptOwnerName>(.*?)</rptOwnerName>', str(soup))
            if name_match:
                return name_match.group(1)
            
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def _extract_insider_role(self, soup) -> str:
        """Extract insider role/title from Form 4."""
        try:
            # Look for officer title
            title_elem = soup.find('officerTitle')
            if title_elem:
                return title_elem.get_text(strip=True)
            
            # Check for director
            is_director = soup.find('isDirector')
            if is_director and is_director.get_text(strip=True) == '1':
                return "Director"
            
            # Check for officer
            is_officer = soup.find('isOfficer')
            if is_officer and is_officer.get_text(strip=True) == '1':
                return "Officer"
            
            return "Insider"
        except Exception:
            return "Insider"
    
    def _parse_transaction_element(
        self,
        trans_elem,
        ticker: str,
        insider_name: str,
        insider_role: str
    ) -> Optional[InsiderTransaction]:
        """Parse a single transaction element."""
        try:
            # Extract transaction date
            trans_date_elem = trans_elem.find('transactionDate')
            if not trans_date_elem:
                return None
            
            trans_date_text = trans_date_elem.find('value')
            if trans_date_text:
                trans_date = datetime.strptime(
                    trans_date_text.get_text(strip=True),
                    '%Y-%m-%d'
                ).date()
            else:
                return None
            
            # Extract transaction code (P=Purchase, S=Sale, etc.)
            trans_code_elem = trans_elem.find('transactionCode')
            trans_code = trans_code_elem.get_text(strip=True) if trans_code_elem else ""
            
            # Determine transaction type
            if trans_code in ['P', 'A', 'M']:
                trans_type = 'buy'
            elif trans_code in ['S', 'D']:
                trans_type = 'sell'
            else:
                trans_type = 'other'
            
            # Extract shares
            shares_elem = trans_elem.find('transactionShares')
            shares_value = shares_elem.find('value') if shares_elem else None
            shares = int(float(shares_value.get_text(strip=True))) if shares_value else 0
            
            # Extract price per share
            price_elem = trans_elem.find('transactionPricePerShare')
            price_value = price_elem.find('value') if price_elem else None
            price_per_share = Decimal(price_value.get_text(strip=True)) if price_value else None
            
            # Calculate total value
            total_value = None
            if price_per_share and shares:
                total_value = price_per_share * Decimal(shares)
            
            transaction = InsiderTransaction(
                ticker=ticker,
                transaction_date=trans_date,
                insider_name=insider_name,
                insider_role=insider_role,
                transaction_type=trans_type,
                shares=shares,
                price_per_share=price_per_share,
                total_value=total_value
            )
            
            return transaction
            
        except Exception as e:
            logger.warning("transaction_element_parse_error", error=str(e))
            return None
    
    def _filter_by_date_range(
        self,
        transactions: List[InsiderTransaction],
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> List[InsiderTransaction]:
        """Filter transactions by date range."""
        filtered = transactions
        
        if start_date:
            filtered = [t for t in filtered if t.transaction_date >= start_date]
        
        if end_date:
            filtered = [t for t in filtered if t.transaction_date <= end_date]
        
        return filtered
    
    def calculate_90day_metrics(
        self,
        ticker: str,
        end_date: Optional[date] = None
    ) -> InsiderMetrics:
        """
        Calculate insider trading metrics over rolling 90-day period.
        
        Requirement 15.6: Calculate insider buying and selling ratios
        over rolling 90-day periods.
        
        Args:
            ticker: Stock ticker symbol
            end_date: End date for 90-day window (default: today)
        
        Returns:
            InsiderMetrics object with buy/sell ratios
        """
        if not end_date:
            end_date = date.today()
        
        start_date = end_date - timedelta(days=90)
        
        # Check cache
        cache_key = CacheKeyPatterns.format_key(
            "insider:metrics_90d",
            ticker=ticker,
            end_date=end_date.isoformat()
        )
        
        cached_metrics = self.cache.get(cache_key)
        if cached_metrics:
            logger.debug("insider_metrics_cache_hit", ticker=ticker)
            return cached_metrics
        
        # Get transactions for 90-day period
        transactions = self.get_insider_transactions(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate metrics
        buy_transactions = [t for t in transactions if t.transaction_type == 'buy']
        sell_transactions = [t for t in transactions if t.transaction_type == 'sell']
        
        total_buy_shares = sum(t.shares for t in buy_transactions)
        total_sell_shares = sum(t.shares for t in sell_transactions)
        
        total_buy_value = sum(
            t.total_value for t in buy_transactions
            if t.total_value is not None
        ) or Decimal(0)
        
        total_sell_value = sum(
            t.total_value for t in sell_transactions
            if t.total_value is not None
        ) or Decimal(0)
        
        # Calculate buy/sell ratio
        total_shares = total_buy_shares + total_sell_shares
        buy_sell_ratio = (
            total_buy_shares / total_shares
            if total_shares > 0
            else 0.0
        )
        
        metrics = InsiderMetrics(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            total_buy_transactions=len(buy_transactions),
            total_sell_transactions=len(sell_transactions),
            total_buy_shares=total_buy_shares,
            total_sell_shares=total_sell_shares,
            total_buy_value=total_buy_value,
            total_sell_value=total_sell_value,
            buy_sell_ratio=buy_sell_ratio
        )
        
        # Cache for 6 hours
        self.cache.set(cache_key, metrics, ttl=21600)
        
        logger.info(
            "insider_metrics_calculated",
            ticker=ticker,
            buy_sell_ratio=buy_sell_ratio,
            buy_transactions=len(buy_transactions),
            sell_transactions=len(sell_transactions)
        )
        
        return metrics
