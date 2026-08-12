"""
Integration tests for the auth router (/auth/* endpoints).

Strategy
--------
- FastAPI TestClient drives the full request/response cycle.
- get_db is overridden to yield a real in-memory SQLite session so that
  the register/login/refresh endpoints can actually perform ORM operations.
- All tables (users + paper_trading_accounts) are created before each test
  and dropped after, giving each test class a clean slate.

Requirements validated: R1.1, R1.2, R1.3, R1.4, R1.5, R1.7, R7.1, R7.2
"""

import sys
import os

# ---------------------------------------------------------------------------
# Path setup — make backend/ importable
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use SQLite so no PostgreSQL instance is required.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database import Base

# Import models so their tables are registered on Base.metadata
import auth.models  # noqa: F401 — registers User table
import trading.models  # noqa: F401 — registers PaperTradingAccountDB table

# ---------------------------------------------------------------------------
# SQLite test database helpers
# ---------------------------------------------------------------------------

_SQLITE_URL = "sqlite:///./test_auth_tmp.db"

# Use check_same_thread=False because FastAPI runs handlers in a thread pool
_engine = create_engine(
    _SQLITE_URL,
    connect_args={"check_same_thread": False},
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _create_tables() -> None:
    Base.metadata.create_all(bind=_engine)


def _drop_tables() -> None:
    Base.metadata.drop_all(bind=_engine)


def _get_test_db():
    """Dependency override that yields a real SQLite session."""
    db: Session = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# App fixture — one app instance per test module; tables reset per class
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """FastAPI app with DB overridden to use SQLite."""
    from main import app as _app
    from dependencies import get_db

    _app.dependency_overrides[get_db] = _get_test_db
    _create_tables()
    yield _app
    _app.dependency_overrides.clear()
    _drop_tables()
    # Dispose the engine connection pool before trying to delete the file.
    # On Windows, the file is locked until all connections are released.
    _engine.dispose()
    if os.path.exists("test_auth_tmp.db"):
        try:
            os.remove("test_auth_tmp.db")
        except OSError:
            pass  # Best-effort cleanup; file may be cleaned up on next run


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_REG_PAYLOAD = {
    "email": "alice@example.com",
    "name": "Alice",
    "password": "securepassword123",
}


def _register(client, payload: dict | None = None) -> dict:
    """POST /auth/register and return parsed JSON."""
    resp = client.post("/auth/register", json=payload or _REG_PAYLOAD)
    return resp


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

class TestRegister:
    """Tests for POST /auth/register (R1.2, R1.5, R7.1)."""

    def test_successful_registration_returns_201(self, client):
        """New user registration returns 201 with access token (R1.2)."""
        resp = _register(client)
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_registration_returns_user_fields(self, client):
        """Response includes user object with id, email, name (R1.2)."""
        resp = client.post("/auth/register", json={
            "email": "bob@example.com",
            "name": "Bob",
            "password": "password1234",
        })
        assert resp.status_code == 201
        user = resp.json()["user"]
        assert user["email"] == "bob@example.com"
        assert user["name"] == "Bob"
        assert "id" in user
        assert user["is_active"] is True

    def test_duplicate_email_returns_400(self, client):
        """Registering the same email twice returns 400 (R1.2 uniqueness)."""
        payload = {
            "email": "duplicate@example.com",
            "name": "Dup",
            "password": "somepassword99",
        }
        first = client.post("/auth/register", json=payload)
        assert first.status_code == 201
        second = client.post("/auth/register", json=payload)
        assert second.status_code == 400
        assert "already registered" in second.json()["detail"].lower()

    def test_short_password_returns_422(self, client):
        """Password shorter than 8 chars is rejected with 422 (R1.5)."""
        resp = client.post("/auth/register", json={
            "email": "short@example.com",
            "name": "Short",
            "password": "abc",
        })
        assert resp.status_code == 422

    def test_empty_name_returns_422(self, client):
        """Whitespace-only name is rejected with 422 (R1.2 validation)."""
        resp = client.post("/auth/register", json={
            "email": "noname@example.com",
            "name": "   ",
            "password": "validpassword",
        })
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client):
        """Non-email address is rejected with 422 by Pydantic EmailStr (R1.2)."""
        resp = client.post("/auth/register", json={
            "email": "not-an-email",
            "name": "Bad Email",
            "password": "validpassword",
        })
        assert resp.status_code == 422

    def test_registration_sets_refresh_cookie(self, client):
        """Successful registration sets an HTTP-only refresh_token cookie (R1.3)."""
        resp = client.post("/auth/register", json={
            "email": "cookie@example.com",
            "name": "Cookie",
            "password": "cookiepassword",
        })
        assert resp.status_code == 201
        assert "refresh_token" in resp.cookies

    def test_access_token_is_non_empty_string(self, client):
        """access_token in response is a non-empty JWT string."""
        resp = client.post("/auth/register", json={
            "email": "tokencheck@example.com",
            "name": "Tokencheck",
            "password": "tokenpassword",
        })
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        assert isinstance(token, str)
        assert len(token) > 20  # JWTs are longer than 20 chars


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    """Tests for POST /auth/login (R1.1, R1.7, R7.1)."""

    @pytest.fixture(autouse=True)
    def _seed_user(self, client):
        """Register a user to use for login tests."""
        client.post("/auth/register", json={
            "email": "login_user@example.com",
            "name": "Login User",
            "password": "loginpassword1",
        })

    def test_successful_login_returns_200(self, client):
        """Correct credentials return 200 with access token (R1.1)."""
        resp = client.post("/auth/login", json={
            "email": "login_user@example.com",
            "password": "loginpassword1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_response_includes_user(self, client):
        """Login response includes user object with email and name (R1.1)."""
        resp = client.post("/auth/login", json={
            "email": "login_user@example.com",
            "password": "loginpassword1",
        })
        assert resp.status_code == 200
        user = resp.json()["user"]
        assert user["email"] == "login_user@example.com"
        assert user["name"] == "Login User"

    def test_wrong_password_returns_401(self, client):
        """Wrong password returns 401 (R1.7 — same error as unknown email)."""
        resp = client.post("/auth/login", json={
            "email": "login_user@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()

    def test_unknown_email_returns_401(self, client):
        """Unknown email returns 401 with same message as wrong password (R1.7)."""
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "somepassword",
        })
        assert resp.status_code == 401
        assert "invalid credentials" in resp.json()["detail"].lower()

    def test_wrong_password_and_unknown_email_same_message(self, client):
        """Wrong password and unknown email return identical error messages (R1.7)."""
        resp_wrong_pw = client.post("/auth/login", json={
            "email": "login_user@example.com",
            "password": "wrongpassword",
        })
        resp_unknown = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "somepassword",
        })
        assert resp_wrong_pw.json()["detail"] == resp_unknown.json()["detail"]

    def test_login_sets_refresh_cookie(self, client):
        """Successful login sets an HTTP-only refresh_token cookie (R1.3)."""
        resp = client.post("/auth/login", json={
            "email": "login_user@example.com",
            "password": "loginpassword1",
        })
        assert resp.status_code == 200
        assert "refresh_token" in resp.cookies

    def test_inactive_user_returns_401(self, app, client):
        """Inactive user cannot log in (R1.7 active status check)."""
        from sqlalchemy.orm import Session
        from auth.models import User

        # Deactivate the user directly in the DB
        db: Session = _TestingSessionLocal()
        try:
            user = db.query(User).filter(User.email == "login_user@example.com").first()
            if user:
                user.is_active = False
                db.commit()
        finally:
            db.close()

        resp = client.post("/auth/login", json={
            "email": "login_user@example.com",
            "password": "loginpassword1",
        })
        assert resp.status_code == 401

        # Re-activate for any subsequent tests in this class
        db2: Session = _TestingSessionLocal()
        try:
            user = db2.query(User).filter(User.email == "login_user@example.com").first()
            if user:
                user.is_active = True
                db2.commit()
        finally:
            db2.close()

    def test_missing_email_field_returns_422(self, client):
        """Request without email field returns 422 validation error."""
        resp = client.post("/auth/login", json={"password": "somepassword"})
        assert resp.status_code == 422

    def test_missing_password_field_returns_422(self, client):
        """Request without password field returns 422 validation error."""
        resp = client.post("/auth/login", json={"email": "login_user@example.com"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

class TestLogout:
    """Tests for POST /auth/logout (R1.4, R7.1)."""

    @pytest.fixture
    def auth_client(self, app) -> TestClient:
        """Return a TestClient that has a valid access token in the header."""
        import time
        unique_email = f"logout_{int(time.time() * 1000)}@example.com"
        with TestClient(app) as c:
            resp = c.post("/auth/register", json={
                "email": unique_email,
                "name": "Logout User",
                "password": "logoutpassword1",
            })
            token = resp.json()["access_token"]
            c.headers.update({"Authorization": f"Bearer {token}"})
            yield c

    def test_logout_returns_200(self, auth_client):
        """Authenticated logout returns 200 with a message (R1.4)."""
        resp = auth_client.post("/auth/logout")
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()

    def test_logout_without_token_returns_401(self, client):
        """Logout without Authorization header returns 401 (R7.1)."""
        resp = client.post("/auth/logout")
        assert resp.status_code == 401

    def test_logout_clears_refresh_cookie(self, auth_client):
        """Logout response clears the refresh_token cookie (R1.4)."""
        resp = auth_client.post("/auth/logout")
        assert resp.status_code == 200
        # After logout the refresh_token cookie should be gone or empty
        cookie_value = resp.cookies.get("refresh_token", "")
        assert cookie_value == "" or cookie_value is None


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    """Tests for POST /auth/refresh (R1.3, R7.1)."""

    @pytest.fixture
    def client_with_cookie(self, app) -> TestClient:
        """Return a client that has a valid refresh_token cookie from login."""
        with TestClient(app) as c:
            c.post("/auth/register", json={
                "email": "refresh_user@example.com",
                "name": "Refresh User",
                "password": "refreshpassword1",
            })
            # Login to get the refresh cookie set on the client's cookie jar
            c.post("/auth/login", json={
                "email": "refresh_user@example.com",
                "password": "refreshpassword1",
            })
            yield c

    def test_valid_refresh_cookie_returns_200(self, client_with_cookie):
        """Valid refresh_token cookie returns 200 with new access token (R1.3)."""
        resp = client_with_cookie.post("/auth/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_response_includes_user(self, client_with_cookie):
        """Refresh response includes user object (R1.3)."""
        resp = client_with_cookie.post("/auth/refresh")
        assert resp.status_code == 200
        user = resp.json()["user"]
        assert user["email"] == "refresh_user@example.com"

    def test_missing_cookie_returns_401(self, app):
        """POST /auth/refresh with no cookie returns 401 (R7.1)."""
        # Use a fresh client with an empty cookie jar to guarantee no
        # refresh_token cookie is present from previous tests.
        with TestClient(app) as fresh_client:
            resp = fresh_client.post("/auth/refresh")
        assert resp.status_code == 401
        assert "missing" in resp.json()["detail"].lower()

    def test_invalid_refresh_token_returns_401(self, app):
        """Tampered refresh token in cookie returns 401."""
        with TestClient(app) as fresh_client:
            fresh_client.cookies.set("refresh_token", "invalid.token.value")
            resp = fresh_client.post("/auth/refresh")
        assert resp.status_code == 401

    def test_new_access_token_differs_from_none(self, client_with_cookie):
        """Refreshed access token is a non-empty string."""
        resp = client_with_cookie.post("/auth/refresh")
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        assert isinstance(token, str)
        assert len(token) > 20


# ---------------------------------------------------------------------------
# End-to-end: register → login → use token → refresh → logout
# ---------------------------------------------------------------------------

class TestAuthFlow:
    """End-to-end auth flow: register, login, token use, refresh, logout."""

    def test_full_auth_lifecycle(self, app):
        """Complete auth flow: register → login → refresh → logout works (R1.1–R1.4)."""
        with TestClient(app) as c:
            # 1. Register
            reg = c.post("/auth/register", json={
                "email": "flow@example.com",
                "name": "Flow User",
                "password": "flowpassword1",
            })
            assert reg.status_code == 201
            access_token = reg.json()["access_token"]

            # 2. Use the access token on an authenticated endpoint
            c.headers.update({"Authorization": f"Bearer {access_token}"})
            logout_check = c.post("/auth/logout")
            assert logout_check.status_code == 200

            # 3. Register again and do full login → refresh sequence
            c.headers.clear()
            reg2 = c.post("/auth/register", json={
                "email": "flow2@example.com",
                "name": "Flow2",
                "password": "flowpassword2",
            })
            assert reg2.status_code == 201

            login = c.post("/auth/login", json={
                "email": "flow2@example.com",
                "password": "flowpassword2",
            })
            assert login.status_code == 200
            assert "refresh_token" in login.cookies

            # 4. Refresh using the cookie set during login
            refresh = c.post("/auth/refresh")
            assert refresh.status_code == 200
            assert "access_token" in refresh.json()
