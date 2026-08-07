"""
News categorization and ticker extraction module.

This module implements the news categorization pipeline with the following features:
- Keyword-based news categorization (Property 8)
- Ticker extraction using regex and NER
- Relevance scoring for personalized news ranking
- Redis caching for categorization results

Requirements implemented:
- Requirement 2.2: Categorize news by topic (earnings, M&A, regulatory, economic, sector-specific)
- Requirement 2.3: Extract mentioned stock tickers from news articles using NLP
- Requirement 2.6: Rank news articles by relevance score

Property validated:
- Property 8: News category assignment
- Property 11: News relevance ranking
"""

import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import structlog
from sqlalchemy.orm import Session

from ...data.models import NewsArticle, NewsCategory
from ...infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
from ...infrastructure.database import get_db
from ...infrastructure.models import Stock as DBStock

logger = structlog.get_logger(__name__)


# Category keywords for classification
CATEGORY_KEYWORDS = {
    NewsCategory.EARNINGS: {
        'earnings', 'revenue', 'profit', 'loss', 'quarterly', 'results',
        'eps', 'ebitda', 'guidance', 'forecast', 'miss', 'beat',
        'q1', 'q2', 'q3', 'q4', 'fiscal', 'report', 'announced',
        'financial results', 'quarterly report', 'earnings call'
    },
    NewsCategory.MA: {
        'merger', 'acquisition', 'acquire', 'takeover', 'buyout',
        'merge', 'deal', 'bid', 'offer', 'purchase', 'acquired',
        'acquiring', 'consolidation', 'joint venture', 'strategic partnership',
        'm&a', 'tender offer', 'hostile takeover'
    },
    NewsCategory.REGULATORY: {
        'fda', 'sec', 'investigation', 'lawsuit', 'regulatory', 'compliance',
        'approval', 'clearance', 'patent', 'recall', 'fine', 'penalty',
        'litigation', 'settlement', 'ruling', 'court', 'judge', 'trial',
        'ftc', 'doj', 'antitrust', 'sanctions', 'violation'
    },
    NewsCategory.ECONOMIC: {
        'gdp', 'inflation', 'fed', 'federal reserve', 'interest rate',
        'unemployment', 'jobs report', 'cpi', 'ppi', 'retail sales',
        'housing', 'economic', 'recession', 'growth', 'stimulus',
        'monetary policy', 'fiscal policy', 'treasury', 'bond yield'
    },
    NewsCategory.SECTOR_SPECIFIC: {
        'sector', 'industry', 'oil', 'energy', 'tech', 'technology',
        'healthcare', 'pharma', 'biotech', 'finance', 'banking',
        'retail', 'consumer', 'industrial', 'materials', 'utilities',
        'real estate', 'semiconductor', 'automotive', 'telecom'
    }
}

# Ticker regex patterns
TICKER_PATTERNS = [
    # Standard format: $AAPL or AAPL
    r'\$([A-Z]{1,5})\b',
    # Parenthetical format: (NASDAQ:AAPL) or (NYSE:TSLA)
    r'\((?:NASDAQ|NYSE|AMEX|OTC):\s*([A-Z]{1,5})\)',
    # Standalone uppercase 1-5 letters followed by specific contexts
    r'\b([A-Z]{2,5})\s+(?:stock|shares|ticker|symbol)',
]


@dataclass
class CategorizationResult:
    """Result of article categorization."""
    category: NewsCategory
    confidence: float  # 0.0-1.0
    matched_keywords: List[str]
    
    
@dataclass
class RelevanceScore:
    """Relevance score for an article."""
    score: float  # 0.0-1.0
    factors: Dict[str, float]  # Breakdown of score components


