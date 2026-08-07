"""
Tests for NewsAlertDetector.

Unit tests cover every public method.
Property-based test covers Property 36:
    |current_sentiment - previous_sentiment| > threshold → alert triggered
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from hypothesis import given, settings
from hypothesis import strategies as st

from stockiq.data.models import (
    NewsArticle,
    EnrichedNewsArticle,
    SentimentScore,
    Entities,
    NewsCategory,
)
from stockiq.news.alerts.detector import NewsAlertDetector, AlertType, NewsAlert


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_article(
    tickers: List[str] | None = None,
    title: str = "Market Update",
    content: str = "",
    published_at: datetime | None = None,
    sentiment: SentimentScore | None = None,
    entities: Entities | None = None,
    category: NewsCategory = NewsCategory.GENERAL,
) -> EnrichedNewsArticle:
    """Build a minimal EnrichedNewsArticle for testing."""
    if published_at is None:
        published_at = datetime.now(timezone.utc)
    return EnrichedNewsArticle(
        id="test-001",
        title=title,
        content=content,
        source="TestSource",
        published_at=published_at,
        url="https://example.com/news/1",
        tickers=tickers or [],
        category=category,
        sentiment=sentiment,
        entities=entities,
        summary="",
        relevance_score=0.5,
    )


def _make_base_article(
    title: str = "Market Update",
    content: str = "",
    published_at: datetime | None = None,
    tickers: List[str] | None = None,
) -> NewsArticle:
    """Build a minimal NewsArticle for testing."""
    if published_at is None:
        published_at = datetime.now(timezone.utc)
    return NewsArticle(
        id="test-001",
        title=title,
        content=content,
        source="TestSource",
        published_at=published_at,
        url="https://example.com/news/1",
        tickers=tickers or [],
    )


@pytest.fixture
def detector() -> NewsAlertDetector:
    return NewsAlertDetector()


# ---------------------------------------------------------------------------
# should_alert
# ---------------------------------------------------------------------------


class TestShouldAlert:
    def test_returns_true_when_article_mentions_watchlist_ticker(self, detector):
        article = _make_article(tickers=["AAPL"])
        assert detector.should_alert(article, watchlist=["AAPL"]) is True

    def test_case_insensitive_ticker_matching(self, detector):
        article = _make_article(tickers=["aapl"])
        assert detector.should_alert(article, watchlist=["AAPL"]) is True

    def test_returns_false_when_no_overlap(self, detector):
        article = _make_article(tickers=["GOOG"])
        assert detector.should_alert(article, watchlist=["AAPL", "MSFT"]) is False

    def test_returns_false_for_empty_watchlist(self, detector):
        article = _make_article(tickers=["AAPL"])
        assert detector.should_alert(article, watchlist=[]) is False

    def test_returns_false_for_empty_article_tickers_and_no_sentiment(self, detector):
        article = _make_article(tickers=[])
        assert detector.should_alert(article, watchlist=["AAPL"]) is False

    def test_returns_true_when_sentiment_change_exceeds_threshold(self, detector):
        ticker = "TSLA"
        # Prime the cache with previous sentiment
        detector.update_sentiment(ticker, -0.2)
        # Article now has a very positive sentiment — change = 0.8 > 0.5
        sentiment = SentimentScore(overall=0.6, vader_score=0.6, finbert_score=0.6, confidence=0.9)
        article = _make_article(tickers=[ticker], sentiment=sentiment)
        # Article ticker is NOT in watchlist, but sentiment change should trigger
        assert detector.should_alert(article, watchlist=["OTHER"]) is True

    def test_entities_tickers_also_checked(self, detector):
        entities = Entities(tickers=["NVDA"])
        article = _make_article(tickers=[], entities=entities)
        assert detector.should_alert(article, watchlist=["NVDA"]) is True


# ---------------------------------------------------------------------------
# detect_breaking_news
# ---------------------------------------------------------------------------


class TestDetectBreakingNews:
    def test_article_published_now_is_breaking(self, detector):
        article = _make_article(published_at=datetime.now(timezone.utc))
        assert detector.detect_breaking_news(article) is True

    def test_article_published_29_minutes_ago_is_breaking(self, detector):
        published = datetime.now(timezone.utc) - timedelta(minutes=29)
        article = _make_article(published_at=published)
        assert detector.detect_breaking_news(article) is True

    def test_article_published_exactly_30_minutes_ago_is_breaking(self, detector):
        # boundary: age == 30 minutes exactly → still within window (<=)
        published = datetime.now(timezone.utc) - timedelta(minutes=30)
        article = _make_article(published_at=published)
        assert detector.detect_breaking_news(article) is True

    def test_article_published_31_minutes_ago_is_not_breaking(self, detector):
        published = datetime.now(timezone.utc) - timedelta(minutes=31)
        article = _make_article(published_at=published)
        assert detector.detect_breaking_news(article) is False

    def test_article_published_yesterday_is_not_breaking(self, detector):
        published = datetime.now(timezone.utc) - timedelta(days=1)
        article = _make_article(published_at=published)
        assert detector.detect_breaking_news(article) is False

    def test_naive_datetime_treated_as_utc(self, detector):
        # Naive datetime (no tzinfo) — should be treated as UTC
        naive_now = datetime.utcnow()
        article = _make_article(published_at=naive_now)
        assert detector.detect_breaking_news(article) is True


# ---------------------------------------------------------------------------
# detect_sentiment_change / detect_sentiment_change_with_score / update_sentiment
# ---------------------------------------------------------------------------


class TestDetectSentimentChange:
    def test_first_call_returns_false(self, detector):
        # No prior data → no change to detect
        assert detector.detect_sentiment_change("AAPL") is False

    def test_detect_sentiment_change_with_score_first_call_false(self, detector):
        assert detector.detect_sentiment_change_with_score("AAPL", 0.5) is False

    def test_significant_change_triggers(self, detector):
        # Seed with −0.3, then update with +0.4 → |0.4 − (−0.3)| = 0.7 > 0.5
        detector.update_sentiment("AAPL", -0.3)
        assert detector.detect_sentiment_change_with_score("AAPL", 0.4) is True

    def test_small_change_does_not_trigger(self, detector):
        detector.update_sentiment("AAPL", 0.1)
        # Change = |0.3 − 0.1| = 0.2 ≤ 0.5
        assert detector.detect_sentiment_change_with_score("AAPL", 0.3) is False

    def test_exactly_threshold_does_not_trigger(self, detector):
        # |current − previous| must be STRICTLY greater than threshold
        detector.update_sentiment("AAPL", 0.0)
        assert detector.detect_sentiment_change_with_score("AAPL", 0.5) is False

    def test_just_above_threshold_triggers(self, detector):
        detector.update_sentiment("AAPL", 0.0)
        assert detector.detect_sentiment_change_with_score("AAPL", 0.51) is True

    def test_negative_direction_change_triggers(self, detector):
        # Positive → strongly negative
        detector.update_sentiment("MSFT", 0.5)
        assert detector.detect_sentiment_change_with_score("MSFT", -0.1) is True

    def test_update_sentiment_returns_true_on_significant_change(self, detector):
        detector.update_sentiment("TSLA", -0.5)
        result = detector.update_sentiment("TSLA", 0.2)
        # |0.2 − (−0.5)| = 0.7 > 0.5
        assert result is True

    def test_update_sentiment_returns_false_on_first_call(self, detector):
        assert detector.update_sentiment("GOOG", 0.3) is False

    def test_cache_is_updated_after_check(self, detector):
        # After detect_sentiment_change_with_score, the cache stores the new value
        detector.update_sentiment("NVDA", 0.0)
        detector.detect_sentiment_change_with_score("NVDA", 0.3)
        # Now new baseline is 0.3; a further change of 0.2 should NOT trigger
        assert detector.detect_sentiment_change_with_score("NVDA", 0.5) is False

    def test_custom_threshold_respected(self, detector):
        detector.update_sentiment("AMD", 0.0)
        # With threshold=0.2: change 0.25 should trigger
        assert detector.detect_sentiment_change_with_score("AMD", 0.25, threshold=0.2) is True

    def test_tickers_are_case_insensitive(self, detector):
        detector.update_sentiment("aapl", -0.4)
        # Using uppercase — should use the same cache slot
        assert detector.detect_sentiment_change_with_score("AAPL", 0.2) is True


# ---------------------------------------------------------------------------
# detect_earnings_announcement
# ---------------------------------------------------------------------------


class TestDetectEarningsAnnouncement:
    @pytest.mark.parametrize("text", [
        "Company reports strong earnings for Q3",
        "EPS beat analyst expectations",
        "Revenue grew 20% year-over-year",
        "Quarterly results exceed guidance",
        "Company profit up despite headwinds",
        "Analyst guidance raised after the beat",
        "Company miss on earnings sends shares lower",
        "Positive outlook for next fiscal year",
    ])
    def test_positive_cases(self, detector, text):
        article = _make_base_article(title=text)
        assert detector.detect_earnings_announcement(article) is True

    @pytest.mark.parametrize("text", [
        "Company signs new partnership deal",
        "Regulatory approval received",
        "CEO comments on market conditions",
    ])
    def test_negative_cases(self, detector, text):
        article = _make_base_article(title=text)
        assert detector.detect_earnings_announcement(article) is False

    def test_keyword_in_content_detected(self, detector):
        article = _make_base_article(
            title="Company Update",
            content="The company announced strong quarterly results.",
        )
        assert detector.detect_earnings_announcement(article) is True

    def test_empty_article_returns_false(self, detector):
        article = _make_base_article(title="", content="")
        assert detector.detect_earnings_announcement(article) is False


# ---------------------------------------------------------------------------
# detect_ma_news
# ---------------------------------------------------------------------------


class TestDetectMaNews:
    @pytest.mark.parametrize("text", [
        "Mega Corp announces merger with rival",
        "Acquisition of startup for $2 billion",
        "Company plans to acquire smaller competitor",
        "Hostile takeover bid rejected by board",
        "Private equity buyout valued at $5B",
        "M&A activity surges in tech sector",
        "Deal between two industry leaders finalized",
        "Tender offer made for outstanding shares",
    ])
    def test_positive_cases(self, detector, text):
        article = _make_base_article(title=text)
        assert detector.detect_ma_news(article) is True

    @pytest.mark.parametrize("text", [
        "Company reports record earnings",
        "FDA approves new drug treatment",
        "CEO interviewed on CNBC",
    ])
    def test_negative_cases(self, detector, text):
        article = _make_base_article(title=text)
        assert detector.detect_ma_news(article) is False

    def test_keyword_in_content_detected(self, detector):
        article = _make_base_article(
            title="Corporate News",
            content="Sources say the acquisition of the startup was completed.",
        )
        assert detector.detect_ma_news(article) is True


# ---------------------------------------------------------------------------
# detect_regulatory_action
# ---------------------------------------------------------------------------


class TestDetectRegulatoryAction:
    @pytest.mark.parametrize("text", [
        "FDA approves new cancer drug",
        "SEC charges company with fraud",
        "FTC blocks proposed merger on antitrust grounds",
        "DOJ opens investigation into price fixing",
        "CFTC fines bank for market manipulation",
        "Regulatory approval granted for acquisition",
        "Enforcement action taken against broker",
        "Company under SEC investigation for insider trading",
        "Judge issues penalty against pharmaceutical firm",
        "Regulator imposes fine on bank",
    ])
    def test_positive_cases(self, detector, text):
        article = _make_base_article(title=text)
        assert detector.detect_regulatory_action(article) is True

    @pytest.mark.parametrize("text", [
        "Company posts strong quarterly earnings",
        "Merger between tech giants announced",
        "CEO steps down after board vote",
    ])
    def test_negative_cases(self, detector, text):
        article = _make_base_article(title=text)
        assert detector.detect_regulatory_action(article) is False

    def test_keyword_in_content_detected(self, detector):
        article = _make_base_article(
            title="Breaking News",
            content="The SEC today announced enforcement action against the company.",
        )
        assert detector.detect_regulatory_action(article) is True


# ---------------------------------------------------------------------------
# Property-based test: Property 36
# Hypothesis verifies that detect_sentiment_change_with_score triggers
# alerts if and only if |current - previous| > threshold.
# ---------------------------------------------------------------------------


class TestProperty36SentimentChange:
    @given(
        previous=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        current=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        threshold=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=500)
    def test_property_36_alert_iff_change_exceeds_threshold(
        self,
        previous: float,
        current: float,
        threshold: float,
    ):
        """
        Property 36: detect_sentiment_change triggers alert iff
        |current_sentiment - previous_sentiment| > threshold.
        """
        detector = NewsAlertDetector()
        detector.update_sentiment("TEST", previous)
        result = detector.detect_sentiment_change_with_score("TEST", current, threshold=threshold)
        expected = abs(current - previous) > threshold
        assert result is expected, (
            f"previous={previous}, current={current}, threshold={threshold}, "
            f"diff={abs(current - previous)}, expected={expected}, got={result}"
        )

    @given(
        sentiment=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_first_call_always_returns_false(self, sentiment: float):
        """
        On the first call for a ticker (no cached previous value),
        detect_sentiment_change_with_score must return False regardless of score.
        """
        detector = NewsAlertDetector()
        result = detector.detect_sentiment_change_with_score("NEWTIC", sentiment)
        assert result is False, (
            f"First call with sentiment={sentiment} should return False, got {result}"
        )

    @given(
        score=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_no_change_never_triggers(self, score: float):
        """Same value twice → no change → never triggers (with default threshold 0.5)."""
        detector = NewsAlertDetector()
        detector.update_sentiment("STABLE", score)
        result = detector.detect_sentiment_change_with_score("STABLE", score, threshold=0.5)
        assert result is False

    @given(
        previous=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        current=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=300)
    def test_update_sentiment_matches_expected(self, previous: float, current: float):
        """
        update_sentiment should return True iff |current - previous| > 0.5.
        """
        detector = NewsAlertDetector()
        detector.update_sentiment("CHK", previous)
        result = detector.update_sentiment("CHK", current)
        expected = abs(current - previous) > 0.5
        assert result is expected


# ---------------------------------------------------------------------------
# Integration: AlertType and NewsAlert dataclass
# ---------------------------------------------------------------------------


class TestAlertTypes:
    def test_alert_type_values(self):
        assert AlertType.BREAKING_NEWS == "breaking_news"
        assert AlertType.SENTIMENT_CHANGE == "sentiment_change"
        assert AlertType.EARNINGS == "earnings"
        assert AlertType.REGULATORY == "regulatory"

    def test_news_alert_creation(self):
        alert = NewsAlert(
            alert_type=AlertType.EARNINGS,
            ticker="AAPL",
            headline="Apple beats Q4 earnings",
            sentiment_score=0.8,
        )
        assert alert.ticker == "AAPL"
        assert alert.alert_type == AlertType.EARNINGS
        assert alert.triggered_at is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_should_alert_with_none_sentiment(self, detector):
        """Article with no sentiment should still match on ticker overlap."""
        article = _make_article(tickers=["AAPL"], sentiment=None)
        assert detector.should_alert(article, watchlist=["AAPL"]) is True

    def test_should_alert_no_tickers_no_sentiment(self, detector):
        article = _make_article(tickers=[], sentiment=None)
        assert detector.should_alert(article, watchlist=["AAPL"]) is False

    def test_detect_breaking_news_future_article(self, detector):
        """Article dated in the future should be breaking (age is negative → ≤ 30min)."""
        future = datetime.now(timezone.utc) + timedelta(seconds=60)
        article = _make_article(published_at=future)
        # age = now - future < 0 → timedelta is negative; -0:01 <= 0:30 is True
        assert detector.detect_breaking_news(article) is True

    def test_multiple_tickers_in_article(self, detector):
        article = _make_article(tickers=["AAPL", "MSFT", "GOOG"])
        assert detector.should_alert(article, watchlist=["GOOG"]) is True

    def test_earnings_keyword_case_insensitive(self, detector):
        article = _make_base_article(title="EARNINGS BEAT FOR Q3")
        assert detector.detect_earnings_announcement(article) is True

    def test_ma_keyword_case_insensitive(self, detector):
        article = _make_base_article(title="HOSTILE TAKEOVER ANNOUNCED")
        assert detector.detect_ma_news(article) is True

    def test_regulatory_keyword_case_insensitive(self, detector):
        article = _make_base_article(title="FDA APPROVES VACCINE")
        assert detector.detect_regulatory_action(article) is True
