import uuid
from sqlalchemy import Column, String, Integer, Uuid, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Response(Base):
    __tablename__ = "responses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    item_id = Column(String(50), nullable=False)
    answer = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    domain = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("AssessmentSession", back_populates="responses")
