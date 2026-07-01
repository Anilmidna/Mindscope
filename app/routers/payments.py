"""
Payment endpoints.

POST /payments/create-order   — create Razorpay order for a session (B2C only)
POST /payments/verify         — verify payment signature + mark session paid
GET  /payments/status/{id}    — check payment status for a session
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.payment import (
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentStatusResponse,
    VerifyPaymentRequest,
)
from app.services.payment_service import (
    create_order,
    get_payment_status,
    verify_payment,
    REPORT_PRICE_PAISE,
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-order", response_model=CreateOrderResponse)
def create_payment_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        payment = create_order(db, current_user.id, body.session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CreateOrderResponse(
        order_id=payment.razorpay_order_id,
        amount=payment.amount,
        currency=payment.currency,
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify")
def verify_payment_endpoint(
    body: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        payment = verify_payment(
            db,
            body.razorpay_order_id,
            body.razorpay_payment_id,
            body.razorpay_signature,
            current_user_id=current_user.id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"status": "paid", "session_id": str(payment.session_id)}


@router.get("/status/{session_id}", response_model=PaymentStatusResponse)
def payment_status(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = get_payment_status(db, session_id)
    if not payment:
        return PaymentStatusResponse(session_id=session_id, status="unpaid")
    if payment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your payment")
    return PaymentStatusResponse(
        session_id=session_id,
        status=payment.status,
        amount=payment.amount,
    )
