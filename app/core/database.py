"""
Конфигурация базы данных SQLAlchemy
"""
import os
import logging

from app.models.models import Base

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dotenv import load_dotenv
from typing import AsyncGenerator


load_dotenv()
db_url = os.getenv('SQLALCHEMY_DATABASE_URL')

logging.basicConfig(level=logging.INFO)

# Создание асинхронного движка
engine = create_async_engine(
    url=db_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии базы данных
    Yields:
        AsyncSession: Сессия базы данных
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logging.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Инициализация базы данныx.
    Проверяет соединение, но не создает таблицы автоматически
    """
    try:
        async with engine.begin() as conn:
            # Проверка соединения с базой данных
            await conn.execute(text("SELECT 1"))

        logging.info("Database connection established")
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        raise