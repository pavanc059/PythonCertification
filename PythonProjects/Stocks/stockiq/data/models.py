"""
Data models and DTOs for data collection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


class NewsCategory(str, Enum):
    """News article categories."""
    EARNINGS = "earnings"
    MA = "M&A"
    REGULATORY = "regulatory"
    ECONOMIC = "economic"
    SECTOR_SPECIFIC = "sector-specific"
    GENERAL = "general"


@dataclass
class Price:
    """Price data point."""
    ticker: str
    timestamp: datetime
    price: Decimal
    volume: int
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate price data."""
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")


@dataclass
class OHLCV:
    """OHLCV (Open, High, Low, Close, Volume) data."""
    ticker: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate OHLCV data (Property 26, 28)."""
        # Property 26: OHLC Price Consistency
        # H ≥ max(O, C) and L ≤ min(O, C)
        max_oc = max(self.open, self.close)
        min_oc = min(self.open, self.close)
        
        if self.high < max_oc:
            raise ValueError(
                f"High ({self.high}) must be >= max(Open={self.open}, Close={self.close})"
            )
        
        if self.low > min_oc:
            raise ValueError(
                f"Low ({self.low}) must be <= min(Open={self.open}, Close={self.close})"
            )
        
        # Property 28: Volume Non-Negativity
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
    
    def percentage_change(self) -> Decimal:
        """Calculate percentage change (Property 3)."""
        if self.open == 0:
            raise ValueError("Open price cannot be zero")
        return ((self.close - self.open) / self.open) * 100
    
    def absolute_change(self) -> Decimal:
        """Calculate absolute price change."""
        return self.close - self.open


@dataclass
class Stock:
    """Stock information."""
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None
    avg_volume: Optional[int] = None
    current_price: Optional[Decimal] = None
    
    def is_penny_stock(self) -> bool:
        """Check if stock is a penny stock (Property 42)."""
        if self.current_price is None:
            return False
        return self.current_price <= Decimal("5.00")


@dataclass
class NewsArticle:
    """News article data."""
    id: str
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    tickers: List[str]
    category: Optional[NewsCategory] = None
    author: Optional[str] = None
    
    def is_breaking(self) -> bool:
        """Check if news is breaking (Property 10)."""
        time_diff = datetime.utcnow() - self.published_at
        return time_diff.total_seconds() <= 1800  # 30 minutes


@dataclass
class SentimentScore:
    """
    Sentiment score with confidence metrics.

    Property 9: All scores SHALL be in range [-1.0, 1.0]
    """
    overall: float  # -1 to +1, combined score from all models
    vader_score: float = 0.0
    finbert_score: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for storage."""
        return {
            'overall': self.overall,
            'vader_score': self.vader_score,
            'finbert_score': self.finbert_score,
            'confidence': self.confidence,
        }


@dataclass
class Entities:
    """Extracted entities from news text."""
    companies: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    tickers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[str]]:
        return {
            'companies': self.companies,
            'people': self.people,
            'locations': self.locations,
            'tickers': self.tickers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, List[str]]) -> 'Entities':
        return cls(
            companies=data.get('companies', []),
            people=data.get('people', []),
            locations=data.get('locations', []),
            tickers=data.get('tickers', []),
        )


@dataclass
class EnrichedNewsArticle:
    """
    News article enriched with NLP analysis results.

    Extends NewsArticle with sentiment, entities, summary,
    and relevance score derived from NLP processing.
    """
    id: str
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    tickers: List[str]
    category: Optional[NewsCategory] = None
    author: Optional[str] = None
    sentiment: Optional[SentimentScore] = None
    entities: Optional[Entities] = None
    summary: str = ""
    relevance_score: float = 0.0

    def is_breaking(self) -> bool:
        """Check if news is breaking (Property 10)."""
        time_diff = datetime.utcnow() - self.published_at
        return time_diff.total_seconds() <= 1800  # 30 minutes

    @classmethod
    def from_news_article(
        cls,
        article: 'NewsArticle',
        sentiment: Optional['SentimentScore'] = None,
        entities: Optional['Entities'] = None,
        summary: str = "",
        relevance_score: float = 0.0,
    ) -> 'EnrichedNewsArticle':
        """Create from a plain NewsArticle by adding enrichment data."""
        return cls(
            id=article.id,
            title=article.title,
            content=article.content,
            source=article.source,
            published_at=article.published_at,
            url=article.url,
            tickers=article.tickers,
            category=article.category,
            author=article.author,
            sentiment=sentiment,
            entities=entities,
            summary=summary,
            relevance_score=relevance_score,
        )


@dataclass
class TopMover:
    """Top mover (gainer or loser) data."""
    ticker: str
    name: str
    price_change_pct: float
    price_change_abs: Decimal
    current_price: Decimal
    volume: int
    avg_volume: int
    market_cap: int
    sector: str
    is_gainer: bool
    
    def volume_ratio(self) -> float:
        """Calculate volume ratio (Property 7)."""
        if self.avg_volume == 0:
            return 0.0
        return self.volume / self.avg_volume
    
    def has_unusual_volume(self) -> bool:
        """Check for unusual volume (Property 7)."""
        return self.volume_ratio() > 3.0


@dataclass
class ValidationResult:
    """Data validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __bool__(self):
        return self.is_valid
    
    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(warning)
