# Implementation Plan: Webull Integration

## Overview

This plan implements the Webull integration in two parallel workstreams:
1. **Market data workstream** — replace `yfinance`/stub with `WebullClient` + `WebullMarketService` using the official `webull-openapi-python-sdk` (App Key + App Secret auth, no session management, fallback chain, drop-in `MarketService` replacement).
2. **Real-trade confirmation workstream** — `TradingConfirmationService`, `RealTradeAuditLog`, new `POST /trading/real/confirm` route, and the `RealTradeConfirmModal` + `tradingConfirmStore` frontend gate.

Tasks are ordered to build foundational pieces first (config, package scaffold, DB migration) before layering in the service logic, frontend components, and tests.

---

## Tasks

- [x] 1. Environment configuration and SDK dependency
  - [x] 1.1 Update Webull settings fields in `backend/config.py`
    - Remove `webull_email`, `webull_password`, `webull_device_id`, `webull_mfa_code`, `webull_session_refresh_interval`.
    - Add `webull_app_key: str = ""`, `webull_app_secret: str = ""`, `webull_region_id: str = "us"`, `webull_endpoint: str = "api.webull.com"`, `webull_sandbox: bool = False`.
    - Keep `webull_trading_pin: str = ""` (stored but NEVER forwarded to any client call).
    - Keep `market_data_source: str = "webull"`.
    - All new fields with safe defaults so existing deployments don't break.
    - _Requirements: 11.1, 11.2_

  - [x] 1.2 Update `backend/.env.example` with new Webull variables
    - Remove placeholder entries for `WEBULL_EMAIL`, `WEBULL_PASSWORD`, `WEBULL_DEVICE_ID`, `WEBULL_MFA_CODE`, `WEBULL_SESSION_REFRESH_INTERVAL`.
    - Add placeholder entries for `WEBULL_APP_KEY`, `WEBULL_APP_SECRET`, `WEBULL_REGION_ID`, `WEBULL_ENDPOINT`, `WEBULL_SANDBOX` with inline comments.
    - _Requirements: 11.4_

  - [x] 1.3 Update `backend/requirements.txt`: replace `webull==0.1.16` with `webull-openapi-python-sdk`
    - Remove `webull==0.1.16`.
    - Add `webull-openapi-python-sdk` (latest stable release).
    - _Requirements: Dependencies section_


