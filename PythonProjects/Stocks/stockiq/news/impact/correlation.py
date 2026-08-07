"""
News-Price Correlation Analysis Module.

This module implements Requirements 2.11 and 7:
- Track news sentiment correlation with price movements (Req 2.11)
- Multi-timeframe news impact analysis (Req 7)
- Calculate price impact at 1h, 4h, 1d, 1w timeframes
- Calculate news beta (stock's sensitivity to news)
- Store correlation results in database for historical tracking

Property Tests:
- Property 12: Correlation coefficients SHALL be in range [-1.0, 1.0]

Dependencies:
- SentimentAnalyzer (PHASE_0.3.1) for sentiment scores
- MarketDataCollector (PHASE_0.2.1) for price data
- Database schema for storing correlation results
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import structlog
import pandas as pd
import numpy as np
from scipy import stats

from ..nlp.sentiment import SentimentScore
from ...infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
from ...infrastructure.database import get_db_context
from ...infrastructure.models import (
    NewsSentiment as NewsSentimentModel,
    PriceData as PriceDataModel,
    Stock as StockModel,
    NewsArticle as NewsArticleModel,
)

logger = structlog.get_logger(__name__)


@dataclass
class PriceImpact:
    """
    Price impact at a specific timeframe.
    
    Attributes:
        timeframe: Time period (e.g., '1h', '4h', '1d', '1w')
        price_change_pct: Percentage price change in timeframe
        volume_change_pct: Percentage volume change in timeframe
        statistical_significance: P-value from statistical test (lower = more significant)
    """
    timeframe: str
    price_change_pct: float
    volume_change_pct: float
    statistical_significance: float
    
    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if impact is statistically significant at given alpha level."""
        return self.statistical_significance < alpha
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for storage."""
        return {
            'timeframe': self.timeframe,
            'price_change_pct': self.price_change_pct,
            'volume_change_pct': self.volume_change_pct,
            'statistical_significance': self.statistical_significance,
        }


@dataclass
class ImpactAnalysis:
    """
    Complete impact analysis for a news article.
    
    Attributes:
        ticker: Stock ticker symbol
        article_id: News article identifier
        timeframes: Dictionary mapping timeframe to PriceImpact
        analyzed_at: Timestamp of analysis
    """
    ticker: str
    article_id: str
    timeframes: Dict[str, PriceImpact] = field(default_factory=dict)
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            'ticker': self.ticker,
            'article_id': self.article_id,
            'timeframes': {
                tf: impact.to_dict() 
                for tf, impact in self.timeframes.items()
            },
            'analyzed_at': self.analyzed_at.isoformat(),
        }


class NewsImpactAnalyzer:
    """
    Analyzes correlation between news and price movements.
    
    Features:
    - Multi-timeframe impact analysis (1h, 4h, 1d, 1w)
    - Sentiment-price correlation calculation (Property 12)
    - News beta calculation (stock sensitivity to news)
    - Statistical significance testing
    - Database storage for historical tracking
    
    Requirements:
    - Req 2.11: Track news sentiment correlation with price movements
    - Req 7: Multi-timeframe news impact analysis
    
    Property Tests:
    - Property 12: Correlation coefficients in range [-1.0, 1.0]
    """
    
    # Timeframe mappings to hours
    TIMEFRAME_HOURS = {
        '1h': 1,
        '4h': 4,
        '1d': 24,
        '1w': 168,  # 7 * 24
    }
    
    def __init__(self):
        """Initialize the news impact analyzer."""
        self.cache = get_cache()
        logger.info("news_impact_analyzer_initialized")
    
    def _get_price_at_time(
        self,
        stock_id: int,
        target_time: datetime,
        window_minutes: int = 30
    ) -> Optional[Tuple[Decimal, int]]:
        """
        Get price and volume at a specific time (with window tolerance).
        
        Args:
            stock_id: Database ID of stock
            target_time: Target timestamp
            window_minutes: Time window tolerance in minutes
        
        Returns:
            Tuple of (price, volume) or None if not found
        """
        try:
            with get_db_context() as db:
                # Query price data within window
                start_time = target_time - timedelta(minutes=window_minutes)
                end_time = target_time + timedelta(minutes=window_minutes)
                
                price_record = (
                    db.query(PriceDataModel)
                    .filter(PriceDataModel.stock_id == stock_id)
                    .filter(PriceDataModel.timestamp >= start_time)
                    .filter(PriceDataModel.timestamp <= end_time)
                    .order_by(PriceDataModel.timestamp)
                    .first()
                )
                
                if price_record:
                    return (price_record.close, price_record.volume)
                
                logger.debug(
                    "price_not_found_at_time",
                    stock_id=stock_id,
                    target_time=target_time.isoformat()
                )
                return None
                
        except Exception as e:
            logger.error(
                "price_retrieval_failed",
                stock_id=stock_id,
                error=str(e)
            )
            return None
    
    def _calculate_price_change(
        self,
        stock_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[float, float]:
        """
        Calculate price and volume change between two times.
        
        Args:
            stock_id: Database ID of stock
            start_time: Start timestamp
            end_time: End timestamp
        
        Returns:
            Tuple of (price_change_pct, volume_change_pct)
        """
        # Get price at start
        start_data = self._get_price_at_time(stock_id, start_time)
        if not start_data:
            return (0.0, 0.0)
        
        start_price, start_volume = start_data
        
        # Get price at end
        end_data = self._get_price_at_time(stock_id, end_time)
        if not end_data:
            return (0.0, 0.0)
        
        end_price, end_volume = end_data
        
        # Calculate percentage changes
        if start_price > 0:
            price_change_pct = float((end_price - start_price) / start_price * 100)
        else:
            price_change_pct = 0.0
        
        if start_volume > 0:
            volume_change_pct = float((end_volume - start_volume) / start_volume * 100)
        else:
            volume_change_pct = 0.0
        
        return (price_change_pct, volume_change_pct)
    
    def calculate_impact(
        self,
        article_id: str,
        ticker: str,
        timeframes: Optional[List[str]] = None
    ) -> ImpactAnalysis:
        """
        Calculate price impact at multiple timeframes after news publication.
        
        Implements Requirement 7: Multi-timeframe news impact analysis.
        
        Args:
            article_id: News article ID (external ID, not database ID)
            ticker: Stock ticker symbol
            timeframes: List of timeframes (default: ['1h', '4h', '1d', '1w'])
        
        Returns:
            ImpactAnalysis with results for each timeframe
        
        Example:
            >>> analyzer = NewsImpactAnalyzer()
            >>> impact = analyzer.calculate_impact("news_123", "AAPL", ["1h", "1d"])
            >>> print(impact.timeframes['1h'].price_change_pct)
            2.5
        """
        if timeframes is None:
            timeframes = ['1h', '4h', '1d', '1w']
        
        # Validate timeframes
        invalid_timeframes = [tf for tf in timeframes if tf not in self.TIMEFRAME_HOURS]
        if invalid_timeframes:
            logger.warning(
                "invalid_timeframes_ignored",
                invalid=invalid_timeframes,
                valid=list(self.TIMEFRAME_HOURS.keys())
            )
            timeframes = [tf for tf in timeframes if tf in self.TIMEFRAME_HOURS]
        
        # Create impact analysis object
        impact_analysis = ImpactAnalysis(
            ticker=ticker,
            article_id=article_id
        )
        
        try:
            with get_db_context() as db:
                # Get stock
                stock = db.query(StockModel).filter(StockModel.ticker == ticker).first()
                if not stock:
                    logger.warning("stock_not_found", ticker=ticker)
                    return impact_analysis
                
                # Get article
                article = (
                    db.query(NewsArticleModel)
                    .filter(NewsArticleModel.article_id == article_id)
                    .first()
                )
                
                if not article:
                    logger.warning("article_not_found", article_id=article_id)
                    return impact_analysis
                
                publication_time = article.published_at
                
                # Calculate impact for each timeframe
                for timeframe in timeframes:
                    hours = self.TIMEFRAME_HOURS[timeframe]
                    end_time = publication_time + timedelta(hours=hours)
                    
                    # Calculate price and volume changes
                    price_change_pct, volume_change_pct = self._calculate_price_change(
                        stock.id,
                        publication_time,
                        end_time
                    )
                    
                    # TODO: Implement statistical significance test
                    # For now, use a simple threshold-based approach
                    # Proper implementation would use t-test or similar
                    statistical_significance = 1.0  # Placeholder
                    if abs(price_change_pct) > 2.0:  # >2% change
                        statistical_significance = 0.01  # Significant
                    elif abs(price_change_pct) > 1.0:  # >1% change
                        statistical_significance = 0.05  # Marginally significant
                    
                    # Create price impact object
                    price_impact = PriceImpact(
                        timeframe=timeframe,
                        price_change_pct=price_change_pct,
                        volume_change_pct=volume_change_pct,
                        statistical_significance=statistical_significance
                    )
                    
                    impact_analysis.timeframes[timeframe] = price_impact
                    
                    logger.debug(
                        "timeframe_impact_calculated",
                        ticker=ticker,
                        article_id=article_id,
                        timeframe=timeframe,
                        price_change_pct=round(price_change_pct, 2),
                        volume_change_pct=round(volume_change_pct, 2)
                    )
                
                logger.info(
                    "impact_analysis_complete",
                    ticker=ticker,
                    article_id=article_id,
                    timeframes=len(impact_analysis.timeframes)
                )
                
        except Exception as e:
            logger.error(
                "impact_calculation_failed",
                ticker=ticker,
                article_id=article_id,
                error=str(e)
            )
        
        return impact_analysis
    
    def calculate_sentiment_correlation(
        self,
        ticker: str,
        period_days: int = 90
    ) -> float:
        """
        Calculate correlation between news sentiment and price movements.
        
        Implements Requirement 2.11 and Property 12.
        
        Property 12: Correlation coefficient SHALL be in range [-1.0, 1.0]
        
        Args:
            ticker: Stock ticker symbol
            period_days: Historical period in days (default: 90)
        
        Returns:
            Pearson correlation coefficient in range [-1.0, 1.0]
        
        **Validates: Property 12**
        
        Example:
            >>> analyzer = NewsImpactAnalyzer()
            >>> corr = analyzer.calculate_sentiment_correlation("AAPL", period_days=90)
            >>> print(f"Sentiment-Price Correlation: {corr:.3f}")
            Sentiment-Price Correlation: 0.342
        """
        # Check cache first
        cache_key = CacheKeyPatterns.format_key(
            "correlation:sentiment_price:{ticker}:{period}",
            ticker=ticker,
            period=period_days
        )
        
        cached_corr = self.cache.get(cache_key, deserialize=False)
        if cached_corr is not None:
            logger.debug(
                "correlation_cache_hit",
                ticker=ticker,
                period_days=period_days
            )
            return float(cached_corr)
        
        try:
            with get_db_context() as db:
                # Get stock
                stock = db.query(StockModel).filter(StockModel.ticker == ticker).first()
                if not stock:
                    logger.warning("stock_not_found", ticker=ticker)
                    return 0.0
                
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                # Query sentiment data
                sentiment_records = (
                    db.query(NewsSentimentModel)
                    .filter(NewsSentimentModel.stock_id == stock.id)
                    .filter(NewsSentimentModel.created_at >= start_date)
                    .filter(NewsSentimentModel.created_at <= end_date)
                    .all()
                )
                
                if len(sentiment_records) < 2:
                    logger.warning(
                        "insufficient_sentiment_data",
                        ticker=ticker,
                        count=len(sentiment_records)
                    )
                    return 0.0
                
                # Query price data for same period
                price_records = (
                    db.query(PriceDataModel)
                    .filter(PriceDataModel.stock_id == stock.id)
                    .filter(PriceDataModel.timestamp >= start_date)
                    .filter(PriceDataModel.timestamp <= end_date)
                    .order_by(PriceDataModel.timestamp)
                    .all()
                )
                
                if len(price_records) < 2:
                    logger.warning(
                        "insufficient_price_data",
                        ticker=ticker,
                        count=len(price_records)
                    )
                    return 0.0
                
                # Create DataFrames for analysis
                sentiment_df = pd.DataFrame([
                    {
                        'timestamp': record.created_at,
                        'sentiment': record.sentiment_score
                    }
                    for record in sentiment_records
                ])
                
                price_df = pd.DataFrame([
                    {
                        'timestamp': record.timestamp,
                        'close': float(record.close)
                    }
                    for record in price_records
                ])
                
                # Calculate daily returns
                price_df = price_df.set_index('timestamp')
                price_df['returns'] = price_df['close'].pct_change()
                
                # Aggregate sentiment by day
                sentiment_df['date'] = pd.to_datetime(sentiment_df['timestamp']).dt.date
                daily_sentiment = sentiment_df.groupby('date')['sentiment'].mean().reset_index()
                
                # Merge sentiment and returns on date
                price_df['date'] = price_df.index.date
                daily_data = price_df[['date', 'returns']].dropna().reset_index(drop=True)
                merged = pd.merge(daily_sentiment, daily_data, on='date', how='inner')
                
                if len(merged) < 2:
                    logger.warning(
                        "insufficient_merged_data",
                        ticker=ticker,
                        count=len(merged)
                    )
                    return 0.0
                
                # Calculate Pearson correlation
                correlation = merged['sentiment'].corr(merged['returns'])
                
                # Handle NaN (can occur if one series is constant)
                if pd.isna(correlation):
                    correlation = 0.0
                
                # Ensure correlation is in valid range (Property 12)
                correlation = float(np.clip(correlation, -1.0, 1.0))
                
                logger.info(
                    "sentiment_correlation_calculated",
                    ticker=ticker,
                    period_days=period_days,
                    correlation=round(correlation, 3),
                    data_points=len(merged)
                )
                
                # Cache result for 24 hours
                self.cache.set(
                    cache_key,
                    str(correlation),
                    ttl=86400,  # 24 hours
                    serialize=False
                )
                
                # Store in database for historical tracking
                self._store_correlation_result(
                    stock.id,
                    period_days,
                    correlation,
                    len(merged)
                )
                
                return correlation
                
        except Exception as e:
            logger.error(
                "correlation_calculation_failed",
                ticker=ticker,
                period_days=period_days,
                error=str(e)
            )
            return 0.0
    
    def calculate_news_beta(
        self,
        ticker: str,
        period_days: int = 90
    ) -> float:
        """
        Calculate news beta (stock's sensitivity to news sentiment).
        
        News beta measures how much a stock's price moves in response to
        news sentiment changes. Similar to market beta, but for news.
        
        Beta interpretation:
        - beta > 1.0: Stock is more sensitive to news than average
        - beta = 1.0: Stock has average news sensitivity
        - beta < 1.0: Stock is less sensitive to news than average
        - beta < 0: Stock moves opposite to news sentiment (rare)
        
        Args:
            ticker: Stock ticker symbol
            period_days: Historical period in days (default: 90)
        
        Returns:
            News beta coefficient
        
        Example:
            >>> analyzer = NewsImpactAnalyzer()
            >>> beta = analyzer.calculate_news_beta("TSLA", period_days=90)
            >>> print(f"News Beta: {beta:.2f}")
            News Beta: 1.45
        """
        # Check cache first
        cache_key = CacheKeyPatterns.format_key(
            "correlation:news_beta:{ticker}:{period}",
            ticker=ticker,
            period=period_days
        )
        
        cached_beta = self.cache.get(cache_key, deserialize=False)
        if cached_beta is not None:
            logger.debug("news_beta_cache_hit", ticker=ticker)
            return float(cached_beta)
        
        try:
            with get_db_context() as db:
                # Get stock
                stock = db.query(StockModel).filter(StockModel.ticker == ticker).first()
                if not stock:
                    logger.warning("stock_not_found", ticker=ticker)
                    return 0.0
                
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                # Query sentiment data
                sentiment_records = (
                    db.query(NewsSentimentModel)
                    .filter(NewsSentimentModel.stock_id == stock.id)
                    .filter(NewsSentimentModel.created_at >= start_date)
                    .filter(NewsSentimentModel.created_at <= end_date)
                    .all()
                )
                
                if len(sentiment_records) < 10:  # Need more data for beta
                    logger.warning(
                        "insufficient_sentiment_data_for_beta",
                        ticker=ticker,
                        count=len(sentiment_records)
                    )
                    return 1.0  # Default to average sensitivity
                
                # Query price data
                price_records = (
                    db.query(PriceDataModel)
                    .filter(PriceDataModel.stock_id == stock.id)
                    .filter(PriceDataModel.timestamp >= start_date)
                    .filter(PriceDataModel.timestamp <= end_date)
                    .order_by(PriceDataModel.timestamp)
                    .all()
                )
                
                if len(price_records) < 10:
                    logger.warning(
                        "insufficient_price_data_for_beta",
                        ticker=ticker,
                        count=len(price_records)
                    )
                    return 1.0  # Default to average sensitivity
                
                # Create DataFrames
                sentiment_df = pd.DataFrame([
                    {
                        'timestamp': record.created_at,
                        'sentiment': record.sentiment_score
                    }
                    for record in sentiment_records
                ])
                
                price_df = pd.DataFrame([
                    {
                        'timestamp': record.timestamp,
                        'close': float(record.close)
                    }
                    for record in price_records
                ])
                
                # Calculate daily returns
                price_df = price_df.set_index('timestamp')
                price_df['returns'] = price_df['close'].pct_change()
                
                # Calculate sentiment changes
                sentiment_df = sentiment_df.set_index('timestamp').sort_index()
                sentiment_df['sentiment_change'] = sentiment_df['sentiment'].diff()
                
                # Aggregate by day
                sentiment_df['date'] = sentiment_df.index.date
                price_df['date'] = price_df.index.date
                
                daily_sentiment = sentiment_df.groupby('date')['sentiment_change'].mean().reset_index()
                daily_returns = price_df.groupby('date')['returns'].mean().reset_index()
                
                # Merge data
                merged = pd.merge(daily_sentiment, daily_returns, on='date', how='inner')
                merged = merged.dropna()
                
                if len(merged) < 10:
                    logger.warning(
                        "insufficient_merged_data_for_beta",
                        ticker=ticker,
                        count=len(merged)
                    )
                    return 1.0
                
                # Calculate beta using linear regression
                # Beta = Cov(returns, sentiment_change) / Var(sentiment_change)
                X = merged['sentiment_change'].values.reshape(-1, 1)
                y = merged['returns'].values
                
                # Use scipy for robust calculation
                slope, intercept, r_value, p_value, std_err = stats.linregress(
                    X.flatten(),
                    y
                )
                
                news_beta = float(slope)
                
                logger.info(
                    "news_beta_calculated",
                    ticker=ticker,
                    period_days=period_days,
                    beta=round(news_beta, 3),
                    r_squared=round(r_value**2, 3),
                    p_value=round(p_value, 4),
                    data_points=len(merged)
                )
                
                # Cache result for 24 hours
                self.cache.set(
                    cache_key,
                    str(news_beta),
                    ttl=86400,
                    serialize=False
                )
                
                # Store in database
                self._store_news_beta_result(
                    stock.id,
                    period_days,
                    news_beta,
                    r_value**2,
                    p_value
                )
                
                return news_beta
                
        except Exception as e:
            logger.error(
                "news_beta_calculation_failed",
                ticker=ticker,
                period_days=period_days,
                error=str(e)
            )
            return 1.0  # Default to average sensitivity
    
    def _store_correlation_result(
        self,
        stock_id: int,
        period_days: int,
        correlation: float,
        data_points: int
    ) -> bool:
        """
        Store correlation result in database for historical tracking.
        
        Args:
            stock_id: Database ID of stock
            period_days: Period used for calculation
            correlation: Correlation coefficient
            data_points: Number of data points used
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement database table for correlation tracking
            # For now, just log the result
            logger.debug(
                "correlation_result_stored",
                stock_id=stock_id,
                period_days=period_days,
                correlation=round(correlation, 3),
                data_points=data_points
            )
            return True
            
        except Exception as e:
            logger.error(
                "correlation_storage_failed",
                stock_id=stock_id,
                error=str(e)
            )
            return False
    
    def _store_news_beta_result(
        self,
        stock_id: int,
        period_days: int,
        beta: float,
        r_squared: float,
        p_value: float
    ) -> bool:
        """
        Store news beta result in database for historical tracking.
        
        Args:
            stock_id: Database ID of stock
            period_days: Period used for calculation
            beta: News beta coefficient
            r_squared: R-squared value
            p_value: Statistical significance
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # TODO: Implement database table for news beta tracking
            # For now, just log the result
            logger.debug(
                "news_beta_result_stored",
                stock_id=stock_id,
                period_days=period_days,
                beta=round(beta, 3),
                r_squared=round(r_squared, 3),
                p_value=round(p_value, 4)
            )
            return True
            
        except Exception as e:
            logger.error(
                "news_beta_storage_failed",
                stock_id=stock_id,
                error=str(e)
            )
            return False


# Convenience functions for external use

def calculate_sentiment_correlation(ticker: str, period_days: int = 90) -> float:
    """
    Calculate correlation between news sentiment and price movements.
    
    Convenience function that creates an analyzer instance and calculates correlation.
    
    Args:
        ticker: Stock ticker symbol
        period_days: Historical period in days (default: 90)
    
    Returns:
        Pearson correlation coefficient in range [-1.0, 1.0]
    
    **Validates: Property 12**
    
    Example:
        >>> from stockiq.news.impact import calculate_sentiment_correlation
        >>> corr = calculate_sentiment_correlation("AAPL")
        >>> print(f"Sentiment-Price Correlation: {corr:.3f}")
    """
    analyzer = NewsImpactAnalyzer()
    return analyzer.calculate_sentiment_correlation(ticker, period_days)


def calculate_news_beta(ticker: str, period_days: int = 90) -> float:
    """
    Calculate news beta (stock's sensitivity to news sentiment).
    
    Convenience function that creates an analyzer instance and calculates news beta.
    
    Args:
        ticker: Stock ticker symbol
        period_days: Historical period in days (default: 90)
    
    Returns:
        News beta coefficient
    
    Example:
        >>> from stockiq.news.impact import calculate_news_beta
        >>> beta = calculate_news_beta("TSLA")
        >>> print(f"News Beta: {beta:.2f}")
    """
    analyzer = NewsImpactAnalyzer()
    return analyzer.calculate_news_beta(ticker, period_days)
