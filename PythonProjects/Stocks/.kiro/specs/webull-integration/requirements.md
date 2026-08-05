# Requirements Document

## Introduction

This document specifies requirements for the Webull Integration feature. The feature replaces the existing `yfinance`/stub market data sources with the official Webull OpenAPI SDK (`webull-openapi-python-sdk`) for real-time quotes, charts, movers, and market snapshots. It also introduces a real-trade confirmation gate that intercepts every real-money order, requires explicit user acknowledgement via a typed-confirmation modal, and writes an immutable audit log for every confirmation attempt. Webull is used in **read-only mode only** — no orders are ever submitted through Webull's API, and no trading PIN is ever passed to the client layer.

---

## Glossary

- **WebullClient**: The Python wrapper around the official `webull-openapi-python-sdk`. Constructed from `app_key` and `app_secret`; the SDK handles HMAC-SHA1 signing automatically on every request. Has no `trading_pin` parameter.
- **ApiClient**: The `webull.core.client.ApiClient` from the official SDK. Initialized with `app_key`, `app_secret`, and `region_id`; signs every request automatically.
- **DataClient**: The `webull.data.data_client.DataClient` from the official SDK. Provides market data endpoints (snapshot, history bars, screener, instrument).
- **WebullMarketService**: The drop-in replacement for `MarketService`. Delegates to `WebullClient` for live data, falls back to `yfinance`, and finally raises HTTP 503 if both fail.
- **WebullUnavailableError**: A typed exception raised by `WebullClient` when the Webull API returns a non-200 status code or an unexpected response after all retries.
- **TradingConfirmationService**: Backend service that validates typed confirmation strings, generates confirmation challenges, and writes immutable audit log rows.
- **RealTradeConfirmModal**: The frontend modal component that intercepts real-money orders and requires typed confirmation before submission.
- **tradingConfirmStore**: Zustand store managing the state of the real-trade confirmation flow.
- **AuditLogService**: Internal service responsible for inserting rows into `real_trade_audit_log`.
- **real_trade_audit_log**: Immutable PostgreSQL table that records every real-trade confirmation attempt (success or failure).
- **Confirmation_Challenge**: The exact string a user must type to confirm a real order, formatted as `"{TICKER} {QUANTITY} {SIDE}"` (e.g., `"AAPL 100 BUY"`).
- **Fallback_Chain**: The ordered sequence of market data providers: Webull → yfinance → HTTP 503.
- **Provider_TTL**: The cache time-to-live specific to the data source: 15 seconds for Webull quotes, 30 seconds for yfinance quotes, 60 seconds for charts, 120 seconds for news, 30 seconds for movers.
- **Paper_Mode**: An account mode in which no real money is involved; paper trades bypass the confirmation gate.
- **Real_Mode**: An account mode in which actual money is at risk; all orders must pass through the confirmation gate.
- **OrderTicket**: The frontend component from which users initiate orders.
- **Settings**: The Pydantic `BaseSettings` configuration object in `backend/config.py`.

---

## Requirements

### Requirement 1: WebullClient Construction and Authentication

**User Story:** As a backend developer, I want the `WebullClient` to authenticate using the official Webull OpenAPI SDK with App Key and App Secret, so that all market data requests are properly signed without per-request credential management.

#### Acceptance Criteria

1. THE `WebullClient` constructor SHALL accept `app_key`, `app_secret`, `region_id` (default `"us"`), and `endpoint` (default `"api.webull.com"`); it SHALL NOT accept `trading_pin`, `email`, `password`, `device_id`, or `mfa_code`.
2. WHEN `WebullClient.__init__` is called, THE `WebullClient` SHALL construct an `ApiClient(app_key, app_secret, region_id)` and a `DataClient(api_client)` internally, and call `api_client.add_endpoint(region_id, endpoint)`.
3. THE `WebullClient` SHALL NOT require a `login()` call — the official SDK signs every request automatically via HMAC-SHA1; no session token is needed.
4. THE `WebullClient` SHALL NOT maintain any session state, refresh tokens, or background refresh tasks.
5. THE `WebullClient` SHALL log every Webull API call at `DEBUG` level including the ticker or operation name and elapsed time.

---

