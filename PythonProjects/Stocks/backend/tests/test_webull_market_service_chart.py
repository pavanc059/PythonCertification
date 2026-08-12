"""
Unit tests for WebullMarketService.get_chart() — task 3.5.

Tests cover:
  - Cache hit returns cached value without calling any provider
  - Webull success: returns candles with data_source="webull", TTL=60s
  - Webull unavailable: falls back to yfinance, data_source="yfinance", TTL=60s
  - Unmapped period/interval: skips Webull, falls through to yfinance
  - data_source="yfinance": bypasses Webull entirely
  - data_source="stub": raises 503 immediately
  - Webull client is None: falls through to yfinance
  - Both providers fail → HTTPException 503
  - Timestamp handling: ms integer, ISO string, "time" and "vt" field names
  - Result dict contains all required fields
  - Candle structure is correct
  - cache_key format: "chart:{ticker}:{period}:{interval}"

Requirements: 4.8, 5.1
"""

from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from backend.market.service import WebullMarketService
from backend.webull_client.client import WebullUnavailableError


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_service(
    data_source: str = "webull",
    webull_client=None,
) -> WebullMarketService:
    svc = WebullMarketService(
        redis_url=None,
        webull_client=webull_client,
        data_source=data_source,
    )
    svc._cache_get = MagicMock(return_value=None)
    svc._cache_set = MagicMock()
    return svc


def _make_webull_client(bars=None, raise_error=False) -> MagicMock:
    client = MagicMock()
    if raise_error:
        client.fetch_bars.side_effect = WebullUnavailableError("Webull down")
    else:
        bars = bars or [
            {
                "open": 150.0, "high": 155.0, "low": 149.0, "close": 153.0,
                "volume": 1_000_000, "timestamp": "2024-01-15T09:30:00",
            },
            {
                "open": 153.0, "high": 156.0, "low": 152.0, "close": 154.5,
                "volume": 900_000, "timestamp": "2024-01-15T09:35:00",
            },
        ]
        client.fetch_bars.return_value = bars
    return client


def _make_yfinance_hist(rows=None):
    """Return a mock pandas DataFrame-like object for yfinance history."""
    import pandas as pd
    rows = rows or [
        {"Open": 150.0, "High": 155.0, "Low": 149.0, "Close": 153.0, "Volume": 1_000_000},
        {"Open": 153.0, "High": 156.0, "Low": 152.0, "Close": 154.5, "Volume": 900_000},
    ]
    idx = pd.date_range("2024-01-15 09:30", periods=len(rows), freq="5min", tz="America/New_York")
    df = pd.DataFrame(rows, index=idx)
    df.index.name = "Datetime"
    return df


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_cache_hit_returns_cached_value(self):
        """Cache hit returns value without touching any provider."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)
        cached = {
            "ticker": "AAPL", "period": "1d", "interval": "5m",
            "candles": [], "data_source": "webull",
        }
        svc._cache_get.return_value = cached

        result = svc.get_chart("AAPL", "1d", "5m")

        assert result is cached
        wb_client.fetch_bars.assert_not_called()
        svc._cache_set.assert_not_called()

    def test_cache_key_format(self):
        """Cache is checked with key 'chart:{ticker}:{period}:{interval}'."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        # Return cached value so we can just check the key used
        svc._cache_get.return_value = {"ticker": "TSLA", "candles": [], "data_source": "webull"}

        svc.get_chart("TSLA", "5d", "5m")

        svc._cache_get.assert_called_once_with("chart:TSLA:5d:5m")


# ---------------------------------------------------------------------------
# Webull primary source
# ---------------------------------------------------------------------------

