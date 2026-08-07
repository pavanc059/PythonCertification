"""
Feature Engineering Module for Stock Analysis

This module provides comprehensive feature engineering capabilities for the ML pipeline,
including technical indicators, fundamental metrics, and sentiment features.

Requirements: 3.6, 13.1-13.3
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
        
    Returns:
        Series of RSI values (0-100)
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series, 
                   fast: int = 12, 
                   slow: int = 26, 
                   signal: int = 9) -> Dict[str, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        prices: Series of closing prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
        
    Returns:
        Dictionary with MACD line, signal line, and histogram
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'macd_signal': signal_line,
        'macd_histogram': histogram
    }


def calculate_bollinger_bands(prices: pd.Series, 
                               period: int = 20, 
                               std_dev: float = 2.0) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Args:
        prices: Series of closing prices
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
        
    Returns:
        Dictionary with upper band, middle band (SMA), and lower band
    """
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return {
        'bb_upper': upper_band,
        'bb_middle': sma,
        'bb_lower': lower_band,
        'bb_width': upper_band - lower_band
    }


def calculate_atr(high: pd.Series, 
                  low: pd.Series, 
                  close: pd.Series, 
                  period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: ATR period (default 14)
        
    Returns:
        Series of ATR values
    """
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV).
    
    Args:
        close: Series of closing prices
        volume: Series of volume data
        
    Returns:
        Series of OBV values
    """
    price_change = close.diff()
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if price_change.iloc[i] > 0:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif price_change.iloc[i] < 0:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def calculate_technical_features(price_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate comprehensive technical features from price data.
    
    This function implements all technical indicators required for the ML pipeline:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Bollinger Bands
    - ATR (Average True Range)
    - OBV (On-Balance Volume)
    - Moving Averages (SMA 20, 50, 200)
    - Momentum Indicators
    
    Args:
        price_data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        
    Returns:
        DataFrame with original data plus technical features
        
    Raises:
        ValueError: If required columns are missing from price_data
    """
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in price_data.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Create a copy to avoid modifying the original
    df = price_data.copy()
    
    # Calculate RSI
    df['rsi'] = calculate_rsi(df['Close'])
    
    # Calculate MACD
    macd_data = calculate_macd(df['Close'])
    df['macd'] = macd_data['macd']
    df['macd_signal'] = macd_data['macd_signal']
    df['macd_histogram'] = macd_data['macd_histogram']
    
    # Calculate Bollinger Bands
    bb_data = calculate_bollinger_bands(df['Close'])
    df['bb_upper'] = bb_data['bb_upper']
    df['bb_middle'] = bb_data['bb_middle']
    df['bb_lower'] = bb_data['bb_lower']
    df['bb_width'] = bb_data['bb_width']
    
    # Calculate ATR
    df['atr'] = calculate_atr(df['High'], df['Low'], df['Close'])
    
    # Calculate OBV
    df['obv'] = calculate_obv(df['Close'], df['Volume'])
    
    # Calculate Moving Averages
    df['sma_20'] = df['Close'].rolling(window=20).mean()
    df['sma_50'] = df['Close'].rolling(window=50).mean()
    df['sma_200'] = df['Close'].rolling(window=200).mean()
    
    # Calculate EMAs
    df['ema_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    
    # Calculate Momentum Indicators
    df['momentum'] = df['Close'] - df['Close'].shift(10)
    df['rate_of_change'] = ((df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10)) * 100
    
    # Price position relative to moving averages
    df['price_to_sma20'] = (df['Close'] - df['sma_20']) / df['sma_20']
    df['price_to_sma50'] = (df['Close'] - df['sma_50']) / df['sma_50']
    df['price_to_sma200'] = (df['Close'] - df['sma_200']) / df['sma_200']
    
    # Bollinger Band position
    df['bb_position'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Volume indicators
    df['volume_sma_20'] = df['Volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['Volume'] / df['volume_sma_20']
    
    # Volatility
    df['volatility'] = df['Close'].pct_change().rolling(window=20).std()
    
    # Price change features
    df['daily_return'] = df['Close'].pct_change()
    df['price_range'] = df['High'] - df['Low']
    df['price_range_pct'] = (df['High'] - df['Low']) / df['Close']
    
    logger.info(f"Calculated {len(df.columns) - len(required_columns)} technical features")
    
    return df


def calculate_fundamental_features(ticker: str) -> Dict[str, float]:
    """
    Extract fundamental features from company financial data.
    
    This function retrieves fundamental metrics including:
    - P/E ratio (Price-to-Earnings)
    - P/B ratio (Price-to-Book)
    - Debt-to-Equity ratio
    - ROE (Return on Equity)
    - And other key financial metrics
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        
    Returns:
        Dictionary with fundamental features
        
    Example:
        >>> features = calculate_fundamental_features('AAPL')
        >>> print(features['pe_ratio'])
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        features = {
            # Valuation ratios
            'pe_ratio': info.get('trailingPE', np.nan),
            'forward_pe': info.get('forwardPE', np.nan),
            'pb_ratio': info.get('priceToBook', np.nan),
            'ps_ratio': info.get('priceToSalesTrailing12Months', np.nan),
            'peg_ratio': info.get('pegRatio', np.nan),
            
            # Profitability metrics
            'roe': info.get('returnOnEquity', np.nan),
            'roa': info.get('returnOnAssets', np.nan),
            'profit_margin': info.get('profitMargins', np.nan),
            'operating_margin': info.get('operatingMargins', np.nan),
            
            # Financial health
            'debt_to_equity': info.get('debtToEquity', np.nan),
            'current_ratio': info.get('currentRatio', np.nan),
            'quick_ratio': info.get('quickRatio', np.nan),
            
            # Growth metrics
            'revenue_growth': info.get('revenueGrowth', np.nan),
            'earnings_growth': info.get('earningsGrowth', np.nan),
            
            # Dividend metrics
            'dividend_yield': info.get('dividendYield', np.nan),
            'payout_ratio': info.get('payoutRatio', np.nan),
            
            # Market metrics
            'market_cap': info.get('marketCap', np.nan),
            'enterprise_value': info.get('enterpriseValue', np.nan),
            'beta': info.get('beta', np.nan),
            
            # Other metrics
            'book_value': info.get('bookValue', np.nan),
            'price_to_book': info.get('priceToBook', np.nan),
            'shares_outstanding': info.get('sharesOutstanding', np.nan),
        }
        
        logger.info(f"Retrieved {len([v for v in features.values() if not pd.isna(v)])} fundamental features for {ticker}")
        return features
        
    except Exception as e:
        logger.error(f"Error retrieving fundamental features for {ticker}: {e}")
        # Return dictionary with NaN values if retrieval fails
        return {
            'pe_ratio': np.nan, 'forward_pe': np.nan, 'pb_ratio': np.nan,
            'ps_ratio': np.nan, 'peg_ratio': np.nan, 'roe': np.nan,
            'roa': np.nan, 'profit_margin': np.nan, 'operating_margin': np.nan,
            'debt_to_equity': np.nan, 'current_ratio': np.nan, 'quick_ratio': np.nan,
            'revenue_growth': np.nan, 'earnings_growth': np.nan,
            'dividend_yield': np.nan, 'payout_ratio': np.nan,
            'market_cap': np.nan, 'enterprise_value': np.nan, 'beta': np.nan,
            'book_value': np.nan, 'price_to_book': np.nan, 'shares_outstanding': np.nan,
        }


def calculate_sentiment_features(ticker: str, hours: int = 24) -> Dict[str, float]:
    """
    Calculate sentiment features from news and social media.
    
    This is a placeholder implementation that will be integrated with the
    News Analyzer module in a later phase. Currently returns default values.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        hours: Number of hours to look back for sentiment data (default 24)
        
    Returns:
        Dictionary with sentiment features:
        - average_sentiment: Mean sentiment score (-1 to 1)
        - sentiment_trend: Change in sentiment over time
        - news_volume: Number of news articles in time period
        - positive_ratio: Ratio of positive news
        - negative_ratio: Ratio of negative news
        
    Note:
        This function will be fully implemented when the News Analyzer module
        (stockiq.news) is integrated with the feature engineering pipeline.
    """
    # Placeholder implementation
    # TODO: Integrate with stockiq.news.nlp for real sentiment analysis
    
    logger.info(f"Sentiment features for {ticker} (placeholder - will be integrated with News Analyzer)")
    
    return {
        'average_sentiment': 0.0,  # Neutral sentiment
        'sentiment_trend': 0.0,    # No trend
        'news_volume': 0,          # No news articles
        'positive_ratio': 0.0,     # No positive news
        'negative_ratio': 0.0,     # No negative news
        'sentiment_volatility': 0.0,  # Sentiment stability
        'bullish_mentions': 0,     # Social media bullish mentions
        'bearish_mentions': 0,     # Social media bearish mentions
    }


def create_feature_matrix(ticker: str, lookback_days: int = 90) -> pd.DataFrame:
    """
    Create a comprehensive feature matrix combining technical, fundamental, and sentiment features.
    
    This function orchestrates the entire feature engineering pipeline:
    1. Retrieves historical price data
    2. Calculates technical indicators
    3. Adds fundamental metrics (broadcast to all rows)
    4. Adds sentiment features (placeholder for now)
    5. Handles missing values appropriately
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        lookback_days: Number of days of historical data to retrieve (default 90)
        
    Returns:
        DataFrame with complete feature matrix ready for ML pipeline
        
    Example:
        >>> features = create_feature_matrix('AAPL', lookback_days=90)
        >>> print(features.columns)
        >>> print(features.shape)
        
    Raises:
        ValueError: If ticker is invalid or data retrieval fails
    """
    try:
        # Retrieve historical price data
        logger.info(f"Fetching {lookback_days} days of historical data for {ticker}")
        stock = yf.Ticker(ticker)
        
        # Add buffer days to account for indicator calculations
        # (e.g., SMA 200 needs 200 days of history)
        buffer_days = 250  # ~1 year for SMA 200
        total_days = lookback_days + buffer_days
        
        price_data = stock.history(period=f"{total_days}d")
        
        if price_data.empty:
            raise ValueError(f"No price data available for ticker: {ticker}")
        
        # Calculate technical features
        logger.info("Calculating technical features...")
        df = calculate_technical_features(price_data)
        
        # Calculate fundamental features (same for all rows)
        logger.info("Calculating fundamental features...")
        fundamental_features = calculate_fundamental_features(ticker)
        
        # Add fundamental features as columns
        for feature_name, feature_value in fundamental_features.items():
            df[f'fund_{feature_name}'] = feature_value
        
        # Calculate sentiment features (placeholder)
        logger.info("Calculating sentiment features...")
        sentiment_features = calculate_sentiment_features(ticker)
        
        # Add sentiment features as columns
        for feature_name, feature_value in sentiment_features.items():
            df[f'sent_{feature_name}'] = feature_value
        
        # Handle missing values
        logger.info("Handling missing values...")
        
        # Forward fill technical indicators (carry forward last known value)
        technical_cols = [col for col in df.columns if not col.startswith(('fund_', 'sent_'))]
        df[technical_cols] = df[technical_cols].ffill()
        
        # Backward fill any remaining NaNs at the start of the series
        df[technical_cols] = df[technical_cols].bfill()
        
        # For fundamental features, interpolate or use forward fill
        fundamental_cols = [col for col in df.columns if col.startswith('fund_')]
        df[fundamental_cols] = df[fundamental_cols].ffill()
        
        # Sentiment features already have default values (0.0)
        
        # Keep only the requested lookback period (remove buffer days)
        df = df.tail(lookback_days)
        
        # Add target variable for ML (next day return)
        df['target_return'] = df['Close'].shift(-1) / df['Close'] - 1
        df['target_direction'] = (df['target_return'] > 0).astype(int)
        
        logger.info(f"Feature matrix created: {df.shape[0]} rows x {df.shape[1]} columns")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error creating feature matrix for {ticker}: {e}")
        raise ValueError(f"Failed to create feature matrix for {ticker}: {str(e)}")


# Convenience function for batch processing
def create_feature_matrices(tickers: list, lookback_days: int = 90) -> Dict[str, pd.DataFrame]:
    """
    Create feature matrices for multiple tickers.
    
    Args:
        tickers: List of stock ticker symbols
        lookback_days: Number of days of historical data to retrieve
        
    Returns:
        Dictionary mapping ticker to feature DataFrame
        
    Example:
        >>> tickers = ['AAPL', 'GOOGL', 'MSFT']
        >>> features_dict = create_feature_matrices(tickers)
        >>> print(features_dict['AAPL'].head())
    """
    results = {}
    
    for ticker in tickers:
        try:
            logger.info(f"Processing {ticker}...")
            results[ticker] = create_feature_matrix(ticker, lookback_days)
        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}")
            # Continue with other tickers
            continue
    
    logger.info(f"Successfully processed {len(results)}/{len(tickers)} tickers")
    return results


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)
    
    print("Feature Engineering Module - Example Usage\n")
    
    # Test with a single ticker
    ticker = "AAPL"
    print(f"Creating feature matrix for {ticker}...")
    
    try:
        features = create_feature_matrix(ticker, lookback_days=30)
        print(f"\nFeature matrix shape: {features.shape}")
        print(f"\nColumns ({len(features.columns)}):")
        print(features.columns.tolist())
        print(f"\nLast 5 rows:")
        print(features.tail())
        print(f"\nMissing values:")
        print(features.isnull().sum().sum())
    except Exception as e:
        print(f"Error: {e}")
