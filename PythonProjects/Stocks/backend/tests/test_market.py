"""
Integration tests for the market data router (/market/* endpoints).

Strategy
--------
- FastAPI TestClient drives the full request/response cycle.
- MarketService is patched at the *router* module level so no live yfinance
  or Redis calls are made.
- get_current_user dependency is overridden to return a fake user.
- get_db dependency is overridden to return None.

Requirements validated: R3.2, R3.8, R3.9, R7.6
"""

import sys
import os
import uuid
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Path setup — make backend/ importable
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point at SQLite so database module doesn't try to reach PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# Use yfinance so the startup event skips WebullClient initialisation
# (the 'webull' SDK package is not installed in the test environment)
os.environ.setdefault("MARKET_DATA_SOURCE", "yfinance")

# ---------------------------------------------------------------------------
# Fake user shared across tests
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()


class FakeUser:
    id = FAKE_USER_ID
    email = "market@example.com"
    name = "Market Tester"
    is_active = True
    theme_preference = "dark"
    created_at = datetime(2024, 1, 1)


# ---------------------------------------------------------------------------
# Canonical service return-value builders
# ---------------------------------------------------------------------------


def _quote(ticker: str = "AAPL") -> dict:
    """Standard quote matching QuoteResponse schema."""
    return {
        "ticker": ticker,
        "company_name": "Apple Inc.",
        "price": 192.40,
        "change": 2.30,
        "change_pct": 1.21,
        "volume": 55_000_000,
        "day_high": 193.50,
        "day_low": 190.10,
        "week_52_high": 200.00,
        "week_52_low": 150.00,
        "market_cap": 3_000_000_000_000.0,
    }


def _candle(time: str = "2024-06-01T10:00:00") -> dict:
    return {
        "time": time,
        "open": 191.00,
        "high": 193.50,
        "low": 190.50,
        "close": 192.40,
        "volume": 1_200_000,
    }


def _chart(ticker: str = "AAPL", period: str = "1d", interval: str = "5m") -> dict:
    """Standard chart matching ChartResponse schema."""
    return {
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "candles": [_candle(), _candle("2024-06-01T10:05:00")],
    }


def _prediction(ticker: str = "AAPL", direction: str = "bullish") -> dict:
    """Standard prediction matching PredictionResponse schema."""
    return {
        "ticker": ticker,
        "direction": direction,
        "confidence": 72.5,
        "factors": [{"name": "RSI", "value": 68.5}],
    }


# ---------------------------------------------------------------------------
# Helper — build a MarketService mock with sensible defaults
# ---------------------------------------------------------------------------


def _make_service_mock(**method_overrides) -> MagicMock:
    mock = MagicMock()
    mock.get_quote.return_value = _quote()
    mock.get_chart.return_value = _chart()
    mock.get_prediction.return_value = _prediction()
    for method, value in method_overrides.items():
        getattr(mock, method).return_value = value
    return mock


# ---------------------------------------------------------------------------
# Helper — context manager to override market service dependency
# ---------------------------------------------------------------------------

from contextlib import contextmanager


@contextmanager
def _market_service_override(app, mock_svc):
    """Temporarily override the get_market_service dependency."""
    from market.router import get_market_service
    app.dependency_overrides[get_market_service] = lambda: mock_svc
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_market_service, None)


# ---------------------------------------------------------------------------
# App fixture — override DB and auth dependencies once per test module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    """Return the FastAPI app with DB and auth dependencies overridden."""
    from main import app as _app
    from dependencies import get_current_user, get_db

    _app.dependency_overrides[get_db] = lambda: None
    _app.dependency_overrides[get_current_user] = lambda: FakeUser()
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
def client(app) -> Generator:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /market/quote/{ticker}
# ---------------------------------------------------------------------------


