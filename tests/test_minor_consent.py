"""Tests for minor consent flow (D2 — DPDP §9)."""
import uuid
from datetime import date, timedelta

import pytest

from app.core.security import create_access_token
from app.models.user import User
from app.models.session import AssessmentSession


def _make_user(db) -> User:
    user = User(google_sub=str(uuid.uuid4()), email="minor@example.com", name="Minor Test")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_session(db, user_id: uuid.UUID) -> AssessmentSession:
    session = AssessmentSession(
        user_id=user_id,
        context_of_origin="standalone-public",
        status="started",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _auth_headers(user: User) -> dict:
    token = create_access_token(str(user.id), user.email)
    return {"Authorization": f"Bearer {token}"}


def _dob(years_ago: int) -> str:
    return (date.today().replace(year=date.today().year - years_ago)).isoformat()


def _intake_payload(**overrides) -> dict:
    base = {
        "life_stage": "Undergraduate Student",
        "future_goals": "Test goals",
        "satisfaction": 7,
        "consent_given_at": "2026-07-01T10:00:00Z",
    }
    base.update(overrides)
    return base


class TestMinorConsent:
    def test_adult_user_no_dob_normal_flow(self, client, db):
        user = _make_user(db)
        session = _make_session(db, user.id)

        res = client.post(
            f"/sessions/{session.id}/intake",
            headers=_auth_headers(user),
            json=_intake_payload(),
        )
        assert res.status_code == 200

    def test_adult_18_plus_with_dob(self, client, db):
        user = _make_user(db)
        session = _make_session(db, user.id)

        res = client.post(
            f"/sessions/{session.id}/intake",
            headers=_auth_headers(user),
            json=_intake_payload(date_of_birth=_dob(20)),
        )
        assert res.status_code == 200

    def test_minor_16_17_with_parent_email_accepted(self, client, db):
        user = _make_user(db)
        session = _make_session(db, user.id)

        res = client.post(
            f"/sessions/{session.id}/intake",
            headers=_auth_headers(user),
            json=_intake_payload(
                date_of_birth=_dob(17),
                parent_email="parent@example.com",
            ),
        )
        assert res.status_code == 200

    def test_minor_16_17_without_parent_email_rejected(self, client, db):
        user = _make_user(db)
        session = _make_session(db, user.id)

        res = client.post(
            f"/sessions/{session.id}/intake",
            headers=_auth_headers(user),
            json=_intake_payload(date_of_birth=_dob(16)),
        )
        assert res.status_code == 400
        assert "parent" in res.json()["detail"].lower()

    def test_under_16_rejected_with_403(self, client, db):
        user = _make_user(db)
        session = _make_session(db, user.id)

        res = client.post(
            f"/sessions/{session.id}/intake",
            headers=_auth_headers(user),
            json=_intake_payload(date_of_birth=_dob(14)),
        )
        assert res.status_code == 403
        assert "under 16" in res.json()["detail"].lower()
