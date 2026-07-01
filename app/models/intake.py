import uuid
from sqlalchemy import Column, String, Integer, Text, Uuid, ForeignKey, DateTime, Date, Boolean, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class IntakeForm(Base):
    __tablename__ = "intake_forms"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), unique=True, nullable=False)

    # Determines RIASEC bank: "student" or "professional"
    life_stage = Column(String(100), nullable=False)
    persona = Column(String(20), nullable=False)  # "student" | "professional"

    domain = Column(String(200), nullable=True)          # field of study/work
    specialization = Column(String(100), nullable=True)  # free text job title / major
    future_goals = Column(Text, nullable=True)           # capped 200 chars
    satisfaction = Column(Integer, nullable=True)        # 1-10 slider
    challenges = Column(Text, nullable=True)             # capped 200 chars
    education_level = Column(String(100), nullable=True)
    preferred_work_style = Column(String(100), nullable=True)

    consent_given_at = Column(DateTime(timezone=True), nullable=False)

    # DPDP §9 minor consent
    date_of_birth = Column(Date, nullable=True)
    parent_email = Column(String(254), nullable=True)
    minor_consent_pending = Column(Boolean, nullable=True, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("AssessmentSession", back_populates="intake")