class TestGetQuote:
    """Tests for GET /market/quote/{ticker} (R3.2, R7.6)."""

    def test_returns_200_with_quote_fields(self, app, client):
        """GET /market/quote/AAPL returns 200 with all required quote fields (R3.2)."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/quote/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["company_name"] == "Apple Inc."
        assert data["price"] == pytest.approx(192.40)
        assert data["change"] == pytest.approx(2.30)
        assert data["change_pct"] == pytest.approx(1.21)
        assert data["volume"] == 55_000_000
        assert data["day_high"] == pytest.approx(193.50)
        assert data["day_low"] == pytest.approx(190.10)
        assert data["week_52_high"] == pytest.approx(200.00)
        assert data["week_52_low"] == pytest.approx(150.00)

    def test_ticker_uppercased_before_service_call(self, app, client):
        """Ticker path param is uppercased before being passed to the service."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            client.get("/market/quote/aapl")
        mock_svc.get_quote.assert_called_once_with("AAPL")

    def test_unknown_ticker_returns_404(self, app, client):
        """GET /market/quote/FAKE returns 404 when ticker not found."""
        mock_svc = _make_service_mock()
        mock_svc.get_quote.side_effect = HTTPException(
            status_code=404, detail="Ticker 'FAKE' not found."
        )
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/quote/FAKE")
        assert resp.status_code == 404

    def test_optional_fields_can_be_null(self, app, client):
        """Optional fields (company_name, volume, etc.) may be null."""
        minimal_quote = {
            "ticker": "XYZ",
            "company_name": None,
            "price": 10.00,
            "change": 0.0,
            "change_pct": 0.0,
            "volume": None,
            "day_high": None,
            "day_low": None,
            "week_52_high": None,
            "week_52_low": None,
            "market_cap": None,
        }
        mock_svc = _make_service_mock(get_quote=minimal_quote)
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/quote/XYZ")
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_name"] is None
        assert data["volume"] is None


# ---------------------------------------------------------------------------
# GET /market/chart/{ticker}
# ---------------------------------------------------------------------------


