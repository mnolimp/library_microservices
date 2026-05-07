from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
from typing import Optional, List
import re

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")
    full_name: str = Field(..., min_length=2, max_length=255, description="Полное имя")
    phone: Optional[str] = Field(None, max_length=20, description="Телефон")
    address: Optional[str] = Field(None, max_length=500, description="Адрес")

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    registered_at: datetime
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    total: int
    users: List[UserResponse]