import uuid
from sqlalchemy import Column, String, Text, Uuid, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), unique=True, nullable=False)
    s3_url = Column(Text, nullable=True)
    prompt_template_version = Column(String(20), nullable=True)
    llm_model = Column(String(100), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    template_name = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("AssessmentSession")
