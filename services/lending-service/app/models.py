from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base

class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index("idx_loans_user_id", "user_id"),
        Index("idx_loans_book_copy_id", "book_copy_id"),
        Index("idx_loans_status", "status"),
        Index("idx_loans_due_date", "due_date"),
        Index("idx_loans_user_status", "user_id", "status"),
        {"schema": "lending"},
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, comment="ID пользователя из user-service")
    book_copy_id = Column(Integer, nullable=False, comment="ID экземпляра книги из catalog-service")
    loan_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())