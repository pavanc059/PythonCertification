"""
Penny stock scanner.

Scans for penny stocks (price ≤ $5.00) with sudden intraday or multi-day gains,
filters by volume, and caches results in Redis.

Properties implemented:
- Property 42: Penny stocks must have price ≤ $5.00
- Property 43: Intraday gainers must have gain ≥ min_gain_pct (default 20%)
- Property 44: Multi-day gainers must have gain ≥ min_gain_pct over `days` days
              (default 50% over 5 days)
- Property 47: volume_ratio = current_volume / average_volume, must be ≥ 1.0
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependencies — graceful degradation
# ---------------------------------------------------------------------------
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available — penny stock live data disabled")

try:
    from ...infrastructure.cache import get_cache, CacheKeyPatterns, CacheTTL
    CACHE_AVAILABLE = True
except Exception:
    CACHE_AVAILABLE = False
    logger.warning("Redis cache not available — penny stock caching disabled")

try:
    from ...infrastructure.database import get_db_context
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False
    logger.warning("Database not available — penny stock DB queries disabled")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RiskMetrics:
    """Risk metrics specific to penny stocks."""
    liquidity_risk: float       # 0-1, higher = more risky
    volatility_risk: float      # 0-1, higher = more risky
    spread_percentage: float    # bid-ask spread as % of mid-price (≥ 0)
    overall_risk: str           # 'low', 'medium', 'high', or 'extreme'


@dataclass
class PennyStock:
    """
    Represents a penny stock with associated metrics.

    A penny stock is defined as a security trading at or below $5.00 per share
    (Property 42).
    """
    ticker: str
    price: Decimal
    price_change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float
    market_cap: int
    sector: str
    momentum_score: Optional[float] = None
    risk_metrics: Optional[RiskMetrics] = None
    catalyst: Optional[str] = None

    def __post_init__(self):
        # Property 42: price must be ≤ $5.00
        if self.price > Decimal("5.00"):
            raise ValueError(
                f"PennyStock price {self.price} exceeds $5.00 — not a penny stock "
                "(Property 42)"
            )
        if self.price < Decimal("0"):
            raise ValueError(f"PennyStock price {self.price} cannot be negative")


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

# Tickers commonly screened for penny stocks (used when DB is not available)
_DEFAULT_PENNY_UNIVERSE: List[str] = []


class PennyStockScanner:
    """
    Scans for penny stocks with sudden gains and momentum.

    Redis caching is used when available (2-minute TTL for intraday data).
    Falls back to direct yfinance queries when cache / DB is unavailable.
    """

    #: Maximum price to be considered a penny stock (Property 42)
    PENNY_PRICE_THRESHOLD = Decimal("5.00")
    #: Cache TTL in seconds (2 minutes during market hours)
    CACHE_TTL_SECONDS = 120

    def __init__(self):
        self._cache = None
        if CACHE_AVAILABLE:
            try:
                self._cache = get_cache()
            except Exception as exc:
                logger.warning("Could not connect to Redis: %s", exc)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def scan_intraday_gainers(
        self, min_gain_pct: float = 20.0
    ) -> List[PennyStock]:
        """
        Identify penny stocks with an intraday gain ≥ min_gain_pct.

        Implements Properties 42 and 43:
        - Property 42: Only returns stocks with price ≤ $5.00
        - Property 43: Only returns stocks whose intraday gain ≥ min_gain_pct

        Args:
            min_gain_pct: Minimum intraday percentage gain (default 20.0%).

        Returns:
            List of PennyStock objects that satisfy both properties.
        """
        cache_key = f"penny:intraday_gainers:{date.today().isoformat()}:{min_gain_pct}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        universe = self.get_penny_stock_universe()
        gainers: List[PennyStock] = []

        for ticker in universe:
            try:
                stock = self._fetch_intraday_stock(ticker)
                if stock is None:
                    continue
                # Property 42: price ≤ $5.00 (enforced by PennyStock.__post_init__)
                # Property 43: gain ≥ min_gain_pct
                if stock.price_change_pct >= min_gain_pct:
                    gainers.append(stock)
            except ValueError:
                # PennyStock constructor rejects prices > $5
                continue
            except Exception as exc:
                logger.debug("Error fetching intraday data for %s: %s", ticker, exc)

        self._set_in_cache(cache_key, gainers)
        logger.info("scan_intraday_gainers found %d stocks (min_gain=%.1f%%)",
                    len(gainers), min_gain_pct)
        return gainers

    def scan_multi_day_gainers(
        self, days: int = 5, min_gain_pct: float = 50.0
    ) -> List[PennyStock]:
        """
        Identify penny stocks with a multi-day gain ≥ min_gain_pct over `days` days.

        Implements Properties 42 and 44:
        - Property 42: Only returns stocks with price ≤ $5.00
        - Property 44: Only returns stocks whose gain over `days` trading
                       days ≥ min_gain_pct

        Args:
            days:         Number of trading days to look back (default 5).
            min_gain_pct: Minimum gain over the period (default 50.0%).

        Returns:
            List of PennyStock objects that satisfy both properties.
        """
        cache_key = (
            f"penny:multiday_gainers:{date.today().isoformat()}:{days}:{min_gain_pct}"
        )
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        universe = self.get_penny_stock_universe()
        gainers: List[PennyStock] = []

        for ticker in universe:
            try:
                stock = self._fetch_multi_day_stock(ticker, days)
                if stock is None:
                    continue
                # Property 42 enforced by constructor
                # Property 44: gain over `days` ≥ min_gain_pct
                if stock.price_change_pct >= min_gain_pct:
                    gainers.append(stock)
            except ValueError:
                continue
            except Exception as exc:
                logger.debug("Error fetching %d-day data for %s: %s", days, ticker, exc)

        self._set_in_cache(cache_key, gainers)
        logger.info(
            "scan_multi_day_gainers found %d stocks (days=%d, min_gain=%.1f%%)",
            len(gainers), days, min_gain_pct,
        )
        return gainers

    def filter_by_volume(
        self,
        stocks: List[PennyStock],
        min_avg_volume: int = 50_000,
    ) -> List[PennyStock]:
        """
        Filter penny stocks by minimum average daily volume.

        Args:
            stocks:         List of PennyStock objects to filter.
            min_avg_volume: Minimum acceptable average daily volume
                            (default 50,000 shares per Requirement 11.6).

        Returns:
            Subset of `stocks` whose avg_volume ≥ min_avg_volume.
        """
        filtered = [s for s in stocks if s.avg_volume >= min_avg_volume]
        logger.debug(
            "filter_by_volume: %d → %d (min_avg_volume=%d)",
            len(stocks), len(filtered), min_avg_volume,
        )
        return filtered

    def calculate_volume_ratio(self, stock: PennyStock) -> float:
        """
        Calculate the volume ratio for a penny stock.

        Property 47: volume_ratio = current_volume / average_volume (≥ 1.0
        is considered a volume surge; the ratio is always ≥ 0).

        The result is ≥ 0.  Values ≥ 1.0 mean current volume is at or above
        the average; values > 1.0 indicate a volume surge.

        Args:
            stock: PennyStock whose volume_ratio to compute.

        Returns:
            Float representing volume_ratio.  Returns 0.0 when avg_volume is 0
            to avoid division by zero.
        """
        if stock.avg_volume <= 0:
            return 0.0
        ratio = stock.volume / stock.avg_volume
        return ratio

    def get_penny_stock_universe(self) -> List[str]:
        """
        Return the list of stock tickers whose most recent close was < $5.

        Priority:
        1. Query the PostgreSQL database (when available).
        2. Fall back to an in-memory cache of a previous successful DB query.
        3. Fall back to yfinance screening of a small watchlist.
        4. Return an empty list if nothing is available.

        The list is refreshed every 2 minutes during market hours (the caller
        is responsible for scheduling; this method caches results internally).
        """
        cache_key = f"penny:universe:{date.today().isoformat()}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        tickers: List[str] = []

        # --- Strategy 1: database ---
        if DB_AVAILABLE:
            tickers = self._query_universe_from_db()

        # --- Strategy 2: yfinance fallback ---
        if not tickers and YFINANCE_AVAILABLE:
            tickers = self._query_universe_from_yfinance()

        self._set_in_cache(cache_key, tickers)
        return tickers

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_intraday_stock(self, ticker: str) -> Optional[PennyStock]:
        """
        Fetch current intraday data for *ticker* and return a PennyStock if
        the price is ≤ $5.00, or None otherwise.
        """
        if not YFINANCE_AVAILABLE:
            return None

        yfobj = yf.Ticker(ticker)
        info = yfobj.info or {}

        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        if current_price is None:
            return None

        price = Decimal(str(current_price))
        if price > self.PENNY_PRICE_THRESHOLD:
            return None

        open_price = info.get("open") or info.get("regularMarketOpen")
        if open_price is None or open_price == 0:
            return None

        intraday_change_pct = float(
            ((price - Decimal(str(open_price))) / Decimal(str(open_price))) * 100
        )

        avg_volume = info.get("averageVolume") or info.get("averageDailyVolume10Day") or 0
        volume = info.get("volume") or info.get("regularMarketVolume") or 0
        market_cap = info.get("marketCap") or 0
        sector = info.get("sector") or "Unknown"

        volume_ratio = (volume / avg_volume) if avg_volume > 0 else 0.0

        return PennyStock(
            ticker=ticker,
            price=price,
            price_change_pct=intraday_change_pct,
            volume=int(volume),
            avg_volume=int(avg_volume),
            volume_ratio=volume_ratio,
            market_cap=int(market_cap),
            sector=sector,
        )

    def _fetch_multi_day_stock(
        self, ticker: str, days: int
    ) -> Optional[PennyStock]:
        """
        Fetch multi-day price data for *ticker* and return a PennyStock if
        the price is ≤ $5.00, or None otherwise.
        """
        if not YFINANCE_AVAILABLE:
            return None

        end_date = date.today()
        # Add buffer days to account for weekends/holidays
        start_date = end_date - timedelta(days=days + 5)

        yfobj = yf.Ticker(ticker)
        hist = yfobj.history(start=start_date, end=end_date, interval="1d")

        if hist is None or hist.empty or len(hist) < 2:
            return None

        # Use the most recent `days` trading sessions
        hist = hist.tail(days + 1)

        current_close = Decimal(str(hist["Close"].iloc[-1]))
        if current_close > self.PENNY_PRICE_THRESHOLD:
            return None

        start_close = Decimal(str(hist["Close"].iloc[0]))
        if start_close == 0:
            return None

        pct_change = float(
            ((current_close - start_close) / start_close) * 100
        )

        info = yfobj.info or {}
        avg_volume = int(
            info.get("averageVolume") or info.get("averageDailyVolume10Day") or 0
        )
        current_volume = int(hist["Volume"].iloc[-1])
        market_cap = int(info.get("marketCap") or 0)
        sector = info.get("sector") or "Unknown"

        volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 0.0

        return PennyStock(
            ticker=ticker,
            price=current_close,
            price_change_pct=pct_change,
            volume=current_volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            market_cap=market_cap,
            sector=sector,
        )

    def _query_universe_from_db(self) -> List[str]:
        """Query PostgreSQL for tickers with last known price < $5."""
        try:
            from ...infrastructure.models import Stock as StockModel  # type: ignore
            with get_db_context() as db:
                rows = (
                    db.query(StockModel.ticker)
                    .filter(StockModel.current_price < 5.0)
                    .all()
                )
                tickers = [r.ticker for r in rows]
                logger.info("penny_universe_from_db: %d tickers", len(tickers))
                return tickers
        except Exception as exc:
            logger.warning("DB penny universe query failed: %s", exc)
            return []

    def _query_universe_from_yfinance(self) -> List[str]:
        """
        Fallback: screen a broad watchlist via yfinance and return tickers
        whose current price is < $5.
        """
        # A representative sample — in production this would come from a
        # proper screener or exchange-provided low-price list.
        candidates = _DEFAULT_PENNY_UNIVERSE
        if not candidates:
            return []

        results: List[str] = []
        for ticker in candidates:
            try:
                info = yf.Ticker(ticker).info or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                if price is not None and Decimal(str(price)) <= self.PENNY_PRICE_THRESHOLD:
                    results.append(ticker)
            except Exception:
                continue

        logger.info("penny_universe_from_yfinance: %d tickers", len(results))
        return results

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_from_cache(self, key: str):
        if self._cache is None:
            return None
        try:
            return self._cache.get(key)
        except Exception as exc:
            logger.debug("Cache get failed for key '%s': %s", key, exc)
            return None

    def _set_in_cache(self, key: str, value) -> None:
        if self._cache is None:
            return
        try:
            self._cache.set(key, value, ttl=self.CACHE_TTL_SECONDS)
        except Exception as exc:
            logger.debug("Cache set failed for key '%s': %s", key, exc)
