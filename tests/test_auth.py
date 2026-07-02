"""
Unit tests for the auth flow — Day 4 sprint requirement.

Cases covered:
  1. Happy path — valid refresh token returns new access token
  2. Expired token — refresh with expired token is rejected (401)
  3. Bad signature — tampered token is rejected (401)
  4. Logout then refresh — blocklisted token is rejected (401)
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import jwt

from app.core.config import settings
from app.core.security import create_refresh_token
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db) -> User:
    user = User(
        google_sub="google-sub-test",
        email="test@example.com",
        name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_expired_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        "iat": datetime.now(timezone.utc) - timedelta(days=8),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _make_bad_signature_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, "wrong-secret-key", algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRefreshHappyPath:
    def test_valid_refresh_token_returns_new_access_token(self, client, db):
        user = _make_user(db)
        refresh_token = create_refresh_token(user_id=str(user.id))

        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_access_token_contains_correct_claims(self, client, db):
        user = _make_user(db)
        refresh_token = create_refresh_token(user_id=str(user.id))

        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

        access_token = response.json()["access_token"]
        claims = jwt.decode(
            access_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert claims["sub"] == str(user.id)
        assert claims["email"] == user.email
        assert claims["type"] == "access"


class TestExpiredToken:
    def test_expired_refresh_token_returns_401(self, client, db):
        user = _make_user(db)
        expired_token = _make_expired_refresh_token(str(user.id))

        response = client.post("/auth/refresh", json={"refresh_token": expired_token})

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

    def test_expired_token_rejected_by_logout(self, client, db):
        user = _make_user(db)
        expired_token = _make_expired_refresh_token(str(user.id))

        response = client.post("/auth/logout", json={"refresh_token": expired_token})

        assert response.status_code == 401


class TestBadSignature:
    def test_tampered_token_returns_401_on_refresh(self, client, db):
        user = _make_user(db)
        bad_token = _make_bad_signature_token(str(user.id))

        response = client.post("/auth/refresh", json={"refresh_token": bad_token})

        assert response.status_code == 401

    def test_tampered_token_returns_401_on_logout(self, client, db):
        user = _make_user(db)
        bad_token = _make_bad_signature_token(str(user.id))

        response = client.post("/auth/logout", json={"refresh_token": bad_token})

        assert response.status_code == 401


class TestLogoutThenRefresh:
    def test_logout_returns_204(self, client, db):
        user = _make_user(db)
        refresh_token = create_refresh_token(user_id=str(user.id))

        response = client.post("/auth/logout", json={"refresh_token": refresh_token})

        assert response.status_code == 204

    def test_refresh_after_logout_returns_401(self, client, db):
        user = _make_user(db)
        refresh_token = create_refresh_token(user_id=str(user.id))

        client.post("/auth/logout", json={"refresh_token": refresh_token})
        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "revoked" in detail or "reuse" in detail

    def test_logout_is_idempotent(self, client, db):
        user = _make_user(db)
        refresh_token = create_refresh_token(user_id=str(user.id))

        r1 = client.post("/auth/logout", json={"refresh_token": refresh_token})
        r2 = client.post("/auth/logout", json={"refresh_token": refresh_token})

        assert r1.status_code == 204
        assert r2.status_code == 204
