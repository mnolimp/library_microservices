from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base

class BookType(str, enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    BOTH = "both"

class CopyStatus(str, enum.Enum):
    AVAILABLE = "available"
    LOANED = "loaned"
    MAINTENANCE = "maintenance"
    LOST = "lost"

class Book(Base):
    __tablename__ = "books"
    __table_args__ = {"schema": "catalog"}
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    isbn = Column(String(20), unique=True, nullable=False, index=True)
    publication_year = Column(Integer)
    description = Column(String(2000))
    book_type = Column(Enum(BookType), default=BookType.BOTH, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    copies = relationship("BookCopy", back_populates="book", cascade="all, delete-orphan")

class BookCopy(Base):
    __tablename__ = "book_copies"
    __table_args__ = {"schema": "catalog"}
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("catalog.books.id"), nullable=False)
    copy_number = Column(Integer, nullable=False)
    status = Column(Enum(CopyStatus), default=CopyStatus.AVAILABLE, nullable=False)
    location = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    book = relationship("Book", back_populates="copies")