- [x] 2. `WebullClient` package scaffold — types, exception, and core client
  - [x] 2.1 Create `backend/webull_client/__init__.py` and `backend/webull_client/types.py`
    - Create `backend/webull_client/` directory.
    - `__init__.py` exports `WebullClient`, `WebullUnavailableError`, `WebullQuoteData`.
    - `types.py` defines the `WebullQuoteData` dataclass with all fields from design Model 3.
    - _Requirements: 14.1, 14.3_

  - [ ]* 2.2 Write property test for `WebullQuoteData` round-trip (Property 9)
    - **Property 9: Quote Normalization Round-Trip**
    - For any valid `WebullQuoteData`, serialize to dict and reconstruct — all fields must be equal.
    - Use `hypothesis` with `@given` strategies for all fields.
    - Place in `backend/tests/test_webull_client.py`.
    - **Validates: Requirements 14.4**

  - [x] 2.3 Rewrite `WebullClient.__init__` in `backend/webull_client/client.py` for official SDK
    - Define `WebullUnavailableError(Exception)`.
    - `WebullClient.__init__` accepts `app_key: str`, `app_secret: str`, `region_id: str = "us"`, `endpoint: str = "api.webull.com"`. NO `trading_pin`, `email`, `password`, `device_id`, `mfa_code` parameters.
    - Construct `ApiClient(app_key, app_secret, region_id)` internally.
    - Call `api_client.add_endpoint(region_id, endpoint)`.
    - Construct `DataClient(api_client)` and store as `self._data_client`.
    - No `login()` call — SDK is stateless/signature-based.
    - Remove all session management state (`self._authenticated`, `self._wb`, `self._session_refresh_interval`, rate-limiting attributes).
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2_

  - [x] 2.4 Rewrite `fetch_quote`, `fetch_bars` in `WebullClient` for official SDK
    - Remove `login()`, `refresh_session()`, `_acquire_rate_slot()`, `_call_with_retry()` (replace with simpler retry helper that checks `.status_code`).
    - Add `_call_with_retry_sdk(fn, *args, **kwargs)` that calls `fn(*args, **kwargs)`, checks `res.status_code == 200`; if not, retries up to 3 attempts with `2^attempt` backoff; raises `WebullUnavailableError` if all fail.
    - `fetch_quote(ticker)`: call `self._data_client.market_data.get_snapshot(ticker, "US_STOCK", extend_hour_required=True, overnight_required=True)` via retry helper; check `.status_code == 200`; raise `WebullUnavailableError` on non-200; call `_check_not_empty` on `.json()`; return raw dict.
    - `fetch_bars(ticker, interval, count=200)`: call `self._data_client.market_data.get_history_bar(ticker, "US_STOCK", interval)` via retry helper; `interval` is a Timespan enum name string (`"M1"`, `"M5"`, `"M15"`, `"M30"`, `"H1"`, `"D1"`); return list of bar dicts.
    - `fetch_news(ticker, count=20)`: always raises `WebullUnavailableError("News not available via official Webull SDK — use yfinance fallback")`. No API call.
    - `fetch_movers()`: always raises `WebullUnavailableError("Movers not available via official Webull SDK — use stub fallback")`. No API call.
    - Log every call at `DEBUG` with ticker/operation and elapsed time.
    - _Requirements: 1.5, 2.1, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

  - [x]* 2.5 Write unit tests for `WebullClient` (retry, read-only enforcement, SDK construction)
    - Mock `DataClient` and `ApiClient` instances.
    - Test: `__init__` constructs `ApiClient`, calls `add_endpoint`, constructs `DataClient`.
    - Test: `fetch_quote` with non-200 response → retries up to 3 times → `WebullUnavailableError`.
    - Test: `fetch_quote` with 200 and null `close` → treated as failure → retried.
    - Test: `fetch_news` always raises `WebullUnavailableError` (no SDK call made).
    - Test: `fetch_movers` always raises `WebullUnavailableError` (no SDK call made).
    - Test: `trading_pin` is never passed in any call (constructor has no such parameter).
    - Place in `backend/tests/test_webull_client.py`.
    - _Requirements: 1.3, 1.4, 2.1, 3.1–3.4_


