"""
Market data collector using yfinance.

This module implements the MarketDataCollector class with the following features:
- Real-time and historical price data collection
- Rate limiting (2000 req/hour for yfinance)
- Retry logic with exponential backoff (3 attempts)
- Data validation (Properties 26, 27, 28)
- Redis caching (5-minute TTL for prices)

Properties validated:
- Property 26: OHLC price consistency (H >= max(O,C), L <= min(O,C))
- Property 27: Timestamp ordering (strictly ascending, no duplicates)
- Property 28: Volume non-negativity (volume >= 0)
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
import yfinance as yf
import pandas as pd
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import Price, OHLCV, Stock
from ...infrastructure.config import get_settings
from ...infrastructure.cache import get_cache, CacheKeyPatterns
from ..processors.validator import DataValidator

logger = structlog.get_logger(__name__)


class MarketDataCollector:
    """Collects real-time and historical market data using yfinance."""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self._rate_limit_key = "ratelimit:yfinance"
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        count = self.cache.get(self._rate_limit_key, deserialize=False)
        if count is None:
            return True
        
        limit = self.settings.yfinance_rate_limit
        return int(count) < int(limit * 0.8)  # Stay at 80% of limit
    
    def _increment_rate_limit(self):
        """Increment rate limit counter."""
        count = self.cache.increment(self._rate_limit_key)
        if count == 1:
            # Set expiration on first increment (1 hour window)
            self.cache.expire(self._rate_limit_key, 3600)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_realtime_price(self, ticker: str) -> Optional[Price]:
        """
        Get current real-time price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Price object or None if not available
        """
        # Check cache first
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_LATEST,
            ticker=ticker
        )
        
        cached_price = self.cache.get(cache_key)
        if cached_price:
            logger.debug("price_cache_hit", ticker=ticker)
            return cached_price
        
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("rate_limit_approached", ticker=ticker)
            return None
        
        try:
            self._increment_rate_limit()
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info or 'currentPrice' not in info:
                logger.warning("price_not_available", ticker=ticker)
                return None
            
            price = Price(
                ticker=ticker,
                timestamp=datetime.utcnow(),
                price=Decimal(str(info.get('currentPrice', 0))),
                volume=info.get('volume', 0),
                bid=Decimal(str(info.get('bid', 0))) if info.get('bid') else None,
                ask=Decimal(str(info.get('ask', 0))) if info.get('ask') else None,
            )
            
            # Cache for 5 minutes
            self.cache.set(
                cache_key,
                price,
                ttl=self.settings.price_cache_ttl
            )
            
            logger.info("price_fetched", ticker=ticker, price=float(price.price))
            return price
            
        except Exception as e:
            logger.error("price_fetch_failed", ticker=ticker, error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_historical_data(
        self,
        ticker: str,
        start: date,
        end: date,
        interval: str = "1d"
    ) -> List[OHLCV]:
        """
        Get historical OHLCV data for a ticker with validation.
        
        Validates:
        - Property 26: OHLC consistency (validated in OHLCV.__post_init__)
        - Property 27: Timestamp ordering (validated after fetching)
        - Property 28: Volume non-negativity (validated in OHLCV.__post_init__)
        
        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date
            interval: Data interval (1d, 1h, 5m, etc.)
        
        Returns:
            List of OHLCV objects
        """
        # Check cache
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_HISTORY,
            ticker=ticker,
            timeframe=f"{start}_{end}_{interval}"
        )
        
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.debug("historical_data_cache_hit", ticker=ticker)
            return cached_data
        
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("rate_limit_approached", ticker=ticker)
            return []
        
        try:
            self._increment_rate_limit()
            
            stock = yf.Ticker(ticker)
            df = stock.history(start=start, end=end, interval=interval)
            
            if df.empty:
                logger.warning("no_historical_data", ticker=ticker)
                return []
            
            ohlcv_list = []
            for timestamp, row in df.iterrows():
                try:
                    # OHLCV.__post_init__ validates Property 26 (OHLC consistency)
                    # and Property 28 (volume non-negativity)
                    ohlcv = OHLCV(
                        ticker=ticker,
                        timestamp=timestamp.to_pydatetime(),
                        open=Decimal(str(row['Open'])),
                        high=Decimal(str(row['High'])),
                        low=Decimal(str(row['Low'])),
                        close=Decimal(str(row['Close'])),
                        volume=int(row['Volume']),
                        adjusted_close=Decimal(str(row.get('Close', row['Close'])))
                    )
                    ohlcv_list.append(ohlcv)
                except ValueError as e:
                    logger.warning(
                        "invalid_ohlcv_data",
                        ticker=ticker,
                        timestamp=timestamp,
                        error=str(e),
                        property_violation=self._classify_validation_error(str(e))
                    )
                    continue
            
            # Validate timestamp ordering (Property 27)
            validation_result = DataValidator.validate_price_data(ohlcv_list)
            
            if not validation_result.is_valid:
                logger.error(
                    "data_validation_failed",
                    ticker=ticker,
                    errors=validation_result.errors,
                    property="27"
                )
                # Return empty list if validation fails critically
                # (timestamp ordering issues indicate data corruption)
                return []
            
            if validation_result.warnings:
                logger.warning(
                    "data_validation_warnings",
                    ticker=ticker,
                    warnings=validation_result.warnings
                )
            
            # Cache for 1 hour
            self.cache.set(cache_key, ohlcv_list, ttl=3600)
            
            logger.info(
                "historical_data_fetched",
                ticker=ticker,
                records=len(ohlcv_list),
                validated=True
            )
            return ohlcv_list
            
        except Exception as e:
            logger.error(
                "historical_data_fetch_failed",
                ticker=ticker,
                error=str(e)
            )
            raise
    
    def _classify_validation_error(self, error_msg: str) -> str:
        """
        Classify validation error to property violation.
        
        Args:
            error_msg: Error message from validation
        
        Returns:
            Property number as string
        """
        error_lower = error_msg.lower()
        
        if "high" in error_lower and ("open" in error_lower or "close" in error_lower):
            return "Property_26_OHLC_Consistency"
        elif "low" in error_lower and ("open" in error_lower or "close" in error_lower):
            return "Property_26_OHLC_Consistency"
        elif "volume" in error_lower and "negative" in error_lower:
            return "Property_28_Volume_Non_Negativity"
        elif "timestamp" in error_lower:
            return "Property_27_Timestamp_Ordering"
        else:
            return "Unknown"
    
    def get_intraday_data(
        self,
        ticker: str,
        interval: str = "5m"
    ) -> List[OHLCV]:
        """
        Get today's intraday data with validation.
        
        Validates the same properties as get_historical_data:
        - Property 26: OHLC consistency
        - Property 27: Timestamp ordering
        - Property 28: Volume non-negativity
        
        Args:
            ticker: Stock ticker symbol
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m)
        
        Returns:
            List of OHLCV objects
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        return self.get_historical_data(
            ticker=ticker,
            start=yesterday,
            end=today,
            interval=interval
        )
    
    def get_historical_data_df(
        self,
        ticker: str,
        start: date,
        end: date,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical data as DataFrame (alternative interface).
        
        This is a convenience method that returns data as a pandas DataFrame
        for compatibility with existing code that expects DataFrame format.
        
        Args:
            ticker: Stock ticker symbol
            start: Start date
            end: End date
            interval: Data interval (1d, 1h, 5m, etc.)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ohlcv_list = self.get_historical_data(ticker, start, end, interval)
        
        if not ohlcv_list:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for ohlcv in ohlcv_list:
            data.append({
                'timestamp': ohlcv.timestamp,
                'open': float(ohlcv.open),
                'high': float(ohlcv.high),
                'low': float(ohlcv.low),
                'close': float(ohlcv.close),
                'volume': ohlcv.volume,
                'adjusted_close': float(ohlcv.adjusted_close) if ohlcv.adjusted_close else None
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_intraday_data_df(
        self,
        ticker: str,
        interval: str = "5m"
    ) -> pd.DataFrame:
        """
        Get intraday data as DataFrame (alternative interface).
        
        Args:
            ticker: Stock ticker symbol
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        return self.get_historical_data_df(
            ticker=ticker,
            start=yesterday,
            end=today,
            interval=interval
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_stock_info(self, ticker: str) -> Optional[Stock]:
        """
        Get stock information.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Stock object or None if not available
        """
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning("rate_limit_approached", ticker=ticker)
            return None
        
        try:
            self._increment_rate_limit()
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                logger.warning("stock_info_not_available", ticker=ticker)
                return None
            
            stock_obj = Stock(
                ticker=ticker,
                name=info.get('longName', ticker),
                sector=info.get('sector'),
                industry=info.get('industry'),
                market_cap=info.get('marketCap'),
                avg_volume=info.get('averageVolume'),
                current_price=Decimal(str(info.get('currentPrice', 0))) if info.get('currentPrice') else None
            )
            
            logger.info("stock_info_fetched", ticker=ticker)
            return stock_obj
            
        except Exception as e:
            logger.error("stock_info_fetch_failed", ticker=ticker, error=str(e))
            raise
    
    def get_bulk_quotes(self, tickers: List[str]) -> Dict[str, Price]:
        """
        Get current prices for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Dictionary mapping ticker to Price object
        """
        quotes = {}
        
        for ticker in tickers:
            try:
                price = self.get_realtime_price(ticker)
                if price:
                    quotes[ticker] = price
            except Exception as e:
                logger.error("bulk_quote_failed", ticker=ticker, error=str(e))
                continue
        
        logger.info("bulk_quotes_fetched", count=len(quotes), total=len(tickers))
        return quotes
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def get_daily_quote(self, ticker: str) -> Optional[Dict]:
        """
        Get a consolidated daily quote for a ticker in a single yfinance call.

        Returns the fields required to rank top movers by trend (price change)
        and trading activity (volume / "purchases"):
            ticker, name, current_price, previous_close, price_change_pct,
            price_change_abs, volume, avg_volume, market_cap, sector

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with quote fields, or None if data is unavailable.
        """
        # Check cache first (5-minute TTL keeps the dashboard < 2s)
        cache_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.PRICE_LATEST,
            ticker=f"{ticker}:dailyquote"
        )
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug("daily_quote_cache_hit", ticker=ticker)
            return cached

        if not self._check_rate_limit():
            logger.warning("rate_limit_approached", ticker=ticker)
            return None

        try:
            self._increment_rate_limit()

            stock = yf.Ticker(ticker)
            info = stock.info or {}

            # Current price: prefer live currentPrice, fall back to regularMarketPrice
            current = info.get('currentPrice') or info.get('regularMarketPrice')
            previous = (
                info.get('previousClose')
                or info.get('regularMarketPreviousClose')
            )

            if not current or not previous:
                logger.warning("daily_quote_incomplete", ticker=ticker)
                return None

            current_price = float(current)
            previous_close = float(previous)

            price_change_abs = current_price - previous_close
            price_change_pct = (
                (price_change_abs / previous_close) * 100.0
                if previous_close else 0.0
            )

            quote = {
                "ticker": ticker,
                "name": info.get('longName', ticker),
                "current_price": current_price,
                "previous_close": previous_close,
                "price_change_pct": round(price_change_pct, 2),
                "price_change_abs": round(price_change_abs, 2),
                "volume": int(
                    info.get('volume') or info.get('regularMarketVolume') or 0
                ),
                "avg_volume": int(info.get('averageVolume') or 0),
                "market_cap": int(info.get('marketCap') or 0),
                "sector": info.get('sector') or "Unknown",
            }

            # Cache for 5 minutes
            self.cache.set(cache_key, quote, ttl=self.settings.price_cache_ttl)

            logger.info(
                "daily_quote_fetched",
                ticker=ticker,
                change_pct=quote["price_change_pct"],
            )
            return quote

        except Exception as e:
            logger.error("daily_quote_failed", ticker=ticker, error=str(e))
            raise

    def get_bulk_daily_quotes(self, tickers: List[str]) -> List[Dict]:
        """
        Get daily quotes for multiple tickers.

        Skips tickers that fail or have incomplete data so the dashboard can
        still render with whatever data is available.

        Args:
            tickers: List of ticker symbols

        Returns:
            List of quote dicts (see get_daily_quote).
        """
        quotes: List[Dict] = []
        for ticker in tickers:
            try:
                quote = self.get_daily_quote(ticker)
                if quote:
                    quotes.append(quote)
            except Exception as e:
                logger.error("bulk_daily_quote_failed", ticker=ticker, error=str(e))
                continue

        logger.info("bulk_daily_quotes_fetched", count=len(quotes), total=len(tickers))
        return quotes

    def get_market_indices(self) -> Dict[str, Price]:
        """
        Get current prices for major market indices.
        
        Returns:
            Dictionary mapping index name to Price object
        """
        indices = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "DOW": "^DJI",
            "Russell 2000": "^RUT"
        }
        
        # Check cache
        cache_key = CacheKeyPatterns.MARKET_INDICES
        cached_indices = self.cache.get(cache_key)
        if cached_indices:
            logger.debug("market_indices_cache_hit")
            return cached_indices
        
        result = {}
        for name, ticker in indices.items():
            try:
                price = self.get_realtime_price(ticker)
                if price:
                    result[name] = price
            except Exception as e:
                logger.error("index_fetch_failed", index=name, error=str(e))
                continue
        
        # Cache for 5 minutes
        self.cache.set(cache_key, result, ttl=300)
        
        logger.info("market_indices_fetched", count=len(result))
        return result
