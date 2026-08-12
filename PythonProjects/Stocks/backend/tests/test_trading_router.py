"""
Integration tests for the trading router (/trading/* endpoints).

Strategy
--------
- FastAPI TestClient drives the full request/response cycle.
- TradingService is patched at the *module* level so no database or
  trading engine is needed.
- get_current_user dependency is overridden to return a fake user.
- get_db dependency is overridden to return None (never reaches the DB).

Requirements validated: R4.2, R5.1–R5.8, R7.5
"""

import sys
import os
import uuid
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Path setup — make backend/ importable
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point at SQLite so the database module doesn't try to reach PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# ---------------------------------------------------------------------------
# Fake user fixture shared across tests
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()


class FakeUser:
    id = FAKE_USER_ID
    email = "trader@example.com"
    name = "Test Trader"
    is_active = True
    theme_preference = "dark"
    created_at = datetime(2024, 1, 1)


# ---------------------------------------------------------------------------
# Helpers to build canonical service return values
# ---------------------------------------------------------------------------

def _account_summary() -> dict:
    return {
        "account_id": str(uuid.uuid4()),
        "cash": 95_000.0,
        "portfolio_value": 5_000.0,
        "total_value": 100_000.0,
        "buying_power": 95_000.0,
        "total_return": 0.0,
        "total_return_pct": 0.0,
        "num_positions": 1,
        "num_pending_orders": 0,
        "created_at": datetime(2024, 1, 1).isoformat(),
    }


def _order_filled() -> dict:
    return {
        "status": "filled",
        "order_id": str(uuid.uuid4()),
        "filled_price": 150.0,
        "filled_quantity": 10,
        "commission": 0.0,
        "slippage": 0.15,
        "reason": None,
    }


def _order_pending() -> dict:
    return {
        "status": "pending",
        "order_id": str(uuid.uuid4()),
        "filled_price": None,
        "filled_quantity": 0,
        "commission": 0.0,
        "slippage": 0.0,
        "reason": None,
    }


def _order_rejected(reason: str = "Insufficient buying power") -> dict:
    return {
        "status": "rejected",
        "order_id": None,
        "filled_price": None,
        "filled_quantity": None,
        "commission": None,
        "slippage": None,
        "reason": reason,
    }


def _order_history_item(order_id: str | None = None, status: str = "filled") -> dict:
    return {
        "order_id": order_id or str(uuid.uuid4()),
        "ticker": "AAPL",
        "side": "buy",
        "order_type": "market",
        "quantity": 10,
        "limit_price": None,
        "stop_price": None,
        "status": status,
        "filled_price": 150.0 if status == "filled" else None,
        "filled_quantity": 10 if status == "filled" else 0,
        "commission": 0.0,
        "slippage": 0.15,
        "created_at": datetime(2024, 1, 2).isoformat(),
        "filled_at": datetime(2024, 1, 2).isoformat() if status == "filled" else None,
    }


def _position() -> dict:
    return {
        "ticker": "AAPL",
        "quantity": 10,
        "avg_entry_price": 148.0,
        "current_price": 155.0,
        "market_value": 1550.0,
        "unrealized_pnl": 70.0,
        "unrealized_pnl_pct": 4.73,
        "cost_basis": 1480.0,
    }


# ---------------------------------------------------------------------------
# App fixture — patch TradingService once per test module
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
# Helpers — patch TradingService constructor + method
# ---------------------------------------------------------------------------

def _make_service_mock(**method_overrides) -> MagicMock:
    """Return a MagicMock TradingService instance with sensible defaults."""
    mock = MagicMock()
    mock.get_account_summary.return_value = _account_summary()
    mock.place_order.return_value = _order_filled()
    mock.get_orders.return_value = [_order_history_item()]
    mock.get_positions.return_value = [_position()]
    mock.cancel_order.return_value = True
    mock.reset_account.return_value = None
    for method, value in method_overrides.items():
        getattr(mock, method).return_value = value
    return mock


# ---------------------------------------------------------------------------
# GET /trading/account
# ---------------------------------------------------------------------------

