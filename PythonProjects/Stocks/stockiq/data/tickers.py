"""
Ticker management and S&P 500 ticker list

This module provides ticker validation and access to major stock index constituents.
"""

from typing import List, Optional


# S&P 500 representative tickers (top companies by market cap)
# This is a curated list for demonstration. In production, this would be loaded
# from a database or API.
SP500_TICKERS = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "ORCL", "CSCO",
    "AMD", "INTC", "CRM", "ADBE", "ACN", "TXN", "QCOM", "AMAT", "INTU", "IBM",
    
    # Healthcare
    "JNJ", "UNH", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "CVS", "CI", "ELV", "HUM", "ISRG", "VRTX", "REGN", "ZTS",
    
    # Financial Services
    "BRK.B", "JPM", "V", "MA", "BAC", "WFC", "MS", "GS", "AXP", "SPGI",
    "BLK", "C", "SCHW", "CB", "PGR", "MMC", "AON", "ICE", "CME", "COF",
    
    # Consumer Cyclical
    "HD", "MCD", "NKE", "SBUX", "LOW", "TGT", "BKNG", "TJX", "MAR", "GM",
    "F", "CMG", "ORLY", "YUM", "AZO", "DPZ", "ULTA", "RCL", "HLT", "DHI",
    
    # Communication Services
    "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "TTWO", "MTCH",
    
    # Industrial
    "UPS", "HON", "BA", "CAT", "RTX", "LMT", "GE", "UNP", "DE", "MMM",
    "FDX", "NOC", "GD", "WM", "EMR", "ITW", "CSX", "NSC", "ETN", "PH",
    
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "WMB",
    
    # Consumer Defensive
    "WMT", "PG", "KO", "PEP", "COST", "PM", "MO", "CL", "MDLZ", "GIS",
    "KMB", "KHC", "SYY", "HSY", "K", "CAG", "CPB", "HRL", "MKC", "TSN",
    
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ES",
    
    # Real Estate
    "PLD", "AMT", "EQIX", "PSA", "SPG", "WELL", "DLR", "O", "VICI", "AVB",
    
    # Materials
    "LIN", "APD", "ECL", "SHW", "FCX", "NEM", "DD", "DOW", "ALB", "VMC",
]


def get_sp500_tickers() -> List[str]:
    """
    Return a list of S&P 500 tickers.
    
    Returns:
        List of ticker symbols as strings
    """
    return SP500_TICKERS.copy()


def get_major_tickers(limit: Optional[int] = None) -> List[str]:
    """
    Return a list of major stock tickers.
    
    Args:
        limit: Maximum number of tickers to return (default: all)
    
    Returns:
        List of ticker symbols
    """
    tickers = get_sp500_tickers()
    if limit:
        return tickers[:limit]
    return tickers


def validate_ticker(ticker: str) -> bool:
    """
    Validate if a ticker symbol is in the SP500 list.
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        True if ticker is valid, False otherwise
    """
    return ticker.upper() in SP500_TICKERS


def get_tickers_by_sector(sector: str) -> List[str]:
    """
    Get tickers by sector (simplified implementation).
    
    Args:
        sector: Sector name (Technology, Healthcare, Financial Services, etc.)
    
    Returns:
        List of tickers in that sector
    """
    # Simplified mapping - in production this would query the database
    sector_map = {
        "Technology": SP500_TICKERS[0:20],
        "Healthcare": SP500_TICKERS[20:40],
        "Financial Services": SP500_TICKERS[40:60],
        "Consumer Cyclical": SP500_TICKERS[60:80],
        "Communication Services": SP500_TICKERS[80:90],
        "Industrial": SP500_TICKERS[90:110],
        "Energy": SP500_TICKERS[110:120],
        "Consumer Defensive": SP500_TICKERS[120:140],
        "Utilities": SP500_TICKERS[140:150],
        "Real Estate": SP500_TICKERS[150:160],
        "Materials": SP500_TICKERS[160:170],
    }
    
    return sector_map.get(sector, [])
