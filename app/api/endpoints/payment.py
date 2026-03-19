from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_payment_service
from app.core.exceptions import PaymentException
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentStatusResponse,
    PaymentRefundResponse
)
from app.services.payment_service import PaymentService

router = APIRouter()


@router.post(
    "/create",
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание платежа",
    description="Создание нового платежа через API банка"
)
async def create_payment(
        request: PaymentCreateRequest,
        payment_service: Annotated[PaymentService, Depends(get_payment_service)]
) -> PaymentCreateResponse:
    """
    Создание нового платежа
    Args:
        request: Данные для создания платежа
        payment_service: Сервис для работы с платежами
    Returns:
        PaymentCreateResponse: Результат создания платежа
    Raises:
        HTTPException: При ошибке создания платежа
    """

    try:
        return await payment_service.create_payment(request)
    except PaymentException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/status/{bank_order_id}",
    response_model=PaymentStatusResponse,
    summary="Получение статуса платежа",
    description="Получение статуса платежа по уникальному ID платежа банке"
)
async def get_payment_status(
        bank_order_id: str,
        payment_service: Annotated[PaymentService, Depends(get_payment_service)]
) -> PaymentStatusResponse:
    """
    Получение статуса платежа
    Args:
        bank_order_id: bank_order_id  в таблице acquiring
        payment_service: Сервис для работы с платежами
    Returns:
        PaymentStatusResponse: Статус платежа
    Raises:
        HTTPException: При ошибке получения статуса
    """

    try:
        return await payment_service.get_payment_status(bank_order_id)
    except PaymentException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post(
    "/refund/{bank_order_id}",
    response_model=PaymentRefundResponse,
    summary="Возврат платежа",
    description="Возврат платежа, обновление статуса оплаты заказа"
)
async def refund_payment(
        bank_order_id: str,
        payment_service: Annotated[PaymentService, Depends(get_payment_service)]
) -> PaymentRefundResponse:
    """
    Возврат платежа
    Args:
        bank_order_id: ID заказа в банке
        payment_service: Сервис для работы с платежами
    Returns:
        PaymentRefundResponse: Результат возврата платежа
    Raises:
        HTTPException: При ошибке возврата платежа
    """

    try:
        return await payment_service.refund_payment(bank_order_id)
    except PaymentException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
