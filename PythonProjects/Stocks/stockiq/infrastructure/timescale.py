"""
TimescaleDB continuous aggregate query utilities.

This module provides efficient query functions for accessing pre-computed
OHLCV rollups at different time granularities (1m, 5m, 1h, 1d).

The continuous aggregates enable sub-200ms query performance for 5-year
time spans (Requirement 12.5).
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

import pandas as pd
from sqlalchemy import text
import structlog

from stockiq.infrastructure.database import get_engine

logger = structlog.get_logger(__name__)


# Time interval to aggregate mapping
AGGREGATE_VIEWS = {
    '1m': 'price_data_1min',
    '1min': 'price_data_1min',
    '5m': 'price_data_5min',
    '5min': 'price_data_5min',
    '1h': 'price_data_1hour',
    '1hour': 'price_data_1hour',
    '1d': 'price_data_1day',
    '1day': 'price_data_1day',
    'daily': 'price_data_1day',
}


def get_ohlcv_data(
    ticker: str,
    start_time: datetime,
    end_time: datetime,
    interval: str = '1d'
) -> pd.DataFrame:
    """
    Query OHLCV data from continuous aggregates for optimal performance.
    
    Automatically selects the appropriate continuous aggregate based on the
    requested interval to achieve sub-200ms query times for 5-year spans.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        start_time: Start of time range (inclusive)
        end_time: End of time range (inclusive)
        interval: Time interval ('1m', '5m', '1h', '1d')
    
    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume, num_trades
    
    Raises:
        ValueError: If interval is not supported
    """
    if interval not in AGGREGATE_VIEWS:
        raise ValueError(
            f"Unsupported interval: {interval}. "
            f"Supported intervals: {', '.join(AGGREGATE_VIEWS.keys())}"
        )
    
    view_name = AGGREGATE_VIEWS[interval]
    engine = get_engine()
    
    query = text(f"""
        SELECT 
            ca.bucket as timestamp,
            ca.open,
            ca.high,
            ca.low,
            ca.close,
            ca.volume,
            ca.num_trades
        FROM {view_name} ca
        JOIN stocks s ON s.id = ca.stock_id
        WHERE s.ticker = :ticker
          AND ca.bucket >= :start_time
          AND ca.bucket <= :end_time
        ORDER BY ca.bucket ASC
    """)
    
    try:
        start = datetime.now()
        
        with engine.connect() as conn:
            result = conn.execute(
                query,
                {
                    'ticker': ticker,
                    'start_time': start_time,
                    'end_time': end_time
                }
            )
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        elapsed = (datetime.now() - start).total_seconds() * 1000
        logger.info(
            "ohlcv_query_completed",
            ticker=ticker,
            interval=interval,
            rows=len(df),
            elapsed_ms=f"{elapsed:.1f}"
        )
        
        return df
        
    except Exception as e:
        logger.error(
            "ohlcv_query_failed",
            ticker=ticker,
            interval=interval,
            error=str(e)
        )
        raise


def get_ohlcv_data_multi_ticker(
    tickers: List[str],
    start_time: datetime,
    end_time: datetime,
    interval: str = '1d'
) -> Dict[str, pd.DataFrame]:
    """
    Query OHLCV data for multiple tickers from continuous aggregates.
    
    This is more efficient than calling get_ohlcv_data() multiple times
    as it uses a single query with JOIN.
    
    Args:
        tickers: List of stock ticker symbols
        start_time: Start of time range (inclusive)
        end_time: End of time range (inclusive)
        interval: Time interval ('1m', '5m', '1h', '1d')
    
    Returns:
        Dictionary mapping ticker -> DataFrame
    """
    if interval not in AGGREGATE_VIEWS:
        raise ValueError(
            f"Unsupported interval: {interval}. "
            f"Supported intervals: {', '.join(AGGREGATE_VIEWS.keys())}"
        )
    
    view_name = AGGREGATE_VIEWS[interval]
    engine = get_engine()
    
    query = text(f"""
        SELECT 
            s.ticker,
            ca.bucket as timestamp,
            ca.open,
            ca.high,
            ca.low,
            ca.close,
            ca.volume,
            ca.num_trades
        FROM {view_name} ca
        JOIN stocks s ON s.id = ca.stock_id
        WHERE s.ticker = ANY(:tickers)
          AND ca.bucket >= :start_time
          AND ca.bucket <= :end_time
        ORDER BY s.ticker, ca.bucket ASC
    """)
    
    try:
        start = datetime.now()
        
        with engine.connect() as conn:
            result = conn.execute(
                query,
                {
                    'tickers': tickers,
                    'start_time': start_time,
                    'end_time': end_time
                }
            )
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        # Split by ticker
        result_dict = {}
        for ticker in tickers:
            ticker_df = df[df['ticker'] == ticker].drop(columns=['ticker']).reset_index(drop=True)
            result_dict[ticker] = ticker_df
        
        elapsed = (datetime.now() - start).total_seconds() * 1000
        logger.info(
            "multi_ticker_ohlcv_query_completed",
            tickers=tickers,
            interval=interval,
            total_rows=len(df),
            elapsed_ms=f"{elapsed:.1f}"
        )
        
        return result_dict
        
    except Exception as e:
        logger.error(
            "multi_ticker_ohlcv_query_failed",
            tickers=tickers,
            interval=interval,
            error=str(e)
        )
        raise


def get_latest_ohlcv(ticker: str, interval: str = '1d', limit: int = 100) -> pd.DataFrame:
    """
    Query the most recent OHLCV data from continuous aggregates.
    
    Args:
        ticker: Stock ticker symbol
        interval: Time interval ('1m', '5m', '1h', '1d')
        limit: Maximum number of records to return
    
    Returns:
        DataFrame with latest OHLCV data
    """
    if interval not in AGGREGATE_VIEWS:
        raise ValueError(
            f"Unsupported interval: {interval}. "
            f"Supported intervals: {', '.join(AGGREGATE_VIEWS.keys())}"
        )
    
    view_name = AGGREGATE_VIEWS[interval]
    engine = get_engine()
    
    query = text(f"""
        SELECT 
            ca.bucket as timestamp,
            ca.open,
            ca.high,
            ca.low,
            ca.close,
            ca.volume,
            ca.num_trades
        FROM {view_name} ca
        JOIN stocks s ON s.id = ca.stock_id
        WHERE s.ticker = :ticker
        ORDER BY ca.bucket DESC
        LIMIT :limit
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {'ticker': ticker, 'limit': limit})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        # Reverse to get chronological order
        df = df.iloc[::-1].reset_index(drop=True)
        
        logger.info(
            "latest_ohlcv_query_completed",
            ticker=ticker,
            interval=interval,
            rows=len(df)
        )
        
        return df
        
    except Exception as e:
        logger.error(
            "latest_ohlcv_query_failed",
            ticker=ticker,
            interval=interval,
            error=str(e)
        )
        raise


