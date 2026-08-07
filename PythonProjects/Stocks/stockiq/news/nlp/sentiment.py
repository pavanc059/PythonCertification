"""
Sentiment Analysis Pipeline for Financial News.

This module implements Requirements 2.4, 2.10, 2.11:
- Multi-model sentiment analysis (VADER + FinBERT) (Req 2.4)
- Sentiment-price correlation tracking (Req 2.10, 2.11)
- Redis caching with 24-hour TTL
- Database storage for historical analysis

Property Tests:
- Property 9: Sentiment scores SHALL be in range [-1.0, 1.0]
- Property 12: Correlation coefficients SHALL be in range [-1.0, 1.0]
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

from stockiq.infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
from stockiq.infrastructure.database import get_db_context
from stockiq.infrastructure.models import NewsSentiment as NewsSentimentModel

logger = structlog.get_logger(__name__)


@dataclass
class SentimentScore:
    """
    Sentiment score with confidence metrics.
    
    Property 9: All scores SHALL be in range [-1.0, 1.0]
    """
    overall: float  # -1 to +1, combined score from all models
    vader_score: float  # -1 to +1, VADER sentiment
    finbert_score: float  # -1 to +1, FinBERT sentiment
    confidence: float  # 0 to 1, based on model agreement
    
    def __post_init__(self):
        """Validate sentiment score ranges (Property 9)."""
        # Ensure all scores are in valid range
        self.overall = max(-1.0, min(1.0, self.overall))
        self.vader_score = max(-1.0, min(1.0, self.vader_score))
        self.finbert_score = max(-1.0, min(1.0, self.finbert_score))
        self.confidence = max(0.0, min(1.0, self.confidence))
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for storage."""
        return {
            'overall': self.overall,
            'vader_score': self.vader_score,
            'finbert_score': self.finbert_score,
            'confidence': self.confidence,
        }