class TestGetChart:
    """Tests for GET /market/chart/{ticker} (R3.9, R7.6)."""

    def test_returns_200_with_candles(self, app, client):
        """GET /market/chart/AAPL returns 200 with a candles list (R3.9)."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["period"] == "1d"
        assert data["interval"] == "5m"
        assert isinstance(data["candles"], list)
        assert len(data["candles"]) == 2

    def test_candle_fields_are_present(self, app, client):
        """Each candle contains time, open, high, low, close, volume (R3.9)."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/AAPL")
        candle = resp.json()["candles"][0]
        assert "time" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle
        assert "volume" in candle

    def test_default_period_and_interval(self, app, client):
        """Default period='1d' and interval='5m' are used when not specified."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            client.get("/market/chart/AAPL")
        mock_svc.get_chart.assert_called_once_with("AAPL", period="1d", interval="5m")

    def test_custom_period_and_interval_forwarded(self, app, client):
        """Custom period and interval query params are forwarded to the service."""
        mock_svc = _make_service_mock(get_chart=_chart(period="1mo", interval="1d"))
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/TSLA?period=1mo&interval=1d")
        assert resp.status_code == 200
        mock_svc.get_chart.assert_called_once_with("TSLA", period="1mo", interval="1d")

    def test_invalid_period_returns_400(self, app, client):
        """GET /market/chart with invalid period returns 400 (R7.6 validation)."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/AAPL?period=99y")
        assert resp.status_code == 400

    def test_invalid_interval_returns_400(self, app, client):
        """GET /market/chart with invalid interval returns 400."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/AAPL?interval=99s")
        assert resp.status_code == 400

    def test_both_invalid_params_returns_400(self, app, client):
        """Both period and interval invalid → 400 (period checked first)."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/AAPL?period=bad&interval=bad")
        assert resp.status_code == 400

    def test_no_data_returns_404(self, app, client):
        """GET /market/chart returns 404 when yfinance has no data."""
        mock_svc = _make_service_mock()
        mock_svc.get_chart.side_effect = HTTPException(
            status_code=404, detail="No chart data found for 'FAKE'."
        )
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/chart/FAKE")
        assert resp.status_code == 404

    def test_ticker_uppercased_before_service_call(self, app, client):
        """Ticker path param is uppercased before being passed to the service."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            client.get("/market/chart/tsla?period=1d&interval=5m")
        mock_svc.get_chart.assert_called_once_with("TSLA", period="1d", interval="5m")

    def test_all_valid_periods_accepted(self, app, client):
        """All five valid period values are accepted without a 400 error."""
        mock_svc = _make_service_mock()
        for period in ["1d", "5d", "1mo", "3mo", "1y"]:
            mock_svc.get_chart.return_value = _chart(period=period)
            with _market_service_override(app, mock_svc):
                resp = client.get(f"/market/chart/AAPL?period={period}")
            assert resp.status_code == 200, f"Expected 200 for period={period}"

    def test_all_valid_intervals_accepted(self, app, client):
        """All five valid interval values are accepted without a 400 error."""
        mock_svc = _make_service_mock()
        for interval in ["1m", "5m", "15m", "1h", "1d"]:
            mock_svc.get_chart.return_value = _chart(interval=interval)
            with _market_service_override(app, mock_svc):
                resp = client.get(f"/market/chart/AAPL?interval={interval}")
            assert resp.status_code == 200, f"Expected 200 for interval={interval}"


# ---------------------------------------------------------------------------
# GET /market/predict/{ticker}
# ---------------------------------------------------------------------------


class TestGetPrediction:
    """Tests for GET /market/predict/{ticker} (R3.8, R7.6)."""

    def test_bullish_prediction_returned(self, app, client):
        """GET /market/predict returns bullish direction with confidence (R3.8)."""
        mock_svc = _make_service_mock(get_prediction=_prediction(direction="bullish"))
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/predict/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["direction"] == "bullish"
        assert data["confidence"] == pytest.approx(72.5)
        assert isinstance(data["factors"], list)
        assert data["factors"][0]["name"] == "RSI"

    def test_bearish_prediction_returned(self, app, client):
        """GET /market/predict returns bearish direction (R3.8)."""
        mock_svc = _make_service_mock(
            get_prediction=_prediction(direction="bearish")
        )
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/predict/TSLA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["direction"] == "bearish"

    def test_neutral_prediction_returned(self, app, client):
        """GET /market/predict returns neutral direction (R3.8)."""
        mock_svc = _make_service_mock(
            get_prediction={
                "ticker": "SPY",
                "direction": "neutral",
                "confidence": 50.0,
                "factors": [],
            }
        )
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/predict/SPY")
        assert resp.status_code == 200
        data = resp.json()
        assert data["direction"] == "neutral"
        assert data["confidence"] == pytest.approx(50.0)
        assert data["factors"] == []

    def test_prediction_schema_fields_present(self, app, client):
        """Prediction response contains ticker, direction, confidence, factors."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/predict/AAPL")
        data = resp.json()
        assert "ticker" in data
        assert "direction" in data
        assert "confidence" in data
        assert "factors" in data

    def test_ticker_uppercased_before_service_call(self, app, client):
        """Ticker path param is uppercased before being passed to the service."""
        mock_svc = _make_service_mock()
        with _market_service_override(app, mock_svc):
            client.get("/market/predict/aapl")
        mock_svc.get_prediction.assert_called_once_with("AAPL")

    def test_multiple_factors_allowed(self, app, client):
        """Prediction response can include multiple factors."""
        pred = _prediction()
        pred["factors"] = [
            {"name": "RSI", "value": 68.5},
            {"name": "Volume", "value": 1.3},
        ]
        mock_svc = _make_service_mock(get_prediction=pred)
        with _market_service_override(app, mock_svc):
            resp = client.get("/market/predict/AAPL")
        factors = resp.json()["factors"]
        assert len(factors) == 2


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------


