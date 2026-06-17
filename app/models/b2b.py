import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Uuid, ForeignKey, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class B2BLicense(Base):
    __tablename__ = "b2b_licenses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_name = Column(String(200), nullable=False)
    context_of_origin = Column(String(50), nullable=False)
    total_licenses = Column(Integer, nullable=False)
    used_licenses = Column(Integer, nullable=False, default=0)
    invite_code = Column(String(64), unique=True, nullable=False)
    created_by = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user_licenses = relationship("UserLicense", back_populates="license")


class UserLicense(Base):
    __tablename__ = "user_licenses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    license_id = Column(Uuid(as_uuid=True), ForeignKey("b2b_licenses.id"), nullable=False)
    activated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    license = relationship("B2BLicense", back_populates="user_licenses")
