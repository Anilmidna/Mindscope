"""Tests for HttpOnly cookie auth (H3)."""
import uuid

import pytest

from app.core.security import create_refresh_token
from app.models.user import User


def _make_user(db) -> User:
    user = User(google_sub=str(uuid.uuid4()), email="cookie@example.com", name="Cookie User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestHttpOnlyCookie:
    def test_refresh_via_body_returns_access_token(self, client, db):
        """Body-based refresh (test path) still works."""
        user = _make_user(db)
        token = create_refresh_token(str(user.id))

        res = client.post("/auth/refresh", json={"refresh_token": token})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_refresh_sets_httponly_cookie(self, client, db):
        user = _make_user(db)
        token = create_refresh_token(str(user.id))

        res = client.post("/auth/refresh", json={"refresh_token": token})
        assert res.status_code == 200
        set_cookie = res.headers.get("Set-Cookie", "")
        assert "refresh_token" in set_cookie
        assert "HttpOnly" in set_cookie

    def test_refresh_via_cookie_returns_200(self, client, db):
        """Cookie-based refresh (production path)."""
        user = _make_user(db)
        token = create_refresh_token(str(user.id))

        res = client.post(
            "/auth/refresh",
            json={},
            cookies={"refresh_token": token},
        )
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_refresh_without_cookie_or_body_returns_401(self, client, db):
        res = client.post("/auth/refresh", json={})
        assert res.status_code == 401

    def test_logout_clears_cookie(self, client, db):
        user = _make_user(db)
        token = create_refresh_token(str(user.id))

        res = client.post("/auth/logout", json={"refresh_token": token})
        assert res.status_code == 204
        # Logout response should delete the cookie
        set_cookie = res.headers.get("Set-Cookie", "")
        assert "refresh_token" in set_cookie