class SentimentAnalyzer:
    """
    Multi-model sentiment analyzer combining VADER and FinBERT.
    
    VADER (Valence Aware Dictionary and sEntiment Reasoner):
    - Rule-based lexicon approach
    - Fast, lightweight
    - Good for general sentiment
    
    FinBERT:
    - Transformer-based deep learning model
    - Fine-tuned on financial text
    - Better for financial domain
    
    The analyzer combines both models to leverage their strengths
    and provides confidence scores based on model agreement.
    
    Requirements:
    - Req 2.4: Calculate sentiment scores using VADER and FinBERT
    - Req 2.10: Track sentiment trends over time
    - Req 2.11: Correlate sentiment with price movements
    
    Property Tests:
    - Property 9: Sentiment scores in range [-1.0, 1.0]
    """
    
    def __init__(self):
        """Initialize sentiment analyzers."""
        # Initialize VADER
        self.vader = SentimentIntensityAnalyzer()
        logger.info("vader_initialized")
        
        # Initialize FinBERT
        try:
            import os
            from pathlib import Path
            
            # Try local path first (manually downloaded model)
            local_model_path = Path(__file__).parent.parent.parent / "models" / "sentiment" / "FinBERT"
            
            if local_model_path.exists() and (local_model_path / "pytorch_model.bin").exists():
                logger.info("loading_finbert_from_local", path=str(local_model_path))
                
                # Check if tokenizer files exist
                vocab_file = local_model_path / "vocab.txt"
                
                if vocab_file.exists():
                    # Load complete model from local
                    self.finbert_tokenizer = AutoTokenizer.from_pretrained(
                        str(local_model_path),
                        local_files_only=True
                    )
                    self.finbert_model = AutoModelForSequenceClassification.from_pretrained(
                        str(local_model_path),
                        local_files_only=True
                    )
                    logger.info("finbert_initialized", source="local_complete", path=str(local_model_path))
                else:
                    # Use BERT base tokenizer (FinBERT is based on BERT)
                    # Load model from local, tokenizer from bert-base-uncased
                    logger.warning("local_finbert_missing_vocab_using_bert_base", path=str(local_model_path))
                    try:
                        self.finbert_tokenizer = AutoTokenizer.from_pretrained(
                            "bert-base-uncased",
                            cache_dir=".cache/transformers"
                        )
                        self.finbert_model = AutoModelForSequenceClassification.from_pretrained(
                            str(local_model_path),
                            local_files_only=True
                        )
                        logger.info("finbert_initialized", source="hybrid", tokenizer="bert-base", model="local")
                    except Exception as e2:
                        logger.error("bert_base_tokenizer_failed_trying_online", error=str(e2))
                        # Last resort: try downloading FinBERT tokenizer online
                        self.finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                        self.finbert_model = AutoModelForSequenceClassification.from_pretrained(
                            str(local_model_path),
                            local_files_only=True
                        )
                        logger.info("finbert_initialized", source="hybrid", tokenizer="online", model="local")
            else:
                # Fallback to HuggingFace cache or download
                logger.info("local_finbert_not_found_using_cache", attempted_path=str(local_model_path))
                self.finbert_tokenizer = AutoTokenizer.from_pretrained(
                    "ProsusAI/finbert",
                    cache_dir=".cache/transformers"
                )
                self.finbert_model = AutoModelForSequenceClassification.from_pretrained(
                    "ProsusAI/finbert",
                    cache_dir=".cache/transformers"
                )
                logger.info("finbert_initialized", source="huggingface", model="ProsusAI/finbert")
            
            self.finbert_model.eval()  # Set to evaluation mode
        except Exception as e:
            logger.error("finbert_initialization_failed", error=str(e))
            self.finbert_tokenizer = None
            self.finbert_model = None
        
        # Get cache instance (with graceful degradation if Redis unavailable)
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
    
    def analyze_with_vader(self, text: str) -> float:
        """
        Analyze sentiment using VADER.
        
        VADER returns a compound score in range [-1, 1]:
        - Positive sentiment: > 0.05
        - Neutral sentiment: -0.05 to 0.05
        - Negative sentiment: < -0.05
        
        Args:
            text: Text to analyze
        
        Returns:
            Sentiment score in range [-1.0, 1.0]
        
        Property 9: Return value SHALL be in range [-1.0, 1.0]
        """
        try:
            if not text or not text.strip():
                logger.warning("vader_empty_text")
                return 0.0
            
            # Get VADER scores
            scores = self.vader.polarity_scores(text)
            compound_score = scores['compound']
            
            # Ensure score is in valid range (Property 9)
            compound_score = max(-1.0, min(1.0, compound_score))
            
            logger.debug(
                "vader_analysis_complete",
                score=compound_score,
                pos=scores['pos'],
                neg=scores['neg'],
                neu=scores['neu']
            )
            
            return compound_score
            
        except Exception as e:
            logger.error("vader_analysis_failed", error=str(e))
            return 0.0
    
    def analyze_with_finbert(self, text: str) -> float:
        """
        Analyze sentiment using FinBERT.
        
        FinBERT classifies text into three categories.
        The label mapping is read from the model's config.json:
        - Standard FinBERT: 0=negative, 1=neutral, 2=positive
        - Some variants: 0=positive, 1=negative, 2=neutral
        
        We convert the probability distribution to a continuous score [-1, 1]:
        score = P(positive) - P(negative)
        
        Args:
            text: Text to analyze
        
        Returns:
            Sentiment score in range [-1.0, 1.0]
        
        Property 9: Return value SHALL be in range [-1.0, 1.0]
        """
        try:
            if not text or not text.strip():
                logger.warning("finbert_empty_text")
                return 0.0
            
            if self.finbert_tokenizer is None or self.finbert_model is None:
                logger.warning("finbert_not_available", fallback="vader_only")
                return 0.0
            
            # Tokenize input (truncate to 512 tokens max)
            inputs = self.finbert_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            # Get predictions
            with torch.no_grad():
                outputs = self.finbert_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Convert to numpy
            probs = predictions[0].cpu().numpy()
            
            # Get label mapping from model config
            id2label = self.finbert_model.config.id2label
            
            # Find which index corresponds to each label
            positive_idx = None
            negative_idx = None
            for idx, label in id2label.items():
                if label.lower() == 'positive':
                    positive_idx = int(idx)
                elif label.lower() == 'negative':
                    negative_idx = int(idx)
            
            # Calculate sentiment score: P(positive) - P(negative)
            if positive_idx is not None and negative_idx is not None:
                sentiment_score = float(probs[positive_idx] - probs[negative_idx])
            else:
                # Fallback to standard mapping if config not found
                logger.warning("finbert_label_mapping_not_found_using_standard")
                sentiment_score = float(probs[2] - probs[0])
            
            # Ensure score is in valid range (Property 9)
            sentiment_score = max(-1.0, min(1.0, sentiment_score))
            
            logger.debug(
                "finbert_analysis_complete",
                score=sentiment_score,
                prob_positive=float(probs[positive_idx]) if positive_idx is not None else float(probs[2]),
                prob_neutral=float(probs[1]) if len(probs) > 1 else 0.0,
                prob_negative=float(probs[negative_idx]) if negative_idx is not None else float(probs[0]),
                label_mapping=id2label
            )
            
            return sentiment_score
            
        except Exception as e:
            logger.error("finbert_analysis_failed", error=str(e))
            return 0.0
    
    def _calculate_confidence(self, vader_score: float, finbert_score: float) -> float:
        """
        Calculate confidence based on model agreement.
        
        Confidence is calculated as:
        1. If both models agree on direction (both positive or both negative),
           confidence is high (based on magnitude similarity)
        2. If models disagree, confidence is lower
        
        Args:
            vader_score: VADER sentiment score
            finbert_score: FinBERT sentiment score
        
        Returns:
            Confidence score in range [0, 1]
        """
        # Check if both scores are available
        if vader_score == 0.0 and finbert_score == 0.0:
            return 0.0
        
        # If only one model available, medium confidence
        if vader_score == 0.0 or finbert_score == 0.0:
            return 0.5
        
        # Calculate agreement: 1 - normalized distance
        distance = abs(vader_score - finbert_score)
        max_distance = 2.0  # Maximum possible distance (-1 to +1)
        agreement = 1.0 - (distance / max_distance)
        
        # Boost confidence if both agree on direction
        same_direction = (vader_score * finbert_score) > 0
        if same_direction:
            # Higher confidence when models agree
            confidence = 0.5 + (agreement * 0.5)
        else:
            # Lower confidence when models disagree
            confidence = agreement * 0.5
        
        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def analyze_sentiment(self, text: str) -> SentimentScore:
        """
        Analyze sentiment using both VADER and FinBERT models.
        
        The overall score is a weighted average:
        - VADER: 40% weight (fast, general sentiment)
        - FinBERT: 60% weight (accurate, financial domain)
        
        If FinBERT is unavailable, VADER score is used as overall score.
        
        Args:
            text: Text to analyze
        
        Returns:
            SentimentScore with combined results
        
        Requirements:
        - Req 2.4: Multi-model sentiment analysis
        
        Property Tests:
        - Property 9: All scores SHALL be in range [-1.0, 1.0]
        """
        try:
            # Check cache first
            cache_key = f"sentiment:text:{hash(text)}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug("sentiment_cache_hit", cache_key=cache_key)
                return SentimentScore(**cached_result)
            
            # Analyze with VADER
            vader_score = self.analyze_with_vader(text)
            
            # Analyze with FinBERT
            finbert_score = self.analyze_with_finbert(text)
            
            # Calculate weighted average
            if finbert_score != 0.0:
                # Both models available
                overall_score = (0.4 * vader_score) + (0.6 * finbert_score)
            else:
                # FinBERT unavailable, use VADER only
                overall_score = vader_score
            
            # Ensure overall score is in valid range (Property 9)
            overall_score = max(-1.0, min(1.0, overall_score))
            
            # Calculate confidence
            confidence = self._calculate_confidence(vader_score, finbert_score)
            
            # Create sentiment score
            sentiment = SentimentScore(
                overall=overall_score,
                vader_score=vader_score,
                finbert_score=finbert_score,
                confidence=confidence
            )
            
            # Cache result (24-hour TTL as per requirements)
            self.cache.set(
                cache_key,
                sentiment.to_dict(),
                ttl=CacheTTL.SENTIMENT_ARTICLE,
                serialize=False
            )
            
            logger.info(
                "sentiment_analysis_complete",
                overall=overall_score,
                vader=vader_score,
                finbert=finbert_score,
                confidence=confidence
            )
            
            return sentiment
            
        except Exception as e:
            logger.error("sentiment_analysis_failed", error=str(e))
            # Return neutral sentiment on error
            return SentimentScore(
                overall=0.0,
                vader_score=0.0,
                finbert_score=0.0,
                confidence=0.0
            )
    
    def analyze_article(
        self,
        article_id: str,
        text: str,
        use_cache: bool = True
    ) -> SentimentScore:
        """
        Analyze sentiment for a news article with caching.
        
        Args:
            article_id: Unique article identifier
            text: Article text (title + content)
            use_cache: Whether to use cache (default: True)
        
        Returns:
            SentimentScore with results
        
        Requirements:
        - Cache sentiment results in Redis (24-hour TTL)
        """
        try:
            # Check cache first if enabled
            if use_cache:
                cache_key = CacheKeyPatterns.format_key(
                    CacheKeyPatterns.SENTIMENT_ARTICLE,
                    article_id=article_id
                )
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.debug("article_sentiment_cache_hit", article_id=article_id)
                    return SentimentScore(**cached_result)
            
            # Analyze sentiment
            sentiment = self.analyze_sentiment(text)
            
            # Cache result if enabled
            if use_cache:
                cache_key = CacheKeyPatterns.format_key(
                    CacheKeyPatterns.SENTIMENT_ARTICLE,
                    article_id=article_id
                )
                self.cache.set_with_pattern_ttl(
                    cache_key,
                    sentiment.to_dict(),
                    pattern=CacheKeyPatterns.SENTIMENT_ARTICLE,
                    serialize=False
                )
            
            logger.info(
                "article_sentiment_analyzed",
                article_id=article_id,
                overall=sentiment.overall,
                confidence=sentiment.confidence
            )
            
            return sentiment
            
        except Exception as e:
            logger.error(
                "article_sentiment_analysis_failed",
                article_id=article_id,
                error=str(e)
            )
            return SentimentScore(
                overall=0.0,
                vader_score=0.0,
                finbert_score=0.0,
                confidence=0.0
            )
    
    def store_sentiment(
        self,
        article_db_id: int,
        stock_db_id: int,
        sentiment: SentimentScore,
        entities: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store sentiment analysis results in database.
        
        Args:
            article_db_id: Database ID of news article
            stock_db_id: Database ID of stock
            sentiment: Sentiment score to store
            entities: Optional extracted entities (companies, people, locations)
        
        Returns:
            True if successful, False otherwise
        
        Requirements:
        - Store sentiment scores in database linked to articles
        """
        try:
            with get_db_context() as db:
                # Create sentiment record
                sentiment_record = NewsSentimentModel(
                    article_id=article_db_id,
                    stock_id=stock_db_id,
                    sentiment_score=sentiment.overall,
                    vader_score=sentiment.vader_score,
                    finbert_score=sentiment.finbert_score,
                    confidence=sentiment.confidence,
                    entities=entities,
                    created_at=datetime.utcnow()
                )
                
                db.add(sentiment_record)
                db.commit()
                
                logger.info(
                    "sentiment_stored",
                    article_id=article_db_id,
                    stock_id=stock_db_id,
                    sentiment=sentiment.overall
                )
                
                return True
                
        except Exception as e:
            logger.error(
                "sentiment_storage_failed",
                article_id=article_db_id,
                stock_id=stock_db_id,
                error=str(e)
            )
            return False
    
    def get_ticker_sentiment(self, ticker: str, use_cache: bool = True) -> Optional[float]:
        """
        Get latest sentiment score for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            use_cache: Whether to use cache (default: True)
        
        Returns:
            Latest sentiment score or None if not available
        
        Requirements:
        - Cache sentiment results in Redis (24-hour TTL)
        """
        try:
            # Check cache first if enabled
            if use_cache:
                cache_key = CacheKeyPatterns.format_key(
                    CacheKeyPatterns.SENTIMENT_TICKER,
                    ticker=ticker
                )
                cached_score = self.cache.get(cache_key, deserialize=False)
                if cached_score:
                    logger.debug("ticker_sentiment_cache_hit", ticker=ticker)
                    return float(cached_score)
            
            # Query database for latest sentiment
            with get_db_context() as db:
                from stockiq.infrastructure.models import Stock
                from sqlalchemy import desc
                
                # Get stock
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if not stock:
                    logger.warning("stock_not_found", ticker=ticker)
                    return None
                
                # Get latest sentiment
                latest_sentiment = (
                    db.query(NewsSentimentModel)
                    .filter(NewsSentimentModel.stock_id == stock.id)
                    .order_by(desc(NewsSentimentModel.created_at))
                    .first()
                )
                
                if not latest_sentiment:
                    logger.debug("no_sentiment_found", ticker=ticker)
                    return None
                
                sentiment_score = latest_sentiment.sentiment_score
                
                # Cache result if enabled
                if use_cache:
                    cache_key = CacheKeyPatterns.format_key(
                        CacheKeyPatterns.SENTIMENT_TICKER,
                        ticker=ticker
                    )
                    self.cache.set_with_pattern_ttl(
                        cache_key,
                        str(sentiment_score),
                        pattern=CacheKeyPatterns.SENTIMENT_TICKER,
                        serialize=False
                    )
                
                logger.info(
                    "ticker_sentiment_retrieved",
                    ticker=ticker,
                    sentiment=sentiment_score
                )
                
                return sentiment_score
                
        except Exception as e:
            logger.error(
                "ticker_sentiment_retrieval_failed",
                ticker=ticker,
                error=str(e)
            )
            return None


# Global sentiment analyzer instance
_sentiment_analyzer = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get the global sentiment analyzer instance."""
    global _sentiment_analyzer
    
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    
    return _sentiment_analyzer