### Requirement 2: Read-Only Enforcement

**User Story:** As a security engineer, I want the Webull integration to be strictly read-only, so that no order placement is ever possible through the `WebullClient` regardless of configuration.

#### Acceptance Criteria

1. THE `WebullClient` SHALL NOT pass `WEBULL_TRADING_PIN` to any SDK call, in any `fetch_*` method or any internal helper.
2. THE `Settings` object SHALL store `webull_trading_pin` as a field but THE `WebullClient` constructor SHALL NOT accept or use it.
3. WHEN any `WebullClient` method would require the trading PIN to execute, THE `WebullClient` SHALL raise `PermissionError` immediately.
4. THE `WebullClient` SHALL expose only read operations: `fetch_quote`, `fetch_bars`, `fetch_news`, and `fetch_movers`.

---

### Requirement 3: Resilient Market Data Fetching with Retry

**User Story:** As a backend developer, I want `WebullClient` to retry failed Webull calls with exponential backoff, so that transient network errors do not immediately cause a fallback to yfinance.

#### Acceptance Criteria

1. WHEN a Webull API call returns a non-200 HTTP status code, THE `WebullClient` SHALL treat it as a failure and retry up to a maximum of 3 attempts total (1 initial + 2 retries).
2. WHEN retrying, THE `WebullClient` SHALL wait `2^attempt` seconds before each retry attempt, where `attempt` starts at 1.
3. IF all 3 attempts fail, THEN THE `WebullClient` SHALL raise `WebullUnavailableError` with a message indicating the number of failed attempts and the ticker or operation.
4. WHEN a Webull API call returns null or empty data (missing required fields), THE `WebullClient` SHALL treat it as a failure and apply the retry logic.

---

### Requirement 4: Cache-First Market Data with Fallback Chain

**User Story:** As a backend developer, I want `WebullMarketService` to serve cached data first and fall back gracefully when providers fail, so that the API remains responsive under Webull outages.

#### Acceptance Criteria

1. WHEN a market data request arrives for a ticker, THE `WebullMarketService` SHALL first check Redis for a cached result before calling any external provider.
2. WHEN a valid cached result exists in Redis, THE `WebullMarketService` SHALL return the cached result without calling `WebullClient` or yfinance.
3. WHEN `WebullClient` successfully returns data, THE `WebullMarketService` SHALL store the result in Redis with the appropriate `Provider_TTL` (15 seconds for quote, 60 seconds for chart, 120 seconds for news, 30 seconds for movers).
4. WHEN `WebullClient` raises `WebullUnavailableError`, THE `WebullMarketService` SHALL log a WARNING and immediately attempt to fetch the same data from yfinance.
5. WHEN yfinance returns data after a Webull failure, THE `WebullMarketService` SHALL store the result in Redis with a 30-second TTL and include `"data_source": "yfinance"` in the response.
6. IF both `WebullClient` and yfinance fail for a given ticker, THEN THE `WebullMarketService` SHALL raise `HTTPException` with status code 503 and the message `"Market data temporarily unavailable for {ticker}"`.
7. THE `WebullMarketService` SHALL include a `data_source` field in every market data response indicating which provider served the data (`"webull"`, `"yfinance"`, or `"stub"`).
8. THE `WebullMarketService` SHALL map yfinance `(period, interval)` pairs to Webull `(interval_code, count)` pairs using the official SDK `Timespan` enum values (`M1`, `M5`, `M15`, `M30`, `H1`, `D1`).
9. WHILE `MARKET_DATA_SOURCE` is set to `"yfinance"` or `"stub"`, THE `WebullMarketService` SHALL bypass `WebullClient` entirely and use the configured provider directly.

---

### Requirement 5: Identical Market Data API Surface

**User Story:** As a frontend developer, I want `WebullMarketService` to expose the same method signatures as the existing `MarketService`, so that no route or frontend code changes are required to support the new provider.

#### Acceptance Criteria

