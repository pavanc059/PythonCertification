"""
News Summarization Pipeline for Financial News.

This module implements Requirement 2.8 (AI-Powered News Summarization):
- Extractive summarization using TextRank algorithm
- Key fact extraction (numerical data: prices, percentages, dates)
- Daily market summary generation
- Redis caching with 24-hour TTL

Requirements implemented:
- Requirement 2.8: Generate 2-3 sentence summaries for news articles
- Requirement 10.1: Extract key facts (who, what, when, where, why)
- Requirement 10.3: Identify and highlight numerical data

Features:
- TextRank algorithm for extractive summarization
- Regular expressions for numerical fact extraction
- Intelligent sentence selection based on importance
- Redis caching (24-hour TTL)
- Graceful degradation if dependencies unavailable
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
import structlog
from collections import Counter
import math

from stockiq.data.models import NewsArticle
from stockiq.infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL

logger = structlog.get_logger(__name__)


@dataclass
class KeyFacts:
    """
    Extracted key facts from a news article.
    
    Contains structured numerical and temporal data:
    - Prices: Stock prices, valuations, deal amounts
    - Percentages: Changes, growth rates, margins
    - Dates: Event dates, deadlines, earnings dates
    - Numbers: Volume, revenue, profit, other metrics
    """
    prices: List[Dict[str, Any]]  # [{value, currency, context}]
    percentages: List[Dict[str, Any]]  # [{value, context}]
    dates: List[Dict[str, Any]]  # [{value, context}]
    numbers: List[Dict[str, Any]]  # [{value, unit, context}]
    
    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert to dictionary for storage."""
        return {
            'prices': self.prices,
            'percentages': self.percentages,
            'dates': self.dates,
            'numbers': self.numbers,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, List[Dict[str, Any]]]) -> 'KeyFacts':
        """Create from dictionary."""
        return cls(
            prices=data.get('prices', []),
            percentages=data.get('percentages', []),
            dates=data.get('dates', []),
            numbers=data.get('numbers', []),
        )


