import uuid
from sqlalchemy import Column, String, Integer, Text, Uuid, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class IntakeForm(Base):
    __tablename__ = "intake_forms"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), unique=True, nullable=False)
    life_stage = Column(String(100), nullable=True)
    current_role = Column(String(200), nullable=True)
    current_field = Column(String(200), nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)
    goals = Column(Text, nullable=True)
    challenges = Column(Text, nullable=True)
    background_tags = Column(String(500), nullable=True)
    years_of_experience = Column(String(50), nullable=True)
    highest_education = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("AssessmentSession", back_populates="intake")
