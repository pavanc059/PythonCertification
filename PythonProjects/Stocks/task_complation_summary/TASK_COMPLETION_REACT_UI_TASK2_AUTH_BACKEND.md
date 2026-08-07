# Task Completion: Implement user authentication backend

**Status:** Completed ✅  
**Date:** 2025-01-28

---

## Files Created or Modified

| File | Action | Description |
|------|--------|-------------|
| `backend/config.py` | **Created** | Moved `Settings` / `settings` out of `main.py` into a standalone module so `dependencies.py` and `auth/` can import settings without a circular dependency |
| `backend/auth/models.py` | **Created** | SQLAlchemy `User` ORM model (`users` table: UUID PK, email, name, hashed_password, is_active, theme_preference, created_at) |
| `backend/auth/schemas.py` | **Created** | Pydantic v2 request/response schemas: `UserRegister`, `UserLogin`, `UserResponse`, `TokenResponse`, `TokenData` |
| `backend/auth/service.py` | **Created** | bcrypt password hashing/verification (using `bcrypt` directly to avoid passlib 1.7.x / bcrypt 4.x incompatibility); JWT access and refresh token creation and decoding via `python-jose` |
| `backend/auth/router.py` | **Created** | FastAPI router with four endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`; HTTP-only SameSite=lax refresh-token cookie |
| `backend/dependencies.py` | **Modified** | Replaced the `HTTP 501` stub `get_current_user` with real JWT validation using `decode_token` + DB user lookup |
| `backend/main.py` | **Modified** | Imports `settings` from `config.py` (not inline); uncommented `auth_router` include |
| `backend/requirements.txt` | **Modified** | Added `email-validator==2.1.1` (required by `pydantic[email]` for `EmailStr`); added explicit `bcrypt==4.2.1` pin |
| `backend/migrations/versions/001_create_users_table.py` | **Created** | Alembic migration that creates the `users` table with `op.create_table()` and a unique index on `email`; supports both `upgrade()` and `downgrade()` |
| `backend/tests/test_auth_service.py` | **Created** | 17 unit tests covering password hashing, token creation, token decoding, expired tokens, tampered tokens, wrong secrets |

---

## What Was Implemented

### Password Security (R1.6)
- `hash_password(plain)` — bcrypt hash with random salt
- `verify_password(plain, hashed)` — constant-time compare
- Used `bcrypt` library directly; bypasses `passlib`/bcrypt 4.x incompatibility

### JWT Tokens (R1.3, R1.4)
- `create_access_token(data, expires_delta)` — HS256-signed, configurable expiry (default 8 h)
- `create_refresh_token(data, expires_delta)` — signed with a derived secret (`secret_key + "_refresh"`) so a leaked access secret does not compromise refresh tokens
- `decode_token(token, secret_key)` — validates signature + expiry, returns `TokenData`

### Endpoints (R7.2)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /auth/register` | ✅ | 400 if email taken; issues access + refresh tokens |
| `POST /auth/login` | ✅ | 401 on any credential mismatch (email-or-password ambiguity) |
| `POST /auth/logout` | ✅ | Clears refresh-token cookie; requires valid Bearer token |
| `POST /auth/refresh` | ✅ | Reads `refresh_token` cookie, issues new access token (no rotation) |

### Dependency Injection (R7.7)
`get_current_user` in `dependencies.py` now:
1. Extracts Bearer token via `OAuth2PasswordBearer`
2. Decodes it with `decode_token`
3. Queries `users` table by UUID
4. Raises HTTP 401 if token invalid, user missing, or user inactive

### Database Migration
`001_create_users_table.py` creates the `users` table and `ix_users_email` unique index, with full `upgrade()` / `downgrade()` support.

---

## Tests

**File:** `backend/tests/test_auth_service.py`  
**Result:** 17 / 17 passed ✅

| Class | Tests |
|-------|-------|
| `TestPasswordHashing` | 6 — hash format, verify correct/wrong password, salt randomness, roundtrip |
| `TestAccessToken` | 6 — create, decode, expired, wrong secret, tampered, UUID type |
| `TestRefreshToken` | 5 — create, decode, access≠refresh, cross-secret rejection, expired |

---

## Requirements Satisfied

| Requirement | Description |
|-------------|-------------|
| R1.1 | Login via email + password |
| R1.2 | Registration with name, email, password |
| R1.3 | JWT access tokens with configurable expiry (480 min default) |
| R1.4 | HTTP-only cookie for refresh token |
| R1.6 | bcrypt password hashing; plain-text passwords never stored |
| R1.7 | Pydantic validators surface "Email already registered" and "Password too short" |
| R1.8 | Logout clears session cookies |
| R7.2 | All four `/auth/*` endpoints implemented |
| R7.7 | `get_current_user` dependency validates JWT Bearer token on every protected route |

---

## Notes

- **Circular import resolution**: `Settings`/`settings` live in `backend/config.py`. `main.py` imports from `config.py`. `dependencies.py` imports from `config.py`. `auth/router.py` imports from `config.py`. No module imports from `main.py`.
- **bcrypt compatibility**: `passlib 1.7.4` is incompatible with `bcrypt ≥ 4.x`. Password operations call `bcrypt` directly; `passlib` was removed from the effective dependency graph for this module (left in `requirements.txt` for any other potential use).
- **Refresh token rotation**: Not implemented (as per spec — "don't rotate refresh token" in `/auth/refresh`).
- **Next steps**: Task 3 (portfolio backend) can now use `get_current_user` from `dependencies.py` to protect its routes.
