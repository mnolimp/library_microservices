from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

# Константы для валидации
VALID_STATUSES = {"active", "returned", "overdue", "cancelled"}

class LoanStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class LoanBase(BaseModel):
    user_id: int = Field(..., gt=0, description="ID пользователя")
    book_copy_id: int = Field(..., gt=0, description="ID экземпляра книги")
    due_date: datetime = Field(..., description="Дата возврата")

class LoanCreate(LoanBase):
    pass

class LoanUpdate(BaseModel):
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(active|returned|overdue|cancelled)$")

class LoanResponse(LoanBase):
    id: int
    loan_date: datetime
    return_date: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class LoanReturn(BaseModel):
    return_date: Optional[datetime] = None
    
    @field_validator('return_date')
    @classmethod
    def validate_return_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v > datetime.now():
            raise ValueError('Return date cannot be in the future')
        return v

class LoanWithDetails(LoanResponse):
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    copy_number: Optional[int] = None

class LoanListResponse(BaseModel):
    total: int
    loans: List[LoanResponse]

class OverdueStats(BaseModel):
    total_overdue: int
    overdue_loans: List[LoanResponse]