- [x] 3. `WebullMarketService` — drop-in replacement for `MarketService`
  - [x] 3.1 Update quote normalization in `backend/webull_client/client.py` for official SDK field names
    - Update `_normalize_webull_quote` to map official SDK snapshot fields: `close` → `price`, `changeRate` → `change_pct` (decimal e.g. 0.0121), `change` → `change`, `volume` → `volume`, `high` → `day_high`, `low` → `day_low`, `week52High` → `week_52_high`, `week52Low` → `week_52_low`, `marketValue` → `market_cap`.
    - Company name: use `get_instrument` response `name` field where available; fall back to ticker symbol.
    - Raise `WebullUnavailableError` if `price` is `None` or zero.
    - Set `source="webull"`.
    - _Requirements: 14.1, 14.2, 14.3, 14.5_

  - [x] 3.2 Update `PERIOD_INTERVAL_MAP` in `backend/market/service.py` for official SDK Timespan names
    - Update `PERIOD_INTERVAL_MAP` values to use official SDK Timespan enum names: `"M1"`, `"M5"`, `"M15"`, `"M30"`, `"H1"`, `"D1"` (uppercase, matching `Timespan.M1.name` etc.).
    - Mapping table (unchanged pairs, updated interval codes):
      - `("1d", "1m")` → `("M1", 390)`
      - `("1d", "5m")` → `("M5", 78)`
      - `("1d", "15m")` → `("M15", 26)`
      - `("5d", "5m")` → `("M5", 390)`
      - `("1mo", "1h")` → `("H1", 720)`
      - `("3mo", "1d")` → `("D1", 63)`
      - `("1y", "1d")` → `("D1", 252)`
    - _Requirements: 4.8_

  - [x] 3.3 Verify `get_quote` fallback chain still correct in `WebullMarketService`
    - No logic change needed — `WebullUnavailableError` is still the trigger for yfinance fallback.
    - TTL 15 s for Webull, 30 s for yfinance remains correct.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.9_

  - [ ]* 3.4 Write property test for fallback completeness (Property 2)
    - **Property 2: Fallback Completeness**
    - For any ticker where `WebullClient.fetch_quote` raises `WebullUnavailableError` and yfinance returns a valid price, `WebullMarketService.get_quote` returns a valid `QuoteResponse` with `data_source="yfinance"`.
    - Use `hypothesis` with mocked `WebullClient`.
    - Place in `backend/tests/test_webull_market_service.py`.
    - **Validates: Requirements 4.4, 4.5, 4.7**

  - [x] 3.5 Verify `get_chart` period/interval mapping uses updated Timespan names
    - No logic change needed — `PERIOD_INTERVAL_MAP` update in 3.2 is sufficient.
    - Confirm `fetch_bars` is called with `"M1"` / `"M5"` etc. (not `"m1"` / `"m5"`).
    - _Requirements: 4.8, 5.1_

  - [x] 3.6 Verify `get_movers`, `get_news`, `get_ticker_news`, `get_snapshot` fallback behavior
    - `get_movers`: `fetch_movers()` now always raises `WebullUnavailableError` → always falls back to stub data. No logic change needed.
    - `get_news` / `get_ticker_news`: `fetch_news()` now always raises `WebullUnavailableError` → always falls back to stub data. Remove the conditional Webull news path if present.
    - `get_snapshot`: `fetch_quote("SPY")` etc. still works via official SDK — no change needed.
    - _Requirements: 4.3, 4.5, 5.1_

  - [x] 3.7 Verify stub-passthrough methods and alert methods in `WebullMarketService`
    - `get_prediction`, `get_predictions`, `get_penny_stocks`: unchanged.
    - `get_alerts`, `dismiss_alert`, `mark_all_alerts_read`: unchanged.
    - _Requirements: 5.3_

  - [ ]* 3.8 Write unit tests for `WebullMarketService` cache and fallback paths
    - Mock `WebullClient`; test cache hit (no Webull call), cache miss + Webull success, Webull fail + yfinance success, both fail → 503.
    - Test `data_source` field value in each path.
    - Test period/interval mapping produces correct `fetch_bars` call args (uppercase Timespan names).
    - Place in `backend/tests/test_webull_market_service.py`.
    - _Requirements: 4.1–4.9, 5.2_


- [x] 4. Startup wiring — simplified `WebullClient` construction and dependency injection
  - [x] 4.1 Rewrite `_startup_webull` in `backend/main.py` for official SDK
    - Remove the existing `_session_refresh_loop` function entirely.
    - Remove `_startup_webull`'s `client.login()` call and `asyncio.create_task(_session_refresh_loop(client))`.
    - Rewrite startup handler to:
      1. Check `settings.market_data_source`; skip Webull init if `"yfinance"` or `"stub"`.
      2. Determine endpoint: `"api.sandbox.webull.com"` if `settings.webull_sandbox` else `settings.webull_endpoint`.
      3. Instantiate `WebullClient(app_key=settings.webull_app_key, app_secret=settings.webull_app_secret, region_id=settings.webull_region_id, endpoint=endpoint)`.
      4. Store via `set_webull_client(client)`.
      5. Log success. No login(), no create_task.
    - Update `get_market_service()` in `backend/market/router.py` to inject the singleton `WebullClient` into `WebullMarketService` (no behavior change needed if already done).
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 4.2 Write unit tests for startup wiring behavior
    - Test: `market_data_source="webull"` → `WebullClient` constructed with correct `app_key`/`app_secret`; no `login()` called; no background task started.
    - Test: `market_data_source="yfinance"` → `WebullClient` never instantiated.
    - Test: `webull_sandbox=True` → endpoint set to `"api.sandbox.webull.com"`.
    - Test: `get_market_service()` returns `WebullMarketService` with the singleton client.
    - Place in `backend/tests/test_webull_market_service.py`.
    - _Requirements: 13.1, 13.4_

- [x] 5. Checkpoint — market data workstream
  - Ensure all backend tests in the market data workstream pass.
  - Verify `WebullMarketService` is a drop-in replacement: all `/market/*` routes return the same schemas as before.
  - Ask the user if questions arise.

