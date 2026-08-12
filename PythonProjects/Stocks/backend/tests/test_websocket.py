"""
Tests for the WebSocket price feed endpoint (WS /ws/prices).

Strategy
--------
- Use FastAPI TestClient's WebSocket context manager.
- Patch ``auth.service.decode_token`` to control authentication behaviour.
- Patch ``websocket.price_feed.fetch_batch_prices`` to avoid live yfinance calls.
- Tests cover R8.1 (endpoint exists), R8.2 (connect/disconnect), and the
  message protocol (subscribe ack, unsubscribe, invalid JSON resilience).

Requirements validated: R8.1, R8.2, R8.5
"""

import json
import os
import sys
import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Path setup — make backend/ importable when running from the tests/ dir
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use SQLite to avoid requiring a running PostgreSQL instance.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()
FAKE_EMAIL = "ws_test@example.com"


def _make_token_data():
    """Return a valid TokenData-like object for auth mocking."""
    from auth.schemas import TokenData

    return TokenData(user_id=FAKE_USER_ID, email=FAKE_EMAIL)


def _make_valid_jwt() -> str:
    """Create a real short-lived JWT for integration-style auth tests."""
    from auth.service import create_access_token

    return create_access_token(
        data={"sub": str(FAKE_USER_ID), "email": FAKE_EMAIL},
        expires_delta=timedelta(minutes=5),
    )


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    """Import and return the FastAPI app (DB dependency not needed for WS tests)."""
    from main import app as _app

    # Override get_db — WebSocket endpoint does not use the DB directly,
    # but other routers loaded by main.py do.
    from dependencies import get_db

    _app.dependency_overrides[get_db] = lambda: None
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Invalid token → error message + connection closes
# ---------------------------------------------------------------------------


class TestInvalidToken:
    """Connection with an invalid / missing JWT must receive an error and close."""

    def test_missing_token_receives_error(self, client):
        """No token → error message is sent and connection closes (R8.1)."""
        with client.websocket_connect("/ws/prices") as ws:
            data = ws.receive_json()
        assert data["type"] == "error"
        assert "Authentication" in data["message"] or "authentication" in data["message"]

    def test_bad_token_receives_error_message(self, client):
        """Garbage token → server sends error JSON before closing."""
        with client.websocket_connect("/ws/prices?token=not-a-valid-jwt") as ws:
            data = ws.receive_json()
        assert data["type"] == "error"
        assert "Authentication" in data["message"] or "authentication" in data["message"]

    def test_expired_token_receives_error(self, client):
        """Expired token → error message (R8.1 auth guard)."""
        from auth.service import create_access_token

        expired = create_access_token(
            data={"sub": str(FAKE_USER_ID), "email": FAKE_EMAIL},
            expires_delta=timedelta(seconds=-1),  # already expired
        )
        with client.websocket_connect(f"/ws/prices?token={expired}") as ws:
            data = ws.receive_json()
        assert data["type"] == "error"


# ---------------------------------------------------------------------------
# 2. Valid token → connection accepted
# ---------------------------------------------------------------------------


class TestValidConnection:
    """A valid JWT must result in a live connection (no immediate error/close)."""

    def test_connection_accepted_with_valid_token(self, client):
        """
        Valid token → connection stays open and client can send a message
        without receiving an error.  (R8.1, R8.2)
        """
        token = _make_valid_jwt()
        # Patch fetch_batch_prices so no yfinance calls are made.
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                # Send a harmless subscribe so the connection exercises the
                # receive loop; the test just verifies no exception is raised.
                ws.send_text(json.dumps({"type": "subscribe", "tickers": []}))
                # Connection is still alive — we exit the context cleanly.


# ---------------------------------------------------------------------------
# 3. Subscribe message → receives ack
# ---------------------------------------------------------------------------


class TestSubscribe:
    """Subscribe message must produce an ack frame."""

    def test_subscribe_returns_ack(self, client):
        """
        Sending {"type": "subscribe", "tickers": ["AAPL"]} returns
        {"type": "ack", "message": "Subscribed to AAPL"}.  (R8.1, R8.5)
        """
        token = _make_valid_jwt()
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                ws.send_text(
                    json.dumps({"type": "subscribe", "tickers": ["AAPL"]})
                )
                resp = ws.receive_json()

        assert resp["type"] == "ack"
        assert "AAPL" in resp["message"]

    def test_subscribe_multiple_tickers_ack_contains_all(self, client):
        """Subscribe to multiple tickers — all appear in the ack message."""
        token = _make_valid_jwt()
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                ws.send_text(
                    json.dumps({"type": "subscribe", "tickers": ["AAPL", "MSFT"]})
                )
                resp = ws.receive_json()

        assert resp["type"] == "ack"
        assert "AAPL" in resp["message"]
        assert "MSFT" in resp["message"]

    def test_subscribe_triggers_immediate_price_push(self, client):
        """
        After subscribing, if fetch returns prices, the client immediately
        receives a "prices" frame (before the 30-second timer fires).
        """
        token = _make_valid_jwt()
        mock_prices = {"AAPL": 192.40}
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value=mock_prices),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                ws.send_text(
                    json.dumps({"type": "subscribe", "tickers": ["AAPL"]})
                )
                ack = ws.receive_json()
                assert ack["type"] == "ack"

                prices_msg = ws.receive_json()

        assert prices_msg["type"] == "prices"
        assert "AAPL" in prices_msg["data"]
        assert prices_msg["data"]["AAPL"] == pytest.approx(192.40)


# ---------------------------------------------------------------------------
# 4. Unsubscribe message → handled without error
# ---------------------------------------------------------------------------