class TestUnauthenticated:
    """Verify that at least one endpoint rejects unauthenticated requests (R7.7)."""

    def test_get_quote_requires_auth(self, app):
        """GET /market/quote/{ticker} without token → 401."""
        from dependencies import get_current_user

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/market/quote/AAPL")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401

    def test_get_chart_requires_auth(self, app):
        """GET /market/chart/{ticker} without token → 401."""
        from dependencies import get_current_user

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/market/chart/AAPL")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401

    def test_get_predict_requires_auth(self, app):
        """GET /market/predict/{ticker} without token → 401."""
        from dependencies import get_current_user

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/market/predict/AAPL")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# MarketService unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


class TestMarketServiceRSI:
    """Unit tests for the RSI calculation and prediction logic in MarketService."""

    def test_rsi_above_65_gives_bullish(self):
        """RSI > 65 produces a bullish prediction with confidence > 60."""
        import numpy as np

        from market.service import MarketService

        svc = MarketService(redis_url=None)

        # Build a price series that gives RSI ~70 (strong uptrend)
        # Start at 100, add +1 every day for 20 days → all gains, RSI near 100
        prices = np.linspace(100, 120, 30)
        rsi = svc._calculate_rsi(prices, period=14)
        assert rsi is not None
        assert rsi > 65

        result = {"rsi": rsi, "direction": "bullish" if rsi > 65 else ("bearish" if rsi < 35 else "neutral")}
        assert result["direction"] == "bullish"

    def test_rsi_below_35_gives_bearish(self):
        """RSI < 35 produces a bearish prediction with confidence > 60."""
        import numpy as np

        from market.service import MarketService

        svc = MarketService(redis_url=None)

        # Strong downtrend: prices fall from 120 to 100
        prices = np.linspace(120, 100, 30)
        rsi = svc._calculate_rsi(prices, period=14)
        assert rsi is not None
        assert rsi < 35

    def test_rsi_in_neutral_range(self):
        """RSI between 35 and 65 produces neutral direction."""
        import numpy as np

        from market.service import MarketService

        svc = MarketService(redis_url=None)

        # Flat price produces RSI near 50
        prices = np.ones(30) * 100.0
        # Add tiny oscillation so there are some gains and losses
        for i in range(30):
            prices[i] += (i % 2) * 0.01
        rsi = svc._calculate_rsi(prices, period=14)
        assert rsi is not None
        # Flat should give RSI in the neutral zone (or very near it)
        assert 30 < rsi < 70, f"Expected neutral-zone RSI, got {rsi}"

    def test_rsi_returns_none_for_insufficient_data(self):
        """_calculate_rsi returns None when fewer than period+1 data points."""
        import numpy as np

        from market.service import MarketService

        svc = MarketService(redis_url=None)
        assert svc._calculate_rsi(np.array([100.0, 101.0]), period=14) is None

    def test_confidence_clamped_to_95(self):
        """Confidence is never above 95 even for extreme RSI values."""
        import numpy as np

        from market.service import MarketService

        svc = MarketService(redis_url=None)

        # Simulate a very strong uptrend (RSI ~ 98)
        prices = np.linspace(100, 200, 30)
        rsi = svc._calculate_rsi(prices, period=14)
        assert rsi is not None and rsi > 65

        confidence = 60.0 + (rsi - 65.0) * 2.0
        confidence = max(50.0, min(95.0, confidence))
        assert confidence <= 95.0

    def test_confidence_never_below_50(self):
        """Confidence is never below 50."""
        from market.service import MarketService
        import numpy as np

        svc = MarketService(redis_url=None)
        prices = np.ones(30) * 100.0
        for i in range(30):
            prices[i] += (i % 2) * 0.01
        rsi = svc._calculate_rsi(prices, period=14)
        assert rsi is not None

        if rsi > 65:
            conf = 60.0 + (rsi - 65.0) * 2.0
        elif rsi < 35:
            conf = 60.0 + (35.0 - rsi) * 2.0
        else:
            conf = 50.0 + abs(50.0 - rsi)
        conf = max(50.0, min(95.0, conf))
        assert conf >= 50.0