- [x] 6. Database migration `004_create_real_trade_audit_log`
  - [x] 6.1 Create `backend/migrations/versions/004_create_real_trade_audit_log.py`
    - Set `revision = "004"`, `down_revision = "003"`.
    - `upgrade()`: create `real_trade_audit_log` table with all columns from design Model 2.
    - Use `ondelete="RESTRICT"` on the `user_id` FK.
    - Create index `ix_rtaudit_user_created` on `(user_id, created_at)`.
    - Create index `ix_rtaudit_ticker` on `ticker`.
    - `downgrade()`: drop indexes then drop table in correct order.
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 7. `RealTradeAuditLog` SQLAlchemy model and trading schemas
  - [x] 7.1 Add `RealTradeAuditLog` model to `backend/trading/models.py`
    - Add `RealTradeAuditLog` SQLAlchemy ORM model with all columns from design Model 2.
    - `user_id` FK uses `ondelete="RESTRICT"`.
    - Row is insert-only; do NOT expose any update/delete methods.
    - _Requirements: 7.1, 7.3_

  - [x] 7.2 Add `RealOrderRequest` and `RealOrderConfirmResponse` to `backend/trading/schemas.py`
    - `RealOrderRequest`: `ticker`, `side` (Literal buy/sell), `order_type` (Literal), `quantity` (Field gt=0), optional `limit_price`, optional `stop_price`, `confirmation_text`.
    - `RealOrderConfirmResponse`: `order_id: str`, `status: str`, `message: str`.
    - _Requirements: 8.1, 8.2_


- [x] 8. `TradingConfirmationService`
  - [x] 8.1 Implement `TradingConfirmationService` in `backend/trading/confirmation_service.py`
    - `__init__(self, db: Session, redis_client, user_id: UUID)`.
    - `generate_confirmation_challenge(order)` → returns `"{TICKER} {QUANTITY} {SIDE.upper()}"` string.
    - `validate_and_submit(order, confirmation_text, user_id, ip_address)`:
      1. Normalize both strings with `.strip().upper()`.
      2. Compare; build `ConfirmationResult` accordingly.
      3. ALWAYS call `_write_audit_log` regardless of outcome.
    - `_write_audit_log(...)` → INSERT into `real_trade_audit_log`.
    - NEVER access `WEBULL_TRADING_PIN` or any trading PIN value.
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.6_

  - [ ]* 8.2 Write property test for confirmation soundness (Property 4)
    - **Property 4: Confirmation Gate Soundness**
    - For all `(ticker, quantity, side)` and any `confirmation_text` ≠ `"{ticker} {quantity} {side.upper()}"`, `validate_and_submit` must return `success=False`.
    - Use `hypothesis` with `st.text()` strategies; mock DB session.
    - Place in `backend/tests/test_trading_confirmation_service.py`.
    - **Validates: Requirements 6.2, 6.4**

  - [ ]* 8.3 Write property test for audit log immutability (Property 3)
    - **Property 3: Audit Log Immutability**
    - For any call to `validate_and_submit`, exactly one row is inserted into `real_trade_audit_log` (DB row count +1 regardless of outcome).
    - Use `hypothesis`; track DB INSERT call count via mock.
    - Place in `backend/tests/test_trading_confirmation_service.py`.
    - **Validates: Requirements 6.5, 7.3, 7.4**

  - [ ]* 8.4 Write unit tests for `TradingConfirmationService`
    - Test: correct `confirmation_text` → `success=True`, audit row written with `outcome="confirmed"`.
    - Test: wrong `confirmation_text` → `success=False`, audit row written with `outcome="rejected"`.
    - Test: case/whitespace normalization (e.g. `"  aapl 100 buy  "` matches `"AAPL 100 BUY"`).
    - Test: `ip_address` stored in audit row.
    - Place in `backend/tests/test_trading_confirmation_service.py`.
    - _Requirements: 6.1–6.6_

