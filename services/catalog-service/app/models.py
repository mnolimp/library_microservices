from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db import Base

class BookType(enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    BOTH = "both"

class CopyStatus(enum.Enum):
    AVAILABLE = "available"
    LOANED = "loaned"
    MAINTENANCE = "maintenance"
    LOST = "lost"

class Book(Base):
    __tablename__ = "books"
    
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
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    copy_number = Column(Integer, nullable=False)
    status = Column(Enum(CopyStatus), default=CopyStatus.AVAILABLE, nullable=False)
    location = Column(String(100))  # Для физических: номер стеллажа/полки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    book = relationship("Book", back_populates="copies")
    
    __table_args__ = (
        # Уникальность: одна книга не может иметь два экземпляра с одинаковым номером
        {'unique_constraint': 'uq_book_copy_number', 'columns': ('book_id', 'copy_number')},
    )