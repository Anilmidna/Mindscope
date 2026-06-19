import uuid
from sqlalchemy import Column, String, Float, Uuid, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), unique=True, nullable=False)

    riasec_r = Column(Float, nullable=True)
    riasec_i = Column(Float, nullable=True)
    riasec_a = Column(Float, nullable=True)
    riasec_s = Column(Float, nullable=True)
    riasec_e = Column(Float, nullable=True)
    riasec_c = Column(Float, nullable=True)

    ocean_o = Column(Float, nullable=True)
    ocean_c = Column(Float, nullable=True)
    ocean_e = Column(Float, nullable=True)
    ocean_a = Column(Float, nullable=True)
    ocean_n = Column(Float, nullable=True)

    apt_logical = Column(Float, nullable=True)
    apt_numerical = Column(Float, nullable=True)
    apt_verbal = Column(Float, nullable=True)
    apt_spatial = Column(Float, nullable=True)

    percentiles = Column(JSON, nullable=True)
    scoring_engine_version = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("AssessmentSession")