- [x] 9. `POST /trading/real/confirm` route
  - [x] 9.1 Add `confirm_real_order` route to `backend/trading/router.py`
    - Implement `POST /real/confirm` as specified in the design.
    - Import and use `TradingConfirmationService`, `RealOrderRequest`, `RealOrderConfirmResponse`.
    - Capture `request.client.host` as `ip_address`.
    - Return HTTP 201 on success; raise HTTP 422 with `result.reason` on mismatch.
    - Add a paper-mode guard: if `current_user` has no real-money flag, return HTTP 403.
    - Require `get_current_user` dependency (HTTP 401 for unauthenticated requests handled by dependency).
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 9.2 Write integration tests for `POST /trading/real/confirm`
    - Use `TestClient` with mocked `TradingConfirmationService`.
    - Test: valid `confirmation_text` → HTTP 201 with `order_id` and `status="submitted"`.
    - Test: mismatched `confirmation_text` → HTTP 422 with detail message.
    - Test: unauthenticated request → HTTP 401.
    - Test: paper-mode user → HTTP 403.
    - Place in `backend/tests/test_real_trade_route.py`.
    - _Requirements: 8.1–8.6_

- [x] 10. Checkpoint — backend confirmation workstream
  - Ensure all backend tests for tasks 6–9 pass.
  - Verify audit log writes on both confirmed and rejected paths.
  - Ask the user if questions arise.


- [x] 11. Frontend: `tradingConfirmStore`
  - [x] 11.1 Create `frontend/src/store/tradingConfirmStore.ts`
    - Implement `RealTradeConfirmState` interface and `useTradingConfirmStore` Zustand store exactly as specified in the design Component 5.
    - Export `RealOrderRequest` interface (or import from `api/trading.ts`).
    - `openConfirmation(order)` sets `isOpen=true`, `pendingRealOrder=order`, `expectedConfirmText="{ticker} {quantity} {side.toUpperCase()}"`.
    - `closeConfirmation()` resets all fields to initial values.
    - `setSubmitting(v)` sets `isSubmitting=v`.
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 11.2 Write property test for `tradingConfirmStore` (Property 8 — frontend side)
    - **Property 8: Confirmation String Correctness (frontend)**
    - For any `{ ticker, quantity, side }`, `openConfirmation` sets `expectedConfirmText` to `"{ticker} {quantity} {side.toUpperCase()}"`.
    - Use `fast-check` with `fc.record({ ticker: fc.string(), quantity: fc.integer(), side: fc.constantFrom("buy","sell") })`.
    - Place in `frontend/src/api/__tests__/tradingConfirmStore.property.test.ts`.
    - **Validates: Requirements 10.2**

  - [ ]* 11.3 Write unit tests for `tradingConfirmStore`
    - Test: initial state (all null/false).
    - Test: `openConfirmation` → `isOpen=true`, correct `expectedConfirmText`.
    - Test: `closeConfirmation` → all fields reset.
    - Test: `setSubmitting(true)` → `isSubmitting=true`.
    - Place in `frontend/src/api/__tests__/tradingConfirmStore.test.ts`.
    - _Requirements: 10.1–10.4_

- [x] 12. Frontend: `confirmRealOrder` API function
  - [x] 12.1 Add `RealOrderRequest`, `RealOrderConfirmResponse`, and `confirmRealOrder` to `frontend/src/api/trading.ts`
    - Add `RealOrderRequest` interface matching backend schema (include `confirmation_text`).
    - Add `RealOrderConfirmResponse` interface.
    - Implement `confirmRealOrder(data: RealOrderRequest): Promise<RealOrderConfirmResponse>` that calls `POST /trading/real/confirm`.
    - _Requirements: 8.1_