class NewsCategorizer:
    """
    News categorization engine with keyword-based classification.
    
    Features:
    - Multi-category keyword matching (Property 8)
    - Confidence scoring based on keyword density
    - Ticker extraction using regex and database validation
    - Relevance scoring for personalized news ranking
    - Redis caching for categorization results
    """
    
    def __init__(self):
        self.cache = get_cache()
        self.category_keywords = CATEGORY_KEYWORDS
        self.ticker_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in TICKER_PATTERNS]
        
        # Ticker validation cache
        self._valid_tickers: Optional[Set[str]] = None
        self._ticker_cache_key = "news:valid_tickers"
    
    def _get_valid_tickers(self) -> Set[str]:
        """
        Get set of valid ticker symbols from database.
        
        Cached for 1 hour to reduce database queries.
        
        Returns:
            Set of valid ticker symbols
        """
        # Check cache first
        if self._valid_tickers is None:
            cached_tickers = self.cache.get(self._ticker_cache_key)
            
            if cached_tickers:
                self._valid_tickers = cached_tickers
                logger.debug("valid_tickers_cache_hit", count=len(cached_tickers))
            else:
                # Query database
                db: Session = next(get_db())
                try:
                    stocks = db.query(DBStock.ticker).all()
                    self._valid_tickers = {stock.ticker.upper() for stock in stocks}
                    
                    # Cache for 1 hour
                    self.cache.set(self._ticker_cache_key, self._valid_tickers, ttl=3600)
                    
                    logger.info("valid_tickers_loaded", count=len(self._valid_tickers))
                finally:
                    db.close()
        
        return self._valid_tickers
    
    def _calculate_keyword_matches(self, text: str, keywords: Set[str]) -> tuple[int, List[str]]:
        """
        Calculate keyword matches in text.
        
        Args:
            text: Text to search
            keywords: Set of keywords to match
        
        Returns:
            Tuple of (match_count, matched_keywords)
        """
        text_lower = text.lower()
        matched = []
        
        for keyword in keywords:
            # Use word boundary matching for single words
            if ' ' not in keyword:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text_lower):
                    matched.append(keyword)
            else:
                # Exact phrase match for multi-word keywords
                if keyword in text_lower:
                    matched.append(keyword)
        
        return len(matched), matched
    
    def categorize_article(self, article: NewsArticle) -> NewsCategory:
        """
        Categorize a news article based on keyword analysis (Property 8).
        
        Property 8: News Category Assignment
        Each article must be assigned to exactly one category:
        - earnings, M&A, regulatory, economic, sector-specific, general
        
        Algorithm:
        1. Count keyword matches for each category in title + content
        2. Calculate confidence score based on keyword density
        3. Select category with highest confidence
        4. Default to GENERAL if no clear category
        
        Args:
            article: NewsArticle to categorize
        
        Returns:
            NewsCategory enum value
        
        **Validates: Property 8**
        """
        # Check cache first
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.NEWS_ARTICLE,
            article_id=article.id
        ) + ":category"
        
        cached_category = self.cache.get(cache_key, deserialize=False)
        if cached_category:
            logger.debug("category_cache_hit", article_id=article.id)
            return NewsCategory(cached_category.decode('utf-8'))
        
        # Combine title and content for analysis (title weighted more heavily)
        search_text = f"{article.title} {article.title} {article.content}"
        
        # Calculate keyword matches for each category
        category_scores = {}
        category_matches = {}
        
        for category, keywords in self.category_keywords.items():
            match_count, matched_keywords = self._calculate_keyword_matches(
                search_text, 
                keywords
            )
            
            # Calculate confidence score (keyword density)
            # Score = matches / total_words * 100
            word_count = len(search_text.split())
            confidence = (match_count / word_count * 100) if word_count > 0 else 0.0
            
            category_scores[category] = confidence
            category_matches[category] = matched_keywords
        
        # Select category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            selected_category = best_category[0]
            confidence = best_category[1]
            
            # If confidence is very low (<1%), default to GENERAL
            if confidence < 1.0:
                selected_category = NewsCategory.GENERAL
                confidence = 0.0
        else:
            selected_category = NewsCategory.GENERAL
            confidence = 0.0
        
        logger.info(
            "article_categorized",
            article_id=article.id,
            category=selected_category.value,
            confidence=round(confidence, 2),
            matched_keywords=category_matches.get(selected_category, [])[:5]
        )
        
        # Cache result
        self.cache.set(
            cache_key,
            selected_category.value,
            ttl=CacheTTL.NEWS_ARTICLE,
            serialize=False
        )
        
        return selected_category
    
    def extract_tickers(self, text: str) -> List[str]:
        """
        Extract stock ticker symbols from text using regex and validation.
        
        Uses multiple regex patterns to find tickers in various formats:
        - $TICKER format (e.g., $AAPL)
        - Exchange:TICKER format (e.g., NASDAQ:TSLA)
        - Contextual standalone tickers (e.g., "AAPL stock")
        
        Validates extracted tickers against database of known stocks.
        
        Args:
            text: Text to extract tickers from
        
        Returns:
            List of valid ticker symbols (uppercase, deduplicated)
        
        Example:
            >>> extract_tickers("Apple ($AAPL) and Tesla (NASDAQ:TSLA) stocks rose today")
            ['AAPL', 'TSLA']
        """
        extracted_tickers = set()
        
        # Apply each regex pattern
        for pattern in self.ticker_patterns:
            matches = pattern.findall(text)
            extracted_tickers.update(match.upper() for match in matches)
        
        # Validate against known tickers
        valid_tickers = self._get_valid_tickers()
        validated_tickers = [
            ticker for ticker in extracted_tickers 
            if ticker in valid_tickers
        ]
        
        # Sort for consistent ordering
        validated_tickers.sort()
        
        logger.debug(
            "tickers_extracted",
            extracted=len(extracted_tickers),
            validated=len(validated_tickers),
            tickers=validated_tickers
        )
        
        return validated_tickers
    
    def calculate_relevance_score(
        self, 
        article: NewsArticle, 
        user_interests: List[str]
    ) -> float:
        """
        Calculate relevance score for an article based on user interests.
        
        Relevance factors:
        1. Ticker overlap (40%): Mentioned tickers match user watchlist
        2. Category match (30%): Article category matches user interests
        3. Source credibility (20%): Trusted news sources ranked higher
        4. Recency (10%): More recent articles ranked higher
        
        Args:
            article: NewsArticle to score
            user_interests: List of user interests (tickers, categories, sources)
        
        Returns:
            Relevance score from 0.0 to 1.0
        """
        # Check cache
        cache_key = f"news:relevance:{article.id}:{hash(tuple(sorted(user_interests)))}"
        cached_score = self.cache.get(cache_key)
        if cached_score is not None:
            logger.debug("relevance_cache_hit", article_id=article.id)
            return cached_score
        
        # Parse user interests
        interest_tickers = set()
        interest_categories = set()
        interest_sources = set()
        
        for interest in user_interests:
            interest_upper = interest.upper()
            
            # Check if it's a ticker (1-5 uppercase letters)
            if interest_upper.isalpha() and 1 <= len(interest_upper) <= 5:
                interest_tickers.add(interest_upper)
            # Check if it's a category
            elif interest.lower() in [cat.value for cat in NewsCategory]:
                interest_categories.add(interest.lower())
            # Otherwise treat as source
            else:
                interest_sources.add(interest.lower())
        
        # Calculate component scores
        scores = {}
        
        # 1. Ticker overlap (40%)
        article_tickers = set(ticker.upper() for ticker in article.tickers)
        if interest_tickers and article_tickers:
            ticker_overlap = len(interest_tickers & article_tickers) / len(interest_tickers)
        else:
            ticker_overlap = 0.0
        scores['ticker_overlap'] = ticker_overlap * 0.4
        
        # 2. Category match (30%)
        if article.category and interest_categories:
            category_match = 1.0 if article.category.value in interest_categories else 0.0
        else:
            category_match = 0.0
        scores['category_match'] = category_match * 0.3
        
        # 3. Source credibility (20%)
        # High credibility sources
        high_credibility = {'reuters', 'bloomberg', 'wsj', 'ft', 'cnbc', 'marketwatch'}
        article_source_lower = article.source.lower()
        
        if interest_sources:
            # User has source preferences
            source_match = 1.0 if article_source_lower in interest_sources else 0.0
        else:
            # No user preference, use general credibility
            source_match = 1.0 if any(cred in article_source_lower for cred in high_credibility) else 0.5
        scores['source_credibility'] = source_match * 0.2
        
        # 4. Recency (10%)
        # More recent articles get higher scores
        from datetime import datetime, timedelta
        age = datetime.utcnow() - article.published_at
        age_hours = age.total_seconds() / 3600
        
        # Decay function: 1.0 at 0 hours, 0.5 at 12 hours, 0.0 at 24 hours
        if age_hours <= 12:
            recency_score = 1.0 - (age_hours / 24)
        elif age_hours <= 24:
            recency_score = 0.5 - ((age_hours - 12) / 24)
        else:
            recency_score = 0.0
        scores['recency'] = max(0.0, recency_score) * 0.1
        
        # Total relevance score
        relevance = sum(scores.values())
        
        logger.debug(
            "relevance_calculated",
            article_id=article.id,
            relevance=round(relevance, 3),
            components=scores
        )
        
        # Cache for 1 hour
        self.cache.set(cache_key, relevance, ttl=3600)
        
        return relevance
    
    def rank_by_relevance(
        self,
        articles: List[NewsArticle],
        user_interests: Optional[List[str]] = None
    ) -> List[NewsArticle]:
        """
        Rank news articles by relevance score (Property 11).
        
        Property 11: News Relevance Ranking
        Articles must be ranked in descending order of relevance score.
        
        If no user interests provided, ranks by:
        1. Breaking news first
        2. Source credibility
        3. Recency
        
        Args:
            articles: List of NewsArticle objects to rank
            user_interests: Optional list of user interests for personalized ranking
        
        Returns:
            List of NewsArticle objects sorted by relevance (highest first)
        
        **Validates: Property 11**
        """
        if not articles:
            return []
        
        # Calculate relevance scores for all articles
        article_scores = []
        
        for article in articles:
            if user_interests:
                # Personalized ranking
                score = self.calculate_relevance_score(article, user_interests)
            else:
                # Default ranking based on breaking news, credibility, recency
                score = self._default_relevance_score(article)
            
            article_scores.append((article, score))
        
        # Sort by score (descending)
        article_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Extract articles in ranked order
        ranked_articles = [article for article, score in article_scores]
        
        logger.info(
            "articles_ranked",
            total=len(articles),
            has_user_interests=bool(user_interests),
            top_score=round(article_scores[0][1], 3) if article_scores else 0.0
        )
        
        return ranked_articles
    
    def _default_relevance_score(self, article: NewsArticle) -> float:
        """
        Calculate default relevance score (no user interests).
        
        Factors:
        1. Breaking news (50%)
        2. Source credibility (30%)
        3. Recency (20%)
        
        Args:
            article: NewsArticle to score
        
        Returns:
            Relevance score from 0.0 to 1.0
        """
        scores = {}
        
        # 1. Breaking news (50%)
        is_breaking = article.is_breaking()
        scores['breaking'] = 1.0 if is_breaking else 0.0
        scores['breaking'] *= 0.5
        
        # 2. Source credibility (30%)
        high_credibility = {'reuters', 'bloomberg', 'wsj', 'ft', 'cnbc', 'marketwatch'}
        article_source_lower = article.source.lower()
        source_match = 1.0 if any(cred in article_source_lower for cred in high_credibility) else 0.5
        scores['source'] = source_match * 0.3
        
        # 3. Recency (20%)
        from datetime import datetime
        age = datetime.utcnow() - article.published_at
        age_hours = age.total_seconds() / 3600
        
        # Decay function
        if age_hours <= 12:
            recency_score = 1.0 - (age_hours / 24)
        elif age_hours <= 24:
            recency_score = 0.5 - ((age_hours - 12) / 24)
        else:
            recency_score = 0.0
        scores['recency'] = max(0.0, recency_score) * 0.2
        
        return sum(scores.values())
    
    def categorize_batch(self, articles: List[NewsArticle]) -> Dict[str, NewsCategory]:
        """
        Categorize multiple articles efficiently.
        
        Args:
            articles: List of NewsArticle objects
        
        Returns:
            Dictionary mapping article IDs to categories
        """
        categorized = {}
        
        for article in articles:
            category = self.categorize_article(article)
            categorized[article.id] = category
        
        logger.info("batch_categorization_complete", count=len(articles))
        
        return categorized
    
    def clear_cache(self, article_id: Optional[str] = None):
        """
        Clear categorization cache.
        
        Args:
            article_id: Optional specific article ID to clear, or None for all
        """
        if article_id:
            # Clear specific article
            cache_key = CacheKeyPatterns.format_key(
                CacheKeyPatterns.NEWS_ARTICLE,
                article_id=article_id
            )
            self.cache.delete(cache_key + ":category")
            logger.info("cache_cleared", article_id=article_id)
        else:
            # Clear all categorization caches
            self.cache.delete_pattern("news:article:*:category")
            self.cache.delete_pattern("news:relevance:*")
            logger.info("all_categorization_cache_cleared")


# Convenience function for ticker extraction
def extract_tickers(text: str) -> List[str]:
    """
    Extract stock ticker symbols from text.
    
    Convenience function that creates a categorizer instance and extracts tickers.
    
    Args:
        text: Text to extract tickers from
    
    Returns:
        List of valid ticker symbols
    
    Example:
        >>> from stockiq.news.nlp import extract_tickers
        >>> extract_tickers("Apple ($AAPL) rose 5% today")
        ['AAPL']
    """
    categorizer = NewsCategorizer()
    return categorizer.extract_tickers(text)
