from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from contextlib import asynccontextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA = os.getenv("SCHEMA", "auth")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with async_session_maker() as session:
        await session.execute(text(f"SET search_path TO {SCHEMA}"))
        yield session

@asynccontextmanager
async def get_db_context():
    async with async_session_maker() as session:
        await session.execute(text(f"SET search_path TO {SCHEMA}"))
        yield session