class TestWebullPrimarySource:
    def test_returns_data_source_webull(self):
        """On Webull success, result has data_source='webull'."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("AAPL", "1d", "5m")

        assert result["data_source"] == "webull"

    def test_caches_with_ttl_60(self):
        """Webull chart result is cached with TTL=60 seconds (Req 4.8)."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)

        svc.get_chart("AAPL", "1d", "5m")

        svc._cache_set.assert_called_once()
        args, kwargs = svc._cache_set.call_args
        ttl_val = kwargs.get("ttl") or (args[2] if len(args) > 2 else None)
        assert ttl_val == 60

    def test_result_contains_required_fields(self):
        """Result dict contains ticker, period, interval, candles, data_source."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("AAPL", "1d", "5m")

        assert {"ticker", "period", "interval", "candles", "data_source"}.issubset(result.keys())
        assert result["ticker"] == "AAPL"
        assert result["period"] == "1d"
        assert result["interval"] == "5m"
        assert isinstance(result["candles"], list)

    def test_period_interval_mapping_used(self):
        """fetch_bars is called with the correct Webull interval code and count."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)

        svc.get_chart("AAPL", "1d", "5m")

        # ("1d", "5m") → ("M5", 78) per PERIOD_INTERVAL_MAP
        wb_client.fetch_bars.assert_called_once_with("AAPL", interval="M5", count=78)

    def test_all_mapped_period_interval_pairs(self):
        """fetch_bars is called with correct params for every mapped pair."""
        expected = WebullMarketService.PERIOD_INTERVAL_MAP
        for (period, interval), (wb_iv, count) in expected.items():
            wb_client = _make_webull_client()
            svc = _make_service(webull_client=wb_client)

            svc.get_chart("SPY", period, interval)

            wb_client.fetch_bars.assert_called_once_with("SPY", interval=wb_iv, count=count)

    def test_candle_structure(self):
        """Each candle has time, open, high, low, close, volume with correct types."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("AAPL", "1d", "5m")

        assert len(result["candles"]) == 2
        for candle in result["candles"]:
            assert set(candle.keys()) == {"time", "open", "high", "low", "close", "volume"}
            assert isinstance(candle["open"], float)
            assert isinstance(candle["high"], float)
            assert isinstance(candle["low"], float)
            assert isinstance(candle["close"], float)
            assert isinstance(candle["volume"], int)
            assert isinstance(candle["time"], str)

    def test_candle_values_match_raw_bars(self):
        """Candle OHLCV values match the raw bars returned by fetch_bars."""
        bars = [{"open": 200.0, "high": 210.0, "low": 195.0, "close": 205.0,
                 "volume": 500_000, "timestamp": "2024-01-15T10:00:00"}]
        wb_client = _make_webull_client(bars=bars)
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("MSFT", "1d", "5m")

        candle = result["candles"][0]
        assert candle["open"] == 200.0
        assert candle["high"] == 210.0
        assert candle["low"] == 195.0
        assert candle["close"] == 205.0
        assert candle["volume"] == 500_000


# ---------------------------------------------------------------------------
# Timestamp handling
# ---------------------------------------------------------------------------

class TestTimestampHandling:
    def test_iso_string_timestamp_used_as_is(self):
        """ISO string timestamp is passed through unchanged."""
        bars = [{"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5,
                 "volume": 100, "timestamp": "2024-01-15T09:30:00"}]
        wb_client = _make_webull_client(bars=bars)
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("X", "1d", "5m")

        assert result["candles"][0]["time"] == "2024-01-15T09:30:00"

    def test_millisecond_unix_timestamp_converted(self):
        """Unix timestamp in ms is converted to ISO format."""
        import datetime
        ts_ms = 1705315800000  # 2024-01-15T09:30:00 UTC (approx)
        bars = [{"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5,
                 "volume": 100, "timestamp": ts_ms}]
        wb_client = _make_webull_client(bars=bars)
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("X", "1d", "5m")

        # Should be an ISO string derived from the ms timestamp
        time_str = result["candles"][0]["time"]
        assert isinstance(time_str, str)
        assert "T" in time_str or "t" in time_str.lower() or "-" in time_str

    def test_time_field_name_used_when_timestamp_missing(self):
        """'time' field is used as fallback when 'timestamp' is absent."""
        bars = [{"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5,
                 "volume": 100, "time": "2024-01-15T10:00:00"}]
        wb_client = _make_webull_client(bars=bars)
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("X", "1d", "5m")

        assert result["candles"][0]["time"] == "2024-01-15T10:00:00"

    def test_vt_field_name_used_when_timestamp_and_time_missing(self):
        """'vt' field is used as final fallback when 'timestamp' and 'time' are absent."""
        bars = [{"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5,
                 "volume": 100, "vt": "2024-01-15T11:00:00"}]
        wb_client = _make_webull_client(bars=bars)
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("X", "1d", "5m")

        assert result["candles"][0]["time"] == "2024-01-15T11:00:00"

    def test_missing_timestamp_fields_produce_empty_string(self):
        """If no timestamp field exists, candle time is empty string."""
        bars = [{"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100}]
        wb_client = _make_webull_client(bars=bars)
        svc = _make_service(webull_client=wb_client)

        result = svc.get_chart("X", "1d", "5m")

        assert result["candles"][0]["time"] == ""


# ---------------------------------------------------------------------------
# Fallback to yfinance
# ---------------------------------------------------------------------------

class TestYfinanceFallback:
    def test_webull_unavailable_falls_back_to_yfinance(self):
        """WebullUnavailableError triggers yfinance fallback."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_chart("AAPL", "1d", "5m")

        assert result["data_source"] == "yfinance"

    def test_fallback_caches_with_ttl_60(self):
        """yfinance chart result is also cached with TTL=60s."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            svc.get_chart("AAPL", "1d", "5m")

        svc._cache_set.assert_called_once()
        args, kwargs = svc._cache_set.call_args
        ttl_val = kwargs.get("ttl") or (args[2] if len(args) > 2 else None)
        assert ttl_val == 60

    def test_fallback_result_contains_required_fields(self):
        """yfinance fallback result has all required schema fields."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_chart("AAPL", "1d", "5m")

        assert {"ticker", "period", "interval", "candles", "data_source"}.issubset(result.keys())

    def test_fallback_yfinance_called_with_period_interval(self):
        """yfinance Ticker.history is called with the original period and interval."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            svc.get_chart("AAPL", "3mo", "1d")

        mock_ticker.history.assert_called_once_with(period="3mo", interval="1d")

    def test_unmapped_pair_skips_webull_uses_yfinance(self):
        """If (period, interval) not in PERIOD_INTERVAL_MAP, Webull is skipped."""
        wb_client = _make_webull_client()
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        # "6mo" / "1wk" is not in PERIOD_INTERVAL_MAP
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_chart("AAPL", "6mo", "1wk")

        wb_client.fetch_bars.assert_not_called()
        assert result["data_source"] == "yfinance"

    def test_fallback_warning_logged_on_webull_unavailable(self, caplog):
        """WebullUnavailableError causes a WARNING log with ticker info."""
        import logging
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with caplog.at_level(logging.WARNING, logger="backend.market.service"):
            with patch("yfinance.Ticker", return_value=mock_ticker):
                svc.get_chart("AAPL", "1d", "5m")

        assert any("AAPL" in r.message for r in caplog.records)
        assert any(r.levelname == "WARNING" for r in caplog.records)


# ---------------------------------------------------------------------------
# data_source bypasses
# ---------------------------------------------------------------------------

class TestDataSourceBypasses:
    def test_yfinance_data_source_skips_webull(self):
        """data_source='yfinance' skips Webull even for mapped period/interval."""
        wb_client = _make_webull_client()
        svc = _make_service(data_source="yfinance", webull_client=wb_client)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_chart("AAPL", "1d", "5m")

        wb_client.fetch_bars.assert_not_called()
        assert result["data_source"] == "yfinance"

    def test_stub_data_source_raises_503(self):
        """data_source='stub' raises HTTPException 503 immediately."""
        svc = _make_service(data_source="stub")

        with pytest.raises(HTTPException) as exc_info:
            svc.get_chart("AAPL", "1d", "5m")

        assert exc_info.value.status_code == 503

    def test_webull_client_none_falls_through_to_yfinance(self):
        """data_source='webull' with None client falls through to yfinance."""
        svc = _make_service(data_source="webull", webull_client=None)
        hist = _make_yfinance_hist()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = svc.get_chart("AAPL", "1d", "5m")

        assert result["data_source"] == "yfinance"


# ---------------------------------------------------------------------------
# Both providers fail → 503
# ---------------------------------------------------------------------------

class TestBothProvidersFail:
    def test_raises_503_when_both_fail(self):
        """HTTPException 503 when Webull raises and yfinance returns empty."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)

        import pandas as pd
        empty_hist = pd.DataFrame()
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = empty_hist

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_chart("AAPL", "1d", "5m")

        assert exc_info.value.status_code == 503

    def test_503_detail_contains_ticker(self):
        """503 detail message includes the failing ticker."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)

        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_chart("TSLA", "1d", "5m")

        assert "TSLA" in exc_info.value.detail

    def test_raises_503_when_yfinance_raises_exception(self):
        """503 raised when yfinance itself throws an exception."""
        wb_client = _make_webull_client(raise_error=True)
        svc = _make_service(webull_client=wb_client)

        with patch("yfinance.Ticker", side_effect=Exception("network error")):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_chart("GOOG", "1d", "5m")

        assert exc_info.value.status_code == 503

    def test_yfinance_source_raises_503_on_empty_hist(self):
        """data_source='yfinance' with empty history raises 503."""
        svc = _make_service(data_source="yfinance", webull_client=None)

        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("yfinance.Ticker", return_value=mock_ticker):
            with pytest.raises(HTTPException) as exc_info:
                svc.get_chart("XYZ", "1d", "5m")

        assert exc_info.value.status_code == 503
