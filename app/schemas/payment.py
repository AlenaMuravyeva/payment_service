"""
Pydantic схемы для работы с платежами
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field
from app.models.models import PaymentState


class PaymentCreateRequest(BaseModel):
    """
    Схема запроса на создание платежа
    """

    amount: Decimal = Field(...,gt=0, le=999999999999, description="Сумма платежа в рублях")
    order_id: int = Field(..., description="ID записи в таблице orders")


class PaymentCreateResponse(BaseModel):
    """
    Схема ответа на создание платежа
    """

    success: bool = Field(..., description="Статус успешности операции")
    order_id: int = Field(..., description="ID заказа в таблице orders")
    amount: Optional[Decimal] = Field(default=None, description="Сумма платежа")
    payment_id: Optional[int] = Field(..., description="Уникальный ID платежа в базе")
    message: Optional[str] = Field(default=None, description="Сообщение о статусе платежа")
    bank_order_id: Optional[str] = Field(default=None, description="Уникальный ID платежа в банке")


class PaymentStatusResponse(BaseModel):
    """
    Схема ответа на запрос статуса платежа
    """

    success: bool = Field(..., description="Статус успешности операции")
    order_id: Optional[int] = Field(..., description="ID заказа в таблице orders ")
    amount: Optional[Decimal] = Field(default=None, description="Сумма платежа")
    status: Optional[str] = Field(default=None, description="Cтатус платежа")
    bank_order_id: Optional[str] = Field(default=None, description="Уникальный ID платежа в банке")
    created_at: Optional[datetime] = Field(default=None, description="Дата создания")
    operation_time: Optional[datetime] = Field(default=None, description="Время операции")


class PaymentRefundResponse(BaseModel):
    """
    Схема ответа на возврат платежа
    """

    success: bool = Field(..., description="Статус успешности операции")
    payment_id: int = Field(..., description="ID платежа  в таблице payments")
    bank_order_id: str = Field(..., description="Уникальный ID платежа в банке")
    status: PaymentState = Field(..., description="Cтатус платежа")
    refund_amount: Optional[Decimal] = Field(..., description="Сумма возврата")
    message: str = Field(..., description="Сообщение об операции")
