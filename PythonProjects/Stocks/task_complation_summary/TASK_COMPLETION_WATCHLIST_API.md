# Task Completion: Implement Watchlist API Endpoints

**Status:** Completed ✅  
**Date:** 2025-01-27

## Files

### Created
- `backend/watchlist/models.py` — `WatchlistItem` SQLAlchemy ORM model with UUID PK, user_id FK, ticker, list_name, alert_price, created_at, unique constraint on (user_id, ticker, list_name), and index on user_id
- `backend/watchlist/schemas.py` — Pydantic v2 schemas: `WatchlistItemResponse`, `WatchlistListResponse`, `AddWatchlistItemRequest` (with ticker auto-uppercase validator), `WatchlistListCreate` (with alphanumeric name validator)
- `backend/watchlist/service.py` — `WatchlistService` class with `get_items`, `add_item`, `remove_item`, `get_lists`, and `create_list` methods; raises HTTP 409 on duplicate, HTTP 404 on missing item for delete
- `backend/watchlist/router.py` — FastAPI router with all 5 endpoints protected by `get_current_user` dependency
- `backend/tests/test_watchlist.py` — 41 pytest tests covering all endpoints

### Modified
- `backend/main.py` — Uncommented watchlist router registration (`from watchlist.router import router as watchlist_router` + `app.include_router(...)`)

## What Was Implemented

### Model (`watchlist/models.py`)
- `WatchlistItem` table with columns: `id` (UUID PK), `user_id` (UUID, indexed), `ticker` (String), `list_name` (String, default "Default"), `alert_price` (Numeric(18,6), nullable), `created_at` (DateTime)
- Unique constraint `uq_watchlist_user_ticker_list` on `(user_id, ticker, list_name)` — same ticker can appear in multiple lists but not duplicated within the same list
- Inherits from `database.Base`

### Schemas (`watchlist/schemas.py`)
- `AddWatchlistItemRequest`: ticker auto-uppercased via `field_validator`, list_name defaults to "Default", optional alert_price
- `WatchlistListCreate`: name validated to reject empty strings and special characters (only alphanumerics, spaces, hyphens, underscores allowed)
- `WatchlistItemResponse` / `WatchlistListResponse`: Pydantic v2 with `ConfigDict(from_attributes=True)`

### Service (`watchlist/service.py`)
- `get_items(list_name=None)`: returns all items for user, optionally filtered by list
- `add_item(ticker, list_name, alert_price)`: creates item; raises HTTP 409 if duplicate within same list
- `remove_item(ticker, list_name)`: deletes item; returns `True` if found, `False` if not
- `get_lists()`: aggregates distinct list names with `COUNT()` via SQLAlchemy
- `create_list(name)`: returns existing list metadata if populated, otherwise returns empty list metadata (lists are implicit)

### Router (`watchlist/router.py`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/watchlist` | List all items; optional `?list_name=` filter |
| POST | `/watchlist/add` | Add ticker; returns 201 on success, 409 on duplicate |
| DELETE | `/watchlist/{ticker}` | Remove ticker; optional `?list_name=` param; 404 if not found |
| GET | `/watchlist/lists` | Get all list names with item counts |
| POST | `/watchlist/lists` | Create named list; returns 201; 422 on invalid name |

## Tests

**File:** `backend/tests/test_watchlist.py`  
**Result:** 41/41 passed ✅

### Test coverage by class:
| Class | Count | Description |
|-------|-------|-------------|
| `TestGetWatchlist` | 8 | 200 responses, empty list, list_name filter, schema fields, alert_price null/set, user_id propagation |
| `TestAddToWatchlist` | 9 | 201 creation, ticker uppercasing, named lists, alert price, 409 duplicate, 422 empty ticker, defaults |
| `TestRemoveFromWatchlist` | 6 | 200 success, 404 not found, ticker uppercasing, list_name forwarding, defaults |
| `TestGetLists` | 4 | 200 with lists, item_count field, empty array, user_id propagation |
| `TestCreateList` | 7 | 201 creation, schema, existing list metadata, 422 empty name, 422 special chars, name forwarding |
| `TestUnauthenticated` | 4 | 401 for GET, POST /add, DELETE, GET /lists |
| `TestMultipleItems` | 3 | Multiple tickers, same ticker in different lists, multiple lists |

## Requirements Satisfied

- **R3.1** — Users can add stocks to a personal watchlist (`POST /watchlist/add`)
- **R3.3** — Users can remove stocks from their watchlist (`DELETE /watchlist/{ticker}`)
- **R3.4** — Watchlist supports multiple named lists (`list_name` field, `GET/POST /watchlist/lists`)
- **R3.7** — Price alerts stored on watchlist items (`alert_price` field on model and add endpoint)
- **R7.4** — All required watchlist endpoints implemented: `GET /watchlist`, `POST /watchlist/add`, `DELETE /watchlist/{ticker}`, `GET /watchlist/lists`, `POST /watchlist/lists`

## Notes

- Alembic migration for the `watchlist_items` table was not generated in this task (migration files are managed separately). The model is ready and the table will be created when the next migration is run.
- The `user_id` column has no SQLAlchemy-level FK constraint declared in the model file (to avoid a circular import with `auth.models`); the FK is intended to be added in the Alembic migration as done in `trading/models.py`.
- `GET /watchlist/lists` returns only lists that have at least one item (empty lists created via `POST /watchlist/lists` are not persisted to the DB — they are logical, client-side concepts until populated).
