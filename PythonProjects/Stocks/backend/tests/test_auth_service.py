"""
Unit tests for backend/auth/service.py.

Tests cover:
- Password hashing and verification
- Access token creation and decoding
- Refresh token creation and decoding
- Invalid / expired token handling
"""

import sys
import os
from datetime import timedelta
from uuid import UUID

import pytest
from jose import JWTError

# Make backend/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth.service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_is_not_plain_text(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"

    def test_hash_starts_with_bcrypt_marker(self):
        hashed = hash_password("mysecretpassword")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_verify_correct_password(self):
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_plain_produces_different_hashes(self):
        """bcrypt uses random salts — two hashes must differ."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_hash_then_verify_roundtrip(self):
        password = "P@ssw0rd!1234"
        assert verify_password(password, hash_password(password)) is True


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------


class TestAccessToken:
    USER_ID = "11111111-1111-1111-1111-111111111111"
    EMAIL = "user@example.com"

    def _claims(self):
        return {"sub": self.USER_ID, "email": self.EMAIL}

    def test_create_returns_string(self):
        tok = create_access_token(self._claims(), timedelta(minutes=15))
        assert isinstance(tok, str) and len(tok) > 0

    def test_decode_returns_token_data(self):
        tok = create_access_token(self._claims(), timedelta(minutes=15))
        td = decode_token(tok, settings.secret_key)
        assert str(td.user_id) == self.USER_ID
        assert td.email == self.EMAIL

    def test_expired_token_raises(self):
        tok = create_access_token(self._claims(), timedelta(seconds=-1))
        with pytest.raises(JWTError):
            decode_token(tok, settings.secret_key)

    def test_wrong_secret_raises(self):
        tok = create_access_token(self._claims(), timedelta(minutes=15))
        with pytest.raises(JWTError):
            decode_token(tok, "totally-wrong-secret")

    def test_tampered_token_raises(self):
        tok = create_access_token(self._claims(), timedelta(minutes=15))
        tampered = tok[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered, settings.secret_key)

    def test_user_id_is_uuid(self):
        tok = create_access_token(self._claims(), timedelta(minutes=15))
        td = decode_token(tok, settings.secret_key)
        assert isinstance(td.user_id, UUID)


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------


class TestRefreshToken:
    USER_ID = "22222222-2222-2222-2222-222222222222"
    EMAIL = "refresh@example.com"
    REFRESH_SECRET = settings.secret_key + "_refresh"

    def _claims(self):
        return {"sub": self.USER_ID, "email": self.EMAIL}

    def test_create_returns_string(self):
        tok = create_refresh_token(self._claims(), timedelta(days=30))
        assert isinstance(tok, str) and len(tok) > 0

    def test_decode_returns_token_data(self):
        tok = create_refresh_token(self._claims(), timedelta(days=30))
        td = decode_token(tok, self.REFRESH_SECRET)
        assert str(td.user_id) == self.USER_ID
        assert td.email == self.EMAIL

    def test_refresh_and_access_are_different_tokens(self):
        claims = self._claims()
        access = create_access_token(claims, timedelta(minutes=480))
        refresh = create_refresh_token(claims, timedelta(days=30))
        assert access != refresh

    def test_access_secret_cannot_decode_refresh(self):
        """Refresh token is signed with a different secret."""
        tok = create_refresh_token(self._claims(), timedelta(days=30))
        with pytest.raises(JWTError):
            decode_token(tok, settings.secret_key)  # wrong secret

    def test_expired_refresh_raises(self):
        tok = create_refresh_token(self._claims(), timedelta(seconds=-1))
        with pytest.raises(JWTError):
            decode_token(tok, self.REFRESH_SECRET)
