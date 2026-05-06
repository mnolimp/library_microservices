from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db import Base

class UserStatus(enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    HAS_DEBT = "has_debt"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    registration_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    max_loans = Column(Integer, default=5, nullable=False)  # Макс. количество активных займов
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())