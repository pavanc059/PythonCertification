"""
Technical Indicators Module

Calculation functions for 10+ technical indicators that can be overlayed
on price charts.

Requirement 18.3: Support for at least 10 technical indicator overlays
"""

from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# List of all available indicators
AVAILABLE_INDICATORS = [
    "SMA_20", "SMA_50", "SMA_200",
    "EMA_12", "EMA_26", "EMA_50",
    "BB",  # Bollinger Bands
    "RSI",
    "MACD",
    "ATR",
    "Stochastic",
    "OBV",
    "ADX",
    "CCI",
]


def calculate_sma(prices: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        prices: Series of closing prices
        period: Number of periods for average
    
    Returns:
        Series of SMA values
    """
    return prices.rolling(window=period, min_periods=1).mean()


def calculate_ema(prices: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        prices: Series of closing prices
        period: Number of periods for average
    
    Returns:
        Series of EMA values
    """
    return prices.ewm(span=period, adjust=False, min_periods=1).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    
    Args:
        prices: Series of closing prices
        period: Number of periods for RSI calculation
    
    Returns:
        Series of RSI values (0-100)
    """
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate average gain and loss
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal)
    Histogram = MACD Line - Signal Line
    
    Args:
        prices: Series of closing prices
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
    
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Middle Band = SMA(period)
    Upper Band = Middle Band + (std_dev * standard deviation)
    Lower Band = Middle Band - (std_dev * standard deviation)
    
    Args:
        prices: Series of closing prices
        period: Number of periods for SMA
        std_dev: Number of standard deviations for bands
    
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle_band = calculate_sma(prices, period)
    rolling_std = prices.rolling(window=period, min_periods=1).std()
    
    upper_band = middle_band + (rolling_std * std_dev)
    lower_band = middle_band - (rolling_std * std_dev)
    
    return upper_band, middle_band, lower_band


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Calculate Average True Range.
    
    True Range = max(High - Low, abs(High - Previous Close), abs(Low - Previous Close))
    ATR = SMA(True Range, period)
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Number of periods for ATR
    
    Returns:
        Series of ATR values
    """
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period, min_periods=1).mean()
    
    return atr


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator.
    
    %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = SMA(%K, d_period)
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        k_period: Number of periods for %K
        d_period: Number of periods for %D
    
    Returns:
        Tuple of (%K, %D)
    """
    lowest_low = low.rolling(window=k_period, min_periods=1).min()
    highest_high = high.rolling(window=k_period, min_periods=1).max()
    
    k = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    d = k.rolling(window=d_period, min_periods=1).mean()
    
    return k, d


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On-Balance Volume.
    
    OBV increases by volume on up days, decreases by volume on down days.
    
    Args:
        close: Series of closing prices
        volume: Series of volume data
    
    Returns:
        Series of OBV values
    """
    price_change = close.diff()
    
    # Add volume on up days, subtract on down days
    obv_change = volume.where(price_change > 0, -volume)
    obv_change = obv_change.where(price_change != 0, 0)
    
    obv = obv_change.cumsum()
    
    return obv


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Calculate Average Directional Index.
    
    ADX measures trend strength on a scale of 0-100.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Number of periods for ADX
    
    Returns:
        Series of ADX values (0-100)
    """
    # Calculate +DM and -DM
    high_diff = high.diff()
    low_diff = -low.diff()
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    # Calculate True Range
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate smoothed +DI and -DI
    atr = true_range.rolling(window=period, min_periods=1).mean()
    plus_di = 100 * (plus_dm.rolling(window=period, min_periods=1).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period, min_periods=1).mean() / atr)
    
    # Calculate DX and ADX
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=period, min_periods=1).mean()
    
    return adx


def calculate_cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20,
    constant: float = 0.015,
) -> pd.Series:
    """
    Calculate Commodity Channel Index.
    
    CCI = (Typical Price - SMA(Typical Price)) / (constant * Mean Deviation)
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        period: Number of periods for CCI
        constant: Scaling constant (default 0.015)
    
    Returns:
        Series of CCI values
    """
    # Calculate typical price
    typical_price = (high + low + close) / 3
    
    # Calculate SMA of typical price
    sma_tp = typical_price.rolling(window=period, min_periods=1).mean()
    
    # Calculate mean deviation
    mean_dev = (typical_price - sma_tp).abs().rolling(window=period, min_periods=1).mean()
    
    # Calculate CCI
    cci = (typical_price - sma_tp) / (constant * mean_dev)
    
    return cci


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    Calculate Volume Weighted Average Price.
    
    VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        volume: Series of volume data
    
    Returns:
        Series of VWAP values
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    
    return vwap


def calculate_ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_span_b_period: int = 52,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculate Ichimoku Cloud components.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of closing prices
        tenkan_period: Conversion line period
        kijun_period: Base line period
        senkou_span_b_period: Leading span B period
    
    Returns:
        Tuple of (tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span)
    """
    # Tenkan-sen (Conversion Line)
    tenkan_high = high.rolling(window=tenkan_period, min_periods=1).max()
    tenkan_low = low.rolling(window=tenkan_period, min_periods=1).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2
    
    # Kijun-sen (Base Line)
    kijun_high = high.rolling(window=kijun_period, min_periods=1).max()
    kijun_low = low.rolling(window=kijun_period, min_periods=1).min()
    kijun_sen = (kijun_high + kijun_low) / 2
    
    # Senkou Span A (Leading Span A)
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
    
    # Senkou Span B (Leading Span B)
    senkou_high = high.rolling(window=senkou_span_b_period, min_periods=1).max()
    senkou_low = low.rolling(window=senkou_span_b_period, min_periods=1).min()
    senkou_span_b = ((senkou_high + senkou_low) / 2).shift(kijun_period)
    
    # Chikou Span (Lagging Span)
    chikou_span = close.shift(-kijun_period)
    
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span
