"""
Главный модуль FastAPI приложения для работы с банком
"""
import os
import logging

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.database import init_db
from app.core.exceptions import add_exception_handlers

from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('SQLALCHEMY_DATABASE_URL')
origin = os.getenv('ORIGIN')

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Управление жизненным циклом приложения
    Args:
        app: Экземпляр FastAPI приложения
    Yields:
        None: Контекст выполнения приложения
    """

    # Startup
    logging.info("Starting payment service")
    await init_db()

    yield

    # Shutdown
    logging.info("Shutting down payment service")


def create_app() -> FastAPI:
    """
    Создание и настройка FastAPI приложения
    Returns:
        FastAPI: Настроенное приложение
    """

    app = FastAPI(
        title="Service orders payment",
        description="API для работы с платежами по заказам.",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    # Exception handlers
    add_exception_handlers(app)

    # API routers
    app.include_router(api_router, prefix="/app")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Проверка состояния API"""
        return {"status": "healthy"}

    return app


app = create_app()
