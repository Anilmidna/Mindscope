"""
Razorpay payment service.

Handles order creation and payment signature verification.
"""
import hashlib
import hmac
import logging
import uuid

import razorpay
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.payment import Payment
from app.models.session import AssessmentSession

logger = logging.getLogger(__name__)

REPORT_PRICE_PAISE = 19900  # ₹199 in paise


def _razorpay_client() -> razorpay.Client:
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def create_order(db: Session, user_id: uuid.UUID, session_id: uuid.UUID) -> Payment:
    """
    Create a Razorpay order and persist a Payment row with status='created'.
    Raises ValueError if session not found or already paid.
    """
    session = db.query(AssessmentSession).filter(
        AssessmentSession.id == session_id,
        AssessmentSession.user_id == user_id,
    ).first()
    if not session:
        raise ValueError("Session not found")

    existing = db.query(Payment).filter(
        Payment.session_id == session_id,
        Payment.status == "paid",
    ).first()
    if existing:
        raise ValueError("Session already paid")

    client = _razorpay_client()
    order = client.order.create({
        "amount": REPORT_PRICE_PAISE,
        "currency": "INR",
        "receipt": str(session_id),
    })

    payment = Payment(
        user_id=user_id,
        session_id=session_id,
        razorpay_order_id=order["id"],
        amount=REPORT_PRICE_PAISE,
        currency="INR",
        status="created",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info("Payment order created", extra={
        "session_id": str(session_id),
        "order_id": order["id"],
    })
    return payment


def verify_payment(
    db: Session,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> Payment:
    """
    Verify Razorpay webhook signature and mark payment as paid.
    Raises ValueError on signature mismatch or order not found.
    """
    payment = db.query(Payment).filter(
        Payment.razorpay_order_id == razorpay_order_id
    ).first()
    if not payment:
        raise ValueError("Order not found")

    # Razorpay signature = HMAC-SHA256(order_id + "|" + payment_id, secret)
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        payment.status = "failed"
        db.commit()
        raise ValueError("Invalid payment signature")

    payment.razorpay_payment_id = razorpay_payment_id
    payment.status = "paid"
    db.commit()
    db.refresh(payment)
    logger.info("Payment verified", extra={
        "session_id": str(payment.session_id),
        "payment_id": razorpay_payment_id,
    })
    return payment


def get_payment_status(db: Session, session_id: uuid.UUID) -> Payment | None:
    """Return the most recent payment for a session, or None."""
    return (
        db.query(Payment)
        .filter(Payment.session_id == session_id)
        .order_by(Payment.created_at.desc())
        .first()
    )
