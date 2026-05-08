from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from app.database import get_db
from app.models import Book, BookCopy
from app.schemas import (
    BookCreate, BookUpdate, BookResponse, BookWithCopiesResponse,
    BookCopyCreate, BookCopyResponse
)
import msgpack
from fastapi import Response

app = FastAPI(
    title="Catalog Service",
    description="Управление каталогом книг и экземплярами",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Словари для валидации типов
VALID_BOOK_TYPES = {"physical", "digital", "both"}
VALID_COPY_STATUSES = {"available", "loaned", "maintenance", "lost"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "catalog"}

@app.get("/books", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(100, ge=1, le=500, description="Максимальное количество записей"),
    title: Optional[str] = Query(None, description="Фильтр по названию"),
    author: Optional[str] = Query(None, description="Фильтр по автору"),
    book_type: Optional[str] = Query(None, description="Фильтр по типу книги (physical, digital, both)"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список книг с пагинацией и фильтрацией"""
    query = select(Book)
    
    if title:
        query = query.where(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.where(Book.author.ilike(f"%{author}%"))
    if book_type:
        if book_type not in VALID_BOOK_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid book_type. Must be one of {VALID_BOOK_TYPES}")
        query = query.where(Book.book_type == book_type)
    
    query = query.offset(skip).limit(limit).order_by(Book.id)
    result = await db.execute(query)
    books = result.scalars().all()
    return books

@app.get("/books/{book_id}", response_model=BookWithCopiesResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Получить книгу по ID вместе с экземплярами"""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found"
        )
    
    # Загружаем копии
    copies_result = await db.execute(
        select(BookCopy).where(BookCopy.book_id == book_id)
    )
    copies = copies_result.scalars().all()
    
    return BookWithCopiesResponse.model_validate(book)

@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, db: AsyncSession = Depends(get_db)):
    """Создать новую книгу"""
    # Проверяем уникальность ISBN
    result = await db.execute(select(Book).where(Book.isbn == book.isbn))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book with ISBN {book.isbn} already exists"
        )
    
    db_book = Book(**book.model_dump())
    db.add(db_book)
    await db.commit()
    await db.refresh(db_book)
    return db_book

@app.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, book: BookUpdate, db: AsyncSession = Depends(get_db)):
    """Обновить информацию о книге"""
    result = await db.execute(select(Book).where(Book.id == book_id))
    db_book = result.scalar_one_or_none()
    
    if not db_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found"
        )
    
    update_data = book.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_book, key, value)
    
    await db.commit()
    await db.refresh(db_book)
    return db_book

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить книгу (каскадно удалит все экземпляры)"""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found"
        )
    
    await db.delete(book)
    await db.commit()

@app.get("/books/{book_id}/copies", response_model=List[BookCopyResponse])
async def get_book_copies(
    book_id: int,
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу (available, loaned, maintenance, lost)"),
    db: AsyncSession = Depends(get_db)
):
    """Получить все экземпляры книги"""
    # Проверяем существование книги
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    if not book_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found"
        )
    
    query = select(BookCopy).where(BookCopy.book_id == book_id)
    if status_filter:
        if status_filter not in VALID_COPY_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_COPY_STATUSES}")
        query = query.where(BookCopy.status == status_filter)
    
    result = await db.execute(query)
    copies = result.scalars().all()
    return copies

@app.post("/books/{book_id}/copies", response_model=BookCopyResponse, status_code=status.HTTP_201_CREATED)
async def add_book_copy(
    book_id: int,
    copy: BookCopyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Добавить новый экземпляр книги"""
    # Проверяем существование книги
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    if not book_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found"
        )
    
    # Проверяем уникальность номера экземпляра
    existing = await db.execute(
        select(BookCopy).where(
            and_(BookCopy.book_id == book_id, BookCopy.copy_number == copy.copy_number)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Copy number {copy.copy_number} already exists for this book"
        )
    
    db_copy = BookCopy(book_id=book_id, **copy.model_dump())
    db.add(db_copy)
    await db.commit()
    await db.refresh(db_copy)
    return db_copy

@app.put("/copies/{copy_id}/status", response_model=BookCopyResponse)
async def update_copy_status(
    copy_id: int,
    status: str = Query(..., description="Новый статус (available, loaned, maintenance, lost)"),
    db: AsyncSession = Depends(get_db)
):
    """Обновить статус экземпляра книги"""
    if status not in VALID_COPY_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_COPY_STATUSES}")
    
    result = await db.execute(select(BookCopy).where(BookCopy.id == copy_id))
    copy = result.scalar_one_or_none()
    
    if not copy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Copy with id {copy_id} not found"
        )
    
    copy.status = status
    await db.commit()
    await db.refresh(copy)
    return copy

@app.get("/stats/books")
async def get_books_stats(db: AsyncSession = Depends(get_db)):
    """Получить статистику по книгам"""
    # Общее количество книг
    total_books = await db.scalar(select(func.count()).select_from(Book))
    
    # Количество по типам
    physical = await db.scalar(
        select(func.count()).where(Book.book_type == "physical")
    )
    digital = await db.scalar(
        select(func.count()).where(Book.book_type == "digital")
    )
    both = await db.scalar(
        select(func.count()).where(Book.book_type == "both")
    )
    
    # Количество экземпляров по статусам
    available = await db.scalar(
        select(func.count()).where(BookCopy.status == "available")
    )
    loaned = await db.scalar(
        select(func.count()).where(BookCopy.status == "loaned")
    )
    total_copies = await db.scalar(select(func.count()).select_from(BookCopy))
    
    return {
        "total_books": total_books or 0,
        "books_by_type": {
            "physical": physical or 0,
            "digital": digital or 0,
            "both": both or 0
        },
        "copies_stats": {
            "available": available or 0,
            "loaned": loaned or 0,
            "total": total_copies or 0
        }
    }

@app.get("/internal/books/{book_id}")
async def get_book_internal(book_id: int, db: AsyncSession = Depends(get_db)):
    """Внутренний вызов: получить книгу (MessagePack)"""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    
    if not book:
        return Response(status_code=404)
    
    data = {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "book_type": book.book_type
    }
    
    return Response(
        content=msgpack.packb(data),
        media_type="application/x-msgpack"
    )


@app.get("/internal/copies/{copy_id}")
async def get_copy_internal(copy_id: int, db: AsyncSession = Depends(get_db)):
    """Внутренний вызов: получить экземпляр книги (MessagePack)"""
    result = await db.execute(select(BookCopy).where(BookCopy.id == copy_id))
    copy = result.scalar_one_or_none()
    
    if not copy:
        return Response(status_code=404)
    
    data = {
        "id": copy.id,
        "book_id": copy.book_id,
        "copy_number": copy.copy_number,
        "status": copy.status
    }
    
    return Response(
        content=msgpack.packb(data),
        media_type="application/x-msgpack"
    )


@app.get("/internal/books/by-isbn/{isbn}")
async def get_book_by_isbn_internal(isbn: str, db: AsyncSession = Depends(get_db)):
    """Внутренний вызов: получить книгу по ISBN (MessagePack)"""
    result = await db.execute(select(Book).where(Book.isbn == isbn))
    book = result.scalar_one_or_none()
    
    if not book:
        return Response(status_code=404)
    
    data = {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn
    }
    
    return Response(
        content=msgpack.packb(data),
        media_type="application/x-msgpack"
    )
