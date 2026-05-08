from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    isbn: str = Field(..., min_length=5, max_length=20)
    publication_year: Optional[int] = Field(None, ge=1800, le=2025)
    description: Optional[str] = None
    book_type: str = Field(default="physical", pattern="^(physical|digital|both)$")

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    book_type: Optional[str] = Field(None, pattern="^(physical|digital|both)$")

class BookResponse(BookBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookCopyBase(BaseModel):
    copy_number: int = Field(..., ge=1)
    location: Optional[str] = None
    status: str = Field(default="available", pattern="^(available|loaned|maintenance|lost)$")

class BookCopyCreate(BookCopyBase):
    book_id: int

class BookCopyResponse(BookCopyBase):
    id: int
    book_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookWithCopiesResponse(BookResponse):
    copies: list[BookCopyResponse] = []