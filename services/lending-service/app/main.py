from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import os

from app.database import get_db
from app.models import Loan
from app.schemas import (
    LoanCreate, LoanUpdate, LoanResponse, LoanReturn,
    LoanWithDetails, LoanListResponse, OverdueStats, LoanStatus
)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL")

app = FastAPI(
    title="Lending Service",
    description="Управление выдачей книг",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Константы для валидации
VALID_STATUSES = {"active", "returned", "overdue", "cancelled"}

async def verify_user_exists(user_id: int) -> bool:
    """Проверить существование пользователя через user-service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
            return response.status_code == 200
    except Exception:
        return False

async def verify_book_copy_exists(copy_id: int) -> tuple[bool, Optional[dict]]:
    """Проверить существование экземпляра книги через catalog-service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CATALOG_SERVICE_URL}/books/copies/{copy_id}")
            if response.status_code == 200:
                return True, response.json()
            return False, None
    except Exception:
        return False, None

async def get_user_info(user_id: int) -> Optional[dict]:
    """Получить информацию о пользователе"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{USER_SERVICE_URL}/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None

async def get_book_copy_info(copy_id: int) -> Optional[dict]:
    """Получить информацию об экземпляре книги"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CATALOG_SERVICE_URL}/copies/{copy_id}")
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None

async def get_book_info(book_id: int) -> Optional[dict]:
    """Получить информацию о книге по ID книги"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CATALOG_SERVICE_URL}/books/{book_id}")
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "lending"}

@app.get("/loans", response_model=LoanListResponse)
async def get_loans(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(100, ge=1, le=500, description="Максимальное количество записей"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    overdue_only: bool = Query(False, description="Только просроченные"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список выдач с пагинацией и фильтрацией"""
    
    count_query = select(func.count()).select_from(Loan)
    query = select(Loan)
    
    if user_id:
        query = query.where(Loan.user_id == user_id)
        count_query = count_query.where(Loan.user_id == user_id)
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")
        query = query.where(Loan.status == status)
        count_query = count_query.where(Loan.status == status)
    if overdue_only:
        query = query.where(
            and_(Loan.status == "active", Loan.due_date < func.now())
        )
        count_query = count_query.where(
            and_(Loan.status == "active", Loan.due_date < func.now())
        )
    
    total = await db.scalar(count_query)
    
    query = query.offset(skip).limit(limit).order_by(Loan.loan_date.desc())
    result = await db.execute(query)
    loans = result.scalars().all()
    
    return LoanListResponse(total=total or 0, loans=loans)

@app.get("/loans/{loan_id}", response_model=LoanResponse)
async def get_loan(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Получить выдачу по ID"""
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan with id {loan_id} not found"
        )
    
    return loan

@app.get("/loans/user/{user_id}", response_model=LoanListResponse)
async def get_user_loans(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(False, description="Только активные выдачи"),
    db: AsyncSession = Depends(get_db)
):
    """Получить все выдачи пользователя"""
    
    count_query = select(func.count()).where(Loan.user_id == user_id)
    query = select(Loan).where(Loan.user_id == user_id)
    
    if active_only:
        query = query.where(Loan.status == "active")
        count_query = count_query.where(Loan.status == "active")
    
    total = await db.scalar(count_query)
    
    query = query.offset(skip).limit(limit).order_by(Loan.loan_date.desc())
    result = await db.execute(query)
    loans = result.scalars().all()
    
    return LoanListResponse(total=total or 0, loans=loans)

@app.post("/loans", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def create_loan(loan: LoanCreate, db: AsyncSession = Depends(get_db)):
    """Создать новую выдачу (выдать книгу пользователю)"""
    
    # Проверяем существование пользователя
    if not await verify_user_exists(loan.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with id {loan.user_id} does not exist"
        )
    
    # Проверяем существование экземпляра книги
    copy_exists, copy_info = await verify_book_copy_exists(loan.book_copy_id)
    if not copy_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book copy with id {loan.book_copy_id} does not exist"
        )
    
    # Проверяем, что экземпляр доступен
    if copy_info and copy_info.get("status") != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Book copy {loan.book_copy_id} is not available (status: {copy_info.get('status')})"
        )
    
    # Проверяем, нет ли у пользователя активных просроченных выдач
    overdue_count = await db.scalar(
        select(func.count()).where(
            and_(
                Loan.user_id == loan.user_id,
                Loan.status == "active",
                Loan.due_date < func.now()
            )
        )
    )
    if overdue_count and overdue_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User has {overdue_count} overdue loans. Cannot issue new books."
        )
    
    # Создаем выдачу
    db_loan = Loan(**loan.model_dump())
    db.add(db_loan)
    await db.commit()
    await db.refresh(db_loan)
    
    return db_loan

@app.put("/loans/{loan_id}/return", response_model=LoanResponse)
async def return_loan(
    loan_id: int,
    return_data: LoanReturn = LoanReturn(),
    db: AsyncSession = Depends(get_db)
):
    """Вернуть книгу"""
    
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan with id {loan_id} not found"
        )
    
    if loan.status == "returned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book already returned"
        )
    
    loan.return_date = return_data.return_date or datetime.now()
    loan.status = "returned"
    
    await db.commit()
    await db.refresh(loan)
    
    return loan

@app.put("/loans/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: int,
    loan_update: LoanUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить информацию о выдаче"""
    
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan with id {loan_id} not found"
        )
    
    update_data = loan_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(loan, key, value)
    
    await db.commit()
    await db.refresh(loan)
    
    return loan

