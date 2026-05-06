from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base

class DigitalAsset(Base):
    __tablename__ = "digital_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False, index=True)  # external_id из catalog-service
    file_url = Column(String(500), nullable=False)  # Ссылка на файл
    file_format = Column(String(20), nullable=False)  # pdf, epub, fb2, etc.
    file_size_mb = Column(Integer, nullable=False)
    license_type = Column(String(50), default="single-user", nullable=False)
    drm_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AccessToken(Base):
    __tablename__ = "access_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("digital_assets.id"), nullable=False)
    loan_id = Column(Integer, nullable=False, index=True)  # external_id из lending-service
    token = Column(String(255), unique=True, nullable=False, index=True)  # UUID или JWT
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    
    asset = relationship("DigitalAsset")