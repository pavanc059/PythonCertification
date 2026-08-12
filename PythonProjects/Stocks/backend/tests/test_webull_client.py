"""
Unit tests for WebullClient — official SDK-based implementation.

Tests cover:
  - Construction: ApiClient/DataClient wired up correctly, no trading_pin param
  - fetch_quote(): success, non-200, empty response, retry, backoff
  - fetch_bars(): success, non-200, empty response, interval passthrough, dict response
  - fetch_news(): always raises WebullUnavailableError
  - fetch_movers(): always raises WebullUnavailableError
  - _check_not_empty(): kept from original
  - _normalize_webull_quote(): kept + updated for SDK field names (changeRate, name)
"""

from __future__ import annotations

import inspect
import sys
from unittest.mock import MagicMock, patch

import pytest

from backend.webull_client.client import WebullClient, WebullUnavailableError
from backend.webull_client.types import WebullQuoteData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client_with_mocks(
    app_key: str = "ak",
    app_secret: str = "as",
    region_id: str = "us",
    endpoint: str = "api.webull.com",
):
    """Return (client, mock_data_client, mock_api_client) with webull SDK mocked.

    The lazy imports inside WebullClient.__init__ are intercepted via
    sys.modules patching so no real webull SDK is required.
    """
    mock_api_client = MagicMock()
    mock_data_client = MagicMock()

    mock_core_module = MagicMock()
    mock_core_module.ApiClient = MagicMock(return_value=mock_api_client)
    mock_data_module = MagicMock()
    mock_data_module.DataClient = MagicMock(return_value=mock_data_client)

    with patch.dict(
        sys.modules,
        {
            "webull": MagicMock(),
            "webull.core": MagicMock(),
            "webull.core.client": mock_core_module,
            "webull.data": MagicMock(),
            "webull.data.data_client": mock_data_module,
        },
    ):
        client = WebullClient(
            app_key=app_key,
            app_secret=app_secret,
            region_id=region_id,
            endpoint=endpoint,
        )

    # Expose the mocks captured during construction
    return client, mock_data_client, mock_api_client, mock_core_module, mock_data_module


def _make_client(app_key: str = "ak", app_secret: str = "as",
                 region_id: str = "us", endpoint: str = "api.webull.com"):
    """Convenience wrapper that returns only (client, mock_data_client)."""
    client, mock_data_client, *_ = _make_client_with_mocks(
        app_key=app_key, app_secret=app_secret,
        region_id=region_id, endpoint=endpoint,
    )
    return client, mock_data_client


# ---------------------------------------------------------------------------
# TestWebullClientConstruction
# ---------------------------------------------------------------------------

