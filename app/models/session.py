import uuid
from sqlalchemy import Column, String, DateTime, Uuid, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class AssessmentSession(Base):
    __tablename__ = "sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    context_of_origin = Column(String(50), nullable=False)
    flow_type = Column(String(20), nullable=False, default="b2c")   # b2c | b2b
    persona_tag = Column(String(20), nullable=True)                 # student | professional
    status = Column(String(50), nullable=False, default="started")
    norm_group_id = Column(String(50), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    scoring_engine_version = Column(String(20), nullable=True)

    user = relationship("User", back_populates="sessions")
    responses = relationship("Response", back_populates="session")
    intake = relationship("IntakeForm", back_populates="session", uselist=False)