1. THE `WebullMarketService` SHALL implement `get_quote`, `get_chart`, `get_prediction`, `get_movers`, `get_news`, `get_ticker_news`, `get_predictions`, `get_penny_stocks`, `get_snapshot`, `get_alerts`, `dismiss_alert`, and `mark_all_alerts_read` with identical method signatures to the existing `MarketService`.
2. THE `WebullMarketService` SHALL return responses that conform to the same JSON schema as the existing `MarketService` for every method.
3. THE `WebullMarketService` SHALL keep `get_predictions`, `get_penny_stocks`, and alert methods unchanged from the existing stub implementation.
4. WHEN `WebullClient` is injected into `WebullMarketService` at construction time, THE `WebullMarketService` SHALL use that single instance for all Webull calls within a request lifecycle without creating new instances.

---

### Requirement 6: Real-Trade Confirmation Gate — Backend

**User Story:** As a risk manager, I want every real-money order to require explicit typed confirmation before proceeding, so that accidental or automated submissions are blocked.

#### Acceptance Criteria

1. THE `TradingConfirmationService` SHALL generate a `Confirmation_Challenge` string formatted as `"{TICKER} {QUANTITY} {SIDE}"` (all uppercase) for any given `RealOrderRequest`.
2. WHEN `validate_and_submit` is called, THE `TradingConfirmationService` SHALL normalize both `confirmation_text` and the expected string using `.strip().upper()` before comparing them.
3. WHEN the normalized `confirmation_text` exactly matches the normalized `Confirmation_Challenge`, THE `TradingConfirmationService` SHALL return `ConfirmationResult(success=True, order_id=<new_uuid>)`.
4. WHEN the normalized `confirmation_text` does not match the normalized `Confirmation_Challenge`, THE `TradingConfirmationService` SHALL return `ConfirmationResult(success=False, reason="Confirmation text did not match. Expected: {expected}")`.
5. THE `TradingConfirmationService` SHALL write exactly one row to `real_trade_audit_log` for every call to `validate_and_submit`, regardless of whether the confirmation succeeds or fails.
6. THE `TradingConfirmationService` SHALL NOT access or use `WEBULL_TRADING_PIN` or any trading PIN value anywhere in its implementation.

---

### Requirement 7: Real-Trade Audit Log

**User Story:** As a compliance officer, I want every real-money trade confirmation attempt to be recorded in an immutable audit log, so that there is a complete forensic record of all confirmation events.

#### Acceptance Criteria

1. THE `AuditLogService` SHALL insert a row into `real_trade_audit_log` containing `user_id`, `ticker`, `side`, `order_type`, `quantity`, `limit_price`, `stop_price`, `confirmation_text`, `outcome`, `ip_address`, `user_agent`, and `created_at` for every confirmation attempt.
2. THE `AuditLogService` SHALL set `outcome` to exactly one of `"confirmed"`, `"rejected"`, or `"expired"` depending on the result of the confirmation attempt.
3. THE `real_trade_audit_log` table SHALL use `ondelete="RESTRICT"` on the `user_id` foreign key to prevent cascading deletes that would erase audit evidence.
4. THE system SHALL NOT provide any application-layer endpoint for updating or deleting rows from `real_trade_audit_log`.
5. THE `real_trade_audit_log` table SHALL have an index on `(user_id, created_at DESC)` for efficient per-user audit queries and an index on `ticker`.
6. WHEN the client IP address is available on the request, THE `AuditLogService` SHALL store it in the `ip_address` field of the audit log row.

---

### Requirement 8: Real-Trade Confirmation API Endpoint

**User Story:** As a frontend developer, I want a dedicated API endpoint for real-trade confirmation, so that the confirmation gate is enforced server-side and cannot be bypassed by the client.

#### Acceptance Criteria

1. THE system SHALL expose `POST /trading/real/confirm` accepting a `RealOrderRequest` body with fields: `ticker`, `side`, `order_type`, `quantity`, `limit_price` (optional), `stop_price` (optional), and `confirmation_text`.
2. WHEN a valid confirmed request is received, THE `trading/router` SHALL return HTTP 201 with a `RealOrderConfirmResponse` containing `order_id`, `status: "submitted"`, and a confirmation message.
3. WHEN the `confirmation_text` does not match the expected pattern, THE `trading/router` SHALL return HTTP 422 with `detail` containing the mismatch reason.
4. WHEN an unauthenticated request is received at `POST /trading/real/confirm`, THE system SHALL return HTTP 401.
5. WHEN a request is received from a user in `Paper_Mode`, THE `trading/router` SHALL return HTTP 403 with the message `"Real-money trading is not enabled for this account."`.
6. THE `POST /trading/real/confirm` endpoint SHALL capture the client IP from `request.client.host` and pass it to `TradingConfirmationService` for audit logging.

