"""
Integration tests for the portfolio router (/portfolio/* endpoints).

Strategy
--------
- FastAPI TestClient drives the full request/response cycle.
- PortfolioService is patched at the *module* level so no database,
  trading engine, or live yfinance call is needed.
- get_current_user dependency is overridden to return a fake user.
- get_db dependency is overridden to return None.

Requirements validated: R2.1–R2.8, R7.3
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
    email = "investor@example.com"
    name = "Test Investor"
    is_active = True
    theme_preference = "light"
    created_at = datetime(2024, 1, 1)


# ---------------------------------------------------------------------------
# Canonical service return value builders
# ---------------------------------------------------------------------------

def _summary() -> dict:
    """Standard portfolio summary matching PortfolioSummaryResponse schema."""
    return {
        "account_id": str(uuid.uuid4()),
        "cash": 90_000.0,
        "portfolio_value": 12_000.0,
        "total_value": 102_000.0,
        "buying_power": 90_000.0,
        "initial_cash": 100_000.0,
        # P&L
        "total_return": 2_000.0,
        "total_return_pct": 0.02,
        "realized_pnl": 500.0,
        "unrealized_pnl": 1_500.0,
        # Performance stats
        "win_rate": 0.6,
        "num_trades": 5,
        "num_winning_trades": 3,
        "num_losing_trades": 2,
        "avg_win": 400.0,
        "avg_loss": -150.0,
        # Benchmark
        "benchmark": {
            "benchmark_ticker": "SPY",
            "benchmark_return_pct": 0.015,
            "portfolio_return_pct": 0.02,
            "alpha": 0.005,
            "performance": "matching",
        },
    }


def _summary_no_benchmark() -> dict:
    """Portfolio summary when benchmark data is unavailable."""
    d = _summary()
    d["benchmark"] = None
    return d


def _position() -> dict:
    """Open position matching PositionDetail schema."""
    return {
        "ticker": "AAPL",
        "quantity": 40,
        "avg_entry_price": 148.0,
        "current_price": 155.0,
        "market_value": 6_200.0,
        "unrealized_pnl": 280.0,
        "unrealized_pnl_pct": 4.73,
        "cost_basis": 5_920.0,
        "day_change_pct": 1.25,
    }


def _position_no_day_change() -> dict:
    pos = _position()
    pos["day_change_pct"] = None
    return pos


def _history() -> dict:
    """Portfolio history matching PortfolioHistoryResponse schema."""
    return {
        "closed_trades": [
            {
                "ticker": "TSLA",
                "quantity": 10,
                "avg_entry_price": 200.0,
                "exit_price": 250.0,
                "entry_time": "2024-01-10T09:30:00",
                "exit_time": "2024-01-15T15:45:00",
                "realized_pnl": 500.0,
                "realized_pnl_pct": 0.25,
            }
        ],
        "equity_snapshots": [
            {"date": "2024-01-10", "total_value": 100_500.0},
            {"date": "2024-01-15", "total_value": 101_200.0},
        ],
        "total_realized_pnl": 500.0,
    }


def _empty_history() -> dict:
    return {
        "closed_trades": [],
        "equity_snapshots": [],
        "total_realized_pnl": 0.0,
    }


# ---------------------------------------------------------------------------
# Helper — build a PortfolioService mock with sensible defaults
# ---------------------------------------------------------------------------

def _make_service_mock(**method_overrides) -> MagicMock:
    """Return a MagicMock PortfolioService instance with sensible defaults."""
    mock = MagicMock()
    mock.get_summary.return_value = _summary()
    mock.get_positions.return_value = [_position()]
    mock.get_history.return_value = _history()
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
# GET /portfolio/summary
# ---------------------------------------------------------------------------

class TestGetSummary:
    """Tests for GET /portfolio/summary (R2.1, R2.2, R2.5, R2.7)."""

    def test_returns_200_with_all_required_fields(self, client):
        """Summary endpoint returns 200 and includes all required schema fields (R2.1, R2.2)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        assert resp.status_code == 200
        data = resp.json()
        # Account fields
        assert "account_id" in data
        assert data["cash"] == 90_000.0
        assert data["total_value"] == 102_000.0
        assert data["portfolio_value"] == 12_000.0
        assert data["buying_power"] == 90_000.0

    def test_summary_contains_pnl_fields(self, client):
        """Summary includes realized/unrealized P&L and total return (R2.2)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        data = resp.json()
        assert data["total_return"] == pytest.approx(2_000.0)
        assert data["total_return_pct"] == pytest.approx(0.02)
        assert data["realized_pnl"] == pytest.approx(500.0)
        assert data["unrealized_pnl"] == pytest.approx(1_500.0)

    def test_summary_contains_performance_metrics(self, client):
        """Summary includes win-rate and trade-count stats (R2.7)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        data = resp.json()
        assert data["win_rate"] == pytest.approx(0.6)
        assert data["num_trades"] == 5
        assert data["num_winning_trades"] == 3
        assert data["num_losing_trades"] == 2
        assert data["avg_win"] == pytest.approx(400.0)
        assert data["avg_loss"] == pytest.approx(-150.0)

    def test_summary_includes_benchmark_comparison(self, client):
        """Summary includes benchmark object with alpha/performance fields (R2.5)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        data = resp.json()
        bm = data["benchmark"]
        assert bm is not None
        assert bm["benchmark_ticker"] == "SPY"
        assert "benchmark_return_pct" in bm
        assert "portfolio_return_pct" in bm
        assert "alpha" in bm
        assert "performance" in bm

    def test_summary_benchmark_can_be_null(self, client):
        """Summary benchmark field is null when SPY data unavailable (R2.5)."""
        mock_svc = _make_service_mock(get_summary=_summary_no_benchmark())
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        assert resp.status_code == 200
        assert resp.json()["benchmark"] is None

    def test_service_constructed_with_correct_user(self, client):
        """PortfolioService is instantiated with the authenticated user's id (R7.3)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc) as mock_cls:
            client.get("/portfolio/summary")
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
            resp = c.get("/portfolio/summary")
        # Restore
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401

    def test_initial_cash_field_present(self, client):
        """Summary includes initial_cash field for return calculation baseline (R2.1)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        assert resp.json()["initial_cash"] == pytest.approx(100_000.0)


# ---------------------------------------------------------------------------
# GET /portfolio/positions
# ---------------------------------------------------------------------------

class TestGetPositions:
    """Tests for GET /portfolio/positions (R2.3)."""

    def test_returns_200_list_of_positions(self, client):
        """Positions endpoint returns 200 with a list of positions (R2.3)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["ticker"] == "AAPL"

    def test_positions_contain_required_fields(self, client):
        """Each position contains expected fields from PositionDetail schema (R2.3)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        pos = resp.json()[0]
        assert pos["quantity"] == 40
        assert pos["avg_entry_price"] == pytest.approx(148.0)
        assert pos["current_price"] == pytest.approx(155.0)
        assert pos["market_value"] == pytest.approx(6_200.0)
        assert pos["unrealized_pnl"] == pytest.approx(280.0)
        assert pos["cost_basis"] == pytest.approx(5_920.0)

    def test_positions_include_day_change_pct(self, client):
        """Positions include day_change_pct enriched from yfinance (R2.3)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        pos = resp.json()[0]
        assert "day_change_pct" in pos
        assert pos["day_change_pct"] == pytest.approx(1.25)

    def test_positions_day_change_pct_can_be_null(self, client):
        """day_change_pct is null when yfinance data is unavailable (R2.3)."""
        mock_svc = _make_service_mock(get_positions=[_position_no_day_change()])
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        assert resp.status_code == 200
        assert resp.json()[0]["day_change_pct"] is None

    def test_empty_positions_returns_empty_list(self, client):
        """Returns empty list when no open positions exist."""
        mock_svc = _make_service_mock(get_positions=[])
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_multiple_positions_returned(self, client):
        """All open positions are returned when multiple exist."""
        positions = [
            _position(),
            {**_position(), "ticker": "NVDA", "quantity": 10, "current_price": 450.0,
             "market_value": 4_500.0, "unrealized_pnl": 200.0, "unrealized_pnl_pct": 4.65,
             "cost_basis": 4_300.0, "day_change_pct": -0.5},
        ]
        mock_svc = _make_service_mock(get_positions=positions)
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        data = resp.json()
        assert len(data) == 2
        tickers = {p["ticker"] for p in data}
        assert tickers == {"AAPL", "NVDA"}

    def test_service_constructed_with_correct_user(self, client):
        """PortfolioService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc) as mock_cls:
            client.get("/portfolio/positions")
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID


# ---------------------------------------------------------------------------
# GET /portfolio/history
# ---------------------------------------------------------------------------

class TestGetHistory:
    """Tests for GET /portfolio/history (R2.4, R2.6)."""

    def test_returns_200_with_history_structure(self, client):
        """History endpoint returns 200 with closed_trades and equity_snapshots (R2.4, R2.6)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "closed_trades" in data
        assert "equity_snapshots" in data
        assert "total_realized_pnl" in data

    def test_closed_trades_contain_required_fields(self, client):
        """Closed trade records include all ClosedTradeRecord schema fields (R2.6)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/history")
        trade = resp.json()["closed_trades"][0]
        assert trade["ticker"] == "TSLA"
        assert trade["quantity"] == 10
        assert trade["avg_entry_price"] == pytest.approx(200.0)
        assert trade["exit_price"] == pytest.approx(250.0)
        assert trade["realized_pnl"] == pytest.approx(500.0)
        assert trade["realized_pnl_pct"] == pytest.approx(0.25)
        assert "entry_time" in trade
        assert "exit_time" in trade

    def test_equity_snapshots_contain_date_and_value(self, client):
        """Each equity snapshot includes date and total_value (R2.4)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/history")
        snapshots = resp.json()["equity_snapshots"]
        assert len(snapshots) == 2
        assert snapshots[0]["date"] == "2024-01-10"
        assert snapshots[0]["total_value"] == pytest.approx(100_500.0)
        assert snapshots[1]["date"] == "2024-01-15"

    def test_total_realized_pnl_field(self, client):
        """total_realized_pnl is present and matches expected value (R2.2)."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/history")
        assert resp.json()["total_realized_pnl"] == pytest.approx(500.0)

    def test_empty_account_returns_empty_history(self, client):
        """New account with no trades or snapshots returns empty history (edge case)."""
        mock_svc = _make_service_mock(get_history=_empty_history())
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["closed_trades"] == []
        assert data["equity_snapshots"] == []
        assert data["total_realized_pnl"] == pytest.approx(0.0)

    def test_service_constructed_with_correct_user(self, client):
        """PortfolioService is instantiated with the authenticated user's id."""
        mock_svc = _make_service_mock()
        with patch("portfolio.router.PortfolioService", return_value=mock_svc) as mock_cls:
            client.get("/portfolio/history")
        _, kwargs = mock_cls.call_args
        assert kwargs["user_id"] == FAKE_USER_ID

    def test_unauthenticated_returns_401(self, app):
        """History endpoint requires authentication."""
        from dependencies import get_current_user
        from fastapi import HTTPException

        def raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = raise_401
        with TestClient(app) as c:
            resp = c.get("/portfolio/history")
        app.dependency_overrides[get_current_user] = lambda: FakeUser()
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases: empty account (no positions, no trades)
# ---------------------------------------------------------------------------

