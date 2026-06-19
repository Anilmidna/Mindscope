"""Unit tests for B2B invite validation and activation — Day 7 requirement."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import create_access_token
from app.models.b2b import B2BLicense, UserLicense
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db, *, email="user@example.com", google_sub=None) -> User:
    user = User(
        google_sub=google_sub or str(uuid.uuid4()),
        email=email,
        name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_org(db, *, total=5, used=0, is_active=True, expires_at=None) -> B2BLicense:
    org = B2BLicense(
        org_name="Acme Corp",
        context_of_origin="b2b-partner",
        total_licenses=total,
        used_licenses=used,
        invite_code="test-invite-code-abc",
        is_active=is_active,
        expires_at=expires_at,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _auth_headers(user: User) -> dict:
    token = create_access_token(str(user.id), user.email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /b2b/create-org
# ---------------------------------------------------------------------------

class TestCreateOrg:
    def test_creates_org_with_invite_code(self, client, db):
        res = client.post("/b2b/create-org", json={
            "org_name": "TATA Consultancy",
            "context_of_origin": "b2b-partner",
            "total_licenses": 10,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["org_name"] == "TATA Consultancy"
        assert data["total_licenses"] == 10
        assert data["used_licenses"] == 0
        assert data["licenses_remaining"] == 10
        assert len(data["invite_code"]) > 10
        assert data["is_active"] is True

    def test_rejects_invalid_context(self, client):
        res = client.post("/b2b/create-org", json={
            "org_name": "Bad Corp",
            "context_of_origin": "not-a-real-context",
            "total_licenses": 5,
        })
        assert res.status_code == 422

    def test_rejects_zero_licenses(self, client):
        res = client.post("/b2b/create-org", json={
            "org_name": "Empty Corp",
            "context_of_origin": "b2b-partner",
            "total_licenses": 0,
        })
        assert res.status_code == 422

    def test_invite_code_is_unique_per_org(self, client):
        def create():
            return client.post("/b2b/create-org", json={
                "org_name": "Org",
                "context_of_origin": "b2b-partner",
                "total_licenses": 1,
            }).json()["invite_code"]
        assert create() != create()


# ---------------------------------------------------------------------------
# GET /b2b/validate-invite
# ---------------------------------------------------------------------------

class TestValidateInvite:
    def test_valid_invite(self, client, db):
        _make_org(db)
        res = client.get("/b2b/validate-invite", params={"code": "test-invite-code-abc"})
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["org_name"] == "Acme Corp"
        assert data["licenses_remaining"] == 5

    def test_invalid_code(self, client, db):
        res = client.get("/b2b/validate-invite", params={"code": "does-not-exist"})
        assert res.status_code == 404

    def test_inactive_org(self, client, db):
        _make_org(db, is_active=False)
        res = client.get("/b2b/validate-invite", params={"code": "test-invite-code-abc"})
        assert res.status_code == 410

    def test_expired_invite(self, client, db):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        _make_org(db, expires_at=past)
        res = client.get("/b2b/validate-invite", params={"code": "test-invite-code-abc"})
        assert res.status_code == 410

    def test_fully_used_licenses(self, client, db):
        _make_org(db, total=2, used=2)
        res = client.get("/b2b/validate-invite", params={"code": "test-invite-code-abc"})
        assert res.status_code == 409

    def test_future_expiry_is_valid(self, client, db):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        _make_org(db, expires_at=future)
        res = client.get("/b2b/validate-invite", params={"code": "test-invite-code-abc"})
        assert res.status_code == 200


# ---------------------------------------------------------------------------
# POST /b2b/activate-invite
# ---------------------------------------------------------------------------

class TestActivateInvite:
    def test_activate_tags_user_as_b2b(self, client, db):
        user = _make_user(db)
        _make_org(db)
        res = client.post(
            "/b2b/activate-invite",
            params={"code": "test-invite-code-abc"},
            headers=_auth_headers(user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["activated"] is True
        assert data["account_type"] == "b2b"
        assert data["org_name"] == "Acme Corp"

    def test_activate_decrements_license_count(self, client, db):
        user = _make_user(db)
        org = _make_org(db, total=5, used=0)
        client.post(
            "/b2b/activate-invite",
            params={"code": "test-invite-code-abc"},
            headers=_auth_headers(user),
        )
        db.refresh(org)
        assert org.used_licenses == 1

    def test_double_activation_rejected(self, client, db):
        user = _make_user(db)
        _make_org(db)
        headers = _auth_headers(user)
        first = client.post("/b2b/activate-invite",
                            params={"code": "test-invite-code-abc"},
                            headers=headers)
        assert first.status_code == 200
        second = client.post("/b2b/activate-invite",
                             params={"code": "test-invite-code-abc"},
                             headers=headers)
        assert second.status_code == 409

    def test_activate_last_license(self, client, db):
        user = _make_user(db)
        _make_org(db, total=1, used=0)
        res = client.post(
            "/b2b/activate-invite",
            params={"code": "test-invite-code-abc"},
            headers=_auth_headers(user),
        )
        assert res.status_code == 200

    def test_activate_when_no_licenses_left(self, client, db):
        user = _make_user(db)
        _make_org(db, total=1, used=1)
        res = client.post(
            "/b2b/activate-invite",
            params={"code": "test-invite-code-abc"},
            headers=_auth_headers(user),
        )
        assert res.status_code == 409

    def test_activate_requires_auth(self, client, db):
        _make_org(db)
        res = client.post("/b2b/activate-invite",
                          params={"code": "test-invite-code-abc"})
        # HTTPBearer returns 403 (not 401) when Authorization header is absent
        assert res.status_code in (401, 403)

    def test_activate_invalid_code(self, client, db):
        user = _make_user(db)
        res = client.post(
            "/b2b/activate-invite",
            params={"code": "wrong-code"},
            headers=_auth_headers(user),
        )
        assert res.status_code == 404

    def test_creates_user_license_record(self, client, db):
        user = _make_user(db)
        org = _make_org(db)
        client.post(
            "/b2b/activate-invite",
            params={"code": "test-invite-code-abc"},
            headers=_auth_headers(user),
        )
        ul = db.query(UserLicense).filter(
            UserLicense.user_id == user.id,
            UserLicense.license_id == org.id,
        ).first()
        assert ul is not None


# ---------------------------------------------------------------------------
# POST /b2b/generate-invites/{org_id} — regenerate invite code
# ---------------------------------------------------------------------------

class TestRegenerateInvite:
    def test_new_code_is_different(self, client, db):
        org = _make_org(db)
        old_code = org.invite_code
        res = client.post(f"/b2b/generate-invites/{org.id}")
        assert res.status_code == 200
        assert res.json()["invite_code"] != old_code

    def test_old_code_no_longer_valid(self, client, db):
        org = _make_org(db)
        old_code = org.invite_code
        client.post(f"/b2b/generate-invites/{org.id}")
        # Old code should now be 404
        res = client.get("/b2b/validate-invite", params={"code": old_code})
        assert res.status_code == 404

    def test_nonexistent_org_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        res = client.post(f"/b2b/generate-invites/{fake_id}")
        assert res.status_code == 404
