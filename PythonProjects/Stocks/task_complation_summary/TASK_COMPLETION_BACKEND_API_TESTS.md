# Task Completion: 30. Write backend API tests

**Status:** Completed ✅  
**Date:** 2025-01-27

## Files Created or Modified

| File | Action | Description |
|------|--------|-------------|
| `backend/tests/test_auth.py` | Modified | Fixed 3 issues: engine disposal before DB file deletion, unique emails in logout fixture, fresh clients for cookie-sensitive refresh tests |
| `backend/tests/test_trading.py` | Verified (no changes) | All 35 tests passed as-is |
| `backend/tests/test_portfolio.py` | Verified (no changes) | All 27 tests passed as-is |
| `backend/tests/test_watchlist.py` | Verified (no changes) | All 46 tests passed as-is |
| `backend/watchlist/models.py` | Modified | Removed duplicate `index=True` on `user_id` column — the same index was already declared in `__table_args__` as `Index("ix_watchlist_items_user_id", "user_id")`, causing SQLite to fail with "index already exists" when `Base.metadata.create_all()` was called during auth tests |

## What Was Implemented

The four test files already existed. The work was running them together, identifying failures, and fixing root causes:

### Root Cause 1 — Duplicate SQLite index (`watchlist/models.py`)
`WatchlistItem.user_id` had both `index=True` (which auto-creates `ix_watchlist_items_user_id`) **and** an explicit `Index("ix_watchlist_items_user_id", "user_id")` in `__table_args__`. SQLAlchemy emits two `CREATE INDEX` statements for the same name. PostgreSQL silently ignores this; SQLite raises `OperationalError: index already exists`. This caused all 26 auth tests to error when run alongside the other test files (which import the watchlist model via the app).

**Fix:** Removed `index=True` from the column definition, keeping only the explicit `Index` in `__table_args__`.

### Root Cause 2 — Module-scoped client cookie bleed (`test_auth.py`)
`TestRefresh::test_invalid_refresh_token_returns_401` set a cookie on the module-scoped `client` and attempted to delete it, but the deletion didn't take effect before `test_missing_cookie_returns_401` ran. The subsequent test then got `200` (valid cookie present) instead of `401`.

**Fix:** Both `test_invalid_refresh_token_returns_401` and `test_missing_cookie_returns_401` now use fresh `TestClient` instances with isolated cookie jars.

### Root Cause 3 — Windows file lock on SQLite teardown (`test_auth.py`)
The `app` fixture (module-scoped) tried to `os.remove("test_auth_tmp.db")` on teardown. On Windows, SQLAlchemy's connection pool holds the file open. The `PermissionError` prevented cleanup.

**Fix:** Added `_engine.dispose()` before `os.remove()` to release all pooled connections. Wrapped the remove in a try/except for best-effort cleanup.

### Root Cause 4 — Email collision in `TestLogout.auth_client` fixture
The `auth_client` fixture registered `logout_user@example.com` every test invocation. If the module-scoped SQLite DB persisted from a prior interrupted run, the second registration would hit the 400 "already registered" path, causing `KeyError: 'access_token'`.

**Fix:** Now generates a unique email per fixture call using a millisecond timestamp.

## Tests Written

| File | Tests | Result |
|------|-------|--------|
| `backend/tests/test_auth.py` | 26 | ✅ 26/26 passed |
| `backend/tests/test_trading.py` | 35 | ✅ 35/35 passed |
| `backend/tests/test_portfolio.py` | 27 | ✅ 27/27 passed |
| `backend/tests/test_watchlist.py` | 46 | ✅ 46/46 passed |
| **Total** | **134** | **✅ 134/134 passed** |

## Requirements Satisfied

R1.1, R1.2, R1.3, R1.4, R1.5, R1.7, R1.8, R2.1, R2.2, R2.3, R2.4, R2.5, R2.6, R2.7, R2.8, R3.1, R3.3, R3.4, R3.7, R4.1, R4.2, R5.1, R5.2, R5.3, R5.4, R5.5, R5.6, R5.7, R5.8, R7.3, R7.4, R7.5

## Notes

- **No `conftest.py` or `pytest.ini` needed** — all test files include their own `sys.path.insert` to add the `backend/` directory to the path, and `os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")` to bypass PostgreSQL.
- **No `tests/__init__.py` needed** — pytest discovers the tests fine without it in this layout.
- **`watchlist/models.py` change is safe for production** — PostgreSQL creates the index via the `Index` declaration in `__table_args__`; removing `index=True` from the column doesn't change the DDL emitted by Alembic (the explicit `Index` object is what Alembic tracks).
- **Auth tests use a real SQLite database** (`test_auth_tmp.db`) rather than mocks, giving genuine end-to-end coverage of register/login/refresh/logout flows including JWT generation and bcrypt password hashing.
