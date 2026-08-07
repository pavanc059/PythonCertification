"""
Tests for the Penny Stock Momentum Dashboard.

Tests cover:
- Demo / fallback data validity
- Pure data-assembly helpers (top-20 selection, table rows, sector distribution)
- Refresh-interval helpers (Property 53 support)
- Section render functions (mocked Streamlit context)
- render_penny_dashboard() structure

Requirements addressed: 11.5, 11.8, 11.12, 11.13, 11.15-11.19
Property: 53 (dashboard refresh interval <= 2 minutes)
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub out Streamlit + Plotly before the module loads so tests run without a
# live Streamlit server.
# ---------------------------------------------------------------------------

def _make_streamlit_stub() -> types.ModuleType:
    """Build a minimal Streamlit stub that records calls."""
    st = types.ModuleType("streamlit")

    for attr in (
        "title", "caption", "divider", "subheader", "markdown", "info",
        "container", "progress", "metric", "warning", "plotly_chart",
        "selectbox",
    ):
        setattr(st, attr, MagicMock())

    # selectbox returns the first option by default
    st.selectbox = MagicMock(side_effect=lambda label, options, **kw: options[0])

    def _columns(spec):
        n = len(spec) if hasattr(spec, "__len__") else int(spec)
        return [
            MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
            for _ in range(n)
        ]

    st.columns = _columns

    def _tabs(labels):
        return [
            MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
            for _ in labels
        ]

    st.tabs = _tabs

    def _expander(label, expanded=False):
        return MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))

    st.expander = _expander
    st.session_state = {}
    st.cache_data = lambda ttl=None: (lambda fn: fn)
    return st


_st_stub = _make_streamlit_stub()
sys.modules["streamlit"] = _st_stub

_plotly = types.ModuleType("plotly")
_plotly_go = types.ModuleType("plotly.graph_objects")
_plotly_px = types.ModuleType("plotly.express")
# go.Figure / go.Scatter / go.Pie stubs
_plotly_go.Figure = MagicMock(return_value=MagicMock())
_plotly_go.Scatter = MagicMock()
_plotly_go.Pie = MagicMock()
sys.modules.setdefault("plotly", _plotly)
sys.modules["plotly.graph_objects"] = _plotly_go
sys.modules["plotly.express"] = _plotly_px


from stockiq.ui.dashboards.penny_stocks import (  # noqa: E402
    _demo_penny_stocks,
    _demo_price_history,
    _demo_catalyst_events,
    _fmt_price,
    _fmt_pct,
    _fmt_volume,
    _pct_colour,
    _risk_colour,
    _recommendation_colour,
    select_top_penny_stocks,
    build_table_rows,
    compute_sector_distribution,
    fetch_penny_stocks,
    get_refresh_interval_seconds,
    should_refresh,
    seconds_until_next_refresh,
    render_penny_stock_table,
    render_penny_stock_charts,
    render_penny_stock_metrics,
    render_sector_distribution,
    render_penny_dashboard,
    TOP_PENNY_LIMIT,
    MAX_REFRESH_INTERVAL_SECONDS,
    PENNY_DASHBOARD_REFRESH_SECONDS,
    CHART_TIMEFRAMES,
    STREAMLIT_AVAILABLE,
)


# =========================================================================
# Demo data
# =========================================================================

class TestDemoPennyStocks:
    def test_returns_rows(self):
        assert len(_demo_penny_stocks()) > 0

    def test_required_keys(self):
        required = {
            "ticker", "price", "price_change_pct", "volume", "avg_volume",
            "volume_ratio", "market_cap", "sector", "momentum_score",
            "risk_level", "liquidity_risk", "volatility_risk", "spread_pct",
            "recommendation", "suspicion_score", "insider_net",
        }
        for r in _demo_penny_stocks():
            assert required.issubset(r.keys()), f"Missing keys in {r['ticker']}"

    def test_all_prices_penny(self):
        """Demo prices must all be <= $5.00 (penny stock definition)."""
        for r in _demo_penny_stocks():
            assert r["price"] <= 5.00, f"{r['ticker']} price {r['price']} > $5"

    def test_momentum_scores_in_range(self):
        for r in _demo_penny_stocks():
            assert 0.0 <= r["momentum_score"] <= 100.0

    def test_risk_levels_valid(self):
        valid = {"low", "medium", "high", "extreme"}
        for r in _demo_penny_stocks():
            assert r["risk_level"] in valid


class TestDemoPriceHistory:
    def test_length_matches_days(self):
        history = _demo_price_history("ABCD", 30)
        assert len(history) == 30

    def test_prices_positive(self):
        for pt in _demo_price_history("WXYZ", 5):
            assert pt["close"] > 0

    def test_deterministic(self):
        assert _demo_price_history("ABCD", 5) == _demo_price_history("ABCD", 5)


class TestDemoCatalystEvents:
    def test_returns_list(self):
        assert isinstance(_demo_catalyst_events("ABCD", 30), list)


# =========================================================================
# Pure data-assembly helpers
# =========================================================================

class TestSelectTopPennyStocks:
    def test_sorts_descending_by_momentum(self):
        rows = [
            {"ticker": "A", "momentum_score": 10.0},
            {"ticker": "B", "momentum_score": 90.0},
            {"ticker": "C", "momentum_score": 50.0},
        ]
        ranked = select_top_penny_stocks(rows)
        scores = [r["momentum_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)
        assert ranked[0]["ticker"] == "B"

    def test_respects_limit(self):
        rows = [{"ticker": str(i), "momentum_score": float(i)} for i in range(50)]
        ranked = select_top_penny_stocks(rows, limit=20)
        assert len(ranked) == 20

    def test_default_limit_is_20(self):
        rows = [{"ticker": str(i), "momentum_score": float(i)} for i in range(50)]
        ranked = select_top_penny_stocks(rows)
        assert len(ranked) == TOP_PENNY_LIMIT == 20

    def test_handles_missing_momentum(self):
        rows = [{"ticker": "A"}, {"ticker": "B", "momentum_score": 5.0}]
        ranked = select_top_penny_stocks(rows)
        assert ranked[0]["ticker"] == "B"

    def test_empty_list(self):
        assert select_top_penny_stocks([]) == []


class TestBuildTableRows:
    def test_columns_present(self):
        rows = _demo_penny_stocks()
        table = build_table_rows(rows)
        expected_cols = {"Ticker", "Price", "% Change", "Vol Ratio", "Momentum", "Risk"}
        for tr in table:
            assert set(tr.keys()) == expected_cols

    def test_preserves_order_and_count(self):
        rows = _demo_penny_stocks()
        table = build_table_rows(rows)
        assert len(table) == len(rows)
        assert table[0]["Ticker"] == rows[0]["ticker"]

    def test_formatting(self):
        rows = [{
            "ticker": "TST", "price": 1.5, "price_change_pct": 25.0,
            "volume_ratio": 3.2, "momentum_score": 77.7, "risk_level": "high",
        }]
        tr = build_table_rows(rows)[0]
        assert tr["Price"] == "$1.50"
        assert tr["% Change"] == "+25.00%"
        assert tr["Vol Ratio"] == "3.20x"
        assert tr["Momentum"] == "77.7"
        assert tr["Risk"] == "High"


class TestComputeSectorDistribution:
    def test_counts_sectors(self):
        rows = [
            {"sector": "Technology"},
            {"sector": "Technology"},
            {"sector": "Healthcare"},
        ]
        dist = compute_sector_distribution(rows)
        assert dist == {"Technology": 2, "Healthcare": 1}

    def test_total_equals_input(self):
        rows = _demo_penny_stocks()
        dist = compute_sector_distribution(rows)
        assert sum(dist.values()) == len(rows)

    def test_missing_sector_becomes_unknown(self):
        dist = compute_sector_distribution([{"ticker": "X"}])
        assert dist == {"Unknown": 1}

    def test_empty(self):
        assert compute_sector_distribution([]) == {}


class TestFetchPennyStocks:
    def test_returns_list(self):
        assert isinstance(fetch_penny_stocks(), list)

    def test_respects_limit(self):
        rows = fetch_penny_stocks(limit=5)
        assert len(rows) <= 5

    def test_ranked_descending(self):
        rows = fetch_penny_stocks()
        scores = [r.get("momentum_score", 0.0) for r in rows]
        assert scores == sorted(scores, reverse=True)


# =========================================================================
# Refresh-interval helpers (Property 53 support)
# =========================================================================

class TestRefreshInterval:
    def test_interval_within_bound(self):
        assert get_refresh_interval_seconds() <= MAX_REFRESH_INTERVAL_SECONDS

    def test_interval_positive(self):
        assert get_refresh_interval_seconds() > 0

    def test_max_bound_is_two_minutes(self):
        assert MAX_REFRESH_INTERVAL_SECONDS == 120

    def test_configured_interval_within_bound(self):
        assert PENNY_DASHBOARD_REFRESH_SECONDS <= MAX_REFRESH_INTERVAL_SECONDS

    def test_should_refresh_after_interval(self):
        last = datetime.utcnow() - timedelta(seconds=get_refresh_interval_seconds() + 1)
        assert should_refresh(last) is True

    def test_should_not_refresh_before_interval(self):
        last = datetime.utcnow()
        assert should_refresh(last) is False

    def test_seconds_until_next_never_exceeds_interval(self):
        last = datetime.utcnow()
        remaining = seconds_until_next_refresh(last)
        assert 0.0 <= remaining <= get_refresh_interval_seconds()

    def test_seconds_until_next_zero_when_overdue(self):
        last = datetime.utcnow() - timedelta(seconds=10_000)
        assert seconds_until_next_refresh(last) == 0.0


# =========================================================================
# Formatting helpers
# =========================================================================

class TestFormatting:
    def test_fmt_price(self):
        assert _fmt_price(1.5) == "$1.50"

    def test_fmt_pct_positive(self):
        assert _fmt_pct(3.0) == "+3.00%"

    def test_fmt_pct_negative(self):
        assert _fmt_pct(-2.0).startswith("-")

    def test_fmt_volume(self):
        assert _fmt_volume(2_500_000) == "2.5M"
        assert _fmt_volume(25_000) == "25K"
        assert _fmt_volume(500) == "500"

    def test_pct_colour(self):
        assert _pct_colour(1.0) == "#00c853"
        assert _pct_colour(-1.0) == "#d50000"

    def test_risk_colour_known(self):
        assert _risk_colour("extreme") == "#d50000"
        assert _risk_colour("low") == "#00c853"

    def test_risk_colour_unknown(self):
        assert _risk_colour("zzz").startswith("#")

    def test_recommendation_colour(self):
        assert _recommendation_colour("avoid") == "#d50000"
        assert _recommendation_colour("safe") == "#00c853"


# =========================================================================
# Constants
# =========================================================================

class TestConstants:
    def test_top_limit_is_20(self):
        assert TOP_PENNY_LIMIT == 20

    def test_chart_timeframes(self):
        assert CHART_TIMEFRAMES == ("1D", "5D", "30D")

    def test_streamlit_available(self):
        assert STREAMLIT_AVAILABLE is True


# =========================================================================
# Section render smoke tests (Streamlit + Plotly stubbed)
# =========================================================================

class TestRenderPennyStockTable:
    def test_renders_without_exception(self):
        render_penny_stock_table(_demo_penny_stocks())

    def test_calls_subheader(self):
        _st_stub.subheader.reset_mock()
        render_penny_stock_table(_demo_penny_stocks())
        _st_stub.subheader.assert_called()

    def test_empty_rows_shows_info(self):
        _st_stub.info.reset_mock()
        render_penny_stock_table([])
        _st_stub.info.assert_called()


class TestRenderPennyStockCharts:
    def test_renders_without_exception(self):
        render_penny_stock_charts(_demo_penny_stocks())

    def test_calls_subheader(self):
        _st_stub.subheader.reset_mock()
        render_penny_stock_charts(_demo_penny_stocks())
        _st_stub.subheader.assert_called()


class TestRenderPennyStockMetrics:
    def test_renders_without_exception(self):
        render_penny_stock_metrics(_demo_penny_stocks())

    def test_calls_subheader(self):
        _st_stub.subheader.reset_mock()
        render_penny_stock_metrics(_demo_penny_stocks())
        _st_stub.subheader.assert_called()


class TestRenderSectorDistribution:
    def test_renders_without_exception(self):
        render_sector_distribution(_demo_penny_stocks())

    def test_calls_subheader(self):
        _st_stub.subheader.reset_mock()
        render_sector_distribution(_demo_penny_stocks())
        _st_stub.subheader.assert_called()

    def test_empty_shows_info(self):
        _st_stub.info.reset_mock()
        render_sector_distribution([])
        _st_stub.info.assert_called()


class TestRenderPennyDashboard:
    def test_renders_without_exception(self):
        render_penny_dashboard()

    def test_calls_title(self):
        _st_stub.title.reset_mock()
        render_penny_dashboard()
        _st_stub.title.assert_called_once()

    def test_title_mentions_penny(self):
        _st_stub.title.reset_mock()
        render_penny_dashboard()
        call_args = _st_stub.title.call_args
        title_text = call_args[0][0] if call_args[0] else str(call_args)
        assert "Penny" in title_text

    def test_calls_divider(self):
        _st_stub.divider.reset_mock()
        render_penny_dashboard()
        _st_stub.divider.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