class TestWebullClientConstruction:
    def test_constructs_api_client_with_correct_args(self):
        """ApiClient is called with (app_key, app_secret, region_id)."""
        mock_api_client = MagicMock()

        mock_core_module = MagicMock()
        mock_api_cls = MagicMock(return_value=mock_api_client)
        mock_core_module.ApiClient = mock_api_cls

        mock_data_module = MagicMock()
        mock_data_module.DataClient = MagicMock(return_value=MagicMock())

        with patch.dict(
            sys.modules,
            {
                "webull": MagicMock(),
                "webull.core": MagicMock(),
                "webull.core.client": mock_core_module,
                "webull.data": MagicMock(),
                "webull.data.data_client": mock_data_module,
            },
        ):
            WebullClient(app_key="my-key", app_secret="my-secret", region_id="us")

        mock_api_cls.assert_called_once_with("my-key", "my-secret", "us")

    def test_calls_add_endpoint(self):
        """api_client.add_endpoint(region_id, endpoint) is called."""
        mock_api_client = MagicMock()

        mock_core_module = MagicMock()
        mock_core_module.ApiClient = MagicMock(return_value=mock_api_client)
        mock_data_module = MagicMock()
        mock_data_module.DataClient = MagicMock(return_value=MagicMock())

        with patch.dict(
            sys.modules,
            {
                "webull": MagicMock(),
                "webull.core": MagicMock(),
                "webull.core.client": mock_core_module,
                "webull.data": MagicMock(),
                "webull.data.data_client": mock_data_module,
            },
        ):
            WebullClient(app_key="k", app_secret="s",
                         region_id="us", endpoint="api.webull.com")

        mock_api_client.add_endpoint.assert_called_once_with("us", "api.webull.com")

    def test_constructs_data_client_with_api_client(self):
        """DataClient is called with the ApiClient instance."""
        mock_api_client = MagicMock()
        mock_data_cls = MagicMock(return_value=MagicMock())

        mock_core_module = MagicMock()
        mock_core_module.ApiClient = MagicMock(return_value=mock_api_client)
        mock_data_module = MagicMock()
        mock_data_module.DataClient = mock_data_cls

        with patch.dict(
            sys.modules,
            {
                "webull": MagicMock(),
                "webull.core": MagicMock(),
                "webull.core.client": mock_core_module,
                "webull.data": MagicMock(),
                "webull.data.data_client": mock_data_module,
            },
        ):
            WebullClient(app_key="k", app_secret="s", region_id="us")

        mock_data_cls.assert_called_once_with(mock_api_client)

    def test_no_trading_pin_parameter(self):
        """WebullClient.__init__ must NOT accept a trading_pin parameter."""
        sig = inspect.signature(WebullClient.__init__)
        assert "trading_pin" not in sig.parameters, (
            "trading_pin must not be a parameter of WebullClient.__init__"
        )


# ---------------------------------------------------------------------------
# TestFetchQuote
# ---------------------------------------------------------------------------

