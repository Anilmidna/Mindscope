from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class CreateOrderRequest(BaseModel):
    session_id: UUID


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int        # paise
    currency: str
    key_id: str        # Razorpay public key — needed by frontend to init checkout


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentStatusResponse(BaseModel):
    session_id: UUID
    status: str        # created | paid | failed
    amount: Optional[int] = None

    class Config:
        from_attributes = True
