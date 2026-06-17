from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class NormGroup(Base):
    __tablename__ = "norm_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    context = Column(String(50), nullable=False)
    label = Column(String(100), nullable=False)
    sample_size = Column(Integer, nullable=True)
    score_stats = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