class TestUnsubscribe:
    """Unsubscribe messages must be handled gracefully."""

    def test_unsubscribe_after_subscribe_returns_ack(self, client):
        """
        Subscribe then unsubscribe — the unsubscribe ack confirms the ticker
        was removed.
        """
        token = _make_valid_jwt()
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                ws.send_text(
                    json.dumps({"type": "subscribe", "tickers": ["TSLA"]})
                )
                _ack = ws.receive_json()  # subscription ack

                ws.send_text(
                    json.dumps({"type": "unsubscribe", "tickers": ["TSLA"]})
                )
                resp = ws.receive_json()

        assert resp["type"] == "ack"
        assert "TSLA" in resp["message"]
        assert "Unsubscribed" in resp["message"] or "unsubscribed" in resp["message"]

    def test_unsubscribe_without_prior_subscribe_does_not_crash(self, client):
        """
        Unsubscribing a ticker that was never subscribed must not crash the
        server or close the connection.
        """
        token = _make_valid_jwt()
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                ws.send_text(
                    json.dumps({"type": "unsubscribe", "tickers": ["FAKE"]})
                )
                resp = ws.receive_json()
                # Still alive — can send another message
                ws.send_text(json.dumps({"type": "subscribe", "tickers": []}))

        # As long as we got back an ack and didn't throw, the test passes.
        assert resp["type"] == "ack"


# ---------------------------------------------------------------------------
# 5. Invalid JSON → connection stays alive
# ---------------------------------------------------------------------------


class TestInvalidJson:
    """Malformed JSON must not crash or close an authenticated connection."""

    def test_invalid_json_does_not_close_connection(self, client):
        """
        Sending non-JSON text must be silently ignored; the connection stays
        open and subsequent valid messages are still processed.
        """
        token = _make_valid_jwt()
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                # Send garbage text.
                ws.send_text("this is not json {{{{")

                # Connection must still be alive — send a valid subscribe.
                ws.send_text(
                    json.dumps({"type": "subscribe", "tickers": ["GOOG"]})
                )
                resp = ws.receive_json()

        assert resp["type"] == "ack"
        assert "GOOG" in resp["message"]

    def test_unknown_message_type_does_not_close_connection(self, client):
        """
        An unknown ``type`` field is silently ignored; connection stays alive.
        """
        token = _make_valid_jwt()
        with patch(
            "websocket.price_feed.fetch_batch_prices",
            new=AsyncMock(return_value={}),
        ):
            with client.websocket_connect(f"/ws/prices?token={token}") as ws:
                ws.send_text(json.dumps({"type": "ping"}))
                # Send a valid subscribe so we have something to read.
                ws.send_text(
                    json.dumps({"type": "subscribe", "tickers": ["NVDA"]})
                )
                resp = ws.receive_json()

        assert resp["type"] == "ack"


# ---------------------------------------------------------------------------
# ConnectionManager unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


class TestConnectionManager:
    """Pure unit tests for the ConnectionManager class."""

    def _make_manager(self):
        from websocket.price_feed import ConnectionManager

        return ConnectionManager()

    def test_initial_state_is_empty(self):
        m = self._make_manager()
        assert len(m.connections) == 0
        assert len(m.subscriptions) == 0

    def test_disconnect_removes_connection_and_subscriptions(self):
        m = self._make_manager()
        conn_id = "test-conn"
        ws_mock = MagicMock()
        # Manually insert without calling async connect().
        m.connections[conn_id] = ws_mock
        m.subscriptions[conn_id] = {"AAPL"}

        m.disconnect(conn_id)

        assert conn_id not in m.connections
        assert conn_id not in m.subscriptions

    def test_subscribe_uppercases_tickers(self):
        m = self._make_manager()
        conn_id = "test-conn"
        m.subscriptions[conn_id] = set()

        m.subscribe(conn_id, ["aapl", "Msft"])

        assert "AAPL" in m.subscriptions[conn_id]
        assert "MSFT" in m.subscriptions[conn_id]

    def test_unsubscribe_removes_tickers(self):
        m = self._make_manager()
        conn_id = "test-conn"
        m.subscriptions[conn_id] = {"AAPL", "MSFT", "TSLA"}

        m.unsubscribe(conn_id, ["aapl", "MSFT"])

        assert "AAPL" not in m.subscriptions[conn_id]
        assert "MSFT" not in m.subscriptions[conn_id]
        assert "TSLA" in m.subscriptions[conn_id]

    def test_get_all_tickers_returns_union(self):
        m = self._make_manager()
        m.subscriptions["c1"] = {"AAPL", "MSFT"}
        m.subscriptions["c2"] = {"AAPL", "TSLA"}

        result = m.get_all_tickers()

        assert result == {"AAPL", "MSFT", "TSLA"}

    def test_get_all_tickers_empty_when_no_subscriptions(self):
        m = self._make_manager()
        assert m.get_all_tickers() == set()

    def test_subscribe_unknown_connection_is_noop(self):
        """subscribe() on an unknown connection_id must not raise."""
        m = self._make_manager()
        m.subscribe("nonexistent", ["AAPL"])  # should not raise

    def test_unsubscribe_unknown_connection_is_noop(self):
        """unsubscribe() on an unknown connection_id must not raise."""
        m = self._make_manager()
        m.unsubscribe("nonexistent", ["AAPL"])  # should not raise

    def test_disconnect_unknown_connection_is_noop(self):
        """disconnect() on an unknown connection_id must not raise."""
        m = self._make_manager()
        m.disconnect("nonexistent")  # should not raise