class TestEmptyAccount:
    """Edge-case tests for a brand-new account with no activity."""

    def test_summary_zero_pnl_empty_account(self, client):
        """Summary reflects zero P&L on a fresh account with no trades (R2.1)."""
        empty_summary = {
            "account_id": str(uuid.uuid4()),
            "cash": 100_000.0,
            "portfolio_value": 0.0,
            "total_value": 100_000.0,
            "buying_power": 100_000.0,
            "initial_cash": 100_000.0,
            "total_return": 0.0,
            "total_return_pct": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "num_winning_trades": 0,
            "num_losing_trades": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "benchmark": None,
        }
        mock_svc = _make_service_mock(get_summary=empty_summary)
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["num_trades"] == 0
        assert data["win_rate"] == pytest.approx(0.0)
        assert data["total_return"] == pytest.approx(0.0)
        assert data["benchmark"] is None

    def test_positions_empty_for_new_account(self, client):
        """New account has no open positions (R2.3)."""
        mock_svc = _make_service_mock(get_positions=[])
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/positions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_empty_for_new_account(self, client):
        """New account has no closed trades and no snapshots (R2.4, R2.6)."""
        mock_svc = _make_service_mock(get_history=_empty_history())
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["closed_trades"] == []
        assert data["equity_snapshots"] == []
        assert data["total_realized_pnl"] == pytest.approx(0.0)

    def test_all_three_endpoints_healthy_empty_account(self, client):
        """All three portfolio endpoints return 200 for a brand-new account."""
        empty_summary = {
            "account_id": str(uuid.uuid4()),
            "cash": 100_000.0,
            "portfolio_value": 0.0,
            "total_value": 100_000.0,
            "buying_power": 100_000.0,
            "initial_cash": 100_000.0,
            "total_return": 0.0,
            "total_return_pct": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "num_winning_trades": 0,
            "num_losing_trades": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "benchmark": None,
        }
        mock_svc = _make_service_mock(
            get_summary=empty_summary,
            get_positions=[],
            get_history=_empty_history(),
        )
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            r1 = client.get("/portfolio/summary")
            r2 = client.get("/portfolio/positions")
            r3 = client.get("/portfolio/history")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200


