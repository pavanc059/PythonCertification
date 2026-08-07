"""
Alert Notifier.

Delivers news alerts via multiple channels:
- In-app notifications (stored in ``user_notifications`` database table)
- Email notifications (SMTP with HTML template formatting)
- Webhook notifications (HTTP POST JSON payload)

Retry logic: 3 attempts with exponential backoff for email and webhook.
Graceful degradation: logs warnings when DB/email/webhook are unavailable.

Requirements: 5.9, 17.6
"""

from __future__ import annotations

import json
import logging
import smtplib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import structlog

# ---------------------------------------------------------------------------
# Optional dependencies with graceful degradation
# ---------------------------------------------------------------------------

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

try:
    from sqlalchemy.orm import Session
    SQLALCHEMY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SQLALCHEMY_AVAILABLE = False

from stockiq.news.alerts.detector import NewsAlert

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maximum number of delivery attempts for retryable channels.
MAX_RETRY_ATTEMPTS: int = 3

#: Base delay (seconds) for exponential backoff between retries.
RETRY_BASE_DELAY: float = 1.0

#: Valid sensitivity settings.
VALID_SENSITIVITIES = frozenset({"high", "medium", "low"})

#: Supported delivery channels.
SUPPORTED_CHANNELS = frozenset({"in_app", "email", "webhook"})


# ---------------------------------------------------------------------------
# Dataclass for user notification settings (stored in memory or DB)
# ---------------------------------------------------------------------------


@dataclass
class UserNotificationSettings:
    """Per-user alert delivery configuration."""

    user_id: int
    sensitivity: str = "medium"  # 'high', 'medium', 'low'
    email: Optional[str] = None
    webhook_url: Optional[str] = None
    channels: List[str] = field(default_factory=lambda: ["in_app"])


# ---------------------------------------------------------------------------
# HTML Email Template
# ---------------------------------------------------------------------------

