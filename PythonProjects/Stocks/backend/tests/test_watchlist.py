"""
Integration tests for the watchlist router (/watchlist/* endpoints).

Strategy
--------
- FastAPI TestClient drives the full request/response cycle.
- WatchlistService is patched at the *module* level so no database is needed.
- get_current_user dependency is overridden to return a fake user.
- get_db dependency is overridden to return None.

Requirements validated: R3.1, R3.3, R3.4, R3.7, R7.4
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

# Point at SQLite so database module doesn't try to reach PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# ---------------------------------------------------------------------------
# Fake user shared across tests
# ---------------------------------------------------------------------------

FAKE_USER_ID = uuid.uuid4()


class FakeUser:
    id = FAKE_USER_ID
    email = "watcher@example.com"
    name = "Test Watcher"
    is_active = True
    theme_preference = "dark"
    created_at = datetime(2024, 1, 1)


# ---------------------------------------------------------------------------
# Canonical service return-value builders
# ---------------------------------------------------------------------------

def _item(
    ticker: str = "AAPL",
    list_name: str = "Default",
    alert_price: float | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "ticker": ticker,
        "list_name": list_name,
        "alert_price": alert_price,
        "created_at": datetime(2024, 6, 1, 10, 0).isoformat(),
    }


def _list_info(name: str = "Default", item_count: int = 1) -> dict:
    return {"name": name, "item_count": item_count}


# ---------------------------------------------------------------------------
# Helper — build a WatchlistService mock with sensible defaults
# ---------------------------------------------------------------------------

def _make_service_mock(**method_overrides) -> MagicMock:
    mock = MagicMock()
    mock.get_items.return_value = [_item()]
    mock.add_item.return_value = _item()
    mock.remove_item.return_value = True
    mock.get_lists.return_value = [_list_info()]
    mock.create_list.return_value = _list_info(item_count=0)
    for method, value in method_overrides.items():
        getattr(mock, method).return_value = value
    return mock


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
# GET /watchlist
# ---------------------------------------------------------------------------

class TestGetWatchlist:
    """Tests for GET /watchlist (R3.1, R7.4)."""

    def test_returns_200_with_items(self, client):
        """GET /watchlist returns 200 and a list of items."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"

    def test_empty_watchlist_returns_empty_list(self, client):
        """GET /watchlist returns [] when the user has no items."""
        mock_svc = _make_service_mock(get_items=[])
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filters_by_list_name(self, client):
        """GET /watchlist?list_name=Tech returns only items from that list."""
        tech_items = [
            _item("NVDA", "Tech"),
            _item("MSFT", "Tech"),
        ]
        mock_svc = _make_service_mock(get_items=tech_items)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist?list_name=Tech")
        assert resp.status_code == 200
        # Verify the list_name filter was forwarded to the service
        mock_svc.get_items.assert_called_once_with(list_name="Tech")
        data = resp.json()
        assert len(data) == 2
        assert all(d["list_name"] == "Tech" for d in data)

    def test_no_list_name_filter_calls_service_with_none(self, client):
        """GET /watchlist without filter calls get_items(list_name=None)."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            client.get("/watchlist")
        mock_svc.get_items.assert_called_once_with(list_name=None)

    def test_item_schema_fields_present(self, client):
        """Each item in the response contains required schema fields."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        item = resp.json()[0]
        assert "id" in item
        assert "ticker" in item
        assert "list_name" in item
        assert "alert_price" in item
        assert "created_at" in item

    def test_service_constructed_with_correct_user(self, client):
        """WatchlistService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc) as mock_cls:
            client.get("/watchlist")
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID

    def test_alert_price_can_be_null(self, client):
        """alert_price is null when not set (R3.7)."""
        mock_svc = _make_service_mock(get_items=[_item(alert_price=None)])
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        assert resp.json()[0]["alert_price"] is None

    def test_alert_price_returned_when_set(self, client):
        """alert_price is a float when set (R3.7)."""
        mock_svc = _make_service_mock(get_items=[_item(alert_price=175.50)])
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        assert resp.json()[0]["alert_price"] == pytest.approx(175.50)


# ---------------------------------------------------------------------------
# POST /watchlist/add
# ---------------------------------------------------------------------------

class TestAddToWatchlist:
    """Tests for POST /watchlist/add (R3.1, R3.7, R7.4)."""

    _basic_payload = {"ticker": "AAPL"}

    def test_add_item_returns_201(self, client):
        """POST /watchlist/add returns 201 on success (R3.1)."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json=self._basic_payload)
        assert resp.status_code == 201

    def test_add_item_returns_created_item(self, client):
        """Response body matches WatchlistItemResponse schema."""
        created = _item("AAPL")
        mock_svc = _make_service_mock(add_item=created)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json=self._basic_payload)
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert "id" in data
        assert "created_at" in data

    def test_ticker_is_uppercased_by_schema(self, client):
        """Lowercase ticker in request body is normalised to uppercase by schema."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json={"ticker": "aapl"})
        assert resp.status_code == 201
        # Service must receive uppercased ticker
        _, kwargs = mock_svc.add_item.call_args
        assert kwargs["ticker"] == "AAPL"

    def test_add_to_named_list(self, client):
        """list_name is forwarded to the service (R3.4)."""
        mock_svc = _make_service_mock(add_item=_item("NVDA", "Tech"))
        payload = {"ticker": "NVDA", "list_name": "Tech"}
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json=payload)
        assert resp.status_code == 201
        _, kwargs = mock_svc.add_item.call_args
        assert kwargs["list_name"] == "Tech"

    def test_add_with_alert_price(self, client):
        """alert_price is forwarded to the service (R3.7)."""
        mock_svc = _make_service_mock(add_item=_item("TSLA", alert_price=200.0))
        payload = {"ticker": "TSLA", "alert_price": 200.0}
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json=payload)
        assert resp.status_code == 201
        _, kwargs = mock_svc.add_item.call_args
        assert kwargs["alert_price"] == pytest.approx(200.0)

    def test_duplicate_returns_409(self, client):
        """Duplicate ticker in the same list raises 409 (R3.1 uniqueness)."""
        from fastapi import HTTPException

        mock_svc = _make_service_mock()
        mock_svc.add_item.side_effect = HTTPException(
            status_code=409, detail="AAPL is already in list 'Default'"
        )
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json=self._basic_payload)
        assert resp.status_code == 409

    def test_empty_ticker_returns_422(self, client):
        """Empty ticker string triggers Pydantic validation error (422)."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/add", json={"ticker": ""})
        assert resp.status_code == 422

    def test_default_list_name_is_default(self, client):
        """list_name defaults to 'Default' when omitted."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            client.post("/watchlist/add", json={"ticker": "GOOG"})
        _, kwargs = mock_svc.add_item.call_args
        assert kwargs["list_name"] == "Default"

    def test_service_constructed_with_correct_user(self, client):
        """WatchlistService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc) as mock_cls:
            client.post("/watchlist/add", json=self._basic_payload)
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID


