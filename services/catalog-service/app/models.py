from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Book(Base):
    __tablename__ = "books"
    __table_args__ = {"schema": "catalog"}
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    isbn = Column(String(20), unique=True, nullable=False, index=True)
    publication_year = Column(Integer)
    description = Column(String(2000))
    book_type = Column(String(20), default="physical", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    copies = relationship("BookCopy", back_populates="book", cascade="all, delete-orphan")

class BookCopy(Base):
    __tablename__ = "book_copies"
    __table_args__ = {"schema": "catalog"}
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("catalog.books.id"), nullable=False)
    copy_number = Column(Integer, nullable=False)
    status = Column(String(20), default="available", nullable=False)
    location = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    book = relationship("Book", back_populates="copies")