- [x] 13. Frontend: `RealTradeConfirmModal` component
  - [x] 13.1 Create `frontend/src/components/trading/RealTradeConfirmModal.tsx`
    - Props: `isOpen`, `onClose`, `order: RealOrderRequest | null`, `onConfirmed(orderId: string)`.
    - Amber header band with `⚠ REAL MONEY TRADE` label.
    - Order summary rows matching `OrderConfirmModal` layout.
    - Disclaimer: `"This will place a REAL order with REAL money. This action cannot be undone."`.
    - Typed confirmation input with dynamic placeholder `Type "{TICKER} {QUANTITY} {SIDE}" to confirm`.
    - Submit button disabled until `inputValue.trim().toUpperCase() === expectedConfirmText`; amber color when enabled.
    - Do NOT render `PaperTradingBanner`.
    - Disable Escape key and backdrop click while `isSubmitting=true`.
    - On HTTP 422 response: show inline error, keep modal open.
    - On HTTP 201 response: call `tradingConfirmStore.closeConfirmation()`, show `toast.success("Real order submitted")`.
    - _Requirements: 9.1–9.10_

  - [ ]* 13.2 Write unit tests for `RealTradeConfirmModal`
    - Test: submit button is disabled when input is empty.
    - Test: submit button is disabled when input is partial/wrong.
    - Test: submit button is enabled when exact `expectedConfirmText` is entered.
    - Test: amber header band is rendered (check CSS class or text).
    - Test: `PaperTradingBanner` is NOT in the DOM.
    - Test: HTTP 422 response keeps modal open and shows inline error.
    - Place in `frontend/src/test/RealTradeConfirmModal.test.tsx`.
    - _Requirements: 9.2–9.9_

- [x] 14. Frontend: wire `OrderTicket` to use `tradingConfirmStore` for real-money orders
  - [x] 14.1 Update `frontend/src/components/trading/OrderTicket.tsx`
    - Import `useTradingConfirmStore` and `RealTradeConfirmModal`.
    - In `onSubmit`, check if the current account is in real-money mode (e.g., via a prop or store flag). If real-money: call `tradingConfirmStore.openConfirmation(orderRequest)` instead of `setPendingOrder(orderRequest)`.
    - Render `<RealTradeConfirmModal>` alongside `<OrderConfirmModal>` in the return, driven by `tradingConfirmStore.isOpen`.
    - Paper trades continue to use the existing `OrderConfirmModal` path unchanged.
    - _Requirements: 9.1_

- [x] 15. Checkpoint — frontend confirmation workstream
  - Ensure all frontend tests pass (`vitest --run`).
  - Verify the typed confirmation gate works end-to-end in the browser for a real-money order.
  - Ask the user if questions arise.

- [x] 16. Final checkpoint — full integration
  - Ensure all backend tests pass.
  - Ensure all frontend tests pass.
  - Verify that all `/market/*` routes return identical schemas to the pre-integration baseline.
  - Ask the user if questions arise.


---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP implementation.
- Migration number is `004` — migration `003` is already used by `watchlist_items`.
- `WebullClient` constructor has NO `trading_pin`, `email`, `password`, `device_id`, or `mfa_code` parameters. `Settings.webull_trading_pin` is stored but blocked at the client layer.
- `WebullMarketService` must be a drop-in replacement — all method signatures identical to `MarketService`.
- `data_source` field must be present in every market data response.
- The `real_trade_audit_log` table is insert-only; no application-layer update or delete endpoint is to be created.
- Property tests use `hypothesis` (Python backend) and `fast-check` (TypeScript frontend).
- The official SDK uses `Timespan` enum values `M1`, `M5`, `M15`, `M30`, `H1`, `D1` (uppercase) — not the lowercase `m1`/`m5` strings used in the unofficial package.
- News and movers via the official SDK are not supported; both always fall back to yfinance/stub immediately.
- No `login()` or background session refresh is needed — the SDK signs requests via HMAC-SHA1 automatically.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "6.1"] },
    { "id": 2, "tasks": ["2.2", "2.3"] },
    { "id": 3, "tasks": ["2.4", "3.1"] },
    { "id": 4, "tasks": ["2.5", "3.2", "7.1", "7.2"] },
    { "id": 5, "tasks": ["3.3", "8.1"] },
    { "id": 6, "tasks": ["3.4", "3.5", "8.2", "8.3", "8.4"] },
    { "id": 7, "tasks": ["3.6", "9.1"] },
    { "id": 8, "tasks": ["3.7", "3.8", "9.2"] },
    { "id": 9, "tasks": ["4.1", "11.1"] },
    { "id": 10, "tasks": ["4.2", "11.2", "11.3", "12.1"] },
    { "id": 11, "tasks": ["13.1"] },
    { "id": 12, "tasks": ["13.2", "14.1"] }
  ]
}
```
