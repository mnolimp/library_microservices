from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db import Base

class LoanStatus(enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class LoanType(enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"

class Loan(Base):
    __tablename__ = "loans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # external_id из user-service
    book_copy_id = Column(Integer, nullable=False, index=True)  # external_id из catalog-service
    digital_asset_id = Column(Integer, nullable=True, index=True)  # external_id из digital-service (для электронных)
    
    loan_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True))
    
    status = Column(Enum(LoanStatus), default=LoanStatus.ACTIVE, nullable=False)
    loan_type = Column(Enum(LoanType), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_loans_user_loan_date', 'user_id', 'loan_date'),
        Index('idx_loans_status_due_date', 'status', 'due_date'),
    )