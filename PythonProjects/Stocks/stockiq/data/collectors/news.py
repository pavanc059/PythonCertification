"""
News data collector with multi-source integration.

This module implements the NewsCollector class with the following features:
- Multi-source news aggregation (NewsAPI, Finnhub, Alpha Vantage)
- Rate limiting per source (stays at 80% of limits)
- Duplicate detection using content hashing
- Redis caching (1-hour TTL)
- Database persistence with timestamps
- Breaking news detection (Property 10)

Requirements implemented:
- Requirement 2.1: Collect news from at least 10 financial news sources
- Requirement 2.5: Identify breaking news (published within last 30 minutes)
- Requirement 2.9: Detect duplicate/similar news articles

Property validated:
- Property 10: Breaking news detection (published within last 30 minutes)
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Set, Dict
from decimal import Decimal
import requests
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy.orm import Session

from ..models import NewsArticle, NewsCategory
from ...infrastructure.config import get_settings
from ...infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
from ...infrastructure.database import get_db
from ...infrastructure.models import (
    NewsArticle as DBNewsArticle,
    Stock as DBStock
)

logger = structlog.get_logger(__name__)


class NewsCollector:
    """
    Collects financial news from multiple sources with rate limiting and caching.
    
    Supports:
    - NewsAPI.org (general financial news)
    - Finnhub.io (real-time market news)
    - Alpha Vantage (news sentiment)
    
    Features:
    - Rate limiting per source (80% of API limits)
    - Duplicate detection using SHA-256 content hashing
    - Redis caching (1-hour TTL)
    - PostgreSQL persistence
    - Breaking news detection (Property 10)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self._rate_limit_keys = {
            'newsapi': 'ratelimit:newsapi',
            'finnhub': 'ratelimit:finnhub',
            'alphavantage': 'ratelimit:alphavantage'
        }
        
        # Content hash set key for duplicate detection
        self._hash_set_key = 'news:content_hashes'
        
        # API endpoints
        self._newsapi_base = "https://newsapi.org/v2"
        self._finnhub_base = "https://finnhub.io/api/v1"
        self._alphavantage_base = "https://www.alphavantage.co/query"
    
    def _check_rate_limit(self, source: str) -> bool:
        """
        Check if we're within rate limits for a source.
        
        Stays at 80% of rate limit threshold as per requirements.
        
        Args:
            source: API source name ('newsapi', 'finnhub', 'alphavantage')
        
        Returns:
            True if within limits, False otherwise
        """
        key = self._rate_limit_keys.get(source)
        if not key:
            return True
        
        count = self.cache.get(key, deserialize=False)
        if count is None:
            return True
        
        # Get rate limits from settings
        limits = {
            'newsapi': self.settings.newsapi_rate_limit,
            'finnhub': self.settings.finnhub_rate_limit,
            'alphavantage': self.settings.alphavantage_rate_limit
        }
        
        limit = limits.get(source, 100)
        current_count = int(count)
        
        # Stay at 80% of limit
        return current_count < int(limit * 0.8)
    
    def _increment_rate_limit(self, source: str, ttl: int = 3600):
        """
        Increment rate limit counter for a source.
        
        Args:
            source: API source name
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        key = self._rate_limit_keys.get(source)
        if not key:
            return
        
        count = self.cache.increment(key)
        if count == 1:
            # Set expiration on first increment
            self.cache.expire(key, ttl)
    
    def _generate_content_hash(self, title: str, content: str) -> str:
        """
        Generate SHA-256 hash of article content for duplicate detection.
        
        Args:
            title: Article title
            content: Article content
        
        Returns:
            Hexadecimal hash string
        """
        combined = f"{title.lower().strip()}|{content.lower().strip()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def _is_duplicate(self, content_hash: str) -> bool:
        """
        Check if article is a duplicate based on content hash.
        
        Args:
            content_hash: SHA-256 hash of article content
        
        Returns:
            True if duplicate, False if unique
        """
        # Check if hash exists in Redis set
        exists = self.cache.client.sismember(self._hash_set_key, content_hash)
        return bool(exists)
    
    def _mark_as_seen(self, content_hash: str, ttl: int = 86400):
        """
        Mark article as seen by storing its hash.
        
        Args:
            content_hash: SHA-256 hash of article content
            ttl: Time-to-live in seconds (default: 24 hours)
        """
        self.cache.client.sadd(self._hash_set_key, content_hash)
        # Set TTL on the set
        self.cache.expire(self._hash_set_key, ttl)
    
    def detect_breaking_news(self, article: NewsArticle) -> bool:
        """
        Detect if news article is breaking news (Property 10).
        
        Property 10: Breaking News Detection
        An article is considered breaking news if it was published within
        the last 30 minutes (1800 seconds).
        
        Args:
            article: NewsArticle object
        
        Returns:
            True if article is breaking news, False otherwise
        
        **Validates: Property 10**
        """
        time_diff = datetime.utcnow() - article.published_at
        is_breaking = time_diff.total_seconds() <= 1800  # 30 minutes
        
        if is_breaking:
            logger.info(
                "breaking_news_detected",
                article_id=article.id,
                title=article.title[:50],
                published_at=article.published_at.isoformat(),
                age_seconds=int(time_diff.total_seconds())
            )
        
        return is_breaking
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _fetch_newsapi(self, query: Optional[str] = None, limit: int = 50) -> List[NewsArticle]:
        """
        Fetch news from NewsAPI.org.
        
        API Limits: 100 requests/day (free tier) or custom based on plan
        
        Args:
            query: Search query (default: financial news keywords)
            limit: Maximum number of articles
        
        Returns:
            List of NewsArticle objects
        """
        if not self.settings.newsapi_key:
            logger.warning("newsapi_key_not_configured")
            return []
        
        if not self._check_rate_limit('newsapi'):
            logger.warning("newsapi_rate_limit_approached")
            return []
        
        try:
            self._increment_rate_limit('newsapi', ttl=86400)  # 24-hour window
            
            # Default query for financial news
            if not query:
                query = "(stock OR market OR trading OR NYSE OR NASDAQ OR finance)"
            
            # Calculate time range (last 24 hours)
            from_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
            
            params = {
                'q': query,
                'from': from_time,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': min(limit, 100),  # API max is 100
                'apiKey': self.settings.newsapi_key
            }
            
            response = requests.get(
                f"{self._newsapi_base}/everything",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data.get('articles', []):
                # Skip if no title or content
                if not item.get('title') or not item.get('description'):
                    continue
                
                # Generate article ID and content hash
                article_id = f"newsapi_{hashlib.md5(item['url'].encode()).hexdigest()}"
                content = item.get('content') or item.get('description', '')
                content_hash = self._generate_content_hash(item['title'], content)
                
                # Skip duplicates
                if self._is_duplicate(content_hash):
                    logger.debug("duplicate_article_skipped", article_id=article_id)
                    continue
                
                # Parse published date
                try:
                    published_at = datetime.fromisoformat(
                        item['publishedAt'].replace('Z', '+00:00')
                    ).replace(tzinfo=None)
                except:
                    published_at = datetime.utcnow()
                
                article = NewsArticle(
                    id=article_id,
                    title=item['title'],
                    content=content,
                    source=item.get('source', {}).get('name', 'NewsAPI'),
                    published_at=published_at,
                    url=item['url'],
                    tickers=[],  # Will be extracted later by NLP
                    author=item.get('author')
                )
                
                articles.append(article)
                self._mark_as_seen(content_hash)
            
            logger.info(
                "newsapi_fetch_complete",
                fetched=len(articles),
                duplicates_skipped=len(data.get('articles', [])) - len(articles)
            )
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error("newsapi_fetch_failed", error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _fetch_finnhub(self, category: str = 'general', limit: int = 50) -> List[NewsArticle]:
        """
        Fetch news from Finnhub.io.
        
        API Limits: 60 requests/minute (free tier)
        
        Args:
            category: News category ('general', 'forex', 'crypto', 'merger')
            limit: Maximum number of articles
        
        Returns:
            List of NewsArticle objects
        """
        if not self.settings.finnhub_api_key:
            logger.warning("finnhub_api_key_not_configured")
            return []
        
        if not self._check_rate_limit('finnhub'):
            logger.warning("finnhub_rate_limit_approached")
            return []
        
        try:
            self._increment_rate_limit('finnhub', ttl=60)  # 1-minute window
            
            params = {
                'category': category,
                'token': self.settings.finnhub_api_key
            }
            
            response = requests.get(
                f"{self._finnhub_base}/news",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data[:limit]:
                # Skip if no headline
                if not item.get('headline'):
                    continue
                
                # Generate article ID and content hash
                article_id = f"finnhub_{item['id']}"
                content = item.get('summary', '')
                content_hash = self._generate_content_hash(item['headline'], content)
                
                # Skip duplicates
                if self._is_duplicate(content_hash):
                    logger.debug("duplicate_article_skipped", article_id=article_id)
                    continue
                
                # Parse published date (Unix timestamp)
                published_at = datetime.utcfromtimestamp(item['datetime'])
                
                # Extract related tickers
                tickers = item.get('related', '').split(',') if item.get('related') else []
                tickers = [t.strip() for t in tickers if t.strip()]
                
                article = NewsArticle(
                    id=article_id,
                    title=item['headline'],
                    content=content,
                    source=item.get('source', 'Finnhub'),
                    published_at=published_at,
                    url=item['url'],
                    tickers=tickers,
                    category=None  # Will be categorized later
                )
                
                articles.append(article)
                self._mark_as_seen(content_hash)
            
            logger.info(
                "finnhub_fetch_complete",
                fetched=len(articles),
                category=category
            )
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error("finnhub_fetch_failed", error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _fetch_alphavantage_news(self, tickers: Optional[str] = None, limit: int = 50) -> List[NewsArticle]:
        """
        Fetch news from Alpha Vantage news sentiment endpoint.
        
        API Limits: 5 requests/minute (free tier)
        
        Args:
            tickers: Comma-separated ticker symbols
            limit: Maximum number of articles
        
        Returns:
            List of NewsArticle objects
        """
        if not self.settings.alphavantage_api_key:
            logger.warning("alphavantage_api_key_not_configured")
            return []
        
        if not self._check_rate_limit('alphavantage'):
            logger.warning("alphavantage_rate_limit_approached")
            return []
        
        try:
            self._increment_rate_limit('alphavantage', ttl=60)  # 1-minute window
            
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.settings.alphavantage_api_key,
                'limit': min(limit, 1000)  # API max is 1000
            }
            
            if tickers:
                params['tickers'] = tickers
            
            response = requests.get(
                self._alphavantage_base,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data.get('feed', []):
                # Skip if no title
                if not item.get('title'):
                    continue
                
                # Generate article ID and content hash
                article_id = f"alphavantage_{hashlib.md5(item['url'].encode()).hexdigest()}"
                content = item.get('summary', '')
                content_hash = self._generate_content_hash(item['title'], content)
                
                # Skip duplicates
                if self._is_duplicate(content_hash):
                    logger.debug("duplicate_article_skipped", article_id=article_id)
                    continue
                
                # Parse published date
                try:
                    published_at = datetime.strptime(
                        item['time_published'],
                        '%Y%m%dT%H%M%S'
                    )
                except:
                    published_at = datetime.utcnow()
                
                # Extract ticker symbols
                tickers_list = []
                for ticker_data in item.get('ticker_sentiment', []):
                    if ticker_data.get('ticker'):
                        tickers_list.append(ticker_data['ticker'])
                
                article = NewsArticle(
                    id=article_id,
                    title=item['title'],
                    content=content,
                    source=item.get('source', 'Alpha Vantage'),
                    published_at=published_at,
                    url=item['url'],
                    tickers=tickers_list,
                    category=None  # Will be categorized later
                )
                
                articles.append(article)
                self._mark_as_seen(content_hash)
            
            logger.info(
                "alphavantage_fetch_complete",
                fetched=len(articles)
            )
            
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error("alphavantage_fetch_failed", error=str(e))
            raise
    
    def collect_latest_news(self, limit: int = 100) -> List[NewsArticle]:
        """
        Collect latest news from all configured sources.
        
        Aggregates news from:
        - NewsAPI.org (general financial news)
        - Finnhub.io (real-time market news)
        - Alpha Vantage (news with sentiment data)
        
        Features:
        - Rate limiting per source (80% of limits)
        - Duplicate detection via content hashing
        - Redis caching (1-hour TTL)
        - Database persistence
        
        Args:
            limit: Maximum total number of articles (distributed across sources)
        
        Returns:
            List of unique NewsArticle objects, sorted by published date (newest first)
        """
        # Check cache first
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.NEWS_LATEST,
            limit=limit
        )
        
        cached_news = self.cache.get(cache_key)
        if cached_news:
            logger.debug("news_cache_hit", limit=limit)
            return cached_news
        
        all_articles = []
        per_source_limit = limit // 3  # Distribute across 3 sources
        
        # Fetch from each source
        try:
            newsapi_articles = self._fetch_newsapi(limit=per_source_limit)
            all_articles.extend(newsapi_articles)
        except Exception as e:
            logger.error("newsapi_collection_failed", error=str(e))
        
        try:
            finnhub_articles = self._fetch_finnhub(limit=per_source_limit)
            all_articles.extend(finnhub_articles)
        except Exception as e:
            logger.error("finnhub_collection_failed", error=str(e))
        
        try:
            alphavantage_articles = self._fetch_alphavantage_news(limit=per_source_limit)
            all_articles.extend(alphavantage_articles)
        except Exception as e:
            logger.error("alphavantage_collection_failed", error=str(e))
        
        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        # Limit to requested count
        all_articles = all_articles[:limit]
        
        # Store in database
        self._store_articles(all_articles)
        
        # Cache results
        self.cache.set_with_pattern_ttl(
            cache_key,
            all_articles,
            pattern=CacheKeyPatterns.NEWS_LATEST
        )
        
        logger.info(
            "news_collection_complete",
            total_articles=len(all_articles),
            breaking_news=sum(1 for a in all_articles if self.detect_breaking_news(a))
        )
        
        return all_articles
    
    def collect_ticker_news(self, ticker: str, hours: int = 24) -> List[NewsArticle]:
        """
        Collect news articles mentioning a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            hours: Number of hours to look back
        
        Returns:
            List of NewsArticle objects mentioning the ticker
        """
        # Check cache first
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.NEWS_TICKER,
            ticker=ticker,
            hours=hours
        )
        
        cached_news = self.cache.get(cache_key)
        if cached_news:
            logger.debug("ticker_news_cache_hit", ticker=ticker)
            return cached_news
        
        articles = []
        
        # Try Alpha Vantage first (has ticker-specific endpoint)
        try:
            av_articles = self._fetch_alphavantage_news(tickers=ticker, limit=50)
            articles.extend(av_articles)
        except Exception as e:
            logger.error("alphavantage_ticker_fetch_failed", ticker=ticker, error=str(e))
        
        # Try Finnhub (check for ticker in related field)
        try:
            finnhub_articles = self._fetch_finnhub(limit=50)
            # Filter for ticker
            ticker_articles = [
                a for a in finnhub_articles
                if ticker.upper() in [t.upper() for t in a.tickers]
            ]
            articles.extend(ticker_articles)
        except Exception as e:
            logger.error("finnhub_ticker_fetch_failed", ticker=ticker, error=str(e))
        
        # Filter by time window
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        articles = [a for a in articles if a.published_at >= cutoff_time]
        
        # Sort by published date (newest first)
        articles.sort(key=lambda x: x.published_at, reverse=True)
        
        # Store in database
        self._store_articles(articles)
        
        # Cache results
        self.cache.set_with_pattern_ttl(
            cache_key,
            articles,
            pattern=CacheKeyPatterns.NEWS_TICKER
        )
        
        logger.info(
            "ticker_news_collection_complete",
            ticker=ticker,
            articles=len(articles),
            hours=hours
        )
        
        return articles
    
    def _store_articles(self, articles: List[NewsArticle]):
        """
        Store news articles in the database.
        
        Args:
            articles: List of NewsArticle objects to store
        """
        if not articles:
            return
        
        db: Session = next(get_db())
        
        try:
            stored_count = 0
            updated_count = 0
            
            for article in articles:
                # Check if article already exists
                existing = db.query(DBNewsArticle).filter(
                    DBNewsArticle.article_id == article.id
                ).first()
                
                if existing:
                    # Update existing article
                    existing.title = article.title
                    existing.content = article.content
                    existing.summary = article.content[:500] if article.content else None
                    existing.source = article.source
                    existing.author = article.author
                    existing.published_at = article.published_at
                    existing.url = article.url
                    existing.category = article.category.value if article.category else None
                    existing.is_breaking = self.detect_breaking_news(article)
                    updated_count += 1
                else:
                    # Create new article
                    db_article = DBNewsArticle(
                        article_id=article.id,
                        title=article.title,
                        content=article.content,
                        summary=article.content[:500] if article.content else None,
                        source=article.source,
                        author=article.author,
                        published_at=article.published_at,
                        url=article.url,
                        category=article.category.value if article.category else None,
                        is_breaking=self.detect_breaking_news(article)
                    )
                    db.add(db_article)
                    stored_count += 1
            
            db.commit()
            
            logger.info(
                "articles_stored",
                stored=stored_count,
                updated=updated_count,
                total=len(articles)
            )
            
        except Exception as e:
            db.rollback()
            logger.error("article_storage_failed", error=str(e))
        finally:
            db.close()
    
    def get_breaking_news(self) -> List[NewsArticle]:
        """
        Get all breaking news articles (published within last 30 minutes).
        
        Returns:
            List of breaking NewsArticle objects
        
        **Validates: Property 10**
        """
        # Check cache first
        cache_key = CacheKeyPatterns.NEWS_BREAKING
        
        cached_breaking = self.cache.get(cache_key)
        if cached_breaking:
            logger.debug("breaking_news_cache_hit")
            return cached_breaking
        
        # Collect latest news
        articles = self.collect_latest_news(limit=100)
        
        # Filter for breaking news
        breaking = [a for a in articles if self.detect_breaking_news(a)]
        
        # Cache for 5 minutes
        self.cache.set_with_pattern_ttl(
            cache_key,
            breaking,
            pattern=CacheKeyPatterns.NEWS_BREAKING
        )
        
        logger.info("breaking_news_identified", count=len(breaking))
        return breaking