class TestFetchQuote:
    def test_returns_dict_on_200(self):
        """fetch_quote returns the raw dict when status_code==200."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"close": 150.0, "volume": 1_000}
        mock_dc.market_data.get_snapshot.return_value = mock_resp

        result = client.fetch_quote("AAPL")

        assert result == {"close": 150.0, "volume": 1_000}
        mock_dc.market_data.get_snapshot.assert_called_once()

    def test_raises_on_non_200(self):
        """fetch_quote raises WebullUnavailableError after 3 retries on 401."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_dc.market_data.get_snapshot.return_value = mock_resp

        with patch("time.sleep"):
            with pytest.raises(WebullUnavailableError):
                client.fetch_quote("AAPL")

    def test_raises_on_empty_response(self):
        """fetch_quote raises ValueError when json() returns {} (no close key).

        _check_not_empty raises ValueError for empty/missing price data.
        """
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_dc.market_data.get_snapshot.return_value = mock_resp

        with pytest.raises(ValueError, match="Empty response for AAPL"):
            client.fetch_quote("AAPL")

    def test_retries_3_times_on_failure(self):
        """fetch_quote retries 3 times before raising on status 500."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_dc.market_data.get_snapshot.return_value = mock_resp

        with patch("time.sleep"):
            with pytest.raises(WebullUnavailableError):
                client.fetch_quote("AAPL")

        assert mock_dc.market_data.get_snapshot.call_count == 3

    def test_exponential_backoff(self):
        """sleep is called with 2, 4 seconds between retries."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_dc.market_data.get_snapshot.return_value = mock_resp

        sleep_calls = []
        with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            with pytest.raises(WebullUnavailableError):
                client.fetch_quote("AAPL")

        assert sleep_calls == [2, 4]

    def test_no_trading_pin_passed(self):
        """trading_pin is never passed in any call during fetch_quote."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"close": 100.0}
        mock_dc.market_data.get_snapshot.return_value = mock_resp

        client.fetch_quote("AAPL")

        for c in mock_dc.method_calls:
            assert "trading_pin" not in c.kwargs


# ---------------------------------------------------------------------------
# TestFetchBars
# ---------------------------------------------------------------------------

class TestFetchBars:
    def test_returns_list_on_200(self):
        """fetch_bars returns list of bar dicts on success."""
        client, mock_dc = _make_client()

        bars = [{"open": 1.0, "close": 2.0, "timestamp": "2024-01-01"}]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = bars
        mock_dc.market_data.get_history_bar.return_value = mock_resp

        result = client.fetch_bars("AAPL", interval="M5")

        assert result == bars

    def test_raises_on_non_200(self):
        """fetch_bars raises WebullUnavailableError on status 500."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_dc.market_data.get_history_bar.return_value = mock_resp

        with patch("time.sleep"):
            with pytest.raises(WebullUnavailableError):
                client.fetch_bars("AAPL", interval="M5")

    def test_raises_on_empty_list(self):
        """fetch_bars raises WebullUnavailableError when json() returns []."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_dc.market_data.get_history_bar.return_value = mock_resp

        with pytest.raises(WebullUnavailableError):
            client.fetch_bars("AAPL", interval="M5")

    def test_uppercase_interval_passed(self):
        """fetch_bars passes interval='M5' unchanged to get_history_bar."""
        client, mock_dc = _make_client()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"open": 1.0}]
        mock_dc.market_data.get_history_bar.return_value = mock_resp

        client.fetch_bars("AAPL", interval="M5")

        # The SDK should receive "M5" (not "m5")
        call_args = mock_dc.market_data.get_history_bar.call_args
        positional = call_args.args
        assert "M5" in positional, (
            f"Expected 'M5' in positional args {positional}"
        )

    def test_handles_dict_response(self):
        """fetch_bars converts dict response to list of values."""
        client, mock_dc = _make_client()

        raw_dict = {"0": {"open": 1.0}, "1": {"open": 2.0}}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = raw_dict
        mock_dc.market_data.get_history_bar.return_value = mock_resp

        result = client.fetch_bars("AAPL", interval="D1")

        assert isinstance(result, list)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestFetchNewsAlwaysRaises
# ---------------------------------------------------------------------------

class TestFetchNewsAlwaysRaises:
    def test_fetch_news_raises_webull_unavailable(self):
        """fetch_news always raises WebullUnavailableError, no SDK call made."""
        client, mock_dc = _make_client()

        with pytest.raises(WebullUnavailableError):
            client.fetch_news("AAPL")

        # No SDK calls should have been made
        mock_dc.market_data.get_snapshot.assert_not_called()
        mock_dc.market_data.get_history_bar.assert_not_called()


# ---------------------------------------------------------------------------
# TestFetchMoversAlwaysRaises
# ---------------------------------------------------------------------------

class TestFetchMoversAlwaysRaises:
    def test_fetch_movers_raises_webull_unavailable(self):
        """fetch_movers always raises WebullUnavailableError, no SDK call made."""
        client, mock_dc = _make_client()

        with pytest.raises(WebullUnavailableError):
            client.fetch_movers()

        # No SDK calls should have been made
        mock_dc.market_data.get_snapshot.assert_not_called()
        mock_dc.market_data.get_history_bar.assert_not_called()


# ---------------------------------------------------------------------------
# _check_not_empty() — kept from original
# ---------------------------------------------------------------------------

class TestCheckNotEmpty:
    def _client(self) -> WebullClient:
        client, _ = _make_client()
        return client

    def test_raises_on_none(self):
        client = self._client()
        with pytest.raises(ValueError, match="Empty response for AAPL"):
            client._check_not_empty(None, "AAPL")

    def test_raises_on_dict_without_price_keys(self):
        client = self._client()
        with pytest.raises(ValueError, match="Empty response for TSLA"):
            client._check_not_empty({"someKey": "value"}, "TSLA")

    def test_passes_for_dict_with_close_key(self):
        client = self._client()
        # Should not raise
        client._check_not_empty({"close": 150.0}, "AAPL")

    def test_passes_for_dict_with_price_key(self):
        client = self._client()
        client._check_not_empty({"price": 200.0, "volume": 100}, "MSFT")

    def test_passes_for_dict_with_latest_price_key(self):
        client = self._client()
        client._check_not_empty({"latestPrice": 300.0}, "GOOG")

    def test_passes_for_non_dict_non_none(self):
        client = self._client()
        # A list or other non-None value that isn't a dict passes through
        client._check_not_empty([{"close": 1}], "SPY")


# ---------------------------------------------------------------------------
# _normalize_webull_quote() — updated for SDK field names
# ---------------------------------------------------------------------------

class TestNormalizeWebullQuote:
    """Tests for WebullClient._normalize_webull_quote().

    Requirements: 14.1, 14.2, 14.3, 14.5

    Field name updates from unofficial → official SDK:
      - changeRatio → changeRate  (primary; changeRatio kept as fallback)
      - name → primary company name field  (companyName kept as fallback)
    """

    def _client(self) -> WebullClient:
        client, _ = _make_client()
        return client

    # --- success: full response ----------------------------------------

    def test_full_response_maps_all_fields(self):
        """All fields present in raw dict map correctly to WebullQuoteData."""
        client = self._client()
        raw = {
            "close": 150.25,
            "name": "Apple Inc.",
            "change": -1.50,
            "changeRate": -0.0099,
            "volume": 75_000_000,
            "high": 152.00,
            "low": 149.00,
            "week52High": 198.23,
            "week52Low": 124.17,
            "marketValue": 2_400_000_000_000.0,
        }
        result = client._normalize_webull_quote(raw, "AAPL")

        assert result.ticker == "AAPL"
        assert result.company_name == "Apple Inc."
        assert result.price == 150.25
        assert result.change == -1.50
        assert result.change_pct == -0.0099
        assert result.volume == 75_000_000
        assert result.day_high == 152.00
        assert result.day_low == 149.00
        assert result.week_52_high == 198.23
        assert result.week_52_low == 124.17
        assert result.market_cap == 2_400_000_000_000.0
        assert result.source == "webull"

    def test_source_always_set_to_webull(self):
        """source is always 'webull' regardless of raw content."""
        client = self._client()
        raw = {"close": 100.0, "name": "Test Corp"}
        result = client._normalize_webull_quote(raw, "TEST")
        assert result.source == "webull"

    # --- company_name: name is primary, companyName is fallback --------

    def test_company_name_from_name_field(self):
        """Official SDK 'name' field is used as the primary company_name source."""
        client = self._client()
        raw = {"close": 50.0, "name": "Primary Name", "companyName": "Secondary Name"}
        result = client._normalize_webull_quote(raw, "SYM")
        assert result.company_name == "Primary Name"

    def test_company_name_falls_back_to_companyName_field(self):
        """Falls back to 'companyName' when 'name' is absent."""
        client = self._client()
        raw = {"close": 50.0, "companyName": "Fallback Corp"}
        result = client._normalize_webull_quote(raw, "SYM")
        assert result.company_name == "Fallback Corp"

    def test_company_name_falls_back_to_ticker_when_both_absent(self):
        """Falls back to ticker symbol when both company name fields are absent."""
        client = self._client()
        raw = {"close": 50.0}
        result = client._normalize_webull_quote(raw, "MYSYM")
        assert result.company_name == "MYSYM"

    # --- change_pct: changeRate is primary, changeRatio is fallback ----

    def test_change_pct_uses_changeRate(self):
        """Official SDK 'changeRate' is used as the primary change_pct source."""
        client = self._client()
        raw = {"close": 100.0, "changeRate": 0.025, "changeRatio": 0.999}
        result = client._normalize_webull_quote(raw, "SYM")
        assert result.change_pct == 0.025

    def test_change_pct_falls_back_to_changeRatio(self):
        """Falls back to 'changeRatio' when 'changeRate' is absent."""
        client = self._client()
        raw = {"close": 100.0, "changeRatio": -0.03}
        result = client._normalize_webull_quote(raw, "SYM")
        assert result.change_pct == -0.03

    # --- market_cap fallback to totalMarketValue ------------------------

    def test_market_cap_uses_marketValue(self):
        """'marketValue' is preferred for market_cap."""
        client = self._client()
        raw = {
            "close": 200.0,
            "marketValue": 1_000_000.0,
            "totalMarketValue": 9_999.0,
        }
        result = client._normalize_webull_quote(raw, "X")
        assert result.market_cap == 1_000_000.0

    def test_market_cap_falls_back_to_totalMarketValue(self):
        """Falls back to 'totalMarketValue' when 'marketValue' is absent."""
        client = self._client()
        raw = {"close": 200.0, "totalMarketValue": 5_000_000.0}
        result = client._normalize_webull_quote(raw, "X")
        assert result.market_cap == 5_000_000.0

    # --- optional fields set to None when absent -----------------------

    def test_optional_fields_are_none_when_absent(self):
        """Optional fields default to None when missing from raw dict (Req 14.3)."""
        client = self._client()
        raw = {"close": 42.0}  # only required field
        result = client._normalize_webull_quote(raw, "MIN")

        assert result.volume is None
        assert result.day_high is None
        assert result.day_low is None
        assert result.week_52_high is None
        assert result.week_52_low is None
        assert result.market_cap is None

    # --- change/change_pct default to 0.0 when absent ------------------

    def test_change_defaults_to_zero_when_absent(self):
        client = self._client()
        raw = {"close": 10.0}
        result = client._normalize_webull_quote(raw, "Z")
        assert result.change == 0.0

    def test_change_pct_defaults_to_zero_when_absent(self):
        client = self._client()
        raw = {"close": 10.0}
        result = client._normalize_webull_quote(raw, "Z")
        assert result.change_pct == 0.0

    # --- type coercion --------------------------------------------------

    def test_price_coerced_to_float(self):
        """Integer close value is coerced to float."""
        client = self._client()
        raw = {"close": 100}  # int, not float
        result = client._normalize_webull_quote(raw, "INT")
        assert isinstance(result.price, float)
        assert result.price == 100.0

    def test_volume_coerced_to_int(self):
        """Float volume value is coerced to int."""
        client = self._client()
        raw = {"close": 50.0, "volume": 1_234_567.9}
        result = client._normalize_webull_quote(raw, "VOL")
        assert isinstance(result.volume, int)

    # --- error cases (Req 14.5) ----------------------------------------

    def test_raises_when_price_is_none(self):
        """Raises WebullUnavailableError when close is None (Req 14.5)."""
        client = self._client()
        raw = {"close": None, "name": "Broken Corp"}
        with pytest.raises(WebullUnavailableError, match="Invalid price for FAIL"):
            client._normalize_webull_quote(raw, "FAIL")

    def test_raises_when_price_is_zero(self):
        """Raises WebullUnavailableError when close is 0 (Req 14.5)."""
        client = self._client()
        raw = {"close": 0, "name": "Zero Corp"}
        with pytest.raises(WebullUnavailableError, match="Invalid price for ZERO"):
            client._normalize_webull_quote(raw, "ZERO")

    def test_raises_when_close_key_absent(self):
        """Raises WebullUnavailableError when close key is entirely absent."""
        client = self._client()
        raw = {"name": "No Price Corp", "volume": 1000}
        with pytest.raises(WebullUnavailableError, match="Invalid price for NPC"):
            client._normalize_webull_quote(raw, "NPC")

    # --- ticker passthrough ---------------------------------------------

    def test_ticker_matches_argument_not_raw_symbol(self):
        """The ticker in the result is always the argument, not raw 'symbol'."""
        client = self._client()
        raw = {"close": 100.0, "symbol": "WRONG", "tickerId": 12345}
        result = client._normalize_webull_quote(raw, "CORRECT")
        assert result.ticker == "CORRECT"

    # --- returns WebullQuoteData instance --------------------------------

    def test_returns_webull_quote_data_instance(self):
        client = self._client()
        raw = {"close": 99.99}
        result = client._normalize_webull_quote(raw, "T")
        assert isinstance(result, WebullQuoteData)
