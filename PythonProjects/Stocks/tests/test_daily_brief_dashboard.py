"""
Tests for the Daily Market Brief Dashboard.

Tests cover:
- Demo / fallback data validity
- Formatting helpers
- Section render functions (mocked Streamlit context)
- render_daily_dashboard() structure

Requirements addressed: 4.1-4.4, 4.12
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Stub out Streamlit before the module loads so tests run without a live
# Streamlit server.
# ---------------------------------------------------------------------------

def _make_streamlit_stub() -> types.ModuleType:
    """Build a minimal Streamlit stub that records calls."""
    st = types.ModuleType("streamlit")

    # Simple no-op / recorder stubs
    for attr in (
        "title", "caption", "divider", "subheader", "markdown", "info",
        "container", "progress",
    ):
        setattr(st, attr, MagicMock())

    # columns() must return a context manager pair/triple
    def _columns(spec):
        n = len(spec) if hasattr(spec, "__len__") else int(spec)
        cols = [MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
                for _ in range(n)]
        return cols

    st.columns = _columns
    st.cache_data = lambda ttl=None: (lambda fn: fn)  # pass-through decorator
    return st


# Inject the stub before importing the module under test
_st_stub = _make_streamlit_stub()
sys.modules["streamlit"] = _st_stub

# Also stub plotly so it isn't required for tests
_plotly_go = types.ModuleType("plotly.graph_objects")
_plotly_px = types.ModuleType("plotly.express")
sys.modules.setdefault("plotly", types.ModuleType("plotly"))
sys.modules["plotly.graph_objects"] = _plotly_go
sys.modules["plotly.express"] = _plotly_px

# Now import the module under test
from stockiq.ui.dashboards.daily_brief import (  # noqa: E402
    _demo_gainers,
    _demo_losers,
    _demo_news,
    _demo_predictions,
    _sentiment_badge,
    _sentiment_label,
    _category_colour,
    _pct_colour,
    _fmt_volume,
    _fmt_price,
    _fmt_pct,
    _time_ago,
    _confidence_colour,
    _return_pct,
    _fetch_top_movers,
    _fetch_top_news,
    _fetch_predictions,
    render_top_movers_section,
    render_news_section,
    render_predictions_section,
    render_daily_dashboard,
    TOP_MOVERS_LIMIT,
    NEWS_DISPLAY_LIMIT,
    DASHBOARD_CACHE_TTL,
    STREAMLIT_AVAILABLE,
)


# =========================================================================
# Demo data tests
# =========================================================================

class TestDemoGainers:
    def test_returns_ten_items(self):
        assert len(_demo_gainers()) == 10

    def test_all_positive_pct(self):
        for g in _demo_gainers():
            assert g["price_change_pct"] > 0, f"{g['ticker']} should be a gainer"

    def test_required_keys(self):
        required = {"ticker", "name", "price_change_pct", "current_price",
                    "volume", "avg_volume", "sector", "has_unusual_volume"}
        for g in _demo_gainers():
            assert required.issubset(g.keys()), f"Missing keys in {g}"

    def test_sorted_descending(self):
        pcts = [g["price_change_pct"] for g in _demo_gainers()]
        assert pcts == sorted(pcts, reverse=True)


class TestDemoLosers:
    def test_returns_ten_items(self):
        assert len(_demo_losers()) == 10

    def test_all_negative_pct(self):
        for lo in _demo_losers():
            assert lo["price_change_pct"] < 0, f"{lo['ticker']} should be a loser"

    def test_required_keys(self):
        required = {"ticker", "name", "price_change_pct", "current_price",
                    "volume", "avg_volume", "sector", "has_unusual_volume"}
        for lo in _demo_losers():
            assert required.issubset(lo.keys()), f"Missing keys in {lo}"

    def test_sorted_ascending(self):
        pcts = [lo["price_change_pct"] for lo in _demo_losers()]
        assert pcts == sorted(pcts)


class TestDemoNews:
    def test_returns_five_items(self):
        assert len(_demo_news()) == 5

    def test_required_keys(self):
        required = {"title", "source", "published_at", "sentiment",
                    "category", "is_breaking", "summary", "tickers", "url"}
        for article in _demo_news():
            assert required.issubset(article.keys()), f"Missing keys in {article}"

    def test_sentiment_in_range(self):
        for article in _demo_news():
            s = article["sentiment"]
            assert -1.0 <= s <= 1.0, f"Sentiment {s} out of [-1, 1] for {article['title']}"

    def test_published_at_is_datetime(self):
        for article in _demo_news():
            assert isinstance(article["published_at"], datetime)


class TestDemoPredictions:
    def test_returns_items(self):
        assert len(_demo_predictions()) > 0

    def test_required_keys(self):
        required = {"ticker", "category", "confidence", "value",
                    "lower_bound", "upper_bound", "low_confidence"}
        for pred in _demo_predictions():
            assert required.issubset(pred.keys()), f"Missing keys in {pred}"

    def test_confidence_in_range(self):
        for pred in _demo_predictions():
            c = pred["confidence"]
            assert 0.0 <= c <= 100.0, f"Confidence {c} out of [0, 100] for {pred['ticker']}"

    def test_low_confidence_flag_consistency(self):
        """low_confidence should be True when confidence < 60."""
        for pred in _demo_predictions():
            if pred["confidence"] < 60.0:
                assert pred["low_confidence"] is True, (
                    f"{pred['ticker']}: confidence={pred['confidence']} "
                    "but low_confidence is False"
                )

    def test_bounds_consistency(self):
        """lower_bound <= value <= upper_bound for every prediction."""
        for pred in _demo_predictions():
            assert pred["lower_bound"] <= pred["value"] <= pred["upper_bound"], (
                f"{pred['ticker']}: bounds ({pred['lower_bound']}, {pred['upper_bound']}) "
                f"don't bracket value {pred['value']}"
            )

    def test_valid_categories(self):
        valid = {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"}
        for pred in _demo_predictions():
            assert pred["category"] in valid, (
                f"{pred['ticker']} has unknown category '{pred['category']}'"
            )


# =========================================================================
# Formatting helpers
# =========================================================================

class TestSentimentBadge:
    def test_positive_returns_green(self):
        assert _sentiment_badge(0.5) == "🟢"

    def test_negative_returns_red(self):
        assert _sentiment_badge(-0.5) == "🔴"

    def test_neutral_returns_yellow(self):
        assert _sentiment_badge(0.0) == "🟡"

    def test_boundary_positive(self):
        # 0.15 is the threshold; just above → green
        assert _sentiment_badge(0.16) == "🟢"

    def test_boundary_negative(self):
        assert _sentiment_badge(-0.16) == "🔴"

    def test_at_threshold_neutral(self):
        assert _sentiment_badge(0.15) == "🟡"
        assert _sentiment_badge(-0.15) == "🟡"


class TestSentimentLabel:
    def test_positive_label(self):
        label = _sentiment_label(0.8)
        assert label.startswith("Positive")
        assert "+0.80" in label

    def test_negative_label(self):
        label = _sentiment_label(-0.6)
        assert label.startswith("Negative")
        assert "-0.60" in label

    def test_neutral_label(self):
        label = _sentiment_label(0.0)
        assert label.startswith("Neutral")


class TestCategoryColour:
    def test_strong_buy_colour(self):
        assert _category_colour("Strong Buy") == "#00c853"

    def test_strong_sell_colour(self):
        assert _category_colour("Strong Sell") == "#d50000"

    def test_unknown_returns_fallback(self):
        colour = _category_colour("Unknown Category")
        assert colour.startswith("#")


class TestPctColour:
    def test_positive_green(self):
        assert _pct_colour(1.0) == "#00c853"

    def test_zero_green(self):
        assert _pct_colour(0.0) == "#00c853"

    def test_negative_red(self):
        assert _pct_colour(-1.0) == "#d50000"


class TestFmtVolume:
    def test_millions(self):
        assert _fmt_volume(5_000_000) == "5.0M"

    def test_thousands(self):
        assert _fmt_volume(25_000) == "25K"

    def test_small(self):
        assert _fmt_volume(500) == "500"


class TestFmtPrice:
    def test_format(self):
        assert _fmt_price(1234.56) == "$1,234.56"

    def test_small_price(self):
        assert _fmt_price(4.99) == "$4.99"


class TestFmtPct:
    def test_positive(self):
        result = _fmt_pct(3.75)
        assert result.startswith("+")
        assert "3.75%" in result

    def test_negative(self):
        result = _fmt_pct(-2.50)
        assert result.startswith("-")
        assert "2.50%" in result

    def test_zero(self):
        result = _fmt_pct(0.0)
        assert "+0.00%" == result


class TestTimeAgo:
    def test_seconds(self):
        dt = datetime.utcnow() - timedelta(seconds=45)
        assert "s ago" in _time_ago(dt)

    def test_minutes(self):
        dt = datetime.utcnow() - timedelta(minutes=30)
        assert "m ago" in _time_ago(dt)

    def test_hours(self):
        dt = datetime.utcnow() - timedelta(hours=3)
        assert "h ago" in _time_ago(dt)

    def test_days(self):
        dt = datetime.utcnow() - timedelta(days=2)
        # Should return a date string like "Jun 17"
        assert "ago" not in _time_ago(dt)


class TestConfidenceColour:
    def test_high_confidence(self):
        assert _confidence_colour(80.0) == "#00c853"

    def test_medium_confidence(self):
        assert _confidence_colour(65.0) == "#ffd740"

    def test_low_confidence(self):
        assert _confidence_colour(50.0) == "#ff6d00"


class TestReturnPct:
    def test_positive(self):
        assert _return_pct(0.05) == "+5.00%"

    def test_negative(self):
        assert _return_pct(-0.03) == "-3.00%"

    def test_zero(self):
        assert _return_pct(0.0) == "+0.00%"


# =========================================================================
# Constants
# =========================================================================

class TestConstants:
    def test_top_movers_limit(self):
        assert TOP_MOVERS_LIMIT == 10

    def test_news_display_limit(self):
        assert NEWS_DISPLAY_LIMIT == 5

    def test_cache_ttl_positive(self):
        assert DASHBOARD_CACHE_TTL > 0

    def test_streamlit_available(self):
        # Our stub means it should be True in this test context
        assert STREAMLIT_AVAILABLE is True


# =========================================================================
# Data-fetch helpers (using demo fallback)
# =========================================================================

class TestFetchTopMovers:
    """_fetch_top_movers() should return (gainers, losers) as lists of dicts."""

    def test_returns_tuple_of_two_lists(self):
        gainers, losers = _fetch_top_movers()
        assert isinstance(gainers, list)
        assert isinstance(losers, list)

    def test_gainers_length(self):
        gainers, _ = _fetch_top_movers()
        assert 1 <= len(gainers) <= TOP_MOVERS_LIMIT

    def test_losers_length(self):
        _, losers = _fetch_top_movers()
        assert 1 <= len(losers) <= TOP_MOVERS_LIMIT

    def test_gainers_have_required_keys(self):
        required = {"ticker", "price_change_pct", "current_price"}
        gainers, _ = _fetch_top_movers()
        for g in gainers:
            assert required.issubset(g.keys())

    def test_losers_have_required_keys(self):
        required = {"ticker", "price_change_pct", "current_price"}
        _, losers = _fetch_top_movers()
        for lo in losers:
            assert required.issubset(lo.keys())


class TestFetchTopNews:
    def test_returns_list(self):
        articles = _fetch_top_news()
        assert isinstance(articles, list)

    def test_respects_limit(self):
        articles = _fetch_top_news(limit=3)
        assert len(articles) <= 3

    def test_default_limit(self):
        articles = _fetch_top_news()
        assert len(articles) <= NEWS_DISPLAY_LIMIT

    def test_articles_have_required_keys(self):
        required = {"title", "source", "sentiment", "is_breaking"}
        for a in _fetch_top_news():
            assert required.issubset(a.keys())

    def test_sentiment_in_range(self):
        for a in _fetch_top_news():
            s = a["sentiment"]
            assert -1.0 <= s <= 1.0


class TestFetchPredictions:
    def test_returns_list(self):
        preds = _fetch_predictions()
        assert isinstance(preds, list)

    def test_predictions_have_required_keys(self):
        required = {"ticker", "category", "confidence", "value"}
        for p in _fetch_predictions():
            assert required.issubset(p.keys())

    def test_confidence_in_range(self):
        for p in _fetch_predictions():
            assert 0.0 <= p["confidence"] <= 100.0


# =========================================================================
# Section render smoke tests (Streamlit is stubbed)
# =========================================================================

class TestRenderTopMoversSection:
    def test_renders_without_exception(self):
        """render_top_movers_section() should not raise."""
        render_top_movers_section()

    def test_calls_streamlit_subheader(self):
        _st_stub.subheader.reset_mock()
        render_top_movers_section()
        _st_stub.subheader.assert_called()


class TestRenderNewsSection:
    def test_renders_without_exception(self):
        render_news_section()

    def test_calls_streamlit_subheader(self):
        _st_stub.subheader.reset_mock()
        render_news_section()
        _st_stub.subheader.assert_called()

    def test_renders_all_articles(self):
        """render_news_section should render each article (one st.subheader + items)."""
        # Patch _fetch_top_news to guarantee demo data (avoids live Redis dependency)
        with patch(
            "stockiq.ui.dashboards.daily_brief._fetch_top_news",
            return_value=_demo_news()[:NEWS_DISPLAY_LIMIT],
        ):
            _st_stub.divider.reset_mock()
            render_news_section()
            # One st.divider() call per news item
            assert _st_stub.divider.call_count >= NEWS_DISPLAY_LIMIT


class TestRenderPredictionsSection:
    def test_renders_without_exception(self):
        render_predictions_section()

    def test_calls_progress_for_each_prediction(self):
        _st_stub.progress.reset_mock()
        render_predictions_section()
        preds = _demo_predictions()
        assert _st_stub.progress.call_count == len(preds)


class TestRenderDailyDashboard:
    def test_renders_without_exception(self):
        render_daily_dashboard()

    def test_calls_title(self):
        _st_stub.title.reset_mock()
        render_daily_dashboard()
        _st_stub.title.assert_called_once()

    def test_title_contains_market_brief(self):
        _st_stub.title.reset_mock()
        render_daily_dashboard()
        call_args = _st_stub.title.call_args
        title_text = call_args[0][0] if call_args[0] else str(call_args)
        assert "Market Brief" in title_text or "Daily" in title_text

    def test_calls_divider(self):
        _st_stub.divider.reset_mock()
        render_daily_dashboard()
        _st_stub.divider.assert_called()

    def test_three_columns_created(self):
        """render_daily_dashboard should call st.columns with a 3-element spec."""
        columns_specs = []

        def _track_columns(spec):
            columns_specs.append(spec)
            n = len(spec) if hasattr(spec, "__len__") else int(spec)
            return [
                MagicMock(__enter__=lambda s: s, __exit__=MagicMock(return_value=False))
                for _ in range(n)
            ]

        with patch.object(_st_stub, "columns", side_effect=_track_columns):
            render_daily_dashboard()

        # At least one call to st.columns should have produced 3 columns
        three_col_calls = [s for s in columns_specs if hasattr(s, "__len__") and len(s) == 3]
        assert len(three_col_calls) >= 1, (
            "Expected at least one st.columns([...]) call with 3 columns"
        )
