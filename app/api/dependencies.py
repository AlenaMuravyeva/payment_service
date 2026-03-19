"""
Зависимости для API endpoints
"""

from typing import Annotated

from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.payment_service import PaymentService
from app.services.bank_service import BankService


async def get_bank_service() -> BankService:
    """
    Dependency для получения сервиса Банка
    Returns:
        BankService: Экземпляр сервиса
    """

    return BankService()


async def get_payment_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        bank_service: Annotated[BankService, Depends(get_bank_service)]
) -> PaymentService:
    """
    Dependency для получения сервиса платежей
    Args:
        db: Сессия базы данных
        bank_service: Сервис банка
    Returns:
        PaymentService: Экземпляр сервиса платежей
    """

    return PaymentService(db, bank_service)
