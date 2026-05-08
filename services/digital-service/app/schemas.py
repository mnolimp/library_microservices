from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List

# Константы
VALID_FORMATS = {"pdf", "epub", "mobi"}

class DigitalBookBase(BaseModel):
    book_id: int = Field(..., gt=0, description="ID книги из catalog-service")
    file_url: str = Field(..., max_length=500, description="URL файла")
    file_size_bytes: Optional[int] = Field(None, ge=0, description="Размер файла в байтах")
    format: str = Field(default="pdf", description=f"Формат файла: {VALID_FORMATS}")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in VALID_FORMATS:
            raise ValueError(f'Format must be one of {VALID_FORMATS}')
        return v

class DigitalBookCreate(DigitalBookBase):
    pass

class DigitalBookUpdate(BaseModel):
    file_url: Optional[str] = Field(None, max_length=500)
    file_size_bytes: Optional[int] = Field(None, ge=0)
    format: Optional[str] = None

class DigitalBookResponse(DigitalBookBase):
    id: int
    access_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class DigitalAccessLogBase(BaseModel):
    digital_book_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    ip_address: Optional[str] = Field(None, max_length=45)

class DigitalAccessLogCreate(DigitalAccessLogBase):
    pass

class DigitalAccessLogResponse(DigitalAccessLogBase):
    id: int
    access_time: datetime
    
    class Config:
        from_attributes = True

class DigitalAccessRequest(BaseModel):
    user_id: int = Field(..., gt=0)
    book_id: int = Field(..., gt=0)

class DigitalAccessResponse(BaseModel):
    granted: bool
    file_url: Optional[str] = None
    message: str
    format: Optional[str] = None

class DigitalBookWithStats(DigitalBookResponse):
    access_logs_count: int = 0

class DigitalStats(BaseModel):
    total_digital_books: int
    total_accesses: int
    total_size_bytes: int
    by_format: dict
    most_accessed_books: List[DigitalBookResponse]