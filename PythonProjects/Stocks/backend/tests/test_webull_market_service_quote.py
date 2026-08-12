"""
Unit tests for WebullMarketService.get_quote() — task 3.3.

Tests cover:
  - Cache hit returns cached value without hitting any provider
  - Webull success: returns normalized dict with data_source="webull", TTL=15s
  - Webull unavailable: falls back to yfinance, data_source="yfinance", TTL=30s
  - data_source="yfinance": bypasses Webull entirely, uses yfinance
  - data_source="stub": bypasses both Webull and yfinance → 503
  - Webull client is None: falls through to yfinance
  - Both providers fail → HTTPException 503
  - Result dict contains all required fields

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from backend.market.service import WebullMarketService
from backend.webull_client.client import WebullUnavailableError
from backend.webull_client.types import WebullQuoteData


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_service(
    data_source: str = "webull",
    webull_client=None,
    redis_url: str | None = None,
) -> WebullMarketService:
    return WebullMarketService(
        redis_url=redis_url,
        webull_client=webull_client,
        data_source=data_source,
    )


def _make_webull_client(raw: dict | None = None, raise_error: bool = False) -> MagicMock:
    """Return a mock WebullClient."""
    client = MagicMock()
    if raise_error:
        client.fetch_quote.side_effect = WebullUnavailableError("Webull is down")
    else:
        raw = raw or {"close": 150.0, "companyName": "Apple Inc.", "change": 1.5,
                      "changeRatio": 0.01, "volume": 55_000_000, "high": 152.0,
                      "low": 149.0, "week52High": 198.0, "week52Low": 124.0,
                      "marketValue": 2_400_000_000_000.0}
        client.fetch_quote.return_value = raw
        # Wire _normalize_webull_quote to return a real WebullQuoteData
        client._normalize_webull_quote.side_effect = lambda r, t: WebullQuoteData(
            ticker=t,
            company_name=r.get("companyName") or r.get("name") or t,
            price=float(r["close"]),
            change=float(r.get("change", 0.0)),
            change_pct=float(r.get("changeRatio", 0.0)),
            volume=int(r["volume"]) if r.get("volume") is not None else None,
            day_high=float(r["high"]) if r.get("high") is not None else None,
            day_low=float(r["low"]) if r.get("low") is not None else None,
            week_52_high=float(r["week52High"]) if r.get("week52High") is not None else None,
            week_52_low=float(r["week52Low"]) if r.get("week52Low") is not None else None,
            market_cap=float(r["marketValue"]) if r.get("marketValue") is not None else None,
            source="webull",
        )
    return client


_YFINANCE_INFO = {
    "regularMarketPrice": 192.40,
    "regularMarketChange": 2.30,
    "regularMarketChangePercent": 1.21,
    "regularMarketVolume": 55_000_000,
    "regularMarketDayHigh": 193.50,
    "regularMarketDayLow": 190.10,
    "fiftyTwoWeekHigh": 200.0,
    "fiftyTwoWeekLow": 150.0,
    "marketCap": 3_000_000_000_000,
    "longName": "Apple Inc.",
    "regularMarketPreviousClose": 190.10,
}


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_cache_hit_returns_cached_value_without_calling_providers(self):
        """When cache has a value, neither Webull nor yfinance is called."""
        svc = _make_service(data_source="webull")
        cached = {"ticker": "AAPL", "price": 100.0, "data_source": "webull"}
        svc._cache_get = MagicMock(return_value=cached)
        svc._cache_set = MagicMock()
        wb_client = _make_webull_client()
        svc._webull_client = wb_client

        result = svc.get_quote("AAPL")

        assert result == cached
        wb_client.fetch_quote.assert_not_called()
        svc._cache_set.assert_not_called()

    def test_cache_hit_returns_exact_cached_dict(self):
        """Cached dict is returned verbatim."""
        svc = _make_service()
        cached = {"ticker": "TSLA", "price": 250.0, "data_source": "yfinance",
                  "company_name": "Tesla Inc.", "change": -5.0, "change_pct": -0.02}
        svc._cache_get = MagicMock(return_value=cached)

        result = svc.get_quote("TSLA")

        assert result is cached


# ---------------------------------------------------------------------------
# Webull primary source
# ---------------------------------------------------------------------------

class TestWebullPrimarySource:
    def test_returns_dict_with_data_source_webull(self):
        """On Webull success, result has data_source='webull'."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        result = svc.get_quote("AAPL")

        assert result["data_source"] == "webull"

    def test_caches_webull_result_with_ttl_15(self):
        """Webull result is cached with TTL=15 seconds (Req 4.2)."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        svc.get_quote("AAPL")

        svc._cache_set.assert_called_once()
        call_args = svc._cache_set.call_args
        assert call_args[1].get("ttl") == 15 or (len(call_args[0]) > 2 and call_args[0][2] == 15)

    def test_result_contains_all_required_fields(self):
        """Result dict contains all required QuoteResponse fields (Req 4.7)."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        result = svc.get_quote("AAPL")

        required_keys = {
            "ticker", "company_name", "price", "change", "change_pct",
            "volume", "day_high", "day_low", "week_52_high", "week_52_low",
            "market_cap", "data_source",
        }
        assert required_keys.issubset(result.keys())

    def test_ticker_in_result_matches_argument(self):
        """Result ticker matches the argument passed to get_quote."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        result = svc.get_quote("MSFT")

        assert result["ticker"] == "MSFT"

    def test_price_is_float(self):
        """price field is a Python float."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        result = svc.get_quote("AAPL")

        assert isinstance(result["price"], float)

    def test_webull_client_fetch_quote_called_with_ticker(self):
        """WebullClient.fetch_quote is called with the exact ticker."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        svc.get_quote("NVDA")

        wb_client.fetch_quote.assert_called_once_with("NVDA")


# ---------------------------------------------------------------------------
# Fallback to yfinance
# ---------------------------------------------------------------------------

class TestYfinanceFallback:
    def _svc_with_failing_webull(self) -> WebullMarketService:
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()
        return svc

    def test_fallback_returns_data_source_yfinance(self):
        """When Webull raises WebullUnavailableError, result has data_source='yfinance'."""
        svc = self._svc_with_failing_webull()
        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_quote("AAPL")

        assert result["data_source"] == "yfinance"

    def test_fallback_caches_with_ttl_30(self):
        """yfinance result is cached with TTL=30 seconds (Req 4.5)."""
        svc = self._svc_with_failing_webull()
        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with patch("yfinance.Ticker", return_value=mock_ticker):
            svc.get_quote("AAPL")

        svc._cache_set.assert_called_once()
        call_args = svc._cache_set.call_args
        # TTL arg is positional (index 2) or keyword
        ttl_val = call_args[1].get("ttl") if call_args[1].get("ttl") else call_args[0][2]
        assert ttl_val == 30

    def test_fallback_result_contains_required_fields(self):
        """yfinance fallback result has all required schema fields."""
        svc = self._svc_with_failing_webull()
        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_quote("AAPL")

        required_keys = {
            "ticker", "company_name", "price", "change", "change_pct",
            "volume", "day_high", "day_low", "week_52_high", "week_52_low",
            "market_cap", "data_source",
        }
        assert required_keys.issubset(result.keys())

    def test_fallback_price_matches_yfinance_value(self):
        """yfinance price value is correctly propagated to result."""
        svc = self._svc_with_failing_webull()
        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_quote("AAPL")

        assert result["price"] == pytest.approx(192.40)

    def test_fallback_webull_unavailable_error_logged(self, caplog):
        """WebullUnavailableError causes a WARNING log."""
        import logging
        svc = self._svc_with_failing_webull()
        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with caplog.at_level(logging.WARNING, logger="backend.market.service"):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                svc.get_quote("AAPL")

        assert "AAPL" in caplog.text
        assert any(r.levelname == "WARNING" for r in caplog.records)


# ---------------------------------------------------------------------------
# data_source bypasses
# ---------------------------------------------------------------------------

class TestDataSourceBypasses:
    def test_yfinance_data_source_skips_webull(self):
        """When data_source='yfinance', WebullClient.fetch_quote is never called."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="yfinance", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_quote("AAPL")

        wb_client.fetch_quote.assert_not_called()
        assert result["data_source"] == "yfinance"

    def test_stub_data_source_raises_503(self):
        """data_source='stub' skips both providers and raises 503."""
        svc = _make_service(data_source="stub")
        svc._cache_get = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            svc.get_quote("AAPL")

        assert exc_info.value.status_code == 503

    def test_webull_client_none_falls_through_to_yfinance(self):
        """When data_source='webull' but _webull_client is None, yfinance is used."""
        svc = _make_service(data_source="webull", webull_client=None)
        svc._cache_get = MagicMock(return_value=None)
        svc._cache_set = MagicMock()

        mock_ticker = MagicMock()
        mock_ticker.info = _YFINANCE_INFO

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_quote("AAPL")

        assert result["data_source"] == "yfinance"


