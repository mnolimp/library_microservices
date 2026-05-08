from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from typing import Optional, List
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse, UserListResponse
import msgpack
from fastapi import Response

app = FastAPI(title="user-service", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "user-service"}

@app.get("/users", response_model=UserListResponse)
async def get_users(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(100, ge=1, le=500, description="Максимальное количество записей"),
    email: Optional[str] = Query(None, description="Фильтр по email (частичное совпадение)"),
    full_name: Optional[str] = Query(None, description="Фильтр по имени (частичное совпадение)"),
    is_active: Optional[bool] = Query(None, description="Фильтр по статусу"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список пользователей с пагинацией и фильтрацией"""
    
    # Запрос для общего количества
    count_query = select(func.count()).select_from(User)
    
    # Основной запрос
    query = select(User)
    
    if email:
        query = query.where(User.email.ilike(f"%{email}%"))
        count_query = count_query.where(User.email.ilike(f"%{email}%"))
    if full_name:
        query = query.where(User.full_name.ilike(f"%{full_name}%"))
        count_query = count_query.where(User.full_name.ilike(f"%{full_name}%"))
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    # Получаем общее количество
    total = await db.scalar(count_query)
    
    # Получаем пользователей
    query = query.offset(skip).limit(limit).order_by(User.id)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(total=total or 0, users=users)

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Получить пользователя по ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    return user

@app.get("/users/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """Получить пользователя по email"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found"
        )
    
    return user

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Создать нового пользователя"""
    # Проверяем уникальность email
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {user.email} already exists"
        )
    
    db_user = User(**user.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Обновить данные пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    update_data = user.model_dump(exclude_unset=True)
    
    # Если обновляем email, проверяем уникальность
    if "email" in update_data and update_data["email"] != db_user.email:
        existing = await db.execute(select(User).where(User.email == update_data["email"]))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with email {update_data['email']} already exists"
            )
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить пользователя (мягкое удаление - деактивировать)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Мягкое удаление - деактивируем
    user.is_active = False
    await db.commit()

@app.delete("/users/{user_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Полностью удалить пользователя из БД"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    await db.delete(user)
    await db.commit()

@app.patch("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Активировать пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    return user

@app.patch("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Деактивировать пользователя"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user

@app.get("/internal/users/{user_id}")
async def get_user_internal(user_id: int, db: AsyncSession = Depends(get_db)):
    """Внутренний вызов: получить пользователя (MessagePack)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        return Response(status_code=404)
    
    data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active
    }
    
    return Response(
        content=msgpack.packb(data),
        media_type="application/x-msgpack"
    )


@app.get("/internal/users/by-email/{email}")
async def get_user_by_email_internal(email: str, db: AsyncSession = Depends(get_db)):
    """Внутренний вызов: получить пользователя по email (MessagePack)"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        return Response(status_code=404)
    
    data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name
    }
    
    return Response(
        content=msgpack.packb(data),
        media_type="application/x-msgpack"
    )