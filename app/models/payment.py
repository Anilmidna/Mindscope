import uuid
from sqlalchemy import Column, String, Integer, DateTime, Uuid, ForeignKey, func

from app.db.session import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    amount = Column(Integer, nullable=False)       # in paise (₹199 = 19900)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="created")  # created | paid | failed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
