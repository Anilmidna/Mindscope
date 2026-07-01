"""Tests for payment ownership checks (C3)."""
import uuid

import pytest

from app.core.security import create_access_token
from app.models.payment import Payment
from app.models.user import User


def _make_user(db, *, email="user@example.com") -> User:
    user = User(
        google_sub=str(uuid.uuid4()),
        email=email,
        name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token(str(user.id), user.email)
    return {"Authorization": f"Bearer {token}"}


def _make_payment(db, user_id: uuid.UUID, session_id: uuid.UUID = None) -> Payment:
    sid = session_id or uuid.uuid4()
    payment = Payment(
        user_id=user_id,
        session_id=sid,
        razorpay_order_id=f"order_{uuid.uuid4().hex[:12]}",
        amount=19900,
        currency="INR",
        status="created",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


class TestPaymentOwnership:
    def test_user_cannot_verify_another_users_payment(self, client, db):
        user_a = _make_user(db, email="a@example.com")
        user_b = _make_user(db, email="b@example.com")
        payment = _make_payment(db, user_a.id)

        # User B tries to verify User A's payment
        res = client.post(
            "/payments/verify",
            json={
                "razorpay_order_id": payment.razorpay_order_id,
                "razorpay_payment_id": "pay_fake123",
                "razorpay_signature": "bad_sig",
            },
            headers=_auth_headers(user_b),
        )
        assert res.status_code == 403
        assert "Not your payment" in res.json()["detail"]

    def test_user_cannot_query_another_users_payment_status(self, client, db):
        user_a = _make_user(db, email="c@example.com")
        user_b = _make_user(db, email="d@example.com")
        session_id = uuid.uuid4()
        _make_payment(db, user_a.id, session_id=session_id)

        # User B tries to see User A's payment status
        res = client.get(f"/payments/status/{session_id}", headers=_auth_headers(user_b))
        assert res.status_code == 403

    def test_user_can_query_own_payment_status(self, client, db):
        user = _make_user(db, email="e@example.com")
        session_id = uuid.uuid4()
        _make_payment(db, user.id, session_id=session_id)

        res = client.get(f"/payments/status/{session_id}", headers=_auth_headers(user))
        assert res.status_code == 200
        assert res.json()["status"] in ("created", "paid", "failed")
