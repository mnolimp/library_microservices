from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class DigitalFormat(str, enum.Enum):
    PDF = "pdf"
    EPUB = "epub"
    MOBI = "mobi"

class DigitalBook(Base):
    __tablename__ = "digital_books"
    __table_args__ = {"schema": "digital"}
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False, unique=True)
    file_url = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger)
    format = Column(Enum(DigitalFormat), default=DigitalFormat.PDF)
    access_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DigitalAccessLog(Base):
    __tablename__ = "digital_access_log"
    __table_args__ = {"schema": "digital"}
    
    id = Column(Integer, primary_key=True, index=True)
    digital_book_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    access_time = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))  # IPv6 может быть 45 символов