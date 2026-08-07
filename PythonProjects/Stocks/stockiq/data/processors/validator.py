"""
Data validation for quality checks.
"""

from typing import List
from datetime import datetime
import pandas as pd
import structlog

from ..models import OHLCV, ValidationResult, NewsArticle

logger = structlog.get_logger(__name__)


class DataValidator:
    """Validates data quality and consistency."""
    
    @staticmethod
    def validate_price_data(data: List[OHLCV]) -> ValidationResult:
        """
        Validate price data for anomalies, missing values, and outliers.
        
        Checks:
        - Property 26: OHLC consistency (H >= max(O,C), L <= min(O,C))
        - Property 27: Timestamp ordering (strictly ascending)
        - Property 28: Volume non-negativity
        - Missing values
        - Outliers (price changes > 50%)
        
        Args:
            data: List of OHLCV objects
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not data:
            result.add_error("No data provided")
            return result
        
        # Check timestamp ordering (Property 27)
        timestamps = [d.timestamp for d in data]
        if timestamps != sorted(timestamps):
            result.add_error("Timestamps are not in ascending order")
        
        # Check for duplicate timestamps (Property 27)
        if len(timestamps) != len(set(timestamps)):
            result.add_error("Duplicate timestamps found")
        
        # Validate each OHLCV record
        for i, ohlcv in enumerate(data):
            try:
                # OHLC consistency is checked in OHLCV.__post_init__
                # Volume non-negativity is checked in OHLCV.__post_init__
                pass
            except ValueError as e:
                result.add_error(f"Record {i}: {str(e)}")
        
        # Check for outliers
        if len(data) > 1:
            for i in range(1, len(data)):
                prev = data[i-1]
                curr = data[i]
                
                pct_change = abs(
                    ((curr.close - prev.close) / prev.close) * 100
                )
                
                if pct_change > 50:
                    result.add_warning(
                        f"Large price change detected: {pct_change:.2f}% "
                        f"at {curr.timestamp}"
                    )
        
        # Check for missing values (gaps in time series)
        if len(data) > 1:
            for i in range(1, len(data)):
                time_diff = (data[i].timestamp - data[i-1].timestamp).total_seconds()
                expected_diff = 86400  # 1 day in seconds
                
                if time_diff > expected_diff * 1.5:
                    result.add_warning(
                        f"Gap in time series detected: "
                        f"{time_diff / 86400:.1f} days between "
                        f"{data[i-1].timestamp} and {data[i].timestamp}"
                    )
        
        logger.info(
            "price_data_validated",
            records=len(data),
            errors=len(result.errors),
            warnings=len(result.warnings)
        )
        
        return result
    
    @staticmethod
    def validate_news_data(article: NewsArticle) -> ValidationResult:
        """
        Validate news article data.
        
        Checks:
        - Required fields present
        - Valid timestamps
        - URL format
        
        Args:
            article: NewsArticle object
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check required fields
        if not article.id:
            result.add_error("Article ID is missing")
        
        if not article.title:
            result.add_error("Article title is missing")
        
        if not article.content:
            result.add_warning("Article content is empty")
        
        if not article.source:
            result.add_error("Article source is missing")
        
        if not article.url:
            result.add_warning("Article URL is missing")
        
        # Validate timestamp
        if article.published_at > datetime.utcnow():
            result.add_error("Article published_at is in the future")
        
        # Validate URL format
        if article.url and not article.url.startswith(('http://', 'https://')):
            result.add_warning("Article URL does not start with http:// or https://")
        
        # Check for tickers
        if not article.tickers:
            result.add_warning("No tickers extracted from article")
        
        logger.debug(
            "news_data_validated",
            article_id=article.id,
            errors=len(result.errors),
            warnings=len(result.warnings)
        )
        
        return result
    
    @staticmethod
    def detect_anomalies(data: List[OHLCV]) -> List[int]:
        """
        Detect anomalies in price data using statistical methods.
        
        Args:
            data: List of OHLCV objects
        
        Returns:
            List of indices where anomalies were detected
        """
        if len(data) < 10:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'timestamp': d.timestamp,
                'close': float(d.close),
                'volume': d.volume
            }
            for d in data
        ])
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Detect outliers using IQR method
        Q1 = df['returns'].quantile(0.25)
        Q3 = df['returns'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR
        
        anomalies = df[
            (df['returns'] < lower_bound) | (df['returns'] > upper_bound)
        ].index.tolist()
        
        if anomalies:
            logger.warning("anomalies_detected", count=len(anomalies))
        
        return anomalies