---

### Requirement 9: Real-Trade Confirmation Modal — Frontend

**User Story:** As a user, I want a high-friction confirmation modal for real-money orders, so that I am clearly aware of the risk and cannot accidentally submit a real trade.

#### Acceptance Criteria

1. WHEN a user initiates a real-money order from `OrderTicket`, THE `OrderTicket` SHALL call `tradingConfirmStore.openConfirmation(pendingOrder)` instead of submitting the order directly.
2. THE `RealTradeConfirmModal` SHALL render with an amber header band containing a `⚠ REAL MONEY TRADE` label, visually distinct from paper trade modals.
3. THE `RealTradeConfirmModal` SHALL display the prominent disclaimer: `"This will place a REAL order with REAL money. This action cannot be undone."`.
4. THE `RealTradeConfirmModal` SHALL display a labeled confirmation input field with the placeholder `Type "{TICKER} {QUANTITY} {SIDE}" to confirm`, populated dynamically from the pending order.
5. WHEN the value in the confirmation input field, after `.trim().toUpperCase()`, does not equal `expectedConfirmText`, THE `RealTradeConfirmModal` SHALL keep the submit button disabled.
6. WHEN the value in the confirmation input field exactly matches `expectedConfirmText`, THE `RealTradeConfirmModal` SHALL enable the submit button with an amber (`bg-amber-600`) color.
7. THE `RealTradeConfirmModal` SHALL NOT render the `PaperTradingBanner` component.
8. WHILE the confirmation is being submitted (`isSubmitting` is `true`), THE `RealTradeConfirmModal` SHALL disable both the Escape key dismiss and the backdrop click dismiss.
9. WHEN the confirmation submission returns a server error (HTTP 422), THE `RealTradeConfirmModal` SHALL display an inline error message and keep the modal open.
10. WHEN the confirmation submission succeeds (HTTP 201), THE `RealTradeConfirmModal` SHALL call `tradingConfirmStore.closeConfirmation()` and display a toast notification with the message `"Real order submitted"`.

---

### Requirement 10: Trading Confirm Store

**User Story:** As a frontend developer, I want a Zustand store to manage the real-trade confirmation flow state, so that the modal and order ticket are decoupled and state transitions are predictable.

#### Acceptance Criteria

1. THE `tradingConfirmStore` SHALL maintain the state fields: `isOpen`, `pendingRealOrder`, `expectedConfirmText`, and `isSubmitting`.
2. WHEN `openConfirmation(order)` is called, THE `tradingConfirmStore` SHALL set `isOpen` to `true`, `pendingRealOrder` to `order`, and `expectedConfirmText` to `"{order.ticker} {order.quantity} {order.side.toUpperCase()}"`.
3. WHEN `closeConfirmation()` is called, THE `tradingConfirmStore` SHALL reset `isOpen` to `false`, `pendingRealOrder` to `null`, `expectedConfirmText` to `null`, and `isSubmitting` to `false`.
4. WHEN `setSubmitting(true)` is called, THE `tradingConfirmStore` SHALL set `isSubmitting` to `true`.

---

### Requirement 11: Environment Configuration

**User Story:** As a DevOps engineer, I want all Webull credentials and configuration values to be managed exclusively via environment variables, so that no secrets are hardcoded in source code or returned in API responses.

#### Acceptance Criteria

1. THE `Settings` object SHALL include the fields: `webull_app_key` (default `""`), `webull_app_secret` (default `""`), `webull_region_id` (default `"us"`), `webull_endpoint` (default `"api.webull.com"`), `webull_sandbox` (bool, default `False`), `webull_trading_pin` (default `""`), and `market_data_source` (default `"webull"`).
2. THE system SHALL support `market_data_source` values of `"webull"`, `"yfinance"`, and `"stub"`.
3. THE system SHALL NOT log, return in any API response, or expose any Webull credential values (`webull_app_key`, `webull_app_secret`, `webull_trading_pin`).
4. THE `.env.example` file SHALL include all new Webull environment variable names with placeholder values and comments.
5. WHEN `webull_sandbox` is `True`, THE `WebullClient` SHALL configure the `ApiClient` endpoint as `"api.sandbox.webull.com"` instead of the production endpoint.