# ---------------------------------------------------------------------------
# DELETE /watchlist/{ticker}
# ---------------------------------------------------------------------------

class TestRemoveFromWatchlist:
    """Tests for DELETE /watchlist/{ticker} (R3.3, R7.4)."""

    def test_remove_existing_returns_200(self, client):
        """DELETE /watchlist/AAPL returns 200 when item exists (R3.3)."""
        mock_svc = _make_service_mock(remove_item=True)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.delete("/watchlist/AAPL")
        assert resp.status_code == 200
        assert "AAPL" in resp.json()["message"]

    def test_remove_nonexistent_returns_404(self, client):
        """DELETE /watchlist/NVDA returns 404 when ticker not found (R3.3)."""
        mock_svc = _make_service_mock(remove_item=False)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.delete("/watchlist/NVDA")
        assert resp.status_code == 404

    def test_ticker_uppercased_before_delete(self, client):
        """Ticker in path is uppercased before being forwarded to the service."""
        mock_svc = _make_service_mock(remove_item=True)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            client.delete("/watchlist/aapl")
        _, kwargs = mock_svc.remove_item.call_args
        assert kwargs["ticker"] == "AAPL"

    def test_list_name_query_param_forwarded(self, client):
        """list_name query param is forwarded to remove_item (R3.4)."""
        mock_svc = _make_service_mock(remove_item=True)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.delete("/watchlist/AAPL?list_name=Tech")
        assert resp.status_code == 200
        _, kwargs = mock_svc.remove_item.call_args
        assert kwargs["list_name"] == "Tech"

    def test_default_list_name_is_default(self, client):
        """list_name defaults to 'Default' when not provided."""
        mock_svc = _make_service_mock(remove_item=True)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            client.delete("/watchlist/AAPL")
        _, kwargs = mock_svc.remove_item.call_args
        assert kwargs["list_name"] == "Default"

    def test_service_constructed_with_correct_user(self, client):
        """WatchlistService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock(remove_item=True)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc) as mock_cls:
            client.delete("/watchlist/AAPL")
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID


# ---------------------------------------------------------------------------
# GET /watchlist/lists
# ---------------------------------------------------------------------------

class TestGetLists:
    """Tests for GET /watchlist/lists (R3.4, R7.4)."""

    def test_returns_200_with_list_names(self, client):
        """GET /watchlist/lists returns 200 with list names and counts (R3.4)."""
        mock_svc = _make_service_mock(
            get_lists=[_list_info("Default", 2), _list_info("Tech", 3)]
        )
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist/lists")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        names = {d["name"] for d in data}
        assert "Default" in names
        assert "Tech" in names

    def test_list_response_contains_item_count(self, client):
        """Each list entry includes an item_count field (R3.4)."""
        mock_svc = _make_service_mock(get_lists=[_list_info("Default", 5)])
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist/lists")
        data = resp.json()
        assert data[0]["item_count"] == 5

    def test_empty_lists_returns_empty_array(self, client):
        """Returns [] when the user has no watchlist items."""
        mock_svc = _make_service_mock(get_lists=[])
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist/lists")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_service_constructed_with_correct_user(self, client):
        """WatchlistService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc) as mock_cls:
            client.get("/watchlist/lists")
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID


