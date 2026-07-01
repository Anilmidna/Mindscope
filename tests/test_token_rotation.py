"""Tests for refresh token rotation (H1)."""
import pytest

from app.core.security import create_refresh_token, decode_token
from app.models.user import User
from app.models.token_blocklist import RefreshTokenBlocklist
import uuid


def _make_user(db) -> User:
    user = User(google_sub=str(uuid.uuid4()), email="rotate@example.com", name="Rotate User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestTokenRotation:
    def test_refresh_returns_new_access_token_and_sets_cookie(self, client, db):
        user = _make_user(db)
        old_refresh = create_refresh_token(str(user.id))

        res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        # New refresh token is in cookie, not body
        assert "Set-Cookie" in res.headers

    def test_old_refresh_token_blocklisted_after_use(self, client, db):
        user = _make_user(db)
        old_refresh = create_refresh_token(str(user.id))

        res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res.status_code == 200

        # Old token should now be rejected
        res2 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res2.status_code == 401

    def test_reuse_of_old_refresh_token_returns_401(self, client, db):
        user = _make_user(db)
        old_refresh = create_refresh_token(str(user.id))

        # First use — legitimate rotation
        res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res.status_code == 200

        # Second use of old token — reuse detected
        res2 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res2.status_code == 401

    def test_reuse_detection_logs_warning(self, client, db, caplog):
        import logging
        user = _make_user(db)
        old_refresh = create_refresh_token(str(user.id))

        client.post("/auth/refresh", json={"refresh_token": old_refresh})

        with caplog.at_level(logging.WARNING, logger="app.routers.auth"):
            res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert res.status_code == 401
        assert "refresh_token_reuse_detected" in caplog.text