# ---------------------------------------------------------------------------
# Both providers fail → 503
# ---------------------------------------------------------------------------

class TestBothProvidersFail:
    def test_raises_503_when_both_fail(self):
        """HTTPException(503) raised when Webull raises and yfinance has no price."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)

        mock_ticker = MagicMock()
        mock_ticker.info = {}  # no price data

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_quote("AAPL")

        assert exc_info.value.status_code == 503

    def test_503_detail_contains_ticker(self):
        """503 detail message includes the failing ticker."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)

        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_quote("TSLA")

        assert "TSLA" in exc_info.value.detail

    def test_raises_503_when_yfinance_raises_exception(self):
        """503 raised when yfinance throws an exception (not just empty info)."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(data_source="webull", webull_client=wb_client)
        svc._cache_get = MagicMock(return_value=None)

        with patch("yfinance.Ticker", side_effect=Exception("yf network error")):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_quote("GOOG")

        assert exc_info.value.status_code == 503

    def test_yfinance_source_raises_503_on_yfinance_failure(self):
        """When data_source='yfinance' and yfinance fails, 503 is raised."""
        svc = _make_service(data_source="yfinance", webull_client=None)
        svc._cache_get = MagicMock(return_value=None)

        mock_ticker = MagicMock()
        mock_ticker.info = {}  # no price

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_quote("XYZ")

        assert exc_info.value.status_code == 503
