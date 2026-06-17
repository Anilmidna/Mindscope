import uuid
from sqlalchemy import Column, String, DateTime, Uuid, func

from app.db.session import Base


class RefreshTokenBlocklist(Base):
    __tablename__ = "refresh_token_blocklist"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    blocked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