# ---------------------------------------------------------------------------
# Performance metrics wiring (R2.7 — PerformanceMetrics.calculate())
# ---------------------------------------------------------------------------

class TestPerformanceMetricsWiring:
    """Verify that the summary correctly surfaces PerformanceMetrics data (R2.7)."""

    def test_outperforming_benchmark_reflected_in_summary(self, client):
        """Summary benchmark.performance reports 'outperforming' when alpha > 0.02."""
        summary = _summary()
        summary["benchmark"] = {
            "benchmark_ticker": "SPY",
            "benchmark_return_pct": 0.01,
            "portfolio_return_pct": 0.05,
            "alpha": 0.04,
            "performance": "outperforming",
        }
        mock_svc = _make_service_mock(get_summary=summary)
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        assert resp.json()["benchmark"]["performance"] == "outperforming"

    def test_underperforming_benchmark_reflected_in_summary(self, client):
        """Summary benchmark.performance reports 'underperforming' when alpha < -0.02."""
        summary = _summary()
        summary["benchmark"] = {
            "benchmark_ticker": "SPY",
            "benchmark_return_pct": 0.05,
            "portfolio_return_pct": 0.01,
            "alpha": -0.04,
            "performance": "underperforming",
        }
        mock_svc = _make_service_mock(get_summary=summary)
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        assert resp.json()["benchmark"]["performance"] == "underperforming"

    def test_100_pct_win_rate(self, client):
        """100% win rate (all trades profitable) is correctly represented."""
        summary = _summary()
        summary.update({
            "win_rate": 1.0,
            "num_trades": 3,
            "num_winning_trades": 3,
            "num_losing_trades": 0,
            "avg_win": 600.0,
            "avg_loss": 0.0,
        })
        mock_svc = _make_service_mock(get_summary=summary)
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        data = resp.json()
        assert data["win_rate"] == pytest.approx(1.0)
        assert data["num_losing_trades"] == 0

    def test_zero_win_rate(self, client):
        """0% win rate (all trades losing) is correctly represented."""
        summary = _summary()
        summary.update({
            "win_rate": 0.0,
            "num_trades": 2,
            "num_winning_trades": 0,
            "num_losing_trades": 2,
            "avg_win": 0.0,
            "avg_loss": -300.0,
        })
        mock_svc = _make_service_mock(get_summary=summary)
        with patch("portfolio.router.PortfolioService", return_value=mock_svc):
            resp = client.get("/portfolio/summary")
        data = resp.json()
        assert data["win_rate"] == pytest.approx(0.0)
        assert data["num_winning_trades"] == 0