_HTML_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>StockIQ Alert: {ticker}</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 30px auto; background: #ffffff; border-radius: 8px;
                  overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.12); }}
    .header {{ background: #1a1a2e; color: #e0e0e0; padding: 24px 32px; }}
    .header h1 {{ margin: 0; font-size: 20px; }}
    .header .ticker {{ font-size: 28px; font-weight: bold; color: #f5a623; }}
    .body {{ padding: 24px 32px; color: #333333; }}
    .headline {{ font-size: 16px; font-weight: bold; margin-bottom: 16px; }}
    .metrics {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
    .metric {{ background: #f0f0f5; border-radius: 6px; padding: 12px 16px; min-width: 130px; }}
    .metric .label {{ font-size: 11px; text-transform: uppercase; color: #888; margin-bottom: 4px; }}
    .metric .value {{ font-size: 18px; font-weight: bold; color: #1a1a2e; }}
    .sentiment-positive {{ color: #27ae60; }}
    .sentiment-negative {{ color: #e74c3c; }}
    .sentiment-neutral {{ color: #7f8c8d; }}
    .footer {{ background: #f9f9f9; padding: 16px 32px; font-size: 12px; color: #999;
               border-top: 1px solid #e0e0e0; }}
    .alert-type-badge {{ display: inline-block; background: #e8f4fd; color: #2980b9;
                         border-radius: 4px; padding: 3px 10px; font-size: 12px;
                         font-weight: bold; margin-bottom: 12px; text-transform: uppercase; }}
    .cta {{ display: inline-block; margin-top: 16px; background: #1a1a2e; color: #ffffff;
            text-decoration: none; padding: 10px 22px; border-radius: 6px; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="ticker">{ticker}</div>
      <h1>StockIQ News Alert</h1>
    </div>
    <div class="body">
      <div class="alert-type-badge">{alert_type}</div>
      <div class="headline">{headline}</div>
      <div class="metrics">
        <div class="metric">
          <div class="label">Sentiment Score</div>
          <div class="value {sentiment_class}">{sentiment_score:.2f}</div>
        </div>
        <div class="metric">
          <div class="label">Predicted Impact</div>
          <div class="value">{predicted_impact}</div>
        </div>
        <div class="metric">
          <div class="label">Alert Time</div>
          <div class="value" style="font-size:13px;">{triggered_at}</div>
        </div>
      </div>
      {article_link}
    </div>
    <div class="footer">
      This alert was generated by StockIQ. Adjust your notification settings in the dashboard.
    </div>
  </div>
</body>
</html>
"""


def _build_html_email(alert: NewsAlert) -> str:
    """Render the HTML email template for *alert*."""
    # Sentiment class for CSS colouring
    if alert.sentiment_score > 0.1:
        sentiment_class = "sentiment-positive"
    elif alert.sentiment_score < -0.1:
        sentiment_class = "sentiment-negative"
    else:
        sentiment_class = "sentiment-neutral"

    predicted_impact = (
        f"{alert.predicted_impact:+.2f}" if alert.predicted_impact is not None else "N/A"
    )

    triggered_at = alert.triggered_at.strftime("%Y-%m-%d %H:%M UTC")

    article_link = ""
    if alert.article_id:
        article_link = (
            f'<a class="cta" href="#">View Full Article &amp; Analysis</a>'
        )

    return _HTML_EMAIL_TEMPLATE.format(
        ticker=alert.ticker,
        alert_type=alert.alert_type.value.replace("_", " ").title(),
        headline=alert.headline,
        sentiment_class=sentiment_class,
        sentiment_score=alert.sentiment_score,
        predicted_impact=predicted_impact,
        triggered_at=triggered_at,
        article_link=article_link,
    )


# ---------------------------------------------------------------------------
# AlertNotifier
# ---------------------------------------------------------------------------


class AlertNotifier:
    """
    Delivers :class:`~stockiq.news.alerts.detector.NewsAlert` objects via
    multiple channels: in-app, email, and webhook.

    All channels degrade gracefully — if a dependency (database, SMTP,
    ``requests``) is unavailable, a warning is logged instead of raising.

    Retry logic (3 attempts, exponential backoff) is applied to email and
    webhook channels which involve network I/O.

    Requirements: 5.9, 17.6
    """

    def __init__(
        self,
        db_session: Optional[Any] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from: str = "noreply@stockanalyzer.com",
        requests_lib: Optional[Any] = None,
    ) -> None:
        """
        Initialise the notifier.

        Args:
            db_session:    SQLAlchemy Session (or None to skip DB writes).
            smtp_host:     SMTP server hostname.
            smtp_port:     SMTP server port (default 587 for STARTTLS).
            smtp_user:     SMTP authentication username.
            smtp_password: SMTP authentication password.
            smtp_from:     Sender address for outgoing emails.
            requests_lib:  ``requests``-compatible library (injectable for tests).
        """
        self._db = db_session
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._smtp_from = smtp_from
        # Allow injection for testing; fall back to the real requests module.
        self._requests = requests_lib if requests_lib is not None else (
            _requests if REQUESTS_AVAILABLE else None
        )
        # In-memory store of user sensitivity settings (user_id → sensitivity).
        self._user_settings: Dict[int, UserNotificationSettings] = {}

    # ------------------------------------------------------------------
    # Primary dispatch
    # ------------------------------------------------------------------

    def send_alert(self, alert: NewsAlert, channels: List[str]) -> None:
        """
        Dispatch *alert* to every channel listed in *channels*.

        Supported channel strings:
        - ``"in_app"`` — requires ``user_id`` in ``alert.details["user_id"]``
        - ``"email"`` — requires ``email`` in ``alert.details["email"]``
        - ``"webhook"`` — requires ``webhook_url`` in ``alert.details["webhook_url"]``

        Unknown channels are logged as warnings and skipped.  Delivery
        failures on individual channels do not prevent other channels from
        being attempted.

        Args:
            alert:    The :class:`~stockiq.news.alerts.detector.NewsAlert` to send.
            channels: List of channel identifiers to attempt.

        Requirements: 5.9, 17.6
        """
        if not channels:
            logger.warning("send_alert called with empty channel list", ticker=alert.ticker)
            return

        for channel in channels:
            channel_lower = channel.lower()
            try:
                if channel_lower == "in_app":
                    user_id: Optional[int] = alert.details.get("user_id")
                    if user_id is not None:
                        self.send_in_app_notification(alert, user_id)
                    else:
                        logger.warning(
                            "send_alert: channel=in_app requires alert.details['user_id']",
                            ticker=alert.ticker,
                        )
                elif channel_lower == "email":
                    email: Optional[str] = alert.details.get("email")
                    if email:
                        self.send_email_notification(alert, email)
                    else:
                        logger.warning(
                            "send_alert: channel=email requires alert.details['email']",
                            ticker=alert.ticker,
                        )
                elif channel_lower == "webhook":
                    webhook_url: Optional[str] = alert.details.get("webhook_url")
                    if webhook_url:
                        self.send_webhook_notification(alert, webhook_url)
                    else:
                        logger.warning(
                            "send_alert: channel=webhook requires alert.details['webhook_url']",
                            ticker=alert.ticker,
                        )
                else:
                    logger.warning(
                        "send_alert: unsupported channel ignored",
                        channel=channel,
                        ticker=alert.ticker,
                    )
            except Exception as exc:  # pragma: no cover — belt-and-suspenders
                logger.error(
                    "send_alert: unexpected error on channel",
                    channel=channel,
                    ticker=alert.ticker,
                    error=str(exc),
                )

    # ------------------------------------------------------------------
    # In-app notifications
    # ------------------------------------------------------------------

    def send_in_app_notification(self, alert: NewsAlert, user_id: int) -> None:
        """
        Store a notification record in the ``user_notifications`` database table.

        If no database session is available, the notification is logged as a
        warning and the method returns without raising.

        Schema columns written:
        - ``user_id``
        - ``ticker``
        - ``alert_type``
        - ``headline``
        - ``sentiment_score``
        - ``predicted_impact``
        - ``article_id``
        - ``triggered_at``
        - ``is_read`` (False)
        - ``details`` (JSON-serialisable dict)

        Args:
            alert:   The alert to store.
            user_id: Target user's identifier.
        """
        if self._db is None:
            logger.warning(
                "send_in_app_notification: no DB session available — notification not persisted",
                ticker=alert.ticker,
                user_id=user_id,
            )
            return

        try:
            record = {
                "user_id": user_id,
                "ticker": alert.ticker,
                "alert_type": alert.alert_type.value,
                "headline": alert.headline,
                "sentiment_score": alert.sentiment_score,
                "predicted_impact": alert.predicted_impact,
                "article_id": alert.article_id,
                "triggered_at": alert.triggered_at.isoformat(),
                "is_read": False,
                "details": json.dumps(alert.details),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._db.execute(
                "INSERT INTO user_notifications "
                "(user_id, ticker, alert_type, headline, sentiment_score, "
                "predicted_impact, article_id, triggered_at, is_read, details, created_at) "
                "VALUES (:user_id, :ticker, :alert_type, :headline, :sentiment_score, "
                ":predicted_impact, :article_id, :triggered_at, :is_read, :details, :created_at)",
                record,
            )
            self._db.commit()
            logger.info(
                "in_app_notification_stored",
                ticker=alert.ticker,
                user_id=user_id,
                alert_type=alert.alert_type.value,
            )
        except Exception as exc:
            logger.warning(
                "send_in_app_notification: failed to persist notification",
                ticker=alert.ticker,
                user_id=user_id,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Email notifications
    # ------------------------------------------------------------------

    def send_email_notification(self, alert: NewsAlert, email: str) -> None:
        """
        Send an HTML-formatted email for *alert* to *email* via SMTP.

        Retries up to :data:`MAX_RETRY_ATTEMPTS` (3) times with exponential
        backoff (1s, 2s, 4s) on SMTP or connection errors.

        If SMTP credentials are not configured, logs a warning and returns.

        Args:
            alert: The alert to deliver.
            email: Recipient email address.
        """
        if not self._smtp_host:
            logger.warning(
                "send_email_notification: SMTP host not configured — email skipped",
                ticker=alert.ticker,
                email=email,
            )
            return

        html_body = _build_html_email(alert)
        subject = (
            f"[StockIQ Alert] {alert.ticker} — "
            f"{alert.alert_type.value.replace('_', ' ').title()}"
        )

        self._send_with_retry(
            channel="email",
            ticker=alert.ticker,
            action=lambda: self._dispatch_email(email, subject, html_body),
        )

    def _dispatch_email(self, to_email: str, subject: str, html_body: str) -> None:
        """Low-level SMTP send. Raises on any failure so retry logic can handle it."""
        msg = MIMEMultipart("alternative")
        msg["From"] = self._smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            if self._smtp_user and self._smtp_password:
                smtp.login(self._smtp_user, self._smtp_password)
            smtp.sendmail(self._smtp_from, to_email, msg.as_string())

        logger.info(
            "email_notification_sent",
            to=to_email,
            subject=subject,
        )

    # ------------------------------------------------------------------
    # Webhook notifications
    # ------------------------------------------------------------------

    def send_webhook_notification(self, alert: NewsAlert, webhook_url: str) -> None:
        """
        POST a JSON payload for *alert* to *webhook_url*.

        Payload schema::

            {
              "ticker":           str,
              "alert_type":       str,
              "headline":         str,
              "sentiment_score":  float,
              "predicted_impact": float | null,
              "article_id":       str | null,
              "triggered_at":     str (ISO-8601),
              "details":          dict
            }

        Retries up to :data:`MAX_RETRY_ATTEMPTS` (3) times with exponential
        backoff on network / HTTP errors.

        If ``requests`` is not available, logs a warning and returns.

        Args:
            alert:       The alert to deliver.
            webhook_url: Target HTTPS URL.
        """
        if self._requests is None:
            logger.warning(
                "send_webhook_notification: requests library not available — webhook skipped",
                ticker=alert.ticker,
                webhook_url=webhook_url,
            )
            return

        payload: Dict[str, Any] = {
            "ticker": alert.ticker,
            "alert_type": alert.alert_type.value,
            "headline": alert.headline,
            "sentiment_score": alert.sentiment_score,
            "predicted_impact": alert.predicted_impact,
            "article_id": alert.article_id,
            "triggered_at": alert.triggered_at.isoformat(),
            "details": alert.details,
        }

        self._send_with_retry(
            channel="webhook",
            ticker=alert.ticker,
            action=lambda: self._dispatch_webhook(webhook_url, payload),
        )

    def _dispatch_webhook(self, url: str, payload: Dict[str, Any]) -> None:
        """Low-level HTTP POST. Raises on network error or non-2xx response."""
        response = self._requests.post(
            url,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json", "User-Agent": "StockIQ/1.0"},
        )
        response.raise_for_status()
        logger.info(
            "webhook_notification_sent",
            url=url,
            status_code=response.status_code,
        )

    # ------------------------------------------------------------------
    # Retry logic
    # ------------------------------------------------------------------

    def _send_with_retry(
        self,
        channel: str,
        ticker: str,
        action: Any,
        max_attempts: int = MAX_RETRY_ATTEMPTS,
        base_delay: float = RETRY_BASE_DELAY,
    ) -> None:
        """
        Execute *action* up to *max_attempts* times with exponential backoff.

        Backoff delays: 1s, 2s, 4s (i.e. ``base_delay * 2^(attempt-1)``).

        Args:
            channel:      Channel name for logging.
            ticker:       Ticker symbol for logging.
            action:       Zero-argument callable that performs the delivery.
            max_attempts: Maximum number of attempts (default 3).
            base_delay:   Base delay in seconds (default 1.0).
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                action()
                return  # success
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "delivery_retry",
                        channel=channel,
                        ticker=ticker,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=delay,
                        error=str(exc),
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "delivery_failed_after_retries",
                        channel=channel,
                        ticker=ticker,
                        attempts=max_attempts,
                        error=str(exc),
                    )

    # ------------------------------------------------------------------
    # Alert sensitivity configuration
    # ------------------------------------------------------------------

    def configure_alert_sensitivity(self, user_id: int, sensitivity: str) -> None:
        """
        Store the alert sensitivity setting for *user_id*.

        Sensitivity levels filter how aggressively alerts are generated
        for the user's watchlist:
        - ``"high"``   — all alerts, including low-impact events
        - ``"medium"`` — moderate-impact and above (default)
        - ``"low"``    — only high-impact events

        The setting is persisted to the database (``user_alert_settings``
        table) when a DB session is available, and is also cached in memory.

        Args:
            user_id:     Target user's identifier.
            sensitivity: One of ``"high"``, ``"medium"``, or ``"low"``.

        Raises:
            ValueError: If *sensitivity* is not one of the valid values.
        """
        sensitivity = sensitivity.lower().strip()
        if sensitivity not in VALID_SENSITIVITIES:
            raise ValueError(
                f"Invalid sensitivity '{sensitivity}'. "
                f"Must be one of: {sorted(VALID_SENSITIVITIES)}"
            )

        # Update in-memory cache
        if user_id not in self._user_settings:
            self._user_settings[user_id] = UserNotificationSettings(user_id=user_id)
        self._user_settings[user_id].sensitivity = sensitivity

        # Persist to DB if available
        if self._db is not None:
            try:
                self._db.execute(
                    "INSERT INTO user_alert_settings (user_id, sensitivity, updated_at) "
                    "VALUES (:user_id, :sensitivity, :updated_at) "
                    "ON CONFLICT (user_id) DO UPDATE "
                    "SET sensitivity = EXCLUDED.sensitivity, updated_at = EXCLUDED.updated_at",
                    {
                        "user_id": user_id,
                        "sensitivity": sensitivity,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                self._db.commit()
            except Exception as exc:
                logger.warning(
                    "configure_alert_sensitivity: failed to persist to DB",
                    user_id=user_id,
                    sensitivity=sensitivity,
                    error=str(exc),
                )

        logger.info(
            "alert_sensitivity_configured",
            user_id=user_id,
            sensitivity=sensitivity,
        )

    def get_user_sensitivity(self, user_id: int) -> str:
        """
        Return the current sensitivity setting for *user_id*.

        Defaults to ``"medium"`` if never explicitly configured.

        Args:
            user_id: Target user's identifier.

        Returns:
            Sensitivity string: ``"high"``, ``"medium"``, or ``"low"``.
        """
        settings = self._user_settings.get(user_id)
        return settings.sensitivity if settings else "medium"