---

### Requirement 12: Database Migration

**User Story:** As a database administrator, I want an Alembic migration that creates the `real_trade_audit_log` table with all required columns and indexes, so that the audit log is properly initialized in all environments.

#### Acceptance Criteria

1. THE Alembic migration `004_create_real_trade_audit_log` SHALL create the `real_trade_audit_log` table with columns: `id` (UUID primary key), `user_id` (UUID, FK to `users.id`, NOT NULL), `ticker` (varchar 10, NOT NULL), `side` (varchar 4, NOT NULL), `order_type` (varchar 20, NOT NULL), `quantity` (integer, NOT NULL), `limit_price` (numeric 18,6, nullable), `stop_price` (numeric 18,6, nullable), `confirmation_text` (text, NOT NULL), `outcome` (varchar 10, NOT NULL), `ip_address` (varchar 45, nullable), `user_agent` (text, nullable), `created_at` (datetime, NOT NULL, server default `now()`).
2. THE migration SHALL create an index `ix_rtaudit_user_created` on `(user_id, created_at)` in descending order on `created_at`.
3. THE migration SHALL create an index `ix_rtaudit_ticker` on `ticker`.
4. THE migration `downgrade()` SHALL drop both indexes and the table in the correct order.
5. THE migration `down_revision` SHALL be set to `"003"` to chain correctly after the existing migrations.

---

### Requirement 13: WebullClient Startup and Dependency Injection

**User Story:** As a backend developer, I want the `WebullClient` to be instantiated once at application startup and injected as a dependency, so that no per-request SDK construction overhead is incurred.

#### Acceptance Criteria

1. WHEN the FastAPI application starts and `market_data_source` is `"webull"`, THE system SHALL instantiate a single `WebullClient` from settings and store it for injection.
2. THE system SHALL create a single `WebullClient` instance and inject it into `WebullMarketService` via the `get_market_service()` dependency function.
3. THE system SHALL NOT call `login()`, start any background refresh task, or perform any session management during the `startup` event — the SDK is stateless and self-signing.
4. WHERE `MARKET_DATA_SOURCE` is set to `"yfinance"` or `"stub"`, THE system SHALL skip `WebullClient` initialization and not attempt to connect to Webull.

---

### Requirement 14: Parser and Normalizer for Webull Quote Data

**User Story:** As a backend developer, I want a normalization layer that converts raw Webull OpenAPI SDK responses into the canonical `QuoteResponse` schema, so that downstream consumers receive consistent data regardless of provider.

#### Acceptance Criteria

1. WHEN `WebullClient.fetch_quote()` returns raw data, THE `WebullMarketService` SHALL normalize the raw dict into a `WebullQuoteData` object containing: `ticker`, `company_name`, `price` (positive float), `change`, `change_pct`, `volume`, `day_high`, `day_low`, `week_52_high`, `week_52_low`, `market_cap`, and `source`.
2. THE normalizer SHALL map official SDK snapshot response fields: `close` → `price`, `change` → `change`, `changeRate` → `change_pct`, `volume` → `volume`, `high` → `day_high`, `low` → `day_low`, `week52High` → `week_52_high`, `week52Low` → `week_52_low`, `marketValue` → `market_cap`. Company name SHALL be fetched from `get_instrument` `name` field or fall back to the ticker symbol.
3. WHEN raw Webull data is missing an optional field (`volume`, `day_high`, `day_low`, `week_52_high`, `week_52_low`, `market_cap`), THE normalizer SHALL set the corresponding `WebullQuoteData` field to `None`.
4. FOR ALL valid `WebullQuoteData` objects, serializing to dict and then constructing a new `WebullQuoteData` from that dict SHALL produce an equivalent object (round-trip property).
5. WHEN raw Webull data has `price` as `None` or zero, THE normalizer SHALL treat it as a failure and raise `WebullUnavailableError` for that ticker.