class TestGetAccount:
    def test_returns_200_with_summary(self, client):
        """GET /trading/account returns a 200 with account summary fields (R7.5)."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.get("/trading/account")
        assert resp.status_code == 200
        data = resp.json()
        assert "account_id" in data
        assert data["cash"] == 95_000.0
        assert data["total_value"] == 100_000.0
        assert data["num_positions"] == 1

    def test_service_called_with_correct_user(self, client):
        """TradingService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc) as mock_cls:
            client.get("/trading/account")
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID

    def test_unauthenticated_returns_401(self, app):
        """Endpoint requires authentication — no token → 401."""
        from dependencies import get_current_user
        from fastapi import HTTPException

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/trading/account")
        # Restore
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /trading/orders
# ---------------------------------------------------------------------------

class TestPlaceOrder:
    _market_buy = {
        "ticker": "AAPL",
        "side": "buy",
        "order_type": "market",
        "quantity": 10,
    }

    def test_market_order_filled_returns_201(self, client):
        """Successful market order returns 201 with filled status (R5.5)."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=self._market_buy)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "filled"
        assert data["filled_price"] == 150.0
        assert data["filled_quantity"] == 10

    def test_limit_order_pending_returns_201(self, client):
        """Limit order placed successfully returns pending status."""
        mock_svc = _make_service_mock(place_order=_order_pending())
        payload = {
            "ticker": "TSLA",
            "side": "buy",
            "order_type": "limit",
            "quantity": 5,
            "limit_price": 200.0,
        }
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

    def test_rejected_order_returns_201_with_rejected_status(self, client):
        """Rejected orders (insufficient funds) return 201 with rejected status."""
        mock_svc = _make_service_mock(place_order=_order_rejected())
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=self._market_buy)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["reason"] == "Insufficient buying power"

    def test_ticker_is_uppercased(self, client):
        """Ticker is normalised to uppercase before being forwarded (R5.6 validation)."""
        mock_svc = _make_service_mock()
        payload = {**self._market_buy, "ticker": "aapl"}
        with patch("trading.router.TradingService", return_value=mock_svc):
            client.post("/trading/orders", json=payload)
        _, kwargs = mock_svc.place_order.call_args
        assert kwargs["ticker"] == "AAPL"

    def test_invalid_side_returns_422(self, client):
        """Invalid side value triggers Pydantic validation error (R5.6)."""
        payload = {**self._market_buy, "side": "long"}
        with patch("trading.router.TradingService", return_value=_make_service_mock()):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 422

    def test_invalid_order_type_returns_422(self, client):
        """Invalid order_type triggers Pydantic validation error (R5.6)."""
        payload = {**self._market_buy, "order_type": "twap"}
        with patch("trading.router.TradingService", return_value=_make_service_mock()):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 422

    def test_zero_quantity_returns_422(self, client):
        """quantity <= 0 triggers validation error (R5.6)."""
        payload = {**self._market_buy, "quantity": 0}
        with patch("trading.router.TradingService", return_value=_make_service_mock()):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 422

    def test_negative_quantity_returns_422(self, client):
        """Negative quantity triggers validation error (R5.6)."""
        payload = {**self._market_buy, "quantity": -5}
        with patch("trading.router.TradingService", return_value=_make_service_mock()):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 422

    def test_stop_limit_order_with_prices(self, client):
        """Stop-limit order body passes limit_price and stop_price through."""
        mock_svc = _make_service_mock(place_order=_order_pending())
        payload = {
            "ticker": "NVDA",
            "side": "sell",
            "order_type": "stop_limit",
            "quantity": 3,
            "limit_price": 490.0,
            "stop_price": 495.0,
        }
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 201
        _, kwargs = mock_svc.place_order.call_args
        assert kwargs["limit_price"] == 490.0
        assert kwargs["stop_price"] == 495.0

    def test_decimal_fields_coerced_to_float(self, client):
        """filled_price, commission, slippage are returned as floats, not Decimals."""
        from decimal import Decimal

        decimal_result = {
            "status": "filled",
            "order_id": str(uuid.uuid4()),
            "filled_price": Decimal("152.35"),
            "filled_quantity": 10,
            "commission": Decimal("0.00"),
            "slippage": Decimal("0.15"),
            "reason": None,
        }
        mock_svc = _make_service_mock(place_order=decimal_result)
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=self._market_buy)
        assert resp.status_code == 201
        data = resp.json()
        assert isinstance(data["filled_price"], float)
        assert data["filled_price"] == pytest.approx(152.35)


# ---------------------------------------------------------------------------
# GET /trading/orders
# ---------------------------------------------------------------------------

class TestGetOrders:
    def test_returns_list_of_orders(self, client):
        """GET /trading/orders returns a list with expected fields (R7.5)."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.get("/trading/orders")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["status"] == "filled"

    def test_empty_orders_returns_empty_list(self, client):
        """GET /trading/orders returns [] when no orders exist."""
        mock_svc = _make_service_mock(get_orders=[])
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.get("/trading/orders")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_pending_and_filled_orders_returned(self, client):
        """Both pending and completed orders appear in the response."""
        orders = [
            _order_history_item(status="filled"),
            _order_history_item(status="pending"),
        ]
        mock_svc = _make_service_mock(get_orders=orders)
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.get("/trading/orders")
        statuses = {o["status"] for o in resp.json()}
        assert "filled" in statuses
        assert "pending" in statuses


