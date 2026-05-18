from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import os

from app.database import get_db
from app.models import DigitalBook, DigitalAccessLog
from app.schemas import (
    DigitalBookCreate, DigitalBookUpdate, DigitalBookResponse,
    DigitalAccessLogCreate, DigitalAccessLogResponse,
    DigitalAccessRequest, DigitalAccessResponse,
    DigitalBookWithStats, DigitalStats
)
from app.auth import require_admin, require_user, UserPrincipal

# URL других сервисов
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://catalog-service:8001")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8002")

app = FastAPI(
    title="Digital Service",
    description="Управление электронными книгами и доступом",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

async def verify_book_exists(book_id: int) -> tuple[bool, Optional[dict]]:
    """Проверить существование книги в catalog-service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CATALOG_SERVICE_URL}/books/{book_id}")
            if response.status_code == 200:
                book_data = response.json()
                # Проверяем, что книга поддерживает цифровой формат
                book_type = book_data.get("book_type")
                if book_type in ["digital", "both"]:
                    return True, book_data
                return False, {"error": f"Book does not support digital format. Type: {book_type}"}
            return False, None
    except Exception as e:
        return False, None

async def verify_user_exists(user_id: int) -> bool:
    """Проверить существование пользователя в user-service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
            return response.status_code == 200
    except Exception:
        return False

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "digital"}

@app.get("/digital-books", response_model=List[DigitalBookResponse])
async def get_digital_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    book_id: Optional[int] = Query(None, description="Фильтр по book_id"),
    format: Optional[str] = Query(None, description="Фильтр по формату"),
    db: AsyncSession = Depends(get_db),
    principal: UserPrincipal = Depends(require_user),
):
    """Получить список электронных книг"""
    query = select(DigitalBook)
    
    if book_id:
        query = query.where(DigitalBook.book_id == book_id)
    if format:
        query = query.where(DigitalBook.format == format)
    
    query = query.offset(skip).limit(limit).order_by(DigitalBook.id)
    result = await db.execute(query)
    books = result.scalars().all()
    return books

