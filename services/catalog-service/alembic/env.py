import asyncio
import os
import sys
import sqlalchemy
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_file)

# Добавляем путь к моделям
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base
from app import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Получаем URL из переменной окружения
DATABASE_URL = os.getenv("CATALOG_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not set!\n"
    )

# Убеждаемся, что используется asyncpg
if "postgresql://" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

print(f"Using database: {DATABASE_URL.split('@')[0].split('://')[1].split(':')[0] + ':***@' + DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    connectable = create_async_engine(DATABASE_URL, poolclass=sqlalchemy.pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())