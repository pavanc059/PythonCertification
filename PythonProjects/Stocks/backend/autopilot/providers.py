"""
Pluggable market-data providers for AutoPilot.

AutoPilot never talks to yfinance (or any vendor SDK) directly. Instead it
depends on the ``MarketDataProvider`` interface, and a factory picks the
concrete implementation from ``settings.autopilot_data_provider``.

To add a new provider (Webull, Polygon, Alpaca, ...):
  1. Subclass MarketDataProvider and implement the three methods.
  2. Register it in ``_PROVIDER_REGISTRY``.
  3. Set AUTOPILOT_DATA_PROVIDER=<name> in the environment.

All methods return plain dataclasses / builtins so the rest of the system is
provider-agnostic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from autotrade.strategies import Bar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass
class Quote:
    """A point-in-time snapshot for a ticker."""
    ticker: str
    price: float
    change_pct: float          # intraday % change vs previous close
    volume: int
    avg_volume: int
    volume_ratio: float        # volume / avg_volume (surge indicator)
    day_high: Optional[float] = None
    day_low: Optional[float] = None

    @property
    def is_volume_surge(self) -> bool:
        return self.volume_ratio >= 1.5


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class MarketDataProvider(ABC):
    """Abstract market-data source. Implementations must be thread-safe."""

    name: str = "abstract"

    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[Quote]:
        """Return a current Quote for the ticker, or None if unavailable."""

    @abstractmethod
    def get_bars(self, ticker: str, period: str = "5d", interval: str = "5m") -> List[Bar]:
        """
        Return chronological OHLCV bars (oldest first) for indicator math.

        Defaults to intraday granularity suited to day-trading signals.
        """

    @abstractmethod
    def get_universe(self, market_type: str) -> List[str]:
        """
        Return the candidate ticker universe for a market type.

        Args:
            market_type: "penny" | "regular"
        """


# ---------------------------------------------------------------------------
# yfinance implementation
# ---------------------------------------------------------------------------

# A curated set of liquid, reasonably volatile large/mid caps for the
# "regular" day-trading universe. Kept modest to stay within yfinance rate
# limits when scanned every 5 minutes.
_REGULAR_UNIVERSE: List[str] = [
    "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "AMZN", "META", "GOOGL", "NFLX",
    "INTC", "MU", "CRM", "ORCL", "AVGO", "QCOM", "PYPL", "SHOP", "SQ", "COIN",
    "PLTR", "SOFI", "RIVN", "LCID", "NIO", "BABA", "DIS", "BA", "F", "GM",
    "UBER", "ABNB", "SNAP", "PINS", "ROKU", "DKNG", "MARA", "RIOT", "SMCI",
    "ARM", "DELL",
]

# Fallback penny universe when the DB / scanner universe is empty.
_PENNY_UNIVERSE_FALLBACK: List[str] = [
    "SNDL", "CGC", "TLRY", "NOK", "SIRI", "PLUG", "FCEL", "GEVO", "IDEX",
    "ZOM", "OCGN", "BNGO", "CTRM", "SHIP", "GNUS", "XELA", "MULN", "BBIG",
]


class YFinanceProvider(MarketDataProvider):
    """Market data backed by yfinance (free, ~15-min intraday delay)."""

    name = "yfinance"

    def __init__(self) -> None:
        self._session = self._build_session()

    @staticmethod
    def _build_session():
        """Browser-like session to reduce Yahoo rate-limiting of container IPs."""
        try:
            import requests
            s = requests.Session()
            s.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            })
            return s
        except Exception:
            return None

    def _ticker(self, ticker: str):
        import yfinance as yf
        try:
            return yf.Ticker(ticker, session=self._session)
        except TypeError:
            # Older/newer yfinance without session kwarg
            return yf.Ticker(ticker)

    def get_quote(self, ticker: str) -> Optional[Quote]:
        try:
            info = self._ticker(ticker).info or {}
        except Exception as exc:
            logger.debug("yfinance info failed for %s: %s", ticker, exc)
            return None

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is None:
            return None

        prev_close = info.get("regularMarketPreviousClose") or price
        change_pct = info.get("regularMarketChangePercent")
        if change_pct is None:
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        volume = info.get("regularMarketVolume") or info.get("volume") or 0
        avg_volume = info.get("averageVolume") or info.get("averageDailyVolume10Day") or 0
        volume_ratio = (volume / avg_volume) if avg_volume else 0.0

        return Quote(
            ticker=ticker.upper(),
            price=float(price),
            change_pct=float(change_pct),
            volume=int(volume),
            avg_volume=int(avg_volume),
            volume_ratio=round(volume_ratio, 2),
            day_high=info.get("regularMarketDayHigh") or info.get("dayHigh"),
            day_low=info.get("regularMarketDayLow") or info.get("dayLow"),
        )

    def get_bars(self, ticker: str, period: str = "5d", interval: str = "5m") -> List[Bar]:
        try:
            hist = self._ticker(ticker).history(period=period, interval=interval)
        except Exception as exc:
            logger.debug("yfinance history failed for %s: %s", ticker, exc)
            return []

        if hist is None or hist.empty:
            return []

        bars: List[Bar] = []
        for ts, row in hist.iterrows():
            try:
                bars.append(Bar(
                    timestamp=ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                ))
            except (ValueError, KeyError, TypeError):
                continue
        return bars

    def get_universe(self, market_type: str) -> List[str]:
        if market_type == "regular":
            return list(_REGULAR_UNIVERSE)

        # penny: try the existing scanner's universe, fall back to a static list
        try:
            from stockiq.news.penny.scanner import PennyStockScanner
            universe = PennyStockScanner().get_penny_stock_universe()
            if universe:
                return universe
        except Exception as exc:
            logger.debug("PennyStockScanner universe unavailable: %s", exc)
        return list(_PENNY_UNIVERSE_FALLBACK)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_PROVIDER_REGISTRY = {
    "yfinance": YFinanceProvider,
}

# Simple process-level cache so we reuse the (session-holding) provider.
_provider_cache: dict[str, MarketDataProvider] = {}


def get_provider(name: Optional[str] = None) -> MarketDataProvider:
    """
    Return the configured market-data provider.

    Falls back to yfinance if the requested provider is unknown.
    """
    from config import settings

    key = (name or settings.autopilot_data_provider or "yfinance").lower()
    if key not in _PROVIDER_REGISTRY:
        logger.warning("Unknown AutoPilot data provider '%s', using yfinance.", key)
        key = "yfinance"

    if key not in _provider_cache:
        _provider_cache[key] = _PROVIDER_REGISTRY[key]()
    return _provider_cache[key]


def list_providers() -> List[str]:
    """Return the names of all registered providers."""
    return list(_PROVIDER_REGISTRY.keys())