@app.get("/digital-books/{digital_book_id}", response_model=DigitalBookResponse)
async def get_digital_book(digital_book_id: int, db: AsyncSession = Depends(get_db), principal: UserPrincipal = Depends(require_user)):
    """Получить электронную книгу по ID"""
    result = await db.execute(select(DigitalBook).where(DigitalBook.id == digital_book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital book with id {digital_book_id} not found"
        )
    return book

@app.get("/digital-books/by-book/{book_id}", response_model=DigitalBookResponse)
async def get_digital_book_by_book_id(book_id: int, db: AsyncSession = Depends(get_db), principal: UserPrincipal = Depends(require_user)):
    """Получить электронную книгу по ID оригинальной книги"""
    result = await db.execute(select(DigitalBook).where(DigitalBook.book_id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital book for book_id {book_id} not found"
        )
    return book

@app.post("/digital-books", response_model=DigitalBookResponse, status_code=status.HTTP_201_CREATED)
async def create_digital_book(
    digital_book: DigitalBookCreate,
    db: AsyncSession = Depends(get_db),
    principal: UserPrincipal = Depends(require_admin),
):
    """Создать электронную версию книги"""
    
    # Проверяем существование книги в catalog-service
    exists, book_data = await verify_book_exists(digital_book.book_id)
    if not exists:
        error_msg = book_data.get("error") if book_data else "Book does not exist or does not support digital format"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Проверяем, нет ли уже цифровой версии
    existing = await db.execute(
        select(DigitalBook).where(DigitalBook.book_id == digital_book.book_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Digital version for book {digital_book.book_id} already exists"
        )
    
    db_book = DigitalBook(**digital_book.model_dump())
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book

@app.put("/digital-books/{digital_book_id}", response_model=DigitalBookResponse)
async def update_digital_book(
    digital_book_id: int,
    digital_book: DigitalBookUpdate,
    db: AsyncSession = Depends(get_db),
    principal: UserPrincipal = Depends(require_admin),
):
    """Обновить информацию об электронной книге"""
    result = await db.execute(select(DigitalBook).where(DigitalBook.id == digital_book_id))
    db_book = result.scalar_one_or_none()
    
    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital book with id {digital_book_id} not found"
        )
    
    update_data = digital_book.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_book, key, value)
    
    await db.commit()
    await db.refresh(db_book)
    return db_book

@app.delete("/digital-books/{digital_book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_digital_book(digital_book_id: int, db: AsyncSession = Depends(get_db), principal: UserPrincipal = Depends(require_admin)):
    """Удалить электронную книгу"""
    result = await db.execute(select(DigitalBook).where(DigitalBook.id == digital_book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital book with id {digital_book_id} not found"
        )
    
    await db.delete(book)
    await db.commit()

@app.post("/access/request", response_model=DigitalAccessResponse)
async def request_access(
    request: DigitalAccessRequest,
    db: AsyncSession = Depends(get_db),
    principal: UserPrincipal = Depends(require_user),
):
    """Запросить доступ к электронной книге"""
    
    # Проверяем пользователя
    if not await verify_user_exists(request.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id {request.user_id} does not exist"
        )

@app.get("/access/logs", response_model=List[DigitalAccessLogResponse])
async def get_access_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    user_id: Optional[int] = Query(None),
    digital_book_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    principal: UserPrincipal = Depends(require_admin),
):
    """Получить логи доступа"""
    query = select(DigitalAccessLog)
    
    if user_id:
        query = query.where(DigitalAccessLog.user_id == user_id)
    if digital_book_id:
        query = query.where(DigitalAccessLog.digital_book_id == digital_book_id)
    
    query = query.offset(skip).limit(limit).order_by(desc(DigitalAccessLog.access_time))
    result = await db.execute(query)
    logs = result.scalars().all()
    return logs

@app.get("/access/check/{user_id}/{book_id}")
async def check_access(
    user_id: int,
    book_id: int,
    db: AsyncSession = Depends(get_db),
    principal: UserPrincipal = Depends(require_user),
):
    """Проверить, есть ли у пользователя доступ к книге"""
    
    # Находим цифровую книгу
    result = await db.execute(
        select(DigitalBook).where(DigitalBook.book_id == book_id)
    )
    digital_book = result.scalar_one_or_none()
    
    if not digital_book:
        return {"has_access": False, "message": "No digital version available"}
    
    # Проверяем логи доступа за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    access_log = await db.execute(
        select(DigitalAccessLog).where(
            and_(
                DigitalAccessLog.digital_book_id == digital_book.id,
                DigitalAccessLog.user_id == user_id,
                DigitalAccessLog.access_time >= thirty_days_ago
            )
        )
    )
    
    has_access = access_log.scalar_one_or_none() is not None
    
    return {
        "has_access": has_access,
        "digital_book_id": digital_book.id,
        "message": "Access granted" if has_access else "No recent access found"
    }

@app.get("/stats", response_model=DigitalStats)
async def get_stats(db: AsyncSession = Depends(get_db), principal: UserPrincipal = Depends(require_admin)):
    """Получить статистику по цифровым книгам"""
    
    total_books = await db.scalar(select(func.count()).select_from(DigitalBook))
    total_accesses = await db.scalar(select(func.count()).select_from(DigitalAccessLog))
    total_size = await db.scalar(select(func.sum(DigitalBook.file_size_bytes))) or 0
    
    # Статистика по форматам
    format_stats = await db.execute(
        select(DigitalBook.format, func.count())
        .group_by(DigitalBook.format)
    )
    by_format = {row[0]: row[1] for row in format_stats}
    
    # Самые популярные книги
    popular = await db.execute(
        select(DigitalBook)
        .order_by(desc(DigitalBook.access_count))
        .limit(5)
    )
    most_accessed = popular.scalars().all()
    
    return DigitalStats(
        total_digital_books=total_books or 0,
        total_accesses=total_accesses or 0,
        total_size_bytes=total_size or 0,
        by_format=by_format,
        most_accessed_books=most_accessed
    )