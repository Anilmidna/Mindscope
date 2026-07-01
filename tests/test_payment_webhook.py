"""Tests for Razorpay webhook endpoint (C4)."""
import hashlib
import hmac
import json
import uuid

import pytest

from app.models.payment import Payment
from app.models.user import User
from app.core.config import settings


_WEBHOOK_SECRET = "test_webhook_secret_abc123"


def _make_user(db) -> User:
    user = User(google_sub=str(uuid.uuid4()), email="webhook@example.com", name="W User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_payment(db, user_id: uuid.UUID, order_id: str, status: str = "created") -> Payment:
    session_id = uuid.uuid4()
    payment = Payment(
        user_id=user_id,
        session_id=session_id,
        razorpay_order_id=order_id,
        amount=19900,
        currency="INR",
        status=status,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _webhook_payload(event: str, order_id: str, payment_id: str = "pay_test123") -> dict:
    return {
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                }
            }
        },
    }


class TestRazorpayWebhook:
    def test_payment_captured_marks_paid(self, client, db, monkeypatch):
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", _WEBHOOK_SECRET)
        user = _make_user(db)
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        _make_payment(db, user.id, order_id)

        body = json.dumps(_webhook_payload("payment.captured", order_id)).encode()
        sig = _sign(body, _WEBHOOK_SECRET)

        res = client.post(
            "/payments/webhook",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert res.status_code == 200

        payment = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
        db.refresh(payment)
        assert payment.status == "paid"
        assert payment.razorpay_payment_id == "pay_test123"

    def test_payment_captured_already_paid_is_idempotent(self, client, db, monkeypatch):
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", _WEBHOOK_SECRET)
        user = _make_user(db)
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        _make_payment(db, user.id, order_id, status="paid")

        body = json.dumps(_webhook_payload("payment.captured", order_id)).encode()
        sig = _sign(body, _WEBHOOK_SECRET)

        res = client.post(
            "/payments/webhook",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert res.status_code == 200

    def test_invalid_signature_returns_400(self, client, db, monkeypatch):
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", _WEBHOOK_SECRET)
        user = _make_user(db)
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        _make_payment(db, user.id, order_id)

        body = json.dumps(_webhook_payload("payment.captured", order_id)).encode()

        res = client.post(
            "/payments/webhook",
            content=body,
            headers={"X-Razorpay-Signature": "bad_signature", "Content-Type": "application/json"},
        )
        assert res.status_code == 400

    def test_unknown_order_id_returns_200(self, client, db, monkeypatch):
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", _WEBHOOK_SECRET)
        order_id = "order_nonexistent"

        body = json.dumps(_webhook_payload("payment.captured", order_id)).encode()
        sig = _sign(body, _WEBHOOK_SECRET)

        res = client.post(
            "/payments/webhook",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert res.status_code == 200

    def test_payment_failed_sets_failed_status(self, client, db, monkeypatch):
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", _WEBHOOK_SECRET)
        user = _make_user(db)
        order_id = f"order_{uuid.uuid4().hex[:12]}"
        _make_payment(db, user.id, order_id)

        body = json.dumps(_webhook_payload("payment.failed", order_id)).encode()
        sig = _sign(body, _WEBHOOK_SECRET)

        res = client.post(
            "/payments/webhook",
            content=body,
            headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"},
        )
        assert res.status_code == 200

        payment = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
        db.refresh(payment)
        assert payment.status == "failed"
