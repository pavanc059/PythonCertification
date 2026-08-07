# Task Completion: Alert Notifier

**Status:** Completed ✅  
**Date:** 2025-07-14

## Files

- `stockiq/news/alerts/notifier.py` — Full `AlertNotifier` implementation (new file)
- `stockiq/news/alerts/__init__.py` — Updated to export `AlertNotifier`, `UserNotificationSettings`, `SUPPORTED_CHANNELS`, `VALID_SENSITIVITIES`
- `tests/test_alert_notifier.py` — 54 tests covering all functionality

## What Was Implemented

### `AlertNotifier` class (`stockiq/news/alerts/notifier.py`)

**`send_alert(alert: NewsAlert, channels: List[str]) -> None`**  
Dispatches to the appropriate channel method based on the `channels` list. Channels are case-insensitive. Unknown channels are logged and skipped without raising. Per-channel delivery errors are caught so that one failing channel doesn't block others. The `alert.details` dict carries channel-specific targets (`user_id`, `email`, `webhook_url`).

**`send_in_app_notification(alert: NewsAlert, user_id: int) -> None`**  
Inserts a row into the `user_notifications` table via a raw SQLAlchemy `execute()` call. Stores: `user_id`, `ticker`, `alert_type`, `headline`, `sentiment_score`, `predicted_impact`, `article_id`, `triggered_at`, `is_read=False`, `details` (JSON), `created_at`. Gracefully degrades (logs warning) when no DB session is provided or the execute fails.

**`send_email_notification(alert: NewsAlert, email: str) -> None`**  
Renders an HTML email using `_build_html_email()` and sends via `smtplib.SMTP` with STARTTLS. Subject includes ticker and alert type. Retries 3 times with exponential backoff (1s, 2s, 4s) on SMTP errors. Skips silently if `smtp_host` is not configured.

**`send_webhook_notification(alert: NewsAlert, webhook_url: str) -> None`**  
POSTs a JSON payload (`ticker`, `alert_type`, `headline`, `sentiment_score`, `predicted_impact`, `article_id`, `triggered_at`, `details`) to the webhook URL with a 10-second timeout. Retries 3 times with exponential backoff on network / HTTP errors. Degrades gracefully when `requests` is unavailable.

**`configure_alert_sensitivity(user_id: int, sensitivity: str) -> None`**  
Validates sensitivity is one of `"high"`, `"medium"`, `"low"` (case-insensitive), raising `ValueError` otherwise. Persists to `user_alert_settings` table via upsert when a DB session is available. Also cached in-memory. `get_user_sensitivity(user_id)` returns the current setting, defaulting to `"medium"`.

**Retry logic (`_send_with_retry`)**  
Shared by email and webhook. Runs up to `MAX_RETRY_ATTEMPTS` (3) attempts. Between attempts: `time.sleep(base_delay * 2^(attempt-1))` — delays of 1s, 2s. After all attempts fail, logs an error and returns (no exception propagated).

**HTML email template (`_build_html_email`)**  
Responsive HTML with: ticker, alert type badge, headline, sentiment score (with positive/negative/neutral CSS colouring), predicted impact, triggered-at timestamp, and optional article CTA link.

**Graceful degradation throughout:**  
Every external dependency (SQLAlchemy session, SMTP, `requests`) is optional. Missing or failing dependencies produce `structlog` warnings, not unhandled exceptions.

## Tests

**54/54 passed** in `tests/test_alert_notifier.py`

| Group | Tests |
|---|---|
| `TestSendAlertRouting` | 8 |
| `TestSendInAppNotification` | 6 |
| `TestSendEmailNotification` | 5 |
| `TestSendWebhookNotification` | 6 |
| `TestRetryLogic` | 5 |
| `TestConfigureAlertSensitivity` | 10 |
| `TestHtmlEmailTemplate` | 11 |
| `TestConstants` | 3 |

All tests use mocks — no live DB, SMTP server, or HTTP endpoint required.

## Requirements Satisfied

- **5.9** — THE Alert_System SHALL deliver news alerts via in-app notifications, email, and webhook ✅
- **17.6** — THE Alert_System SHALL deliver alerts via multiple channels (in-app, email, webhook) ✅
- **5.8** — `configure_alert_sensitivity` enables user-configurable sensitivity (high/medium/low) ✅

## Notes

- The `user_notifications` table is referenced by raw SQL; the corresponding ORM model (`UserNotification`) can be added to `stockiq/infrastructure/models.py` as a follow-up if SQLAlchemy ORM-level access is needed.
- The `user_alert_settings` table (for sensitivity persistence) similarly uses raw SQL with an `ON CONFLICT` upsert — PostgreSQL-specific syntax.
- `requests_lib` is injectable in the constructor to facilitate testing without a live HTTP server.
- The `_build_html_email` function is exported publicly so downstream code and tests can render email previews without instantiating the full notifier.
