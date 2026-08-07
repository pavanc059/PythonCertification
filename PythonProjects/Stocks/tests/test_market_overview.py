"""
Tests for stockiq/ui/components/market_overview.py

Covers:
- Demo / fallback data validity
- Formatting helpers
- Sentiment calculation logic
- Widget render functions (mocked Streamlit + Plotly)

Requirements addressed: 1.8, 1.9, 4.5, 4.6, 4.8, 4.9
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub Streamlit before the module loads (no live server required)
# ---------------------------------------------------------------------------

def _make_st_stub() -> types.ModuleType:
    st = types.ModuleType("streamlit")
    for attr in (
        "subheader", "markdown", "info", "caption", "divider",
        "container", "metric",
    ):
        setattr(st, attr, MagicMock())

    def _columns(spec):
        n = len(spec) if hasattr(spec, "__len__") else int(spec)
        return [
            MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
            for _ in range(n)
        ]

    st.columns = _columns
    st.plotly_chart = MagicMock()
    st.cache_data = lambda ttl=None: (lambda fn: fn)
    return st


_st = _make_st_stub()
sys.modules["streamlit"] = _st


# Stub plotly.graph_objects
def _make_plotly_stub() -> None:
    plotly_mod = types.ModuleType("plotly")
    go_mod = types.ModuleType("plotly.graph_objects")

    class _FigureStub:
        def __init__(self, *args, **kwargs):
            self.data = [MagicMock()]
        def update_layout(self, **kwargs): pass
        def update_traces(self, **kwargs): pass

    go_mod.Figure = _FigureStub
    go_mod.Treemap = MagicMock(return_value=MagicMock())
    go_mod.Indicator = MagicMock(return_value=MagicMock())

    sys.modules.setdefault("plotly", plotly_mod)
    sys.modules["plotly.graph_objects"] = go_mod


_make_plotly_stub()

# Now import the module under test
from stockiq.ui.components.market_overview import (  # noqa: E402
    _demo_indices,
    _demo_sectors,
    _demo_economic_events,
    _calculate_market_sentiment,
    _change_colour,
    _fmt_price,
    _fmt_pct,
    _importance_badge,
    _fetch_index_data,
    _fetch_sector_data,
    _fetch_economic_events,
    render_market_indices,
    render_sector_heatmap,
    render_market_sentiment_gauge,
    render_economic_calendar,
    MARKET_INDICES,
    SECTOR_ETFS,
    STREAMLIT_AVAILABLE,
    YFINANCE_AVAILABLE,
)


# =========================================================================
# Demo data tests
# =========================================================================

class TestDemoIndices:
    def test_returns_four_indices(self):
        assert len(_demo_indices()) == 4

    def test_required_keys(self):
        required = {"ticker", "name", "price", "change", "change_pct", "prev_close"}
        for idx in _demo_indices():
            assert required.issubset(idx.keys()), f"Missing keys: {idx}"

    def test_prices_positive(self):
        for idx in _demo_indices():
            assert idx["price"] > 0, f"{idx['ticker']} price must be positive"

    def test_expected_tickers(self):
        tickers = {d["ticker"] for d in _demo_indices()}
        assert "^GSPC" in tickers
        assert "^IXIC" in tickers
        assert "^DJI"  in tickers
        assert "^RUT"  in tickers

    def test_change_consistency(self):
        """change == price - prev_close (within floating-point tolerance)."""
        for idx in _demo_indices():
            expected = idx["price"] - idx["prev_close"]
            assert abs(idx["change"] - expected) < 0.01, (
                f"{idx['ticker']}: change mismatch"
            )


class TestDemoSectors:
    def test_returns_eleven_sectors(self):
        assert len(_demo_sectors()) == 11

    def test_required_keys(self):
        required = {"ticker", "name", "change_pct"}
        for s in _demo_sectors():
            assert required.issubset(s.keys()), f"Missing keys: {s}"

    def test_expected_sector_etfs(self):
        tickers = {s["ticker"] for s in _demo_sectors()}
        for expected_ticker, _ in SECTOR_ETFS:
            assert expected_ticker in tickers, f"{expected_ticker} missing from demo sectors"


class TestDemoEconomicEvents:
    def test_returns_events(self):
        events = _demo_economic_events()
        assert len(events) >= 1

    def test_required_keys(self):
        required = {"time", "event", "importance", "prior", "forecast"}
        for ev in _demo_economic_events():
            assert required.issubset(ev.keys()), f"Missing keys: {ev}"

    def test_importance_valid_values(self):
        valid = {"high", "medium", "low"}
        for ev in _demo_economic_events():
            assert ev["importance"] in valid, (
                f"Invalid importance '{ev['importance']}'"
            )

    def test_actual_is_none_or_string(self):
        for ev in _demo_economic_events():
            assert ev.get("actual") is None or isinstance(ev["actual"], str)


# =========================================================================
# Sentiment calculation
# =========================================================================

class TestCalculateMarketSentiment:
    def test_all_up_sectors_is_positive(self):
        indices = [{"change_pct": 1.0}] * 4
        sectors = [{"change_pct": 1.0}] * 11
        score = _calculate_market_sentiment(indices, sectors)
        assert score > 0

    def test_all_down_sectors_is_negative(self):
        indices = [{"change_pct": -1.0}] * 4
        sectors = [{"change_pct": -1.0}] * 11
        score = _calculate_market_sentiment(indices, sectors)
        assert score < 0

    def test_flat_market_near_zero(self):
        indices = [{"change_pct": 0.0}] * 4
        sectors = [{"change_pct": 0.0}] * 11
        score = _calculate_market_sentiment(indices, sectors)
        assert abs(score) < 5.0, f"Expected near zero, got {score}"

    def test_output_clamped_to_range(self):
        # Extreme gains
        indices = [{"change_pct": 100.0}] * 4
        sectors = [{"change_pct": 100.0}] * 11
        score = _calculate_market_sentiment(indices, sectors)
        assert -100.0 <= score <= 100.0

        # Extreme losses
        indices = [{"change_pct": -100.0}] * 4
        sectors = [{"change_pct": -100.0}] * 11
        score = _calculate_market_sentiment(indices, sectors)
        assert -100.0 <= score <= 100.0

    def test_empty_inputs_returns_zero(self):
        score = _calculate_market_sentiment([], [])
        assert score == 0.0

    def test_mixed_sectors_intermediate(self):
        indices = [{"change_pct": 0.5}] * 4
        # 6 up, 5 down
        sectors = [{"change_pct": 0.5}] * 6 + [{"change_pct": -0.5}] * 5
        score = _calculate_market_sentiment(indices, sectors)
        # Slight positive (more up than down, positive index)
        assert score > 0


# =========================================================================
# Formatting helpers
# =========================================================================

class TestChangeColour:
    def test_positive_green(self):
        assert _change_colour(0.5) == "#00c853"

    def test_zero_green(self):
        assert _change_colour(0.0) == "#00c853"

    def test_negative_red(self):
        assert _change_colour(-0.5) == "#d50000"


class TestFmtPrice:
    def test_large_price_no_decimal(self):
        result = _fmt_price(39_000.0)
        assert "." not in result   # no decimals for prices ≥10k
        assert "," in result        # thousands separator

    def test_small_price_two_decimal(self):
        assert _fmt_price(4.99) == "4.99"

    def test_medium_price(self):
        result = _fmt_price(5_304.72)
        assert "5,304.72" in result


class TestFmtPct:
    def test_positive_has_plus(self):
        result = _fmt_pct(1.25)
        assert result.startswith("+")
        assert "1.25%" in result

    def test_negative_has_minus(self):
        result = _fmt_pct(-1.25)
        assert result.startswith("-")
        assert "1.25%" in result

    def test_zero(self):
        assert _fmt_pct(0.0) == "+0.00%"

    def test_unsigned_positive(self):
        result = _fmt_pct(1.25, signed=False)
        assert not result.startswith("+")

    def test_unsigned_zero(self):
        result = _fmt_pct(0.0, signed=False)
        assert not result.startswith("+")


class TestImportanceBadge:
    def test_high_red(self):
        assert _importance_badge("high") == "🔴"

    def test_medium_yellow(self):
        assert _importance_badge("medium") == "🟡"

    def test_low_green(self):
        assert _importance_badge("low") == "🟢"

    def test_unknown_returns_white(self):
        assert _importance_badge("extreme") == "⚪"

    def test_case_insensitive(self):
        assert _importance_badge("HIGH") == "🔴"
        assert _importance_badge("Medium") == "🟡"


# =========================================================================
# Data fetch helpers
# =========================================================================

class TestFetchIndexData:
    def test_returns_list(self):
        result = _fetch_index_data()
        assert isinstance(result, list)

    def test_returns_four_indices(self):
        result = _fetch_index_data()
        assert len(result) == 4

    def test_required_keys(self):
        required = {"ticker", "name", "price", "change", "change_pct"}
        for idx in _fetch_index_data():
            assert required.issubset(idx.keys())


class TestFetchSectorData:
    def test_returns_list(self):
        result = _fetch_sector_data()
        assert isinstance(result, list)

    def test_returns_eleven_sectors(self):
        result = _fetch_sector_data()
        assert len(result) == 11

    def test_required_keys(self):
        required = {"ticker", "name", "change_pct"}
        for s in _fetch_sector_data():
            assert required.issubset(s.keys())


class TestFetchEconomicEvents:
    def test_returns_list(self):
        assert isinstance(_fetch_economic_events(), list)

    def test_returns_events(self):
        events = _fetch_economic_events()
        assert len(events) >= 1


# =========================================================================
# Constants
# =========================================================================

class TestConstants:
    def test_market_indices_count(self):
        assert len(MARKET_INDICES) == 4

    def test_market_indices_tickers(self):
        tickers = [t for t, _ in MARKET_INDICES]
        assert "^GSPC" in tickers
        assert "^IXIC" in tickers
        assert "^DJI"  in tickers
        assert "^RUT"  in tickers

    def test_sector_etfs_count(self):
        assert len(SECTOR_ETFS) == 11

    def test_streamlit_available(self):
        # Stub is injected, so this should be True
        assert STREAMLIT_AVAILABLE is True


# =========================================================================
# Render function smoke tests (Streamlit is stubbed)
# =========================================================================

class TestRenderMarketIndices:
    def test_renders_without_exception(self):
        render_market_indices()

    def test_calls_subheader(self):
        _st.subheader.reset_mock()
        render_market_indices()
        _st.subheader.assert_called()

    def test_calls_columns_with_four(self):
        column_specs = []

        def _track(spec):
            column_specs.append(spec)
            n = len(spec) if hasattr(spec, "__len__") else int(spec)
            return [
                MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
                for _ in range(n)
            ]

        with patch.object(_st, "columns", side_effect=_track):
            render_market_indices()

        def _col_count(s):
            return len(s) if hasattr(s, "__len__") else int(s)

        four_col_calls = [s for s in column_specs if _col_count(s) == 4]
        assert len(four_col_calls) >= 1


class TestRenderSectorHeatmap:
    def test_renders_without_exception(self):
        render_sector_heatmap()

    def test_calls_subheader(self):
        _st.subheader.reset_mock()
        render_sector_heatmap()
        _st.subheader.assert_called()

    def test_calls_plotly_chart(self):
        _st.plotly_chart.reset_mock()
        render_sector_heatmap()
        _st.plotly_chart.assert_called()


class TestRenderMarketSentimentGauge:
    def test_renders_without_exception(self):
        render_market_sentiment_gauge()

    def test_calls_subheader(self):
        _st.subheader.reset_mock()
        render_market_sentiment_gauge()
        _st.subheader.assert_called()

    def test_calls_plotly_chart(self):
        _st.plotly_chart.reset_mock()
        render_market_sentiment_gauge()
        _st.plotly_chart.assert_called()

    def test_calls_columns_for_legend(self):
        column_specs = []

        def _track(spec):
            column_specs.append(spec)
            n = len(spec) if hasattr(spec, "__len__") else int(spec)
            return [
                MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
                for _ in range(n)
            ]

        with patch.object(_st, "columns", side_effect=_track):
            render_market_sentiment_gauge()

        def _col_count(s):
            return len(s) if hasattr(s, "__len__") else int(s)

        three_col_calls = [s for s in column_specs if _col_count(s) == 3]
        assert len(three_col_calls) >= 1


class TestRenderEconomicCalendar:
    def test_renders_without_exception(self):
        render_economic_calendar()

    def test_calls_subheader(self):
        _st.subheader.reset_mock()
        render_economic_calendar()
        _st.subheader.assert_called()

    def test_displays_events(self):
        """With events present, markdown should be called multiple times."""
        _st.markdown.reset_mock()
        render_economic_calendar()
        assert _st.markdown.call_count > 1

    def test_shows_no_events_when_empty(self):
        """When _fetch_economic_events returns [], st.info is called."""
        _st.info.reset_mock()
        with patch(
            "stockiq.ui.components.market_overview._fetch_economic_events",
            return_value=[],
        ):
            render_economic_calendar()
        _st.info.assert_called_once()