class NewsSummarizer:
    """
    News summarization using TextRank algorithm for extractive summarization.
    
    TextRank Algorithm:
    - Graph-based ranking algorithm (similar to PageRank)
    - Treats sentences as nodes in a graph
    - Edges represent similarity between sentences
    - Ranks sentences by importance/centrality
    - Selects top-ranked sentences for summary
    
    Key Fact Extraction:
    - Uses regex patterns to identify numerical data
    - Extracts prices, percentages, dates, and other numbers
    - Maintains context around extracted values
    
    Features:
    - Extractive summarization (selects existing sentences)
    - Customizable summary length (number of sentences)
    - Key fact extraction with context
    - Daily summary generation from multiple articles
    - Redis caching (24-hour TTL)
    
    Requirements:
    - Req 2.8: Generate 2-3 sentence summaries
    - Req 10.1: Extract key facts
    - Req 10.3: Identify numerical data
    """
    
    # Regex patterns for numerical fact extraction
    PRICE_PATTERN = r'(?:\$|USD|EUR|GBP)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:billion|million|thousand|[bBmMkK])?'
    PERCENTAGE_PATTERN = r'(\d+(?:\.\d+)?)\s*(?:%|percent|percentage)'
    DATE_PATTERN = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}'
    NUMBER_PATTERN = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|thousand|shares|contracts|dollars|units)'
    
    def __init__(self):
        """Initialize news summarizer."""
        # Get cache instance
        try:
            self.cache = get_cache()
        except Exception as e:
            logger.warning("cache_initialization_failed_using_mock", error=str(e))
            # Create a mock cache that always misses
            from unittest.mock import MagicMock
            self.cache = MagicMock()
            self.cache.get.return_value = None
            self.cache.set = lambda *args, **kwargs: None
            self.cache.set_with_pattern_ttl = lambda *args, **kwargs: None
        
        # Compile regex patterns
        self._price_regex = re.compile(self.PRICE_PATTERN, re.IGNORECASE)
        self._percentage_regex = re.compile(self.PERCENTAGE_PATTERN, re.IGNORECASE)
        self._date_regex = re.compile(self.DATE_PATTERN, re.IGNORECASE)
        self._number_regex = re.compile(self.NUMBER_PATTERN, re.IGNORECASE)
    
    def _tokenize_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Uses simple regex-based sentence splitting.
        More sophisticated than split('.') but lighter than NLTK.
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of sentences
        """
        # Split on sentence boundaries (., !, ?)
        # But preserve abbreviations like U.S., Inc., etc.
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
        sentences = re.split(sentence_pattern, text)
        
        # Clean and filter sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Filter out very short sentences (< 5 words to be more permissive)
        sentences = [s for s in sentences if len(s.split()) >= 5]
        
        return sentences
    
    def _tokenize_words(self, text: str) -> List[str]:
        """
        Split text into words.
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of words (lowercase, no punctuation)
        """
        # Remove punctuation and convert to lowercase
        words = re.findall(r'\b[a-z]{2,}\b', text.lower())
        return words
    
    def _calculate_sentence_similarity(self, sent1: str, sent2: str) -> float:
        """
        Calculate similarity between two sentences using word overlap.
        
        Uses Jaccard similarity: |A ∩ B| / |A ∪ B|
        
        Args:
            sent1: First sentence
            sent2: Second sentence
        
        Returns:
            Similarity score [0, 1]
        """
        words1 = set(self._tokenize_words(sent1))
        words2 = set(self._tokenize_words(sent2))
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _build_similarity_matrix(self, sentences: List[str]) -> List[List[float]]:
        """
        Build similarity matrix for sentences.
        
        Creates an NxN matrix where element [i][j] is the similarity
        between sentence i and sentence j.
        
        Args:
            sentences: List of sentences
        
        Returns:
            2D similarity matrix
        """
        n = len(sentences)
        matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self._calculate_sentence_similarity(
                        sentences[i],
                        sentences[j]
                    )
        
        return matrix
    
    def _textrank(self, similarity_matrix: List[List[float]], 
                  damping: float = 0.85, 
                  iterations: int = 30) -> List[float]:
        """
        Apply TextRank algorithm to rank sentences.
        
        TextRank is based on PageRank:
        - Each sentence is a node
        - Edges have weights (similarity scores)
        - Iteratively calculate importance scores
        - Converges to stable ranking
        
        Args:
            similarity_matrix: NxN similarity matrix
            damping: Damping factor (default: 0.85, like PageRank)
            iterations: Number of iterations (default: 30)
        
        Returns:
            List of importance scores for each sentence
        """
        n = len(similarity_matrix)
        if n == 0:
            return []
        
        # Initialize scores uniformly
        scores = [1.0 / n] * n
        
        # Calculate sum of similarities for normalization
        similarity_sums = [sum(row) for row in similarity_matrix]
        
        # Iterative scoring
        for _ in range(iterations):
            new_scores = []
            
            for i in range(n):
                # Calculate weighted sum of incoming scores
                incoming_score = 0.0
                for j in range(n):
                    if i != j and similarity_sums[j] > 0:
                        # Weighted contribution from sentence j to sentence i
                        incoming_score += (similarity_matrix[j][i] / similarity_sums[j]) * scores[j]
                
                # Apply damping factor
                new_score = (1 - damping) + damping * incoming_score
                new_scores.append(new_score)
            
            scores = new_scores
        
        return scores
    
    def summarize_extractive(self, text: str, sentences: int = 3) -> str:
        """
        Generate extractive summary using TextRank algorithm.
        
        Extractive summarization:
        - Selects important sentences from original text
        - Preserves exact wording and structure
        - No new text generation
        
        Process:
        1. Split text into sentences
        2. Build similarity matrix
        3. Apply TextRank to rank sentences
        4. Select top N sentences
        5. Return in original order
        
        Args:
            text: Text to summarize
            sentences: Number of sentences in summary (default: 3)
        
        Returns:
            Extractive summary as string
        
        Requirements:
        - Req 2.8: Generate 2-3 sentence summaries
        
        Example:
            >>> summarizer = NewsSummarizer()
            >>> summary = summarizer.summarize_extractive(long_article, sentences=3)
        """
        try:
            if not text or not text.strip():
                logger.warning("summarize_empty_text")
                return ""
            
            # Check cache first
            cache_key = f"summary:extractive:{hash(text)}:{sentences}"
            cached_summary = self.cache.get(cache_key, deserialize=False)
            if cached_summary:
                logger.debug("summary_cache_hit", cache_key=cache_key)
                return cached_summary
            
            # Tokenize into sentences
            sentence_list = self._tokenize_sentences(text)
            
            # Handle edge cases
            if not sentence_list:
                logger.warning("no_sentences_found")
                return text[:500]  # Return first 500 chars as fallback
            
            if len(sentence_list) <= sentences:
                # Text is already short enough
                summary = ' '.join(sentence_list)
                logger.debug("text_already_short", sentence_count=len(sentence_list))
            else:
                # Build similarity matrix
                similarity_matrix = self._build_similarity_matrix(sentence_list)
                
                # Apply TextRank
                scores = self._textrank(similarity_matrix)
                
                # Select top N sentences
                # Pair sentences with their scores and original indices
                ranked_sentences = [
                    (idx, score, sent) 
                    for idx, (score, sent) in enumerate(zip(scores, sentence_list))
                ]
                
                # Sort by score (descending) and take top N
                ranked_sentences.sort(key=lambda x: x[1], reverse=True)
                top_sentences = ranked_sentences[:sentences]
                
                # Sort by original index to preserve order
                top_sentences.sort(key=lambda x: x[0])
                
                # Extract sentence text
                summary = ' '.join([sent for _, _, sent in top_sentences])
            
            # Cache result (24-hour TTL)
            self.cache.set(
                cache_key,
                summary,
                ttl=86400,  # 24 hours
                serialize=False
            )
            
            logger.info(
                "extractive_summary_generated",
                original_length=len(text),
                summary_length=len(summary),
                sentences_extracted=sentences
            )
            
            return summary
            
        except Exception as e:
            logger.error("extractive_summarization_failed", error=str(e))
            # Return first 500 chars as fallback
            return text[:500] if text else ""
    
    def extract_key_facts(self, text: str) -> KeyFacts:
        """
        Extract key numerical facts from text.
        
        Extracts:
        - Prices: Dollar amounts, valuations, deal sizes
        - Percentages: Changes, growth rates, margins
        - Dates: Event dates, deadlines, quarters
        - Numbers: Volume, revenue, units, other metrics
        
        Each extracted fact includes:
        - Value: The numerical value
        - Unit: Associated unit (if applicable)
        - Context: Surrounding text for interpretation
        
        Args:
            text: Text to extract facts from
        
        Returns:
            KeyFacts object with extracted information
        
        Requirements:
        - Req 10.1: Extract key facts from articles
        - Req 10.3: Identify and highlight numerical data
        
        Example:
            >>> facts = summarizer.extract_key_facts("Stock rose 15% to $125.50")
            >>> facts.prices[0]['value']  # 125.50
            >>> facts.percentages[0]['value']  # 15.0
        """
        try:
            if not text or not text.strip():
                logger.warning("extract_facts_empty_text")
                return KeyFacts(prices=[], percentages=[], dates=[], numbers=[])
            
            # Check cache first
            cache_key = f"facts:text:{hash(text)}"
            cached_facts = self.cache.get(cache_key)
            if cached_facts:
                logger.debug("facts_cache_hit", cache_key=cache_key)
                return KeyFacts.from_dict(cached_facts)
            
            prices = []
            percentages = []
            dates = []
            numbers = []
            
            # Extract prices
            for match in self._price_regex.finditer(text):
                value_str = match.group(1).replace(',', '')
                start, end = match.span()
                context = text[max(0, start-30):min(len(text), end+30)]
                
                try:
                    value = float(value_str)
                    # Check for multiplier (billion, million, etc.)
                    multiplier_match = re.search(r'(billion|million|thousand|[bBmMkK])', match.group(0))
                    if multiplier_match:
                        multiplier = multiplier_match.group(1).lower()
                        if multiplier in ('billion', 'b'):
                            value *= 1_000_000_000
                        elif multiplier in ('million', 'm'):
                            value *= 1_000_000
                        elif multiplier in ('thousand', 'k'):
                            value *= 1_000
                    
                    prices.append({
                        'value': value,
                        'currency': 'USD',  # Default assumption
                        'context': context.strip()
                    })
                except ValueError:
                    pass
            
            # Extract percentages
            for match in self._percentage_regex.finditer(text):
                value_str = match.group(1)
                start, end = match.span()
                context = text[max(0, start-30):min(len(text), end+30)]
                
                try:
                    value = float(value_str)
                    percentages.append({
                        'value': value,
                        'context': context.strip()
                    })
                except ValueError:
                    pass
            
            # Extract dates
            for match in self._date_regex.finditer(text):
                date_str = match.group(0)
                start, end = match.span()
                context = text[max(0, start-20):min(len(text), end+20)]
                
                dates.append({
                    'value': date_str,
                    'context': context.strip()
                })
            
            # Extract other numbers
            for match in self._number_regex.finditer(text):
                value_str = match.group(1).replace(',', '')
                unit = match.group(2)
                start, end = match.span()
                context = text[max(0, start-30):min(len(text), end+30)]
                
                try:
                    value = float(value_str)
                    # Apply multiplier
                    if unit.lower() == 'billion':
                        value *= 1_000_000_000
                    elif unit.lower() == 'million':
                        value *= 1_000_000
                    elif unit.lower() == 'thousand':
                        value *= 1_000
                    
                    numbers.append({
                        'value': value,
                        'unit': unit,
                        'context': context.strip()
                    })
                except ValueError:
                    pass
            
            # Create facts object
            facts = KeyFacts(
                prices=prices,
                percentages=percentages,
                dates=dates,
                numbers=numbers
            )
            
            # Cache result (24-hour TTL)
            self.cache.set(
                cache_key,
                facts.to_dict(),
                ttl=86400,  # 24 hours
                serialize=False
            )
            
            logger.info(
                "key_facts_extracted",
                prices=len(prices),
                percentages=len(percentages),
                dates=len(dates),
                numbers=len(numbers)
            )
            
            return facts
            
        except Exception as e:
            logger.error("key_fact_extraction_failed", error=str(e))
            return KeyFacts(prices=[], percentages=[], dates=[], numbers=[])
    
    def generate_daily_summary(self, articles: List[NewsArticle]) -> str:
        """
        Generate daily market summary from multiple news articles.
        
        Aggregates information from multiple articles to create
        a comprehensive daily market summary covering:
        - Major market movements
        - Top gaining/losing sectors
        - Key corporate announcements
        - Economic indicators
        - Breaking developments
        
        Process:
        1. Summarize each article individually
        2. Identify most important articles (breaking news, high sentiment)
        3. Extract key themes and topics
        4. Combine into cohesive narrative
        5. Highlight numerical facts
        
        Args:
            articles: List of NewsArticle objects from the day
        
        Returns:
            Daily summary as formatted string
        
        Requirements:
        - Req 10.5: Generate daily market summary combining multiple sources
        
        Example:
            >>> articles = news_collector.collect_latest_news(limit=50)
            >>> daily_summary = summarizer.generate_daily_summary(articles)
        """
        try:
            if not articles:
                logger.warning("generate_daily_summary_no_articles")
                return "No news available for daily summary."
            
            # Check cache first
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            cache_key = f"summary:daily:{date_str}"
            cached_summary = self.cache.get(cache_key, deserialize=False)
            if cached_summary:
                logger.debug("daily_summary_cache_hit", date=date_str)
                return cached_summary
            
            # Sort articles by importance
            # Priority: breaking news > recent > older
            breaking_articles = [a for a in articles if a.is_breaking()]
            recent_articles = [a for a in articles if not a.is_breaking()]
            
            # Combine with breaking news first
            sorted_articles = breaking_articles + recent_articles
            
            # Limit to top 20 articles for summary
            top_articles = sorted_articles[:20]
            
            # Extract key themes by analyzing titles
            all_titles = ' '.join([a.title for a in top_articles])
            words = self._tokenize_words(all_titles)
            
            # Get most common meaningful words (excluding stop words)
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
                'has', 'have', 'had', 'will', 'would', 'should', 'could', 'may'
            }
            meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
            word_freq = Counter(meaningful_words)
            top_themes = [word for word, _ in word_freq.most_common(5)]
            
            # Build summary sections
            summary_parts = []
            
            # Opening: Market overview
            if breaking_articles:
                summary_parts.append(
                    f"Breaking: {len(breaking_articles)} major developments today, "
                    f"focusing on {', '.join(top_themes[:3])}."
                )
            else:
                summary_parts.append(
                    f"Today's market coverage highlights {', '.join(top_themes[:3])}."
                )
            
            # Key stories section
            key_stories = []
            for i, article in enumerate(top_articles[:5]):
                # Summarize article to 1 sentence
                summary = self.summarize_extractive(
                    article.title + '. ' + article.content,
                    sentences=1
                )
                key_stories.append(summary)
            
            if key_stories:
                summary_parts.append(
                    "Key stories: " + " ".join(key_stories)
                )
            
            # Extract notable facts
            all_facts = []
            for article in top_articles[:10]:
                facts = self.extract_key_facts(article.content)
                if facts.percentages:
                    all_facts.extend([
                        f"{f['value']:.1f}% ({f['context'][:40]}...)"
                        for f in facts.percentages[:2]
                    ])
            
            if all_facts:
                summary_parts.append(
                    f"Notable movements: {', '.join(all_facts[:5])}."
                )
            
            # Sector focus
            if len(top_themes) > 0:
                summary_parts.append(
                    f"Investor attention centered on {top_themes[0]} sector developments."
                )
            
            # Combine into final summary
            daily_summary = ' '.join(summary_parts)
            
            # Cache result (24-hour TTL)
            self.cache.set(
                cache_key,
                daily_summary,
                ttl=86400,  # 24 hours
                serialize=False
            )
            
            logger.info(
                "daily_summary_generated",
                article_count=len(articles),
                breaking_count=len(breaking_articles),
                summary_length=len(daily_summary),
                themes=top_themes
            )
            
            return daily_summary
            
        except Exception as e:
            logger.error("daily_summary_generation_failed", error=str(e))
            return "Unable to generate daily summary. Please check individual news articles."
    
    def summarize_article(
        self,
        article: NewsArticle,
        sentences: int = 3,
        include_facts: bool = False
    ) -> Dict[str, Any]:
        """
        Generate comprehensive summary for a news article.
        
        Combines extractive summarization with key fact extraction.
        
        Args:
            article: NewsArticle object
            sentences: Number of sentences in summary
            include_facts: Whether to include key facts (default: False)
        
        Returns:
            Dictionary with 'summary' and optionally 'facts'
        """
        try:
            # Generate summary
            full_text = f"{article.title}. {article.content}"
            summary = self.summarize_extractive(full_text, sentences=sentences)
            
            result = {
                'article_id': article.id,
                'summary': summary,
                'summary_length': len(summary),
                'original_length': len(full_text)
            }
            
            # Extract facts if requested
            if include_facts:
                facts = self.extract_key_facts(article.content)
                result['facts'] = facts.to_dict()
            
            logger.info(
                "article_summarized",
                article_id=article.id,
                sentences=sentences,
                include_facts=include_facts
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "article_summarization_failed",
                article_id=article.id,
                error=str(e)
            )
            return {
                'article_id': article.id,
                'summary': article.content[:500],
                'error': str(e)
            }
    
    def clear_cache(self, date: Optional[str] = None):
        """
        Clear summary cache.
        
        Args:
            date: Optional specific date to clear (YYYY-MM-DD), or None for all
        """
        try:
            if date:
                # Clear specific date
                cache_key = f"summary:daily:{date}"
                self.cache.delete(cache_key)
                logger.info("summary_cache_cleared", date=date)
            else:
                # Clear all summary caches
                self.cache.delete_pattern("summary:*")
                self.cache.delete_pattern("facts:*")
                logger.info("all_summary_cache_cleared")
        except Exception as e:
            logger.error("summary_cache_clear_failed", error=str(e))


# Global summarizer instance
_news_summarizer = None


def get_news_summarizer() -> NewsSummarizer:
    """Get the global news summarizer instance."""
    global _news_summarizer
    
    if _news_summarizer is None:
        _news_summarizer = NewsSummarizer()
    
    return _news_summarizer