# ---------------------------------------------------------------------------
# DELETE /trading/orders/{order_id}
# ---------------------------------------------------------------------------

class TestCancelOrder:
    def test_cancel_pending_order_returns_200(self, client):
        """DELETE /trading/orders/{id} cancels a pending order and returns 200."""
        mock_svc = _make_service_mock(cancel_order=True)
        oid = str(uuid.uuid4())
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.delete(f"/trading/orders/{oid}")
        assert resp.status_code == 200
        assert oid in resp.json()["message"]

    def test_cancel_nonexistent_order_returns_404(self, client):
        """DELETE /trading/orders/{id} returns 404 when order not found."""
        mock_svc = _make_service_mock(cancel_order=False)
        oid = str(uuid.uuid4())
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.delete(f"/trading/orders/{oid}")
        assert resp.status_code == 404

    def test_cancel_service_called_with_order_id(self, client):
        """cancel_order service method receives the correct order_id."""
        mock_svc = _make_service_mock(cancel_order=True)
        oid = str(uuid.uuid4())
        with patch("trading.router.TradingService", return_value=mock_svc):
            client.delete(f"/trading/orders/{oid}")
        mock_svc.cancel_order.assert_called_once_with(oid)


# ---------------------------------------------------------------------------
# POST /trading/reset
# ---------------------------------------------------------------------------

class TestResetAccount:
    def test_reset_returns_200_with_new_balance(self, client):
        """POST /trading/reset returns 200 with new_balance of 100 000 (R4.2)."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/reset")
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_balance"] == 100_000.0
        assert "reset" in data["message"].lower()

    def test_reset_calls_service_reset(self, client):
        """POST /trading/reset calls service.reset_account() exactly once."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc):
            client.post("/trading/reset")
        mock_svc.reset_account.assert_called_once()


# ---------------------------------------------------------------------------
# GET /trading/positions
# ---------------------------------------------------------------------------

class TestGetPositions:
    def test_returns_list_of_positions(self, client):
        """GET /trading/positions returns a list with expected fields."""
        mock_svc = _make_service_mock()
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.get("/trading/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["ticker"] == "AAPL"
        assert data[0]["quantity"] == 10

    def test_empty_positions_returns_empty_list(self, client):
        """GET /trading/positions returns [] when no open positions exist."""
        mock_svc = _make_service_mock(get_positions=[])
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.get("/trading/positions")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Schema validation edge cases
# ---------------------------------------------------------------------------

class TestOrderSchemas:
    def test_missing_required_fields_returns_422(self, client):
        """Payload without required fields returns 422 Unprocessable Entity."""
        with patch("trading.router.TradingService", return_value=_make_service_mock()):
            resp = client.post("/trading/orders", json={"ticker": "AAPL"})
        assert resp.status_code == 422

    def test_sell_side_is_valid(self, client):
        """side='sell' is accepted as a valid value."""
        mock_svc = _make_service_mock()
        payload = {
            "ticker": "AAPL",
            "side": "sell",
            "order_type": "market",
            "quantity": 5,
        }
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 201

    def test_stop_loss_order_type_is_valid(self, client):
        """order_type='stop_loss' is accepted."""
        mock_svc = _make_service_mock(place_order=_order_pending())
        payload = {
            "ticker": "SPY",
            "side": "sell",
            "order_type": "stop_loss",
            "quantity": 2,
            "stop_price": 400.0,
        }
        with patch("trading.router.TradingService", return_value=mock_svc):
            resp = client.post("/trading/orders", json=payload)
        assert resp.status_code == 201
