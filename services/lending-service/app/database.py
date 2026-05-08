from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA = "lending"

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with async_session_maker() as session:
        await session.execute(text(f"SET search_path TO {SCHEMA}"))
        yield session