# ---------------------------------------------------------------------------
# POST /watchlist/lists
# ---------------------------------------------------------------------------

class TestCreateList:
    """Tests for POST /watchlist/lists (R3.4, R7.4)."""

    def test_create_list_returns_201(self, client):
        """POST /watchlist/lists returns 201 on success (R3.4)."""
        mock_svc = _make_service_mock(
            create_list=_list_info("Biotech", item_count=0)
        )
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/lists", json={"name": "Biotech"})
        assert resp.status_code == 201

    def test_create_list_response_schema(self, client):
        """Response body matches WatchlistListResponse schema."""
        mock_svc = _make_service_mock(
            create_list=_list_info("Biotech", item_count=0)
        )
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/lists", json={"name": "Biotech"})
        data = resp.json()
        assert data["name"] == "Biotech"
        assert data["item_count"] == 0

    def test_existing_list_returns_existing_metadata(self, client):
        """Creating an already-existing list returns its current item count."""
        mock_svc = _make_service_mock(
            create_list=_list_info("Default", item_count=3)
        )
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/lists", json={"name": "Default"})
        assert resp.status_code == 201
        assert resp.json()["item_count"] == 3

    def test_empty_name_returns_422(self, client):
        """Empty list name triggers Pydantic validation error (422)."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/lists", json={"name": ""})
        assert resp.status_code == 422

    def test_special_chars_in_name_returns_422(self, client):
        """List name with invalid chars (e.g. '<script>') triggers 422."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.post("/watchlist/lists", json={"name": "<script>"})
        assert resp.status_code == 422

    def test_name_forwarded_to_service(self, client):
        """The validated list name is forwarded to create_list."""
        mock_svc = _make_service_mock(
            create_list=_list_info("Energy", item_count=0)
        )
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            client.post("/watchlist/lists", json={"name": "Energy"})
        mock_svc.create_list.assert_called_once_with(name="Energy")

    def test_service_constructed_with_correct_user(self, client):
        """WatchlistService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("watchlist.router.WatchlistService", return_value=mock_svc) as mock_cls:
            client.post("/watchlist/lists", json={"name": "MyList"})
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

class TestUnauthenticated:
    """Verify all endpoints reject unauthenticated requests (R7.7)."""

    def test_get_watchlist_requires_auth(self, app):
        """GET /watchlist without token → 401."""
        from dependencies import get_current_user
        from fastapi import HTTPException

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/watchlist")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401

    def test_add_watchlist_requires_auth(self, app):
        """POST /watchlist/add without token → 401."""
        from dependencies import get_current_user
        from fastapi import HTTPException

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.post("/watchlist/add", json={"ticker": "AAPL"})
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401

    def test_delete_watchlist_requires_auth(self, app):
        """DELETE /watchlist/{ticker} without token → 401."""
        from dependencies import get_current_user
        from fastapi import HTTPException

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.delete("/watchlist/AAPL")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401

    def test_get_lists_requires_auth(self, app):
        """GET /watchlist/lists without token → 401."""
        from dependencies import get_current_user
        from fastapi import HTTPException

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/watchlist/lists")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Multiple-items edge cases
# ---------------------------------------------------------------------------

class TestMultipleItems:
    """Edge-case tests covering multiple items and multiple lists."""

    def test_multiple_tickers_returned(self, client):
        """GET /watchlist returns all tickers when multiple items exist."""
        items = [_item("AAPL"), _item("TSLA"), _item("NVDA")]
        mock_svc = _make_service_mock(get_items=items)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        data = resp.json()
        assert len(data) == 3
        tickers = {d["ticker"] for d in data}
        assert tickers == {"AAPL", "TSLA", "NVDA"}

    def test_same_ticker_in_different_lists(self, client):
        """Same ticker can appear in multiple different lists (R3.4)."""
        items = [
            _item("AAPL", "Default"),
            _item("AAPL", "Tech"),
        ]
        mock_svc = _make_service_mock(get_items=items)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist")
        data = resp.json()
        assert len(data) == 2
        list_names = {d["list_name"] for d in data}
        assert "Default" in list_names
        assert "Tech" in list_names

    def test_multiple_lists_returned(self, client):
        """GET /watchlist/lists returns all distinct lists."""
        lists = [
            _list_info("Default", 2),
            _list_info("Tech", 3),
            _list_info("Energy", 1),
        ]
        mock_svc = _make_service_mock(get_lists=lists)
        with patch("watchlist.router.WatchlistService", return_value=mock_svc):
            resp = client.get("/watchlist/lists")
        assert len(resp.json()) == 3