def get_aggregate_statistics(interval: str = '1d') -> Dict[str, Any]:
    """
    Get statistics about a continuous aggregate view.
    
    Returns information like number of rows, date range, update status.
    
    Args:
        interval: Time interval to check
    
    Returns:
        Dictionary with aggregate statistics
    """
    if interval not in AGGREGATE_VIEWS:
        raise ValueError(
            f"Unsupported interval: {interval}. "
            f"Supported intervals: {', '.join(AGGREGATE_VIEWS.keys())}"
        )
    
    view_name = AGGREGATE_VIEWS[interval]
    engine = get_engine()
    
    query = text(f"""
        SELECT
            COUNT(*) as total_rows,
            COUNT(DISTINCT stock_id) as num_stocks,
            MIN(bucket) as earliest_data,
            MAX(bucket) as latest_data,
            pg_size_pretty(pg_total_relation_size('{view_name}')) as total_size
        FROM {view_name}
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
            
            stats = {
                'view_name': view_name,
                'interval': interval,
                'total_rows': row[0],
                'num_stocks': row[1],
                'earliest_data': row[2],
                'latest_data': row[3],
                'total_size': row[4]
            }
            
            logger.info("aggregate_statistics_retrieved", **stats)
            return stats
            
    except Exception as e:
        logger.error("failed_to_get_aggregate_statistics", interval=interval, error=str(e))
        raise


def refresh_continuous_aggregate(interval: str) -> None:
    """
    Manually refresh a continuous aggregate view.
    
    This forces an immediate refresh rather than waiting for the scheduled
    refresh policy to run.
    
    Args:
        interval: Time interval to refresh
    """
    if interval not in AGGREGATE_VIEWS:
        raise ValueError(
            f"Unsupported interval: {interval}. "
            f"Supported intervals: {', '.join(AGGREGATE_VIEWS.keys())}"
        )
    
    view_name = AGGREGATE_VIEWS[interval]
    engine = get_engine()
    
    try:
        logger.info("refreshing_continuous_aggregate", view_name=view_name)
        
        with engine.connect() as conn:
            # Refresh the entire aggregate
            conn.execute(text(f"""
                CALL refresh_continuous_aggregate('{view_name}', NULL, NULL);
            """))
            conn.commit()
        
        logger.info("continuous_aggregate_refreshed", view_name=view_name)
        
    except Exception as e:
        logger.error(
            "failed_to_refresh_continuous_aggregate",
            view_name=view_name,
            error=str(e)
        )
        raise


def benchmark_query_performance(ticker: str = 'AAPL') -> Dict[str, float]:
    """
    Benchmark query performance across all continuous aggregate intervals.
    
    Queries 5 years of data for each interval and measures query time.
    Should achieve sub-200ms for all intervals (Requirement 12.5).
    
    Args:
        ticker: Stock ticker to benchmark with
    
    Returns:
        Dictionary mapping interval -> query time in milliseconds
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=5*365)  # 5 years
    
    results = {}
    
    for interval in ['1d', '1h', '5m', '1m']:
        try:
            start = datetime.now()
            df = get_ohlcv_data(ticker, start_time, end_time, interval)
            elapsed_ms = (datetime.now() - start).total_seconds() * 1000
            
            results[interval] = {
                'elapsed_ms': elapsed_ms,
                'rows': len(df),
                'meets_requirement': elapsed_ms < 200
            }
            
            logger.info(
                "benchmark_result",
                interval=interval,
                elapsed_ms=f"{elapsed_ms:.1f}",
                rows=len(df),
                meets_requirement=elapsed_ms < 200
            )
            
        except Exception as e:
            logger.error("benchmark_failed", interval=interval, error=str(e))
            results[interval] = {
                'elapsed_ms': None,
                'rows': 0,
                'meets_requirement': False,
                'error': str(e)
            }
    
    return results
