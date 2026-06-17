from sqlalchemy import Column, Boolean, Float, Uuid, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class BiasFlag(Base):
    __tablename__ = "bias_flags"

    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id"), primary_key=True)
    attention_check_result = Column(Boolean, nullable=True)
    social_desirability_score = Column(Float, nullable=True)
    response_time_outlier_flag = Column(Boolean, nullable=True)
    flagged_for_review = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("AssessmentSession")
