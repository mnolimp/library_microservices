from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

class AuthUser(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # null для OAuth-пользователей
    full_name = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    github_id = Column(String(64), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OAuthState(Base):
    __tablename__ = "oauth_states"
    __table_args__ = {"schema": "auth"}

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
