import uuid
from sqlalchemy import Column, String, Integer, Uuid, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class SectionTimer(Base):
    """Tracks server-side start time per aptitude section per session."""
    __tablename__ = "section_timers"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    domain = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    time_limit_seconds = Column(Integer, nullable=False)

    session = relationship("AssessmentSession")
