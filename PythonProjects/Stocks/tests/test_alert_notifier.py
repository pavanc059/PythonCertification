"""
Tests for AlertNotifier class in stockiq/news/alerts/notifier.py.

Covers:
- send_alert routing to correct channels
- send_in_app_notification DB storage (mock DB)
- send_email_notification SMTP dispatch (mock SMTP)
- send_webhook_notification HTTP POST (mock requests)
- Retry logic triggers on failures (3 attempts, exponential backoff)
- configure_alert_sensitivity with valid/invalid inputs
- HTML email template contains required fields
- Graceful degradation when dependencies missing

Requirements: 5.9, 17.6
"""

from __future__ import annotations

import json
import smtplib
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock, patch, call

import pytest

from stockiq.news.alerts.detector import AlertType, NewsAlert
from stockiq.news.alerts.notifier import (
    MAX_RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
    SUPPORTED_CHANNELS,
    VALID_SENSITIVITIES,
    AlertNotifier,
    UserNotificationSettings,
    _build_html_email,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_alert(
    ticker: str = "AAPL",
    alert_type: AlertType = AlertType.GENERAL,
    headline: str = "Apple reports record revenue",
    sentiment_score: float = 0.5,
    predicted_impact: Optional[float] = 0.3,
    article_id: Optional[str] = "art-001",
    details: Optional[dict] = None,
) -> NewsAlert:
    if details is None:
        details = {}
    return NewsAlert(
        alert_type=alert_type,
        ticker=ticker,
        headline=headline,
        sentiment_score=sentiment_score,
        predicted_impact=predicted_impact,
        article_id=article_id,
        triggered_at=datetime(2024, 6, 1, 9, 30, 0, tzinfo=timezone.utc),
        details=details,
    )


def _make_notifier(
    db=None,
    smtp_host="smtp.example.com",
    smtp_user="user@example.com",
    smtp_password="secret",
    requests_lib=None,
) -> AlertNotifier:
    return AlertNotifier(
        db_session=db,
        smtp_host=smtp_host,
        smtp_port=587,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        smtp_from="alerts@stockiq.com",
        requests_lib=requests_lib,
    )


# ---------------------------------------------------------------------------
# 1. send_alert — channel routing
# ---------------------------------------------------------------------------


class TestSendAlertRouting:
    """send_alert should dispatch to the correct private methods based on channel list."""

    def test_routes_to_in_app(self):
        notifier = _make_notifier()
        notifier.send_in_app_notification = MagicMock()
        alert = _make_alert(details={"user_id": 42})
        notifier.send_alert(alert, ["in_app"])
        notifier.send_in_app_notification.assert_called_once_with(alert, 42)

    def test_routes_to_email(self):
        notifier = _make_notifier()
        notifier.send_email_notification = MagicMock()
        alert = _make_alert(details={"email": "trader@example.com"})
        notifier.send_alert(alert, ["email"])
        notifier.send_email_notification.assert_called_once_with(alert, "trader@example.com")

    def test_routes_to_webhook(self):
        notifier = _make_notifier()
        notifier.send_webhook_notification = MagicMock()
        alert = _make_alert(details={"webhook_url": "https://hooks.example.com/notify"})
        notifier.send_alert(alert, ["webhook"])
        notifier.send_webhook_notification.assert_called_once_with(
            alert, "https://hooks.example.com/notify"
        )

    def test_routes_to_multiple_channels(self):
        notifier = _make_notifier()
        notifier.send_in_app_notification = MagicMock()
        notifier.send_email_notification = MagicMock()
        notifier.send_webhook_notification = MagicMock()
        alert = _make_alert(details={
            "user_id": 1,
            "email": "a@b.com",
            "webhook_url": "https://x.com/hook",
        })
        notifier.send_alert(alert, ["in_app", "email", "webhook"])
        notifier.send_in_app_notification.assert_called_once()
        notifier.send_email_notification.assert_called_once()
        notifier.send_webhook_notification.assert_called_once()

    def test_empty_channel_list_no_dispatch(self):
        notifier = _make_notifier()
        notifier.send_in_app_notification = MagicMock()
        alert = _make_alert()
        notifier.send_alert(alert, [])
        notifier.send_in_app_notification.assert_not_called()

    def test_unknown_channel_is_ignored(self):
        """Unknown channels should be silently skipped."""
        notifier = _make_notifier()
        notifier.send_in_app_notification = MagicMock()
        alert = _make_alert(details={"user_id": 5})
        # "sms" is unsupported — should not raise
        notifier.send_alert(alert, ["in_app", "sms"])
        notifier.send_in_app_notification.assert_called_once()

    def test_in_app_without_user_id_no_crash(self):
        """send_alert should warn and skip when user_id is missing."""
        notifier = _make_notifier()
        notifier.send_in_app_notification = MagicMock()
        alert = _make_alert(details={})  # no user_id
        notifier.send_alert(alert, ["in_app"])
        notifier.send_in_app_notification.assert_not_called()

    def test_channel_names_case_insensitive(self):
        notifier = _make_notifier()
        notifier.send_in_app_notification = MagicMock()
        alert = _make_alert(details={"user_id": 7})
        notifier.send_alert(alert, ["IN_APP"])
        notifier.send_in_app_notification.assert_called_once()


# ---------------------------------------------------------------------------
# 2. send_in_app_notification — DB storage
# ---------------------------------------------------------------------------


class TestSendInAppNotification:
    """send_in_app_notification should write to the user_notifications table."""

    def _make_db_mock(self):
        db = MagicMock()
        db.execute = MagicMock()
        db.commit = MagicMock()
        return db

    def test_executes_insert(self):
        db = self._make_db_mock()
        notifier = _make_notifier(db=db)
        alert = _make_alert()
        notifier.send_in_app_notification(alert, user_id=10)
        db.execute.assert_called_once()

    def test_insert_contains_correct_ticker(self):
        db = self._make_db_mock()
        notifier = _make_notifier(db=db)
        alert = _make_alert(ticker="TSLA")
        notifier.send_in_app_notification(alert, user_id=99)
        call_args = db.execute.call_args
        params = call_args[0][1]  # second positional arg is the params dict
        assert params["ticker"] == "TSLA"

    def test_insert_marks_is_read_false(self):
        db = self._make_db_mock()
        notifier = _make_notifier(db=db)
        alert = _make_alert()
        notifier.send_in_app_notification(alert, user_id=1)
        params = db.execute.call_args[0][1]
        assert params["is_read"] is False

    def test_commits_after_insert(self):
        db = self._make_db_mock()
        notifier = _make_notifier(db=db)
        alert = _make_alert()
        notifier.send_in_app_notification(alert, user_id=1)
        db.commit.assert_called_once()

    def test_no_db_session_does_not_raise(self):
        notifier = _make_notifier(db=None)
        alert = _make_alert()
        # Must not raise; should warn and return
        notifier.send_in_app_notification(alert, user_id=5)

    def test_db_failure_is_caught(self):
        db = self._make_db_mock()
        db.execute.side_effect = Exception("DB connection refused")
        notifier = _make_notifier(db=db)
        alert = _make_alert()
        # Must not propagate the exception
        notifier.send_in_app_notification(alert, user_id=3)


# ---------------------------------------------------------------------------
# 3. send_email_notification — SMTP
# ---------------------------------------------------------------------------


class TestSendEmailNotification:
    """send_email_notification should send an HTML email via SMTP."""

    def test_calls_smtp_sendmail(self):
        notifier = _make_notifier()
        alert = _make_alert()
        with patch("smtplib.SMTP") as MockSMTP:
            smtp_instance = MockSMTP.return_value.__enter__.return_value
            smtp_instance.sendmail = MagicMock()
            notifier.send_email_notification(alert, "trader@example.com")
            smtp_instance.sendmail.assert_called_once()

    def test_starttls_called(self):
        notifier = _make_notifier()
        alert = _make_alert()
        with patch("smtplib.SMTP") as MockSMTP:
            smtp_instance = MockSMTP.return_value.__enter__.return_value
            notifier.send_email_notification(alert, "user@example.com")
            smtp_instance.starttls.assert_called_once()

    def test_login_called_with_credentials(self):
        notifier = _make_notifier(smtp_user="bot@stockiq.com", smtp_password="pw123")
        alert = _make_alert()
        with patch("smtplib.SMTP") as MockSMTP:
            smtp_instance = MockSMTP.return_value.__enter__.return_value
            notifier.send_email_notification(alert, "recv@x.com")
            smtp_instance.login.assert_called_once_with("bot@stockiq.com", "pw123")

    def test_no_smtp_host_does_not_raise(self):
        notifier = _make_notifier(smtp_host=None)
        alert = _make_alert()
        notifier.send_email_notification(alert, "x@y.com")  # should warn, not raise

    def test_email_subject_contains_ticker(self):
        notifier = _make_notifier()
        alert = _make_alert(ticker="NVDA")
        captured_subject = {}
        with patch("smtplib.SMTP") as MockSMTP:
            smtp_instance = MockSMTP.return_value.__enter__.return_value

            def capture_sendmail(from_addr, to_addrs, msg_str):
                captured_subject["raw"] = msg_str

            smtp_instance.sendmail.side_effect = capture_sendmail
            notifier.send_email_notification(alert, "u@v.com")

        assert "NVDA" in captured_subject.get("raw", "")


# ---------------------------------------------------------------------------
# 4. send_webhook_notification — HTTP POST
# ---------------------------------------------------------------------------


class TestSendWebhookNotification:
    """send_webhook_notification should POST JSON to the webhook URL."""

    def _make_requests_mock(self, status_code=200, raise_exc=None):
        mock_req = MagicMock()
        if raise_exc:
            mock_req.post.side_effect = raise_exc
        else:
            resp = MagicMock()
            resp.status_code = status_code
            resp.raise_for_status = MagicMock()
            mock_req.post.return_value = resp
        return mock_req

    def test_posts_to_correct_url(self):
        req = self._make_requests_mock()
        notifier = _make_notifier(requests_lib=req)
        alert = _make_alert()
        notifier.send_webhook_notification(alert, "https://hooks.example.com/ab")
        req.post.assert_called_once()
        call_kwargs = req.post.call_args
        assert call_kwargs[0][0] == "https://hooks.example.com/ab"

    def test_payload_contains_ticker(self):
        req = self._make_requests_mock()
        notifier = _make_notifier(requests_lib=req)
        alert = _make_alert(ticker="MSFT")
        notifier.send_webhook_notification(alert, "https://hook.io/x")
        payload = req.post.call_args[1]["json"]
        assert payload["ticker"] == "MSFT"

    def test_payload_contains_headline(self):
        req = self._make_requests_mock()
        notifier = _make_notifier(requests_lib=req)
        alert = _make_alert(headline="Big news!")
        notifier.send_webhook_notification(alert, "https://hook.io/y")
        payload = req.post.call_args[1]["json"]
        assert payload["headline"] == "Big news!"

    def test_payload_contains_sentiment_score(self):
        req = self._make_requests_mock()
        notifier = _make_notifier(requests_lib=req)
        alert = _make_alert(sentiment_score=-0.7)
        notifier.send_webhook_notification(alert, "https://hook.io/z")
        payload = req.post.call_args[1]["json"]
        assert payload["sentiment_score"] == pytest.approx(-0.7)

    def test_payload_is_json_serialisable(self):
        req = self._make_requests_mock()
        notifier = _make_notifier(requests_lib=req)
        alert = _make_alert()
        notifier.send_webhook_notification(alert, "https://hook.io/check")
        payload = req.post.call_args[1]["json"]
        # Must not raise
        json.dumps(payload)

    def test_no_requests_lib_does_not_raise(self):
        notifier = _make_notifier(requests_lib=None)
        notifier._requests = None
        alert = _make_alert()
        notifier.send_webhook_notification(alert, "https://hook.io/noop")


# ---------------------------------------------------------------------------
# 5. Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Failed deliveries should be retried up to MAX_RETRY_ATTEMPTS times."""

    def test_retry_three_times_on_failure(self):
        req = MagicMock()
        req.post.side_effect = ConnectionError("timeout")
        notifier = _make_notifier(requests_lib=req)

        with patch("time.sleep"):
            notifier.send_webhook_notification(
                _make_alert(), "https://hook.io/fail"
            )

        assert req.post.call_count == MAX_RETRY_ATTEMPTS

    def test_retry_succeeds_on_second_attempt(self):
        req = MagicMock()
        good_resp = MagicMock()
        good_resp.status_code = 200
        good_resp.raise_for_status = MagicMock()
        req.post.side_effect = [ConnectionError("first fail"), good_resp]

        notifier = _make_notifier(requests_lib=req)
        with patch("time.sleep"):
            notifier.send_webhook_notification(_make_alert(), "https://hook.io/retry")

        assert req.post.call_count == 2

    def test_sleep_called_between_retries(self):
        req = MagicMock()
        req.post.side_effect = ConnectionError("fail")
        notifier = _make_notifier(requests_lib=req)

        with patch("time.sleep") as mock_sleep:
            notifier.send_webhook_notification(_make_alert(), "https://hook.io/sleep")
            # 3 attempts → 2 sleeps (not after the last failure)
            assert mock_sleep.call_count == MAX_RETRY_ATTEMPTS - 1

    def test_exponential_backoff_delays(self):
        req = MagicMock()
        req.post.side_effect = ConnectionError("fail")
        notifier = _make_notifier(requests_lib=req)

        with patch("time.sleep") as mock_sleep:
            notifier.send_webhook_notification(_make_alert(), "https://hook.io/back")
            delays = [c[0][0] for c in mock_sleep.call_args_list]
            # 1st retry: 1.0s, 2nd retry: 2.0s
            assert delays[0] == pytest.approx(RETRY_BASE_DELAY * 1)
            assert delays[1] == pytest.approx(RETRY_BASE_DELAY * 2)

    def test_email_retry_on_smtp_error(self):
        notifier = _make_notifier()
        alert = _make_alert()
        with patch("smtplib.SMTP") as MockSMTP:
            MockSMTP.side_effect = smtplib.SMTPException("connection failed")
            with patch("time.sleep"):
                notifier.send_email_notification(alert, "u@v.com")
            assert MockSMTP.call_count == MAX_RETRY_ATTEMPTS


# ---------------------------------------------------------------------------
# 6. configure_alert_sensitivity
# ---------------------------------------------------------------------------


class TestConfigureAlertSensitivity:
    def test_set_high_sensitivity(self):
        notifier = _make_notifier()
        notifier.configure_alert_sensitivity(1, "high")
        assert notifier.get_user_sensitivity(1) == "high"

    def test_set_medium_sensitivity(self):
        notifier = _make_notifier()
        notifier.configure_alert_sensitivity(2, "medium")
        assert notifier.get_user_sensitivity(2) == "medium"

    def test_set_low_sensitivity(self):
        notifier = _make_notifier()
        notifier.configure_alert_sensitivity(3, "low")
        assert notifier.get_user_sensitivity(3) == "low"

    def test_invalid_sensitivity_raises_value_error(self):
        notifier = _make_notifier()
        with pytest.raises(ValueError, match="Invalid sensitivity"):
            notifier.configure_alert_sensitivity(1, "extreme")

    def test_empty_string_raises_value_error(self):
        notifier = _make_notifier()
        with pytest.raises(ValueError):
            notifier.configure_alert_sensitivity(1, "")

    def test_case_insensitive_input(self):
        notifier = _make_notifier()
        notifier.configure_alert_sensitivity(4, "HIGH")
        assert notifier.get_user_sensitivity(4) == "high"

    def test_default_sensitivity_is_medium(self):
        notifier = _make_notifier()
        assert notifier.get_user_sensitivity(999) == "medium"

    def test_persists_to_db_when_available(self):
        db = MagicMock()
        db.execute = MagicMock()
        db.commit = MagicMock()
        notifier = _make_notifier(db=db)
        notifier.configure_alert_sensitivity(10, "low")
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_db_failure_on_sensitivity_does_not_raise(self):
        db = MagicMock()
        db.execute.side_effect = Exception("DB unavailable")
        notifier = _make_notifier(db=db)
        # Should not propagate the DB error
        notifier.configure_alert_sensitivity(11, "high")
        assert notifier.get_user_sensitivity(11) == "high"

    def test_overwrite_existing_sensitivity(self):
        notifier = _make_notifier()
        notifier.configure_alert_sensitivity(5, "low")
        notifier.configure_alert_sensitivity(5, "high")
        assert notifier.get_user_sensitivity(5) == "high"


# ---------------------------------------------------------------------------
# 7. HTML email template
# ---------------------------------------------------------------------------


class TestHtmlEmailTemplate:
    """The rendered HTML should contain all key fields from the alert."""

    def test_template_contains_ticker(self):
        alert = _make_alert(ticker="GOOGL")
        html = _build_html_email(alert)
        assert "GOOGL" in html

    def test_template_contains_headline(self):
        alert = _make_alert(headline="Earnings beat expectations")
        html = _build_html_email(alert)
        assert "Earnings beat expectations" in html

    def test_template_contains_sentiment_score(self):
        alert = _make_alert(sentiment_score=0.75)
        html = _build_html_email(alert)
        assert "0.75" in html

    def test_template_contains_predicted_impact(self):
        alert = _make_alert(predicted_impact=0.42)
        html = _build_html_email(alert)
        assert "0.42" in html

    def test_template_contains_alert_type(self):
        alert = _make_alert(alert_type=AlertType.EARNINGS)
        html = _build_html_email(alert)
        assert "Earnings" in html  # rendered from alert_type

    def test_template_contains_triggered_at(self):
        alert = _make_alert()  # triggered_at = 2024-06-01 09:30 UTC
        html = _build_html_email(alert)
        assert "2024-06-01" in html

    def test_positive_sentiment_class(self):
        alert = _make_alert(sentiment_score=0.5)
        html = _build_html_email(alert)
        assert "sentiment-positive" in html

    def test_negative_sentiment_class(self):
        alert = _make_alert(sentiment_score=-0.5)
        html = _build_html_email(alert)
        assert "sentiment-negative" in html

    def test_neutral_sentiment_class(self):
        alert = _make_alert(sentiment_score=0.0)
        html = _build_html_email(alert)
        assert "sentiment-neutral" in html

    def test_no_predicted_impact_shows_na(self):
        alert = _make_alert(predicted_impact=None)
        html = _build_html_email(alert)
        assert "N/A" in html

    def test_template_is_valid_html_structure(self):
        alert = _make_alert()
        html = _build_html_email(alert)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html


# ---------------------------------------------------------------------------
# 8. Module-level constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_retry_attempts_is_three(self):
        assert MAX_RETRY_ATTEMPTS == 3

    def test_valid_sensitivities_contains_expected_values(self):
        assert VALID_SENSITIVITIES == {"high", "medium", "low"}

    def test_supported_channels_contains_expected_values(self):
        assert SUPPORTED_CHANNELS == {"in_app", "email", "webhook"}
