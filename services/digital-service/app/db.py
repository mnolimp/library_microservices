from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv("DIGITAL_DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Для миграций
async def get_db():
    async with async_session_maker() as session:
        yield session

async def init_db():
    """Создать таблицы, если не существуют"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)