@app.get("/loans/{loan_id}/detailed", response_model=LoanWithDetails)
async def get_loan_detailed(loan_id: int, db: AsyncSession = Depends(get_db)):
    """Получить выдачу с деталями (пользователь + книга)"""
    
    result = await db.execute(select(Loan).where(Loan.id == loan_id))
    loan = result.scalar_one_or_none()
    
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan with id {loan_id} not found"
        )
    
    # Получаем данные из других сервисов
    user_info = await get_user_info(loan.user_id)
    copy_info = await get_book_copy_info(loan.book_copy_id)
    
    book_info = None
    if copy_info:
        book_info = await get_book_info(copy_info.get("book_id"))
    
    return LoanWithDetails(
        id=loan.id,
        user_id=loan.user_id,
        book_copy_id=loan.book_copy_id,
        loan_date=loan.loan_date,
        due_date=loan.due_date,
        return_date=loan.return_date,
        status=loan.status,
        created_at=loan.created_at,
        updated_at=loan.updated_at,
        user_email=user_info.get("email") if user_info else None,
        user_name=user_info.get("full_name") if user_info else None,
        book_title=book_info.get("title") if book_info else None,
        book_author=book_info.get("author") if book_info else None,
        copy_number=copy_info.get("copy_number") if copy_info else None
    )

@app.get("/users/{user_id}/loans-detailed", response_model=List[LoanWithDetails])
async def get_user_loans_detailed(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Получить все выдачи пользователя с деталями книг"""
    
    result = await db.execute(
        select(Loan)
        .where(Loan.user_id == user_id)
        .order_by(Loan.loan_date.desc())
        .limit(limit)
    )
    loans = result.scalars().all()
    
    # Получаем данные о пользователе (один запрос)
    user_info = await get_user_info(user_id)
    
    # Получаем данные о всех книгах (параллельно)
    detailed_loans = []
    for loan in loans:
        copy_info = await get_book_copy_info(loan.book_copy_id)
        book_info = None
        if copy_info:
            book_info = await get_book_info(copy_info.get("book_id"))
        
        detailed_loans.append(LoanWithDetails(
            id=loan.id,
            user_id=loan.user_id,
            book_copy_id=loan.book_copy_id,
            loan_date=loan.loan_date,
            due_date=loan.due_date,
            return_date=loan.return_date,
            status=loan.status,
            created_at=loan.created_at,
            updated_at=loan.updated_at,
            user_email=user_info.get("email") if user_info else None,
            user_name=user_info.get("full_name") if user_info else None,
            book_title=book_info.get("title") if book_info else None,
            book_author=book_info.get("author") if book_info else None,
            copy_number=copy_info.get("copy_number") if copy_info else None
        ))
    
    return detailed_loans

@app.get("/stats/overdue", response_model=OverdueStats)
async def get_overdue_loans(db: AsyncSession = Depends(get_db)):
    """Получить список просроченных выдач"""
    
    query = select(Loan).where(
        and_(Loan.status == "active", Loan.due_date < func.now())
    ).order_by(Loan.due_date)
    
    result = await db.execute(query)
    loans = result.scalars().all()
    
    return OverdueStats(
        total_overdue=len(loans),
        overdue_loans=loans
    )