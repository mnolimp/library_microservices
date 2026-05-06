from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import init_db, get_db, engine

SERVICE_NAME = "lending_service"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()

app = FastAPI(title=SERVICE_NAME, version="0.1.0", lifespan=lifespan)

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверяет и приложение, и соединение с БД"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "service": SERVICE_NAME, "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "service": SERVICE_NAME, "database": "disconnected", "error": str(e)}
        )

@app.get("/")
async def root():
    return {"message": f"{SERVICE_NAME} is running", "docs": "/docs"}