"""
Роуты
"""

from fastapi import APIRouter

from app.api.endpoints import payment

api_router = APIRouter()

# Подключение роутов
api_router.include_router(
    payment.router,
    prefix="",
    tags=["payments"]
)
